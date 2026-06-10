<p align="center">
  <img src="assets/banner.png" alt="UsageTracker Banner" width="800">
</p>

<h1 align="center"><img src="assets/logo.png" width="48" alt="Logo"> UsageTracker</h1>

<p align="right">
  <a href="README.zh-CN.md">中文</a> | English
</p>

<p align="center">
  <b>Linux-first Desktop Usage Time Tracker</b><br>
  Lightweight background daemon that silently records your screen time
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.4.0--linux--prerelease-blue" alt="Version">
  <img src="https://img.shields.io/badge/platform-Linux%20%28X11%2FXWayland%29-1793D1" alt="Platform">
  <img src="https://img.shields.io/badge/license-GPL--3.0-green" alt="License">
  <img src="https://img.shields.io/badge/lang-English%20%7C%20%E4%B8%AD%E6%96%87-orange" alt="Languages">
  <img src="https://img.shields.io/badge/headless-ready-brightgreen" alt="Headless Ready">
</p>

---

## 🎯 Quick Start (Source Code)

> **Linux-first, no exe, no installer — just git clone and run.**

```bash
# 1. Clone the repository
git clone https://github.com/GiftedScout/UsageTracker.git
cd UsageTracker

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
#    Core (daemon + WebUI only): pip install psutil
#    Full (with system tray):    pip install -r requirements.txt
pip install psutil

# 4. Start the daemon (headless, no tray)
./bin/usagetracker daemon

# 5. Open WebUI settings in your browser
#    → http://127.0.0.1:19234/settings
```

> **Note:** The program runs as a background daemon. Close the browser tab — the tracker keeps running.
> To stop: `./bin/usagetracker stop` or `python -m src.main stop` (from the repository root).

---

## 🖥️ CLI Interface

The CLI is fully functional. From the repository root you can use `python -m src.main`; from any working directory use the absolute `bin/usagetracker` wrapper (for example `/path/to/UsageTracker/bin/usagetracker status`):

```bash
# Start headless daemon (no tray)
./bin/usagetracker daemon

# Start with system tray (if pystray + Pillow installed)
./bin/usagetracker daemon --tray

# Open WebUI settings in browser
./bin/usagetracker web

# Show today's usage summary
./bin/usagetracker today

# Check daemon status
./bin/usagetracker status

# Gracefully stop the daemon
./bin/usagetracker stop

# View help
python -m src.main --help
```

See [docs/roadmap-v0.3.0.md](docs/roadmap-v0.3.0.md) for the full Linux Phase 1 plan.

---

## 🌐 WebUI Settings (Primary Configuration)

The settings interface runs as a local web server at **`http://127.0.0.1:19234`**.

Open it in any browser to configure all aspects of the tracker:

| Feature | Description |
|:--------|:------------|
| **General** | Language switch, auto-start toggle, auto-show yesterday's report |
| **App Categories** | View/edit custom categories, assign running processes to categories |
| **Browser Management** | View recognized browsers (7 built-in), add custom browsers manually |
| **Project Directories** | Configure frequently used development/work project directories for Linux-first context analysis |
| **Ignore List** | Add programs to exclude from tracking (pick from running processes) |
| **Database Management** | View DB size & record count, preview recent data, clean old data, backup DB |
| **Feedback & Logs** | Adjust log level (DEBUG/INFO/WARNING/ERROR), view runtime logs, submit feedback |

> The settings page is fully bilingual (English / 中文). Theme: 🌸 Fairy Tale or 💼 Geek.

---

## 🔔 Notifications

- **Ubuntu/Linux Desktop:** Uses `notify-send` for usage reminders (e.g., "You've been using Firefox for 1 hour").
- **Fallback:** If `notify-send` is unavailable, notifications degrade gracefully with a log message (no crash).

---

## 🔲 Optional: System Tray Icon

The system tray icon is **optional** and does not block daemon operation:

- **Install tray deps:** `pip install pystray Pillow`
- **Linux system tray required:** The tray icon needs a tray host (GNOME Extension `appindicator`, `trayer`, `tint2`, etc.)
- **Without tray:** The daemon still tracks, serves WebUI, and sends notifications normally.
- **Start with tray:** `python -m src.main` (current) or `usage-tracker daemon --tray` (planned).

If `pystray` is not installed, the daemon prints a log message and continues without the tray.

---

## ❌ Non-Goals (Phase 1)

| Item | Status |
|:-----|:-------|
| ❌ Windows exe / Inno Setup installer | **Not planned** — Linux source-only distribution |
| ❌ Windows source alignment | **Not planned** — linux-port branch diverges from Windows main |
| ❌ Game-first classification | **Not planned** — Linux default: Development, Terminal, Browser, Communication, etc. |
| ❌ Native GNOME Wayland window detection | **Phase 2+** — Phase 1 accepts XWayland-only with graceful degradation |
| ❌ AppIndicator tray on Wayland | **Phase 2+** — Phase 1: X11/XWayland tray only, non-blocking |
| ❌ systemd user service auto-install | **Future** — XDG autostart used in Phase 1 |

---

## 📁 Project Structure

```
UsageTracker/
├── src/                      # Core Python modules
│   ├── main.py               # Entry point: tracker → bridge → (optional) tray
│   ├── tracker.py            # Foreground window tracker (Linux: xprop polling)
│   ├── app_classifier.py     # App categorization (Linux-first defaults)
│   ├── bridge_handler.py     # HTTP server (127.0.0.1:19234) + WebUI + REST API
│   ├── notifier.py           # Usage time notifications (notify-send on Linux)
│   ├── platform_utils.py     # Cross-platform abstraction (Linux: xprop, fcntl, XDG)
│   ├── data_store.py         # SQLite data layer (zero platform coupling)
│   ├── reporter.py           # Daily/weekly/monthly HTML report generator
│   ├── config_manager.py     # JSON config management
│   ├── singleton.py          # Single-instance protection (Linux: fcntl file lock)
│   ├── startup_manager.py    # Auto-start (Linux: XDG autostart .desktop)
│   ├── tray_app.py           # pystray system tray (optional, lazy-loaded)
│   ├── constants.py          # Global constants & XDG-aware paths
│   ├── crash_handler.py      # Crash handling & logging
│   ├── onboarding_web.py     # First-run onboarding page
│   ├── updater.py            # Update check
│   ├── i18n.py               # Internationalization (zh-CN / en)
│   └── version.py            # v0.4.0-linux-prerelease
├── ui/web/                   # WebUI (HTML/CSS/JS)
│   ├── index.html            # Settings page (bilingual)
│   ├── js/app.js             # Front-end logic (REST API client)
│   └── css/                  # Dual themes (fairy-tale.css, geek.css)
├── assets/                   # Static resources (icons, Chart.js, report themes)
├── docs/                     # Design docs & roadmaps
├── bin/                      # Linux entry scripts (planned)
├── requirements.txt          # Python dependencies (core + optional)
└── LICENSE                   # GPL-3.0
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|:------|:-----------|
| Language | Python 3.11+ |
| UI | Web UI (HTML/CSS/JS) + optional pystray (system tray) |
| Database | SQLite (stdlib) |
| Charts | Chart.js (embedded in reports) |
| i18n | Custom JSON-based lightweight module |
| System tools | `xprop` (foreground window), `notify-send` (notifications) |
| Core dep | `psutil` — system process information |
| Optional deps | `pystray` + `Pillow` — system tray icon |
| Distribution | **git clone + venv** (no exe, no installer) |

---

## 🗺️ Roadmap

- [x] **v0.1.0–v0.3.0** — Windows origin: bug fixes, bilingual support, WebUI migration
- [x] **v0.4.0-linux-prerelease** — Linux port: cross-platform abstraction, XDG paths, notify-send, X11 tracking
- [ ] **Phase 1a** — CLI daemon entry, WebUI-first, tray optional, pidfile stop
- [ ] **Phase 1b** — Linux notifications, XDG autostart, browser detection
- [ ] **Phase 1c** — Optional AppIndicator tray (GNOME Wayland)
- [ ] **Phase 2+** — Native Wayland window detection, systemd service, plugins

---

## 🔗 Links

| Type | Link |
|:-----|:-----|
| GitHub Repository | https://github.com/GiftedScout/UsageTracker |
| License | [GPL-3.0](LICENSE) |
| Design Report | [docs/design-report-v0.1.0-beta.md](docs/design-report-v0.1.0-beta.md) |
| Linux Port Plan | [docs/roadmap-v0.3.0.md](docs/roadmap-v0.3.0.md) |

---

<p align="center">
  <sub>Built with ❤️ by chaos · Licensed under GPL-3.0 · Linux-first edition</sub>
</p>
