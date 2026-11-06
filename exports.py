"""Scientific figures and selected data formats; no implicit Origin dependency."""
from __future__ import annotations
import base64
import io
import json
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from core import DataError, VERSION
from engine_manager import work_directory
from issues import issue

FORMATS = ('png', 'tiff', 'svg', 'pdf', 'txt', 'csv', 'xlsx', 'origin_xyz', 'opju', 'npz', 'raw')
PLOT_LOCK = threading.RLock()
matplotlib.rcParams.update({'font.family': ['DejaVu Sans', 'Microsoft YaHei', 'SimHei'], 'pdf.fonttype': 42, 'svg.fonttype': 'none'})


def plot(results, cmap='viridis', normalized=False, signal=False, vmax_override=None):
    if cmap not in ('viridis', 'turbo', 'magma', 'cividis'):
        cmap = 'viridis'
    count = len(results)
    columns = min(count, 2)
    rows = (count + columns - 1) // columns
    fig = Figure(figsize=(7.2 * columns, 4.6 * rows), layout='constrained', facecolor='white')
    axes = fig.subplots(rows, columns, squeeze=False)
    vmax = vmax_override or max(float(r.magnitude.max()) for r in results)
    for index, ax in enumerate(axes.flat):
        if index >= count:
            ax.set_visible(False)
            continue
        r = results[index]
        ax.set_title(r.name, fontsize=11, pad=12)
        ax.set_xlabel(r'$k$ ($\mathrm{\AA}^{-1}$)')
        if signal:
            ax.plot(r.k, r.weighted, color='#087f8c', linewidth=1.4)
            ax.set_ylabel(f"k^{r.metadata['settings']['weight']} χ(k)")
            ax.axhline(0, color='#94a3b8', linewidth=.6)
            ax.grid(alpha=.18)
        else:
            z = r.magnitude / r.magnitude.max() if normalized else r.magnitude
            mesh = ax.pcolormesh(r.grid_k, r.grid_r, z, cmap=cmap, vmin=0, vmax=1 if normalized else vmax, shading='auto', rasterized=True)
            ax.set_ylabel(r'$R$ ($\mathrm{\AA}$), uncorrected')
            fig.colorbar(mesh, ax=ax, label='WT / sample maximum' if normalized else 'WT magnitude (raw)')
        ax.set_xlim(r.k[0], r.k[-1])
    fig.suptitle('EXAFS Wavelet Studio · ' + ('weighted signals' if signal else 'per-sample normalization' if normalized else 'shared color scale'), fontsize=12)
    return fig


def preview(results, cmap='viridis', normalized=False, signal=False, vmax_override=None):
    if not results:
        return ''
    with PLOT_LOCK:
        fig = plot(results, cmap, normalized, signal, vmax_override)
        stream = io.BytesIO()
        fig.savefig(stream, format='png', dpi=115)
        fig.clear()
    return 'data:image/png;base64,' + base64.b64encode(stream.getvalue()).decode('ascii')


def xyz(r):
    kk, rr = np.meshgrid(r.grid_k, r.grid_r)
    return np.column_stack((kk.ravel(), rr.ravel(), r.magnitude.ravel()))


def origin_available():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'Origin.Application\CLSID'):
            return True
    except (OSError, ImportError):
        return False


def origin_project(results, target):
    if not origin_available():
        raise DataError('origin_missing')
    import pythoncom
    import win32com.client
    pythoncom.CoInitialize()
    origin = None
    try:
        # Application (not ApplicationSI): a dedicated instance, never the user's
        # currently open project. No GetActiveObject or attachment is allowed.
        origin = win32com.client.DispatchEx('Origin.Application')
        origin.Visible = 0
        origin.NewProject()
        with work_directory() as job:
            for i, r in enumerate(results, 1):
                book = origin.CreatePage(2, f'Signal{i}', 'Origin')
                for c, data in enumerate((r.k, r.chi, r.weighted)):
                    if not origin.PutWorksheet(book, data.tolist(), 0, c):
                        raise RuntimeError('PutWorksheet failed')
                origin.Execute(f'win -a {book}; wks.col1.lname$="k"; wks.col1.unit$="1/Angstrom"; wks.col2.lname$="chi"; wks.col3.lname$="Weighted chi";')
                matrix = origin.CreatePage(1, f'WT{i}', 'Origin')
                nr, nc = r.magnitude.shape
                if not origin.Execute(f'win -a {matrix}; mdim cols:={nc} rows:={nr} x1:={r.grid_k[0]:.12g} x2:={r.grid_k[-1]:.12g} y1:={r.grid_r[0]:.12g} y2:={r.grid_r[-1]:.12g};'):
                    raise RuntimeError('Matrix coordinate mapping failed')
                # pywin32 nested lists are rows, unlike the OriginExt example.
                # Keep rows=R and columns=k, exactly as in the preview/Excel.
                if not origin.PutMatrix(matrix, r.magnitude.tolist()):
                    raise RuntimeError('PutMatrix failed')
                actual = np.asarray(origin.GetMatrix(matrix), dtype=float)
                if actual.shape != r.magnitude.shape or not np.allclose(actual, r.magnitude, rtol=1e-12, atol=1e-12):
                    raise RuntimeError('Origin matrix round-trip differs from calculated values')
                # Independently inspect Origin's dimensions, coordinate mapping
                # and off-diagonal cells: Get/Put round-trip alone misses transpose bugs.
                expected = (nr, nc, r.grid_k[0], r.grid_k[-1], r.grid_r[0], r.grid_r[-1])
                properties = ('wks.nrows', 'wks.ncols', 'wks.col1.x1', 'wks.col1.x2', 'wks.col1.y1', 'wks.col1.y2')
                if not np.allclose([origin.LTVar(p) for p in properties], expected, rtol=1e-10, atol=1e-10):
                    raise RuntimeError('Origin matrix dimensions or k/R coordinates differ from preview')
                peak = np.unravel_index(np.argmax(r.magnitude), r.magnitude.shape)
                for row, col in {(0, nc - 1), (nr - 1, 0), peak}:
                    origin.Execute(f'range wtcheck=[{matrix}]1!1; double wtcell=wtcheck[{row + 1},{col + 1}];')
                    if not np.isclose(origin.LTVar('wtcell'), r.magnitude[row, col], rtol=1e-12, atol=1e-12):
                        raise RuntimeError('Origin matrix cell orientation differs from preview')
                if not origin.Execute(f'win -a {matrix}; plotm im:=[{matrix}]1!1 plot:=105 ogl:=<new template:=heatmap>; label -xb "k (1/Angstrom)"; label -yl "R (Angstrom), uncorrected";'):
                    raise RuntimeError('Origin heatmap creation failed')
                # Match preview limits instead of the template's half-cell padding.
                origin.Execute(f'layer.x.from={r.grid_k[0]:.12g}; layer.x.to={r.grid_k[-1]:.12g}; layer.y.from={r.grid_r[0]:.12g}; layer.y.to={r.grid_r[-1]:.12g};')
            output = job / 'Wavelet.opju'
            if not origin.Save(str(output)) or not output.is_file() or output.stat().st_size < 100:
                raise RuntimeError('Origin did not save an OPJU project')
            # Release Origin's project-file lock before copying and deleting
            # the isolated work folder (Origin 2021 keeps a saved OPJU open).
            origin.NewProject()
            shutil.copy2(output, target)
    except DataError:
        raise
    except Exception as e:
        raise DataError('origin_failed', str(e)) from e
    finally:
        if origin is not None:
            try:
                origin.Exit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def excel(results, path):
    workbook = Workbook()
    overview = workbook.active
    overview.title = 'Overview'
    overview.append(['EXAFS Wavelet Studio', VERSION])
    overview.append(['Values', 'Raw Hama WT; no phase correction; measured k domain only'])
    overview.append(['Matrix orientation', 'Rows = R (Angstrom); columns = k (1/Angstrom)'])
    overview.append(['Sample', 'Signal sheet', 'WT sheet', 'Source'])
    for i, r in enumerate(results, 1):
        # Use explicit strings for labels to prevent Excel formula injection
        # through user-controlled sample names or paths.
        row = [r.name, f'S{i:02d}_signal', f'S{i:02d}_WT', r.source]
        overview.append(row)
        for cell in overview[overview.max_row]:
            cell.data_type = 's'
        ws = workbook.create_sheet(row[1])
        ws.append(['k (1/Angstrom)', 'chi(k)', f"k^{r.metadata['settings']['weight']} chi(k)"])
        for values in zip(r.k.tolist(), r.chi.tolist(), r.weighted.tolist()):
            ws.append(values)
        wt = workbook.create_sheet(row[2])
        wt.append(['R \\ k'] + r.grid_k.tolist())
        for radius, values in zip(r.grid_r.tolist(), r.magnitude.tolist()):
            wt.append([radius] + values)
        info = workbook.create_sheet(f'S{i:02d}_parameters')
        info.append(['Parameter', 'Value'])
        for key, value in r.metadata.items():
            info.append([key, json.dumps(value, ensure_ascii=False)])
    for sheet in workbook:
        sheet.freeze_panes = 'B2' if sheet.title.endswith('_WT') else 'A2'
        sheet.column_dimensions['A'].width = 27
        sheet.column_dimensions['B'].width = 24
        for cell in sheet[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='087F8C')
    workbook.save(path)


def export_selected(results, parent, formats, cmap='viridis', normalized=False, dpi=300, progress=None):
    if not results:
        raise DataError('no_results')
    formats = list(dict.fromkeys(formats))
    if not formats or any(f not in FORMATS for f in formats) or dpi not in (150, 300, 600):
        raise DataError('formats')
    folder = Path(parent) / ('WT_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir(parents=True, exist_ok=False)
    folders = []
    for index, r in enumerate(results, 1):
        safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', r.name).strip('. ')[:70] or 'Sample'
        p = folder / f'{index:02d}_{safe}'
        p.mkdir()
        folders.append(p)
        (p / 'parameters.json').write_text(json.dumps(r.metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        (p / 'hama_run.log').write_text(r.log, encoding='utf-8')
        (p / 'hama_parameters.txt').write_text(r.parameters, encoding='utf-8')
    report = {'app_version': VERSION, 'folder': str(folder), 'requested': formats, 'completed': [], 'errors': [],
              'display': {'cmap': cmap, 'per_sample_normalization': normalized, 'dpi': dpi},
              'data_note': 'Numeric exports always contain raw, unnormalized Hama WT. Origin uses native graph styling; adjust native graph color scales for comparisons.',
              'samples': [{'index': i + 1, 'name': r.name, 'source': r.source} for i, r in enumerate(results)]}
    for index, fmt in enumerate(formats):
        if progress:
            progress(index, len(formats), fmt)
        try:
            if fmt in ('png', 'tiff', 'svg'):
                with PLOT_LOCK:
                    for r, p in zip(results, folders):
                        fig = plot([r], cmap, normalized, vmax_override=max(float(x.magnitude.max()) for x in results))
                        fig.savefig(p / f'wavelet.{fmt}', dpi=dpi)
                        fig.clear()
                    fig = plot(results, cmap, normalized)
                    fig.savefig(folder / f'comparison.{fmt}', dpi=dpi)
                    fig.clear()
            elif fmt == 'pdf':
                with PLOT_LOCK, PdfPages(folder / 'Wavelet_report.pdf') as pdf:
                    for batch in [results[n:n + 4] for n in range(0, len(results), 4)]:
                        for signals in (False, True):
                            fig = plot(batch, cmap, normalized, signals, max(float(x.magnitude.max()) for x in results))
                            pdf.savefig(fig, dpi=dpi)
                            fig.clear()
                    fig = Figure(figsize=(8.3, 11.7))
                    details = ['EXAFS Wavelet Studio ' + VERSION, '', 'Reproducibility / interpretation notes',
                               'Raw WT values; R is not phase corrected.', 'No extrapolation beyond measured k in displayed grids.',
                               'Boundary features may reflect finite-range artifacts.', 'Similar features alone do not identify a unique scattering path.',
                               'Compare using identical preparation, parameters and a common color scale.',
                               'Per-sample display normalization: ' + str(normalized), '', 'Sample parameters:']
                    for r in results:
                        s = r.metadata['settings']
                        details += [r.name[:65], f"  {s['wavelet']}, k={r.k[0]:g}..{r.k[-1]:g}, R={s['rmin']:g}..{s['rmax']:g}, weight={s['weight']}",
                                    f"  kappa={s['kappa']:g}, sigma={s['sigma']:g}, Cauchy n={s['cauchy_n']}; resampled={r.metadata.get('linear_resampling_applied', False)}"]
                    # Paginate notes instead of letting a long batch overflow.
                    for n in range(0, len(details), 45):
                        fig.text(.08, .94, '\n'.join(details[n:n + 45]), va='top', fontsize=10, linespacing=1.6)
                        pdf.savefig(fig)
                        fig.clear()
            elif fmt == 'xlsx':
                excel(results, folder / 'Wavelet_data.xlsx')
            elif fmt == 'opju':
                origin_project(results, folder / 'Wavelet.opju')
            else:
                for r, p in zip(results, folders):
                    if fmt in ('txt', 'csv'):
                        sep = ',' if fmt == 'csv' else '\t'
                        np.savetxt(p / f'signal.{fmt}', np.column_stack((r.k, r.chi, r.weighted)), delimiter=sep, fmt='%.12e', header=sep.join(['k_A^-1', 'chi', 'weighted_chi']), comments='')
                        np.savetxt(p / f'wt_xyz.{fmt}', xyz(r), delimiter=sep, fmt='%.12e', header=sep.join(['k_A^-1', 'R_A', 'WT_raw']), comments='')
                    elif fmt == 'origin_xyz':
                        np.savetxt(p / 'Origin_XYZ.txt', xyz(r), delimiter='\t', fmt='%.12e', header='k_A^-1\tR_A\tWT_raw', comments='')
                    elif fmt == 'npz':
                        np.savez_compressed(p / 'wavelet.npz', k=r.grid_k, r=r.grid_r, wt=r.magnitude, signal_k=r.k, chi=r.chi)
                    elif fmt == 'raw':
                        np.savetxt(p / 'Hama_full_grid.txt', r.raw_xyz, fmt='%.12e', header='k_A^-1 R_A WT_raw; extended grid is NOT additional measured data')
            report['completed'].append(fmt)
        except Exception as e:
            report['errors'].append(issue(e, fmt.upper()))
    (folder / 'export_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report
