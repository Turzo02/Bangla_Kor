"""Status HUD — premium floating toast near cursor."""
import tkinter as tk

import customtkinter as ctk

from config import (
    GWL_EXSTYLE, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE, WS_EX_APPWINDOW,
    SWP_NOACTIVATE, SWP_SHOWWINDOW, HWND_TOPMOST,
)
from platform_win.api import user32


class StatusToast:
    # ── geometry ─────────────────────────────────────────────
    WIDTH = 380
    HEIGHT = 64

    # ── palette ──────────────────────────────────────────────
    BG_OUTER = "#07090D"        # window bg
    CARD_BG = "#0C1016"         # card body
    CARD_BORDER = "#1A2130"
    TRACK = "#151A23"

    TEXT = "#F2F5FA"
    TEXT_SOFT = "#9AA4B5"

    # state colors (bright accent + deep bg + border)
    WORKING_ACCENT = "#7DD3FC"       # sky
    WORKING_BG = "#0B2030"
    WORKING_BORDER = "#1E4258"

    SUCCESS_ACCENT = "#6EE7B7"       # emerald
    SUCCESS_BG = "#0B2219"
    SUCCESS_BORDER = "#1E4534"

    ERROR_ACCENT = "#FCA5A5"         # rose
    ERROR_BG = "#261117"
    ERROR_BORDER = "#552A34"

    WARN_ACCENT = "#FCD34D"          # amber
    WARN_BG = "#221A0A"
    WARN_BORDER = "#4D3D18"

    SPINNER_FRAMES = ("◜", "◝", "◞", "◟")

    # ─────────────────────────────────────────────────────────
    def __init__(self, root_window):
        self.root = root_window

        self.window = tk.Toplevel(self.root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.attributes("-topmost", True)
        self.window.configure(bg=self.BG_OUTER)
        self.window.resizable(False, False)

        # ── Card ─────────────────────────────────────────────
        self.card = ctk.CTkFrame(
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT,
            corner_radius=18,
            fg_color=self.CARD_BG,
            border_width=1,
            border_color=self.CARD_BORDER,
        )
        self.card.pack(fill="both", expand=True)
        self.card.pack_propagate(False)

        # ── Icon square (double-layer for depth) ─────────────
        self.icon_outer = ctk.CTkFrame(
            self.card,
            width=38,
            height=38,
            corner_radius=11,
            fg_color=self.WORKING_BG,
            border_width=1,
            border_color=self.WORKING_BORDER,
        )
        self.icon_outer.place(x=13, y=13)
        self.icon_outer.pack_propagate(False)

        self.icon_label = ctk.CTkLabel(
            self.icon_outer,
            text="✦",
            font=ctk.CTkFont(family="Segoe UI Symbol", size=14, weight="bold"),
            text_color=self.WORKING_ACCENT,
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # ── Message (main text) ──────────────────────────────
        self.message_label = ctk.CTkLabel(
            self.card,
            text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.TEXT,
            anchor="w",
        )
        self.message_label.place(x=64, y=23)

        # ── Right indicator (spinner / static) ───────────────
        self.indicator = ctk.CTkLabel(
            self.card,
            text="",
            font=ctk.CTkFont(family="Segoe UI Symbol", size=14, weight="bold"),
            text_color=self.WORKING_ACCENT,
        )
        self.indicator.place(x=self.WIDTH - 26, y=23)

        # ── Bottom progress strip (2px, flush) ───────────────
        self.progress = ctk.CTkProgressBar(
            self.card,
            width=self.WIDTH - 36,
            height=2,
            corner_radius=2,
            fg_color=self.TRACK,
            progress_color=self.WORKING_ACCENT,
            mode="indeterminate",
        )
        self.progress.place(x=18, y=self.HEIGHT - 9)

        self.window.update_idletasks()

        # ── Native Windows tweaks ────────────────────────────
        try:
            self.hwnd = self.window.winfo_id()
        except Exception:
            self.hwnd = None

        if self.hwnd:
            try:
                ex_style = user32.GetWindowLongPtrW(self.hwnd, GWL_EXSTYLE)
                ex_style |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
                ex_style &= ~WS_EX_APPWINDOW
                user32.SetWindowLongPtrW(self.hwnd, GWL_EXSTYLE, ex_style)
            except Exception:
                pass

        # ── Runtime state ────────────────────────────────────
        self.hide_after_id = None
        self.animation_id = None
        self.spinner_index = 0
        self.current_kind = "working"
        self.closed = False

    # ─────────────────────────────────────────────────────────
    # Internals
    # ─────────────────────────────────────────────────────────
    def _alive(self):
        if self.closed:
            return False
        try:
            return bool(self.window.winfo_exists()) and bool(self.card.winfo_exists())
        except (tk.TclError, RuntimeError):
            return False

    def _fit_message(self, text):
        length = len(text)
        if length <= 26:
            return 13
        if length <= 34:
            return 12
        if length <= 44:
            return 11
        return 10

    # ─────────────────────────────────────────────────────────
    # Animation
    # ─────────────────────────────────────────────────────────
    def start_animation(self):
        self.stop_animation()
        if not self._alive():
            return
        self.spinner_index = 0
        try:
            self.progress.configure(mode="indeterminate")
            try:
                self.progress.configure(indeterminate_speed=0.9)
            except Exception:
                pass
            try:
                self.progress.start()
            except TypeError:
                self.progress.start(0.9)
        except tk.TclError:
            return
        self.animate_spinner()

    def animate_spinner(self):
        if self.current_kind != "working" or not self._alive():
            self.animation_id = None
            return
        try:
            frame = self.SPINNER_FRAMES[self.spinner_index]
            self.indicator.configure(text=frame)
            self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER_FRAMES)
            self.animation_id = self.root.after(120, self.animate_spinner)
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
        except (tk.TclError, RuntimeError):
            pass

    # ─────────────────────────────────────────────────────────
    # State application
    # ─────────────────────────────────────────────────────────
    def apply_state(self, message, kind):
        if not self._alive():
            return
        self.current_kind = kind

        try:
            size = self._fit_message(message)
            self.message_label.configure(
                text=message,
                font=ctk.CTkFont(family="Segoe UI", size=size, weight="bold"),
            )
        except tk.TclError:
            return

        if kind == "working":
            try:
                self.icon_label.configure(text="✦", text_color=self.WORKING_ACCENT)
                self.icon_outer.configure(
                    fg_color=self.WORKING_BG,
                    border_color=self.WORKING_BORDER,
                )
                self.progress.configure(progress_color=self.WORKING_ACCENT)
                self.indicator.configure(text_color=self.WORKING_ACCENT)
                self.start_animation()
            except tk.TclError:
                return

        elif kind == "success":
            self.stop_animation()
            try:
                self.icon_label.configure(text="✓", text_color=self.SUCCESS_ACCENT)
                self.icon_outer.configure(
                    fg_color=self.SUCCESS_BG,
                    border_color=self.SUCCESS_BORDER,
                )
                self.progress.configure(progress_color=self.SUCCESS_ACCENT)
                self.indicator.configure(text="✓", text_color=self.SUCCESS_ACCENT)
            except tk.TclError:
                return

        elif kind == "error":
            self.stop_animation()
            try:
                self.icon_label.configure(text="!", text_color=self.ERROR_ACCENT)
                self.icon_outer.configure(
                    fg_color=self.ERROR_BG,
                    border_color=self.ERROR_BORDER,
                )
                self.progress.configure(progress_color=self.ERROR_ACCENT)
                self.indicator.configure(text="!", text_color=self.ERROR_ACCENT)
            except tk.TclError:
                return

        elif kind == "warning":
            self.stop_animation()
            try:
                self.icon_label.configure(text="!", text_color=self.WARN_ACCENT)
                self.icon_outer.configure(
                    fg_color=self.WARN_BG,
                    border_color=self.WARN_BORDER,
                )
                self.progress.configure(progress_color=self.WARN_ACCENT)
                self.indicator.configure(text="!", text_color=self.WARN_ACCENT)
            except tk.TclError:
                return

    # ─────────────────────────────────────────────────────────
    # Position
    # ─────────────────────────────────────────────────────────
    def _compute_position(self, anchor):
        width, height = self.WIDTH, self.HEIGHT
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        margin = 14

        if anchor:
            mouse_x, mouse_y = anchor
            x = mouse_x + 18
            y = mouse_y - height - 14
            if x + width > sw - margin:
                x = mouse_x - width - 18
            if y < margin:
                y = mouse_y + 20
            if x < margin:
                x = margin
            if x + width > sw - margin:
                x = sw - width - margin
            if y + height > sh - margin:
                y = sh - height - margin
        else:
            x = sw - width - 24
            y = sh - height - 72
        return int(x), int(y)

    # ─────────────────────────────────────────────────────────
    # Show / Hide
    # ─────────────────────────────────────────────────────────
    def show(self, message, duration_ms, anchor, kind):
        if not self._alive():
            return
        try:
            self.apply_state(message, kind)
            x, y = self._compute_position(anchor)

            self.window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")
            self.window.deiconify()
            self.window.lift()

            if self.hwnd:
                user32.SetWindowPos(
                    self.hwnd, HWND_TOPMOST,
                    x, y, self.WIDTH, self.HEIGHT,
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
        for attr in ("animation_id", "hide_after_id"):
            aid = getattr(self, attr, None)
            if aid is not None:
                try:
                    self.root.after_cancel(aid)
                except (tk.TclError, RuntimeError):
                    pass
                setattr(self, attr, None)
        try:
            self.window.destroy()
        except (tk.TclError, RuntimeError):
            pass