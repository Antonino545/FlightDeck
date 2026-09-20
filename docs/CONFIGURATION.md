# ⚙️ FlightDeck — Configuration & Custom Rules Guide

FlightDeck stores all user preferences, timing thresholds, routing configurations, and custom keyword rules in:
`~/.flightdeck/config.json`

---

## 📝 Configuration File Reference

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `language` | `string` | `"system"` | Active UI language (`"system"` for OS auto-detection, `"en"` for English, `"it"` for Italian). |
| `meeting_reminder_stages` | `list[int]` | `[20, 10, 5, 2, 0]` | Minutes before an online meeting to trigger the banner notification sequence. |
| `general_reminder_stages` | `list[int]` | `[20, 10, 5, 2, 0]` | Minutes before a general non-travel event to trigger the banner notification sequence. |
| `travel_reminder_stages` | `list[int]` | `[45, 30, 15, 5, 0]` | Minutes before departure to trigger the travel/transit banner notification sequence. |
| `lead_time_meeting_minutes` | `int` | `6` | Legacy trigger threshold (used for fallback compatibility). |
| `lead_time_travel_minutes` | `int` | `35` | Legacy trigger threshold (used for fallback compatibility). |
| `default_snooze_seconds` | `int` | `120` | Duration (in seconds) for the Snooze button (e.g. 120 = 2 min). |
| `flight_speed` | `float` | `3.2` | Flying airplane speed multiplier (2.0 = Relaxed, 3.2 = Standard, 4.8 = Turbo). |
| `banner_position` | `string` | `"top"` | Screen position for the banner (`"top"` or `"bottom"`). |
| `menubar_status_mode` | `string` | `"countdown"` | Default tray display mode (`"countdown"`, `"event_time"`, `"time_only"`, `"icon_only"`). |
| `max_countdown_lookahead_hours`| `int` | `3` | Maximum hours ahead to show live countdown in the menu bar. Events further out show a clean start time. |
| `sound_enabled` | `bool` | `true` | Whether to play a system sound when the banner appears. |
| `sound_name` | `string` | `"Glass"` | System sound name to play (`"Glass"`, `"Hero"`, `"Ping"`, `"Pop"`, `"Submarine"`). |
| `mute_during_lessons` | `bool` | `true` | Automatically mute banner chime when attending a university lecture/lesson or when the event is a class. |
| `enable_bill_reminders` | `bool` | `true` | Periodically send recurring reminders for bills and rent until marked paid or actioned. |
| `bill_reminder_interval_minutes` | `int` | `120` | Interval in minutes between recurring bill reminders (e.g. 30, 60, 120, 240). |
| `ignored_calendars` | `list[str]` | `[...]` | Exact names of calendars to exclude from scanning (e.g., `"Birthdays"`, `"Holidays"`). |
| `calendar_urls` | `list[str]` | `[]` | URLs for remote ICS / CalDAV feeds, used on Linux and Windows. |
| `home_address` | `string` | `""` | Origin street address for ETA calculations (e.g., `"Via Pietro Cossa 11"`). |
| `home_city` | `string` | `""` | Default city/metro area to automatically qualify local addresses (e.g., `"Torino"`). |
| `exam_location` | `string` | `""` | Default campus or university address automatically assigned to all exam events (e.g., `"Politecnico di Torino, Corso Duca degli Abruzzi 24"`). |
| `transport_mode` | `string` | `"transit"` | Default travel mode (`"transit"`, `"automobile"`, `"walking"`, `"bicycling"`). |
| `enable_eta_service` | `bool` | `true` | Whether to calculate departure times and routing links via Apple Maps / Google Maps. |
| `eta_buffer_minutes` | `int` | `10` | Buffer minutes added before departure to account for reaching transit stop/parking. |
| `auto_walking_threshold_km` | `float` | `1.2` | Distance threshold (in km) to automatically suggest/switch to walking route ETA instead of public transit/driving. Set to `0` to disable. |
| `calendar_category_map` | `dict[str, str]` | `{}` | Direct calendar-to-category binding (e.g. `{"Studio": "study", "Work": "work", "Bollette": "bill", "Concerti": "concert"}`). Overrides keyword guessing for events originating from that calendar. |
| `custom_keywords` | `dict` | `{...}` | Custom keyword mappings for event categories (`study`, `class`, `exam`, `bill`, `food`, `travel`, `sport`, `in_person`, `health`, `work`, `concert`, `general`). |
| `mascot_customization` | `dict` | `{...}` | Mascot animal, outfit, and accessory assignments per event category (`study`, `work`, `bill`, `food`, `travel`, `sport`, `in_person`, `health`, `concert`, `general`). |

---

## 📅 Direct Calendar-to-Category Mapping (`calendar_category_map`)

You can connect any calendar source directly to a specific category. When an event originates from a mapped calendar, FlightDeck immediately assigns that category without needing keyword matching heuristics:

```json
{
  "calendar_category_map": {
    "Studio": "study",
    "Lavoro": "work",
    "Concerti & Spettacoli": "concert",
    "Palestra": "sport"
  }
}
```

This mapping can be configured interactively from the **Settings > Connected Calendars** panel via the category dropdown next to each calendar source.

---

## 🏷️ Custom Keyword Rules (`custom_keywords`)

Category keywords can be managed visually directly within the application's **Hangar** tab under each event category card, or edited manually in `~/.flightdeck/config.json`. The Academic category is divided into three distinct subcategories with their own keywords and mascots:

```json
{
  "custom_keywords": {
    "study": [
      "universit", "uni", "politecnico", "tesi", "smartgrid", "ricerca operativa", "studio", "studiare", "focus", "ripasso", "progetto", "homework", "compiti", "laboratorio"
    ],
    "class": [
      "lezione", "lezioni", "corso", "aula", "classe", "lecture", "seminar", "seminario", "workshop"
    ],
    "exam": [
      "esame", "esami", "appello", "parziale", "esonero", "orale", "scritto", "test", "midterm", "final exam"
    ],
    "bill": [
      "affitto", "rent", "bolletta", "bollette", "fattura", "fatture", "invoice", "invoices", "utenze", "utenza", "luce", "gas", "tari", "imu", "f24", "pagamento", "pagare", "scadenza rata", "rata", "rate", "condominio", "spese condominiali", "abbonamento", "revisore", "commercialista"
    ],
    "food": [
      "cena", "pranzo", "dinner", "lunch", "ristorante", "pizza", "pizzeria", "sushi", "aperitivo", "apericena", "osteria", "trattoria", "cibo", "food", "mangiare", "pub", "burger"
    ],
    "travel": [
      "flight", "volo", "airport", "aeroporto", "bus", "navetta", "shuttle", "pullman", "ryanair", "easyjet", "wizz", "ita airways", "treno", "frecciarossa", "italo", "stazione", "viaggio", "partenza", "gate", "terminal", "imbarco", "boarding", "taxi", "uber"
    ],
    "sport": [
      "palestra", "gym", "workout", "allenamento", "crossfit", "fitness", "sport", "padel", "tennis", "calcio", "calcetto", "partita", "match", "nuoto", "swimming", "running", "corsa", "boxe", "boxing", "basket", "pallavolo", "pesi", "cardio", "training", "maratona", "pilates", "atletica"
    ],
    "in_person": [
      "dentista", "dottore", "visita", "medico", "clinica", "ospedale", "appuntamento", "consulenza", "meccanico"
    ],
    "health": [
      "serenis", "terapia", "yoga", "meditazione", "benessere", "relax"
    ],
    "work": [
      "work", "working", "office", "client", "job", "shift", "shifts", "coworking", "business", "company", "colleagues", "standup", "sprint review", "lavoro", "lavorativo", "ufficio", "cliente", "turno", "progetto", "riunione di lavoro"
    ],
    "concert": [
      "concert", "concerts", "live music", "festival", "gig", "gigs", "tour", "band", "stadium", "arena", "tickets", "concerto", "concerti", "musica dal vivo", "spettacolo", "palasport", "teatro", "opera", "dj set", "biglietti"
    ],
    "general": []
  }
}
```

