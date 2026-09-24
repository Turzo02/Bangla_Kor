"""Protected words and patterns — URLs, emails, code, brand names."""
import re

PROTECTED_WORDS = [
    "Visual Studio Code", "VS Code", "ChatGPT", "Hugging Face", "GitHub",
    "GitLab", "Stack Overflow", "Google Drive", "Google Docs", "Google Sheets",
    "Google Chrome", "YouTube", "Facebook", "Instagram", "Telegram", "Discord",
    "WhatsApp", "OpenAI", "Gemini", "Chrome", "Firefox", "Edge", "GPT",
    "GPT-4", "GPT-4o", "GPT-5", "HTML", "CSS", "JavaScript", "TypeScript",
    "React", "ReactJS", "Next.js", "Node.js", "Express", "MongoDB", "Firebase",
    "Tailwind", "Tailwind CSS", "DaisyUI", "Vite", "npm", "npx", "pnpm",
    "Yarn", "Python", "Java", "Kotlin", "Android", "Windows", "Linux", "macOS",
    "API", "REST API", "JSON", "XML", "HTTP", "HTTPS", "URL", "SQL", "MySQL",
    "PostgreSQL", "Redis", "Docker", "PyTorch", "TensorFlow", "NumPy", "OpenCV",
    "Whisper", "Transformer", "Transformers", "CPU", "GPU", "AI", "ML", "NLP",
    "OCR", "EXE", ".NET", "C++", "C#", "CSSBattle", "localhost",
]
PROTECTED_WORDS = sorted(PROTECTED_WORDS, key=len, reverse=True)

PROTECTED_PATTERNS = [
    r"https?://[^\s]+",
    r"www\.[^\s]+",
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}",
    r"`[^`\r\n]+`",
    r"```[\s\S]*?```",
]
for word in PROTECTED_WORDS:
    escaped = re.escape(word)
    PROTECTED_PATTERNS.append(rf"(?<![A-Za-z0-9_]){escaped}(?![A-Za-z0-9_])")

PROTECTED_PATTERN = re.compile(
    "|".join(f"({p})" for p in PROTECTED_PATTERNS),
    re.IGNORECASE,
)


def contains_bengali(text):
    return bool(re.search(r"[\u0980-\u09FF]", text))


def visible_without_protected(text):
    return PROTECTED_PATTERN.sub(" ", text)


def get_latin_words(text):
    return re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())