@echo off
REM BBC Windows Launcher v8.3
REM Usage: bbc.bat [command] [args]

setlocal

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

if not exist "%SCRIPT_DIR%\bbc.py" (
    echo [ERROR] BBC not found at %SCRIPT_DIR%
    exit /b 1
)

if "%~1"=="" (
    python "%SCRIPT_DIR%\bbc.py" start "%CD%"
    exit /b %errorlevel%
)

set "CMD=%~1"

if /I "%CMD%"=="--help" goto :main_help
if /I "%CMD%"=="-h" goto :main_help

if /I "%CMD%"=="start" goto :path_default
if /I "%CMD%"=="menu" goto :path_default
if /I "%CMD%"=="analyze" goto :path_default
if /I "%CMD%"=="audit" goto :path_default
if /I "%CMD%"=="verify" goto :path_default
if /I "%CMD%"=="purge" goto :path_default
if /I "%CMD%"=="install" goto :path_default
if /I "%CMD%"=="watch" goto :path_default
if /I "%CMD%"=="uninstall" goto :path_default

if /I "%CMD%"=="stop" goto :pass_all
if /I "%CMD%"=="status" goto :pass_all
if /I "%CMD%"=="serve" goto :pass_all

if /I "%CMD%"=="migrate" goto :fallback
if /I "%CMD%"=="agent" goto :fallback
if /I "%CMD%"=="bootstrap" goto :fallback
if /I "%CMD%"=="cleanup" goto :fallback
if /I "%CMD%"=="adaptive" goto :fallback

goto :pass_all

:main_help
python "%SCRIPT_DIR%\bbc.py" --help
exit /b %errorlevel%

:path_default
if "%~2"=="" (
    python "%SCRIPT_DIR%\bbc.py" %CMD% "%CD%"
) else (
    python "%SCRIPT_DIR%\bbc.py" %*
)
exit /b %errorlevel%

:pass_all
python "%SCRIPT_DIR%\bbc.py" %*
exit /b %errorlevel%

:fallback
python "%SCRIPT_DIR%\run_bbc.py" %*
exit /b %errorlevel%
