# Build Notes

The development machine uses the Rust toolchain under `D:\Calix\tools` without changing the global Rust installation. Build scripts set `CARGO_HOME`, `RUSTUP_HOME`, and a process-local PATH.

Tauri CLI 2.5.0 has an inconsistent NSIS plugin cache check: the Windows required-file list checks `Plugins/x86-unicode/nsis_tauri_utils.dll`, while extraction puts the plugin in `Plugins/x86-unicode/additional/`. This can trigger a full download on every bundle operation. Both locations were populated with the identical verified plugin in the local Tauri cache. The archive's required `Bin/makensis.exe` path was also checked. No application code was changed to bypass integrity checks.

Verified upstream tools:

- `https://github.com/tauri-apps/binary-releases/releases/download/nsis-3/nsis-3.zip`
- SHA-1, as pinned by Tauri CLI 2.5.0: `057e83c7d82462ec394af76c87d06733605543d4`
- `https://github.com/tauri-apps/nsis-tauri-utils/releases/download/nsis_tauri_utils-v0.4.2/nsis_tauri_utils.dll`
- SHA-1, as pinned by Tauri CLI 2.5.0: `6532DA4545864C6EC95F62F27F2199BFD668560B`

The final desktop and backend also have SHA-256 records in `release/SHA256.json`. A future CLI upgrade should remove the cache workaround after repeating the packaging tests.

PyInstaller emits optional-import warnings for `tzdata` and `pkg_resources`; current calculations do not use either. The packaged service independently passed all 25 shipped example expressions. The Python test client emits one upstream deprecation warning; all tests pass.
