import AppKit
import objc
from core.services.calendar_service import calendar_service
from core.services.config_service import is_debug_mode
from core.services.language_service import t
from ui.macos.components import CardView, ModernButton, FlippedView
from ui.macos.dashboard_tabs.settings import (
    CalendarsCardController,
    ETACardController,
    ArrivalCardController,
    SystemCardController,
    TimingCardController,
)
from ui.macos.theme import Theme



class SettingsTabController(AppKit.NSObject):
    """Coordinator for the Settings & Preferences tab on macOS with two-pane sidebar navigation."""

    def init(self):
        self = objc.super(SettingsTabController, self).init()
        self.dashboard_controller = None
        self.config = None
        self.cached_calendars = []
        self._cached_view = None
        self._cached_sig = None
        self.selected_category = 0
        self.category_buttons = []
        self.right_container = None
        self._category_pages = {}

        self.timing_card = TimingCardController.alloc().initWithParent_(self)
        self.eta_card = ETACardController.alloc().initWithParent_(self)
        self.arrival_card = ArrivalCardController.alloc().initWithParent_(self)
        self.calendars_card = CalendarsCardController.alloc().initWithParent_(self)
        self.system_card = SystemCardController.alloc().initWithParent_(self)
        return self

    @objc.python_method
    def invalidate_cache(self):
        self.close_suggestions()
        self._cached_view = None
        self._cached_sig = None
        self._category_pages.clear()
        self.category_buttons = []
        self.right_container = None

    @objc.python_method
    def close_suggestions(self):
        if hasattr(self, "eta_card") and hasattr(self.eta_card, "close_suggestions"):
            self.eta_card.close_suggestions()

    @objc.python_method
    def refresh_data(self, force=False):
        if force:
            self.invalidate_cache()
            if self.dashboard_controller and hasattr(self.dashboard_controller, "refresh_current_tab"):
                self.dashboard_controller.refresh_current_tab()

    @objc.python_method
    def render(self, container, w, h, config, cached_calendars):
        self.dashboard_controller = container
        self.config = config
        self.cached_calendars = cached_calendars

        current_sig = (
            w,
            h,
            is_debug_mode(),
            len(cached_calendars or []),
            config.get("language", "system"),
        )

        if self._cached_view and self._cached_sig == current_sig:
            return self._cached_view

        self.close_suggestions()
        self._category_pages.clear()
        self.category_buttons = []
        view = self._render_settings_tab(w, h)
        self._cached_view = view
        self._cached_sig = current_sig
        return view

    @objc.python_method
    def _render_settings_tab(self, w, h):
        main_view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, w, h))
        sidebar_w = 210.0
        gap = 14.0
        content_w = w - sidebar_w - gap

        # 1. Left Sidebar Navigation Container
        sidebar = self._create_card_container(0, 0, sidebar_w, h)
        self._build_sidebar(sidebar, sidebar_w, h)
        main_view.addSubview_(sidebar)

        # 2. Right Content Container Area
        self.right_container = AppKit.NSView.alloc().initWithFrame_(
            AppKit.NSMakeRect(sidebar_w + gap, 0, content_w, h)
        )
        main_view.addSubview_(self.right_container)

        # Display currently selected category
        self.select_category(self.selected_category)
        return main_view

    @objc.python_method
    def _build_sidebar(self, sidebar, w, h):
        """Constructs the left category navigation sidebar matching Linux styling & hierarchy."""
        header_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(14, h - 34, w - 28, 16))
        header_lbl.setStringValue_(t("settings_categories_header"))
        header_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(10.0))
        header_lbl.setTextColor_(Theme.OVERLAY0)
        header_lbl.setBezeled_(False)
        header_lbl.setDrawsBackground_(False)
        header_lbl.setEditable_(False)
        header_lbl.setSelectable_(False)
        sidebar.addSubview_(header_lbl)

        categories = [
            ("⏱️", t("settings_cat_reminders"), t("settings_cat_reminders_sub"), 0),
            ("📍", t("settings_cat_presence"), t("settings_cat_presence_sub"), 1),
            ("📅", t("settings_cat_calendars"), t("settings_cat_calendars_sub"), 2),
            ("🚗", t("settings_cat_commute"), t("settings_cat_commute_sub"), 3),
            ("⚙️", t("settings_cat_preferences"), t("settings_cat_preferences_sub"), 4),
        ]

        btn_w = w - 16.0
        btn_h = 54.0
        btn_gap = 6.0
        start_y = h - 42.0 - btn_h

        self.category_buttons = []
        for icon, title, subtitle, idx in categories:
            btn_y = start_y - idx * (btn_h + btn_gap)
            btn = ModernButton.alloc().initWithFrame_(AppKit.NSMakeRect(8, btn_y, btn_w, btn_h))
            btn.setTitle_("")
            btn.setTag_(idx)
            btn.setTarget_(self)
            btn.setAction_(objc.selector(self.onSelectCategory_, signature=b"v@:@"))

            # Active left accent bar (4px)
            accent_bar = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 8, 4, 38))
            accent_bar.setWantsLayer_(True)
            accent_bar.layer().setBackgroundColor_(Theme.BLUE.CGColor())
            accent_bar.layer().setCornerRadius_(2.0)
            accent_bar.setHidden_(True)
            btn.addSubview_(accent_bar)
            btn._accent_bar = accent_bar

            # Large Icon label
            icon_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(10, 14, 28, 26))
            icon_lbl.setStringValue_(icon)
            icon_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(18.0))
            icon_lbl.setBezeled_(False)
            icon_lbl.setDrawsBackground_(False)
            icon_lbl.setEditable_(False)
            icon_lbl.setSelectable_(False)
            btn.addSubview_(icon_lbl)

            # Title label
            t_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(42, 27, btn_w - 66, 17))
            t_lbl.setStringValue_(title)
            t_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.0))
            t_lbl.setTextColor_(Theme.TEXT)
            t_lbl.setBezeled_(False)
            t_lbl.setDrawsBackground_(False)
            t_lbl.setEditable_(False)
            t_lbl.setSelectable_(False)
            btn.addSubview_(t_lbl)
            btn._title_lbl = t_lbl

            # Subtitle label
            st_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(42, 10, btn_w - 66, 15))
            st_lbl.setStringValue_(subtitle)
            st_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(10.0))
            st_lbl.setTextColor_(Theme.SUBTEXT0)
            st_lbl.setBezeled_(False)
            st_lbl.setDrawsBackground_(False)
            st_lbl.setEditable_(False)
            st_lbl.setSelectable_(False)
            btn.addSubview_(st_lbl)
            btn._subtitle_lbl = st_lbl

            # Chevron indicator
            arr_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(btn_w - 20, 16, 14, 20))
            arr_lbl.setStringValue_("›")
            arr_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(16.0))
            arr_lbl.setTextColor_(Theme.BLUE)
            arr_lbl.setBezeled_(False)
            arr_lbl.setDrawsBackground_(False)
            arr_lbl.setEditable_(False)
            arr_lbl.setSelectable_(False)
            btn.addSubview_(arr_lbl)
            btn._arrow_lbl = arr_lbl

            sidebar.addSubview_(btn)
            self.category_buttons.append(btn)

    @objc.python_method
    def _update_sidebar_buttons(self):
        for btn in self.category_buttons:
            is_sel = (btn.tag() == self.selected_category)
            if is_sel:
                btn.layer().setBackgroundColor_(Theme.SURFACE0.CGColor())
                btn.layer().setBorderWidth_(1.0)
                btn.layer().setBorderColor_(Theme.SURFACE1.CGColor())
                btn.layer().setCornerRadius_(8.0)
                if hasattr(btn, "_accent_bar"):
                    btn._accent_bar.setHidden_(False)
                if hasattr(btn, "_title_lbl"):
                    btn._title_lbl.setTextColor_(Theme.TEXT)
                if hasattr(btn, "_arrow_lbl"):
                    btn._arrow_lbl.setTextColor_(Theme.BLUE)
            else:
                btn.layer().setBackgroundColor_(AppKit.NSColor.clearColor().CGColor())
                btn.layer().setBorderWidth_(0.0)
                btn.layer().setCornerRadius_(8.0)
                if hasattr(btn, "_accent_bar"):
                    btn._accent_bar.setHidden_(True)
                if hasattr(btn, "_title_lbl"):
                    btn._title_lbl.setTextColor_(Theme.SUBTEXT1)
                if hasattr(btn, "_arrow_lbl"):
                    btn._arrow_lbl.setTextColor_(Theme.SURFACE2)

    @objc.python_method
    def select_category(self, idx):
        self.selected_category = idx
        self.close_suggestions()
        self._update_sidebar_buttons()

        if not self.right_container:
            return

        for sub in list(self.right_container.subviews()):
            sub.removeFromSuperview()

        cw = self.right_container.frame().size.width
        ch = self.right_container.frame().size.height

        if idx not in self._category_pages:
            self._category_pages[idx] = self._build_category_page(idx, cw, ch)

        page = self._category_pages[idx]
        self.right_container.addSubview_(page)

    @objc.python_method
    def _build_category_page(self, idx, content_w, h):
        scroll_view = AppKit.NSScrollView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, content_w, h)
        )
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setDrawsBackground_(False)
        scroll_view.setAutohidesScrollers_(True)

        card_w = content_w - 12.0

        cals = self.cached_calendars if self.cached_calendars else calendar_service.get_available_calendars()
        if not self.cached_calendars and cals:
            self.cached_calendars = cals

        n_cals = len(cals) if cals else 1

        card_heights = {
            0: 460.0,
            1: 424.0,
            2: 80.0 + n_cals * 40.0 + 16.0,
            3: 418.0,
            4: 336.0 if is_debug_mode() else 272.0,
        }
        card_h = card_heights.get(idx, 360.0)
        doc_h = max(h, card_h + 36.0)

        doc_view = FlippedView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, content_w, doc_h))
        card = self._create_card_container(0, 0, card_w, card_h)

        if idx == 0:
            self.timing_card.build_card(card, card_w, card_h)
        elif idx == 1:
            self.arrival_card.build_card(card, card_w, card_h)
        elif idx == 2:
            self.calendars_card.build_card(card, card_w, card_h, cals)
        elif idx == 3:
            self.eta_card.build_card(card, card_w, card_h)
        else:
            self.system_card.build_card(card, card_w, card_h)

        doc_view.addSubview_(card)
        scroll_view.setDocumentView_(doc_view)
        if scroll_view.contentView():
            scroll_view.contentView().scrollToPoint_(AppKit.NSMakePoint(0, 0))
            scroll_view.reflectScrolledClipView_(scroll_view.contentView())

        return scroll_view

    @objc.IBAction
    def onSelectCategory_(self, sender):
        tag = sender.tag()
        if tag != self.selected_category:
            self.select_category(tag)

    @objc.python_method
    def _create_card_container(self, x, y, w, h):
        """Creates a solid card container with Catppuccin Mocha styling."""
        return CardView.create(
            AppKit.NSMakeRect(x, y, w, h),
            bg_color=Theme.MANTLE,
            corner_radius=12.0,
            border_width=1.0,
            border_color=Theme.SURFACE0,
        )


    # ── Backward-compatible Action Delegators ─────────────────────────────
    @objc.IBAction
    def onApplyPresetRelaxed_(self, sender):
        self.timing_card.onApplyPresetRelaxed_(sender)

    @objc.IBAction
    def onApplyPresetStandard_(self, sender):
        self.timing_card.onApplyPresetStandard_(sender)

    @objc.IBAction
    def onApplyPresetIntensive_(self, sender):
        self.timing_card.onApplyPresetIntensive_(sender)

    @objc.IBAction
    def onToggleMeetingStage_(self, sender):
        self.timing_card.onToggleMeetingStage_(sender)

    @objc.IBAction
    def onToggleGeneralStage_(self, sender):
        self.timing_card.onToggleGeneralStage_(sender)

    @objc.IBAction
    def onToggleTravelStage_(self, sender):
        self.timing_card.onToggleTravelStage_(sender)

    @objc.IBAction
    def onSelectBillInterval_(self, sender):
        self.timing_card.onSelectBillInterval_(sender)

    @objc.IBAction
    def onSelectModeBtn_(self, sender):
        self.eta_card.onSelectModeBtn_(sender)

    @objc.IBAction
    def onSaveHomeAddress_(self, sender):
        self.eta_card.onSaveHomeAddress_(sender)

    @objc.IBAction
    def onSaveExamAddress_(self, sender):
        self.eta_card.onSaveExamAddress_(sender)

    @objc.IBAction
    def onSelectETABuffer_(self, sender):
        self.eta_card.onSelectETABuffer_(sender)

    @objc.IBAction
    def onToggleCalendarSource_(self, sender):
        self.calendars_card.onToggleCalendarSource_(sender)

    @objc.IBAction
    def onSelectLanguageBtn_(self, sender):
        self.system_card.onSelectLanguageBtn_(sender)

    @objc.IBAction
    def onCheckForUpdatesMac_(self, sender):
        self.system_card.onCheckForUpdatesMac_(sender)

    @objc.IBAction
    def onInstallUpdateMac_(self, sender):
        self.system_card.onInstallUpdateMac_(sender)

    @objc.IBAction
    def onOpenConfigEditor_(self, sender):
        self.system_card.onOpenConfigEditor_(sender)

    @objc.IBAction
    def onOpenLogs_(self, sender):
        self.system_card.onOpenLogs_(sender)

    @objc.IBAction
    def onOpenLogFolder_(self, sender):
        self.system_card.onOpenLogFolder_(sender)

    @objc.IBAction
    def onOpenLicenseMac_(self, sender):
        self.system_card.onOpenLicenseMac_(sender)
