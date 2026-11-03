@echo off
setlocal
:scan
if "%~1"=="" goto launch
if /I "%~1"=="--code" goto inline_error
shift /1
goto scan
:inline_error
echo {"ok":false,"error":"Use calix-cli.exe for --code; the Windows batch shell changes expression characters. Alternatively use --file or --stdin.","error_type":"LauncherError"}
exit /b 2
:launch
if exist "%~dp0calix-cli.exe" goto native
if exist "%~dp0backend\calix-service.exe" goto packaged
if exist "%~dp0.venv\Scripts\python.exe" goto source
echo {"ok":false,"error":"Calix calculation runtime is missing"}
exit /b 2
:native
"%~dp0calix-cli.exe" %*
exit /b %errorlevel%
:packaged
"%~dp0backend\calix-service.exe" --cli %*
exit /b %errorlevel%
:source
set "PYTHONPATH=%~dp0;%PYTHONPATH%"
"%~dp0.venv\Scripts\python.exe" -m backend.cli %*
exit /b %errorlevel%
