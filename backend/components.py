"""Installed optional resources, outside the frozen application archive."""
import importlib.util
import os
from pathlib import Path
import sys

# Keep incidental BLAS calls serial; PARDISO receives its own thread-local cap.
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'


ROOT = Path(sys.executable).resolve().parents[1] / 'components' if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'components'
if (ROOT / 'pde').is_dir():
    sys.path.insert(0, str(ROOT / 'pde'))


def capabilities():
    return {'pde': (ROOT / 'pde/calix_pde/__init__.py').is_file(),
            'languages': (ROOT / 'languages.json').is_file(),
            'themes': (ROOT / 'themes.css').is_file()}


def pde_module():
    from .syntax import InputError
    if not capabilities()['pde']:
        raise InputError('PDE module is not installed. Run the Calix installer and select PDE module.')
    location = str(ROOT / 'pde')
    if location not in sys.path:
        sys.path.insert(0, location)
    # Restrict numerical BLAS pools inside each application CPU worker.
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    os.environ['OMP_NUM_THREADS'] = '1'
    try:
        import calix_pde
        return calix_pde
    except ImportError as exc:
        raise InputError(f'PDE component is incomplete; reinstall it: {exc}') from exc
