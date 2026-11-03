$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
& "$projectRoot\.venv\Scripts\python.exe" scripts\package-service.py
if ($LASTEXITCODE) { throw 'Calculation service packaging failed' }
