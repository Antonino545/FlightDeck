---
name: flightdeck-workflow
description: Operating guide: architecture boundaries, reminder safety rules, verification, and hygiene.
trigger: always_on
---

# FlightDeck Agent Operating Guide

Reference: [docs/PROJECT_GUIDE.md](../../docs/PROJECT_GUIDE.md), [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md), [docs/CONFIGURATION.md](../../docs/CONFIGURATION.md).

## Fast Navigation & Prompt Protocol (Token & Time Efficiency)
- **Immediate Focus**: Act directly on the user's latest prompt. Never re-read, re-summarize, or dig through older turns in the chat history unless explicitly asked.
- **Docs First**: Always consult `docs/PROJECT_GUIDE.md` or `docs/ARCHITECTURE.md` first to locate the single file responsible for a feature.
- **Pinpoint Grep**: Use `grep_search` / `rg` for specific class or method names; do not open whole files blindly.
- **Bounded Reads**: When viewing code, use narrow `StartLine` and `EndLine` ranges (max 50–100 lines around target). Never read 500+ lines end-to-end.
- **Search Before Coding**: `rg -i "<concept>"` in `core/` and `ui/common/`. Check `requirements.txt` before writing new utilities.

## Protocol & Git
- Branch: `test` only (`git branch --show-current`). Run `git pull` before modifications.
- Preserve worktree user changes (`git status --short`).
- Keep changes narrow; update regression tests and docs in `docs/` for architectural/config changes.
- **Never auto-commit**: commit only on explicit user request; all unit tests must pass first.

## Architecture Boundaries
- `core/domain/`: Pure data classes and domain logic; no AppKit/Qt/external calendar APIs.
- `core/providers/`: Data ingestion. `core/services/`: Caching, ETA, reminders, persistence, event bus.
- `ui/macos/`: PyObjC/AppKit only. `ui/linux/`: PyQt6 only. `ui/common/`: Shared presentation logic & Catppuccin theme.
- **Cross-Platform UI Parity**: Keep visual styling and features matched across macOS and Linux/Windows.
- Service-to-UI: via `EventBus` only. UI handlers must accept the full payload (`event_dict`).

## Calendar & Reminder Invariants
- Calendar fetch, agenda, and reminders are strictly **today-only** in local timezone.
- Boundary entity: `Meeting` (`Meeting.to_dict()` / `from_dict()`).
- Reminder stages: `start_time` for standard events; `departure_time` for travel events.
- Startup catch-up: max 1 banner for today's most recent due event; never catch up all-day or arrived events.
- Preserve persisted notification state keys to prevent duplicate banners.
- Always use `format_duration()` for user-visible durations.

## macOS Constraints
- Preserve in-process Mach-O launcher in `build_macos_app.py`.
- Banner overlays must run on the AppKit main thread (non-activating, all-spaces panel).
- Python binary: `/opt/miniconda3/bin/python3`.

## Verification Workflow
Detect OS (`uname -s`):
- **macOS**:
  1. `/opt/miniconda3/bin/python3 -m unittest discover -s tests -v`
  2. `/opt/miniconda3/bin/python3 build_macos_app.py`
  3. `ditto "$PWD/FlightDeck.app" /Applications/FlightDeck.app`
  4. `pkill -f "FlightDeck" 2>/dev/null; sleep 1; open /Applications/FlightDeck.app`
  5. `sleep 2 && ps aux | grep -i "[F]lightDeck" && tail -15 ~/.flightdeck/flightdeck.log`
- **Linux**:
  1. `python3 -m unittest discover -s tests -v`
  2. `bash scripts/build_ubuntu_deb.sh`
  3. `sudo apt-get install --reinstall ./deb_dist/flightdeck_*_amd64.deb` (ask user approval)
  4. `pkill -f "flightdeck" 2>/dev/null; sleep 1; flightdeck &`
  5. `tail -15 ~/.flightdeck/flightdeck.log`

## Output Hygiene
- Be concise. Report outcome first, then test/build/restart status and files modified.
- Avoid repeating entire file dumps or restating rules.
