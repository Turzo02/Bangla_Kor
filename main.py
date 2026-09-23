import ctypes
from ctypes import wintypes
import os
import queue
import re
import subprocess
import sys
import threading
import time
import warnings
import winreg
import tkinter as tk

# =========================================================
# Console-safe mode for Windows windowed builds
# =========================================================
# PyInstaller --windowed/--noconsole builds do not provide a real
# stdout/stderr console stream. The application still contains useful
# print() diagnostics, so redirect missing streams to NUL instead of
# letting print() crash the background app.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import customtkinter as ctk
import pyperclip

# =========================================================
# PyTorch warning cleanup
# =========================================================
warnings.filterwarnings(
    "ignore",
    message=r"The PyTorch API of nested tensors.*",
)

# =========================================================
# Paths
# =========================================================
APP_NAME = "Bangla Kor"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
LOCAL_MODEL_ROOT = os.path.join(
    BASE_DIR,
    "local_model",
)
LOCAL_MODEL_DIR = os.path.join(
    LOCAL_MODEL_ROOT,
    "model",
    "ro2bn_ft",
)
RESOURCE_BASE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
ICON_PATH = os.path.join(
    RESOURCE_BASE_DIR,
    "bangla-kor-icon.ico",
)

# =========================================================
# Local model import
# =========================================================
if not os.path.isdir(
    LOCAL_MODEL_ROOT
):
    raise RuntimeError(
        "local_model folder was not found."
    )
if LOCAL_MODEL_ROOT not in sys.path:
    sys.path.insert(
        0,
        LOCAL_MODEL_ROOT,
    )
from infer import (
    load_model,
    transliterate,
)

# =========================================================
# Hotkey
# =========================================================
HOTKEY_ID = 1
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
VK_B = ord("B")
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
PM_REMOVE = 0x0001

# =========================================================
# System tray
# =========================================================
WM_NULL = 0x0000
WM_DESTROY = 0x0002
WM_RBUTTONUP = 0x0205
WM_LBUTTONUP = 0x0202
WM_APP = 0x8000
TRAY_CALLBACK_MESSAGE = WM_APP + 1

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_GRAYED = 0x00000001
TPM_LEFTALIGN = 0x0000
TPM_BOTTOMALIGN = 0x0020
TPM_RIGHTBUTTON = 0x0002
TPM_RETURNCMD = 0x0100

TRAY_MENU_STATUS = 2001
TRAY_MENU_SHORTCUT = 2002
TRAY_MENU_EXIT = 2003
TRAY_MENU_OPEN = 2005

IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040


# =========================================================
# Window styles
# =========================================================
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040
HWND_TOPMOST = -1

# =========================================================
# Windows API
# =========================================================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

# Explicit ctypes signatures for the APIs we use. This keeps the
# hotkey / cursor code predictable on Python 3.14 and 64-bit Windows.
try:
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
except Exception:
    pass

# =========================================================
# Windows structures
# =========================================================
class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]

try:
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
except Exception:
    pass

try:
    user32.RegisterHotKey.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
    ]
    user32.RegisterHotKey.restype = wintypes.BOOL
    user32.UnregisterHotKey.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
    ]
    user32.UnregisterHotKey.restype = wintypes.BOOL
except Exception:
    pass

try:
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
except Exception:
    pass

# =========================================================
# Cursor helper
# =========================================================
def get_mouse_position():
    """Return the current Windows cursor position as (x, y)."""
    point = POINT()
    if user32.GetCursorPos(ctypes.byref(point)):
        return int(point.x), int(point.y)
    return 0, 0

# =========================================================
# Global state
# =========================================================
busy_lock = threading.Lock()
status_queue = queue.Queue()
ui_queue = queue.Queue()
stop_event = threading.Event()
root = None
LOCAL_MODEL = None
SRC_VOCAB = None
TGT_VOCAB = None
MODEL_CFG = None
MODEL_READY = False
TRAY = None
APP_MUTEX = None

# =========================================================
# Input limits
# =========================================================
MAX_INPUT_CHARS = 20000

# =========================================================
# Smart analyzer - Banglish vocabulary
# =========================================================
# This list is a confidence signal, not the model vocabulary.  Unknown
# Banglish is still handled by the pattern/context rules below.
BANGLISH_COMMON_WORDS = {
    # pronouns / people
    "ami", "amra", "amar", "amader", "amake",
    "tumi", "tomar", "tomake", "tomader",
    "apni", "apnar", "apnake", "apnader",
    "uni", "oder", "ora", "tara", "tar",
    "oita", "oitay", "oitake", "oitar",
    "eita", "eitay", "eitake", "eitar",
    "eta", "etar", "etay", "etake",
    "kire", "kirey", "mama", "vai", "bhai", "bon", "apu", "re",

    # question / common words
    "ki", "kno", "keno", "kivabe", "kmne", "kemon",
    "kothay", "kothai", "kokhon", "kisu", "kichu", "keu",
    "sob", "shob", "shobai", "sobai", "onek", "ekhon",
    "ekhane", "okhane", "sekhaney", "aj", "ajke", "ajk",
    "kalke", "kal", "pore", "porer", "age", "ager",
    "abar", "aro", "kom", "beshi", "khub", "shudhu", "sudhu",

    # verbs / verb forms
    "jabo", "jabe", "jawa", "jai", "jao", "jacchi", "jacci", "jacche",
    "jatchi", "jaitesi", "gechi", "gese", "gesey", "gelo", "giye",
    "aso", "asho", "achi", "acho", "ache", "ase", "nai", "nei",
    "hoy", "hoise", "hobe", "hobo", "hochhe", "hocche", "hoye",
    "kor", "koro", "koren", "korte", "kora", "kore", "korbo", "korbi",
    "korbe", "korben", "kortesi", "kortese", "kortam", "korlam",
    "korchi", "korchhi", "korchhe", "korechi", "koreche",
    "dibo", "dibe", "dibey", "dei", "dao", "day",
    "nibo", "nibe", "nite", "niye", "niyechi", "nei",
    "chai", "chay", "lagbe", "lage", "lagse", "laglo", "dorkar",
    "bolbo", "bolbe", "bolte", "bolo", "bol", "bolsi", "bolse",
    "shune", "shunsi", "shunbo", "dekh", "dekha", "dekhi", "dekho",
    "dekhte", "dekhbo", "dite", "asbo", "asbe", "aschi", "eshe", "eshechi",
    "thakbo", "thakbe", "thak", "thake", "thaka", "thaki", "thako",
    "bujhi", "bujhte", "bujhbo", "bujhbe", "shikhi", "shikbo", "shikhbo",
    "shikhte", "likhi", "likhbo", "likhte", "pori", "porbo", "porte", "porchi",
    "khabo", "kheye", "khete", "ghumabo", "ghumai", "uthbo", "uthi", "boshbo", "boshi",

    # nouns / adjectives / general words
    "valo", "bhalo", "bhalobasha", "bhalobashi", "kharap", "shundor", "sundor",
    "boro", "chhoto", "soto", "notun", "purono", "manush", "mon", "mone",
    "bari", "basay", "basha", "bondhu", "bondhura", "kaj", "kotha", "kothar",
    "somoy", "shomoy", "jinish", "byapar", "bapar", "proshno", "uttor",
    "somossa", "shomossha", "upay", "taka", "din", "rat", "raat", "shokal", "sokal",
    "dupur", "bikal", "boi", "khata", "phone", "mobile", "computer", "file",
    "text", "lekha", "message", "chobi", "pani", "khabar", "ranna", "rastay",
    "room", "ghor", "desh", "bangla", "bangladesh", "ekta", "ekhon",
    "jodi", "tahole", "tokhon", "taile", "tai", "ejonno", "jonno", "sathe",
    "theke", "diye", "niye", "amr", "tmr", "kn", "kmn", "pls", "please", "hmm", "ha",
}

# =========================================================
# Banglish heuristics
# =========================================================
BANGLISH_SUFFIXES = (
    "tese", "tesi", "techi", "tese", "chhi", "chhe", "chi", "che",
    "gechi", "gese", "gesi", "bo", "be", "te", "ta", "ti", "gulo", "gula",
    "der", "lam", "len", "li", "si", "se", "lo", "en",
)

DISTINCTIVE_BANGLISH_PATTERNS = (
    "kh", "bh", "dh", "gh", "ch", "sh", "aa", "oo", "ee",
    "jhi", "jha", "kha", "bhi", "dhi", "tumi", "ami", "amar",
    "tom", "amr", "tmr", "kno", "kmn", "kmne",
)

# A small list of very common English words helps avoid false positives
# when a short English sentence happens to contain a weak phonetic pattern.
COMMON_ENGLISH_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "get", "go",
    "good", "have", "has", "had", "he", "her", "here", "him", "his",
    "how", "i", "if", "in", "is", "it", "its", "just", "like", "me",
    "my", "no", "not", "now", "of", "on", "one", "or", "our", "out",
    "please", "say", "see", "she", "should", "so", "some", "than", "that",
    "the", "their", "them", "there", "these", "they", "this", "to", "too",
    "up", "us", "use", "very", "was", "we", "were", "what", "when", "where",
    "which", "who", "will", "with", "would", "you", "your", "today", "hello",
}

ENGLISH_SUFFIXES = (
    "ing", "tion", "sion", "ment", "ness", "able", "ible", "ous", "ful", "less",
    "ity", "ive", "ize", "ise", "ally", "edly", "ing", "est", "ers", "ly",
)

# =========================================================
# Protected technical / brand words
# =========================================================
PROTECTED_WORDS = [
    "Visual Studio Code",
    "VS Code",
    "ChatGPT",
    "Hugging Face",
    "GitHub",
    "GitLab",
    "Stack Overflow",
    "Google Drive",
    "Google Docs",
    "Google Sheets",
    "Google Chrome",
    "YouTube",
    "Facebook",
    "Instagram",
    "Telegram",
    "Discord",
    "WhatsApp",
    "OpenAI",
    "Gemini",
    "Chrome",
    "Firefox",
    "Edge",
    "GPT",
    "GPT-4",
    "GPT-4o",
    "GPT-5",
    "HTML",
    "CSS",
    "JavaScript",
    "TypeScript",
    "React",
    "ReactJS",
    "Next.js",
    "Node.js",
    "Express",
    "MongoDB",
    "Firebase",
    "Tailwind",
    "Tailwind CSS",
    "DaisyUI",
    "Vite",
    "npm",
    "npx",
    "pnpm",
    "Yarn",
    "Python",
    "Java",
    "Kotlin",
    "Android",
    "Windows",
    "Linux",
    "macOS",
    "API",
    "REST API",
    "JSON",
    "XML",
    "HTTP",
    "HTTPS",
    "URL",
    "SQL",
    "MySQL",
    "PostgreSQL",
    "Redis",
    "Docker",
    "PyTorch",
    "TensorFlow",
    "NumPy",
    "OpenCV",
    "Whisper",
    "Transformer",
    "Transformers",
    "CPU",
    "GPU",
    "AI",
    "ML",
    "NLP",
    "OCR",
    "EXE",
    ".NET",
    "C++",
    "C#",
    "CSSBattle",
    "localhost",
]

PROTECTED_WORDS = sorted(
    PROTECTED_WORDS,
    key=len,
    reverse=True,
)

# =========================================================
# Protected patterns
# =========================================================
PROTECTED_PATTERNS = [
    # URLs
    r"https?://[^\s]+",
    r"www\.[^\s]+",
    # Emails
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    # Inline code
    r"`[^`\r\n]+`",
    # Markdown fenced code blocks
    r"```[\s\S]*?```",
]

for word in PROTECTED_WORDS:
    escaped = re.escape(word)
    PROTECTED_PATTERNS.append(
        rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])"
    )

PROTECTED_PATTERN = re.compile(
    "|".join(
        f"({pattern})"
        for pattern in PROTECTED_PATTERNS
    ),
    re.IGNORECASE,
)

# =========================================================
# Analyzer helpers
# =========================================================
def contains_bengali(text):
    return bool(
        re.search(
            r"[\u0980-\u09FF]",
            text,
        )
    )


def visible_without_protected(text):
    return PROTECTED_PATTERN.sub(
        " ",
        text,
    )


def get_latin_words(text):
    return re.findall(
        r"[A-Za-z]+(?:'[A-Za-z]+)?",
        text.lower(),
    )


def word_banglish_score(word):
    """Return a conservative confidence score for one Latin word."""
    word = word.lower().strip("._'+-")
    if not word:
        return 0, False, False

    if word in BANGLISH_COMMON_WORDS:
        return 4, True, True

    score = 0
    distinctive = any(
        pattern in word
        for pattern in DISTINCTIVE_BANGLISH_PATTERNS
    )
    suffix = any(
        word.endswith(suffix)
        for suffix in BANGLISH_SUFFIXES
        if len(word) >= max(4, len(suffix) + 1)
    )

    if distinctive:
        score += 1
    if suffix:
        score += 2 if len(word) <= 9 else 1

    # Repeated consonants and Bangla-style clusters are useful weak signals.
    if re.search(r"(?:kk|gg|jj|pp|tt|dd|mm|nn|ll|ss)", word):
        score += 1
    if re.search(r"(?:[bcdfghjklmnpqrstvwxyz]{3,})", word):
        score += 1

    for pattern in ("kh", "bh", "dh", "gh", "ch", "sh", "ng", "aa", "ee", "oo"):
        if pattern in word:
            score += 1
            break

    # Strongly English-looking morphology reduces weak accidental matches.
    if len(word) >= 6 and any(
        word.endswith(suffix)
        for suffix in ENGLISH_SUFFIXES
    ):
        score -= 2

    return max(0, min(score, 4)), distinctive, suffix


def banglish_score(text):
    visible = visible_without_protected(text)
    words = get_latin_words(visible)
    if not words:
        return 0

    score = 0
    for word in words:
        current, _distinctive, _suffix = word_banglish_score(word)
        score += current

    return min(score, 12)


def should_convert_line(line):
    """Context-aware Banglish detector.

    The classifier intentionally stays conservative for pure English.  A
    strong Banglish cue can trigger a line by itself; otherwise it expects
    multiple supporting cues or a Bengali+Banglish mix.
    """
    if not line.strip():
        return False

    visible = visible_without_protected(line)
    if not re.search(r"[A-Za-z]", visible):
        return False

    words = get_latin_words(visible)
    if not words:
        return False

    score = 0
    strong_hits = 0
    weak_hits = 0
    distinctive_hits = 0
    suffix_hits = 0
    english_hits = 0

    for word in words:
        if word in COMMON_ENGLISH_WORDS:
            english_hits += 1
            continue

        current, distinctive, suffix = word_banglish_score(word)
        if current > 0:
            score += current
            if current >= 3:
                strong_hits += 1
            else:
                weak_hits += 1
            if distinctive:
                distinctive_hits += 1
            if suffix:
                suffix_hits += 1

    if strong_hits >= 1:
        return True

    if weak_hits >= 2 and score >= 4 and (
        distinctive_hits >= 1 or suffix_hits >= 1
    ):
        return True

    if (
        contains_bengali(line)
        and score >= 2
        and (distinctive_hits >= 1 or suffix_hits >= 1)
    ):
        return True

    # Short lines are held to a higher standard so English is not
    # accidentally transliterated.
    if len(words) <= 2 and english_hits >= len(words) - 1:
        return False

    return False


def split_leading_trailing_space(text):
    leading_match = re.match(
        r"^\s*",
        text,
    )
    trailing_match = re.search(
        r"\s*$",
        text,
    )
    leading = (
        leading_match.group(0)
        if leading_match
        else ""
    )
    trailing = (
        trailing_match.group(0)
        if trailing_match
        else ""
    )
    start = len(leading)
    end = (
        len(text)
        - len(trailing)
    )
    if end < start:
        end = start
    core = text[
        start:end
    ]
    return (
        leading,
        core,
        trailing,
    )

# =========================================================
# Output cleanup
# =========================================================
def clean_model_output(text):
    """Clean unwanted spaces introduced by the model while preserving lines."""
    if not text:
        return ""

    # Normalize horizontal whitespace only.
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text,
    )

    # Remove spaces before punctuation.
    text = re.sub(
        r"[ \t]+([,!?;:])",
        r"\1",
        text,
    )

    # Bengali danda.
    text = re.sub(
        r"[ \t]+।",
        "।",
        text,
    )

    # Bracket spacing.
    text = re.sub(
        r"([([\{])\s+",
        r"\1",
        text,
    )
    text = re.sub(
        r"\s+([)\]}])",
        r"\1",
        text,
    )

    # Keep line structure but remove trailing horizontal whitespace.
    text = re.sub(
        r"[ \t]+(?=\n|$)",
        "",
        text,
    )
    return text.strip()

# =========================================================
# Model chunking
# =========================================================
def get_model_token_limit():
    maxlen = int(
        MODEL_CFG.get(
            "maxlen",
            128,
        )
    )
    return max(
        maxlen - 2,
        8,
    )


def split_into_model_chunks(text):
    """Split long text into safe word-based chunks without truncation."""
    limit = get_model_token_limit()
    words = re.split(r"(\s+)", text)
    if not any(part.strip() for part in words):
        return []

    chunks = []
    current = ""

    def token_count(value):
        try:
            return len(
                SRC_VOCAB.encode(
                    value,
                    maxlen=10000,
                )
            )
        except Exception:
            return len(value)

    for piece in words:
        if not piece:
            continue

        candidate = current + piece
        if current and piece.isspace():
            # Whitespace itself is cheap; keep it while the following word
            # decides whether the chunk still fits.
            current = candidate
            continue

        if not current:
            if token_count(piece) <= limit:
                current = piece
                continue

            # Hard split a single huge token only when unavoidable.
            buffer = ""
            for char in piece:
                trial = buffer + char
                if buffer and token_count(trial) > limit:
                    chunks.append(buffer)
                    buffer = char
                else:
                    buffer = trial
            current = buffer
            continue

        if token_count(candidate) <= limit:
            current = candidate
            continue

        chunks.append(current.rstrip())
        current = piece.lstrip()

    if current.strip():
        chunks.append(current.rstrip())

    return chunks


def convert_model_piece(text):
    """Convert one manageable piece through the local model."""
    if not text.strip():
        return text

    chunks = split_into_model_chunks(text)
    if not chunks:
        return text

    converted_chunks = []
    for chunk in chunks:
        leading, core, trailing = split_leading_trailing_space(chunk)
        if not core:
            continue

        result = transliterate(
            core,
            LOCAL_MODEL,
            SRC_VOCAB,
            TGT_VOCAB,
            "cpu",
            MODEL_CFG,
            reverse=False,
        )
        if result is None:
            raise RuntimeError(
                "Local model returned no result."
            )

        cleaned = clean_model_output(
            str(result)
        )
        converted_chunks.append(
            leading + cleaned + trailing
        )

    return " ".join(
        chunk.strip()
        for chunk in converted_chunks
        if chunk.strip()
    )

# =========================================================
# Convert smart line
# =========================================================
def convert_line_smart(line):
    if not should_convert_line(line):
        return line

    pieces = []
    cursor = 0

    # Protected things + already-Bengali text.
    combined_pattern = re.compile(
        "(" + PROTECTED_PATTERN.pattern + r"|[\u0980-\u09FF]+)",
        re.IGNORECASE,
    )

    for match in combined_pattern.finditer(line):
        gap = line[
            cursor:match.start()
        ]

        if gap:
            leading, core, trailing = split_leading_trailing_space(gap)
            if (
                core
                and re.search(r"[A-Za-z]", core)
            ):
                converted = convert_model_piece(core)
                pieces.append(
                    leading
                    + converted
                    + trailing
                )
            else:
                pieces.append(gap)

        # Preserve protected/Bengali segment exactly.
        pieces.append(
            match.group(0)
        )
        cursor = match.end()

    if cursor < len(line):
        gap = line[cursor:]
        leading, core, trailing = split_leading_trailing_space(gap)
        if (
            core
            and re.search(r"[A-Za-z]", core)
        ):
            converted = convert_model_piece(core)
            pieces.append(
                leading
                + converted
                + trailing
            )
        else:
            pieces.append(gap)

    return clean_model_output(
        "".join(pieces)
    )

# =========================================================
# Full text smart conversion
# =========================================================
def convert_full_text(text):
    """Convert appropriate Banglish while preserving protected content/lines."""
    parts = re.split(
        r"(\r\n|\n|\r)",
        text,
    )
    converted_parts = []

    for part in parts:
        if part in (
            "\r\n",
            "\n",
            "\r",
        ):
            converted_parts.append(part)
            continue

        if not part:
            continue

        converted_parts.append(
            convert_line_smart(part)
        )

    return "".join(
        converted_parts
    )


def contains_convertible_text(text):
    for line in re.split(
        r"\r\n|\n|\r",
        text,
    ):
        if should_convert_line(line):
            return True
    return False

# =========================================================
# Status HUD
# =========================================================
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
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT,
            corner_radius=18,
            fg_color=self.BG,
            border_width=1,
            border_color=self.BORDER,
        )
        self.card.pack(fill="both", expand=True)
        self.card.pack_propagate(False)

        self.icon_frame = ctk.CTkFrame(
            self.card,
            width=42,
            height=42,
            corner_radius=21,
            fg_color="#171A20",
            border_width=1,
            border_color="#252A33",
        )
        self.icon_frame.place(x=15, y=17)
        self.icon_frame.pack_propagate(False)
        self.icon_label = ctk.CTkLabel(
            self.icon_frame,
            text="✦",
            font=ctk.CTkFont(family="Segoe UI Symbol", size=18, weight="bold"),
            text_color=self.CYAN,
        )
        self.icon_label.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = ctk.CTkLabel(
            self.card,
            text="BANGLA KOR",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.TEXT_MUTED,
            anchor="w",
        )
        self.title_label.place(x=70, y=10)

        self.badge = ctk.CTkLabel(
            self.card,
            text="● OFFLINE",
            font=ctk.CTkFont(family="Segoe UI", size=8, weight="bold"),
            text_color="#7EE7A7",
            fg_color="#14251C",
            corner_radius=8,
            padx=7,
            pady=3,
        )
        self.badge.place(x=225, y=8)

        self.message_label = ctk.CTkLabel(
            self.card,
            text="Ready",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.TEXT_MAIN,
            anchor="w",
        )
        self.message_label.place(x=70, y=29)

        self.dots_label = ctk.CTkLabel(
            self.card,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.CYAN,
        )
        self.dots_label.place(x=278, y=29)

        self.progress = ctk.CTkProgressBar(
            self.card,
            width=235,
            height=3,
            corner_radius=4,
            fg_color="#22262F",
            progress_color=self.CYAN,
            mode="indeterminate",
        )
        self.progress.place(x=70, y=63)

        self.bottom_label = ctk.CTkLabel(
            self.card,
            text="Local AI",
            font=ctk.CTkFont(family="Segoe UI", size=8),
            text_color="#656C79",
            anchor="w",
        )
        self.bottom_label.place(x=70, y=66)

        self.window.update_idletasks()
        self.hwnd = self.window.winfo_id()
        try:
            ex_style = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
            ex_style &= ~WS_EX_APPWINDOW
            user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex_style)
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
        self.stop_animation()
        if not self._alive():
            return
        self.dot_index = 0
        try:
            self.progress.configure(mode="indeterminate")
            self.progress.start(0.7)
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
            width = self.WIDTH
            height = self.HEIGHT
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
                self.hwnd,
                HWND_TOPMOST,
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
            # Do not spam the console for a HUD disappearing during shutdown.
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

# =========================================================
# Status system
# =========================================================
def set_status(
    message,
    duration_ms=2500,
    anchor=None,
    kind="working",
):
    status_queue.put(
        (
            message,
            duration_ms,
            anchor,
            kind,
        )
    )


def process_status_queue(
    toast
):
    try:
        while True:
            (
                message,
                duration_ms,
                anchor,
                kind,
            ) = status_queue.get_nowait()
            toast.show(
                message,
                duration_ms,
                anchor,
                kind,
            )
    except queue.Empty:
        pass

    if not stop_event.is_set():
        toast.root.after(
            40,
            process_status_queue,
            toast,
        )

# =========================================================
# PowerShell
# =========================================================
def run_powershell_command(
    command
):
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-WindowStyle",
            "Hidden",
            "-Command",
            command,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        creationflags=(
            getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            )
        ),
    )

# =========================================================
# Send keys
# =========================================================
def send_keys(
    keys,
    delay=0.08,
):
    # PowerShell single-quoted string escape.  Our normal keys contain no
    # apostrophe, but this keeps the helper safe for future use.
    safe_keys = str(keys).replace(
        "'",
        "''",
    )
    command = (
        "$wshell = "
        "New-Object -ComObject "
        "WScript.Shell; "
        f"$wshell.SendKeys('{safe_keys}');"
    )
    run_powershell_command(
        command
    )
    if delay:
        time.sleep(delay)

# =========================================================
# Select all + copy
# =========================================================
def select_all_and_copy():
    # Clear stale clipboard.
    pyperclip.copy("")
    time.sleep(
        0.05
    )

    command = (
        "$wshell = "
        "New-Object -ComObject "
        "WScript.Shell; "
        "$wshell.SendKeys('^a'); "
        "Start-Sleep "
        "-Milliseconds 100; "
        "$wshell.SendKeys('^c');"
    )

    run_powershell_command(
        command
    )

    # Give clipboard time to update.
    time.sleep(
        0.18
    )
    return pyperclip.paste()

# =========================================================
# Replace selected text
# =========================================================
def replace_selected_text(
    converted_text,
    original_hwnd,
):
    pyperclip.copy(
        converted_text
    )
    time.sleep(
        0.12
    )

    if original_hwnd:
        try:
            user32.SetForegroundWindow(
                original_hwnd
            )
        except Exception:
            pass

    time.sleep(
        0.12
    )

    command = (
        "$wshell = "
        "New-Object -ComObject "
        "WScript.Shell; "
        "$wshell.SendKeys('^v');"
    )
    result = run_powershell_command(
        command
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Paste operation failed."
        )

# =========================================================
# Model loading
# =========================================================
def load_local_model():
    global LOCAL_MODEL
    global SRC_VOCAB
    global TGT_VOCAB
    global MODEL_CFG
    global MODEL_READY

    print()
    print(
        "Loading local model..."
    )
    print(
        f"Model path: "
        f"{LOCAL_MODEL_DIR}"
    )

    if not os.path.isdir(
        LOCAL_MODEL_DIR
    ):
        raise FileNotFoundError(
            "Local model directory not found:\n"
            + LOCAL_MODEL_DIR
        )

    (
        LOCAL_MODEL,
        SRC_VOCAB,
        TGT_VOCAB,
        MODEL_CFG,
    ) = load_model(
        LOCAL_MODEL_DIR,
        device="cpu",
    )

    MODEL_READY = True
    print(
        "Local model loaded successfully."
    )
    print(
        "Mode: OFFLINE / CPU"
    )

# =========================================================
# Main worker
# =========================================================
def convert_current_input(
    original_hwnd,
    status_anchor,
):
    try:
        # -------------------------------------------------
        # Select
        # -------------------------------------------------
        set_status(
            "Selecting input",
            5000,
            status_anchor,
            "working",
        )
        original_text = (
            select_all_and_copy()
        )

        # -------------------------------------------------
        # Empty input
        # -------------------------------------------------
        if not original_text.strip():
            # Collapse empty selection.
            send_keys(
                "{RIGHT}",
                delay=0.05,
            )
            set_status(
                "No text found",
                2200,
                status_anchor,
                "warning",
            )
            return

        # -------------------------------------------------
        # Safety limit
        # -------------------------------------------------
        input_length = len(
            original_text
        )
        print()
        print(
            f"Input length: "
            f"{input_length} characters"
        )

        if (
            input_length
            > MAX_INPUT_CHARS
        ):
            print(
                "Input is too large."
            )
            set_status(
                "Text too long • Use a shorter input",
                3500,
                status_anchor,
                "warning",
            )
            return

        print(
            "[Hotkey] full input"
        )
        print(
            f"Input: "
            f"{original_text!r}"
        )

        # -------------------------------------------------
        # Smart analyzer
        # -------------------------------------------------
        if not contains_convertible_text(
            original_text
        ):
            print(
                "No Banglish detected."
            )

            # Restore normal cursor state.
            send_keys(
                "{RIGHT}",
                delay=0.05,
            )
            set_status(
                "No Banglish text found",
                2200,
                status_anchor,
                "warning",
            )
            return

        # -------------------------------------------------
        # Local AI
        # -------------------------------------------------
        set_status(
            "Converting offline",
            30000,
            status_anchor,
            "working",
        )
        print(
            "Smart conversion with local model..."
        )

        converted_text = (
            convert_full_text(
                original_text
            )
        )
        converted_text = (
            clean_model_output(
                converted_text
            )
        )

        if not converted_text.strip():
            raise RuntimeError(
                "Conversion returned empty text."
            )

        # -------------------------------------------------
        # Verify there is actually a result difference.
        # -------------------------------------------------
        if (
            converted_text
            == original_text
        ):
            print(
                "Conversion produced no change."
            )
            send_keys(
                "{RIGHT}",
                delay=0.05,
            )
            set_status(
                "Nothing to convert",
                2200,
                status_anchor,
                "warning",
            )
            return

        print()
        print(
            f"Converted: "
            f"{converted_text!r}"
        )

        # -------------------------------------------------
        # Replacement
        # -------------------------------------------------
        set_status(
            "Replacing text",
            5000,
            status_anchor,
            "working",
        )
        replace_selected_text(
            converted_text,
            original_hwnd,
        )

        # -------------------------------------------------
        # Success
        # -------------------------------------------------
        print(
            "Replacement completed."
        )
        set_status(
            "Converted successfully",
            1800,
            status_anchor,
            "success",
        )

    except Exception as e:
        # We do not attempt replacement after an error.
        print()
        print(
            "ERROR:"
        )
        print(
            repr(e)
        )
        set_status(
            "Conversion failed • Original text kept",
            4000,
            status_anchor,
            "error",
        )

    finally:
        try:
            busy_lock.release()
        except RuntimeError:
            pass

# =========================================================
# Start conversion
# =========================================================
def start_conversion():
    # -----------------------------------------------------
    # Double-trigger protection
    # -----------------------------------------------------
    if not busy_lock.acquire(
        blocking=False
    ):
        set_status(
            "Already converting",
            1600,
            None,
            "warning",
        )
        return

    # -----------------------------------------------------
    # Original focused application
    # -----------------------------------------------------
    original_hwnd = (
        user32.GetForegroundWindow()
    )

    # -----------------------------------------------------
    # Mouse anchor
    # -----------------------------------------------------
    status_anchor = (
        get_mouse_position()
    )

    # -----------------------------------------------------
    # Background worker
    # -----------------------------------------------------
    worker = threading.Thread(
        target=convert_current_input,
        args=(
            original_hwnd,
            status_anchor,
        ),
        daemon=True,
    )
    worker.start()

# =========================================================
# Windows startup helpers
# =========================================================
STARTUP_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "BanglaKor"
TRAY_MENU_STARTUP = 2004
MF_CHECKED = 0x00000008
STARTUP_MODE = "--startup" in sys.argv[1:]


def get_startup_command():
    """Return the command Windows should run at user logon."""
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}" --startup'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}" --startup'


def is_startup_enabled():
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_PATH,
            0,
            winreg.KEY_READ,
        ) as key:
            value, _ = winreg.QueryValueEx(
                key,
                STARTUP_VALUE_NAME,
            )
            return bool(value)
    except (FileNotFoundError, OSError, PermissionError):
        return False


def set_startup_enabled(enabled):
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            STARTUP_REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    STARTUP_VALUE_NAME,
                    0,
                    winreg.REG_SZ,
                    get_startup_command(),
                )
            else:
                try:
                    winreg.DeleteValue(
                        key,
                        STARTUP_VALUE_NAME,
                    )
                except FileNotFoundError:
                    pass
        return True
    except (OSError, PermissionError) as exc:
        print(f"Startup setting error: {exc}")
        return False

# =========================================================
# =========================================================
# Main window / welcome screen
# =========================================================
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
    if root is None:
        return
    try:
        root.update_idletasks()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        x = max(0, (screen_w - WELCOME_WIDTH) // 2)
        y = max(0, (screen_h - WELCOME_HEIGHT) // 2)
        root.geometry(f"{WELCOME_WIDTH}x{WELCOME_HEIGHT}+{x}+{y}")
    except Exception:
        pass


def hide_main_window():
    if root is None:
        return
    try:
        root.withdraw()
    except Exception:
        pass


def _clear_root_children():
    if root is None:
        return
    for widget in root.winfo_children():
        try:
            widget.destroy()
        except Exception:
            pass


def _make_kbd(parent, text, width=46):
    box = ctk.CTkFrame(
        parent,
        width=width,
        height=34,
        corner_radius=9,
        fg_color=UI_KBD,
        border_width=1,
        border_color="#2C394C",
    )
    box.pack(side="left", padx=3)
    box.pack_propagate(False)
    ctk.CTkLabel(
        box,
        text=text,
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color=UI_TEXT,
    ).place(relx=0.5, rely=0.5, anchor="center")
    return box


def build_main_window():
    """Build the polished Bangla Kor welcome interface."""
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
        outer,
        corner_radius=24,
        fg_color=UI_CARD,
        border_width=1,
        border_color=UI_BORDER,
    )
    card.pack(fill="both", expand=True)

    # Top accent strip
    accent_strip = ctk.CTkFrame(card, height=3, fg_color=UI_ACCENT, corner_radius=3)
    accent_strip.pack(fill="x", padx=24, pady=(0, 0))

    header = ctk.CTkFrame(card, fg_color="transparent")
    header.pack(fill="x", padx=26, pady=(22, 0))

    logo = ctk.CTkFrame(
        header,
        width=58,
        height=58,
        corner_radius=17,
        fg_color=UI_ACCENT_SOFT,
        border_width=1,
        border_color="#38285F",
    )
    logo.pack(side="left")
    logo.pack_propagate(False)
    ctk.CTkLabel(
        logo,
        text="ক",
        font=ctk.CTkFont(size=30, weight="bold"),
        text_color="#EDE9FE",
    ).place(relx=0.5, rely=0.48, anchor="center")

    brand = ctk.CTkFrame(header, fg_color="transparent")
    brand.pack(side="left", padx=(14, 0), fill="x", expand=True)
    ctk.CTkLabel(
        brand,
        text="Bangla Kor",
        anchor="w",
        font=ctk.CTkFont(size=25, weight="bold"),
        text_color=UI_TEXT,
    ).pack(fill="x")
    ctk.CTkLabel(
        brand,
        text="Banglish → বাংলা",
        anchor="w",
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=UI_MUTED,
    ).pack(fill="x", pady=(2, 0))

    status = ctk.CTkFrame(
        header,
        corner_radius=12,
        fg_color=UI_GREEN_SOFT,
        border_width=1,
        border_color="#205545",
    )
    status.pack(side="right", anchor="n")
    ctk.CTkLabel(
        status,
        text="●  OFFLINE",
        font=ctk.CTkFont(size=9, weight="bold"),
        text_color="#6EE7B7",
    ).pack(padx=11, pady=7)

    ctk.CTkLabel(
        card,
        text="Type normally. One shortcut turns Banglish into বাংলা. Made by TurzO",
        anchor="w",
        font=ctk.CTkFont(size=11),
        text_color=UI_TEXT_SOFT,
    ).pack(fill="x", padx=26, pady=(14, 18))

    hero = ctk.CTkFrame(
        card,
        corner_radius=18,
        fg_color=UI_CARD_2,
        border_width=1,
        border_color=UI_BORDER,
    )
    hero.pack(fill="x", padx=26)

    ctk.CTkLabel(
        hero,
        text="YOUR SHORTCUT",
        font=ctk.CTkFont(size=9, weight="bold"),
        text_color=UI_MUTED,
    ).pack(pady=(13, 8))

    keys = ctk.CTkFrame(hero, fg_color="transparent")
    keys.pack(pady=(0, 9))
    _make_kbd(keys, "CTRL")
    ctk.CTkLabel(keys, text="+", width=14, font=ctk.CTkFont(size=14, weight="bold"), text_color=UI_MUTED).pack(side="left")
    _make_kbd(keys, "SHIFT", 54)
    ctk.CTkLabel(keys, text="+", width=14, font=ctk.CTkFont(size=14, weight="bold"), text_color=UI_MUTED).pack(side="left")
    _make_kbd(keys, "B", 40)

    ctk.CTkLabel(
        hero,
        text="Works in the focused text box",
        font=ctk.CTkFont(size=10),
        text_color=UI_MUTED,
    ).pack(pady=(0, 13))

    guide_title = ctk.CTkFrame(card, fg_color="transparent")
    guide_title.pack(fill="x", padx=26, pady=(17, 7))
    ctk.CTkLabel(
        guide_title,
        text="HOW TO USE",
        anchor="w",
        font=ctk.CTkFont(size=9, weight="bold"),
        text_color=UI_MUTED,
    ).pack(side="left")
    ctk.CTkLabel(
        guide_title,
        text="100% local • No cloud",
        anchor="e",
        font=ctk.CTkFont(size=9),
        text_color="#657287",
    ).pack(side="right")

    steps = ctk.CTkFrame(card, fg_color="transparent")
    steps.pack(fill="x", padx=26)
    step_data = (
        ("01", "Focus a text field", "Click where you want the Bangla text."),
        ("02", "Press Ctrl + Shift + B", "Bangla Kor reads the current text."),
        ("03", "Done", "The converted text replaces the selected text."),
    )
    for number, title, desc in step_data:
        row = ctk.CTkFrame(
            steps,
            height=43,
            corner_radius=11,
            fg_color=UI_CARD_3,
            border_width=1,
            border_color=UI_BORDER_SOFT,
        )
        row.pack(fill="x", pady=3)
        row.pack_propagate(False)

        num = ctk.CTkLabel(
            row,
            text=number,
            width=42,
            height=27,
            corner_radius=8,
            fg_color=UI_ACCENT_SOFT,
            text_color=UI_ACCENT_2,
            font=ctk.CTkFont(size=8, weight="bold"),
        )
        num.pack(side="left", padx=(8, 11))

        copy = ctk.CTkFrame(row, fg_color="transparent")
        copy.pack(side="left", fill="both", expand=True, pady=4)
        ctk.CTkLabel(copy, text=title, anchor="w", font=ctk.CTkFont(size=9, weight="bold"), text_color=UI_TEXT).pack(fill="x")
        ctk.CTkLabel(copy, text=desc, anchor="w", font=ctk.CTkFont(size=8), text_color=UI_MUTED).pack(fill="x")

    footer_line = ctk.CTkFrame(card, height=1, fg_color=UI_BORDER)
    footer_line.pack(fill="x", padx=26, pady=(13, 0))

    footer = ctk.CTkFrame(card, fg_color="transparent")
    footer.pack(fill="x", padx=26, pady=(9, 14))
    ctk.CTkLabel(
        footer,
        text="Made with ♥ by Turzo",
        font=ctk.CTkFont(size=10, weight="bold"),
        text_color="#C4B5FD",
    ).pack(side="left")
    ctk.CTkLabel(
        footer,
        text="Close this window • Bangla Kor stays in the tray",
        font=ctk.CTkFont(size=8),
        text_color="#657287",
    ).pack(side="right")


def show_main_window():
    if root is None:
        return
    try:
        build_main_window()
        center_main_window()
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(250, lambda: root.attributes("-topmost", False))
        root.after(270, root.focus_force)
    except Exception as exc:
        print(f"Main window error: {exc}")


def process_ui_queue():
    while True:
        try:
            action = ui_queue.get_nowait()
        except queue.Empty:
            break
        if action == "show":
            show_main_window()

    if root is not None and not stop_event.is_set():
        try:
            root.after(80, process_ui_queue)
        except (tk.TclError, RuntimeError):
            pass

def show_main_window():
    """Show the main interface without affecting the tray/hotkey."""
    if root is None:
        return
    try:
        build_main_window()
        center_main_window()
        root.deiconify()
        root.lift()
        root.attributes("-topmost", True)
        root.after(250, lambda: root.attributes("-topmost", False))
        root.after(270, root.focus_force)
    except Exception as exc:
        print(f"Main window error: {exc}")


def process_ui_queue():
    """Handle UI requests sent safely from the native tray thread."""
    while True:
        try:
            action = ui_queue.get_nowait()
        except queue.Empty:
            break
        if action == "show":
            show_main_window()

    if root is not None and not stop_event.is_set():
        try:
            root.after(80, process_ui_queue)
        except Exception:
            pass

# =========================================================
# System tray manager
# =========================================================

# Python 3.14 does not expose wintypes.WNDCLASSW consistently in this
# environment, so define the structure ourselves.
class TRAY_GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint32),
        ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint32),
        ("uFlags", ctypes.c_uint32),
        ("uCallbackMessage", ctypes.c_uint32),
        ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_uint32),
        ("dwStateMask", ctypes.c_uint32),
        ("szInfo", ctypes.c_wchar * 256),
        ("uTimeoutOrVersion", ctypes.c_uint32),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_uint32),
        ("guidItem", TRAY_GUID),
        ("hBalloonIcon", ctypes.c_void_p),
    ]


class TRAY_WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint32),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int32),
        ("cbWndExtra", ctypes.c_int32),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


try:
    shell32.Shell_NotifyIconW.argtypes = [
        ctypes.c_uint32,
        ctypes.POINTER(NOTIFYICONDATAW),
    ]
    shell32.Shell_NotifyIconW.restype = ctypes.c_int

    user32.RegisterClassW.argtypes = [
        ctypes.POINTER(TRAY_WNDCLASSW),
    ]
    user32.RegisterClassW.restype = ctypes.c_uint16

    user32.UnregisterClassW.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_void_p,
    ]
    user32.UnregisterClassW.restype = ctypes.c_int

    user32.CreateWindowExW.argtypes = [
        ctypes.c_uint32,
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.CreateWindowExW.restype = ctypes.c_void_p

    user32.DestroyWindow.argtypes = [ctypes.c_void_p]
    user32.DestroyWindow.restype = ctypes.c_int

    user32.DefWindowProcW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.DefWindowProcW.restype = ctypes.c_ssize_t

    user32.PostThreadMessageW.argtypes = [
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.PostThreadMessageW.restype = ctypes.c_int

    user32.GetMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
    ]
    user32.GetMessageW.restype = ctypes.c_int

    user32.TranslateMessage.argtypes = [
        ctypes.POINTER(wintypes.MSG),
    ]
    user32.TranslateMessage.restype = ctypes.c_int

    user32.DispatchMessageW.argtypes = [
        ctypes.POINTER(wintypes.MSG),
    ]
    user32.DispatchMessageW.restype = ctypes.c_ssize_t

    user32.CreatePopupMenu.argtypes = []
    user32.CreatePopupMenu.restype = ctypes.c_void_p

    user32.DestroyMenu.argtypes = [ctypes.c_void_p]
    user32.DestroyMenu.restype = ctypes.c_int

    user32.AppendMenuW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_size_t,
        ctypes.c_wchar_p,
    ]
    user32.AppendMenuW.restype = ctypes.c_int

    user32.TrackPopupMenu.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.TrackPopupMenu.restype = ctypes.c_uint32

    user32.GetCursorPos.argtypes = [
        ctypes.POINTER(POINT),
    ]
    user32.GetCursorPos.restype = ctypes.c_int

    user32.SetForegroundWindow.argtypes = [
        ctypes.c_void_p,
    ]
    user32.SetForegroundWindow.restype = ctypes.c_int

    user32.PostMessageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.PostMessageW.restype = ctypes.c_int

    user32.LoadIconW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    user32.LoadIconW.restype = ctypes.c_void_p

    user32.LoadImageW.argtypes = [
        ctypes.c_void_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    user32.LoadImageW.restype = ctypes.c_void_p

    user32.DestroyIcon.argtypes = [
        ctypes.c_void_p,
    ]
    user32.DestroyIcon.restype = ctypes.c_int

    kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p

    kernel32.GetCurrentThreadId.argtypes = []
    kernel32.GetCurrentThreadId.restype = ctypes.c_uint32
except Exception:
    pass


class SystemTray:
    """Native Windows tray icon with its own message thread."""

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
        self.class_name = (
            f"BanglaKorTrayWindow_{os.getpid()}_{id(self)}"
        )

    def start(self):
        self.thread = threading.Thread(
            target=self._thread_main,
            name="BanglaKor-Tray",
            daemon=True,
        )
        self.thread.start()

        if not self.ready_event.wait(timeout=5):
            self.stop_event.set()
            if self.thread_id:
                try:
                    user32.PostThreadMessageW(
                        self.thread_id,
                        WM_QUIT,
                        0,
                        0,
                    )
                except Exception:
                    pass
            raise RuntimeError(
                "System tray thread did not become ready."
            )

        print("System tray: ready")

    def _thread_main(self):
        self.thread_id = kernel32.GetCurrentThreadId()

        WNDPROC = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )
        self._wndproc = WNDPROC(
            self._window_proc
        )

        self.hinstance = kernel32.GetModuleHandleW(None)

        wc = TRAY_WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = ctypes.cast(
            self._wndproc,
            ctypes.c_void_p,
        ).value
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = self.hinstance
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = self.class_name

        atom = user32.RegisterClassW(
            ctypes.byref(wc)
        )
        if not atom:
            error = ctypes.get_last_error()
            raise ctypes.WinError(error) if error else RuntimeError(
                "Could not register tray window class."
            )

        self.hwnd = user32.CreateWindowExW(
            0,
            self.class_name,
            APP_NAME,
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self.hinstance,
            None,
        )
        if not self.hwnd:
            user32.UnregisterClassW(
                self.class_name,
                self.hinstance,
            )
            error = ctypes.get_last_error()
            raise ctypes.WinError(error) if error else RuntimeError(
                "Could not create tray window."
            )

        try:
            self._add_icon()
            self.ready_event.set()

            msg = wintypes.MSG()
            while not self.stop_event.is_set():
                result = user32.GetMessageW(
                    ctypes.byref(msg),
                    None,
                    0,
                    0,
                )
                if result == -1 or result == 0:
                    break

                user32.TranslateMessage(
                    ctypes.byref(msg)
                )
                user32.DispatchMessageW(
                    ctypes.byref(msg)
                )
        finally:
            self._delete_icon()

            if self.hwnd:
                try:
                    user32.DestroyWindow(
                        self.hwnd
                    )
                except Exception:
                    pass
                self.hwnd = None

            try:
                user32.UnregisterClassW(
                    self.class_name,
                    self.hinstance,
                )
            except Exception:
                pass

    def _add_icon(self):

        # Load the custom Bangla Kor icon from the same folder as
        # main.py in development and next to BanglaKor.exe when frozen.
        if not os.path.isfile(ICON_PATH):
            raise FileNotFoundError(
                f"Bangla Kor icon not found: {ICON_PATH}"
            )

        self.hicon = user32.LoadImageW(
            None,
            ICON_PATH,
            IMAGE_ICON,
            0,
            0,
            LR_LOADFROMFILE | LR_DEFAULTSIZE,
        )

        if not self.hicon:
            error = ctypes.get_last_error()
            if error:
                raise ctypes.WinError(error)
            raise RuntimeError(
                "Windows could not load bangla-kor-icon.ico."
            )

        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(
            NOTIFYICONDATAW
        )
        data.hWnd = self.hwnd
        data.uID = 1
        data.uFlags = (
            NIF_MESSAGE
            | NIF_ICON
            | NIF_TIP
        )
        data.uCallbackMessage = (
            TRAY_CALLBACK_MESSAGE
        )
        data.hIcon = self.hicon
        data.szTip = "Bangla Kor • by Turzo"

        result = shell32.Shell_NotifyIconW(
            NIM_ADD,
            ctypes.byref(data),
        )

        if not result:
            try:
                user32.DestroyIcon(
                    self.hicon
                )
            except Exception:
                pass
            self.hicon = None
            raise RuntimeError(
                "Windows rejected the Bangla Kor tray icon."
            )

        self.icon_added = True

    def _delete_icon(self):
        if not self.hwnd or not self.icon_added:
            return

        data = NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(
            NOTIFYICONDATAW
        )
        data.hWnd = self.hwnd
        data.uID = 1

        try:
            shell32.Shell_NotifyIconW(
                NIM_DELETE,
                ctypes.byref(data),
            )
        except Exception:
            pass

        self.icon_added = False

        if self.hicon:
            try:
                user32.DestroyIcon(
                    self.hicon
                )
            except Exception:
                pass
            self.hicon = None

    def _window_proc(
        self,
        hwnd,
        msg,
        wparam,
        lparam,
    ):
        if msg == TRAY_CALLBACK_MESSAGE:
            event = (
                ctypes.cast(
                    lparam,
                    ctypes.c_void_p,
                ).value
                or 0
            ) & 0xFFFF

            if event == WM_RBUTTONUP:
                try:
                    self._show_menu()
                except Exception as exc:
                    print(
                        f"Tray menu error: {exc}"
                    )
                return 0

            return 0

        if msg == WM_DESTROY:
            return 0

        return user32.DefWindowProcW(
            hwnd,
            msg,
            wparam,
            lparam,
        )

    def _show_menu(self):
        menu = user32.CreatePopupMenu()
        if not menu:
            return

        if not MODEL_READY:
            status_text = "Status: Loading local AI"
        elif busy_lock.locked():
            status_text = "Status: Converting..."
        else:
            status_text = "Status: Offline • Ready"

        startup_enabled = is_startup_enabled()

        try:
            # Informational items are intentionally NOT grayed out.
            user32.AppendMenuW(
                menu,
                MF_STRING,
                TRAY_MENU_STATUS,
                status_text,
            )

            user32.AppendMenuW(
                menu,
                MF_STRING,
                TRAY_MENU_SHORTCUT,
                "Shortcut: Ctrl + Shift + B",
            )

            user32.AppendMenuW(
                menu,
                MF_STRING,
                TRAY_MENU_OPEN,
                "Open Bangla Kor",
            )

            user32.AppendMenuW(
                menu,
                MF_SEPARATOR,
                0,
                None,
            )

            startup_flags = MF_STRING
            if startup_enabled:
                startup_flags |= MF_CHECKED

            user32.AppendMenuW(
                menu,
                startup_flags,
                TRAY_MENU_STARTUP,
                "Start with Windows",
            )

            user32.AppendMenuW(
                menu,
                MF_SEPARATOR,
                0,
                None,
            )

            user32.AppendMenuW(
                menu,
                MF_STRING,
                TRAY_MENU_EXIT,
                "Exit",
            )

            point = POINT()
            if not user32.GetCursorPos(
                ctypes.byref(point)
            ):
                point.x = 0
                point.y = 0

            user32.SetForegroundWindow(
                self.hwnd
            )

            command = user32.TrackPopupMenu(
                menu,
                TPM_RIGHTBUTTON
                | TPM_BOTTOMALIGN
                | TPM_LEFTALIGN
                | TPM_RETURNCMD,
                int(point.x),
                int(point.y),
                0,
                self.hwnd,
                None,
            )

            command = int(command)

            if command == TRAY_MENU_OPEN:
                self.open_callback()

            elif command == TRAY_MENU_STARTUP:
                new_state = not startup_enabled

                if set_startup_enabled(
                    new_state
                ):
                    message = (
                        "Start with Windows enabled"
                        if new_state
                        else "Start with Windows disabled"
                    )
                    print(
                        f"Start with Windows: "
                        f"{'ON' if new_state else 'OFF'}"
                    )
                    set_status(
                        message,
                        2200,
                        get_mouse_position(),
                        "success",
                    )
                else:
                    set_status(
                        "Could not change startup setting",
                        3000,
                        get_mouse_position(),
                        "error",
                    )

            elif command == TRAY_MENU_EXIT:
                self.exit_callback()

            user32.PostMessageW(
                self.hwnd,
                WM_NULL,
                0,
                0,
            )

        finally:
            user32.DestroyMenu(menu)

    def stop(self):
        self.stop_event.set()

        if self.thread_id:
            try:
                user32.PostThreadMessageW(
                    self.thread_id,
                    WM_QUIT,
                    0,
                    0,
                )
            except Exception:
                pass

        if (
            self.thread
            and self.thread.is_alive()
            and threading.current_thread() is not self.thread
        ):
            try:
                self.thread.join(timeout=3)
            except Exception:
                pass

        self.thread = None
        print("System tray: stopped")

# =========================================================
# Single-instance protection
# =========================================================
SINGLE_INSTANCE_NAME = "Local\\BanglaKor_SingleInstance_8C6C0C6D"
ERROR_ALREADY_EXISTS = 183


def acquire_single_instance():
    """Prevent multiple Bangla Kor processes from running at once."""
    global APP_MUTEX

    try:
        kernel32.CreateMutexW.argtypes = [
            wintypes.LPVOID,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        kernel32.GetLastError.restype = wintypes.DWORD
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
    except Exception:
        pass

    try:
        APP_MUTEX = kernel32.CreateMutexW(
            None,
            False,
            SINGLE_INSTANCE_NAME,
        )
        if not APP_MUTEX:
            return True

        if int(kernel32.GetLastError()) == ERROR_ALREADY_EXISTS:
            kernel32.CloseHandle(APP_MUTEX)
            APP_MUTEX = None
            return False

        return True
    except Exception as exc:
        # If mutex creation is unavailable, do not block the app from running.
        print(f"Single-instance check unavailable: {exc}")
        APP_MUTEX = None
        return True


def release_single_instance():
    global APP_MUTEX
    if APP_MUTEX:
        try:
            kernel32.CloseHandle(APP_MUTEX)
        except Exception:
            pass
        APP_MUTEX = None

# =========================================================
# Hotkey registration
# =========================================================
def register_hotkey():
    success = (
        user32.RegisterHotKey(
            None,
            HOTKEY_ID,
            MOD_CONTROL
            | MOD_SHIFT
            | MOD_NOREPEAT,
            VK_B,
        )
    )
    if not success:
        error = ctypes.get_last_error()
        if error:
            raise ctypes.WinError(error)
        raise RuntimeError(
            "Could not register "
            "Ctrl + Shift + B."
        )


def unregister_hotkey():
    try:
        user32.UnregisterHotKey(
            None,
            HOTKEY_ID,
        )
    except Exception:
        pass

# =========================================================
# Main
# =========================================================
def main():
    global root

    if not acquire_single_instance():
        print("Bangla Kor is already running.")
        return

    # -----------------------------------------------------
    # CustomTkinter
    # -----------------------------------------------------
    ctk.set_appearance_mode(
        "dark"
    )
    ctk.set_default_color_theme(
        "blue"
    )
    root = ctk.CTk()
    root.withdraw()

    # -----------------------------------------------------
    # HUD
    # -----------------------------------------------------
    toast = StatusToast(
        root
    )
    root.after(
        40,
        process_status_queue,
        toast,
    )
    root.after(
        80,
        process_ui_queue,
    )

    # -----------------------------------------------------
    # Startup
    # -----------------------------------------------------
    set_status(
        "Loading local AI",
        60000,
        None,
        "working",
    )

    try:
        load_local_model()
    except Exception as e:
        set_status(
            "Local AI failed to load",
            5000,
            None,
            "error",
        )
        print()
        print(
            "Model loading failed."
        )
        print(
            f"Error: {e}"
        )
        try:
            root.update()
            time.sleep(2)
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass
        return

    # -----------------------------------------------------
    # Ready
    # -----------------------------------------------------
    set_status(
        "Local AI ready",
        2200,
        None,
        "success",
    )

    # -----------------------------------------------------
    # Register global shortcut
    # -----------------------------------------------------
    try:
        register_hotkey()
    except Exception as e:
        print()
        print(
            "Hotkey registration failed."
        )
        print(
            f"Error: {e}"
        )
        set_status(
            "Hotkey registration failed",
            5000,
            None,
            "error",
        )
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
        return

    # -----------------------------------------------------
    # System tray
    # -----------------------------------------------------
    global TRAY
    try:
        TRAY = SystemTray(
            exit_callback=lambda: stop_event.set(),
            open_callback=lambda: ui_queue.put("show"),
        )
        TRAY.start()
    except Exception as e:
        TRAY = None
        print()
        print("System tray failed to start.")
        print(f"Error: {e}")
        set_status(
            "Tray failed • App still running",
            3000,
            None,
            "warning",
        )

    # -----------------------------------------------------
    # Main interface
    # -----------------------------------------------------
    # Manual launch shows the compact welcome screen. Windows startup
    # passes --startup and starts directly in the background tray.
    if not STARTUP_MODE:
        show_main_window()

    # -----------------------------------------------------
    # Console
    # -----------------------------------------------------
    print()
    print(
        "=" * 60
    )
    print(
        "Bangla Kor"
    )
    print(
        "=" * 60
    )
    print()
    print(
        "AI Engine: Local"
    )
    print(
        "Mode: 100% Offline"
    )
    print()
    print(
        "Ctrl + Shift + B"
    )
    print(
        "-> Convert all Banglish text in the focused input"
    )
    print()
    print(
        "Smart analyzer:"
    )
    print(
        "- Existing Bangla preserved"
    )
    print(
        "- Pure English preserved"
    )
    print(
        "- Technical words protected"
    )
    print(
        "- URLs / emails / code protected"
    )
    print(
        "- Long text chunked safely"
    )
    print(
        f"- Max input: {MAX_INPUT_CHARS} characters"
    )
    print()
    print(
        "Gemini API: OFF"
    )
    print(
        "Internet required: NO"
    )
    print()
    print(
        "Right-click the tray icon for menu • Ctrl + C also stops the app."
    )
    print(
        "=" * 60
    )

    # -----------------------------------------------------
    # Event loop
    # -----------------------------------------------------
    try:
        msg = wintypes.MSG()

        while not stop_event.is_set():
            while user32.PeekMessageW(
                ctypes.byref(msg),
                None,
                0,
                0,
                PM_REMOVE,
            ):
                if (
                    msg.message
                    == WM_HOTKEY
                ):
                    if (
                        int(msg.wParam)
                        == HOTKEY_ID
                    ):
                        start_conversion()

                user32.TranslateMessage(
                    ctypes.byref(msg)
                )
                user32.DispatchMessageW(
                    ctypes.byref(msg)
                )

            try:
                root.update()
            except tk.TclError:
                break

            time.sleep(
                0.01
            )

    except KeyboardInterrupt:
        print()
        print(
            "Stopping Bangla Kor..."
        )

    finally:
        stop_event.set()
        unregister_hotkey()

        try:
            if TRAY:
                TRAY.stop()
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

        print(
            "Hotkey unregistered."
        )
        print(
            "Bangla Kor stopped."
        )

# =========================================================
# Run
# =========================================================
if __name__ == "__main__":
    main()
