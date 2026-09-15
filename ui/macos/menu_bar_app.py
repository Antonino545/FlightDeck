"""
Menu Bar Application for FlightDeck.
Displays dynamic status bar item, full macOS top menu bar, quick-action context menu, and background scanning.
"""
import AppKit
import Foundation
import objc
import webbrowser
import threading
import time
import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.domain.models import Meeting, format_duration
from core.services.calendar_service import calendar_service
from core.services.reminder_engine import reminder_engine
from core.services.event_bus import event_bus
from core.services.config_service import config, is_debug_mode
from core.services.updater_service import updater_service
from core.services.language_service import t, get_active_language, init_system_locale_listener
from core.logger import setup_logging, logger, open_log_file, open_log_folder
from ui.macos.banner import show_banner_async, _run_banner
from ui.macos.dashboard_window import show_dashboard
from ui.common.tray_viewmodel import TrayViewModel

_theme_observer = None

def get_theme_icon_path(mode: str = "dark") -> str:
    """Finds the icon path for the requested appearance mode ('dark' or 'light')."""
    filename = "icon_dark.png" if mode == "dark" else "icon_light.png"
    candidates = []
    bundle = AppKit.NSBundle.mainBundle()
    if bundle and bundle.resourcePath():
        candidates.append(os.path.join(bundle.resourcePath(), "assets", filename))
        candidates.append(os.path.join(bundle.resourcePath(), "assets", "icon.png"))
    project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidates.append(os.path.join(project_dir, "assets", filename))
    candidates.append(os.path.join(project_dir, "assets", "icon.png"))
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""


def update_dock_icon(app=None):
    """Dynamically updates the macOS Dock icon according to the active system theme (Light vs Dark)."""
    if app is None:
        app = AppKit.NSApplication.sharedApplication()
    try:
        appearance = app.effectiveAppearance().bestMatchFromAppearancesWithNames_([
            AppKit.NSAppearanceNameAqua,
            AppKit.NSAppearanceNameDarkAqua
        ])
        is_dark = (appearance == AppKit.NSAppearanceNameDarkAqua)
        target_path = get_theme_icon_path("dark" if is_dark else "light")
        if target_path and os.path.exists(target_path):
            img = AppKit.NSImage.alloc().initWithContentsOfFile_(target_path)
            if img and img.isValid():
                app.setApplicationIconImage_(img)
                logger.debug("macOS Dock icon set to %s (%s)", "Dark" if is_dark else "Light", target_path)
    except Exception as e:
        logger.warning("Could not update dynamic Dock icon: %s", e)


def init_system_theme_listener():
    """Listens for macOS system Dark/Light theme changes to update the Dock icon in real time."""
    if sys.platform != "darwin":
        return
    global _theme_observer
    if _theme_observer is not None:
        return
    try:
        class SystemThemeObserver(Foundation.NSObject):
            def themeDidChange_(self, notification):
                logger.info("macOS System Theme changed (Dark/Light), updating Dock icon.")
                update_dock_icon()

        _theme_observer = SystemThemeObserver.alloc().init()
        center = Foundation.NSDistributedNotificationCenter.defaultCenter()
        center.addObserver_selector_name_object_(
            _theme_observer,
            objc.selector(_theme_observer.themeDidChange_, signature=b"v@:@"),
            "AppleInterfaceThemeChangedNotification",
            None
        )
        logger.debug("Registered AppleInterfaceThemeChangedNotification observer for dynamic Dock icon.")
    except Exception as e:
        logger.debug("Could not register system theme observer: %s", e)

class FlightDeckAppDelegate(AppKit.NSObject):
    def applicationDidFinishLaunching_(self, notification):
        logger.info("FlightDeck running in macOS menu bar & system status bar!")
        logger.debug("macOS application finished launching; argv=%s", sys.argv)
        update_dock_icon()
        init_system_theme_listener()
        if "--silent" not in sys.argv and "--autostart" not in sys.argv:
            show_dashboard()

    def applicationShouldHandleReopen_hasVisibleWindows_(self, sender, flag):
        show_dashboard()
        return True

    def applicationShouldTerminateAfterLastWindowClosed_(self, sender):
        return False

    @objc.IBAction
    def showBannerOnMainThread_(self, meeting_data):
        _run_banner(meeting_data)

class FlightDeckMenuBar(AppKit.NSObject):
    def init(self):
        self = objc.super(FlightDeckMenuBar, self).init()
        if self is None:
            return None

        self.app = AppKit.NSApplication.sharedApplication()

        # Force macOS to (re-)register this process as a GUI app with menu bar.
        self.app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        self.app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)

        self.delegate = FlightDeckAppDelegate.alloc().init()
        self.app.setDelegate_(self.delegate)

        # Dynamic Application icon matching macOS theme (Light/Dark)
        update_dock_icon(self.app)
        init_system_theme_listener()

        # 1. macOS Top Menu Bar (App Menu, Edit, Window, Help)
        self._setup_main_menubar()

        # Initialize dynamic macOS locale change listener
        init_system_locale_listener()

        # 2. macOS System Status Bar Item (Top Right tray icon & dropdown)
        self.status_bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)
        self.status_item.setVisible_(True)

        btn = self.status_item.button()
        if btn:
            btn.setTitle_("✈️")
            btn.setToolTip_("FlightDeck — Smart Schedule & Travel Reminders")

        self.menu = AppKit.NSMenu.alloc().init()
        self.status_item.setMenu_(self.menu)

        self._last_menu_signature = None
        self.meetings: List[Dict[str, Any]] = []
        self._startup_catch_up_checked = False
        logger.debug("Initialized macOS menu bar controller.")

        # Subscribe to EventBus
        event_bus.subscribe("REMINDER_TRIGGERED", self._on_reminder_triggered)
        event_bus.subscribe("TRIGGER_BANNER", self._on_trigger_banner)
        event_bus.subscribe("CALENDAR_SYNCED", self._on_calendar_synced)
        event_bus.subscribe("CONFIG_CHANGED", self._on_config_changed)
        event_bus.subscribe("AGENDA_UPDATED", self._on_agenda_updated)
        event_bus.subscribe("UPDATE_AVAILABLE", self._on_update_event)
        event_bus.subscribe("UPDATE_CHECK_COMPLETE", self._on_update_event)
        event_bus.subscribe("UPDATE_INSTALLED", self._on_update_event)

        self._check_startup_catch_up(calendar_service.get_upcoming_meetings())
        self.build_menu()
        return self

    def _setup_main_menubar(self):
        """Builds standard macOS Top Menu Bar so menus & shortcuts (Cmd+C, Cmd+V, Cmd+Q) work globally."""
        main_menu = AppKit.NSMenu.alloc().init()

        # --- APP MENU ---
        app_menu_item = AppKit.NSMenuItem.alloc().init()
        app_menu = AppKit.NSMenu.alloc().initWithTitle_("FlightDeck")

        about_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("about_flightdeck"), "openAbout:", ""
        )
        about_item.setTarget_(self)
        app_menu.addItem_(about_item)
        app_menu.addItem_(AppKit.NSMenuItem.separatorItem())

        pref_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("preferences_menu"), "openDashboard:", ","
        )
        pref_item.setTarget_(self)
        app_menu.addItem_(pref_item)

        sync_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("sync_calendars"), "refreshCalendar:", "r"
        )
        sync_item.setTarget_(self)
        app_menu.addItem_(sync_item)
        app_menu.addItem_(AppKit.NSMenuItem.separatorItem())

        hide_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("hide_app"), "hide:", "h"
        )
        app_menu.addItem_(hide_item)

        hide_others = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("hide_others"), "hideOtherApplications:", "h"
        )
        hide_others.setKeyEquivalentModifierMask_(AppKit.NSEventModifierFlagCommand | AppKit.NSEventModifierFlagOption)
        app_menu.addItem_(hide_others)

        show_all = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("show_all"), "unhideAllApplications:", ""
        )
        app_menu.addItem_(show_all)
        app_menu.addItem_(AppKit.NSMenuItem.separatorItem())

        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("quit"), "terminate:", "q"
        )
        app_menu.addItem_(quit_item)
        app_menu_item.setSubmenu_(app_menu)
        main_menu.addItem_(app_menu_item)

        # --- EDIT MENU (Enables standard cut, copy, paste, select all) ---
        edit_menu_item = AppKit.NSMenuItem.alloc().init()
        edit_menu = AppKit.NSMenu.alloc().initWithTitle_(t("edit_menu"))
        edit_menu.addItemWithTitle_action_keyEquivalent_(t("undo"), "undo:", "z")
        edit_menu.addItemWithTitle_action_keyEquivalent_(t("redo"), "redo:", "Z")
        edit_menu.addItem_(AppKit.NSMenuItem.separatorItem())
        edit_menu.addItemWithTitle_action_keyEquivalent_(t("cut"), "cut:", "x")
        edit_menu.addItemWithTitle_action_keyEquivalent_(t("copy"), "copy:", "c")
        edit_menu.addItemWithTitle_action_keyEquivalent_(t("paste"), "paste:", "v")
        edit_menu.addItemWithTitle_action_keyEquivalent_(t("select_all"), "selectAll:", "a")
        edit_menu_item.setSubmenu_(edit_menu)
        main_menu.addItem_(edit_menu_item)

        # --- WINDOW MENU ---
        win_menu_item = AppKit.NSMenuItem.alloc().init()
        win_menu = AppKit.NSMenu.alloc().initWithTitle_(t("window_menu"))

        dash_win_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            t("flight_deck"), "openDashboard:", "o"
        )
        dash_win_item.setTarget_(self)
        win_menu.addItem_(dash_win_item)
        win_menu.addItemWithTitle_action_keyEquivalent_(t("minimize"), "performMiniaturize:", "m")
        win_menu.addItemWithTitle_action_keyEquivalent_(t("close"), "performClose:", "w")
        win_menu_item.setSubmenu_(win_menu)
        main_menu.addItem_(win_menu_item)

        # --- HELP MENU ---
        help_menu_item = AppKit.NSMenuItem.alloc().init()
        help_menu = AppKit.NSMenu.alloc().initWithTitle_(t("help_menu"))

        if is_debug_mode():
            help_log = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "View Log File (flightdeck.log)", "openLogFileAction:", "l"
            )
            help_log.setTarget_(self)
            help_menu.addItem_(help_log)
            help_menu.addItem_(AppKit.NSMenuItem.separatorItem())

        help_doc = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "FlightDeck Guide & GitHub", "openHelp:", ""
        )
        help_doc.setTarget_(self)
        help_menu.addItem_(help_doc)
        help_menu_item.setSubmenu_(help_menu)
        main_menu.addItem_(help_menu_item)

        self.app.setMainMenu_(main_menu)

    @objc.IBAction
    def openAbout_(self, sender):
        show_dashboard(0)

    @objc.IBAction
    def openHelp_(self, sender):
        webbrowser.open("https://github.com/Antonino545/FlightDeck")

    def _on_reminder_triggered(
        self,
        meeting: Optional[Meeting] = None,
        stage: Optional[int] = None,
        event_dict: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Display a reminder banner from the EventBus payload.

        ReminderEngine publishes both the Meeting object and its serialized form.
        Accepting the complete payload keeps the UI compatible with all event
        subscribers and, importantly, prevents an unexpected keyword argument
        from dropping the banner before it reaches AppKit.
        """
        m_dict = event_dict or (meeting.to_dict() if isinstance(meeting, Meeting) else meeting)
        if not m_dict:
            logger.warning("Ignoring REMINDER_TRIGGERED event without meeting data.")
            return
        show_banner_async(m_dict)

    def _on_trigger_banner(
        self,
        event_dict: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> None:
        """Display an arbitrary or update banner from the EventBus payload."""
        payload = event_dict or kwargs
        if not payload:
            logger.warning("Ignoring TRIGGER_BANNER event without payload.")
            return
        show_banner_async(payload)

    def _on_calendar_synced(self, meetings: Optional[List[Any]] = None, **kwargs) -> None:
        meetings = meetings or []
        self._check_startup_catch_up(meetings)
        self.meetings = [m.to_dict() if isinstance(m, Meeting) else m for m in meetings]
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "refreshMenuOnMainThread:",
            None,
            False
        )

    def _check_startup_catch_up(self, meetings: List[Meeting]) -> None:
        """Surface one missed event after the first startup calendar result."""
        if self._startup_catch_up_checked or not meetings:
            return
        self._startup_catch_up_checked = True
        reminder_engine.trigger_startup_catch_up(meetings)

    def _on_config_changed(self, key: Optional[str] = None, **kwargs) -> None:
        self._last_menu_signature = None
        if key in ("transport_mode", "home_address", "eta_buffer_minutes", "enable_eta_service", "custom_keywords", "ignored_calendars", None):
            if key == "transport_mode":
                calendar_service.update_transport_mode()
            calendar_service.request_background_sync("config_changed")
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            "refreshMenuOnMainThread:",
            None,
            False
        )

    @objc.IBAction
    def refreshMenuOnMainThread_(self, sender):
        self._setup_main_menubar()
        self.build_menu()

    # _format_status_title is now handled by TrayViewModel

    def build_menu(self):
        now = datetime.now().astimezone()
        from datetime import timedelta

        def _is_all_day_or_bill(ev):
            if isinstance(ev, dict):
                return bool(ev.get("is_all_day", False) or ev.get("category") == "bill" or ev.get("event_type") == "bill")
            return bool(getattr(ev, "is_all_day", False) or getattr(ev, "category", None) == "bill" or getattr(ev, "event_type", None) == "bill")

        today_upcoming = [
            m for m in self.meetings
            if m.get("start_time") and m["start_time"].astimezone().date() == now.date()
            and ((m.get("end_time") and m["end_time"] > now) or m["start_time"] > now)
            and not _is_all_day_or_bill(m)
        ]

        tomorrow_date = now.date() + timedelta(days=1)
        tomorrow_upcoming = [
            m for m in self.meetings
            if m.get("start_time") and m["start_time"].astimezone().date() == tomorrow_date
        ]

        status_mode = config.get("menubar_status_mode", "countdown")
        max_lookahead_min = int(config.get("max_countdown_lookahead_hours", 3)) * 60

        # State signature diffing to avoid unnecessary menu rebuilding
        m_sigs = tuple((m.get("title"), str(m.get("start_time")), m.get("pilot_type")) for m in today_upcoming[:6] + tomorrow_upcoming[:6])
        minute_str = now.strftime("%H:%M")
        new_signature = (minute_str, len(today_upcoming), len(tomorrow_upcoming), status_mode, m_sigs, get_active_language())

        if self._last_menu_signature == new_signature:
            return
        self._last_menu_signature = new_signature

        primary_m = today_upcoming[0] if today_upcoming else None
        title_str = TrayViewModel.get_status_bar_title(primary_m, now, status_mode, max_lookahead_min)

        # Must execute AppKit UI updates on Main Thread
        def _update_ui():
            self.status_item.button().setTitle_(title_str)
        if self.status_item.button():
            self.status_item.button().performSelectorOnMainThread_withObject_waitUntilDone_("setTitle:", title_str, False)

        self.menu.removeAllItems()

        # 1. Open Flight Deck
        item_dash = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"🦆 {t('flight_deck')}", "openDashboard:", "o"
        )
        item_dash.setTarget_(self)
        self.menu.addItem_(item_dash)
        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 2. Next Event & Quick Join (Only for today!)
        icon_map = {"chef": "🍕", "captain": "✈️", "owl": "🎓", "driver": "🚗", "zen_duck": "🛋️", "duck": "🦆"}

        if today_upcoming:
            next_m = today_upcoming[0]
            start_str = next_m["start_time"].astimezone().strftime("%H:%M") if next_m.get("start_time") else "--:--"
            m_title = (next_m.get("title") or "Event").strip()

            p_type = next_m.get("pilot_type", "duck")
            icon_prefix = icon_map.get(p_type, "🦆")

            travel_min = next_m.get("travel_time_minutes")
            dep_dt = next_m.get("departure_time")
            t_mode = next_m.get("transport_mode") or config.get("transport_mode", "transit")

            next_label = TrayViewModel.format_next_event_label(icon_prefix, start_str, m_title, travel_min, dep_dt, transport_mode=t_mode)

            item_next = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                next_label, None, ""
            )
            item_next.setEnabled_(False)
            self.menu.addItem_(item_next)

            action_url = next_m.get("action_url") or next_m.get("meeting_url")
            if action_url:
                btn_title = f"   {next_m.get('action_btn_text', t('banner_join_flight'))}"
                item_join = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    btn_title, "openNextMeeting:", "j"
                )
                item_join.setTarget_(self)
                self.menu.addItem_(item_join)

            self.menu.addItem_(AppKit.NSMenuItem.separatorItem())
        else:
            if self.status_item.button():
                fallback_title = TrayViewModel.get_status_bar_title(None, now, status_mode, max_lookahead_min)
                self.status_item.button().setTitle_(fallback_title)

            item_none = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"✨ {t('no_remaining_today')}", None, ""
            )
            item_none.setEnabled_(False)
            self.menu.addItem_(item_none)
            self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        all_upcoming = [m for m in self.meetings if (m.get("end_time") and m["end_time"] > now) or (m.get("start_time") and m["start_time"] > now)]

        # 3. Upcoming Today List
        if len(today_upcoming) > 1:
            item_header = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(f"📅 {t('events_today_header')}", None, "")
            item_header.setEnabled_(False)
            self.menu.addItem_(item_header)

            for m in today_upcoming[1:6]:
                try:
                    idx = all_upcoming.index(m)
                except ValueError:
                    continue
                start_str = m["start_time"].astimezone().strftime("%H:%M") if m.get("start_time") else "--:--"
                p_type = m.get("pilot_type", "duck")
                icon = icon_map.get(p_type, "🦆")
                m_title = (m.get("title") or "Event").strip()
                title_short = m_title[:24] + "…" if len(m_title) > 24 else m_title

                tr_min = m.get("travel_time_minutes")
                sub_text = f"  {icon} {start_str} - {title_short}"
                if tr_min:
                    sub_text += f" (~{format_duration(tr_min)})"

                sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    sub_text, "openMeetingItem:", ""
                )
                sub_item.setTarget_(self)
                sub_item.setTag_(idx)
                self.menu.addItem_(sub_item)

            self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        if tomorrow_upcoming:
            item_header_tmrw = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(f"🗓️ {t('tomorrow_header')}", None, "")
            item_header_tmrw.setEnabled_(False)
            self.menu.addItem_(item_header_tmrw)

            for m in tomorrow_upcoming[:5]:
                try:
                    idx = all_upcoming.index(m)
                except ValueError:
                    continue
                start_str = m["start_time"].astimezone().strftime("%H:%M") if m.get("start_time") else "--:--"
                p_type = m.get("pilot_type", "duck")
                icon = icon_map.get(p_type, "🦆")
                m_title = (m.get("title") or "Event").strip()
                title_short = m_title[:24] + "…" if len(m_title) > 24 else m_title

                tr_min = m.get("travel_time_minutes")
                sub_text = f"  {icon} {start_str} - {title_short}"
                if tr_min:
                    sub_text += f" (~{format_duration(tr_min)})"

                sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    sub_text, "openMeetingItem:", ""
                )
                sub_item.setTarget_(self)
                sub_item.setTag_(idx)
                self.menu.addItem_(sub_item)

            self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 4. Updates & Utilities (Sync, Preferences, Quit)
        if updater_service.latest_release_info and updater_service.latest_release_info.get("has_update"):
            v_tag = updater_service.latest_release_info.get("tag_name") or "New Version"
            item_up = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                t("update_available_menu", version=v_tag), "onInstallUpdateAction:", "u"
            )
            item_up.setTarget_(self)
            self.menu.addItem_(item_up)
            self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        item_sync = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"🔄 {t('sync_calendars')}", "refreshCalendar:", "r"
        )
        item_sync.setTarget_(self)
        self.menu.addItem_(item_sync)

        item_settings = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"⚙️ {t('preferences')}", "openSettings:", ","
        )
        item_settings.setTarget_(self)
        self.menu.addItem_(item_settings)

        item_check = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"🔍 {t('check_updates')}", "onCheckUpdatesAction:", ""
        )
        item_check.setTarget_(self)
        self.menu.addItem_(item_check)

        # Status Bar Display Mode Quick Switcher
        item_display_mode = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "📊 Status Bar Mode", None, ""
        )
        mode_menu = AppKit.NSMenu.alloc().initWithTitle_("📊 Status Bar Mode")

        curr_mode = config.get("menubar_status_mode", "countdown")
        modes_def = [
            ("countdown", "⏳ Live Countdown (e.g. In 25m / Leave in 10m)"),
            ("event_time", "🕐 Start Time & Title (e.g. 20:00 Dinner)"),
            ("time_only", "⏱️ Time & Countdown (e.g. 20:00 in 25m)"),
            ("icon_only", "🦆 Icon Only (Minimal)")
        ]
        for idx, (mode_key, mode_label) in enumerate(modes_def):
            m_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                mode_label, "onSelectStatusMode:", ""
            )
            m_item.setTarget_(self)
            m_item.setTag_(idx)
            if mode_key == curr_mode:
                m_item.setState_(AppKit.NSControlStateValueOn)
            else:
                m_item.setState_(AppKit.NSControlStateValueOff)
            mode_menu.addItem_(m_item)

        item_display_mode.setSubmenu_(mode_menu)
        self.menu.addItem_(item_display_mode)

        if is_debug_mode():
            item_logs = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "📄 View Logs & Diagnostics...", "openLogFileAction:", "l"
            )
            item_logs.setTarget_(self)
            self.menu.addItem_(item_logs)

        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 5. Quit
        item_quit = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"❌ {t('quit')}", "quitApp:", "q"
        )
        item_quit.setTarget_(self)
        self.menu.addItem_(item_quit)

    @objc.IBAction
    def onSelectStatusMode_(self, sender):
        tag = sender.tag()
        modes = ["countdown", "event_time", "time_only", "icon_only"]
        if 0 <= tag < len(modes):
            config.set("menubar_status_mode", modes[tag])
            event_bus.publish("CONFIG_CHANGED", key="menubar_status_mode")
            self._last_menu_signature = None
            self.build_menu()

    @objc.IBAction
    def openDashboard_(self, sender):
        show_dashboard(0)

    @objc.IBAction
    def openSettings_(self, sender):
        show_dashboard(2)

    @objc.IBAction
    def onCheckUpdatesAction_(self, sender):
        updater_service.check_for_updates(background=True, manual=True)

    @objc.IBAction
    def onInstallUpdateAction_(self, sender):
        show_dashboard(2)
        updater_service.download_and_install_update(background=True)

    @objc.IBAction
    def openLogFileAction_(self, sender):
        open_log_file()

    def _on_update_event(self, **kwargs):
        def refresh_ui():
            self._last_menu_signature = None
            self.build_menu()
        AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(refresh_ui)

    @objc.IBAction
    def openNextMeeting_(self, sender):
        now = datetime.now().astimezone()
        upcoming = [m for m in self.meetings if (m.get("end_time") and m["end_time"] > now) or (m.get("start_time") and m["start_time"] > now)]
        if upcoming:
            url = upcoming[0].get("action_url") or upcoming[0].get("meeting_url")
            if url and url != "https://calendar.apple.com":
                webbrowser.open(url)

    @objc.IBAction
    def openMeetingItem_(self, sender):
        idx = sender.tag()
        now = datetime.now().astimezone()
        upcoming = [m for m in self.meetings if (m.get("end_time") and m["end_time"] > now) or (m.get("start_time") and m["start_time"] > now)]
        if 0 <= idx < len(upcoming):
            m = upcoming[idx]
            url = m.get("action_url") or m.get("meeting_url")
            if url and url != "https://calendar.apple.com":
                webbrowser.open(url)

    @objc.IBAction
    def refreshCalendar_(self, sender):
        logger.info("Manual calendar synchronization triggered")
        raw_meetings = calendar_service.sync_now()
        self.meetings = [m.to_dict() if isinstance(m, Meeting) else m for m in raw_meetings]
        self.build_menu()

    @objc.IBAction
    def quitApp_(self, sender):
        self.is_scanning = False
        AppKit.NSApplication.sharedApplication().terminate_(self)

    def _on_agenda_updated(self, meeting_objects=None, **kwargs):
        if meeting_objects is None:
            return
        from core.domain.models import Meeting
        self.meetings = [m.to_dict() if isinstance(m, Meeting) else m for m in meeting_objects]
        self.performSelectorOnMainThread_withObject_waitUntilDone_("refreshMenuOnMainThread:", None, False)

    @objc.IBAction
    def triggerBannerOnMainThread_(self, meeting_data):
        _run_banner(meeting_data)

    def run(self):
        self.app.run()

def run_menu_bar_app():
    """Initializes and runs the native macOS menu bar status item and event loop."""
    import sys
    app_instance = FlightDeckMenuBar.alloc().init()
    if app_instance is None:
        logger.error("Failed to allocate and initialize FlightDeckMenuBar!")
        return

    from core.app_controller import app_controller
    app_controller.start_background_loop()

    if "--silent" not in sys.argv and "--autostart" not in sys.argv:
        show_dashboard()

    logger.info("Entering macOS Application Run Loop...")
    app_instance.run()

if __name__ == "__main__":
    run_menu_bar_app()
