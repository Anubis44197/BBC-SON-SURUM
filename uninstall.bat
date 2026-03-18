@echo off
REM BBC global uninstaller (clean model)
setlocal

set "BBC_HOME=%~dp0"
if "%BBC_HOME:~-1%"=="\" set "BBC_HOME=%BBC_HOME:~0,-1%"
set "PROJECT_PATH=%~1"

echo [BBC] Global uninstall starting
echo [BBC] BBC_HOME: %BBC_HOME%

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found.
    exit /b 1
)

if not "%PROJECT_PATH%"=="" (
    echo [BBC] Cleaning project traces: %PROJECT_PATH%
    python "%BBC_HOME%\bbc.py" uninstall "%PROJECT_PATH%" --force
)

python -m pip uninstall -y bbc-master bbc

echo [BBC] Global uninstall complete
echo [BBC] You may clear BBC_HOME manually from environment settings if needed.
exit /b 0
