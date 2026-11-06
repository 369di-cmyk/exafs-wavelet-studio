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


def download_engine():
    try:
        # ESRF's CDN rejects some custom client user agents with HTTP 403.
        # This standard download-client header was verified with the official ZIP.
        request = urllib.request.Request(DOWNLOAD, headers={'User-Agent': 'curl/8.13.0'})
        with urllib.request.urlopen(request, timeout=35) as response:
            if not response.url.startswith('https://www.esrf.fr/'):
                raise DataError('download', 'Unexpected redirect outside www.esrf.fr')
            blob = response.read(LIMIT + 1)
        return install_bytes(blob, zipped=True)
    except DataError:
        raise
    except (OSError, ValueError) as e:
        raise DataError('download', str(e)) from e


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
