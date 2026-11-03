# 安装、升级与卸载

## 平台与发行状态

已测试目标为 Windows x64，桌面依赖 Microsoft Edge WebView2。Linux、macOS、ARM64 的桌面发行与完整构建尚未验证，不能从 Tauri 的跨平台能力推断 Calix 已支持这些平台。

公开仓库和开源许可证尚未确定。当前根目录 LICENSE 仍保留应用源码权利。取得维护者提供的发行包后可按本页使用；后续以实际发行页公布的文件和授权为准。

## 安装版

1. 运行 `Calix_0.1.27_x64-setup.exe`。
2. 选择安装目录。安装包自带计算服务与 Python，不需要另装 Python、Node.js。
3. 按需选择组件，安装完成后启动软件，等待计算引擎就绪。
4. 运行[快速上手](GETTING-STARTED.md)中的示例。

| 组件 | 用途 |
|---|---|
| Calix Core | 必选；笔记本、公式、常用符号/数值计算、单位和基本绘图 |
| PDE module | PDE/FEM/flow 和相应数值依赖 |
| Additional languages | 日、法、俄、德、西班牙语；中英文随核心提供 |
| Themes | 黑色、粉色、海洋蓝、森林绿等附加皮肤 |

WebView2 缺失时，安装器可能需要联网获取运行时。组织电脑可由管理员按微软官方说明安装；离线机器应提前准备官方运行时。

本地计算不要求云端账户。安装、依赖下载、外部链接和 Windows 自身网络活动不属于离线计算范围。

## 便携版

解压完整目录，运行 `Calix.exe`。保留相邻 `backend/`、`components/`、`notices/` 和 CLI 文件；只移动 exe 会丢失服务。便携指发行目录可移动，设置和自动保存仍可能写入 Windows 用户配置目录。

## 验证下载

如发行包附有 SHA-256 清单，在 PowerShell 中执行：

```powershell
Get-FileHash .\Calix_0.1.27_x64-setup.exe -Algorithm SHA256
```

与相同发行版公布的哈希比较。哈希不替代发布者身份或数字签名验证。未签名版本可能触发 SmartScreen；先核对来源、文件和维护者说明，不要直接关闭系统防护。

## 升级与数据

升级前结束计算，保存重要笔记并关闭旧版。安装器设计为保留组件与设置，仍应保留磁盘笔记本备份。

- `.cixnb` 是建议扩展名；兼容打开 `.clxnb`、`.calix`。
- `%LOCALAPPDATA%\com.calix.desktop` 含 WebView 工作空间和本地服务发现文件。
- `%APPDATA%\com.calix.desktop\preferences.json` 存放桌面偏好设置。
- 重置 WebView 数据可能丢失未另存为文件的笔记，不应作为第一步排错。

首次默认 CPU Workers 为物理核心数，后续保留用户选择。缺少可选模块时，使用相关功能会提示重新运行安装包并选装。

## 卸载

关闭软件，通过 Windows“已安装的应用”卸载。手动删除用户配置前先导出笔记；磁盘笔记本和另存的 PNG/JSON 由用户管理。

## 源码运行

普通用户不必构建源码。开发者按[开发指南](DEVELOPMENT.md)准备工具链与依赖；本机 `D:\Calix` 不是其他机器的安装要求。
