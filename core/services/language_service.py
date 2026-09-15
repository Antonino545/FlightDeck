"""
Language and Internationalization Service for FlightDeck.
Provides OS language detection, runtime language resolution, and bilingual translations (English & Italian).
"""
import os
import sys
import locale
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("FlightDeck.LanguageService")

# Translation Dictionaries: English ('en') & Italian ('it')
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        # General & App
        "app_title": "FlightDeck",
        "system_language": "System (Auto)",
        "language_en": "English 🇬🇧",
        "language_it": "Italiano 🇮🇹",
        "language_label": "Language / Lingua",
        "save": "Save",
        "saved": "Saved",
        "cancel": "Cancel",
        "close": "Close",
        "quit": "Quit FlightDeck",
        "flight_deck": "Flight Deck",
        "preferences": "Flight Config...",
        "check_updates": "Check for Updates...",
        "no_events_today": "No events today",
        "all_caught_up": "All caught up! No more flights today.",
        "upcoming_alert": "Upcoming Alert",
        "test_banner": "Test Banner Alert",

        # Tray & Menu Bar
        "tray_all_day": "All Day",
        "tray_now": "NOW",
        "tray_in_mins": "in {mins}m",
        "tray_in_hours": "in {hours}h {mins}m",
        "tray_depart_in": "Leave in {mins}m",
        "tray_late": "LATE {mins}m",
        "tray_no_more": "No more flights today",
        "tray_calendar_sync": "Calendar Synced: {count} events",

        # Tabs
        "tab_agenda": "Flight Plan",
        "tab_hangar": "Pilot Hangar",
        "tab_settings": "Flight Config",

        # Agenda Tab
        "agenda_today_flights": "Today's Flights",
        "agenda_upcoming": "Upcoming Flights",
        "agenda_active": "In Flight Now",
        "agenda_completed": "Completed Flights",
        "agenda_no_flights": "No flights scheduled for today.",
        "agenda_join_button": "🚀 Join Flight",
        "agenda_maps_button": "🗺️ Directions",
        "agenda_earlier_today": "🏁 EARLIER TODAY",
        "agenda_all_day": "All Day",

        # Hangar Tab
        "hangar_title": "Pilot Hangar",
        "hangar_subtitle": "Select and customize your squad of flying mascots.",
        "hangar_default_pilot": "Default Mascot",
        "hangar_force_default": "Always use default mascot (disable smart classifier)",
        "hangar_active_badge": "ACTIVE PILOT",
        "hangar_select_btn": "Assign Pilot",
        "hangar_selected_btn": "✓ Current Pilot",
        "hangar_customize": "Customize Outfit",

        # Settings Tab
        "settings_general": "General Preferences",
        "settings_launch_at_login": "Launch at Login",
        "settings_sound": "Play Notification Sound",
        "settings_flight_speed": "Banner Flight Speed",
        "settings_status_mode": "Menu Bar Display Mode",
        "settings_status_countdown": "Dynamic Countdown (e.g. In 5m)",
        "settings_status_time": "Event Time (e.g. 14:30)",
        "settings_status_icon": "Icon Only",
        "settings_travel_eta": "Smart Travel & Multi-Modal Transit (Apple Maps)",
        "settings_home_address": "Home / Origin Address",
        "settings_home_city": "Default City",
        "settings_transport_mode": "Preferred Transport Mode",
        "settings_transit": "Transit (Bus/Metro/Train) 🚆",
        "settings_driving": "Driving (Car) 🚗",
        "settings_walking": "Walking 🚶",
        "settings_cycling": "Cycling 🚲",
        "settings_eta_buffer": "Departure Buffer (Minutes)",
        "settings_keywords_title": "🏷️ Smart Mascot & Keyword Rules",
        "settings_keywords_subtitle": "Assign custom keywords to automatically trigger specific mascot pilots and categories.",
        "settings_keywords_add_placeholder": "Type a keyword (e.g. Thesis, Padel, Doctor)...",
        "settings_keywords_add_btn": "＋ Add",
        "settings_keywords_test_placeholder": "Test an event title (e.g. Morning Padel with Alex)...",
        "settings_keywords_test_matched": "🎯 Matched Pilot:",
        "settings_keywords_reset_btn": "↺ Reset Defaults",
        "settings_calendars": "Connected Calendars",
        "settings_developer": "Developer & Diagnostic Tools",
        "settings_license": "📜 License & About",
        "license_title": "FlightDeck License & Acknowledgements",
        "license_body": "FlightDeck is free and open-source software licensed under the MIT License.\n\nAcknowledgements:\n• Inspired by QuakPit (Ooble Studio)\n• Palette & Visual Tokens: Catppuccin Mocha\n• Native Bridges: PyObjC & PyQt6\n• Calendar Sync: Apple EventKit & CalDAV (RFC 5545)",

        # Banner HUD & Buttons
        "banner_join_flight": "🚀 Join Flight",
        "banner_join_meeting": "🚀 Join Meeting",
        "banner_got_it": "✅ Got it",
        "banner_heads_up": "👀 Heads Up",
        "banner_flyby_pill": "✈️ FLYBY",
        "banner_im_here": "📍 I'm Here",
        "banner_snooze_5m": "💤 5m",
        "banner_skip": "⏭️ Skip",
        "banner_online_meeting": "Online Meeting",

        # Banner Countdown & Badges
        "badge_in_mins_early": "In {mins}m • Early Alert",
        "badge_in_mins_ready": "In {mins}m • Get Ready",
        "badge_in_mins_almost": "In {mins}m • Almost Time!",
        "badge_in_secs_now": "Starting Now!",
        "badge_study_in_mins": "In {mins}m • Study Time",
        "badge_study_open_books": "In {mins}m • Open Books",
        "badge_study_time_to_study": "In {mins}m • Time to Study!",
        "badge_study_starting": "Study Starting Now!",
        "badge_class_in_mins": "Lesson in {mins}m • {classroom}",
        "badge_class_soon": "Class in {mins}m • {classroom}",
        "badge_class_starting": "Class starting now • {classroom}",
        "badge_travel_in_mins": "In {mins}m • Travel Notice",
        "badge_travel_prepare": "In {mins}m • Prepare to Leave",
        "badge_travel_leave_now": "Leave Now!",
        "badge_travel_leave_in": "Leave in {mins}m ({time})",
        "badge_travel_leave_at": "Leave at {time} (~{duration})",
        "badge_travel_late_by": "LATE BY {mins}m • LEAVE NOW!",
        "badge_travel_depart_now": "DEPART NOW!",
        "badge_late_by_mins": "LATE BY {mins}m • IN PROGRESS",
        "badge_late_class_by": "LATE BY {mins}m • {classroom}",
        "badge_late_study_by": "STUDY OVERDUE BY {mins}m • DO IT!",
        "badge_in_progress": "IN PROGRESS NOW",
        "badge_class_started": "CLASS STARTED • {classroom}",
        "badge_study_now": "TIME TO STUDY • DO IT!",

        # Event Providers & Titles
        "provider_study": "Study Session 📖",
        "provider_class": "University Lecture 🎓",
        "provider_food": "Dinner / Food 🍕🍽️",
        "provider_travel": "Travel & Transit ✈️🚆",
        "provider_gym": "Workout & Fitness 🏋️‍♂️",
        "provider_health": "Wellness & Health 🧘",
        "provider_in_person": "Appointment / Errand 📍",
        "provider_quick": "Quick Sync / Brainstorm 🐿️",
        "provider_calendar": "Calendar Alert ⏰",

        # Additional UI & Menus
        "sync_now": "Sync Now",
        "sync_calendars": "Sync Calendars",
        "sync_pending": "Pending",
        "sync_success": "Sync: {time}",
        "sync_failed": "Failed (Last: {time})",
        "scanner_active_events": "Scanner Active  •  {count} events today  •  Next: {time}{travel}",
        "scanner_active_no_events": "Scanner Active  •  No upcoming events for today",
        "events_today_header": "Today's Events:",
        "tomorrow_header": "Tomorrow:",
        "no_remaining_today": "No remaining events today",
        "update_available_menu": "🚀 Update Available ({version}) - Install...",
        "update_up_to_date_title": "You're Up to Date! ✨",
        "update_up_to_date_pill": "UP TO DATE ✨",
        "update_up_to_date_sub": "FlightDeck v{version} is currently the newest version.",
        "update_up_to_date_btn": "✓ Great",
        "update_check_failed_title": "Update Check Failed",
        "update_check_failed_sub": "Could not connect to GitHub Releases.",
        "preferences_menu": "Flight Config (Preferences)...",
        "about_flightdeck": "About FlightDeck",
        "hide_app": "Hide FlightDeck",
        "hide_others": "Hide Others",
        "show_all": "Show All",
        "window_menu": "Window",
        "help_menu": "Help",
        "edit_menu": "Edit",
        "undo": "Undo",
        "redo": "Redo",
        "cut": "Cut",
        "copy": "Copy",
        "paste": "Paste",
        "select_all": "Select All",
        "minimize": "Minimize",
        "leave_at": "Leave at {time}",
        "travel_suffix": "travel",
        "next_event_label": "Next: {time} — {title}",

        # Settings Categories Navigation
        "settings_categories_header": "SETTINGS CATEGORIES",
        "settings_cat_reminders": "Reminders & Timing",
        "settings_cat_reminders_sub": "Lead times & presets",
        "settings_cat_presence": "Smart Presence",
        "settings_cat_presence_sub": "Auto-arrival & calls",
        "settings_cat_calendars": "Calendar Sources",
        "settings_cat_calendars_sub": "Connected calendars",
        "settings_cat_commute": "Commute & Travel",
        "settings_cat_commute_sub": "Departure & ETA",
        "settings_cat_preferences": "App Preferences",
        "settings_cat_preferences_sub": "General & updates",

        # Settings Card 1: Timing & Stages
        "settings_timing_title": "⏱️ Notification Lead Times & Staged Reminders",
        "settings_timing_subtitle": "Select reminder alert windows to receive progressive notifications ahead of time.",
        "settings_quick_presets": "⚡ Quick Presets:",
        "preset_relaxed": "🧘 Relaxed",
        "preset_standard": "⚡ Standard",
        "preset_intensive": "🚨 Intensive",
        "settings_video_meetings": "📹 Video Meetings",
        "settings_video_meetings_desc": "Alert ahead of meeting start (0m is always on)",
        "settings_general_events": "📅 General Events",
        "settings_general_events_desc": "Alert ahead of start time (0m is always on)",
        "settings_travel_trips": "🚗 Travel & Trips",
        "settings_travel_trips_desc": "Alert ahead of leave time (0m is always on)",

        # Settings Card 2: ETA & Departure Address
        "settings_eta_title": "📍 Home / Departure Address & Multi-Modal Route ETA",
        "settings_eta_subtitle": "Calculates real-time travel duration and departure times for Public Transit, Driving, Walking, or Cycling.",
        "settings_starting_address": "🏠 Starting Address (Origin)",
        "settings_address_placeholder": "Search address, campus, or landmark (e.g. Corso Duca degli Abruzzi 24, Torino)",
        "settings_address_format_hint": "💡 Format: Street & Number, City, Postal Code, Country (e.g. Corso Duca degli Abruzzi 24, 10129 Torino, Italy)",
        "settings_address_suggest_hint": "💡 Type to search addresses. Click a suggestion or Save directly.",
        "settings_address_verified": "✓ Verified on Map",
        "settings_address_not_found": "⚠️ Address not found on map",
        "settings_address_searching": "🔍 Searching map...",
        "settings_address_view_map": "🗺️ Map",
        "settings_address_verify_btn": "🔍 Verify",
        "settings_address_incomplete_warning": "⚠️ Please specify street, number, and city for accurate transit ETA.",
        "settings_address_error_invalid": "❌ Invalid address format. Required: Street, Number, City (e.g. Corso Duca degli Abruzzi 24, 10129 Torino)",
        "settings_address_error_btn": "❌ Invalid Format",
        "settings_save_location": "💾 Save Location",
        "settings_exam_location": "🎓 University & Exam Campus",
        "settings_exam_location_placeholder": "Write university name or campus (e.g. Politecnico di Milano, Sapienza, Harvard...)",
        "settings_exam_location_hint": "💡 Type any university or campus name. Automatically assigned to exams to calculate transit routes & ETA.",
        "settings_exam_campus_presets": "Quick Presets:",
        "campus_polito_main": "🏛️ PoliTO Centrale",
        "campus_polito_mirafiori": "🏛️ Mirafiori",
        "campus_polito_lingotto": "🏛️ Lingotto",
        "campus_unito": "🏛️ UniTO",
        "settings_exam_save": "💾 Save Exam Location",
        "provider_exam": "University Exam 🎓",
        "settings_transport_calc": "🚦 Transport Mode for Route Calculation",
        "settings_public_transit": "🚆 Public Transit",
        "settings_driving_mode": "🚗 Driving",
        "settings_cycling_mode": "🚲 Cycling",
        "settings_walking_mode": "🚶 Walking",
        "settings_address_edit": "Edit",
        "settings_route_title": "Route & Navigation",
        "settings_departure_buffer": "Departure Buffer Margin",
        "settings_buffer_hint_transit": "Station transit time",
        "settings_buffer_hint_driving": "Parking & walk-in time",
        "settings_buffer_hint_cycling": "Lock-up & walk-in time",
        "settings_buffer_hint_walking": "Not usually needed",
        "buffer_0m": "0 minutes (Exact ETA)",
        "buffer_5m": "5 minutes",
        "buffer_10m_rec": "10 minutes (Recommended)",
        "buffer_15m": "15 minutes",
        "buffer_20m": "20 minutes",
        "buffer_30m": "30 minutes",

        # Settings Card: Smart Presence & Arrival Detection
        "settings_arrival_title": "📍 Smart Presence & Arrival Detection",
        "settings_arrival_subtitle": "Automatically suppresses redundant reminders when you're already in a call or on-site.",
        "settings_arrival_enable": "Enable Smart Presence & Auto-Arrival Detection",
        "settings_arrival_enable_sub": "Silences reminders when you've joined the call or arrived at the venue",
        "settings_arrival_calls": "Active Video Call Detection",
        "settings_arrival_calls_sub": "Suppresses alerts when Zoom, Teams, Webex, Skype, or Slack is active",
        "settings_arrival_wifi": "Venue & Campus Wi-Fi Matching",
        "settings_arrival_wifi_sub": "Suppresses reminders when connected to recognized campus or office Wi-Fi",
        "settings_arrival_diagnostics_title": "Live Diagnostics & Presence Status:",
        "settings_arrival_current_wifi": "Current Wi-Fi:",
        "settings_arrival_status_matched": "Recognized Venue ✅",
        "settings_arrival_status_unmatched": "Standard Network",
        "settings_arrival_status_disconnected": "Disconnected",
        "settings_arrival_active_call": "Active Call App:",
        "settings_arrival_no_call": "None running",
        "settings_arrival_ssids_label": "Monitored Venue Wi-Fi SSIDs (comma-separated):",
        "settings_arrival_ssids_placeholder": "eduroam, polito, campus, universit, studenti...",
        "settings_arrival_ssids_hint": "💡 When connected to these Wi-Fi networks, reminders for matching lectures or campus events are auto-silenced.",
        "settings_arrival_save_btn": "💾 Save SSIDs",
        "settings_arrival_reset_btn": "↺ Reset Defaults",
        "settings_arrival_refresh_btn": "🔄 Check Now",
        "settings_arrival_summary_title": "Current Status:",
        "settings_arrival_summary_normal": "⚪ Normal Mode — All reminder flight banners will alert as scheduled.",
        "settings_arrival_summary_call": "🟢 In-Call Mode — Active video call ({app}) detected. Meeting alerts are automatically suppressed.",
        "settings_arrival_summary_venue": "🟢 Venue Mode — Connected to recognized venue Wi-Fi ({ssid}). Lecture & in-person reminders are suppressed.",
        "settings_arrival_summary_disabled": "⏸️ Presence Detection Paused — Automatic arrival checks are currently disabled.",
        "settings_arrival_add_current_wifi": "➕ Add '{ssid}' to Venue Wi-Fi List",
        "settings_arrival_added_wifi": "✓ '{ssid}' Added to Venue List!",
        "agenda_arrived_badge": "Arrived",
        "agenda_in_call_badge": "In Call",
        "agenda_on_site_badge": "On Site",
        "agenda_ended_badge": "Ended",
        "agenda_concluded": "Completed",
        "agenda_cancelled_badge": "Cancelled",
        "agenda_cancelled": "Cancelled",

        # Settings Card 3: Calendars
        "settings_calendars_title": "📅 Included System Calendars",
        "settings_calendars_subtitle": "Select which local, iCloud, or Google calendars to actively monitor for reminders.",
        "settings_all_cals_monitored": "All calendar sources are currently monitored.",

        # Settings Card 4: System & Diagnostics
        "settings_system_lang_diag": "⚙️ System, Language & Diagnostics",
        "settings_system_lang": "⚙️ System & Language",
        "settings_lang_selector_label": "🌐 Language / Lingua dell'Applicazione:",
        "settings_autostart_mac": "🚀 Launch FlightDeck automatically at macOS login",
        "settings_mute_lessons": "🤫 Mute banner chime during university lessons & classes",
        "settings_debug_mode": "🐛 Enable Developer & Debug Diagnostics Mode",
        "settings_config_json": "📝 Config JSON",
        "settings_view_logs": "📄 View Logs",
        "settings_log_folder": "📂 Log Folder",
        "settings_update_ready": "FlightDeck v{version}  •  Ready",
        "settings_install_update_now": "⚡ Install Update Now",

        # Hangar Tab
        "hangar_header_title": "✈️ Aircraft Hangar & Pilot Workshop",
        "hangar_header_subtitle": "Configure aerial mascots, customize flight uniforms, and fine-tune category triggers.",
        "hangar_filter_all": "🌟 All ({count})",
        "hangar_filter_productivity": "💼 Productivity",
        "hangar_filter_lifestyle": "🎯 Lifestyle",
        "hangar_filter_commute": "🚗 Commute & Events",
        "hangar_filter_general": "⚙️ General",
        "hangar_test_chime": "🔔 Test Chime",
        "hangar_surprise_me": "🎲 Surprise Me",
        "hangar_reset_presets": "🔄 Reset Presets",
        "hangar_animal_mascot": "Animal Mascot:",
        "hangar_active_pilot_label": "Active Pilot",
        "hangar_test_btn": "🚀 Test Flight",
        "hangar_keywords_label": "🏷️ Trigger Keywords",
        "hangar_keywords_toggle_btn": "🏷️ Keywords ({count}) ▾",
        "hangar_keywords_toggle_btn_open": "🏷️ Keywords ({count}) ▴",
        "hangar_keywords_drawer_title": "🏷️ Trigger Keywords for {category}",
        "hangar_keywords_drawer_subtitle": "Events matching these keywords automatically trigger this category and mascot.",
        "hangar_keywords_drawer_hide": "▲ Hide",
        "hangar_keywords_add_placeholder": "Add keyword (e.g. padel, sushi)...",
        "hangar_keywords_add_btn": "+ Add",
        "hangar_keywords_reset_btn": "↺ Reset",
        "hangar_keywords_custom_title": "✨ Your Custom Triggers",
        "hangar_keywords_custom_active": "({count} active)",
        "hangar_keywords_custom_empty": "No custom triggers yet. Add courses, rooms, or keywords above!",
        "hangar_keywords_presets_toggle_show": "🔒 Built-in Core Presets ({count} defaults)  ▾  [Show Defaults]",
        "hangar_keywords_presets_toggle_hide": "🔒 Built-in Core Presets ({count} defaults)  ▴  [Hide Defaults]",
        "hangar_keywords_add_custom_btn": "+ Add Custom Keyword",
        "hangar_keywords_reset_to_defaults": "↺ Reset to Defaults",
        "hangar_keywords_add_placeholder_custom": "Add custom keyword (e.g. aula 3b, politecnico, cs101)...",
        "hangar_subcat_study": "📖 Self-Study",
        "hangar_subcat_class": "🏫 Lectures & Classes",
        "hangar_subcat_exam": "🎓 Exams & Tests",
        "hangar_subcat_study_guide": "💡 Motivational pre-study alerts ('Open your books!') and focus countdowns for solo revision, homework & thesis.",
        "hangar_subcat_class_guide": "💡 Automatically extracts Classroom & Professor from calendar events to route you to your lecture hall.",
        "hangar_subcat_exam_guide": "💡 High-priority exam alerts for midterms and finals with quick directions to your testing hall.",
        "hangar_test_study_btn": "🚀 Test Study Alert",
        "hangar_test_class_btn": "🚀 Test Lecture Alert",
        "hangar_test_exam_btn": "🚀 Test Exam Alert",
        "hangar_subcat_preview_tag": "⚡ LIVE ALERT PREVIEW",
        "hangar_subcat_preview_hint": "Real-time mockup of the alert banner when this event triggers",
        "hangar_subcat_test_btn": "🚀 Test This Alert",
        "hangar_subcat_keywords_heading": "🏷️ Trigger Keywords for {subcat}:",
        "hangar_subcat_sim_study_title": "Deep Focus & Solo Study Session",
        "hangar_subcat_sim_study_btn": "⚡ TIME TO STUDY! 📖",
        "hangar_subcat_sim_study_badge1": "💡 Solo Revision",
        "hangar_subcat_sim_study_badge2": "📖 Library Focus",
        "hangar_subcat_sim_class_title": "Neural Networks & AI Lecture (Room 3B)",
        "hangar_subcat_sim_class_btn": "🏫 ROOM 3B & NOTES",
        "hangar_subcat_sim_class_badge1": "📍 Room: Aula 3B",
        "hangar_subcat_sim_class_badge2": "👨‍🏫 Prof. Rossi",
        "hangar_subcat_sim_exam_title": "General Physics Final Exam (Main Hall)",
        "hangar_subcat_sim_exam_btn": "🎓 MAIN HALL & NOTES",
        "hangar_subcat_sim_exam_badge1": "🚨 HIGH PRIORITY EXAM",
        "hangar_subcat_sim_exam_badge2": "📍 Hall: Aula Magna",
        "hangar_subcat_sim_in_10m": "⏱️ In 10 min",
        "hangar_subcat_mascot_sync": "🔗 Same as Academic Pilot",
        "hangar_subcat_mascot_label": "Mascot for this type:",
        "hangar_intel_title_study": "🎯 Deep Focus & Solo Revision Mode",
        "hangar_intel_title_class": "🏫 Smart Lecture & Classroom Routing",
        "hangar_intel_title_exam": "🚨 High-Priority Exam & Test Alarms",
        "hangar_intel_badge_study_1": "⏱️ 10m Focus Countdown",
        "hangar_intel_badge_study_2": "📚 Books & Homework Detection",
        "hangar_intel_badge_study_3": "🔇 Quiet Chime",
        "hangar_intel_badge_class_1": "📍 Auto-extracts Classroom (e.g. Aula 3B)",
        "hangar_intel_badge_class_2": "👨‍🏫 Detects Professor",
        "hangar_intel_badge_class_3": "🗺️ Campus Nav",
        "hangar_intel_badge_exam_1": "🚨 High-Priority Siren",
        "hangar_intel_badge_exam_2": "🏛️ Exam Hall Navigation",
        "hangar_intel_badge_exam_3": "⏰ Critical Countdown",
        "hangar_change_pilot_btn": "Change Pilot",
        "animal_duck": "🦆 Aviator Duck",
        "animal_owl": "🦉 Academic Owl",
        "animal_bunny": "🐰 Clever Bunny",
        "animal_platypus": "🕵️‍♂️ Secret Platypus",
        "animal_squirrel": "🐿️ Hyper Squirrel",
        "animal_fox": "🦊 Tactical Fox",
        "animal_penguin": "🐧 Dapper Penguin",
        "animal_panda": "🐼 Chill Panda",
        "cat_study_title": "🎓 University & Study Sessions",
        "cat_study_desc": "Lectures, exams, self-study, homework & thesis.",
        "cat_food_title": "🍕 Dining, Lunch & Restaurants",
        "cat_food_desc": "Dinners, lunch dates, pizzerias & food routes.",
        "cat_travel_title": "✈️ Travel, Flights & Trains",
        "cat_travel_desc": "Airports, flights, high-speed trains & trips.",
        "cat_sport_title": "🏋️ Gym, Palestra & Sports",
        "cat_sport_desc": "Workouts, crossfit, padel, tennis & running.",
        "cat_in_person_title": "🏎️ In-Person & Commute",
        "cat_in_person_desc": "Doctor visits, dentist & real-time navigation.",
        "cat_health_title": "🌸 Wellness & Therapy",
        "cat_health_desc": "Serenis sessions, yoga, meditation & calm.",
        "cat_work_title": "💼 Work & Office",
        "cat_work_desc": "Shifts, client meetings, standups, sprint reviews & office tasks.",
        "cat_concert_title": "🎸 Concerts, Shows & Live Music",
        "cat_concert_desc": "Live music, gigs, festivals, arena tours & theater tickets.",
        "cat_bill_title": "💳 Bills, Rent & Payments",
        "cat_bill_desc": "Rent, utilities, subscriptions, invoices, taxes & recurring dues.",
        "cat_general_title": "⏰ General Meetings & Reminders",
        "cat_general_desc": "Video conferences (Meet, Zoom, Teams) & alerts.",
        "cal_category_mapping": "Category Mapping",
        "cal_cat_auto": "✨ Auto Detect",
        "cal_cat_study": "🎓 Study & Academic",
        "cal_cat_food": "🍕 Food & Dining",
        "cal_cat_travel": "✈️ Travel & Commute",
        "cal_cat_sport": "🏋️ Gym & Sport",
        "cal_cat_in_person": "🏎️ In-Person",
        "cal_cat_health": "🌸 Wellness & Health",
        "cal_cat_work": "💼 Work & Office",
        "cal_cat_concert": "🎸 Concert & Live",
        "cal_cat_bill": "💳 Bills & Rent",
        "cal_cat_general": "⏰ General",
        "banner_mark_paid": "✅ Mark Paid",
        "banner_already_paid": "✅ Paid",
        "banner_pay_now": "💳 Pay Now",
        "settings_bill_reminders_title": "💳 Recurring Bill & Rent Reminders",
        "settings_bill_reminders_desc": "Repeat notifications for unpaid bills and rent until marked paid.",
        "settings_bill_interval_label": "Reminder Frequency:",
    },

    "it": {
        # General & App
        "app_title": "FlightDeck",
        "system_language": "Sistema (Auto)",
        "language_en": "English 🇬🇧",
        "language_it": "Italiano 🇮🇹",
        "language_label": "Lingua / Language",
        "save": "Salva",
        "saved": "Salvato",
        "cancel": "Annulla",
        "close": "Chiudi",
        "quit": "Esci da FlightDeck",
        "flight_deck": "Flight Deck",
        "preferences": "Configurazione Volo...",
        "check_updates": "Verifica Aggiornamenti...",
        "no_events_today": "Nessun evento oggi",
        "all_caught_up": "Tutto completato! Nessun altro volo in programma oggi.",
        "upcoming_alert": "Avviso Prossimo Volo",
        "test_banner": "Avviso Banner di Prova",

        # Tray & Menu Bar
        "tray_all_day": "Tutto il giorno",
        "tray_now": "ORA",
        "tray_in_mins": "tra {mins}m",
        "tray_in_hours": "tra {hours}h {mins}m",
        "tray_depart_in": "Partenza tra {mins}m",
        "tray_late": "RITARDO {mins}m",
        "tray_no_more": "Nessun altro volo oggi",
        "tray_calendar_sync": "Calendario sincronizzato: {count} eventi",

        # Tabs
        "tab_agenda": "Piano di Volo",
        "tab_hangar": "Hangar Piloti",
        "tab_settings": "Configurazione",

        # Agenda Tab
        "agenda_today_flights": "Voli di Oggi",
        "agenda_upcoming": "Prossimi Voli",
        "agenda_active": "In Volo Adesso",
        "agenda_completed": "Voli Completati",
        "agenda_no_flights": "Nessun volo in programma per oggi.",
        "agenda_join_button": "🚀 Entra nel Volo",
        "agenda_maps_button": "🗺️ Indicazioni Mappe",
        "agenda_earlier_today": "🏁 VOLI PRECEDENTI",
        "agenda_all_day": "Tutto il giorno",

        # Hangar Tab
        "hangar_title": "Hangar Piloti",
        "hangar_subtitle": "Seleziona e personalizza la tua squadriglia di mascotte volanti.",
        "hangar_default_pilot": "Mascotte Predefinita",
        "hangar_force_default": "Usa sempre la mascotte predefinita (disattiva classificazione automatica)",
        "hangar_active_badge": "PILOTA ATTIVO",
        "hangar_select_btn": "Assegna Pilota",
        "hangar_selected_btn": "✓ Pilota Attuale",
        "hangar_customize": "Personalizza Completo",

        # Settings Tab
        "settings_general": "Preferenze Generali",
        "settings_launch_at_login": "Avvia al login di sistema",
        "settings_sound": "Riproduci suono di notifica",
        "settings_flight_speed": "Velocità di volo del banner",
        "settings_status_mode": "Modalità icona barra dei menu",
        "settings_status_countdown": "Conto alla rovescia dinamico (es. Tra 5m)",
        "settings_status_time": "Orario evento (es. 14:30)",
        "settings_status_icon": "Solo Icona",
        "settings_travel_eta": "Calcolo Spostamenti & Mezzi (Apple Maps)",
        "settings_home_address": "Indirizzo di partenza / Casa",
        "settings_home_city": "Città / Area",
        "settings_transport_mode": "Mezzo di trasporto preferito",
        "settings_transit": "Mezzi Pubblici (Bus/Metro/Treno) 🚆",
        "settings_driving": "Automobile 🚗",
        "settings_walking": "A Piedi 🚶",
        "settings_cycling": "Bicicletta 🚲",
        "settings_eta_buffer": "Margine di anticipo partenza (minuti)",
        "settings_keywords_title": "🏷️ Regole Parole Chiave & Mascotte",
        "settings_keywords_subtitle": "Associa parole chiave personalizzate per attivare automaticamente piloti e categorie.",
        "settings_keywords_add_placeholder": "Scrivi una parola chiave (es. Tesi, Padel, Dottore)...",
        "settings_keywords_add_btn": "＋ Aggiungi",
        "settings_keywords_test_placeholder": "Testa un titolo evento (es. Partita di Padel con Luca)...",
        "settings_keywords_test_matched": "🎯 Pilota Riconosciuto:",
        "settings_keywords_reset_btn": "↺ Ripristina Predefiniti",
        "settings_calendars": "Calendari Collegati",
        "settings_developer": "Strumenti Sviluppatore & Diagnostica",
        "settings_license": "📜 Licenza e Info",
        "license_title": "Licenza e Ringraziamenti di FlightDeck",
        "license_body": "FlightDeck è un software libero e open-source distribuito con licenza MIT.\n\nRingraziamenti:\n• Ispirato da QuakPit (Ooble Studio)\n• Palette e Design: Catppuccin Mocha\n• Integrazioni native: PyObjC e PyQt6\n• Sincronizzazione calendari: Apple EventKit e CalDAV (RFC 5545)",

        # Banner HUD & Buttons
        "banner_join_flight": "🚀 Entra nel Volo",
        "banner_join_meeting": "🚀 Partecipa alla Riunione",
        "banner_got_it": "✅ Capito",
        "banner_heads_up": "👀 Preavviso",
        "banner_flyby_pill": "✈️ AL VOLO",
        "banner_im_here": "📍 Sono qui",
        "banner_snooze_5m": "💤 5m",
        "banner_skip": "⏭️ Salta",
        "banner_online_meeting": "Riunione Online",

        # Banner Countdown & Badges
        "badge_in_mins_early": "Tra {mins}m • Preavviso",
        "badge_in_mins_ready": "Tra {mins}m • Preparati",
        "badge_in_mins_almost": "Tra {mins}m • Quasi ora!",
        "badge_in_secs_now": "Inizia ora!",
        "badge_study_in_mins": "Tra {mins}m • Studio",
        "badge_study_open_books": "Tra {mins}m • Apri i Libri",
        "badge_study_time_to_study": "Tra {mins}m • Tempo di Studiare!",
        "badge_study_starting": "Studio al via!",
        "badge_class_in_mins": "Lezione tra {mins}m • {classroom}",
        "badge_class_soon": "Classe tra {mins}m • {classroom}",
        "badge_class_starting": "Lezione al via • {classroom}",
        "badge_travel_in_mins": "Tra {mins}m • Avviso Partenza",
        "badge_travel_prepare": "Tra {mins}m • Preparati a uscire",
        "badge_travel_leave_now": "Esci Adesso!",
        "badge_travel_leave_in": "Partenza tra {mins}m ({time})",
        "badge_travel_leave_at": "Partenza alle {time} (~{duration})",
        "badge_travel_late_by": "IN RITARDO DI {mins}m • ESCI ORA!",
        "badge_travel_depart_now": "PARTENZA ORA!",
        "badge_late_by_mins": "IN RITARDO DI {mins}m • IN CORSO",
        "badge_late_class_by": "IN RITARDO DI {mins}m • {classroom}",
        "badge_late_study_by": "STUDIO IN RITARDO DI {mins}m • STUDIA!",
        "badge_in_progress": "IN CORSO ORA",
        "badge_class_started": "LEZIONE INIZIATA • {classroom}",
        "badge_study_now": "TEMPO DI STUDIARE • FALLO ORA!",

        # Event Providers & Titles
        "provider_study": "Sessione di Studio 📖",
        "provider_class": "Lezione Universitaria 🎓",
        "provider_food": "Cena / Pranzo 🍕🍽️",
        "provider_travel": "Viaggio & Spostamento ✈️🚆",
        "provider_gym": "Allenamento & Fitness 🏋️‍♂️",
        "provider_health": "Salute & Benessere 🧘",
        "provider_in_person": "Appuntamento / Visita 📍",
        "provider_quick": "Confronto Veloce / Idea 🐿️",
        "provider_calendar": "Avviso Calendario ⏰",

        # Additional UI & Menus
        "sync_now": "Sincronizza Ora",
        "sync_calendars": "Sincronizza Calendari",
        "sync_pending": "In attesa",
        "sync_success": "Sync: {time}",
        "sync_failed": "Errore (Ultimo: {time})",
        "scanner_active_events": "Scanner Attivo  •  {count} eventi oggi  •  Prossimo: {time}{travel}",
        "scanner_active_no_events": "Scanner Attivo  •  Nessun prossimo evento per oggi",
        "events_today_header": "Eventi di Oggi:",
        "tomorrow_header": "Domani:",
        "no_remaining_today": "Nessun altro evento oggi",
        "update_available_menu": "🚀 Aggiornamento Disponibile ({version}) - Installa...",
        "update_up_to_date_title": "Sei all'ultima versione! ✨",
        "update_up_to_date_pill": "AGGIORNATO ✨",
        "update_up_to_date_sub": "FlightDeck v{version} è la versione più recente disponibile.",
        "update_up_to_date_btn": "✓ Ottimo",
        "update_check_failed_title": "Verifica Aggiornamenti Fallita",
        "update_check_failed_sub": "Impossibile connettersi a GitHub Releases.",
        "preferences_menu": "Configurazione Volo (Preferenze)...",
        "about_flightdeck": "Informazioni su FlightDeck",
        "hide_app": "Nascondi FlightDeck",
        "hide_others": "Nascondi Altre",
        "show_all": "Mostra Tutte",
        "window_menu": "Finestra",
        "help_menu": "Aiuto",
        "edit_menu": "Modifica",
        "undo": "Annulla",
        "redo": "Ripristina",
        "cut": "Taglia",
        "copy": "Copia",
        "paste": "Incolla",
        "select_all": "Seleziona Tutto",
        "minimize": "Riduci a icona",
        "leave_at": "Partenza alle {time}",
        "travel_suffix": "viaggio",
        "next_event_label": "Prossimo: {time} — {title}",

        # Settings Categories Navigation
        "settings_categories_header": "CATEGORIE IMPOSTAZIONI",
        "settings_cat_reminders": "Promemoria & Tempi",
        "settings_cat_reminders_sub": "Anticipi e profili",
        "settings_cat_presence": "Presenza Smart",
        "settings_cat_presence_sub": "Arrivo e chiamate",
        "settings_cat_calendars": "Sorgenti Calendari",
        "settings_cat_calendars_sub": "Calendari collegati",
        "settings_cat_commute": "Percorsi & Viaggio",
        "settings_cat_commute_sub": "Partenza ed ETA",
        "settings_cat_preferences": "Preferenze App",
        "settings_cat_preferences_sub": "Generali e aggiornamenti",

        # Settings Card 1: Timing & Stages
        "settings_timing_title": "⏱️ Tempi di Preavviso & Notifiche Scaglionate",
        "settings_timing_subtitle": "Seleziona le finestre di avviso per ricevere notifiche progressive in anticipo.",
        "settings_quick_presets": "⚡ Profili Rapidi:",
        "preset_relaxed": "🧘 Rilassato",
        "preset_standard": "⚡ Standard",
        "preset_intensive": "🚨 Intensivo",
        "settings_video_meetings": "📹 Riunioni Video",
        "settings_video_meetings_desc": "Avviso prima dell'inizio della riunione (0m sempre attivo)",
        "settings_general_events": "📅 Eventi Generali",
        "settings_general_events_desc": "Avviso prima dell'orario di inizio (0m sempre attivo)",
        "settings_travel_trips": "🚗 Viaggi & Spostamenti",
        "settings_travel_trips_desc": "Avviso prima dell'orario di partenza (0m sempre attivo)",

        # Settings Card 2: ETA & Departure Address
        "settings_eta_title": "📍 Indirizzo di Partenza & Calcolo Percorsi (ETA)",
        "settings_eta_subtitle": "Calcola durata del tragitto e orario di partenza in tempo reale per Mezzi Pubblici, Auto, A Piedi o Bici.",
        "settings_starting_address": "🏠 Indirizzo di Partenza (Origine)",
        "settings_address_placeholder": "Cerca indirizzo, campus o luogo (es. Corso Duca degli Abruzzi 24, Torino)",
        "settings_address_format_hint": "💡 Formato: Via e Civico, Città, CAP, Stato (es. Corso Duca degli Abruzzi 24, 10129 Torino, Italia)",
        "settings_address_suggest_hint": "💡 Digita per cercare indirizzi. Clicca un suggerimento o Salva direttamente.",
        "settings_address_verified": "✓ Verificato sulla mappa",
        "settings_address_not_found": "⚠️ Indirizzo non trovato sulla mappa",
        "settings_address_searching": "🔍 Ricerca sulla mappa...",
        "settings_address_view_map": "🗺️ Mappa",
        "settings_address_verify_btn": "🔍 Verifica",
        "settings_address_incomplete_warning": "⚠️ Inserisci via, numero civico e città per un calcolo accurato dell'ETA.",
        "settings_address_error_invalid": "❌ Formato indirizzo non valido. Richiesto: Via, Civico, Città (es. Corso Duca degli Abruzzi 24, 10129 Torino)",
        "settings_address_error_btn": "❌ Formato Errato",
        "settings_save_location": "💾 Salva Posizione",
        "settings_exam_location": "🎓 Università & Campus Esami",
        "settings_exam_location_placeholder": "Scrivi nome università o campus (es. Politecnico di Milano, Sapienza, Bocconi...)",
        "settings_exam_location_hint": "💡 Scrivi il nome di qualsiasi università o sede. Assegnata agli esami per calcolare percorsi ed ETA.",
        "settings_exam_campus_presets": "Sedi Rapide:",
        "campus_polito_main": "🏛️ PoliTO Centrale",
        "campus_polito_mirafiori": "🏛️ Mirafiori",
        "campus_polito_lingotto": "🏛️ Lingotto",
        "campus_unito": "🏛️ UniTO",
        "settings_exam_save": "💾 Salva Sede Esami",
        "provider_exam": "Esame Universitario 🎓",
        "settings_transport_calc": "🚦 Mezzo di Trasporto per il Calcolo del Percorso",
        "settings_public_transit": "🚆 Mezzi Pubblici",
        "settings_driving_mode": "🚗 Automobile",
        "settings_cycling_mode": "🚲 Bicicletta",
        "settings_walking_mode": "🚶 A Piedi",
        "settings_address_edit": "Modifica",
        "settings_route_title": "Percorso & Navigazione",
        "settings_departure_buffer": "Margine di anticipo partenza",
        "settings_buffer_hint_transit": "Tempo di transito in stazione",
        "settings_buffer_hint_driving": "Tempo di parcheggio e a piedi",
        "settings_buffer_hint_cycling": "Tempo di sosta e custodia bici",
        "settings_buffer_hint_walking": "Solitamente non necessario",
        "buffer_0m": "0 minuti (ETA Esatta)",
        "buffer_5m": "5 minuti",
        "buffer_10m_rec": "10 minuti (Consigliato)",
        "buffer_15m": "15 minuti",
        "buffer_20m": "20 minuti",
        "buffer_30m": "30 minuti",

        # Settings Card: Smart Presence & Arrival Detection
        "settings_arrival_title": "📍 Rilevamento Presenza & Arrivo Smart",
        "settings_arrival_subtitle": "Silenzia automaticamente i promemoria quando sei già in chiamata o sul posto.",
        "settings_arrival_enable": "Abilita Rilevamento Presenza e Arrivo Smart",
        "settings_arrival_enable_sub": "Silenzia i promemoria quando sei già in chiamata o sei arrivato in sede",
        "settings_arrival_calls": "Rilevamento Videochiamate Attive",
        "settings_arrival_calls_sub": "Silenzia i banner quando Zoom, Teams, Webex, Skype o Slack sono attivi",
        "settings_arrival_wifi": "Rilevamento Reti Wi-Fi Sede & Campus",
        "settings_arrival_wifi_sub": "Silenzia i promemoria delle lezioni quando sei connesso al Wi-Fi universitario o d'ufficio",
        "settings_arrival_diagnostics_title": "Diagnostica live & Stato presenza:",
        "settings_arrival_current_wifi": "Wi-Fi attuale:",
        "settings_arrival_status_matched": "Sede riconosciuta ✅",
        "settings_arrival_status_unmatched": "Rete standard",
        "settings_arrival_status_disconnected": "Disconnesso",
        "settings_arrival_active_call": "App chiamata attiva:",
        "settings_arrival_no_call": "Nessuna attiva",
        "settings_arrival_ssids_label": "SSID Wi-Fi sede monitorati (separati da virgola):",
        "settings_arrival_ssids_placeholder": "eduroam, polito, campus, universit, studenti...",
        "settings_arrival_ssids_hint": "💡 Quando sei connesso a queste reti Wi-Fi, i promemoria per lezioni o eventi in sede vengono silenziati automaticamente.",
        "settings_arrival_save_btn": "💾 Salva SSID",
        "settings_arrival_reset_btn": "↺ Ripristina Predefiniti",
        "settings_arrival_refresh_btn": "🔄 Verifica Ora",
        "settings_arrival_summary_title": "Stato Attuale:",
        "settings_arrival_summary_normal": "⚪ Modalità Normale — Tutti i banner promemoria voleranno come da programma.",
        "settings_arrival_summary_call": "🟢 In Chiamata — Videochiamata attiva ({app}) rilevata. I promemoria riunione sono silenziati.",
        "settings_arrival_summary_venue": "🟢 In Sede — Connesso al Wi-Fi riconosciuto ({ssid}). Promemoria lezioni ed eventi sono silenziati.",
        "settings_arrival_summary_disabled": "⏸️ Rilevamento in Pausa — I controlli automatici di arrivo sono attualmente disabilitati.",
        "settings_arrival_add_current_wifi": "➕ Aggiungi '{ssid}' ai Wi-Fi di Sede",
        "settings_arrival_added_wifi": "✓ '{ssid}' Aggiunto alla Lista Sedi!",
        "agenda_arrived_badge": "Presente",
        "agenda_in_call_badge": "In Chiamata",
        "agenda_on_site_badge": "In Sede",
        "agenda_ended_badge": "Concluso",
        "agenda_concluded": "Completato",
        "agenda_cancelled_badge": "Annullato",
        "agenda_cancelled": "Annullato",

        # Settings Card 3: Calendars
        "settings_calendars_title": "📅 Calendari di Sistema Inclusi",
        "settings_calendars_subtitle": "Seleziona quali calendari locali, iCloud o Google monitorare per i promemoria.",
        "settings_all_cals_monitored": "Tutti i calendari disponibili sono attualmente monitorati.",

        # Settings Card 4: System & Diagnostics
        "settings_system_lang_diag": "⚙️ Sistema, Lingua & Diagnostica",
        "settings_system_lang": "⚙️ Sistema & Lingua",
        "settings_lang_selector_label": "🌐 Lingua dell'Applicazione / Language:",
        "settings_autostart_mac": "🚀 Avvia FlightDeck automaticamente all'accesso macOS",
        "settings_mute_lessons": "🤫 Silenzia il suono del banner durante le lezioni universitarie",
        "settings_debug_mode": "🐛 Abilita Modalità Sviluppatore & Diagnostica Debug",
        "settings_config_json": "📝 Config JSON",
        "settings_view_logs": "📄 Visualizza Log",
        "settings_log_folder": "📂 Cartella Log",
        "settings_update_ready": "FlightDeck v{version}  •  Pronto",
        "settings_install_update_now": "⚡ Installa Aggiornamento Ora",

        # Hangar Tab
        "hangar_header_title": "✈️ Hangar Voli & Officina Piloti",
        "hangar_header_subtitle": "Configura i piloti alati, personalizza le uniformi e perfeziona le parole chiave.",
        "hangar_filter_all": "🌟 Tutti ({count})",
        "hangar_filter_productivity": "💼 Produttività",
        "hangar_filter_lifestyle": "🎯 Lifestyle",
        "hangar_filter_commute": "🚗 Spostamenti & Eventi",
        "hangar_filter_general": "⚙️ Generale",
        "hangar_test_chime": "🔔 Prova Suono",
        "hangar_surprise_me": "🎲 A Sorpresa",
        "hangar_reset_presets": "🔄 Ripristina Predefiniti",
        "hangar_animal_mascot": "Mascotte Animale:",
        "hangar_active_pilot_label": "Pilota Attivo",
        "hangar_test_btn": "🚀 Prova Volo",
        "hangar_keywords_label": "🏷️ Parole Chiave Trigger",
        "hangar_keywords_toggle_btn": "🏷️ Parole chiave ({count}) ▾",
        "hangar_keywords_toggle_btn_open": "🏷️ Parole chiave ({count}) ▴",
        "hangar_keywords_drawer_title": "🏷️ Parole chiave per {category}",
        "hangar_keywords_drawer_subtitle": "Gli eventi con queste parole chiave attiveranno automaticamente questa categoria e mascotte.",
        "hangar_keywords_drawer_hide": "▲ Chiudi",
        "hangar_keywords_add_placeholder": "Aggiungi parola chiave (es. padel, sushi)...",
        "hangar_keywords_add_btn": "+ Aggiungi",
        "hangar_keywords_reset_btn": "↺ Ripristina",
        "hangar_keywords_custom_title": "✨ I Tuoi Trigger Personalizzati",
        "hangar_keywords_custom_active": "({count} attivi)",
        "hangar_keywords_custom_empty": "Nessun trigger personalizzato. Aggiungi sopra corsi, aule o parole chiave!",
        "hangar_keywords_presets_toggle_show": "🔒 Preset Predefiniti ({count})  ▾  [Mostra Predefiniti]",
        "hangar_keywords_presets_toggle_hide": "🔒 Preset Predefiniti ({count})  ▴  [Nascondi Predefiniti]",
        "hangar_keywords_add_custom_btn": "+ Aggiungi Trigger",
        "hangar_keywords_reset_to_defaults": "↺ Ripristina Predefiniti",
        "hangar_keywords_add_placeholder_custom": "Aggiungi parola chiave personalizzata (es. aula 3b, politecnico)...",
        "hangar_subcat_study": "📖 Studio Autonomo",
        "hangar_subcat_class": "🏫 Lezioni & Corsi",
        "hangar_subcat_exam": "🎓 Esami & Appelli",
        "hangar_subcat_study_guide": "💡 Countdown motivazionali ('Apri i libri!') e timer concentrazione per studio individuale, compiti e ripasso.",
        "hangar_subcat_class_guide": "💡 Rileva automaticamente Aula e Docente nel calendario con mappa del campus e indicazioni per la classe.",
        "hangar_subcat_exam_guide": "💡 Allarmi prioritari per appelli ed esoneri con pulsante per aula e appunti d'esame.",
        "hangar_test_study_btn": "🚀 Prova Notifica Studio",
        "hangar_test_class_btn": "🚀 Prova Notifica Lezione",
        "hangar_test_exam_btn": "🚀 Prova Notifica Esame",
        "hangar_subcat_preview_tag": "⚡ ANTEPRIMA BANNER IN TEMPO REALE",
        "hangar_subcat_preview_hint": "Simulazione in tempo reale del banner di avviso all'attivazione",
        "hangar_subcat_test_btn": "🚀 Testa Questo Avviso",
        "hangar_subcat_keywords_heading": "🏷️ Parole Chiave Trigger per {subcat}:",
        "hangar_subcat_sim_study_title": "Sessione di Studio Individuale - Biblioteca",
        "hangar_subcat_sim_study_btn": "⚡ TEMPO DI STUDIARE! 📖",
        "hangar_subcat_sim_study_badge1": "💡 Studio Individuale",
        "hangar_subcat_sim_study_badge2": "📖 Focus Biblioteca",
        "hangar_subcat_sim_class_title": "Lezione di Reti Neurali & AI (Aula 3B)",
        "hangar_subcat_sim_class_btn": "🏫 AULA 3B & NOTE",
        "hangar_subcat_sim_class_badge1": "📍 Aula: Aula 3B",
        "hangar_subcat_sim_class_badge2": "👨‍🏫 Prof. Rossi",
        "hangar_subcat_sim_exam_title": "Esame di Fisica Generale - Appello Orale (Aula Magna)",
        "hangar_subcat_sim_exam_btn": "🎓 AULA MAGNA & NOTE",
        "hangar_subcat_sim_exam_badge1": "🚨 ESAME PRIORITARIO",
        "hangar_subcat_sim_exam_badge2": "📍 Sede: Aula Magna",
        "hangar_subcat_sim_in_10m": "⏱️ Tra 10 min",
        "hangar_subcat_mascot_sync": "🔗 Come Pilota Accademico",
        "hangar_subcat_mascot_label": "Mascotte per questo tipo:",
        "hangar_intel_title_study": "🎯 Modalità Studio Individuale & Focus",
        "hangar_intel_title_class": "🏫 Instradamento Intelligente Lezioni & Aule",
        "hangar_intel_title_exam": "🚨 Allarmi Prioritari per Esami & Prove",
        "hangar_intel_badge_study_1": "⏱️ Countdown Focus 10 min",
        "hangar_intel_badge_study_2": "📚 Rilevamento Libri & Compiti",
        "hangar_intel_badge_study_3": "🔇 Chime Studio Discreto",
        "hangar_intel_badge_class_1": "📍 Rileva Aula Automatica (es. Aula 3B)",
        "hangar_intel_badge_class_2": "👨‍🏫 Identifica il Docente",
        "hangar_intel_badge_class_3": "🗺️ Navigazione Campus",
        "hangar_intel_badge_exam_1": "🚨 Sirena Prioritaria Esame",
        "hangar_intel_badge_exam_2": "🏛️ Indicazione Aula d'Esame",
        "hangar_intel_badge_exam_3": "⏰ Countdown Critico & Avviso Forte",
        "hangar_change_pilot_btn": "Cambia Pilota",
        "animal_duck": "🦆 Anatra Aviatrice",
        "animal_owl": "🦉 Gufo Accademico",
        "animal_bunny": "🐰 Coniglio Ingegnoso",
        "animal_platypus": "🕵️‍♂️ Ornitorinco Segreto",
        "animal_squirrel": "🐿️ Scoiattolo Hyper",
        "animal_fox": "🦊 Volpe Tattica",
        "animal_penguin": "🐧 Pinguino Elegante",
        "animal_panda": "🐼 Panda Zen",
        "cat_study_title": "🎓 Università & Sessioni di Studio",
        "cat_study_desc": "Lezioni, esami, studio individuale, compiti e tesi.",
        "cat_food_title": "🍕 Pranzo, Cena & Ristoranti",
        "cat_food_desc": "Cene, pranzi, pizzerie e percorsi cibo.",
        "cat_travel_title": "✈️ Viaggi, Voli & Treni",
        "cat_travel_desc": "Aeroporti, voli aerei, treni ad alta velocità e viaggi.",
        "cat_sport_title": "🏋️ Palestra, Fitness & Sport",
        "cat_sport_desc": "Allenamenti, crossfit, padel, tennis e corsa.",
        "cat_in_person_title": "🏎️ Appuntamenti di Persona & Spostamenti",
        "cat_in_person_desc": "Visite mediche, dentista e navigazione in tempo reale.",
        "cat_health_title": "🌸 Benessere & Terapia",
        "cat_health_desc": "Sedute Serenis, yoga, meditazione e relax.",
        "cat_work_title": "💼 Lavoro & Ufficio",
        "cat_work_desc": "Turni, riunioni con clienti, standup, sprint review e ufficio.",
        "cat_concert_title": "🎸 Concerti, Spettacoli & Musica dal Vivo",
        "cat_concert_desc": "Musica dal vivo, festival, tour nei palasport, teatri e biglietti.",
        "cat_bill_title": "💳 Bollette, Affitto & Pagamenti",
        "cat_bill_desc": "Affitto, bollette, abbonamenti, fatture, tasse e scadenze.",
        "cat_general_title": "⏰ Riunioni Generali & Promemoria",
        "cat_general_desc": "Videoconferenze (Meet, Zoom, Teams) e promemoria.",
        "cal_category_mapping": "Mappatura Categoria",
        "cal_cat_auto": "✨ Riconoscimento Automatico",
        "cal_cat_study": "🎓 Studio & Università",
        "cal_cat_food": "🍕 Cibo & Ristoranti",
        "cal_cat_travel": "✈️ Viaggi & Spostamenti",
        "cal_cat_sport": "🏋️ Palestra & Sport",
        "cal_cat_in_person": "🏎️ Di Persona",
        "cal_cat_health": "🌸 Benessere & Terapia",
        "cal_cat_work": "💼 Lavoro & Ufficio",
        "cal_cat_concert": "🎸 Concerti & Live",
        "cal_cat_bill": "💳 Bollette & Affitto",
        "cal_cat_general": "⏰ Generale",
        "banner_mark_paid": "✅ Segna Pagato",
        "banner_already_paid": "✅ Pagato",
        "banner_pay_now": "💳 Paga Ora",
        "settings_bill_reminders_title": "💳 Promemoria Ricorrenti Bollette & Affitto",
        "settings_bill_reminders_desc": "Ripeti le notifiche per bollette e affitto fino a quando non vengono pagate.",
        "settings_bill_interval_label": "Frequenza Promemoria:",
    }
}

_locale_observer = None

def init_system_locale_listener():
    """Listens for macOS system language/locale change notifications to dynamically update UI."""
    if sys.platform != "darwin":
        return
    global _locale_observer
    if _locale_observer is not None:
        return
    try:
        import Foundation
        import objc
        from core.services.event_bus import event_bus

        class SystemLocaleObserver(Foundation.NSObject):
            def localeDidChange_(self, notification):
                from core.services.config_service import config
                if config.get("language", "system") == "system":
                    logger.info("macOS System Locale changed, publishing CONFIG_CHANGED for language.")
                    event_bus.publish("CONFIG_CHANGED", key="language", value="system")

        _locale_observer = SystemLocaleObserver.alloc().init()
        center = Foundation.NSNotificationCenter.defaultCenter()
        center.addObserver_selector_name_object_(
            _locale_observer,
            objc.selector(_locale_observer.localeDidChange_, signature=b"v@:@"),
            Foundation.NSCurrentLocaleDidChangeNotification,
            None
        )
    except Exception as e:
        logger.debug(f"Could not register system locale observer: {e}")


def detect_system_language() -> str:
    """Detects the operating system's preferred language code ('it' or 'en')."""
    # macOS native detection (avoid searching/importing AppKit on Linux/Ubuntu)
    if sys.platform == "darwin":
        # 1. macOS NSUserDefaults AppleLanguages
        try:
            import Foundation
            user_defaults = Foundation.NSUserDefaults.standardUserDefaults()
            apple_langs = user_defaults.objectForKey_("AppleLanguages")
            if apple_langs and len(apple_langs) > 0:
                first_lang = str(apple_langs[0]).lower()
                if first_lang.startswith("it") or "it_" in first_lang or "it-" in first_lang:
                    return "it"
                elif first_lang.startswith("en") or "en_" in first_lang or "en-" in first_lang:
                    return "en"
        except Exception:
            pass

        # 2. macOS native preferred language detection via PyObjC
        try:
            import AppKit
            langs = AppKit.NSLocale.preferredLanguages()
            if langs and len(langs) > 0:
                primary = str(langs[0]).lower()
                if primary.startswith("it") or "it_" in primary or "it-" in primary:
                    return "it"
                elif primary.startswith("en") or "en_" in primary or "en-" in primary:
                    return "en"
        except Exception:
            pass

        # 3. macOS currentLocale languageCode
        try:
            import AppKit
            loc = AppKit.NSLocale.currentLocale()
            if loc:
                code = loc.languageCode() if hasattr(loc, "languageCode") else None
                if code and str(code).lower().startswith("it"):
                    return "it"
                ident = loc.localeIdentifier() if hasattr(loc, "localeIdentifier") else None
                if ident and str(ident).lower().startswith("it"):
                    return "it"
        except Exception:
            pass

    # 4. Linux environment / locale detection
    for env_var in ["LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"]:
        val = os.environ.get(env_var)
        if val:
            val_low = val.lower()
            if val_low.startswith("it") or "it_" in val_low or "it-" in val_low:
                return "it"
            if val_low.startswith("en") or "en_" in val_low or "en-" in val_low:
                return "en"

    # 5. Python standard locale
    try:
        loc = locale.getlocale()
        if loc and loc[0]:
            if loc[0].lower().startswith("it"):
                return "it"
    except Exception:
        pass

    return "en"


def get_active_language(forced_lang: Optional[str] = None) -> str:
    """Resolves the current active language ('en' or 'it') taking user config into account."""
    if forced_lang and forced_lang in ("en", "it"):
        return forced_lang

    try:
        from core.services.config_service import config
        configured = str(config.get("language", "system")).lower()
        if configured in ("it", "italian", "italiano"):
            return "it"
        if configured in ("en", "english"):
            return "en"
    except Exception:
        pass

    return detect_system_language()


def t(key: str, lang: Optional[str] = None, default: Optional[str] = None, **kwargs) -> str:
    """Translates a key into the active language with optional parameter interpolation."""
    active_lang = lang or get_active_language()
    dict_for_lang = TRANSLATIONS.get(active_lang) or TRANSLATIONS["en"]

    fallback = default if default is not None else key
    template = dict_for_lang.get(key)
    if template is None:
        template = TRANSLATIONS["en"].get(key, fallback)

    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    return template
