"""
Autostart / Launch-at-Login Management Subsystem for FlightDeck.
Supports native macOS 13+ SMAppService and universal Aqua LaunchAgents plist.
"""
import os
import platform
import sys
import subprocess
import logging
from typing import Optional

logger = logging.getLogger("FlightDeck.Autostart")

PLIST_LABEL = "com.flightdeck.app"
LEGACY_PLIST_LABEL = "com.flightdeck.app"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_LABEL}.plist")

IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = sys.platform == "win32"
LINUX_AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
LINUX_DESKTOP_FILE = os.path.join(LINUX_AUTOSTART_DIR, "flightdeck.desktop")

WINREG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WINREG_VAL_NAME = "FlightDeck"

def _get_windows_executable_cmd() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return f'"{sys.executable}" --silent --autostart'
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(project_dir, "main.py")
    py_dir = os.path.dirname(sys.executable)
    pyw = os.path.join(py_dir, "pythonw.exe")
    exec_bin = pyw if os.path.exists(pyw) else sys.executable
    return f'"{exec_bin}" "{main_py}" --silent --autostart'

def _is_autostart_enabled_windows() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINREG_RUN_KEY, 0, winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, WINREG_VAL_NAME)
            return bool(val)
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        logger.debug(f"Windows autostart check failed: {e}")
        return False

def _enable_autostart_windows() -> bool:
    try:
        import winreg
        cmd = _get_windows_executable_cmd()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINREG_RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.SetValueEx(key, WINREG_VAL_NAME, 0, winreg.REG_SZ, cmd)
            logger.info(f"✅ Successfully registered Windows autostart Run key: {cmd}")
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        logger.error(f"Failed to enable Windows autostart: {e}")
        return False

def _disable_autostart_windows() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINREG_RUN_KEY, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, WINREG_VAL_NAME)
            logger.info("Successfully removed Windows autostart Run key.")
            return True
        except FileNotFoundError:
            return True
        finally:
            winreg.CloseKey(key)
    except Exception as e:
        logger.error(f"Failed to disable Windows autostart: {e}")
        return False

def _get_linux_executable_path() -> str:
    # If installed via deb package, it's in /usr/bin/flightdeck
    # Otherwise fallback to python3 main.py
    if os.path.exists("/usr/bin/flightdeck"):
        return "/usr/bin/flightdeck"
    # fallback to source dir
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(project_dir, "main.py")
    return f"{sys.executable} {main_py}"

def _enable_autostart_linux() -> bool:
    try:
        os.makedirs(LINUX_AUTOSTART_DIR, exist_ok=True)
        exec_cmd = _get_linux_executable_path()
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=FlightDeck
Comment=Smart Schedule & Travel Reminders
Exec={exec_cmd} --silent --autostart
Icon=flightdeck
Terminal=false
StartupNotify=false
"""
        with open(LINUX_DESKTOP_FILE, "w", encoding="utf-8") as f:
            f.write(desktop_content)
        return True
    except Exception as e:
        logger.error(f"Failed to enable Linux autostart: {e}")
        return False

def _disable_autostart_linux() -> bool:
    try:
        if os.path.exists(LINUX_DESKTOP_FILE):
            os.remove(LINUX_DESKTOP_FILE)
        return True
    except Exception as e:
        logger.error(f"Failed to disable Linux autostart: {e}")
        return False



def _get_target_app_path() -> str:
    """Resolves the installed or running FlightDeck.app bundle path."""
    standard_app = "/Applications/FlightDeck.app"
    if os.path.exists(standard_app):
        return standard_app

    # Check if running within a bundle (macOS only)
    if sys.platform == "darwin":
        try:
            import AppKit
            bundle = AppKit.NSBundle.mainBundle()
            if bundle and bundle.bundlePath() and bundle.bundlePath().endswith(".app"):
                return bundle.bundlePath()
        except Exception:
            pass

    # Check project directory app bundle
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    local_app = os.path.join(project_dir, "FlightDeck.app")
    if os.path.exists(local_app):
        return local_app

    return standard_app


def generate_launchagent_plist(app_path: Optional[str] = None) -> str:
    """Generates the launchd Aqua session LaunchAgent plist XML."""
    if not app_path:
        app_path = _get_target_app_path()

    from xml.sax.saxutils import escape as xml_escape
    safe_path = xml_escape(app_path)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-a</string>
        <string>{safe_path}</string>
        <string>--args</string>
        <string>--silent</string>
        <string>--autostart</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>LimitLoadToSessionType</key>
    <string>Aqua</string>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""


def _check_smappservice_status() -> Optional[bool]:
    """Checks autostart status using macOS 13+ ServiceManagement SMAppService."""
    if sys.platform != "darwin":
        return None
    try:
        import ServiceManagement
        import AppKit
        bundle = AppKit.NSBundle.mainBundle()
        if not bundle or not bundle.bundleIdentifier() or not bundle.bundlePath().endswith(".app"):
            return None

        service = ServiceManagement.SMAppService.mainAppService()
        if service is None:
            return None

        # SMAppServiceStatusEnabled = 1, SMAppServiceStatusRequiresApproval = 2
        status = service.status()
        if status in (1, 2):
            return True
        elif status == 0:  # SMAppServiceStatusNotRegistered
            return False
    except Exception as e:
        logger.debug(f"SMAppService check not available or error: {e}")
    return None


def is_autostart_enabled() -> bool:
    """Determines whether FlightDeck is configured to launch at macOS/Linux/Windows login."""
    if IS_WINDOWS:
        return _is_autostart_enabled_windows()
    if IS_LINUX:
        return os.path.exists(LINUX_DESKTOP_FILE)
        
    sm_status = _check_smappservice_status()
    if sm_status is not None:
        return sm_status

    return os.path.exists(PLIST_PATH)


def enable_autostart() -> bool:
    """Enables launch at login using Windows Registry, SMAppService / LaunchAgent on macOS, or .desktop on Linux."""
    logger.info("Enabling Launch-at-Login for FlightDeck...")
    
    if IS_WINDOWS:
        return _enable_autostart_windows()

    if IS_LINUX:
        return _enable_autostart_linux()
        
    # 1. Try SMAppService if inside an app bundle (macOS only)
    if sys.platform == "darwin":
        try:
            import ServiceManagement
            import AppKit
            bundle = AppKit.NSBundle.mainBundle()
            if bundle and bundle.bundleIdentifier() and bundle.bundlePath().endswith(".app"):
                service = ServiceManagement.SMAppService.mainAppService()
                if service is not None:
                    success, err = service.registerAndReturnError_(None)
                    if success:
                        logger.info("✅ Successfully registered with SMAppService (macOS Login Items).")
                        return True
                    else:
                        logger.warning(f"SMAppService registration failed ({err}), falling back to LaunchAgent plist.")
        except Exception as e:
            logger.debug(f"SMAppService registration skipped/failed: {e}")

    # 2. Universal LaunchAgent fallback
    try:
        app_path = _get_target_app_path()
        plist_content = generate_launchagent_plist(app_path)
        os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)

        with open(PLIST_PATH, "w", encoding="utf-8") as f:
            f.write(plist_content.strip() + "\n")

        uid = os.getuid() if hasattr(os, "getuid") else 501
        # Unload/bootout previous state if present
        subprocess.run(["launchctl", "bootout", f"gui/{uid}/{PLIST_LABEL}"], capture_output=True)
        subprocess.run(["launchctl", "unload", "-w", PLIST_PATH], capture_output=True)

        # Bootstrap / Load
        res = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", PLIST_PATH], capture_output=True)
        if res.returncode != 0:
            subprocess.run(["launchctl", "load", "-w", PLIST_PATH], capture_output=True)

        logger.info(f"✅ Successfully wrote and loaded LaunchAgent: {PLIST_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to enable LaunchAgent autostart: {e}", exc_info=True)
        return False


def disable_autostart() -> bool:
    """Disables launch at login by removing Registry Run key on Windows, unregistering on macOS, or removing .desktop on Linux."""
    logger.info("Disabling Launch-at-Login for FlightDeck...")
    
    if IS_WINDOWS:
        return _disable_autostart_windows()

    if IS_LINUX:
        return _disable_autostart_linux()
        
    success = True

    # 1. Try SMAppService unregister (macOS only)
    if sys.platform == "darwin":
        try:
            import ServiceManagement
            import AppKit
            bundle = AppKit.NSBundle.mainBundle()
            if bundle and bundle.bundleIdentifier() and bundle.bundlePath().endswith(".app"):
                service = ServiceManagement.SMAppService.mainAppService()
                if service is not None:
                    service.unregisterAndReturnError_(None)
                    logger.info("Unregistered from SMAppService.")
        except Exception as e:
            logger.debug(f"SMAppService unregister: {e}")

    # 2. Remove LaunchAgent plist
    try:
        if os.path.exists(PLIST_PATH):
            uid = os.getuid() if hasattr(os, "getuid") else 501
            subprocess.run(["launchctl", "bootout", f"gui/{uid}/{PLIST_LABEL}"], capture_output=True)
            subprocess.run(["launchctl", "unload", "-w", PLIST_PATH], capture_output=True)
            os.remove(PLIST_PATH)
            logger.info(f"Removed LaunchAgent plist: {PLIST_PATH}")
    except Exception as e:
        logger.error(f"Failed to remove LaunchAgent plist: {e}", exc_info=True)
        success = False

    return success


def toggle_autostart() -> bool:
    """Toggles current autostart state."""
    if is_autostart_enabled():
        disable_autostart()
        return False
    else:
        enable_autostart()
        return True
