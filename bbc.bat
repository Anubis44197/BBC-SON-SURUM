@echo off
REM ============================================================
REM  BBC Universal Self-Installing Launcher v8.3
REM  Kullaniciya SADECE bu .bat dosyasi gider.
REM  Ilk calistirmada GitHub'dan BBC'yi %APPDATA%\BBC\ altina
REM  otomatik indirir ve kurar. Sonraki calismalar aninda baslar.
REM ============================================================

setlocal enabledelayedexpansion

REM --- YAPILANDIRMA ---
set "BBC_REPO=https://github.com/Anubis44197/BBC_MASTER_BBCMath.git"
set "BBC_INSTALL_DIR=%APPDATA%\BBC"
set "BBC_HOME=%BBC_INSTALL_DIR%\BBC_MASTER_BBCMath"

REM ============================================================
REM  1. PYTHON KONTROLU
REM ============================================================
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [BBC] HATA: Python bulunamadi.
    echo  [BBC] Lutfen https://python.org adresinden Python 3.8+ kurun.
    echo.
    pause
    exit /b 1
)

REM ============================================================
REM  2. BBC KURULU MU? DEGILSE YUKLE
REM ============================================================
if not exist "%BBC_HOME%\bbc.py" (
    echo.
    echo  ============================================================
    echo   BBC v8.3 - Ilk Kurulum Basliyor...
    echo  ============================================================
    echo  [BBC] BBC bulunamadi. GitHub'dan indiriliyor...
    echo  [BBC] Hedef: %BBC_HOME%
    echo.

    REM Git kontrolu
    git --version >nul 2>&1
    if errorlevel 1 (
        echo  [BBC] HATA: Git bulunamadi.
        echo  [BBC] Lutfen https://git-scm.com adresinden Git kurun.
        echo  [BBC] Veya BBC klasorunu bu .bat dosyasinin yanina kopyalayin.
        echo.
        pause
        exit /b 1
    )

    REM Kurulum dizinini olustur
    if not exist "%BBC_INSTALL_DIR%" mkdir "%BBC_INSTALL_DIR%"

    REM GitHub'dan klonla
    echo  [BBC] Klonlaniyor: %BBC_REPO%
    git clone --depth=1 "%BBC_REPO%" "%BBC_HOME%"
    if errorlevel 1 (
        echo.
        echo  [BBC] HATA: Klonlama basarisiz oldu.
        echo  [BBC] Internet baglantinizi kontrol edin.
        echo.
        pause
        exit /b 1
    )

    REM Bagimliliklari kur
    echo.
    echo  [BBC] Bagimlilıklar kuruluyor...
    python -m pip install -r "%BBC_HOME%\requirements.txt" -q
    if errorlevel 1 (
        echo  [UYARI] Bazi bagimlıliklar kurulamadi, devam ediliyor...
    )

    echo.
    echo  ============================================================
    echo   [BBC] Kurulum tamamlandi!
    echo  ============================================================
    echo.
)

REM ============================================================
REM  3. GUNCELLEME KONTROLU (--update parametresiyle)
REM ============================================================
if /i "%1"=="update" (
    echo  [BBC] Guncelleniyor...
    cd /d "%BBC_HOME%"
    git pull
    echo  [BBC] Guncelleme tamamlandi.
    exit /b 0
)

REM ============================================================
REM  4. BBC'YI CALISTIR
REM ============================================================
REM Parametre verilmediyse mevcut dizini proje olarak kullan
if "%1"=="" (
    python "%BBC_HOME%\bbc.py" start "%CD%"
    exit /b %errorlevel%
)

if /i "%1"=="start" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" start "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" start %2 %3 %4 %5
    )
    exit /b %errorlevel%
)

if /i "%1"=="menu" (
    if "%2"=="" (
        python "%BBC_HOME%\bbc.py" menu "%CD%"
    ) else (
        python "%BBC_HOME%\bbc.py" menu %2
    )
    exit /b %errorlevel%
)

if /i "%1"=="stop" (
    python "%BBC_HOME%\bbc.py" stop
    exit /b %errorlevel%
)

if /i "%1"=="status" (
    python "%BBC_HOME%\bbc.py" status
    exit /b %errorlevel%
)

if /i "%1"=="install" (
    python "%BBC_HOME%\bbc_installer.py" install %2
    exit /b %errorlevel%
)

REM Diger tum komutlar (analyze, inject, bootstrap, verify, audit...)
python "%BBC_HOME%\run_bbc.py" %*
exit /b %errorlevel%
