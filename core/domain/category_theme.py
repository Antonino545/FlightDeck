"""
Data-driven Category Presentation and Theming for FlightDeck.

Defines CategoryTheme and the canonical _CATEGORY_THEMES mapping table
which dictates mascot pilots, UI themes, action buttons, URLs, and travel
logic for each EventCategory.
"""
import urllib.parse
from typing import Dict, Any, Optional
from .models import Meeting, PilotType, EventCategory

_CALENDAR_FALLBACK = "https://calendar.apple.com"


class CategoryTheme:
    """Per-category presentation theme for Meeting instantiation.

    Instead of an ad-hoc if/elif chain, each category's theme, pilot, provider,
    button text, URL construction, and travel logic are encapsulated here.

    The resolve_* methods contain the exact per-category branching:
      - resolve_is_travel(has_loc, is_online, search_blob) -> bool
      - resolve_action_url(maps_dest, location, title, classroom, has_loc, is_trav) -> str
      - resolve_provider(classroom) -> str
      - resolve_btn_text(location, classroom, is_trav) -> str
    """

    __slots__ = (
        'pilot_type', 'theme_name', '_provider', '_btn_text', '_travel_mode',
        '_url_mode', 'extra_kwargs'
    )

    def __init__(
        self,
        pilot_type: str,
        theme_name: str,
        provider: str,
        btn_text: str,
        travel_mode: str = "always",
        url_mode: str = "q",
        extra_kwargs: Optional[Dict[str, Any]] = None
    ):
        self.pilot_type = pilot_type
        self.theme_name = theme_name
        self._provider = provider
        self._btn_text = btn_text
        self._travel_mode = travel_mode       # "always", "never", "loc_online", "online_only", "loc_only"
        self._url_mode = url_mode             # "q", "daddr", "calendar", "exam", "class", "study", "work", "concert", "bill"
        self.extra_kwargs = extra_kwargs

    # -- is_travel resolver ---------------------------------------------------

    def resolve_is_travel(self, has_loc: bool, is_online: bool, search_blob: str) -> bool:
        if self._travel_mode == "always":
            return True
        elif self._travel_mode == "never":
            return False
        elif self._travel_mode == "loc_online":
            return has_loc and not is_online
        elif self._travel_mode == "online_only":
            return not is_online
        elif self._travel_mode == "loc_only":
            return has_loc
        return False

    # -- action_url resolver --------------------------------------------------

    def resolve_action_url(self, maps_dest: str, location: str, title: str,
                           classroom: Optional[str], has_loc: bool, is_trav: bool) -> str:
        if self._url_mode == "q":
            return f"https://maps.apple.com/?q={urllib.parse.quote(maps_dest)}"
        elif self._url_mode == "daddr":
            return f"https://maps.apple.com/?daddr={urllib.parse.quote(maps_dest)}"
        elif self._url_mode == "calendar":
            return _CALENDAR_FALLBACK
        elif self._url_mode == "exam":
            if is_trav:
                exam_dest = location if has_loc else (f"{title} {classroom or ''}".strip())
                return f"https://maps.apple.com/?q={urllib.parse.quote(exam_dest)}"
            return _CALENDAR_FALLBACK
        elif self._url_mode == "class":
            if is_trav:
                class_dest = location if has_loc else (f"{title} {classroom or ''}".strip())
                return f"https://maps.apple.com/?q={urllib.parse.quote(class_dest)}"
            return _CALENDAR_FALLBACK
        elif self._url_mode == "study":
            return f"https://maps.apple.com/?q={urllib.parse.quote(maps_dest)}" if is_trav else _CALENDAR_FALLBACK
        elif self._url_mode == "work":
            if is_trav:
                work_dest = location if has_loc else title
                return f"https://maps.apple.com/?q={urllib.parse.quote(work_dest)}"
            return _CALENDAR_FALLBACK
        elif self._url_mode == "concert":
            concert_dest = location if has_loc else title
            return f"https://maps.apple.com/?q={urllib.parse.quote(concert_dest)}"
        elif self._url_mode == "bill":
            bill_dest = location if has_loc else ""
            return f"https://maps.apple.com/?q={urllib.parse.quote(bill_dest)}" if bill_dest else _CALENDAR_FALLBACK
        return _CALENDAR_FALLBACK

    # -- provider resolver ----------------------------------------------------

    def resolve_provider(self, classroom: Optional[str]) -> str:
        if "{classroom}" in self._provider:
            if classroom:
                return self._provider.replace("{classroom}", f" {classroom}")
            return self._provider.replace("{classroom}", "")
        return self._provider

    # -- btn_text resolver ----------------------------------------------------

    def resolve_btn_text(self, location: str, classroom: Optional[str], is_trav: bool) -> str:
        if self._btn_text.startswith("IF_TRAV:"):
            parts = self._btn_text[len("IF_TRAV:"):].split("|ELSE:", 1)
            trav_tpl, fallback = parts[0], parts[1]
            if is_trav:
                return trav_tpl.replace("{location}", location or "").replace("{classroom}", classroom or "CAMPUS").replace("{classroom_or_loc}", classroom or "EXAM LOCATION")
            return fallback
        return self._btn_text


_CATEGORY_THEMES: Dict[EventCategory, CategoryTheme] = {
    EventCategory.FOOD: CategoryTheme(
        pilot_type=PilotType.CHEF.value,
        theme_name="Coral Food",
        provider="Dinner / Food 🍕🍽️",
        btn_text="🗺️ RESTAURANT DIRECTIONS",
        travel_mode="always",
        url_mode="q"
    ),
    EventCategory.TRAVEL: CategoryTheme(
        pilot_type=PilotType.CAPTAIN.value,
        theme_name="Sky Captain Blue",
        provider="Flight / Travel ✈️",
        btn_text="🗺️ TRAVEL DIRECTIONS",
        travel_mode="always",
        url_mode="q"
    ),
    EventCategory.EXAM: CategoryTheme(
        pilot_type=PilotType.OWL.value,
        theme_name="Academic Purple",
        provider="Exam 🎓{classroom}",
        btn_text="IF_TRAV:🎓 {classroom_or_loc}|ELSE:🎓 EXAM NOTES",
        travel_mode="online_only",
        url_mode="exam"
    ),
    EventCategory.STUDY: CategoryTheme(
        pilot_type=PilotType.OWL.value,
        theme_name="Academic Purple",
        provider="Study Session 📖",
        btn_text="IF_TRAV:🗺️ {location}|ELSE:⚡ TIME TO STUDY! DO IT 📖",
        travel_mode="loc_online",
        url_mode="study"
    ),
    EventCategory.CLASS: CategoryTheme(
        pilot_type=PilotType.OWL.value,
        theme_name="Academic Purple",
        provider="Class / Lecture 🏫{classroom}",
        btn_text="IF_TRAV:🗺️ {classroom}|ELSE:🏫 CLASSROOM & NOTES",
        travel_mode="loc_online",
        url_mode="class"
    ),
    EventCategory.SPORT: CategoryTheme(
        pilot_type=PilotType.GYM.value,
        theme_name="Athletic Crimson",
        provider="Gym & Sport 🏋️‍♂️💪",
        btn_text="🗺️ GYM DIRECTIONS",
        travel_mode="always",
        url_mode="daddr"
    ),
    EventCategory.IN_PERSON: CategoryTheme(
        pilot_type=PilotType.DRIVER.value,
        theme_name="Racing Green",
        provider="In Person 📍 Travel Time!",
        btn_text="🗺️ NAVIGATE IN MAPS",
        travel_mode="always",
        url_mode="daddr"
    ),
    EventCategory.HEALTH: CategoryTheme(
        pilot_type=PilotType.ZEN_DUCK.value,
        theme_name="Teal Modern",
        provider="Therapy & Wellness 🌸🛋️",
        btn_text="🌸 WELLNESS TIME",
        travel_mode="never",
        url_mode="calendar"
    ),
    EventCategory.WORK: CategoryTheme(
        pilot_type="penguin",
        theme_name="Midnight Slate",
        provider="Work Session 💼",
        btn_text="IF_TRAV:🗺️ {location}|ELSE:💼 OPEN WORK",
        travel_mode="loc_online",
        url_mode="work"
    ),
    EventCategory.CONCERT: CategoryTheme(
        pilot_type="fox",
        theme_name="Sunset Orange",
        provider="Concert & Live 🎸🎵",
        btn_text="IF_TRAV:🎸 {location}|ELSE:🎸 TICKETS & MAPS",
        travel_mode="loc_only",
        url_mode="concert"
    ),
    EventCategory.BILL: CategoryTheme(
        pilot_type="duck",
        theme_name="Mint Green",
        provider="Bill & Payment 💳💰",
        btn_text="💳 PAY BILL",
        travel_mode="never",
        url_mode="bill",
        extra_kwargs={"outfit": "banker"}
    ),
}
# Note: EventCategory.GENERAL is handled dynamically by _build_meeting.
