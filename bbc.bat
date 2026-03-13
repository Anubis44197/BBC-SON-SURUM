@echo off
REM ============================================================
REM  BBC Universal Self-Installing Launcher v8.3
REM  Distribute ONLY this .bat file to end users.
REM  On first run it clones BBC from GitHub into %APPDATA%\BBC\
REM  and installs dependencies automatically.
REM  Subsequent runs start instantly.
REM ============================================================

setlocal enabledelayedexpansion

REM --- CONFIGURATION ---
set "BBC_REPO=https://github.com/Anubis44197/BBC_MASTER_BBCMath.git"
set "BBC_INSTALL_DIR=%APPDATA%\BBC"
set "BBC_HOME=%BBC_INSTALL_DIR%\BBC_MASTER_BBCMath"

REM ============================================================
REM  1. CHECK PYTHON
REM ============================================================
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [BBC] ERROR: Python not found.
    echo  [BBC] Please install Python 3.8+ from https://python.org
    echo  [BBC] During installation, check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM  2. IS BBC INSTALLED? IF NOT, INSTALL IT
REM ============================================================
if not exist "%BBC_HOME%\bbc.py" (
    echo.
    echo  ============================================================
    echo   BBC v8.3 - First-Time Setup
    echo  ============================================================
    echo  [BBC] BBC not found. Downloading from GitHub...
    echo  [BBC] Install target: %BBC_HOME%
    echo.

    REM Check Git
    git --version >nul 2>&1
    if errorlevel 1 (
        echo  [BBC] ERROR: Git not found.
        echo  [BBC] Please install Git from https://git-scm.com
        echo.
        pause
        exit /b 1
    )

    REM Create install directory
    if not exist "%BBC_INSTALL_DIR%" mkdir "%BBC_INSTALL_DIR%"

    REM Clone from GitHub
    echo  [BBC] Cloning: %BBC_REPO%
    git clone --depth=1 "%BBC_REPO%" "%BBC_HOME%"
    if errorlevel 1 (
        echo.
        echo  [BBC] ERROR: Clone failed.
        echo  [BBC] Please check your internet connection and try again.
        echo.
        pause
        exit /b 1
    )

    REM Install dependencies
    echo.
    echo  [BBC] Installing dependencies...
    python -m pip install -r "%BBC_HOME%\requirements.txt" -q
    if errorlevel 1 (
        echo.
        echo  [BBC] ERROR: Dependencies could not be installed.
        echo  [BBC] This may happen if the process was interrupted (Ctrl+C^).
        echo  [BBC] Please run this command again to retry:
        echo.
        echo       bbc.bat
        echo.
        pause
        exit /b 1
    )

    echo.
    echo  ============================================================
    echo   [BBC] Installation complete!
    echo  ============================================================
    echo.
)

REM ============================================================
REM  3. UPDATE COMMAND
REM ============================================================
if /i "%1"=="update" (
    echo  [BBC] Updating BBC...
    cd /d "%BBC_HOME%"
    git fetch origin main
    if !errorlevel! neq 0 (
        echo  [BBC] ERROR: Could not reach GitHub. Check your internet connection.
        exit /b 1
    )
    git reset --hard origin/main
    echo  [BBC] Update complete.
    exit /b 0
)

REM ============================================================
REM  4. ROUTE COMMANDS
REM ============================================================

REM No argument: connect current directory
if "%1"=="" (
    python "%BBC_HOME%\bbc.py" start "%CD%"
    exit /b !errorlevel!
)

REM --- Commands routed to bbc.py ---
if /i "%1"=="start" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" start "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" start %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="stop" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" stop "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" stop %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="status" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" status "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" status %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="menu" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" menu "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" menu %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="serve" (
    python "%BBC_HOME%\bbc.py" serve %2 %3
    exit /b !errorlevel!
)

if /i "%1"=="verify" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" verify "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" verify %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="audit" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" audit "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" audit %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="purge" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" purge "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" purge %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="watch" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" watch "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" watch %2 %3 %4 %5
    )
    exit /b !errorlevel!
)

if /i "%1"=="install" (
    python "%BBC_HOME%\bbc_installer.py" install %2
    exit /b !errorlevel!
)

REM --- Commands routed to run_bbc.py (bootstrap, analyze, inject) ---
python "%BBC_HOME%\run_bbc.py" %*
exit /b %errorlevel%
