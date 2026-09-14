"""
Auto-Updater Service for FlightDeck.
Checks GitHub Releases for new versions, downloads platform assets,
and performs in-place upgrades for macOS and Ubuntu Linux.
"""
import os
import sys
import time
import json
import shutil
import urllib.request
import tempfile
import subprocess
import threading
import logging
from typing import Optional, Dict, Any, Tuple
from core.domain.models import __version__
from core.services.event_bus import event_bus

logger = logging.getLogger("FlightDeck.UpdaterService")

DEFAULT_REPO = "Antonino545/FlightDeck"

class UpdaterService:
    """Manages automatic version checking and seamless updates from GitHub Releases."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UpdaterService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, repo: str = DEFAULT_REPO):
        if self._initialized:
            return
        self.repo = repo
        self.latest_release_info: Optional[Dict[str, Any]] = None
        self.is_checking = False
        self.is_downloading = False
        self._initialized = True

    @property
    def current_version(self) -> str:
        """Dynamically detects the installed package version from local files, dpkg, NSBundle, or models.py."""
        # 1. Check native macOS NSBundle if running as AppKit app
        if sys.platform == "darwin":
            try:
                import AppKit
                bundle = AppKit.NSBundle.mainBundle()
                if bundle:
                    b_path = bundle.bundlePath() if hasattr(bundle, "bundlePath") else None
                    if b_path and (b_path.endswith("FlightDeck.app") or b_path.endswith("QuakMeeting.app")):
                        b_ver = bundle.objectForInfoDictionaryKey_("CFBundleShortVersionString")
                        if b_ver and str(b_ver).strip():
                            return str(b_ver).strip()
            except Exception:
                pass

        # 2. Check local VERSION file in application bundle or root
        try:
            curr_dir = os.path.dirname(os.path.abspath(__file__))
            for _ in range(4):
                ver_file = os.path.join(curr_dir, "VERSION")
                if os.path.exists(ver_file):
                    with open(ver_file, "r") as f:
                        v = f.read().strip()
                        if v:
                            return v
                curr_dir = os.path.dirname(curr_dir)
        except Exception:
            pass

        # 3. Check Info.plist on macOS
        if sys.platform == "darwin":
            try:
                res_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                plist_candidate = os.path.join(os.path.dirname(res_dir), "Info.plist")
                if not os.path.exists(plist_candidate):
                    plist_candidate = "/Applications/FlightDeck.app/Contents/Info.plist"
                if os.path.exists(plist_candidate):
                    import plistlib
                    with open(plist_candidate, "rb") as f:
                        pl = plistlib.load(f)
                        if "CFBundleShortVersionString" in pl and pl["CFBundleShortVersionString"]:
                            return str(pl["CFBundleShortVersionString"]).strip()
            except Exception:
                pass

        # 4. Check dpkg on Linux
        if sys.platform.startswith("linux"):
            try:
                res = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "flightdeck"], capture_output=True, text=True, timeout=1.5)
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except Exception:
                pass

        # 5. Check Windows (Inno Setup Registry & PyInstaller exe directory)
        if sys.platform == "win32":
            # 5a. Check VERSION file next to sys.executable or in _MEIPASS / assets
            try:
                base_dirs = [os.path.dirname(sys.executable)]
                if hasattr(sys, "_MEIPASS"):
                    base_dirs.append(getattr(sys, "_MEIPASS"))
                for b in base_dirs:
                    if not b:
                        continue
                    for v_path in (
                        os.path.join(b, "VERSION"),
                        os.path.join(b, "assets", "VERSION"),
                        os.path.join(b, "_internal", "VERSION"),
                    ):
                        if os.path.isfile(v_path):
                            with open(v_path, "r", encoding="utf-8") as f:
                                v = f.read().strip()
                                if v:
                                    return v.lstrip("vV")
            except Exception:
                pass

            # 5b. Query Inno Setup DisplayVersion from Windows Registry
            try:
                import winreg
                for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                    for subkey in (
                        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{67A41E1C-A47E-4E65-A656-11884C0F700B}_is1",
                        r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{67A41E1C-A47E-4E65-A656-11884C0F700B}_is1",
                    ):
                        try:
                            with winreg.OpenKey(root, subkey) as k:
                                val, _ = winreg.QueryValueEx(k, "DisplayVersion")
                                if val and str(val).strip():
                                    return str(val).strip().lstrip("vV")
                        except Exception:
                            pass
            except Exception:
                pass

        return __version__

    @current_version.setter
    def current_version(self, val: str):
        pass

    def parse_semver(self, v_str: str) -> Tuple[int, int, int]:
        """Parses 'v1.2.3' or '1.2.3' into (1, 2, 3) tuple."""
        cleaned = v_str.strip().lstrip("vV")
        parts = []
        for part in cleaned.split("."):
            try:
                parts.append(int(part.split("-")[0]))
            except ValueError:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    def is_newer_version(self, latest_v: str, current_v: str) -> bool:
        """Returns True if latest_v is strictly greater than current_v."""
        return self.parse_semver(latest_v) > self.parse_semver(current_v)

    def check_for_updates(self, background: bool = True, manual: bool = False) -> Optional[Dict[str, Any]]:
        """Queries GitHub Releases API for the latest release."""
        if self.is_checking:
            logger.debug("Update check skipped because another check is already running.")
            return self.latest_release_info

        logger.debug("Starting update check: background=%s manual=%s current_version=%s.", background, manual, self.current_version)

        def _worker():
            self.is_checking = True
            try:
                is_windows = sys.platform == "win32"
                # On Windows, query releases list to find the latest release containing an executable (.exe) installer
                if is_windows:
                    url = f"https://api.github.com/repos/{self.repo}/releases?per_page=20"
                else:
                    url = f"https://api.github.com/repos/{self.repo}/releases/latest"

                req = urllib.request.Request(url, headers={
                    "User-Agent": f"FlightDeck-Updater/{self.current_version}",
                    "Accept": "application/vnd.github.v3+json"
                })
                with urllib.request.urlopen(req, timeout=12) as resp:
                    raw_data = json.loads(resp.read().decode("utf-8"))

                if is_windows:
                    if isinstance(raw_data, list):
                        data = self._find_windows_release(raw_data)
                        if not data and raw_data:
                            data = raw_data[0]
                    else:
                        data = raw_data
                else:
                    data = raw_data[0] if isinstance(raw_data, list) and raw_data else raw_data

                if not data:
                    data = {}

                tag_name = data.get("tag_name", "")
                has_update = self.is_newer_version(tag_name, self.current_version) if tag_name else False

                release_info = {
                    "has_update": has_update,
                    "version": tag_name.lstrip("vV"),
                    "tag_name": tag_name,
                    "name": data.get("name", tag_name),
                    "body": data.get("body", ""),
                    "html_url": data.get("html_url", ""),
                    "assets": data.get("assets", []),
                    "published_at": data.get("published_at", "")
                }
                self.latest_release_info = release_info
                logger.debug("Update check completed: latest=%s has_update=%s.", tag_name, has_update)
                if has_update:
                    logger.info(f"🚀 New FlightDeck update found: {tag_name} (Current: {self.current_version})")
                    event_bus.publish("UPDATE_AVAILABLE", **release_info)
                    try:
                        from ui.common.banner_presets import get_update_preset
                        event_bus.publish("TRIGGER_BANNER", event_dict=get_update_preset(tag_name, release_info.get("html_url", "")))
                    except Exception as b_err:
                        logger.debug(f"Banner trigger on update: {b_err}")
                else:
                    logger.info(f"✨ FlightDeck is up to date (Current: {self.current_version})")
                    event_bus.publish("UPDATE_CHECK_COMPLETE", has_update=False, current_version=self.current_version)
                    if manual:
                        try:
                            from ui.common.banner_presets import get_up_to_date_preset
                            event_bus.publish("TRIGGER_BANNER", event_dict=get_up_to_date_preset(self.current_version))
                        except Exception as b_err:
                            logger.debug(f"Banner trigger on up-to-date: {b_err}")
                return release_info
            except Exception as e:
                logger.warning(f"Update check failed: {e}")
                event_bus.publish("UPDATE_CHECK_COMPLETE", has_update=False, error=str(e), current_version=self.current_version)
                if manual:
                    try:
                        from ui.common.banner_presets import get_update_error_preset
                        event_bus.publish("TRIGGER_BANNER", event_dict=get_update_error_preset(str(e)))
                    except Exception as b_err:
                        logger.debug(f"Banner trigger on update error: {b_err}")
                return None
            finally:
                self.is_checking = False

        if background:
            threading.Thread(target=_worker, daemon=True).start()
            logger.debug("Update check worker started in background.")
            return self.latest_release_info
        else:
            return _worker()

    def _find_windows_release(self, releases: list) -> Optional[Dict[str, Any]]:
        """Finds the most recent release containing a Windows .exe installer asset."""
        for rel in releases:
            for asset in rel.get("assets", []):
                name = asset.get("name", "").lower()
                if name.endswith(".exe"):
                    return rel
        return None

    def get_platform_asset(self, assets: list) -> Optional[Dict[str, Any]]:
        """Selects the best asset for the current OS (macOS DMG/ZIP vs Ubuntu DEB vs Windows EXE/ZIP)."""
        is_mac = sys.platform == "darwin"
        is_linux = sys.platform.startswith("linux")
        is_windows = sys.platform == "win32"

        # On Windows, prefer executable installer (.exe) first
        if is_windows:
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".exe"):
                    return asset
            for asset in assets:
                name = asset.get("name", "").lower()
                if name.endswith(".msi") or (name.endswith(".zip") and "win" in name):
                    return asset
            return None

        for asset in assets:
            name = asset.get("name", "").lower()
            if is_mac and (name.endswith(".dmg") or (name.endswith(".zip") and "macos" in name)):
                return asset
            elif is_linux and name.endswith(".deb"):
                return asset
            elif is_linux and name.endswith(".appimage"):
                return asset

        return None

    def download_and_install_update(self, background: bool = True, on_progress=None) -> bool:
        """Downloads the matching asset and initiates installer / replacement."""
        if self.is_downloading:
            logger.debug("Update download skipped because another download is already running.")
            return False

        def _worker():
            if not self.latest_release_info or not self.latest_release_info.get("assets"):
                info = self.check_for_updates(background=False)
                if not info or not info.get("has_update"):
                    return False

            asset = self.get_platform_asset(self.latest_release_info["assets"])
            if not asset or not asset.get("browser_download_url"):
                logger.error("No compatible release asset found for current OS.")
                event_bus.publish("UPDATE_FAILED", error="No compatible release asset found for current OS.")
                if self.latest_release_info and self.latest_release_info.get("html_url"):
                    import webbrowser
                    webbrowser.open(self.latest_release_info["html_url"])
                return False

            download_url = asset["browser_download_url"]
            file_name = asset["name"]
            temp_dir = tempfile.mkdtemp(prefix="flightdeck_update_")
            target_path = os.path.join(temp_dir, file_name)
            logger.debug("Selected update asset %s for download.", file_name)

            self.is_downloading = True
            event_bus.publish("UPDATE_STEP", step_id="download", step_name="Downloading update...")
            event_bus.publish("UPDATE_DOWNLOADING", file_name=file_name, url=download_url)
            try:
                logger.info(f"Downloading update {file_name} from {download_url}...")

                def _reporthook(block_num, block_size, total_size):
                    if total_size > 0:
                        downloaded = block_num * block_size
                        percent = min(100, int((downloaded / total_size) * 100))
                        if on_progress:
                            on_progress(percent, downloaded, total_size)
                        event_bus.publish("UPDATE_PROGRESS", percent=percent)
                        event_bus.publish("UPDATE_DOWNLOAD_PROGRESS", percent=percent, downloaded=downloaded, total=total_size)

                urllib.request.urlretrieve(download_url, target_path, reporthook=_reporthook)
                event_bus.publish("UPDATE_STEP", step_id="install", step_name="Installing update package...")
                event_bus.publish("UPDATE_PROGRESS", percent=100.0)
                event_bus.publish("UPDATE_DOWNLOADED", target_path=target_path)

                if sys.platform == "darwin":
                    return self._install_macos_update(target_path, temp_dir)
                elif sys.platform.startswith("linux"):
                    return self._install_linux_update(target_path)
                elif sys.platform == "win32":
                    return self._install_windows_update(target_path, temp_dir)
                return False
            except Exception as e:
                logger.error(f"Failed to install update: {e}")
                event_bus.publish("UPDATE_FAILED", error=str(e))
                return False
            finally:
                self.is_downloading = False

        if background:
            threading.Thread(target=_worker, daemon=True).start()
            return True
        else:
            return _worker()

    def _install_macos_update(self, package_path: str, temp_dir: str) -> bool:
        """Mounts DMG or unzips update and replaces the running FlightDeck.app in /Applications."""
        try:
            # 1. Resolve target destination bundle path
            app_dest = "/Applications/FlightDeck.app"
            try:
                import AppKit
                bundle = AppKit.NSBundle.mainBundle()
                b_path = bundle.bundlePath() if bundle else None
                if b_path and (b_path.endswith("FlightDeck.app") or b_path.endswith("QuakMeeting.app")) and os.path.exists(b_path):
                    app_dest = b_path
            except Exception:
                pass

            def _find_app(search_dir: str) -> Optional[str]:
                for candidate in ("FlightDeck.app", "QuakMeeting.app"):
                    p = os.path.join(search_dir, candidate)
                    if os.path.exists(p):
                        return p
                # Scan for any .app bundle inside directory
                try:
                    for f in os.listdir(search_dir):
                        if f.endswith(".app"):
                            return os.path.join(search_dir, f)
                except Exception:
                    pass
                return None

            source_app = None
            mount_point = None

            if package_path.endswith(".dmg"):
                mount_point = os.path.join(temp_dir, "mount")
                os.makedirs(mount_point, exist_ok=True)
                subprocess.run(["hdiutil", "attach", package_path, "-mountpoint", mount_point, "-nobrowse", "-quiet"], check=True)
                source_app = _find_app(mount_point)
            elif package_path.endswith(".zip"):
                subprocess.run(["unzip", "-q", package_path, "-d", temp_dir], check=True)
                source_app = _find_app(temp_dir)

            if not source_app or not os.path.exists(source_app):
                if mount_point and os.path.exists(mount_point):
                    subprocess.run(["hdiutil", "detach", mount_point, "-quiet"], check=False)
                raise RuntimeError(f"Could not locate FlightDeck.app in update package: {package_path}")

            # 2. Safely replace installed app (atomic backup move to avoid running-file lock)
            backup_app = os.path.join(temp_dir, "OldFlightDeckBackup.app")
            if os.path.exists(app_dest):
                try:
                    shutil.move(app_dest, backup_app)
                except Exception:
                    shutil.rmtree(app_dest, ignore_errors=True)

            # Clean up any legacy QuakMeeting.app in /Applications
            legacy_dest = "/Applications/QuakMeeting.app"
            if os.path.exists(legacy_dest) and legacy_dest != app_dest:
                try:
                    shutil.rmtree(legacy_dest, ignore_errors=True)
                except Exception:
                    pass

            shutil.copytree(source_app, app_dest)
            logger.info(f"Successfully installed FlightDeck.app to {app_dest}!")

            if mount_point and os.path.exists(mount_point):
                subprocess.run(["hdiutil", "detach", mount_point, "-quiet"], check=False)

            # 3. Clear quarantine flags and apply designated requirement ad-hoc codesign
            if os.path.exists(app_dest):
                subprocess.run(["xattr", "-cr", app_dest], check=False)
                subprocess.run([
                    "codesign", "--force", "--deep", "-s", "-",
                    "-i", "com.flightdeck.app",
                    "-r", '=designated => identifier "com.flightdeck.app"',
                    app_dest
                ], check=False)

            event_bus.publish("UPDATE_INSTALLED")
            time.sleep(0.5)

            # 4. Relaunch cleanly once the current PID exits
            current_pid = os.getpid()
            relaunch_cmd = (
                f"tail --pid={current_pid} -f /dev/null 2>/dev/null || sleep 1.2; "
                f"sleep 0.5; "
                f"open -n \"{app_dest}\" &"
            )
            subprocess.Popen(["bash", "-c", relaunch_cmd], start_new_session=True)
            os._exit(0)
            return True
        except Exception as e:
            logger.error(f"macOS update installation failed: {e}")
            event_bus.publish("UPDATE_FAILED", error=str(e))
            return False

    def _install_linux_update(self, package_path: str) -> bool:
        """Installs .deb package on Ubuntu Linux via pkexec or apt and automatically relaunches."""
        try:
            if package_path.endswith(".deb"):
                try:
                    logger.info(f"Executing: pkexec dpkg -i {package_path}")
                    res = subprocess.run(["pkexec", "dpkg", "-i", package_path], capture_output=True, text=True)
                    if res.returncode == 0:
                        logger.info("✅ Update package installed successfully via dpkg!")
                        event_bus.publish("UPDATE_INSTALLED")
                        time.sleep(1.0)
                        # Wait for current process to terminate, then launch the updated package
                        current_pid = os.getpid()
                        relaunch_cmd = (
                            f"tail --pid={current_pid} -f /dev/null 2>/dev/null || sleep 1.5; "
                            "sleep 0.5; "
                            "if command -v gtk-launch >/dev/null 2>&1 && [ -f /usr/share/applications/flightdeck.desktop ]; then "
                            "  gtk-launch flightdeck.desktop >/dev/null 2>&1 & "
                            "elif [ -x /usr/bin/flightdeck ]; then "
                            "  /usr/bin/flightdeck >/dev/null 2>&1 & "
                            "elif [ -f /opt/flightdeck/main.py ]; then "
                            "  /usr/bin/python3 /opt/flightdeck/main.py >/dev/null 2>&1 & "
                            "fi"
                        )
                        subprocess.Popen(["bash", "-c", relaunch_cmd], start_new_session=True)
                        os._exit(0)
                        return True
                    else:
                        err_msg = res.stderr.strip() or res.stdout.strip() or f"Process returned code {res.returncode}"
                        logger.warning(f"pkexec install finished with error: {err_msg}")
                        event_bus.publish("UPDATE_FAILED", error=err_msg)
                        return False
                except Exception as pk_err:
                    logger.warning(f"pkexec install failed ({pk_err}). Opening browser release page.")
                    event_bus.publish("UPDATE_FAILED", error=str(pk_err))
                    if self.latest_release_info and self.latest_release_info.get("html_url"):
                        import webbrowser
                        webbrowser.open(self.latest_release_info["html_url"])
                    return False
            elif package_path.endswith(".AppImage"):
                os.chmod(package_path, 0o755)
                event_bus.publish("UPDATE_INSTALLED")
                current_pid = os.getpid()
                relaunch_cmd = (
                    f"tail --pid={current_pid} -f /dev/null 2>/dev/null || sleep 1.5; "
                    f"sleep 0.5; "
                    f"\"{package_path}\" >/dev/null 2>&1 &"
                )
                subprocess.Popen(["bash", "-c", relaunch_cmd], start_new_session=True)
                os._exit(0)
                return True
        except Exception as e:
            logger.error(f"Linux update installation failed: {e}")
            event_bus.publish("UPDATE_FAILED", error=str(e))
            return False

    def _install_windows_update(self, package_path: str, temp_dir: str) -> bool:
        """Installs .exe/.msi or extracts .zip update on Windows."""
        try:
            event_bus.publish("UPDATE_STEP", step_id="install", step_name="Launching Windows installer...")
            if package_path.endswith(".exe") or package_path.endswith(".msi"):
                if hasattr(os, "startfile"):
                    os.startfile(package_path)
                else:
                    subprocess.Popen([package_path], shell=True)
                event_bus.publish("UPDATE_INSTALLED")
                return True
            elif package_path.endswith(".zip"):
                import zipfile
                with zipfile.ZipFile(package_path, 'r') as zip_ref:
                    extract_dir = os.path.join(temp_dir, "extracted")
                    zip_ref.extractall(extract_dir)
                event_bus.publish("UPDATE_INSTALLED")
                if hasattr(os, "startfile"):
                    os.startfile(extract_dir)
                return True
            return False
        except Exception as e:
            logger.error(f"Windows update installation failed: {e}")
            event_bus.publish("UPDATE_FAILED", error=str(e))
            return False

updater_service = UpdaterService()
