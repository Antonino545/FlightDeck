"""
Banner View for macOS FlightDeck Banners.
Coordinates Cocoa view lifecycle, animation loop ticks, mouse interaction,
and delegates HUD rendering, particle physics, and speech quotes to specialized modules.
"""
import math
from datetime import datetime
from typing import Dict, Any, Optional
import AppKit
import objc

from ui.macos.theme import Theme
from core.services.config_service import config
from core.services.language_service import t
from core.domain.models import format_duration
from ui.common.banner_speech import build_pilot_speech_text, build_pilot_hover_speech_text
from ui.common.banner_particles import BannerParticleEngine, compute_airplane_flight_dynamics
from ui.common.banner_formatting import compute_countdown_text, MODE_ICONS
from .renderers import get_pilot_renderer
from .banner_layout import BannerLayout
from .banner_hud_painter import BannerHUDPainter

def _norm_dt(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v).astimezone()
    return None

class QuakPitBannerView(AppKit.NSView):
    """Refactored, high-performance macOS banner canvas view."""

    def initWithFrame_meetingData_controller_(self, frame, meeting_data: Dict[str, Any], controller=None):
        self = objc.super(QuakPitBannerView, self).initWithFrame_(frame)
        if self is None:
            return None

        self.meeting_data = meeting_data
        self.controller = controller

        # Extract event attributes
        self.title = meeting_data.get("title", "Upcoming Meeting")
        self.start_time = _norm_dt(meeting_data.get("start_time"))
        self.end_time = _norm_dt(meeting_data.get("end_time"))
        self.location = meeting_data.get("location")
        self.provider = meeting_data.get("provider", "Calendar")
        self.action_url = meeting_data.get("action_url") or meeting_data.get("meeting_url") or meeting_data.get("maps_url")
        self.pilot_type = meeting_data.get("pilot_type", "duck")
        self.classroom = meeting_data.get("classroom")
        self.teacher = meeting_data.get("teacher")
        self.is_travel = meeting_data.get("is_travel", False)
        self.travel_time_minutes = meeting_data.get("travel_time_minutes")
        self.travel_distance_km = meeting_data.get("travel_distance_km")
        self.transport_mode = meeting_data.get("transport_mode", config.get("transport_mode", "transit"))
        self.departure_time = _norm_dt(meeting_data.get("departure_time"))
        self.origin_address = meeting_data.get("origin_address")
        self.eta_text = meeting_data.get("eta_text")
        self.category = meeting_data.get("category") or meeting_data.get("event_type") or "general"
        self.is_bill = (self.category == "bill")

        # Determine Late Status
        self.is_late = self._compute_is_late()

        # Modular mascot customization & renderer
        self.animal = meeting_data.get("animal")
        self.outfit = meeting_data.get("outfit")
        self.renderer = get_pilot_renderer(
            self.pilot_type,
            animal=self.animal,
            outfit=self.outfit,
            accessories=meeting_data.get("accessories"),
        )

        # Stage metadata
        self.reminder_stage = meeting_data.get("reminder_stage")
        self.renderer.status = "urgent" if self.is_late else "upcoming" if self.reminder_stage and self.reminder_stage > 0 else "normal"

        # Flight dynamics & geometry (Boost speed by 40% when late)
        base_speed = float(config.get("flight_speed", 3.2))
        self.speed = base_speed * 1.40 if self.is_late else base_speed
        self.x = -720.0
        self.base_y = 48.0
        self.tick = 0
        self.is_paused = False

        self.has_real_url = bool(
            self.action_url and
            self.action_url.strip() and
            self.action_url != "https://calendar.apple.com"
        )
        self.has_maps_url = bool(
            self.has_real_url and
            ("maps.apple.com" in self.action_url.lower() or
             "maps.google.com" in self.action_url.lower() or
             "google.com/maps" in self.action_url.lower())
        ) or self.is_travel

        if not meeting_data.get("action_btn_text") and self.has_maps_url:
            self.action_btn_text = t("agenda_maps_button", default="🗺️ Directions")
        else:
            self.action_btn_text = meeting_data.get("action_btn_text", "🚀 Join Flight")

        # Determine slim card layout for buttonless advance flyby
        self.is_slim = bool(
            self.reminder_stage is not None and
            self.reminder_stage > 0 and
            not self.has_real_url and
            not self.has_maps_url
        )

        # Modular Engines & Painters
        self.banner_w = 535.0
        self.banner_h = 96.0 if self.is_slim else 132.0
        self.layout_mgr = BannerLayout(banner_w=self.banner_w, banner_h=self.banner_h)
        self.hud_painter = BannerHUDPainter()
        self.particle_engine = BannerParticleEngine()

        # Hover & Click Interaction State
        self.pressed_button = None
        self.hovered_button = None

        # Precompute Theme Palette & Cached Details/Speech Strings
        self._palette = self._build_theme_palette()
        self._init_cached_resources()

        tracking_options = (
            AppKit.NSTrackingMouseEnteredAndExited |
            AppKit.NSTrackingMouseMoved |
            AppKit.NSTrackingActiveAlways |
            AppKit.NSTrackingInVisibleRect
        )
        self.tracking_area = AppKit.NSTrackingArea.alloc().initWithRect_options_owner_userInfo_(
            self.bounds(),
            tracking_options,
            self,
            None
        )
        self.addTrackingArea_(self.tracking_area)

        return self

    @property
    def flame_particles(self):
        return self.particle_engine.flame_particles

    @property
    def smoke_particles(self):
        return self.particle_engine.smoke_particles

    @property
    def sparkle_particles(self):
        return self.particle_engine.sparkle_particles

    def _compute_is_late(self) -> bool:
        if isinstance(self.meeting_data, dict):
            if self.meeting_data.get("is_late") is not None:
                return bool(self.meeting_data["is_late"])
            if self.meeting_data.get("is_test_banner") or self.meeting_data.get("is_test"):
                return False
        now = datetime.now().astimezone()
        if self.is_travel and self.departure_time:
            dep = self.departure_time
            if isinstance(dep, datetime):
                dep = dep.astimezone() if dep.tzinfo else dep.replace(tzinfo=now.tzinfo)
                return now > dep
        if self.start_time:
            st = self.start_time
            if isinstance(st, datetime):
                st = st.astimezone() if st.tzinfo else st.replace(tzinfo=now.tzinfo)
                return now > st
        return False

    def _init_cached_resources(self):
        # Truncate title cleanly (sanitizing newlines/tabs)
        clean_title = " ".join(str(self.title or "").split())
        max_chars = 34
        self._cached_short_title = clean_title if len(clean_title) <= max_chars else clean_title[:max_chars - 3] + "..."

        # Precompute static details string
        detail_text = ""
        if self.start_time:
            s_time = self.start_time.astimezone().strftime("%H:%M")
            if self.end_time:
                e_time = self.end_time.astimezone().strftime("%H:%M")
                detail_text = f"🕒 {s_time} - {e_time}"
            else:
                detail_text = f"🕒 At {s_time}"

        if self.classroom:
            clean_cls = " ".join(str(self.classroom).split())
            detail_text += f"  •  🏫 {clean_cls}"
        elif self.location:
            clean_loc = " ".join(str(self.location).split())
            loc_short = clean_loc if len(clean_loc) <= 24 else clean_loc[:21] + "..."
            detail_text += f"  •  📍 {loc_short}"
            if self.travel_time_minutes:
                mode_icon = MODE_ICONS.get(self.transport_mode, "🚆")
                dur_str = format_duration(self.travel_time_minutes)
                detail_text += f" ({mode_icon} ~{dur_str})"
        elif self.action_url and ("meet.google.com" in self.action_url or "zoom" in self.action_url or "teams" in self.action_url or "serenis" in self.action_url):
            detail_text += "  •  🌐 Online Meeting"

        if self.teacher:
            clean_tch = " ".join(str(self.teacher).split())
            detail_text += f" ({clean_tch})"

        self._cached_detail_text = detail_text
        self._cached_speech_text = build_pilot_speech_text(
            self.meeting_data,
            animal=self.animal,
            outfit=self.outfit,
            pilot_type=self.pilot_type,
            is_late=self.is_late,
            classroom=self.classroom,
            title=self.title,
            provider=self.provider,
            reminder_stage=self.reminder_stage
        )
        self._cached_hover_speech_text = build_pilot_hover_speech_text(
            animal=self.animal or self.pilot_type
        )
        self._cached_countdown_text, self._cached_is_urgent = compute_countdown_text(
            self.meeting_data,
            self.start_time,
            self.departure_time,
            self.travel_time_minutes,
            self.is_travel,
            self.transport_mode,
            self.classroom,
            self.pilot_type,
            self.provider,
            self.title
        )

    def _get_button_rects(self, banner_x, banner_y):
        return self.layout_mgr.get_button_rects(
            banner_x, banner_y, self.has_maps_url, self.has_real_url, self.reminder_stage,
            is_bill=getattr(self, "is_bill", False)
        )

    def _get_interactive_rects(self, banner_x: float, banner_y: float, plane_x: float, plane_y: float):
        rects = self._get_button_rects(banner_x, banner_y)
        plane_rect = self.layout_mgr.get_plane_rect(plane_x, plane_y)
        bubble_rect = None
        speech = self._cached_hover_speech_text if (self.hovered_button == "plane" and self._cached_hover_speech_text) else self._cached_speech_text
        if speech:
            text_len = len(speech) * 6.8
            bubble_rect = self.layout_mgr.get_speech_bubble_rect(
                plane_x, plane_y, banner_x + self.banner_w, text_len, self.tick
            )
        return rects, plane_rect, bubble_rect

    def _compute_coordinates(self) -> tuple[float, float, float, float, float, float, float]:
        """
        Computes (banner_x, banner_y, banner_w, banner_h, dyn_px, dyn_py, pitch_deg)
        incorporating flight bobbing, dynamic airplane float, and pitch angle.
        """
        y_wave = self.base_y + math.sin(self.tick * 0.038) * 8.0
        banner_x = self.x
        banner_y = y_wave + (20.0 if self.is_slim else -10.0)
        base_px = self.x + 620.0
        base_py = y_wave + (19.0 if self.is_slim else 4.0)

        float_x, float_y, pitch_deg = compute_airplane_flight_dynamics(self.tick, self.is_paused)
        dyn_px = base_px + float_x
        dyn_py = base_py + float_y

        return banner_x, banner_y, self.banner_w, self.banner_h, dyn_px, dyn_py, pitch_deg

    def hitTest_(self, aPoint):
        if self.superview() is not None:
            loc = self.convertPoint_fromView_(aPoint, self.superview())
        else:
            loc = self.convertPoint_fromView_(aPoint, None)

        banner_x, banner_y, _, _, dyn_px, dyn_py, _ = self._compute_coordinates()
        rects, plane_rect, bubble_rect = self._get_interactive_rects(banner_x, banner_y, dyn_px, dyn_py)

        if (
            AppKit.NSPointInRect(loc, plane_rect) or
            AppKit.NSPointInRect(loc, rects["card"]) or
            AppKit.NSPointInRect(loc, rects["close_hit"]) or
            (bubble_rect is not None and AppKit.NSPointInRect(loc, bubble_rect))
        ):
            return self

        return None

    def mouseEntered_(self, event):
        # Do not pause on general window enter; pausing is handled selectively for airplane / card.
        pass

    def _safe_set_cursor(self, pointing_hand: bool = False):
        try:
            cursor = AppKit.NSCursor.pointingHandCursor() if pointing_hand else AppKit.NSCursor.arrowCursor()
            if cursor is not None and hasattr(cursor, "set"):
                cursor.set()
        except Exception:
            pass

    def mouseExited_(self, event):
        self.is_paused = False
        self.pressed_button = None
        self.hovered_button = None
        self._safe_set_cursor(pointing_hand=False)
        if self.window():
            self.window().setIgnoresMouseEvents_(True)
        self.setNeedsDisplay_(True)

    def mouseMoved_(self, event):
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        self._update_mouse_interaction_at_point(loc)

    def _update_mouse_interaction_at_point(self, loc):
        banner_x, banner_y, _, _, dyn_px, dyn_py, _ = self._compute_coordinates()
        rects, plane_rect, bubble_rect = self._get_interactive_rects(banner_x, banner_y, dyn_px, dyn_py)
        old_hover = self.hovered_button

        is_over_interactive = False

        if AppKit.NSPointInRect(loc, rects["close_hit"]):
            self.hovered_button = "close"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=True)
        elif AppKit.NSPointInRect(loc, rects["action"]):
            self.hovered_button = "action"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=True)
        elif AppKit.NSPointInRect(loc, rects["arrived"]):
            self.hovered_button = "arrived"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=True)
        elif AppKit.NSPointInRect(loc, rects["snooze1"]):
            self.hovered_button = "snooze1"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=True)
        elif AppKit.NSPointInRect(loc, rects["snooze2"]):
            self.hovered_button = "snooze2"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=True)
        elif AppKit.NSPointInRect(loc, rects["card"]):
            self.hovered_button = "card"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=False)
        elif AppKit.NSPointInRect(loc, plane_rect) or (bubble_rect is not None and AppKit.NSPointInRect(loc, bubble_rect)):
            self.hovered_button = "plane"
            is_over_interactive = True
            self._safe_set_cursor(pointing_hand=True)
        else:
            self.hovered_button = None
            is_over_interactive = False
            self._safe_set_cursor(pointing_hand=False)

        self.is_paused = is_over_interactive

        win = self.window()
        if win is not None:
            should_ignore = not is_over_interactive
            if win.ignoresMouseEvents() != should_ignore:
                win.setIgnoresMouseEvents_(should_ignore)

        if old_hover != self.hovered_button:
            self.setNeedsDisplay_(True)

    def mouseDown_(self, event):
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        banner_x, banner_y, _, _, dyn_px, dyn_py, _ = self._compute_coordinates()
        rects, plane_rect, bubble_rect = self._get_interactive_rects(banner_x, banner_y, dyn_px, dyn_py)

        if AppKit.NSPointInRect(loc, rects["close_hit"]):
            self.pressed_button = "close"
        elif AppKit.NSPointInRect(loc, rects["action"]):
            self.pressed_button = "action"
        elif AppKit.NSPointInRect(loc, rects["arrived"]):
            self.pressed_button = "arrived"
        elif AppKit.NSPointInRect(loc, rects["snooze1"]):
            self.pressed_button = "snooze1"
        elif AppKit.NSPointInRect(loc, rects["snooze2"]):
            self.pressed_button = "snooze2"
        elif AppKit.NSPointInRect(loc, rects["card"]):
            self.pressed_button = "card"
        elif AppKit.NSPointInRect(loc, plane_rect) or (bubble_rect is not None and AppKit.NSPointInRect(loc, bubble_rect)):
            self.pressed_button = "plane"
        else:
            self.pressed_button = None

        self.setNeedsDisplay_(True)

    def mouseUp_(self, event):
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        banner_x, banner_y, _, _, dyn_px, dyn_py, _ = self._compute_coordinates()
        rects, plane_rect, bubble_rect = self._get_interactive_rects(banner_x, banner_y, dyn_px, dyn_py)

        clicked = self.pressed_button
        self.pressed_button = None
        self.setNeedsDisplay_(True)

        if clicked == "close" and AppKit.NSPointInRect(loc, rects["close_hit"]):
            if self.controller:
                self.controller.dismiss()
        elif clicked == "action" and AppKit.NSPointInRect(loc, rects["action"]):
            if self.controller:
                if self.has_real_url:
                    self.controller.trigger_action()
                else:
                    self.controller.trigger_acknowledge()
        elif clicked == "arrived" and AppKit.NSPointInRect(loc, rects["arrived"]):
            if self.controller:
                if getattr(self, "is_bill", False):
                    self.controller.trigger_mark_paid()
                else:
                    self.controller.trigger_arrived()
        elif clicked == "snooze1" and AppKit.NSPointInRect(loc, rects["snooze1"]):
            if self.controller:
                if self.reminder_stage == 0:
                    self.controller.trigger_acknowledge()
                else:
                    self.controller.trigger_snooze(300) # 5 minutes
        elif clicked == "snooze2" and AppKit.NSPointInRect(loc, rects["snooze2"]):
            if self.controller:
                if self.reminder_stage == 0:
                    self.controller.trigger_acknowledge()
                else:
                    self.controller.trigger_arrived() # Skip event
        elif (clicked in ("card", "plane")) and (
            AppKit.NSPointInRect(loc, rects["card"]) or
            AppKit.NSPointInRect(loc, plane_rect) or
            (bubble_rect is not None and AppKit.NSPointInRect(loc, bubble_rect))
        ):
            if self.controller:
                if self.has_real_url:
                    self.controller.trigger_action()
                else:
                    self.controller.trigger_acknowledge()

    def stepAnimation_(self, timer):
        self.tick += 1
        screen_w = self.bounds().size.width

        # Check real-time hardware cursor position even if mouse is stationary
        win = self.window()
        if win is not None:
            screen_loc = AppKit.NSEvent.mouseLocation()
            if AppKit.NSPointInRect(screen_loc, win.frame()):
                win_loc = win.convertPointFromScreen_(screen_loc)
                loc = self.convertPoint_fromView_(win_loc, None)
                self._update_mouse_interaction_at_point(loc)
            else:
                if self.is_paused:
                    self.is_paused = False
                    self.hovered_button = None
                if not win.ignoresMouseEvents():
                    win.setIgnoresMouseEvents_(True)

        if not self.is_paused:
            self.x += self.speed
            if self.x > screen_w + 700:
                if self.reminder_stage is not None and self.reminder_stage > 0:
                    if self.controller:
                        self.controller.dismiss()
                    return
                else:
                    self.x = -720.0

        if self.tick % 30 == 0:
            self._cached_countdown_text, self._cached_is_urgent = compute_countdown_text(
                self.meeting_data,
                self.start_time,
                self.departure_time,
                self.travel_time_minutes,
                self.is_travel,
                self.transport_mode,
                self.classroom,
                self.pilot_type,
                self.provider,
                self.title
            )

        _, _, _, _, dyn_px, dyn_py, _ = self._compute_coordinates()
        self.particle_engine.emit_and_update(
            dyn_px, dyn_py, self.tick, self.is_late, self.is_paused, self.pilot_type
        )
        self.setNeedsDisplay_(True)

    def _build_theme_palette(self):
        if self.pilot_type == "chef":
            accent = Theme.PEACH
            accent_bright = Theme.YELLOW
            btn_gradient_top = Theme.PEACH
            btn_gradient_bot = Theme.MAROON
        elif self.pilot_type == "captain":
            accent = Theme.SAPPHIRE
            accent_bright = Theme.SKY
            btn_gradient_top = Theme.SAPPHIRE
            btn_gradient_bot = Theme.BLUE
        elif self.pilot_type == "owl":
            accent = Theme.MAUVE
            accent_bright = Theme.LAVENDER
            btn_gradient_top = Theme.MAUVE
            btn_gradient_bot = Theme.LAVENDER
        elif self.pilot_type == "gym":
            accent = Theme.RED
            accent_bright = Theme.PEACH
            btn_gradient_top = Theme.RED
            btn_gradient_bot = Theme.MAROON
        elif self.pilot_type in ("driver", "racer"):
            accent = Theme.YELLOW
            accent_bright = Theme.PEACH
            btn_gradient_top = Theme.YELLOW
            btn_gradient_bot = Theme.PEACH
        elif self.pilot_type == "platypus":
            accent = Theme.TEAL
            accent_bright = Theme.SKY
            btn_gradient_top = Theme.TEAL
            btn_gradient_bot = Theme.SAPPHIRE
        elif self.pilot_type == "squirrel":
            accent = Theme.PEACH
            accent_bright = Theme.YELLOW
            btn_gradient_top = Theme.PEACH
            btn_gradient_bot = Theme.MAROON
        else:
            accent = Theme.GREEN
            accent_bright = Theme.TEAL
            btn_gradient_top = Theme.GREEN
            btn_gradient_bot = Theme.TEAL

        return {
            "accent": accent,
            "accent_bright": accent_bright,
            "btn_gradient_top": btn_gradient_top,
            "btn_gradient_bot": btn_gradient_bot,
            "card_tint": Theme.BASE
        }

    def drawRect_(self, rect):
        AppKit.NSColor.clearColor().set()
        AppKit.NSRectFill(rect)

        palette = self._palette
        accent = palette["accent"]

        banner_x, banner_y, banner_w, banner_h, dyn_px, dyn_py, pitch_deg = self._compute_coordinates()

        # 1. Turbo Flame Particles
        for f in self.particle_engine.flame_particles:
            stage = f["color_stage"]
            if stage < 1.0:
                f_col = AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.90, 0.30, f["alpha"])
            elif stage < 2.0:
                f_col = AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.52, 0.15, f["alpha"])
            else:
                f_col = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.22, 0.18, f["alpha"] * 0.8)

            f_col.set()
            f_path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
                AppKit.NSMakeRect(f["x"] - f["r"], f["y"] - f["r"], f["r"] * 2, f["r"] * 2)
            )
            f_path.fill()

        # 2. Standard Smoke & Sparkles
        for p in self.particle_engine.smoke_particles:
            smoke_col = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.85, 0.88, 0.98, p["alpha"] * 0.50)
            smoke_col.set()
            smoke_path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
                AppKit.NSMakeRect(p["x"] - p["r"], p["y"] - p["r"], p["r"] * 2, p["r"] * 2)
            )
            smoke_path.fill()

        for s in self.particle_engine.sparkle_particles:
            sparkle_col = AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.92, 0.45, s["alpha"])
            sparkle_col.set()
            sparkle_path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
                AppKit.NSMakeRect(s["x"] - s["r"], s["y"] - s["r"], s["r"] * 2, s["r"] * 2)
            )
            sparkle_path.fill()

        # 3. Towing Cables
        self.hud_painter.draw_towing_cables(
            banner_x, banner_y, banner_w, banner_h, dyn_px, dyn_py, self.is_late, pitch_deg=pitch_deg, tick=self.tick
        )

        # 4. Card HUD
        self.hud_painter.draw_glass_banner_card(banner_x, banner_y, banner_w, banner_h, self.is_late, self.tick, self.reminder_stage)

        # 5. Provider Pill & Classroom Badge
        self.hud_painter.draw_provider_and_classroom_pills(banner_x, banner_y, banner_h, self.provider, self.classroom, accent, self.reminder_stage)

        # 6. Countdown Pill
        self.hud_painter.draw_countdown_pill(banner_x, banner_y, banner_w, banner_h, self._cached_countdown_text, self._cached_is_urgent)

        # 7. Close Button
        self.hud_painter.draw_close_button(banner_x, banner_y, banner_w, banner_h, self.pressed_button, self.hovered_button)

        # 8. Event Details
        self.hud_painter.draw_event_details(banner_x, banner_y, banner_h, self._cached_short_title, self._cached_detail_text, bw=banner_w)

        # 9. Action Buttons Bar
        rects = self._get_button_rects(banner_x, banner_y)
        self.hud_painter.draw_buttons_bar(
            banner_x,
            banner_y,
            palette,
            self.has_real_url,
            self.action_btn_text,
            self.has_maps_url,
            self.reminder_stage,
            rects,
            self.pressed_button,
            self.hovered_button
        )

        # 10. Vector Pilot Mascot with Dynamic Pitch Rotation
        # Centers rotation at dynamic airplane center (dyn_px, dyn_py)
        ctx = AppKit.NSGraphicsContext.currentContext()
        ctx.saveGraphicsState()
        transform = AppKit.NSAffineTransform.transform()
        transform.translateXBy_yBy_(dyn_px, dyn_py)
        transform.rotateByDegrees_(pitch_deg)
        transform.translateXBy_yBy_(-dyn_px, -dyn_py)
        transform.concat()

        self.renderer.draw_pilot(dyn_px, dyn_py, self.tick)
        ctx.restoreGraphicsState()

        # 11. Pilot Speech Bubble (Playful mascot hover quote when hovering plane)
        active_speech = self._cached_hover_speech_text if (self.hovered_button == "plane" and self._cached_hover_speech_text) else self._cached_speech_text
        self.hud_painter.draw_pilot_speech_bubble(
            dyn_px, dyn_py, banner_x + banner_w, active_speech, self.is_late, self.tick
        )

    def acceptsFirstResponder(self):
        return True

    def keyDown_(self, event):
        if event.keyCode() == 53:  # Escape key
            if self.controller:
                self.controller.dismiss()
        else:
            objc.super(QuakPitBannerView, self).keyDown_(event)

