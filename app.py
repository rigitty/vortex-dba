#!/usr/bin/env python3
"""VortexDBA - Autonomous AI Index Advisor.

Main desktop application entry point.
Run: python app.py
"""

import sys
from pathlib import Path

# Add src to Python path
SRC_DIR = Path(__file__).parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from desktop_app import launch_desktop

if __name__ == "__main__":
    launch_desktop()
