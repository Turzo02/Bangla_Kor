"""Native Windows system tray."""
import ctypes
import os
import threading

from ctypes import wintypes

from config import (
    APP_NAME, ICON_PATH, TRAY_CALLBACK_MESSAGE, WM_DESTROY, WM_RBUTTONUP, WM_QUIT,
    NIM_ADD, NIM_DELETE, NIF_MESSAGE, NIF_ICON, NIF_TIP,
    MF_STRING, MF_SEPARATOR, MF_CHECKED,
    TPM_RIGHTBUTTON, TPM_BOTTOMALIGN, TPM_LEFTALIGN, TPM_RETURNCMD,
    TRAY_MENU_STATUS, TRAY_MENU_SHORTCUT, TRAY_MENU_EXIT, TRAY_MENU_STARTUP,
    TRAY_MENU_OPEN, IMAGE_ICON, LR_LOADFROMFILE, LR_DEFAULTSIZE, WM_NULL,
)
from platform_win.api import (
    user32, kernel32, shell32,
    NOTIFYICONDATAW, TRAY_WNDCLASSW, POINT, get_mouse_position,
)
from platform_win.startup import is_startup_enabled, set_startup_enabled
import state
from state import busy_lock


class SystemTray:
    def __init__(self, exit_callback, open_callback):
        self.exit_callback = exit_callback
        self.open_callback = open_callback
        self.hwnd = None
        self.hinstance = None
        self.thread = None
        self.thread_id = None
        self.ready_event = threading.Event()
        self.stop_event = threading.Event()
        self.icon_added = False
        self.hicon = None
        self._wndproc = None
        self.class_name = f"BanglaKorTrayWindow_{os.getpid()}_{id(self)}"

    def start(self):
        self.thread = threading.Thread(
            target=self._thread_main, name="BanglaKor-Tray", daemon=True,
        )
        self.thread.start()
        if not self.ready_event.wait(timeout=5):
            self.stop_event.set()
            if self.thread_id:
                try:
                    user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
                except Exception:
                    pass
            raise RuntimeError("System tray thread did not become ready.")
        print("System tray: ready")

    def _thread_main(self):
        self.thread_id = kernel32.GetCurrentThreadId()

        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t, ctypes.c_void_p, ctypes.c_uint32,
            ctypes.c_void_p, ctypes.c_void_p,
        )
        self._wndproc = WNDPROC(self._window_proc)
        self.hinstance = kernel32.GetModuleHandleW(None)

        wc = TRAY_WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = ctypes.cast(self._wndproc, ctypes.c_void_p).value
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = self.hinstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = self.class_name

        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error) if error else RuntimeError(
                "Could not register tray window class."
            )

        self.hwnd = user32.CreateWindowExW(
            0, self.class_name, APP_NAME, 0, 0, 0, 0, 0, None, None,
            self.hinstance, None,
        )
        if not self.hwnd:
            user32.UnregisterClassW(self.class_name, self.hinstance)
            error = ctypes.get_last_error()
            raise ctypes.WinError(error) if error else RuntimeError(
                "Could not create tray window."
            )

        try:
            self._add_icon()
            self.ready_event.set()
            msg = wintypes.MSG()
            while not self.stop_event.is_set():
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == -1 or result == 0:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self._delete_icon()
            if self.hwnd:
                try:
                    user32.DestroyWindow(self.hwnd)
                except Exception:
                    pass
                self.hwnd = None
            try:
                user32.UnregisterClassW(self.class_name, self.hinstance)
            except Exception:
                pass

    def _add_icon(self):
        if not os.path.isfile(ICON_PATH):
            raise FileNotFoundError(f"Bangla Kor icon not found: {ICON_PATH}")

        self.hicon = user32.LoadImageW(
            None, ICON_PATH, IMAGE_ICON, 0, 0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )
        if not self.hicon:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error) if error else RuntimeError(
                "Windows could not load bangla-kor-icon.ico."
            )

        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = 1
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        data.uCallbackMessage = TRAY_CALLBACK_MESSAGE
        data.hIcon = self.hicon
        data.szTip = "Bangla Kor • by Turzo"

        result = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data))
        if not result:
            try:
                user32.DestroyIcon(self.hicon)
            except Exception:
                pass
            self.hicon = None
            raise RuntimeError("Windows rejected the Bangla Kor tray icon.")
        self.icon_added = True

    def _delete_icon(self):
        if not self.hwnd or not self.icon_added:
            return
        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        data.hWnd = self.hwnd
        data.uID = 1
        try:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(data))
        except Exception:
            pass
        self.icon_added = False
        if self.hicon:
            try:
                user32.DestroyIcon(self.hicon)
            except Exception:
                pass
            self.hicon = None

    def _window_proc(self, hwnd, msg, wparam, lparam):
        if msg == TRAY_CALLBACK_MESSAGE:
            event = (ctypes.cast(lparam, ctypes.c_void_p).value or 0) & 0xFFFF
            if event == WM_RBUTTONUP:
                try:
                    self._show_menu()
                except Exception as exc:
                    print(f"Tray menu error: {exc}")
                return 0
            return 0
        if msg == WM_DESTROY:
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _show_menu(self):
        menu = user32.CreatePopupMenu()
        if not menu:
            return

        if not state.MODEL_READY:
            status_text = "Status: Loading local AI"
        elif busy_lock.locked():
            status_text = "Status: Converting..."
        else:
            status_text = "Status: Offline • Ready"

        startup_enabled = is_startup_enabled()

        try:
            user32.AppendMenuW(menu, MF_STRING, TRAY_MENU_STATUS, status_text)
            user32.AppendMenuW(menu, MF_STRING, TRAY_MENU_SHORTCUT,
                               "Shortcut: Ctrl + Shift + B")
            user32.AppendMenuW(menu, MF_STRING, TRAY_MENU_OPEN, "Open Bangla Kor")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)

            startup_flags = MF_STRING
            if startup_enabled:
                startup_flags |= MF_CHECKED
            user32.AppendMenuW(menu, startup_flags, TRAY_MENU_STARTUP,
                               "Start with Windows")
            user32.AppendMenuW(menu, MF_SEPARATOR, 0, None)
            user32.AppendMenuW(menu, MF_STRING, TRAY_MENU_EXIT, "Exit")

            point = POINT()
            if not user32.GetCursorPos(ctypes.byref(point)):
                point.x = 0
                point.y = 0

            user32.SetForegroundWindow(self.hwnd)
            command = user32.TrackPopupMenu(
                menu,
                TPM_RIGHTBUTTON | TPM_BOTTOMALIGN | TPM_LEFTALIGN | TPM_RETURNCMD,
                int(point.x), int(point.y), 0, self.hwnd, None,
            )
            command = int(command)

            if command == TRAY_MENU_OPEN:
                self.open_callback()
            elif command == TRAY_MENU_STARTUP:
                new_state = not startup_enabled
                if set_startup_enabled(new_state):
                    message = ("Start with Windows enabled"
                               if new_state else "Start with Windows disabled")
                    print(f"Start with Windows: {'ON' if new_state else 'OFF'}")
                    state.set_status(message, 2200, get_mouse_position(), "success")
                else:
                    state.set_status("Could not change startup setting", 3000,
                                     get_mouse_position(), "error")
            elif command == TRAY_MENU_EXIT:
                self.exit_callback()

            user32.PostMessageW(self.hwnd, WM_NULL, 0, 0)
        finally:
            user32.DestroyMenu(menu)

    def stop(self):
        self.stop_event.set()
        if self.thread_id:
            try:
                user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        if (self.thread and self.thread.is_alive()
                and threading.current_thread() is not self.thread):
            try:
                self.thread.join(timeout=3)
            except Exception:
                pass
        self.thread = None
        print("System tray: stopped")