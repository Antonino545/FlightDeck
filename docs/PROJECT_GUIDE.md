# ✈️ FlightDeck — Developer & Agent Guide

> **IMPORTANT FOR AI AGENTS & DEVELOPERS:**
> Read this document first before making changes. It contains the project architecture, operational rules, and the **mandatory 4-step development workflow** to follow after every code modification.

---

## ⚡ Mandatory 4-Step Development Workflow (Execute on Every Change)

Whenever you make any change to code or configuration in this project, **always execute this complete workflow**:

### For macOS:
```bash
# 1. Run Unit Test Suite
/opt/miniconda3/bin/python3 -m unittest discover -s tests -v

# 2. Rebuild the macOS Native .app Bundle
/opt/miniconda3/bin/python3 build_macos_app.py

# 3. Close the running instance and reopen the freshly built .app
pkill -f "FlightDeck" 2>/dev/null; sleep 1; open /Applications/FlightDeck.app

# 4. Verify running process and inspect live logs
sleep 2 && ps aux | grep -i "[F]lightDeck" && echo "---" && tail -15 ~/.flightdeck/flightdeck.log
```

### For Linux (Ubuntu/Debian):
```bash
# 1. Run Unit Test Suite
python3 -m unittest discover -s tests -v

# 2. Build the Ubuntu .deb package
bash scripts/build_ubuntu_deb.sh

# 3. Optional: Build Flatpak bundle
bash scripts/build_flatpak.sh

# 4. Install and run (if testing installation)
sudo apt-get install --reinstall ./deb_dist/flightdeck_*_amd64.deb
pkill -f "flightdeck" 2>/dev/null; sleep 1; flightdeck &

# 5. Verify live logs
tail -15 ~/.flightdeck/flightdeck.log
```

### For Windows:
```powershell
# 1. Run Unit Test Suite
python -m unittest discover -s tests -v

# 2. Build the Windows Setup Installer (requires Inno Setup: choco install innosetup)
python scripts/build_windows_release.py

# 3. Run and verify installer
./dist/FlightDeck-Setup.exe
```

> ⚠️ **IMPORTANT COMMIT RULE**:
> **DO NOT automatically commit changes.** Only commit to Git when explicitly requested by the user.

---

## 🏗️ Architecture & Core Components

```
FlightDeck/
├── main.py                        # App entry point (cross-platform dispatch)
├── build_macos_app.py             # Custom build script compiling C launcher Mach-O & bundling app (macOS)
├── scripts/
│   ├── build_ubuntu_deb.sh        # Debian/Ubuntu .deb package builder for Linux (Wayland/X11)
│   ├── build_windows_release.py   # PyInstaller & Inno Setup installer builder for Windows
│   └── install_linux_deps.sh      # Installs system dependencies for Linux
├── packaging/
│   ├── flatpak/                   # Flatpak manifests and desktop definitions
│   └── windows/
│       └── flightdeck.iss         # Inno Setup installer script for Windows
├── assets/                        # App icons (PNG, ICNS & ICO), audio files
├── core/
│   ├── domain/
│   │   ├── models.py              # CalendarEvent / Meeting, EventTime, Location, MeetingLink, TravelPlan, PresenceStatus, EventPresentation
│   │   ├── clock.py               # Clock protocol, SystemClock, FakeClock
│   │   ├── state_machine.py       # EventState lifecycle machine & state resolver
│   │   ├── reminder_policy.py     # Strategy-based ReminderPolicy & ReminderPolicyRegistry
│   │   ├── capabilities.py        # EventCapabilities presentation flags
│   │   ├── context_engine.py      # Context Engine & "Why?" Transparency Engine (TransitionGuidance, ActionType)
│   │   └── classifier.py          # Smart keyword matching, category classification & video URL extraction
│   ├── providers/
│   │   ├── base.py                # BaseCalendarProvider abstract class
│   │   ├── eventkit_provider.py   # Native Apple EventKit bridge (macOS)
│   │   └── caldav_provider.py     # CalDAV/ICS provider with RRULE expansion, TZID & fallback cache
│   ├── services/
│   │   ├── database_service.py    # Centralized ACID SQLite store (~/.flightdeck/flightdeck.db)
│   │   ├── notification_service.py # Unified NotificationProvider protocol (Mascot, System, Sound, Composite)
│   │   ├── calendar_service.py    # Synchronizes & caches Today-only events via MeetingRepository
│   │   ├── reminder_engine.py     # Multi-stage notification triggers (evaluates leave vs start time)
│   │   ├── state_store.py         # NotifiedStateStore & BannerHistoryStore backed by SQLite
│   │   ├── eta_service.py         # Apple Maps route URLs & departure time calculator
│   │   ├── arrival_service.py     # Multiplatform presence detection (call apps, venue Wi-Fi, diagnostics)
│   │   ├── config_service.py      # Configuration manager (~/.flightdeck/config.json)
│   │   └── event_bus.py           # Decoupled pub/sub event system
│   └── logger.py                  # Dual console & file logger (~/.flightdeck/flightdeck.log)
├── ui/
│   ├── app_launcher.py            # Platform-aware UI dispatcher
│   ├── common/                    # Cross-platform UI helpers
│   │   ├── theme.py               # Central Catppuccin Mocha palette & pilot mappings (Single source of truth)
│   │   ├── tray_viewmodel.py      # Status formatting & stage logic
│   │   ├── agenda_viewmodel.py    # Cross-platform AgendaEventVM & CommandCenterVM (NOW / NEXT / LATER)
│   │   ├── banner_queue.py        # Cross-platform banner sequencing queue
│   │   └── banner_presets.py      # Cross-platform test & update mock banner presets
│   ├── macos/                     # macOS Native UI (PyObjC, AppKit, Quartz 2D)
│   │   ├── theme.py               # Catppuccin Mocha AppKit NSColor/CGColor palette
│   │   ├── menu_bar_app.py        # NSStatusItem status bar controller & dropdown
│   │   ├── dashboard_window.py    # Native NSWindow Flight Deck HUD
│   │   ├── dashboard_tabs/        # Native AppKit Tab Views (Agenda, Hangar, Settings)
│   │   ├── banner_window.py       # NSWindow overlay wrapper
│   │   └── banner/                # Quartz 2D animated HUD banners
│   │       ├── banner_controller.py
│   │       ├── banner_view.py
│   │       ├── quiet_banner_view.py
│   │       └── renderers/         # Modular CoreGraphics pilot renderers
│   └── linux/                     # Linux / Ubuntu UI (PyQt6, Wayland / X11)
│       ├── qt_tray_app.py         # PyQt6 QSystemTrayIcon menu & status
│       ├── qt_dashboard.py        # PyQt6 Flight Deck window
│       └── banner/                # PyQt6 animated banner overlay
│           ├── qt_banner.py
│           └── renderers/         # Modular PyQt6 pilot renderers
└── tests/                         # Full automated unit test suite (195+ tests)
```

---

## 📌 Critical Design Decisions & Rules

### 1. Cross-Platform Runtime, macOS Mach-O Embedding & TCC Code Signing
- **Rule**: Code must be cross-platform using `sys.platform` checks. Linux uses standard Python entry points (e.g., Wayland/Qt/AppIndicator) while macOS requires a specialized build.
- **macOS Exception (Mach-O)**: When building `FlightDeck.app`, the launcher stub in `build_macos_app.py` compiles a native C Mach-O binary that loads `libpython3.13.dylib` via `dlopen`/`dlsym` and invokes `Py_Main` in-process.
- **Why (macOS)**: Calling `execv` to a shell script or external interpreter breaks macOS bundle association and causes the top macOS menu bar (`FlightDeck`, `Edit`, `Window`, `Help`) to disappear.
- **TCC Permission Persistence**: macOS codesigning must include an explicit Designated Requirement (`-r '=designated => identifier "com.flightdeck.app"'`). Without this, ad-hoc codesigning binds permissions to the binary's `cdhash`, which causes macOS TCC to prompt for Calendar permissions after every update or rebuild.

### 2. Strict Today-Only Calendar Filter
- **Rule**: `CalendarService` only fetches and evaluates events scheduled for **Today** (`00:00:00` to `23:59:59`).
- **Why**: Events for tomorrow must **never** appear in Today's Agenda, must not be picked as "Next Event" 24 hours in advance, and must not trigger premature notifications.

### 2a. Cache-First UI and Background Providers
- **Rule**: Startup must render the persisted calendar cache before waiting for EDS, EventKit, or CalDAV.
- **Rule**: Calendar provider fetches, parsing, and calendar metadata discovery run outside the Qt/AppKit main thread. UI updates return through `EventBus` or platform-native signals.
- **Rule**: A failed refresh preserves the last valid cache and does not launch overlapping retry workers.
- **Rule**: On Linux, `EDSCalendarProvider` must cache connected `ECal.Client` instances and connect to uncached sources concurrently to prevent sequential timeout stalls.

### 2b. Responsive Linux Startup
- **Rule**: Do not force `QT_QPA_PLATFORM=xcb` for Wayland sessions. Set it only when `FLIGHTDECK_QT_XCB` is explicitly enabled.
- **Rule**: Notification banners are rendered by a dedicated XCB/XWayland helper process when the main Qt application is native Wayland, because native Wayland does not permit animated top-level window positioning.
- **Rule**: The Flight Deck must show a loading, empty, or recovery state before optional tabs, provider discovery, updater checks, or presence detection complete.
- **Rule**: Dashboard construction failures must remain visible through a retryable error window; logging alone is not an acceptable startup failure experience.
- **Rule**: The updater runs once after the first Qt event-loop turn, and `AppController` starts at most one polling loop.

### 3. Transit / Travel Events vs Video Calls
- **Travel / Transit Events (`is_travel=True`, `departure_time` set)**:
  - Notification stages (e.g. 45m, 30m, 15m, 5m, 0m) evaluate relative to the **Leave / Departure Time** (`departure_time`), not the event start time.
  - Stage 0m = *"🚨 Time to Leave! 🚗"*.
- **Online Meetings & Regular Events (`is_travel=False`)**:
  - Notification stages evaluate relative to the **Event Start Time** (`start_time`).

### 4. Duration & Time Formatting
- **Rule**: Always use `format_duration(minutes, long_form=False)` from `core.domain.models`:
  - `120 min` → `2h` (or `2 hours`)
  - `90 min` → `1h 30m`
  - `60 min` → `1h`
  - `45 min` → `45m`

### 5. Menu Bar Live Status Modes & 3-Hour Lookahead Cap
- **Modes**:
  - `countdown` (Default): Dynamic countdown (`Leave in 18m (Dinner)` / `in 25m: Sync` / `🟢 Sync (15m left)`).
  - `event_time`: Start time and title (`20:00 Dinner (~25m)`).
  - `time_only`: Time with countdown (`20:00 in 25m`).
  - `icon_only`: Minimal icon (`🦆` or pilot emoji).
- **Lookahead Cap (`max_countdown_lookahead_hours: 3`)**:
  - If the next event is more than 3 hours away, the menu bar displays a clean event start time (`20:00 [Title]`) instead of long countdowns (`in 11h15m`).
  - Once within 3 hours, it automatically transitions to active live countdown.
- **Immediate EventBus Sync**:
  - Changing mode in dropdown or Flight Deck Preferences fires `event_bus.publish("CONFIG_CHANGED")` to immediately update the tray title without delay.

### 6. Cross-Platform UI Parity Invariant
- **Rule**: Whenever UI components, layout structures, settings cards, or visual styling are added or modified on macOS (`ui/macos/`), always replicate and maintain identical design, hierarchy, and functionality on Linux/Ubuntu (`ui/linux/`), and vice-versa. Both platforms must stay visually consistent under Catppuccin Mocha theme.

### 7. Platform Packaging Isolation
- **Rule**: Distribution builds must exclusively contain the target platform's UI layer and common design tokens:
  - **macOS (`FlightDeck.app`)**: Packages only `ui/macos/` and `ui/common/`. The Qt UI tree (`ui/linux/`) is excluded.
  - **Linux (`.deb` & Flatpak)**: Packages only `ui/linux/` and `ui/common/`. The Cocoa/AppKit UI tree (`ui/macos/`) is excluded.
  - **Windows**: PyInstaller packaging excludes `ui.macos`.
  - **Shared Presets**: Test and update presets must live in `ui/common/banner_presets.py` to avoid cross-platform dependencies.

---

## 💻 CLI Flags & Runtime Options

| Flag | Description | Example |
| :--- | :--- | :--- |
| *(no flags)* | Launches the default platform UI (AppKit on macOS, PyQt6 on Linux/Windows). | `python3 main.py` |
| `-c`, `--check`, `--diagnostics` | Runs a complete system health and arrival diagnostics check with clear actionable report. | `python3 main.py --check` |
| `--qt` | Forces the PyQt6 UI runtime on macOS (useful for development and cross-platform testing). | `python3 main.py --qt` |
| `--silent` | Launches in background / menu bar without opening the Flight Deck dashboard window. | `python3 main.py --silent` |
| `--test` | Runs a standalone banner test without starting background loops. | `python3 main.py --test` |
| `--pilot <name>` | *(With `--test`)* Selects pilot mascot skin (`duck`, `owl`, `bunny`). | `python3 main.py --test --pilot duck` |
| `--stage <0-3>` | *(With `--test`)* Simulates specific reminder stage. | `python3 main.py --test --stage 0` |
| `--delay <sec>` | *(With `--test`)* Adds delay countdown before triggering banner. | `python3 main.py --test --delay 3` |
| `-d`, `--debug` | Activates debug mode logging and developer UI cards. | `python3 main.py --debug` |
| `-h`, `--help` | Displays command line usage options. | `python3 main.py --help` |

---

## 🧪 Testing Guidelines

Always run unit tests before building or committing:
```bash
/opt/miniconda3/bin/python3 -m unittest discover -s tests -v
```

Existing test suites:
- `tests/test_models.py` (Meeting model, serialization, `format_duration`)
- `tests/test_reminder_engine.py` (Stage evaluation, travel departure stages, arrival suppression)
- `tests/test_calendar_service.py` (EventKit extraction, ETA enrichment)
- `tests/test_classifier.py` (Keyword matching, pilot categories, URL extraction)
- `tests/test_eta_service.py` (Apple Maps route URLs, departure calculation)
- `tests/test_event_bus.py` (Publish/subscribe event isolation)
- `tests/test_config_service.py` (Default configuration, fallback handling)
- `tests/test_arrival_service.py` (Manual & presence arrival state)
- `tests/test_dashboard_ui.py` (UI rendering and app launcher routing)
- `tests/test_windows_compat.py` (Windows registry autostart, audio via winsound, process/Wi-Fi detection, os.startfile, updater)

---

## 🪟 Windows Setup & Execution

### Prerequisites
- Python 3.10+ (with "Add Python to PATH" enabled)
- Install requirements:
  ```powershell
  pip install -r requirements-windows.txt
  ```

### Running on Windows
Double-click `scripts\run_windows.bat` or run from terminal:
```powershell
python main.py
```

### Building Windows Standalone Release
```powershell
pip install pyinstaller pillow
python scripts/build_windows_release.py 1.0.0
```
This produces `FlightDeck-Windows.zip` containing the standalone executable and all required assets.
