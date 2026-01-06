# 🎮 VKit - Toolbox v2.5

**Advanced GTA V utility suite with firewall control, heist solvers, autoclicker, and Discord webhook integration.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/) 
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Usage](#-usage)
- [Hotkeys Reference](#-hotkeys-reference)
- [Requirements](#-requirements)
- [Credits](#-credits)

---

## ✨ Features

### 🔥 Core Features
- **NO SAVE MODE**: Block/unblock cloud save servers via firewall rules
- **Overlay System**: Full-screen or mini glowing orb indicator
- **Auto-hide**: Overlay disappears when GTA V loses focus
- **Sound Effects**: Audio feedback for state changes

### ⚡ Tools
- **Fast Autoclicker**
- **Snack Spammer**: Automated snack consumption (Hold TAB)
- **Process Killer**: Instant GTA5 process termination

### 🎰 Heist Solvers (Optional)
- Casino Fingerprint Solver (F5)
- Casino Keypad Solver (F6)
- Cayo Perico Fingerprint Solver (CTRL+F5)
- Cayo Perico Voltage Solver (CTRL+F6)

### 🚀 Exploits (Optional)
- Job Warp Exploit (CTRL+ALT+J)

---

## 📦 Installation

### 1. Clone Repository
```bash
git clone https://github.com/ItsCEED/vkit-toolbox
cd vkit-toolbox
```


### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Script

```bash
python main.py
```

### 3.1 Or Build in to executable 

```bash
python -m nuitka --standalone --onefile --windows-icon-from-ico=icon.ico --windows-uac-admin --enable-plugin=tk-inter --include-data-dir=assets=assets --output-filename=VKit.exe --product-name="GTA V VKit Toolbox" --product-version=1.0.0.0 --file-version=1.0.0.0 --file-description="GTA V VKit" --copyright="2026" --remove-output --assume-yes-for-downloads main.py
```

**⚠️ Administrator privileges required for firewall control!**

---


## 🎮 Usage

### Starting the Application

```bash
python main.py          # Normal mode
python main.py --debug  # Debug mode (shows keypresses)
```
### 🎮 Usage if executable

Right Click > Run As Administrator
### Basic Workflow

1. **Launch script** → Run as administrator
2. **Enable NO SAVE** → Press `CTRL+ALT+F9`
3. **Toggle overlay** → Press `CTRL+ALT+F8` (Full ↔ Mini)
4. **Use tools** → See hotkeys below
5. **Disable NO SAVE** → Press `CTRL+ALT+F12`
6. **Exit** → Press `CTRL+C` in console

---

## ⌨️ Hotkeys Reference

### Core Controls

| Hotkey | Action |
| :-- | :-- |
| `CTRL + ALT + F8` | Toggle overlay mode (Full ↔ Mini) |
| `CTRL + ALT + F9` | Enable NO SAVE (Block IP) |
| `CTRL + ALT + F12` | Disable NO SAVE (Unblock IP) |
| `CTRL + ALT + D` | Toggle debug mode |

### Tools

| Hotkey | Action |
| :-- | :-- |
| `CTRL + ALT + K` | Toggle autoclicker |
| `CTRL + ALT + C` | Toggle snack spammer (Hold TAB) |
| `CTRL + ALT + ]` | Kill GTA5 process instantly |
| `CTRL + ALT + J` | Job Warp exploit (if available) |

### Heist Solvers

| Hotkey | Action |
| :-- | :-- |
| `F5` | Casino Fingerprint Solver |
| `F6` | Casino Keypad Solver |
| `CTRL + F5` | Cayo Perico Fingerprint Solver |
| `CTRL + F6` | Cayo Perico Voltage Solver |

---



## 🤝 Credits

**Community:** [GTAGlitches Discord](https://discord.gg/rgtaglitches)

### Special Thanks
- [Crest Companion](https://github.com/Abosmra/Crest-Companion-Tool) for the solvers
- [ElectroBytezLV](https://www.reddit.com/user/ElectroBytezLV/) for the original nosave ahk.

---

## ⚠️ Disclaimer

**This tool is for educational purposes only.**
Use at your own risk. The developers are not responsible for:

- Account bans or suspensions
- Game file corruption
- Unintended side effects

**Always backup your game saves before using any modifications.**

---

## 🌟 Support

Found a bug? Have a feature request?

- **Issues**: [GitHub Issues](https://github.com/yourusername/vkit-toolbox/issues)
- **Discord**: [Join GTAGlitches](https://discord.gg/rgtaglitches)

---

**Made with ❤️ for the GTA V community**
