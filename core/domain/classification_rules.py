"""
Classification Rules Pipeline for FlightDeck Event Classification.

Encapsulates individual classification heuristics into discrete, ordered
rule objects implementing the ClassificationRule interface.
"""
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from .models import Meeting, PilotType, EventCategory
from .temporal_parser import (
    IDIOM_OVERRIDES,
    PREFIX_REGEX,
    PREFIX_CATEGORY_WORDS,
)

# Reference to MEETING_PATTERNS will be imported or passed via classifier_cls/module
MEETING_PATTERNS = [
    (r"https://meet\.google\.com/[a-z0-9-]+", "Google Meet 🟢", "duck", "🚀 JOIN GOOGLE MEET"),
    (r"https://[a-zA-Z0-9-]+\.zoom\.us/[jsw]/[0-9a-zA-Z?=&_-]+", "Zoom Meeting 🔷", "duck", "🚀 JOIN ZOOM MEETING"),
    (r"https://teams\.microsoft\.com/l/meetup-join/[0-9a-zA-Z%?=&_-]+", "Microsoft Teams 🟣", "duck", "🚀 JOIN TEAMS MEETING"),
    (r"https://teams\.live\.com/meet/[0-9a-zA-Z?=&_-]+", "Microsoft Teams 🟣", "duck", "🚀 JOIN TEAMS MEETING"),
    (r"https://[a-zA-Z0-9-]+\.webex\.com/(?:meet|join|wbxmjs)/[0-9a-zA-Z?=&_/\.-]+", "Cisco Webex 🟢", "duck", "🚀 JOIN WEBEX"),
    (r"https://(?:meet\.jit\.si|8x8\.vc)/[0-9a-zA-Z?=&_/\.-]+", "Jitsi Meet 🌐", "duck", "🚀 JOIN JITSI MEET"),
    (r"https://whereby\.com/[0-9a-zA-Z_\.-]+", "Whereby 🌿", "duck", "🚀 JOIN WHEREBY"),
    (r"https://(?:global|app)\.gotomeeting\.com/join/[0-9a-zA-Z?=&_\.-]+", "GoToMeeting 🟠", "duck", "🚀 JOIN GOTOMEETING"),
    (r"https://join\.skype\.com/[0-9a-zA-Z_\.-]+", "Skype 🔵", "duck", "🚀 JOIN SKYPE"),
    (r"https://discord\.(?:com|gg)/(?:channels|invite)/[0-9a-zA-Z/_\.-]+", "Discord 💬", "duck", "🚀 JOIN DISCORD"),
    (r"https://[a-zA-Z0-9-]+\.slack\.com/archives/[0-9a-zA-Z/_\.-]+", "Slack Huddle 📱", "squirrel", "⚡ JOIN SLACK HUDDLE"),
    (r"https://app\.serenis\.it/join/[0-9a-zA-Z_-]+", "Serenis 🛋️", "zen_duck", "🚀 JOIN SESSION")
]


@dataclass
class ClassificationContext:
    """Carries all normalized and extracted context through the classification pipeline."""
    title: str
    location: str
    description: str
    meeting_url: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    calendar_name: Optional[str]
    keywords_dict: Dict[str, List[str]]
    classroom: Optional[str]
    teacher: Optional[str]
    raw_blob: str
    search_blob: str
    active_url: Optional[str]
    clean_title: str
    core_title: str
    last_stripped_cat: Optional[EventCategory]
    cleaned_search_blob: str
    core_blob: str
    has_structured_food: bool
    config_provider: Optional[Any] = None


class ClassificationRule:
    """Base class for an ordered classification step in the rule pipeline."""
    name: str = "base_rule"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        """Inspect context and return a classified Meeting if this rule matches, else None."""
        raise NotImplementedError


class CalendarMappingRule(ClassificationRule):
    name = "calendar_mapping"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if not ctx.calendar_name:
            return None
        cal_map = {}
        if ctx.config_provider is not None:
            try:
                raw_map = ctx.config_provider.get("calendar_category_map", {})
                if isinstance(raw_map, dict):
                    cal_map = raw_map
            except (AttributeError, TypeError, KeyError):
                pass
        else:
            try:
                from core.services.config_service import config
                raw_map = config.get("calendar_category_map", {})
                if isinstance(raw_map, dict):
                    cal_map = raw_map
            except (ImportError, AttributeError, TypeError, KeyError):
                pass

        if cal_map:
            target_cat_str = cal_map.get(ctx.calendar_name)
            if not target_cat_str:
                cal_lower = ctx.calendar_name.strip().lower()
                for k, v in cal_map.items():
                    if k.strip().lower() == cal_lower:
                        target_cat_str = v
                        break
            if target_cat_str:
                try:
                    mapped_category = EventCategory(target_cat_str)
                    return classifier_cls._build_meeting(
                        mapped_category, title=ctx.title, location=ctx.location, description=ctx.description,
                        start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                        search_blob=ctx.search_blob, active_url=ctx.active_url
                    )
                except ValueError:
                    pass
        return None


class VideoMeetingUrlRule(ClassificationRule):
    name = "video_meeting_url"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if not ctx.active_url:
            return None
        for pattern, provider_name, p_type, btn_text in MEETING_PATTERNS:
            if re.search(pattern, ctx.active_url, re.IGNORECASE):
                res_meeting = Meeting(
                    title=ctx.title,
                    start_time=ctx.start_time or datetime.now(),
                    end_time=ctx.end_time,
                    meeting_url=ctx.active_url,
                    location=ctx.location,
                    description=ctx.description,
                    event_type=EventCategory.VIDEO_MEETING.value,
                    pilot_type=p_type,
                    provider=provider_name,
                    action_btn_text=btn_text,
                    action_url=ctx.active_url,
                    theme_name="Teal Modern" if p_type == "zen_duck" else "Sunset Orange",
                    is_travel=False,
                    classroom=ctx.classroom,
                    teacher=ctx.teacher
                )
                return classifier_cls._apply_forced_pilot_if_needed(res_meeting)
        return None


class IdiomOverrideRule(ClassificationRule):
    name = "idiom_override"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        clean_lower = ctx.clean_title.lower()
        for idiom_phrase, target_cat in IDIOM_OVERRIDES.items():
            if idiom_phrase in clean_lower:
                return classifier_cls._build_meeting(
                    target_cat, title=ctx.title, location=ctx.location, description=ctx.description,
                    start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                    search_blob=ctx.search_blob, active_url=ctx.active_url
                )
        return None


class EmptyCoreTitleFallbackRule(ClassificationRule):
    name = "empty_core_title_fallback"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if not ctx.core_title.strip():
            fallback_cat = ctx.last_stripped_cat or EventCategory.GENERAL
            return classifier_cls._build_meeting(
                fallback_cat, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )
        return None


class PrefixRule(ClassificationRule):
    name = "prefix"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        m_prefix = PREFIX_REGEX.match(ctx.clean_title)
        if m_prefix:
            prefix_word = m_prefix.group("prefix").lower()
            prefix_cat = PREFIX_CATEGORY_WORDS.get(prefix_word)
            if prefix_cat:
                if ctx.has_structured_food and prefix_cat != EventCategory.FOOD:
                    return classifier_cls._build_meeting(
                        EventCategory.FOOD, title=ctx.title, location=ctx.location, description=ctx.description,
                        start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                        search_blob=ctx.search_blob, active_url=ctx.active_url
                    )
                return classifier_cls._build_meeting(
                    prefix_cat, title=ctx.title, location=ctx.location, description=ctx.description,
                    start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                    search_blob=ctx.search_blob, active_url=ctx.active_url
                )
        return None


class StructuredFoodRule(ClassificationRule):
    name = "structured_food"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if ctx.has_structured_food:
            return classifier_cls._build_meeting(
                EventCategory.FOOD, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )
        return None


class FoodStartsWithRule(ClassificationRule):
    name = "food_starts_with"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        title_starts_with_food = bool(
            re.search(r'^\s*(?:dinner|lunch|breakfast|brunch|supper|cena|pranzo|colazione|pizza|aperitivo|coffee|drinks|sushi)\b', ctx.core_title, re.IGNORECASE)
        )
        if title_starts_with_food:
            if classifier_cls.category_matches("chef", ctx.core_blob, ctx.keywords_dict) or classifier_cls.category_matches("chef", ctx.cleaned_search_blob, ctx.keywords_dict):
                return classifier_cls._build_meeting(
                    EventCategory.FOOD, title=ctx.title, location=ctx.location, description=ctx.description,
                    start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                    search_blob=ctx.search_blob, active_url=ctx.active_url
                )
        return None


class TravelRule(ClassificationRule):
    name = "travel"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if classifier_cls.category_matches("captain", ctx.core_blob, ctx.keywords_dict) or classifier_cls.category_matches("captain", ctx.cleaned_search_blob, ctx.keywords_dict):
            return classifier_cls._build_meeting(
                EventCategory.TRAVEL, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )
        return None


class AcademicRule(ClassificationRule):
    name = "academic"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        is_facility_or_setup = bool(
            re.search(r'\b(?:booking|setup|check|maintenance|cleaning|inspection)\b', ctx.core_title, re.IGNORECASE)
        )
        is_exam_event = not is_facility_or_setup and (
            classifier_cls.category_matches("exam", ctx.core_blob, ctx.keywords_dict)
            or classifier_cls.category_matches("exam", ctx.cleaned_search_blob, ctx.keywords_dict)
        )
        is_explicit_study_title = classifier_cls.category_matches("owl", ctx.core_title, ctx.keywords_dict)
        if is_exam_event and not is_explicit_study_title:
            return classifier_cls._build_meeting(
                EventCategory.EXAM, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )

        is_study_event = (
            classifier_cls.category_matches("owl", ctx.core_blob, ctx.keywords_dict)
            or classifier_cls.category_matches("owl", ctx.cleaned_search_blob, ctx.keywords_dict)
        )
        has_academic_class_kw = (
            classifier_cls.category_matches("class", ctx.core_blob, ctx.keywords_dict)
            or classifier_cls.category_matches("class", ctx.cleaned_search_blob, ctx.keywords_dict)
        )
        is_class_event = not is_facility_or_setup and (
            bool(ctx.teacher)
            or has_academic_class_kw
            or (bool(ctx.classroom) and bool(re.search(r'\baula\b', ctx.classroom, re.IGNORECASE)))
        )

        if is_study_event:
            return classifier_cls._build_meeting(
                EventCategory.STUDY, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )

        if is_class_event:
            return classifier_cls._build_meeting(
                EventCategory.CLASS, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )
        return None


class SimpleCategoryKeywordRule(ClassificationRule):
    name = "simple_category_keyword"

    def __init__(self, category_key: str, event_category: EventCategory):
        self.category_key = category_key
        self.event_category = event_category

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if classifier_cls.category_matches(self.category_key, ctx.core_blob, ctx.keywords_dict) or classifier_cls.category_matches(self.category_key, ctx.cleaned_search_blob, ctx.keywords_dict):
            return classifier_cls._build_meeting(
                self.event_category, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )
        return None


class SpecialMissionPlatypusRule(ClassificationRule):
    name = "special_mission_platypus"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if classifier_cls.category_matches("platypus", ctx.core_blob, ctx.keywords_dict) or classifier_cls.category_matches("platypus", ctx.cleaned_search_blob, ctx.keywords_dict):
            return classifier_cls._build_meeting(
                EventCategory.GENERAL, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url,
                special_pilot=PilotType.PLATYPUS.value, special_provider="Top Secret Mission 🕵️‍♂️",
                special_btn="🕵️ BRIEFING ACCESS", special_theme="Midnight Slate"
            )
        return None


class QuickSyncSquirrelRule(ClassificationRule):
    name = "quick_sync_squirrel"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if classifier_cls.category_matches("squirrel", ctx.core_blob, ctx.keywords_dict) or classifier_cls.category_matches("squirrel", ctx.cleaned_search_blob, ctx.keywords_dict):
            return classifier_cls._build_meeting(
                EventCategory.GENERAL, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url,
                special_pilot=PilotType.SQUIRREL.value, special_provider="Quick Sync & Brainstorm 🐿️⚡",
                special_btn="🐿️ JOIN HUDDLE", special_theme="Amber Glow"
            )
        return None


class GenericPhysicalLocationRule(ClassificationRule):
    name = "generic_physical_location"

    def match(self, ctx: ClassificationContext, classifier_cls: Any) -> Optional[Meeting]:
        if ctx.location and ctx.location != "missing value" and len(ctx.location.strip()) > 2:
            return classifier_cls._build_meeting(
                EventCategory.IN_PERSON, title=ctx.title, location=ctx.location, description=ctx.description,
                start_time=ctx.start_time, end_time=ctx.end_time, classroom=ctx.classroom, teacher=ctx.teacher,
                search_blob=ctx.search_blob, active_url=ctx.active_url
            )
        return None


CLASSIFICATION_PIPELINE: List[ClassificationRule] = [
    CalendarMappingRule(),
    VideoMeetingUrlRule(),
    IdiomOverrideRule(),
    EmptyCoreTitleFallbackRule(),
    PrefixRule(),
    StructuredFoodRule(),
    FoodStartsWithRule(),
    TravelRule(),
    AcademicRule(),
    SimpleCategoryKeywordRule("chef", EventCategory.FOOD),
    SimpleCategoryKeywordRule("gym", EventCategory.SPORT),
    SimpleCategoryKeywordRule("work", EventCategory.WORK),
    SimpleCategoryKeywordRule("concert", EventCategory.CONCERT),
    SimpleCategoryKeywordRule("bill", EventCategory.BILL),
    SimpleCategoryKeywordRule("driver", EventCategory.IN_PERSON),
    SimpleCategoryKeywordRule("zen_duck", EventCategory.HEALTH),
    SpecialMissionPlatypusRule(),
    QuickSyncSquirrelRule(),
    GenericPhysicalLocationRule(),
]
