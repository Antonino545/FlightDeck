"""
Agenda View Model for FlightDeck.
Builds cross-platform AgendaEventVM presentation models from domain CalendarEvent/Meeting objects.
Decouples macOS AppKit and Linux PyQt6 presentation tabs from raw data structures.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

from core.domain.clock import Clock, system_clock
from core.domain.state_machine import EventState, resolve_event_state
from core.domain.capabilities import EventCapabilities
from core.domain.models import format_duration
from core.services.language_service import t, get_active_language

PILOT_ICONS = {
    "duck": "🦆",
    "captain": "✈️",
    "chef": "🍕",
    "owl": "🎓",
    "driver": "🚗",
    "zen_duck": "🛋️",
    "gym": "🏋️",
    "platypus": "🕵️",
    "squirrel": "🐿️"
}

TRANSPORT_ICONS = {
    "transit": "🚆",
    "automobile": "🚗",
    "walking": "🚶",
    "bicycling": "🚲"
}


@dataclass
class AgendaEventVM:
    """Decoupled, platform-agnostic presentation model for an agenda card."""
    uid: str
    title: str
    subtitle: str
    time_display: str
    countdown_text: str
    icon: str
    state: EventState
    capabilities: EventCapabilities
    action_btn_text: Optional[str] = None
    action_url: Optional[str] = None
    badge_text: Optional[str] = None
    badge_color: Optional[str] = None
    is_urgent: bool = False
    classroom: Optional[str] = None
    location_name: Optional[str] = None
    travel_time_minutes: Optional[int] = None
    departure_time_str: Optional[str] = None
    is_all_day: bool = False
    is_bill: bool = False
    is_paid: bool = False

    @property
    def has_action(self) -> bool:
        """Indicates if this event has an actionable URL for launching or copying."""
        return bool(self.action_url and self.action_url.strip() and self.action_url != "https://calendar.apple.com")


@dataclass
class CommandCenterVM:
    """Structured ViewModel partitioning today's agenda into NOW, NEXT, LATER, and EARLIER buckets."""
    now_event: Optional[AgendaEventVM] = None
    next_event: Optional[AgendaEventVM] = None
    later_events: List[AgendaEventVM] = field(default_factory=list)
    earlier_events: List[AgendaEventVM] = field(default_factory=list)
    all_events: List[AgendaEventVM] = field(default_factory=list)
    guidance: Optional[Any] = None  # TransitionGuidance from ContextEngine

    @property
    def has_events(self) -> bool:
        return bool(self.now_event or self.next_event or self.later_events or self.earlier_events or self.all_events)


class AgendaViewModel:
    """Transforms domain calendar items into ready-to-render AgendaEventVM list."""

    @staticmethod
    def build_event_vm(
        event: Any,
        clock: Optional[Clock] = None,
        lang: Optional[str] = None
    ) -> AgendaEventVM:
        import sys
        import urllib.parse
        current_clock = clock or system_clock
        active_lang = lang or get_active_language()
        now = current_clock.now()

        # Handle dict or object
        is_dict = isinstance(event, dict)
        get_val = lambda key, default=None: event.get(key, default) if is_dict else getattr(event, key, default)

        uid = str(get_val("uid") or get_val("id") or "")
        title = str(get_val("title") or "Event").strip()

        # Extract timestamps
        start_dt = get_val("start_time")
        if isinstance(start_dt, str):
            try:
                start_dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
            except Exception:
                start_dt = None
        if isinstance(start_dt, datetime) and start_dt.tzinfo is None:
            start_dt = start_dt.astimezone(timezone.utc)

        end_dt = get_val("end_time")
        if isinstance(end_dt, str):
            try:
                end_dt = datetime.fromisoformat(end_dt.replace("Z", "+00:00"))
            except Exception:
                end_dt = None
        if isinstance(end_dt, datetime) and end_dt.tzinfo is None:
            end_dt = end_dt.astimezone(timezone.utc)

        dep_dt = get_val("departure_time")
        if isinstance(dep_dt, str):
            try:
                dep_dt = datetime.fromisoformat(dep_dt.replace("Z", "+00:00"))
            except Exception:
                dep_dt = None
        if isinstance(dep_dt, datetime) and dep_dt.tzinfo is None:
            dep_dt = dep_dt.astimezone(timezone.utc)

        is_all_day = bool(get_val("is_all_day", False) or get_val("category") == "bill" or get_val("event_type") == "bill")

        # Time formatting
        start_str = start_dt.astimezone().strftime("%H:%M") if isinstance(start_dt, datetime) else "--:--"
        end_str = end_dt.astimezone().strftime("%H:%M") if isinstance(end_dt, datetime) else ""
        if is_all_day:
            time_display = t("agenda_all_day", default="All Day")
        else:
            time_display = f"{start_str} - {end_str}" if end_str else start_str

        # Pilot icon
        p_type = get_val("pilot_type", "duck")
        icon = PILOT_ICONS.get(p_type, "🦆")

        # Location & Subtitle components (clean up excessive whitespace/newlines)
        loc = " ".join(str(get_val("location") or "").split())
        classroom = " ".join(str(get_val("classroom")).split()) if get_val("classroom") else None
        teacher = " ".join(str(get_val("teacher")).split()) if get_val("teacher") else None
        travel_min = get_val("travel_time_minutes")
        transport_mode = get_val("transport_mode", "transit")
        trans_icon = TRANSPORT_ICONS.get(transport_mode, "🚗")

        # Resolve presence and arrival
        is_arr = bool(get_val("is_arrived", False))
        arr_reason = str(get_val("arrival_reason") or "")
        try:
            from core.services.arrival_service import arrival_service
            if not is_arr and arrival_service.is_manually_arrived(uid):
                is_arr = True
            if is_arr and not arr_reason:
                arr_reason = arrival_service.get_arrival_reason(uid) or "manual"
        except Exception:
            pass

        # Bill detection and paid status
        _cat = str(get_val("category", "") or get_val("event_type", "") or "").lower()
        is_bill = _cat == "bill"
        is_paid = False
        if is_bill:
            try:
                from core.services.reminder_engine import reminder_engine
                is_paid = reminder_engine.is_bill_paid(uid)
            except Exception:
                pass
            # Also check arrival reason
            if is_arr and "paid" in arr_reason:
                is_paid = True

        # Action URL resolution (online meeting or maps navigation fallback)
        meeting_url = get_val("meeting_url")
        action_url = get_val("action_url") or meeting_url

        try:
            from core.domain.classifier import EventClassifier
            extracted = EventClassifier.extract_meeting_url(f"{loc} {get_val('description', '')}")
            if extracted and (not action_url or action_url == "https://calendar.apple.com"):
                action_url = extracted
        except Exception:
            pass

        if not action_url and loc and loc != "missing value":
            if sys.platform == "darwin":
                action_url = f"https://maps.apple.com/?q={urllib.parse.quote(loc)}"
            else:
                action_url = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(loc)}"

        # Action Button text resolution
        action_btn_text = get_val("action_btn_text")
        if action_url and action_url != "https://calendar.apple.com":
            is_map_url = any(k in action_url.lower() for k in ["maps.apple.com", "google.com/maps", "maps."])
            if is_map_url or (action_btn_text and any(w in action_btn_text.upper() for w in ["MAPS", "MAPPE"])):
                maps_lbl = t("agenda_maps_button", default="🗺️ Maps")
                action_btn_text = f"{maps_lbl} (~{format_duration(travel_min)})" if travel_min else maps_lbl
            elif action_btn_text and action_btn_text not in ["📋 OPEN EVENT", "🚀 JOIN", "🚀 Join", "JOIN"]:
                # Preserve explicit custom button labels (e.g. "🚀 JOIN SESSION")
                pass
            elif "zoom.us" in action_url:
                action_btn_text = "🔷 Zoom"
            elif "teams.microsoft" in action_url or "teams.live.com" in action_url:
                action_btn_text = "🟣 Teams"
            elif "serenis" in action_url:
                action_btn_text = "🛋️ Serenis"
            elif "meet.google.com" in action_url:
                action_btn_text = "🟢 Meet"
            else:
                action_btn_text = t("agenda_join_button", default="🚀 Join")

        # Subtitle construction
        provider = get_val("provider")
        subtitle_parts = []
        if provider and provider != "missing value" and provider != "Reminder ⏰":
            subtitle_parts.append(provider)
        if classroom:
            subtitle_parts.append(f"🏫 {classroom}")
        if teacher:
            subtitle_parts.append(f"👤 {teacher}")
        if loc and loc != "missing value" and not classroom:
            subtitle_parts.append(f"📍 {loc[:35]}")
        elif action_url and "meet.google.com" in action_url and not classroom:
            subtitle_parts.append("🌐 Google Meet")

        if travel_min:
            dur_str = format_duration(travel_min)
            dep_clock = dep_dt.astimezone().strftime("%H:%M") if isinstance(dep_dt, datetime) else ""
            if dep_clock:
                subtitle_parts.append(f"{trans_icon} ~{dur_str} (Leave at {dep_clock})")
            else:
                subtitle_parts.append(f"{trans_icon} ~{dur_str} travel")

        subtitle = "  •  ".join(subtitle_parts) if subtitle_parts else str(get_val("description", "") or "")

        # State resolution
        state = resolve_event_state(event, clock=current_clock)

        # Capabilities resolution
        has_video = bool(action_url and any(k in action_url.lower() for k in ["meet.", "zoom.", "teams.", "webex.", "jitsi", "serenis"]))
        has_loc = bool(loc or classroom)
        has_nav = bool(action_url and any(m in action_url.lower() for m in ["maps.apple.com", "google.com/maps", "maps."]))
        capabilities = EventCapabilities(
            can_join=has_video,
            can_navigate=has_nav or has_loc,
            has_location=has_loc,
            needs_travel=bool(get_val("is_travel", False)),
            can_snooze=True,
            requires_acknowledgement=bool(get_val("category") in ["exam", "travel"]),
            show_arrival_badge=is_arr,
            show_in_call_badge=bool("call" in arr_reason)
        )

        # Status badge & countdown text
        badge_text = None
        badge_color = None
        is_urgent = False
        countdown_text = ""

        if is_bill and is_paid:
            badge_text = f"✅ {t('agenda_paid_badge', default='Paid')}"
            badge_color = "#a6e3a1"
        elif is_arr:
            if "call" in arr_reason:
                app_name = arr_reason.split(":", 1)[1] if ":" in arr_reason else ""
                badge_text = f"🟢 In {app_name}" if app_name and app_name != "manual" else f"🟢 {t('agenda_in_call_badge', default='In Call')}"
                badge_color = "#a6e3a1"
            elif "wifi" in arr_reason:
                badge_text = f"📍 {t('agenda_on_site_badge', default='On Site')}"
                badge_color = "#89b4fa"
            else:
                badge_text = f"✅ {t('agenda_arrived_badge', default='Arrived')}"
                badge_color = "#a6e3a1"
        elif state == EventState.COMPLETED:
            badge_text = f"✓ {t('agenda_ended_badge', default='Ended')}"
            badge_color = "#6c7086"
            countdown_text = t("agenda_concluded", default="Completed")
            is_urgent = False
        elif state == EventState.CANCELLED:
            badge_text = f"🚫 {t('agenda_cancelled_badge', default='Cancelled')}"
            badge_color = "#f38ba8"
            countdown_text = t("agenda_cancelled", default="Cancelled")
            is_urgent = False
        elif state == EventState.ACTIVE:
            badge_text = "🔴 Active"
            badge_color = "#f38ba8"
            is_urgent = True
        elif state == EventState.TIME_TO_LEAVE:
            badge_text = "🚨 Leave Now"
            badge_color = "#fab387"
            is_urgent = True
        elif state == EventState.ARRIVING:
            badge_text = "🚶 En Route"
            badge_color = "#f9e2af"

        # Countdown calculation
        if is_all_day:
            countdown_text = t("agenda_all_day", default="All Day")
            is_urgent = False
        elif state in (EventState.COMPLETED, EventState.CANCELLED):
            if not countdown_text:
                countdown_text = t("agenda_concluded", default="Completed")
        elif start_dt:
            diff_start = (start_dt - now).total_seconds() / 60.0
            if dep_dt and bool(get_val("is_travel", False)):
                diff_dep = (dep_dt - now).total_seconds() / 60.0
                if diff_dep <= 0 and diff_start > 0:
                    countdown_text = "🚨 Depart Now"
                    is_urgent = True
                elif 0 < diff_dep <= 60:
                    countdown_text = f"Leave in {int(diff_dep)}m"
                    if diff_dep <= 10:
                        is_urgent = True
                elif diff_dep > 60:
                    countdown_text = f"Leave at {dep_dt.astimezone().strftime('%H:%M')}"
            else:
                if 0 < diff_start <= 60:
                    countdown_text = f"In {int(diff_start)}m"
                    if diff_start <= 5:
                        is_urgent = True
                elif diff_start > 60:
                    countdown_text = f"At {start_str}"
                elif diff_start <= 0 and end_dt and now < end_dt:
                    diff_end = int((end_dt - now).total_seconds() / 60.0)
                    countdown_text = f"Ends in {format_duration(diff_end)}"

        dep_str = dep_dt.astimezone().strftime("%H:%M") if isinstance(dep_dt, datetime) else None

        return AgendaEventVM(
            uid=uid,
            title=title,
            subtitle=subtitle,
            time_display=time_display,
            countdown_text=countdown_text,
            icon=icon,
            state=state,
            capabilities=capabilities,
            action_btn_text=action_btn_text,
            action_url=action_url,
            badge_text=badge_text,
            badge_color=badge_color,
            is_urgent=is_urgent,
            classroom=classroom,
            location_name=loc,
            travel_time_minutes=travel_min,
            departure_time_str=dep_str,
            is_all_day=is_all_day,
            is_bill=is_bill,
            is_paid=is_paid
        )

    @staticmethod
    def build(
        events: List[Any],
        clock: Optional[Clock] = None,
        lang: Optional[str] = None
    ) -> List[AgendaEventVM]:
        """Builds a sorted list of AgendaEventVM items for today's agenda."""
        current_clock = clock or system_clock
        now = current_clock.now()

        # Filter events for today in local date
        today_events = []
        for e in events:
            start_dt = e.get("start_time") if isinstance(e, dict) else getattr(e, "start_time", None)
            if isinstance(start_dt, str):
                try:
                    start_dt = datetime.fromisoformat(start_dt.replace("Z", "+00:00"))
                except Exception:
                    start_dt = None
            if isinstance(start_dt, datetime):
                if start_dt.astimezone().date() == now.astimezone().date():
                    today_events.append((e, start_dt))

        # Sort chronologically by start_time
        today_events.sort(key=lambda item: item[1])

        vms = [AgendaViewModel.build_event_vm(item[0], clock=current_clock, lang=lang) for item in today_events]
        return vms

    @staticmethod
    def build_command_center(
        events: List[Any],
        clock: Optional[Clock] = None,
        lang: Optional[str] = None
    ) -> CommandCenterVM:
        """Partitions today's events into NOW, NEXT, LATER, and EARLIER buckets with ContextEngine guidance."""
        current_clock = clock or system_clock
        now = current_clock.now()

        all_vms = AgendaViewModel.build(events, clock=current_clock, lang=lang)
        if not all_vms:
            return CommandCenterVM()

        from core.domain.context_engine import ContextEngine
        guidance = ContextEngine.evaluate(events, current_time=now, clock=current_clock, lang=lang)

        # 1. Partition into completed/past vs active/upcoming candidates
        earlier_vms = [
            v for v in all_vms
            if v.state in (EventState.COMPLETED, EventState.CANCELLED, EventState.DISMISSED)
        ]
        active_candidates = [
            v for v in all_vms
            if v.state not in (EventState.COMPLETED, EventState.CANCELLED, EventState.DISMISSED)
        ]

        now_vm: Optional[AgendaEventVM] = None
        target_uid = None
        if guidance and guidance.target_event:
            target_uid = str(getattr(guidance.target_event, "uid", None) or getattr(guidance.target_event, "id", None) or "")

        # Look for explicitly active/arriving/time-to-leave events in active_candidates (excluding all-day/bills)
        for vm in active_candidates:
            if vm.is_all_day:
                continue
            if vm.state in (EventState.ACTIVE, EventState.TIME_TO_LEAVE, EventState.ARRIVING):
                now_vm = vm
                break
            if target_uid and vm.uid == target_uid and guidance and guidance.is_urgent:
                now_vm = vm
                break

        remaining_vms = [v for v in active_candidates if now_vm is None or v.uid != now_vm.uid]

        # Determine NEXT event: first event chronologically that is UPCOMING or PREPARE (excluding all-day/bills)
        next_vm: Optional[AgendaEventVM] = None
        for vm in remaining_vms:
            if vm.is_all_day:
                continue
            if vm.state in (EventState.UPCOMING, EventState.PREPARE):
                next_vm = vm
                break

        if not now_vm and not next_vm and remaining_vms:
            timed_remaining = [v for v in remaining_vms if not v.is_all_day]
            if timed_remaining:
                next_vm = timed_remaining[0]

        later_vms = [v for v in remaining_vms if next_vm is None or v.uid != next_vm.uid]

        return CommandCenterVM(
            now_event=now_vm,
            next_event=next_vm,
            later_events=later_vms,
            earlier_events=earlier_vms,
            all_events=all_vms,
            guidance=guidance
        )
