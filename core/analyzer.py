"""Banglish detection heuristics — decides which lines to convert."""
import re

from core.protect import (
    PROTECTED_PATTERN, contains_bengali, get_latin_words, visible_without_protected,
)

BANGLISH_COMMON_WORDS = {
    "ami", "amra", "amar", "amader", "amake", "tumi", "tomar", "tomake",
    "tomader", "apni", "apnar", "apnake", "apnader", "uni", "oder", "ora",
    "tara", "tar", "oita", "oitay", "oitake", "oitar", "eita", "eitay",
    "eitake", "eitar", "eta", "etar", "etay", "etake", "kire", "kirey",
    "mama", "vai", "bhai", "bon", "apu", "re", "ki", "kno", "keno", "kivabe",
    "kmne", "kemon", "kothay", "kothai", "kokhon", "kisu", "kichu", "keu",
    "sob", "shob", "shobai", "sobai", "onek", "ekhon", "ekhane", "okhane",
    "sekhaney", "aj", "ajke", "ajk", "kalke", "kal", "pore", "porer", "age",
    "ager", "abar", "aro", "kom", "beshi", "khub", "shudhu", "sudhu", "jabo",
    "jabe", "jawa", "jai", "jao", "jacchi", "jacci", "jacche", "jatchi",
    "jaitesi", "gechi", "gese", "gesey", "gelo", "giye", "aso", "asho",
    "achi", "acho", "ache", "ase", "nai", "nei", "hoy", "hoise", "hobe",
    "hobo", "hochhe", "hocche", "hoye", "kor", "koro", "koren", "korte",
    "kora", "kore", "korbo", "korbi", "korbe", "korben", "kortesi", "kortese",
    "kortam", "korlam", "korchi", "korchhi", "korchhe", "korechi", "koreche",
    "dibo", "dibe", "dibey", "dei", "dao", "day", "nibo", "nibe", "nite",
    "niye", "niyechi", "nei", "chai", "chay", "lagbe", "lage", "lagse",
    "laglo", "dorkar", "bolbo", "bolbe", "bolte", "bolo", "bol", "bolsi",
    "bolse", "shune", "shunsi", "shunbo", "dekh", "dekha", "dekhi", "dekho",
    "dekhte", "dekhbo", "dite", "asbo", "asbe", "aschi", "eshe", "eshechi",
    "thakbo", "thakbe", "thak", "thake", "thaka", "thaki", "thako", "bujhi",
    "bujhte", "bujhbo", "bujhbe", "shikhi", "shikbo", "shikhbo", "shikhte",
    "likhi", "likhbo", "likhte", "pori", "porbo", "porte", "porchi", "khabo",
    "kheye", "khete", "ghumabo", "ghumai", "uthbo", "uthi", "boshbo", "boshi",
    "valo", "bhalo", "bhalobasha", "bhalobashi", "kharap", "shundor", "sundor",
    "boro", "chhoto", "soto", "notun", "purono", "manush", "mon", "mone",
    "bari", "basay", "basha", "bondhu", "bondhura", "kaj", "kotha", "kothar",
    "somoy", "shomoy", "jinish", "byapar", "bapar", "proshno", "uttor",
    "somossa", "shomossha", "upay", "taka", "din", "rat", "raat", "shokal",
    "sokal", "dupur", "bikal", "boi", "khata", "phone", "mobile", "computer",
    "file", "text", "lekha", "message", "chobi", "pani", "khabar", "ranna",
    "rastay", "room", "ghor", "desh", "bangla", "bangladesh", "ekta", "ekhon",
    "jodi", "tahole", "tokhon", "taile", "tai", "ejonno", "jonno", "sathe",
    "theke", "diye", "niye", "amr", "tmr", "kn", "kmn", "pls", "please",
    "hmm", "ha",
}

BANGLISH_SUFFIXES = (
    "tese", "tesi", "techi", "tese", "chhi", "chhe", "chi", "che", "gechi",
    "gese", "gesi", "bo", "be", "te", "ta", "ti", "gulo", "gula", "der",
    "lam", "len", "li", "si", "se", "lo", "en",
)

DISTINCTIVE_BANGLISH_PATTERNS = (
    "kh", "bh", "dh", "gh", "ch", "sh", "aa", "oo", "ee", "jhi", "jha",
    "kha", "bhi", "dhi", "tumi", "ami", "amar", "tom", "amr", "tmr",
    "kno", "kmn", "kmne",
)

COMMON_ENGLISH_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can",
    "could", "did", "do", "does", "for", "from", "get", "go", "good", "have",
    "has", "had", "he", "her", "here", "him", "his", "how", "i", "if", "in",
    "is", "it", "its", "just", "like", "me", "my", "no", "not", "now", "of",
    "on", "one", "or", "our", "out", "please", "say", "see", "she", "should",
    "so", "some", "than", "that", "the", "their", "them", "there", "these",
    "they", "this", "to", "too", "up", "us", "use", "very", "was", "we",
    "were", "what", "when", "where", "which", "who", "will", "with", "would",
    "you", "your", "today", "hello",
}

ENGLISH_SUFFIXES = (
    "ing", "tion", "sion", "ment", "ness", "able", "ible", "ous", "ful",
    "less", "ity", "ive", "ize", "ise", "ally", "edly", "ing", "est",
    "ers", "ly",
)


def word_banglish_score(word):
    word = word.lower().strip("._'+-")
    if not word:
        return 0, False, False
    if word in BANGLISH_COMMON_WORDS:
        return 4, True, True

    score = 0
    distinctive = any(p in word for p in DISTINCTIVE_BANGLISH_PATTERNS)
    suffix = any(
        word.endswith(s) for s in BANGLISH_SUFFIXES
        if len(word) >= max(4, len(s) + 1)
    )
    if distinctive:
        score += 1
    if suffix:
        score += 2 if len(word) <= 9 else 1
    if re.search(r"(?:kk|gg|jj|pp|tt|dd|mm|nn|ll|ss)", word):
        score += 1
    if re.search(r"(?:[bcdfghjklmnpqrstvwxyz]{3,})", word):
        score += 1
    for pattern in ("kh", "bh", "dh", "gh", "ch", "sh", "ng", "aa", "ee", "oo"):
        if pattern in word:
            score += 1
            break
    if len(word) >= 6 and any(word.endswith(s) for s in ENGLISH_SUFFIXES):
        score -= 2
    return max(0, min(score, 4)), distinctive, suffix


def banglish_score(text):
    words = get_latin_words(visible_without_protected(text))
    return min(sum(word_banglish_score(w)[0] for w in words), 12)


def should_convert_line(line):
    if not line.strip():
        return False
    visible = visible_without_protected(line)
    if not re.search(r"[A-Za-z]", visible):
        return False
    words = get_latin_words(visible)
    if not words:
        return False

    score = 0
    strong_hits = weak_hits = distinctive_hits = suffix_hits = english_hits = 0

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
    if weak_hits >= 2 and score >= 4 and (distinctive_hits >= 1 or suffix_hits >= 1):
        return True
    if contains_bengali(line) and score >= 2 and (distinctive_hits >= 1 or suffix_hits >= 1):
        return True
    if len(words) <= 2 and english_hits >= len(words) - 1:
        return False
    return False