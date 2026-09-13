"""
Universal CalDAV / iCalendar (.ics / webcal) Calendar Provider for FlightDeck.
Pure Python calendar provider for Ubuntu/Linux and cross-platform feed sync.
"""
from __future__ import annotations
import os
import re
import html
import urllib.request
import logging
from datetime import datetime, timedelta, timezone, date
from typing import List, Dict, Any, Optional, Tuple
from core.domain.models import Meeting
from core.domain.classifier import EventClassifier
from core.services.config_service import config_service, ConfigService
from .base import BaseCalendarProvider

logger = logging.getLogger("FlightDeck.CalDAVProvider")

class CalDAVCalendarProvider(BaseCalendarProvider):
    """Calendar provider supporting CalDAV endpoints, webcal feeds, and local .ics files."""

    DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

    def __init__(self, config: Optional[ConfigService] = None):
        self.config = config or config_service
        self._feed_cache: Dict[str, str] = {}

    def fetch_events(self, start_offset_hours: int = 2, end_offset_hours: int = 24) -> List[Meeting]:
        """Fetch today's events from configured remote calendar feeds or local .ics files."""
        calendar_sources = list(self.config.get("calendar_urls", []))
        if not calendar_sources:
            # Check default local calendars directory or test ICS
            local_cal_dir = os.path.expanduser("~/.flightdeck/calendars")
            if os.path.isdir(local_cal_dir):
                try:
                    for fname in os.listdir(local_cal_dir):
                        if fname.endswith(".ics"):
                            calendar_sources.append(os.path.join(local_cal_dir, fname))
                except OSError:
                    pass

        if not calendar_sources:
            logger.debug("No CalDAV or local ICS calendar sources configured.")
            return []

        logger.debug("Fetching calendar events from %d CalDAV/ICS sources.", len(calendar_sources))

        meetings: List[Meeting] = []
        ignored = set(self.config.get("ignored_calendars", []))
        custom_kw = self.config.get("custom_keywords", {})
        now = datetime.now()
        today_date = now.date()

        for source in calendar_sources:
            if isinstance(source, dict):
                source_str = str(source.get("url", "")).strip()
                custom_name = str(source.get("name", "")).strip()
            else:
                source_str = str(source).strip()
                custom_name = ""

            if not source_str or source_str in ignored or (custom_name and custom_name in ignored):
                continue

            ics_text = self._load_ics_content(source_str)
            if not ics_text:
                continue

            cal_name = custom_name or self._extract_calendar_name(ics_text, source_str)
            if cal_name in ignored:
                continue

            events = self._parse_ics_events(ics_text)
            for ev in events:
                s_dt = ev.get("start_time")
                e_dt = ev.get("end_time")
                if not s_dt:
                    continue

                title = ev.get("title", "Untitled Event")
                loc = ev.get("location", "")
                desc = ev.get("description", "")
                url_val = ev.get("url", "")
                is_all_day = ev.get("is_all_day", False)
                uid_base = ev.get("uid", "")
                rec_id = ev.get("recurrence_id", "")
                uid = f"{uid_base}_{rec_id}" if rec_id else uid_base

                meeting = EventClassifier.classify(
                    title=title,
                    location=loc,
                    description=desc,
                    meeting_url=(
                        EventClassifier.extract_meeting_url(url_val) or
                        EventClassifier.extract_meeting_url(loc) or
                        EventClassifier.extract_meeting_url(desc)
                    ),
                    custom_keywords=custom_kw,
                    start_time=s_dt,
                    end_time=e_dt or (s_dt + timedelta(hours=1)),
                    calendar_name=cal_name
                )
                meeting.provider = cal_name
                if uid:
                    meeting.uid = uid
                meeting.is_all_day = is_all_day
                if is_all_day and not e_dt:
                    meeting.end_time = s_dt.replace(hour=23, minute=59, second=59)
                meetings.append(meeting)

        meetings.sort(key=lambda m: m.start_time)
        logger.debug("Parsed %d meetings from CalDAV/ICS sources.", len(meetings))
        return meetings

    def get_available_calendars(self) -> List[Dict[str, Any]]:
        """List configured calendar URLs and local sources."""
        sources = self.config.get("calendar_urls", [])
        ignored = set(self.config.get("ignored_calendars", []))
        cals: List[Dict[str, Any]] = []

        for src in sources:
            if isinstance(src, dict):
                url = str(src.get("url", "")).strip()
                name = str(src.get("name", "")).strip() or url.split("/")[-1].replace(".ics", "") or url
            else:
                url = str(src).strip()
                name = url.split("/")[-1].replace(".ics", "") or url
            cals.append({
                "name": name,
                "enabled": name not in ignored and url not in ignored,
                "source": url
            })
        return cals

    def _load_ics_content(self, source: str) -> Optional[str]:
        try:
            if source.startswith("webcal://"):
                source = "https://" + source[len("webcal://"):]

            if source.startswith("http://") or source.startswith("https://"):
                logger.debug("Loading remote calendar source: %s", source)
                req = urllib.request.Request(source, headers={"User-Agent": "FlightDeck/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    content = resp.read().decode("utf-8", errors="ignore")
                    self._feed_cache[source] = content
                    return content
            elif os.path.exists(source):
                logger.debug("Loading local calendar source: %s", source)
                with open(source, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    self._feed_cache[source] = content
                    return content
        except Exception as e:
            if source in self._feed_cache:
                logger.warning(f"Failed to load calendar source {source} ({e}). Serving cached version.")
                return self._feed_cache[source]
            logger.warning(f"Failed to load calendar source {source}: {e}")
        return None

    def _extract_calendar_name(self, ics_text: str, default_source: str) -> str:
        for line in ics_text.splitlines():
            if line.startswith("X-WR-CALNAME:"):
                return line.split(":", 1)[1].strip()
        base = os.path.basename(default_source).replace(".ics", "")
        return base or "Linux Calendar"

    def _parse_ics_events(self, ics_text: str) -> List[Dict[str, Any]]:
        """Parses VEVENT components from raw iCalendar text with RRULE expansion for Today."""
        events = []
        in_event = False
        current_event: Dict[str, Any] = {}

        # Unfold lines according to RFC 5545
        unfolded_lines = []
        for line in ics_text.splitlines():
            if line.startswith(" ") or line.startswith("\t"):
                if unfolded_lines:
                    unfolded_lines[-1] += line[1:]
            else:
                unfolded_lines.append(line)

        for line in unfolded_lines:
            line = line.strip()
            if line == "BEGIN:VALARM":
                in_alarm = True
                continue
            if line == "END:VALARM":
                in_alarm = False
                continue
            if line == "BEGIN:VEVENT":
                in_event = True
                in_alarm = False
                current_event = {}
            elif line == "END:VEVENT":
                if in_event and "title" in current_event and "start_time" in current_event:
                    # Evaluate recurring event for Today
                    if "rrule" in current_event:
                        today_occ = self._expand_rrule_for_today(current_event)
                        if today_occ:
                            events.append(today_occ)
                    else:
                        events.append(current_event)
                in_event = False
            elif in_event and not in_alarm:
                if ":" in line:
                    raw_key, val = line.split(":", 1)
                    key = raw_key.split(";")[0].upper()

                    # Extract TZID parameter if present (e.g. DTSTART;TZID=Europe/Rome:20260907T100000)
                    tzid = None
                    if ";" in raw_key:
                        for param in raw_key.split(";")[1:]:
                            if param.upper().startswith("TZID="):
                                tzid = param.split("=", 1)[1].strip().strip('"\'')

                    if key == "SUMMARY":
                        current_event["title"] = self._unescape_ics(val)
                    elif key == "LOCATION":
                        current_event["location"] = self._unescape_ics(val)
                    elif key == "DESCRIPTION":
                        current_event["description"] = self._unescape_ics(val)
                    elif key == "X-ALT-DESC":
                        alt_description = self._unescape_ics(html.unescape(val))
                        if not current_event.get("description") or current_event["description"] == "This is an event reminder":
                            current_event["description"] = alt_description
                        elif alt_description not in current_event["description"]:
                            current_event["description"] += "\n" + alt_description
                    elif key == "URL":
                        current_event["url"] = val.strip()
                    elif key == "UID":
                        current_event["uid"] = val.strip()
                    elif key == "RECURRENCE-ID":
                        current_event["recurrence_id"] = val.strip()
                    elif key == "RRULE":
                        current_event["rrule"] = val.strip()
                    elif key == "EXDATE":
                        current_event.setdefault("exdates", []).extend([x.strip() for x in val.split(",") if x.strip()])
                    elif key == "DTSTART":
                        dt, is_all_day = self._parse_ics_datetime(val, tzid=tzid)
                        current_event["start_time"] = dt
                        if is_all_day:
                            current_event["is_all_day"] = True
                    elif key == "DTEND":
                        dt, _ = self._parse_ics_datetime(val, tzid=tzid)
                        current_event["end_time"] = dt

        return events

    def _expand_rrule_for_today(self, event: Dict[str, Any], target_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Evaluates RRULE on a VEVENT dictionary to check if an occurrence falls on target_date (default: today).
        Returns a cloned event dictionary for today with updated start_time, end_time, and UID, or None.
        """
        rrule_str = event.get("rrule")
        if not rrule_str:
            return None

        s_dt = event.get("start_time")
        if not s_dt:
            return None

        now = datetime.now().astimezone()
        today = target_date or now.date()

        rrule_params = {}
        for item in rrule_str.split(";"):
            if "=" in item:
                k, v = item.split("=", 1)
                rrule_params[k.strip().upper()] = v.strip().upper()

        freq = rrule_params.get("FREQ")
        if not freq:
            return None

        interval = int(rrule_params.get("INTERVAL", 1))
        byday_str = rrule_params.get("BYDAY")
        until_str = rrule_params.get("UNTIL")
        count = int(rrule_params.get("COUNT", 0)) if "COUNT" in rrule_params else None

        s_local = s_dt.astimezone()
        s_date = s_local.date()

        # 1. Has recurrence started?
        if today < s_date:
            return None

        # 2. Has recurrence expired via UNTIL?
        if until_str:
            until_dt, _ = self._parse_ics_datetime(until_str)
            if until_dt:
                until_date = until_dt.astimezone().date()
                if today > until_date:
                    return None

        # 3. Check EXDATE (exception/cancelled dates)
        exdates = event.get("exdates", [])
        for ex in exdates:
            clean_ex = ex.replace("-", "").replace(":", "")[:8]
            if clean_ex == today.strftime("%Y%m%d"):
                return None

        # 4. Frequency evaluation
        matches = False
        today_weekday_code = self.DAY_CODES[today.weekday()]

        if freq == "WEEKLY":
            if byday_str:
                allowed_days = [re.sub(r'^[+-]?\d+', '', d).strip() for d in byday_str.split(",")]
                if today_weekday_code in allowed_days:
                    weeks_diff = (today - s_date).days // 7
                    if interval <= 1 or (weeks_diff % interval == 0):
                        matches = True
            else:
                if today.weekday() == s_date.weekday():
                    weeks_diff = (today - s_date).days // 7
                    if interval <= 1 or (weeks_diff % interval == 0):
                        matches = True

        elif freq == "DAILY":
            days_diff = (today - s_date).days
            if interval <= 1 or (days_diff % interval == 0):
                matches = True

        elif freq == "MONTHLY":
            if byday_str:
                allowed_days = [re.sub(r'^[+-]?\d+', '', d).strip() for d in byday_str.split(",")]
                if today_weekday_code in allowed_days:
                    months_diff = (today.year - s_date.year) * 12 + (today.month - s_date.month)
                    if interval <= 1 or (months_diff % interval == 0):
                        matches = True
            elif today.day == s_date.day:
                months_diff = (today.year - s_date.year) * 12 + (today.month - s_date.month)
                if interval <= 1 or (months_diff % interval == 0):
                    matches = True

        if not matches:
            return None

        # 5. Check COUNT limit if specified
        if count is not None and count > 0:
            if freq == "DAILY":
                occ_num = ((today - s_date).days // interval) + 1
            elif freq == "WEEKLY":
                occ_num = 0
                cur = s_date
                while cur <= today:
                    c_code = self.DAY_CODES[cur.weekday()]
                    w_diff = (cur - s_date).days // 7
                    if interval <= 1 or (w_diff % interval == 0):
                        if byday_str:
                            allowed_days = [re.sub(r'^[+-]?\d+', '', d).strip() for d in byday_str.split(",")]
                            if c_code in allowed_days:
                                occ_num += 1
                        elif cur.weekday() == s_date.weekday():
                            occ_num += 1
                    cur += timedelta(days=1)
            else:
                occ_num = 1
            if occ_num > count:
                return None

        # 6. Construct today's occurrence
        duration = (event["end_time"] - s_dt) if event.get("end_time") else timedelta(hours=1)
        today_start_local = datetime.combine(today, s_local.time(), tzinfo=s_local.tzinfo)
        today_start_utc = today_start_local.astimezone(timezone.utc)
        today_end_utc = today_start_utc + duration

        clone = dict(event)
        clone["start_time"] = today_start_utc
        clone["end_time"] = today_end_utc
        base_uid = event.get("uid", "event")
        clone["uid"] = f"{base_uid}_rrule_{today.isoformat()}"
        clone["is_recurring"] = True
        return clone

    def _parse_ics_datetime(self, val: str, tzid: Optional[str] = None) -> Tuple[Optional[datetime], bool]:
        val = val.strip()
        tz = None
        if tzid:
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(tzid)
            except Exception:
                tz = None

        try:
            if val.endswith("Z"):
                dt = datetime.strptime(val, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
                return dt, False
            elif "T" in val:
                dt_naive = datetime.strptime(val[:15], "%Y%m%dT%H%M%S")
                if tz:
                    dt = dt_naive.replace(tzinfo=tz)
                else:
                    dt = dt_naive.astimezone()
                return dt.astimezone(timezone.utc), False
            elif len(val) == 8:
                dt_naive = datetime.strptime(val, "%Y%m%d").replace(hour=0, minute=0, second=0)
                if tz:
                    dt = dt_naive.replace(tzinfo=tz)
                else:
                    dt = dt_naive.astimezone()
                return dt.astimezone(timezone.utc), True
        except Exception:
            pass
        return None, False

    def _unescape_ics(self, text: str) -> str:
        text = text.replace(r"\,", ",").replace(r"\;", ";").replace(r"\n", "\n").replace(r"\\", "\\")
        text = re.sub(r"https:\s*//", "https://", text)
        return text.strip()
