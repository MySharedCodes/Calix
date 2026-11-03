"""Write a reproducible source revision and toolchain record without machine secrets."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def command(*args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    return result.stdout.strip() if result.returncode == 0 else None


version = json.loads((ROOT/'package.json').read_text(encoding='utf-8'))['version']
files = [name for name in (command('git', 'ls-files', '-z') or '').split('\0') if name]
digest = hashlib.sha256()
for name in sorted(files):
    path = ROOT/name
    if path.is_file():
        digest.update(name.encode('utf-8')+b'\0'+hashlib.sha256(path.read_bytes()).digest())
record = {
    'version': version,
    'source_commit': command('git', 'rev-parse', 'HEAD'),
    'source_dirty': bool(command('git', 'status', '--porcelain', '--untracked-files=no')),
    'tracked_source_sha256': digest.hexdigest(),
    'python': platform.python_version(),
    'node': command('node', '--version'),
    'rust': command('rustc', '--version'),
    'lockfiles': {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['package-lock.json','src-tauri/Cargo.lock','requirements-lock.txt']},
}
(ROOT/'release').mkdir(exist_ok=True)
(ROOT/'release/BUILD-INFO.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
print(f'Build provenance: version {version}, commit {record["source_commit"]}, dirty={record["source_dirty"]}')
