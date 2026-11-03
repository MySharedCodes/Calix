$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
$vs = & $vswhere -latest -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Visual Studio C++ Build Tools are required' }
$cmake = Join-Path $vs 'Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe'
$boost = Join-Path $projectRoot 'tools\boost_1_86_0'
& $cmake -S "$projectRoot\native" -B "$projectRoot\native\build" -G 'Visual Studio 17 2022' -A x64 "-DBOOST_ROOT=$boost"
if ($LASTEXITCODE) { throw 'CMake configuration failed' }
& $cmake --build "$projectRoot\native\build" --config Release --parallel
if ($LASTEXITCODE) { throw 'Native build failed' }
Copy-Item -LiteralPath "$projectRoot\native\build\Release\calix-cli.exe" -Destination "$projectRoot\calix-cli.exe" -Force
