"""Bangla Kor — entry point. Wires all modules together."""
import os
import sys

print("=== BANGLA KOR BOOT ===", flush=True)

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


# ═══════════════════════════════════════════════════════════
# CRITICAL DLL SETUP (before torch import)
#
# Three fixes applied:
#   1. Keep os.add_dll_directory() handles alive in a module-level
#      list — otherwise Python's GC removes the search path.
#   2. Preload torch DLLs using LoadLibraryExW with
#      LOAD_WITH_ALTERED_SEARCH_PATH — Windows searches the DLL's
#      OWN directory for its dependencies. This is THE fix for
#      "shm.dll / torch_cpu.dll not found" on clean Windows.
#   3. Load in dependency-safe order (torch_global_deps first).
# ═══════════════════════════════════════════════════════════
_DLL_DIR_HANDLES = []   # module-level — never let GC collect these

if getattr(sys, "frozen", False):
    _base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    print(f"[BOOT] base={_base}", flush=True)

    _dll_dirs = []
    for _rel in ("torch", "torch/lib", "torch/bin"):
        _p = os.path.join(_base, *_rel.split("/"))
        if os.path.isdir(_p):
            _dll_dirs.append(_p)
            print(f"[BOOT] found: {_p}", flush=True)

    # Method 1: os.add_dll_directory — KEEP HANDLES ALIVE
    for _p in _dll_dirs:
        try:
            _h = os.add_dll_directory(_p)
            _DLL_DIR_HANDLES.append(_h)
        except Exception as _e:
            print(f"[BOOT] add_dll_directory FAIL: {_p} → {_e}", flush=True)

    # Method 2: PATH fallback
    if _dll_dirs:
        os.environ["PATH"] = (
            os.pathsep.join(_dll_dirs)
            + os.pathsep
            + os.environ.get("PATH", "")
        )

    # Method 3: preload torch DLLs with LOAD_WITH_ALTERED_SEARCH_PATH
    _torch_lib = os.path.join(_base, "torch", "lib")
    if os.path.isdir(_torch_lib):
        try:
            import ctypes
            from ctypes import wintypes

            _LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008

            _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            _kernel32.LoadLibraryExW.argtypes = [
                wintypes.LPCWSTR,
                wintypes.HANDLE,
                wintypes.DWORD,
            ]
            _kernel32.LoadLibraryExW.restype = wintypes.HMODULE

            _preload_order = [
                "torch_global_deps.dll",
                "c10.dll",
                "libiomp5md.dll",
                "libiompstubs5md.dll",
                "uv.dll",
                "torch_cpu.dll",
                "shm.dll",
                "torch.dll",
                "torch_python.dll",
            ]
            for _f in sorted(os.listdir(_torch_lib)):
                if _f.lower().endswith(".dll") and _f not in _preload_order:
                    _preload_order.append(_f)

            for _name in _preload_order:
                _pre = os.path.join(_torch_lib, _name)
                if not os.path.isfile(_pre):
                    continue
                _h = _kernel32.LoadLibraryExW(
                    _pre, None, _LOAD_WITH_ALTERED_SEARCH_PATH
                )
                if _h:
                    print(f"[BOOT] loaded {_name} (altered path)", flush=True)
                else:
                    _err = ctypes.get_last_error()
                    print(f"[BOOT] skip {_name}: err={_err}", flush=True)
        except Exception as _e:
            print(f"[BOOT] preload section error: {_e}", flush=True)

    print(f"[BOOT] kept {len(_DLL_DIR_HANDLES)} DLL dir handles alive", flush=True)
    print("[BOOT] DLL setup complete", flush=True)
else:
    print("[BOOT] running from source", flush=True)


# ═══════════════════════════════════════════════════════════
# Warnings cleanup
# ═══════════════════════════════════════════════════════════
import warnings
warnings.filterwarnings(
    "ignore",
    message=r"The PyTorch API of nested tensors.*",
)


# ═══════════════════════════════════════════════════════════
# Standard library
# ═══════════════════════════════════════════════════════════
import threading
import time

import tkinter as tk
import customtkinter as ctk


# ═══════════════════════════════════════════════════════════
# Application imports
# ═══════════════════════════════════════════════════════════
from config import MAX_INPUT_CHARS, STARTUP_MODE
from platform_win.api import user32, get_mouse_position
from platform_win.hotkey import register_hotkey, unregister_hotkey
from platform_win.input import (
    select_all_and_copy, replace_selected_text, send_keys,
)
from platform_win.single_instance import (
    acquire_single_instance, release_single_instance,
)
from core.model import (
    load_local_model, convert_full_text, clean_model_output,
    contains_convertible_text,
)
import state
from state import (
    busy_lock, status_queue, ui_queue, stop_event, set_status,
)
from ui.toast import StatusToast
from ui.window import show_main_window, process_ui_queue
from ui.tray import SystemTray


# ═══════════════════════════════════════════════════════════
# Status queue → toast
# ═══════════════════════════════════════════════════════════
def process_status_queue(toast):
    try:
        while True:
            message, duration_ms, anchor, kind = status_queue.get_nowait()
            toast.show(message, duration_ms, anchor, kind)
    except Exception:
        pass

    if not stop_event.is_set():
        try:
            toast.root.after(40, process_status_queue, toast)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# Conversion worker
# ═══════════════════════════════════════════════════════════
def convert_current_input(original_hwnd, status_anchor):
    try:
        set_status("Selecting input", 5000, status_anchor, "working")
        original_text = select_all_and_copy()

        if not original_text.strip():
            send_keys("{RIGHT}", delay=0.05)
            set_status("No text found", 2200, status_anchor, "warning")
            return

        input_length = len(original_text)
        print(f"\nInput length: {input_length} characters")

        if input_length > MAX_INPUT_CHARS:
            print("Input is too large.")
            set_status("Text too long • Use a shorter input", 3500,
                       status_anchor, "warning")
            return

        print("[Hotkey] full input")
        print(f"Input: {original_text!r}")

        if not contains_convertible_text(original_text):
            print("No Banglish detected.")
            send_keys("{RIGHT}", delay=0.05)
            set_status("No Banglish text found", 2200, status_anchor, "warning")
            return

        set_status("Converting offline", 30000, status_anchor, "working")
        print("Smart conversion with local model...")

        converted_text = clean_model_output(convert_full_text(original_text))

        if not converted_text.strip():
            raise RuntimeError("Conversion returned empty text.")

        if converted_text == original_text:
            print("Conversion produced no change.")
            send_keys("{RIGHT}", delay=0.05)
            set_status("Nothing to convert", 2200, status_anchor, "warning")
            return

        print(f"\nConverted: {converted_text!r}")
        set_status("Replacing text", 5000, status_anchor, "working")
        replace_selected_text(converted_text, original_hwnd)
        print("Replacement completed.")
        set_status("Converted successfully", 1800, status_anchor, "success")

    except Exception as e:
        print(f"\nERROR:\n{repr(e)}")
        set_status("Conversion failed • Original text kept", 4000,
                   status_anchor, "error")
    finally:
        try:
            busy_lock.release()
        except RuntimeError:
            pass


def start_conversion():
    if not busy_lock.acquire(blocking=False):
        set_status("Already converting", 1600, None, "warning")
        return

    original_hwnd = user32.GetForegroundWindow()
    status_anchor = get_mouse_position()

    worker = threading.Thread(
        target=convert_current_input,
        args=(original_hwnd, status_anchor),
        daemon=True,
    )
    worker.start()


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════
def _watch_stop():
    if stop_event.is_set():
        try:
            state.root.quit()
        except Exception:
            pass
        return
    try:
        state.root.after(100, _watch_stop)
    except Exception:
        pass


def _show_error_dialog(title, message):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        pass


def main():
    if not acquire_single_instance():
        print("Bangla Kor is already running.")
        return

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    state.root = root
    root.withdraw()

    toast = StatusToast(root)
    root.after(40, process_status_queue, toast)
    root.after(80, process_ui_queue)

    set_status("Loading local AI", 60000, None, "working")
    try:
        load_local_model()
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"\nModel loading failed.\nError: {e}\n\n{tb}", flush=True)

        _show_error_dialog(
            "Bangla Kor - Model Load Error",
            f"Bangla Kor failed to load the local model.\n\n"
            f"Error: {e}\n\n"
            f"Full traceback:\n{tb[:2000]}",
        )

        set_status("Local AI failed to load", 5000, None, "error")
        try:
            root.update()
            time.sleep(2)
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        release_single_instance()
        return

    set_status("Local AI ready", 2200, None, "success")

    try:
        register_hotkey(start_conversion)
    except Exception as e:
        print(f"\nHotkey registration failed.\nError: {e}", flush=True)
        set_status("Hotkey registration failed", 5000, None, "error")
        try:
            root.update()
            time.sleep(2)
        except Exception:
            pass
        try:
            toast.close()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        release_single_instance()
        return

    try:
        state.TRAY = SystemTray(
            exit_callback=lambda: stop_event.set(),
            open_callback=lambda: ui_queue.put("show"),
        )
        state.TRAY.start()
    except Exception as e:
        state.TRAY = None
        print(f"\nSystem tray failed to start.\nError: {e}", flush=True)
        set_status("Tray failed • App still running", 3000, None, "warning")

    if not STARTUP_MODE:
        show_main_window()

    print("\n" + "=" * 60, flush=True)
    print("Bangla Kor", flush=True)
    print("=" * 60, flush=True)
    print("\nAI Engine: Local", flush=True)
    print("Mode: 100% Offline", flush=True)
    print("\nCtrl + Shift + B", flush=True)
    print("-> Convert all Banglish text in the focused input", flush=True)
    print(f"\nMax input: {MAX_INPUT_CHARS} characters", flush=True)
    print("=" * 60, flush=True)

    root.after(100, _watch_stop)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nStopping Bangla Kor...", flush=True)
    finally:
        stop_event.set()
        unregister_hotkey()
        if state.TRAY:
            try:
                state.TRAY.stop()
            except Exception:
                pass
        try:
            toast.close()
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        release_single_instance()
        print("Bangla Kor stopped.", flush=True)


if __name__ == "__main__":
    main()