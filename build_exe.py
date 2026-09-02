#!/usr/bin/env python3
"""Build script for creating standalone VortexDBA.exe executable using PyInstaller."""

import os
import sys
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()

def build_exe():
    print("=" * 65)
    print("   VORTEX DBA - STANDALONE .EXE BUILDER (PYINSTALLER)")
    print("=" * 65)
    print()

    # Verify PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[*] PyInstaller yukleniyor...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    templates_dir = ROOT_DIR / "src" / "templates"
    config_file = ROOT_DIR / "config.yaml"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=VortexDBA",
        f"--add-data={templates_dir}{os.pathsep}src/templates",
        f"--add-data={config_file}{os.pathsep}.",
        "--hidden-import=uvicorn.logging",
        "--hidden-import=uvicorn.loops",
        "--hidden-import=uvicorn.loops.auto",
        "--hidden-import=uvicorn.protocols",
        "--hidden-import=uvicorn.protocols.http",
        "--hidden-import=uvicorn.protocols.http.auto",
        "--hidden-import=uvicorn.protocols.websockets",
        "--hidden-import=uvicorn.protocols.websockets.auto",
        "--hidden-import=uvicorn.lifespan",
        "--hidden-import=uvicorn.lifespan.on",
        "--hidden-import=fastapi",
        "--hidden-import=pymssql",
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=jinja2",
        "--hidden-import=yaml",
        "--hidden-import=clr_loader",
        "--hidden-import=pythonnet",
        str(ROOT_DIR / "app.py"),
    ]

    print("[*] PyInstaller calistiriliyor...")
    print(" ".join(cmd))
    print()

    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode == 0:
        print()
        print("=" * 65)
        print("✔ DERLEME BASARILI!")
        print(f"Masaustu Uygulamasi: {ROOT_DIR / 'dist' / 'VortexDBA' / 'VortexDBA.exe'}")
        print("=" * 65)
    else:
        print()
        print("[HATA] Derleme basarisiz oldu. Hata kodu:", res.returncode)


if __name__ == "__main__":
    build_exe()
