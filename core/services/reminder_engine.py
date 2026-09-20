"""
Reminder Engine for FlightDeck.
Calculates multi-stage notification windows (e.g. 45m, 30m, 20m, 10m, 5m, 2m, 0m),
handles snooze timers, immediate first-time triggers for soon-starting events,
departure time triggers for travel/transit events, and publishes REMINDER_TRIGGERED events via EventBus.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Set, Dict, Optional, Tuple
from core.domain.models import Meeting
from core.services.event_bus import event_bus, EventBus
from core.services.config_service import config_service, ConfigService
from core.services.arrival_service import arrival_service, ArrivalService
from core.services.state_store import NotifiedStateStore, banner_history_store
from core.logger import setup_logging

from core.domain.clock import Clock, system_clock
from core.domain.state_machine import EventState, resolve_event_state
from core.domain.reminder_policy import ReminderPolicyRegistry

logger = logging.getLogger("FlightDeck.ReminderEngine")

class ReminderEngine:
    """Calculates reminder triggers for meetings based on configurable stage intervals, arrival status, and travel ETA."""

    def __init__(self, config: Optional[ConfigService] = None, bus: Optional[EventBus] = None, clock: Optional[Clock] = None):
        self.config = config or config_service
        self.bus = bus or event_bus
        self.clock = clock or system_clock
        self._state_store = NotifiedStateStore()
        self.notified_stage_keys: Set[str] = self._state_store.load()
        from core.services.notification_service import NotificationService, notification_service
        self.notification_service = notification_service if (config is None and bus is None) else NotificationService(config=self.config, bus=self.bus)
        self.bus.subscribe("MARK_ARRIVED", lambda **kwargs: self.mark_arrived(kwargs.get("meeting_id")) if kwargs.get("meeting_id") else None)
        self.bus.subscribe("MARK_PAID", lambda **kwargs: self.mark_bill_paid(kwargs.get("meeting_id")) if kwargs.get("meeting_id") else None)

    def _dispatch_reminder(self, meeting: Meeting, stage: int) -> None:
        """Dispatches notification via unified NotificationService."""
        self.notification_service.notify_meeting(meeting, stage=stage)

    def _add_notified_key(self, key: str) -> None:
        self.notified_stage_keys.add(key)
        self._state_store.add(key)

    def mark_arrived(self, meeting_id: str, reason: str = "manual") -> None:
        """Marks meeting as arrived, suppressing all remaining reminder stages for it."""
        arrival_service.mark_arrived(meeting_id, reason=reason)
        # Suppress all future keys for this meeting
        for s in range(0, 60):
            self._add_notified_key(f"{meeting_id}_stage_{s}")
        self._add_notified_key(f"{meeting_id}_departure_alert")
        logger.info(f"Suppressed future reminders for arrived event: {meeting_id}")

    def mark_bill_paid(self, meeting_id: str) -> None:
        """Marks a bill as paid, suppressing all recurring bill notifications for it."""
        today_str = self.clock.now().astimezone().strftime("%Y-%m-%d")
        self._add_notified_key(f"{meeting_id}_paid")
        self._add_notified_key(f"{meeting_id}_{today_str}_paid")
        self.mark_arrived(meeting_id, reason="paid")
        # Persist to SQLite for durability across restarts
        try:
            from core.services.database_service import database_service
            database_service.record_bill_paid(meeting_id)
        except Exception:
            pass
        logger.info(f"Marked bill as paid, suppressing future reminders: {meeting_id}")

    def is_bill_paid(self, meeting_id: str, today_str: Optional[str] = None) -> bool:
        """Checks if a bill event has been marked as paid."""
        if f"{meeting_id}_paid" in self.notified_stage_keys:
            return True
        date_str = today_str or self.clock.now().astimezone().strftime("%Y-%m-%d")
        if f"{meeting_id}_{date_str}_paid" in self.notified_stage_keys:
            return True
        # Fallback: check SQLite persistence
        try:
            from core.services.database_service import database_service
            return database_service.is_bill_paid(meeting_id)
        except Exception:
            return False

    def reset_state(self) -> None:
        """Clear fired notifications cache (useful for testing or daily reset)."""
        self.notified_stage_keys.clear()
        self._state_store._state.clear()
        self._state_store.force_save()

    def check_and_notify(self, current_time: Optional[datetime] = None) -> List[Tuple[Meeting, int]]:
        """
        Convenience method that fetches upcoming meetings from calendar_service and evaluates them.
        """
        from core.services.calendar_service import calendar_service
        meetings = calendar_service.get_upcoming_meetings()
        return self.evaluate_meetings(meetings, current_time=current_time)

    def is_meeting_active(self, m: Meeting, now: datetime) -> bool:
        """Determines if the meeting is currently active and taking user's attention."""
        from datetime import timezone
        if now.tzinfo is None:
            now = now.astimezone(timezone.utc)
        else:
            now = now.astimezone(timezone.utc)
            
        if m.is_travel and m.departure_time:
            end = m.end_time or m.start_time or (m.departure_time + timedelta(minutes=60))
            if m.departure_time <= now <= end:
                return True
        if m.start_time and m.end_time:
            if m.start_time <= now <= m.end_time:
                return True
        elif m.start_time:
            diff = (now - m.start_time).total_seconds() / 60.0
            if 0 <= diff <= 45:
                return True
        return False

    def get_stages_for_meeting(self, meeting: Meeting) -> List[int]:
        """Retrieve configured stage intervals (minutes before start) for a given meeting type."""
        policy = ReminderPolicyRegistry.get_policy(meeting)
        return policy.get_stages(meeting, self.config)

    def is_within_stage_window(self, diff_minutes: float, stage: int) -> bool:
        """
        Check if diff_minutes (start_time - now) falls within the trigger window for a stage.
        Tolerance window ensures 15s-30s scanning loops never miss a trigger.
        For stage 0 (at start time): [-3.5 min, +1.2 min].
        For stage > 0: [stage - 1.8 min, stage + 1.2 min].
        """
        if stage == 0:
            return -3.5 <= diff_minutes <= 1.2
        return (stage - 1.8) <= diff_minutes <= (stage + 1.2)

    def has_notified_meeting(self, base_key: str) -> bool:
        """Checks if any stage has already been notified for this meeting schedule revision."""
        prefix = f"{base_key}_"
        return any(k.startswith(prefix) for k in self.notified_stage_keys)

    def trigger_startup_catch_up(
        self, meetings: List[Meeting], current_time: Optional[datetime] = None
    ) -> Optional[Tuple[Meeting, int]]:
        """Show the most recent missed reminder once when FlightDeck starts.

        Calendar reminders can be missed while the app is closed. On startup,
        surface today's latest due reminder only when no banner for that event
        is recorded in the persisted notification state and the event has not already ended.
        Travel events become due at their departure time; all other events become due at start time.
        """
        from datetime import timezone

        now = (current_time or datetime.now(timezone.utc)).astimezone(timezone.utc)
        missed = []
        for m in meetings:
            if not m.start_time or m.is_all_day or arrival_service.is_meeting_arrived(m):
                continue
            # If the event has already ended, do not trigger catch-up
            if m.end_time and m.end_time <= now:
                continue
            reminder_time = m.departure_time if m.is_travel and m.departure_time else m.start_time
            if reminder_time.astimezone().date() == now.astimezone().date() and reminder_time <= now:
                # Do not catch up on events that started/were due >30 minutes ago unless still actively ongoing
                elapsed_min = (now - reminder_time).total_seconds() / 60.0
                if elapsed_min > 30.0 and not self.is_meeting_active(m, now):
                    continue
                missed.append((reminder_time, m))
        if not missed:
            return None

        due_time, latest = max(missed, key=lambda item: item[0])
        if self.has_notified_meeting(latest.id):
            return None

        catch_up_key = f"{latest.id}_{int(latest.start_time.timestamp())}_startup_catch_up"
        self._add_notified_key(catch_up_key)

        triggered = Meeting.from_dict(latest.to_dict())
        triggered.reminder_stage = 0
        logger.info(
            f"🔔 >>> TRIGGER STARTUP CATCH-UP BANNER for \"{latest.title}\" "
            f"(due at {due_time.astimezone().strftime('%H:%M')})"
        )
        self._dispatch_reminder(triggered, stage=0)
        return triggered, 0

    def evaluate_meetings(self, meetings: List[Meeting], current_time: Optional[datetime] = None) -> List[Tuple[Meeting, int]]:
        """
        Evaluate all upcoming meetings against notification windows and departure times.
        Returns a list of (meeting, triggered_stage) tuples and publishes REMINDER_TRIGGERED events.
        """
        from datetime import timezone
        from core.domain.clock import FakeClock
        if current_time:
            eval_clock = FakeClock(current_time)
        else:
            eval_clock = self.clock
        now = eval_clock.now()
        triggered_events = []

        if not meetings:
            logger.debug(f"[{now.astimezone().strftime('%H:%M:%S')}] No events to evaluate.")
            return []

        # Determine if there are currently active meetings taking user's attention
        has_active_meeting = any(self.is_meeting_active(m, now) for m in meetings)

        logger.info(f"📊 [Scanner] Evaluating {len(meetings)} events at {now.astimezone().strftime('%H:%M:%S')} (Busy: {has_active_meeting})...")

        for m in meetings:
            is_bill = (getattr(m, "category", "") == "bill" or getattr(m, "event_type", "") == "bill")

            # Non-bill all-day events are skipped
            if m.is_all_day and not is_bill:
                continue
            if not m.start_time:
                continue

            # Special recurring reminder evaluation for bills (rent, bollette, subscriptions, payments)
            if is_bill:
                if not self.config.get("enable_bill_reminders", True):
                    logger.info(f"  ✓ \"{m.title}\" | Bill reminders disabled in settings. Suppressed.")
                    continue

                now_local = now.astimezone()
                today_str = now_local.strftime("%Y-%m-%d")

                if self.is_bill_paid(m.id, today_str=today_str) or arrival_service.is_meeting_arrived(m):
                    logger.info(f"  ✓ \"{m.title}\" | Bill already marked paid. Suppressed.")
                    continue

                interval = max(15, int(self.config.get("bill_reminder_interval_minutes", 120)))
                # Active waking hours (default 08:00 to 22:00)
                start_hour = int(self.config.get("bill_reminder_start_hour", 8))
                end_hour = int(self.config.get("bill_reminder_end_hour", 22))

                if self.config.get("bill_respect_quiet_hours", True):
                    if now_local.hour < start_hour or now_local.hour >= end_hour:
                        logger.debug(f"Bill reminder for '{m.title}' outside active hours ({start_hour}:00-{end_hour}:00)")
                        continue

                mins_since_start = max(0, (now_local.hour - start_hour) * 60 + now_local.minute)
                slot = int(mins_since_start // interval)
                slot_key = f"{m.id}_{today_str}_bill_slot_{slot}"

                if slot_key not in self.notified_stage_keys:
                    self._add_notified_key(slot_key)
                    m_triggered = Meeting.from_dict(m.to_dict())
                    m_triggered.reminder_stage = 0
                    if has_active_meeting and not self.is_meeting_active(m, now):
                        m_triggered.is_quiet_reminder = True
                    triggered_events.append((m_triggered, 0))
                    logger.info(f"💳 >>> TRIGGER BILL REMINDER [Slot {slot}, interval={interval}m] for \"{m.title}\"")
                    self._dispatch_reminder(m_triggered, stage=0)
                continue

            # Skip events that have already ended or are in the past (>45 min ago with no end_time)
            if m.end_time and m.end_time <= now:
                continue
            if not m.end_time and (now - m.start_time).total_seconds() > 45 * 60:
                continue

            # Check if user already arrived (manually or via Wi-Fi/Active app)
            if arrival_service.is_meeting_arrived(m):
                logger.info(f"  ✓ \"{m.title}\" ({m.provider}) | Arrived / Active. Suppressed.")
                continue

            # Check policy suppression via state machine
            event_state = resolve_event_state(m, clock=eval_clock)
            policy = ReminderPolicyRegistry.get_policy(m)

            # Determine reference target time and label:
            # - For travel/transit events with ETA: stages are relative to DEPARTURE (leave) time
            # - For video meetings & regular events: stages are relative to START time
            is_departure_mode = bool(m.is_travel and m.departure_time)
            target_time = m.departure_time if is_departure_mode else m.start_time

            # State key timestamp (revision hash)
            rev_ts = int(target_time.timestamp())
            base_key = f"{m.id}_{rev_ts}"

            # Prune obsolete keys for this meeting
            if m.uid:
                keys_to_remove = [k for k in self.notified_stage_keys if k.startswith(f"{m.uid}_") and not k.startswith(base_key)]
                for k in keys_to_remove:
                    self.notified_stage_keys.remove(k)
                    self._state_store.remove(k)
                    logger.info(f"Pruned obsolete reminder state for rescheduled event: {k}")

            diff_min = (target_time - now).total_seconds() / 60.0

            if policy.should_suppress(m, event_state, diff_min):
                logger.info(f"  ✓ \"{m.title}\" ({m.provider}) | State {event_state.value}. Suppressed by policy.")
                continue

            # If event is on a future date and more than 3 hours away, do not trigger reminders today
            if m.start_time.astimezone().date() > now.astimezone().date() and diff_min > 180:
                continue

            start_str = m.start_time.astimezone().strftime("%H:%M")
            dep_str = m.departure_time.astimezone().strftime("%H:%M") if m.departure_time else ""
            stages = self.get_stages_for_meeting(m)

            matched_stage = None

            # 1. Evaluate Multi-Stage Intervals relative to target time (Departure vs Start)
            for stage in stages:
                stage_key = f"{base_key}_dep_stage_{stage}" if is_departure_mode else f"{base_key}_stage_{stage}"
                if self.is_within_stage_window(diff_min, stage):
                    if stage_key not in self.notified_stage_keys:
                        matched_stage = stage
                        self._add_notified_key(stage_key)

                        # Apply busy mode logic
                        if has_active_meeting and not self.is_meeting_active(m, now):
                            if stage > 10:
                                logger.info(f"🔇 Suppressed stage {stage} reminder for '{m.title}' (User is busy).")
                                continue

                        m_triggered = Meeting.from_dict(m.to_dict())
                        m_triggered.reminder_stage = stage

                        if has_active_meeting and not self.is_meeting_active(m, now) and stage > 0:
                            m_triggered.is_quiet_reminder = True
                            logger.info(f"🤫 Downgrading to quiet reminder for '{m.title}' at stage {stage} (User is busy).")

                        triggered_events.append((m_triggered, stage))

                        if is_departure_mode:
                            stage_label = "LEAVE NOW (0m)" if stage == 0 else f"leave in {stage}m"
                            logger.info(f"🚨 >>> TRIGGER DEPARTURE BANNER [{stage_label}] for \"{m.title}\" (Leave at {dep_str}, Event at {start_str}, diff={diff_min:+.1f}m)")
                        else:
                            stage_label = "at start (0m)" if stage == 0 else f"{stage}m ahead"
                            logger.info(f"🔔 >>> TRIGGER BANNER [{stage_label}] for \"{m.title}\" ({m.provider}, at {start_str}, diff={diff_min:+.1f}m)")

                        self._dispatch_reminder(m_triggered, stage=stage)
                        break

            # 2. Fallback: If target time is imminent (<= 5 min) or in progress and has NEVER been notified
            if matched_stage is None and not self.has_notified_meeting(base_key):
                if -3.5 <= diff_min <= 5.0:
                    fallback_stage = max(0, round(diff_min))
                    stage_key = f"{base_key}_dep_stage_{fallback_stage}" if is_departure_mode else f"{base_key}_stage_{fallback_stage}"
                    self._add_notified_key(stage_key)

                    m_triggered = Meeting.from_dict(m.to_dict())
                    m_triggered.reminder_stage = fallback_stage

                    if has_active_meeting and not self.is_meeting_active(m, now) and fallback_stage > 0:
                        m_triggered.is_quiet_reminder = True
                        logger.info(f"🤫 Downgrading fallback to quiet reminder for '{m.title}' at stage {fallback_stage} (User is busy).")

                    triggered_events.append((m_triggered, fallback_stage))

                    if is_departure_mode:
                        stage_label = "DEPART NOW" if fallback_stage == 0 else f"leave imminent ({fallback_stage}m)"
                        logger.info(f"🚨 >>> TRIGGER IMMEDIATE DEPARTURE BANNER [{stage_label}] for \"{m.title}\" (Leave at {dep_str}, Event at {start_str}, diff={diff_min:+.1f}m)")
                    else:
                        stage_label = "at start (0m)" if fallback_stage == 0 else f"imminent ({fallback_stage}m)"
                        logger.info(f"🔔 >>> TRIGGER IMMEDIATE BANNER [{stage_label}] for \"{m.title}\" ({m.provider}, at {start_str}, diff={diff_min:+.1f}m)")

                    self._dispatch_reminder(m_triggered, stage=fallback_stage)
                    matched_stage = fallback_stage

            # 3. ALWAYS trigger a banner exactly at start time for Travel events
            if is_departure_mode:
                start_diff_min = (m.start_time - now).total_seconds() / 60.0
                start_stage_key = f"{m.id}_{int(m.start_time.timestamp())}_start_stage_0"
                if self.is_within_stage_window(start_diff_min, 0):
                    if start_stage_key not in self.notified_stage_keys:
                        self._add_notified_key(start_stage_key)
                        m_start_triggered = Meeting.from_dict(m.to_dict())
                        m_start_triggered.reminder_stage = 0
                        triggered_events.append((m_start_triggered, 0))
                        logger.info(f"🔔 >>> TRIGGER START BANNER [at start (0m)] for \"{m.title}\" (Travel event starting, diff={start_diff_min:+.1f}m)")
                        self._dispatch_reminder(m_start_triggered, stage=0)
                        matched_stage = 0

            if not matched_stage:
                if is_departure_mode:
                    logger.info(f"  🚗 \"{m.title}\" (Travel) | Leave: {dep_str} | Event: {start_str} | Leave In: {diff_min:+.1f} min | Stages: {stages}")
                else:
                    logger.info(f"  📅 \"{m.title}\" ({m.provider}) | Start: {start_str} | In: {diff_min:+.1f} min | Stages: {stages}")

        return triggered_events

# Global shared instance
reminder_engine = ReminderEngine()
