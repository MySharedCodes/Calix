param([string]$BoostRoot = '', [string]$EigenRoot = '')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$null = New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'tools')
$null = New-Item -ItemType Directory -Force -Path (Join-Path $projectRoot 'work')
if ($BoostRoot) { $env:CALIX_BOOST_ROOT = (Resolve-Path -LiteralPath $BoostRoot).Path }
elseif (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'tools/boost_1_86_0/boost/version.hpp'))) {
    $archive = Join-Path $projectRoot 'work/boost_1_86_0.zip'
    $url = 'https://archives.boost.io/release/1.86.0/source/boost_1_86_0.zip'
    Invoke-WebRequest -Uri $url -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne 'cd20a5694e753683e1dc2ee10e2d1bb11704e65893ebcc6ced234ba68e5d8646') { throw 'Boost archive checksum mismatch' }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $projectRoot 'tools') -Force
}
if ($EigenRoot) { $env:CALIX_EIGEN_ROOT = (Resolve-Path -LiteralPath $EigenRoot).Path }
elseif (-not (Test-Path -LiteralPath (Join-Path $projectRoot 'tools/eigen-3.4.0/Eigen/Core'))) {
    $archive = Join-Path $projectRoot 'work/eigen-3.4.0.zip'
    Invoke-WebRequest -Uri 'https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.zip' -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash -ne 'eba3f3d414d2f8cba2919c78ec6daab08fc71ba2ba4ae502b7e5d4d99fc02cda') { throw 'Eigen archive checksum mismatch' }
    Expand-Archive -LiteralPath $archive -DestinationPath (Join-Path $projectRoot 'tools') -Force
}
& (Join-Path $PSScriptRoot 'build-native.ps1')
if ($LASTEXITCODE) { throw 'Native bootstrap build failed' }
