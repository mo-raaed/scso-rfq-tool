# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for SCSO RFQ Tool.

Build with:
    pyinstaller build.spec

This creates a one-folder distribution in dist/SCSO_RFQ_Tool/
"""

import os
import sys

block_cipher = None

BASE_DIR = os.path.dirname(os.path.abspath(SPEC))

# Find pywin32_system32 folder dynamically
pywin32_sys32_dir = ""
for path in sys.path:
    candidate = os.path.join(path, "pywin32_system32")
    if os.path.isdir(candidate):
        pywin32_sys32_dir = candidate
        break

if not pywin32_sys32_dir:
    pywin32_sys32_dir = os.path.join(
        os.path.dirname(sys.executable), "Lib", "site-packages", "pywin32_system32"
    )

binaries_list = []
if os.path.isdir(pywin32_sys32_dir):
    binaries_list = [
        (os.path.join(pywin32_sys32_dir, "pythoncom312.dll"), "."),
        (os.path.join(pywin32_sys32_dir, "pywintypes312.dll"), "."),
    ]

a = Analysis(
    ['main.py'],
    pathex=[BASE_DIR],
    binaries=binaries_list,
    datas=[
        # Bundle the RFQ template
        (os.path.join('resources', 'SCSO RFQ.docx'), 'resources'),
    ],
    hiddenimports=[
        'models',
        'models.rfq_data',
        'config',
        'config.settings',
        'extractors',
        'extractors.base',
        'extractors.pdf_extractor',
        'extractors.msg_extractor',
        'extractors.xlsx_extractor',
        'extractors.docx_extractor',
        'processors',
        'processors.rfq_builder',
        'gui',
        'gui.app',
        'pdfplumber',
        'extract_msg',
        'docx',
        'openpyxl',
        'fitz',  # PyMuPDF
        'PIL',
        'deep_translator',
        'tkcalendar',
        'babel',
        'babel.numbers',
        'docx2pdf',
        'win32com',
        'win32com.client',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SCSO RFQ Tool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,        # Windowed app — no console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='resources/icon.ico',  # Uncomment when icon is ready
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SCSO_RFQ_Tool',
)
