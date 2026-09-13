"""
Domain models, Enums, and Value Objects for FlightDeck.
Pure Python representations decoupled from PyObjC, PyQt, and external frameworks.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any
import uuid

__version__ = "1.0.54"


class PilotType(str, Enum):
    DUCK = "duck"
    CAPTAIN = "captain"
    CHEF = "chef"
    OWL = "owl"
    DRIVER = "driver"
    ZEN_DUCK = "zen_duck"
    GYM = "gym"
    PLATYPUS = "platypus"
    SQUIRREL = "squirrel"


class EventCategory(str, Enum):
    VIDEO_MEETING = "video_meeting"
    TRAVEL = "travel"
    FOOD = "food"
    EXAM = "exam"
    CLASS = "class"
    STUDY = "study"
    HEALTH = "health"
    IN_PERSON = "in_person"
    SPORT = "sport"
    WORK = "work"
    CONCERT = "concert"
    GENERAL = "general"


class TransportMode(str, Enum):
    TRANSIT = "transit"           # Public Transit (Bus, Tram, Subway, Train) 🚆🚌
    AUTOMOBILE = "automobile"     # Car / Motorcycle 🚗
    WALKING = "walking"           # Walking 🚶‍♂️
    BICYCLING = "bicycling"       # Cycling 🚲


def format_duration(minutes: Optional[int], long_form: bool = False) -> str:
    """
    Converts a duration in minutes into a human-readable string with hours and minutes.
    Examples:
    - 30 min -> "30m" (short) or "30 min" (long)
    - 60 min -> "1h" (short) or "1 hour" (long)
    - 90 min -> "1h 30m" (short) or "1h 30m" (long)
    - 120 min -> "2h" (short) or "2 hours" (long)
    - 145 min -> "2h 25m" (short) or "2h 25m" (long)
    """
    if minutes is None or minutes <= 0:
        return "0m" if not long_form else "0 min"

    hours = int(minutes // 60)
    rem_min = int(minutes % 60)

    if hours > 0 and rem_min > 0:
        return f"{hours}h {rem_min}m"
    elif hours > 0:
        if long_form:
            return f"{hours} hour" if hours == 1 else f"{hours} hours"
        return f"{hours}h"
    else:
        return f"{rem_min}m" if not long_form else f"{rem_min} min"


# ==============================================================================
# Domain Value Objects
# ==============================================================================

@dataclass
class EventTime:
    """Temporal schedule metadata for an event."""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    is_all_day: bool = False

    def __post_init__(self):
        if self.start:
            self.start = self.start.astimezone(timezone.utc)
        if self.end:
            self.end = self.end.astimezone(timezone.utc)

    @property
    def duration_minutes(self) -> Optional[int]:
        if self.start and self.end:
            diff = (self.end - self.start).total_seconds() / 60.0
            return max(0, int(round(diff)))
        return None

    @property
    def is_upcoming(self) -> bool:
        now = datetime.now(timezone.utc)
        if self.end:
            return self.end > now
        if self.start:
            return self.start > now
        return False

    @property
    def is_past(self) -> bool:
        return not self.is_upcoming


@dataclass
class Location:
    """Geographic and venue location metadata."""
    name: str = ""
    classroom: Optional[str] = None
    teacher: Optional[str] = None
    origin_address: Optional[str] = None

    def __post_init__(self):
        if self.name:
            self.name = " ".join(str(self.name).split())
        if self.classroom:
            self.classroom = " ".join(str(self.classroom).split())
        if self.teacher:
            self.teacher = " ".join(str(self.teacher).split())
        if self.origin_address:
            self.origin_address = " ".join(str(self.origin_address).split())

    @property
    def has_location(self) -> bool:
        return bool(self.name or self.classroom)

    def __str__(self) -> str:
        return self.name


@dataclass
class MeetingLink:
    """Online video conference or telemedicine metadata."""
    url: Optional[str] = None
    action_url: Optional[str] = None
    provider_name: Optional[str] = None

    @property
    def is_online(self) -> bool:
        return bool(self.url or self.action_url)


@dataclass
class TravelPlan:
    """Multi-modal travel and departure estimation metadata."""
    is_travel: bool = False
    departure_time: Optional[datetime] = None
    travel_time_minutes: Optional[int] = None
    travel_distance_km: Optional[float] = None
    transport_mode: Optional[str] = None
    origin_address: Optional[str] = None
    eta_text: Optional[str] = None

    def __post_init__(self):
        if self.departure_time:
            self.departure_time = self.departure_time.astimezone(timezone.utc)


@dataclass
class PresenceStatus:
    """Real-time user presence, venue Wi-Fi, and arrival detection."""
    is_arrived: bool = False
    arrival_reason: Optional[str] = None
    is_quiet_reminder: bool = False


@dataclass
class EventPresentation:
    """UI presentation styling and mascot tokens decoupled from pure domain data."""
    pilot_type: str = "duck"
    theme_name: str = "Sunset Orange"
    action_btn_text: str = "📋 OPEN EVENT"
    animal: Optional[str] = None
    outfit: Optional[str] = None
    accessories: list = field(default_factory=list)


# ==============================================================================
# Central Domain Entity: CalendarEvent (with Meeting backward-compatibility)
# ==============================================================================

class CalendarEvent:
    """
    Central domain entity representing any scheduled calendar item in FlightDeck.
    Composes pure value objects (EventTime, Location, MeetingLink, TravelPlan,
    PresenceStatus, EventPresentation) while providing full backward compatibility
    with the historical Meeting dataclass.
    """

    def __init__(
        self,
        title: str = "",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        meeting_url: Optional[str] = None,
        location: str = "",
        description: str = "",
        event_type: str = "general",
        pilot_type: str = "duck",
        provider: str = "Reminder ⏰",
        action_btn_text: str = "📋 OPEN EVENT",
        action_url: Optional[str] = None,
        theme_name: str = "Sunset Orange",
        is_travel: bool = False,
        reminder_stage: Optional[int] = None,
        category: Optional[str] = None,
        uid: Optional[str] = None,
        is_all_day: bool = False,
        travel_time_minutes: Optional[int] = None,
        travel_distance_km: Optional[float] = None,
        transport_mode: Optional[str] = None,
        departure_time: Optional[datetime] = None,
        origin_address: Optional[str] = None,
        eta_text: Optional[str] = None,
        classroom: Optional[str] = None,
        teacher: Optional[str] = None,
        is_arrived: bool = False,
        arrival_reason: Optional[str] = None,
        is_quiet_reminder: bool = False,
        animal: Optional[str] = None,
        outfit: Optional[str] = None,
        accessories: Optional[list] = None,
        # Composed value object parameters
        time_info: Optional[EventTime] = None,
        location_info: Optional[Location] = None,
        meeting_link: Optional[MeetingLink] = None,
        travel_plan: Optional[TravelPlan] = None,
        presence_info: Optional[PresenceStatus] = None,
        presentation_info: Optional[EventPresentation] = None,
        **extra_kwargs: Any
    ):
        self.title = str(title or "")
        self.description = str(description or "")
        self.provider = str(provider or "Reminder ⏰")
        self.reminder_stage = reminder_stage
        self.uid = uid or extra_kwargs.get("id")

        # Category and Event Type normalization
        cat = category or event_type or "general"
        self.category = cat
        self.event_type = cat

        # Compose value objects
        self.time = time_info or EventTime(
            start=start_time,
            end=end_time,
            is_all_day=bool(is_all_day)
        )
        self.location_info = location_info or Location(
            name=str(location or ""),
            classroom=classroom,
            teacher=teacher,
            origin_address=origin_address
        )
        if isinstance(meeting_link, str):
            self.online_meeting = MeetingLink(
                url=meeting_link,
                action_url=action_url,
                provider_name=provider
            )
        else:
            self.online_meeting = meeting_link or MeetingLink(
                url=meeting_url,
                action_url=action_url,
                provider_name=provider
            )
        self.travel = travel_plan or TravelPlan(
            is_travel=bool(is_travel),
            departure_time=departure_time,
            travel_time_minutes=travel_time_minutes,
            travel_distance_km=travel_distance_km,
            transport_mode=transport_mode,
            origin_address=origin_address,
            eta_text=eta_text
        )
        self.presence = presence_info or PresenceStatus(
            is_arrived=bool(is_arrived),
            arrival_reason=arrival_reason,
            is_quiet_reminder=bool(is_quiet_reminder)
        )
        self.presentation = presentation_info or EventPresentation(
            pilot_type=pilot_type or "duck",
            theme_name=theme_name or "Sunset Orange",
            action_btn_text=action_btn_text or "📋 OPEN EVENT",
            animal=animal,
            outfit=outfit,
            accessories=list(accessories or extra_kwargs.get("accessories", []))
        )

        # Generate deterministic UUID if none provided
        if not self.uid:
            time_str = self.start_time.strftime("%Y%m%dT%H%M") if self.start_time else "unknown_time"
            unique_str = f"{self.title}_{time_str}_{self.provider}_{self.location}_{self.description}"
            self.uid = str(uuid.uuid5(uuid.NAMESPACE_URL, unique_str))

    # --------------------------------------------------------------------------
    # Backward-Compatible Delegated Properties
    # --------------------------------------------------------------------------

    @property
    def id(self) -> str:
        if self.uid:
            return self.uid
        time_str = self.start_time.strftime("%Y%m%d%H%M") if self.start_time else "000000000000"
        return f"{self.title}_{time_str}"

    @property
    def start_time(self) -> Optional[datetime]:
        return self.time.start if self.time else None

    @start_time.setter
    def start_time(self, val: Optional[datetime]) -> None:
        if val:
            val = val.astimezone(timezone.utc)
        if self.time is None:
            self.time = EventTime(start=val)
        else:
            self.time.start = val

    @property
    def end_time(self) -> Optional[datetime]:
        return self.time.end if self.time else None

    @end_time.setter
    def end_time(self, val: Optional[datetime]) -> None:
        if val:
            val = val.astimezone(timezone.utc)
        if self.time is None:
            self.time = EventTime(end=val)
        else:
            self.time.end = val

    @property
    def is_all_day(self) -> bool:
        return self.time.is_all_day if self.time else False

    @is_all_day.setter
    def is_all_day(self, val: bool) -> None:
        if self.time is None:
            self.time = EventTime(is_all_day=bool(val))
        else:
            self.time.is_all_day = bool(val)

    @property
    def duration_minutes(self) -> Optional[int]:
        return self.time.duration_minutes if self.time else None

    @property
    def is_upcoming(self) -> bool:
        return self.time.is_upcoming if self.time else False

    @property
    def is_past(self) -> bool:
        return self.time.is_past if self.time else True

    @property
    def location(self) -> str:
        return self.location_info.name if self.location_info else ""

    @location.setter
    def location(self, val: str) -> None:
        if self.location_info is None:
            self.location_info = Location(name=str(val or ""))
        else:
            self.location_info.name = str(val or "")

    @property
    def classroom(self) -> Optional[str]:
        return self.location_info.classroom if self.location_info else None

    @classroom.setter
    def classroom(self, val: Optional[str]) -> None:
        if self.location_info is None:
            self.location_info = Location(classroom=val)
        else:
            self.location_info.classroom = val

    @property
    def teacher(self) -> Optional[str]:
        return self.location_info.teacher if self.location_info else None

    @teacher.setter
    def teacher(self, val: Optional[str]) -> None:
        if self.location_info is None:
            self.location_info = Location(teacher=val)
        else:
            self.location_info.teacher = val

    @property
    def origin_address(self) -> Optional[str]:
        return self.location_info.origin_address if self.location_info else None

    @origin_address.setter
    def origin_address(self, val: Optional[str]) -> None:
        if self.location_info is None:
            self.location_info = Location(origin_address=val)
        else:
            self.location_info.origin_address = val
        if self.travel:
            self.travel.origin_address = val

    @property
    def meeting_url(self) -> Optional[str]:
        return self.online_meeting.url if self.online_meeting else None

    @meeting_url.setter
    def meeting_url(self, val: Optional[str]) -> None:
        if self.online_meeting is None:
            self.online_meeting = MeetingLink(url=val)
        else:
            self.online_meeting.url = val

    @property
    def meeting_link(self) -> Optional[str]:
        return self.meeting_url

    @meeting_link.setter
    def meeting_link(self, val: Optional[str]) -> None:
        self.meeting_url = val

    @property
    def video_link(self) -> Optional[str]:
        return self.meeting_url

    @video_link.setter
    def video_link(self, val: Optional[str]) -> None:
        self.meeting_url = val

    @property
    def action_url(self) -> Optional[str]:
        return self.online_meeting.action_url if self.online_meeting else None

    @action_url.setter
    def action_url(self, val: Optional[str]) -> None:
        if self.online_meeting is None:
            self.online_meeting = MeetingLink(action_url=val)
        else:
            self.online_meeting.action_url = val

    @property
    def is_travel(self) -> bool:
        return self.travel.is_travel if self.travel else False

    @is_travel.setter
    def is_travel(self, val: bool) -> None:
        if self.travel is None:
            self.travel = TravelPlan(is_travel=bool(val))
        else:
            self.travel.is_travel = bool(val)

    @property
    def departure_time(self) -> Optional[datetime]:
        return self.travel.departure_time if self.travel else None

    @departure_time.setter
    def departure_time(self, val: Optional[datetime]) -> None:
        if val:
            val = val.astimezone(timezone.utc)
        if self.travel is None:
            self.travel = TravelPlan(departure_time=val)
        else:
            self.travel.departure_time = val

    @property
    def travel_time_minutes(self) -> Optional[int]:
        return self.travel.travel_time_minutes if self.travel else None

    @travel_time_minutes.setter
    def travel_time_minutes(self, val: Optional[int]) -> None:
        if self.travel is None:
            self.travel = TravelPlan(travel_time_minutes=val)
        else:
            self.travel.travel_time_minutes = val

    @property
    def travel_distance_km(self) -> Optional[float]:
        return self.travel.travel_distance_km if self.travel else None

    @travel_distance_km.setter
    def travel_distance_km(self, val: Optional[float]) -> None:
        if self.travel is None:
            self.travel = TravelPlan(travel_distance_km=val)
        else:
            self.travel.travel_distance_km = val

    @property
    def transport_mode(self) -> Optional[str]:
        return self.travel.transport_mode if self.travel else None

    @transport_mode.setter
    def transport_mode(self, val: Optional[str]) -> None:
        if self.travel is None:
            self.travel = TravelPlan(transport_mode=val)
        else:
            self.travel.transport_mode = val

    @property
    def eta_text(self) -> Optional[str]:
        return self.travel.eta_text if self.travel else None

    @eta_text.setter
    def eta_text(self, val: Optional[str]) -> None:
        if self.travel is None:
            self.travel = TravelPlan(eta_text=val)
        else:
            self.travel.eta_text = val

    @property
    def is_arrived(self) -> bool:
        return self.presence.is_arrived if self.presence else False

    @is_arrived.setter
    def is_arrived(self, val: bool) -> None:
        if self.presence is None:
            self.presence = PresenceStatus(is_arrived=bool(val))
        else:
            self.presence.is_arrived = bool(val)

    @property
    def arrival_reason(self) -> Optional[str]:
        return self.presence.arrival_reason if self.presence else None

    @arrival_reason.setter
    def arrival_reason(self, val: Optional[str]) -> None:
        if self.presence is None:
            self.presence = PresenceStatus(arrival_reason=val)
        else:
            self.presence.arrival_reason = val

    @property
    def is_quiet_reminder(self) -> bool:
        return self.presence.is_quiet_reminder if self.presence else False

    @is_quiet_reminder.setter
    def is_quiet_reminder(self, val: bool) -> None:
        if self.presence is None:
            self.presence = PresenceStatus(is_quiet_reminder=bool(val))
        else:
            self.presence.is_quiet_reminder = bool(val)

    @property
    def pilot_type(self) -> str:
        return self.presentation.pilot_type if self.presentation else "duck"

    @pilot_type.setter
    def pilot_type(self, val: str) -> None:
        if self.presentation is None:
            self.presentation = EventPresentation(pilot_type=val)
        else:
            self.presentation.pilot_type = val

    @property
    def theme_name(self) -> str:
        return self.presentation.theme_name if self.presentation else "Sunset Orange"

    @theme_name.setter
    def theme_name(self, val: str) -> None:
        if self.presentation is None:
            self.presentation = EventPresentation(theme_name=val)
        else:
            self.presentation.theme_name = val

    @property
    def action_btn_text(self) -> str:
        return self.presentation.action_btn_text if self.presentation else "📋 OPEN EVENT"

    @action_btn_text.setter
    def action_btn_text(self, val: str) -> None:
        if self.presentation is None:
            self.presentation = EventPresentation(action_btn_text=val)
        else:
            self.presentation.action_btn_text = val

    @property
    def animal(self) -> Optional[str]:
        return self.presentation.animal if self.presentation else None

    @animal.setter
    def animal(self, val: Optional[str]) -> None:
        if self.presentation is None:
            self.presentation = EventPresentation(animal=val)
        else:
            self.presentation.animal = val

    @property
    def outfit(self) -> Optional[str]:
        return self.presentation.outfit if self.presentation else None

    @outfit.setter
    def outfit(self, val: Optional[str]) -> None:
        if self.presentation is None:
            self.presentation = EventPresentation(outfit=val)
        else:
            self.presentation.outfit = val

    @property
    def accessories(self) -> list:
        return list(self.presentation.accessories or []) if self.presentation else []

    @accessories.setter
    def accessories(self, val: Optional[list]) -> None:
        if self.presentation is None:
            self.presentation = EventPresentation(accessories=list(val or []))
        else:
            self.presentation.accessories = list(val or [])

    # --------------------------------------------------------------------------
    # State Machine & Capabilities Integration
    # --------------------------------------------------------------------------

    @property
    def state(self):
        """Resolves active EventState using the state machine."""
        from core.domain.state_machine import resolve_event_state
        return resolve_event_state(self)

    @property
    def capabilities(self):
        """Resolves explicit EventCapabilities for this event."""
        from core.domain.capabilities import EventCapabilities
        has_video = bool(self.meeting_url or (self.action_url and any(k in self.action_url.lower() for k in ["meet.", "zoom.", "teams.", "webex.", "jitsi"])))
        has_nav = bool(self.action_url and any(m in self.action_url.lower() for m in ["maps.apple.com", "google.com/maps", "maps."]))
        has_loc = bool(self.location or self.classroom)
        is_urgent = bool(self.category in ["exam", "travel"] or self.reminder_stage == 0)

        return EventCapabilities(
            can_join=has_video,
            can_navigate=has_nav or has_loc,
            has_location=has_loc,
            needs_travel=bool(self.is_travel),
            can_snooze=True,
            requires_acknowledgement=is_urgent,
            show_arrival_badge=bool(self.is_arrived),
            show_in_call_badge=bool(self.arrival_reason and self.arrival_reason.startswith("call:"))
        )

    # --------------------------------------------------------------------------
    # Dictionary, Indexing, and Serialization Compatibility
    # --------------------------------------------------------------------------

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        """Convert CalendarEvent to dictionary format for backward compatibility and JSON serialization."""
        return {
            "uid": self.uid,
            "title": self.title,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "is_all_day": self.is_all_day,
            "meeting_url": self.meeting_url,
            "location": self.location,
            "description": self.description,
            "event_type": self.event_type,
            "pilot_type": self.pilot_type,
            "provider": self.provider,
            "action_btn_text": self.action_btn_text,
            "action_url": self.action_url,
            "theme_name": self.theme_name,
            "is_travel": self.is_travel,
            "reminder_stage": self.reminder_stage,
            "category": self.category,
            "travel_time_minutes": self.travel_time_minutes,
            "travel_distance_km": self.travel_distance_km,
            "transport_mode": self.transport_mode,
            "departure_time": self.departure_time,
            "origin_address": self.origin_address,
            "eta_text": self.eta_text,
            "classroom": self.classroom,
            "teacher": self.teacher,
            "is_arrived": self.is_arrived,
            "arrival_reason": self.arrival_reason,
            "is_quiet_reminder": self.is_quiet_reminder,
            "animal": self.animal,
            "outfit": self.outfit,
            "accessories": self.accessories
        }

    def to_serializable_dict(self) -> Dict[str, Any]:
        """Convert CalendarEvent to JSON-serializable dictionary with ISO-formatted dates."""
        d = self.to_dict()
        d["start_time"] = self.start_time.isoformat() if self.start_time else None
        d["end_time"] = self.end_time.isoformat() if self.end_time else None
        d["departure_time"] = self.departure_time.isoformat() if self.departure_time else None
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CalendarEvent":
        """Create CalendarEvent from a dictionary, handling both datetime and ISO string formats."""
        start_val = d.get("start_time")
        if isinstance(start_val, str):
            start_dt = datetime.fromisoformat(start_val)
        else:
            start_dt = start_val

        end_val = d.get("end_time")
        if isinstance(end_val, str):
            end_dt = datetime.fromisoformat(end_val)
        else:
            end_dt = end_val

        dep_val = d.get("departure_time")
        if isinstance(dep_val, str):
            dep_dt = datetime.fromisoformat(dep_val)
        else:
            dep_dt = dep_val

        return cls(
            uid=d.get("uid"),
            title=d.get("title", ""),
            start_time=start_dt,
            end_time=end_dt,
            is_all_day=bool(d.get("is_all_day", False)),
            meeting_url=d.get("meeting_url"),
            location=d.get("location", ""),
            description=d.get("description", ""),
            event_type=d.get("event_type", d.get("category", "general")),
            pilot_type=d.get("pilot_type", "duck"),
            provider=d.get("provider", "Reminder ⏰"),
            action_btn_text=d.get("action_btn_text", "📋 OPEN EVENT"),
            action_url=d.get("action_url"),
            theme_name=d.get("theme_name", "Sunset Orange"),
            is_travel=bool(d.get("is_travel", False)),
            reminder_stage=d.get("reminder_stage"),
            category=d.get("category"),
            travel_time_minutes=d.get("travel_time_minutes"),
            travel_distance_km=d.get("travel_distance_km"),
            transport_mode=d.get("transport_mode"),
            departure_time=dep_dt,
            origin_address=d.get("origin_address"),
            eta_text=d.get("eta_text"),
            classroom=d.get("classroom"),
            teacher=d.get("teacher"),
            is_arrived=bool(d.get("is_arrived", False)),
            arrival_reason=d.get("arrival_reason"),
            is_quiet_reminder=bool(d.get("is_quiet_reminder", False)),
            animal=d.get("animal"),
            outfit=d.get("outfit"),
            accessories=d.get("accessories", [])
        )

    def __repr__(self) -> str:
        start_str = self.start_time.isoformat() if self.start_time else "None"
        return f"<CalendarEvent id={self.id!r} title={self.title!r} start={start_str} category={self.category!r}>"


# First-class backward compatibility alias for existing callers and invariant rule
Meeting = CalendarEvent
Event = CalendarEvent
