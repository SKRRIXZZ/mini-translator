# 🌐 Mini Translator

Lightweight clipboard translator with a global hotkey. Press the hotkey after `Ctrl+C` and get a popup with the translation instantly.

**English** | [Русский](README.ru.md)

---

## ✨ Features
- Global hotkey: `Ctrl+Shift+Q` / `Ctrl+Alt+Q`
- Translates clipboard content into a popup
- Auto-detects source language
- 4 translation services with automatic fallback:
  Google → Lingva → Lingva mirror → MyMemory
- Full clipboard wipe button
- 20 interface languages
- Dark / light theme
- Autostart with Windows

---

## ✅ Requirements
- Windows 10 or 11
- Internet connection
- **Python 3.11 or newer** — required even if you use the `.exe` version

---

## 🚀 Installation

### Step 1 — Install / update Python (always, one command)

Open **CMD** (`Win + R` → `cmd` → Enter):

```cmd
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements & winget upgrade --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
```

Then **close and reopen CMD** and verify:

```cmd
py -3 --version
```

### Step 2 — Update pip, setuptools, wheel (always, one command)

```cmd
py -3 -m pip install --upgrade pip setuptools wheel
```

---

## 📥 Installing the app

### 🟢 A. If you have the `.exe` file
Double-click `MiniTranslator.exe`. Done.

### 🟡 B. If you have the `.pyw` file
```cmd
py -3 -m pip install --upgrade pystray Pillow
pythonw mini_translator_multilang.pyw
```

### 🔴 C. If you have a `.bat` that builds `.exe`
```cmd
py -3 -m pip install --upgrade pyinstaller pystray Pillow
```
Then double-click the `.bat`. The `.exe` appears in `dist\`.

---

## ▶️ Usage
1. Select text in any program.
2. Press `Ctrl+C`.
3. Press `Ctrl+Shift+Q` (or `Ctrl+Alt+Q`) — a popup appears with the translation.
4. Press **Copy** in the popup, or press `Esc` to close.

You can also open the main window and type text manually, then press **Translate**.

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| `'py' is not recognized` | Reinstall Python with PrependPath (see weather README) |
| `pip` not found | Use `py -3 -m pip ...` |
| Hotkeys do not work | Another program holds them. Use **📋 Translate clipboard** button in the main window |
| Translation fails | Check internet. The app tries 4 services in a row |
| Clipboard is empty | Always press `Ctrl+C` first — the hotkey does not copy text itself |

---

## 📜 License
MIT
