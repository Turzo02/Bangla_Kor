"""Status HUD — floating toast notification.

FIX: start_animation() now works with BOTH customtkinter 5.1.x and 5.2.x.
"""
import tkinter as tk

import customtkinter as ctk

from config import GWL_EXSTYLE, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE, WS_EX_APPWINDOW
from config import SWP_NOACTIVATE, SWP_SHOWWINDOW, HWND_TOPMOST
from platform_win.api import user32


class StatusToast:
    WIDTH = 320
    HEIGHT = 78
    BG = "#0F1115"
    BORDER = "#2B303A"
    TEXT_MAIN = "#F5F7FA"
    TEXT_MUTED = "#9298A5"
    CYAN = "#67E8F9"
    GREEN = "#6EE7A3"
    RED = "#FF7180"
    YELLOW = "#FFD166"

    def __init__(self, root_window):
        self.root = root_window
        self.window = ctk.CTkToplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(fg_color=self.BG)

        self.card = ctk.CTkFrame(
            self.window, width=self.WIDTH, height=self.HEIGHT,
            corner_radius=18, fg_color=self.BG,
            border_width=1, border_color=self.BORDER,
        )
        self.card.pack(fill="both", expand=True)
        self.card.pack_propagate(False)

        self.icon_frame = ctk.CTkFrame(
            self.card, width=42, height=42, corner_radius=21,
            fg_color="#171A20", border_width=1, border_color="#252A33",
        )
        self.icon_frame.place(x=15, y=17)
        self.icon_frame.pack_propagate(False)
        self.icon_label = ctk.CTkLabel(
            self.icon_frame, text="✦",
            font=ctk.CTkFont(family="Segoe UI Symbol", size=18, weight="bold"),
            text_color=self.CYAN,
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = ctk.CTkLabel(
            self.card, text="BANGLA KOR",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.TEXT_MUTED, anchor="w",
        )
        self.title_label.place(x=70, y=10)

        self.badge = ctk.CTkLabel(
            self.card, text="● OFFLINE",
            font=ctk.CTkFont(family="Segoe UI", size=8, weight="bold"),
            text_color="#7EE7A7", fg_color="#14251C",
            corner_radius=8, padx=7, pady=3,
        )
        self.badge.place(x=225, y=8)

        self.message_label = ctk.CTkLabel(
            self.card, text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.TEXT_MAIN, anchor="w",
        )
        self.message_label.place(x=70, y=29)

        self.dots_label = ctk.CTkLabel(
            self.card, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.CYAN,
        )
        self.dots_label.place(x=278, y=29)

        self.progress = ctk.CTkProgressBar(
            self.card, width=235, height=3, corner_radius=4,
            fg_color="#22262F", progress_color=self.CYAN,
            mode="indeterminate",
        )
        self.progress.place(x=70, y=63)

        self.bottom_label = ctk.CTkLabel(
            self.card, text="Local AI",
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color="#656C79", anchor="w",
        )
        self.bottom_label.place(x=70, y=66)

        self.window.update_idletasks()

        # FIX: get correct top-level HWND (not the child one)
        try:
            child_hwnd = self.window.winfo_id()
            parent = user32.GetParent(child_hwnd)
            self.hwnd = parent if parent else child_hwnd
        except Exception:
            self.hwnd = self.window.winfo_id()

        try:
            # FIX: use SetWindowLongPtrW for 64-bit safety
            ex_style = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, ex_style)
        except Exception:
            pass

        self.hide_after_id = None
        self.animation_id = None
        self.dot_index = 0
        self.current_kind = "working"
        self.closed = False

    def _alive(self):
        if self.closed:
            return False
        try:
            return bool(self.window.winfo_exists()) and bool(self.card.winfo_exists())
        except (tk.TclError, RuntimeError):
            return False

    def start_animation(self):
        """FIX: works with customtkinter 5.1.x AND 5.2.x."""
        self.stop_animation()
        if not self._alive():
            return
        self.dot_index = 0
        try:
            self.progress.configure(mode="indeterminate")
            # 5.2.x uses configure(); 5.1.x uses start(speed)
            try:
                self.progress.configure(indeterminate_speed=0.7)
            except Exception:
                pass
            try:
                self.progress.start()          # 5.2.x style
            except TypeError:
                self.progress.start(0.7)       # 5.1.x fallback
        except tk.TclError:
            return
        self.animate_dots()

    def animate_dots(self):
        if self.current_kind != "working" or not self._alive():
            self.animation_id = None
            return
        dots = ("", "·", "··", "···")
        try:
            self.dots_label.configure(text=dots[self.dot_index])
            self.dot_index = (self.dot_index + 1) % len(dots)
            self.animation_id = self.root.after(230, self.animate_dots)
        except tk.TclError:
            self.animation_id = None

    def stop_animation(self):
        if self.animation_id is not None:
            try:
                self.root.after_cancel(self.animation_id)
            except (tk.TclError, RuntimeError):
                pass
            self.animation_id = None
        try:
            if self._alive():
                self.progress.stop()
                self.dots_label.configure(text="")
        except (tk.TclError, RuntimeError):
            pass

    def apply_state(self, message, kind):
        if not self._alive():
            return
        self.current_kind = kind
        if kind == "working":
            accent = self.CYAN
            try:
                self.icon_label.configure(text="✦", text_color=accent)
                self.icon_frame.configure(fg_color="#12232A", border_color="#21414A")
                self.badge.configure(text="● OFFLINE", text_color="#7EE7A7", fg_color="#14251C")
                self.message_label.configure(text=message)
                self.progress.configure(progress_color=accent)
                self.start_animation()
            except tk.TclError:
                return
        elif kind == "success":
            accent = self.GREEN
            self.stop_animation()
            try:
                self.icon_label.configure(text="✓", text_color=accent)
                self.icon_frame.configure(fg_color="#14241C", border_color="#28513A")
                self.badge.configure(text="● DONE", text_color=accent, fg_color="#14241C")
                self.message_label.configure(text=message)
            except tk.TclError:
                return
        elif kind == "error":
            accent = self.RED
            self.stop_animation()
            try:
                self.icon_label.configure(text="!", text_color=accent)
                self.icon_frame.configure(fg_color="#28161A", border_color="#563039")
                self.badge.configure(text="● ERROR", text_color=accent, fg_color="#28161A")
                self.message_label.configure(text=message)
            except tk.TclError:
                return
        elif kind == "warning":
            accent = self.YELLOW
            self.stop_animation()
            try:
                self.icon_label.configure(text="!", text_color=accent)
                self.icon_frame.configure(fg_color="#292313", border_color="#554820")
                self.badge.configure(text="● WAIT", text_color=accent, fg_color="#292313")
                self.message_label.configure(text=message)
            except tk.TclError:
                return

    def show(self, message, duration_ms, anchor, kind):
        if not self._alive():
            return
        try:
            self.apply_state(message, kind)
            width, height = self.WIDTH, self.HEIGHT
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            margin = 14

            if anchor:
                mouse_x, mouse_y = anchor
                x = mouse_x + 18
                y = mouse_y - height - 16
                if x + width > screen_width - margin:
                    x = mouse_x - width - 18
                if x < margin:
                    x = margin
                if y < margin:
                    y = mouse_y + 22
                if y + height > screen_height - margin:
                    y = screen_height - height - margin
            else:
                x = screen_width - width - 20
                y = screen_height - height - 70

            self.window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
            self.window.deiconify()
            self.window.lift()
            user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST,
                int(x), int(y), width, height,
                SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )

            if self.hide_after_id is not None:
                try:
                    self.root.after_cancel(self.hide_after_id)
                except (tk.TclError, RuntimeError):
                    pass
                self.hide_after_id = None
            self.hide_after_id = self.root.after(duration_ms, self.hide)
        except (tk.TclError, RuntimeError, OSError) as exc:
            if not self.closed:
                print(f"Status HUD error: {exc}")

    def hide(self):
        if self.closed:
            return
        try:
            if self._alive():
                self.window.withdraw()
        except (tk.TclError, RuntimeError):
            pass
        self.current_kind = "idle"
        self.stop_animation()
        self.hide_after_id = None

    def close(self):
        self.closed = True
        if self.animation_id is not None:
            try:
                self.root.after_cancel(self.animation_id)
            except (tk.TclError, RuntimeError):
                pass
            self.animation_id = None
        if self.hide_after_id is not None:
            try:
                self.root.after_cancel(self.hide_after_id)
            except (tk.TclError, RuntimeError):
                pass
            self.hide_after_id = None
        try:
            self.window.destroy()
        except (tk.TclError, RuntimeError):
            pass