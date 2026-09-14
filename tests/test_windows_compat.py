"""
Unit tests for FlightDeck Windows Platform Compatibility.
Validates autostart via Windows Registry, audio playback via winsound,
file/folder launch via os.startfile, calendar provider selection,
process and Wi-Fi detection, and updater asset resolution on Windows.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

from core.domain.models import Meeting


class TestWindowsCompatibility(unittest.TestCase):

    def test_windows_autostart_lifecycle(self):
        """Tests Windows autostart checking, enabling, and disabling via winreg."""
        import core.autostart as autostart

        fake_reg = {}

        class MockWinreg:
            HKEY_CURRENT_USER = "HKCU"
            KEY_READ = 1
            KEY_SET_VALUE = 2
            REG_SZ = 1

            @staticmethod
            def OpenKey(hkey, subkey, reserved=0, access=0):
                return "key_handle"

            @staticmethod
            def QueryValueEx(key, val_name):
                if val_name in fake_reg:
                    return fake_reg[val_name], MockWinreg.REG_SZ
                raise FileNotFoundError()

            @staticmethod
            def SetValueEx(key, val_name, reserved, val_type, value):
                fake_reg[val_name] = value

            @staticmethod
            def DeleteValue(key, val_name):
                if val_name in fake_reg:
                    del fake_reg[val_name]
                else:
                    raise FileNotFoundError()

            @staticmethod
            def CloseKey(key):
                pass

        with patch.dict("sys.modules", {"winreg": MockWinreg}):
            with patch.object(autostart, "IS_WINDOWS", True):
                # 1. Initial state: disabled
                self.assertFalse(autostart.is_autostart_enabled())

                # 2. Enable autostart
                self.assertTrue(autostart.enable_autostart())
                self.assertTrue(autostart.is_autostart_enabled())
                self.assertIn("FlightDeck", fake_reg)
                self.assertIn("--silent --autostart", fake_reg["FlightDeck"])

                # 3. Disable autostart
                self.assertTrue(autostart.disable_autostart())
                self.assertFalse(autostart.is_autostart_enabled())
                self.assertNotIn("FlightDeck", fake_reg)

    def test_windows_sound_playback(self):
        """Tests Windows audio volume detection and chime playback using winsound."""
        import core.services.sound_service as sound_service

        mock_winsound = MagicMock()
        mock_winsound.SND_FILENAME = 0x00020000
        mock_winsound.SND_ASYNC = 0x00000001
        mock_winsound.MB_ICONASTERISK = 0x00000040

        with patch.dict("sys.modules", {"winsound": mock_winsound}):
            with patch("sys.platform", "win32"):
                # Volume check on Windows returns True
                self.assertTrue(sound_service.is_system_volume_on())

                # Play chime synchronously
                with patch("os.path.exists", return_value=True):
                    sound_service.play_chime("Windows Notify System Generic", sync=True)
                    self.assertTrue(mock_winsound.PlaySound.called)

                # Test chime plays sample
                mock_winsound.reset_mock()
                with patch("os.path.exists", return_value=True):
                    sound_service.play_test_chime("Windows Notify System Generic")
                    import time
                    time.sleep(0.05)
                    self.assertTrue(mock_winsound.PlaySound.called)

    def test_windows_open_log_and_config(self):
        """Tests that open_log_file and open_config_in_editor use os.startfile on Windows."""
        from core.logger import open_log_file, open_log_folder
        from core.services.config_service import config

        mock_startfile = MagicMock()
        with patch("sys.platform", "win32"):
            with patch("os.startfile", mock_startfile, create=True):
                # 1. Open log file
                res = open_log_file()
                self.assertTrue(res)
                self.assertTrue(mock_startfile.called)

                # 2. Open log folder
                mock_startfile.reset_mock()
                res = open_log_folder()
                self.assertTrue(res)
                self.assertTrue(mock_startfile.called)

                # 3. Open config editor
                mock_startfile.reset_mock()
                config.open_config_in_editor()
                self.assertTrue(mock_startfile.called)

    def test_windows_calendar_provider_selection(self):
        """Tests that CalendarService automatically selects CalDAV provider on Windows."""
        from core.services.calendar_service import CalendarService
        from core.providers.caldav_provider import CalDAVCalendarProvider

        with patch("sys.platform", "win32"):
            # Create fresh uninitialized instance for test
            mock_cfg = MagicMock()
            mock_cfg.get.return_value = []
            service = CalendarService.__new__(CalendarService)
            service._initialized = False
            service.__init__(provider=None, config=mock_cfg, bus=MagicMock())

            self.assertIsInstance(service._provider, CalDAVCalendarProvider)
            self.assertEqual(service.provider_name, "CalDAV")

    def test_windows_arrival_service_detection(self):
        """Tests Zoom/Teams process detection and Wi-Fi SSID querying on Windows."""
        from core.services.arrival_service import ArrivalService

        service = ArrivalService.__new__(ArrivalService)
        service._initialized = False
        service.__init__(config=MagicMock())

        from datetime import datetime
        now = datetime.now()
        # Test video call check for Zoom
        zoom_meeting = Meeting(
            title="Design Review",
            start_time=now,
            action_url="https://zoom.us/j/123456789"
        )
        teams_meeting = Meeting(
            title="Team Sync",
            start_time=now,
            action_url="https://teams.microsoft.com/l/meetup-join/123"
        )

        with patch("sys.platform", "win32"):
            # 1. When Zoom.exe is running in tasklist
            mock_tasklist_zoom = MagicMock(returncode=0, stdout="Zoom.exe 1234 Console 1 45,000 K\n")
            with patch("subprocess.run", return_value=mock_tasklist_zoom):
                self.assertTrue(service.is_active_video_call_running(zoom_meeting))

            # 2. When Zoom is not running
            mock_tasklist_empty = MagicMock(returncode=0, stdout="INFO: No tasks are running which match the specified criteria.\n")
            with patch("subprocess.run", return_value=mock_tasklist_empty):
                self.assertFalse(service.is_active_video_call_running(zoom_meeting))

            # 3. When Teams.exe is running
            mock_tasklist_teams = MagicMock(returncode=0, stdout="Teams.exe 5678 Console 1 80,000 K\n")
            with patch("subprocess.run", return_value=mock_tasklist_teams):
                self.assertTrue(service.is_active_video_call_running(teams_meeting))

            # 4. Wi-Fi SSID parsing via netsh
            netsh_output = (
                "There is 1 interface on the system:\n"
                "    Name                   : Wi-Fi\n"
                "    Description            : Intel(R) Wi-Fi 6 AX200\n"
                "    State                  : connected\n"
                "    SSID                   : Campus-WiFi\n"
                "    BSSID                  : 00:11:22:33:44:55\n"
            )
            with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout=netsh_output)):
                ssid = service.get_current_wifi_ssid()
                self.assertEqual(ssid, "Campus-WiFi")

    def test_windows_updater_asset_selection_and_install(self):
        """Tests that updater resolves Windows .exe / .zip assets and launches installer."""
        from core.services.updater_service import UpdaterService

        assets = [
            {"name": "FlightDeck-macOS.dmg", "browser_download_url": "https://example.com/mac.dmg"},
            {"name": "flightdeck_1.0.0_amd64.deb", "browser_download_url": "https://example.com/linux.deb"},
            {"name": "FlightDeck-Windows.zip", "browser_download_url": "https://example.com/win.zip"},
            {"name": "FlightDeck-Setup.exe", "browser_download_url": "https://example.com/win.exe"}
        ]

        service = UpdaterService()
        with patch("sys.platform", "win32"):
            chosen = service.get_platform_asset(assets)
            self.assertIsNotNone(chosen)
            self.assertTrue(chosen["name"].endswith(".exe") or chosen["name"].endswith(".zip"))

            # Test installation of .exe installer
            mock_startfile = MagicMock()
            with patch("os.startfile", mock_startfile, create=True):
                res = service._install_windows_update("C:\\Temp\\FlightDeck-Setup.exe", "C:\\Temp")
                self.assertTrue(res)
                mock_startfile.assert_called_with("C:\\Temp\\FlightDeck-Setup.exe")

    def test_windows_current_version_detection(self):
        """Tests that updater detects installed Windows version from registry or VERSION file."""
        from core.services.updater_service import UpdaterService
        service = UpdaterService()

        # 1. From Windows Registry (Inno Setup)
        class MockWinreg:
            HKEY_CURRENT_USER = "HKCU"
            HKEY_LOCAL_MACHINE = "HKLM"
            @staticmethod
            def OpenKey(*args, **kwargs):
                return "key"
            @staticmethod
            def QueryValueEx(key, name):
                if name == "DisplayVersion":
                    return "1.0.54", 1
                raise FileNotFoundError()

        with patch("sys.platform", "win32"):
            with patch.dict("sys.modules", {"winreg": MockWinreg}):
                self.assertEqual(service.current_version, "1.0.54")

    def test_windows_search_last_version_with_exe(self):
        """Tests that Windows searches releases for the newest version containing an .exe asset."""
        from core.services.updater_service import UpdaterService
        import json

        service = UpdaterService()

        # Mock releases where newest release v1.0.55 only has macOS and Linux,
        # but earlier release v1.0.54 has FlightDeck-Setup.exe
        mock_releases = [
            {
                "tag_name": "v1.0.55",
                "name": "FlightDeck v1.0.55",
                "assets": [
                    {"name": "FlightDeck-macOS.dmg", "browser_download_url": "https://example.com/mac.dmg"},
                    {"name": "flightdeck_1.0.55_amd64.deb", "browser_download_url": "https://example.com/deb.deb"}
                ]
            },
            {
                "tag_name": "v1.0.54",
                "name": "FlightDeck v1.0.54",
                "assets": [
                    {"name": "FlightDeck-macOS.dmg", "browser_download_url": "https://example.com/mac.dmg"},
                    {"name": "FlightDeck-Setup.exe", "browser_download_url": "https://example.com/win.exe"},
                    {"name": "flightdeck_1.0.54_amd64.deb", "browser_download_url": "https://example.com/deb.deb"}
                ]
            }
        ]

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_releases).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("sys.platform", "win32"), \
             patch.object(UpdaterService, "current_version", "1.0.50"), \
             patch("urllib.request.urlopen", return_value=mock_resp):
            info = service.check_for_updates(background=False)
            self.assertIsNotNone(info)
            self.assertTrue(info["has_update"])
            # Should have bypassed v1.0.55 and selected v1.0.54 because it has the .exe file
            self.assertEqual(info["tag_name"], "v1.0.54")
            asset = service.get_platform_asset(info["assets"])
            self.assertIsNotNone(asset)
            self.assertEqual(asset["name"], "FlightDeck-Setup.exe")


if __name__ == "__main__":
    unittest.main()
