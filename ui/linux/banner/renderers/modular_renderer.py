"""
Modular Vector Pilot Renderer for FlightDeck (Linux PyQt6 QPainter).
Dynamically composites any base animal (Duck 🦆, Owl 🦉, Bunny 🐰)
with any costume/headwear (Student 🎓, Chef 👨‍🍳, Captain 🧑‍✈️, Agent 🕵️, Gym 🏋️, Racer 🏎️, Zen 🌸, Aviator 🪖).
"""
from __future__ import annotations
import math

try:
    from PyQt6.QtCore import Qt, QRectF, QPointF
    from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
except (ImportError, ModuleNotFoundError):
    Qt = object
    QRectF = object
    QPointF = object
    QPainter = object
    QColor = object
    QPen = object
    QBrush = object
    QPainterPath = object

from .base_renderer import BaseQtPilotRenderer
from ui.common.mascot_catalog import normalize_accessories

class QtModularRenderer(BaseQtPilotRenderer):
    def __init__(self, animal: str = "duck", outfit: str = "aviator", accessories=None):
        self.animal = animal.lower()
        self.outfit = outfit.lower()
        self.accessories = normalize_accessories(outfit, accessories, self.animal)

    def draw_pilot(self, p: QPainter, px: float, py: float, tick: int) -> None:
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 1. Base Aircraft / Vehicle Fuselage
        self._draw_fuselage(p, px, py, tick)

        # 2. Base Animal (Duck, Owl, Bunny, Platypus, Squirrel)
        if self.animal == "bunny":
            self._draw_bunny(p, px, py, tick)
        elif self.animal == "owl":
            self._draw_owl(p, px, py, tick)
        elif self.animal == "platypus":
            self._draw_platypus(p, px, py, tick)
        elif self.animal == "squirrel":
            self._draw_squirrel(p, px, py, tick)
        elif self.animal == "fox":
            self._draw_fox(p, px, py, tick)
        elif self.animal == "penguin":
            self._draw_penguin(p, px, py, tick)
        elif self.animal == "panda":
            self._draw_panda(p, px, py, tick)
        else:
            self._draw_duck(p, px, py, tick)

        # 3. Costume / Headwear Overlay
        self._draw_outfit(p, px, py, tick)
        self._draw_accessories(p, px, py, tick)

        # 4. Propeller
        self.draw_propeller(p, px + 34, py + 1, tick)

        p.restore()

    def _draw_fuselage(self, p: QPainter, px: float, py: float, tick: int) -> None:
        p.setPen(QPen(QColor(51, 38, 25, 204), 1.4))
        if self.outfit in ("agent", "tuxedo", "racer"):
            p.setBrush(QColor(46, 56, 71))
        elif self.outfit == "concert":
            p.setBrush(QColor(76, 46, 107))
        elif self.outfit == "captain":
            p.setBrush(QColor(31, 51, 97))
        elif self.outfit == "student":
            p.setBrush(QColor(76, 56, 102))
        elif self.outfit == "banker":
            p.setBrush(QColor(31, 89, 61))
        else:
            p.setBrush(QColor(250, 240, 209))
        p.drawEllipse(QRectF(px - 44, py - 13, 76, 28))

        # Stripe
        stripe_path = QPainterPath()
        stripe_path.moveTo(px - 38, py - 2)
        stripe_path.lineTo(px + 24, py - 2)
        stripe_path.lineTo(px + 22, py - 6)
        stripe_path.lineTo(px - 36, py - 6)
        stripe_path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        if self.outfit == "student":
            p.setBrush(QColor(204, 166, 250))
        elif self.outfit in ("agent", "tuxedo"):
            p.setBrush(QColor(38, 217, 209))
        elif self.outfit == "concert":
            p.setBrush(QColor(245, 194, 231))
        elif self.outfit == "captain":
            p.setBrush(QColor(242, 199, 89))
        elif self.outfit == "banker":
            p.setBrush(QColor(245, 209, 71))
        else:
            p.setBrush(QColor(224, 51, 46))
        p.drawPath(stripe_path)

        # Cockpit
        p.setBrush(QColor(38, 46, 64))
        p.drawEllipse(QRectF(px - 14, py, 26, 16))

        # Wing & Strobe
        wing_path = QPainterPath()
        wing_path.moveTo(px - 16, py - 4)
        wing_path.lineTo(px + 14, py - 4)
        wing_path.lineTo(px + 2, py - 26)
        wing_path.lineTo(px - 14, py - 26)
        wing_path.closeSubpath()
        p.setBrush(QColor(245, 158, 38, 217))
        p.drawPath(wing_path)

        # Wingtip navigation strobe beacon
        self.draw_wingtip_strobe(p, px + 2.0, py - 26.0, tick)

    def _get_animal_bob(self, tick: int) -> float:
        if self.animal in ("duck", "bunny", "platypus", "squirrel", "fox"):
            return math.sin(tick * 0.14) * 1.2
        elif self.animal in ("owl", "penguin"):
            return math.sin(tick * 0.12) * 1.0
        elif self.animal == "panda":
            return math.sin(tick * 0.10) * 0.9
        return math.sin(tick * 0.14) * 1.2

    def _draw_duck(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 209, 71))
        p.drawEllipse(QRectF(px - 10, py + 2 + hb_y, 22, 20))

        # Guanciotta aranciata / blush caldo
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 166, 51, 89))
        p.drawEllipse(QRectF(px + 1, py + 4 + hb_y, 8, 6))

        # Beak 3D sculpted with breathing bob and smile crease
        beak_bob = math.sin(tick * 0.12) * 0.7

        # Lower beak shadow
        lower_beak = QPainterPath()
        lower_beak.moveTo(px + 4, py + 5.5 + hb_y)
        lower_beak.cubicTo(
            px + 9, py + 2.5 + hb_y,
            px + 14, py + 3.8 + hb_y + beak_bob,
            px + 17, py + 6.5 + hb_y + beak_bob,
        )
        lower_beak.lineTo(px + 4, py + 6.5 + hb_y)
        lower_beak.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(217, 89, 5))
        p.drawPath(lower_beak)

        # Main beak body
        beak_path = QPainterPath()
        beak_path.moveTo(px + 4, py + 10.5 + hb_y)
        beak_path.cubicTo(
            px + 9, py + 11.2 + hb_y,
            px + 15, py + 10.2 + hb_y + beak_bob,
            px + 18.5, py + 7.5 + hb_y + beak_bob,
        )
        beak_path.cubicTo(
            px + 17.5, py + 5.5 + hb_y + beak_bob,
            px + 19.5, py + 6.8 + hb_y + beak_bob,
            px + 19.0, py + 5.8 + hb_y + beak_bob,
        )
        beak_path.cubicTo(
            px + 13, py + 5.0 + hb_y + beak_bob,
            px + 8, py + 4.5 + hb_y,
            px + 4, py + 5.0 + hb_y,
        )
        beak_path.closeSubpath()
        p.setBrush(QColor(255, 128, 8))
        p.drawPath(beak_path)

        # Smile crease line
        crease = QPainterPath()
        crease.moveTo(px + 4.5, py + 6.8 + hb_y)
        crease.cubicTo(
            px + 9, py + 6.5 + hb_y,
            px + 13, py + 7.0 + hb_y + beak_bob,
            px + 16.5, py + 6.8 + hb_y + beak_bob,
        )
        p.setPen(QPen(QColor(199, 71, 0, 230), 0.85, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(crease)

        # Highlight curve
        highlight = QPainterPath()
        highlight.moveTo(px + 6, py + 9.8 + hb_y)
        highlight.cubicTo(
            px + 9, py + 10.3 + hb_y,
            px + 12, py + 9.5 + hb_y + beak_bob,
            px + 14.5, py + 8.4 + hb_y + beak_bob,
        )
        p.setPen(QPen(QColor(255, 199, 77, 217), 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(highlight)

        # Duck nostril
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(166, 56, 0, 242))
        p.drawEllipse(QRectF(px + 7.0, py + 8.8 + hb_y, 1.6, 1.2))

        # Eye with natural blinking
        if self.is_eye_blinking(tick):
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 1.5, py + 13.5 + hb_y)
            eye_arc.quadTo(px + 4.2, py + 16.0 + hb_y, px + 7.0, py + 13.5 + hb_y)
            p.setPen(QPen(QColor(0, 0, 0), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(0, 0, 0))
            p.drawEllipse(QRectF(px + 2, py + 11 + hb_y, 4.5, 4.5))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 3.5, py + 12.5 + hb_y, 1.5, 1.5))

    def _draw_owl(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tuft_wave = math.sin(tick * 0.22) * 2.8
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(148, 117, 97))
        p.drawEllipse(QRectF(px - 11, py + 1 + hb_y, 23, 21))

        # Ear tufts fluttering in slipstream
        tuft_path = QPainterPath()
        tuft_path.moveTo(px - 9, py + 17 + hb_y)
        tuft_path.lineTo(px - 13, py + 25 + hb_y + tuft_wave)
        tuft_path.lineTo(px - 4, py + 20 + hb_y)
        tuft_path.closeSubpath()
        p.drawPath(tuft_path)

        # Face mask
        p.setBrush(QColor(235, 224, 204))
        p.drawEllipse(QRectF(px - 2, py + 4 + hb_y, 14, 14))

        # Beak
        beak_path = QPainterPath()
        beak_path.moveTo(px + 7, py + 10 + hb_y)
        beak_path.lineTo(px + 14, py + 7 + hb_y)
        beak_path.lineTo(px + 7, py + 5 + hb_y)
        beak_path.closeSubpath()
        p.setBrush(QColor(242, 166, 38))
        p.drawPath(beak_path)

        # Eye with natural blinking
        if self.is_eye_blinking(tick):
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 1.0, py + 12.5 + hb_y)
            eye_arc.quadTo(px + 5.0, py + 16.0 + hb_y, px + 9.0, py + 12.5 + hb_y)
            p.setPen(QPen(QColor(40, 30, 20), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(255, 204, 38))
            p.drawEllipse(QRectF(px + 2, py + 10 + hb_y, 6.0, 6.0))
            p.setBrush(QColor(0, 0, 0))
            p.drawEllipse(QRectF(px + 4, py + 11.5 + hb_y, 3.0, 3.0))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 5, py + 13 + hb_y, 1.2, 1.2))

    def _draw_bunny(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        ear_base_wave = math.sin(tick * 0.18) * 2.5
        ear_tip_wave = math.sin(tick * 0.22 + 0.8) * 4.2
        p.setPen(Qt.PenStyle.NoPen)

        # 🐰 1. Back Ear (Depth)
        ear_r = QPainterPath()
        ear_r.moveTo(px - 3, py + 17 + hb_y)
        ear_r.cubicTo(px - 8, py + 26 + ear_base_wave * 0.8 + hb_y, px - 17, py + 32 + ear_tip_wave * 0.9 + hb_y, px - 10, py + 36 + ear_tip_wave * 0.9 + hb_y)
        ear_r.cubicTo(px - 4, py + 33 + ear_tip_wave * 0.9 + hb_y, px + 1, py + 25 + hb_y, px + 2, py + 18 + hb_y)
        ear_r.closeSubpath()
        p.setBrush(QColor(230, 224, 220))
        p.drawPath(ear_r)

        # Back ear inner shadow
        p.setBrush(QColor(242, 166, 184, 153))
        ear_r_in = QPainterPath()
        ear_r_in.moveTo(px - 2, py + 19 + hb_y)
        ear_r_in.lineTo(px - 8, py + 32 + ear_tip_wave * 0.9 + hb_y)
        ear_r_in.lineTo(px, py + 21 + hb_y)
        ear_r_in.closeSubpath()
        p.drawPath(ear_r_in)

        # 🐰 2. Front Floppy Ear
        ear_path = QPainterPath()
        ear_path.moveTo(px - 9, py + 16 + hb_y)
        ear_path.cubicTo(px - 17, py + 24 + ear_base_wave + hb_y, px - 25, py + 30 + ear_tip_wave + hb_y, px - 18, py + 35 + ear_tip_wave + hb_y)
        ear_path.cubicTo(px - 10, py + 32 + ear_tip_wave + hb_y, px - 5, py + 24 + hb_y, px - 4, py + 18 + hb_y)
        ear_path.closeSubpath()
        p.setBrush(QColor(250, 245, 240))
        p.drawPath(ear_path)

        # Pink inner ear
        p.setBrush(QColor(255, 184, 199, 217))
        inner_path = QPainterPath()
        inner_path.moveTo(px - 8, py + 18 + hb_y)
        inner_path.lineTo(px - 16, py + 31 + ear_tip_wave + hb_y)
        inner_path.lineTo(px - 6, py + 20 + hb_y)
        inner_path.closeSubpath()
        p.drawPath(inner_path)

        # 🐰 3. Head
        p.setBrush(QColor(250, 245, 240))
        p.drawEllipse(QRectF(px - 9, py + 2 + hb_y, 21, 19))

        # 🐰 4. Soft Cheek Blush
        p.setBrush(QColor(255, 210, 220, 166))
        p.drawEllipse(QRectF(px - 1, py + 4 + hb_y, 9, 7))

        # 🐰 5. Puffy Muzzle Pad (Eliminates beak appearance)
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(px + 6, py + 3.5 + hb_y, 7.5, 6.5))

        # 🐰 6. Cute Bunny Buck Tooth
        p.setBrush(QColor(242, 242, 250))
        p.setPen(QPen(QColor(178, 166, 178, 153), 0.6))
        p.drawRoundedRect(QRectF(px + 8.5, py + 2.0 + hb_y, 3.2, 3.2), 1.0, 1.0)
        p.setPen(Qt.PenStyle.NoPen)

        # 🐰 7. Eye with sweet reflections and natural blinking
        if self.is_eye_blinking(tick):
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 1.0, py + 12.5 + hb_y)
            eye_arc.quadTo(px + 4.5, py + 15.5 + hb_y, px + 8.0, py + 12.5 + hb_y)
            p.setPen(QPen(QColor(56, 38, 71), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(56, 38, 71))
            p.drawEllipse(QRectF(px + 1.5, py + 9.5 + hb_y, 5.5, 6.5))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 3.0, py + 12.5 + hb_y, 2.2, 2.2))
            p.drawEllipse(QRectF(px + 4.5, py + 10.5 + hb_y, 1.0, 1.0))

        # 🐰 8. Button nose (Cute rounded pink nose on top of muzzle)
        nose_twitch = 0.4 if (tick % 24) < 10 else 0.0
        p.setBrush(QColor(255, 122, 158))
        p.drawEllipse(QRectF(px + 10.0, py + 7.0 + hb_y + nose_twitch, 3.5, 2.8))

        # Philtrum line
        p.setPen(QPen(QColor(217, 102, 140, 204), 0.8))
        p.drawLine(QPointF(px + 10.5, py + 7.0 + hb_y + nose_twitch), QPointF(px + 10.5, py + 4.8 + hb_y))

        # 🐰 9. Cheek whisker freckles (Zero gray beak)
        p.setBrush(QColor(217, 140, 166, 178))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(px + 4.0, py + 6.5 + hb_y, 1.1, 1.1))
        p.drawEllipse(QRectF(px + 6.0, py + 5.8 + hb_y, 1.1, 1.1))
        p.drawEllipse(QRectF(px + 4.8, py + 4.8 + hb_y, 1.1, 1.1))

    def _draw_platypus(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tail_bob = math.sin(tick * 0.16) * 3.5
        p.setPen(Qt.PenStyle.NoPen)
        # Tail bobbing in slipstream
        tail_path = QPainterPath()
        tail_path.moveTo(px - 36, py - 4 + tail_bob * 0.3)
        tail_path.lineTo(px - 58, py + 4 + tail_bob)
        tail_path.lineTo(px - 62, py - 6 + tail_bob)
        tail_path.lineTo(px - 38, py - 12 + tail_bob * 0.3)
        tail_path.closeSubpath()
        p.setBrush(QColor(107, 66, 41))
        p.drawPath(tail_path)

        # Head / Body
        p.setBrush(QColor(38, 166, 158))
        p.drawEllipse(QRectF(px - 10, py + 2 + hb_y, 23, 19))

        # Flat bill
        p.setBrush(QColor(245, 133, 31))
        p.drawRoundedRect(QRectF(px + 4, py + 3 + hb_y, 19, 8), 3.0, 3.0)

        # Eye with blinking
        if self.is_eye_blinking(tick):
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 2.0, py + 13.0 + hb_y)
            eye_arc.quadTo(px + 5.0, py + 15.5 + hb_y, px + 8.0, py + 13.0 + hb_y)
            p.setPen(QPen(QColor(0, 0, 0), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(0, 0, 0))
            p.drawEllipse(QRectF(px + 3, py + 11 + hb_y, 4.5, 4.5))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 4.5, py + 12.5 + hb_y, 1.5, 1.5))

    def _draw_squirrel(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tail_wave = math.sin(tick * 0.18) * 3.8
        tail_path = QPainterPath()
        tail_path.moveTo(px - 34, py - 4)
        tail_path.cubicTo(px - 48, py + 8 + tail_wave * 0.5, px - 56, py + 22 + tail_wave, px - 44, py + 26 + tail_wave)
        tail_path.cubicTo(px - 36, py + 24 + tail_wave, px - 30, py + 12, px - 26, py + 4)
        tail_path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(199, 107, 56))
        p.drawPath(tail_path)

        # Head
        p.setBrush(QColor(209, 117, 64))
        p.drawEllipse(QRectF(px - 9, py + 2 + hb_y, 21, 19))

        # Cheeks
        p.setBrush(QColor(250, 242, 230))
        p.drawEllipse(QRectF(px + 1, py + 3 + hb_y, 10, 8))

        # Muzzle
        p.setBrush(QColor(64, 38, 31))
        p.drawEllipse(QRectF(px + 10, py + 6 + hb_y, 3.5, 3.5))

        # Eye with blinking
        if self.is_eye_blinking(tick):
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 1.0, py + 12.0 + hb_y)
            eye_arc.quadTo(px + 4.0, py + 14.5 + hb_y, px + 7.0, py + 12.0 + hb_y)
            p.setPen(QPen(QColor(0, 0, 0), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(0, 0, 0))
            p.drawEllipse(QRectF(px + 2, py + 10 + hb_y, 4.5, 5.0))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 3.5, py + 12 + hb_y, 1.8, 1.8))

    def _draw_fox(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tail_sway = math.sin(tick * 0.18) * 3.2
        p.setPen(Qt.PenStyle.NoPen)

        # 🦊 1. Fluffy S-curved Bushy Tail behind cockpit
        tail = QPainterPath()
        tail.moveTo(px - 34, py - 4)
        tail.cubicTo(
            px - 46, py + 4 + tail_sway * 0.4,
            px - 58, py + 16 + tail_sway,
            px - 48, py + 22 + tail_sway,
        )
        tail.cubicTo(
            px - 42, py + 24 + tail_sway,
            px - 32, py + 10,
            px - 28, py + 2,
        )
        tail.closeSubpath()
        p.setBrush(QColor(235, 97, 38))
        p.drawPath(tail)

        # Cream-white fluffy tail tip
        tip = QPainterPath()
        tip.moveTo(px - 44, py + 15 + tail_sway)
        tip.cubicTo(
            px - 47, py + 17 + tail_sway,
            px - 52, py + 20 + tail_sway,
            px - 48, py + 22 + tail_sway,
        )
        tip.cubicTo(
            px - 45, py + 22 + tail_sway,
            px - 42, py + 19 + tail_sway,
            px - 40, py + 17 + tail_sway,
        )
        tip.closeSubpath()
        p.setBrush(QColor(250, 242, 230))
        p.drawPath(tip)

        # 🦊 2. Back Ear
        back_ear = QPainterPath()
        back_ear.moveTo(px - 10, py + 15 + hb_y)
        back_ear.lineTo(px - 9, py + 27 + hb_y)
        back_ear.lineTo(px - 2, py + 18 + hb_y)
        back_ear.closeSubpath()
        p.setBrush(QColor(199, 71, 26))
        p.drawPath(back_ear)

        back_tip = QPainterPath()
        back_tip.moveTo(px - 10, py + 23 + hb_y)
        back_tip.lineTo(px - 9, py + 27 + hb_y)
        back_tip.lineTo(px - 5, py + 22 + hb_y)
        back_tip.closeSubpath()
        p.setBrush(QColor(51, 31, 26))
        p.drawPath(back_tip)

        # 🦊 3. Round Warm Terracotta Head
        p.setBrush(QColor(242, 115, 46))
        p.drawEllipse(QRectF(px - 10, py + 2 + hb_y, 22, 20))

        # 🦊 4. Front Ear
        front_ear = QPainterPath()
        front_ear.moveTo(px - 4, py + 17 + hb_y)
        front_ear.lineTo(px - 1, py + 29 + hb_y)
        front_ear.lineTo(px + 6, py + 17 + hb_y)
        front_ear.closeSubpath()
        p.setBrush(QColor(242, 115, 46))
        p.drawPath(front_ear)

        ear_tip = QPainterPath()
        ear_tip.moveTo(px - 3, py + 24 + hb_y)
        ear_tip.lineTo(px - 1, py + 29 + hb_y)
        ear_tip.lineTo(px + 3, py + 22 + hb_y)
        ear_tip.closeSubpath()
        p.setBrush(QColor(46, 31, 26))
        p.drawPath(ear_tip)

        inner_ear = QPainterPath()
        inner_ear.moveTo(px - 2, py + 18 + hb_y)
        inner_ear.lineTo(px - 1, py + 24 + hb_y)
        inner_ear.lineTo(px + 3, py + 18 + hb_y)
        inner_ear.closeSubpath()
        p.setBrush(QColor(255, 235, 214))
        p.drawPath(inner_ear)

        # 🦊 5. Chubby Cream Muzzle & Cheeks
        muzzle = QPainterPath()
        muzzle.moveTo(px - 1, py + 3 + hb_y)
        muzzle.cubicTo(
            px + 4, py + 2.5 + hb_y,
            px + 11, py + 4.5 + hb_y,
            px + 14, py + 6.5 + hb_y,
        )
        muzzle.cubicTo(
            px + 13, py + 9.5 + hb_y,
            px + 8, py + 11.5 + hb_y,
            px + 3, py + 11 + hb_y,
        )
        muzzle.closeSubpath()
        p.setBrush(QColor(250, 242, 230))
        p.drawPath(muzzle)

        # Soft peach blush
        p.setBrush(QColor(255, 122, 102, 102))
        p.drawEllipse(QRectF(px + 1, py + 5.5 + hb_y, 7, 5))

        # 🦊 6. Button Nose & Sweet Smile
        p.setBrush(QColor(38, 26, 26))
        p.drawEllipse(QRectF(px + 12.0, py + 6.8 + hb_y, 3.2, 2.4))
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(px + 13.0, py + 7.8 + hb_y, 1.0, 0.8))

        p.setPen(QPen(QColor(128, 51, 26, 217), 0.9))
        p.setBrush(Qt.BrushStyle.NoBrush)
        smile = QPainterPath()
        smile.moveTo(px + 8.5, py + 5.5 + hb_y)
        smile.cubicTo(
            px + 10.0, py + 4.6 + hb_y,
            px + 11.5, py + 4.8 + hb_y,
            px + 12.5, py + 6.2 + hb_y,
        )
        p.drawPath(smile)
        p.setPen(Qt.PenStyle.NoPen)

        # 🦊 7. Expressive Blinking Eyes
        if self.is_eye_blinking(tick):
            p.setPen(QPen(QColor(38, 26, 20), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 1.5, py + 13.0 + hb_y)
            eye_arc.cubicTo(
                px + 3.5, py + 15.8 + hb_y,
                px + 5.5, py + 15.8 + hb_y,
                px + 7.5, py + 13.0 + hb_y,
            )
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(38, 26, 20))
            p.drawEllipse(QRectF(px + 2.0, py + 10.5 + hb_y, 4.8, 5.2))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 3.6, py + 12.6 + hb_y, 2.0, 2.0))
            p.drawEllipse(QRectF(px + 4.8, py + 11.2 + hb_y, 0.9, 0.9))

    def _draw_penguin(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        wing_flap = math.sin(tick * 0.22) * 3.0
        p.setPen(Qt.PenStyle.NoPen)

        # 🐧 1. Flapping Little Wing
        wing = QPainterPath()
        wing.moveTo(px - 14, py + 10 + hb_y)
        wing.cubicTo(
            px - 19, py + 7 + hb_y + wing_flap * 0.5,
            px - 21, py + 3 + hb_y + wing_flap,
            px - 18, py + 1 + hb_y + wing_flap,
        )
        wing.cubicTo(
            px - 16, py - 1 + hb_y + wing_flap,
            px - 13, py + 2 + hb_y,
            px - 12, py + 5 + hb_y,
        )
        wing.closeSubpath()
        p.setBrush(QColor(36, 41, 61))
        p.drawPath(wing)

        # 🐧 2. Round Navy Head & Body
        p.setBrush(QColor(36, 41, 61))
        p.drawEllipse(QRectF(px - 11, py + 1 + hb_y, 23, 21))

        # 🐧 3. Pearly White Face & Tummy Bib
        p.setBrush(QColor(250, 247, 240))
        p.drawEllipse(QRectF(px - 4, py + 2 + hb_y, 15, 17))

        # Soft baby penguin blush
        p.setBrush(QColor(255, 115, 140, 107))
        p.drawEllipse(QRectF(px + 2, py + 5 + hb_y, 7, 5))

        # 🐧 4. Cute Gold/Orange Beak
        beak = QPainterPath()
        beak.moveTo(px + 7.5, py + 9.5 + hb_y)
        beak.cubicTo(
            px + 10.5, py + 9.8 + hb_y,
            px + 13.5, py + 8.8 + hb_y,
            px + 15.0, py + 7.0 + hb_y,
        )
        beak.cubicTo(
            px + 12.5, py + 5.8 + hb_y,
            px + 9.5, py + 5.4 + hb_y,
            px + 7.5, py + 5.5 + hb_y,
        )
        beak.closeSubpath()
        p.setBrush(QColor(250, 166, 38))
        p.drawPath(beak)

        p.setPen(QPen(QColor(255, 209, 89, 230), 0.8))
        p.drawLine(QPointF(px + 8.5, py + 8.8 + hb_y), QPointF(px + 12.5, py + 7.8 + hb_y))
        p.setPen(Qt.PenStyle.NoPen)

        # 🐧 5. Dapper Ruby Bow Tie (only when not wearing tuxedo)
        if self.outfit not in ("agent", "tuxedo") and "tuxedo" not in self.accessories:
            p.setBrush(QColor(224, 56, 71))
            bow_l = QPainterPath()
            bow_l.moveTo(px + 1, py + 3 + hb_y)
            bow_l.lineTo(px - 3, py + 5.5 + hb_y)
            bow_l.lineTo(px - 3, py + 1.5 + hb_y)
            bow_l.closeSubpath()
            p.drawPath(bow_l)
            bow_r = QPainterPath()
            bow_r.moveTo(px + 1, py + 3 + hb_y)
            bow_r.lineTo(px + 5, py + 5.5 + hb_y)
            bow_r.lineTo(px + 5, py + 1.5 + hb_y)
            bow_r.closeSubpath()
            p.drawPath(bow_r)
            p.setBrush(QColor(179, 38, 51))
            p.drawEllipse(QRectF(px - 0.5, py + 2.0 + hb_y, 3, 3))

        # 🐧 6. Sparkling Blinking Eyes
        if self.is_eye_blinking(tick):
            p.setPen(QPen(QColor(31, 36, 51), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 1.0, py + 12.0 + hb_y)
            eye_arc.cubicTo(
                px + 3.0, py + 14.8 + hb_y,
                px + 5.0, py + 14.8 + hb_y,
                px + 7.0, py + 12.0 + hb_y,
            )
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(26, 31, 46))
            p.drawEllipse(QRectF(px + 1.5, py + 9.5 + hb_y, 4.8, 5.2))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 3.0, py + 11.8 + hb_y, 2.0, 2.0))
            p.drawEllipse(QRectF(px + 4.2, py + 10.4 + hb_y, 0.9, 0.9))

    def _draw_panda(self, p: QPainter, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        ear_twitch = math.sin(tick * 0.15) * 0.6
        p.setPen(Qt.PenStyle.NoPen)

        # 🐼 1. Furry Round Ears with 3D Depth
        p.setBrush(QColor(38, 38, 46))
        p.drawEllipse(QRectF(px - 11, py + 16 + hb_y + ear_twitch, 8, 8))
        p.setBrush(QColor(31, 31, 38))
        p.drawEllipse(QRectF(px + 4, py + 16 + hb_y + ear_twitch, 8, 8))
        p.setBrush(QColor(64, 64, 76, 153))
        p.drawEllipse(QRectF(px + 5.5, py + 17.5 + hb_y + ear_twitch, 5, 5))

        # 🐼 2. Plump Cream-White Head
        p.setBrush(QColor(250, 250, 245))
        p.drawEllipse(QRectF(px - 10, py + 2 + hb_y, 22, 20))

        # 🐼 3. Soft Rosy Blush
        p.setBrush(QColor(255, 115, 148, 102))
        p.drawEllipse(QRectF(px + 1, py + 4.5 + hb_y, 7.5, 5))

        # 🐼 4. Characteristic Tilted Teardrop Eye Patch
        p.save()
        p.translate(px + 4.5, py + 12.0 + hb_y)
        p.rotate(-18.0)
        p.setBrush(QColor(31, 31, 41))
        p.drawEllipse(QRectF(-3.5, -4.5, 7.0, 9.0))
        p.restore()

        # 🐼 5. Sparkling Eyes inside Eye Patch with Blinking
        if self.is_eye_blinking(tick):
            p.setPen(QPen(QColor(255, 255, 255), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            eye_arc = QPainterPath()
            eye_arc.moveTo(px + 2.0, py + 13.0 + hb_y)
            eye_arc.cubicTo(
                px + 4.0, py + 15.5 + hb_y,
                px + 5.5, py + 15.5 + hb_y,
                px + 7.5, py + 13.0 + hb_y,
            )
            p.drawPath(eye_arc)
            p.setPen(Qt.PenStyle.NoPen)
        else:
            p.setBrush(QColor(13, 13, 20))
            p.drawEllipse(QRectF(px + 2.5, py + 10.5 + hb_y, 4.5, 4.8))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px + 3.8, py + 12.5 + hb_y, 2.2, 2.2))
            p.drawEllipse(QRectF(px + 5.0, py + 11.2 + hb_y, 1.0, 1.0))

        # 🐼 6. Button Nose & Sweet Smile
        p.setBrush(QColor(255, 255, 255, 204))
        p.drawEllipse(QRectF(px + 6.0, py + 4.0 + hb_y, 7.5, 6.0))

        p.setBrush(QColor(31, 31, 38))
        p.drawEllipse(QRectF(px + 9.5, py + 6.5 + hb_y, 3.2, 2.2))
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(px + 10.5, py + 7.4 + hb_y, 0.9, 0.7))

        p.setPen(QPen(QColor(64, 51, 51, 217), 0.85))
        p.setBrush(Qt.BrushStyle.NoBrush)
        mouth = QPainterPath()
        mouth.moveTo(px + 8.5, py + 5.2 + hb_y)
        mouth.cubicTo(
            px + 9.2, py + 4.2 + hb_y,
            px + 10.5, py + 4.2 + hb_y,
            px + 11.0, py + 5.0 + hb_y,
        )
        p.drawPath(mouth)
        p.setPen(Qt.PenStyle.NoPen)

        # 🐼 7. Fresh Green Bamboo Shoot with Leaf
        bamboo_sway = math.sin(tick * 0.12) * 1.5
        p.setPen(QPen(QColor(76, 184, 82), 2.2))
        p.drawLine(QPointF(px - 1, py + 5 + hb_y), QPointF(px + 14, py + 1 + bamboo_sway))

        p.setPen(QPen(QColor(51, 140, 56), 1.2))
        p.drawLine(QPointF(px + 6, py + 5 + hb_y * 0.5), QPointF(px + 7, py + 2.5 + hb_y * 0.5))
        p.setPen(Qt.PenStyle.NoPen)

        p.setBrush(QColor(97, 209, 97))
        leaf = QPainterPath()
        leaf.moveTo(px + 14, py + 1 + bamboo_sway)
        leaf.cubicTo(
            px + 16, py + 5 + bamboo_sway,
            px + 18, py + 5 + bamboo_sway,
            px + 20, py + 4 + bamboo_sway,
        )
        leaf.cubicTo(
            px + 18, py + 2 + bamboo_sway,
            px + 16, py + 1 + bamboo_sway,
            px + 14, py + 1 + bamboo_sway,
        )
        leaf.closeSubpath()
        p.drawPath(leaf)

    def _draw_outfit(self, p: QPainter, px: float, py: float, tick: int) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        if self.outfit == "student":
            # 🎓 Mortarboard
            p.setBrush(QColor(38, 41, 56))
            cap_path = QPainterPath()
            cap_path.moveTo(px - 14, py + 19)
            cap_path.lineTo(px + 3, py + 26)
            cap_path.lineTo(px + 18, py + 19)
            cap_path.lineTo(px + 1, py + 14)
            cap_path.closeSubpath()
            p.drawPath(cap_path)

            # Tassel
            tassel_sway = math.sin(tick * 0.20) * 3.0
            p.setPen(QPen(QColor(250, 217, 89), 1.4))
            p.drawLine(QPointF(px + 2, py + 22), QPointF(px - 12 + tassel_sway, py + 10))

            # Spectacles
            p.setPen(QPen(QColor(242, 204, 51), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(px + 1, py + 8, 7.5, 7.5))

        elif self.outfit == "chef":
            # 👨‍🍳 Toque
            p.setPen(QPen(QColor(204, 209, 224), 1.0))
            p.setBrush(QColor(255, 255, 255))
            toque_path = QPainterPath()
            toque_path.moveTo(px - 8, py + 16)
            toque_path.lineTo(px - 10, py + 27)
            toque_path.cubicTo(px - 4, py + 34, px + 6, py + 34, px + 10, py + 28)
            toque_path.lineTo(px + 8, py + 16)
            toque_path.closeSubpath()
            p.drawPath(toque_path)

        elif self.outfit == "captain":
            # 🧑‍✈️ Captain Hat
            p.setBrush(QColor(31, 41, 71))
            p.drawEllipse(QRectF(px - 8, py + 16, 20, 8))
            p.setBrush(QColor(0, 0, 0))
            p.drawEllipse(QRectF(px + 2, py + 14, 12, 4))
            p.setBrush(QColor(245, 204, 64))
            p.drawEllipse(QRectF(px + 2, py + 19, 4, 4))

        elif self.outfit in ("agent", "tuxedo"):
            self._draw_tuxedo(p, px, py, tick)
            if self.animal == "platypus":
                self._draw_fedora(p, px, py, tick)
            else:
                self._draw_top_hat(p, px, py, tick)

        elif self.outfit == "concert":
            self._draw_headphones(p, px, py, tick)

        elif self.outfit == "gym":
            p.setBrush(QColor(235, 64, 64))
            p.drawRoundedRect(QRectF(px - 8, py + 14, 18, 5), 2.0, 2.0)
            p.setBrush(QColor(255, 255, 255))
            p.drawRect(QRectF(px - 7, py + 15.5, 16, 1.5))

        elif self.outfit == "racer":
            p.setBrush(QColor(250, 115, 38))
            p.drawEllipse(QRectF(px - 8, py + 12, 19, 14))
            p.setBrush(QColor(38, 46, 64, 217))
            p.drawEllipse(QRectF(px + 2, py + 13, 10, 8))

        elif self.outfit == "zen":
            p.setBrush(QColor(255, 140, 191))
            p.drawEllipse(QRectF(px - 6, py + 16, 8, 8))
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(px - 4, py + 18, 4, 4))
            p.setBrush(QColor(255, 217, 51))
            p.drawEllipse(QRectF(px - 3, py + 19, 2, 2))

        elif self.outfit == "banker":
            self._draw_banker_visor(p, px, py, tick)
            self._draw_gold_coin(p, px, py, tick)

        else:
            p.setBrush(QColor(89, 64, 46))
            p.drawRect(QRectF(px - 8, py + 13, 18, 3))
            p.setPen(QPen(QColor(230, 191, 89), 1.6))
            p.setBrush(QColor(140, 224, 250, 191))
            p.drawEllipse(QRectF(px, py + 9, 10, 10))

    def _draw_fedora(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Iconic brown fedora with black ribbon band - strictly for Perry the Platypus."""
        hb_y = self._get_animal_bob(tick)
        p.setPen(QPen(QColor(64, 33, 17), 1.0))
        p.setBrush(QColor(140, 82, 43))
        p.drawEllipse(QRectF(px - 14, py + 16 + hb_y, 28, 6))
        crown_path = QPainterPath()
        crown_path.moveTo(px - 7, py + 18 + hb_y)
        crown_path.lineTo(px - 6, py + 28 + hb_y)
        crown_path.lineTo(px - 1, py + 30 + hb_y)
        crown_path.lineTo(px + 5, py + 28 + hb_y)
        crown_path.lineTo(px + 7, py + 18 + hb_y)
        crown_path.closeSubpath()
        p.setBrush(QColor(153, 92, 49))
        p.drawPath(crown_path)
        p.setBrush(QColor(38, 38, 46))
        p.drawRect(QRectF(px - 6.5, py + 18 + hb_y, 13, 3))
        p.setPen(QPen(QColor(194, 128, 71, 204), 0.8))
        p.drawLine(QPointF(px - 1, py + 28.5 + hb_y), QPointF(px + 1, py + 28.5 + hb_y))

    def _draw_top_hat(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Dapper black formal silk top hat with satin ribbon band for work animals."""
        hb_y = self._get_animal_bob(tick)
        p.setPen(Qt.PenStyle.NoPen)
        # Flared brim
        p.setBrush(QColor(20, 20, 30))
        p.drawEllipse(QRectF(px - 13, py + 16 + hb_y, 26, 5))

        # Tall silk crown
        crown_path = QPainterPath()
        crown_path.moveTo(px - 7, py + 18 + hb_y)
        crown_path.lineTo(px - 8, py + 33 + hb_y)
        crown_path.lineTo(px + 8, py + 33 + hb_y)
        crown_path.lineTo(px + 7, py + 18 + hb_y)
        crown_path.closeSubpath()
        p.setBrush(QColor(28, 28, 40))
        p.drawPath(crown_path)

        # Crown top oval
        p.setBrush(QColor(36, 36, 50))
        p.drawEllipse(QRectF(px - 8, py + 31.5 + hb_y, 16, 3))

        # Satin ribbon band
        p.setBrush(QColor(217, 56, 76))
        p.drawRect(QRectF(px - 7, py + 18 + hb_y, 14, 3.2))

        # Gold buckle
        p.setBrush(QColor(245, 204, 64))
        p.drawRect(QRectF(px + 3, py + 18.5 + hb_y, 2.2, 2.2))

    def _draw_tuxedo(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Tailored black tuxedo jacket with satin lapels, white pleated shirt, black studs, and pocket square."""
        hb_y = self._get_animal_bob(tick)
        p.setPen(Qt.PenStyle.NoPen)

        # 1. Tailored onyx jacket base hugging animal's round torso
        p.setBrush(QColor(20, 20, 30))
        jacket = QPainterPath()
        jacket.moveTo(px - 4.5, py + 5.5 + hb_y)
        jacket.cubicTo(px - 7.8, py + 5.2 + hb_y, px - 11.0, py + 3.2 + hb_y, px - 10.5, py + 1.2 + hb_y)
        jacket.cubicTo(px - 6.0, py - 0.5 + hb_y, px + 2.5, py - 0.5 + hb_y, px + 6.5, py + 1.2 + hb_y)
        jacket.cubicTo(px + 7.2, py + 2.6 + hb_y, px + 5.8, py + 4.2 + hb_y, px + 3.8, py + 4.8 + hb_y)
        jacket.cubicTo(px + 1.0, py + 5.6 + hb_y, px - 2.0, py + 5.6 + hb_y, px - 4.5, py + 5.5 + hb_y)
        jacket.closeSubpath()
        p.drawPath(jacket)

        # 2. Crisp white pleated shirt bib (curved V-neck)
        p.setBrush(QColor(250, 250, 255))
        shirt = QPainterPath()
        shirt.moveTo(px - 2.4, py + 5.0 + hb_y)
        shirt.lineTo(px + 2.4, py + 5.0 + hb_y)
        shirt.cubicTo(px + 1.8, py + 2.8 + hb_y, px + 0.8, py + 1.6 + hb_y, px + 0.1, py + 0.8 + hb_y)
        shirt.cubicTo(px - 0.6, py + 1.6 + hb_y, px - 1.8, py + 2.8 + hb_y, px - 2.4, py + 5.0 + hb_y)
        shirt.closeSubpath()
        p.drawPath(shirt)

        # Black studs
        p.setBrush(QColor(26, 26, 38))
        p.drawEllipse(QRectF(px - 0.4, py + 2.6 + hb_y, 1.1, 1.1))
        p.drawEllipse(QRectF(px - 0.4, py + 1.4 + hb_y, 1.1, 1.1))

        # 3. Satin peak lapels
        p.setBrush(QColor(46, 48, 66))
        l_lapel = QPainterPath()
        l_lapel.moveTo(px - 3.8, py + 5.0 + hb_y)
        l_lapel.cubicTo(px - 4.8, py + 4.6 + hb_y, px - 5.6, py + 4.0 + hb_y, px - 5.5, py + 3.4 + hb_y)
        l_lapel.lineTo(px - 0.2, py + 0.9 + hb_y)
        l_lapel.cubicTo(px - 0.8, py + 2.2 + hb_y, px - 1.6, py + 3.6 + hb_y, px - 2.0, py + 5.0 + hb_y)
        l_lapel.closeSubpath()
        p.drawPath(l_lapel)

        r_lapel = QPainterPath()
        r_lapel.moveTo(px + 3.6, py + 5.0 + hb_y)
        r_lapel.cubicTo(px + 4.4, py + 4.4 + hb_y, px + 5.0, py + 3.8 + hb_y, px + 4.8, py + 3.2 + hb_y)
        r_lapel.lineTo(px + 0.2, py + 0.9 + hb_y)
        r_lapel.cubicTo(px + 0.8, py + 2.2 + hb_y, px + 1.6, py + 3.6 + hb_y, px + 2.0, py + 5.0 + hb_y)
        r_lapel.closeSubpath()
        p.drawPath(r_lapel)

        # 4. Pocket square (two white folded silk peaks)
        p.setBrush(QColor(250, 250, 255))
        psquare = QPainterPath()
        psquare.moveTo(px - 7.5, py + 2.0 + hb_y)
        psquare.lineTo(px - 6.2, py + 3.8 + hb_y)
        psquare.lineTo(px - 5.5, py + 2.8 + hb_y)
        psquare.lineTo(px - 4.8, py + 3.6 + hb_y)
        psquare.lineTo(px - 4.2, py + 2.0 + hb_y)
        psquare.closeSubpath()
        p.drawPath(psquare)

        # 5. Dapper ruby butterfly bow tie
        p.setBrush(QColor(224, 51, 66))
        bow_l = QPainterPath()
        bow_l.moveTo(px + 0.1, py + 4.9 + hb_y)
        bow_l.cubicTo(px - 1.2, py + 5.7 + hb_y, px - 2.8, py + 6.3 + hb_y, px - 3.6, py + 6.1 + hb_y)
        bow_l.cubicTo(px - 4.0, py + 5.1 + hb_y, px - 4.0, py + 4.5 + hb_y, px - 3.6, py + 3.7 + hb_y)
        bow_l.cubicTo(px - 2.8, py + 3.5 + hb_y, px - 1.2, py + 4.3 + hb_y, px + 0.1, py + 4.9 + hb_y)
        bow_l.closeSubpath()
        p.drawPath(bow_l)

        bow_r = QPainterPath()
        bow_r.moveTo(px + 0.1, py + 4.9 + hb_y)
        bow_r.cubicTo(px + 1.4, py + 5.7 + hb_y, px + 2.8, py + 6.3 + hb_y, px + 3.6, py + 6.1 + hb_y)
        bow_r.cubicTo(px + 4.0, py + 5.1 + hb_y, px + 4.0, py + 4.5 + hb_y, px + 3.6, py + 3.7 + hb_y)
        bow_r.cubicTo(px + 2.8, py + 3.5 + hb_y, px + 1.4, py + 4.3 + hb_y, px + 0.1, py + 4.9 + hb_y)
        bow_r.closeSubpath()
        p.drawPath(bow_r)

        p.setBrush(QColor(178, 36, 51))
        p.drawEllipse(QRectF(px - 1.0, py + 3.9 + hb_y, 2.2, 2.0))

    def _draw_headphones(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Cushioned over-ear DJ concert headphones with glowing accents and animated floating music notes."""
        hb_y = self._get_animal_bob(tick)
        p.setPen(Qt.PenStyle.NoPen)

        # 1. Padded arched headband over top of crown
        band_path = QPainterPath()
        band_path.moveTo(px - 4.5, py + 18.0 + hb_y)
        band_path.cubicTo(px - 4.0, py + 26.5 + hb_y, px + 2.5, py + 27.5 + hb_y, px + 4.0, py + 21.0 + hb_y)
        p.setPen(QPen(QColor(31, 33, 46), 3.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(band_path)

        # Headband top soft cushion (Catppuccin Mauve)
        cushion_path = QPainterPath()
        cushion_path.moveTo(px - 2.5, py + 23.8 + hb_y)
        cushion_path.cubicTo(px - 1.5, py + 26.8 + hb_y, px + 1.8, py + 27.0 + hb_y, px + 2.8, py + 24.2 + hb_y)
        p.setPen(QPen(QColor(204, 166, 250), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPath(cushion_path)

        p.setPen(Qt.PenStyle.NoPen)
        # 2. Main DJ Ear-Cup on the side of the head (behind eye, unobscured face)
        cx = px - 4.5
        cy = py + 7.5 + hb_y
        p.setBrush(QColor(31, 33, 46))
        p.drawEllipse(QRectF(cx - 4.5, cy, 9.0, 13.0))

        p.setPen(QPen(QColor(245, 194, 231), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - 3.2, cy + 1.8, 6.4, 9.4))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(204, 166, 250))
        p.drawEllipse(QRectF(cx - 1.8, cy + 3.8, 3.6, 5.4))

        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(cx - 0.9, cy + 5.2, 1.8, 2.6))

        # 3. Animated floating music notes (♪ ♫)
        note_bob1 = math.sin(tick * 0.16) * 2.0
        note_bob2 = math.sin(tick * 0.16 + 1.8) * 2.0

        # Note 1 (♪) floating top-left
        p.setBrush(QColor(250, 217, 102, 242))
        n1_x = px - 15.0
        n1_y = py + 22.0 + hb_y + note_bob1
        p.drawEllipse(QRectF(n1_x, n1_y, 3.5, 2.6))
        p.setPen(QPen(QColor(250, 217, 102, 242), 1.1))
        n1_stem = QPainterPath()
        n1_stem.moveTo(n1_x + 3.0, n1_y + 1.5)
        n1_stem.lineTo(n1_x + 3.0, n1_y + 7.5)
        n1_stem.cubicTo(n1_x + 3.2, n1_y + 8.5, n1_x + 5.5, n1_y + 7.5, n1_x + 6.0, n1_y + 5.5)
        p.drawPath(n1_stem)

        # Note 2 (♫ beamed pair) floating top-right
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(245, 194, 231, 242))
        n2_x = px + 12.0
        n2_y = py + 23.0 + hb_y + note_bob2
        p.drawEllipse(QRectF(n2_x, n2_y, 3.0, 2.2))
        p.drawEllipse(QRectF(n2_x + 5.0, n2_y + 1.5, 3.0, 2.2))
        p.setPen(QPen(QColor(245, 194, 231, 242), 1.0))
        p.drawLine(QPointF(n2_x + 2.5, n2_y + 1.0), QPointF(n2_x + 2.5, n2_y + 7.0))
        p.drawLine(QPointF(n2_x + 7.5, n2_y + 2.5), QPointF(n2_x + 7.5, n2_y + 8.5))
        p.setPen(QPen(QColor(245, 194, 231, 242), 1.8))
        p.drawLine(QPointF(n2_x + 2.0, n2_y + 7.0), QPointF(n2_x + 8.0, n2_y + 8.5))

    def _draw_accessories(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Draws optional reusable layers without changing animal geometry."""
        p.setPen(Qt.PenStyle.NoPen)
        # Dedicated full accessories
        if "headphones" in self.accessories and self.outfit != "concert":
            self._draw_headphones(p, px, py, tick)
        if "tuxedo" in self.accessories and self.outfit not in ("agent", "tuxedo"):
            self._draw_tuxedo(p, px, py, tick)
        if "top_hat" in self.accessories and self.animal != "platypus" and self.outfit not in ("agent", "tuxedo"):
            self._draw_top_hat(p, px, py, tick)
        if "fedora" in self.accessories and self.animal == "platypus" and self.outfit not in ("agent", "tuxedo"):
            self._draw_fedora(p, px, py, tick)

        if "sunglasses" in self.accessories:
            p.setBrush(QColor(20, 24, 34, 235))
            p.drawEllipse(QRectF(px + 1, py + 9, 8, 5))
            p.drawEllipse(QRectF(px + 10, py + 9, 8, 5))
        if "bow_tie" in self.accessories and self.animal != "penguin" and self.outfit not in ("agent", "tuxedo") and "tuxedo" not in self.accessories:
            p.setBrush(QColor(217, 70, 76))
            p.drawEllipse(QRectF(px - 1, py + 1, 6, 5))
            p.drawEllipse(QRectF(px + 5, py + 1, 6, 5))
        if "briefcase" in self.accessories:
            p.setBrush(QColor(140, 82, 43))
            p.drawRect(QRectF(px - 28, py - 9, 12, 8))
        if "badge" in self.accessories:
            p.setBrush(QColor(245, 204, 64))
            p.drawEllipse(QRectF(px - 2, py + 5, 4, 4))
        if "earpiece" in self.accessories:
            p.setBrush(QColor(38, 38, 46))
            p.drawEllipse(QRectF(px - 12, py + 10, 3, 3))
        if "banker_visor" in self.accessories and self.outfit != "banker":
            self._draw_banker_visor(p, px, py, tick)
        if "gold_coin" in self.accessories and self.outfit != "banker":
            self._draw_gold_coin(p, px, py, tick)

    def _draw_banker_visor(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Classic translucent emerald green banker's visor with dark trim and strap."""
        hb_y = self._get_animal_bob(tick)
        p.setPen(Qt.PenStyle.NoPen)
        # 1. Dark leather strap wrapping head
        p.setBrush(QColor(46, 36, 31))
        p.drawRoundedRect(QRectF(px - 9, py + 14 + hb_y, 20, 4.5), 1.5, 1.5)

        # 2. Golden buckle on strap
        p.setBrush(QColor(245, 209, 71))
        p.drawRect(QRectF(px - 8.5, py + 14.5 + hb_y, 2.5, 3.5))

        # 3. Translucent emerald-green visor bill/brim jutting forward
        p.setBrush(QColor(31, 199, 115, 209))
        brim_path = QPainterPath()
        brim_path.moveTo(px - 4, py + 15 + hb_y)
        brim_path.cubicTo(px + 5, py + 16 + hb_y, px + 14, py + 14 + hb_y, px + 18, py + 11.5 + hb_y)
        brim_path.lineTo(px + 16, py + 8.5 + hb_y)
        brim_path.cubicTo(px + 10, py + 9.5 + hb_y, px + 3, py + 11.5 + hb_y, px - 3, py + 12.5 + hb_y)
        brim_path.closeSubpath()
        p.drawPath(brim_path)

        # 4. Mint/gloss shine reflection along visor brim
        p.setPen(QPen(QColor(179, 250, 209, 191), 1.0))
        p.drawLine(QPointF(px, py + 14.5 + hb_y), QPointF(px + 16, py + 11 + hb_y))
        p.setPen(Qt.PenStyle.NoPen)

    def _draw_gold_coin(self, p: QPainter, px: float, py: float, tick: int) -> None:
        """Sparkling gold coin emblem with subtle twinkle."""
        hb_y = self._get_animal_bob(tick)
        cx = px - 3.5
        cy = py + 2.5 + hb_y

        # 1. Outer golden coin disk
        p.setPen(QPen(QColor(204, 153, 31), 0.8))
        p.setBrush(QColor(245, 204, 56))
        p.drawEllipse(QRectF(cx - 3.5, cy - 3.5, 7.0, 7.0))

        # 2. Embossed Currency Symbol (mini $ bar)
        p.setPen(QPen(QColor(148, 102, 20), 0.7))
        p.drawLine(QPointF(cx, cy - 2.2), QPointF(cx, cy + 2.2))

        # 3. Sparkle twinkle
        twinkle = (tick % 30) < 8
        if twinkle:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255))
            p.drawEllipse(QRectF(cx + 1.2, cy + 1.2, 1.5, 1.5))
        p.setPen(Qt.PenStyle.NoPen)
