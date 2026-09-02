@echo off
title VortexDBA - Desktop Application
color 0b

echo ======================================================================
echo             VORTEX DBA - OTONOM SQL SERVER MASAUSTU UYGULAMASI
echo ======================================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Lutfen Python 3.10+ yukleyin.
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [*] Bagimliliklar kontrol ediliyor...
pip install -r requirements.txt >nul 2>&1

:: Launch Native Desktop Application Window
echo [*] VortexDBA Masaustu Penceresi baslatiliyor...
python app.py
