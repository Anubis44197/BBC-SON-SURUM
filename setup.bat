@echo off
REM BBC v8.3 - One-Command Setup (Windows)
REM Usage: Clone BBC into your project, then run this script
REM   cd your-project
REM   git clone https://github.com/Anubis44197/BBC.git
REM   BBC\setup.bat

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

REM Detect project path (parent of BBC folder)
set "BBC_DIR=%~dp0"
set "BBC_DIR=%BBC_DIR:~0,-1%"

REM If BBC is inside a project folder, use parent as project path
for %%I in ("%BBC_DIR%") do set "PROJECT_DIR=%%~dpI"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

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
