"""Stage optional runtime packages without linking them into the application."""
from pathlib import Path
import importlib.metadata as metadata
import json
import shutil
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
dest=root/'release/components'
dest.mkdir(parents=True,exist_ok=True)
subprocess.run([sys.executable,str(root/'scripts/stage-sparse-runtime.py'),str(root/'components/pde/native')],check=True)
shutil.copytree(root/'components/pde/native',dest/'pde/native',dirs_exist_ok=True)
shutil.copy2(root/'components/themes.css',dest/'themes.css')
shutil.copytree(root/'components/pde/calix_pde',dest/'pde/calix_pde',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for name in ('numpy','scipy','scikit-fem'):
    dist=metadata.distribution(name)
    folders=set()
    for file in dist.files:
        head=file.parts[0]
        if head not in ('.','..') and not head.endswith('.pyc'):
            folders.add(head)
    for folder in folders:
        src=Path(dist.locate_file(folder));target=dest/'pde'/folder
        if src.is_dir():shutil.copytree(src,target,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','tests','benchmarks'))
        elif src.is_file():shutil.copy2(src,target)
    if name == 'numpy':
        required = 'numpy/_core/tests/_natype.py'
        target = dest/'pde'/required
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(dist.locate_file(required),target)
subprocess.run(['node','scripts/package-locales.cjs'],cwd=root,check=True)
# Keep development resources available through the same authenticated API.
shutil.copy2(dest/'languages.json',root/'components/languages.json')
versions={n:metadata.version(n) for n in ('numpy','scipy','scikit-fem')}
(dest/'pde/versions.json').write_text(json.dumps(versions,indent=2),encoding='utf-8')
print('Staged optional components:',versions)
