import AppKit
import objc
import webbrowser
import threading
import time
from datetime import datetime
from core.domain.models import format_duration
from core.services.eta_service import MODE_ICONS
from core.services.arrival_service import arrival_service
from core.services.language_service import t, get_active_language
from ui.common.agenda_viewmodel import AgendaViewModel, AgendaEventVM, CommandCenterVM
from ui.macos.theme import Theme

class AgendaTabController(AppKit.NSObject):
    def init(self):
        self = objc.super(AgendaTabController, self).init()
        self.dashboard_controller = None
        self.config = None
        self.vms = []
        self._rendered_vms = []
        self._cached_view = None
        self._cached_sig = None
        self._saved_dist_from_top = None
        return self

    @objc.python_method
    def invalidate_cache(self):
        if self._cached_view and self._cached_view.contentView() and self._cached_view.documentView():
            old_doc_h = self._cached_view.documentView().frame().size.height
            clip_y = self._cached_view.contentView().bounds().origin.y
            clip_h = self._cached_view.contentView().bounds().size.height
            self._saved_dist_from_top = max(0.0, old_doc_h - (clip_y + clip_h))
        self._cached_view = None
        self._cached_sig = None

    @objc.python_method
    def render(self, container, w, h, meetings, is_loading, config, clock=None):
        self.dashboard_controller = container
        self.meetings = meetings or []
        self.config = config
        self.command_center = AgendaViewModel.build_command_center(self.meetings, clock=clock, lang=get_active_language())
        self.vms = self.command_center.all_events
        self._rendered_vms = []

        if is_loading and not self.meetings:
            loading_view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, w, h))

            spinner = AppKit.NSProgressIndicator.alloc().initWithFrame_(AppKit.NSMakeRect((w - 32) * 0.5, (h - 32) * 0.5 + 24, 32, 32))
            spinner.setStyle_(AppKit.NSProgressIndicatorStyleSpinning)
            spinner.setControlSize_(AppKit.NSControlSizeRegular)
            spinner.startAnimation_(None)
            loading_view.addSubview_(spinner)

            load_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(20, (h - 32) * 0.5 - 34, w - 40, 48))
            load_lbl.setStringValue_(f"🦆 {t('agenda_today_flights')}...\n{t('scanner_active_no_events')}")
            load_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(13.5))
            load_lbl.setTextColor_(AppKit.NSColor.colorWithRed_green_blue_alpha_(0.72, 0.78, 0.92, 1.0))
            load_lbl.setAlignment_(AppKit.NSTextAlignmentCenter)
            load_lbl.setBezeled_(False)
            load_lbl.setDrawsBackground_(False)
            load_lbl.setEditable_(False)
            loading_view.addSubview_(load_lbl)

            return loading_view

        scroll_view = AppKit.NSScrollView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, w, h))
        scroll_view.setHasVerticalScroller_(True)
        scroll_view.setDrawsBackground_(False)
        scroll_view.setAutohidesScrollers_(True)

        header_h = 24.0
        hero_card_h = 106.0
        std_card_h = 76.0
        gap = 12.0
        top_pad = 16.0

        # Calculate required height for Command Center sections
        content_h = top_pad + 20.0
        if self.command_center.now_event:
            content_h += header_h + hero_card_h + gap
        if self.command_center.next_event:
            content_h += header_h + std_card_h + gap
        if self.command_center.later_events:
            content_h += header_h + len(self.command_center.later_events) * (std_card_h + gap)
        if self.command_center.earlier_events:
            content_h += header_h + len(self.command_center.earlier_events) * (std_card_h + gap)

        content_h = max(h, content_h)
        doc_view = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, w, content_h))

        if not self.command_center.has_events:
            empty_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(20, content_h - 100, w - 40, 50))
            empty_lbl.setStringValue_(f"🧘‍♂️ {t('agenda_no_flights')}\n{t('all_caught_up')}")
            empty_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(14))
            empty_lbl.setTextColor_(Theme.SUBTEXT0)
            empty_lbl.setAlignment_(AppKit.NSTextAlignmentCenter)
            empty_lbl.setBezeled_(False)
            empty_lbl.setDrawsBackground_(False)
            empty_lbl.setEditable_(False)
            doc_view.addSubview_(empty_lbl)
        else:
            cur_y = content_h - top_pad

            # 1. NOW SECTION (Hero Card + Why? Explanation)
            if self.command_center.now_event:
                cur_y -= header_h
                doc_view.addSubview_(self._create_section_header("⚡️ NOW", 0, cur_y, w - 16))
                cur_y -= hero_card_h
                hero_idx = len(self._rendered_vms)
                self._rendered_vms.append(self.command_center.now_event)
                doc_view.addSubview_(
                    self._create_hero_card(
                        self.command_center.now_event,
                        self.command_center.guidance,
                        hero_idx,
                        0, cur_y, w - 16, hero_card_h
                    )
                )
                cur_y -= gap

            # 2. NEXT SECTION
            if self.command_center.next_event:
                cur_y -= header_h
                doc_view.addSubview_(self._create_section_header("🗓️ NEXT", 0, cur_y, w - 16))
                cur_y -= std_card_h
                next_idx = len(self._rendered_vms)
                self._rendered_vms.append(self.command_center.next_event)
                doc_view.addSubview_(
                    self._create_meeting_card(
                        self.command_center.next_event,
                        next_idx,
                        0, cur_y, w - 16, std_card_h
                    )
                )
                cur_y -= gap

            # 3. LATER SECTION
            if self.command_center.later_events:
                cur_y -= header_h
                doc_view.addSubview_(self._create_section_header("🕒 LATER TODAY", 0, cur_y, w - 16))
                for ev in self.command_center.later_events:
                    cur_y -= std_card_h
                    later_idx = len(self._rendered_vms)
                    self._rendered_vms.append(ev)
                    doc_view.addSubview_(
                        self._create_meeting_card(
                            ev,
                            later_idx,
                            0, cur_y, w - 16, std_card_h
                        )
                    )
                    cur_y -= gap

            # 4. EARLIER TODAY SECTION (Completed / Past events)
            if self.command_center.earlier_events:
                cur_y -= header_h
                earlier_hdr = t("agenda_earlier_today", default="🏁 EARLIER TODAY")
                doc_view.addSubview_(self._create_section_header(earlier_hdr, 0, cur_y, w - 16, color=Theme.SUBTEXT0))
                for ev in self.command_center.earlier_events:
                    cur_y -= std_card_h
                    earlier_idx = len(self._rendered_vms)
                    self._rendered_vms.append(ev)
                    doc_view.addSubview_(
                        self._create_meeting_card(
                            ev,
                            earlier_idx,
                            0, cur_y, w - 16, std_card_h,
                            is_completed=True
                        )
                    )
                    cur_y -= gap

        scroll_view.setDocumentView_(doc_view)
        if scroll_view.contentView():
            if hasattr(self, "_saved_dist_from_top") and self._saved_dist_from_top is not None:
                target_y = max(0.0, min(content_h - h, content_h - h - self._saved_dist_from_top))
            else:
                target_y = max(0.0, content_h - h)
            scroll_view.contentView().scrollToPoint_(AppKit.NSMakePoint(0, target_y))
            scroll_view.reflectScrolledClipView_(scroll_view.contentView())
        return scroll_view

    @objc.python_method
    def _create_section_header(self, title, x, y, w, h=22, color=None):
        header_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(x + 4, y, w, h))
        header_lbl.setStringValue_(title)
        header_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(11.5))
        header_lbl.setTextColor_(color or Theme.BLUE)
        header_lbl.setBezeled_(False)
        header_lbl.setDrawsBackground_(False)
        header_lbl.setEditable_(False)
        return header_lbl

    @objc.python_method
    def _create_hero_card(self, vm, guidance, idx, x, y, w, h):
        """Prominent Hero Card with Why? explanation box for active or imminent events."""
        card = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(x, y, w, h))
        card.setWantsLayer_(True)
        card.layer().setBackgroundColor_(Theme.MANTLE.CGColor())
        card.layer().setCornerRadius_(14.0)
        card.layer().setMasksToBounds_(True)
        card.layer().setBorderWidth_(1.5)

        # Highlight border according to urgency
        border_color = Theme.PEACH if vm.is_urgent else Theme.BLUE
        card.layer().setBorderColor_(border_color.CGColor())

        icon_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(14, h - 52, 40, 40))
        icon_lbl.setStringValue_(vm.icon)
        icon_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(30))
        icon_lbl.setBezeled_(False)
        icon_lbl.setDrawsBackground_(False)
        icon_lbl.setEditable_(False)
        card.addSubview_(icon_lbl)

        title_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(62, h - 34, w - 275, 24))
        title_lbl.setStringValue_(f"{vm.time_display}  •  {vm.title}")
        title_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(14.5))
        title_lbl.setTextColor_(Theme.TEXT)
        title_lbl.setBezeled_(False)
        title_lbl.setDrawsBackground_(False)
        title_lbl.setEditable_(False)
        card.addSubview_(title_lbl)

        # Subtitle
        sub_str = vm.subtitle
        if vm.badge_text:
            sub_str = f"{sub_str}  •  {vm.badge_text}" if sub_str else vm.badge_text

        sub_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(62, h - 54, w - 275, 18))
        sub_lbl.setStringValue_(sub_str)
        sub_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(11.5))
        sub_lbl.setTextColor_(Theme.SUBTEXT0)
        sub_lbl.setBezeled_(False)
        sub_lbl.setDrawsBackground_(False)
        sub_lbl.setEditable_(False)
        card.addSubview_(sub_lbl)

        # "Why?" Transparency Box
        why_box = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(14, 10, w - 28, 38))
        why_box.setWantsLayer_(True)
        why_box.layer().setBackgroundColor_(Theme.SURFACE0.CGColor())
        why_box.layer().setCornerRadius_(8.0)
        why_box.layer().setMasksToBounds_(True)

        is_active_session = False
        if guidance and getattr(guidance, "action_type", None):
            from core.domain.context_engine import ActionType
            is_active_session = (guidance.action_type == ActionType.ACTIVE_SESSION)

        if is_active_session and guidance and guidance.rationale:
            why_text = str(guidance.rationale)
        elif guidance and guidance.rationale:
            why_text = f"💡 {guidance.rationale}"
        else:
            why_text = f"💡 {vm.countdown_text or 'Active event'}"
        why_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(10, 8, w - 48, 22))
        why_lbl.setStringValue_(why_text)
        why_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(11.5))
        why_lbl.setTextColor_(Theme.YELLOW)
        why_lbl.setBezeled_(False)
        why_lbl.setDrawsBackground_(False)
        why_lbl.setEditable_(False)
        why_box.addSubview_(why_lbl)
        card.addSubview_(why_box)

        # Action Buttons
        if vm.has_action:
            action_btn = Theme.create_button(
                AppKit.NSMakeRect(w - 142, h - 46, 126, 34),
                title=vm.action_btn_text or t("agenda_join_button", default="🚀 Join"),
                bg_color=Theme.BLUE,
                text_color=Theme.CRUST,
                border_color=None,
                corner_radius=8.0,
                font_size=12.0,
                bold=True
            )
            action_btn.setTarget_(self)
            action_btn.setAction_("onOpenMeetingUrl:")
            action_btn.setTag_(idx)
            card.addSubview_(action_btn)

            copy_btn = Theme.create_button(
                AppKit.NSMakeRect(w - 238, h - 46, 90, 34),
                title="📋 " + t("copy"),
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=8.0,
                font_size=11.5,
                bold=False
            )
            copy_btn.setTarget_(self)
            copy_btn.setAction_("onCopyMeetingUrl:")
            copy_btn.setTag_(idx)
            card.addSubview_(copy_btn)

        # Bill "Mark as Paid" button
        if vm.is_bill and not vm.is_paid:
            paid_x = 10
            paid_btn = Theme.create_button(
                AppKit.NSMakeRect(paid_x, h - 46, 140, 34),
                title=f"✅ {t('agenda_mark_paid', default='Mark Paid')}",
                bg_color=Theme.GREEN,
                text_color=Theme.CRUST,
                border_color=None,
                corner_radius=8.0,
                font_size=12.0,
                bold=True
            )
            paid_btn.setTarget_(self)
            paid_btn.setAction_("onMarkBillPaid:")
            paid_btn.setTag_(idx)
            card.addSubview_(paid_btn)

        return card

    @objc.python_method
    def _create_meeting_card(self, vm, idx, x, y, w, h, is_completed=False):
        card = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(x, y, w, h))
        card.setWantsLayer_(True)
        bg_color = Theme.MANTLE if is_completed else Theme.BASE
        card.layer().setBackgroundColor_(bg_color.CGColor())
        card.layer().setCornerRadius_(12.0)
        card.layer().setMasksToBounds_(True)
        card.layer().setBorderWidth_(1.0)
        card.layer().setBorderColor_(Theme.SURFACE0.CGColor())

        icon_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(14, 18, 40, 40))
        icon_lbl.setStringValue_(vm.icon)
        icon_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(26))
        icon_lbl.setBezeled_(False)
        icon_lbl.setDrawsBackground_(False)
        icon_lbl.setEditable_(False)
        if is_completed:
            icon_lbl.setAlphaValue_(0.7)
        card.addSubview_(icon_lbl)

        title_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(62, 38, w - 275, 24))
        title_lbl.setStringValue_(f"{vm.time_display}  •  {vm.title}")
        title_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(14))
        title_lbl.setTextColor_(Theme.SUBTEXT0 if is_completed else Theme.TEXT)
        title_lbl.setBezeled_(False)
        title_lbl.setDrawsBackground_(False)
        title_lbl.setEditable_(False)
        card.addSubview_(title_lbl)

        sub_str = vm.subtitle
        if vm.badge_text:
            sub_str = f"{sub_str}  •  {vm.badge_text}" if sub_str else vm.badge_text

        sub_lbl = AppKit.NSTextField.alloc().initWithFrame_(AppKit.NSMakeRect(62, 16, w - 275, 20))
        sub_lbl.setStringValue_(sub_str)
        sub_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(11.5))
        sub_lbl.setTextColor_(Theme.OVERLAY0 if is_completed else Theme.SUBTEXT0)
        sub_lbl.setBezeled_(False)
        sub_lbl.setDrawsBackground_(False)
        sub_lbl.setEditable_(False)
        card.addSubview_(sub_lbl)

        if vm.has_action:
            btn_bg = Theme.SURFACE0 if is_completed else Theme.BLUE
            btn_text_color = Theme.TEXT if is_completed else Theme.CRUST
            action_btn = Theme.create_button(
                AppKit.NSMakeRect(w - 142, 20, 126, 34),
                title=vm.action_btn_text or t("agenda_join_button", default="🚀 Join"),
                bg_color=btn_bg,
                text_color=btn_text_color,
                border_color=Theme.SURFACE1 if is_completed else None,
                corner_radius=8.0,
                font_size=12.0,
                bold=not is_completed
            )
            action_btn.setTarget_(self)
            action_btn.setAction_("onOpenMeetingUrl:")
            action_btn.setTag_(idx)
            card.addSubview_(action_btn)

            copy_title = "📋 " + t("copy")
            copy_btn = Theme.create_button(
                AppKit.NSMakeRect(w - 238, 20, 90, 34),
                title=copy_title,
                bg_color=Theme.SURFACE0,
                text_color=Theme.TEXT,
                border_color=Theme.SURFACE1,
                corner_radius=8.0,
                font_size=11.5,
                bold=False
            )
            copy_btn.setTarget_(self)
            copy_btn.setAction_("onCopyMeetingUrl:")
            copy_btn.setTag_(idx)
            card.addSubview_(copy_btn)

        # Bill "Mark as Paid" button
        if vm.is_bill and not vm.is_paid:
            paid_btn = Theme.create_button(
                AppKit.NSMakeRect(62, 20, 130, 34),
                title=f"✅ {t('agenda_mark_paid', default='Mark Paid')}",
                bg_color=Theme.GREEN,
                text_color=Theme.CRUST,
                border_color=None,
                corner_radius=8.0,
                font_size=11.5,
                bold=True
            )
            paid_btn.setTarget_(self)
            paid_btn.setAction_("onMarkBillPaid:")
            paid_btn.setTag_(idx)
            card.addSubview_(paid_btn)

        return card

    def onOpenMeetingUrl_(self, sender):
        idx = sender.tag()
        target_list = self._rendered_vms if hasattr(self, "_rendered_vms") and self._rendered_vms else self.vms
        if 0 <= idx < len(target_list):
            url = target_list[idx].action_url
            if url:
                webbrowser.open(url)

    def onCopyMeetingUrl_(self, sender):
        idx = sender.tag()
        target_list = self._rendered_vms if hasattr(self, "_rendered_vms") and self._rendered_vms else self.vms
        if 0 <= idx < len(target_list):
            url = target_list[idx].action_url
            if url:
                pasteboard = AppKit.NSPasteboard.generalPasteboard()
                pasteboard.clearContents()
                pasteboard.setString_forType_(url, AppKit.NSPasteboardTypeString)
                sender.setTitle_("✓ " + t("saved"))
                def reset():
                    time.sleep(1.5)
                    AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(lambda: sender.setTitle_("📋 " + t("copy")))
                threading.Thread(target=reset, daemon=True).start()

    def onMarkBillPaid_(self, sender):
        idx = sender.tag()
        target_list = self._rendered_vms if hasattr(self, "_rendered_vms") and self._rendered_vms else self.vms
        if 0 <= idx < len(target_list):
            vm = target_list[idx]
            uid = vm.uid
            try:
                from core.services.reminder_engine import reminder_engine
                reminder_engine.mark_bill_paid(uid)
            except Exception:
                pass
            try:
                from core.services.event_bus import event_bus
                event_bus.publish("MARK_PAID", meeting_id=uid)
            except Exception:
                pass
            # Visual feedback
            sender.setTitle_(f"✅ {t('agenda_paid_badge', default='Paid')}")
            sender.setEnabled_(False)
            # Refresh agenda after short delay
            def _refresh():
                time.sleep(0.5)
                if self.dashboard_controller and hasattr(self.dashboard_controller, "invalidate_cache"):
                    AppKit.NSOperationQueue.mainQueue().addOperationWithBlock_(
                        lambda: self.dashboard_controller.invalidate_cache()
                    )
            threading.Thread(target=_refresh, daemon=True).start()
