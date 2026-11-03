$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
& "$projectRoot\scripts\build-service.ps1"
if ($LASTEXITCODE) { throw 'Service build failed' }
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\package-components.py"
if ($LASTEXITCODE) { throw 'Component staging failed' }
$env:RUSTUP_HOME = "$projectRoot\tools\rustup"
$env:CARGO_HOME = "$projectRoot\tools\cargo"
$env:PATH = "$env:CARGO_HOME\bin;$env:PATH"
npm.cmd run tauri -- build
if ($LASTEXITCODE) { throw 'Desktop build failed' }
& "$projectRoot\.venv\Scripts\python.exe" "$projectRoot\scripts\optional-installer.py"
if ($LASTEXITCODE) { throw 'Optional component installer build failed' }
