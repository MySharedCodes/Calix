"""Synchronize the desktop, service, lockfiles and current manuals."""
from pathlib import Path
import json
import re
import sys

root = Path(__file__).resolve().parents[1]
version = sys.argv[1]
if not re.fullmatch(r'\d+\.\d+\.\d+', version):
    raise SystemExit('Expected a numeric x.y.z version')
old = json.loads((root/'package.json').read_text(encoding='utf-8'))['version']
for name in ('package.json', 'package-lock.json', 'src-tauri/tauri.conf.json'):
    path = root/name
    data = json.loads(path.read_text(encoding='utf-8'))
    data['version'] = version
    if 'packages' in data:
        data['packages']['']['version'] = version
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
for name in ('src-tauri/Cargo.toml', 'src-tauri/Cargo.lock', 'backend/service.py', 'frontend/src/App.tsx', 'frontend/src/Help.tsx'):
    path = root/name
    text = path.read_text(encoding='utf-8')
    if name.endswith('Cargo.lock'):
        text = re.sub(r'(name = "calix"\nversion = ")[^"]+', lambda match: match[1]+version, text)
    else:
        text = text.replace(old, version)
    path.write_text(text, encoding='utf-8')
for name in ('README.md','README.zh-CN.md','docs/README.md','docs/GETTING-STARTED.md','docs/GETTING-STARTED.en.md','docs/USER-GUIDE.md','docs/INSTALLATION.md','docs/TROUBLESHOOTING.md','docs/SUPPORTED-SYNTAX.md','docs/STATISTICS-AND-UNITS.md','docs/PDE.md','docs/ROADMAP.md'):
    path = root/name
    text = path.read_text(encoding='utf-8')
    text = text.replace(old, version)
    path.write_text(text, encoding='utf-8')
print(f'{old} -> {version}')
