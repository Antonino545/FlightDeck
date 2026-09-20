import unittest
from datetime import datetime, timedelta, timezone
from core.domain.models import Meeting, PilotType
from core.services.reminder_engine import ReminderEngine
from core.services.event_bus import EventBus
from core.services.config_service import ConfigService

class TestReminderEngine(unittest.TestCase):
    def setUp(self):
        self.bus = EventBus()
        self.bus.clear()
        self.engine = ReminderEngine(bus=self.bus)
        self.engine.config.set("general_reminder_stages", [20, 10, 5, 2, 0])
        self.engine.config.set("meeting_reminder_stages", [20, 10, 5, 2, 0])
        self.engine.config.set("travel_reminder_stages", [45, 30, 15, 5, 2, 0])
        self.engine.reset_state()

    def test_reminder_stage_evaluation(self):
        now = datetime(2026, 8, 22, 12, 0, 0)
        # Meeting in 10 minutes (should match stage 10)
        meeting_10m = Meeting(
            title="Team Sync",
            start_time=now + timedelta(minutes=10),
            pilot_type=PilotType.DUCK.value,
            is_travel=False
        )

        triggered_events = []
        def handler(meeting, stage, **kwargs):
            triggered_events.append((meeting.title, stage))

        self.bus.subscribe("REMINDER_TRIGGERED", handler)

        results = self.engine.evaluate_meetings([meeting_10m], current_time=now)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], 10)
        self.assertEqual(len(triggered_events), 1)
        self.assertEqual(triggered_events[0], ("Team Sync", 10))

    def test_duplicate_suppression_on_same_stage(self):
        now = datetime(2026, 8, 22, 12, 0, 0)
        meeting = Meeting(
            title="Design Review",
            start_time=now + timedelta(minutes=5),
            pilot_type=PilotType.DUCK.value
        )

        # First evaluation: triggers stage 5
        res1 = self.engine.evaluate_meetings([meeting], current_time=now)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0][1], 5)

        # Second evaluation 10 seconds later: should NOT trigger stage 5 again
        now_plus_10s = now + timedelta(seconds=10)
        res2 = self.engine.evaluate_meetings([meeting], current_time=now_plus_10s)
        self.assertEqual(len(res2), 0)

    def test_travel_stages(self):
        now = datetime(2026, 8, 22, 12, 0, 0)
        meeting_travel = Meeting(
            title="Flight Departure",
            start_time=now + timedelta(minutes=45),
            is_travel=True
        )
        self.engine.config.set("travel_reminder_stages", [45, 30, 15, 5, 0])

        stages = self.engine.get_stages_for_meeting(meeting_travel)
        self.assertEqual(stages, [45, 30, 15, 5, 0])

        res = self.engine.evaluate_meetings([meeting_travel], current_time=now)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], 45)

    def test_travel_departure_time_stages(self):
        now = datetime(2026, 8, 22, 12, 0, 0)
        # Event is in 2 hours (14:00), but departure time is in 15 minutes (12:15)
        meeting_transit = Meeting(
            title="Dinner at Restaurant",
            start_time=now + timedelta(hours=2),
            departure_time=now + timedelta(minutes=15),
            travel_time_minutes=35,
            is_travel=True
        )

        # Evaluating at 12:00: departure is in 15 mins -> triggers stage 15 (15m before leave time!)
        res = self.engine.evaluate_meetings([meeting_transit], current_time=now)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0][1], 15)

    def test_mark_arrived_suppression(self):
        now = datetime(2026, 8, 22, 12, 0, 0)
        meeting = Meeting(
            title="ICT for smart mobility (VASSIO LUCA) - Aula 5M",
            start_time=now + timedelta(minutes=5),
            classroom="Aula 5M"
        )

        # Mark arrived
        self.engine.mark_arrived(meeting.id)

        # Should not trigger any reminder
        results = self.engine.evaluate_meetings([meeting], current_time=now)
        self.assertEqual(len(results), 0)

    def test_event_time_stage_zero_and_pre_event_stages(self):
        now = datetime(2026, 8, 22, 12, 0, 0)
        # Event exactly starting at 12:00 (stage 0)
        meeting_stage_0 = Meeting(
            title="Now Starting Meeting",
            start_time=now,
            pilot_type=PilotType.DUCK.value
        )
        results = self.engine.evaluate_meetings([meeting_stage_0], current_time=now)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], 0)
        self.assertEqual(results[0][0].reminder_stage, 0)

    def test_rescheduled_event_resets_stages(self):
        now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        meeting = Meeting(
            uid="uid-reschedule-1",
            title="Design Review",
            start_time=now + timedelta(minutes=10)
        )

        # Trigger stage 10
        res1 = self.engine.evaluate_meetings([meeting], current_time=now)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0][1], 10)

        # Event is rescheduled to 20 minutes later (e.g. 12:30)
        # 10 minutes pass (now is 12:10). We evaluate again.
        now_10m = now + timedelta(minutes=10)
        meeting.start_time = meeting.start_time + timedelta(minutes=20)
        
        # Now diff is 20m. It should trigger stage 20 because the timestamp hash changed, pruning old state.
        res2 = self.engine.evaluate_meetings([meeting], current_time=now_10m)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0][1], 20)

    def test_travel_event_exact_start_time_banner(self):
        now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        # Event exactly starting at 12:00, but is a travel event with a past departure time
        meeting = Meeting(
            title="Meeting with Location",
            start_time=now,
            departure_time=now - timedelta(minutes=15),
            is_travel=True
        )
        results = self.engine.evaluate_meetings([meeting], current_time=now)
        # Should trigger the exact start time banner (stage 0) for the travel event
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][1], 0)
        self.assertEqual(results[0][0].reminder_stage, 0)

    def test_startup_catch_up_shows_latest_unnotified_event_once(self):
        now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        older = Meeting(title="Earlier Event", start_time=now - timedelta(hours=2))
        latest = Meeting(title="Most Recent Event", start_time=now - timedelta(minutes=20))
        triggered_events = []
        self.bus.subscribe(
            "REMINDER_TRIGGERED",
            lambda meeting, stage, **kwargs: triggered_events.append((meeting, stage)),
        )

        result = self.engine.trigger_startup_catch_up([older, latest], current_time=now)

        self.assertIsNotNone(result)
        self.assertEqual(result[0].title, "Most Recent Event")
        self.assertEqual(result[1], 0)
        self.assertEqual(len(triggered_events), 1)
        self.assertIsNone(self.engine.trigger_startup_catch_up([older, latest], current_time=now))

    def test_startup_catch_up_skips_event_with_existing_banner(self):
        now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        meeting = Meeting(title="Already Shown", start_time=now - timedelta(minutes=20))
        self.engine._add_notified_key(f"{meeting.id}_{int(meeting.start_time.timestamp())}_stage_0")

        self.assertIsNone(self.engine.trigger_startup_catch_up([meeting], current_time=now))

    def test_startup_catch_up_uses_missed_travel_departure(self):
        now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        travel = Meeting(
            title="Train to campus",
            start_time=now + timedelta(minutes=30),
            departure_time=now - timedelta(minutes=10),
            is_travel=True,
        )

        result = self.engine.trigger_startup_catch_up([travel], current_time=now)

        self.assertIsNotNone(result)
        self.assertEqual(result[0].title, "Train to campus")
        self.assertEqual(result[1], 0)

    def test_startup_catch_up_skips_past_ended_events(self):
        now = datetime(2026, 8, 22, 23, 30, 0, tzinfo=timezone.utc)
        past_event = Meeting(
            title="Studiare Satellite",
            start_time=now - timedelta(hours=8),
            end_time=now - timedelta(hours=6)
        )
        result = self.engine.trigger_startup_catch_up([past_event], current_time=now)
        self.assertIsNone(result)

    def test_evaluate_meetings_skips_past_ended_events(self):
        now = datetime(2026, 8, 22, 23, 30, 0, tzinfo=timezone.utc)
        past_event = Meeting(
            title="Studiare Satellite",
            start_time=now - timedelta(hours=8),
            end_time=now - timedelta(hours=6)
        )
        results = self.engine.evaluate_meetings([past_event], current_time=now)
        self.assertEqual(len(results), 0)

    def test_all_day_event_is_skipped(self):
        now = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
        meeting = Meeting(
            title="Company Holiday",
            start_time=now, # starts right now
            is_all_day=True
        )
        res = self.engine.evaluate_meetings([meeting], current_time=now)
        self.assertEqual(len(res), 0)

    def test_check_and_notify_convenience_method(self):
        res = self.engine.check_and_notify()
        self.assertIsInstance(res, list)

    def test_bill_recurring_reminders_all_day(self):
        now = datetime(2026, 8, 22, 9, 0, 0, tzinfo=timezone.utc)
        bill = Meeting(
            id="bill_rent_101",
            title="Affitto Mensile",
            start_time=now,
            is_all_day=True,
            category="bill",
            event_type="bill"
        )
        self.engine.config.set("enable_bill_reminders", True)
        self.engine.config.set("bill_reminder_interval_minutes", 120)

        # 1. First evaluation: should trigger reminder stage 0
        res1 = self.engine.evaluate_meetings([bill], current_time=now)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0][1], 0)

        # 2. Evaluation 30m later (less than 120m): should be suppressed
        t_plus_30m = now + timedelta(minutes=30)
        res2 = self.engine.evaluate_meetings([bill], current_time=t_plus_30m)
        self.assertEqual(len(res2), 0)

        # 3. Evaluation 125m later (interval elapsed): should trigger next slot
        t_plus_125m = now + timedelta(minutes=125)
        res3 = self.engine.evaluate_meetings([bill], current_time=t_plus_125m)
        self.assertEqual(len(res3), 1)

    def test_bill_mark_paid_suppresses_reminders(self):
        now = datetime(2026, 8, 22, 9, 0, 0, tzinfo=timezone.utc)
        bill = Meeting(
            id="bill_electric_202",
            title="Bolletta Luce",
            start_time=now,
            is_all_day=True,
            category="bill"
        )
        self.engine.config.set("enable_bill_reminders", True)
        self.engine.config.set("bill_reminder_interval_minutes", 60)

        # First evaluation triggers
        res1 = self.engine.evaluate_meetings([bill], current_time=now)
        self.assertEqual(len(res1), 1)

        # Mark paid
        self.engine.mark_bill_paid("bill_electric_202")
        self.assertTrue(self.engine.is_bill_paid("bill_electric_202"))

        # Evaluation after interval has elapsed should still be suppressed because it is paid
        t_plus_90m = now + timedelta(minutes=90)
        res2 = self.engine.evaluate_meetings([bill], current_time=t_plus_90m)
        self.assertEqual(len(res2), 0)

    def test_bill_reminders_disabled_setting(self):
        now = datetime(2026, 8, 22, 9, 0, 0, tzinfo=timezone.utc)
        bill = Meeting(
            id="bill_gas_303",
            title="Bolletta Gas",
            start_time=now,
            is_all_day=True,
            category="bill"
        )
        self.engine.config.set("enable_bill_reminders", False)
        res = self.engine.evaluate_meetings([bill], current_time=now)
        self.assertEqual(len(res), 0)

    def test_bill_event_bus_mark_paid(self):
        now = datetime(2026, 8, 22, 9, 0, 0, tzinfo=timezone.utc)
        bill = Meeting(
            id="bill_tax_404",
            title="Tassa Rifiuti",
            start_time=now,
            is_all_day=True,
            category="bill"
        )
        self.engine.config.set("enable_bill_reminders", True)
        self.bus.publish("MARK_PAID", meeting_id="bill_tax_404")
        self.assertTrue(self.engine.is_bill_paid("bill_tax_404"))
        res = self.engine.evaluate_meetings([bill], current_time=now)
        self.assertEqual(len(res), 0)

if __name__ == "__main__":
    unittest.main()
