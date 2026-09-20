import unittest
from datetime import datetime, timezone
from ui.common.tray_viewmodel import TrayViewModel, MODE_ICONS_TRAY

class TestTrayViewModelTransportMode(unittest.TestCase):
    def test_format_next_event_label_modes(self):
        dep = datetime(2026, 8, 30, 8, 30, tzinfo=timezone.utc)

        # Transit
        lbl_transit = TrayViewModel.format_next_event_label(
            "🦆", "09:00", "Team Sync", travel_minutes=25, departure_time=dep, transport_mode="transit", lang="en"
        )
        self.assertIn("🚆", lbl_transit)
        self.assertNotIn("🚗", lbl_transit)

        # Automobile
        lbl_auto = TrayViewModel.format_next_event_label(
            "🦆", "09:00", "Client Visit", travel_minutes=35, departure_time=dep, transport_mode="automobile", lang="en"
        )
        self.assertIn("🚗", lbl_auto)

        # Walking
        lbl_walk = TrayViewModel.format_next_event_label(
            "🦆", "09:00", "Lunch", travel_minutes=10, departure_time=dep, transport_mode="walking", lang="en"
        )
        self.assertIn("🚶", lbl_walk)

        # Bicycling
        lbl_bike = TrayViewModel.format_next_event_label(
            "🦆", "09:00", "Gym", travel_minutes=15, departure_time=dep, transport_mode="bicycling", lang="en"
        )
        self.assertIn("🚲", lbl_bike)

    def test_format_travel_info_modes(self):
        dep = datetime(2026, 8, 30, 8, 30, tzinfo=timezone.utc)
        info_transit = TrayViewModel.format_travel_info(20, dep, transport_mode="transit", lang="en")
        self.assertIn("🚆", info_transit)

        info_auto = TrayViewModel.format_travel_info(20, dep, transport_mode="automobile", lang="en")
        self.assertIn("🚗", info_auto)

        info_walk = TrayViewModel.format_travel_info(15, dep, transport_mode="walking", lang="en")
        self.assertIn("🚶", info_walk)

        info_bike = TrayViewModel.format_travel_info(10, dep, transport_mode="bicycling", lang="en")
        self.assertIn("🚲", info_bike)

    def test_all_day_and_bill_excluded_from_status_bar_title(self):
        now = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)

        # 1. All-day event
        all_day_m = {
            "title": "Bank Holiday",
            "start_time": datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc),
            "end_time": datetime(2026, 8, 30, 23, 59, tzinfo=timezone.utc),
            "is_all_day": True
        }
        title_all_day = TrayViewModel.get_status_bar_title(all_day_m, now, mode="countdown", max_lookahead_min=180)
        self.assertEqual(title_all_day, "🦆 FlightDeck")

        # 2. Bill event
        bill_m = {
            "title": "Affitto",
            "start_time": datetime(2026, 8, 30, 0, 0, tzinfo=timezone.utc),
            "end_time": datetime(2026, 8, 30, 23, 59, tzinfo=timezone.utc),
            "category": "bill"
        }
        title_bill = TrayViewModel.get_status_bar_title(bill_m, now, mode="countdown", max_lookahead_min=180)
        self.assertEqual(title_bill, "🦆 FlightDeck")


if __name__ == "__main__":
    unittest.main()
