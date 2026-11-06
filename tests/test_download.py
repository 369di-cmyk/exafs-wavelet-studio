import hashlib
import io
import json
import os
from pathlib import Path
import socket
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import zipfile

import engine_manager as em
from core import DataError


class Response(io.BytesIO):
    def __init__(self, body, **headers):
        super().__init__(body)
        self.url = em.DOWNLOAD
        self.headers = {'Content-Length': str(len(body)), 'Content-Type': 'application/zip', **headers}


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.binary = b'MZtest-engine-never-executed'
        self.hash = hashlib.sha256(self.binary).hexdigest()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            z.writestr('hama_fortran.exe', self.binary)
        self.archive = stream.getvalue()
        for p in (patch.dict(os.environ, EXAFS_STUDIO_HOME=self.tmp.name),
                  patch.object(em, 'KNOWN_HASH', self.hash),
                  patch.object(em, 'download_candidates', return_value=[]),
                  patch.object(em.time, 'sleep')):
            p.start()
            self.addCleanup(p.stop)

    def test_valid_cache_works_offline_without_network(self):
        em.install_bytes(self.binary)
        with patch('urllib.request.OpenerDirector.open') as network:
            events = []
            self.assertTrue(em.download_engine(events.append)['ready'])
            network.assert_not_called()
            self.assertEqual(events[-1]['stage'], 'cached')

    def test_timeout_retries_then_verifies(self):
        events = []
        with patch('urllib.request.OpenerDirector.open', side_effect=[TimeoutError('slow'), Response(self.archive)]) as network:
            self.assertTrue(em.download_engine(events.append)['ready'])
            self.assertEqual(network.call_count, 2)
            self.assertTrue(all(call.kwargs['timeout'] == 8 for call in network.call_args_list))
        self.assertIn('retry', [e['stage'] for e in events])
        self.assertIn('receiving', [e['stage'] for e in events])
        self.assertEqual(events[-1]['stage'], 'complete')
        log = json.loads((Path(self.tmp.name) / 'last_download.json').read_text())
        self.assertTrue(any(e.get('code') == 'download_timeout' for e in log))

    def test_downloads_file_is_imported_without_network(self):
        path = Path(self.tmp.name) / 'hama_1 (2).zip'
        path.write_bytes(self.archive)
        with patch.object(em, 'download_candidates', return_value=[path]), patch('urllib.request.OpenerDirector.open') as network:
            self.assertTrue(em.download_engine(local_only=True)['ready'])
            network.assert_not_called()

    def test_bad_local_file_does_not_prevent_official_download(self):
        path = Path(self.tmp.name) / 'hama_1.zip'
        path.write_text('<html>blocked</html>')
        with patch.object(em, 'download_candidates', return_value=[path]), patch('urllib.request.OpenerDirector.open', return_value=Response(self.archive)):
            self.assertTrue(em.download_engine()['ready'])

    def test_detect_only_does_not_silently_download(self):
        with patch('urllib.request.OpenerDirector.open') as network:
            with self.assertRaises(DataError) as cm:
                em.download_engine(local_only=True)
            self.assertEqual(cm.exception.key, 'download_local_missing')
            network.assert_not_called()

    def test_blocked_after_three_attempts_is_specific(self):
        error = urllib.error.HTTPError(em.DOWNLOAD, 403, 'Forbidden', {}, None)
        with patch('urllib.request.OpenerDirector.open', side_effect=error) as network:
            with self.assertRaises(DataError) as cm:
                em.download_engine()
            self.assertEqual(cm.exception.key, 'download_blocked')
            self.assertEqual(network.call_count, 3)
            self.assertIn('Attempt 3', cm.exception.detail)

    def test_html_and_truncated_responses_are_not_installed(self):
        for key, factory in (
            ('download_html', lambda: Response(b'<html>blocked</html>', **{'Content-Type': 'text/html'})),
            ('download_html', lambda: Response(b' <html>blocked</html>')),
            ('download_incomplete', lambda: Response(self.archive, **{'Content-Length': str(len(self.archive) + 10)})),
            ('download_limit', lambda: Response(b'', **{'Content-Length': str(em.LIMIT + 1)})),
        ):
            with self.subTest(key=key), patch('urllib.request.OpenerDirector.open', side_effect=lambda *a, **k: factory()):
                with self.assertRaises(DataError) as cm:
                    em.download_engine()
                self.assertEqual(cm.exception.key, key)
                self.assertFalse(em.engine_status()['ready'])

    def test_certificate_failure_is_not_bypassed_or_retried(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=urllib.error.URLError(ssl.SSLCertVerificationError('untrusted'))) as network:
            with self.assertRaises(DataError) as cm:
                em.download_engine()
            self.assertEqual(cm.exception.key, 'download_tls')
            self.assertEqual(network.call_count, 1)

    def test_wrong_binary_is_never_installed(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            z.writestr('hama_fortran.exe', b'MZwrong')
        with patch('urllib.request.OpenerDirector.open', return_value=Response(stream.getvalue())) as network:
            with self.assertRaises(DataError) as cm:
                em.download_engine()
            self.assertEqual(cm.exception.key, 'engine_hash')
            self.assertEqual(network.call_count, 1)
            self.assertFalse(em.engine_status()['ready'])

    def test_cancel_before_and_during_download(self):
        cancel = threading.Event()
        cancel.set()
        with patch('urllib.request.OpenerDirector.open') as network:
            with self.assertRaises(DataError) as cm:
                em.download_engine(cancel=cancel)
            self.assertEqual(cm.exception.key, 'download_cancelled')
            network.assert_not_called()
        cancel.clear()
        def progress(event):
            if event['stage'] == 'receiving':
                cancel.set()
        with patch('urllib.request.OpenerDirector.open', return_value=Response(self.archive)):
            with self.assertRaises(DataError) as cm:
                em.download_engine(progress, cancel)
            self.assertEqual(cm.exception.key, 'download_cancelled')
            self.assertFalse(em.engine_status()['ready'])

    def test_redirect_cannot_leave_https_official_domain(self):
        handler = em.OfficialRedirect()
        for url in ('http://www.esrf.fr/test', 'https://www.esrf.fr.evil.test/file', 'https://example.com/file'):
            with self.subTest(url=url), self.assertRaises(DataError):
                handler.redirect_request(urllib.request.Request(em.DOWNLOAD), None, 302, '', {}, url)

    def test_dns_and_proxy_classification(self):
        self.assertEqual(em._download_error(urllib.error.URLError(socket.gaierror('dns'))).key, 'download_dns')
        self.assertEqual(em._download_error(urllib.error.HTTPError(em.DOWNLOAD, 407, 'Proxy', {}, None)).key, 'download_proxy')


if __name__ == '__main__':
    unittest.main()
