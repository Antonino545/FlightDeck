"""
Quartz 2D Banner HUD Painter for macOS QuakPit Banners.
Encapsulates all Quartz drawing operations: Glass card, Pills, Details, Buttons Bar, Cables, and Pilot Speech Bubble.
"""
import math
import AppKit
from typing import Dict, Any, Optional

from ui.macos.theme import Theme
from core.services.language_service import t
from ui.common.banner_particles import compute_towing_cable_hooks

class BannerHUDPainter:
    def __init__(self):
        self.font_title = AppKit.NSFont.boldSystemFontOfSize_(14.5)
        self.font_sub = AppKit.NSFont.systemFontOfSize_(11.5)
        self.font_pill = AppKit.NSFont.boldSystemFontOfSize_(10.5)
        self.font_btn = AppKit.NSFont.boldSystemFontOfSize_(12.5)
        self.font_btn_sec = AppKit.NSFont.boldSystemFontOfSize_(11.5)
        self.font_bubble = AppKit.NSFont.boldSystemFontOfSize_(10.5)

        self.color_white = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.97, 1.0, 1.0)
        self.color_sub = AppKit.NSColor.colorWithRed_green_blue_alpha_(0.70, 0.74, 0.86, 1.0)
        self.color_arrived = Theme.GREEN
        self.color_urgent_time = Theme.RED
        self.color_normal_time = Theme.YELLOW

    @staticmethod
    def _centered_text_point(text, rect, attributes):
        text_size = text.sizeWithAttributes_(attributes)
        return AppKit.NSMakePoint(
            rect.origin.x + (rect.size.width - text_size.width) / 2.0,
            rect.origin.y + (rect.size.height - text_size.height) / 2.0,
        )

    def draw_towing_cables(self, bx: float, by: float, bw: float, bh: float, px: float, py: float, is_late: bool, pitch_deg: float = 0.0, tick: int = 0):
        cable_col = Theme.RED.colorWithAlphaComponent_(0.75) if is_late else Theme.SUBTEXT1.colorWithAlphaComponent_(0.45)
        cable_col.set()

        (hook_top_x, hook_top_y), (hook_bot_x, hook_bot_y) = compute_towing_cable_hooks(px, py, pitch_deg, is_qt_coords=False)
        dx = hook_top_x - (bx + bw)
        vibe = (math.sin(tick * 0.55) * 1.8) if is_late else (math.sin(tick * 0.38) * 1.2)

        cable_top = AppKit.NSBezierPath.bezierPath()
        cable_top.setLineWidth_(1.5)
        cable_top.moveToPoint_(AppKit.NSMakePoint(bx + bw, by + bh - 24.0))
        ctrl_pt1 = AppKit.NSMakePoint(bx + bw + dx * 0.45, by + bh - 16.0 - vibe)
        cable_top.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(hook_top_x, hook_top_y),
            ctrl_pt1,
            AppKit.NSMakePoint(hook_top_x - 16.0, hook_top_y + 2.0 + vibe)
        )
        cable_top.stroke()

        cable_bot = AppKit.NSBezierPath.bezierPath()
        cable_bot.setLineWidth_(1.5)
        cable_bot.moveToPoint_(AppKit.NSMakePoint(bx + bw, by + 24.0))
        ctrl_pt2 = AppKit.NSMakePoint(bx + bw + dx * 0.45, by + 16.0 + vibe)
        cable_bot.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(hook_bot_x, hook_bot_y),
            ctrl_pt2,
            AppKit.NSMakePoint(hook_bot_x - 16.0, hook_bot_y - 2.0 - vibe)
        )
        cable_bot.stroke()

    def draw_glass_banner_card(self, bx: float, by: float, bw: float, bh: float, is_late: bool, tick: int, reminder_stage: Optional[int] = None):
        card_rect = AppKit.NSMakeRect(bx, by, bw, bh)
        card_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(card_rect, 16.0, 16.0)

        # Solid Catppuccin Base
        Theme.BASE.set()
        card_path.fill()

        # Subtle rim border / Emergency red pulse when late / Lavender glow for flyby
        if is_late:
            pulse = math.sin(tick * 0.15) * 0.3 + 0.7
            border_col = Theme.RED.colorWithAlphaComponent_(pulse)
            card_path.setLineWidth_(1.8)
        elif reminder_stage is not None and reminder_stage > 0:
            border_col = Theme.LAVENDER.colorWithAlphaComponent_(0.45)
            card_path.setLineWidth_(1.2)
        else:
            border_col = Theme.SURFACE0
            card_path.setLineWidth_(1.0)

        border_col.set()
        card_path.stroke()

    def draw_provider_and_classroom_pills(self, bx: float, by: float, bh: float, provider: str, classroom: Optional[str], accent: AppKit.NSColor, reminder_stage: Optional[int] = None):
        attrs = {
            AppKit.NSFontAttributeName: self.font_pill,
            AppKit.NSForegroundColorAttributeName: accent
        }

        ns_str = AppKit.NSString.stringWithString_(provider.upper())
        str_size = ns_str.sizeWithAttributes_(attrs)
        pill_w = str_size.width + 16.0
        pill_h = 20.0

        pill_x = bx + 18.0
        pill_y = by + bh - 32.0

        pill_rect = AppKit.NSMakeRect(pill_x, pill_y, pill_w, pill_h)
        pill_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, 10.0, 10.0)

        accent.colorWithAlphaComponent_(0.14).set()
        pill_path.fill()

        accent.colorWithAlphaComponent_(0.38).set()
        pill_path.setLineWidth_(1.0)
        pill_path.stroke()

        text_pt = AppKit.NSMakePoint(pill_x + 8.0, pill_y + 3.0)
        ns_str.drawAtPoint_withAttributes_(text_pt, attrs)

        next_x = pill_x + pill_w + 8.0

        # Draw Classroom Badge if available
        if classroom:
            c_attrs = {
                AppKit.NSFontAttributeName: self.font_pill,
                AppKit.NSForegroundColorAttributeName: Theme.MAUVE
            }
            c_str = AppKit.NSString.stringWithString_(f"🏫 {classroom}")
            c_size = c_str.sizeWithAttributes_(c_attrs)
            c_pill_x = next_x
            c_pill_rect = AppKit.NSMakeRect(c_pill_x, pill_y, c_size.width + 14.0, pill_h)
            c_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(c_pill_rect, 10.0, 10.0)

            Theme.MAUVE.colorWithAlphaComponent_(0.15).set()
            c_path.fill()
            Theme.MAUVE.colorWithAlphaComponent_(0.45).set()
            c_path.setLineWidth_(1.0)
            c_path.stroke()

            c_str.drawAtPoint_withAttributes_(AppKit.NSMakePoint(c_pill_x + 7.0, pill_y + 3.0), c_attrs)
            next_x = c_pill_x + c_size.width + 14.0 + 8.0

        # Draw Flyby Badge if advance reminder
        if reminder_stage is not None and reminder_stage > 0:
            fly_attrs = {
                AppKit.NSFontAttributeName: self.font_pill,
                AppKit.NSForegroundColorAttributeName: Theme.LAVENDER
            }
            fly_str = AppKit.NSString.stringWithString_(t("banner_flyby_pill"))
            fly_size = fly_str.sizeWithAttributes_(fly_attrs)
            fly_pill_rect = AppKit.NSMakeRect(next_x, pill_y, fly_size.width + 14.0, pill_h)
            fly_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(fly_pill_rect, 10.0, 10.0)

            Theme.LAVENDER.colorWithAlphaComponent_(0.15).set()
            fly_path.fill()
            Theme.LAVENDER.colorWithAlphaComponent_(0.45).set()
            fly_path.setLineWidth_(1.0)
            fly_path.stroke()

            fly_str.drawAtPoint_withAttributes_(AppKit.NSMakePoint(next_x + 7.0, pill_y + 3.0), fly_attrs)

    def draw_countdown_pill(self, bx: float, by: float, bw: float, bh: float, countdown_text: str, is_urgent: bool):
        time_col = self.color_urgent_time if is_urgent else self.color_normal_time

        attrs = {
            AppKit.NSFontAttributeName: self.font_pill,
            AppKit.NSForegroundColorAttributeName: time_col
        }

        ns_str = AppKit.NSString.stringWithString_(countdown_text)
        str_size = ns_str.sizeWithAttributes_(attrs)
        pill_w = str_size.width + 18.0
        pill_h = 20.0

        pill_x = bx + bw - 44.0 - pill_w
        pill_y = by + bh - 32.0

        pill_rect = AppKit.NSMakeRect(pill_x, pill_y, pill_w, pill_h)
        pill_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, 10.0, 10.0)

        bg_col = Theme.RED.colorWithAlphaComponent_(0.20) if is_urgent else Theme.MANTLE
        bg_col.set()
        pill_path.fill()

        border_col = time_col.colorWithAlphaComponent_(0.55)
        border_col.set()
        pill_path.setLineWidth_(1.0)
        pill_path.stroke()

        text_pt = AppKit.NSMakePoint(pill_x + 9.0, pill_y + 3.0)
        ns_str.drawAtPoint_withAttributes_(text_pt, attrs)

    def draw_close_button(self, bx: float, by: float, bw: float, bh: float, pressed_button: Optional[str], hovered_button: Optional[str]):
        is_pressed = (pressed_button == "close")
        is_hovered = (hovered_button == "close")

        btn_rect = AppKit.NSMakeRect(bx + bw - 36.0, by + bh - 34.0, 24.0, 24.0)
        btn_path = AppKit.NSBezierPath.bezierPathWithOvalInRect_(btn_rect)

        if is_pressed:
            fill_col = Theme.SURFACE1
        elif is_hovered:
            fill_col = Theme.SURFACE0
        else:
            fill_col = Theme.MANTLE

        fill_col.set()
        btn_path.fill()

        border_col = Theme.SURFACE1
        border_col.set()
        btn_path.setLineWidth_(1.0)
        btn_path.stroke()

        close_attrs = {
            AppKit.NSFontAttributeName: self.font_btn_sec,
            AppKit.NSForegroundColorAttributeName: Theme.TEXT if is_hovered else Theme.SUBTEXT0
        }
        close_text = AppKit.NSString.stringWithString_("✕")
        close_text.drawAtPoint_withAttributes_(
            self._centered_text_point(close_text, btn_rect, close_attrs),
            close_attrs
        )

    def draw_event_details(self, bx: float, by: float, bh: float, title_text: str, detail_text: str, bw: float = 535.0):
        para_style = AppKit.NSMutableParagraphStyle.alloc().init()
        para_style.setLineBreakMode_(AppKit.NSLineBreakByTruncatingTail)

        max_text_w = max(100.0, bw - 60.0)

        title_attrs = {
            AppKit.NSFontAttributeName: self.font_title,
            AppKit.NSForegroundColorAttributeName: self.color_white,
            AppKit.NSParagraphStyleAttributeName: para_style
        }
        clean_title = " ".join(str(title_text or "").split())
        title_rect = AppKit.NSMakeRect(bx + 18.0, by + bh - 58.0, max_text_w, 20.0)
        AppKit.NSString.stringWithString_(clean_title).drawWithRect_options_attributes_(
            title_rect,
            AppKit.NSStringDrawingUsesLineFragmentOrigin | AppKit.NSStringDrawingTruncatesLastVisibleLine,
            title_attrs
        )

        sub_attrs = {
            AppKit.NSFontAttributeName: self.font_sub,
            AppKit.NSForegroundColorAttributeName: self.color_sub,
            AppKit.NSParagraphStyleAttributeName: para_style
        }
        clean_detail = " ".join(str(detail_text or "").split())
        sub_rect = AppKit.NSMakeRect(bx + 18.0, by + bh - 78.0, max_text_w, 18.0)
        AppKit.NSString.stringWithString_(clean_detail).drawWithRect_options_attributes_(
            sub_rect,
            AppKit.NSStringDrawingUsesLineFragmentOrigin | AppKit.NSStringDrawingTruncatesLastVisibleLine,
            sub_attrs
        )

    def draw_buttons_bar(
        self,
        bx: float,
        by: float,
        palette: Dict[str, Any],
        has_real_url: bool,
        action_btn_text: str,
        has_maps_url: bool,
        reminder_stage: Optional[int],
        button_rects: Dict[str, AppKit.NSRect],
        pressed_button: Optional[str],
        hovered_button: Optional[str],
        is_bill: bool = False
    ):
        # 1. Main Action Button
        btn_act_rect = button_rects["action"]
        if btn_act_rect.size.width > 0:
            is_pressed_act = (pressed_button == "action")
            is_hovered_act = (hovered_button == "action")
            btn_act_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(btn_act_rect, 9.0, 9.0)

            if not has_real_url:
                top_c = Theme.SAPPHIRE
                bot_c = Theme.BLUE
                btn_text = t("banner_got_it")
                txt_c = Theme.CRUST
            else:
                if has_maps_url:
                    top_c = Theme.SKY
                    bot_c = Theme.SAPPHIRE
                else:
                    top_c = palette["btn_gradient_top"]
                    bot_c = palette["btn_gradient_bot"]
                btn_text = action_btn_text
                txt_c = Theme.CRUST

            if is_pressed_act:
                grad = AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(bot_c, top_c)
            elif is_hovered_act:
                if not has_real_url:
                    hover_color = Theme.SKY
                elif has_maps_url:
                    hover_color = Theme.TEAL
                else:
                    hover_color = palette["accent_bright"]
                grad = AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(hover_color, bot_c)
            else:
                grad = AppKit.NSGradient.alloc().initWithStartingColor_endingColor_(top_c, bot_c)

            grad.drawInBezierPath_angle_(btn_act_path, 270.0)

            btn_attrs = {
                AppKit.NSFontAttributeName: self.font_btn,
                AppKit.NSForegroundColorAttributeName: txt_c
            }
            ns_btn_str = AppKit.NSString.stringWithString_(btn_text)
            str_size = ns_btn_str.sizeWithAttributes_(btn_attrs)
            text_x = btn_act_rect.origin.x + (btn_act_rect.size.width - str_size.width) * 0.5
            text_y = btn_act_rect.origin.y + (btn_act_rect.size.height - str_size.height) * 0.5
            ns_btn_str.drawAtPoint_withAttributes_(AppKit.NSMakePoint(text_x, text_y), btn_attrs)

        # 2. "📍 I'm Here" / "✅ Mark Paid" Dismissal Button
        if (has_maps_url or is_bill) and button_rects["arrived"].size.width > 0:
            is_pressed_arr = (pressed_button == "arrived")
            is_hovered_arr = (hovered_button == "arrived")

            btn_arr_rect = button_rects["arrived"]
            btn_arr_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(btn_arr_rect, 9.0, 9.0)

            if is_pressed_arr:
                arr_fill = Theme.SURFACE1
            elif is_hovered_arr:
                arr_fill = Theme.SURFACE0
            else:
                arr_fill = Theme.MANTLE

            arr_fill.set()
            btn_arr_path.fill()

            btn2_color = Theme.GREEN if is_bill else self.color_arrived
            arr_border = btn2_color.colorWithAlphaComponent_(0.50)
            arr_border.set()
            btn_arr_path.setLineWidth_(1.0)
            btn_arr_path.stroke()

            arr_attrs = {
                AppKit.NSFontAttributeName: self.font_btn_sec,
                AppKit.NSForegroundColorAttributeName: btn2_color
            }
            btn2_text = t("banner_mark_paid", default="✅ Mark Paid") if is_bill else t("banner_im_here", default="📍 I'm Here")
            ns_arr_str = AppKit.NSString.stringWithString_(btn2_text)
            arr_size = ns_arr_str.sizeWithAttributes_(arr_attrs)
            arr_tx = btn_arr_rect.origin.x + (btn_arr_rect.size.width - arr_size.width) * 0.5
            arr_ty = btn_arr_rect.origin.y + (btn_arr_rect.size.height - arr_size.height) * 0.5
            ns_arr_str.drawAtPoint_withAttributes_(AppKit.NSMakePoint(arr_tx, arr_ty), arr_attrs)

        # 3. Snooze / Acknowledge Buttons
        is_stage_zero = (reminder_stage == 0)

        def _draw_snooze_btn(btn_key, rect, text_str):
            if rect.size.width == 0: return
            is_pressed = (pressed_button == btn_key)
            is_hovered = (hovered_button == btn_key)
            path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, 9.0, 9.0)

            if is_stage_zero:
                if is_pressed:
                    fill = Theme.SURFACE1
                elif is_hovered:
                    fill = Theme.SURFACE0
                else:
                    fill = Theme.MANTLE
                border = Theme.SAPPHIRE.colorWithAlphaComponent_(0.50)
                txt_col = Theme.SAPPHIRE
            else:
                if is_pressed:
                    fill = Theme.SURFACE1
                elif is_hovered:
                    fill = Theme.SURFACE0
                else:
                    fill = Theme.MANTLE
                border = Theme.SURFACE1
                txt_col = Theme.TEXT if is_hovered else self.color_sub

            fill.set()
            path.fill()
            border.set()
            path.setLineWidth_(1.0)
            path.stroke()

            s_attrs = {
                AppKit.NSFontAttributeName: self.font_btn_sec,
                AppKit.NSForegroundColorAttributeName: txt_col
            }
            ns_str = AppKit.NSString.stringWithString_(text_str)
            s_size = ns_str.sizeWithAttributes_(s_attrs)
            tx = rect.origin.x + (rect.size.width - s_size.width) * 0.5
            ty = rect.origin.y + (rect.size.height - s_size.height) * 0.5
            ns_str.drawAtPoint_withAttributes_(AppKit.NSMakePoint(tx, ty), s_attrs)

        if is_stage_zero:
            _draw_snooze_btn("snooze1", button_rects["snooze1"], t("banner_got_it"))
        else:
            _draw_snooze_btn("snooze1", button_rects["snooze1"], "💤 5m")
            _draw_snooze_btn("snooze2", button_rects["snooze2"], "⏭️ Skip")

    def draw_pilot_speech_bubble(self, px: float, py: float, card_right_x: float, speech_text: str, is_late: bool, tick: int):
        if not speech_text:
            return

        bubble_attrs = {
            AppKit.NSFontAttributeName: self.font_bubble,
            AppKit.NSForegroundColorAttributeName: Theme.CRUST if is_late else Theme.TEXT
        }
        ns_str = AppKit.NSString.stringWithString_(speech_text)
        text_size = ns_str.sizeWithAttributes_(bubble_attrs)

        bw = text_size.width + 24.0
        bh = 26.0

        # Ensure the speech bubble never overlaps the close button or left card area
        min_bx = card_right_x + 10.0
        ideal_bx = px - bw * 0.5
        bx = max(min_bx, ideal_bx)
        by = py + 62.0 + math.sin(tick * 0.08) * 3.0

        # Anchor tail securely between bubble base and pilot tip
        tail_tip_x = px
        tail_base_x = max(bx + 14.0, min(bx + bw - 14.0, tail_tip_x))

        # Bubble Container Shape with Tail
        bubble_rect = AppKit.NSMakeRect(bx, by, bw, bh)
        bubble_path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bubble_rect, 10.0, 10.0)

        # Tail pointing to pilot
        tail_path = AppKit.NSBezierPath.bezierPath()
        tail_path.moveToPoint_(AppKit.NSMakePoint(tail_base_x - 6.0, by))
        tail_path.lineToPoint_(AppKit.NSMakePoint(tail_tip_x, by - 7.0))
        tail_path.lineToPoint_(AppKit.NSMakePoint(tail_base_x + 6.0, by))
        tail_path.closePath()

        if is_late:
            bg_col = Theme.RED
            border_col = Theme.MAROON
        else:
            bg_col = Theme.MANTLE
            border_col = Theme.SURFACE1

        bg_col.set()
        bubble_path.fill()
        tail_path.fill()

        border_col.set()
        bubble_path.setLineWidth_(1.0)
        bubble_path.stroke()

        text_pt = AppKit.NSMakePoint(bx + (bw - text_size.width) * 0.5, by + (bh - text_size.height) * 0.5)
        ns_str.drawAtPoint_withAttributes_(text_pt, bubble_attrs)
