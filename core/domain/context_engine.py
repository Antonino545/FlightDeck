"""
Context Engine & "Why?" Transparency Engine for FlightDeck.
Single authority that evaluates real-time calendar schedules, transit ETA buffers,
user presence signals (Wi-Fi, active call processes), and time horizons to output
actionable transition recommendations with explicit, human-readable rationale.
"""
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional, Any

from core.domain.clock import Clock, system_clock
from core.domain.models import CalendarEvent, format_duration
from core.domain.state_machine import EventState, resolve_event_state
from core.services.language_service import t


class ActionType(Enum):
    """Specific immediate action prescribed by the Context Engine."""
    LEAVE_NOW = "leave_now"
    PREPARE_DEPARTURE = "prepare_departure"
    JOIN_CALL = "join_call"
    HEAD_TO_CLASS = "head_to_class"
    ACTIVE_SESSION = "active_session"
    RELAX = "relax"


class UserContextState(Enum):
    """High-level real-time state of the user."""
    IDLE = "idle"
    PREPARING = "preparing"
    TIME_TO_LEAVE = "time_to_leave"
    EN_ROUTE = "en_route"
    IN_CALL = "in_call"
    IN_SESSION = "in_session"


@dataclass
class TransitionGuidance:
    """Actionable transition guidance with transparent 'Why?' rationale."""
    action_type: ActionType
    context_state: UserContextState
    headline: str
    rationale: str
    urgency_level: str  # "critical", "urgent", "normal", "low"
    target_event: Optional[Any] = None
    action_url: Optional[str] = None
    action_btn_text: Optional[str] = None
    countdown_text: str = ""
    buffer_minutes: int = 0

    @property
    def is_urgent(self) -> bool:
        return self.urgency_level in ("critical", "urgent")


class ContextEngine:
    """Evaluates calendar items and environmental signals to generate clear recommendations."""

    @staticmethod
    def _build_active_session_rationale(
        event: Any,
        now: datetime,
        st: Optional[datetime],
        et: Optional[datetime],
        is_arr: bool = False,
        arr_reason: str = "",
        lang: Optional[str] = None
    ) -> str:
        """Constructs human-friendly, category-tailored context and progress for active events."""
        from core.services.language_service import get_active_language
        active_lang = lang or get_active_language()

        def get_attr(ev: Any, key: str, default: Any = None) -> Any:
            return ev.get(key, default) if isinstance(ev, dict) else getattr(ev, key, default)

        title = str(get_attr(event, "title") or "").strip()
        cat = str(get_attr(event, "category") or get_attr(event, "event_type") or "").lower()
        provider = str(get_attr(event, "provider") or "").lower()
        classroom = get_attr(event, "classroom")
        search_blob = f"{title} {cat} {provider}".lower()

        # Calculate time remaining and end clock
        rem_str = ""
        end_clock = ""
        if et:
            rem_min = max(0, int((et - now).total_seconds() / 60))
            rem_str = format_duration(rem_min)
            end_clock = et.astimezone().strftime("%H:%M")

        is_it = (active_lang == "it")

        # 1. Study
        if cat == "study" or any(w in search_blob for w in ["study", "studio", "studiare", "ripasso", "compiti", "homework"]):
            if et:
                if is_it:
                    return f"📖 Sessione di studio in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Buono studio e concentrazione!"
                return f"📖 Study session in progress • ~{rem_str} remaining (until {end_clock}) • Good luck & stay focused!"
            return "📖 Sessione di studio in corso • Buono studio e concentrazione!" if is_it else "📖 Study session in progress • Good luck & stay focused!"

        # 2. Exam
        if cat == "exam" or any(w in search_blob for w in ["exam", "esame", "appello", "parziale", "midterm"]):
            if et:
                if is_it:
                    return f"🎯 Esame in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Buona fortuna!"
                return f"🎯 Exam in progress • ~{rem_str} remaining (until {end_clock}) • Good luck!"
            return "🎯 Esame in corso • Buona fortuna!" if is_it else "🎯 Exam in progress • Good luck!"

        # 3. Class / Lecture
        if cat == "class" or any(w in search_blob for w in ["class", "lecture", "lezione", "corso"]):
            room_it = f" in aula {classroom}" if classroom else ""
            room_en = f" in {classroom}" if classroom else ""
            if et:
                if is_it:
                    return f"🎓 Lezione in corso{room_it} • ~{rem_str} rimanenti (fino alle {end_clock})"
                return f"🎓 Lecture in progress{room_en} • ~{rem_str} remaining (until {end_clock})"
            return f"🎓 Lezione in corso{room_it}" if is_it else f"🎓 Lecture in progress{room_en}"

        # 4. Sport / Workout
        if cat in ("sport", "gym") or any(w in search_blob for w in ["gym", "workout", "palestra", "allenamento", "fitness"]):
            if et:
                if is_it:
                    return f"🏋️ Allenamento in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Dacci dentro!"
                return f"🏋️ Workout in progress • ~{rem_str} remaining (until {end_clock}) • Keep pushing!"
            return "🏋️ Allenamento in corso • Dacci dentro!" if is_it else "🏋️ Workout in progress • Keep pushing!"

        # 5. Food / Meal
        if cat in ("food", "chef") or any(w in search_blob for w in ["dinner", "lunch", "cena", "pranzo", "pizzeria", "ristorante"]):
            if et:
                if is_it:
                    return f"🍽️ Pranzo o cena in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Buon appetito!"
                return f"🍽️ Meal in progress • ~{rem_str} remaining (until {end_clock}) • Enjoy your meal!"
            return "🍽️ Buon appetito!" if is_it else "🍽️ Meal in progress • Enjoy your meal!"

        # 6. Wellness / Health
        if cat in ("health", "zen_duck") or any(w in search_blob for w in ["meditation", "wellness", "relax", "yoga", "serenis"]):
            if et:
                if is_it:
                    return f"🧘 Sessione benessere in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Rilassati e ricaricati."
                return f"🧘 Wellness session in progress • ~{rem_str} remaining (until {end_clock}) • Relax & recharge."
            return "🧘 Rilassati e ricaricati." if is_it else "🧘 Wellness session in progress • Relax & recharge."

        # 7. Work
        if cat == "work" or any(w in search_blob for w in ["work", "working", "office", "lavoro", "ufficio", "progetto", "coworking"]):
            if et:
                if is_it:
                    return f"💼 Sessione di lavoro in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Buona produttività!"
                return f"💼 Work session in progress • ~{rem_str} remaining (until {end_clock}) • Have a productive session!"
            return "💼 Sessione di lavoro in corso • Buona produttività!" if is_it else "💼 Work session in progress • Have a productive session!"

        # 8. Concert / Live Music
        if cat == "concert" or any(w in search_blob for w in ["concert", "concerto", "live music", "musica dal vivo", "festival", "show"]):
            if et:
                if is_it:
                    return f"🎸 Concerto dal vivo in corso • ~{rem_str} rimanenti (fino alle {end_clock}) • Goditi lo spettacolo!"
                return f"🎸 Live concert in progress • ~{rem_str} remaining (until {end_clock}) • Enjoy the show!"
            return "🎸 Concerto dal vivo in corso • Goditi lo spettacolo!" if is_it else "🎸 Live concert in progress • Enjoy the show!"

        # 9. General Fallback
        if is_arr or "wifi" in arr_reason:
            if et:
                return f"📍 Presenza confermata sul posto • ~{rem_str} rimanenti (fino alle {end_clock})" if is_it else f"📍 On-site presence confirmed • ~{rem_str} remaining (until {end_clock})"
            return "📍 Presenza confermata sul posto." if is_it else "📍 On-site venue presence confirmed."

        if et:
            return f"⏳ In corso • ~{rem_str} rimanenti (fino alle {end_clock})" if is_it else f"⏳ In progress • ~{rem_str} remaining (until {end_clock})"
        return "⏳ In corso." if is_it else "⏳ In progress."

    @staticmethod
    def evaluate(
        events: List[Any],
        clock: Optional[Clock] = None,
        default_buffer_minutes: int = 10,
        current_time: Optional[datetime] = None,
        lang: Optional[str] = None
    ) -> TransitionGuidance:
        """
        Determines the immediate primary recommendation and transparent rationale for the user.
        """
        from core.domain.clock import FakeClock
        from core.services.language_service import get_active_language
        active_lang = lang or get_active_language()

        if current_time:
            current_clock = FakeClock(current_time)
        else:
            current_clock = clock or system_clock
        now = current_clock.now()
        now_local = now.astimezone()

        # Filter events for today (local time) that haven't ended yet
        today_events = []
        for e in events:
            # Extract start and end time
            st = e.get("start_time") if isinstance(e, dict) else getattr(e, "start_time", None)
            et = e.get("end_time") if isinstance(e, dict) else getattr(e, "end_time", None)

            if isinstance(st, str):
                st = datetime.fromisoformat(st)
            if isinstance(st, datetime) and st.tzinfo is None:
                st = st.astimezone(timezone.utc)

            if isinstance(et, str):
                et = datetime.fromisoformat(et)
            if isinstance(et, datetime) and et.tzinfo is None:
                et = et.astimezone(timezone.utc)

            if isinstance(st, datetime):
                if st.astimezone().date() == now_local.date():
                    is_all_day = bool(e.get("is_all_day", False) if isinstance(e, dict) else getattr(e, "is_all_day", False))
                    cat = str((e.get("category") or e.get("event_type") or "") if isinstance(e, dict) else (getattr(e, "category", None) or getattr(e, "event_type", None) or ""))
                    if not is_all_day and cat != "bill":
                        if et is None or et > now:
                            today_events.append((e, st, et))

        # Sort by start time
        today_events.sort(key=lambda item: item[1])

        if not today_events:
            return TransitionGuidance(
                action_type=ActionType.RELAX,
                context_state=UserContextState.IDLE,
                headline="All Clear for Today",
                rationale="No pending calendar events scheduled for the rest of today.",
                urgency_level="low",
                target_event=None,
                action_url=None,
                action_btn_text=None,
                countdown_text="Clear Schedule"
            )

        # Helper to retrieve attributes from dict or model
        def get_attr(ev: Any, key: str, default: Any = None) -> Any:
            return ev.get(key, default) if isinstance(ev, dict) else getattr(ev, key, default)

        # 1. Check if any event is currently ACTIVE or IN_CALL
        for event, st, et in today_events:
            state = resolve_event_state(event, clock=current_clock)
            is_arr = bool(get_attr(event, "is_arrived", False))
            arr_reason = str(get_attr(event, "arrival_reason") or "")
            title = str(get_attr(event, "title") or "Event").strip()
            action_url = get_attr(event, "action_url") or get_attr(event, "meeting_url")
            action_btn = get_attr(event, "action_btn_text") or t("agenda_join_button", default="🚀 Join")

            if state == EventState.ACTIVE or (st <= now and (et is None or now < et)):
                rem_dur = format_duration(max(0, int((et - now).total_seconds() / 60))) if et else ""
                countdown_lbl = f"Ends in {rem_dur}" if rem_dur else "In Session"

                if "call" in arr_reason:
                    app_name = arr_reason.split(":", 1)[1] if ":" in arr_reason else "Call"
                    end_info = f" • ~{rem_dur} remaining" if rem_dur else ""
                    return TransitionGuidance(
                        action_type=ActionType.ACTIVE_SESSION,
                        context_state=UserContextState.IN_CALL,
                        headline=f"Active in {app_name}: {title}",
                        rationale=f"Currently attending online conference via {app_name}{end_info}. Banners suppressed.",
                        urgency_level="normal",
                        target_event=event,
                        action_url=action_url,
                        action_btn_text=action_btn,
                        countdown_text=countdown_lbl
                    )
                elif action_url and ("meet." in action_url or "zoom." in action_url or "teams." in action_url or "serenis" in action_url) and not is_arr and (now - st).total_seconds() < 300:
                    # Within first 5 minutes of online meeting start time, offer 1-click join if not joined yet
                    return TransitionGuidance(
                        action_type=ActionType.JOIN_CALL,
                        context_state=UserContextState.IN_SESSION,
                        headline=f"Starting Now: {title}",
                        rationale="Event has started. Online meeting link is active and ready to join.",
                        urgency_level="critical",
                        target_event=event,
                        action_url=action_url,
                        action_btn_text=action_btn,
                        countdown_text="Live Now"
                    )
                else:
                    active_rationale = ContextEngine._build_active_session_rationale(
                        event=event, now=now, st=st, et=et, is_arr=is_arr, arr_reason=arr_reason, lang=active_lang
                    )
                    return TransitionGuidance(
                        action_type=ActionType.ACTIVE_SESSION,
                        context_state=UserContextState.IN_SESSION,
                        headline=f"In Session: {title}",
                        rationale=active_rationale,
                        urgency_level="normal",
                        target_event=event,
                        action_url=action_url,
                        action_btn_text=action_btn,
                        countdown_text=countdown_lbl
                    )

        # 2. Check closest upcoming event
        closest_event, st, et = today_events[0]
        title = str(get_attr(closest_event, "title") or "Upcoming Event").strip()
        loc = str(get_attr(closest_event, "location") or "")
        classroom = get_attr(closest_event, "classroom")
        category = get_attr(closest_event, "category") or "general"
        is_travel = bool(get_attr(closest_event, "is_travel", False))
        travel_min = get_attr(closest_event, "travel_time_minutes")
        action_url = get_attr(closest_event, "action_url") or get_attr(closest_event, "meeting_url")
        action_btn = get_attr(closest_event, "action_btn_text")

        # Check departure time
        dep_dt = get_attr(closest_event, "departure_time")
        if isinstance(dep_dt, str):
            dep_dt = datetime.fromisoformat(dep_dt)
        if isinstance(dep_dt, datetime) and dep_dt.tzinfo is None:
            dep_dt = dep_dt.astimezone(timezone.utc)

        minutes_to_start = (st - now).total_seconds() / 60.0

        # Scenario A: Event requires travel / departure
        if is_travel or (travel_min and travel_min > 0):
            est_travel = travel_min or 15
            if not dep_dt:
                dep_dt = st - timedelta(minutes=est_travel + default_buffer_minutes)

            minutes_to_dep = (dep_dt - now).total_seconds() / 60.0

            if minutes_to_dep <= 0:
                # Past departure time but before event start -> Time to leave / En route
                destination = classroom or (loc[:30] if loc and loc != "missing value" else "destination")
                return TransitionGuidance(
                    action_type=ActionType.LEAVE_NOW,
                    context_state=UserContextState.TIME_TO_LEAVE,
                    headline=f"Leave Now for {title}",
                    rationale=f"Departure deadline reached: ~{format_duration(est_travel)} travel required to reach {destination} on time for {st.astimezone().strftime('%H:%M')}.",
                    urgency_level="critical",
                    target_event=closest_event,
                    action_url=action_url,
                    action_btn_text=action_btn or t("agenda_maps_button", default="🗺️ Directions"),
                    countdown_text="🚨 Depart Now",
                    buffer_minutes=default_buffer_minutes
                )
            elif minutes_to_dep <= 15:
                destination = classroom or (loc[:30] if loc and loc != "missing value" else "destination")
                return TransitionGuidance(
                    action_type=ActionType.PREPARE_DEPARTURE,
                    context_state=UserContextState.PREPARING,
                    headline=f"Prepare Departure for {title}",
                    rationale=f"Leave in {int(minutes_to_dep)}m: ~{format_duration(est_travel)} travel + {default_buffer_minutes}m buffer to reach {destination} by {st.astimezone().strftime('%H:%M')}.",
                    urgency_level="urgent" if minutes_to_dep <= 5 else "high",
                    target_event=closest_event,
                    action_url=action_url,
                    action_btn_text=action_btn or t("agenda_maps_button", default="🗺️ Directions"),
                    countdown_text=f"Leave in {int(minutes_to_dep)}m",
                    buffer_minutes=default_buffer_minutes
                )

        # Scenario B: Online Video Conference
        if action_url and ("meet." in action_url or "zoom." in action_url or "teams." in action_url or "serenis" in action_url):
            if minutes_to_start <= 10:
                return TransitionGuidance(
                    action_type=ActionType.JOIN_CALL,
                    context_state=UserContextState.PREPARING,
                    headline=f"Ready to Join: {title}",
                    rationale=f"Online video meeting begins in {int(minutes_to_start)}m. 1-click link is ready to connect.",
                    urgency_level="urgent" if minutes_to_start <= 3 else "high",
                    target_event=closest_event,
                    action_url=action_url,
                    action_btn_text=action_btn or t("agenda_join_button", default="🚀 Join"),
                    countdown_text=f"In {int(minutes_to_start)}m"
                )

        # Scenario C: In-Person Lecture or Exam
        if classroom or category in ("class", "exam"):
            dest = f"room {classroom}" if classroom else (loc[:30] if loc else "campus")
            if minutes_to_start <= 15:
                return TransitionGuidance(
                    action_type=ActionType.HEAD_TO_CLASS,
                    context_state=UserContextState.PREPARING,
                    headline=f"Head to {classroom or title}",
                    rationale=f"Academic session starts in {int(minutes_to_start)}m at {dest}. Ensure notes and materials are ready.",
                    urgency_level="urgent" if minutes_to_start <= 5 else "high",
                    target_event=closest_event,
                    action_url=action_url,
                    action_btn_text=action_btn,
                    countdown_text=f"In {int(minutes_to_start)}m"
                )

        # Scenario D: General Event
        if minutes_to_start <= 30:
            return TransitionGuidance(
                action_type=ActionType.PREPARE_DEPARTURE,
                context_state=UserContextState.PREPARING,
                headline=f"Upcoming: {title}",
                rationale=f"Starts in {int(minutes_to_start)}m ({st.astimezone().strftime('%H:%M')}).",
                urgency_level="normal",
                target_event=closest_event,
                action_url=action_url,
                action_btn_text=action_btn,
                countdown_text=f"In {int(minutes_to_start)}m"
            )

        # Scenario E: Far ahead (> 30 mins)
        return TransitionGuidance(
            action_type=ActionType.RELAX,
            context_state=UserContextState.IDLE,
            headline=f"Next: {title} at {st.astimezone().strftime('%H:%M')}",
            rationale=f"Upcoming flight scheduled for {st.astimezone().strftime('%H:%M')} (in {format_duration(int(minutes_to_start))}). No immediate action needed.",
            urgency_level="low",
            target_event=closest_event,
            action_url=action_url,
            action_btn_text=action_btn,
            countdown_text=f"At {st.astimezone().strftime('%H:%M')}"
        )
