"""
SQLite Local State Storage Engine (flightdeck.db).
Consolidates scattered JSON cache files into a single, ACID-compliant SQLite database
with WAL journal mode, thread safety, and transparent legacy migration.
"""
import os
import json
import sqlite3
import threading
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple

logger = logging.getLogger("FlightDeck.DatabaseService")

DEFAULT_DB_PATH = os.path.expanduser("~/.flightdeck/flightdeck.db")
LEGACY_DB_PATH = os.path.expanduser("~/.flightdeck/flightdeck.db")


class DatabaseService:
    """Thread-safe SQLite storage service with automatic schema migration and JSON import."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = DEFAULT_DB_PATH):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DatabaseService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        if self._initialized:
            return
        self.db_path = db_path
        self._local = threading.local()
        self._write_lock = threading.Lock()
        self._init_db()
        self._migrate_legacy_json()
        self._initialized = True

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            try:
                if self.db_path != ":memory:":
                    os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
                    if self.db_path == DEFAULT_DB_PATH and not os.path.exists(self.db_path) and os.path.exists(LEGACY_DB_PATH):
                        try:
                            import shutil
                            shutil.copy2(LEGACY_DB_PATH, self.db_path)
                            logger.info("Migrated legacy database from %s to %s", LEGACY_DB_PATH, self.db_path)
                        except Exception as db_mig_err:
                            logger.warning("Could not copy legacy database: %s", db_mig_err)
                conn = sqlite3.connect(self.db_path, timeout=15.0, check_same_thread=False)
            except Exception as e:
                logger.warning(f"Could not open SQLite database at {self.db_path}, using in-memory: {e}")
                self.db_path = ":memory:"
                conn = sqlite3.connect(":memory:", timeout=15.0, check_same_thread=False)

            conn.row_factory = sqlite3.Row
            # Enable WAL mode for file-based database
            if self.db_path != ":memory:":
                try:
                    conn.execute("PRAGMA journal_mode = WAL;")
                    conn.execute("PRAGMA synchronous = NORMAL;")
                except Exception as e:
                    logger.debug("Could not set WAL pragma: %s", e)
            self._local.conn = conn
        return self._local.conn

    def _init_db(self) -> None:
        """Initializes tables and indices."""
        with self._write_lock:
            conn = self._get_connection()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        uid TEXT PRIMARY KEY,
                        title TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        location TEXT,
                        meeting_url TEXT,
                        is_travel INTEGER DEFAULT 0,
                        payload_json TEXT,
                        updated_at TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_time);")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS notified_stages (
                        key TEXT PRIMARY KEY,
                        notified_at TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_notified_at ON notified_stages(notified_at);")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS banner_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT,
                        title TEXT,
                        stage INTEGER,
                        pilot_type TEXT,
                        provider TEXT,
                        status TEXT,
                        created_at TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS eta_cache (
                        cache_key TEXT PRIMARY KEY,
                        origin TEXT,
                        destination TEXT,
                        mode TEXT,
                        duration_min INTEGER,
                        distance_km REAL,
                        updated_at TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS address_cache (
                        query TEXT PRIMARY KEY,
                        canonical_name TEXT,
                        lat REAL,
                        lon REAL,
                        updated_at TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS bill_payments (
                        event_id TEXT PRIMARY KEY,
                        paid_at TEXT,
                        notes TEXT
                    );
                """)

    def _migrate_legacy_json(self) -> None:
        """One-time migration importing existing data from legacy JSON files."""
        base_dir = os.path.dirname(self.db_path)

        # 1. Migrate notified_stages.json
        notified_path = os.path.join(base_dir, "notified_stages.json")
        if os.path.exists(notified_path):
            try:
                with open(notified_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    with self._write_lock, self._get_connection() as conn:
                        for k, v in data.items():
                            conn.execute(
                                "INSERT OR REPLACE INTO notified_stages (key, notified_at) VALUES (?, ?);",
                                (k, str(v))
                            )
                logger.info("Migrated legacy notified_stages.json into SQLite.")
                os.replace(notified_path, notified_path + ".bak")
            except Exception as e:
                logger.warning("Failed migrating notified_stages.json: %s", e)

        # 2. Migrate banner_history.json
        history_path = os.path.join(base_dir, "banner_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                if isinstance(history, list):
                    with self._write_lock, self._get_connection() as conn:
                        for r in history:
                            conn.execute("""
                                INSERT INTO banner_history (event_id, title, stage, pilot_type, provider, status, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?);
                            """, (
                                str(r.get("event_id") or ""),
                                str(r.get("title") or ""),
                                r.get("stage"),
                                str(r.get("pilot_type") or "duck"),
                                str(r.get("provider") or ""),
                                str(r.get("status") or "sent"),
                                str(r.get("created_at") or r.get("timestamp") or datetime.now(timezone.utc).isoformat())
                            ))
                logger.info("Migrated legacy banner_history.json into SQLite.")
                os.replace(history_path, history_path + ".bak")
            except Exception as e:
                logger.warning("Failed migrating banner_history.json: %s", e)

        # 3. Migrate eta_cache.json
        eta_path = os.path.join(base_dir, "eta_cache.json")
        if os.path.exists(eta_path):
            try:
                with open(eta_path, "r", encoding="utf-8") as f:
                    etas = json.load(f)
                if isinstance(etas, dict):
                    with self._write_lock, self._get_connection() as conn:
                        for k, v in etas.items():
                            if isinstance(v, dict):
                                conn.execute("""
                                    INSERT OR REPLACE INTO eta_cache (cache_key, origin, destination, mode, duration_min, distance_km, updated_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?);
                                """, (
                                    k,
                                    str(v.get("origin") or ""),
                                    str(v.get("destination") or ""),
                                    str(v.get("mode") or "transit"),
                                    v.get("duration_minutes") or v.get("duration_min") or 0,
                                    v.get("distance_km") or 0.0,
                                    str(v.get("updated_at") or datetime.now(timezone.utc).isoformat())
                                ))
                logger.info("Migrated legacy eta_cache.json into SQLite.")
                os.replace(eta_path, eta_path + ".bak")
            except Exception as e:
                logger.warning("Failed migrating eta_cache.json: %s", e)

    # --------------------------------------------------------------------------
    # Notified Stages Operations
    # --------------------------------------------------------------------------

    def get_notified_keys(self) -> Set[str]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT key FROM notified_stages;")
        return {row["key"] for row in cursor.fetchall()}

    def record_notified_key(self, key: str, notified_at: Optional[str] = None) -> None:
        ts = notified_at or datetime.now(timezone.utc).isoformat()
        with self._write_lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO notified_stages (key, notified_at) VALUES (?, ?);",
                (key, ts)
            )

    def remove_notified_key(self, key: str) -> None:
        with self._write_lock, self._get_connection() as conn:
            conn.execute("DELETE FROM notified_stages WHERE key = ?;", (key,))

    def clear_notified_keys(self) -> None:
        with self._write_lock, self._get_connection() as conn:
            conn.execute("DELETE FROM notified_stages;")

    def prune_notified_keys(self, max_age_hours: int = 24) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
        with self._write_lock, self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM notified_stages WHERE notified_at < ?;", (cutoff,))
            return cursor.rowcount

    # --------------------------------------------------------------------------
    # Bill Payment Operations
    # --------------------------------------------------------------------------

    def record_bill_paid(self, event_id: str, paid_at: Optional[str] = None, notes: Optional[str] = None) -> None:
        ts = paid_at or datetime.now(timezone.utc).isoformat()
        with self._write_lock, self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO bill_payments (event_id, paid_at, notes) VALUES (?, ?, ?);",
                (event_id, ts, notes)
            )

    def is_bill_paid(self, event_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.execute("SELECT 1 FROM bill_payments WHERE event_id = ?;", (event_id,))
        return cursor.fetchone() is not None

    def remove_bill_paid(self, event_id: str) -> None:
        with self._write_lock, self._get_connection() as conn:
            conn.execute("DELETE FROM bill_payments WHERE event_id = ?;", (event_id,))

    def get_all_paid_bills(self) -> Set[str]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT event_id FROM bill_payments;")
        return {row["event_id"] for row in cursor.fetchall()}

    # --------------------------------------------------------------------------
    # Banner History Operations
    # --------------------------------------------------------------------------

    def record_banner_history(
        self,
        event_id: str,
        title: str,
        stage: Optional[int],
        pilot_type: str = "duck",
        provider: str = "",
        status: str = "sent"
    ) -> int:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._write_lock, self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO banner_history (event_id, title, stage, pilot_type, provider, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (event_id, title, stage, pilot_type, provider, status, now_iso))
            return cursor.lastrowid

    def get_banner_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM banner_history ORDER BY id DESC LIMIT ?;",
            (limit,)
        )
        return [dict(row) for row in cursor.fetchall()]

    # --------------------------------------------------------------------------
    # ETA Cache Operations
    # --------------------------------------------------------------------------

    def get_eta(self, cache_key: str, max_age_seconds: int = 300) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM eta_cache WHERE cache_key = ?;",
            (cache_key,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        # Age check
        updated_at_str = row["updated_at"]
        try:
            updated_dt = datetime.fromisoformat(updated_at_str)
            if updated_dt.tzinfo is None:
                updated_dt = updated_dt.astimezone(timezone.utc)
            age = (datetime.now(timezone.utc) - updated_dt).total_seconds()
            if age > max_age_seconds:
                return None
        except Exception:
            pass

        return {
            "duration_minutes": row["duration_min"],
            "distance_km": row["distance_km"],
            "mode": row["mode"],
            "origin": row["origin"],
            "destination": row["destination"],
            "updated_at": row["updated_at"]
        }

    def set_eta(
        self,
        cache_key: str,
        origin: str,
        destination: str,
        mode: str,
        duration_min: int,
        distance_km: float = 0.0
    ) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._write_lock, self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO eta_cache (cache_key, origin, destination, mode, duration_min, distance_km, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (cache_key, origin, destination, mode, duration_min, distance_km, now_iso))

    # --------------------------------------------------------------------------
    # Address Cache Operations
    # --------------------------------------------------------------------------

    def get_address(self, query: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM address_cache WHERE query = ?;",
            (query.lower().strip(),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "canonical_name": row["canonical_name"],
            "lat": row["lat"],
            "lon": row["lon"],
            "updated_at": row["updated_at"]
        }

    def set_address(self, query: str, canonical_name: str, lat: float, lon: float) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._write_lock, self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO address_cache (query, canonical_name, lat, lon, updated_at)
                VALUES (?, ?, ?, ?, ?);
            """, (query.lower().strip(), canonical_name, lat, lon, now_iso))

    # --------------------------------------------------------------------------
    # Calendar Events Cache Operations
    # --------------------------------------------------------------------------

    def upsert_events(self, events: List[Any]) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._write_lock, self._get_connection() as conn:
            for e in events:
                is_dict = isinstance(e, dict)
                uid = str(e.get("uid") or e.get("id") or "") if is_dict else str(getattr(e, "uid", "") or getattr(e, "id", ""))
                title = str(e.get("title", "") if is_dict else getattr(e, "title", ""))
                st = e.get("start_time") if is_dict else getattr(e, "start_time", None)
                et = e.get("end_time") if is_dict else getattr(e, "end_time", None)
                loc = str(e.get("location", "") if is_dict else getattr(e, "location", ""))
                m_url = str(e.get("meeting_url", "") if is_dict else getattr(e, "meeting_url", ""))
                is_travel = 1 if (e.get("is_travel", False) if is_dict else getattr(e, "is_travel", False)) else 0

                st_str = st.isoformat() if isinstance(st, datetime) else (str(st) if st else "")
                et_str = et.isoformat() if isinstance(et, datetime) else (str(et) if et else "")
                payload = json.dumps(e if is_dict else (e.to_dict() if hasattr(e, "to_dict") else {}), default=str)

                conn.execute("""
                    INSERT OR REPLACE INTO events (uid, title, start_time, end_time, location, meeting_url, is_travel, payload_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (uid, title, st_str, et_str, loc, m_url, is_travel, payload, now_iso))

    def get_cached_events(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.execute("SELECT payload_json FROM events ORDER BY start_time ASC;")
        results = []
        for row in cursor.fetchall():
            try:
                results.append(json.loads(row["payload_json"]))
            except Exception:
                pass
        return results


# Global singleton instance
database_service = DatabaseService()
