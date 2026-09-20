"""
Event Classification and URL Extraction Engine for FlightDeck.
Pure Python matching logic for video meeting providers, keyword pilots, and travel detection.

Known limitations:
- Natural-language negation of anchors (e.g. "No gym today, doing dinner instead") is not handled.
- Anchor-stripping guarantees apply only to English and Italian; other languages fall back to plain keyword matching.
- Emoji/symbol-only titles (e.g. "🍕 after 🏋️") are not parsed by this classifier version.
"""
import re
import urllib.parse
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List, Union
from .models import Meeting, PilotType, EventCategory
from .mascot_customizer import MascotCustomizer, LEGACY_PILOT_MAP, CATEGORY_DEFAULT_OUTFITS
from .keywords_data import build_default_keywords, ENGLISH_KEYWORDS, ITALIAN_KEYWORDS

# Re-exported domain components for backward compatibility
from .temporal_parser import (
    STATUS_MARKER_REGEX,
    IDIOM_OVERRIDES,
    STRUCTURED_FOOD_REGEX,
    PREFIX_CATEGORY_WORDS,
    PREFIX_REGEX,
    ANCHOR_CATEGORY_MAP,
    LOCATION_SUFFIX_DENYLIST,
    TRANSIT_ANCHOR_REGEX,
    STALE_RENAME_REGEX,
    PARENTHETICAL_ANCHOR_REGEX,
    HYPHENATED_ANCHOR_REGEX,
    PREP_ANCHOR_REGEX,
    strip_status_markers,
    strip_temporal_qualifiers,
)
from .category_theme import (
    CategoryTheme,
    _CALENDAR_FALLBACK,
    _CATEGORY_THEMES,
)
from .classification_rules import (
    MEETING_PATTERNS,
    ClassificationContext,
    ClassificationRule,
    CalendarMappingRule,
    VideoMeetingUrlRule,
    IdiomOverrideRule,
    EmptyCoreTitleFallbackRule,
    PrefixRule,
    StructuredFoodRule,
    FoodStartsWithRule,
    TravelRule,
    AcademicRule,
    SimpleCategoryKeywordRule,
    SpecialMissionPlatypusRule,
    QuickSyncSquirrelRule,
    GenericPhysicalLocationRule,
    CLASSIFICATION_PIPELINE,
)

_LOC_SUFFIX_GUARD = r'(?!\s+(?:room|hall|building|floor|wing|aula|edificio|center|centre)\b)'


def _build_category_regex(keywords: List[str]) -> re.Pattern:
    """Build a single compiled alternation regex for a list of keywords.

    Each keyword is word-boundary delimited and guarded against location-suffix
    false positives (e.g. "Training Room" should not match "training").
    Keywords are sorted longest-first so longer phrases match before shorter
    prefixes (e.g. "self-study" before "study").
    """
    sorted_kws = sorted(keywords, key=len, reverse=True)
    alts = "|".join(re.escape(kw) for kw in sorted_kws)
    return re.compile(
        rf'\b(?:{alts})\b{_LOC_SUFFIX_GUARD}',
        re.IGNORECASE
    )


# Pre-compiled per-category regexes built once at import time from DEFAULT_KEYWORDS.
_DEFAULT_CATEGORY_REGEXES: Dict[str, re.Pattern] = {}


def _rebuild_default_regexes() -> None:
    """(Re)build the default per-category compiled regexes from DEFAULT_KEYWORDS."""
    _DEFAULT_CATEGORY_REGEXES.clear()
    for cat_key, kw_list in DEFAULT_KEYWORDS.items():
        if kw_list:
            _DEFAULT_CATEGORY_REGEXES[cat_key] = _build_category_regex(kw_list)


class _CategoryRegexRegistry:
    """Manages per-category compiled regexes, supporting custom keyword overlays.

    The default regexes are built once at module import from DEFAULT_KEYWORDS.
    When custom_keywords are merged for a specific classify() call, only the
    affected categories get their regex rebuilt for that call's keyword dict.
    """

    @staticmethod
    def get_regex(category: str, keywords_dict: Dict[str, List[str]]) -> Optional[re.Pattern]:
        """Return the compiled regex for *category* within *keywords_dict*."""
        kw_list = keywords_dict.get(category)
        if not kw_list:
            return None
        # Fast path: if the list object is the exact same as the default, use cached regex
        if kw_list is DEFAULT_KEYWORDS.get(category):
            return _DEFAULT_CATEGORY_REGEXES.get(category)
        # Slow path: custom keywords were merged — build a one-off regex
        return _build_category_regex(kw_list)


def category_matches(category: str, text: str, keywords_dict: Dict[str, List[str]]) -> bool:
    """Check whether *text* matches any keyword in *category* using a single .search().

    Uses pre-compiled alternation regex per category. The location-suffix negative
    lookahead is baked into the regex pattern.
    """
    regex = _CategoryRegexRegistry.get_regex(category, keywords_dict)
    if regex is None:
        return False
    return bool(regex.search(text))


_KW_REGEX_CACHE: Dict[str, re.Pattern] = {}  # kept temporarily for _matches_kw backward compat

DEFAULT_KEYWORDS: Dict[str, List[str]] = build_default_keywords()
_rebuild_default_regexes()


class EventClassifier:
    """Classifies raw calendar events into enriched domain Meeting objects."""

    category_matches = staticmethod(category_matches)

    def __init__(self, custom_keywords: Optional[Dict[str, List[str]]] = None,
                 config_provider: Optional[Any] = None):
        self.keywords = custom_keywords or DEFAULT_KEYWORDS
        self.config_provider = config_provider

    def classify_event(self, title: str, location: str = "", description: str = "",
                       meeting_url: Optional[str] = None,
                       custom_keywords: Optional[Dict[str, List[str]]] = None,
                       start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None,
                       calendar_name: Optional[str] = None) -> Meeting:
        """Instance method that classifies an event using this instance's configured keywords and config_provider."""
        merged_kws = dict(self.keywords)
        if custom_keywords:
            merged_kws.update(custom_keywords)
        return self.classify(
            title=title, location=location, description=description,
            meeting_url=meeting_url, custom_keywords=merged_kws,
            start_time=start_time, end_time=end_time,
            calendar_name=calendar_name, config_provider=self.config_provider
        )

    @staticmethod
    def extract_meeting_url(text: Optional[str]) -> Optional[str]:
        """Extract first known video meeting URL from text (notes, description, location)."""
        if not text or not isinstance(text, str) or text == "missing value":
            return None
        for pattern, _, _, _ in MEETING_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    @staticmethod
    def extract_classroom_and_teacher(title: str, location: str = "", description: str = "") -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts university/academic classroom and professor from strings such as:
        'ICT for smart mobility (VASSIO LUCA) - Aula 5M'
        'Sistemi Operativi - Aula 3B (Prof. Rossi)'
        'Room 201', 'Lab 4', 'Edificio B'
        """
        full_text = f"{title} {location} {description}"
        classroom = None
        teacher = None

        # 1. Match Teacher in parentheses e.g. (VASSIO LUCA), (Prof. Mario Rossi)
        teacher_match = re.search(r'\(([A-Z\s\.,\'-]{3,35}|Prof[^\)]+)\)', title)
        if teacher_match:
            cand = teacher_match.group(1).strip()
            if cand.lower() not in ["online", "zoom", "meet", "teams", "remoto", "exam", "oral", "written"]:
                teacher = cand

        # 2. Match Classroom patterns: "Aula 5M", "Aula Magna", "Room 101", "Lab 3", "Edificio 2"
        room_match = re.search(r'\b(Aula\s+[0-9A-Za-z]+|Room\s+[0-9A-Za-z]+|Lab(?:oratorio|\.)?\s+[0-9A-Za-z]+|Edificio\s+[0-9A-Za-z]+|Auditorium\s+[0-9A-Za-z]+)', full_text, re.IGNORECASE)
        if room_match:
            classroom = room_match.group(1).strip()
            classroom = re.sub(r'[\-\(\)\]].*$', '', classroom).strip()

        if not classroom and location and location != "missing value":
            if any(term in location.lower() for term in ["aula", "room", "lab", "campus", "edificio"]):
                classroom = location.strip()

        return classroom, teacher

    @staticmethod
    def _matches_kw(kw: str, text: str) -> bool:
        """Match keyword using word-boundary regex with compiled pattern cache,
        guarding against location suffixes like Room, Hall, Building.
        """
        pattern = _KW_REGEX_CACHE.get(kw)
        if pattern is None:
            pattern = re.compile(
                r'\b' + re.escape(kw) + r'\b(?!\s+(?:room|hall|building|floor|wing|aula|edificio|center|centre)\b)',
                re.IGNORECASE
            )
            _KW_REGEX_CACHE[kw] = pattern
        return bool(pattern.search(text))

    @staticmethod
    def _strip_status_markers(title: str) -> str:
        """Strips leading status markers like 'Cancelled:', '[TENTATIVE]', etc."""
        return strip_status_markers(title)

    @classmethod
    def _strip_temporal_qualifiers(cls, text: str) -> Tuple[str, Optional[EventCategory]]:
        """Iteratively strips temporal and ancillary anchors from text.
        Returns the core text and the category of the last stripped anchor.
        """
        return strip_temporal_qualifiers(text)

    @classmethod
    def _build_meeting(cls, category: EventCategory, title: str, location: str = "", description: str = "",
                       start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                       classroom: Optional[str] = None, teacher: Optional[str] = None,
                       search_blob: str = "", active_url: Optional[str] = None,
                       special_pilot: Optional[str] = None, special_provider: Optional[str] = None,
                       special_btn: Optional[str] = None, special_theme: Optional[str] = None) -> Meeting:
        maps_dest = location if (location and location != "missing value") else title
        now_time = start_time or datetime.now()
        has_loc = bool(location and location != "missing value")
        is_online = "online" in search_blob.lower()

        theme = _CATEGORY_THEMES.get(category)
        if theme is not None:
            # Resolve dynamic fields via the theme's resolver callables
            is_trav = theme.resolve_is_travel(has_loc, is_online, search_blob)
            action_url = theme.resolve_action_url(maps_dest, location, title, classroom, has_loc, is_trav)
            provider = theme.resolve_provider(classroom)
            btn_text = theme.resolve_btn_text(location, classroom, is_trav)
            extra_kwargs = theme.extra_kwargs or {}

            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=category.value, pilot_type=theme.pilot_type,
                provider=provider, action_btn_text=btn_text,
                action_url=action_url, theme_name=theme.theme_name,
                is_travel=is_trav, classroom=classroom, teacher=teacher,
                **extra_kwargs
            )
        else:
            # GENERAL — depends on special_pilot/special_provider/etc. passed by callers
            default_pilot_id = special_pilot or cls._get_default_pilot()
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.GENERAL.value, pilot_type=default_pilot_id,
                provider=special_provider or "Reminder ⏰",
                action_btn_text=special_btn or "📋 OPEN IN CALENDAR",
                action_url="https://calendar.apple.com",
                theme_name=special_theme or "Sunset Orange", is_travel=False,
                classroom=classroom, teacher=teacher
            )

        cls._apply_meeting_url_if_found(m, active_url)
        return cls._apply_forced_pilot_if_needed(m)

    @staticmethod
    def _apply_meeting_url_if_found(meeting: Meeting, active_url: Optional[str]) -> Meeting:
        """If a video meeting URL was extracted, overlay it onto the Meeting's action button.

        The event keeps its category theme, pilot, and provider label — only the
        action button text/URL and meeting_url field are updated so the banner
        shows a clickable "Join" button instead of a generic calendar/maps link.
        """
        if not active_url:
            return meeting
        btn_text = "🚀 JOIN MEETING"
        for pat, _, _, pat_btn in MEETING_PATTERNS:
            if re.search(pat, active_url, re.IGNORECASE):
                btn_text = pat_btn
                break
        meeting.meeting_url = active_url
        meeting.action_url = active_url
        meeting.action_btn_text = btn_text
        return meeting

    @classmethod
    def classify(cls, title: str, location: str = "", description: str = "",
                 meeting_url: Optional[str] = None,
                 custom_keywords: Optional[Dict[str, List[str]]] = None,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 calendar_name: Optional[str] = None,
                 config_provider: Optional[Any] = None) -> Meeting:
        """Classifies an event by inspecting URLs, keywords, location metadata, and calendar mappings."""
        keywords_dict = DEFAULT_KEYWORDS.copy()
        if isinstance(cls, EventClassifier) and hasattr(cls, 'keywords') and cls.keywords:
            keywords_dict.update(cls.keywords)

        category_to_targets = {
            "study": ["owl"],
            "self_study": ["owl"],
            "class": ["class"],
            "lesson": ["class"],
            "exam": ["exam"],
            "food": ["chef"],
            "travel": ["captain"],
            "sport": ["gym"],
            "in_person": ["driver"],
            "health": ["zen_duck"],
            "work": ["work"],
            "concert": ["concert"],
            "bill": ["bill"],
            "bills": ["bill"],
            "rent": ["bill"],
            "affitto": ["bill"],
            "general": ["general"],
        }

        if custom_keywords and isinstance(custom_keywords, dict):
            for k, v in custom_keywords.items():
                if not isinstance(v, list):
                    continue
                targets = category_to_targets.get(k, [k])
                for target in targets:
                    if target in keywords_dict:
                        keywords_dict[target] = list(set(keywords_dict[target] + [kw.lower() for kw in v]))
                    else:
                        keywords_dict[target] = [kw.lower() for kw in v]

        classroom, teacher = cls.extract_classroom_and_teacher(title, location, description)
        raw_blob = f"{title} {location} {description} {meeting_url or ''}"
        search_blob = raw_blob.lower()
        active_url = meeting_url or cls.extract_meeting_url(raw_blob)

        # Strip status markers & extract core title
        clean_title = cls._strip_status_markers(title)
        core_title, last_stripped_cat = cls._strip_temporal_qualifiers(clean_title)

        cleaned_search_blob = cls._strip_temporal_qualifiers(search_blob)[0].lower()
        core_blob = f"{core_title} {location}".lower()
        has_structured_food = bool(
            STRUCTURED_FOOD_REGEX.search(core_title) or STRUCTURED_FOOD_REGEX.search(search_blob)
        )

        ctx = ClassificationContext(
            title=title,
            location=location,
            description=description,
            meeting_url=meeting_url,
            start_time=start_time,
            end_time=end_time,
            calendar_name=calendar_name,
            keywords_dict=keywords_dict,
            classroom=classroom,
            teacher=teacher,
            raw_blob=raw_blob,
            search_blob=search_blob,
            active_url=active_url,
            clean_title=clean_title,
            core_title=core_title,
            last_stripped_cat=last_stripped_cat,
            cleaned_search_blob=cleaned_search_blob,
            core_blob=core_blob,
            has_structured_food=has_structured_food,
            config_provider=config_provider or (getattr(cls, 'config_provider', None) if isinstance(cls, EventClassifier) else None)
        )

        for rule in CLASSIFICATION_PIPELINE:
            res = rule.match(ctx, cls)
            if res is not None:
                return res

        # General Default Meeting / Reminder
        return cls._build_meeting(
            EventCategory.GENERAL, title=title, location=location, description=description,
            start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
            search_blob=search_blob, active_url=active_url
        )

    @classmethod
    def _get_default_pilot(cls) -> str:
        return MascotCustomizer.get_default_pilot()

    @classmethod
    def _apply_forced_pilot_if_needed(cls, meeting: Meeting) -> Meeting:
        return MascotCustomizer.apply_customization(meeting)
