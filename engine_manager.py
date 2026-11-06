"""Acquire Hama from the user/ESRF, never from this application's release."""
from __future__ import annotations
import contextlib
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import time
import socket
import ssl
import http.client
import urllib.error
import urllib.parse
import urllib.request
import zipfile

from core import DataError

HOME = 'https://www.esrf.fr/UsersAndScience/Experiments/CRG/BM20/Software/Wavelets/HAMA'
DOWNLOAD = 'https://www.esrf.fr/files/live/sites/www/files/UsersAndScience/Experiments/CRG/BM20/Software/Wavelets/HAMA/hama_1.zip?download=1'
KNOWN_HASH = 'f8fa901ca98bee23113d88e9864ed64ece6aa0c9982d1d6a9a4d360e07f8b054'
LIMIT = 20_000_000


def app_data():
    p = Path(os.environ.get('EXAFS_STUDIO_HOME') or Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'EXAFSWaveletStudio')
    p.mkdir(parents=True, exist_ok=True)
    return p


def preferences():
    try:
        return json.loads((app_data() / 'preferences.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def save_preferences(**values):
    data = preferences()
    data.update(values)
    target = app_data() / 'preferences.json'
    tmp = target.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(target)


def verified_engine(path=None):
    p = Path(path or app_data() / 'engine' / KNOWN_HASH / 'hama_fortran.exe')
    if not p.is_file():
        raise DataError('engine_missing', str(p))
    if p.stat().st_size > LIMIT or hashlib.sha256(p.read_bytes()).hexdigest() != KNOWN_HASH:
        raise DataError('engine_hash', str(p))
    return p


def engine_status():
    try:
        p = verified_engine()
        return {'ready': True, 'path': str(p), 'sha256': KNOWN_HASH}
    except DataError as e:
        return {'ready': False, 'path': '', 'code': e.key, 'sha256': KNOWN_HASH}


def install_bytes(blob, zipped=False):
    if len(blob) > LIMIT:
        raise DataError('engine_archive', 'File exceeds 20 MB')
    if zipped:
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                # Read only the exact program member. No extractall and no paths
                # supplied by the archive are ever used on the filesystem.
                matches = [x for x in archive.infolist() if Path(x.filename.replace('\\', '/')).name.lower() == 'hama_fortran.exe']
                if len(matches) != 1 or matches[0].file_size > LIMIT:
                    raise DataError('engine_archive', 'Expected exactly one hama_fortran.exe')
                blob = archive.read(matches[0])
        except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as e:
            raise DataError('engine_archive', str(e)) from e
    digest = hashlib.sha256(blob).hexdigest()
    if not blob.startswith(b'MZ') or digest != KNOWN_HASH:
        raise DataError('engine_hash', 'SHA256: ' + digest)
    folder = app_data() / 'engine' / digest
    folder.mkdir(parents=True, exist_ok=True)
    temp = folder / 'hama.download'
    temp.write_bytes(blob)
    temp.replace(folder / 'hama_fortran.exe')
    return engine_status()


def import_engine(path):
    path = Path(path)
    if path.is_dir():
        matches = list(path.glob('hama_fortran.exe')) + list(path.glob('*/hama_fortran.exe'))
        if len(matches) != 1:
            raise DataError('engine_archive', str(path))
        path = matches[0]
    if not path.is_file() or path.stat().st_size > LIMIT:
        raise DataError('engine_archive', str(path))
    return install_bytes(path.read_bytes(), path.suffix.lower() == '.zip')


def _official_url(url):
    u = urllib.parse.urlsplit(url)
    return u.scheme == 'https' and u.hostname == 'www.esrf.fr' and u.port in (None, 443) and not u.username and not u.password


class OfficialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _official_url(newurl):
            raise DataError('download_redirect', newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_candidates():
    """Only named Hama files in the user's download folder, never a disk scan."""
    folder = Path.home() / 'Downloads'
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
                folder = Path(os.path.expandvars(winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]))
        except OSError:
            pass
    try:
        files = [p for p in folder.iterdir() if p.is_file() and p.name.lower().startswith('hama')
                 and p.suffix.lower() in ('.zip', '.exe') and p.stat().st_size <= LIMIT]
        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)[:20]
    except OSError:
        return []


def _cancelled(cancel):
    if cancel is not None and cancel.is_set():
        raise DataError('download_cancelled')


def _download_error(exc):
    if isinstance(exc, DataError):
        return exc
    if isinstance(exc, urllib.error.HTTPError):
        key = 'download_proxy' if exc.code == 407 else 'download_blocked' if exc.code in (403, 429) else 'download_http'
    else:
        reason = getattr(exc, 'reason', exc)
        key = ('download_tls' if isinstance(reason, ssl.SSLError) else
               'download_timeout' if isinstance(reason, (TimeoutError, socket.timeout)) else
               'download_dns' if isinstance(reason, socket.gaierror) else
               'download_incomplete' if isinstance(reason, http.client.IncompleteRead) else 'download')
    return DataError(key, str(exc))


def download_engine(progress=None, cancel=None, local_only=False):
    """Reuse verified files first, then bounded retries from official HTTPS only."""
    events = []
    def update(stage, **values):
        event = dict(stage=stage, **values)
        # Keep the diagnostic file small; byte-level updates belong only in UI.
        if stage != 'receiving':
            events.append(event)
        if progress:
            progress(event)
    def record():
        try:
            (app_data() / 'last_download.json').write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
        except OSError:
            pass  # Diagnostics must not invalidate an otherwise successful install.
    try:
        _cancelled(cancel)
        update('checking')
        current = engine_status()
        if current['ready']:
            update('cached')
            return current
        for path in download_candidates():
            _cancelled(cancel)
            try:
                result = import_engine(path)
                update('imported', path=str(path))
                return result
            except (DataError, OSError) as e:
                update('local_rejected', path=str(path), detail=str(e))
        if local_only:
            raise DataError('download_local_missing', '\n'.join(e.get('detail', '') for e in events if e['stage'] == 'local_rejected'))
        opener = urllib.request.build_opener(OfficialRedirect())
        errors = []
        # Both URLs are the official download, with/without the CMS query flag.
        urls = (DOWNLOAD.split('?')[0], DOWNLOAD, DOWNLOAD.split('?')[0])
        for attempt, url in enumerate(urls, 1):
            _cancelled(cancel)
            if attempt > 1:
                update('retry', attempt=attempt, attempts=len(urls), code=errors[-1].key)
                if cancel is not None:
                    if cancel.wait(attempt - 1):
                        raise DataError('download_cancelled')
                else:
                    time.sleep(attempt - 1)
            update('connecting', attempt=attempt, attempts=len(urls), url=url)
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'curl/8.13.0', 'Accept': 'application/zip,*/*', 'Accept-Encoding': 'identity'})
                started = time.monotonic()
                with opener.open(request, timeout=8) as response:
                    if not _official_url(response.url):
                        raise DataError('download_redirect', response.url)
                    length = response.headers.get('Content-Length', '')
                    total = int(length) if length.isdigit() else 0
                    if total > LIMIT:
                        raise DataError('download_limit', f'Content-Length={total}')
                    if 'html' in response.headers.get('Content-Type', '').lower():
                        raise DataError('download_html', 'Server returned HTML instead of ZIP')
                    chunks, received = [], 0
                    while True:
                        _cancelled(cancel)
                        if time.monotonic() - started > 25:
                            raise DataError('download_timeout', 'Attempt exceeded 25 seconds')
                        chunk = response.read1(64 * 1024)
                        if not chunk:
                            break
                        chunks.append(chunk)
                        received += len(chunk)
                        if received > LIMIT:
                            raise DataError('download_limit', 'Downloaded body exceeds 20 MB')
                        update('receiving', attempt=attempt, attempts=len(urls), received=received, total=total)
                    if total and total != received:
                        raise DataError('download_incomplete', f'Expected {total} bytes; received {received}')
                    blob = b''.join(chunks)
                _cancelled(cancel)
                if blob.lstrip()[:1] == b'<':
                    raise DataError('download_html', 'Downloaded an HTML/XML error page')
                update('verifying', received=len(blob))
                result = install_bytes(blob, zipped=True)
                update('complete', received=len(blob))
                return result
            except (DataError, OSError, ValueError, http.client.HTTPException) as exc:
                error = _download_error(exc)
                if error.key == 'download_cancelled':
                    raise error
                errors.append(error)
                update('attempt_failed', attempt=attempt, code=error.key, detail=error.detail)
                if error.key in ('engine_hash', 'download_redirect', 'download_limit', 'download_tls'):
                    break
        last = errors[-1]
        raise DataError(last.key, '\n'.join(f'Attempt {i}: {e.key}: {e.detail}' for i, e in enumerate(errors, 1)))
    except Exception as exc:
        update('failed', code=getattr(exc, 'key', 'unexpected'), detail=str(exc))
        raise
    finally:
        record()


def short_path(path):
    path = str(Path(path).resolve())
    if os.name == 'nt':
        buf = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetShortPathNameW(path, buf, len(buf))
        if 0 < length < len(buf):
            path = buf.value
    return path


def work_root():
    candidates = []
    custom = preferences().get('work_root')
    if custom:
        candidates.append(Path(custom))
    candidates += [app_data() / 'work', Path(tempfile.gettempdir()) / 'EXAFSWT']
    # An ASCII fallback for accounts whose profile path has no ASCII 8.3 alias.
    user = hashlib.sha256(str(app_data()).encode()).hexdigest()[:12]
    if os.name == 'nt':
        candidates.append(Path(os.environ.get('PUBLIC', r'C:\Users\Public')) / 'EXAFSWT' / user)
    errors = []
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            alias = short_path(p)
            if not alias.isascii() or ' ' in alias or len(alias) > 130:
                raise ValueError('No short ASCII path is available')
            with tempfile.TemporaryFile(dir=alias):
                pass
            return Path(alias)
        except (OSError, ValueError) as e:
            errors.append(f'{p}: {e}')
    raise DataError('work_path', '\n'.join(errors))


@contextlib.contextmanager
def work_directory():
    with tempfile.TemporaryDirectory(prefix='wt_', dir=work_root()) as directory:
        yield Path(directory)
