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
    logo_file = ROOT_DIR / "logo.svg"
    src_dir = ROOT_DIR / "src"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name=VortexDBA",
        f"--paths={src_dir}",
        f"--paths={ROOT_DIR}",
        f"--add-data={config_file}{os.pathsep}.",
        f"--add-data={logo_file}{os.pathsep}.",
        f"--add-data={src_dir}{os.pathsep}src",
        "--collect-all=qtawesome",
        "--collect-all=PyQt6",
        "--exclude-module=PyQt5",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        "--exclude-module=tkinter",
        "--collect-submodules=gui",
        "--collect-submodules=src",
        "--hidden-import=gui",
        "--hidden-import=gui.main_window",
        "--hidden-import=gui.theme",
        "--hidden-import=gui.workers",
        "--hidden-import=gui.widgets",
        "--hidden-import=gui.dialogs",
        "--hidden-import=gui.widgets.splash_screen",
        "--hidden-import=gui.widgets.stat_card",
        "--hidden-import=gui.widgets.toast",
        "--hidden-import=gui.widgets.quota_stepper",
        "--hidden-import=gui.widgets.theme_toggle",
        "--hidden-import=gui.widgets.fade_overlay",
        "--hidden-import=gui.widgets.lang_toggle",
        "--hidden-import=gui.widgets.performance_table",
        "--hidden-import=gui.dialogs.db_config_dialog",
        "--hidden-import=gui.dialogs.index_drawer_dialog",
        "--hidden-import=src",
        "--hidden-import=src.gui",
        "--hidden-import=src.gui.main_window",
        "--hidden-import=config",
        "--hidden-import=src.config",
        "--hidden-import=db_connection",
        "--hidden-import=src.db_connection",
        "--hidden-import=state_store",
        "--hidden-import=src.state_store",
        "--hidden-import=index_advisor",
        "--hidden-import=src.index_advisor",
        "--hidden-import=query_discovery",
        "--hidden-import=src.query_discovery",
        "--hidden-import=query_analyzer",
        "--hidden-import=src.query_analyzer",
        "--hidden-import=safety_guard",
        "--hidden-import=src.safety_guard",
        "--hidden-import=auto_remediator",
        "--hidden-import=src.auto_remediator",
        "--hidden-import=benchmark",
        "--hidden-import=src.benchmark",
        "--hidden-import=unused_index_detector",
        "--hidden-import=src.unused_index_detector",
        "--hidden-import=i18n",
        "--hidden-import=src.i18n",
        "--hidden-import=pg_stats_reader",
        "--hidden-import=src.pg_stats_reader",
        "--hidden-import=slow_queries",
        "--hidden-import=src.slow_queries",
        "--hidden-import=notification",
        "--hidden-import=src.notification",
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
