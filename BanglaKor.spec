# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Bangla Kor.

Bundles:
  - main.py (entry)
  - local_model/infer.py + model weights
  - bangla-kor-icon.ico
  - customtkinter theme files
  - torch + torch internals
  - VC++ runtime DLLs (incl. vcruntime140_threads.dll) in root + torch/lib
"""
import os
from PyInstaller.utils.hooks import collect_all


# ═══════════════════════════════════════════════════════════
# Paths  (SPECPATH = folder containing this .spec file)
# ═══════════════════════════════════════════════════════════
SPEC_DIR = os.path.abspath(SPECPATH)
LOCAL_MODEL_ROOT = os.path.join(SPEC_DIR, "local_model")
LOCAL_MODEL_WEIGHTS = os.path.join(LOCAL_MODEL_ROOT, "model", "ro2bn_ft")
VC_RUNTIME_DIR = os.path.join(SPEC_DIR, "vc_runtime")

print(f"[SPEC] SPEC_DIR            = {SPEC_DIR}")
print(f"[SPEC] LOCAL_MODEL_WEIGHTS = {LOCAL_MODEL_WEIGHTS}")
print(f"[SPEC] VC_RUNTIME_DIR      = {VC_RUNTIME_DIR}")


# ═══════════════════════════════════════════════════════════
# Datas — files copied verbatim into the bundle
# ═══════════════════════════════════════════════════════════
datas = [
    # App icon
    ("bangla-kor-icon.ico", "."),

    # Model weights + configs (explicit — no __pycache__)
    (os.path.join(LOCAL_MODEL_WEIGHTS, "best_model.pt"),  "local_model/model/ro2bn_ft"),
    (os.path.join(LOCAL_MODEL_WEIGHTS, "config.json"),    "local_model/model/ro2bn_ft"),
    (os.path.join(LOCAL_MODEL_WEIGHTS, "src_vocab.json"), "local_model/model/ro2bn_ft"),
    (os.path.join(LOCAL_MODEL_WEIGHTS, "tgt_vocab.json"), "local_model/model/ro2bn_ft"),
]


# ═══════════════════════════════════════════════════════════
# Binaries — bundle VC++ runtime DLLs in multiple locations
# so both the bootloader and torch can find them.
# NOTE: vcruntime140_threads.dll is REQUIRED by torch_cpu.dll.
# ═══════════════════════════════════════════════════════════
binaries = []

VC_RUNTIME_DLLS = [
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "vcruntime140_threads.dll",       # ← critical for torch_cpu.dll
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll",
    "concrt140.dll",
]

for dll in VC_RUNTIME_DLLS:
    src = os.path.join(VC_RUNTIME_DIR, dll)
    if os.path.isfile(src):
        binaries.append((src, "."))            # root
        binaries.append((src, "torch/lib"))    # next to torch DLLs
        print(f"[SPEC] bundling {dll} (root + torch/lib)")
    else:
        print(f"[SPEC] skipping {dll} (not found)")


# ═══════════════════════════════════════════════════════════
# Hidden imports
# ═══════════════════════════════════════════════════════════
hiddenimports = [
    # ── our own modules ─────────────────────────────────
    "config",
    "state",
    "platform_win",
    "platform_win.api",
    "platform_win.hotkey",
    "platform_win.input",
    "platform_win.startup",
    "platform_win.single_instance",
    "core",
    "core.protect",
    "core.analyzer",
    "core.model",
    "ui",
    "ui.toast",
    "ui.window",
    "ui.tray",

    # ── local_model/infer.py ────────────────────────────
    "infer",

    # ── runtime deps ────────────────────────────────────
    "PIL._tkinter_finder",
    "pyperclip",

    # ── torch internals ─────────────────────────────────
    "torch",
    "torch.nn",
    "torch.nn.functional",
    "torch.jit",
    "torch.fx",
    "torch.onnx",
    "torch.utils",
    "torch.utils.data",
    "torch.serialization",
    "torch.backends",
    "torch.backends.cpu",
    "torch._C",
]


# ═══════════════════════════════════════════════════════════
# customtkinter — collect theme files
# ═══════════════════════════════════════════════════════════
ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")
datas += ctk_datas
binaries += ctk_binaries
hiddenimports += ctk_hidden


# ═══════════════════════════════════════════════════════════
# Analysis
# ═══════════════════════════════════════════════════════════
a = Analysis(
    ["main.py"],
    pathex=[LOCAL_MODEL_ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib", "scipy", "pandas",
        "IPython", "jupyter", "notebook",
        "tkinter.test", "test",
        "torchvision", "torchaudio",
        "PyQt5", "PyQt6", "PySide2", "PySide6",
        "wx", "gi",
        "setuptools", "pip", "distutils",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)


# ═══════════════════════════════════════════════════════════
# EXE
# ═══════════════════════════════════════════════════════════
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BanglaKor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # ← FINAL: no console window in release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="bangla-kor-icon.ico",
)


# ═══════════════════════════════════════════════════════════
# COLLECT
# ═══════════════════════════════════════════════════════════
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BanglaKor",
    contents_directory=".",
)