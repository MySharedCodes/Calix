$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
& "$projectRoot\scripts\build-service.ps1"
if ($LASTEXITCODE) { throw 'Service build failed' }
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\package-components.py"
if ($LASTEXITCODE) { throw 'Component staging failed' }
if (Test-Path -LiteralPath "$projectRoot\tools\cargo\bin\cargo.exe") {
    $env:RUSTUP_HOME = "$projectRoot\tools\rustup"
    $env:CARGO_HOME = "$projectRoot\tools\cargo"
    $env:PATH = "$env:CARGO_HOME\bin;$env:PATH"
}
cargo.exe fetch --manifest-path "$projectRoot\src-tauri\Cargo.toml" --locked --target x86_64-pc-windows-msvc
if ($LASTEXITCODE) { throw 'Cargo dependency preparation failed' }
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\notices.py"
if ($LASTEXITCODE) { throw 'Third-party notice generation failed' }
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\build-info.py"
if ($LASTEXITCODE) { throw 'Build provenance generation failed' }
npm.cmd run tauri -- build
if ($LASTEXITCODE) { throw 'Desktop build failed' }
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\optional-installer.py"
if ($LASTEXITCODE) { throw 'Optional component installer build failed' }
