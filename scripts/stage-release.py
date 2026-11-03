"""Assemble a relocatable preview next to the standalone installer."""
from pathlib import Path
import hashlib
import json
import shutil

root = Path(__file__).resolve().parents[1]
dest = root / "release/Calix-portable"
dest.mkdir(parents=True, exist_ok=True)
shutil.copy2(root / "src-tauri/target/release/calix.exe", dest / "Calix.exe")
shutil.copytree(root / "release/backend/calix-service", dest / "backend", dirs_exist_ok=True)
shutil.copytree(root / "release/notices", dest / "notices", dirs_exist_ok=True)
shutil.copytree(root / 'release/components', dest / 'components', dirs_exist_ok=True)
shutil.copytree(root / "examples", dest / "examples", dirs_exist_ok=True)
for retired in ("IMO 1988 第6题-韦达跳跃.calix", "IMO 2009 第6题-蚱蜢跳跃.calix", "00-projectile-with-quadratic-drag.calix", "00-projectile-with-linear-drag.calix", "三天体-平面引力运动.calix", "单位换算.calix", "单位运算.calix", "石英与空气-电磁波反射和透射.calix"):
    (dest / "examples" / retired).unlink(missing_ok=True)
shutil.copytree(root / "docs", dest / "docs", dirs_exist_ok=True)
shutil.copy2(root / "README.md", dest / "README.md")
shutil.copy2(root / "LICENSE", dest / "LICENSE")
for name in ('calix.cmd', 'API.md', 'AGENTS.md', 'AI-CONTROL.md', 'README.zh-CN.md', 'CONTRIBUTING.md', 'SECURITY.md'):
    shutil.copy2(root / name, dest / name)
shutil.copy2(root / 'native/build/Release/calix-cli.exe', dest / 'calix-cli.exe')
version = json.loads((root / "package.json").read_text(encoding="utf-8"))["version"]
installer_name = f"Calix_{version}_x64-setup.exe"
installer = root / "release" / installer_name
if not installer.is_file():
    raise FileNotFoundError('Run scripts/build-desktop.ps1 to build the optional-component installer first')
records = []
for path in (dest / "Calix.exe", dest / "backend/calix-service.exe", dest / "backend/_internal/calix_native.dll", installer):
    records.append({"file": str(path.relative_to(root / "release")), "bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
(root / "release/SHA256.json").write_text(json.dumps(records, indent=2), encoding="utf-8")
print(json.dumps(records, indent=2))
