"""
PyQt6 Hangar Tab for FlightDeck Flight Deck on Linux.
Provides interactive mascot workshop, custom animal outfit combinations,
live vector animation previews, and 1-click test flights.
"""

from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QScrollArea, QFrame, QComboBox, QLineEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter

from core.services.config_service import config
from core.services.event_bus import event_bus
from core.services.language_service import t, get_active_language
from ui.common.theme import get_combo_title
from ui.common.mascot_catalog import ANIMALS, normalize_accessories
from ui.linux.theme import get_combo_box_qss
from ui.linux.components.flow_layout import FlowLayout


def get_animals():
    return list(ANIMALS)


CATEGORIES_DEF = [
    ("study", "cat_study_title", "cat_study_desc", "student", "owl", "#cba6f7"),
    ("work", "cat_work_title", "cat_work_desc", "agent", "penguin", "#89b4fa"),
    ("bill", "cat_bill_title", "cat_bill_desc", "banker", "duck", "#a6e3a1"),
    ("food", "cat_food_title", "cat_food_desc", "chef", "squirrel", "#fab387"),
    ("travel", "cat_travel_title", "cat_travel_desc", "captain", "duck", "#74c7ec"),
    ("sport", "cat_sport_title", "cat_sport_desc", "gym", "bunny", "#f38ba8"),
    ("in_person", "cat_in_person_title", "cat_in_person_desc", "racer", "fox", "#f9e2af"),
    ("health", "cat_health_title", "cat_health_desc", "zen", "panda", "#94e2d5"),
    ("concert", "cat_concert_title", "cat_concert_desc", "concert", "fox", "#f5c2e7"),
    ("general", "cat_general_title", "cat_general_desc", "aviator", "duck", "#a6e3a1")
]


def get_categories():
    return [
        (k, t(t_key), t(d_key), fo, da, col)
        for (k, t_key, d_key, fo, da, col) in CATEGORIES_DEF
    ]


def _hex_to_rgba(hex_code: str, alpha: float) -> str:
    h = hex_code.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


CATEGORY_GROUPS = {
    "all": ["study", "work", "bill", "food", "sport", "health", "travel", "in_person", "concert", "general"],
    "productivity": ["study", "work", "bill"],
    "lifestyle": ["food", "sport", "health"],
    "commute": ["travel", "in_person", "concert"],
    "general": ["general"],
}

CATEGORY_BADGES = {
    "study": ("🎓", "ACADEMIC"),
    "work": ("💼", "OFFICE"),
    "bill": ("💳", "BILLS"),
    "food": ("🍕", "DINING"),
    "travel": ("✈️", "TRANSIT"),
    "sport": ("🏋️", "FITNESS"),
    "in_person": ("📍", "ON-SITE"),
    "health": ("🌸", "WELLNESS"),
    "concert": ("🎸", "SHOWTIME"),
    "general": ("⭐", "STANDARD"),
}


class QtMascotMiniWidget(QFrame):
    """Mini preview widget rendering live vector mascot animations."""

    def __init__(self, animal="duck", outfit="aviator", cat_color="#89b4fa", parent=None):
        super().__init__(parent)
        self.animal = animal
        self.outfit = outfit
        self.cat_color = cat_color
        self.tick = 0
        self.setFixedSize(68, 64)
        self.setStyleSheet(f"""
            QFrame {{
                background: #11111b;
                border: 1px solid {_hex_to_rgba(cat_color, 0.35)};
                border-radius: 8px;
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        p.save()
        p.translate(w * 0.5 - 2, h * 0.5 - 2)
        p.scale(0.68, -0.68)
        from ui.linux.banner.renderers.modular_renderer import QtModularRenderer
        renderer = QtModularRenderer(animal=self.animal, outfit=self.outfit)
        renderer.draw_pilot(p, 0, 0, self.tick)
        p.restore()

    def update_mascot(self, animal: str, outfit: str):
        self.animal = animal
        self.outfit = outfit
        self.update()

    def update_animal(self, animal: str):
        self.animal = animal
        self.update()


class QtHangarTab(QWidget):
    """Pilot Hangar workshop and category customization tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.h_mini_widgets = []
        self.hangar_anim_timer = None
        self.expanded_categories = set()
        self.expanded_presets = set()
        self.active_study_subcat = "study"
        self.active_filter = "all"
        self.category_cards = {}
        self.filter_buttons = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.h_scroll = QScrollArea(self)
        self.h_scroll.setWidgetResizable(True)
        self.h_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.h_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.h_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.h_content = QWidget()
        self.h_layout = QVBoxLayout(self.h_content)
        self.h_layout.setContentsMargins(0, 0, 0, 0)
        self.h_layout.setSpacing(12)

        self.refresh_hangar()
        self.h_scroll.setWidget(self.h_content)
        layout.addWidget(self.h_scroll)

    def render_hangar_tab(self):
        """Public alias for refreshing hangar tab."""
        self.refresh_hangar()

    def _refresh_hangar(self):
        """Private alias for backwards compatibility."""
        self.refresh_hangar()

    def start_animation_timer(self):
        """Starts the vector animation tick timer for active previewing."""
        try:
            if self.hangar_anim_timer is None:
                self.hangar_anim_timer = QTimer(self)
                self.hangar_anim_timer.setInterval(40)  # 25 fps
                self.hangar_anim_timer.timeout.connect(self._on_hangar_tick)
            if not self.hangar_anim_timer.isActive():
                self.hangar_anim_timer.start()
        except Exception:
            pass

    def stop_animation_timer(self):
        """Stops the vector animation tick timer to conserve CPU when inactive."""
        try:
            if self.hangar_anim_timer is not None and self.hangar_anim_timer.isActive():
                self.hangar_anim_timer.stop()
        except Exception:
            pass

    def _on_hangar_tick(self):
        """Updates animation ticks across all miniature preview widgets."""
        if not self.isVisible():
            return
        for w in self.h_mini_widgets:
            try:
                w.tick += 1
                w.update()
            except Exception:
                pass

    def refresh_hangar(self):
        """Rebuilds the category customizer cards and toolbars."""
        while self.h_layout.count():
            child = self.h_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.h_mini_widgets = []
        self.category_cards = {}
        self.filter_buttons = {}

        # 1. Modern Header Toolbar
        customs = config.get("mascot_customization", {})
        header_card = QFrame(self.h_content)
        header_card.setObjectName("HeaderCard")
        header_card.setStyleSheet("""
            QFrame#HeaderCard {
                background: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 12px;
            }
        """)
        ANIMALS = get_animals()
        CATEGORIES = get_categories()

        r_box = QHBoxLayout(header_card)
        r_box.setContentsMargins(18, 12, 18, 12)
        r_box.setSpacing(14)

        title_v = QVBoxLayout()
        title_v.setSpacing(2)
        r_title = QLabel(t("hangar_header_title"), header_card)
        r_title.setStyleSheet("color: #cdd6f4; font-weight: 800; font-size: 14.5px;")
        r_sub = QLabel(t("hangar_header_subtitle"), header_card)
        r_sub.setStyleSheet("color: #a6adc8; font-size: 11px;")
        title_v.addWidget(r_title)
        title_v.addWidget(r_sub)
        r_box.addLayout(title_v, stretch=1)

        def _on_surprise():
            import random
            all_a = [a[0] for a in ANIMALS]
            c_dict = config.get("mascot_customization", {})
            if not isinstance(c_dict, dict):
                c_dict = {}
            for ck, _, _, fixed_outfit, _, _ in CATEGORIES:
                c_dict[ck] = {"animal": random.choice(all_a), "outfit": fixed_outfit}
            config.set("mascot_customization", c_dict)
            event_bus.publish("CONFIG_CHANGED", key="mascot_customization", value=c_dict)
            self.refresh_hangar()

        def _on_reset():
            defs = {
                "study": {"animal": "owl", "outfit": "student"},
                "work": {"animal": "penguin", "outfit": "agent"},
                "bill": {"animal": "duck", "outfit": "banker"},
                "food": {"animal": "squirrel", "outfit": "chef"},
                "travel": {"animal": "duck", "outfit": "captain"},
                "sport": {"animal": "bunny", "outfit": "gym"},
                "in_person": {"animal": "fox", "outfit": "racer"},
                "health": {"animal": "panda", "outfit": "zen"},
                "concert": {"animal": "fox", "outfit": "concert"},
                "general": {"animal": "duck", "outfit": "aviator"}
            }
            config.set("mascot_customization", defs)
            event_bus.publish("CONFIG_CHANGED", key="mascot_customization", value=defs)
            self.refresh_hangar()

        chime_btn = QPushButton(t("hangar_test_chime"), header_card)
        chime_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        chime_btn.setStyleSheet("""
            QPushButton {
                background: #242438;
                color: #cdd6f4;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #313244;
                border-color: #89b4fa;
            }
        """)
        def _on_test_chime():
            from core.services.sound_service import play_test_chime
            play_test_chime()
        chime_btn.clicked.connect(_on_test_chime)
        r_box.addWidget(chime_btn)

        sur_btn = QPushButton(t("hangar_surprise_me"), header_card)
        sur_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sur_btn.setStyleSheet("""
            QPushButton {
                background: #242438;
                color: #f9e2af;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #313244;
                border-color: #f9e2af;
            }
        """)
        sur_btn.clicked.connect(_on_surprise)
        r_box.addWidget(sur_btn)

        res_btn = QPushButton(t("hangar_reset_presets"), header_card)
        res_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        res_btn.setStyleSheet("""
            QPushButton {
                background: #242438;
                color: #a6adc8;
                border: 1px solid #45475a;
                border-radius: 8px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #313244;
                color: #f38ba8;
                border-color: #f38ba8;
            }
        """)
        res_btn.clicked.connect(_on_reset)
        r_box.addWidget(res_btn)

        self.h_layout.addWidget(header_card)

        # 2. Modern Segmented Filter Pills Bar
        filter_bar = QFrame(self.h_content)
        filter_bar.setObjectName("HangarFilterBar")
        filter_bar.setStyleSheet("background: transparent; border: none;")
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(4, 2, 4, 2)
        fb_layout.setSpacing(8)

        filter_items = [
            ("all", t("hangar_filter_all", count=len(CATEGORIES))),
            ("productivity", t("hangar_filter_productivity")),
            ("lifestyle", t("hangar_filter_lifestyle")),
            ("commute", t("hangar_filter_commute")),
            ("general", t("hangar_filter_general")),
        ]

        for f_key, f_label in filter_items:
            f_btn = QPushButton(f_label.replace("&", "&&"), filter_bar)
            f_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            f_btn.setFixedHeight(30)
            def _make_filter_cb(fk=f_key):
                return lambda: self._apply_filter(fk)
            f_btn.clicked.connect(_make_filter_cb(f_key))
            fb_layout.addWidget(f_btn)
            self.filter_buttons[f_key] = f_btn

        fb_layout.addStretch()
        self.h_layout.addWidget(filter_bar)

        for idx, (cat_key, cat_title, cat_desc, fixed_outfit, def_animal, cat_color) in enumerate(CATEGORIES):
            card = self._build_category_card(cat_key, cat_title, cat_desc, fixed_outfit, def_animal, cat_color, customs, ANIMALS)
            self.h_layout.addWidget(card)

        self._apply_filter(self.active_filter)
        self.h_layout.addStretch()
        if self.isVisible():
            self.start_animation_timer()

    def _apply_filter(self, filter_key: str):
        """Applies real-time category filtering and updates filter pill button styles."""
        self.active_filter = filter_key
        allowed = set(CATEGORY_GROUPS.get(filter_key, CATEGORY_GROUPS["all"]))
        for ck, card_widget in self.category_cards.items():
            card_widget.setVisible(ck in allowed)

        for fk, btn in self.filter_buttons.items():
            if fk == filter_key:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #313244;
                        color: #cdd6f4;
                        font-size: 11px;
                        font-weight: 700;
                        border: 1.5px solid #89b4fa;
                        border-radius: 14px;
                        padding: 4px 14px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1e1e2e;
                        color: #a6adc8;
                        font-size: 11px;
                        font-weight: 600;
                        border: 1px solid #313244;
                        border-radius: 14px;
                        padding: 4px 14px;
                    }
                    QPushButton:hover {
                        background-color: #242438;
                        color: #cdd6f4;
                        border-color: #45475a;
                    }
                """)

    def _build_category_card(
        self,
        cat_key: str,
        cat_title: str,
        cat_desc: str,
        fixed_outfit: str,
        def_animal: str,
        cat_color: str,
        customs: dict,
        ANIMALS: list,
    ) -> QFrame:
        if cat_key == "study":
            sc_val = customs.get(self.active_study_subcat, customs.get("study", {}))
            current_animal = sc_val.get("animal", "owl") if isinstance(sc_val, dict) else (sc_val or "owl")
        else:
            current_setting = customs.get(cat_key, {})
            current_animal = current_setting.get("animal", def_animal) if isinstance(current_setting, dict) else (current_setting or def_animal)

        card = QFrame(self.h_content)
        card.setObjectName("Card")
        card.setStyleSheet(f"""
            QFrame#Card {{
                background: #181825;
                border: 1px solid #313244;
                border-left: 4px solid {cat_color};
                border-radius: 12px;
            }}
            QFrame#Card:hover {{
                border-color: {_hex_to_rgba(cat_color, 0.45)};
                border-left-color: {cat_color};
                background: #1c1c2e;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(10)

        # ── Top Row: Mini Preview, Titles, Controls ──
        top_row = QHBoxLayout()
        top_row.setSpacing(14)

        # Mini Canvas Preview on Left (Aero Pod)
        preview_outfit = "agent" if current_animal == "platypus" else fixed_outfit
        mini_preview = QtMascotMiniWidget(animal=current_animal, outfit=preview_outfit, cat_color=cat_color, parent=card)
        self.h_mini_widgets.append(mini_preview)
        top_row.addWidget(mini_preview)

        p_box = QVBoxLayout()
        p_box.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        badge_icon, badge_tag = CATEGORY_BADGES.get(cat_key, ("⭐", cat_key.upper()))
        tag_lbl = QLabel(f"{badge_icon} {badge_tag}", card)
        tag_lbl.setStyleSheet(f"""
            background-color: {_hex_to_rgba(cat_color, 0.15)};
            color: {cat_color};
            border: 1px solid {_hex_to_rgba(cat_color, 0.35)};
            border-radius: 5px;
            font-size: 9.5px;
            font-weight: 800;
            padding: 2px 7px;
        """)
        title_row.addWidget(tag_lbl)

        n_l = QLabel(cat_title, card)
        n_l.setStyleSheet("color: #cdd6f4; font-weight: 700; font-size: 13.5px;")
        title_row.addWidget(n_l)
        title_row.addStretch()
        p_box.addLayout(title_row)

        d_l = QLabel(cat_desc, card)
        d_l.setStyleSheet("color: #a6adc8; font-size: 11px;")
        d_l.setWordWrap(True)
        d_l.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        p_box.addWidget(d_l)

        # Dedicated Active Pilot Chip
        active_pilot_name = get_combo_title(current_animal, preview_outfit)
        pilot_chip = QFrame(card)
        pilot_chip.setStyleSheet("""
            QFrame {
                background-color: #1e1e2e;
                border: 1px solid #313244;
                border-radius: 6px;
            }
        """)
        pilot_chip_layout = QHBoxLayout(pilot_chip)
        pilot_chip_layout.setContentsMargins(7, 3, 9, 3)
        pilot_chip_layout.setSpacing(6)
        ap_lbl1 = QLabel(f"✨ {t('hangar_active_pilot_label')}:", pilot_chip)
        ap_lbl1.setStyleSheet("color: #a6adc8; font-size: 10.5px; font-weight: 600; border: none; background: transparent;")
        ap_lbl2 = QLabel(active_pilot_name, pilot_chip)
        ap_lbl2.setStyleSheet(f"color: {cat_color}; font-size: 11px; font-weight: 700; border: none; background: transparent;")
        pilot_chip_layout.addWidget(ap_lbl1)
        pilot_chip_layout.addWidget(ap_lbl2)
        pilot_chip_layout.addStretch()
        p_box.addWidget(pilot_chip)

        top_row.addLayout(p_box, stretch=1)

        # Controls Right Column
        ctrl_widget = QWidget(card)
        ctrl_box = QVBoxLayout(ctrl_widget)
        ctrl_box.setContentsMargins(0, 0, 0, 0)
        ctrl_box.setSpacing(8)
        ctrl_widget.setFixedWidth(248)

        animal_lbl_txt = f"🎭 {t('hangar_change_pilot_btn')}:"
        if cat_key == "study":
            subcat_name_map = {
                "study": t("hangar_subcat_study"),
                "class": t("hangar_subcat_class"),
                "exam": t("hangar_subcat_exam"),
            }
            animal_lbl_txt = f"🎭 {t('hangar_change_pilot_btn')} ({subcat_name_map.get(self.active_study_subcat, '')}):"

        m_head_lbl = QLabel(animal_lbl_txt, ctrl_widget)
        m_head_lbl.setStyleSheet("color: #a6adc8; font-size: 10.5px; font-weight: bold;")
        ctrl_box.addWidget(m_head_lbl)

        a_combo = QComboBox(ctrl_widget)
        for a_id, a_name in ANIMALS:
            a_combo.addItem(a_name, a_id)

        cur_idx = next((i for i, (a_id, _) in enumerate(ANIMALS) if a_id == current_animal), 0)
        a_combo.setCurrentIndex(cur_idx)
        a_combo.setFixedHeight(28)
        a_combo.setStyleSheet(get_combo_box_qss(bg_color="#242438", min_width=170))

        def _on_a_changed(i_val):
            sel_a = ANIMALS[i_val][0]
            c_dict = config.get("mascot_customization", {})
            if not isinstance(c_dict, dict):
                c_dict = {}
            selected_outfit = "agent" if sel_a == "platypus" else fixed_outfit
            target_sc = self.active_study_subcat if cat_key == "study" else cat_key
            c_dict[target_sc] = {"animal": sel_a, "outfit": selected_outfit, "accessories": list(normalize_accessories(selected_outfit, animal=sel_a))}
            if cat_key == "study" and target_sc == "study":
                for sub in ("class", "exam"):
                    if sub not in c_dict or not isinstance(c_dict[sub], dict):
                        c_dict[sub] = {"animal": sel_a, "outfit": "student"}
            config.set("mascot_customization", c_dict)
            event_bus.publish("CONFIG_CHANGED", key="mascot_customization", value=c_dict)
            self.refresh_hangar()

        a_combo.currentIndexChanged.connect(_on_a_changed)
        ctrl_box.addWidget(a_combo)

        # Test Flight Button
        def _trigger_test():
            if cat_key == "study":
                cur_sc = self.active_study_subcat
                cd = config.get("mascot_customization", {})
                val = cd.get(cur_sc, cd.get("study", {}))
                an = val.get("animal", "owl") if isinstance(val, dict) else (val or "owl")
                out = "student"
                now = datetime.now().astimezone()
                if cur_sc == "study":
                    evt = {
                        "title": "Deep Focus & Solo Study Session",
                        "provider": get_combo_title(an, out),
                        "pilot_type": f"{an}_{out}",
                        "animal": an,
                        "outfit": out,
                        "action_btn_text": "⚡ TIME TO STUDY! 📖",
                        "action_url": "https://notion.so",
                        "start_time": now + timedelta(minutes=10),
                        "end_time": now + timedelta(minutes=90),
                        "reminder_stage": 10,
                        "is_travel": False,
                        "is_test_banner": True,
                        "is_late": False,
                    }
                elif cur_sc == "class":
                    evt = {
                        "title": "Neural Networks & AI Lecture (Room 3B)",
                        "provider": get_combo_title(an, out),
                        "pilot_type": f"{an}_{out}",
                        "animal": an,
                        "outfit": out,
                        "action_btn_text": "🏫 ROOM 3B & NOTES",
                        "action_url": "https://meet.google.com/study-class-room",
                        "start_time": now + timedelta(minutes=10),
                        "end_time": now + timedelta(minutes=110),
                        "reminder_stage": 10,
                        "is_travel": False,
                        "is_test_banner": True,
                        "is_late": False,
                    }
                else:
                    evt = {
                        "title": "General Physics Final Exam (Main Hall)",
                        "provider": get_combo_title(an, out),
                        "pilot_type": f"{an}_{out}",
                        "animal": an,
                        "outfit": out,
                        "action_btn_text": "🎓 MAIN HALL & NOTES",
                        "action_url": "https://exam-portal.edu",
                        "start_time": now + timedelta(minutes=10),
                        "end_time": now + timedelta(minutes=130),
                        "reminder_stage": 10,
                        "is_travel": False,
                        "is_test_banner": True,
                        "is_late": False,
                    }
                from core.services.sound_service import play_test_chime
                play_test_chime()
                from ui.linux.banner.qt_banner import show_qt_banner
                show_qt_banner(evt)
                return

            c_dict = config.get("mascot_customization", {})
            val = c_dict.get(cat_key, {})
            an = val.get("animal", "duck") if isinstance(val, dict) else (val or "duck")
            out = "agent" if an == "platypus" else fixed_outfit
            titles = {
                "study": "Neural Networks & AI University Lecture",
                "work": "Executive Board Strategy & Sprint Review",
                "bill": "Monthly Rent & Utility Bill Due",
                "food": "Dinner with Friends at Pizzeria",
                "travel": "Flight BA 257 to London Heathrow",
                "sport": "CrossFit & Palestra Workout Session",
                "in_person": "Architectural Studio Consultation",
                "health": "Serenis Mindfulness & Yoga Session",
                "concert": "Rock Arena Live World Tour Concert",
                "secret": "Top Secret Agent Mission Briefing",
                "general": "Weekly Team Sprint Planning",
            }
            now = datetime.now().astimezone()
            evt = {
                "title": titles.get(cat_key, "Custom Mascot Test Flight"),
                "provider": get_combo_title(an, out),
                "pilot_type": f"{an}_{out}",
                "animal": an,
                "outfit": out,
                "category": cat_key,
                "action_btn_text": "💳 PAY BILL" if cat_key == "bill" else "🚀 TEST FLIGHT",
                "action_url": "https://meet.google.com/test-flight",
                "start_time": now + timedelta(minutes=10),
                "end_time": now + timedelta(minutes=70),
                "reminder_stage": 10,
                "is_travel": cat_key in ("food", "travel", "sport", "in_person", "concert"),
                "is_test_banner": True,
                "is_late": False,
            }
            from core.services.sound_service import play_test_chime
            play_test_chime()
            from ui.linux.banner.qt_banner import show_qt_banner
            show_qt_banner(evt)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        if cat_key == "study":
            kw_count = len(config.get_custom_keywords(self.active_study_subcat))
        else:
            kw_count = len(config.get_custom_keywords(cat_key))
        is_exp = cat_key in self.expanded_categories
        kw_toggle_btn = QPushButton(
            t(
                "hangar_keywords_toggle_btn_open" if is_exp else "hangar_keywords_toggle_btn",
                count=kw_count,
            ),
            ctrl_widget,
        )
        kw_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        kw_toggle_btn.setFixedHeight(28)
        if is_exp:
            kw_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #313244;
                    color: #89b4fa;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 7px;
                    padding: 4px 8px;
                    border: 1px solid #89b4fa;
                }
            """)
        else:
            kw_toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: #242438;
                    color: #cdd6f4;
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 7px;
                    padding: 4px 8px;
                    border: 1px solid #45475a;
                }
                QPushButton:hover {
                    background-color: #313244;
                    color: #ffffff;
                    border-color: #89b4fa;
                }
            """)
        btn_row.addWidget(kw_toggle_btn, stretch=1)

        t_btn = QPushButton(t("hangar_test_btn"), ctrl_widget)
        t_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        t_btn.setFixedHeight(28)
        t_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_hex_to_rgba(cat_color, 0.12)};
                color: {cat_color};
                font-weight: 700;
                font-size: 11px;
                border-radius: 7px;
                padding: 4px 11px;
                border: 1px solid {_hex_to_rgba(cat_color, 0.55)};
            }}
            QPushButton:hover {{
                background-color: {_hex_to_rgba(cat_color, 0.25)};
                border-color: {cat_color};
            }}
            QPushButton:pressed {{
                background-color: {_hex_to_rgba(cat_color, 0.40)};
            }}
        """)
        t_btn.clicked.connect(_trigger_test)
        btn_row.addWidget(t_btn)

        ctrl_box.addLayout(btn_row)
        top_row.addWidget(ctrl_widget)
        card_layout.addLayout(top_row)

        if cat_key == "study":
            # 🎓 Academic Subcategory Switcher (Always accessible directly on Card)
            subcat_tabs_row = QHBoxLayout()
            subcat_tabs_row.setSpacing(8)
            subcat_tabs_row.setContentsMargins(0, 4, 0, 2)
            subcats = [
                ("study", t("hangar_subcat_study")),
                ("class", t("hangar_subcat_class")),
                ("exam", t("hangar_subcat_exam")),
            ]
            cur_sc = self.active_study_subcat
            for s_key, s_lbl in subcats:
                sc_kw_count = len(config.get_custom_keywords(s_key))
                btn_title = f"{s_lbl} ({sc_kw_count})".replace("&", "&&")
                sc_btn = QPushButton(btn_title, card)
                sc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                sc_btn.setFixedHeight(28)
                is_active = (s_key == cur_sc)
                if is_active:
                    sc_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #45475a;
                            color: #cdd6f4;
                            font-size: 11px;
                            font-weight: bold;
                            border: 1px solid #cba6f7;
                            border-radius: 6px;
                            padding: 4px 10px;
                        }
                    """)
                else:
                    sc_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #181825;
                            color: #a6adc8;
                            font-size: 11px;
                            font-weight: 500;
                            border: 1px solid #313244;
                            border-radius: 6px;
                            padding: 4px 10px;
                        }
                        QPushButton:hover {
                            background-color: #313244;
                            color: #cdd6f4;
                        }
                    """)
                def _make_sc_click(sk=s_key):
                    def _set_sc():
                        self.active_study_subcat = sk
                        self.refresh_hangar()
                    return _set_sc
                sc_btn.clicked.connect(_make_sc_click())
                subcat_tabs_row.addWidget(sc_btn)
            card_layout.addLayout(subcat_tabs_row)

        self.category_cards[cat_key] = card

        # ── Hairline Divider ──
        h_line = QFrame(card)
        h_line.setFrameShape(QFrame.Shape.HLine)
        h_line.setStyleSheet("background-color: #313244; max-height: 1px; border: none;")
        h_line.setVisible(is_exp)
        card_layout.addWidget(h_line)

        # ── Expandable Drawer ──
        drawer = QFrame(card)
        drawer.setStyleSheet("background: transparent; border: none;")
        drawer.setVisible(is_exp)
        drawer_layout = QVBoxLayout(drawer)
        drawer_layout.setContentsMargins(4, 6, 4, 4)
        drawer_layout.setSpacing(8)
        card_layout.addWidget(drawer)

        if cat_key == "study":
            cur_sc = self.active_study_subcat
            # 1. Dynamic Explainer Guide (Dedicated full-width row)
            guide_keys = {
                "study": "hangar_subcat_study_guide",
                "class": "hangar_subcat_class_guide",
                "exam": "hangar_subcat_exam_guide",
            }
            guide_lbl = QLabel(t(guide_keys.get(cur_sc, "hangar_subcat_study_guide")), drawer)
            guide_lbl.setStyleSheet("color: #bac2de; font-size: 10.5px; font-style: italic; border: none; padding: 2px 0;")
            guide_lbl.setWordWrap(True)
            drawer_layout.addWidget(guide_lbl)

            # 2. Subcategory Keywords Section Header
            subcat_name_map = {
                "study": t("hangar_subcat_study"),
                "class": t("hangar_subcat_class"),
                "exam": t("hangar_subcat_exam"),
            }
            kw_head_lbl = QLabel(t("hangar_subcat_keywords_heading", subcat=subcat_name_map.get(cur_sc, "")), drawer)
            kw_head_lbl.setStyleSheet("color: #a6adc8; font-size: 11px; font-weight: 700; border: none; padding-top: 4px;")
            drawer_layout.addWidget(kw_head_lbl)
        else:
            # Drawer Guidance Subtitle for standard categories
            guide_lbl = QLabel(t("hangar_keywords_drawer_subtitle"), drawer)
            guide_lbl.setStyleSheet("color: #a6adc8; font-size: 10.5px; font-style: italic; border: none;")
            drawer_layout.addWidget(guide_lbl)

        # ── Dual-Tier Omni Deck ──
        deck_frame = QFrame(drawer)
        deck_frame.setObjectName("DeckFrame")
        deck_frame.setStyleSheet("""
            QFrame#DeckFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 10px;
            }
        """)
        deck_layout = QVBoxLayout(deck_frame)
        deck_layout.setContentsMargins(12, 10, 12, 10)
        deck_layout.setSpacing(10)
        drawer_layout.addWidget(deck_frame)

        # 1. Top Omni-Adder Bar
        adder_row = QHBoxLayout()
        adder_row.setSpacing(8)

        kw_input = QLineEdit(deck_frame)
        kw_input.setPlaceholderText(t("hangar_keywords_add_placeholder_custom"))
        kw_input.setFixedHeight(30)
        kw_input.setStyleSheet("""
            QLineEdit {
                background: #11111b;
                color: #cdd6f4;
                font-size: 11.5px;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QLineEdit:focus {
                border-color: #cba6f7;
            }
        """)
        adder_row.addWidget(kw_input, stretch=1)

        add_btn = QPushButton(t("hangar_keywords_add_custom_btn"), deck_frame)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setFixedHeight(30)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #cba6f7;
                color: #11111b;
                font-size: 11px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 4px 12px;
            }
            QPushButton:hover { background: #d6b4fc; }
        """)
        adder_row.addWidget(add_btn)

        rst_btn = QPushButton(t("hangar_keywords_reset_to_defaults"), deck_frame)
        rst_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rst_btn.setFixedHeight(30)
        rst_btn.setStyleSheet("""
            QPushButton {
                background: #1e1e2e;
                color: #a6adc8;
                font-size: 11px;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #313244; color: #cdd6f4; }
        """)
        adder_row.addWidget(rst_btn)

        hide_btn = QPushButton(t("hangar_keywords_drawer_hide"), deck_frame)
        hide_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hide_btn.setFixedHeight(30)
        hide_btn.setStyleSheet("""
            QPushButton {
                background: #181825;
                color: #a6adc8;
                font-size: 11px;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px 10px;
            }
            QPushButton:hover { background: #313244; color: #cdd6f4; }
        """)
        adder_row.addWidget(hide_btn)
        deck_layout.addLayout(adder_row)

        # 2. Tier 1: Custom Triggers Section
        custom_section = QWidget(deck_frame)
        custom_sec_lay = QVBoxLayout(custom_section)
        custom_sec_lay.setContentsMargins(0, 0, 0, 0)
        custom_sec_lay.setSpacing(5)

        c_head_row = QHBoxLayout()
        c_head_row.setSpacing(6)
        c_head_lbl = QLabel(t("hangar_keywords_custom_title"), custom_section)
        c_head_lbl.setStyleSheet("color: #cba6f7; font-size: 11.5px; font-weight: bold; border: none;")
        c_head_row.addWidget(c_head_lbl)

        c_cnt_lbl = QLabel("", custom_section)
        c_cnt_lbl.setStyleSheet("background: rgba(203, 166, 247, 0.15); color: #cba6f7; font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px;")
        c_head_row.addWidget(c_cnt_lbl)
        c_head_row.addStretch()
        custom_sec_lay.addLayout(c_head_row)

        custom_box = QFrame(custom_section)
        custom_box.setStyleSheet("background: #11111b; border: 1px solid rgba(203, 166, 247, 0.25); border-radius: 8px;")
        custom_flow = FlowLayout(custom_box, margin=8, spacing=6)
        custom_sec_lay.addWidget(custom_box)
        deck_layout.addWidget(custom_section)

        # 3. Tier 2: Built-in Core Presets Toggle & Section (A Scomparsa)
        preset_toggle_row = QHBoxLayout()
        preset_toggle_row.setSpacing(6)

        preset_toggle_btn = QPushButton(deck_frame)
        preset_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        preset_toggle_btn.setFixedHeight(28)
        preset_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e2e;
                color: #a6adc8;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 4px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #313244;
                color: #cdd6f4;
                border-color: #45475a;
            }
        """)
        preset_toggle_row.addWidget(preset_toggle_btn)
        preset_toggle_row.addStretch()
        deck_layout.addLayout(preset_toggle_row)

        preset_scroll = QScrollArea(deck_frame)
        preset_scroll.setFixedHeight(115)
        preset_scroll.setWidgetResizable(True)
        preset_scroll.setFrameShape(QFrame.Shape.NoFrame)
        preset_scroll.setStyleSheet("""
            QScrollArea {
                background: #11111b;
                border: 1px solid #313244;
                border-radius: 8px;
            }
            QScrollBar:vertical {
                background: #11111b;
                width: 6px;
                margin: 4px 2px 4px 0px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #313244;
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #585b70;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        preset_container = QWidget()
        preset_container.setStyleSheet("background: transparent;")
        preset_flow = FlowLayout(preset_container, margin=8, spacing=6)
        preset_scroll.setWidget(preset_container)
        deck_layout.addWidget(preset_scroll)

        def _create_tag_pill(text, is_custom, k_cat):
            tag = QFrame()
            if is_custom:
                tag.setStyleSheet("""
                    QFrame {
                        background-color: rgba(203, 166, 247, 0.14);
                        border: 1.5px solid #cba6f7;
                        border-radius: 6px;
                    }
                    QFrame:hover {
                        background-color: rgba(203, 166, 247, 0.22);
                    }
                """)
                txt_color = "#cba6f7"
                prefix = "✨ "
            else:
                tag.setStyleSheet("""
                    QFrame {
                        background-color: #1e1e2e;
                        border: 1px solid #313244;
                        border-radius: 6px;
                    }
                    QFrame:hover {
                        border-color: #89b4fa;
                        background-color: #242438;
                    }
                """)
                txt_color = "#cdd6f4"
                prefix = ""

            tl = QHBoxLayout(tag)
            tl.setContentsMargins(8, 3, 6, 3)
            tl.setSpacing(5)

            klbl = QLabel(f"{prefix}{text}", tag)
            klbl.setStyleSheet(f"color: {txt_color}; font-size: 11px; font-weight: {'bold' if is_custom else '500'}; border: none; background: transparent;")
            tl.addWidget(klbl)

            del_b = QPushButton("✕", tag)
            del_b.setFixedSize(14, 14)
            del_b.setCursor(Qt.CursorShape.PointingHandCursor)
            del_b.setStyleSheet("""
                QPushButton {
                    color: #f38ba8;
                    background: transparent;
                    border: none;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 0px;
                }
                QPushButton:hover {
                    color: #ffffff;
                    background: #e78284;
                    border-radius: 7px;
                }
            """)

            def _del_action():
                config.remove_custom_keyword(k_cat, text)
                try:
                    event_bus.publish(
                        "CONFIG_CHANGED",
                        key="custom_keywords",
                        value=config.get_custom_keywords(),
                    )
                except Exception:
                    pass
                _render_deck()

            del_b.clicked.connect(_del_action)
            tl.addWidget(del_b)
            return tag

        def _render_deck():
            target_k = self.active_study_subcat if cat_key == "study" else cat_key
            all_kws = config.get_custom_keywords(target_k)
            default_kws = config.get_default_keywords(target_k)
            default_set = {d.strip().lower() for d in default_kws}

            custom_kws = [k for k in all_kws if k.strip().lower() not in default_set]
            preset_kws = [k for k in all_kws if k.strip().lower() in default_set]

            # Update toggle button on card
            is_open = drawer.isVisible()
            total_cnt = len(all_kws)
            kw_toggle_btn.setText(
                t(
                    "hangar_keywords_toggle_btn_open" if is_open else "hangar_keywords_toggle_btn",
                    count=total_cnt,
                )
            )

            # Clear custom flow
            while custom_flow.count():
                it = custom_flow.takeAt(0)
                if it and it.widget():
                    it.widget().deleteLater()

            c_cnt_lbl.setText(t("hangar_keywords_custom_active", count=len(custom_kws)))
            if not custom_kws:
                empty = QLabel(t("hangar_keywords_custom_empty"), custom_box)
                empty.setStyleSheet("color: #6c7086; font-size: 10.5px; font-style: italic; border: none; padding: 4px;")
                custom_flow.addWidget(empty)
            else:
                for kw in custom_kws:
                    custom_flow.addWidget(_create_tag_pill(kw, is_custom=True, k_cat=target_k))

            # Presets collapsible state
            is_preset_open = target_k in self.expanded_presets
            if is_preset_open:
                preset_toggle_btn.setText(t("hangar_keywords_presets_toggle_hide", count=len(preset_kws)))
                preset_scroll.setVisible(True)
            else:
                preset_toggle_btn.setText(t("hangar_keywords_presets_toggle_show", count=len(preset_kws)))
                preset_scroll.setVisible(False)

            # Clear and repopulate presets
            while preset_flow.count():
                it = preset_flow.takeAt(0)
                if it and it.widget():
                    it.widget().deleteLater()

            for kw in preset_kws:
                preset_flow.addWidget(_create_tag_pill(kw, is_custom=False, k_cat=target_k))

        def _toggle_presets():
            target_k = self.active_study_subcat if cat_key == "study" else cat_key
            if target_k in self.expanded_presets:
                self.expanded_presets.remove(target_k)
            else:
                self.expanded_presets.add(target_k)
            _render_deck()

        preset_toggle_btn.clicked.connect(_toggle_presets)

        def _add_action():
            target_k = self.active_study_subcat if cat_key == "study" else cat_key
            txt = kw_input.text().strip()
            if not txt:
                return
            tokens = [tk.strip() for tk in txt.split(",") if tk.strip()]
            any_added = False
            for tok in tokens:
                if config.add_custom_keyword(target_k, tok):
                    any_added = True
            if any_added:
                kw_input.clear()
                try:
                    event_bus.publish(
                        "CONFIG_CHANGED",
                        key="custom_keywords",
                        value=config.get_custom_keywords(),
                    )
                except Exception:
                    pass
                _render_deck()

        add_btn.clicked.connect(_add_action)
        kw_input.returnPressed.connect(_add_action)

        def _rst_action():
            target_k = self.active_study_subcat if cat_key == "study" else cat_key
            config.reset_custom_keywords(target_k)
            try:
                event_bus.publish(
                    "CONFIG_CHANGED",
                    key="custom_keywords",
                    value=config.get_custom_keywords(),
                )
            except Exception:
                pass
            _render_deck()

        rst_btn.clicked.connect(_rst_action)

        def _make_toggle():
            def _toggle_action():
                if cat_key in self.expanded_categories:
                    self.expanded_categories.remove(cat_key)
                else:
                    self.expanded_categories.add(cat_key)
                now_open = cat_key in self.expanded_categories
                drawer.setVisible(now_open)
                h_line.setVisible(now_open)
                _render_deck()
                if now_open:
                    kw_toggle_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #45475a;
                            color: #89b4fa;
                            font-size: 11px;
                            font-weight: bold;
                            border-radius: 6px;
                            padding: 6px 12px;
                            border: 1px solid #89b4fa;
                        }
                    """)
                else:
                    kw_toggle_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #313244;
                            color: #cdd6f4;
                            font-size: 11px;
                            font-weight: 500;
                            border-radius: 6px;
                            padding: 6px 12px;
                            border: 1px solid #45475a;
                        }
                        QPushButton:hover {
                            background-color: #45475a;
                            color: #ffffff;
                        }
                    """)

            return _toggle_action

        kw_toggle_btn.clicked.connect(_make_toggle())
        hide_btn.clicked.connect(_make_toggle())

        _render_deck()
        return card
