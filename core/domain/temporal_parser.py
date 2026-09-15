"""
Temporal Qualifier & Status Marker Parser for FlightDeck Event Classification.

Handles stripping of status markers (e.g. "[CANCELLED]") and temporal / ancillary
anchors (e.g. "after dinner", "pre-workout", "on the train", "(was: old title)"),
as well as prefix category detections.
"""
import re
from typing import Dict, Tuple, Optional
from .models import EventCategory

# Status marker prefix regex (e.g. "[CANCELLED] Meeting", "Tentative: Review")
STATUS_MARKER_REGEX = re.compile(
    r'^\s*(?:\[\s*(?:cancelled|canceled|tentative|declined|annullat[oa]|rifiutat[oa])\s*\]|(?:cancelled|canceled|tentative|declined|annullat[oa]|rifiutat[oa])\s*[:\-]\s*)',
    re.IGNORECASE
)

# Idiom overrides: phrases that look like categories (e.g. "lunch and learn") but have fixed mappings
IDIOM_OVERRIDES: Dict[str, EventCategory] = {
    "lunch and learn": EventCategory.GENERAL,
    "coffee chat": EventCategory.IN_PERSON,
    "brown bag session": EventCategory.GENERAL,
}

# Structured food signal (e.g. "table for 4", "reservation at")
STRUCTURED_FOOD_REGEX = re.compile(
    r'\b(?:table for \d+|reservation(?: at| for)?|party of \d+|prenotazione(?: (?:a|al|da|per))?(?: \d+)?)\b',
    re.IGNORECASE
)

# Explicit prefix category words (e.g. "Study: Math", "Volo: Milano")
PREFIX_CATEGORY_WORDS: Dict[str, EventCategory] = {
    "or study": EventCategory.STUDY,
    "self-study": EventCategory.STUDY,
    "self study": EventCategory.STUDY,
    "studio autonomo": EventCategory.STUDY,
    "studio individuale": EventCategory.STUDY,
    "study": EventCategory.STUDY,
    "studio": EventCategory.STUDY,
    "ripasso": EventCategory.STUDY,
    "exam": EventCategory.EXAM,
    "esame": EventCategory.EXAM,
    "appello": EventCategory.EXAM,
    "midterm": EventCategory.EXAM,
    "esonero": EventCategory.EXAM,
    "parziale": EventCategory.EXAM,
    "lecture": EventCategory.CLASS,
    "lezione": EventCategory.CLASS,
    "class": EventCategory.CLASS,
    "corso": EventCategory.CLASS,
    "flight": EventCategory.TRAVEL,
    "volo": EventCategory.TRAVEL,
    "train": EventCategory.TRAVEL,
    "treno": EventCategory.TRAVEL,
    "gym": EventCategory.SPORT,
    "palestra": EventCategory.SPORT,
    "workout": EventCategory.SPORT,
    "allenamento": EventCategory.SPORT,
    "dinner": EventCategory.FOOD,
    "cena": EventCategory.FOOD,
    "lunch": EventCategory.FOOD,
    "pranzo": EventCategory.FOOD,
    "work": EventCategory.WORK,
    "lavoro": EventCategory.WORK,
    "office": EventCategory.WORK,
    "ufficio": EventCategory.WORK,
    "concert": EventCategory.CONCERT,
    "concerto": EventCategory.CONCERT,
    "live": EventCategory.CONCERT,
    "bill": EventCategory.BILL,
    "bills": EventCategory.BILL,
    "bolletta": EventCategory.BILL,
    "bollette": EventCategory.BILL,
    "rent": EventCategory.BILL,
    "affitto": EventCategory.BILL,
    "payment": EventCategory.BILL,
    "pagamento": EventCategory.BILL,
    "invoice": EventCategory.BILL,
    "fattura": EventCategory.BILL,
    "scadenza": EventCategory.BILL,
}

_PREFIX_ALTS = "|".join(re.escape(k) for k in sorted(PREFIX_CATEGORY_WORDS.keys(), key=len, reverse=True))
PREFIX_REGEX = re.compile(rf'^\s*(?P<prefix>{_PREFIX_ALTS})\s*[:\-\–\—]+\s*', re.IGNORECASE)

# Temporal anchor category mapping
ANCHOR_CATEGORY_MAP: Dict[str, EventCategory] = {
    # Food
    "dinner": EventCategory.FOOD,
    "lunch": EventCategory.FOOD,
    "breakfast": EventCategory.FOOD,
    "brunch": EventCategory.FOOD,
    "supper": EventCategory.FOOD,
    "snack": EventCategory.FOOD,
    "coffee": EventCategory.FOOD,
    "drinks": EventCategory.FOOD,
    "cena": EventCategory.FOOD,
    "pranzo": EventCategory.FOOD,
    "colazione": EventCategory.FOOD,
    "merenda": EventCategory.FOOD,
    "spuntino": EventCategory.FOOD,
    "aperitivo": EventCategory.FOOD,
    # Sport
    "gym": EventCategory.SPORT,
    "workout": EventCategory.SPORT,
    "training": EventCategory.SPORT,
    "exercise": EventCategory.SPORT,
    "run": EventCategory.SPORT,
    "running": EventCategory.SPORT,
    "match": EventCategory.SPORT,
    "palestra": EventCategory.SPORT,
    "allenamento": EventCategory.SPORT,
    "corsa": EventCategory.SPORT,
    "partita": EventCategory.SPORT,
    # Academic
    "class": EventCategory.CLASS,
    "classes": EventCategory.CLASS,
    "lecture": EventCategory.CLASS,
    "lesson": EventCategory.CLASS,
    "lezione": EventCategory.CLASS,
    "lezioni": EventCategory.CLASS,
    "corso": EventCategory.CLASS,
    "exam": EventCategory.EXAM,
    "test": EventCategory.EXAM,
    "esame": EventCategory.EXAM,
    # Travel
    "flight": EventCategory.TRAVEL,
    "plane": EventCategory.TRAVEL,
    "train": EventCategory.TRAVEL,
    "volo": EventCategory.TRAVEL,
    "aereo": EventCategory.TRAVEL,
    "treno": EventCategory.TRAVEL,
    # Work
    "work": EventCategory.WORK,
    "office": EventCategory.WORK,
    "lavoro": EventCategory.WORK,
    "ufficio": EventCategory.WORK,
    # Concert
    "concert": EventCategory.CONCERT,
    "concerto": EventCategory.CONCERT,
    # Bills & Rent
    "bill": EventCategory.BILL,
    "bills": EventCategory.BILL,
    "rent": EventCategory.BILL,
    "affitto": EventCategory.BILL,
    "bolletta": EventCategory.BILL,
    "bollette": EventCategory.BILL,
    # Appointments
    "dentist": EventCategory.IN_PERSON,
    "doctor": EventCategory.IN_PERSON,
    "dentista": EventCategory.IN_PERSON,
    "medico": EventCategory.IN_PERSON,
}

LOCATION_SUFFIX_DENYLIST = {
    "room", "hall", "building", "floor", "wing", "aula", "edificio", "center", "centre"
}

_ANCHOR_WORDS_ALTS = "|".join(re.escape(w) for w in sorted(ANCHOR_CATEGORY_MAP.keys(), key=len, reverse=True))
_LOC_GUARD = r'(?!\s+(?:room|hall|building|floor|wing|aula|edificio|center|centre)\b)'

_PREP_WORDS = (
    r'after|before|post|pre|during|until|till|around|between|'
    r'dopo|prima(?:\s+di|\s+del|\s+della|\s+dell\'|\s+dello)?|durante|fino\s+a|verso|tra'
)
_TIME_TOKEN = r'(?:\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s+)?'
_ARTICLES = r'(?:the|il|la|l\'|lo|i|gli|le|del|della|dell\')?'
_SESSION_SUFFIXES = r'(?:\s+(?:session|sessione|slot|block|meeting|call|hour|ora))?'

TRANSIT_ANCHOR_REGEX = re.compile(
    r'\b(?:on(?:\s+the)?|in(?:\s+the)?|sul|su|in)\s+(?:train|flight|plane|treno|volo|aereo)\b',
    re.IGNORECASE
)

STALE_RENAME_REGEX = re.compile(
    r'\((?:was|formerly|ex|previously|old title):[^)]*\)',
    re.IGNORECASE
)

PARENTHETICAL_ANCHOR_REGEX = re.compile(
    rf'\((?:[^)]*\b)?(?:{_PREP_WORDS})\s+{_TIME_TOKEN}{_ARTICLES}\s*(?P<anchor>{_ANCHOR_WORDS_ALTS}){_LOC_GUARD}[^)]*\)',
    re.IGNORECASE
)

HYPHENATED_ANCHOR_REGEX = re.compile(
    rf'\b(?:post|pre)-(?P<anchor>{_ANCHOR_WORDS_ALTS}){_LOC_GUARD}\b',
    re.IGNORECASE
)

PREP_ANCHOR_REGEX = re.compile(
    rf'\b(?:{_PREP_WORDS})\s+{_TIME_TOKEN}{_ARTICLES}\s*(?P<anchor>{_ANCHOR_WORDS_ALTS}){_LOC_GUARD}{_SESSION_SUFFIXES}\b',
    re.IGNORECASE
)


def strip_status_markers(title: str) -> str:
    """Strips leading status markers like 'Cancelled:', '[TENTATIVE]', etc."""
    if not title:
        return ""
    return STATUS_MARKER_REGEX.sub("", title).strip()


def strip_temporal_qualifiers(text: str) -> Tuple[str, Optional[EventCategory]]:
    """Iteratively strips temporal and ancillary anchors from text.
    Returns the core text and the category of the last stripped anchor.
    """
    curr = text
    last_category: Optional[EventCategory] = None

    # 1. Strip stale rename fragments like "(was: Lunch review)"
    curr = STALE_RENAME_REGEX.sub("", curr)

    # 2. Strip transit backdrop phrases like "on train", "during flight"
    if TRANSIT_ANCHOR_REGEX.search(curr):
        curr = TRANSIT_ANCHOR_REGEX.sub("", curr)
        last_category = EventCategory.TRAVEL

    # 3. Iteratively strip temporal anchors until fixpoint
    changed = True
    while changed:
        changed = False
        # Check parenthetical anchors
        m_paren = PARENTHETICAL_ANCHOR_REGEX.search(curr)
        if m_paren:
            anchor_word = m_paren.group("anchor").lower()
            last_category = ANCHOR_CATEGORY_MAP.get(anchor_word, last_category)
            curr = curr[:m_paren.start()] + " " + curr[m_paren.end():]
            changed = True
            continue

        # Check hyphenated anchors
        m_hyph = HYPHENATED_ANCHOR_REGEX.search(curr)
        if m_hyph:
            anchor_word = m_hyph.group("anchor").lower()
            last_category = ANCHOR_CATEGORY_MAP.get(anchor_word, last_category)
            curr = curr[:m_hyph.start()] + " " + curr[m_hyph.end():]
            changed = True
            continue

        # Check standard preposition anchors
        m_prep = PREP_ANCHOR_REGEX.search(curr)
        if m_prep:
            anchor_word = m_prep.group("anchor").lower()
            last_category = ANCHOR_CATEGORY_MAP.get(anchor_word, last_category)
            curr = curr[:m_prep.start()] + " " + curr[m_prep.end():]
            changed = True
            continue

    # Clean trailing commas, hyphens, and normalize whitespace
    cleaned = re.sub(r'[\s,\-]+$', '', curr).strip()
    cleaned = re.sub(r'^\s*[\s,\-]+', '', cleaned).strip()
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)
    return cleaned, last_category
