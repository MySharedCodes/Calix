# 许可证、仓库与代码签名

状态日期：2026-11-04。

| 项目 | 当前状态 |
|---|---|
| Calix 自有源码许可证 | GNU General Public License version 3，SPDX：`GPL-3.0-only` |
| GitHub 账号 | [MySharedCodes](https://github.com/MySharedCodes) |
| 公开源码仓库 | [MySharedCodes/Calix](https://github.com/MySharedCodes/Calix) |
| 反馈与安全 | [Issues](https://github.com/MySharedCodes/Calix/issues) / [私密漏洞报告](https://github.com/MySharedCodes/Calix/security/advisories/new) |
| Windows 代码签名 | 当前程序及安装包未签名；签名证书或服务尚未配置 |
| 现有发行文件 | 在本次许可变更之前构建，尚未按新的发行要求重新打包 |

## 许可范围

Copyright (c) 2026 Calix authors.

Calix 自有源码、配套文档和自有示例采用 **GPLv3，仅第 3 版**，不是“第 3 版或任意后续版本”。许可证英文全文见根目录 [LICENSE](../LICENSE)；本页说明不替代许可证正文。npm、Cargo 和 Tauri 元数据使用同一 SPDX 标识，安装包配置也引用该 LICENSE 文件。第三方代码、字体、图像和运行库保留各自的许可证，见[第三方许可审查](LICENSE-REVIEW.md)。

允许使用、研究、修改和再分发 Calix，也允许商业使用及收费分发。分发修改后的受 GPL 覆盖程序时，应按 GPLv3 授权并保留必要声明；分发二进制时，应按许可证第 6 条提供相应源码。源码包括该构建所需的自有代码、接口定义、构建与安装脚本，以及适用的依赖源码和安装信息。仅提供一个通用项目首页或不匹配版本的代码，不足以完成此义务。

Calix 按许可证第 15、16 条在法律允许的范围内不提供担保并限制责任。普通用户用软件生成的笔记、计算结果和图形，不会仅因使用 Calix 而自动变成 GPL；复制项目中的受保护示例内容另按其授权处理。GPL 不授予冒充官方发行版或获得商标背书的权利。

## 第三方运行库与公开发行

目前 PDE 模块会从同一进程动态调用 oneMKL PARDISO，并捆绑 Intel oneMKL / OpenMP 运行库。其独立限制与 GPLv3 组合分发的兼容性尚未解决。目录分离、动态加载和“可选组件”本身不能证明它们只是独立聚合物；保留第三方 notices 也不能替代兼容性判断。

本次没有给 GPL 添加 Intel 链接例外。公开分发组合二进制前，应替换成 GPLv3 兼容的并行求解器与运行库，或者取得足以允许组合分发的授权并明确记录。当前发行检查会将此项列为未完成。现有安装包不能仅通过替换 README 就宣称已完成 GPL 发行准备。

其余依赖也应按实际版本逐项核对。保留第三方许可证、Eigen 等适用源码及 GCC Runtime Library Exception 文本；不能把整个发行目录统一改标成 GPL。

## 仓库地址

公开源码仓库为 [MySharedCodes/Calix](https://github.com/MySharedCodes/Calix)。使用 [Issues](https://github.com/MySharedCodes/Calix/issues) 反馈可复现的问题，通过 [Pull requests](https://github.com/MySharedCodes/Calix/pulls) 参与代码与文档开发。安全漏洞使用[私密报告入口](https://github.com/MySharedCodes/Calix/security/advisories/new)。源码公开不表示现有安装包已满足发行要求；当前没有公开二进制下载。

首次公开内容包括应用源码、测试、构建脚本、文档及项目示例，不包括本机配置、账号凭据、私人笔记、开发运行日志、安装包和第三方运行库二进制。后续提交仍需检查授权、凭据与个人数据，不能仅依赖 `.gitignore`。

公开发行时，给安装包对应的源码建立不可变版本标签，随发行提供同版本源码归档、构建说明、第三方 notices 和 SHA-256 清单。源码归档与安装包应能通过构建记录相互对应。

## Windows 代码签名

当前未配置可信发布者证书。代码签名与 GPL 授权、Git 提交签名是三件不同的事；SHA-256 只能核对文件内容，不能证明发布者身份。自签名证书也不等于受 Windows 信任的公开发行签名。

取得适用于 Authenticode 的证书或签名服务后，按以下顺序发布：

1. 构建并签名 Calix 自有 exe / dll，包括桌面程序、CLI、计算服务和原生内核。保留第三方二进制及其上游签名，不修改它们。
2. 用签名后的文件制作便携版和安装包，再签名最终安装包。定制安装包会重新生成文件，不能只签名先前的 Tauri 安装包。
3. 使用 SHA-256 文件摘要和证书提供方支持的 RFC 3161 时间戳。私钥使用证书存储、硬件令牌或签名服务管理，不提交证书私钥、口令或访问令牌。
4. 验证签名状态、预期发布者和时间戳，再生成最终 SHA-256 清单。签名会改变文件哈希，签名后不能沿用旧清单。

Windows SDK 的 `signtool.exe` 可从证书存储中选取证书进行签名。将示例参数替换为真实配置；若使用云签名或硬件令牌，采用提供方支持的接口：

```powershell
signtool.exe sign /sha1 CERTIFICATE_THUMBPRINT /fd SHA256 /tr RFC3161_TIMESTAMP_URL /td SHA256 .\release\Calix_0.1.28_x64-setup.exe
signtool.exe verify /pa /all /v .\release\Calix_0.1.28_x64-setup.exe
Get-AuthenticodeSignature -LiteralPath .\release\Calix_0.1.28_x64-setup.exe | Format-List Status,SignerCertificate,TimeStamperCertificate
Get-FileHash -LiteralPath .\release\Calix_0.1.28_x64-setup.exe -Algorithm SHA256
```

`/sha1` 选择证书指纹，`/fd SHA256` 才是文件摘要算法。验证必须同时检查证书身份；单独看到 `Valid` 不足以确认是预期发布者。签名不保证 SmartScreen 一定不提示。

完整发行步骤见[公开发行准备](RELEASING.md)。
