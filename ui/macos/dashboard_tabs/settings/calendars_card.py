import AppKit
import objc
from core.services.calendar_service import calendar_service
from core.services.event_bus import event_bus
from core.services.language_service import t
from ui.macos.components import ModernButton
from ui.macos.dashboard_tabs.settings.helpers import add_section_header
from ui.macos.theme import Theme


class CalendarsCardController(AppKit.NSObject):
    """Card 3: Included System Calendars."""

    def initWithParent_(self, parent):
        self = objc.super(CalendarsCardController, self).init()
        self.parent = parent
        return self

    @property
    def config(self):
        return self.parent.config

    @objc.python_method
    def _update_calendar_toggle_style(self, btn, is_on):
        """Applies sleek Catppuccin styling matching Qt."""
        if is_on:
            btn.layer().setBackgroundColor_(Theme.SURFACE0.CGColor())
            btn.layer().setBorderWidth_(1.0)
            btn.layer().setBorderColor_(Theme.GREEN.CGColor())
            fg_color = Theme.GREEN
            font = AppKit.NSFont.boldSystemFontOfSize_(11.5)
        else:
            btn.layer().setBackgroundColor_(Theme.MANTLE.CGColor())
            btn.layer().setBorderWidth_(1.0)
            btn.layer().setBorderColor_(Theme.SURFACE1.CGColor())
            fg_color = Theme.SUBTEXT0
            font = AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightMedium)

        pstyle = AppKit.NSMutableParagraphStyle.alloc().init()
        pstyle.setAlignment_(AppKit.NSTextAlignmentLeft)
        pstyle.setFirstLineHeadIndent_(12.0)
        pstyle.setHeadIndent_(12.0)
        attrs = {
            AppKit.NSFontAttributeName: font,
            AppKit.NSForegroundColorAttributeName: fg_color,
            AppKit.NSParagraphStyleAttributeName: pstyle,
        }
        title_str = btn.title() or ""
        attr_str = AppKit.NSAttributedString.alloc().initWithString_attributes_(title_str, attrs)
        btn.setAttributedTitle_(attr_str)

    @objc.python_method
    def build_card(self, card, w, h, cals=None):
        add_section_header(
            card,
            t("settings_calendars_title"),
            t("settings_calendars_subtitle"),
            h, w
        )

        if cals is None:
            cals = self.parent.cached_calendars if self.parent.cached_calendars else calendar_service.get_available_calendars()

        if not cals:
            lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, h - 86, w - 36, 22))
            lbl.setStringValue_(t("settings_all_cals_monitored"))
            lbl.setFont_(AppKit.NSFont.systemFontOfSize_(12))
            lbl.setTextColor_(Theme.SUBTEXT0)
            lbl.setBezeled_(False)
            lbl.setDrawsBackground_(False)
            lbl.setEditable_(False)
            card.addSubview_(lbl)
            return

        row_h = 32.0
        row_gap = 8.0
        y_offset = h - 72.0 - row_h
        popup_w = 175.0
        pill_x = 18.0
        ignored = set(self.config.get("ignored_calendars", []))
        cal_map = self.config.get("calendar_category_map", {})
        if not isinstance(cal_map, dict):
            cal_map = {}

        category_options = [
            ("", t("cal_cat_auto")),
            ("study", t("cal_cat_study")),
            ("work", t("cal_cat_work")),
            ("bill", t("cal_cat_bill")),
            ("concert", t("cal_cat_concert")),
            ("food", t("cal_cat_food")),
            ("travel", t("cal_cat_travel")),
            ("sport", t("cal_cat_sport")),
            ("in_person", t("cal_cat_in_person")),
            ("health", t("cal_cat_health")),
            ("general", t("cal_cat_general")),
        ]

        for idx, cal in enumerate(cals):
            cal_name = cal.get("name", "Calendar")
            title = f"📅  {cal_name}"
            pill_w = max(120.0, w - 36.0 - popup_w - 12.0)
            is_cal_enabled = (cal_name not in ignored)

            btn = ModernButton.alloc().initWithFrame_(
                AppKit.NSMakeRect(pill_x, y_offset, pill_w, 28.0)
            )
            btn.setButtonType_(AppKit.NSButtonTypePushOnPushOff)
            btn.setBordered_(False)
            btn.setFocusRingType_(AppKit.NSFocusRingTypeNone)
            btn.setWantsLayer_(True)
            btn.layer().setCornerRadius_(7.0)
            btn.layer().setMasksToBounds_(True)
            btn.setTag_(idx)
            btn.setTitle_(title)
            btn.setTarget_(self)
            btn.setAction_("onToggleCalendarSource:")
            btn.setState_(AppKit.NSControlStateValueOn if is_cal_enabled else AppKit.NSControlStateValueOff)
            btn.setToolTip_(cal_name)
            self._update_calendar_toggle_style(btn, is_cal_enabled)
            card.addSubview_(btn)

            popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
                AppKit.NSMakeRect(pill_x + pill_w + 12.0, y_offset, popup_w, 28.0), False
            )
            popup.setFont_(AppKit.NSFont.systemFontOfSize_(12.0))
            popup.setTarget_(self)
            popup.setAction_("onSelectCalendarCategory:")
            popup.setToolTip_(cal_name)

            curr_cat = cal_map.get(cal_name, "")
            for opt_val, opt_lbl in category_options:
                item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(opt_lbl, None, "")
                item.setRepresentedObject_(opt_val)
                popup.menu().addItem_(item)
                if opt_val == curr_cat:
                    popup.selectItem_(item)

            card.addSubview_(popup)
            y_offset -= (row_h + row_gap)

    @objc.IBAction
    def onToggleCalendarSource_(self, sender):
        cal_name = sender.toolTip() or sender.title().replace("📅  ", "").replace("📅 ", "")
        is_on = (sender.state() == AppKit.NSControlStateValueOn)
        self._update_calendar_toggle_style(sender, is_on)
        ignored = set(self.config.get("ignored_calendars", []))
        if is_on:
            ignored.discard(cal_name)
        else:
            ignored.add(cal_name)
        self.config.set("ignored_calendars", list(ignored))
        try:
            event_bus.publish("CONFIG_CHANGED", key="ignored_calendars", value=list(ignored))
        except Exception:
            pass

    @objc.IBAction
    def onSelectCalendarCategory_(self, sender):
        cal_name = sender.toolTip()
        if not cal_name:
            return
        sel_item = sender.selectedItem()
        cat_val = str(sel_item.representedObject() or "")
        cal_map = self.config.get("calendar_category_map", {})
        if not isinstance(cal_map, dict):
            cal_map = {}
        else:
            cal_map = cal_map.copy()

        if cat_val:
            cal_map[cal_name] = cat_val
        else:
            cal_map.pop(cal_name, None)

        self.config.set("calendar_category_map", cal_map)
        try:
            event_bus.publish("CONFIG_CHANGED", key="calendar_category_map", value=cal_map)
        except Exception:
            pass

