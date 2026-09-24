"""Bangla Kor — entry point. Wires all modules together."""
import os
import sys
import threading
import time
import warnings

# Console-safe mode for PyInstaller --windowed builds
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

warnings.filterwarnings(
    "ignore",
    message=r"The PyTorch API of nested tensors.*",
)

import tkinter as tk

import customtkinter as ctk

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


# =========================================================
# Status queue → toast
# =========================================================
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


# =========================================================
# Conversion worker
# =========================================================
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


# =========================================================
# Main
# =========================================================
def _watch_stop():
    """Poll the stop_event from inside the tkinter loop."""
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

    # -----------------------------------------------------
    # Load model
    # -----------------------------------------------------
    set_status("Loading local AI", 60000, None, "working")
    try:
        load_local_model()
    except Exception as e:
        set_status("Local AI failed to load", 5000, None, "error")
        print(f"\nModel loading failed.\nError: {e}")
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

    # -----------------------------------------------------
    # Hotkey (own thread)
    # -----------------------------------------------------
    try:
        register_hotkey(start_conversion)
    except Exception as e:
        print(f"\nHotkey registration failed.\nError: {e}")
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

    # -----------------------------------------------------
    # Tray (own thread)
    # -----------------------------------------------------
    try:
        state.TRAY = SystemTray(
            exit_callback=lambda: stop_event.set(),
            open_callback=lambda: ui_queue.put("show"),
        )
        state.TRAY.start()
    except Exception as e:
        state.TRAY = None
        print(f"\nSystem tray failed to start.\nError: {e}")
        set_status("Tray failed • App still running", 3000, None, "warning")

    # -----------------------------------------------------
    # Welcome window
    # -----------------------------------------------------
    if not STARTUP_MODE:
        show_main_window()

    # -----------------------------------------------------
    # Console banner
    # -----------------------------------------------------
    print("\n" + "=" * 60)
    print("Bangla Kor")
    print("=" * 60)
    print("\nAI Engine: Local")
    print("Mode: 100% Offline")
    print("\nCtrl + Shift + B")
    print("-> Convert all Banglish text in the focused input")
    print("\nSmart analyzer:")
    print("- Existing Bangla preserved")
    print("- Pure English preserved")
    print("- Technical words protected")
    print("- URLs / emails / code protected")
    print("- Long text chunked safely")
    print(f"- Max input: {MAX_INPUT_CHARS} characters")
    print("\nGemini API: OFF")
    print("Internet required: NO")
    print("\nRight-click the tray icon for menu • Ctrl + C also stops the app.")
    print("=" * 60)

    # -----------------------------------------------------
    # tkinter mainloop — runs on main thread, owns the
    # Windows message pump for all Tk windows.
    # -----------------------------------------------------
    root.after(100, _watch_stop)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nStopping Bangla Kor...")
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
        print("Hotkey unregistered.")
        print("Bangla Kor stopped.")


if __name__ == "__main__":
    main()