import argparse
import hashlib
import os
from pathlib import Path

FORBIDDEN = {'hama_fortran.exe', 'hama.exe', 'hama_1.zip', 'hama.zip', 'wgnuplot.exe', 'hama_readme.pdf', 'hamareadme.pdf', 'modelparameters.txt', 'preferences.json'}
ENGINE_HASH = 'f8fa901ca98bee23113d88e9864ed64ece6aa0c9982d1d6a9a4d360e07f8b054'
EXCLUDE = {'.git', '.venv', '.npm-prefix', 'node_modules', '__pycache__', 'build', 'dist', 'release', 'test_artifacts'}


def check(root):
    root = Path(root)
    errors = []
    count = 0
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        for name in files:
            p = Path(folder) / name
            count += 1
            if name.lower() in FORBIDDEN:
                errors.append(str(p.relative_to(root)))
            if p.suffix.lower() == '.exe' and hashlib.sha256(p.read_bytes()).hexdigest() == ENGINE_HASH:
                errors.append('Hama executable found under renamed path: ' + str(p.relative_to(root)))
    for required in ('LICENSE', 'README.md', 'README.zh-CN.md', 'THIRD_PARTY_NOTICES.md'):
        if not (root / required).is_file():
            errors.append('Missing: ' + required)
    if errors:
        raise SystemExit('\n'.join(errors))
    print(f'Release boundary passed: {count} files, no Hama distribution files or local preferences.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    check(parser.parse_args().source)
