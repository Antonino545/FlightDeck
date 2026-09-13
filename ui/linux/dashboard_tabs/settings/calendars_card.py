import sys
import threading

from PyQt6.QtWidgets import (
    QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
    QComboBox, QSizePolicy, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.services.config_service import config
from core.services.calendar_service import calendar_service
from core.services.event_bus import event_bus
from core.services.language_service import t
from ui.linux.theme import get_combo_box_qss


class CalendarsCardWidget(QFrame):
    """Monitored system calendar sources filter and direct category mapping."""

    calendars_loaded = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self._editing_url = None

        cc_layout = QVBoxLayout(self)
        cc_layout.setContentsMargins(18, 14, 18, 14)
        cc_layout.setSpacing(10)

        cc_title = QLabel(f"📅 {t('settings_calendars')}", self)
        cc_title.setObjectName("CardTitle")
        cc_sub = QLabel("Select which calendars to monitor and optionally link each directly to an event category.", self)
        cc_sub.setObjectName("CardSub")
        cc_layout.addWidget(cc_title)
        cc_layout.addWidget(cc_sub)

        # On Windows, provide the Google Calendar setup guide & URL manager
        if sys.platform == "win32":
            self._build_windows_setup_guide(cc_layout)

        self.content_host = QWidget(self)
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        loading_lbl = QLabel("Loading calendars...", self.content_host)
        loading_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.content_layout.addWidget(loading_lbl)
        cc_layout.addWidget(self.content_host)

        self.calendars_loaded.connect(self._render_calendars)
        threading.Thread(target=self._load_calendars, daemon=True).start()

    def _build_windows_setup_guide(self, parent_layout):
        """Adds interactive multi-provider setup guide, custom naming, and duplicate prevention on Windows."""
        self._provider_guides = {
            "google": (
                "🌐 Google Calendar (Spark / Web)",
                "1. Open <b>calendar.google.com</b> on your browser.<br>"
                "2. Click the <b>3 dots</b> next to your calendar on the left → <b>Settings and sharing</b>.<br>"
                "3. Scroll down to <b>'Integrate calendar'</b> → Copy the <b>'Secret address in iCal format'</b>.<br>"
                "4. Paste the URL below with a custom name and click <b>Add Calendar</b>."
            ),
            "icloud": (
                "🍎 Apple iCloud (iPhone / Mac / Spark)",
                "1. Open <b>icloud.com/calendar</b> or the Calendar app on your iPhone or Mac.<br>"
                "2. Click the <b>Share icon</b> next to your calendar → Turn on <b>Public / Shareable Calendar</b>.<br>"
                "3. Copy the <b>webcal://...</b> link provided.<br>"
                "4. Paste the link below with a custom name and click <b>Add Calendar</b>."
            ),
            "outlook": (
                "💼 Microsoft Outlook / 365 (Web / Spark)",
                "1. Go to <b>outlook.office.com</b> → Click <b>Settings (⚙️)</b> → <b>Calendar</b> → <b>Shared calendars</b>.<br>"
                "2. Under <b>'Publish a calendar'</b>, select your calendar and choose 'Can view all details' → Click <b>Publish</b>.<br>"
                "3. Copy the generated <b>ICS link</b>.<br>"
                "4. Paste the link below with a custom name and click <b>Add Calendar</b>."
            ),
            "other": (
                "🔗 Other Calendar Feeds (.ics / webcal)",
                "1. Copy any public or private <b>.ics / webcal:// feed URL</b> from your provider (University, Fastmail, Nextcloud, etc.).<br>"
                "2. Paste the link below, assign an optional name (e.g. 'University', 'Work'), and click <b>Add Calendar</b>."
            ),
        }

        # =====================================================================
        # SECTION 1: ADD NEW CALENDAR SOURCE
        # =====================================================================
        add_section = QFrame(self)
        add_section.setStyleSheet("""
            QFrame#AddSection {
                background: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
            }
        """)
        add_section.setObjectName("AddSection")
        as_layout = QVBoxLayout(add_section)
        as_layout.setContentsMargins(14, 12, 14, 12)
        as_layout.setSpacing(10)

        # Section 1 Header
        sec1_header = QLabel("➕ Section 1: Add Calendar Source", add_section)
        sec1_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #89b4fa; border: none; background: transparent;")
        sec1_sub = QLabel("Select your provider below to view instructions, then paste the feed URL.", add_section)
        sec1_sub.setStyleSheet("font-size: 11px; color: #a6adc8; border: none; background: transparent;")
        as_layout.addWidget(sec1_header)
        as_layout.addWidget(sec1_sub)

        # Provider Selector Tabs
        tabs_row = QWidget(add_section)
        tabs_row.setStyleSheet("border: none; background: transparent;")
        t_layout = QHBoxLayout(tabs_row)
        t_layout.setContentsMargins(0, 0, 0, 0)
        t_layout.setSpacing(6)

        self._guide_btns = {}
        tab_defs = [
            ("google", "🌐 Google Calendar"),
            ("icloud", "🍎 Apple iCloud"),
            ("outlook", "💼 Outlook / 365"),
            ("other", "🔗 Other / iCal"),
        ]
        for key, label in tab_defs:
            btn = QPushButton(label, tabs_row)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background: #242438;
                    color: #a6adc8;
                    border: 1px solid #45475a;
                    border-radius: 5px;
                    padding: 5px 10px;
                    font-size: 11px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #313244;
                    color: #cdd6f4;
                }
                QPushButton:checked {
                    background: #313244;
                    color: #89b4fa;
                    font-weight: bold;
                    border: 1px solid #89b4fa;
                }
            """)
            btn.clicked.connect(lambda chk, k=key: self._switch_provider_guide(k))
            t_layout.addWidget(btn)
            self._guide_btns[key] = btn

        as_layout.addWidget(tabs_row)

        # Guide Text Box
        guide_card = QFrame(add_section)
        guide_card.setStyleSheet("""
            QFrame {
                background: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
            }
        """)
        gc_layout = QVBoxLayout(guide_card)
        gc_layout.setContentsMargins(10, 8, 10, 8)
        gc_layout.setSpacing(4)

        self.guide_title = QLabel(guide_card)
        self.guide_title.setStyleSheet("font-weight: bold; font-size: 11.5px; color: #89b4fa; border: none; background: transparent;")
        gc_layout.addWidget(self.guide_title)

        self.guide_desc = QLabel(guide_card)
        self.guide_desc.setTextFormat(Qt.TextFormat.RichText)
        self.guide_desc.setWordWrap(True)
        self.guide_desc.setStyleSheet("color: #bac2de; font-size: 11px; border: none; background: transparent; line-height: 140%;")
        gc_layout.addWidget(self.guide_desc)

        as_layout.addWidget(guide_card)
        self._switch_provider_guide("google")

        # Inputs Form
        inputs_row = QWidget(add_section)
        inputs_row.setStyleSheet("border: none; background: transparent;")
        i_layout = QHBoxLayout(inputs_row)
        i_layout.setContentsMargins(0, 0, 0, 0)
        i_layout.setSpacing(8)

        self.name_input = QLineEdit(inputs_row)
        self.name_input.setFixedWidth(160)
        self.name_input.setPlaceholderText("Calendar Name (optional)")
        self.name_input.setStyleSheet("""
            QLineEdit {
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        i_layout.addWidget(self.name_input)

        self.url_input = QLineEdit(inputs_row)
        self.url_input.setPlaceholderText("Paste calendar feed URL (https://... or webcal://...)")
        self.url_input.setStyleSheet("""
            QLineEdit {
                background: #1e1e2e;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11.5px;
            }
            QLineEdit:focus {
                border-color: #89b4fa;
            }
        """)
        i_layout.addWidget(self.url_input, 1)

        add_btn = QPushButton("➕ Add Calendar", inputs_row)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #89b4fa;
                color: #11111b;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background: #b4befe;
            }
        """)
        add_btn.clicked.connect(self._add_calendar_url)
        i_layout.addWidget(add_btn)
        as_layout.addWidget(inputs_row)

        # Status / Feedback label
        self.status_lbl = QLabel(add_section)
        self.status_lbl.setStyleSheet("font-size: 11px; padding: 2px 4px; border: none; background: transparent;")
        self.status_lbl.setVisible(False)
        as_layout.addWidget(self.status_lbl)

        parent_layout.addWidget(add_section)

        # =====================================================================
        # SECTION 2: CONFIGURED CALENDAR SOURCES
        # =====================================================================
        sources_section = QFrame(self)
        sources_section.setStyleSheet("""
            QFrame#SourcesSection {
                background: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
            }
        """)
        sources_section.setObjectName("SourcesSection")
        ss_layout = QVBoxLayout(sources_section)
        ss_layout.setContentsMargins(14, 12, 14, 12)
        ss_layout.setSpacing(10)

        # Section 2 Header
        self.sec2_header = QLabel("📋 Section 2: Active Calendar Sources", sources_section)
        self.sec2_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #89b4fa; border: none; background: transparent;")
        sec2_sub = QLabel("Manage, rename, or delete your active calendar subscriptions.", sources_section)
        sec2_sub.setStyleSheet("font-size: 11px; color: #a6adc8; border: none; background: transparent;")
        ss_layout.addWidget(self.sec2_header)
        ss_layout.addWidget(sec2_sub)

        # Active URLs container inside Section 2
        self.urls_container = QWidget(sources_section)
        self.urls_container.setStyleSheet("border: none; background: transparent;")
        self.urls_layout = QVBoxLayout(self.urls_container)
        self.urls_layout.setContentsMargins(0, 0, 0, 0)
        self.urls_layout.setSpacing(6)
        ss_layout.addWidget(self.urls_container)

        parent_layout.addWidget(sources_section)

        # Divider before Section 3 (Category mapping)
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #313244; max-height: 1px; margin: 4px 0;")
        parent_layout.addWidget(sep)

        sec3_header = QLabel("🏷️ Section 3: Visibility & Category Mapping", self)
        sec3_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #cdd6f4; border: none; background: transparent; margin-top: 4px;")
        sec3_sub = QLabel("Toggle alerts for individual calendars and assign default pilot categories.", self)
        sec3_sub.setStyleSheet("font-size: 11px; color: #a6adc8; border: none; background: transparent; margin-bottom: 2px;")
        parent_layout.addWidget(sec3_header)
        parent_layout.addWidget(sec3_sub)

        self._refresh_urls_list()

    def _switch_provider_guide(self, key: str):
        for k, btn in self._guide_btns.items():
            btn.setChecked(k == key)
        if key in self._provider_guides:
            title, desc = self._provider_guides[key]
            self.guide_title.setText(f"💡 {title}")
            self.guide_desc.setText(desc)

    @staticmethod
    def _normalize_feed_url(u: str) -> str:
        s = u.strip().rstrip("/")
        if s.startswith("webcal://"):
            s = "https://" + s[len("webcal://"):]
        return s.lower()

    def _add_calendar_url(self):
        url = self.url_input.text().strip()
        name = self.name_input.text().strip()

        if not url:
            self._show_status("⚠️ Please enter a calendar feed URL.", is_error=True)
            return

        # URL scheme validation
        valid_schemes = ("https://", "http://", "webcal://")
        if not any(url.lower().startswith(sch) for sch in valid_schemes) and not url.lower().endswith(".ics"):
            self._show_status("⚠️ Invalid URL. Feed must start with https://, http://, or webcal://", is_error=True)
            return

        norm_url = self._normalize_feed_url(url)
        existing_sources = list(config.get("calendar_urls", []))

        # Duplicate check across all existing calendars
        for src in existing_sources:
            if isinstance(src, dict):
                cur_url = src.get("url", "")
                cur_name = src.get("name", "")
            else:
                cur_url = str(src)
                cur_name = ""

            if self._normalize_feed_url(cur_url) == norm_url:
                self._show_status("⚠️ This calendar URL is already added! Duplicate entries are not allowed.", is_error=True)
                return

            if name and cur_name and cur_name.lower() == name.lower():
                self._show_status(f"⚠️ A calendar named '{name}' already exists. Please choose a unique name.", is_error=True)
                return

        # If name is given, save as dict, otherwise string
        entry = {"name": name, "url": url} if name else url
        existing_sources.append(entry)
        config.set("calendar_urls", existing_sources)

        try:
            event_bus.publish("CONFIG_CHANGED", key="calendar_urls", value=existing_sources)
        except Exception:
            pass

        disp_title = name or url.split("/")[-1].replace(".ics", "") or "Calendar"
        self._show_status(f"✅ Added calendar '{disp_title}'! Synchronizing events in background...", is_error=False)

        self.url_input.clear()
        self.name_input.clear()
        self._refresh_urls_list()
        threading.Thread(target=self._resync_calendars, daemon=True).start()

    def _show_status(self, msg: str, is_error: bool = False):
        color = "#f38ba8" if is_error else "#a6e3a1"
        self.status_lbl.setStyleSheet(f"color: {color}; font-size: 11px; padding: 2px 4px; border: none; background: transparent; font-weight: 500;")
        self.status_lbl.setText(msg)
        self.status_lbl.setVisible(True)

    def _remove_calendar_url(self, target_url: str):
        existing_sources = list(config.get("calendar_urls", []))
        norm_target = self._normalize_feed_url(target_url)

        new_sources = []
        for src in existing_sources:
            src_url = src.get("url", "") if isinstance(src, dict) else str(src)
            if self._normalize_feed_url(src_url) != norm_target:
                new_sources.append(src)

        config.set("calendar_urls", new_sources)
        try:
            event_bus.publish("CONFIG_CHANGED", key="calendar_urls", value=new_sources)
        except Exception:
            pass

        self._show_status("🗑️ Calendar removed.", is_error=False)
        self._refresh_urls_list()
        threading.Thread(target=self._resync_calendars, daemon=True).start()

    def _resync_calendars(self):
        try:
            calendar_service.sync_now()
        except Exception:
            pass
        self._load_calendars()

    def _refresh_urls_list(self):
        while self.urls_layout.count():
            item = self.urls_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        urls = config.get("calendar_urls", [])
        if hasattr(self, "sec2_header"):
            count_str = f"({len(urls)} active)" if urls else "(0 active)"
            self.sec2_header.setText(f"📋 Section 2: Active Calendar Sources {count_str}")

        if not urls:
            empty_lbl = QLabel("No calendar sources configured yet. Use Section 1 above to add a feed.", self.urls_container)
            empty_lbl.setStyleSheet("color: #6c7086; font-size: 11.5px; font-style: italic; padding: 6px 2px;")
            self.urls_layout.addWidget(empty_lbl)
            return

        for item in urls:
            if isinstance(item, dict):
                url_val = item.get("url", "")
                name_val = item.get("name", "")
            else:
                url_val = str(item)
                name_val = ""

            display_name = name_val or url_val.split("/")[-1].replace(".ics", "") or "Custom Calendar"
            display_url = url_val if len(url_val) <= 50 else (url_val[:32] + "..." + url_val[-15:])

            row = QFrame(self.urls_container)
            row.setStyleSheet("""
                QFrame {
                    background: #242438;
                    border: 1px solid #313244;
                    border-radius: 6px;
                    padding: 4px 8px;
                }
            """)
            r_layout = QHBoxLayout(row)
            r_layout.setContentsMargins(6, 4, 6, 4)
            r_layout.setSpacing(10)

            # If this row is in edit mode
            if self._editing_url and self._normalize_feed_url(self._editing_url) == self._normalize_feed_url(url_val):
                edit_input = QLineEdit(row)
                edit_input.setText(name_val or display_name)
                edit_input.setPlaceholderText("Enter custom calendar name")
                edit_input.setStyleSheet("""
                    QLineEdit {
                        background: #181825;
                        color: #cdd6f4;
                        border: 1px solid #89b4fa;
                        border-radius: 5px;
                        padding: 4px 8px;
                        font-size: 11.5px;
                    }
                """)
                r_layout.addWidget(edit_input, 1)

                save_btn = QPushButton("💾 Save", row)
                save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                save_btn.setStyleSheet("""
                    QPushButton {
                        background: #a6e3a1;
                        color: #11111b;
                        font-weight: bold;
                        border: none;
                        border-radius: 5px;
                        padding: 4px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: #94e2d5;
                    }
                """)
                save_btn.clicked.connect(lambda chk, u=url_val, old=name_val, inp=edit_input: self._save_renamed_calendar(u, old, inp.text().strip()))
                edit_input.returnPressed.connect(lambda u=url_val, old=name_val, inp=edit_input: self._save_renamed_calendar(u, old, inp.text().strip()))
                r_layout.addWidget(save_btn)

                cancel_btn = QPushButton("✕ Cancel", row)
                cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                cancel_btn.setStyleSheet("""
                    QPushButton {
                        background: #313244;
                        color: #a6adc8;
                        border: 1px solid #45475a;
                        border-radius: 5px;
                        padding: 4px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: #45475a;
                        color: #cdd6f4;
                    }
                """)
                cancel_btn.clicked.connect(self._cancel_rename)
                r_layout.addWidget(cancel_btn)

            else:
                info_col = QWidget(row)
                info_col.setStyleSheet("background: transparent; border: none;")
                ic_layout = QVBoxLayout(info_col)
                ic_layout.setContentsMargins(0, 0, 0, 0)
                ic_layout.setSpacing(2)

                title_lbl = QLabel(f"📅 {display_name}", info_col)
                title_lbl.setStyleSheet("color: #cdd6f4; font-size: 11.5px; font-weight: bold;")
                ic_layout.addWidget(title_lbl)

                url_lbl = QLabel(display_url, info_col)
                url_lbl.setStyleSheet("color: #a6adc8; font-size: 10px;")
                url_lbl.setToolTip(url_val)
                ic_layout.addWidget(url_lbl)

                r_layout.addWidget(info_col, 1)

                edit_btn = QPushButton("✏️ Rename", row)
                edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                edit_btn.setStyleSheet("""
                    QPushButton {
                        background: #313244;
                        color: #89b4fa;
                        border: 1px solid #45475a;
                        border-radius: 5px;
                        padding: 4px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: #45475a;
                        color: #b4befe;
                        border-color: #89b4fa;
                    }
                """)
                edit_btn.clicked.connect(lambda chk, target=url_val: self._start_rename(target))
                r_layout.addWidget(edit_btn)

                del_btn = QPushButton("🗑️ Remove", row)
                del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                del_btn.setStyleSheet("""
                    QPushButton {
                        background: #313244;
                        color: #f38ba8;
                        border: 1px solid #45475a;
                        border-radius: 5px;
                        padding: 4px 10px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background: #45475a;
                        color: #eba0ac;
                        border-color: #f38ba8;
                    }
                """)
                del_btn.clicked.connect(lambda chk, target=url_val: self._remove_calendar_url(target))
                r_layout.addWidget(del_btn)

            self.urls_layout.addWidget(row)

    def _start_rename(self, target_url: str):
        self._editing_url = target_url
        self._refresh_urls_list()

    def _cancel_rename(self):
        self._editing_url = None
        self._refresh_urls_list()

    def _save_renamed_calendar(self, url_val: str, old_name: str, new_name: str):
        norm_url = self._normalize_feed_url(url_val)
        existing_sources = list(config.get("calendar_urls", []))

        # Duplicate check against other calendars
        if new_name:
            for src in existing_sources:
                if isinstance(src, dict):
                    c_url = src.get("url", "")
                    c_name = src.get("name", "")
                else:
                    c_url = str(src)
                    c_name = ""
                if self._normalize_feed_url(c_url) != norm_url and c_name and c_name.lower() == new_name.lower():
                    self._show_status(f"⚠️ A calendar named '{new_name}' already exists. Please choose a unique name.", is_error=True)
                    return

        updated_sources = []
        for src in existing_sources:
            if isinstance(src, dict):
                c_url = src.get("url", "")
                if self._normalize_feed_url(c_url) == norm_url:
                    updated_sources.append({"name": new_name, "url": c_url} if new_name else c_url)
                else:
                    updated_sources.append(src)
            else:
                c_url = str(src)
                if self._normalize_feed_url(c_url) == norm_url:
                    updated_sources.append({"name": new_name, "url": c_url} if new_name else c_url)
                else:
                    updated_sources.append(src)

        config.set("calendar_urls", updated_sources)

        # Migrate category mapping if present under old name
        if old_name and new_name and old_name != new_name:
            cmap = config.get("calendar_category_map", {})
            if isinstance(cmap, dict) and old_name in cmap:
                cmap = cmap.copy()
                cmap[new_name] = cmap.pop(old_name)
                config.set("calendar_category_map", cmap)

        try:
            event_bus.publish("CONFIG_CHANGED", key="calendar_urls", value=updated_sources)
        except Exception:
            pass

        self._editing_url = None
        self._show_status(f"✅ Renamed calendar to '{new_name or 'Default'}'.", is_error=False)
        self._refresh_urls_list()
        threading.Thread(target=self._resync_calendars, daemon=True).start()

    def _load_calendars(self):
        try:
            self.calendars_loaded.emit(calendar_service.get_available_calendars())
        except Exception:
            self.calendars_loaded.emit([])

    def _render_calendars(self, avail_cals):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not avail_cals:
            empty_lbl = QLabel("All calendar sources are currently monitored.", self.content_host)
            empty_lbl.setStyleSheet("color: #a6adc8; font-size: 12px;")
            self.content_layout.addWidget(empty_lbl)
            empty_lbl.show()
        else:
            list_widget = QWidget(self.content_host)
            list_layout = QVBoxLayout(list_widget)
            list_layout.setContentsMargins(0, 0, 0, 0)
            list_layout.setSpacing(8)

            category_options = [
                ("", t("cal_cat_auto")),
                ("study", t("cal_cat_study")),
                ("work", t("cal_cat_work")),
                ("concert", t("cal_cat_concert")),
                ("food", t("cal_cat_food")),
                ("travel", t("cal_cat_travel")),
                ("sport", t("cal_cat_sport")),
                ("in_person", t("cal_cat_in_person")),
                ("health", t("cal_cat_health")),
                ("general", t("cal_cat_general")),
            ]
            cal_map = config.get("calendar_category_map", {})
            if not isinstance(cal_map, dict):
                cal_map = {}

            for cal in avail_cals:
                c_name = cal.get("name", "Calendar")
                c_enabled = cal.get("enabled", True)
                display_name = c_name.replace("&", "&&")

                row_widget = QWidget(list_widget)
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(10)

                btn = QPushButton(f"📅 {display_name}", row_widget)
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setChecked(c_enabled)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                btn.setStyleSheet("""
                    QPushButton {
                        background: #242438;
                        color: #cdd6f4;
                        border: 1px solid #45475a;
                        border-radius: 7px;
                        padding: 6px 14px;
                        font-size: 11.5px;
                        font-weight: 500;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background: #313244;
                        border-color: #a6e3a1;
                    }
                    QPushButton:checked {
                        background: #313244;
                        color: #a6e3a1;
                        font-weight: bold;
                        border: 1px solid #a6e3a1;
                    }
                """)
                def _cal_toggled(checked, name=c_name):
                    ignored = set(config.get("ignored_calendars", []))
                    if checked:
                        ignored.discard(name)
                    else:
                        ignored.add(name)
                    config.set("ignored_calendars", list(ignored))
                    try:
                        event_bus.publish("CONFIG_CHANGED", key="ignored_calendars", value=list(ignored))
                    except Exception:
                        pass
                btn.toggled.connect(_cal_toggled)
                row_layout.addWidget(btn)

                # Category Mapping Dropdown
                combo = QComboBox(row_widget)
                combo.setFixedHeight(28)
                combo.setFixedWidth(175)
                combo.setStyleSheet(get_combo_box_qss(bg_color="#242438", min_width=175))
                combo.setToolTip(t("cal_category_mapping"))

                mapped_val = cal_map.get(c_name, "")
                sel_idx = 0
                for opt_idx, (cat_val, cat_lbl) in enumerate(category_options):
                    combo.addItem(cat_lbl, cat_val)
                    if cat_val == mapped_val:
                        sel_idx = opt_idx
                combo.setCurrentIndex(sel_idx)

                def _cat_changed(idx_val, name=c_name, cb=combo):
                    val_cat = cb.itemData(idx_val)
                    cmap = config.get("calendar_category_map", {})
                    if not isinstance(cmap, dict):
                        cmap = {}
                    else:
                        cmap = cmap.copy()
                    if val_cat:
                        cmap[name] = val_cat
                    else:
                        cmap.pop(name, None)
                    config.set("calendar_category_map", cmap)
                    try:
                        event_bus.publish("CONFIG_CHANGED", key="calendar_category_map", value=cmap)
                    except Exception:
                        pass
                combo.currentIndexChanged.connect(_cat_changed)
                row_layout.addWidget(combo)

                list_layout.addWidget(row_widget)

            self.content_layout.addWidget(list_widget)
            list_widget.show()
