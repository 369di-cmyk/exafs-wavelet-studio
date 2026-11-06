"""Independent coordinate checks against Origin, not just COM round-trips."""
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from core import Result
from exports import origin_available, origin_project, plot


@unittest.skipUnless(
    (os.environ.get('RUN_ORIGIN_TESTS') == '1' or os.environ.get('RUN_HAMA_TESTS') == '1')
    and origin_available(), 'Requires local Origin and RUN_ORIGIN_TESTS=1')
class OriginOrientationTests(unittest.TestCase):
    def test_asymmetric_peak_coordinates_after_reopen(self):
        import pythoncom
        import win32com.client
        # Non-square catches swapped dimensions; square catches silent transpose.
        for nr, nc in ((3, 5), (5, 5)):
            with self.subTest(shape=(nr, nc)), tempfile.TemporaryDirectory() as folder:
                k, r = np.linspace(2, 10, nc), np.linspace(0, 4, nr)
                z = np.arange(nr * nc, dtype=float).reshape(nr, nc)
                z[0, 3] = 1000  # Independent marker: k=8, R=0, never on diagonal.
                result = Result('Orientation test', 'synthetic', k, k * 0, k * 0,
                                k, r, z, np.empty((0, 3)),
                                {'settings': {'weight': 2}}, '', '')
                fig = plot([result])
                mesh = fig.axes[0].collections[0]
                self.assertEqual(np.unravel_index(np.argmax(mesh.get_array()), z.shape), (0, 3))
                fig.clear()
                path = Path(folder) / 'orientation.opju'
                origin_project([result], path)
                pythoncom.CoInitialize()
                origin = win32com.client.DispatchEx('Origin.Application')
                try:
                    self.assertTrue(origin.Load(str(path)))
                    origin.Execute('win -a WT1;')
                    self.assertEqual(origin.LTVar('wks.nrows'), nr)
                    self.assertEqual(origin.LTVar('wks.ncols'), nc)
                    np.testing.assert_allclose(
                        [origin.LTVar(f'wks.col1.{p}') for p in ('x1', 'x2', 'y1', 'y2')],
                        [2, 10, 0, 4])
                    # Query actual matrix cell by LabTalk row/column, independently
                    # of the Python GetMatrix/PutMatrix array convention.
                    origin.Execute('range marker=[WT1]1!1; double peakvalue=marker[1,4]; double corner=marker[3,1];')
                    self.assertEqual(origin.LTVar('peakvalue'), 1000)
                    self.assertEqual(origin.LTVar('corner'), z[2, 0])
                    actual = np.asarray(origin.GetMatrix('WT1'))
                    peak_row, peak_col = np.unravel_index(actual.argmax(), actual.shape)
                    self.assertEqual((k[peak_col], r[peak_row]), (8, 0))
                    graph = origin.GraphPages(0).Name
                    origin.Execute(f'win -a {graph};')
                    np.testing.assert_allclose(
                        [origin.LTVar(f'layer.{p}') for p in ('x.from', 'x.to', 'y.from', 'y.to')],
                        [2, 10, 0, 4])
                    self.assertEqual(origin.LTVar('layer.x.reverse'), 0)
                    self.assertEqual(origin.LTVar('layer.y.reverse'), 0)
                finally:
                    origin.NewProject()  # Release Origin 2021's saved-file lock.
                    origin.Exit()
                    pythoncom.CoUninitialize()


if __name__ == '__main__':
    unittest.main()
