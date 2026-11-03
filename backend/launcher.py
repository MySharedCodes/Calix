"""Locate and launch the Calix desktop without routing arguments through a shell."""
from pathlib import Path
import os
import subprocess
import sys


def _candidates():
    override = os.environ.get('CALIX_UI_PATH')
    if override:
        yield Path(override)
    here = Path(__file__).resolve()
    # Source checkout, installed App folder, and a frozen backend child all use
    # one of these relative layouts.
    binary = Path(sys.executable).resolve().parent
    roots = [binary, binary.parent, here.parent, here.parent.parent, here.parent.parent.parent, Path.cwd()]
    seen_roots = set()
    for root in roots:
        root = root.resolve()
        if root in seen_roots:
            continue
        seen_roots.add(root)
        yield root / 'calix.exe'
        yield root / 'App/calix.exe'
        yield root / 'src-tauri/target/release/calix.exe'
        yield root / 'release/Calix-portable/Calix.exe'


def find_ui():
    override = os.environ.get('CALIX_UI_PATH')
    if override:
        path = Path(override).resolve()
        if not path.is_file() or path.suffix.lower() != '.exe':
            raise FileNotFoundError('CALIX_UI_PATH must name an existing desktop executable')
        return path
    seen = set()
    for candidate in _candidates():
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file() and candidate.suffix.lower() == '.exe':
            return candidate
    return None


def open_user_interface(notebook=None):
    executable = find_ui()
    if executable is None:
        raise FileNotFoundError('Calix desktop executable was not found; set CALIX_UI_PATH')
    options = {'cwd': str(executable.parent), 'stdin': subprocess.DEVNULL,
               'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL}
    command = [str(executable)]
    if notebook is not None:
        notebook = Path(notebook).resolve()
        if not notebook.is_file() or notebook.suffix.lower() not in ('.cixnb', '.clxnb', '.calix'):
            raise ValueError('Expected an existing Calix notebook')
        if notebook.stat().st_size > 10_000_000:
            raise ValueError('Notebook exceeds 10 MB')
        command += ['--notebook', str(notebook)]
    if os.name == 'nt':
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_BREAKAWAY_FROM_JOB
    else:
        options['start_new_session'] = True
    try:
        process = subprocess.Popen(command, **options)
    except OSError:
        if os.name != 'nt':
            raise
        options['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        process = subprocess.Popen(command, **options)
    return {'opened': True, 'executable': str(executable), 'pid': process.pid,
            'notebook': str(notebook) if notebook else None}
