"""Validated file preparation and an unchanged, local Hama computation engine."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import numpy as np

VERSION = '2.1.0'


class DataError(ValueError):
    def __init__(self, key, detail=''):
        self.key, self.detail = key, str(detail)
        super().__init__(key + (': ' + str(detail) if detail else ''))


def resources():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


@dataclass
class Table:
    path: str
    values: np.ndarray
    skipped_headers: int = 0
    source_sha256: str = ''


@dataclass(frozen=True)
class Settings:
    k_col: int = 0
    chi_col: int = 1
    input_weight: int = 0
    weight: int = 2
    kmin: float = 2.0
    kmax: float = 12.0
    rmin: float = 0.0
    rmax: float = 5.0
    wavelet: str = 'Morlet'
    kappa: float = 15.0
    sigma: float = 1.0
    cauchy_n: int = 50
    resample: bool = False


@dataclass
class Result:
    name: str
    source: str
    k: np.ndarray
    chi: np.ndarray
    weighted: np.ndarray
    grid_k: np.ndarray
    grid_r: np.ndarray
    magnitude: np.ndarray
    raw_xyz: np.ndarray
    metadata: dict
    log: str
    parameters: str


def read_table(path):
    p = Path(path)
    if p.stat().st_size > 20_000_000:
        raise DataError('file_large')
    blob = p.read_bytes()
    for encoding in ('utf-8-sig', 'gb18030', 'utf-16'):
        try:
            text = blob.decode(encoding)
            if '\x00' not in text:
                break
        except UnicodeError:
            continue
    else:
        raise DataError('encoding')
    rows, headers, width = [], 0, None
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith(('#', '!', ';', '//')):
            continue
        line = re.split(r'\s+#|\s+!', line, maxsplit=1)[0]
        # Delimited tables keep empty fields, so a missing cell cannot shift columns.
        fields = line.split(',') if ',' in line else line.split('\t') if '\t' in line else line.split()
        try:
            row = [float(v.strip().strip('"').replace('D', 'E').replace('d', 'e')) for v in fields]
        except ValueError:
            if rows:
                raise DataError('bad_row', f'Line / 行 {number}: {line[:160]}')
            headers += 1
            continue
        if len(row) < 2:
            raise DataError('columns', f'Line / 行 {number}: {len(row)} columns')
        if width is None:
            width = len(row)
        if len(row) != width:
            raise DataError('columns', f'Line / 行 {number}: expected {width}, found {len(row)} columns')
        rows.append(row)
    if len(rows) < 20:
        raise DataError('few_points', len(rows))
    return Table(str(p.resolve()), np.asarray(rows, dtype=float), headers, hashlib.sha256(blob).hexdigest())


def prepare(table, s):
    if s.k_col == s.chi_col or min(s.k_col, s.chi_col) < 0 or max(s.k_col, s.chi_col) >= table.values.shape[1]:
        raise DataError('column_selection')
    if s.input_weight not in range(4) or s.weight not in range(4):
        raise DataError('weight')
    if not np.isfinite([s.kmin, s.kmax, s.rmin, s.rmax, s.kappa, s.sigma]).all():
        raise DataError('range')
    if not (0 <= s.kmin < s.kmax <= 40 and 0 <= s.rmin < s.rmax <= 15):
        raise DataError('range')
    if s.wavelet not in ('Morlet', 'Cauchy') or not (1 <= s.kappa <= 40 and .2 <= s.sigma <= 5 and 2 <= s.cauchy_n <= 200):
        raise DataError('wavelet_parameters')
    k, y = table.values[:, s.k_col], table.values[:, s.chi_col]
    if not np.isfinite(k).all() or not np.isfinite(y).all():
        bad = np.flatnonzero(~np.isfinite(k) | ~np.isfinite(y))[:10] + 1
        raise DataError('nonfinite', 'Numeric data rows / 数值数据行: ' + ', '.join(map(str, bad)))
    if np.any(k < 0) or np.any(k > 40):
        raise DataError('not_k')
    if np.any(np.diff(k) <= 0):
        bad = np.flatnonzero(np.diff(k) <= 0)[:10] + 2
        raise DataError('increasing', 'Numeric data rows / 数值数据行: ' + ', '.join(map(str, bad)))
    tolerance = 1e-7
    if s.kmin < k[0] - tolerance or s.kmax > k[-1] + tolerance:
        raise DataError('outside', f'{k[0]:g} – {k[-1]:g}')
    mask = (k >= s.kmin - tolerance) & (k <= s.kmax + tolerance)
    k, y = k[mask].copy(), y[mask].copy()
    if len(k) < 20:
        raise DataError('few_points', len(k))
    if len(k) > 801:
        raise DataError('many_points', len(k))
    if s.input_weight:
        if np.any(k <= 0):
            raise DataError('zero_weight')
        y = y / k ** s.input_weight
    step = np.diff(k)
    irregular = not np.allclose(step, np.median(step), rtol=1e-3, atol=1e-6)
    if irregular and not s.resample:
        raise DataError('irregular')
    if irregular:
        grid = np.linspace(k[0], k[-1], len(k))
        y = np.interp(grid, k, y)
        k = grid
    if not np.any(np.abs(y) > 0):
        raise DataError('zero_signal')
    return k, y, irregular


def calculate(table, settings, cancel=None, timeout=240, exe=None):
    cancel = cancel or threading.Event()
    k, chi, resampled = prepare(table, settings)
    if cancel.is_set():
        raise DataError('cancelled')
    from engine_manager import verified_engine, work_directory
    exe = verified_engine(exe)
    helper = resources() / 'helpers' / 'plot_bridge.exe'
    if not helper.is_file():
        raise DataError('engine_missing')
    with work_directory() as folder:
        job = Path(folder)
        shutil.copy2(exe, job / 'hama.exe')
        shutil.copy2(helper, job / 'WGNUPLOT.EXE')
        np.savetxt(job / 'input.dat', np.column_stack((k, chi)), fmt='%.17e')
        answers = ['1', 'result.dat', '0', 'input.dat', str(settings.weight), 'N',
                   str(settings.rmin), str(settings.rmax), '1' if settings.wavelet == 'Morlet' else '2']
        answers += [str(settings.kappa), str(settings.sigma)] if settings.wavelet == 'Morlet' else [str(settings.cauchy_n)]
        answers += ['N', 'N']
        start = time.monotonic()
        with (job / 'run.log').open('wb') as log_file:
            proc = subprocess.Popen([str(job / 'hama.exe')], cwd=job, stdin=subprocess.PIPE,
                                    stdout=log_file, stderr=subprocess.STDOUT,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            try:
                proc.stdin.write(('\n'.join(answers) + '\n').encode('ascii'))
                proc.stdin.close()
                while proc.poll() is None:
                    if cancel.wait(.08):
                        raise DataError('cancelled')
                    if time.monotonic() - start > timeout:
                        raise DataError('timeout')
            finally:
                if proc.poll() is None:
                    # Hama launches a short-lived plotting helper. Stop the entire
                    # owned process tree so its inherited log handle cannot survive.
                    if os.name == 'nt':
                        subprocess.run([str(Path(os.environ.get('WINDIR', 'C:/Windows')) / 'System32' / 'taskkill.exe'),
                                        '/PID', str(proc.pid), '/T', '/F'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
                    if proc.poll() is None:
                        proc.terminate()
                    proc.wait(timeout=10)
        log = (job / 'run.log').read_text(encoding='ascii', errors='replace')
        if proc.returncode != 0 or not (job / 'result.dat').exists():
            raise DataError('engine_failed', log[-1500:])
        xyz = np.loadtxt(job / 'result.dat')
        if xyz.ndim != 2 or xyz.shape[1] != 3 or not np.isfinite(xyz).all():
            raise DataError('bad_result')
        gk, gr = np.unique(xyz[:, 0]), np.unique(xyz[:, 1])
        if len(xyz) != len(gk) * len(gr):
            raise DataError('bad_result')
        order = np.lexsort((xyz[:, 1], xyz[:, 0]))
        z = xyz[order, 2].reshape(len(gk), len(gr)).T
        valid = (gk >= k[0] - 1e-5) & (gk <= k[-1] + 1e-5)
        if not np.any(valid):
            raise DataError('bad_result')
        parameters = (job / 'parameters.txt').read_text(encoding='ascii', errors='replace').replace('\x00', '')
        source = Path(table.path)
        metadata = {
            'app_version': VERSION, 'engine': 'Original Hama Fortran executable (Funke / Chukalina)',
            'engine_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(),
            'source': table.path,
            'selected_data_sha256': hashlib.sha256(np.column_stack((k, chi)).tobytes()).hexdigest(),
            'settings': asdict(settings), 'actual_k_range': [float(k[0]), float(k[-1])],
            'input_points': len(k), 'linear_resampling_applied': bool(resampled),
            'additional_window': 'none; native Hama calculation',
            'phase_correction': False, 'color_values': 'raw Hama WT values, not normalized',
            'display_domain': 'measured k interval only; full Hama extension is exported separately',
            'headers_skipped': table.skipped_headers,
            'elapsed_seconds': round(time.monotonic() - start, 3),
        }
        if table.source_sha256:
            metadata['source_sha256'] = table.source_sha256
        return Result(source.stem, table.path, k, chi, chi * k ** settings.weight,
                      gk[valid], gr, z[:, valid], xyz, metadata, log, parameters)


def export_result(result, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    kk, rr = np.meshgrid(result.grid_k, result.grid_r, indexing='ij')
    np.savetxt(folder / 'origin_xyz.txt', np.column_stack((kk.ravel(), rr.ravel(), result.magnitude.T.ravel())),
               fmt='%.10e', header='k_A^-1 R_A WT_raw')
    np.savetxt(folder / 'hama_full_grid.txt', result.raw_xyz, fmt='%.10e', header='k_A^-1 R_A WT_raw; extended grid is not new experimental data')
    np.savetxt(folder / 'prepared_chi.txt', np.column_stack((result.k, result.chi, result.weighted)),
               fmt='%.12e', header='k_A^-1 chi k^weight_chi')
    np.savez_compressed(folder / 'result.npz', k=result.grid_k, r=result.grid_r, wt=result.magnitude)
    (folder / 'parameters.json').write_text(json.dumps(result.metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'hama_parameters.txt').write_text(result.parameters, encoding='utf-8')
    (folder / 'hama_run.log').write_text(result.log, encoding='utf-8')
    return folder


def make_demo(folder):
    """Synthetic signals, explicitly marked, not experimental Ni/Se spectra."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    k = np.linspace(2, 14, 241)
    paths = []
    for name, center, ratio in [('Demo_A_SYNTHETIC', 6.0, .70), ('Demo_B_SYNTHETIC', 7.3, .42)]:
        chi = (.04 * np.exp(-((k-center)/2.4)**2) * np.sin(2*2.1*k + .3)
               + .04 * ratio * np.exp(-((k-9)/2.0)**2) * np.sin(2*3.1*k + .6))
        p = folder / (name + '.txt')
        np.savetxt(p, np.column_stack((k, chi)), fmt='%.12e', header='SYNTHETIC DEMO ONLY - not experimental data\nk chi')
        paths.append(p)
    return paths
