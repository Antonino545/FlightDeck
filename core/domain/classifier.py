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

_KW_REGEX_CACHE: Dict[str, re.Pattern] = {}

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

DEFAULT_KEYWORDS = {
    "chef": [
        "dinner", "lunch", "breakfast", "brunch", "restaurant", "pizza", "pizzeria", "sushi",
        "barbecue", "bbq", "burger", "food", "eat", "dining", "cocktail", "drinks", "pub",
        "bistro", "cafe", "coffee", "snack", "tasting", "cooking", "supper",
        "cena", "pranzo", "colazione", "ristorante", "trattoria", "osteria", "aperitivo",
        "apericena", "cibo", "mangiare", "pasticceria", "bar", "degustazione", "focaccia",
        "panino", "spuntino", "mensa"
    ],
    "captain": [
        "flight", "airplane", "airport", "boarding", "gate", "terminal", "takeoff", "landing",
        "train", "railway", "station", "subway", "metro", "bus", "shuttle", "pullman", "ferry",
        "cruise", "travel", "trip", "journey", "departure", "transit", "commute", "roadtrip",
        "cab", "taxi", "uber", "lyft", "airline", "ryanair", "easyjet", "wizz", "delta",
        "lufthansa", "british airways", "volo", "aereo", "aeroporto", "imbarco", "partenza",
        "treno", "stazione", "ferrovia", "frecciarossa", "italo", "regionale", "metropolitana",
        "navetta", "traghetto", "viaggio", "gita", "trasferta", "spostamento", "ita airways"
    ],
    "exam": [
        "exam", "exams", "esame", "esami", "appello", "parziale", "midterm", "final exam",
        "oral exam", "written exam", "esonero", "prova scritta", "prova orale", "colloquio",
        "test d'esame", "exam prep", "preparazione esame"
    ],
    "class": [
        "lecture", "classes", "course", "classroom", "seminar", "workshop", "tutorial",
        "lab", "laboratory", "university", "college", "professor", "prof", "academic",
        "lezione", "lezioni", "corso", "aula", "seminario", "laboratorio", "universit",
        "politecnico", "professore", "docente", "smartgrid", "building", "ict", "satellite",
        "operations research", "ricerca operativa"
    ],
    "owl": [
        "study", "studying", "homework", "assignment", "revision", "self-study", "self study", "selfstudy",
        "or study", "quiz", "thesis", "dissertation", "library", "research", "paper", "reading", "textbook",
        "studio", "studiare", "studio individuale", "studio autonomo", "compiti", "ripasso",
        "tesi", "tesina", "laurea", "biblioteca", "ricerca", "dispense", "esercitazione", "appunti"
    ],
    "gym": [
        "gym", "workout", "fitness", "training", "exercise", "crossfit", "bodybuilding",
        "weights", "cardio", "running", "jogging", "swimming", "pool", "cycling", "bike ride",
        "yoga", "pilates", "football", "soccer", "basketball", "tennis", "padel", "volleyball",
        "boxing", "martial arts", "climbing", "hiking", "treadmill", "stretching", "match",
        "palestra", "allenamento", "pesi", "corsa", "camminata", "nuoto", "piscina", "bici",
        "bicicletta", "calcio", "calcetto", "partita", "partitella", "basket", "pallavolo",
        "tennis", "atletica", "boxe", "maratona", "scalata", "arrampicata", "ginnastica"
    ],
    "driver": [
        "doctor", "dr.", "physician", "dentist", "medical", "clinic", "hospital",
        "therapy", "checkup", "appointment", "consultation", "optician", "eye doctor",
        "vet", "veterinarian", "mechanic", "garage", "car inspection", "car wash", "driving",
        "drive", "post office", "bank", "barber", "haircut", "errand",
        "dottore", "medico", "visita", "dentista", "ortodontista", "clinica", "ospedale",
        "controllo", "appuntamento", "consulenza", "oculista", "veterinario", "meccanico",
        "tagliando", "revisione auto", "posta", "banca", "barbiere", "parrucchiere",
        "commissione"
    ],
    "zen_duck": [
        "meditation", "mindfulness", "wellness", "relax", "spa", "massage", "thermal",
        "sauna", "breathing", "mental health", "counseling", "serenis", "therapy",
        "therapy session", "calm", "retreat", "chill", "meditazione", "benessere",
        "terme", "massaggio", "respirazione", "salute mentale", "terapia", "seduta", "riposo",
        "nap", "sonnellino"
    ],
    "platypus": [
        "secret", "segreto", "mission", "missione", "spy", "spia", "agent", "agente",
        "undercover", "in incognito", "confidential", "confidenziale", "top secret",
        "perry", "doofenshmirtz", "classified", "riservato"
    ],
    "squirrel": [
        "brainstorm", "brainstorming", "idea", "quick", "sync", "flash", "agile",
        "standup", "sprint", "retro", "retrospettiva", "hackathon", "nut", "squirrel",
        "speed", "allineamento", "confronto", "chiacchierata", "touchpoint", "huddle"
    ],
    "work": [
        "work", "working", "office", "client", "job", "shift", "shifts", "coworking",
        "business", "company", "colleagues", "standup", "sprint review", "lavoro", "lavorativo",
        "ufficio", "cliente", "clienti", "turno", "turni", "progetto", "riunione di lavoro",
        "azienda", "aziendale", "colleghi"
    ],
    "concert": [
        "concert", "concerts", "live music", "festival", "gig", "gigs", "tour", "band",
        "stadium", "arena", "tickets", "ticket", "concerto", "concerti", "musica dal vivo",
        "spettacolo", "palasport", "teatro", "opera", "dj set", "biglietti", "biglietto"
    ],
    "bill": [
        "rent", "affitto", "affitti", "bill", "bills", "bolletta", "bollette",
        "invoice", "invoices", "fattura", "fatture", "payment", "payments",
        "pagamento", "pagamenti", "pay", "pagare", "subscription", "subscriptions",
        "abbonamento", "abbonamenti", "mortgage", "mutuo", "tax", "taxes",
        "tassa", "tasse", "condominio", "insurance", "assicurazione",
        "rata", "rate", "scadenza", "scadenze", "due date", "utility", "utilities",
        "enel", "luce", "gas", "internet bill", "bolletta luce", "bolletta gas"
    ]
}

LEGACY_PILOT_MAP = {
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

# 1. Status marker prefix regex (Section 2 Step 1)
STATUS_MARKER_REGEX = re.compile(
    r'^\s*(?:\[\s*(?:cancelled|canceled|tentative|declined|annullat[oa]|rifiutat[oa])\s*\]|(?:cancelled|canceled|tentative|declined|annullat[oa]|rifiutat[oa])\s*[:\-]\s*)',
    re.IGNORECASE
)

# 2. Idiom overrides (Section 2 Step 2)
IDIOM_OVERRIDES: Dict[str, EventCategory] = {
    "lunch and learn": EventCategory.GENERAL,
    "coffee chat": EventCategory.IN_PERSON,
    "brown bag session": EventCategory.GENERAL,
}

# 3. Structured food signal (Section 2 Step 3)
STRUCTURED_FOOD_REGEX = re.compile(
    r'\b(?:table for \d+|reservation(?: at| for)?|party of \d+|prenotazione(?: (?:a|al|da|per))?(?: \d+)?)\b',
    re.IGNORECASE
)

# 4. Explicit prefix category words (Section 2 Step 4)
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

# 5. Temporal anchor category mapping (Section 2 Step 5)
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


class EventClassifier:
    """Classifies raw calendar events into enriched domain Meeting objects."""

    def __init__(self, custom_keywords: Optional[Dict[str, List[str]]] = None):
        self.keywords = custom_keywords or DEFAULT_KEYWORDS

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
        if not title:
            return ""
        return STATUS_MARKER_REGEX.sub("", title).strip()

    @classmethod
    def _strip_temporal_qualifiers(cls, text: str) -> Tuple[str, Optional[EventCategory]]:
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

    @classmethod
    def _build_meeting(cls, category: EventCategory, title: str, location: str = "", description: str = "",
                       start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                       classroom: Optional[str] = None, teacher: Optional[str] = None,
                       search_blob: str = "", active_url: Optional[str] = None,
                       special_pilot: Optional[str] = None, special_provider: Optional[str] = None,
                       special_btn: Optional[str] = None, special_theme: Optional[str] = None) -> Meeting:
        maps_dest = location if (location and location != "missing value") else title
        now_time = start_time or datetime.now()

        if category == EventCategory.FOOD:
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(maps_dest)}"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.FOOD.value, pilot_type=PilotType.CHEF.value,
                provider="Dinner / Food 🍕🍽️", action_btn_text="🗺️ RESTAURANT DIRECTIONS",
                action_url=maps_url, theme_name="Coral Food", is_travel=True,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.TRAVEL:
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(maps_dest)}"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.TRAVEL.value, pilot_type=PilotType.CAPTAIN.value,
                provider="Flight / Travel ✈️", action_btn_text="🗺️ TRAVEL DIRECTIONS",
                action_url=maps_url, theme_name="Sky Captain Blue", is_travel=True,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.EXAM:
            is_trav = "online" not in search_blob.lower()
            exam_dest = location if (location and location != "missing value") else (f"{title} {classroom or ''}".strip())
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(exam_dest)}" if is_trav else "https://calendar.apple.com"
            provider_label = f"Exam 🎓 {classroom}" if classroom else "Exam 🎓"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.EXAM.value, pilot_type=PilotType.OWL.value,
                provider=provider_label,
                action_btn_text=f"🎓 {classroom or 'EXAM LOCATION'}" if is_trav else "🎓 EXAM NOTES",
                action_url=maps_url, theme_name="Academic Purple", is_travel=is_trav,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.STUDY:
            is_trav = bool(location and location != "missing value" and "online" not in search_blob.lower())
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(maps_dest)}" if is_trav else "https://calendar.apple.com"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.STUDY.value, pilot_type=PilotType.OWL.value,
                provider="Study Session 📖",
                action_btn_text=f"🗺️ {location}" if is_trav else "⚡ TIME TO STUDY! DO IT 📖",
                action_url=maps_url, theme_name="Academic Purple", is_travel=is_trav,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.CLASS:
            is_trav = bool(location and location != "missing value" and "online" not in search_blob.lower())
            class_dest = location if is_trav else (f"{title} {classroom or ''}".strip())
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(class_dest)}" if is_trav else "https://calendar.apple.com"
            provider_label = f"Class / Lecture 🏫 {classroom}" if classroom else "Class / Lecture 🏫"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.CLASS.value, pilot_type=PilotType.OWL.value,
                provider=provider_label,
                action_btn_text=f"🗺️ {classroom or 'CAMPUS'}" if is_trav else "🏫 CLASSROOM & NOTES",
                action_url=maps_url, theme_name="Academic Purple", is_travel=is_trav,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.SPORT:
            maps_url = f"https://maps.apple.com/?daddr={urllib.parse.quote(maps_dest)}"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.SPORT.value, pilot_type=PilotType.GYM.value,
                provider="Gym & Sport 🏋️‍♂️💪", action_btn_text="🗺️ GYM DIRECTIONS",
                action_url=maps_url, theme_name="Athletic Crimson", is_travel=True,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.IN_PERSON:
            maps_url = f"https://maps.apple.com/?daddr={urllib.parse.quote(maps_dest)}"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.IN_PERSON.value, pilot_type=PilotType.DRIVER.value,
                provider="In Person 📍 Travel Time!", action_btn_text="🗺️ NAVIGATE IN MAPS",
                action_url=maps_url, theme_name="Racing Green", is_travel=True,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.HEALTH:
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.HEALTH.value, pilot_type=PilotType.ZEN_DUCK.value,
                provider="Therapy & Wellness 🌸🛋️", action_btn_text="🌸 WELLNESS TIME",
                action_url="https://calendar.apple.com", theme_name="Teal Modern", is_travel=False,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.WORK:
            is_trav = bool(location and location != "missing value" and "online" not in search_blob.lower())
            work_dest = location if is_trav else title
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(work_dest)}" if is_trav else "https://calendar.apple.com"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.WORK.value, pilot_type="penguin",
                provider="Work Session 💼",
                action_btn_text=f"🗺️ {location}" if is_trav else "💼 OPEN WORK",
                action_url=maps_url, theme_name="Midnight Slate", is_travel=is_trav,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.CONCERT:
            is_trav = bool(location and location != "missing value")
            concert_dest = location if is_trav else title
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(concert_dest)}"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.CONCERT.value, pilot_type="fox",
                provider="Concert & Live 🎸🎵",
                action_btn_text=f"🎸 {location}" if is_trav else "🎸 TICKETS & MAPS",
                action_url=maps_url, theme_name="Sunset Orange", is_travel=True,
                classroom=classroom, teacher=teacher
            )
        elif category == EventCategory.BILL:
            bill_dest = location if (location and location != "missing value") else ""
            maps_url = f"https://maps.apple.com/?q={urllib.parse.quote(bill_dest)}" if bill_dest else "https://calendar.apple.com"
            m = Meeting(
                title=title, start_time=now_time, end_time=end_time,
                location=location, description=description,
                event_type=EventCategory.BILL.value, pilot_type="duck",
                provider="Bill & Payment 💳💰",
                action_btn_text="💳 PAY BILL",
                action_url=maps_url, theme_name="Mint Green", is_travel=False,
                classroom=classroom, teacher=teacher, outfit="banker"
            )
        else:  # GENERAL
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
                 calendar_name: Optional[str] = None) -> Meeting:
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

        # Check calendar-to-category mapping direct override
        if calendar_name:
            try:
                from core.services.config_service import config
                cal_map = config.get("calendar_category_map", {})
                if isinstance(cal_map, dict):
                    target_cat_str = cal_map.get(calendar_name)
                    if not target_cat_str:
                        cal_lower = calendar_name.strip().lower()
                        for k, v in cal_map.items():
                            if k.strip().lower() == cal_lower:
                                target_cat_str = v
                                break
                    if target_cat_str:
                        try:
                            mapped_category = EventCategory(target_cat_str)
                            return cls._build_meeting(
                                mapped_category, title=title, location=location, description=description,
                                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                                search_blob=search_blob, active_url=active_url
                            )
                        except ValueError:
                            pass
            except Exception:
                pass
        if active_url:
            for pattern, provider_name, p_type, btn_text in MEETING_PATTERNS:
                if re.search(pattern, active_url, re.IGNORECASE):
                    res_meeting = Meeting(
                        title=title,
                        start_time=start_time or datetime.now(),
                        end_time=end_time,
                        meeting_url=active_url,
                        location=location,
                        description=description,
                        event_type=EventCategory.VIDEO_MEETING.value,
                        pilot_type=p_type,
                        provider=provider_name,
                        action_btn_text=btn_text,
                        action_url=active_url,
                        theme_name="Teal Modern" if p_type == "zen_duck" else "Sunset Orange",
                        is_travel=False,
                        classroom=classroom,
                        teacher=teacher
                    )
                    return cls._apply_forced_pilot_if_needed(res_meeting)

        # Step 1: Strip status markers
        clean_title = cls._strip_status_markers(title)

        # Step 2: Idiom overrides (checked before prefix and anchor logic)
        clean_lower = clean_title.lower()
        for idiom_phrase, target_cat in IDIOM_OVERRIDES.items():
            if idiom_phrase in clean_lower:
                return cls._build_meeting(
                    target_cat, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Step 5: Iteratively strip temporal and ancillary anchors
        core_title, last_stripped_cat = cls._strip_temporal_qualifiers(clean_title)

        # Step 6: Fallback when masking empties the title
        if not core_title.strip():
            fallback_cat = last_stripped_cat or EventCategory.GENERAL
            return cls._build_meeting(
                fallback_cat, title=title, location=location, description=description,
                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                search_blob=search_blob, active_url=active_url
            )

        # Step 3: Structured-signal override (beats explicit prefix when they conflict)
        has_structured_food = bool(
            STRUCTURED_FOOD_REGEX.search(core_title) or STRUCTURED_FOOD_REGEX.search(search_blob)
        )

        # Step 4: Explicit Title Prefix Recognition (tightened closed vocabulary)
        m_prefix = PREFIX_REGEX.match(clean_title)
        if m_prefix:
            prefix_word = m_prefix.group("prefix").lower()
            prefix_cat = PREFIX_CATEGORY_WORDS.get(prefix_word)
            if prefix_cat:
                if has_structured_food and prefix_cat != EventCategory.FOOD:
                    return cls._build_meeting(
                        EventCategory.FOOD, title=title, location=location, description=description,
                        start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                        search_blob=search_blob, active_url=active_url
                    )
                return cls._build_meeting(
                    prefix_cat, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        if has_structured_food:
            return cls._build_meeting(
                EventCategory.FOOD, title=title, location=location, description=description,
                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                search_blob=search_blob, active_url=active_url
            )

        # Step 7: Core keyword matching on core_title and cleaned_search_blob
        cleaned_search_blob = cls._strip_temporal_qualifiers(search_blob)[0].lower()
        core_blob = f"{core_title} {location}".lower()

        title_starts_with_food = bool(
            re.search(r'^\s*(?:dinner|lunch|breakfast|brunch|supper|cena|pranzo|colazione|pizza|aperitivo|coffee|drinks|sushi)\b', core_title, re.IGNORECASE)
        )

        if title_starts_with_food:
            for kw in keywords_dict.get("chef", []):
                if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                    return cls._build_meeting(
                        EventCategory.FOOD, title=title, location=location, description=description,
                        start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                        search_blob=search_blob, active_url=active_url
                    )

        # Check Travel / Flights / Airport / Trains
        for kw in keywords_dict.get("captain", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.TRAVEL, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Exam / Esame
        is_facility_or_setup = bool(
            re.search(r'\b(?:booking|setup|check|maintenance|cleaning|inspection)\b', core_title, re.IGNORECASE)
        )
        is_exam_event = not is_facility_or_setup and (
            any(cls._matches_kw(kw, core_blob) for kw in keywords_dict.get("exam", []))
            or any(cls._matches_kw(kw, cleaned_search_blob) for kw in keywords_dict.get("exam", []))
        )
        is_explicit_study_title = any(
            cls._matches_kw(kw, core_title) for kw in keywords_dict.get("owl", [])
        )
        if is_exam_event and not is_explicit_study_title:
            return cls._build_meeting(
                EventCategory.EXAM, title=title, location=location, description=description,
                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                search_blob=search_blob, active_url=active_url
            )

        # Check Self-Study Block vs Class / Lecture Attendance
        is_study_event = (
            any(cls._matches_kw(kw, core_blob) for kw in keywords_dict.get("owl", []))
            or any(cls._matches_kw(kw, cleaned_search_blob) for kw in keywords_dict.get("owl", []))
        )
        has_academic_class_kw = (
            any(cls._matches_kw(kw, core_blob) for kw in keywords_dict.get("class", []))
            or any(cls._matches_kw(kw, cleaned_search_blob) for kw in keywords_dict.get("class", []))
        )
        is_class_event = not is_facility_or_setup and (
            bool(teacher)
            or has_academic_class_kw
            or (bool(classroom) and bool(re.search(r'\baula\b', classroom, re.IGNORECASE)))
        )

        if is_study_event:
            return cls._build_meeting(
                EventCategory.STUDY, title=title, location=location, description=description,
                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                search_blob=search_blob, active_url=active_url
            )

        if is_class_event:
            return cls._build_meeting(
                EventCategory.CLASS, title=title, location=location, description=description,
                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                search_blob=search_blob, active_url=active_url
            )

        # Check Food if not checked earlier
        for kw in keywords_dict.get("chef", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.FOOD, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Gym / Sport / Workout
        for kw in keywords_dict.get("gym", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.SPORT, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Work / Lavoro
        for kw in keywords_dict.get("work", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.WORK, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Concert / Live Music
        for kw in keywords_dict.get("concert", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.CONCERT, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Bills / Rent / Affitto / Payments
        for kw in keywords_dict.get("bill", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.BILL, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check In-Person Appointments / Driver
        for kw in keywords_dict.get("driver", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.IN_PERSON, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Therapy / Zen Duck / Health
        for kw in keywords_dict.get("zen_duck", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.HEALTH, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url
                )

        # Check Secret Mission / Platypus
        for kw in keywords_dict.get("platypus", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.GENERAL, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url,
                    special_pilot=PilotType.PLATYPUS.value, special_provider="Top Secret Mission 🕵️‍♂️",
                    special_btn="🕵️ BRIEFING ACCESS", special_theme="Midnight Slate"
                )

        # Check Quick Sync / Squirrel
        for kw in keywords_dict.get("squirrel", []):
            if cls._matches_kw(kw, core_blob) or cls._matches_kw(kw, cleaned_search_blob):
                return cls._build_meeting(
                    EventCategory.GENERAL, title=title, location=location, description=description,
                    start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                    search_blob=search_blob, active_url=active_url,
                    special_pilot=PilotType.SQUIRREL.value, special_provider="Quick Sync & Brainstorm 🐿️⚡",
                    special_btn="🐿️ JOIN HUDDLE", special_theme="Amber Glow"
                )

        # Generic Physical Event (if non-empty location)
        if location and location != "missing value" and len(location.strip()) > 2:
            return cls._build_meeting(
                EventCategory.IN_PERSON, title=title, location=location, description=description,
                start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
                search_blob=search_blob, active_url=active_url
            )

        # General Default Meeting / Reminder
        return cls._build_meeting(
            EventCategory.GENERAL, title=title, location=location, description=description,
            start_time=start_time, end_time=end_time, classroom=classroom, teacher=teacher,
            search_blob=search_blob, active_url=active_url
        )

    @classmethod
    def _get_default_pilot(cls) -> str:
        try:
            from core.services.config_service import config
            return str(config.get("default_pilot", "duck"))
        except Exception:
            return "duck"

    @classmethod
    def _apply_forced_pilot_if_needed(cls, meeting: Meeting) -> Meeting:
        try:
            from core.services.config_service import config
            customs = config.get("mascot_customization")
            if not isinstance(customs, dict):
                customs = {}

            is_specialized = meeting.pilot_type in (PilotType.PLATYPUS.value, PilotType.SQUIRREL.value)
            cat_key = meeting.event_type or "general"

            CATEGORY_DEFAULT_OUTFITS = {
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

            if config.get("force_default_pilot", False):
                def_pilot = str(config.get("default_pilot", "duck"))
                meeting.animal = def_pilot
                meeting.pilot_type = LEGACY_PILOT_MAP.get(
                    (def_pilot, meeting.outfit or "aviator"),
                    f"{def_pilot}_{meeting.outfit or 'aviator'}"
                )
        except Exception:
            pass
        return meeting

