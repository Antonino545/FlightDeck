import os
import sys
import threading
import logging
import webbrowser
from datetime import datetime

import gi
gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')
from gi.repository import AyatanaAppIndicator3, Gtk, GLib

AppIndicator3 = AyatanaAppIndicator3

from core.services.config_service import config, is_debug_mode
from core.services.calendar_service import calendar_service
from core.services.reminder_engine import reminder_engine
from core.services.updater_service import updater_service
from core.services.event_bus import event_bus
from core.domain.models import format_duration
from core.logger import open_log_file
from ui.common.tray_viewmodel import TrayViewModel
from ui.linux.qt_tray_app import SignalBridge

logger = logging.getLogger("FlightDeck.AppIndicatorTray")

class AppIndicatorTrayApp:
    def __init__(self, app):
        self.app = app
        self._startup_catch_up_checked = False
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "assets", "icon.png"
        )
        
        self.indicator = AppIndicator3.Indicator.new(
            " " * 60,
            icon_path,
            AppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self.build_menu()
        
        self._bridge = SignalBridge()
        self._bridge.banner.connect(self.on_banner_trigger)
        self._bridge.menu.connect(self.build_menu)
        self._bridge.agenda.connect(self.on_agenda_updated)

        event_bus.subscribe("TRIGGER_BANNER", lambda **kwargs: self._bridge.banner.emit(kwargs.get("event_dict") or kwargs))
        event_bus.subscribe("REMINDER_TRIGGERED", lambda **kwargs: self._bridge.banner.emit(kwargs.get("event_dict") or kwargs))
        event_bus.subscribe("AGENDA_UPDATED", lambda **kwargs: self._bridge.agenda.emit())
        event_bus.subscribe("CALENDAR_SYNCED", lambda **kwargs: self._bridge.agenda.emit())
        event_bus.subscribe("CALENDAR_SYNCED", self._check_startup_catch_up)
        event_bus.subscribe("UPDATE_AVAILABLE", lambda **kwargs: self._bridge.menu.emit())
        event_bus.subscribe("UPDATE_CHECK_COMPLETE", lambda **kwargs: self._bridge.menu.emit())
        event_bus.subscribe("UPDATE_INSTALLED", lambda **kwargs: self._bridge.menu.emit())
        event_bus.subscribe("CONFIG_CHANGED", lambda **kwargs: calendar_service.request_background_sync("config_changed"))
        self._check_startup_catch_up(meetings=calendar_service.get_upcoming_meetings())

    def _check_startup_catch_up(self, meetings=None, **kwargs):
        """Surface one missed event after the first startup calendar result."""
        meetings = meetings or []
        if self._startup_catch_up_checked or not meetings:
            return
        self._startup_catch_up_checked = True
        reminder_engine.trigger_startup_catch_up(meetings)

    def build_menu(self):
        menu = Gtk.Menu()
        
        now = datetime.now().astimezone()
        meetings = calendar_service.get_upcoming_meetings()

        def _is_all_day_or_bill(ev):
            if isinstance(ev, dict):
                return bool(ev.get("is_all_day", False) or ev.get("category") == "bill" or ev.get("event_type") == "bill")
            return bool(getattr(ev, "is_all_day", False) or getattr(ev, "category", None) == "bill" or getattr(ev, "event_type", None) == "bill")

        today_up = [m for m in meetings if m.start_time and m.start_time.astimezone().date() == now.date() and ((m.end_time and m.end_time.astimezone() > now) or m.start_time.astimezone() > now) and not _is_all_day_or_bill(m)]

        icon_map = {"chef": "🍕", "captain": "✈️", "owl": "🎓", "driver": "🚗", "zen_duck": "🛋️", "duck": "🦆"}

        # Flight deck
        item_deck = Gtk.MenuItem(label="🦆 Open Flight Deck")
        item_deck.connect("activate", lambda _: self.show_flight_deck(0))
        menu.append(item_deck)
        menu.append(Gtk.SeparatorMenuItem())

        if today_up:
            nx = today_up[0]
            st = nx.start_time.strftime("%H:%M") if nx.start_time else "--:--"
            m_title = (nx.title or "Event").strip()
            p_type = getattr(nx, "pilot_type", "duck")
            icon_prefix = icon_map.get(p_type, "🦆")

            travel_min = getattr(nx, "travel_time_minutes", 0)
            dep_dt = getattr(nx, "departure_time", None)

            if travel_min and isinstance(dep_dt, datetime):
                dur_str = format_duration(travel_min)
                next_label = f"{icon_prefix} Next: {st} — {m_title} (🚗 ~{dur_str} • Leave at {dep_dt.strftime('%H:%M')})"
            elif travel_min:
                dur_str = format_duration(travel_min)
                next_label = f"{icon_prefix} Next: {st} — {m_title} (🚗 ~{dur_str})"
            else:
                next_label = f"{icon_prefix} Next: {st} — {m_title}"

            item_header = Gtk.MenuItem(label=next_label)
            item_header.set_sensitive(False)
            menu.append(item_header)

            action_url = getattr(nx, "action_url", None) or getattr(nx, "meeting_url", None)
            if action_url:
                btn_title = f"   {getattr(nx, 'action_btn_text', '🚀 Join Now')}"
                item_join = Gtk.MenuItem(label=btn_title)
                item_join.connect("activate", lambda _, u=action_url: webbrowser.open(u))
                menu.append(item_join)

            menu.append(Gtk.SeparatorMenuItem())
        else:
            item_none = Gtk.MenuItem(label="✨ No remaining events today")
            item_none.set_sensitive(False)
            menu.append(item_none)
            menu.append(Gtk.SeparatorMenuItem())

        item_sync = Gtk.MenuItem(label="🔄 Sync Calendars")
        item_sync.connect("activate", lambda _: threading.Thread(target=calendar_service.sync_now, daemon=True).start())
        menu.append(item_sync)

        item_pref = Gtk.MenuItem(label="⚙️ Settings & Preferences...")
        item_pref.connect("activate", lambda _: self.show_flight_deck(2))
        menu.append(item_pref)

        # Status Bar Mode
        mode_menu = Gtk.Menu()
        item_mode = Gtk.MenuItem(label="📊 Status Bar Mode")
        item_mode.set_submenu(mode_menu)
        
        curr_mode = config.get("menubar_status_mode", "countdown")
        modes_def = [
            ("countdown", "⏳ Live Countdown"),
            ("event_time", "🕐 Start Time & Title"),
            ("time_only", "⏱️ Time & Countdown"),
            ("icon_only", "🦆 Icon Only")
        ]
        for mode_key, mode_label in modes_def:
            m_act = Gtk.CheckMenuItem(label=mode_label)
            if mode_key == curr_mode:
                m_act.set_active(True)
            m_act.connect("activate", lambda w, m=mode_key: self.set_status_mode(m))
            mode_menu.append(m_act)
            
        menu.append(item_mode)

        if is_debug_mode():
            item_logs = Gtk.MenuItem(label="📄 View Logs & Diagnostics...")
            item_logs.connect("activate", lambda _: open_log_file())
            menu.append(item_logs)
            menu.append(Gtk.SeparatorMenuItem())

        update_info = updater_service.latest_release_info
        if update_info and update_info.get("has_update"):
            item_up = Gtk.MenuItem(label=f"🚀 Update Available: {update_info['tag_name']}")
            item_up.connect("activate", lambda _: updater_service.download_and_install_update())
            menu.append(item_up)
        else:
            item_chk = Gtk.MenuItem(label="🔍 Check for Updates...")
            item_chk.connect("activate", lambda _: updater_service.check_for_updates(background=True, manual=True))
            menu.append(item_chk)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label="Quit FlightDeck")
        item_quit.connect("activate", lambda _: self.app.quit())
        menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)
        
        # Make sure the current text is applied
        now = datetime.now().astimezone()
        primary_m = today_up[0] if today_up else None
        max_lookahead_min = int(config.get("max_countdown_lookahead_hours", 3)) * 60
        title = TrayViewModel.get_status_bar_title(primary_m, now, curr_mode, max_lookahead_min)
        if curr_mode == "icon_only" or not primary_m:
            self.indicator.set_label("", "")
        else:
            self.indicator.set_label(title, title)


    def set_status_mode(self, mode):
        config.set("menubar_status_mode", mode)
        self.build_menu()

    def on_agenda_updated(self, meeting_objects=None, **kwargs):
        if meeting_objects is None:
            meeting_objects = calendar_service.get_upcoming_meetings()
        try:
            now = datetime.now().astimezone()
            def _is_all_day_or_bill(ev):
                if isinstance(ev, dict):
                    return bool(ev.get("is_all_day", False) or ev.get("category") == "bill" or ev.get("event_type") == "bill")
                return bool(getattr(ev, "is_all_day", False) or getattr(ev, "category", None) == "bill" or getattr(ev, "event_type", None) == "bill")

            today_up = [m for m in meeting_objects if m.start_time and m.start_time.astimezone().date() == now.date() and ((m.end_time and m.end_time.astimezone() > now) or m.start_time.astimezone() > now) and not _is_all_day_or_bill(m)]

            primary_m = today_up[0] if today_up else None
            max_lookahead_min = int(config.get("max_countdown_lookahead_hours", 3)) * 60
            status_mode = config.get("menubar_status_mode", "countdown")
            title = TrayViewModel.get_status_bar_title(primary_m, now, status_mode, max_lookahead_min)

            if status_mode == "icon_only" or not primary_m:
                self.indicator.set_label("", "")
            else:
                self.indicator.set_label(title, title)
                
            self.build_menu()
        except Exception as e:
            logger.warning(f"Error in AppIndicatorTray agenda update: {e}")

    def show_flight_deck(self, tab_index: int = 0):
        try:
            from ui.linux.qt_dashboard import show_qt_dashboard
            show_qt_dashboard(tab_index)
        except Exception as e:
            logger.warning(f"Flight Deck window error: {e}")
            try:
                from ui.linux.qt_dashboard import show_qt_dashboard_error
                show_qt_dashboard_error(e)
            except Exception:
                logger.exception("Unable to show the Flight Deck startup error window.")

    def on_banner_trigger(self, event_dict=None, meeting=None, stage=None, **kwargs):
        try:
            if isinstance(event_dict, dict) and "meeting" in event_dict:
                meeting = event_dict.get("meeting")
                stage = event_dict.get("stage", stage)
                event_dict = event_dict.get("event_dict")

            data = event_dict or (meeting.to_dict() if hasattr(meeting, "to_dict") else meeting) or {}
            if stage is not None and "reminder_stage" not in data:
                data["reminder_stage"] = stage
            from ui.linux.banner.qt_banner import show_qt_banner
            show_qt_banner(data)
        except Exception as e:
            logger.error(f"Error showing Qt banner: {e}")
