# 开发环境与构建

当前验证目标是 Windows x64；Linux/macOS 没有经过完整桌面发行验证。
Calix 自有源码采用 [GPL-3.0-only](../LICENSE)，公开仓库为 [MySharedCodes/Calix](https://github.com/MySharedCodes/Calix)。代码签名尚未配置。见[许可证与发布状态](LICENSING.md)。

## 环境

先克隆源码并进入项目目录：

```powershell
git clone https://github.com/MySharedCodes/Calix.git
cd Calix
```

| 依赖 | 当前使用方式 |
|---|---|
| Node.js 与 npm | Node 24；依赖以 `package-lock.json` 锁定，使用 `npm ci` |
| Python | CPython 3.12 x64，根目录 `.venv` |
| C++ | Visual Studio 2022 Build Tools，Desktop development with C++、Windows SDK、CMake >=3.24 |
| Rust | stable x86_64-pc-windows-msvc，Tauri 2；精确 crate 见 `src-tauri/Cargo.lock` |
| WebView | Microsoft Edge WebView2 Runtime |
| Native headers | Boost 1.86.0、Eigen 3.4.0，分别解压到 `tools/boost_1_86_0`、`tools/eigen-3.4.0` |

不要从别人机器复制虚拟环境。下载上游依赖时保留其许可证和版本；不要把整个本机开发目录上传到仓库。

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm.cmd ci
```

需要数值 PDE、完整案例或发行打包时再安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-pde.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-sparse.txt
```

Intel 运行库有独立限制，其与 GPLv3 组合分发的兼容性尚未解决；上述安装步骤用于本地开发，不能作为已获组合分发授权的证明。公开二进制发行前需解决求解器与运行库的许可问题。见[许可审查](LICENSE-REVIEW.md)。

## 项目结构

| 路径 | 职责 |
|---|---|
| `frontend/src/` | React、CodeMirror、MathLive 编辑器、图形和工作空间 |
| `backend/` | 语言解析、符号运算、单位、API、进程隔离与可选 PDE 接口 |
| `native/` | C++20 数值内核、稀疏求解接口、SIMD 分派和 CLI 启动器 |
| `src-tauri/` | Windows 桌面壳、文件与服务生命周期 |
| `examples/` | 可保存、打开的计算笔记本 |
| `docs/` | 当前手册、函数范围、建模限制和历史变更 |
| `tests/` | 引擎、API、原生和浏览器验证 |
| `scripts/` | 构建、资源准备、组件和安装包生成 |

## 本地运行

先解压上述头文件，再运行 C++ 构建：

```powershell
.\scripts\build-native.ps1
```

这会产生 `native/build/Release/calix_native.dll` 与 `calix-cli.exe`。
保留通用 CPU 基线，AVX2/AVX-512/AMX 分别编译并在运行时检查，不要给整个程序强加 AVX 指令要求。

在一个终端启动计算服务：

```powershell
$env:CALIX_MAX_WORKERS = '8'
.\.venv\Scripts\python.exe -m backend.service --port 8765 --token calix-local-development --workers 8
```

`calix-local-development` 只用于本机开发；发行版生成自己的 token。不要转发服务端口。
另一个终端：

```powershell
npm.cmd run dev
```

打开 `http://127.0.0.1:5173`。Vite 将 `/api` 代理至 8765。浏览器可验证输入、计算和帮助；原生文件对话框等需要 Tauri 桌面验证。使用当前机器物理核范围内的 Workers；此项目调试取 8。

若 8765 已由其它程序占用，为服务选择空闲端口，并在启动 Vite 前设置 `$env:CALIX_BACKEND_URL='http://127.0.0.1:新端口'`。不要终止不属于 Calix 的进程。

桌面开发可运行 `npm.cmd run tauri -- dev`，需要可用的 Rust/MSVC 环境和配套 backend 资源。

## 验证

```powershell
npm.cmd run build
.\.venv\Scripts\python.exe scripts/check-docs.py
.\.venv\Scripts\python.exe -m pytest tests/test_engine.py -q -k "not shipped_examples and not physics_starter"
```

前端构建包含 TypeScript 检查。上面的引擎快速检查排除了运行完整案例和抛体参数反求的慢测试；改动相关求解器时应另行运行它们。根据修改选择其它 `tests/test_*.py`，无需每次运行所有重型案例。可选模块测试需要其依赖与原生运行库。

浏览器检查需要安装 Playwright 及 Chromium；测试脚本接受的环境变量以脚本开头为准。例如 `tests/ui-help.cjs` 使用 `CALIX_PLAYWRIGHT` 指定 Playwright 模块路径，`CALIX_URL` 指定正在运行的开发服务器。部分历史 UI 脚本保留了本机路径，不能当作通用 CI 命令。

## 安装包

`scripts/bootstrap-native.ps1` 可下载指定版本的 Boost/Eigen 并验证归档，再构建 C++。也可用 `-BoostRoot`、`-EigenRoot` 指定已有头文件。桌面打包支持本地 `tools/cargo` 或标准 PATH 中的 Rust。完整发行仍需以下依赖与原始许可归档：

- C++ 输出、锁定的 Python/npm 依赖，以及 PDE 和稀疏运行库；`package-service.py` 会扫描可选 Python 包所用标准库。
- Rust stable MSVC，可使用标准 rustup 安装；存在 `tools/cargo/bin/cargo.exe` 时脚本优先使用该本地工具链。
- `work/eigen-3.4.0.zip`：上游原始源码归档，用于 `scripts/notices.py` 随包提供 MPL 对应源码。清理缓存后必须恢复该归档，不能静默略过。
- 可用 NSIS，通常由 Tauri 安装至本机缓存，或使用 `tools/nsis-unpacked/nsis-3.08/Bin/makensis.exe`。

```powershell
.\scripts\build-desktop.ps1
.\.venv\Scripts\python.exe scripts/stage-release.py
```

第一步生成 backend、可选组件、Tauri 程序及带选项的安装包；第二步组装 `release/Calix-portable` 并更新 `release/SHA256.json`。CLI 与 GUI 必须使用配套版本的 backend。仅修改 UI 和文档时，可以复用已验证的 backend，配置上述 Rust 环境后运行 `npm.cmd run tauri -- build`，再运行 `scripts/optional-installer.py` 与 `scripts/stage-release.py`。

文档通过 `?raw` 导入编入帮助，同时作为 Markdown 随安装包分发。修改手册后应重新构建 UI；只复制 Markdown 不会更新 F1 中的内容。

`scripts/verify.py` 提供核心、数值和完整案例三个有超时限制的验证层；`.github/workflows/verify.yml` 配置 Windows 自动验证。`scripts/verify-ui.py` 启动独立服务做浏览器测试。构建前运行 `scripts/build-info.py`，发行目录含源码提交与依赖摘要；发布前运行 `scripts/release-check.py`。详见 [稳定版验收](ACCEPTANCE.md)。

齿轮性能使用 `python scripts/benchmark-gear.py` 单独测量；它保存相同网格的求解状态，随后可用 `--resume --output work/gear-benchmark/repeat` 重测后处理。状态是本机生成的 pickle，只能读取可信的本地文件，不能把下载的 notebook 或任意外部文件作为 `--state`。基准默认使用与桌面一致的 8 核亲和性，保留壁钟与 CPU 时间、网格规模、原生执行记录和输出；JSON 导出不计入计算时间。`--profile` 会产生额外开销，不作为速度比较。不要在编译或其它基准运行期间计时。

构建中断时先看具体错误；[Windows 打包补充](BUILD-NOTES.md) 记录了本机曾遇到的 NSIS 缓存问题，不是普遍安装前提。公开发布另见 [发行准备](RELEASING.md)。
