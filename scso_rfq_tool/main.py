#!/usr/bin/env python3
"""
SCSO RFQ Automation Tool
========================
Automates the creation of Request for Quotation documents
from various inquiry file formats.

Launch this file to start the application.
"""

import sys
import os

# Redirect win32com gen_py folder under PyInstaller to avoid read-only or permission crashes
if hasattr(sys, '_MEIPASS'):
    import tempfile
    import win32com
    win32com.__gen_path__ = os.path.join(
        tempfile.gettempdir(),
        f"gen_py_{sys.version_info.major}_{sys.version_info.minor}"
    )
    if not os.path.exists(win32com.__gen_path__):
        try:
            os.makedirs(win32com.__gen_path__)
        except Exception:
            pass

# Ensure the project root is on the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gui.app import run_app


if __name__ == "__main__":
    run_app()
