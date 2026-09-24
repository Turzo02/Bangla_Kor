"""Analyzer — simplified for Option B (everything converts to Bangla).

A line should be converted if it contains any Latin letter after removing
protected content.
"""
import re

from core.protect import (
    PROTECTED_PATTERN, contains_bengali, get_latin_words,
    visible_without_protected,
)


def should_convert_line(line):
    """True if the line has any Latin letter outside protected regions."""
    if not line.strip():
        return False
    visible = visible_without_protected(line)
    return bool(re.search(r"[A-Za-z]", visible))


# Keep these exports for backward compatibility
BANGLISH_COMMON_WORDS = set()
def is_english_word(word):
    return False
def word_banglish_score(word):
    return 0, False, False
def banglish_score(text):
    return 0