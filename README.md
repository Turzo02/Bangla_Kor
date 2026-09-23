# 🔤 Bangla Kor

**Banglish → বাংলা — instantly, anywhere on Windows.**

Bangla Kor is a lightweight Windows utility that converts Banglish (Romanized Bengali) text into Bengali script using a **local AI model**.

## ✨ Features

* `Ctrl + Shift + B` global shortcut
* Works in supported Windows text fields
* 100% offline
* Local AI inference
* Existing Bengali text preserved
* URLs, emails and technical/code content protected
* Long text handled with safe chunking
* System tray support
* Start with Windows option
* Minimal modern interface
* Conversion status HUD
* No internet connection required

## 🧠 AI Engine

Bangla Kor uses a local PyTorch-based character-level Transformer model for Roman-to-Bangla transliteration.

**Model:** `nahidstaq/bangla-transliteration`
**License:** MIT

## 🚀 How to Use

1. Install Bangla Kor.
2. Open any supported text field.
3. Type or paste Banglish text.
4. Press `Ctrl + Shift + B`.
5. The selected text will be converted to Bengali.

Example:

```text
ami ajke tomar sathe dekha korte chai
```

becomes:

```text
আমি আজকে তোমার সাথে দেখা করতে চাই
```

## 📴 Offline First

Bangla Kor does not require Gemini API access or an internet connection for text conversion.

The AI model runs locally on the user's computer using CPU inference.

## 🛠️ Project Structure

```text
Bangla Kor/
├── main.py
├── BanglaKor.spec
├── BanglaKor.iss
├── bangla-kor-icon.ico
├── local_model/
│   ├── infer.py
│   └── model/
│       └── ro2bn_ft/
│           ├── best_model.pt
│           ├── config.json
│           ├── src_vocab.json
│           └── tgt_vocab.json
├── README.md
└── .gitignore
```

## 👨‍💻 Author

**Made with ❤️ by Turzo**

Built as a personal offline utility project with a focus on practical Windows automation, local AI and a simple user experience.

## 🤝 Credits

Bangla transliteration model:

**Md Nahid Hasan (@nahidstaq)**

Model: `nahidstaq/bangla-transliteration`

Training data is based on the BanglaTLit dataset.

## 📄 License

This project is released under the MIT License.

The bundled transliteration model is provided under its own MIT license. Please retain the original model attribution and license information when redistributing the model.
