import AppKit
import objc
from core.autostart import disable_autostart, enable_autostart, is_autostart_enabled
from core.logger import open_log_file, open_log_folder
from core.services.config_service import is_debug_mode
from core.services.event_bus import event_bus
from core.services.language_service import t
from core.services.updater_service import updater_service
from ui.macos.components import ModernButton, ModernToggleSwitch
from ui.macos.dashboard_tabs.settings.helpers import add_section_header
from ui.macos.theme import Theme


class SystemCardController(AppKit.NSObject):
    """Card 4: System, Language, Updates & Diagnostics."""

    def initWithParent_(self, parent):
        self = objc.super(SystemCardController, self).init()
        self.parent = parent
        self.lang_buttons = {}
        self.autostart_sw = None
        self.mute_lessons_sw = None
        self.debug_sw = None
        self.mac_check_update_btn = None
        self.mac_install_update_btn = None
        self.mac_update_status_lbl = None
        self.mac_update_icon = None
        self._subscribe_update_events()
        return self

    @property
    def config(self):
        return self.parent.config

    @property
    def dashboard_controller(self):
        return self.parent.dashboard_controller

    @objc.python_method
    def build_card(self, card, w, h):
        is_dbg = is_debug_mode()
        add_section_header(
            card,
            t("settings_system_lang_diag") if is_dbg else t("settings_system_lang"),
            "",
            h, w
        )

        # 1. Language Selector Row
        lang_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, h - 54, w - 80, 18))
        lang_lbl.setStringValue_(t("settings_lang_selector_label"))
        lang_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.5))
        lang_lbl.setTextColor_(Theme.TEXT)
        lang_lbl.setBezeled_(False)
        lang_lbl.setDrawsBackground_(False)
        lang_lbl.setEditable_(False)
        card.addSubview_(lang_lbl)

        langs = [
            ("system", "🌐 " + t("system_language")),
            ("en", t("language_en")),
            ("it", t("language_it"))
        ]
        curr_lang = self.config.get("language", "system")
        self.lang_buttons = {}
        x_l = 18.0
        btn_l_w = (w - 36.0 - 16.0) / 3.0

        for l_key, l_label in langs:
            l_btn = ModernButton.alloc().initWithFrame_(AppKit.NSMakeRect(x_l, h - 90, btn_l_w, 28))
            l_btn.setTitle_(l_label)
            l_btn.setWantsLayer_(True)
            l_btn.setBordered_(False)
            l_btn.setFocusRingType_(AppKit.NSFocusRingTypeNone)
            l_btn.setButtonType_(AppKit.NSButtonTypeMomentaryPushIn)
            l_btn.layer().setCornerRadius_(7.0)
            l_btn.layer().setMasksToBounds_(True)
            l_btn.setTarget_(self)
            l_btn.setAction_("onSelectLanguageBtn:")
            self.lang_buttons[l_key] = l_btn
            card.addSubview_(l_btn)
            x_l += (btn_l_w + 8.0)

        self._update_language_buttons_ui(curr_lang)

        # 2. Autostart toggle row
        auto_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, h - 124, w - 80, 20))
        auto_lbl.setStringValue_(t("settings_autostart_mac"))
        auto_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.5))
        auto_lbl.setTextColor_(Theme.TEXT)
        auto_lbl.setBezeled_(False)
        auto_lbl.setDrawsBackground_(False)
        auto_lbl.setEditable_(False)
        card.addSubview_(auto_lbl)

        self.autostart_sw = ModernToggleSwitch.alloc().initWithFrame_(AppKit.NSMakeRect(w - 62, h - 126, 44, 24))
        self.autostart_sw.setChecked_(is_autostart_enabled())
        self.autostart_sw.setCallback_(self.onToggleAutostartSwitch)
        card.addSubview_(self.autostart_sw)

        # 3. Mute during lessons toggle row
        mute_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, h - 158, w - 80, 20))
        mute_lbl.setStringValue_(t("settings_mute_lessons"))
        mute_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.5))
        mute_lbl.setTextColor_(Theme.TEXT)
        mute_lbl.setBezeled_(False)
        mute_lbl.setDrawsBackground_(False)
        mute_lbl.setEditable_(False)
        card.addSubview_(mute_lbl)

        self.mute_lessons_sw = ModernToggleSwitch.alloc().initWithFrame_(AppKit.NSMakeRect(w - 62, h - 160, 44, 24))
        self.mute_lessons_sw.setChecked_(self.config.get("mute_during_lessons", True))
        self.mute_lessons_sw.setCallback_(self.onToggleMuteLessonsSwitch)
        card.addSubview_(self.mute_lessons_sw)

        if is_dbg:
            # 4. Debug mode toggle row
            dbg_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(18, h - 192, w - 80, 20))
            dbg_lbl.setStringValue_(t("settings_debug_mode"))
            dbg_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.5))
            dbg_lbl.setTextColor_(Theme.TEXT)
            dbg_lbl.setBezeled_(False)
            dbg_lbl.setDrawsBackground_(False)
            dbg_lbl.setEditable_(False)
            card.addSubview_(dbg_lbl)

            self.debug_sw = ModernToggleSwitch.alloc().initWithFrame_(AppKit.NSMakeRect(w - 62, h - 194, 44, 24))
            self.debug_sw.setChecked_(is_debug_mode())
            self.debug_sw.setCallback_(self.onToggleDebugSwitch)
            card.addSubview_(self.debug_sw)

            # 5. Action Buttons Row (Debug: 5 buttons)
            y_btns = h - 240.0
            btn_w = (w - 36.0 - 32.0) / 5.0

            self.mac_check_update_btn = Theme.create_button(
                AppKit.NSMakeRect(18, y_btns, btn_w, 30),
                title=f"🔍 {t('check_updates')}",
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=11.0,
                bold=True
            )
            self.mac_check_update_btn.setTarget_(self)
            self.mac_check_update_btn.setAction_("onCheckForUpdatesMac:")
            card.addSubview_(self.mac_check_update_btn)

            edit_btn = Theme.create_button(
                AppKit.NSMakeRect(18 + (btn_w + 8.0) * 1, y_btns, btn_w, 30),
                title=t("settings_config_json"),
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=11.0
            )
            edit_btn.setTarget_(self)
            edit_btn.setAction_("onOpenConfigEditor:")
            card.addSubview_(edit_btn)

            view_logs_btn = Theme.create_button(
                AppKit.NSMakeRect(18 + (btn_w + 8.0) * 2, y_btns, btn_w, 30),
                title=t("settings_view_logs"),
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=11.0
            )
            view_logs_btn.setTarget_(self)
            view_logs_btn.setAction_("onOpenLogs:")
            card.addSubview_(view_logs_btn)

            folder_btn = Theme.create_button(
                AppKit.NSMakeRect(18 + (btn_w + 8.0) * 3, y_btns, btn_w, 30),
                title=t("settings_log_folder"),
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=11.0
            )
            folder_btn.setTarget_(self)
            folder_btn.setAction_("onOpenLogFolder:")
            card.addSubview_(folder_btn)

            license_btn = Theme.create_button(
                AppKit.NSMakeRect(18 + (btn_w + 8.0) * 4, y_btns, btn_w, 30),
                title=t("settings_license"),
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=11.0
            )
            license_btn.setTarget_(self)
            license_btn.setAction_("onOpenLicenseMac:")
            card.addSubview_(license_btn)
        else:
            # 4. Action Buttons Row (Normal Mode: Clean 2 buttons)
            y_btns = h - 202.0
            btn_w = (w - 36.0 - 12.0) / 2.0

            self.mac_check_update_btn = Theme.create_button(
                AppKit.NSMakeRect(18, y_btns, btn_w, 30),
                title=f"🔍 {t('check_updates')}",
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=12.0,
                bold=True
            )
            self.mac_check_update_btn.setTarget_(self)
            self.mac_check_update_btn.setAction_("onCheckForUpdatesMac:")
            card.addSubview_(self.mac_check_update_btn)

            license_btn = Theme.create_button(
                AppKit.NSMakeRect(18 + btn_w + 12.0, y_btns, btn_w, 30),
                title=t("settings_license"),
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=7.0,
                font_size=12.0
            )
            license_btn.setTarget_(self)
            license_btn.setAction_("onOpenLicenseMac:")
            card.addSubview_(license_btn)

        # 4. Animated Update Card Status Container
        update_box = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(18, 14, w - 36, 48))
        update_box.setWantsLayer_(True)
        update_box.layer().setBackgroundColor_(Theme.BASE.CGColor())
        update_box.layer().setCornerRadius_(10.0)
        update_box.layer().setMasksToBounds_(True)
        update_box.layer().setBorderWidth_(1.0)
        update_box.layer().setBorderColor_(Theme.SURFACE0.CGColor())

        self.mac_update_icon = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(14, 12, 28, 24))
        self.mac_update_icon.setStringValue_("🦆")
        self.mac_update_icon.setFont_(AppKit.NSFont.systemFontOfSize_(18))
        self.mac_update_icon.setBezeled_(False)
        self.mac_update_icon.setDrawsBackground_(False)
        self.mac_update_icon.setEditable_(False)
        update_box.addSubview_(self.mac_update_icon)

        self.mac_update_status_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(46, 14, w - 240, 20))
        self.mac_update_status_lbl.setStringValue_(t("settings_update_ready", version=updater_service.current_version))
        self.mac_update_status_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
        self.mac_update_status_lbl.setTextColor_(Theme.TEXT)
        self.mac_update_status_lbl.setBezeled_(False)
        self.mac_update_status_lbl.setDrawsBackground_(False)
        self.mac_update_status_lbl.setEditable_(False)
        update_box.addSubview_(self.mac_update_status_lbl)

        self.mac_install_update_btn = Theme.create_gradient_button(
            AppKit.NSMakeRect(w - 36 - 190, 8, 176, 32),
            title=t("settings_install_update_now"),
            start_color=Theme.SAPPHIRE,
            end_color=Theme.BLUE,
            text_color=Theme.CRUST,
            corner_radius=8.0,
            font_size=12.0,
            bold=True
        )
        self.mac_install_update_btn.setTarget_(self)
        self.mac_install_update_btn.setAction_("onInstallUpdateMac:")
        self.mac_install_update_btn.setHidden_(True)
        update_box.addSubview_(self.mac_install_update_btn)

        card.addSubview_(update_box)

    @objc.python_method
    def _subscribe_update_events(self):
        def _on_mac_update_avail(tag_name=None, version=None, **k):
            v_name = tag_name or version or "New Version"
            def update_ui():
                if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
                    self.mac_update_status_lbl.setStringValue_(f"Update Available: {v_name} (Current: v{updater_service.current_version})")
                    self.mac_update_status_lbl.setTextColor_(Theme.SAPPHIRE)
                if hasattr(self, 'mac_update_icon') and self.mac_update_icon:
                    self.mac_update_icon.setStringValue_("🚀")
                if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
                    self.mac_install_update_btn.setTitle_(f"⚡ Install {v_name} Now")
                    self.mac_install_update_btn.setHidden_(False)
                if hasattr(self, 'mac_check_update_btn') and self.mac_check_update_btn:
                    self.mac_check_update_btn.setTitle_("🔍 Check for Updates")
                    self.mac_check_update_btn.setEnabled_(True)
            AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(update_ui)

        def _on_mac_update_check_done(has_update=False, current_version=None, error=None, **k):
            def update_ui():
                if hasattr(self, 'mac_check_update_btn') and self.mac_check_update_btn:
                    self.mac_check_update_btn.setTitle_("🔍 Check for Updates")
                    self.mac_check_update_btn.setEnabled_(True)
                if not has_update:
                    if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
                        if error:
                            self.mac_update_status_lbl.setStringValue_(f"Update check error: {error[:60]}")
                            self.mac_update_status_lbl.setTextColor_(Theme.RED)
                            if hasattr(self, 'mac_update_icon') and self.mac_update_icon:
                                self.mac_update_icon.setStringValue_("⚠️")
                        else:
                            self.mac_update_status_lbl.setStringValue_(f"You are on the latest version!  v{current_version or updater_service.current_version}")
                            self.mac_update_status_lbl.setTextColor_(Theme.GREEN)
                            if hasattr(self, 'mac_update_icon') and self.mac_update_icon:
                                self.mac_update_icon.setStringValue_("✨")
                    if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
                        self.mac_install_update_btn.setHidden_(True)
            AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(update_ui)

        def _on_mac_update_progress(percent=0.0, **k):
            pct = int(percent)
            def update_ui():
                if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
                    self.mac_install_update_btn.setTitle_(f"⏳ Downloading ({pct}%)...")
                if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
                    self.mac_update_status_lbl.setStringValue_(f"Downloading FlightDeck update... ({pct}%)")
            AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(update_ui)

        def _on_mac_update_step(step_id=None, step_name=None, **k):
            def update_ui():
                if step_id == "install":
                    if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
                        self.mac_install_update_btn.setTitle_("📦 Installing...")
                    if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
                        self.mac_update_status_lbl.setStringValue_("Installing update package into /Applications...")
            AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(update_ui)

        def _on_mac_update_installed(**k):
            def update_ui():
                if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
                    self.mac_install_update_btn.setTitle_("✅ Done! Relaunching...")
                if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
                    self.mac_update_status_lbl.setStringValue_("Update successfully installed! Relaunching FlightDeck...")
                    self.mac_update_status_lbl.setTextColor_(Theme.GREEN)
                if hasattr(self, 'mac_update_icon') and self.mac_update_icon:
                    self.mac_update_icon.setStringValue_("🎉")
            AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(update_ui)

        def _on_mac_update_failed(error=None, **k):
            err_text = str(error or "Unknown installation error")
            def update_ui():
                if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
                    self.mac_install_update_btn.setEnabled_(True)
                    self.mac_install_update_btn.setTitle_("🔄 Retry Update")
                if hasattr(self, 'mac_check_update_btn') and self.mac_check_update_btn:
                    self.mac_check_update_btn.setEnabled_(True)
                if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
                    self.mac_update_status_lbl.setStringValue_(f"Update failed: {err_text[:60]}")
                    self.mac_update_status_lbl.setTextColor_(Theme.RED)
                if hasattr(self, 'mac_update_icon') and self.mac_update_icon:
                    self.mac_update_icon.setStringValue_("⚠️")
            AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(update_ui)

        event_bus.subscribe("UPDATE_AVAILABLE", _on_mac_update_avail)
        event_bus.subscribe("UPDATE_CHECK_COMPLETE", _on_mac_update_check_done)
        event_bus.subscribe("UPDATE_DOWNLOAD_PROGRESS", _on_mac_update_progress)
        event_bus.subscribe("UPDATE_STEP", _on_mac_update_step)
        event_bus.subscribe("UPDATE_INSTALLED", _on_mac_update_installed)
        event_bus.subscribe("UPDATE_FAILED", _on_mac_update_failed)

    @objc.python_method
    def onToggleAutostartSwitch(self, is_on):
        if is_on:
            success = enable_autostart()
            if not success and hasattr(self, 'autostart_sw') and self.autostart_sw:
                self.autostart_sw.setChecked_(False)
        else:
            success = disable_autostart()
            if not success and hasattr(self, 'autostart_sw') and self.autostart_sw:
                self.autostart_sw.setChecked_(True)

    @objc.python_method
    def onToggleMuteLessonsSwitch(self, is_on):
        self.config.set("mute_during_lessons", is_on)

    @objc.python_method
    def onToggleDebugSwitch(self, is_on):
        self.config.set("debug_mode", is_on)
        self.parent.invalidate_cache()
        self.parent.refresh_data(force=True)

    @objc.IBAction
    def onSelectLanguageBtn_(self, sender):
        for k, btn in getattr(self, "lang_buttons", {}).items():
            if btn == sender:
                self.config.set("language", k)
                self._update_language_buttons_ui(k)
                try:
                    event_bus.publish("CONFIG_CHANGED", key="language", value=k)
                except Exception:
                    pass
                if self.dashboard_controller and hasattr(self.dashboard_controller, "invalidate_caches"):
                    self.dashboard_controller.invalidate_caches()
                else:
                    self.parent.invalidate_cache()
                if self.dashboard_controller and hasattr(self.dashboard_controller, "_update_localized_ui"):
                    self.dashboard_controller._update_localized_ui()
                self.parent.refresh_data(force=False)
                break

    @objc.python_method
    def _update_language_buttons_ui(self, active_lang):
        for k, btn in getattr(self, "lang_buttons", {}).items():
            is_active = (k == active_lang)
            if is_active:
                btn.layer().setBackgroundColor_(Theme.MAUVE.CGColor())
                btn.layer().setBorderWidth_(1.0)
                btn.layer().setBorderColor_(Theme.LAVENDER.CGColor())
                fg = Theme.CRUST
                fnt = AppKit.NSFont.boldSystemFontOfSize_(12.0)
            else:
                btn.layer().setBackgroundColor_(Theme.SURFACE0.CGColor())
                btn.layer().setBorderWidth_(1.0)
                btn.layer().setBorderColor_(Theme.SURFACE1.CGColor())
                fg = Theme.TEXT
                fnt = AppKit.NSFont.systemFontOfSize_(11.5)

            attr_title = AppKit.NSAttributedString.alloc().initWithString_attributes_(
                btn.title(),
                {
                    AppKit.NSForegroundColorAttributeName: fg,
                    AppKit.NSFontAttributeName: fnt
                }
            )
            btn.setAttributedTitle_(attr_title)

    @objc.IBAction
    def onCheckForUpdatesMac_(self, sender):
        if hasattr(self, 'mac_check_update_btn') and self.mac_check_update_btn:
            self.mac_check_update_btn.setTitle_("⏳ Checking...")
            self.mac_check_update_btn.setEnabled_(False)
        if hasattr(self, 'mac_update_status_lbl') and self.mac_update_status_lbl:
            self.mac_update_status_lbl.setStringValue_("Checking for new releases on GitHub...")
        updater_service.check_for_updates(background=True)

    @objc.IBAction
    def onInstallUpdateMac_(self, sender):
        if hasattr(self, 'mac_install_update_btn') and self.mac_install_update_btn:
            self.mac_install_update_btn.setTitle_("⏳ Preparing...")
            self.mac_install_update_btn.setEnabled_(False)
        updater_service.download_and_install_update(background=True)

    @objc.IBAction
    def onOpenConfigEditor_(self, sender):
        self.config.open_config_in_editor()

    @objc.IBAction
    def onOpenLogs_(self, sender):
        open_log_file()

    @objc.IBAction
    def onOpenLogFolder_(self, sender):
        open_log_folder()

    @objc.IBAction
    def onOpenLicenseMac_(self, sender):
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_(t("license_title"))
        alert.setInformativeText_(t("license_body"))
        alert.addButtonWithTitle_(t("close"))
        alert.addButtonWithTitle_("🌐 Open GitHub Repository")
        resp = alert.runModal()
        if resp == AppKit.NSAlertSecondButtonReturn:
            AppKit.NSWorkspace.sharedWorkspace().openURL_(
                AppKit.NSURL.URLWithString_("https://github.com/Antonino545/FlightDeck")
            )
