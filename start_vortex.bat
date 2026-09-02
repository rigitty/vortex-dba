@echo off
title VortexDBA - Autonomous AI Index Advisor
color 0b

echo ======================================================================
echo             VORTEX DBA - OTONOM SQL SERVER INDEKS AJANI
echo ======================================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Lutfen Python 3.10+ yukleyin.
    pause
    exit /b 1
)

:: Install dependencies if needed
echo [*] Bagimliliklar kontrol ediliyor...
pip install -r requirements.txt >nul 2>&1

:: Launch Web Dashboard
echo [*] VortexDBA Web Dashboard baslatiliyor...
echo [*] Tarayicinizda aciliyor: http://localhost:8000
echo.

start http://localhost:8000
python src/web_app.py
pause
