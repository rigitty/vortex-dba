#!/usr/bin/env bash
# VortexDBA - Autonomous AI Index Advisor Starter

echo "======================================================================"
echo "            VORTEX DBA - OTONOM SQL SERVER INDEKS AJANI               "
echo "======================================================================"
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[HATA] Python3 bulunamadı! Lütfen Python 3.10+ yükleyin."
    exit 1
fi

echo "[*] Bağımlılıklar kontrol ediliyor..."
pip install -r requirements.txt > /dev/null 2>&1

echo "[*] VortexDBA Web Dashboard başlatılıyor..."
echo "[*] Adres: http://localhost:8000"
echo ""

python3 src/web_app.py
