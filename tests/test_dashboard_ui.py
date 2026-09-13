import unittest
from unittest.mock import MagicMock
import sys
from datetime import datetime
from core.services.config_service import config

HAS_APPKIT = False
if sys.platform == "darwin":
    try:
        import AppKit
        HAS_APPKIT = True
    except ImportError:
        HAS_APPKIT = False

# Only run macOS UI tests when AppKit is actually available on macOS
class TestDashboardUI(unittest.TestCase):
    @unittest.skipUnless(HAS_APPKIT, "macOS AppKit required")
    def test_instantiate_and_render_tabs(self):
        # Avoid showing actual windows during test
        try:
            from ui.macos.dashboard_tabs.agenda_tab import AgendaTabController
            from ui.macos.dashboard_tabs.hangar_tab import HangarTabController
            from ui.macos.dashboard_tabs.settings_tab import SettingsTabController

            agenda = AgendaTabController.alloc().init()
            hangar = HangarTabController.alloc().init()
            settings = SettingsTabController.alloc().init()

            self.assertIsNotNone(agenda)
            self.assertIsNotNone(hangar)
            self.assertIsNotNone(settings)

            # Mock container and config
            mock_container = MagicMock()
            mock_config = MagicMock()
            mock_config.get.side_effect = lambda k, d=None: d if d is not None else "transit"

            # Test Agenda render
            meetings = []
            agenda_view = agenda.render(mock_container, 800, 600, meetings, False, mock_config)
            self.assertIsNotNone(agenda_view)

            # Test Hangar render and initial scroll to top
            hangar_view = hangar.render(mock_container, 800, 600)
            self.assertIsNotNone(hangar_view)
            doc_h = hangar_view.documentView().frame().size.height
            clip_y = hangar_view.contentView().bounds().origin.y
            # Initial render should be scrolled to the top (doc_h - 600)
            self.assertAlmostEqual(clip_y, max(0.0, doc_h - 600.0), delta=1.0)

            # Test toggling a drawer preserves scroll offset from top
            fake_sender = MagicMock()
            fake_sender.identifier.return_value = "study"
            hangar.onToggleKeywordsDrawer_(fake_sender)
            self.assertIn("study", hangar.expanded_categories)

            # Re-render simulates dashboard controller tab refresh
            hangar_view_exp = hangar.render(mock_container, 800, 600)
            new_doc_h = hangar_view_exp.documentView().frame().size.height
            new_clip_y = hangar_view_exp.contentView().bounds().origin.y
            # New clip y must be at new_doc_h - 600 (still at top, NOT 0 at bottom)
            self.assertAlmostEqual(new_clip_y, max(0.0, new_doc_h - 600.0), delta=1.0)

            # Test batch comma-separated keyword adding
            fake_input = MagicMock()
            fake_input.stringValue.return_value = "quantum, calculus, algebra"
            hangar.kw_inputs["study"] = fake_input
            hangar.onAddCategoryKeyword_(fake_sender)
            study_kws = config.get_custom_keywords("study")
            self.assertIn("quantum", study_kws)
            self.assertIn("calculus", study_kws)
            self.assertIn("algebra", study_kws)
            # Clean up test keywords so user configuration is not polluted
            config.remove_custom_keyword("study", "quantum")
            config.remove_custom_keyword("study", "calculus")
            config.remove_custom_keyword("study", "algebra")

            # Test mini_canvases persistence and animation ticks across cached render
            self.assertGreater(len(hangar.mini_canvases), 0)
            canvases_count_before = len(hangar.mini_canvases)
            # Second render with same signature (cache hit) must NOT wipe mini_canvases
            hangar_cached = hangar.render(mock_container, 800, 600)
            self.assertEqual(len(hangar.mini_canvases), canvases_count_before)
            
            # Simulate an animation tick with a visible test window
            test_win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                AppKit.NSMakeRect(0, 0, 800, 600), 15, AppKit.NSBackingStoreBuffered, False
            )
            test_win.contentView().addSubview_(hangar_cached)
            test_win.orderFrontRegardless()

            canvas = next(iter(hangar.mini_canvases.values()))
            initial_tick = canvas.tick
            hangar.onAnimTick_(None)
            self.assertEqual(canvas.tick, initial_tick + 1)
            test_win.orderOut_(None)

            # Test Settings render
            cached_calendars = [{"name": "Work", "enabled": True}, {"name": "Personal", "enabled": False}]
            settings_view = settings.render(mock_container, 800, 600, mock_config, cached_calendars)
            self.assertIsNotNone(settings_view)

        except ImportError as e:
            self.fail(f"Failed to import UI controllers: {e}")

    @unittest.skipUnless(HAS_APPKIT, "macOS AppKit required")
    def test_hangar_dual_tier_deck_and_presets(self):
        from ui.macos.components import KeywordChipView
        from ui.macos.dashboard_tabs.hangar_tab import HangarTabController
        from core.services.config_service import config

        # 1. Test KeywordChipView with custom vs preset styling
        custom_chip = KeywordChipView.create(0, 0, 100, 24, text="deep learning", is_custom=True)
        self.assertIsNotNone(custom_chip)
        # Find the text label inside custom_chip
        labels = [sub for sub in custom_chip.subviews() if isinstance(sub, AppKit.NSTextField)]
        self.assertEqual(len(labels), 1)
        self.assertTrue(labels[0].stringValue().startswith("✨ "))

        preset_chip = KeywordChipView.create(0, 0, 100, 24, text="math", is_custom=False)
        self.assertIsNotNone(preset_chip)
        p_labels = [sub for sub in preset_chip.subviews() if isinstance(sub, AppKit.NSTextField)]
        self.assertEqual(len(p_labels), 1)
        self.assertEqual(p_labels[0].stringValue(), "math")

        # 2. Test HangarTabController Dual-Tier Deck lifecycle
        mock_container = MagicMock()
        hangar = HangarTabController.alloc().init()
        self.assertEqual(len(hangar.expanded_presets), 0)

        # Expand 'work' category
        fake_sender = MagicMock()
        fake_sender.identifier.return_value = "work"
        hangar.onToggleKeywordsDrawer_(fake_sender)
        self.assertIn("work", hangar.expanded_categories)

        # Render with collapsed presets
        view_collapsed = hangar.render(mock_container, 800, 600)
        h_collapsed = view_collapsed.documentView().frame().size.height

        self.assertIn("work", hangar.custom_cnt_labels)
        self.assertIn("work", hangar.preset_toggle_buttons)
        self.assertIn("work", hangar.custom_doc_views)

        # Toggle presets open for 'work'
        hangar.onTogglePresets_(fake_sender)
        self.assertIn("work", hangar.expanded_presets)

        # Re-render with expanded presets
        view_expanded = hangar.render(mock_container, 800, 600)
        h_expanded = view_expanded.documentView().frame().size.height
        # Height difference must match the extra height for expanded presets (123px)
        self.assertAlmostEqual(h_expanded - h_collapsed, 123.0, delta=1.0)
        self.assertIn("work", hangar.preset_doc_views)

        # Add custom keywords
        fake_input = MagicMock()
        fake_input.stringValue.return_value = "sprint planning, retro"
        hangar.kw_inputs["work"] = fake_input
        hangar.onAddCategoryKeyword_(fake_sender)
        work_kws = config.get_custom_keywords("work")
        self.assertIn("sprint planning", work_kws)
        self.assertIn("retro", work_kws)

        # Remove custom keyword
        del_btn = MagicMock()
        del_btn.toolTip.return_value = "work:::sprint planning"
        hangar.onRemoveCategoryKeyword_(del_btn)
        work_kws_after = config.get_custom_keywords("work")
        self.assertNotIn("sprint planning", work_kws_after)
        self.assertIn("retro", work_kws_after)

        # Reset to defaults
        hangar.onResetCategoryKeywords_(fake_sender)
        work_kws_reset = config.get_custom_keywords("work")
        self.assertNotIn("retro", work_kws_reset)


    @unittest.skipUnless(HAS_APPKIT, "macOS AppKit required")
    def test_menu_bar_build_with_upcoming_events(self):
        from ui.macos.menu_bar_app import FlightDeckMenuBar
        from datetime import datetime, timedelta
        now = datetime.now().astimezone()
        menu_bar = FlightDeckMenuBar.alloc().init()
        self.assertIsNotNone(menu_bar)

        # Set upcoming meeting for today
        m = {
            "title": "Upcoming Lecture",
            "start_time": now + timedelta(minutes=30),
            "end_time": now + timedelta(minutes=90),
            "pilot_type": "owl",
            "travel_time_minutes": 15,
            "departure_time": now + timedelta(minutes=15)
        }
        menu_bar.meetings = [m]
        # Must build menu without raising AttributeError
        menu_bar.build_menu()
        self.assertGreater(menu_bar.menu.numberOfItems(), 0)

    @unittest.skipUnless(HAS_APPKIT, "macOS AppKit required")
    def test_reminder_event_payload_shows_banner(self):
        """The EventBus payload includes event_dict as well as meeting/stage."""
        from ui.macos.menu_bar_app import FlightDeckMenuBar
        from unittest.mock import patch

        payload = {"title": "Banner regression test", "reminder_stage": 0}

        with patch("ui.macos.menu_bar_app.show_banner_async") as show_banner:
            FlightDeckMenuBar._on_reminder_triggered(
                object(), meeting=None, stage=0, event_dict=payload
            )

        show_banner.assert_called_once_with(payload)

    @unittest.skipUnless(HAS_APPKIT, "macOS AppKit required")
    def test_show_dashboard_accepts_tab_index(self):
        from unittest.mock import patch
        from ui.macos.dashboard_window import show_dashboard
        # Ensure show_dashboard accepts positional tab_index parameters (0, 1, 2, None)
        with patch("ui.macos.dashboard_window.DashboardWindowController.refresh_data"), \
             patch("ui.macos.dashboard_window.DashboardWindowController._prewarm_calendars"):
            try:
                show_dashboard()
                show_dashboard(0)
                show_dashboard(2)
            except TypeError as e:
                self.fail(f"show_dashboard raised TypeError with positional tab_index: {e}")

    def test_app_launcher_respects_qt_flag(self):
        from unittest.mock import patch, MagicMock
        from ui.app_launcher import launch_application

        mock_module = MagicMock()
        with patch("sys.argv", ["main.py", "--qt"]), \
             patch.dict("sys.modules", {"ui.linux.qt_tray_app": mock_module}):
            launch_application()
            mock_module.run_qt_tray_app.assert_called_once()

    def test_qt_flight_deck_window_instantiation_and_tabs(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.qt_dashboard import QtFlightDeckWindow, QtMascotMiniWidget
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt dashboard testing")

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = QtFlightDeckWindow(tab_index=1)
        self.assertIsNotNone(window)
        self.assertTrue(hasattr(window, "_refresh_hangar"))
        self.assertTrue(hasattr(window, "render_hangar_tab"))

        # Test calling refresh and tab switching methods
        window.set_active_tab(0)
        window._refresh_agenda()
        window.set_active_tab(1)
        window._refresh_hangar()
        window.render_hangar_tab()
        window.set_active_tab(2)

        # Test settings tab sidebar category navigation
        settings_tab = window.settings_tab
        self.assertIsNotNone(settings_tab)
        self.assertEqual(len(settings_tab.category_buttons), 5)
        self.assertEqual(settings_tab.stacked_widget.currentIndex(), 0)

        # Switch to each category and assert
        for cat_idx in range(5):
            settings_tab.select_category(cat_idx)
            self.assertEqual(settings_tab.stacked_widget.currentIndex(), cat_idx)

        # Verify all sub-cards are present
        self.assertIsNotNone(settings_tab.timing_card)
        self.assertIsNotNone(settings_tab.arrival_card)
        self.assertIsNotNone(settings_tab.calendars_card)
        self.assertIsNotNone(settings_tab.eta_card)
        self.assertIsNotNone(settings_tab.system_card)

        # Test mini widget
        mini = QtMascotMiniWidget(animal="owl", outfit="student")
        self.assertIsNotNone(mini)
        mini.update_mascot("bunny", "gym")
        mini.update_animal("duck")
        window.close()

    def test_qt_tray_debug_menu_visibility(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.qt_tray_app import FlightDeckTrayApp
            from core.services.config_service import config
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt tray app testing")

        app = QApplication.instance() or QApplication(sys.argv)
        with unittest.mock.patch("core.services.updater_service.updater_service.check_for_updates"):
            tray_app = FlightDeckTrayApp(app)

        # 1. Non-debug mode: logs action should not be present
        with unittest.mock.patch("ui.linux.qt_tray_app.is_debug_mode", return_value=False):
            tray_app.build_menu()
            action_texts = [act.text() for act in tray_app.tray.contextMenu().actions()]
            self.assertNotIn("📄 View Logs & Diagnostics...", action_texts)

        # 2. Debug mode: logs action should be present
        with unittest.mock.patch("ui.linux.qt_tray_app.is_debug_mode", return_value=True):
            tray_app.build_menu()
            action_texts = [act.text() for act in tray_app.tray.contextMenu().actions()]
            self.assertIn("📄 View Logs & Diagnostics...", action_texts)

    def test_qt_tray_menu_events_and_styling(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.qt_tray_app import FlightDeckTrayApp
            from core.domain.models import Meeting
            from core.services.language_service import t
            from datetime import datetime, timedelta, timezone
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt tray app testing")

        app = QApplication.instance() or QApplication(sys.argv)
        with unittest.mock.patch("core.services.updater_service.updater_service.check_for_updates"):
            tray_app = FlightDeckTrayApp(app)

        now = datetime.now(timezone.utc)
        m1 = Meeting(id="m1", title="First Flight", start_time=now + timedelta(hours=1), end_time=now + timedelta(hours=2))
        m2 = Meeting(id="m2", title="Second Flight", start_time=now + timedelta(hours=3), end_time=now + timedelta(hours=4))
        m3 = Meeting(id="m3", title="Tomorrow Flight", start_time=now + timedelta(days=1, hours=2), end_time=now + timedelta(days=1, hours=3))

        with unittest.mock.patch("core.services.calendar_service.calendar_service.get_upcoming_meetings", return_value=[m1, m2, m3]):
            tray_app.build_menu()
            action_texts = [act.text() for act in tray_app.tray.contextMenu().actions()]

            # Header and today's remaining events
            self.assertTrue(any("First Flight" in act for act in action_texts))
            self.assertIn(f"📅 {t('events_today_header')}", action_texts)
            self.assertTrue(any("Second Flight" in act for act in action_texts))

            # Tomorrow header and tomorrow events
            self.assertIn(f"🗓️ {t('tomorrow_header')}", action_texts)
            self.assertTrue(any("Tomorrow Flight" in act for act in action_texts))

    def test_qt_settings_system_card_debug_visibility(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.dashboard_tabs.settings.system_card import SystemCardWidget
            from core.services.language_service import t
            from core.services.updater_service import updater_service
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt system card testing")

        app = QApplication.instance() or QApplication(sys.argv)

        # 1. Non-debug mode: diagnostics row hidden, update status hidden (no update available), user actions visible
        with unittest.mock.patch("ui.linux.dashboard_tabs.settings.system_card.is_debug_mode", return_value=False), \
             unittest.mock.patch.object(updater_service, "latest_release_info", None):
            card = SystemCardWidget()
            self.assertEqual(card.uc_title.text(), t("settings_system_lang"))
            self.assertFalse(card.action_row_widget.isHidden())
            self.assertFalse(card.up_btn.isHidden())
            self.assertTrue(card.sys_row_widget.isHidden())
            self.assertTrue(card.update_status_box.isHidden())

        # 2. Debug mode: diagnostics row visible, update status visible, user actions visible
        with unittest.mock.patch("ui.linux.dashboard_tabs.settings.system_card.is_debug_mode", return_value=True), \
             unittest.mock.patch.object(updater_service, "latest_release_info", None):
            card_debug = SystemCardWidget()
            self.assertEqual(card_debug.uc_title.text(), t("settings_system_lang_diag"))
            self.assertFalse(card_debug.action_row_widget.isHidden())
            self.assertFalse(card_debug.up_btn.isHidden())
            self.assertFalse(card_debug.sys_row_widget.isHidden())
            self.assertFalse(card_debug.update_status_box.isHidden())

        # 3. Dynamic toggle via set_debug_visibility
        card.set_debug_visibility(True)
        self.assertEqual(card.uc_title.text(), t("settings_system_lang_diag"))
        self.assertFalse(card.action_row_widget.isHidden())
        self.assertFalse(card.up_btn.isHidden())
        self.assertFalse(card.sys_row_widget.isHidden())
        self.assertFalse(card.update_status_box.isHidden())

        card.set_debug_visibility(False)
        self.assertEqual(card.uc_title.text(), t("settings_system_lang"))
        self.assertFalse(card.action_row_widget.isHidden())
        self.assertFalse(card.up_btn.isHidden())
        self.assertTrue(card.sys_row_widget.isHidden())
        self.assertTrue(card.update_status_box.isHidden())

    def test_qt_agenda_serenis_redirect_button(self):
        try:
            from PyQt6.QtWidgets import QApplication, QPushButton
            from PyQt6.QtCore import QUrl
            from PyQt6.QtGui import QDesktopServices
            from ui.linux.qt_dashboard import QtFlightDeckWindow
            from core.domain.models import Meeting
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt dashboard testing")

        app = QApplication.instance() or QApplication(sys.argv)
        window = QtFlightDeckWindow(tab_index=0)
        meeting = Meeting(
            title="Serenis Online Therapy Session",
            start_time=datetime.now().astimezone(),
            provider="Serenis 🛋️",
            pilot_type="zen_duck",
            action_btn_text="🚀 JOIN SESSION",
            action_url="https://calendar.apple.com",
            description="Join at https://app.serenis.it/join/test123",
        )

        window._refresh_agenda([meeting])
        buttons = [
            button for button in window.scroll_content.findChildren(QPushButton, "PrimaryBtn")
            if button.text() == "🚀 JOIN SESSION"
        ]
        self.assertEqual(len(buttons), 1)
        self.assertLessEqual(buttons[0].geometry().right(), buttons[0].parentWidget().width())

        window.close()

    def test_qt_settings_arrival_card(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.dashboard_tabs.settings.arrival_card import ArrivalCardWidget
            from core.services.language_service import t
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt arrival card testing")

        app = QApplication.instance() or QApplication(sys.argv)
        card = ArrivalCardWidget()
        self.assertIsNotNone(card)
        self.assertTrue(card.master_chk.isChecked())
        self.assertTrue(card.call_chk.isChecked())
        self.assertTrue(card.wifi_chk.isChecked())

        # Test toggles
        card.master_chk.setChecked(False)
        self.assertFalse(config.get("enable_arrival_detection"))
        self.assertFalse(card.sub_container.isEnabled())

        card.master_chk.setChecked(True)
        self.assertTrue(config.get("enable_arrival_detection"))
        self.assertTrue(card.sub_container.isEnabled())

        # Test diagnostics update
        card.update_diagnostics()
        self.assertTrue(len(card.diag_wifi_lbl.text()) > 0)
        self.assertTrue(len(card.diag_call_lbl.text()) > 0)

        # Test SSIDs reset
        card._on_reset_ssids()
        self.assertIn("eduroam", config.get("arrival_wifi_ssids"))

    def test_qt_dashboard_sync_event_updates_ui_and_stops_spinning(self):
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.qt_dashboard import QtFlightDeckWindow
            from core.services.event_bus import event_bus
            from core.domain.models import Meeting
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt dashboard testing")

        app = QApplication.instance() or QApplication(sys.argv)
        window = QtFlightDeckWindow(tab_index=0)
        window.sync_btn.start_spinning("Syncing...")
        self.assertTrue(window.sync_btn.is_spinning)

        m = Meeting(
            title="Synced Standup",
            start_time=datetime.now().astimezone(),
            provider="EDS",
        )

        try:
            event_bus.publish("CALENDAR_SYNCED", meetings=[m], success=True)
            for _ in range(10):
                app.processEvents()

            # Agenda tab should now contain the synced meeting
            self.assertFalse(window.sync_btn.is_spinning)
            self.assertEqual(window.sync_btn.text(), "✅ Synced!")
        finally:
            window.close()


    @unittest.skipUnless(sys.platform == "darwin", "macOS AppKit tests require Darwin")
    def test_macos_keyword_chip_single_line_and_calendar_layout(self):
        import AppKit
        from ui.macos.components.keyword_chip_view import KeywordChipView
        from ui.macos.dashboard_tabs.settings_tab import SettingsTabController
        from core.services.config_service import config

        # 1. Verify KeywordChipView creates single-line non-wrapping label
        chip = KeywordChipView.create(
            0, 0, 90.0, 24.0,
            text="exam",
            is_custom=True,
            tooltip="study:::exam"
        )
        self.assertIsNotNone(chip)
        # Find NSTextField label inside chip
        labels = [sub for sub in chip.subviews() if isinstance(sub, AppKit.NSTextField)]
        self.assertTrue(len(labels) > 0)
        lbl = labels[0]
        self.assertEqual(lbl.stringValue(), "✨ exam")
        self.assertFalse(lbl.cell().wraps())
        self.assertTrue(lbl.usesSingleLineMode())

        # 2. Verify SettingsTab Card 2 height calculation handles multiple calendars
        settings = SettingsTabController.alloc().init()
        container = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 780, 600))
        sample_cals = [
            {"name": "Personal", "enabled": True},
            {"name": "University", "enabled": True},
            {"name": "Work", "enabled": False},
        ]
        # Calling render should calculate card_heights[2] for 3 calendars without clipping
        v = settings.render(container, 780, 600, config, sample_cals)
        self.assertIsNotNone(v)
        settings.select_category(2)
        cal_page = settings._category_pages.get(2)
        self.assertIsNotNone(cal_page)
        # Verify document view height has bottom breathing room
        doc_view = cal_page.documentView()
        self.assertIsNotNone(doc_view)
        # Card height for 3 calendars: 80.0 + 3 * 40.0 + 16.0 = 216.0
        # doc_h = max(600.0, 216.0 + 36.0) = 600.0
        self.assertGreaterEqual(doc_view.frame().size.height, 216.0)

    def test_macos_hangar_tab_category_groups_and_badges(self):
        """Tests that macOS HangarTabController supports category groups filtering, badges, and pilot chips."""
        if sys.platform != "darwin":
            self.skipTest("macOS specific test")

        from ui.macos.dashboard_tabs.hangar_tab import HangarTabController, CATEGORY_GROUPS, CATEGORY_BADGES
        import AppKit

        hangar = HangarTabController.alloc().init()
        self.assertIsNotNone(hangar)
        self.assertEqual(hangar.active_filter, "all")

        # Verify category group definitions
        self.assertIn("productivity", CATEGORY_GROUPS)
        self.assertIn("lifestyle", CATEGORY_GROUPS)
        self.assertIn("commute", CATEGORY_GROUPS)
        self.assertIn("study", CATEGORY_GROUPS["productivity"])
        self.assertIn("work", CATEGORY_GROUPS["productivity"])

        # Verify category badges
        self.assertIn("study", CATEGORY_BADGES)
        self.assertEqual(CATEGORY_BADGES["study"][1], "ACADEMIC")
        self.assertEqual(CATEGORY_BADGES["work"][1], "OFFICE")

        # Test filter switching via onFilterPillClicked_
        mock_sender = MagicMock()
        mock_sender.identifier.return_value = "productivity"
        hangar.onFilterPillClicked_(mock_sender)
        self.assertEqual(hangar.active_filter, "productivity")

        # Test render with active filter
        container = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 780, 600))
        view = hangar.render(container, 780, 600)
        self.assertIsNotNone(view)
        doc = view.documentView()
        self.assertIsNotNone(doc)

        # Verify filter buttons were populated
        self.assertIn("all", hangar.filter_buttons)
        self.assertIn("productivity", hangar.filter_buttons)

    def test_macos_hangar_academic_single_dynamic_preview(self):
        """Tests single dynamic preview and pilot selection for Academic subcategories on macOS."""
        if sys.platform != "darwin":
            self.skipTest("macOS specific test")

        from ui.macos.dashboard_tabs.hangar_tab import HangarTabController
        import AppKit

        hangar = HangarTabController.alloc().init()
        self.assertEqual(hangar.active_study_subcat, "study")
        self.assertEqual(hangar.get_drawer_h("study"), 238.0)

        # Expanding presets should enlarge the drawer height
        hangar.expanded_presets.add("study")
        self.assertEqual(hangar.get_drawer_h("study"), 361.0)
        hangar.expanded_presets.remove("study")

        # Select 'class' subcategory
        mock_sender = MagicMock()
        mock_sender.identifier.return_value = "class"
        hangar.onSelectStudySubcat_(mock_sender)
        self.assertEqual(hangar.active_study_subcat, "class")

        # Select 'exam' subcategory
        mock_sender.identifier.return_value = "exam"
        hangar.onSelectStudySubcat_(mock_sender)
        self.assertEqual(hangar.active_study_subcat, "exam")

    def test_linux_hangar_academic_single_dynamic_preview(self):
        """Tests single dynamic preview and subcategory selection for Academic on Linux Qt."""
        try:
            from PyQt6.QtWidgets import QApplication
            from ui.linux.dashboard_tabs.hangar_tab import QtHangarTab
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available for Qt hangar test")

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        hangar = QtHangarTab()
        self.assertEqual(hangar.active_study_subcat, "study")
        hangar.active_study_subcat = "class"
        self.assertEqual(hangar.active_study_subcat, "class")
        hangar.active_study_subcat = "exam"
        self.assertEqual(hangar.active_study_subcat, "exam")


if __name__ == '__main__':
    unittest.main()
