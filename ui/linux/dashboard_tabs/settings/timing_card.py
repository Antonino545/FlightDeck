"""
Card 1: Notification Lead Times & Staged Reminders for Linux Flight Deck.
"""

from PyQt6.QtWidgets import (
    QFrame, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
)
from PyQt6.QtCore import Qt

from core.services.config_service import config
from core.services.event_bus import event_bus
from core.services.language_service import t
from ui.linux.animated_widgets import ToggleSwitch


class TimingCardWidget(QFrame):
    """Timing presets and staged notification chips."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")

        tc_layout = QVBoxLayout(self)
        tc_layout.setContentsMargins(18, 14, 18, 14)
        tc_layout.setSpacing(10)

        tc_title = QLabel("⏱️ Notification Lead Times & Staged Reminders", self)
        tc_title.setObjectName("CardTitle")
        tc_sub = QLabel("Select reminder alert windows to receive progressive notifications ahead of time.", self)
        tc_sub.setObjectName("CardSub")
        tc_layout.addWidget(tc_title)
        tc_layout.addWidget(tc_sub)

        # 1-Click Timing Presets Row
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        preset_lbl = QLabel("<b>⚡ Quick Presets:</b>", self)
        preset_lbl.setStyleSheet("color: #a6adc8; font-size: 11.5px;")
        preset_row.addWidget(preset_lbl)

        presets = [
            ("🧘 Relaxed", [15, 5, 0], [15, 5, 0], [45, 15, 0]),
            ("⚡ Standard", [20, 10, 5, 2, 0], [20, 10, 5, 2, 0], [45, 30, 15, 5, 2, 0]),
            ("🚨 Intensive", [30, 20, 15, 10, 5, 2, 0], [30, 20, 15, 10, 5, 2, 0], [60, 45, 30, 15, 5, 2, 0]),
        ]

        self.stage_buttons = {}

        def _apply_preset(p_meetings, p_general, p_travel):
            config.set("meeting_reminder_stages", p_meetings)
            config.set("general_reminder_stages", p_general)
            config.set("travel_reminder_stages", p_travel)
            for (k, v), btn in self.stage_buttons.items():
                if k == "meeting_reminder_stages":
                    btn.setChecked(v in p_meetings)
                elif k == "general_reminder_stages":
                    btn.setChecked(v in p_general)
                elif k == "travel_reminder_stages":
                    btn.setChecked(v in p_travel)

        for p_name, p_m, p_g, p_t in presets:
            p_btn = QPushButton(p_name, self)
            p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            p_btn.setStyleSheet("""
                QPushButton {
                    background: #242438;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 7px;
                    padding: 4px 10px;
                    font-size: 11.5px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background: #313244;
                    border-color: #89b4fa;
                    color: #89b4fa;
                }
            """)
            def _make_preset_cb(pm=p_m, pg=p_g, pt=p_t):
                return lambda: _apply_preset(pm, pg, pt)
            p_btn.clicked.connect(_make_preset_cb())
            preset_row.addWidget(p_btn)

        preset_row.addStretch()
        tc_layout.addLayout(preset_row)

        div_p = QFrame(self)
        div_p.setFrameShape(QFrame.Shape.HLine)
        div_p.setStyleSheet("color: #313244; background: #313244;")
        div_p.setFixedHeight(1)
        tc_layout.addWidget(div_p)

        def _build_stage_row(title, subtitle, config_key, default_stages, active_accent="#cba6f7"):
            sec_box = QVBoxLayout()
            sec_box.setSpacing(4)

            t_l = QLabel(title, self)
            t_l.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #cdd6f4;")
            s_l = QLabel(subtitle, self)
            s_l.setStyleSheet("font-size: 11px; color: #a6adc8;")
            sec_box.addWidget(t_l)
            sec_box.addWidget(s_l)

            row = QHBoxLayout()
            row.setSpacing(6)

            all_stages = [60, 45, 30, 20, 15, 10, 5, 2]
            current_stages = set(config.get(config_key, default_stages))

            for stg in all_stages:
                btn = QPushButton(f"{stg}m", self)
                btn.setCheckable(True)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setChecked(stg in current_stages)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #242438;
                        color: #cdd6f4;
                        border: 1px solid #45475a;
                        border-radius: 7px;
                        padding: 5px 10px;
                        font-size: 11.5px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background: #313244;
                        border-color: {active_accent};
                    }}
                    QPushButton:checked {{
                        background: {active_accent};
                        color: #11111b;
                        font-weight: bold;
                        border: 1px solid {active_accent};
                    }}
                """)
                def _toggled(checked, val=stg, ck=config_key, def_s=default_stages):
                    stages = set(config.get(ck, def_s))
                    if checked:
                        stages.add(val)
                    else:
                        stages.discard(val)
                    stages.add(0)
                    config.set(ck, sorted(list(stages), reverse=True))

                btn.toggled.connect(_toggled)
                self.stage_buttons[(config_key, stg)] = btn
                row.addWidget(btn)

            row.addStretch()
            sec_box.addLayout(row)
            return sec_box

        tc_layout.addLayout(_build_stage_row("📹 Video Meetings", "Reminders for Zoom, Google Meet, Microsoft Teams, etc.", "meeting_reminder_stages", [20, 10, 5, 2, 0], "#cba6f7"))
        tc_layout.addLayout(_build_stage_row("📅 General Events", "Tasks, personal appointments, syncs, and routines.", "general_reminder_stages", [20, 10, 5, 2, 0], "#89b4fa"))
        tc_layout.addLayout(_build_stage_row("🚗 Travel & Trips", "Reminders ahead of calculated departure times for in-person destinations.", "travel_reminder_stages", [45, 30, 15, 5, 2, 0], "#fab387"))

        div_bill = QFrame(self)
        div_bill.setFrameShape(QFrame.Shape.HLine)
        div_bill.setStyleSheet("color: #313244; background: #313244;")
        div_bill.setFixedHeight(1)
        tc_layout.addWidget(div_bill)

        bill_box = QVBoxLayout()
        bill_box.setSpacing(6)

        bill_head_row = QHBoxLayout()
        bill_head_row.setSpacing(10)

        bill_text_box = QVBoxLayout()
        bill_text_box.setSpacing(2)
        b_t = QLabel(f"💳 {t('settings_bill_reminders_title', default='Recurring Bill & Rent Reminders')}", self)
        b_t.setStyleSheet("font-size: 12.5px; font-weight: bold; color: #cdd6f4;")
        b_s = QLabel(t('settings_bill_reminders_desc', default='Periodically remind until marked paid or actioned.'), self)
        b_s.setStyleSheet("font-size: 11px; color: #a6adc8;")
        bill_text_box.addWidget(b_t)
        bill_text_box.addWidget(b_s)
        bill_head_row.addLayout(bill_text_box, stretch=1)

        bill_sw = ToggleSwitch(checked=bool(config.get("enable_bill_reminders", True)), parent=self)
        bill_sw.setFixedSize(50, 26)
        def _on_bill_toggled(checked):
            config.set("enable_bill_reminders", checked)
            try:
                event_bus.publish("CONFIG_CHANGED", key="enable_bill_reminders", value=checked)
            except Exception:
                pass
        bill_sw.toggled = _on_bill_toggled
        bill_head_row.addWidget(bill_sw)
        bill_box.addLayout(bill_head_row)

        bill_interval_row = QHBoxLayout()
        bill_interval_row.setSpacing(6)
        bill_interval_opts = [(30, "30m"), (60, "1h"), (120, "2h"), (240, "4h")]
        curr_int = int(config.get("bill_reminder_interval_minutes", 120))

        self.bill_interval_buttons = []
        for val, lbl in bill_interval_opts:
            btn = QPushButton(lbl, self)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(val == curr_int)
            btn.setStyleSheet("""
                QPushButton {
                    background: #242438;
                    color: #cdd6f4;
                    border: 1px solid #45475a;
                    border-radius: 7px;
                    padding: 5px 12px;
                    font-size: 11.5px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background: #313244;
                    border-color: #a6e3a1;
                }
                QPushButton:checked {
                    background: #a6e3a1;
                    color: #11111b;
                    font-weight: bold;
                    border: 1px solid #a6e3a1;
                }
            """)
            def _make_int_cb(target_val=val):
                def _cb():
                    config.set("bill_reminder_interval_minutes", target_val)
                    try:
                        event_bus.publish("CONFIG_CHANGED", key="bill_reminder_interval_minutes", value=target_val)
                    except Exception:
                        pass
                    for b, v in self.bill_interval_buttons:
                        b.setChecked(v == target_val)
                return _cb
            btn.clicked.connect(_make_int_cb(val))
            self.bill_interval_buttons.append((btn, val))
            bill_interval_row.addWidget(btn)

        bill_interval_row.addStretch()
        bill_box.addLayout(bill_interval_row)
        tc_layout.addLayout(bill_box)
