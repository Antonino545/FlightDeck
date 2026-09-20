"""
Mascot and Outfit Customization Service for FlightDeck.
Extracted from EventClassifier to decouple mascot presentation and accessory
rules from calendar event classification.
"""
from typing import Dict, Any, Optional, Tuple
from .models import Meeting, PilotType

LEGACY_PILOT_MAP: Dict[Tuple[str, str], str] = {
    ("duck", "aviator"): "duck",
    ("duck", "chef"): "chef",
    ("duck", "captain"): "captain",
    ("owl", "student"): "owl",
    ("duck", "gym"): "gym",
    ("duck", "racer"): "driver",
    ("duck", "zen"): "zen_duck",
    ("platypus", "agent"): "platypus",
    ("squirrel", "acorn"): "squirrel"
}

CATEGORY_DEFAULT_OUTFITS: Dict[str, str] = {
    "exam": "student",
    "study": "student",
    "class": "student",
    "food": "chef",
    "travel": "captain",
    "sport": "gym",
    "in_person": "racer",
    "health": "zen",
    "work": "agent",
    "concert": "concert",
    "general": "aviator"
}


def _get_active_config(config_provider: Optional[Any] = None) -> Any:
    """Resolve config provider, falling back to ConfigService singleton."""
    if config_provider is not None:
        return config_provider
    try:
        from core.services.config_service import config
        return config
    except (ImportError, AttributeError):
        return None


class MascotCustomizer:
    """Applies mascot animals, outfits, and accessories to classified Meeting events."""

    def __init__(self, config_provider: Optional[Any] = None):
        self._config_provider = config_provider

    @classmethod
    def get_default_pilot(cls, config_provider: Optional[Any] = None) -> str:
        cfg = _get_active_config(config_provider)
        if cfg is not None:
            try:
                return str(cfg.get("default_pilot", "duck"))
            except (AttributeError, TypeError, KeyError):
                pass
        return "duck"

    @classmethod
    def apply_customization(cls, meeting: Meeting, config_provider: Optional[Any] = None) -> Meeting:
        cfg = _get_active_config(config_provider)
        customs: Dict[str, Any] = {}
        force_default = False
        def_pilot_val = "duck"

        if cfg is not None:
            try:
                raw_customs = cfg.get("mascot_customization")
                if isinstance(raw_customs, dict):
                    customs = raw_customs
                force_default = bool(cfg.get("force_default_pilot", False))
                def_pilot_val = str(cfg.get("default_pilot", "duck"))
            except (AttributeError, TypeError, KeyError):
                pass

        try:
            is_specialized = meeting.pilot_type in (PilotType.PLATYPUS.value, PilotType.SQUIRREL.value)
            cat_key = meeting.event_type or "general"

            if not is_specialized or cat_key != "general":
                custom_val = customs.get(cat_key)
                def_outfit = CATEGORY_DEFAULT_OUTFITS.get(cat_key, "aviator")
                if isinstance(custom_val, dict):
                    meeting.animal = custom_val.get("animal", "duck")
                    meeting.outfit = custom_val.get("outfit", def_outfit)
                    meeting.accessories = list(custom_val.get("accessories", []))
                    if cat_key == "concert" and "headphones" not in meeting.accessories:
                        meeting.accessories.append("headphones")
                    if meeting.animal == "platypus":
                        if "top_hat" in meeting.accessories:
                            meeting.accessories.remove("top_hat")
                        if "fedora" not in meeting.accessories:
                            meeting.accessories.append("fedora")
                    else:
                        while "fedora" in meeting.accessories:
                            meeting.accessories.remove("fedora")
                        if meeting.outfit in ("agent", "tuxedo"):
                            if "top_hat" not in meeting.accessories:
                                meeting.accessories.append("top_hat")
                            if "tuxedo" not in meeting.accessories:
                                meeting.accessories.append("tuxedo")
                    meeting.pilot_type = LEGACY_PILOT_MAP.get(
                        (meeting.animal, meeting.outfit),
                        f"{meeting.animal}_{meeting.outfit}"
                    )
                elif isinstance(custom_val, str) and custom_val:
                    meeting.animal = custom_val
                    meeting.outfit = def_outfit
                    if cat_key == "concert" and "headphones" not in meeting.accessories:
                        meeting.accessories.append("headphones")
                    if meeting.animal == "platypus":
                        if "fedora" not in meeting.accessories:
                            meeting.accessories.append("fedora")
                    elif meeting.outfit in ("agent", "tuxedo"):
                        if "top_hat" not in meeting.accessories:
                            meeting.accessories.append("top_hat")
                        if "tuxedo" not in meeting.accessories:
                            meeting.accessories.append("tuxedo")
                    meeting.pilot_type = LEGACY_PILOT_MAP.get(
                        (meeting.animal, meeting.outfit),
                        f"{meeting.animal}_{meeting.outfit}"
                    )
                elif not meeting.animal:
                    meeting.animal = meeting.pilot_type or "duck"
            elif not meeting.animal:
                meeting.animal = meeting.pilot_type or "duck"

            if force_default:
                meeting.animal = def_pilot_val
                meeting.pilot_type = LEGACY_PILOT_MAP.get(
                    (def_pilot_val, meeting.outfit or "aviator"),
                    f"{def_pilot_val}_{meeting.outfit or 'aviator'}"
                )
        except (AttributeError, KeyError, TypeError, ValueError):
            pass
        return meeting

    def customize(self, meeting: Meeting) -> Meeting:
        """Instance method using the injected config_provider."""
        return self.apply_customization(meeting, config_provider=self._config_provider)
