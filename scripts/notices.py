"""Collect installed component licenses without granting rights to Calix source."""
from pathlib import Path
import importlib.metadata as metadata
import json
import shutil
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "release/notices"
DEST.mkdir(parents=True, exist_ok=True)
records = []


def write_component(kind, name, version, license_id, files):
    folder = DEST / kind / name.replace("/", "__").replace("@", "")
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for index, file in enumerate(files):
        if file.is_file():
            target = folder / f"{index}-{file.name}"
            shutil.copy2(file, target)
            saved.append(str(target.relative_to(DEST)))
    records.append({"ecosystem": kind, "name": name, "version": version,
                    "license": license_id, "license_files": saved})


lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))
for relative, data in lock["packages"].items():
    if not relative or data.get("dev"):
        continue
    folder = ROOT / relative
    manifest = folder / "package.json"
    if not manifest.exists():
        continue
    package = json.loads(manifest.read_text(encoding="utf-8"))
    files = [p for p in folder.iterdir() if p.is_file() and any(p.name.lower().startswith(prefix) for prefix in ("license", "licence", "copying", "notice"))]
    files += [p for p in folder.glob("fonts/*") if p.is_file() and any(key in p.name.lower() for key in ("license", "copying", "ofl"))]
    if not files and package["name"] in ("rehype-katex", "remark-math"):
        files = [ROOT / "docs/licenses/remark-math-LICENSE.txt"]
    write_component("npm", package["name"], package["version"], package.get("license", "REVIEW"), files)

excluded = {"pip", "pytest", "iniconfig", "pluggy", "httpx", "httpcore", "certifi", "pyinstaller-hooks-contrib", "altgraph", "pefile", "pywin32-ctypes"}
for dist in metadata.distributions():
    name = dist.metadata["Name"]
    if name.lower() in excluded:
        continue
    files = [Path(dist.locate_file(p)) for p in (dist.files or []) if any(key in str(p).lower() for key in ("license", "licence", "copying", "notice")) and ".dist-info" in str(p)]
    license_id = dist.metadata.get("License-Expression") or dist.metadata.get("License", "REVIEW")
    if len(license_id) > 200:
        license_id = "See license files"
    write_component("python", name, dist.version, license_id, files)

python_license = Path(sys.base_prefix) / "LICENSE.txt"
write_component("runtime", "CPython", sys.version.split()[0], "PSF-2.0 and bundled notices", [python_license])
write_component("native", "Boost", "1.86.0", "BSL-1.0", [ROOT / "tools/boost_1_86_0/LICENSE_1_0.txt"])
write_component("native", "Eigen", "3.4.0", "MPL-2.0 (EIGEN_MPL2_ONLY)", [ROOT / "tools/eigen-3.4.0/COPYING.MPL2", ROOT / "tools/eigen-3.4.0/COPYING.README"])
runtime=ROOT/'components/pde/native'
if (runtime/'manifest.json').is_file():
    shutil.copytree(runtime/'licenses',DEST/'native/oneMKL-runtime-licenses',dirs_exist_ok=True)
    shutil.copy2(runtime/'manifest.json',DEST/'native/oneMKL-runtime-manifest.json')
eigen_source = DEST / 'mpl-sources/eigen-3.4.0.zip'
eigen_source.parent.mkdir(exist_ok=True)
shutil.copy2(ROOT / 'work/eigen-3.4.0.zip', eigen_source)
nsis_license = ROOT / "tools/nsis-unpacked/nsis-3.08/COPYING"
if nsis_license.exists():
    write_component("installer", "NSIS", "3.08", "Zlib (installer uses zlib compression)", [nsis_license])

cargo = ROOT / "tools/cargo/bin/cargo.exe"
if cargo.exists() and (ROOT / "src-tauri/Cargo.lock").exists():
    env = dict(os.environ, CARGO_HOME=str(ROOT / "tools/cargo"), RUSTUP_HOME=str(ROOT / "tools/rustup"))
    env["PATH"] = str(cargo.parent) + os.pathsep + env.get("PATH", "")
    result = subprocess.run([str(cargo), "metadata", "--manifest-path", str(ROOT / "src-tauri/Cargo.toml"), "--format-version", "1", "--filter-platform", "x86_64-pc-windows-msvc", "--locked", "--offline"], capture_output=True, text=True, encoding="utf-8", env=env, check=True)
    for package in json.loads(result.stdout)["packages"]:
        if package["name"] == "calix":
            continue
        folder = Path(package["manifest_path"]).parent
        files = [p for p in folder.iterdir() if p.is_file() and any(p.name.lower().startswith(prefix) for prefix in ("license", "licence", "copying", "notice"))]
        if package.get("license_file"):
            files.append(folder / package["license_file"])
        if not files:
            name = package["name"]
            if name == "selectors":
                files = list(folder.parent.glob("cssparser-*/LICENSE"))[:1]
            elif name == "tauri-plugin":
                files = list(folder.parent.glob("tauri-2.12.5/LICENSE-*"))
            elif name.startswith("webview2-com"):
                files = [ROOT / "docs/licenses/webview2-rs-LICENSE.txt"]
            elif name == "alloc-stdlib":
                files = [ROOT / "docs/licenses/alloc-stdlib-LICENSE.txt"]
        write_component("cargo", package["name"], package["version"], package.get("license") or "REVIEW", files)
        if "MPL-2.0" in (package.get("license") or ""):
            source = next((ROOT / "tools/cargo/registry/cache").glob(f"*/{package['name']}-{package['version']}.crate"))
            source_dest = DEST / "mpl-sources"
            source_dest.mkdir(exist_ok=True)
            shutil.copy2(source, source_dest / source.name)

for file in (ROOT / "docs/licenses").glob("*"):
    shutil.copy2(file, DEST / file.name)

(DEST / "components.json").write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
sections = [f"Calix {version} - Third-party notices", "Calix application code is proprietary. Third-party components retain their own licenses.", ""]
for record in records:
    sections.append(f"{record['ecosystem']}: {record['name']} {record['version']} | {record['license']}")
    sections.extend("  " + file for file in record["license_files"])
    if not record["license_files"]:
        sections.append("  REVIEW REQUIRED: package did not include a root license file")
(DEST / "THIRD-PARTY-NOTICES.txt").write_text("\n".join(sections), encoding="utf-8")
print(f"Collected {len(records)} component records in {DEST}")
