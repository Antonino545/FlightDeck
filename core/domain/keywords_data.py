"""
Bilingual Keyword Lexicon for FlightDeck Event Classification.
Contains base English and Italian keywords per category/pilot.
"""
from typing import Dict, List

ENGLISH_KEYWORDS: Dict[str, List[str]] = {
    "chef": [
        "dinner", "lunch", "breakfast", "brunch", "restaurant", "pizza", "pizzeria", "sushi",
        "barbecue", "bbq", "burger", "food", "eat", "dining", "cocktail", "drinks", "pub",
        "bistro", "cafe", "coffee", "snack", "tasting", "cooking", "supper"
    ],
    "captain": [
        "flight", "airplane", "airport", "boarding", "gate", "terminal", "takeoff", "landing",
        "train", "railway", "station", "subway", "metro", "bus", "shuttle", "pullman", "ferry",
        "cruise", "travel", "trip", "journey", "departure", "transit", "commute", "roadtrip",
        "cab", "taxi", "uber", "lyft", "airline", "ryanair", "easyjet", "wizz", "delta",
        "lufthansa", "british airways"
    ],
    "exam": [
        "exam", "exams", "midterm", "final exam", "oral exam", "written exam",
        "exam prep"
    ],
    "class": [
        "lecture", "classes", "course", "classroom", "seminar", "workshop", "tutorial",
        "lab", "laboratory", "university", "college", "professor", "prof", "academic",
        "smartgrid", "building", "ict", "satellite", "operations research"
    ],
    "owl": [
        "study", "studying", "homework", "assignment", "revision", "self-study", "self study", "selfstudy",
        "or study", "quiz", "thesis", "dissertation", "library", "research", "paper", "reading", "textbook"
    ],
    "gym": [
        "gym", "workout", "fitness", "training", "exercise", "crossfit", "bodybuilding",
        "weights", "cardio", "running", "jogging", "swimming", "pool", "cycling", "bike ride",
        "yoga", "pilates", "football", "soccer", "basketball", "tennis", "padel", "volleyball",
        "boxing", "martial arts", "climbing", "hiking", "treadmill", "stretching", "match"
    ],
    "driver": [
        "doctor", "dr.", "physician", "dentist", "medical", "clinic", "hospital",
        "therapy", "checkup", "appointment", "consultation", "optician", "eye doctor",
        "vet", "veterinarian", "mechanic", "garage", "car inspection", "car wash", "driving",
        "drive", "post office", "bank", "barber", "haircut", "errand"
    ],
    "zen_duck": [
        "meditation", "mindfulness", "wellness", "relax", "spa", "massage", "thermal",
        "sauna", "breathing", "mental health", "counseling", "serenis", "therapy",
        "therapy session", "calm", "retreat", "chill", "nap"
    ],
    "platypus": [
        "secret", "mission", "spy", "agent", "undercover", "confidential",
        "top secret", "perry", "doofenshmirtz", "classified"
    ],
    "squirrel": [
        "brainstorm", "brainstorming", "idea", "quick", "sync", "flash", "agile",
        "standup", "sprint", "retro", "hackathon", "nut", "squirrel", "speed",
        "touchpoint", "huddle"
    ],
    "work": [
        "work", "working", "office", "client", "job", "shift", "shifts", "coworking",
        "business", "company", "colleagues", "standup", "sprint review"
    ],
    "concert": [
        "concert", "concerts", "live music", "festival", "gig", "gigs", "tour", "band",
        "stadium", "arena", "tickets", "ticket"
    ],
    "bill": [
        "rent", "bill", "bills", "invoice", "invoices", "payment", "payments",
        "pay", "subscription", "subscriptions", "mortgage", "tax", "taxes",
        "insurance", "due date", "utility", "utilities", "internet bill"
    ]
}

ITALIAN_KEYWORDS: Dict[str, List[str]] = {
    "chef": [
        "cena", "pranzo", "colazione", "ristorante", "trattoria", "osteria", "aperitivo",
        "apericena", "cibo", "mangiare", "pasticceria", "bar", "degustazione", "focaccia",
        "panino", "spuntino", "mensa"
    ],
    "captain": [
        "volo", "aereo", "aeroporto", "imbarco", "partenza", "treno", "stazione",
        "ferrovia", "frecciarossa", "italo", "regionale", "metropolitana", "navetta",
        "traghetto", "viaggio", "gita", "trasferta", "spostamento", "ita airways"
    ],
    "exam": [
        "esame", "esami", "appello", "parziale", "esonero", "prova scritta",
        "prova orale", "colloquio", "test d'esame", "preparazione esame"
    ],
    "class": [
        "lezione", "lezioni", "corso", "aula", "seminario", "laboratorio", "universit",
        "politecnico", "professore", "docente", "ricerca operativa"
    ],
    "owl": [
        "studio", "studiare", "studio individuale", "studio autonomo", "compiti", "ripasso",
        "tesi", "tesina", "laurea", "biblioteca", "ricerca", "dispense", "esercitazione", "appunti"
    ],
    "gym": [
        "palestra", "allenamento", "pesi", "corsa", "camminata", "nuoto", "piscina", "bici",
        "bicicletta", "calcio", "calcetto", "partita", "partitella", "basket", "pallavolo",
        "tennis", "atletica", "boxe", "maratona", "scalata", "arrampicata", "ginnastica"
    ],
    "driver": [
        "dottore", "medico", "visita", "dentista", "ortodontista", "clinica", "ospedale",
        "controllo", "appuntamento", "consulenza", "oculista", "veterinario", "meccanico",
        "tagliando", "revisione auto", "posta", "banca", "barbiere", "parrucchiere",
        "commissione"
    ],
    "zen_duck": [
        "meditazione", "benessere", "terme", "massaggio", "respirazione", "salute mentale",
        "terapia", "seduta", "riposo", "sonnellino"
    ],
    "platypus": [
        "segreto", "missione", "spia", "agente", "in incognito", "confidenziale", "riservato"
    ],
    "squirrel": [
        "retrospettiva", "allineamento", "confronto", "chiacchierata"
    ],
    "work": [
        "lavoro", "lavorativo", "ufficio", "cliente", "clienti", "turno", "turni",
        "progetto", "riunione di lavoro", "azienda", "aziendale", "colleghi"
    ],
    "concert": [
        "concerto", "concerti", "musica dal vivo", "spettacolo", "palasport",
        "teatro", "opera", "dj set", "biglietti", "biglietto"
    ],
    "bill": [
        "affitto", "affitti", "bolletta", "bollette", "fattura", "fatture",
        "pagamento", "pagamenti", "pagare", "abbonamento", "abbonamenti",
        "mutuo", "tassa", "tasse", "condominio", "assicurazione", "rata", "rate",
        "scadenza", "scadenze", "enel", "luce", "gas", "bolletta luce", "bolletta gas"
    ]
}


def build_default_keywords() -> Dict[str, List[str]]:
    """Build unified DEFAULT_KEYWORDS dictionary merging English and Italian lexicons."""
    all_categories = set(ENGLISH_KEYWORDS.keys()) | set(ITALIAN_KEYWORDS.keys())
    merged: Dict[str, List[str]] = {}
    for cat in all_categories:
        en_list = ENGLISH_KEYWORDS.get(cat, [])
        it_list = ITALIAN_KEYWORDS.get(cat, [])
        # Preserve order: English first, Italian second, deduplicating while preserving order
        seen = set()
        cat_kws = []
        for kw in en_list + it_list:
            kw_clean = kw.strip().lower()
            if kw_clean not in seen:
                seen.add(kw_clean)
                cat_kws.append(kw_clean)
        merged[cat] = cat_kws
    return merged
