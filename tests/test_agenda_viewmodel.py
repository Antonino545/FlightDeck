import unittest
from datetime import datetime, timedelta, timezone

from core.domain.clock import FakeClock
from core.domain.models import CalendarEvent, Meeting, EventCategory
from core.domain.state_machine import EventState
from ui.common.agenda_viewmodel import AgendaViewModel, AgendaEventVM


class TestAgendaViewModel(unittest.TestCase):
    def test_build_event_vm(self):
        clock = FakeClock(datetime(2026, 9, 10, 9, 0, 0, tzinfo=timezone.utc))

        event = CalendarEvent(
            uid="evt-101",
            title="Satellite Communications",
            start_time=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 11, 30, 0, tzinfo=timezone.utc),
            classroom="Aula 5M",
            teacher="Prof. Rossi",
            location="Politecnico",
            category=EventCategory.CLASS.value,
            pilot_type="owl"
        )

        vm = AgendaViewModel.build_event_vm(event, clock=clock)

        self.assertEqual(vm.uid, "evt-101")
        self.assertEqual(vm.title, "Satellite Communications")
        self.assertIn("Aula 5M", vm.subtitle)
        self.assertIn("Prof. Rossi", vm.subtitle)
        self.assertEqual(vm.icon, "🎓")
        self.assertEqual(vm.state, EventState.UPCOMING)
        self.assertTrue(vm.capabilities.has_location)
        self.assertFalse(vm.capabilities.can_join)

    def test_arrived_and_in_call_badges(self):
        clock = FakeClock(datetime(2026, 9, 10, 14, 0, 0, tzinfo=timezone.utc))

        event = CalendarEvent(
            uid="evt-zoom",
            title="Weekly Sprint Planning",
            start_time=datetime(2026, 9, 10, 14, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 15, 0, 0, tzinfo=timezone.utc),
            meeting_url="https://zoom.us/j/999",
            is_arrived=True,
            arrival_reason="call:Zoom",
            category=EventCategory.VIDEO_MEETING.value
        )

        vm = AgendaViewModel.build_event_vm(event, clock=clock)

        self.assertTrue(vm.capabilities.can_join)
        self.assertTrue(vm.capabilities.show_arrival_badge)
        self.assertTrue(vm.capabilities.show_in_call_badge)
        self.assertIn("Zoom", vm.badge_text)

    def test_build_list_filters_today(self):
        clock = FakeClock(datetime(2026, 9, 10, 8, 0, 0, tzinfo=timezone.utc))

        today_event = CalendarEvent(
            uid="evt-today",
            title="Today Meeting",
            start_time=datetime(2026, 9, 10, 11, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc),
        )
        tomorrow_event = CalendarEvent(
            uid="evt-tomorrow",
            title="Tomorrow Meeting",
            start_time=datetime(2026, 9, 11, 11, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 11, 12, 0, 0, tzinfo=timezone.utc),
        )

        vms = AgendaViewModel.build([today_event, tomorrow_event], clock=clock)
        self.assertEqual(len(vms), 1)
        self.assertEqual(vms[0].uid, "evt-today")

    def test_navigation_action_and_maps_fallback(self):
        clock = FakeClock(datetime(2026, 9, 10, 8, 0, 0, tzinfo=timezone.utc))

        event = CalendarEvent(
            uid="evt-loc",
            title="Dentist Appointment",
            start_time=datetime(2026, 9, 10, 15, 0, 0, tzinfo=timezone.utc),
            location="Corso Francia 20, Torino",
            travel_time_minutes=25,
            is_travel=True
        )

        vm = AgendaViewModel.build_event_vm(event, clock=clock)
        self.assertTrue(vm.has_action)
        self.assertTrue(vm.capabilities.can_navigate)
        self.assertFalse(vm.capabilities.can_join)
        self.assertIn("25m", vm.action_btn_text)
        self.assertIn("Corso%20Francia", vm.action_url)

    def test_dict_compatibility(self):
        clock = FakeClock(datetime(2026, 9, 10, 8, 0, 0, tzinfo=timezone.utc))

        raw_dict = {
            "id": "dict-1",
            "title": "Dict Event",
            "start_time": datetime(2026, 9, 10, 16, 0, 0, tzinfo=timezone.utc),
            "meeting_url": "https://meet.google.com/abc-defg-hij",
            "pilot_type": "captain"
        }

        vm = AgendaViewModel.build_event_vm(raw_dict, clock=clock)
        self.assertEqual(vm.uid, "dict-1")
        self.assertEqual(vm.icon, "✈️")
        self.assertTrue(vm.capabilities.can_join)
        self.assertTrue(vm.has_action)

    def test_build_command_center(self):
        clock = FakeClock(datetime(2026, 9, 10, 10, 15, 0, tzinfo=timezone.utc))

        # 1. Ongoing active event (10:00 - 11:00)
        active_event = CalendarEvent(
            uid="evt-active",
            title="Active Lecture",
            start_time=datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 11, 0, 0, tzinfo=timezone.utc),
            location="Aula 1"
        )
        # 2. Next event (11:30 - 12:30)
        next_event = CalendarEvent(
            uid="evt-next",
            title="Team Sync",
            start_time=datetime(2026, 9, 10, 11, 30, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 12, 30, 0, tzinfo=timezone.utc),
            meeting_url="https://meet.google.com/xyz"
        )
        # 3. Later event (15:00 - 16:00)
        later_event = CalendarEvent(
            uid="evt-later",
            title="Evening Study",
            start_time=datetime(2026, 9, 10, 15, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 16, 0, 0, tzinfo=timezone.utc),
        )

        cc = AgendaViewModel.build_command_center([active_event, next_event, later_event], clock=clock)

        self.assertTrue(cc.has_events)
        self.assertIsNotNone(cc.now_event)
        self.assertEqual(cc.now_event.uid, "evt-active")
        self.assertIsNotNone(cc.next_event)
        self.assertEqual(cc.next_event.uid, "evt-next")
        self.assertEqual(len(cc.later_events), 1)
        self.assertEqual(cc.later_events[0].uid, "evt-later")
        self.assertIsNotNone(cc.guidance)
        self.assertTrue(len(cc.guidance.rationale) > 0)

    def test_earlier_today_events_in_command_center(self):
        # Current time is 14:30 (afternoon)
        clock = FakeClock(datetime(2026, 9, 10, 14, 30, 0, tzinfo=timezone.utc))

        # 1. Event from this morning (08:30 - 10:00) as dict
        morning_dict_event = {
            "uid": "evt-morning-1",
            "title": "Maths Lecture",
            "start_time": "2026-09-10T08:30:00+00:00",
            "end_time": "2026-09-10T10:00:00+00:00",
            "location": "Room 101"
        }
        # 2. Another event from late morning (11:00 - 12:00) as CalendarEvent
        late_morning_event = CalendarEvent(
            uid="evt-morning-2",
            title="Physics Lab",
            start_time=datetime(2026, 9, 10, 11, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc),
            location="Lab 3"
        )
        # 3. Next upcoming event (15:00 - 16:00)
        upcoming_event = CalendarEvent(
            uid="evt-upcoming",
            title="Design Review",
            start_time=datetime(2026, 9, 10, 15, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 16, 0, 0, tzinfo=timezone.utc)
        )
        # 4. Later event (18:00 - 19:00)
        later_event = CalendarEvent(
            uid="evt-evening",
            title="Evening Workout",
            start_time=datetime(2026, 9, 10, 18, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 19, 0, 0, tzinfo=timezone.utc)
        )

        all_meetings = [morning_dict_event, late_morning_event, upcoming_event, later_event]
        cc = AgendaViewModel.build_command_center(all_meetings, clock=clock)

        self.assertTrue(cc.has_events)
        # Now event: None (no active event right now at 14:30)
        self.assertIsNone(cc.now_event)
        # Next event: MUST be the upcoming 15:00 event, NOT morning events!
        self.assertIsNotNone(cc.next_event)
        self.assertEqual(cc.next_event.uid, "evt-upcoming")
        # Later events: MUST only be the 18:00 event
        self.assertEqual(len(cc.later_events), 1)
        self.assertEqual(cc.later_events[0].uid, "evt-evening")
        # Earlier events: MUST contain both morning events!
        self.assertEqual(len(cc.earlier_events), 2)
        earlier_uids = [e.uid for e in cc.earlier_events]
        self.assertIn("evt-morning-1", earlier_uids)
        self.assertIn("evt-morning-2", earlier_uids)

        for ev in cc.earlier_events:
            self.assertEqual(ev.state, EventState.COMPLETED)
            self.assertEqual(ev.badge_text, "✓ Ended")
            self.assertEqual(ev.countdown_text, "Completed")
            self.assertFalse(ev.is_urgent)

    def test_all_day_and_bill_events_in_command_center(self):
        clock = FakeClock(datetime(2026, 9, 10, 10, 0, 0, tzinfo=timezone.utc))

        # 1. All-day bill event (00:00 - 23:59)
        bill_event = CalendarEvent(
            uid="bill-rent",
            title="Monthly Rent Due",
            start_time=datetime(2026, 9, 10, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 23, 59, 59, tzinfo=timezone.utc),
            is_all_day=True,
            category="bill",
            pilot_type="duck"
        )
        # 2. Timed upcoming event (11:00 - 12:00)
        upcoming_event = CalendarEvent(
            uid="evt-upcoming",
            title="Client Sync",
            start_time=datetime(2026, 9, 10, 11, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc),
        )

        vm_bill = AgendaViewModel.build_event_vm(bill_event, clock=clock)
        self.assertTrue(vm_bill.is_all_day)
        self.assertEqual(vm_bill.time_display, "All Day")
        self.assertEqual(vm_bill.countdown_text, "All Day")
        self.assertEqual(vm_bill.state, EventState.UPCOMING)

        cc = AgendaViewModel.build_command_center([bill_event, upcoming_event], clock=clock)
        # MUST NOT appear as now_event!
        self.assertIsNone(cc.now_event)
        # MUST NOT hijack next_event! Next event is the timed 11:00 event
        self.assertIsNotNone(cc.next_event)
        self.assertEqual(cc.next_event.uid, "evt-upcoming")
        # Bill MUST be listed in later_events
        later_uids = [e.uid for e in cc.later_events]
        self.assertIn("bill-rent", later_uids)


if __name__ == "__main__":
    unittest.main()

