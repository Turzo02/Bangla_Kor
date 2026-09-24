"""Main welcome window."""
import tkinter as tk

import customtkinter as ctk

from config import APP_NAME, ICON_PATH
from state import stop_event, ui_queue
import state

WELCOME_WIDTH = 560
WELCOME_HEIGHT = 480
UI_BG = "#07090E"
UI_CARD = "#0E131C"
UI_CARD_2 = "#111822"
UI_CARD_3 = "#0B1018"
UI_BORDER = "#202B3B"
UI_BORDER_SOFT = "#182130"
UI_MUTED = "#8995A8"
UI_TEXT = "#F6F8FC"
UI_TEXT_SOFT = "#C4CEDB"
UI_ACCENT = "#8B5CF6"
UI_ACCENT_2 = "#A78BFA"
UI_ACCENT_SOFT = "#21183D"
UI_GREEN = "#34D399"
UI_GREEN_SOFT = "#102A23"
UI_KBD = "#171F2B"


def center_main_window():
    root = state.root
    if root is None:
        return
    try:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = max(0, (sw - WELCOME_WIDTH) // 2)
        y = max(0, (sh - WELCOME_HEIGHT) // 2)
        root.geometry(f"{WELCOME_WIDTH}x{WELCOME_HEIGHT}+{x}+{y}")
    except Exception:
        pass


def hide_main_window():
    root = state.root
    if root is None:
        return
    try:
        root.withdraw()
    except Exception:
        pass


def _clear_root_children():
    root = state.root
    if root is None:
        return
    for widget in root.winfo_children():
        try:
            widget.destroy()
        except Exception:
            pass


def _make_kbd(parent, text, width=46):
    box = ctk.CTkFrame(
        parent, width=width, height=34, corner_radius=9,
        fg_color=UI_KBD, border_width=1, border_color="#2C394C",
    )
    box.pack(side="left", padx=3)
    box.pack_propagate(False)
    ctk.CTkLabel(
        box, text=text,
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=UI_TEXT,
    ).place(relx=0.5, rely=0.5, anchor="center")
    return box


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

    outer = ctk.CTkFrame(root, fg_color=UI_BG, corner_radius=0)
    outer.pack(fill="both", expand=True, padx=14, pady=14)

    card = ctk.CTkFrame(
        outer, corner_radius=24, fg_color=UI_CARD,
        border_width=1, border_color=UI_BORDER,
    )
    card.pack(fill="both", expand=True)

    accent_strip = ctk.CTkFrame(card, height=3, fg_color=UI_ACCENT, corner_radius=3)
    accent_strip.pack(fill="x", padx=24)

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=26, pady=(22, 0))

    logo = ctk.CTkFrame(
        header, width=58, height=58, corner_radius=17,
        fg_color=UI_ACCENT_SOFT, border_width=1, border_color="#38285F",
    )
    logo.pack(side="left")
    logo.pack_propagate(False)
    ctk.CTkLabel(
        logo, text="ক",
        font=ctk.CTkFont(size=30, weight="bold"),
        text_color="#EDE9FE",
    ).place(relx=0.5, rely=0.48, anchor="center")

    brand = ctk.CTkFrame(header, fg_color="transparent")
    brand.pack(side="left", padx=(14, 0), fill="x", expand=True)
    ctk.CTkLabel(
        brand, text="Bangla Kor", anchor="w",
        font=ctk.CTkFont(size=25, weight="bold"), text_color=UI_TEXT,
    ).pack(fill="x")
    ctk.CTkLabel(
        brand, text="Banglish → বাংলা", anchor="w",
        font=ctk.CTkFont(size=11, weight="bold"), text_color=UI_MUTED,
    ).pack(fill="x", pady=(2, 0))

    status = ctk.CTkFrame(
        header, corner_radius=12, fg_color=UI_GREEN_SOFT,
        border_width=1, border_color="#205545",
    )
    status.pack(side="right", anchor="n")
    ctk.CTkLabel(
        status, text="●  OFFLINE",
        font=ctk.CTkFont(size=9, weight="bold"), text_color="#6EE7B7",
    ).pack(padx=11, pady=7)

    ctk.CTkLabel(
        card, text="Type normally. One shortcut turns Banglish into বাংলা.",
        anchor="w", font=ctk.CTkFont(size=11), text_color=UI_TEXT_SOFT,
    ).pack(fill="x", padx=26, pady=(14, 18))

    hero = ctk.CTkFrame(
        card, corner_radius=18, fg_color=UI_CARD_2,
        border_width=1, border_color=UI_BORDER,
    )
    hero.pack(fill="x", padx=26)

    ctk.CTkLabel(
        hero, text="YOUR SHORTCUT",
        font=ctk.CTkFont(size=9, weight="bold"), text_color=UI_MUTED,
    ).pack(pady=(13, 8))

    keys = ctk.CTkFrame(hero, fg_color="transparent")
    keys.pack(pady=(0, 9))
    _make_kbd(keys, "CTRL")
    ctk.CTkLabel(keys, text="+", width=14, font=ctk.CTkFont(size=14, weight="bold"),
                 text_color=UI_MUTED).pack(side="left")
    _make_kbd(keys, "SHIFT", 54)
    ctk.CTkLabel(keys, text="+", width=14, font=ctk.CTkFont(size=14, weight="bold"),
                 text_color=UI_MUTED).pack(side="left")
    _make_kbd(keys, "B", 40)

    ctk.CTkLabel(
        hero, text="Works in the focused text box",
        font=ctk.CTkFont(size=10), text_color=UI_MUTED,
    ).pack(pady=(0, 13))

    guide_title = ctk.CTkFrame(card, fg_color="transparent")
    guide_title.pack(fill="x", padx=26, pady=(17, 7))
    ctk.CTkLabel(
        guide_title, text="HOW TO USE", anchor="w",
        font=ctk.CTkFont(size=9, weight="bold"), text_color=UI_MUTED,
    ).pack(side="left")
    ctk.CTkLabel(
        guide_title, text="100% local • No cloud", anchor="e",
        font=ctk.CTkFont(size=9), text_color="#657287",
    ).pack(side="right")

    steps = ctk.CTkFrame(card, fg_color="transparent")
    steps.pack(fill="x", padx=26)
    step_data = (
        ("01", "Focus a text field", "Click where you want the Bangla text."),
        ("02", "Press Ctrl + Shift + B", "Bangla Kor reads the current text."),
        ("03", "Done", "Converted text replaces the selection."),
    )
    for number, title, desc in step_data:
        row = ctk.CTkFrame(
            steps, height=43, corner_radius=11, fg_color=UI_CARD_3,
            border_width=1, border_color=UI_BORDER_SOFT,
        )
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)
        num = ctk.CTkLabel(
            row, text=number, width=42, height=27, corner_radius=8,
            fg_color=UI_ACCENT_SOFT, text_color=UI_ACCENT_2,
            font=ctk.CTkFont(size=8, weight="bold"),
        )
        num.pack(side="left", padx=(8, 11))
        copy = ctk.CTkFrame(row, fg_color="transparent")
        copy.pack(side="left", fill="both", expand=True, pady=4)
        ctk.CTkLabel(copy, text=title, anchor="w",
                     font=ctk.CTkFont(size=9, weight="bold"), text_color=UI_TEXT).pack(fill="x")
        ctk.CTkLabel(copy, text=desc, anchor="w",
                     font=ctk.CTkFont(size=8), text_color=UI_MUTED).pack(fill="x")

    footer_line = ctk.CTkFrame(card, height=1, fg_color=UI_BORDER)
    footer_line.pack(fill="x", padx=26, pady=(13, 0))

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=26, pady=(9, 14))
    ctk.CTkLabel(
        footer, text="Made with ♥ by Turzo",
        font=ctk.CTkFont(size=10, weight="bold"), text_color="#C4B5FD",
    ).pack(side="left")
    ctk.CTkLabel(
        footer, text="Close this window • Bangla Kor stays in the tray",
        font=ctk.CTkFont(size=8), text_color="#657287",
    ).pack(side="right")


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