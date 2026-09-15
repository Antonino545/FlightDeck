"""Shared mascot and accessory catalog for the Hangar and banner renderers."""

ANIMALS = (
    ("duck", "🦆 Duck"),
    ("owl", "🦉 Owl"),
    ("bunny", "🐰 Bunny"),
    ("platypus", "🕵️ Perry the Platypus"),
    ("squirrel", "🐿️ Squirrel"),
    ("fox", "🦊 Fox Strategist"),
    ("penguin", "🐧 Dapper Penguin"),
    ("panda", "🐼 Chill Panda"),
)

ACCESSORIES = (
    "fedora",
    "sunglasses",
    "cap",
    "graduation_cap",
    "crown",
    "pilot_helmet",
    "headphones",
    "aviator_goggles",
    "bow_tie",
    "scarf",
    "briefcase",
    "badge",
    "earpiece",
    "tuxedo",
    "top_hat",
    "banker_visor",
    "gold_coin",
)

LEGACY_OUTFIT_ACCESSORIES = {
    "agent": ("tuxedo",),
    "tuxedo": ("tuxedo", "top_hat"),
    "student": ("graduation_cap",),
    "captain": ("cap",),
    "racer": ("pilot_helmet",),
    "aviator": ("aviator_goggles",),
    "concert": ("headphones",),
    "banker": ("banker_visor", "gold_coin"),
}


def normalize_accessories(outfit=None, accessories=None, animal=None):
    """Return a stable accessory tuple while preserving legacy outfit configs."""
    values = []
    if accessories:
        values.extend(accessories if isinstance(accessories, (list, tuple)) else [accessories])
    clean_outfit = str(outfit or "").lower()
    values.extend(LEGACY_OUTFIT_ACCESSORIES.get(clean_outfit, ()))

    if animal == "platypus":
        # Fedora is strictly reserved for Perry the Platypus on work/agent attire
        if "top_hat" in values:
            values.remove("top_hat")
        if clean_outfit in ("agent", "tuxedo"):
            if "fedora" not in values:
                values.append("fedora")
        elif clean_outfit == "concert":
            while "fedora" in values:
                values.remove("fedora")
    else:
        # Non-platypus animals never wear the fedora; they wear the formal top hat
        while "fedora" in values:
            values.remove("fedora")
        if clean_outfit in ("agent", "tuxedo"):
            if "top_hat" not in values:
                values.append("top_hat")
            if "tuxedo" not in values:
                values.append("tuxedo")

    if clean_outfit == "concert" and "headphones" not in values:
        values.append("headphones")

    return tuple(dict.fromkeys(value for value in values if value in ACCESSORIES))


def animal_label(animal):
    return dict(ANIMALS).get(animal, str(animal).replace("_", " ").title())
