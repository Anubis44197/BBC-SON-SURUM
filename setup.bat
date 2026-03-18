@echo off
REM BBC v8.3 - One-Command Setup (Windows)
REM Usage (recommended isolated mode):
REM   1) Keep BBC in a central folder (outside projects)
REM   2) cd your-project
REM   3) C:\path\to\BBC\setup.bat [optional-project-path]
REM Backward-compatible embedded usage also works.

echo.
echo ============================================
echo   BBC v8.3 - One-Command Setup
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    echo         https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Detect BBC home path
set "BBC_DIR=%~dp0"
set "BBC_DIR=%BBC_DIR:~0,-1%"

REM Detect project path
if "%~1"=="" (
    set "PROJECT_DIR=%CD%"
) else (
    for %%I in ("%~1") do set "PROJECT_DIR=%%~fI"
)

REM Backward compatibility: if user runs setup from BBC folder itself, use parent as project
if /I "%PROJECT_DIR%"=="%BBC_DIR%" (
    for %%I in ("%BBC_DIR%") do set "PROJECT_DIR=%%~dpI"
    set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
)

echo [BBC] BBC directory:     %BBC_DIR%
echo [BBC] Project directory:  %PROJECT_DIR%
echo.

REM Install dependencies
echo [BBC] Step 1/2: Installing dependencies...
pip install -r "%BBC_DIR%\requirements.txt" -q
if errorlevel 1 (
    echo [WARN] Some dependencies may have failed. Continuing...
) else (
    echo [BBC] Step 1/2: Dependencies installed.
)

echo.

REM Run BBC start on the project
echo [BBC] Step 2/2: Starting BBC on project...
python "%BBC_DIR%\bbc.py" start "%PROJECT_DIR%"

echo.
echo [BBC] Setup complete.
