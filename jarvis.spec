# -*- mode: python ; coding: utf-8 -*-
#
# MARK LIII — PyInstaller spec file
#
# Build command (run from project root with venv active):
#   pyinstaller jarvis.spec --noconfirm
#
# Output: dist\JARVIS\JARVIS.exe  (one-folder bundle)
#         dist\JARVIS_onefile\JARVIS.exe  (single .exe — slower cold-start)
#
# NOTE: The one-folder build (default) is recommended — cold-start is instant
# because nothing needs to be extracted.  The onefile build is included at the
# bottom, commented out.

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)  # project root (where this .spec lives)
VENV = ROOT / "venv" / "Lib" / "site-packages"

# ── Data files to bundle ──────────────────────────────────────────────────────
#
# Tuple format: (source_path_or_glob,  destination_folder_inside_bundle)
#
# • config/         — api_keys.json (pre-filled template) + jarvis.ico
# • core/           — prompt.txt  (system prompt read at runtime)
# • dashboard/      — server.py + static HTML/JS  (served by uvicorn)
# • actions/        — ALL .py files (dynamically imported via importlib)
# • plugins/        — ALL .py files (dynamically imported via importlib)
# • memory/         — Python sources  (imported normally, but listed for safety)
# • _sounddevice_data — PortAudio binaries (sounddevice looks these up by path)

datas = [
    # ── Project source trees that are loaded dynamically ─────────────────
    (str(ROOT / "actions"),               "actions"),
    (str(ROOT / "plugins"),               "plugins"),
    (str(ROOT / "core"),                  "core"),
    (str(ROOT / "memory"),                "memory"),
    (str(ROOT / "config"),                "config"),
    (str(ROOT / "dashboard"),             "dashboard"),

    # ── PortAudio binaries (sounddevice locates these at runtime) ─────────
    (str(VENV / "_sounddevice_data"),     "_sounddevice_data"),
]

# Collect all data files declared by these packages (wheel metadata, etc.)
for pkg in ("google.genai", "google.ai.generativelanguage", "playwright",
            "cv2", "PyQt6", "uvicorn", "fastapi", "cryptography",
            "certifi", "charset_normalizer"):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# ── Hidden imports ────────────────────────────────────────────────────────────
#
# Modules that PyInstaller's static analyser misses because they are:
#   • imported by name string at runtime  (action_loader / plugin_loader)
#   • loaded inside C extensions
#   • optional / platform-specific
#   • deeply nested inside google-genai / grpc

hidden_imports = [
    # ── UI ────────────────────────────────────────────────────────────────
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.sip",

    # ── Audio ─────────────────────────────────────────────────────────────
    "sounddevice",
    "_sounddevice",
    "_sounddevice_data",
    "cffi",
    "_cffi_backend",

    # ── Gemini / Google ───────────────────────────────────────────────────
    "google.genai",
    "google.genai.types",
    "google.genai.live",
    "google.ai.generativelanguage_v1beta",
    "google.api_core",
    "google.api_core.gapic_v1",
    "google.auth",
    "google.auth.transport.requests",
    "google.oauth2",
    "proto",
    "proto.marshal",
    "grpc",
    "grpc.aio",

    # ── Async / networking ────────────────────────────────────────────────
    "asyncio",
    "websockets",
    "websockets.legacy",
    "websockets.server",
    "anyio",
    "anyio._backends._asyncio",
    "anyio._backends._trio",
    "sniffio",

    # ── FastAPI / uvicorn (remote dashboard) ──────────────────────────────
    "fastapi",
    "fastapi.responses",
    "fastapi.staticfiles",
    "uvicorn",
    "uvicorn.main",
    "uvicorn.config",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.staticfiles",
    "starlette.responses",
    "multipart",

    # ── Cryptography / security ───────────────────────────────────────────
    "cryptography",
    "cryptography.hazmat.primitives.ciphers",
    "cryptography.hazmat.primitives.padding",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.backends.openssl",

    # ── Vision ────────────────────────────────────────────────────────────
    "cv2",
    "mss",
    "mss.windows",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",

    # ── Browser automation ────────────────────────────────────────────────
    "playwright",
    "playwright.async_api",
    "playwright.sync_api",
    "playwright._impl._api_types",

    # ── System / automation ───────────────────────────────────────────────
    "psutil",
    "pyautogui",
    "pygetwindow",
    "pyperclip",
    "send2trash",

    # ── Windows-specific ─────────────────────────────────────────────────
    "comtypes",
    "comtypes.client",
    "pycaw",
    "pycaw.pycaw",
    "win10toast",
    "win32api",
    "win32con",
    "win32gui",
    "win32com",
    "win32com.client",
    "win32com.shell",
    "win32com.shell.shell",
    "wmi",
    "pywinauto",
    "pywinauto.application",

    # ── Documents / files ─────────────────────────────────────────────────
    "openpyxl",
    "pptx",
    "pptx.util",
    "youtube_transcript_api",

    # ── Web search ────────────────────────────────────────────────────────
    "duckduckgo_search",
    "bs4",
    "requests",
    "primp",

    # ── Remote dashboard extras ───────────────────────────────────────────
    "qrcode",
    "qrcode.image.pil",
    "google.auth.transport",

    # ── Misc runtime ──────────────────────────────────────────────────────
    "numpy",
    "numpy.core",
    "tinytuya",
    "certifi",
    "charset_normalizer",
    "idna",
    "urllib3",
    "pkg_resources",
    "importlib.util",
    "importlib.metadata",
]

# Pull in every submodule of the dynamically-loaded packages automatically
for pkg in ("uvicorn", "starlette", "fastapi", "google.genai",
            "google.api_core", "google.auth"):
    try:
        hidden_imports += collect_submodules(pkg)
    except Exception:
        pass

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Not needed at runtime — shave ~30 MB off the bundle
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
        "black",
        "mypy",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# ── One-folder EXE (recommended — fast cold start) ───────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,          # binaries go into the COLLECT folder
    name="JARVIS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                       # compress with UPX if installed (optional)
    upx_exclude=[],
    console=False,                  # no black console window — GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "config" / "jarvis.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="JARVIS",                  # → dist/JARVIS/JARVIS.exe
)

# ── Single-file EXE (optional — uncomment to also build a portable .exe) ─────
# Cold-start is slower (~5–10 s) because everything unpacks to %TEMP% first.
#
# exe_onefile = EXE(
#     pyz,
#     a.scripts,
#     a.binaries,
#     a.datas,
#     [],
#     name="JARVIS_portable",
#     debug=False,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     console=False,
#     icon=str(ROOT / "config" / "jarvis.ico"),
# )
