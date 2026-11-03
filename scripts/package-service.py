from pathlib import Path
import ast
import importlib.util
import sys
import PyInstaller.__main__
from PyInstaller.utils.hooks import collect_submodules

root = Path(__file__).resolve().parents[1]
hidden = collect_submodules("sympy", filter=lambda name: not any(part in {"tests", "benchmarks", "galgebra"} for part in name.split(".")))
arguments = ["--noconfirm", "--clean", "--onedir", "--name", "calix-service",
             "--distpath", str(root / "release/backend"), "--workpath", str(root / "work/pyinstaller"),
             "--specpath", str(root / "work"), "--paths", str(root),
             "--add-binary", f"{root / 'native/build/Release/calix_native.dll'};.",
             "--collect-data", "pint", "--add-data", f"{root / 'backend/characters.json'};backend", "--hidden-import", "backend.service", "--hidden-import", "backend.launcher",
             "--hidden-import", "xml.etree.ElementTree", "--hidden-import", "xml.etree.ElementPath", "--hidden-import", "_elementtree",
             "--hidden-import", "ctypes.util", "--hidden-import", "fractions", "--hidden-import", "platform"]
for name in hidden:
    arguments.extend(["--hidden-import", name])
# Optional packages import standard-library modules at runtime. Include those
# standard modules without embedding NumPy/SciPy or the PDE package itself.
stdlib = set()
for package in ('numpy', 'scipy', 'skfem'):
    folder = Path(importlib.util.find_spec(package).origin).parent
    for source in folder.rglob('*.py'):
        if any(part in ('tests','benchmarks') for part in source.relative_to(folder).parts):
            continue
        try:
            tree = ast.parse(source.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
            stdlib.update(name.split('.')[0] for name in names if name and name.split('.')[0] in sys.stdlib_module_names)
for name in sorted(stdlib - {'tkinter','_tkinter','turtle','idlelib','test','antigravity','this'}):
    arguments.extend(['--hidden-import',name])
for name in ("pytest", "_pytest", "tkinter", "IPython", "matplotlib", "scipy", "numpy", "pandas"):
    arguments.extend(["--exclude-module", name])
arguments.append(str(root / "backend/entry.py"))
PyInstaller.__main__.run(arguments)
