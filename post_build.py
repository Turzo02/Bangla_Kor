"""Post-build script: copy VC++ runtime DLLs to exe root.

PyInstaller 6.x puts everything in _internal/ folder. Windows
bootloader needs VC++ DLLs next to the exe. This script copies them.
"""
import os
import shutil
import sys

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "dist", "BanglaKor")
INTERNAL = os.path.join(BASE, "_internal")

DLLS = [
    "vcruntime140.dll",
    "vcruntime140_1.dll",
    "vcruntime140_threads.dll",
    "msvcp140.dll",
    "msvcp140_1.dll",
    "msvcp140_2.dll",
    "msvcp140_atomic_wait.dll",
    "concrt140.dll",
]

if not os.path.isdir(BASE):
    print(f"ERROR: {BASE} not found. Run pyinstaller first.")
    sys.exit(1)

print(f"Copying VC++ runtime DLLs to {BASE} ...")
ok = 0
for dll in DLLS:
    src = os.path.join(INTERNAL, dll)
    dst = os.path.join(BASE, dll)
    if os.path.isfile(src):
        shutil.copy2(src, dst)
        print(f"  [OK]   {dll}")
        ok += 1
    else:
        print(f"  [MISS] {dll}")

print(f"\nDone. {ok}/{len(DLLS)} DLLs copied.")