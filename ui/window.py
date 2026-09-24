"""Main welcome window — premium minimal edition."""
import tkinter as tk

import customtkinter as ctk

from config import APP_NAME, ICON_PATH
from state import stop_event, ui_queue
import state


# ── geometry ──────────────────────────────────────────────────
WELCOME_WIDTH = 620
WELCOME_HEIGHT = 620

# ── palette ───────────────────────────────────────────────────
UI_BG          = "#07090D"
UI_CARD        = "#0B0F15"
UI_SURFACE     = "#10151D"

UI_LINE        = "#1A1F29"

UI_TEXT        = "#F2F5F9"
UI_TEXT_SOFT   = "#9AA4B3"
UI_TEXT_MUTED  = "#5C6675"
UI_TEXT_DIM    = "#3D4453"

UI_ACCENT      = "#A78BFA"
UI_ACCENT_SOFT = "#1B1436"
UI_ACCENT_LINE = "#2E2354"

UI_GREEN       = "#4ADE80"
UI_GREEN_SOFT  = "#0B1F15"
UI_GREEN_LINE  = "#1A3D2C"


# ══════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════
def center_main_window():
    root = state.root
    if root is None:
        return
    try:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = max(0, (sw - WELCOME_WIDTH) // 2)
        y = max(0, (sh - WELCOME_HEIGHT) // 2 - 20)
        root.geometry(f"{WELCOME_WIDTH}x{WELCOME_HEIGHT}+{x}+{y}")
    except Exception:
        pass


def hide_main_window():
    if state.root is None:
        return
    try:
        state.root.withdraw()
    except Exception:
        pass


def process_ui_queue():
    while True:
        try:
            action = ui_queue.get_nowait()
        except Exception:
            break
        if action == "show":
            show_main_window()

    if state.root is not None and not stop_event.is_set():
        try:
            state.root.after(80, process_ui_queue)
        except Exception:
            pass


def show_main_window():
    if state.root is None:
        return
    try:
        build_main_window()
        center_main_window()
        state.root.deiconify()
        state.root.lift()
        state.root.attributes("-topmost", True)
        state.root.after(250, lambda: state.root.attributes("-topmost", False))
        state.root.after(270, state.root.focus_force)
    except Exception as exc:
        print(f"Main window error: {exc}")


# ══════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════
def _clear_root_children():
    root = state.root
    if root is None:
        return
    for widget in root.winfo_children():
        if isinstance(widget, tk.Toplevel):
            continue
        try:
            widget.destroy()
        except Exception:
            pass


def _divider(parent, padx=28):
    ctk.CTkFrame(
        parent, height=1, fg_color=UI_LINE, corner_radius=0,
    ).pack(fill="x", padx=padx)


def _label(parent, text, *, size=11, weight="normal",
           color=UI_TEXT, anchor="w", family="Segoe UI"):
    return ctk.CTkLabel(
        parent, text=text, anchor=anchor,
        font=ctk.CTkFont(family=family, size=size, weight=weight),
        text_color=color,
    )


# ══════════════════════════════════════════════════════════════
# Build
# ══════════════════════════════════════════════════════════════
def build_main_window():
    root = state.root
    if root is None:
        return

    _clear_root_children()
    root.title(APP_NAME)
    root.configure(fg_color=UI_BG)
    root.geometry(f"{WELCOME_WIDTH}x{WELCOME_HEIGHT}")
    root.minsize(WELCOME_WIDTH, WELCOME_HEIGHT)
    root.maxsize(WELCOME_WIDTH, WELCOME_HEIGHT)
    root.resizable(False, False)

    try:
        root.iconbitmap(ICON_PATH)
    except Exception:
        pass
    try:
        root.protocol("WM_DELETE_WINDOW", hide_main_window)
    except Exception:
        pass

    # ── MAIN CARD ────────────────────────────────────────────
    card = ctk.CTkFrame(
        root,
        corner_radius=22,
        fg_color=UI_CARD,
        border_width=1,
        border_color=UI_LINE,
    )
    card.pack(fill="both", expand=True, padx=14, pady=14)

    # ═══════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════
    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=28, pady=(24, 18))

    # Logo
    logo = ctk.CTkFrame(
        header,
        width=52, height=52,
        corner_radius=14,
        fg_color=UI_ACCENT_SOFT,
        border_width=1,
        border_color=UI_ACCENT_LINE,
    )
    logo.pack(side="left")
    logo.pack_propagate(False)
    ctk.CTkLabel(
        logo, text="ক",
        font=ctk.CTkFont(family="Nirmala UI", size=24, weight="bold"),
        text_color=UI_ACCENT,
    ).place(relx=0.5, rely=0.5, anchor="center")

    brand = ctk.CTkFrame(header, fg_color="transparent")
    brand.pack(side="left", padx=(14, 0), fill="x", expand=True)

    _label(brand, "Bangla Kor",
           size=21, weight="bold", color=UI_TEXT).pack(fill="x")
    _label(brand, "Banglish  →  বাংলা",
           size=10, color=UI_TEXT_MUTED).pack(fill="x", pady=(1, 0))

    # Status pill
    status = ctk.CTkFrame(
        header,
        corner_radius=20,
        fg_color=UI_GREEN_SOFT,
        border_width=1,
        border_color=UI_GREEN_LINE,
    )
    status.pack(side="right", anchor="n", pady=(4, 0))

    inner = ctk.CTkFrame(status, fg_color="transparent")
    inner.pack(padx=11, pady=5)

    ctk.CTkLabel(
        inner, text="●",
        font=ctk.CTkFont(family="Segoe UI", size=7),
        text_color=UI_GREEN,
    ).pack(side="left", padx=(0, 5))

    _label(inner, "OFFLINE",
           size=9, weight="bold", color=UI_GREEN).pack(side="left")

    _divider(card, padx=28)

    # ═══════════════════════════════════════════════════════
    # SHORTCUT SECTION
    # ═══════════════════════════════════════════════════════
    hero = ctk.CTkFrame(card, fg_color="transparent")
    hero.pack(fill="x", padx=28, pady=(20, 20))

    _label(hero, "THE SHORTCUT",
           size=9, weight="bold", color=UI_TEXT_DIM, anchor="center",
           ).pack(fill="x")

    keys_row = ctk.CTkFrame(hero, fg_color="transparent")
    keys_row.pack(fill="x", pady=(14, 0))

    keycaps_inner = ctk.CTkFrame(keys_row, fg_color="transparent")
    keycaps_inner.pack(anchor="center")

    def keycap(parent, text, width=74):
        wrap = ctk.CTkFrame(parent, fg_color="transparent",
                            width=width, height=48)
        wrap.pack(side="left", padx=4)
        wrap.pack_propagate(False)

        ctk.CTkFrame(
            wrap, width=width, height=44,
            corner_radius=11, fg_color="#05070A",
        ).place(x=0, y=4)

        body = ctk.CTkFrame(
            wrap, width=width, height=44,
            corner_radius=11,
            fg_color=UI_SURFACE,
            border_width=1,
            border_color=UI_LINE,
        )
        body.place(x=0, y=0)
        body.pack_propagate(False)

        ctk.CTkLabel(
            body, text=text,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=UI_TEXT,
        ).place(relx=0.5, rely=0.5, anchor="center")

    def plus(parent):
        ctk.CTkLabel(
            parent, text="+",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=UI_TEXT_DIM, width=22,
        ).pack(side="left")

    keycap(keycaps_inner, "Ctrl", 76)
    plus(keycaps_inner)
    keycap(keycaps_inner, "Shift", 80)
    plus(keycaps_inner)
    keycap(keycaps_inner, "B", 54)

    _label(hero, "Works in any focused text field",
           size=10, color=UI_TEXT_MUTED, anchor="center",
           ).pack(fill="x", pady=(14, 0))

    _divider(card, padx=28)

    # ═══════════════════════════════════════════════════════
    # QUICK START
    # ═══════════════════════════════════════════════════════
    steps_wrap = ctk.CTkFrame(card, fg_color="transparent")
    steps_wrap.pack(fill="x", padx=28, pady=(18, 0))

    steps_header = ctk.CTkFrame(steps_wrap, fg_color="transparent")
    steps_header.pack(fill="x", pady=(0, 10))

    _label(steps_header, "QUICK START",
           size=9, weight="bold", color=UI_TEXT_DIM).pack(side="left")

    _label(steps_header, "3 simple steps",
           size=9, color=UI_TEXT_DIM, anchor="e").pack(side="right")

    def step_row(parent, num, title, desc):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=5)

        badge = ctk.CTkFrame(
            row, width=24, height=24,
            corner_radius=12,
            fg_color="transparent",
            border_width=1,
            border_color=UI_LINE,
        )
        badge.pack(side="left", pady=(1, 0))
        badge.pack_propagate(False)
        ctk.CTkLabel(
            badge, text=num,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=UI_TEXT_SOFT,
        ).place(relx=0.5, rely=0.5, anchor="center")

        txt = ctk.CTkFrame(row, fg_color="transparent")
        txt.pack(side="left", fill="x", expand=True, padx=(12, 0))

        _label(txt, title, size=11, weight="bold", color=UI_TEXT).pack(fill="x")
        _label(txt, desc, size=9, color=UI_TEXT_MUTED).pack(fill="x", pady=(1, 0))

    step_row(steps_wrap, "1", "Click any text field",
             "Place the cursor where you want Bangla text")
    step_row(steps_wrap, "2", "Type Banglish naturally",
             "Example:  ami bhalo achi, tumi kemon acho?")
    step_row(steps_wrap, "3", "Press Ctrl + Shift + B",
             "Bangla Kor replaces it instantly")

    # ═══════════════════════════════════════════════════════
    # FOOTER — pinned to bottom
    # ═══════════════════════════════════════════════════════
    # Spacer pushes footer down
    spacer = ctk.CTkFrame(card, fg_color="transparent", height=10)
    spacer.pack(fill="x", pady=(12, 0))

    _divider(card, padx=28)

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=28, pady=(12, 16))

    left = ctk.CTkFrame(footer, fg_color="transparent")
    left.pack(side="left")

    _label(left, "v1.0.1",
           size=9, weight="bold", color=UI_TEXT_SOFT).pack(side="left")
    _label(left, "·",
           size=9, color=UI_TEXT_DIM).pack(side="left", padx=6)
    _label(left, "100% offline",
           size=9, color=UI_TEXT_MUTED).pack(side="left")

    _label(footer, "Made with Love by Turzo",
           size=9, color=UI_TEXT_MUTED, anchor="e").pack(side="right")