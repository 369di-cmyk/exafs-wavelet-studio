import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile
import numpy as np
from openpyxl import load_workbook
from core import DataError, Table, Settings, Result, prepare, read_table, calculate, make_demo
import engine_manager as engines
from exports import export_selected, excel, plot, origin_project, origin_available, FORMATS
from issues import issue

ROOT = Path(__file__).resolve().parents[1]


def synthetic_result(name='Synthetic'):
    k = np.linspace(2, 8, 31)
    r = np.linspace(0, 5, 21)
    z = np.outer(1 + r, 2 + np.sin(k))
    kk, rr = np.meshgrid(k, r)
    return Result(name, name + '.txt', k, np.sin(k), k*k*np.sin(k), k, r, z,
                  np.column_stack((kk.ravel(), rr.ravel(), z.ravel())),
                  {'settings': {'weight': 2, 'wavelet': 'Morlet', 'kappa': 15, 'sigma': 1, 'cauchy_n': 50, 'rmin': 0, 'rmax': 5},
                   'linear_resampling_applied': False}, 'Synthetic test log', 'Synthetic parameters')


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.k = np.linspace(2, 12, 101)
        self.table = Table('sample.txt', np.column_stack((self.k, np.sin(self.k))))

    def tearDown(self):
        self.tmp.cleanup()

    def assertCode(self, code, function, *args):
        with self.assertRaises(DataError) as cm:
            function(*args)
        self.assertEqual(code, cm.exception.key)
        return cm.exception

    def test_unicode_path_and_header(self):
        path = self.folder / '中文 样品.csv'
        np.savetxt(path, self.table.values, delimiter=',', header='k,chi', comments='')
        actual = read_table(path)
        np.testing.assert_allclose(actual.values, self.table.values)
        self.assertEqual(actual.skipped_headers, 1)
        self.assertEqual(actual.source_sha256, hashlib.sha256(path.read_bytes()).hexdigest())

    def test_native_data_picker_filter_accepts_athena_chik(self):
        from app import DesktopApi
        from webview.util import parse_file_type
        api = DesktopApi()
        seen = []
        class Window:
            def create_file_dialog(self, *args, **kwargs):
                for file_type in kwargs['file_types']:
                    seen.append(parse_file_type(file_type)[1])
                return None
        api._window = Window()
        response = api.choose_data()
        self.assertTrue(response['ok'], response)
        self.assertIn('*.chik', seen[0].split(';'))

    def test_missing_cell_reports_physical_line(self):
        path = self.folder / 'bad.csv'
        path.write_text('k,chi\n2,0.1\n2.1,\n', encoding='utf-8')
        e = self.assertCode('bad_row', read_table, path)
        self.assertIn('3', e.detail)
        self.assertIn('2.1', e.detail)

    def test_unequal_columns_report_expected_count(self):
        path = self.folder / 'bad.txt'
        path.write_text('2 1\n2.1 1 4', encoding='utf-8')
        self.assertIn('expected 2', self.assertCode('columns', read_table, path).detail)

    def test_weight_is_removed_exactly_once(self):
        weighted = Table('weighted', np.column_stack((self.k, np.sin(self.k)*self.k**2)))
        k, chi, resampled = prepare(weighted, Settings(input_weight=2))
        np.testing.assert_allclose(chi, np.sin(k))
        self.assertFalse(resampled)

    def test_athena_chik_seven_columns_ignore_plot_weight_header(self):
        # Athena 0.9.26 GUI export layout; synthetic signal, no experimental data.
        k = np.arange(0, 12.001, .05)
        chi = np.sin(k)
        values = np.column_stack((k, chi, k*chi, k*k*chi, k**3*chi,
                                  np.ones_like(k), 7112 + 3.81*k*k))
        path = self.folder / '标准样品.chik'
        np.savetxt(path, values, header='XDI/1.0 Athena/0.9.26\nColumn.1: k inverse Angstrom\nColumn.2: chi\nAthena.kweight: 2\nk chi chik chik2 chik3 win energy')
        original = path.read_bytes()
        table = read_table(path)
        self.assertEqual(table.values.shape, (241, 7))
        for power in range(4):
            selected_k, selected_chi, changed = prepare(table, Settings(chi_col=power+1, input_weight=power))
            np.testing.assert_allclose(selected_chi, np.sin(selected_k), atol=1e-14)
            self.assertFalse(changed)
        self.assertEqual(path.read_bytes(), original)

    def test_no_extrapolation(self):
        self.assertCode('outside', prepare, self.table, Settings(kmin=1))

    def test_duplicate_k_reports_data_row(self):
        self.table.values[4, 0] = self.table.values[3, 0]
        self.assertIn('5', self.assertCode('increasing', prepare, self.table, Settings()).detail)

    def test_nonfinite_reports_data_row(self):
        self.table.values[8, 1] = np.nan
        self.assertIn('9', self.assertCode('nonfinite', prepare, self.table, Settings()).detail)

    def test_energy_is_rejected(self):
        self.table.values[:, 0] += 8000
        self.assertCode('not_k', prepare, self.table, Settings())

    def test_irregular_requires_opt_in_and_records_resampling(self):
        self.table.values[10, 0] += .02
        self.assertCode('irregular', prepare, self.table, Settings())
        k, chi, applied = prepare(self.table, Settings(resample=True))
        self.assertTrue(applied)
        np.testing.assert_allclose(np.diff(k), .1)
        self.assertEqual(k[0], 2)
        self.assertEqual(k[-1], 12)
        np.testing.assert_allclose(chi, np.interp(k, self.table.values[:, 0], self.table.values[:, 1]))

    def test_point_limits(self):
        self.assertCode('few_points', prepare, self.table, Settings(kmax=3))
        k = np.linspace(2, 12, 802)
        self.assertCode('many_points', prepare, Table('large', np.column_stack((k, np.sin(k)))), Settings())

    def test_zero_and_invalid_parameters(self):
        for key, value, code in [('kmax', 1, 'range'), ('weight', 4, 'weight'), ('sigma', 0, 'wavelet_parameters'), ('chi_col', 0, 'column_selection')]:
            with self.subTest(key=key):
                self.assertCode(code, prepare, self.table, Settings(**{key: value}))
        self.table.values[:, 1] = 0
        self.assertCode('zero_signal', prepare, self.table, Settings())

    def test_diagnostics_are_actionable_in_both_languages(self):
        from issues import MESSAGES
        for key in MESSAGES:
            data = issue(DataError(key, 'specific detail'), 'sample.txt')
            for language in ('zh', 'en'):
                for part in ('title', 'why', 'fix'):
                    self.assertTrue(data[language][part])
            self.assertEqual('sample.txt', data['where'])


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'EXAFS_STUDIO_HOME': self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_missing_engine_has_explicit_status(self):
        self.assertFalse(engines.engine_status()['ready'])

    def test_corrupt_binary_never_installed(self):
        with self.assertRaises(DataError) as cm:
            engines.install_bytes(b'MZnot-hama')
        self.assertEqual(cm.exception.key, 'engine_hash')
        self.assertFalse(engines.engine_status()['ready'])

    def test_zip_traversal_cannot_extract_files(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            z.writestr('../../escape.txt', 'bad')
            z.writestr('hama_fortran.exe', b'MZbad')
        with self.assertRaises(DataError):
            engines.install_bytes(stream.getvalue(), zipped=True)
        self.assertFalse((Path(self.tmp.name).parent / 'escape.txt').exists())
        self.assertEqual(list(Path(self.tmp.name).iterdir()), [])

    def test_duplicate_engine_members_rejected(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            z.writestr('a/hama_fortran.exe', b'bad')
            z.writestr('b/hama_fortran.exe', b'bad')
        with self.assertRaises(DataError) as cm:
            engines.install_bytes(stream.getvalue(), zipped=True)
        self.assertEqual(cm.exception.key, 'engine_archive')

    def test_network_error_is_actionable(self):
        with patch('engine_manager.download_candidates', return_value=[]), patch('urllib.request.OpenerDirector.open', side_effect=OSError('network disconnected')), patch('engine_manager.time.sleep'):
            with self.assertRaises(DataError) as cm:
                engines.download_engine()
        self.assertEqual(cm.exception.key, 'download')
        self.assertIn('network disconnected', cm.exception.detail)

    def test_ascii_workspace_is_removed(self):
        with engines.work_directory() as p:
            self.assertTrue(str(p).isascii())
            self.assertNotIn(' ', str(p))
            self.assertTrue(p.is_dir())
            (p / 'input.dat').write_text('sample')
        self.assertFalse(p.exists())


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / '中文 结果'
        self.result = synthetic_result('中文_合成样品')

    def tearDown(self):
        self.tmp.cleanup()

    def test_selected_exports_roundtrip(self):
        report = export_selected([self.result], self.folder, ['txt', 'csv', 'xlsx', 'npz', 'origin_xyz'])
        self.assertFalse(report['errors'])
        output = Path(report['folder'])
        sample = next(p for p in output.iterdir() if p.is_dir())
        data = np.loadtxt(sample / 'wt_xyz.txt', skiprows=1)
        np.testing.assert_allclose(data[:, 2].reshape(self.result.magnitude.shape), self.result.magnitude, rtol=1e-11)
        arrays = np.load(sample / 'wavelet.npz')
        np.testing.assert_array_equal(arrays['wt'], self.result.magnitude)
        workbook = load_workbook(output / 'Wavelet_data.xlsx', read_only=True, data_only=True)
        sheet = workbook['S01_WT']
        np.testing.assert_allclose([row[1:] for row in list(sheet.values)[1:]], self.result.magnitude)
        np.testing.assert_allclose(list(sheet.values)[0][1:], self.result.grid_k)
        np.testing.assert_allclose([row[0] for row in list(sheet.values)[1:]], self.result.grid_r)
        workbook.close()
        self.assertFalse(list(output.rglob('*.pdf')))
        manifest = json.loads((output / 'export_manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['completed'], report['completed'])

    def test_excel_labels_are_never_formulas(self):
        self.folder.mkdir(parents=True)
        self.result.name = '=HYPERLINK("https://example.com")'
        excel([self.result], self.folder / 'test.xlsx')
        workbook = load_workbook(self.folder / 'test.xlsx')
        self.assertEqual(workbook['Overview']['A5'].data_type, 's')
        workbook.close()

    def test_format_failure_is_partial_not_success(self):
        with patch('exports.origin_project', side_effect=DataError('origin_missing')):
            report = export_selected([self.result], self.folder, ['txt', 'opju', 'npz'])
        self.assertEqual(report['completed'], ['txt', 'npz'])
        self.assertEqual(report['errors'][0]['code'], 'origin_missing')
        self.assertFalse((Path(report['folder']) / 'Wavelet.opju').exists())

    def test_no_overwrite_and_no_unselected_files(self):
        a = export_selected([self.result], self.folder, ['npz'])
        b = export_selected([self.result], self.folder, ['npz'])
        self.assertNotEqual(a['folder'], b['folder'])
        self.assertFalse(list(Path(a['folder']).rglob('*.xlsx')))

    def test_common_scale_does_not_change_data(self):
        a, b = synthetic_result(), synthetic_result()
        b.magnitude = b.magnitude * 10
        original = a.magnitude.copy()
        figure = plot([a, b])
        main_axes = [ax for ax in figure.axes if ax.collections and ax.get_xlabel()]
        self.assertEqual(main_axes[0].collections[0].get_clim(), main_axes[1].collections[0].get_clim())
        figure.clear()
        figure = plot([a], normalized=True)
        np.testing.assert_array_equal(original, a.magnitude)
        figure.clear()


@unittest.skipUnless(os.environ.get('RUN_HAMA_TESTS') == '1', 'Set RUN_HAMA_TESTS=1 after configuring Hama')
class HamaIntegrationTests(unittest.TestCase):
    def test_original_interactive_reference_matches(self):
        reference = np.load(ROOT / 'fixtures' / 'manual_hama_reference.npz')['xyz']
        result = calculate(read_table(ROOT / 'fixtures' / 'manual_input.txt'), Settings(kmin=0, kmax=15))
        np.testing.assert_array_equal(result.raw_xyz, reference)

    def test_unicode_separate_folders_and_cauchy(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / '中文 测试' / ('Long sample path ' * 6).strip()
            paths = make_demo(folder)
            before = paths[0].read_bytes()
            a = calculate(read_table(paths[0]), Settings(kmax=8))
            b = calculate(read_table(paths[0]), Settings(kmax=8, wavelet='Cauchy', cauchy_n=30))
            self.assertTrue(np.isfinite(b.magnitude).all())
            self.assertGreater(float(b.magnitude.max()), 0)
            self.assertFalse(np.allclose(a.magnitude, b.magnitude))
            self.assertEqual(before, paths[0].read_bytes())

    def test_cancel_and_timeout_clean_owned_job(self):
        with tempfile.TemporaryDirectory() as temporary:
            table = read_table(make_demo(temporary)[0])
            cancel = threading.Event()
            timer = threading.Timer(.1, cancel.set)
            timer.start()
            try:
                with self.assertRaises(DataError) as cm:
                    calculate(table, Settings(), cancel)
                self.assertEqual(cm.exception.key, 'cancelled')
            finally:
                timer.cancel()
            with self.assertRaises(DataError) as cm:
                calculate(table, Settings(), timeout=.01)
            self.assertEqual(cm.exception.key, 'timeout')

    def test_all_exports_and_native_origin_reopen(self):
        output = ROOT / 'test_artifacts' / '验证导出 中文'
        a, b = [calculate(read_table(p), Settings(kmax=8)) for p in make_demo(output / '输入 样品')]
        report = export_selected([a, b], output, FORMATS if origin_available() else [f for f in FORMATS if f != 'opju'], dpi=150)
        self.assertFalse(report['errors'], report['errors'])
        folder = Path(report['folder'])
        from PIL import Image
        with Image.open(folder / 'comparison.png') as image:
            self.assertGreater(image.width, 1500)
        from pypdf import PdfReader
        self.assertEqual(len(PdfReader(folder / 'Wavelet_report.pdf').pages), 3)
        if origin_available():
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            origin = win32com.client.DispatchEx('Origin.Application')
            try:
                self.assertTrue(origin.Load(str(folder / 'Wavelet.opju')))
                np.testing.assert_allclose(np.asarray(origin.GetMatrix('WT1')), a.magnitude, rtol=1e-12)
                np.testing.assert_allclose(np.asarray(origin.GetMatrix('WT2')), b.magnitude, rtol=1e-12)
                self.assertGreaterEqual(origin.GraphPages.Count, 2)
            finally:
                origin.Exit()
                pythoncom.CoUninitialize()
        print('Verified export folder:', folder)


if __name__ == '__main__':
    unittest.main()
