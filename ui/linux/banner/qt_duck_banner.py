from __future__ import annotations
import sys
import os
import math
import random
import webbrowser
from datetime import datetime
from typing import Dict, Any, Optional

try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPointF, QUrl
    from PyQt6.QtGui import (
        QColor, QPainter, QBrush, QPen, QFont, QPainterPath,
        QLinearGradient, QRadialGradient, QFontMetrics, QCursor, QDesktopServices,
        QShortcut, QKeySequence, QKeyEvent
    )
except ImportError:
    pass

from core.services.config_service import config
from core.domain.models import format_duration
from core.domain.classifier import EventClassifier
from ui.linux.theme import Theme
from ui.common.banner_speech import build_pilot_speech_text, build_pilot_hover_speech_text
from ui.common.banner_particles import (
    BannerParticleEngine,
    compute_airplane_flight_dynamics,
    compute_towing_cable_hooks
)
from ui.common.banner_formatting import compute_countdown_text, MODE_ICONS
from core.services.sound_service import play_chime
from core.services.language_service import t
from .renderers import get_pilot_renderer


class QtDuckBannerWindow(QWidget):
    """
    High-Performance Animated Flying Duck Notification Banner for Ubuntu Linux.
    100% visual and behavioral parity with the macOS QuakPit banner:
    - Frosted glass HUD with pilot-specific tints & glowing borders
    - Dual curved towing cables (red glowing during late mode)
    - Dynamic particle systems: Turbo Afterburner flames, engine exhaust smoke, and sparkles
    - Provider pill, classroom badge, live dynamic countdown pill
    - Full action button bar (Pilot-themed gradient Action, "📍 I'm Here", "💤 5m", "⏭️ Skip")
    - Animated context-aware pilot speech bubble
    """

    CARD_W = 535.0
    CARD_H = 132.0
    CARD_R = 18.0
    CARD_X = 10.0
    CARD_Y = 55.0

    WIN_W = 1000
    WIN_H = 195

    PLANE_CX = CARD_X + 630.0
    PLANE_CY = CARD_Y + 54.0

    def __init__(self, event_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.event_data = event_data

        self.title = str(event_data.get("title") or "Event Reminder")
        self.provider = str(event_data.get("provider") or "Event")
        extracted_meeting_url = EventClassifier.extract_meeting_url(
            f"{event_data.get('location', '')} {event_data.get('description', '')}"
        )
        self.action_url = event_data.get("action_url") or event_data.get("meeting_url") or event_data.get("maps_url")
        if extracted_meeting_url and (
            not self.action_url or self.action_url == "https://calendar.apple.com"
        ):
            self.action_url = extracted_meeting_url
        def _norm_dt(dt):
            if isinstance(dt, datetime):
                return dt.astimezone() if dt.tzinfo else dt.astimezone()
            if isinstance(dt, str):
                try:
                    parsed = datetime.fromisoformat(dt)
                    return parsed.astimezone() if parsed.tzinfo else parsed.astimezone()
                except Exception:
                    pass
            return None

        self.start_time = _norm_dt(event_data.get("start_time"))
        self.end_time = _norm_dt(event_data.get("end_time"))
        self.location = str(event_data.get("location") or "")
        self.pilot_type = str(event_data.get("pilot_type") or "duck")
        self.is_travel = bool(event_data.get("is_travel", False))

        # Classroom & Teacher Metadata
        self.classroom = event_data.get("classroom")
        self.teacher = event_data.get("teacher")

        # Multi-modal Travel & ETA metadata
        self.travel_time_minutes = event_data.get("travel_time_minutes")
        self.travel_distance_km = event_data.get("travel_distance_km")
        self.transport_mode = event_data.get("transport_mode", config.get("transport_mode", "transit"))
        self.departure_time = _norm_dt(event_data.get("departure_time"))
        self.origin_address = event_data.get("origin_address")
        self.eta_text = event_data.get("eta_text")

        # Reminder stage metadata (e.g. 20, 10, 5, 2, 0)
        self.reminder_stage = event_data.get("reminder_stage")

        # Determine Late Status
        self.is_late = self._compute_is_late()

        # URL characteristics
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

        if not event_data.get("action_btn_text") and self.has_maps_url:
            self.action_btn_text = t("agenda_maps_button", default="🗺️ Directions")
        else:
            self.action_btn_text = str(event_data.get("action_btn_text") or "🚀 JOIN NOW")

        # Modular animal & outfit customization
        self.category = str(event_data.get("category") or "")
        self.is_bill = (self.category == "bill")
        self.animal = event_data.get("animal")
        self.outfit = event_data.get("outfit")

        # Instantiate pilot renderer
        self.renderer = get_pilot_renderer(
            self.pilot_type,
            animal=self.animal,
            outfit=self.outfit,
            accessories=event_data.get("accessories"),
        )
        self.renderer.status = "urgent" if self.is_late else "upcoming" if self.reminder_stage and self.reminder_stage > 0 else "normal"

        # Flight dynamics & geometry (Boost speed by 40% when late)
        base_speed = float(config.get("flight_speed", 3.2))
        self.speed = base_speed * 1.40 if self.is_late else base_speed
        self.tick = 0
        self.is_paused = False

        # Particle Engine
        self.particle_engine = BannerParticleEngine()

        # Hover & Click Interaction State
        self.hovered_button = None
        self.pressed_button = None
        self._cursor_override_active = False

        # Determine slim card layout for buttonless advance flyby
        self.is_slim = bool(
            self.reminder_stage is not None and
            self.reminder_stage > 0 and
            not self.has_real_url and
            not self.has_maps_url
        )
        self.card_h = 96.0 if self.is_slim else self.CARD_H
        self.plane_cy = self.CARD_Y + (42.0 if self.is_slim else 54.0)
        self.plane_cx = self.CARD_X + 630.0

        # Precompute Theme Palette & Cached Text
        self._palette = self._build_theme_palette()
        self._init_cached_resources()

        # Dynamic window width to accommodate extra-long quotes
        f = QFont("Inter, Arial", 8, QFont.Weight.ExtraBold)
        fm = QFontMetrics(f)
        bubble_w = (fm.horizontalAdvance(self._cached_speech_text) + 24.0) if self._cached_speech_text else 0.0
        hover_bubble_w = (fm.horizontalAdvance(self._cached_hover_speech_text) + 24.0) if self._cached_hover_speech_text else 0.0
        max_bubble_w = max(bubble_w, hover_bubble_w)
        needed_w = int(max(self.WIN_W, (self.CARD_X + self.CARD_W + 10.0) + max_bubble_w + 30.0))

        # Screen setup
        screen = QApplication.primaryScreen()
        geo = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        self.screen_w = geo.width()
        self.screen_x = geo.x()
        self.screen_y = geo.y()
        self._wayland_mode = (
            sys.platform.startswith("linux")
            and os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland"
            and os.environ.get("QT_QPA_PLATFORM", "").lower() not in ("xcb", "wayland-xcomposite-egl")
        )
        self._render_offset_x = 0.0
        self._render_offset_y = 0.0

        self.win_w = needed_w
        self.win_h = self.WIN_H
        self.setFixedSize(max(self.win_w, self.screen_w) if self._wayland_mode else self.win_w, self.win_h)

        self.win_x = float(self.screen_x - self.win_w - 20)
        self.base_y = float(self.screen_y + 24)
        self.is_quiet_reminder = bool(event_data.get("is_quiet_reminder", False))

        flags = (
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        if sys.platform.startswith("linux") and not self._wayland_mode:
            flags |= Qt.WindowType.X11BypassWindowManagerHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self.move(int(self.screen_x if self._wayland_mode else self.win_x), int(self.base_y))

        # Escape key shortcut to instantly dismiss banner
        self._esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._esc_shortcut.activated.connect(self._dismiss)

        if not self.is_quiet_reminder and not self.event_data.get("is_test_banner") and "unittest" not in sys.modules:
            play_chime(event_dict=self.event_data)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._step)
        self._timer.start(16)

    def _compute_is_late(self) -> bool:
        """Determines if the event is already past departure time or past start time."""
        if isinstance(self.event_data, dict):
            if self.event_data.get("is_late") is not None:
                return bool(self.event_data["is_late"])
            if self.event_data.get("is_test_banner") or self.event_data.get("is_test"):
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
        """Precomputes static details, pilot speech quotes, and countdown text."""
        # Static truncated title (sanitizing newlines/tabs)
        clean_title = " ".join(str(self.title or "").split())
        max_chars = 34
        self._cached_short_title = clean_title if len(clean_title) <= max_chars else clean_title[:max_chars - 3] + "..."

        # Static details string
        detail_text = ""
        if self.start_time:
            st = self.start_time.astimezone() if hasattr(self.start_time, "astimezone") else self.start_time
            s_time = st.strftime("%H:%M")
            if self.end_time:
                et = self.end_time.astimezone() if hasattr(self.end_time, "astimezone") else self.end_time
                e_time = et.strftime("%H:%M")
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
        elif self.action_url and ("meet.google.com" in self.action_url or "zoom" in self.action_url or "teams" in self.action_url or "app.serenis.it" in self.action_url):
            detail_text += "  •  🌐 Online Meeting"

        if self.teacher:
            clean_tch = " ".join(str(self.teacher).split())
            detail_text += f" ({clean_tch})"

        self._cached_detail_text = detail_text

        # Precompute pilot speech bubble text & countdown strings from common modules
        self._cached_speech_text = build_pilot_speech_text(
            self.event_data,
            animal=self.animal,
            outfit=self.outfit,
            pilot_type=self.pilot_type,
            is_late=self.is_late,
            classroom=self.classroom,
            title=self.title,
            provider=self.provider,
            reminder_stage=self.reminder_stage
        )
        self._cached_countdown_text, self._cached_is_urgent = compute_countdown_text(
            self.event_data,
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
        self._cached_hover_speech_text = build_pilot_hover_speech_text(
            animal=self.animal or self.pilot_type
        )

    @property
    def flame_particles(self):
        return self.particle_engine.flame_particles

    @property
    def smoke_particles(self):
        return self.particle_engine.smoke_particles

    @property
    def sparkle_particles(self):
        return self.particle_engine.sparkle_particles

    def _update_countdown_text(self):
        self._cached_countdown_text, self._cached_is_urgent = compute_countdown_text(
            self.event_data,
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

    def _build_theme_palette(self) -> Dict[str, Any]:
        """Returns exact theme palette matching macOS."""
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
        elif self.pilot_type == "driver":
            accent = Theme.YELLOW
            accent_bright = Theme.PEACH
            btn_gradient_top = Theme.YELLOW
            btn_gradient_bot = Theme.PEACH
        elif self.pilot_type == "zen_duck":
            accent = Theme.TEAL
            accent_bright = Theme.SKY
            btn_gradient_top = Theme.TEAL
            btn_gradient_bot = Theme.SKY
        elif self.pilot_type == "gym":
            accent = Theme.RED
            accent_bright = Theme.MAROON
            btn_gradient_top = Theme.RED
            btn_gradient_bot = Theme.MAROON
        elif self.pilot_type == "platypus":
            accent = Theme.TEAL
            accent_bright = Theme.SAPPHIRE
            btn_gradient_top = Theme.TEAL
            btn_gradient_bot = Theme.SAPPHIRE
        elif self.pilot_type == "squirrel":
            accent = Theme.MAROON
            accent_bright = Theme.PEACH
            btn_gradient_top = Theme.MAROON
            btn_gradient_bot = Theme.PEACH
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

    def _get_button_rects(self, bx: float, by: float) -> Dict[str, QRectF]:
        """Returns accurate bounding rects for all interactive elements."""
        btn_close_rect = QRectF(bx + self.CARD_W - 36.0, by + 10.0, 24.0, 24.0)
        btn_close_hit_rect = QRectF(bx + self.CARD_W - 44.0, by + 2.0, 40.0, 40.0)

        # 4 Button Bar: [Action] [I'm Here] [Snooze 5m] [Snooze 15m / Skip]
        btn_h = 32.0
        btn_y = by + self.card_h - btn_h - 14.0
        is_stage_zero = (self.reminder_stage == 0)

        if self.is_bill:
            # 2 Buttons for Bill: [Action / Pay (260px)] [✅ Mark Paid (227px)]
            btn_action_rect = QRectF(bx + 18.0, btn_y, 260.0, btn_h)
            btn_arrived_rect = QRectF(bx + 290.0, btn_y, 227.0, btn_h)
            btn_snooze1_rect = QRectF(0, 0, 0, 0)
            btn_snooze2_rect = QRectF(0, 0, 0, 0)
        elif is_stage_zero:
            if self.has_maps_url:
                if self.has_real_url:
                    # 2 Buttons: [Action / Directions (260px)] [📍 I'm Here (227px)]
                    btn_action_rect = QRectF(bx + 18.0, btn_y, 260.0, btn_h)
                    btn_arrived_rect = QRectF(bx + 290.0, btn_y, 227.0, btn_h)
                    btn_snooze1_rect = QRectF(0, 0, 0, 0)
                else:
                    # 1 Button: [📍 I'm Here (200px)]
                    btn_action_rect = QRectF(0, 0, 0, 0)
                    btn_arrived_rect = QRectF(bx + 18.0, btn_y, 200.0, btn_h)
                    btn_snooze1_rect = QRectF(0, 0, 0, 0)
                btn_snooze2_rect = QRectF(0, 0, 0, 0)
            else:
                btn_arrived_rect = QRectF(0, 0, 0, 0)
                btn_snooze1_rect = QRectF(0, 0, 0, 0)
                btn_snooze2_rect = QRectF(0, 0, 0, 0)
                if self.has_real_url:
                    # Online Meeting (Option A): Single prominent [🚀 JOIN NOW] action button
                    btn_action_rect = QRectF(bx + 18.0, btn_y, 220.0, btn_h)
                else:
                    # Plain Event / Note: Single [✅ Got it] confirmation button
                    btn_action_rect = QRectF(bx + 18.0, btn_y, 220.0, btn_h)
        else:
            # Advance Flyby Reminder (Option A - Pure Ambient):
            # - No Snooze or Skip buttons (ambient flyby auto-snoozes via reminder stages)
            # - If meeting has real URL and maps: [Action (260px)] [📍 I'm Here (227px)]
            # - If meeting has only real URL: [Action (220px)]
            # - If travel/maps only: [📍 I'm Here (200px)]
            # - General event: no bottom buttons at all
            btn_snooze1_rect = QRectF(0, 0, 0, 0)
            btn_snooze2_rect = QRectF(0, 0, 0, 0)

            if self.has_real_url and self.has_maps_url:
                btn_action_rect = QRectF(bx + 18.0, btn_y, 260.0, btn_h)
                btn_arrived_rect = QRectF(bx + 290.0, btn_y, 227.0, btn_h)
            elif self.has_real_url:
                btn_action_rect = QRectF(bx + 18.0, btn_y, 220.0, btn_h)
                btn_arrived_rect = QRectF(0, 0, 0, 0)
            elif self.has_maps_url:
                btn_action_rect = QRectF(0, 0, 0, 0)
                btn_arrived_rect = QRectF(bx + 18.0, btn_y, 200.0, btn_h)
            else:
                btn_action_rect = QRectF(0, 0, 0, 0)
                btn_arrived_rect = QRectF(0, 0, 0, 0)

        return {
            "close": btn_close_rect,
            "close_hit": btn_close_hit_rect,
            "action": btn_action_rect,
            "arrived": btn_arrived_rect,
            "snooze1": btn_snooze1_rect,
            "snooze2": btn_snooze2_rect,
            "card": QRectF(bx, by, self.CARD_W, self.card_h)
        }

    def _get_airplane_dynamics(self) -> tuple[float, float, float]:
        """Returns dynamic (px, py, pitch_deg) for airplane flight dynamics."""
        float_x, float_y, pitch_deg = compute_airplane_flight_dynamics(self.tick, self.is_paused)
        return self.plane_cx + float_x, self.plane_cy + float_y, pitch_deg

    # ── Animation Step ─────────────────────────────────────────────────────────

    def _step(self):
        self.tick += 1

        if not self.is_paused:
            self.win_x += self.speed
            if self.win_x > self.screen_x + self.screen_w + 20:
                if self.reminder_stage is not None and self.reminder_stage > 0:
                    self._dismiss()
                    return
                else:
                    self.win_x = float(self.screen_x - self.win_w - 20)

        # Smooth vertical sine wave flight bobbing
        y_wave = self.base_y + math.sin(self.tick * 0.038) * 8.0
        if self._wayland_mode:
            self._render_offset_x = self.win_x - self.screen_x
            self._render_offset_y = y_wave - self.base_y
        else:
            self.move(int(self.win_x), int(y_wave))

        # Check hover even if mouse is stationary
        try:
            cursor_pos = QPointF(self.mapFromGlobal(QCursor.pos()))
            self._update_hover_state(cursor_pos)
        except Exception:
            pass

        dyn_px, dyn_py, _ = self._get_airplane_dynamics()

        # Update countdown once every 30 frames (~0.5s) to save CPU
        if self.tick % 30 == 0:
            self._update_countdown_text()

        self.particle_engine.emit_and_update(
            dyn_px, dyn_py, self.tick, self.is_late, self.is_paused, self.pilot_type
        )

        self.update()

    # ── Mouse & Keyboard Interaction ───────────────────────────────────────────

    def _update_hover_state(self, pos):
        if self._wayland_mode:
            pos = QPointF(pos.x() - self._render_offset_x, pos.y() - self._render_offset_y)
        rects = self._get_button_rects(self.CARD_X, self.CARD_Y)
        dyn_px, dyn_py, _ = self._get_airplane_dynamics()
        plane_rect = QRectF(dyn_px - 65.0, dyn_py - 30.0, 115.0, 60.0)
        old_hover = self.hovered_button

        if rects["close_hit"].contains(pos):
            self.hovered_button = "close"
            self.is_paused = True
        elif rects["action"].contains(pos):
            self.hovered_button = "action"
            self.is_paused = True
        elif rects["arrived"].contains(pos):
            self.hovered_button = "arrived"
            self.is_paused = True
        elif rects["snooze1"].contains(pos):
            self.hovered_button = "snooze1"
            self.is_paused = True
        elif rects["snooze2"].contains(pos):
            self.hovered_button = "snooze2"
            self.is_paused = True
        elif rects["card"].contains(pos):
            self.hovered_button = "card"
            self.is_paused = True
        elif plane_rect.contains(pos):
            self.hovered_button = "plane"
            self.is_paused = True
        else:
            self.hovered_button = None
            self.is_paused = False

        interactive = {"close", "action", "arrived", "snooze1", "snooze2", "plane"}
        cursor_shape = (
            Qt.CursorShape.PointingHandCursor
            if self.hovered_button in interactive
            else Qt.CursorShape.ArrowCursor
        )
        self._set_cursor_shape(cursor_shape)

        if old_hover != self.hovered_button:
            self.update()

    def _set_cursor_shape(self, cursor_shape):
        if cursor_shape == Qt.CursorShape.PointingHandCursor:
            cursor = QCursor(cursor_shape)
            if self._cursor_override_active:
                QApplication.changeOverrideCursor(cursor)
            else:
                QApplication.setOverrideCursor(cursor)
                self._cursor_override_active = True
            return

        if self._cursor_override_active:
            QApplication.restoreOverrideCursor()
            self._cursor_override_active = False
        self.setCursor(cursor_shape)

    def keyPressEvent(self, ev: QKeyEvent):
        if ev.key() == Qt.Key.Key_Escape:
            self._dismiss()
        else:
            super().keyPressEvent(ev)

    def mouseMoveEvent(self, ev):
        self._update_hover_state(ev.position())

    def mousePressEvent(self, ev):
        if ev.button() != Qt.MouseButton.LeftButton:
            return
        pos = ev.position()
        if self._wayland_mode:
            pos = QPointF(pos.x() - self._render_offset_x, pos.y() - self._render_offset_y)
        rects = self._get_button_rects(self.CARD_X, self.CARD_Y)
        dyn_px, dyn_py, _ = self._get_airplane_dynamics()
        plane_rect = QRectF(dyn_px - 65.0, dyn_py - 30.0, 115.0, 60.0)

        if rects["close_hit"].contains(pos):
            self.pressed_button = "close"
        elif rects["action"].contains(pos):
            self.pressed_button = "action"
        elif rects["arrived"].contains(pos):
            self.pressed_button = "arrived"
        elif rects["snooze1"].contains(pos):
            self.pressed_button = "snooze1"
        elif rects["snooze2"].contains(pos):
            self.pressed_button = "snooze2"
        elif rects["card"].contains(pos):
            self.pressed_button = "card"
        elif plane_rect.contains(pos):
            self.pressed_button = "plane"
        else:
            self.pressed_button = None

        self.update()

    def mouseReleaseEvent(self, ev):
        pos = ev.position()
        rects = self._get_button_rects(self.CARD_X, self.CARD_Y)

        clicked = self.pressed_button
        self.pressed_button = None
        self.update()

        meeting_id = str(self.event_data.get("id") or self.event_data.get("uid") or "")

        dyn_px, dyn_py, _ = self._get_airplane_dynamics()
        plane_rect = QRectF(dyn_px - 65.0, dyn_py - 30.0, 115.0, 60.0)

        if clicked == "close" and rects["close_hit"].contains(pos):
            try:
                from core.services.state_store import banner_history_store
                banner_history_store.record_action(meeting_id, "dismissed")
            except Exception:
                pass
            self._dismiss()
        elif clicked == "action" and rects["action"].contains(pos):
            try:
                from core.services.state_store import banner_history_store
                banner_history_store.record_action(meeting_id, "action_clicked")
            except Exception:
                pass
            if self.has_real_url:
                QDesktopServices.openUrl(QUrl(self.action_url))
            self._dismiss()
        elif clicked == "arrived" and rects["arrived"].contains(pos):
            if self.is_bill:
                try:
                    from core.services.reminder_engine import reminder_engine
                    reminder_engine.mark_bill_paid(meeting_id)
                except Exception:
                    pass
                try:
                    from core.services.state_store import banner_history_store
                    banner_history_store.record_action(meeting_id, "bill_paid")
                except Exception:
                    pass
                if meeting_id:
                    try:
                        from core.services.event_bus import event_bus
                        event_bus.publish("MARK_PAID", meeting_id=meeting_id)
                    except Exception:
                        pass
            else:
                try:
                    from core.services.state_store import banner_history_store
                    banner_history_store.record_action(meeting_id, "arrived")
                except Exception:
                    pass
                if meeting_id:
                    try:
                        from core.services.event_bus import event_bus
                        event_bus.publish("MARK_ARRIVED", meeting_id=meeting_id)
                    except Exception:
                        pass
            self._dismiss()
        elif clicked == "snooze1" and rects["snooze1"].contains(pos):
            try:
                from core.services.state_store import banner_history_store
                banner_history_store.record_action(meeting_id, "snoozed" if self.reminder_stage != 0 else "arrived")
            except Exception:
                pass
            if self.reminder_stage == 0:
                if meeting_id:
                    try:
                        from core.services.event_bus import event_bus
                        event_bus.publish("MARK_ARRIVED", meeting_id=meeting_id)
                    except Exception:
                        pass
            else:
                try:
                    from core.services.event_bus import event_bus
                    event_bus.publish("SNOOZE_REMINDER", seconds=300)
                except Exception:
                    pass
            self._dismiss()
        elif clicked == "snooze2" and rects["snooze2"].contains(pos):
            try:
                from core.services.state_store import banner_history_store
                banner_history_store.record_action(meeting_id, "arrived")
            except Exception:
                pass
            if meeting_id:
                try:
                    from core.services.event_bus import event_bus
                    event_bus.publish("MARK_ARRIVED", meeting_id=meeting_id)
                except Exception:
                    pass
            self._dismiss()
        elif (clicked in ["card", "plane"]) and (rects["card"].contains(pos) or plane_rect.contains(pos)):
            try:
                from core.services.state_store import banner_history_store
                banner_history_store.record_action(meeting_id, "card_clicked")
            except Exception:
                pass
            if self.has_real_url:
                QDesktopServices.openUrl(QUrl(self.action_url))
            self._dismiss()

    def leaveEvent(self, ev):
        self.is_paused = False
        self.pressed_button = None
        self.hovered_button = None
        self._set_cursor_shape(Qt.CursorShape.ArrowCursor)
        self.update()

    # ── Paint Event ────────────────────────────────────────────────────────────

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        if self._wayland_mode:
            p.translate(self._render_offset_x, self._render_offset_y)

        palette = self._palette
        accent = palette["accent"]

        bx = self.CARD_X
        by = self.CARD_Y
        bw = self.CARD_W
        bh = self.card_h
        dyn_px, dyn_py, pitch_deg = self._get_airplane_dynamics()

        # 1. Turbo Flame Particles (Afterburners)
        for f in self.flame_particles:
            stage = f["color_stage"]
            alpha_val = max(0, min(255, int(f["alpha"] * 255)))
            if stage < 1.0:
                f_col = QColor(255, 230, 77, alpha_val)
            elif stage < 2.0:
                f_col = QColor(255, 133, 38, alpha_val)
            else:
                f_col = QColor(242, 56, 46, int(alpha_val * 0.8))

            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(f_col)
            p.drawEllipse(QRectF(f["x"] - f["r"], f["y"] - f["r"], f["r"] * 2, f["r"] * 2))

        # 2. Standard Smoke & Sparkles
        for sm in self.smoke_particles:
            smoke_alpha = max(0, min(255, int(sm["alpha"] * 128)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(217, 224, 250, smoke_alpha))
            p.drawEllipse(QRectF(sm["x"] - sm["r"], sm["y"] - sm["r"], sm["r"] * 2, sm["r"] * 2))

        for sp in self.sparkle_particles:
            sp_alpha = max(0, min(255, int(sp["alpha"] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 235, 115, sp_alpha))
            p.drawEllipse(QRectF(sp["x"] - sp["r"], sp["y"] - sp["r"], sp["r"] * 2, sp["r"] * 2))

        # 3. Towing Cables (Curved Bezier Cables)
        self._draw_towing_cables(p, bx, by, bw, bh, dyn_px, dyn_py, pitch_deg)

        # 4. Frosted Glass Banner Card
        self._draw_glass_banner_card(p, bx, by, bw, bh, palette)

        # 5. Provider Pill & Classroom Badge
        self._draw_provider_pill(p, bx, by, bh, accent)

        # 6. Countdown Pill
        self._draw_countdown_pill(p, bx, by, bw, bh, accent)

        # 7. Close Button
        self._draw_close_button(p, bx, by, bw, bh)

        # 8. Event Title & Details
        self._draw_event_details(p, bx, by, bw, bh)

        # 9. Action Buttons Bar ([Action] [📍 I'm Here] [💤 Snooze])
        self._draw_buttons_bar(p, bx, by, palette)

        # 10. Draw Pilot Vehicle & Character with Dynamic Pitch Rotation
        # Centers rotation at dynamic airplane center (dyn_px, dyn_py)
        p.save()
        p.translate(dyn_px, dyn_py)
        p.rotate(pitch_deg)
        p.translate(-dyn_px, -dyn_py)
        p.translate(0.0, 2.0 * dyn_py)
        p.scale(1.0, -1.0)
        p.setPen(Qt.PenStyle.NoPen)
        self.renderer.draw_pilot(p, dyn_px, dyn_py, self.tick)
        p.restore()

        # 11. Animated Pilot Speech Bubble (Above plane, kept strictly clear of card HUD & close button)
        self._draw_pilot_speech_bubble(p, dyn_px, dyn_py, bx + bw)

        p.end()

    # ── Sub-drawing Helpers ────────────────────────────────────────────────────

    def _draw_towing_cables(self, p: QPainter, bx: float, by: float, bw: float, bh: float, px: float, py: float, pitch_deg: float):
        cable_col = QColor(255, 102, 89, 166) if self.is_late else QColor(217, 217, 217, 107)
        pen = QPen(cable_col, 1.5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        (hook_top_x, hook_top_y), (hook_bot_x, hook_bot_y) = compute_towing_cable_hooks(px, py, pitch_deg, is_qt_coords=True)
        dx = hook_top_x - (bx + bw)
        vibe = (math.sin(self.tick * 0.55) * 1.8) if self.is_late else (math.sin(self.tick * 0.38) * 1.2)

        # Top Cable
        top_cable = QPainterPath()
        top_cable.moveTo(bx + bw, by + 24.0)
        top_cable.cubicTo(
            bx + bw + dx * 0.45, by + 16.0 + vibe,
            hook_top_x - 16.0, hook_top_y - 2.0 - vibe,
            hook_top_x, hook_top_y
        )
        p.drawPath(top_cable)

        # Bottom Cable
        bot_cable = QPainterPath()
        bot_cable.moveTo(bx + bw, by + bh - 24.0)
        bot_cable.cubicTo(
            bx + bw + dx * 0.45, by + bh - 16.0 - vibe,
            hook_bot_x - 16.0, hook_bot_y + 2.0 + vibe,
            hook_bot_x, hook_bot_y
        )
        p.drawPath(bot_cable)

    def _draw_glass_banner_card(self, p: QPainter, bx: float, by: float, bw: float, bh: float, palette: Dict[str, Any]):
        card_rect = QRectF(bx, by, bw, bh)
        p.setBrush(palette["card_tint"])

        if self.is_late:
            pulse = math.sin(self.tick * 0.15) * 0.3 + 0.7
            border_col = QColor(255, 77, 77, max(0, min(255, int(pulse * 255))))
            p.setPen(QPen(border_col, 1.8))
        elif self.reminder_stage is not None and self.reminder_stage > 0:
            border_col = QColor(180, 190, 254, 110)
            p.setPen(QPen(border_col, 1.2))
        else:
            border_col = QColor(255, 255, 255, 41)
            p.setPen(QPen(border_col, 1.0))

        p.drawRoundedRect(card_rect, self.CARD_R, self.CARD_R)

    def _draw_provider_pill(self, p: QPainter, bx: float, by: float, bh: float, accent: QColor):
        p.setFont(QFont("Inter, Arial", 9, QFont.Weight.ExtraBold))
        fm = p.fontMetrics()
        prov_str = self.provider.upper()
        text_w = fm.horizontalAdvance(prov_str)
        pill_w = text_w + 16.0
        pill_h = 20.0

        pill_x = bx + 18.0
        pill_y = by + 12.0
        pill_rect = QRectF(pill_x, pill_y, pill_w, pill_h)

        # Pill background
        bg_c = QColor(accent.red(), accent.green(), accent.blue(), 36)
        border_c = QColor(accent.red(), accent.green(), accent.blue(), 97)
        p.setBrush(bg_c)
        p.setPen(QPen(border_c, 1.0))
        p.drawRoundedRect(pill_rect, 10.0, 10.0)

        # Pill text
        p.setPen(accent)
        p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, prov_str)

        next_x = pill_x + pill_w + 8.0

        # Classroom Badge (if present)
        if self.classroom:
            c_str = f"🏫 {self.classroom}"
            c_text_w = fm.horizontalAdvance(c_str)
            c_pill_w = c_text_w + 14.0
            c_pill_rect = QRectF(next_x, pill_y, c_pill_w, pill_h)

            p.setBrush(QColor(89, 51, 140, 166))
            p.setPen(QPen(QColor(191, 140, 242, 166), 1.0))
            p.drawRoundedRect(c_pill_rect, 10.0, 10.0)

            p.setPen(QColor(224, 184, 255))
            p.drawText(c_pill_rect, Qt.AlignmentFlag.AlignCenter, c_str)
            next_x += c_pill_w + 8.0

        # Flyby Badge (for advance reminders)
        if self.reminder_stage is not None and self.reminder_stage > 0:
            fly_str = t("banner_flyby_pill")
            fly_text_w = fm.horizontalAdvance(fly_str)
            fly_pill_w = fly_text_w + 14.0
            fly_pill_rect = QRectF(next_x, pill_y, fly_pill_w, pill_h)

            p.setBrush(QColor(180, 190, 254, 45))
            p.setPen(QPen(QColor(180, 190, 254, 120), 1.0))
            p.drawRoundedRect(fly_pill_rect, 10.0, 10.0)

            p.setPen(QColor(180, 190, 254))
            p.drawText(fly_pill_rect, Qt.AlignmentFlag.AlignCenter, fly_str)

    def _draw_countdown_pill(self, p: QPainter, bx: float, by: float, bw: float, bh: float, accent: QColor):
        countdown_text = self._cached_countdown_text
        is_urgent = self._cached_is_urgent

        p.setFont(QFont("Inter, Arial", 9, QFont.Weight.Bold))
        fm = p.fontMetrics()
        text_w = fm.horizontalAdvance(countdown_text)
        pill_w = text_w + 18.0
        pill_h = 20.0

        pill_x = bx + bw - 44.0 - pill_w
        pill_y = by + 12.0
        pill_rect = QRectF(pill_x, pill_y, pill_w, pill_h)

        if is_urgent:
            bg_col = QColor(66, 20, 20, 224)
            border_col = QColor(255, 89, 89, 140)
            text_col = QColor(255, 89, 89)
        else:
            bg_col = QColor(38, 41, 61, 217)
            border_col = QColor(245, 224, 166, 140)
            text_col = QColor(245, 224, 166)

        p.setBrush(bg_col)
        p.setPen(QPen(border_col, 1.0))
        p.drawRoundedRect(pill_rect, 10.0, 10.0)

        p.setPen(text_col)
        p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, countdown_text)

    def _draw_close_button(self, p: QPainter, bx: float, by: float, bw: float, bh: float):
        is_pressed = (self.pressed_button == "close")
        is_hovered = (self.hovered_button == "close")

        btn_rect = QRectF(bx + bw - 36.0, by + 10.0, 24.0, 24.0)

        if is_pressed:
            fill_col = QColor(107, 112, 148)
        elif is_hovered:
            fill_col = QColor(77, 82, 112)
        else:
            fill_col = QColor(46, 51, 71, 217)

        p.setBrush(fill_col)
        p.setPen(QPen(QColor(128, 140, 179, 166), 1.0))
        p.drawEllipse(btn_rect)

        p.setPen(Qt.GlobalColor.white)
        p.setFont(QFont("Inter, Arial", 10, QFont.Weight.Bold))
        p.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, "✕")

    def _draw_event_details(self, p: QPainter, bx: float, by: float, bw: float, bh: float):
        clean_title = " ".join(str(self._cached_short_title or "").split())
        clean_detail = " ".join(str(self._cached_detail_text or "").split())

        # Title
        p.setPen(Qt.GlobalColor.white)
        tf = QFont("Inter, Arial", 12, QFont.Weight.Bold)
        p.setFont(tf)
        title_rect = QRectF(bx + 18.0, by + 36.0, bw - 36.0, 20.0)
        p.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine, clean_title)

        # Subtitle details
        p.setPen(QColor(184, 194, 224))
        sf = QFont("Inter, Arial", 10)
        p.setFont(sf)
        sub_rect = QRectF(bx + 18.0, by + 58.0, bw - 36.0, 18.0)
        p.drawText(sub_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextSingleLine, clean_detail)

    def _draw_buttons_bar(self, p: QPainter, bx: float, by: float, palette: Dict[str, Any]):
        rects = self._get_button_rects(bx, by)

        # 1. Main Action Button
        btn_act_rect = rects["action"]
        if btn_act_rect.width() > 0:
            is_pressed_act = (self.pressed_button == "action")
            is_hovered_act = (self.hovered_button == "action")
            is_stage_zero = (self.reminder_stage == 0)

            if not self.has_real_url:
                top_c = QColor(26, 153, 179)
                bot_c = QColor(0, 102, 128)
                btn_text = t("banner_got_it")
                text_col = Qt.GlobalColor.white
                border_pen = Qt.PenStyle.NoPen
            else:
                if self.has_maps_url:
                    top_c = Theme.SKY
                    bot_c = Theme.SAPPHIRE
                else:
                    top_c = palette["btn_gradient_top"]
                    bot_c = palette["btn_gradient_bot"]
                btn_text = self.action_btn_text
                text_col = Theme.CRUST
                border_pen = Qt.PenStyle.NoPen

            g = QLinearGradient(btn_act_rect.topLeft(), btn_act_rect.bottomLeft())
            if is_pressed_act:
                g.setColorAt(0, bot_c)
                g.setColorAt(1, top_c)
            elif is_hovered_act:
                if not self.has_real_url:
                    hover_color = QColor(51, 204, 230)
                elif self.has_maps_url:
                    hover_color = Theme.TEAL
                else:
                    hover_color = palette["accent_bright"]
                g.setColorAt(0, hover_color)
                g.setColorAt(1, bot_c)
            else:
                g.setColorAt(0, top_c)
                g.setColorAt(1, bot_c)

            p.setBrush(g)
            p.setPen(border_pen)
            p.drawRoundedRect(btn_act_rect, 9.0, 9.0)

            p.setPen(text_col)
            p.setFont(QFont("Inter, Arial", 10, QFont.Weight.ExtraBold))
            p.drawText(btn_act_rect, Qt.AlignmentFlag.AlignCenter, btn_text)

        # 2. "📍 I'm Here" or "✅ Mark Paid" Arrival/Paid Dismissal Button
        if (self.has_maps_url or self.is_bill) and rects["arrived"].width() > 0:
            is_pressed_arr = (self.pressed_button == "arrived")
            is_hovered_arr = (self.hovered_button == "arrived")
            btn_arr_rect = rects["arrived"]

            if is_pressed_arr:
                arr_fill = QColor(38, 115, 71, 242)
            elif is_hovered_arr:
                arr_fill = QColor(31, 97, 56, 230)
            else:
                arr_fill = QColor(20, 64, 41, 217)

            p.setBrush(arr_fill)
            p.setPen(QPen(QColor(77, 217, 140, 115), 1.0))
            p.drawRoundedRect(btn_arr_rect, 9.0, 9.0)

            arr_text = t("banner_mark_paid", default="✅ Mark Paid") if self.is_bill else t("banner_im_here", default="📍 I'm Here")
            p.setPen(QColor(77, 217, 140))
            p.setFont(QFont("Inter, Arial", 9, QFont.Weight.Bold))
            p.drawText(btn_arr_rect, Qt.AlignmentFlag.AlignCenter, arr_text)

        # 3. Snooze / Acknowledge Buttons
        is_stage_zero = (self.reminder_stage == 0)

        def _draw_snooze_btn(btn_key: str, rect: QRectF, text_str: str):
            if rect.width() == 0:
                return
            is_pressed = (self.pressed_button == btn_key)
            is_hovered = (self.hovered_button == btn_key)

            if is_stage_zero:
                # "✅ Got it" blue glass styling
                if is_pressed:
                    fill = QColor(46, 102, 166, 242)
                elif is_hovered:
                    fill = QColor(38, 122, 204, 230)
                else:
                    fill = QColor(26, 77, 140, 217)
                border = QColor(77, 166, 255, 128)
                txt_col = Qt.GlobalColor.white
            else:
                # "💤 Snooze" slate glass styling
                if is_pressed:
                    fill = QColor(77, 82, 112, 242)
                elif is_hovered:
                    fill = QColor(56, 64, 92, 230)
                else:
                    fill = QColor(38, 43, 64, 217)
                border = QColor(255, 255, 255, 41)
                txt_col = QColor(184, 194, 224)

            p.setBrush(fill)
            p.setPen(QPen(border, 1.0))
            p.drawRoundedRect(rect, 9.0, 9.0)

            p.setPen(txt_col)
            p.setFont(QFont("Inter, Arial", 9, QFont.Weight.Bold))
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text_str)

        if is_stage_zero:
            _draw_snooze_btn("snooze1", rects["snooze1"], t("banner_got_it"))
        else:
            _draw_snooze_btn("snooze1", rects["snooze1"], "💤 5m")
            _draw_snooze_btn("snooze2", rects["snooze2"], "⏭️ Skip")

    def _draw_pilot_speech_bubble(self, p: QPainter, px: float, py: float, card_right_x: float):
        """Draws an animated floating speech bubble pointing directly at the pilot, kept strictly clear of the card close button."""
        text = self._cached_hover_speech_text if (self.hovered_button == "plane" and self._cached_hover_speech_text) else self._cached_speech_text
        if not text:
            return

        f = QFont("Inter, Arial", 8, QFont.Weight.ExtraBold)
        p.setFont(f)
        fm = p.fontMetrics()
        bw = fm.horizontalAdvance(text) + 24.0
        bh = 26.0

        # Ensure the speech bubble never overlaps the close button or left card area
        min_bx = card_right_x + 10.0
        ideal_bx = px - bw * 0.5
        bx = max(min_bx, ideal_bx)

        # Float above plane with bobbing - elevated so hats and ears are fully clear
        bob = math.sin(self.tick * 0.08) * 3.0
        by = py - 72.0 + bob

        bubble_rect = QRectF(bx, by, bw, bh)

        # Anchor tail securely between bubble base and pilot tip
        tail_tip_x = px
        tail_base_x = max(bx + 14.0, min(bx + bw - 14.0, tail_tip_x))

        # Bubble Container Shape & Tail pointing to pilot
        tail = QPainterPath()
        tail.moveTo(tail_base_x - 6.0, by + bh)
        tail.lineTo(tail_tip_x, by + bh + 7.0)
        tail.lineTo(tail_base_x + 6.0, by + bh)
        tail.closeSubpath()

        if self.is_late:
            bg_col = QColor(217, 41, 41, 242)
            border_col = QColor(255, 115, 115)
        else:
            bg_col = QColor(36, 41, 61, 235)
            border_col = QColor(255, 255, 255, 64)

        p.setBrush(bg_col)
        p.setPen(QPen(border_col, 1.2))
        p.drawRoundedRect(bubble_rect, 10.0, 10.0)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(tail)

        # Bubble text
        p.setPen(Qt.GlobalColor.white)
        p.drawText(bubble_rect, Qt.AlignmentFlag.AlignCenter, text)

    # ── Dismiss ────────────────────────────────────────────────────────────────

    def _dismiss(self):
        self._timer.stop()
        self._set_cursor_shape(Qt.CursorShape.ArrowCursor)
        self.close()
        from .qt_banner import _active_banners
        if self in _active_banners:
            _active_banners.remove(self)
        app = QApplication.instance()
        if app and "--test" in sys.argv:
            app.quit()



