"""Desktop host. All scientific data and execution remain on the local PC."""
from __future__ import annotations
from dataclasses import asdict
from functools import wraps
import copy
import json
import os
from pathlib import Path
import threading
import time
import webbrowser
import numpy as np
import webview
from core import DataError, Settings, VERSION, calculate, make_demo, prepare, read_table, resources
from engine_manager import HOME, DOWNLOAD, app_data, download_engine, engine_status, import_engine, preferences, save_preferences, verified_engine, work_root
from exports import export_selected, origin_available, preview
from issues import issue


def safe(method):
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        try:
            return {'ok': True, 'data': method(self, *args, **kwargs)}
        except Exception as exc:
            return {'ok': False, 'error': issue(exc, getattr(exc, 'where', method.__name__))}
    return wrapped


class DesktopApi:
    def __init__(self):
        self._window = None
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._thread = None
        self._tables = []
        self._results = []
        self._revision = 0
        self._state = {'busy': False, 'phase': 'ready', 'done': 0, 'total': 0, 'current': '', 'errors': [], 'export': None, 'started': 0}
        self._engine = engine_status()
        self._origin = origin_available()

    def _idle(self):
        if self._state['busy']:
            raise DataError('busy')

    def _job(self, phase, function):
        with self._lock:
            self._idle()
            self._cancel.clear()
            self._state.update(busy=True, phase=phase, done=0, total=1, current='', errors=[], started=time.monotonic())
            if phase == 'exporting':
                self._state['export'] = None
        def run():
            try:
                function()
            except Exception as e:
                with self._lock:
                    self._state['errors'].append(issue(e, self._state['current'] or phase))
            finally:
                with self._lock:
                    self._state['busy'] = False
                    self._state['phase'] = 'finished'
                    self._engine = engine_status()
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        return True

    def _load(self, paths):
        with self._lock:
            self._idle()
            errors = []
            for path in paths:
                if any(t.path == str(Path(path).resolve()) for t in self._tables):
                    continue
                if len(self._tables) >= 8:
                    raise DataError('file_large', 'Maximum 8 samples per batch / 每批最多 8 个样品')
                try:
                    self._tables.append(read_table(path))
                except Exception as e:
                    errors.append(issue(e, path))
            self._results = []
            self._revision += 1
            self._state['errors'] = errors
            self._state['export'] = None
        return len(paths)

    @safe
    def get_state(self):
        with self._lock:
            state = copy.deepcopy(self._state)
            state.update(version=VERSION, engine=self._engine, origin=self._origin,
                         language=preferences().get('language', 'zh'), revision=self._revision,
                         elapsed=round(time.monotonic() - state['started']) if state['busy'] else 0,
                         inputs=[{'name': Path(t.path).name, 'path': t.path, 'rows': len(t.values), 'cols': t.values.shape[1], 'headers': t.skipped_headers} for t in self._tables],
                         results=[{'name': r.name, 'metadata': r.metadata} for r in self._results])
        return state

    @safe
    def set_language(self, language):
        if language in ('zh', 'en'):
            with self._lock:
                save_preferences(language=language)

    @safe
    def choose_data(self):
        self._idle()
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True,
                 file_types=('EXAFS text (*.txt;*.dat;*.chi;*.csv;*.xmu)', 'All files (*.*)'))
        return self._load(paths) if paths else None

    @safe
    def load_demo(self):
        return self._load(make_demo(app_data() / 'demo'))

    @safe
    def remove_data(self, index):
        with self._lock:
            self._idle()
            self._tables.pop(int(index))
            self._results = []
            self._revision += 1
            self._state['export'] = None

    @safe
    def common_range(self, k_col):
        if not self._tables:
            raise DataError('no_data')
        col = int(k_col)
        if col < 0 or any(col >= t.values.shape[1] for t in self._tables):
            raise DataError('column_selection')
        values = [t.values[:, col] for t in self._tables]
        if not all(np.isfinite(k).all() for k in values):
            raise DataError('nonfinite')
        lower, upper = max(float(k.min()) for k in values), min(float(k.max()) for k in values)
        if lower >= upper:
            raise DataError('outside', 'No common measured interval / 样品无共同 k 区间')
        return {'kmin': lower, 'kmax': upper}

    @safe
    def install_hama(self):
        return self._job('installing', download_engine)

    @safe
    def choose_hama(self, folder=False):
        self._idle()
        paths = self._window.create_file_dialog(webview.FileDialog.FOLDER if folder else webview.FileDialog.OPEN,
                      file_types=('Hama (*.zip;*.exe)',))
        if paths:
            return self._job('installing', lambda: import_engine(paths[0]))

    @safe
    def choose_work_folder(self):
        self._idle()
        paths = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if paths:
            from engine_manager import short_path
            path = short_path(paths[0])
            if not path.isascii() or ' ' in path or len(path) > 130:
                raise DataError('work_path', path)
            import tempfile
            with tempfile.TemporaryFile(dir=path):
                pass
            with self._lock:
                save_preferences(work_root=path)
            return path

    @safe
    def environment(self):
        root = str(work_root())
        self._engine = engine_status()
        self._origin = origin_available()
        return {'work': root, 'engine': self._engine, 'origin': self._origin, 'cache': str(app_data())}

    @safe
    def open_link(self, kind):
        links = {'home': HOME, 'download': DOWNLOAD, 'webview': 'https://developer.microsoft.com/microsoft-edge/webview2/'}
        if kind in links:
            webbrowser.open(links[kind])

    @safe
    def analyze(self, values):
        self._idle()
        if not self._tables:
            raise DataError('no_data')
        exe = verified_engine()
        values = dict(values)
        for key in ('k_col', 'chi_col', 'input_weight', 'weight', 'cauchy_n'):
            try:
                number = float(values[key])
            except (TypeError, ValueError, KeyError) as e:
                raise DataError('wavelet_parameters' if key == 'cauchy_n' else 'column_selection', key) from e
            if not np.isfinite(number) or number != int(number):
                raise DataError('wavelet_parameters' if key == 'cauchy_n' else 'column_selection')
            values[key] = int(number)
        for key in ('kmin', 'kmax', 'rmin', 'rmax', 'kappa', 'sigma'):
            try:
                values[key] = float(values[key])
            except (TypeError, ValueError, KeyError) as e:
                raise DataError('range', key) from e
        settings = Settings(**values)
        tables = list(self._tables)
        # Validate every sample before discarding any previous successful run.
        for table in tables:
            try:
                prepare(table, settings)
            except DataError as e:
                error = DataError(e.key, table.path + '\n' + e.detail)
                error.where = table.path
                raise error from e
        def run():
            with self._lock:
                self._results = []
                self._revision += 1
                self._state['total'] = len(tables)
                self._state['export'] = None
            for i, table in enumerate(tables):
                with self._lock:
                    self._state.update(current=Path(table.path).name, done=i)
                try:
                    result = calculate(table, settings, self._cancel, exe=exe)
                except Exception as e:
                    with self._lock:
                        self._state['errors'].append(issue(e, table.path))
                    if self._cancel.is_set():
                        break
                else:
                    with self._lock:
                        self._results.append(result)
                        self._revision += 1
                with self._lock:
                    self._state['done'] = i + 1
        return self._job('calculating', run)

    @safe
    def cancel(self):
        if self._state['phase'] == 'calculating':
            self._cancel.set()

    @safe
    def get_preview(self, index=-1, cmap='viridis', normalized=False, signal=False):
        with self._lock:
            results = list(self._results)
        vmax = max((float(r.magnitude.max()) for r in results), default=None)
        if index >= 0:
            results = results[index:index + 1]
        return preview(results, cmap, normalized, signal, vmax)

    @safe
    def export(self, formats, cmap='viridis', normalized=False, dpi=300):
        self._idle()
        if not self._results:
            raise DataError('no_results')
        paths = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not paths:
            return None
        results = list(self._results)
        def progress(done, total, current):
            with self._lock:
                self._state.update(done=done, total=total, current=current.upper())
        def run():
            report = export_selected(results, paths[0], formats, cmap, normalized, int(dpi), progress)
            with self._lock:
                self._state['export'] = report
                self._state['errors'] = report['errors']
                self._state['done'] = self._state['total']
        return self._job('exporting', run)

    @safe
    def open_export(self):
        report = self._state.get('export')
        if report and Path(report['folder']).is_dir():
            os.startfile(report['folder'])

    @safe
    def copy_diagnostics(self, data):
        # Clipboard only: no network submission or automatic issue posting.
        import win32clipboard
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(json.dumps(data, ensure_ascii=False, indent=2))
        finally:
            win32clipboard.CloseClipboard()

    def _close(self):
        self._cancel.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=12)

    def _closing(self):
        if self._state['busy']:
            if self._state['phase'] == 'calculating':
                self._cancel.set()
            # Do not abandon a save or COM instance. The UI displays the task
            # status; close again when it has finished (or cancelled).
            return False


def main():
    api = DesktopApi()
    window = webview.create_window('EXAFS Wavelet Studio 2', str(resources() / 'frontend' / 'dist' / 'index.html'), js_api=api,
                                  width=1380, height=940, min_size=(980, 700), background_color='#f5f8fa')
    api._window = window
    window.events.closed += api._close
    window.events.closing += api._closing
    try:
        webview.start(gui='edgechromium', http_server=True, private_mode=True)
    except Exception as e:
        # This runs before a web UI exists, so use a minimal OS error dialog.
        import ctypes
        ctypes.windll.user32.MessageBoxW(None,
            '窗口启动失败 / Cannot open desktop window\n\n' + str(e) +
            '\n\n请安装 Microsoft Edge WebView2 Runtime 后重试。\nInstall Microsoft Edge WebView2 Runtime and retry.\nhttps://developer.microsoft.com/microsoft-edge/webview2/',
            'EXAFS Wavelet Studio', 16)


if __name__ == '__main__':
    main()
