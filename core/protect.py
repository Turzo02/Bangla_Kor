"""Protected content only — URLs, emails, filenames, code, paths, CLI commands.

Strategy (Option B — full Bangla):
  Everything converts to Bangla EXCEPT these safe patterns:
    - URLs
    - Emails
    - Filenames (config.json, main.py)
    - File paths (C:\\Users\\..., /home/...)
    - CLI commands (git commit, pip install, python main.py)
    - Inline code / code blocks
"""
import re

from config import BASE_DIR


# ═══════════════════════════════════════════════════════════
# Protected patterns
# ═══════════════════════════════════════════════════════════
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
    # Filenames with common extensions
    r"\b[\w\-\.\\/]+\.(json|jsonc|py|pyw|exe|dll|so|dylib|txt|md|rst|html|htm|css|scss|js|jsx|ts|tsx|xml|yml|yaml|ini|cfg|conf|log|zip|rar|7z|tar|gz|png|jpg|jpeg|gif|webp|svg|ico|bmp|pdf|doc|docx|xls|xlsx|ppt|pptx|pt|pth|bin|whl|spec|iss|sh|bat|cmd|ps1|vue|svelte|toml|lock)\b",
    # Windows / Linux paths
    r"\b[A-Za-z]:\\[^\s]+",
    r"(?<!\w)/[\w/\.\-]+(?!\w)",

    # ── CLI commands — protect full command with arguments ──
    # git commands (full line, includes -m "message" and version tags)
    r"\bgit\s+commit\s+-m\s+[\"'][^\"']+[\"']",
    r"\bgit\s+push(?:\s+[^\s]+)*",
    r"\bgit\s+pull(?:\s+[^\s]+)*",
    r"\bgit\s+add\s+[^\n\r]+",
    r"\bgit\s+clone\s+[^\s]+",
    r"\bgit\s+(?:status|log|diff|checkout|branch|merge|rebase|reset|tag|stash|fetch|remote|init)\b[^\n\r]*",
    # Other CLI (single argument)
    r"\b(?:npm|npx|pnpm|yarn|pip|pip3|node|cargo|go|docker|kubectl|conda|brew|apt|apt-get|winget|choco)\s+[^\s]+",
    # Python scripts
    r"\bpython(?:3)?\s+[^\s]+\.py",
]

PROTECTED_PATTERN = re.compile(
    "|".join(f"({p})" for p in PROTECTED_PATTERNS),
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════
def contains_bengali(text):
    return bool(re.search(r"[\u0980-\u09FF]", text))


def visible_without_protected(text):
    return PROTECTED_PATTERN.sub(" ", text)


def get_latin_words(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())