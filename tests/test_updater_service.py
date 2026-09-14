"""
Unit tests for Auto-Updater Service and SemVer comparison.
"""
import unittest
from core.services.updater_service import UpdaterService

class TestUpdaterService(unittest.TestCase):
    def setUp(self):
        self.updater = UpdaterService()
        self.updater.is_checking = False
        self.updater.latest_release_info = None

    def test_parse_semver(self):
        self.assertEqual(self.updater.parse_semver("v1.2.3"), (1, 2, 3))
        self.assertEqual(self.updater.parse_semver("1.0.0"), (1, 0, 0))
        self.assertEqual(self.updater.parse_semver("2.5"), (2, 5, 0))
        self.assertEqual(self.updater.parse_semver("v0.9.1-beta"), (0, 9, 1))

    def test_is_newer_version(self):
        self.assertTrue(self.updater.is_newer_version("v1.1.0", "1.0.0"))
        self.assertTrue(self.updater.is_newer_version("2.0.0", "1.9.9"))
        self.assertTrue(self.updater.is_newer_version("1.0.1", "1.0.0"))
        self.assertFalse(self.updater.is_newer_version("1.0.0", "1.0.0"))
        self.assertFalse(self.updater.is_newer_version("0.9.0", "1.0.0"))

    def test_platform_asset_resolution(self):
        mock_assets = [
            {"name": "flightdeck_1.1.0_amd64.deb", "browser_download_url": "https://example.com/quak.deb"},
            {"name": "FlightDeck-macOS.dmg", "browser_download_url": "https://example.com/quak.dmg"},
            {"name": "FlightDeck-Setup.exe", "browser_download_url": "https://example.com/flightdeck.exe"}
        ]
        asset = self.updater.get_platform_asset(mock_assets)
        self.assertIsNotNone(asset)
        self.assertTrue(asset["name"].endswith(".dmg") or asset["name"].endswith(".deb") or asset["name"].endswith(".exe"))

    def test_mocked_check_for_updates(self):
        from unittest.mock import patch, MagicMock
        from core.services.event_bus import event_bus
        import json

        mock_payload = json.dumps({
            "tag_name": "v9.9.9",
            "name": "FlightDeck 9.9.9",
            "body": "Awesome new release",
            "html_url": "https://github.com/Antonino545/FlightDeck/releases/tag/v9.9.9",
            "assets": [{"name": "flightdeck_9.9.9_amd64.deb", "browser_download_url": "https://example.com/quak.deb"}],
            "published_at": "2026-08-25T12:00:00Z"
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_payload
        mock_resp.__enter__.return_value = mock_resp

        events_received = []
        event_bus.subscribe("UPDATE_AVAILABLE", lambda **k: events_received.append(k))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            info = self.updater.check_for_updates(background=False)
            self.assertIsNotNone(info)
            self.assertTrue(info["has_update"])
            self.assertEqual(info["tag_name"], "v9.9.9")

    def test_mocked_check_for_updates_up_to_date_manual(self):
        from unittest.mock import patch, MagicMock
        from core.services.event_bus import event_bus
        import json

        # Version older than or equal to current_version (1.0.0 vs current 1.0.49)
        mock_payload = json.dumps({
            "tag_name": "v1.0.0",
            "name": "FlightDeck 1.0.0",
            "body": "Older release",
            "html_url": "https://github.com/Antonino545/FlightDeck/releases/tag/v1.0.0",
            "assets": [],
            "published_at": "2026-01-01T12:00:00Z"
        }).encode("utf-8")

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_payload
        mock_resp.__enter__.return_value = mock_resp

        banners_triggered = []
        event_bus.subscribe("TRIGGER_BANNER", lambda **k: banners_triggered.append(k))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            info = self.updater.check_for_updates(background=False, manual=True)
            self.assertIsNotNone(info)
            self.assertFalse(info["has_update"])
            self.assertTrue(len(banners_triggered) > 0)
            banner_dict = banners_triggered[-1].get("event_dict") or banners_triggered[-1]
            self.assertTrue(banner_dict.get("is_update_banner"))
            self.assertTrue(banner_dict.get("is_up_to_date"))

    def test_mocked_check_for_updates_error_manual(self):
        from unittest.mock import patch
        from core.services.event_bus import event_bus

        banners_triggered = []
        event_bus.subscribe("TRIGGER_BANNER", lambda **k: banners_triggered.append(k))

        with patch("urllib.request.urlopen", side_effect=Exception("Connection timed out")):
            info = self.updater.check_for_updates(background=False, manual=True)
            self.assertIsNone(info)
            self.assertTrue(len(banners_triggered) > 0)
            banner_dict = banners_triggered[-1].get("event_dict") or banners_triggered[-1]
            self.assertTrue(banner_dict.get("is_update_banner"))
            self.assertTrue(banner_dict.get("is_update_error"))

    def test_mocked_install_linux_update(self):
        from unittest.mock import patch, MagicMock
        from core.services.event_bus import event_bus

        installed_events = []
        event_bus.subscribe("UPDATE_INSTALLED", lambda **k: installed_events.append(True))

        mock_run_res = MagicMock(returncode=0, stdout="Installed", stderr="")
        with patch("subprocess.run", return_value=mock_run_res), \
             patch("subprocess.Popen") as mock_popen, \
             patch("os._exit") as mock_exit, \
             patch("time.sleep"):
            success = self.updater._install_linux_update("/tmp/mock_package.deb")
            self.assertTrue(success)
            self.assertTrue(len(installed_events) >= 1)
            mock_popen.assert_called_once()
    def test_mocked_install_macos_update(self):
        from unittest.mock import patch, MagicMock
        from core.services.event_bus import event_bus

        installed_events = []
        event_bus.subscribe("UPDATE_INSTALLED", lambda **k: installed_events.append(True))

        mock_run_res = MagicMock(returncode=0, stdout="", stderr="")
        with patch("subprocess.run", return_value=mock_run_res) as mock_run, \
             patch("subprocess.Popen") as mock_popen, \
             patch("os._exit") as mock_exit, \
             patch("os.path.exists", return_value=True), \
             patch("os.makedirs"), \
             patch("shutil.rmtree"), \
             patch("shutil.copytree"), \
             patch("time.sleep"):
            success = self.updater._install_macos_update("/tmp/mock_package.dmg", "/tmp/temp_dir")
            self.assertTrue(success)
            self.assertTrue(len(installed_events) >= 1)
            mock_popen.assert_called_once()
            mock_exit.assert_called_once_with(0)

            # Verify codesign was called with the explicit designated requirement
            codesign_called = False
            for call_args in mock_run.call_args_list:
                args = call_args[0][0]
                if "codesign" in args:
                    codesign_called = True
                    self.assertIn("-r", args)
                    self.assertIn('=designated => identifier "com.flightdeck.app"', args)
            self.assertTrue(codesign_called)

    def test_mocked_install_macos_update_legacy_fallback(self):
        from unittest.mock import patch, MagicMock

        mock_run_res = MagicMock(returncode=0, stdout="", stderr="")
        # Simulate DMG where FlightDeck.app is absent but QuakMeeting.app is present
        def mock_exists(path):
            if "FlightDeck.app" in path and "mount" in path:
                return False
            if "QuakMeeting.app" in path and "mount" in path:
                return True
            return True

        with patch("subprocess.run", return_value=mock_run_res), \
             patch("subprocess.Popen"), \
             patch("os._exit"), \
             patch("os.path.exists", side_effect=mock_exists), \
             patch("os.makedirs"), \
             patch("shutil.move"), \
             patch("shutil.rmtree"), \
             patch("shutil.copytree") as mock_copy, \
             patch("time.sleep"):
            success = self.updater._install_macos_update("/tmp/mock_package.dmg", "/tmp/temp_dir")
            self.assertTrue(success)
            self.assertTrue(mock_copy.called)
            src, dst = mock_copy.call_args[0]
            self.assertTrue(src.endswith("QuakMeeting.app"))
            self.assertTrue(dst.endswith("FlightDeck.app"))

if __name__ == "__main__":
    unittest.main()
