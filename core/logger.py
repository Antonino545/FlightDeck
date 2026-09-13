"""
Centralized logging and diagnostic system for FlightDeck.
Provides formatted console output, rotating file logs, global crash hooks,
threading exception catchers, and native macOS error alerts.
"""
import os
import sys
import logging
import traceback
import threading
import platform
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.expanduser("~/.flightdeck")
LOG_FILE = os.path.join(LOG_DIR, "flightdeck.log")
CRASH_FILE = os.path.join(LOG_DIR, "crash.log")

def _show_macos_error_dialog(title: str, message: str) -> None:
    """Displays a native macOS alert modal if a critical startup crash occurs."""
    try:
        import subprocess
        safe_title = title.replace('\\', '\\\\').replace('"', '\\"')
        safe_message = message.replace('\\', '\\\\').replace('"', '\\"')
        script = f'display alert "{safe_title}" message "{safe_message}" as critical buttons {{"OK"}} default button "OK"'
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
    except Exception:
        pass

def _global_exception_handler(exc_type, exc_value, exc_traceback):
    """Intercepts uncaught top-level exceptions, writes full crash report, and logs."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = "".join(tb_lines)

    crash_report = (
        f"\n{'='*70}\n"
        f"🚨 CRITICAL UNCAUGHT EXCEPTION — FLIGHTDECK CRASH REPORT\n"
        f"{'='*70}\n"
        f"Timestamp:        {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', (), None))}\n"
        f"Python:           {sys.version}\n"
        f"Executable:       {sys.executable}\n"
        f"Platform:         {platform.platform()} ({platform.machine()})\n"
        f"Working Dir:      {os.getcwd()}\n"
        f"Arguments:        {sys.argv}\n"
        f"Exception Type:   {exc_type.__name__}\n"
        f"Exception Msg:    {exc_value}\n"
        f"\nTraceback:\n{tb_text}\n"
        f"{'='*70}\n"
    )

    # Write to crash file
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(CRASH_FILE, "a", encoding="utf-8") as f:
            f.write(crash_report)
    except Exception:
        pass

    # Log to logger
    log = logging.getLogger("FlightDeck")
    log.critical(f"Uncaught Exception: {exc_value}\n{tb_text}")

    # Fallback to sys.stderr
    sys.stderr.write(crash_report)

    # If starting up or GUI active, alert the user
    short_msg = f"{exc_type.__name__}: {exc_value}\n\nCheck logs at {LOG_FILE}"
    _show_macos_error_dialog("FlightDeck Startup Error", short_msg)

def _threading_exception_handler(args):
    """Intercepts unhandled exceptions in background threads (Python 3.8+)."""
    tb_lines = traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
    tb_text = "".join(tb_lines)

    log = logging.getLogger("FlightDeck")
    log.error(
        f"💥 Unhandled exception in background thread '{args.thread.name}': "
        f"{args.exc_type.__name__}: {args.exc_value}\n{tb_text}"
    )

def setup_logging(level=None) -> logging.Logger:
    """Configures root logger with formatted console, rotating file handlers, and crash hooks."""
    if level is None:
        level = logging.DEBUG if os.environ.get("FLIGHTDECK_DEBUG", "").strip().lower() in ("1", "true", "yes", "on") else logging.INFO

    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception:
        pass

    root_logger = logging.getLogger("FlightDeck")
    root_logger.setLevel(level)

    for handler in root_logger.handlers:
        handler.setLevel(level)

    # Avoid duplicate handlers on reload
    if not root_logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Ensure stdout/stderr use utf-8 encoding on Windows to prevent charmap errors
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        if hasattr(sys.stderr, "reconfigure"):
            try:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        # 1. Console Stream Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 2. Rotating File Handler (max 5MB, up to 5 backups)
        try:
            file_handler = RotatingFileHandler(
                LOG_FILE,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8"
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            sys.stderr.write(f"Warning: could not initialize file logger: {e}\n")

    # Install global exception hooks
    sys.excepthook = _global_exception_handler
    if hasattr(threading, "excepthook"):
        threading.excepthook = _threading_exception_handler

    return root_logger

def log_system_diagnostics():
    """Logs complete environment diagnostics on startup for debugging."""
    log = logging.getLogger("FlightDeck.Diagnostics")
    log.info("=" * 60)
    log.info("🚀 FlightDeck Initializing")
    log.info(f"📍 Log File:       {LOG_FILE}")
    log.info(f"🐍 Python:         {sys.version.split()[0]} ({sys.executable})")
    log.info(f"💻 System:         {platform.platform()} ({platform.machine()})")
    log.info(f"📂 Working Dir:    {os.getcwd()}")
    log.info(f"⚙️  PID:            {os.getpid()}")
    log.info("=" * 60)

def open_log_file() -> bool:
    """Opens the active log file in the user's default text editor."""
    try:
        import subprocess
        if not os.path.exists(LOG_FILE):
            os.makedirs(LOG_DIR, exist_ok=True)
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("FlightDeck Log Initialized\n")
        if sys.platform == "win32":
            if hasattr(os, "startfile"):
                os.startfile(LOG_FILE)
            else:
                subprocess.run(["cmd", "/c", "start", "", LOG_FILE], shell=True, check=True)
        else:
            cmd = ["open", LOG_FILE] if sys.platform == "darwin" else ["xdg-open", LOG_FILE]
            subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to open log file: {e}")
        return False

def open_log_folder() -> bool:
    """Opens ~/.flightdeck in file manager."""
    try:
        import subprocess
        os.makedirs(LOG_DIR, exist_ok=True)
        if sys.platform == "win32":
            if hasattr(os, "startfile"):
                os.startfile(LOG_DIR)
            else:
                subprocess.run(["cmd", "/c", "start", "", LOG_DIR], shell=True, check=True)
        else:
            cmd = ["open", LOG_DIR] if sys.platform == "darwin" else ["xdg-open", LOG_DIR]
            subprocess.run(cmd, check=True)
        return True
    except Exception as e:
        logger.error(f"Failed to open log folder: {e}")
        return False

# Initialize global logger
logger = setup_logging()

