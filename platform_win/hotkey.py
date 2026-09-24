"""Global hotkey — runs on its own thread with its own message pump.

RegisterHotKey(None, ...) binds the hotkey to the *calling thread*.
That's why we register + pump messages on a dedicated thread, not on
the tkinter main thread. This avoids GIL corruption when the user
drags the UI window.
"""
import ctypes
import threading
from ctypes import wintypes

from config import (
    HOTKEY_ID, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT, VK_B, WM_HOTKEY,
)
from platform_win.api import user32, kernel32

WM_QUIT = 0x0012

_hotkey_thread = None
_hotkey_thread_id = None
_hotkey_thread_ready = threading.Event()
_hotkey_result = [False]


def _hotkey_thread_main(callback):
    global _hotkey_thread_id

    _hotkey_thread_id = kernel32.GetCurrentThreadId()

    success = user32.RegisterHotKey(
        None,
        HOTKEY_ID,
        MOD_CONTROL | MOD_SHIFT | MOD_NOREPEAT,
        VK_B,
    )
    _hotkey_result[0] = bool(success)
    _hotkey_thread_ready.set()

    if not success:
        return

    msg = wintypes.MSG()
    while True:
        result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if result == -1 or result == 0:
            break
        if msg.message == WM_HOTKEY and int(msg.wParam) == HOTKEY_ID:
            try:
                callback()
            except Exception as exc:
                print(f"Hotkey callback error: {exc}")
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    try:
        user32.UnregisterHotKey(None, HOTKEY_ID)
    except Exception:
        pass


def register_hotkey(callback):
    """Start a dedicated hotkey thread. Raises RuntimeError on failure."""
    global _hotkey_thread

    _hotkey_result[0] = False
    _hotkey_thread_ready.clear()

    _hotkey_thread = threading.Thread(
        target=_hotkey_thread_main,
        args=(callback,),
        name="BanglaKor-Hotkey",
        daemon=True,
    )
    _hotkey_thread.start()

    if not _hotkey_thread_ready.wait(timeout=3):
        raise RuntimeError("Hotkey thread did not start in time.")

    if not _hotkey_result[0]:
        error = ctypes.get_last_error()
        if error:
            raise ctypes.WinError(error)
        raise RuntimeError(
            "Could not register Ctrl + Shift + B "
            "(another app may already use it)."
        )


def unregister_hotkey():
    """Signal the hotkey thread to exit cleanly."""
    if _hotkey_thread_id:
        try:
            user32.PostThreadMessageW(_hotkey_thread_id, WM_QUIT, 0, 0)
        except Exception:
            pass