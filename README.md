<div align="center">

# Bangla Kor

**Write Banglish anywhere. One shortcut. Perfect বাংলা.**

[![Download](https://img.shields.io/badge/Download-Latest%20Release-8B5CF6?style=for-the-badge&logo=github)](https://github.com/Turzo02/Bangla_Kor/releases/latest)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D4?style=for-the-badge&logo=windows)](https://github.com/Turzo02/Bangla_Kor/releases)
[![Offline](https://img.shields.io/badge/100%25-Offline-4ADE80?style=for-the-badge)](https://github.com/Turzo02/Bangla_Kor/releases)
[![License](https://img.shields.io/badge/License-Free-FFD166?style=for-the-badge)](https://github.com/Turzo02/Bangla_Kor)

Made with ♥ by **Turzo**

</div>

---

## ⬇️ Download

**[👉 Download the latest release](https://github.com/Turzo02/Bangla_Kor/releases/latest)**

| File | Description |
|------|-------------|
| `BanglaKor-Setup-v1.0.2.exe` | **Recommended** — Windows installer (~174 MB) |

**Requirements**
- Windows 10 or 11 (64-bit)
- No Python required
- No internet required
- Admin rights not required

---

## ✨ Features

- 🎯 **One-hotkey conversion** — `Ctrl + Shift + B` converts selected text instantly
- 🔒 **100% offline** — no internet, no API keys, no cloud
- 🧠 **Local AI model** — TinyTransliterator, runs on CPU
- 🛡️ **Protected content** — URLs, emails, filenames, git/CLI commands, and code blocks stay untouched
- 📝 **Full Bangla output** — Banglish AND English text both convert to বাংলা
- 🖥️ **System tray app** — runs silently in the background
- 🚀 **Auto-start with Windows** — optional, toggleable from tray menu
- 🎨 **Premium UI** — animated status notifications near the cursor
- 📋 **Clipboard-safe** — works with any focused input field

---

## 🎮 How to use

1. **Click** on any text field (browser, Notepad, WhatsApp, Discord, VS Code, etc.)
2. **Type Banglish naturally**

   ```text
   ami bhalo achi, tumi kemon acho?
   ```

3. **Press** `Ctrl + Shift + B`
4. **Done** — text becomes perfect বাংলা:

   ```text
   আমি ভালো আছি, তুমি কেমন আছো?
   ```

---

## 🧠 How it works

Bangla Kor uses a fine-tuned **TinyTransliterator** (a small Transformer model) to convert Banglish → বাংলা completely offline.

**Pipeline:**

```text
Focused text field
        ↓
Ctrl + Shift + B (global hotkey)
        ↓
Select all → copy to clipboard
        ↓
Smart analyzer (Banglish detection)
        ↓
Local AI model (Ro2Bn transliteration)
        ↓
Cleanup + preserve protected content
        ↓
Paste back
```

**Protected content** — the converter automatically leaves these untouched:
- Existing বাংলা text
- URLs (`https://...`, `www....`)
- Email addresses
- Filenames (`config.json`, `main.py`)
- File paths (`C:\Users\...`, `/home/...`)
- Git / CLI commands (`git commit -m "..."`, `pip install customtkinter`)
- Inline code (`...`) and code blocks

---

## 🏗️ Project structure

```text
Bangla_Kor/
├── main.py                  # Entry point — wires everything together
├── config.py                # Constants + paths
├── state.py                 # Shared runtime state (queues, locks)
├── post_build.py            # Post-build helper (VC++ DLL copy)
├── BanglaKor.spec           # PyInstaller spec
├── BanglaKor.iss            # Inno Setup installer script
├── bangla-kor-icon.ico      # App icon
│
├── platform_win/            # Windows-specific helpers
│   ├── api.py               # ctypes API setup + argtypes
│   ├── hotkey.py            # Global hotkey (own thread)
│   ├── input.py             # SendKeys / clipboard
│   ├── startup.py           # Auto-start registry
│   └── single_instance.py   # Mutex
│
├── core/                    # Text processing
│   ├── protect.py           # Protected words + patterns
│   ├── analyzer.py          # Banglish detection
│   └── model.py             # Local model load + conversion
│
├── ui/                      # User interface
│   ├── toast.py             # Animated status HUD
│   ├── window.py            # Welcome window
│   └── tray.py              # System tray
│
├── local_model/             # AI model (bundled in release)
│   ├── infer.py
│   └── model/ro2bn_ft/
│       ├── best_model.pt
│       ├── config.json
│       ├── src_vocab.json
│       └── tgt_vocab.json
│
└── vc_runtime/              # VC++ DLLs for clean-Windows support
```

---

## 🛠️ Build from source

### Prerequisites

- Python 3.11 – 3.14
- Visual C++ Redistributable (usually preinstalled on Windows 10/11)

### Setup

```bash
git clone https://github.com/Turzo02/Bangla_Kor.git
cd Bangla_Kor

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### Run from source

```bash
python main.py
```

### Build the Windows executable

```bash
pyinstaller BanglaKor.spec --clean --noconfirm
python post_build.py
```

### Build the installer

Install [Inno Setup 6](https://jrsoftware.org/isdl.php), then:

```bash
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" BanglaKor.iss
```

Output:

```text
installer/BanglaKor-Setup-v1.0.2.exe
```

---

## 📋 Requirements

```text
customtkinter
pyperclip
Pillow
torch
numpy
pyinstaller
pefile
```

---

## 🐛 Troubleshooting

**App won't start / model load error**
- Make sure `local_model/model/ro2bn_ft/` contains all 4 files
- On clean Windows installs, ensure `vc_runtime/` DLLs are present next to `BanglaKor.exe`

**Hotkey does not work**
- Another app may already use `Ctrl + Shift + B`
- Restart the app or the PC

**Text conversion produces wrong output**
- The model is trained on common Banglish patterns. Very unusual spellings may not convert correctly.
- Protected content (URLs, emails, filenames, CLI commands, code blocks) is intentionally preserved as-is.

---

## 📝 Changelog

### v1.0.2
- 🎯 **+12% accuracy** (85% → 97%)
- 🐛 Fixed pure English sentences being wrongly converted
- 🐛 Fixed URLs / emails / filenames / git commands not protected
- 🐛 Fixed bracket numbers `[01]` hallucinating random symbols
- 🐛 Fixed word spacing in mixed sentences
- ✨ Frequency-based English dictionary (~29K words)
- ✨ Smart word-level preservation in mixed sentences
- ✨ Common Banglish tech words (`office`, `boss`, `code`, `project`) now convert
- ✨ Family words (`ma`, `baba`, `mon`, `dada`) converted correctly

### v1.0.1
- 🎨 Premium UI redesign (welcome window + toast)
- 🏗️ Code refactor into clean modules
- 🐛 Fixed customtkinter 5.2.x API compatibility
- 🐛 Fixed GIL crash on UI drag
- 🔧 64-bit safe Windows API calls
- ⚡ 3× lower idle CPU usage
- 📦 Bundled VC++ runtime DLLs for clean-Windows installs
- 🚀 Inno Setup installer (per-user, no admin)

### v1.0.0
- Initial release

---

## 💛 Credits

- **Model:** TinyTransliterator (fine-tuned by Turzo)
- **UI:** [customtkinter](https://github.com/TomSchimansky/CustomTkinter)
- **Bundler:** [PyInstaller](https://pyinstaller.org/)
- **Installer:** [Inno Setup](https://jrsoftware.org/isinfo.php)

---

## 📄 License

Free for personal and educational use.

---

<div align="center">

**⭐ If Bangla Kor helped you, consider starring the repo!**

[Report Bug](https://github.com/Turzo02/Bangla_Kor/issues) · [Request Feature](https://github.com/Turzo02/Bangla_Kor/issues) · [Releases](https://github.com/Turzo02/Bangla_Kor/releases)

</div>
