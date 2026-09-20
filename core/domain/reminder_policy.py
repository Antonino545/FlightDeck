"""
Category-Specific Reminder Policies and Strategy Registry for FlightDeck.
Decouples reminder intervals, urgency, and suppression logic into modular policies.
"""
from typing import Protocol, List, Optional, Any
from core.domain.state_machine import EventState


class ReminderPolicy(Protocol):
    """Strategy interface for event category reminder rules."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        """Returns ordered list of lead times (in minutes) before target time."""
        ...

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        """Determines if a reminder should be suppressed based on event state."""
        ...

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        """Determines if a reminder should be downgraded to a quiet notification."""
        ...


class ExamReminderPolicy:
    """Long-lead reminder policy for academic and professional exams."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        custom = config.get("exam_reminder_stages") if config else None
        stages = list(custom if custom is not None else [60, 30, 15, 5, 2, 0])
        if 0 not in stages:
            stages.append(0)
        return sorted([int(s) for s in stages], reverse=True)

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        if state in [EventState.COMPLETED, EventState.CANCELLED, EventState.ARRIVED]:
            return True
        if state == EventState.ACTIVE:
            reason = getattr(event, "arrival_reason", None) or ""
            if reason.startswith("call:"):
                return True
            if -3.5 <= diff_min <= 1.2:
                return False
            return True
        return False

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        # Exams are high importance; do not downgrade stage <= 15m
        return has_active_call and stage > 15


class LectureReminderPolicy:
    """Reminder policy for university classes, lectures, and group study."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        custom = config.get("lecture_reminder_stages") if config else None
        stages = list(custom if custom is not None else [30, 15, 5, 2, 0])
        if 0 not in stages:
            stages.append(0)
        return sorted([int(s) for s in stages], reverse=True)

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        if state in [EventState.COMPLETED, EventState.CANCELLED, EventState.ARRIVED]:
            return True
        if state == EventState.ACTIVE:
            reason = getattr(event, "arrival_reason", None) or ""
            if reason.startswith("call:"):
                return True
            if -3.5 <= diff_min <= 1.2:
                return False
            return True
        return False

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        return has_active_call and stage > 5


class VideoMeetingReminderPolicy:
    """Reminder policy for online calls (Google Meet, Zoom, Teams, etc.)."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        stages = list(config.get("meeting_reminder_stages", [20, 10, 5, 2, 0])) if config else [20, 10, 5, 2, 0]
        if 0 not in stages:
            stages.append(0)
        return sorted([int(s) for s in stages], reverse=True)

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        # Suppress if user is already participating in the call or event ended
        if state in [EventState.COMPLETED, EventState.CANCELLED]:
            return True
        reason = getattr(event, "arrival_reason", None) or ""
        if reason.startswith("call:"):
            return True
        if state == EventState.ACTIVE and not (-3.5 <= diff_min <= 1.2):
            return True
        return False

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        return has_active_call and stage > 0


class TransitReminderPolicy:
    """Departure-oriented reminder policy for travel, flights, and in-person navigation."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        stages = list(config.get("travel_reminder_stages", [45, 30, 15, 5, 2, 0])) if config else [45, 30, 15, 5, 2, 0]
        if 0 not in stages:
            stages.append(0)
        return sorted([int(s) for s in stages], reverse=True)

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        # Suppress departure alerts if user has already arrived at the destination
        return state in [EventState.ARRIVED, EventState.COMPLETED, EventState.CANCELLED]

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        return has_active_call and stage > 10


class GeneralReminderPolicy:
    """Fallback reminder policy for general appointments, dining, and activities."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        stages = list(config.get("general_reminder_stages", [20, 10, 5, 2, 0])) if config else [20, 10, 5, 2, 0]
        if 0 not in stages:
            stages.append(0)
        return sorted([int(s) for s in stages], reverse=True)

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        if state in [EventState.COMPLETED, EventState.CANCELLED, EventState.ARRIVED]:
            return True
        if state == EventState.ACTIVE:
            reason = getattr(event, "arrival_reason", None) or ""
            if reason.startswith("call:"):
                return True
            if -3.5 <= diff_min <= 1.2:
                return False
            return True
        return False

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        return has_active_call and stage > 10


class BillReminderPolicy:
    """Reminder policy for bills, rent, utilities, and payments."""

    def get_stages(self, event: Any, config: Any) -> List[int]:
        return [0]

    def should_suppress(self, event: Any, state: EventState, diff_min: float) -> bool:
        return state in [EventState.COMPLETED, EventState.CANCELLED, EventState.ARRIVED]

    def is_quiet(self, event: Any, has_active_call: bool, stage: int) -> bool:
        return has_active_call


class ReminderPolicyRegistry:
    """Central registry resolving the appropriate reminder policy for an event."""

    _exam_policy = ExamReminderPolicy()
    _lecture_policy = LectureReminderPolicy()
    _video_policy = VideoMeetingReminderPolicy()
    _transit_policy = TransitReminderPolicy()
    _general_policy = GeneralReminderPolicy()
    _bill_policy = BillReminderPolicy()

    @classmethod
    def get_policy(cls, event: Any) -> ReminderPolicy:
        """Selects policy based on event category, travel flags, and presence."""
        if getattr(event, "is_travel", False) or getattr(event, "departure_time", None):
            return cls._transit_policy

        cat = (getattr(event, "category", None) or getattr(event, "event_type", None) or "").lower()

        if cat == "bill":
            return cls._bill_policy
        elif cat == "exam":
            return cls._exam_policy
        elif cat in ["class", "study"]:
            return cls._lecture_policy
        elif cat == "video_meeting" or getattr(event, "meeting_url", None):
            return cls._video_policy
        elif cat in ["travel", "captain"]:
            return cls._transit_policy
        else:
            return cls._general_policy
