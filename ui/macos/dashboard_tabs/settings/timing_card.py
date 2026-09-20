import AppKit
import objc
from core.services.language_service import t
from ui.macos.components import ModernToggleSwitch
from ui.macos.theme import Theme
from ui.macos.dashboard_tabs.settings.helpers import (
    add_hairline_divider,
    add_section_header,
    create_pill_chip,
    update_pill_chip_style,
)


class TimingCardController(AppKit.NSObject):
    """Card 1: Notification Lead Times & Staged Reminders."""

    def initWithParent_(self, parent):
        self = objc.super(TimingCardController, self).init()
        self.parent = parent
        self.meeting_stage_chips = []
        self.general_stage_chips = []
        self.travel_stage_chips = []
        self.bill_interval_chips = []
        self.bill_sw = None
        return self

    @property
    def config(self):
        return self.parent.config

    @objc.python_method
    def build_card(self, card, w, h):
        add_section_header(
            card,
            t("settings_timing_title"),
            t("settings_timing_subtitle"),
            h, w
        )

        # Quick Presets Row
        pre_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, h - 84, 110, 20))
        pre_lbl.setStringValue_(t("settings_quick_presets"))
        pre_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(11.5))
        pre_lbl.setTextColor_(Theme.SUBTEXT0)
        pre_lbl.setBezeled_(False)
        pre_lbl.setDrawsBackground_(False)
        pre_lbl.setEditable_(False)
        card.addSubview_(pre_lbl)

        presets = [
            (t("preset_relaxed"), "onApplyPresetRelaxed:", 92.0),
            (t("preset_standard"), "onApplyPresetStandard:", 98.0),
            (t("preset_intensive"), "onApplyPresetIntensive:", 104.0)
        ]
        x_pre = 135.0
        for p_title, p_action, p_w in presets:
            p_btn = Theme.create_button(
                AppKit.NSMakeRect(x_pre, h - 86, p_w, 24),
                title=p_title,
                bg_color=AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(0.141, 0.141, 0.220, 1.0),
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=11.5,
                bold=True
            )
            p_btn.setTarget_(self)
            p_btn.setAction_(p_action)
            card.addSubview_(p_btn)
            x_pre += (p_w + 8.0)

        add_hairline_divider(card, h - 100, w)

        self.meeting_stage_chips = []
        self.general_stage_chips = []
        self.travel_stage_chips = []

        meeting_opts = [(30, "30m"), (20, "20m"), (15, "15m"), (10, "10m"), (5, "5m"), (2, "2m")]
        travel_opts = [(60, "60m"), (45, "45m"), (30, "30m"), (15, "15m"), (5, "5m"), (2, "2m")]

        def _add_sub_header(title, desc, y_t, y_d):
            t_f = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, y_t, w - 36, 18))
            t_f.setStringValue_(title)
            t_f.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.0))
            t_f.setTextColor_(Theme.TEXT)
            t_f.setBezeled_(False)
            t_f.setDrawsBackground_(False)
            t_f.setEditable_(False)
            card.addSubview_(t_f)

            d = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, y_d, w - 36, 16))
            d.setStringValue_(desc)
            d.setFont_(AppKit.NSFont.systemFontOfSize_(11.0))
            d.setTextColor_(Theme.SUBTEXT0)
            d.setBezeled_(False)
            d.setDrawsBackground_(False)
            d.setEditable_(False)
            card.addSubview_(d)

        # 1. Video Meetings Row
        _add_sub_header(t("settings_video_meetings"), t("settings_video_meetings_desc"), h - 124, h - 140)
        curr_meeting_stages = set(self.config.get("meeting_reminder_stages", [20, 10, 5, 2, 0]))
        x_chip = 18.0
        for val, label in meeting_opts:
            chip = create_pill_chip(
                card, label, val, val in curr_meeting_stages, "onToggleMeetingStage:", x_chip, h - 172, 54.0, 26.0, "mauve", target=self
            )
            self.meeting_stage_chips.append(chip)
            x_chip += 60.0

        add_hairline_divider(card, h - 184, w)

        # 2. General Events Row
        _add_sub_header(t("settings_general_events"), t("settings_general_events_desc"), h - 208, h - 224)
        curr_general_stages = set(self.config.get("general_reminder_stages", [20, 10, 5, 2, 0]))
        x_chip = 18.0
        for val, label in meeting_opts:
            chip = create_pill_chip(
                card, label, val, val in curr_general_stages, "onToggleGeneralStage:", x_chip, h - 256, 54.0, 26.0, "blue", target=self
            )
            self.general_stage_chips.append(chip)
            x_chip += 60.0

        add_hairline_divider(card, h - 268, w)

        # 3. Travel & Trips Row
        _add_sub_header(t("settings_travel_trips"), t("settings_travel_trips_desc"), h - 292, h - 308)
        curr_travel_stages = set(self.config.get("travel_reminder_stages", [45, 30, 15, 5, 2, 0]))
        x_chip = 18.0
        for val, label in travel_opts:
            chip = create_pill_chip(
                card, label, val, val in curr_travel_stages, "onToggleTravelStage:", x_chip, h - 340, 54.0, 26.0, "peach", target=self
            )
            self.travel_stage_chips.append(chip)
            x_chip += 60.0

        add_hairline_divider(card, h - 352, w)

        # 4. Recurring Bills & Rent Reminders
        _add_sub_header(
            t("settings_bill_reminders_title", default="Recurring Bill & Rent Reminders"),
            t("settings_bill_reminders_desc", default="Periodically remind until marked paid or actioned."),
            h - 376,
            h - 392,
        )

        self.bill_sw = ModernToggleSwitch.alloc().initWithFrame_(AppKit.NSMakeRect(w - 62, h - 388, 44, 24))
        self.bill_sw.setChecked_(bool(self.config.get("enable_bill_reminders", True)))
        self.bill_sw.setCallback_(self.onToggleBillSwitch)
        card.addSubview_(self.bill_sw)

        curr_bill_interval = int(self.config.get("bill_reminder_interval_minutes", 120))
        bill_opts = [(30, "30m"), (60, "1h"), (120, "2h"), (240, "4h")]
        self.bill_interval_chips = []
        x_chip = 18.0
        for val, label in bill_opts:
            chip = create_pill_chip(
                card, label, val, val == curr_bill_interval, "onSelectBillInterval:", x_chip, h - 428, 54.0, 26.0, "green", target=self
            )
            self.bill_interval_chips.append(chip)
            x_chip += 60.0

    @objc.python_method
    def _refresh_stage_chips_ui(self):
        meeting_stages = set(self.config.get("meeting_reminder_stages", []))
        for btn in getattr(self, "meeting_stage_chips", []):
            is_on = btn.tag() in meeting_stages
            btn.setState_(AppKit.NSControlStateValueOn if is_on else AppKit.NSControlStateValueOff)
            update_pill_chip_style(btn, is_on, "mauve")

        general_stages = set(self.config.get("general_reminder_stages", []))
        for btn in getattr(self, "general_stage_chips", []):
            is_on = btn.tag() in general_stages
            btn.setState_(AppKit.NSControlStateValueOn if is_on else AppKit.NSControlStateValueOff)
            update_pill_chip_style(btn, is_on, "blue")

        travel_stages = set(self.config.get("travel_reminder_stages", []))
        for btn in getattr(self, "travel_stage_chips", []):
            is_on = btn.tag() in travel_stages
            btn.setState_(AppKit.NSControlStateValueOn if is_on else AppKit.NSControlStateValueOff)
            update_pill_chip_style(btn, is_on, "peach")

        if self.bill_sw:
            self.bill_sw.setChecked_(bool(self.config.get("enable_bill_reminders", True)))
        curr_int = int(self.config.get("bill_reminder_interval_minutes", 120))
        for btn in getattr(self, "bill_interval_chips", []):
            is_on = (btn.tag() == curr_int)
            btn.setState_(AppKit.NSControlStateValueOn if is_on else AppKit.NSControlStateValueOff)
            update_pill_chip_style(btn, is_on, "green")

    @objc.python_method
    def onToggleBillSwitch(self, is_on):
        self.config.set("enable_bill_reminders", is_on)
        try:
            from core.services.event_bus import event_bus
            event_bus.publish("CONFIG_CHANGED", key="enable_bill_reminders", value=is_on)
        except Exception:
            pass

    @objc.IBAction
    def onSelectBillInterval_(self, sender):
        val = sender.tag()
        self.config.set("bill_reminder_interval_minutes", val)
        try:
            from core.services.event_bus import event_bus
            event_bus.publish("CONFIG_CHANGED", key="bill_reminder_interval_minutes", value=val)
        except Exception:
            pass
        for btn in getattr(self, "bill_interval_chips", []):
            is_on = (btn.tag() == val)
            btn.setState_(AppKit.NSControlStateValueOn if is_on else AppKit.NSControlStateValueOff)
            update_pill_chip_style(btn, is_on, "green")

    @objc.IBAction
    def onApplyPresetRelaxed_(self, sender):
        self.config.set("meeting_reminder_stages", [15, 5, 0])
        self.config.set("general_reminder_stages", [15, 5, 0])
        self.config.set("travel_reminder_stages", [45, 15, 0])
        self._refresh_stage_chips_ui()
        self.parent.refresh_data(force=False)

    @objc.IBAction
    def onApplyPresetStandard_(self, sender):
        self.config.set("meeting_reminder_stages", [20, 10, 5, 2, 0])
        self.config.set("general_reminder_stages", [20, 10, 5, 2, 0])
        self.config.set("travel_reminder_stages", [45, 30, 15, 5, 2, 0])
        self._refresh_stage_chips_ui()
        self.parent.refresh_data(force=False)

    @objc.IBAction
    def onApplyPresetIntensive_(self, sender):
        self.config.set("meeting_reminder_stages", [30, 20, 15, 10, 5, 2, 0])
        self.config.set("general_reminder_stages", [30, 20, 15, 10, 5, 2, 0])
        self.config.set("travel_reminder_stages", [60, 45, 30, 15, 5, 2, 0])
        self._refresh_stage_chips_ui()
        self.parent.refresh_data(force=False)

    @objc.IBAction
    def onToggleMeetingStage_(self, sender):
        val = sender.tag()
        curr = set(self.config.get("meeting_reminder_stages", [20, 10, 5, 2, 0]))
        is_on = (sender.state() == AppKit.NSControlStateValueOn)
        if is_on:
            curr.add(val)
        else:
            curr.discard(val)
        curr.add(0)
        self.config.set("meeting_reminder_stages", sorted(list(curr), reverse=True))
        update_pill_chip_style(sender, is_on, "mauve")

    @objc.IBAction
    def onToggleGeneralStage_(self, sender):
        val = sender.tag()
        curr = set(self.config.get("general_reminder_stages", [20, 10, 5, 2, 0]))
        is_on = (sender.state() == AppKit.NSControlStateValueOn)
        if is_on:
            curr.add(val)
        else:
            curr.discard(val)
        curr.add(0)
        self.config.set("general_reminder_stages", sorted(list(curr), reverse=True))
        update_pill_chip_style(sender, is_on, "blue")

    @objc.IBAction
    def onToggleTravelStage_(self, sender):
        val = sender.tag()
        curr = set(self.config.get("travel_reminder_stages", [45, 30, 15, 5, 2, 0]))
        is_on = (sender.state() == AppKit.NSControlStateValueOn)
        if is_on:
            curr.add(val)
        else:
            curr.discard(val)
        curr.add(0)
        self.config.set("travel_reminder_stages", sorted(list(curr), reverse=True))
        update_pill_chip_style(sender, is_on, "peach")
