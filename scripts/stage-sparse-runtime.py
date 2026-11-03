"""Stage unmodified CPU runtime DLLs and all supplied license notices."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import shutil
import sys

root=Path(__file__).resolve().parents[1]
destination=Path(sys.argv[1]) if len(sys.argv)>1 else root/'components/pde/native'
destination.mkdir(parents=True,exist_ok=True)
cpu_dlls={'mkl_rt.2.dll','mkl_core.2.dll','mkl_intel_thread.2.dll','mkl_def.2.dll',
          'mkl_mc3.2.dll','mkl_avx2.2.dll','mkl_avx512.2.dll','libimalloc.dll','libiomp5md.dll'}
for previous in destination.glob('*.dll'):
    if previous.name not in cpu_dlls:previous.unlink()
records=[]
for line in (root/'requirements-sparse.txt').read_text(encoding='utf8').splitlines():
    if not line or line.startswith('#'):continue
    name,version=line.split('==');dist=metadata.distribution(name)
    if dist.version!=version:raise RuntimeError(f'{name}: expected {version}, found {dist.version}')
    licenses=[];binaries=[]
    for file in dist.files or []:
        source=Path(dist.locate_file(file));relative=str(file).replace('\\','/')
        if '/Library/bin/' in relative and source.name in cpu_dlls:
            target=destination/source.name
            digest=hashlib.sha256(source.read_bytes()).hexdigest()
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:shutil.copy2(source,target)
            binaries.append({'file':source.name,'sha256':digest})
        elif source.is_file() and (('/licensing/' in relative) or ('.dist-info/' in relative and any(word in source.name.lower() for word in ('license','copying','notice')))):
            target=destination/'licenses'/name/source.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            licenses.append(str(target.relative_to(destination)))
    if not licenses:raise RuntimeError(f'License texts missing for {name}')
    records.append({'name':name,'version':version,'licenses':licenses,'binaries':binaries})
for required in cpu_dlls:
    if not (destination/required).is_file():raise RuntimeError(f'Missing runtime: {required}')
(destination/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(f'Staged oneMKL runtime in {destination}')
