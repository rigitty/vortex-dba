#!/usr/bin/env python3
"""Build script for creating standalone native VortexDBA.exe using PyInstaller and PyQt6."""

import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()

def build_exe():
    print("=" * 65)
    print("   VORTEX DBA - NATIVE STANDALONE .EXE BUILDER (PYQT6)")
    print("=" * 65)
    print()

    # Verify PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] PyInstaller yukleniyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    config_file = ROOT_DIR / "config.yaml"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=VortexDBA",
        f"--add-data={config_file}{os.pathsep}.",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=qtawesome",
        "--hidden-import=pymssql",
        "--hidden-import=yaml",
        str(ROOT_DIR / "app.py"),
    ]

    print("[*] PyInstaller calistiriliyor...")
    print(" ".join(cmd))
    print()

    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode == 0:
        print()
        print("=" * 65)
        print("[OK] DERLEME BASARILI!")
        print(f"Masaustu Uygulamasi: {ROOT_DIR / 'dist' / 'VortexDBA' / 'VortexDBA.exe'}")
        print("=" * 65)
    else:
        print()
        print("[HATA] Derleme basarisiz oldu. Hata kodu:", res.returncode)


if __name__ == "__main__":
    build_exe()
