"""
Banner Window Controller for FlightDeck.
Manages transparent overlay window, multi-screen placement, animation timer, sound effects, and user actions.
Supports full-screen spaces overlay across all macOS desktops.
"""
import AppKit
import objc
import webbrowser
import subprocess
import time
import threading
import logging
from typing import Dict, Any, Optional, Callable

from core.services.config_service import config
from core.services.sound_service import play_chime
from .banner_view import QuakPitBannerView
from .quiet_banner_view import QuietReminderView
from .update_banner_view import MacUpdateBannerView

logger = logging.getLogger("FlightDeck.BannerController")

class QuakPitFlyingBanner(AppKit.NSObject):
    def initWithMeetingData_callback_(self, meeting_data: Dict[str, Any], on_close_callback: Optional[Callable] = None):
        self = objc.super(QuakPitFlyingBanner, self).init()
        if self is None:
            return None
        self.meeting_data = meeting_data
        self.on_close_callback = on_close_callback
        self.window = None
        self.timer = None
        self.is_paused = False
        self.is_quiet = bool(meeting_data.get("is_quiet_reminder", False))
        self.is_update = bool(meeting_data.get("is_update_banner", False))
        self.action_url = meeting_data.get("action_url") or meeting_data.get("meeting_url") or meeting_data.get("maps_url")
        self._esc_monitor = None
        return self

    def show(self) -> None:
        mouse_loc = AppKit.NSEvent.mouseLocation()
        target_screen = None
        for s in AppKit.NSScreen.screens():
            if AppKit.NSPointInRect(mouse_loc, s.frame()):
                target_screen = s
                break
        if target_screen is None:
            target_screen = AppKit.NSScreen.mainScreen() or (AppKit.NSScreen.screens()[0] if AppKit.NSScreen.screens() else None)

        screen_rect = target_screen.frame() if target_screen else AppKit.NSMakeRect(0, 0, 1440, 900)

        is_quiet = self.meeting_data.get("is_quiet_reminder", False)
        is_update = self.meeting_data.get("is_update_banner", False)

        if is_update:
            window_w = 512.0
            window_h = 160.0
            x_pos = screen_rect.origin.x + screen_rect.size.width - window_w - 24.0
            final_y = screen_rect.origin.y + screen_rect.size.height - window_h - 40.0
            start_y = screen_rect.origin.y + screen_rect.size.height + 20.0

            self.x_pos = x_pos
            self.final_y = final_y
            self.curr_y = start_y
            self.window_w = window_w
            self.window_h = window_h
            self.screen_top = screen_rect.origin.y + screen_rect.size.height
            self.is_closing = False
            self.is_animating_in = True

            frame = AppKit.NSMakeRect(x_pos, start_y, window_w, window_h)
        elif is_quiet:
            window_w = 360.0
            window_h = 84.0
            x_pos = screen_rect.origin.x + screen_rect.size.width - window_w - 24.0
            y_pos = screen_rect.origin.y + screen_rect.size.height - window_h - 40.0
            frame = AppKit.NSMakeRect(x_pos, y_pos, window_w, window_h)
        else:
            window_w = screen_rect.size.width
            window_h = 220.0

            banner_pos = config.get("banner_position", "top")
            if banner_pos == "bottom":
                y_pos = screen_rect.origin.y + 40.0
            else:
                y_pos = screen_rect.origin.y + screen_rect.size.height - window_h - 20.0

            frame = AppKit.NSMakeRect(screen_rect.origin.x, y_pos, window_w, window_h)

        # -------------------------------------------------------------------------
        # CRITICAL: DO NOT MODIFY OR REVERT THIS WINDOW / PANEL CONFIGURATION!
        # This exact setup (NSPanel + NSWindowStyleMaskNonactivatingPanel +
        # NSScreenSaverWindowLevel + NSWindowCollectionBehaviorFullScreenAuxiliary
        # + orderFrontRegardless) is REQUIRED for banners to float over native
        # macOS full-screen apps, spaces, games, Keynote, and media players
        # without glitching or stealing key window focus.
        # -------------------------------------------------------------------------
        style_mask = AppKit.NSWindowStyleMaskBorderless | AppKit.NSWindowStyleMaskNonactivatingPanel

        self.window = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style_mask,
            AppKit.NSBackingStoreBuffered,
            False
        )

        self.window.setReleasedWhenClosed_(False)
        self.window.setHidesOnDeactivate_(False)
        self.window.setFloatingPanel_(True)
        self.window.setWorksWhenModal_(True)
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())

        # NSScreenSaverWindowLevel guarantees floating above all full-screen spaces & apps
        self.window.setLevel_(AppKit.NSScreenSaverWindowLevel)

        # For flying banner, start with ignoresMouseEvents=True so transparent full-width
        # trajectory passes all clicks to underlying apps until mouse is over interactive parts.
        if not is_quiet and not is_update:
            self.window.setIgnoresMouseEvents_(True)
        else:
            self.window.setIgnoresMouseEvents_(False)
        self.window.setAcceptsMouseMovedEvents_(True)
        self.window.setMovableByWindowBackground_(False)

        # Collection behavior: join all spaces, auxiliary window above full screen apps, stationary
        behavior = (
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorIgnoresCycle
        )
        self.window.setCollectionBehavior_(behavior)

        if is_update:
            self.banner_view = MacUpdateBannerView.alloc().initWithFrame_meetingData_controller_(
                AppKit.NSMakeRect(0, 0, window_w, window_h),
                self.meeting_data,
                self
            )
            # Auto dismiss after 7 seconds for up-to-date banner, 10 seconds for update available
            dismiss_delay = 7.0 if self.meeting_data.get("is_up_to_date") else 10.0
            AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                dismiss_delay,
                self,
                objc.selector(self.dismissIfIdleAction_, signature=b"v@:@"),
                None,
                False
            )
        elif is_quiet:
            self.banner_view = QuietReminderView.alloc().initWithFrame_meetingData_controller_(
                AppKit.NSMakeRect(0, 0, window_w, window_h),
                self.meeting_data,
                self
            )
            # Auto dismiss after 6 seconds for quiet reminder
            AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                6.0,
                self,
                objc.selector(self.dismissAction_, signature=b"v@:@"),
                None,
                False
            )
        else:
            self.banner_view = QuakPitBannerView.alloc().initWithFrame_meetingData_controller_(
                AppKit.NSMakeRect(0, 0, window_w, window_h),
                self.meeting_data,
                self
            )
        self.window.setContentView_(self.banner_view)

        # Display above everything on the active full-screen space without stealing key focus
        self.window.orderFrontRegardless()

        self.play_chime()

        self.timer = AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / 60.0,
            self.banner_view,
            objc.selector(self.banner_view.stepAnimation_, signature=b"v@:@"),
            None,
            True
        )
        AppKit.NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, AppKit.NSRunLoopCommonModes)

        def _esc_key_monitor(event):
            if event.keyCode() == 53:  # Escape
                self.dismiss()
                return None
            return event

        self._esc_monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            AppKit.NSEventMaskKeyDown,
            _esc_key_monitor
        )

    def play_chime(self) -> None:
        if self.is_quiet:
            return
        play_chime(event_dict=self.meeting_data)

    def trigger_action(self) -> None:
        m_id = str(self.meeting_data.get("id") or self.meeting_data.get("uid") or "")
        try:
            from core.services.state_store import banner_history_store
            banner_history_store.record_action(m_id, "action_clicked")
        except Exception:
            pass

        if self.meeting_data.get("is_update_banner"):
            if not self.meeting_data.get("is_up_to_date") and not self.meeting_data.get("is_update_error"):
                from core.services.updater_service import updater_service
                updater_service.download_and_install_update(background=True)
        elif self.action_url:
            webbrowser.open(self.action_url)
        self.dismiss()

    def trigger_arrived(self) -> None:
        try:
            from core.services.reminder_engine import reminder_engine
            from core.services.state_store import banner_history_store
            from core.domain.models import Meeting
            if isinstance(self.meeting_data, Meeting):
                m_id = self.meeting_data.id
            else:
                m_id = str(self.meeting_data.get("id") or self.meeting_data.get("uid") or "")
                if not m_id:
                    m_title = self.meeting_data.get("title", "")
                    m_start = self.meeting_data.get("start_time")
                    time_str = m_start.strftime("%Y%m%d%H%M") if hasattr(m_start, "strftime") else "000000000000"
                    m_id = f"{m_title}_{time_str}"
            reminder_engine.mark_arrived(m_id)
            banner_history_store.record_action(m_id, "arrived")
            try:
                from core.services.event_bus import event_bus
                event_bus.publish("MARK_ARRIVED", meeting_id=m_id)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error marking arrived: {e}")
        self.dismiss()

    def trigger_mark_paid(self) -> None:
        try:
            from core.services.reminder_engine import reminder_engine
            from core.services.state_store import banner_history_store
            from core.domain.models import Meeting
            if isinstance(self.meeting_data, Meeting):
                m_id = self.meeting_data.id
            else:
                m_id = str(self.meeting_data.get("id") or self.meeting_data.get("uid") or "")
                if not m_id:
                    m_title = self.meeting_data.get("title", "")
                    m_start = self.meeting_data.get("start_time")
                    time_str = m_start.strftime("%Y%m%d%H%M") if hasattr(m_start, "strftime") else "000000000000"
                    m_id = f"{m_title}_{time_str}"
            reminder_engine.mark_bill_paid(m_id)
            banner_history_store.record_action(m_id, "bill_paid")
            try:
                from core.services.event_bus import event_bus
                event_bus.publish("MARK_PAID", meeting_id=m_id)
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error marking bill paid: {e}")
        self.dismiss()

    def trigger_snooze(self, duration_seconds: int = None) -> None:
        m_id = str(self.meeting_data.get("id") or self.meeting_data.get("uid") or "")
        try:
            from core.services.state_store import banner_history_store
            banner_history_store.record_action(m_id, "snoozed")
        except Exception:
            pass

        snooze_sec = duration_seconds if duration_seconds else int(config.get("default_snooze_seconds", 120))
        m_copy = dict(self.meeting_data)
        self.dismiss()

        def _re_notify():
            time.sleep(snooze_sec)
            show_banner_async(m_copy)

        threading.Thread(target=_re_notify, daemon=True).start()

    def trigger_acknowledge(self) -> None:
        """User explicitly acknowledged the event-time reminder."""
        title = self.meeting_data.get("title", "Event") if isinstance(self.meeting_data, dict) else getattr(self.meeting_data, "title", "Event")
        m_id = str(self.meeting_data.get("id") or self.meeting_data.get("uid") or "")
        try:
            from core.services.state_store import banner_history_store
            banner_history_store.record_action(m_id, "acknowledged")
        except Exception:
            pass
        logger.info(f"User acknowledged reminder for: '{title}'")
        self.dismiss()

    @objc.IBAction
    def dismissAction_(self, sender):
        self.dismiss()

    @objc.IBAction
    def dismissIfIdleAction_(self, sender):
        if hasattr(self, "banner_view") and getattr(self.banner_view, "install_mode", False):
            return
        if getattr(self, "is_paused", False):
            return
        self.dismiss()

    def dismiss(self) -> None:
        if self.meeting_data.get("is_update_banner") and not getattr(self, "is_closing", False):
            self.is_closing = True
            return
        self.finish_dismiss()

    def finish_dismiss(self) -> None:
        if self.timer:
            self.timer.invalidate()
            self.timer = None
        if self._esc_monitor:
            AppKit.NSEvent.removeMonitor_(self._esc_monitor)
            self._esc_monitor = None
        if self.window:
            self.window.orderOut_(None)
            self.window = None
        if self.on_close_callback:
            self.on_close_callback()

_current_banner_controller = None

def _maybe_show_next_banner() -> None:
    global _current_banner_controller
    if _current_banner_controller is not None:
        return

    from ui.common.banner_queue import banner_queue
    next_item = banner_queue.pop_next()
    if next_item:
        def _on_close():
            global _current_banner_controller
            _current_banner_controller = None
            _maybe_show_next_banner()

        controller = QuakPitFlyingBanner.alloc().initWithMeetingData_callback_(next_item.meeting_data, _on_close)
        _current_banner_controller = controller
        controller.show()

def _run_banner(meeting_data: Dict[str, Any]) -> None:
    from ui.common.banner_queue import banner_queue, BannerQueueItem
    item = BannerQueueItem(meeting_data)
    banner_queue.push(item)
    _maybe_show_next_banner()

def show_banner_async(meeting_data: Dict[str, Any]) -> None:
    """Safely dispatches banner display onto the AppKit main UI thread."""
    def _main_show():
        _run_banner(meeting_data)

    AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(_main_show)
