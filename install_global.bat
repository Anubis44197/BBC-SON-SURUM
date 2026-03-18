@echo off
REM BBC global installer (clean model)
setlocal

set "BBC_HOME=%~dp0"
if "%BBC_HOME:~-1%"=="\" set "BBC_HOME=%BBC_HOME:~0,-1%"

echo [BBC] Global install starting
echo [BBC] BBC_HOME: %BBC_HOME%

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.8+ first.
    exit /b 1
)

python -m pip install -r "%BBC_HOME%\requirements.txt"
if errorlevel 1 exit /b 1

python -m pip install -e "%BBC_HOME%"
if errorlevel 1 exit /b 1

setx BBC_HOME "%BBC_HOME%" >nul
if errorlevel 1 (
    echo [WARN] Could not persist BBC_HOME with setx.
) else (
    echo [BBC] Saved BBC_HOME for future shells.
)

where bbc >nul 2>nul
if errorlevel 1 (
    echo [WARN] 'bbc' command not found in PATH for this shell.
    echo [WARN] Open a new terminal or run:
    echo        python "%BBC_HOME%\bbc.py" --help
) else (
    echo [BBC] CLI check passed: bbc command is available.
)

echo [BBC] Global install complete
echo [BBC] Open a new terminal, then run: bbc --help
exit /b 0
