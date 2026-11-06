"""Build a source allowlist and portable archive; never harvest a whole workspace."""
from pathlib import Path
import shutil
import zipfile
from check_release import check

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'release'
SOURCE = RELEASE / 'GitHub_Source'
TOP = ['app.py', 'core.py', 'engine_manager.py', 'exports.py', 'issues.py', 'plot_bridge.cs', 'installer.cs', 'app.ico',
       'LICENSE', 'README.md', 'README.zh-CN.md', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_LICENSES.txt',
       'TEST_REPORT.md', 'requirements.txt', 'requirements-dev.txt', '.gitignore']
TREE = ['frontend/src', 'fixtures', 'scripts', 'tests', '.github', 'third_party']
FRONT = ['package.json', 'package-lock.json', 'components.json', 'index.html', 'vite.config.ts', 'tsconfig.json',
         'tsconfig.app.json', 'tsconfig.node.json', 'eslint.config.js', '.gitignore', '.prettierrc', '.prettierignore']


def archive(folder, destination):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED, compresslevel=7) as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():
                z.write(p, p.relative_to(folder).as_posix())


def main():
    RELEASE.mkdir(exist_ok=True)
    # Remove only our exact previously generated source staging directory.
    if SOURCE.exists():
        if SOURCE.resolve() != (ROOT / 'release' / 'GitHub_Source').resolve():
            raise RuntimeError('Unsafe staging path')
        shutil.rmtree(SOURCE)
    SOURCE.mkdir()
    for item in TOP + ['frontend/' + f for f in FRONT]:
        target = SOURCE / item
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / item, target)
    for item in TREE:
        shutil.copytree(ROOT / item, SOURCE / item, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    check(SOURCE)
    archive(SOURCE, RELEASE / 'EXAFS_Wavelet_Studio_2.0.0_Source.zip')
    binary = ROOT / 'dist' / 'EXAFS_Wavelet_Studio'
    if not (binary / 'EXAFS_Wavelet_Studio.exe').is_file():
        raise RuntimeError('Build the desktop executable first')
    for item in ['LICENSE', 'README.md', 'README.zh-CN.md', 'THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_LICENSES.txt', 'TEST_REPORT.md']:
        shutil.copy2(ROOT / item, binary / item)
    shutil.copytree(ROOT / 'third_party', binary / 'third_party', dirs_exist_ok=True)
    check(binary)
    archive(binary, RELEASE / 'EXAFS_Wavelet_Studio_2.0.0_Windows.zip')
    print('Created source and portable archives; no Hama engine is included.')


if __name__ == '__main__':
    main()
