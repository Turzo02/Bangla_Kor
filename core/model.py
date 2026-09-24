"""Local model loading + text conversion pipeline.

Two run modes:
  - Source: `infer` is imported after adding local_model/ to sys.path
  - Frozen: PyInstaller has bundled `infer` into the archive via
            hiddenimports, so we import it directly without sys.path hacks.
"""
import os
import re
import sys

from config import LOCAL_MODEL_ROOT, LOCAL_MODEL_DIR
from core.analyzer import should_convert_line
from core.protect import PROTECTED_PATTERN
import state


# Lazy import cache for `infer`
_infer_module = None


def _get_infer():
    """Import and cache (load_model, transliterate) from infer.py.

    In frozen mode, PyInstaller already bundled `infer` into the app;
    we just import it. In source mode, we add local_model/ to sys.path
    so Python can find it.
    """
    global _infer_module
    if _infer_module is None:
        if not getattr(sys, "frozen", False):
            # Source mode — make `infer.py` importable
            if LOCAL_MODEL_ROOT not in sys.path:
                sys.path.insert(0, LOCAL_MODEL_ROOT)

        # Import regardless of mode (frozen uses bundled module)
        from infer import load_model, transliterate  # type: ignore
        _infer_module = (load_model, transliterate)
    return _infer_module


# ═══════════════════════════════════════════════════════════
# Model loading
# ═══════════════════════════════════════════════════════════
def load_local_model():
    """Load the local transliteration model into `state`."""
    print("\nLoading local model...")
    print(f"Model path: {LOCAL_MODEL_DIR}")

    if not os.path.isdir(LOCAL_MODEL_DIR):
        raise FileNotFoundError(
            f"Local model directory not found:\n{LOCAL_MODEL_DIR}"
        )

    load_model, _ = _get_infer()

    (
        state.LOCAL_MODEL,
        state.SRC_VOCAB,
        state.TGT_VOCAB,
        state.MODEL_CFG,
    ) = load_model(LOCAL_MODEL_DIR, device="cpu")

    state.MODEL_READY = True
    print("Local model loaded successfully.")
    print("Mode: OFFLINE / CPU")


# ═══════════════════════════════════════════════════════════
# Token limit helpers
# ═══════════════════════════════════════════════════════════
def get_model_token_limit():
    maxlen = int(state.MODEL_CFG.get("maxlen", 128))
    return max(maxlen - 2, 8)


def split_into_model_chunks(text):
    """Split long text into safe chunks that fit the model's token limit."""
    limit = get_model_token_limit()
    words = re.split(r"(\s+)", text)
    if not any(p.strip() for p in words):
        return []

    def token_count(value):
        try:
            return len(state.SRC_VOCAB.encode(value, maxlen=10000))
        except Exception:
            return len(value)

    chunks = []
    current = ""

    for piece in words:
        if not piece:
            continue

        candidate = current + piece

        if current and piece.isspace():
            current = candidate
            continue

        if not current:
            if token_count(piece) <= limit:
                current = piece
                continue
            # Hard split oversized token
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


# ═══════════════════════════════════════════════════════════
# Output cleanup
# ═══════════════════════════════════════════════════════════
def clean_model_output(text):
    if not text:
        return ""
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+([,!?;:])", r"\1", text)
    text = re.sub(r"[ \t]+।", "।", text)
    text = re.sub(r"([([\{])\s+", r"\1", text)
    text = re.sub(r"\s+([)\]}])", r"\1", text)
    text = re.sub(r"[ \t]+(?=\n|$)", "", text)
    return text.strip()


def split_leading_trailing_space(text):
    leading = re.match(r"^\s*", text).group(0)
    trailing = re.search(r"\s*$", text).group(0)
    start = len(leading)
    end = max(len(text) - len(trailing), start)
    return leading, text[start:end], trailing


# ═══════════════════════════════════════════════════════════
# Conversion pipeline
# ═══════════════════════════════════════════════════════════
def convert_model_piece(text):
    """Convert one manageable piece through the local model."""
    if not text.strip():
        return text

    chunks = split_into_model_chunks(text)
    if not chunks:
        return text

    _, transliterate = _get_infer()
    converted_chunks = []

    for chunk in chunks:
        leading, core, trailing = split_leading_trailing_space(chunk)
        if not core:
            continue

        result = transliterate(
            core,
            state.LOCAL_MODEL,
            state.SRC_VOCAB,
            state.TGT_VOCAB,
            "cpu",
            state.MODEL_CFG,
            reverse=False,
        )
        if result is None:
            raise RuntimeError("Local model returned no result.")

        cleaned = clean_model_output(str(result))
        converted_chunks.append(leading + cleaned + trailing)

    return " ".join(c.strip() for c in converted_chunks if c.strip())


def convert_line_smart(line):
    """Convert one line, preserving protected content and existing Bengali."""
    if not should_convert_line(line):
        return line

    pieces = []
    cursor = 0

    # Protected things + already-Bengali segments
    combined = re.compile(
        "(" + PROTECTED_PATTERN.pattern + r"|[\u0980-\u09FF]+)",
        re.IGNORECASE,
    )

    for match in combined.finditer(line):
        gap = line[cursor:match.start()]
        if gap:
            leading, core, trailing = split_leading_trailing_space(gap)
            if core and re.search(r"[A-Za-z]", core):
                pieces.append(leading + convert_model_piece(core) + trailing)
            else:
                pieces.append(gap)
        pieces.append(match.group(0))
        cursor = match.end()

    if cursor < len(line):
        gap = line[cursor:]
        leading, core, trailing = split_leading_trailing_space(gap)
        if core and re.search(r"[A-Za-z]", core):
            pieces.append(leading + convert_model_piece(core) + trailing)
        else:
            pieces.append(gap)

    return clean_model_output("".join(pieces))


def convert_full_text(text):
    """Convert full multi-line text, preserving line structure."""
    parts = re.split(r"(\r\n|\n|\r)", text)
    out = []
    for part in parts:
        if part in ("\r\n", "\n", "\r"):
            out.append(part)
            continue
        if not part:
            continue
        out.append(convert_line_smart(part))
    return "".join(out)


def contains_convertible_text(text):
    """True if any line in the text should be converted."""
    for line in re.split(r"\r\n|\n|\r", text):
        if should_convert_line(line):
            return True
    return False