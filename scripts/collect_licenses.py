"""Collect actual installed notices, including build-time tools for transparency."""
import importlib.metadata as metadata
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sections = ['EXAFS Wavelet Studio - third-party license texts\nIncludes runtime dependencies and development/build tools. Not all listed tools are shipped.\nHama and Origin are not bundled.\n']
found = 0
for dist in sorted(metadata.distributions(), key=lambda d: d.metadata.get('Name', '')):
    name = dist.metadata.get('Name', 'Unknown')
    for entry in dist.files or []:
        p = Path(dist.locate_file(entry))
        if p.is_file() and any(word in p.name.lower() for word in ('license', 'copying', 'copyright', 'notice')) and p.suffix.lower() not in ('.py', '.pyc', '.dll', '.exe'):
            try:
                content = p.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            sections.append(f'\n=== {name} {dist.version} / {entry} ===\n{content}\n')
            found += 1
node = ROOT / 'frontend' / 'node_modules'
for p in sorted(node.rglob('*')):
    if p.is_file() and p.name.lower().startswith(('license', 'copying', 'notice')) and p.suffix.lower() not in ('.js', '.map', '.ts', '.cjs', '.mjs'):
        sections.append(f'\n=== npm / {p.relative_to(node).as_posix()} ===\n' + p.read_text(encoding='utf-8', errors='replace') + '\n')
        found += 1
for p in [Path(sys.base_prefix) / 'LICENSE.txt', Path(sys.base_prefix) / 'LICENSE']:
    if p.is_file():
        sections.append('\n=== Python runtime ===\n' + p.read_text(encoding='utf-8', errors='replace'))
        found += 1
if found < 20:
    raise SystemExit('Too few license files found. Install build dependencies before collecting notices.')
for p in sorted((ROOT / 'third_party').glob('*.txt')):
    sections.append('\n=== Microsoft WebView2 SDK 1.0.3856.49 / ' + p.name + ' ===\n' + p.read_text(encoding='utf-8', errors='replace'))
(ROOT / 'THIRD_PARTY_LICENSES.txt').write_text('\n'.join(sections), encoding='utf-8')
print(f'Collected {found} license/notice files.')
