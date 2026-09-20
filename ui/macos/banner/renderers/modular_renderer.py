"""
Modular Vector Pilot Renderer for FlightDeck (macOS Quartz 2D).
Dynamically composites any base animal (Duck 🦆, Owl 🦉, Bunny 🐰)
with any costume/headwear (Student 🎓, Chef 👨‍🍳, Captain 🧑‍✈️, Agent 🕵️, Gym 🏋️, Racer 🏎️, Zen 🌸, Aviator 🪖).
"""
import math
import AppKit
from .base_renderer import BasePilotRenderer
from ui.common.mascot_catalog import normalize_accessories

class ModularPilotRenderer(BasePilotRenderer):
    def __init__(self, animal: str = "duck", outfit: str = "aviator", accessories=None):
        self.animal = animal.lower()
        self.outfit = outfit.lower()
        self.accessories = normalize_accessories(outfit, accessories, self.animal)

    def draw_pilot(self, px: float, py: float, tick: int) -> None:
        ctx = AppKit.NSGraphicsContext.currentContext()
        ctx.saveGraphicsState()

        # 1. Base Aircraft / Vehicle Fuselage
        self._draw_fuselage(px, py, tick)

        # 2. Base Animal (Duck, Owl, Bunny, Platypus, Squirrel)
        if self.animal == "bunny":
            self._draw_bunny(px, py, tick)
        elif self.animal == "owl":
            self._draw_owl(px, py, tick)
        elif self.animal == "platypus":
            self._draw_platypus(px, py, tick)
        elif self.animal == "squirrel":
            self._draw_squirrel(px, py, tick)
        elif self.animal == "fox":
            self._draw_fox(px, py, tick)
        elif self.animal == "penguin":
            self._draw_penguin(px, py, tick)
        elif self.animal == "panda":
            self._draw_panda(px, py, tick)
        else:
            self._draw_duck(px, py, tick)

        # 3. Costume / Headwear Overlay
        self._draw_outfit(px, py, tick)
        self._draw_accessories(px, py, tick)

        # 4. Front Propeller
        self.draw_propeller(px + 34, py + 1, tick)

        ctx.restoreGraphicsState()

    def _draw_fuselage(self, px: float, py: float, tick: int) -> None:
        # Fusoliera Vintage / Spy / Racer in base all'outfit
        body_rect = AppKit.NSMakeRect(px - 44, py - 13, 76, 28)
        body = AppKit.NSBezierPath.bezierPathWithOvalInRect_(body_rect)

        if self.outfit in ("agent", "tuxedo", "racer"):
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.18, 0.22, 0.28, 1.0).set()
        elif self.outfit == "concert":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.30, 0.18, 0.42, 1.0).set()
        elif self.outfit == "captain":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.20, 0.38, 1.0).set()
        elif self.outfit == "student":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.30, 0.22, 0.40, 1.0).set()
        elif self.outfit == "banker":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.35, 0.24, 1.0).set()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.94, 0.82, 1.0).set()
        body.fill()

        # Striscia decorativa
        stripe = AppKit.NSBezierPath.bezierPath()
        stripe.moveToPoint_(AppKit.NSMakePoint(px - 38, py - 2))
        stripe.lineToPoint_(AppKit.NSMakePoint(px + 24, py - 2))
        stripe.lineToPoint_(AppKit.NSMakePoint(px + 22, py - 6))
        stripe.lineToPoint_(AppKit.NSMakePoint(px - 36, py - 6))
        stripe.closePath()

        if self.outfit == "student":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.80, 0.65, 0.98, 1.0).set()
        elif self.outfit in ("agent", "tuxedo"):
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.85, 0.82, 1.0).set()
        elif self.outfit == "concert":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.76, 0.91, 1.0).set()
        elif self.outfit == "captain":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.78, 0.35, 1.0).set()
        elif self.outfit == "banker":
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.82, 0.28, 1.0).set()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.88, 0.20, 0.18, 1.0).set()
        stripe.fill()

        # Bordo fusoliera
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.20, 0.15, 0.10, 0.80).set()
        body.setLineWidth_(1.4)
        body.stroke()

        # Cockpit
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.18, 0.25, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 14, py, 26, 16)).fill()

        # Ala
        # Ala
        wing = AppKit.NSBezierPath.bezierPath()
        wing.moveToPoint_(AppKit.NSMakePoint(px - 16, py - 4))
        wing.lineToPoint_(AppKit.NSMakePoint(px + 14, py - 4))
        wing.lineToPoint_(AppKit.NSMakePoint(px + 2, py - 26))
        wing.lineToPoint_(AppKit.NSMakePoint(px - 14, py - 26))
        wing.closePath()
        wing.fill()

        # Strobo di navigazione
        self.draw_wingtip_strobe(px + 2.0, py - 26.0, tick)

    def _get_animal_bob(self, tick: int) -> float:
        if self.animal in ("duck", "bunny", "platypus", "squirrel", "fox"):
            return math.sin(tick * 0.14) * 1.2
        elif self.animal in ("owl", "penguin"):
            return math.sin(tick * 0.12) * 1.0
        elif self.animal == "panda":
            return math.sin(tick * 0.10) * 0.9
        return math.sin(tick * 0.14) * 1.2

    def _draw_duck(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        # Testa Papero Dorato con guancia morbida
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.82, 0.28, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 10, py + 2 + hb_y, 22, 20)).fill()

        # Guanciotta aranciata / blush caldo
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.65, 0.20, 0.35).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1, py + 4 + hb_y, 8, 6)).fill()

        # Becco 3D Sagomato Curvo con Sorriso (Dettagliato)
        beak_bob = math.sin(tick * 0.12) * 0.7

        # Mandibola inferiore d'ombra
        lower_beak = AppKit.NSBezierPath.bezierPath()
        lower_beak.moveToPoint_(AppKit.NSMakePoint(px + 4, py + 5.5 + hb_y))
        lower_beak.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 17, py + 6.5 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 9, py + 2.5 + hb_y),
            AppKit.NSMakePoint(px + 14, py + 3.8 + hb_y + beak_bob)
        )
        lower_beak.lineToPoint_(AppKit.NSMakePoint(px + 4, py + 6.5 + hb_y))
        lower_beak.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.85, 0.35, 0.02, 1.0).set()
        lower_beak.fill()

        # Corpo principale del becco con concavità e punta arrotondata
        beak_path = AppKit.NSBezierPath.bezierPath()
        beak_path.moveToPoint_(AppKit.NSMakePoint(px + 4, py + 10.5 + hb_y))
        beak_path.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 18.5, py + 7.5 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 9, py + 11.2 + hb_y),
            AppKit.NSMakePoint(px + 15, py + 10.2 + hb_y + beak_bob)
        )
        beak_path.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 17.5, py + 5.5 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 19.5, py + 6.8 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 19.0, py + 5.8 + hb_y + beak_bob)
        )
        beak_path.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 4, py + 5.0 + hb_y),
            AppKit.NSMakePoint(px + 13, py + 5.0 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 8, py + 4.5 + hb_y)
        )
        beak_path.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.50, 0.03, 1.0).set()
        beak_path.fill()

        # Linea del sorriso / separazione labiale
        crease = AppKit.NSBezierPath.bezierPath()
        crease.moveToPoint_(AppKit.NSMakePoint(px + 4.5, py + 6.8 + hb_y))
        crease.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 16.5, py + 6.8 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 9, py + 6.5 + hb_y),
            AppKit.NSMakePoint(px + 13, py + 7.0 + hb_y + beak_bob)
        )
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.78, 0.28, 0.0, 0.90).set()
        crease.setLineWidth_(0.85)
        crease.stroke()

        # Riflesso speculare dorato superiore
        highlight = AppKit.NSBezierPath.bezierPath()
        highlight.moveToPoint_(AppKit.NSMakePoint(px + 6, py + 9.8 + hb_y))
        highlight.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 14.5, py + 8.4 + hb_y + beak_bob),
            AppKit.NSMakePoint(px + 9, py + 10.3 + hb_y),
            AppKit.NSMakePoint(px + 12, py + 9.5 + hb_y + beak_bob)
        )
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.78, 0.30, 0.85).set()
        highlight.setLineWidth_(1.1)
        highlight.stroke()

        # Narice d'anatra
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.65, 0.22, 0.0, 0.95).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(
            AppKit.NSMakeRect(px + 7.0, py + 8.8 + hb_y, 1.6, 1.2)
        ).fill()

        # Occhio con ciclo di ammiccamento e riflessi
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 1.5, py + 13.5 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 7.0, py + 13.5 + hb_y),
                AppKit.NSMakePoint(px + 3.5, py + 16.0 + hb_y),
                AppKit.NSMakePoint(px + 5.0, py + 16.0 + hb_y)
            )
            AppKit.NSColor.blackColor().set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.blackColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1.5, py + 10.5 + hb_y, 5.0, 5.5)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3.0, py + 13.0 + hb_y, 2.0, 2.0)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.2, py + 11.2 + hb_y, 0.9, 0.9)).fill()

    def _draw_owl(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tuft_wave = math.sin(tick * 0.22) * 2.8
        # Piumaggio Gufo Saggio (Marrone Caffè / Grigio Tortora)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.58, 0.46, 0.38, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 11, py + 1 + hb_y, 23, 21)).fill()

        # Ciuffi auricolari a punta da gufo che ondeggiano nel vento
        tuft = AppKit.NSBezierPath.bezierPath()
        tuft.moveToPoint_(AppKit.NSMakePoint(px - 9, py + 17 + hb_y))
        tuft.lineToPoint_(AppKit.NSMakePoint(px - 13, py + 25 + hb_y + tuft_wave))
        tuft.lineToPoint_(AppKit.NSMakePoint(px - 4, py + 20 + hb_y))
        tuft.closePath()
        tuft.fill()

        # Maschera facciale chiara
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.92, 0.88, 0.80, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 2, py + 4 + hb_y, 14, 14)).fill()

        # Becco ricurvo
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.65, 0.15, 1.0).set()
        beak = AppKit.NSBezierPath.bezierPath()
        beak.moveToPoint_(AppKit.NSMakePoint(px + 7, py + 10 + hb_y))
        beak.lineToPoint_(AppKit.NSMakePoint(px + 14, py + 7 + hb_y))
        beak.lineToPoint_(AppKit.NSMakePoint(px + 7, py + 5 + hb_y))
        beak.closePath()
        beak.fill()

        # Occhio dorato con ammiccamento
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(2.0)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 1.0, py + 12.5 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 9.0, py + 12.5 + hb_y),
                AppKit.NSMakePoint(px + 4.0, py + 16.0 + hb_y),
                AppKit.NSMakePoint(px + 6.0, py + 16.0 + hb_y)
            )
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.12, 0.08, 1.0).set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.80, 0.15, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2, py + 10 + hb_y, 6.0, 6.0)).fill()
            AppKit.NSColor.blackColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4, py + 11.5 + hb_y, 3.0, 3.0)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 5, py + 13 + hb_y, 1.2, 1.2)).fill()

    def _draw_bunny(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        ear_base_wave = math.sin(tick * 0.18) * 2.5
        ear_tip_wave = math.sin(tick * 0.22 + 0.8) * 4.2

        # 🐰 1. Back Ear (Orecchio Posteriore per profondità 3D)
        ear_r = AppKit.NSBezierPath.bezierPath()
        ear_r.moveToPoint_(AppKit.NSMakePoint(px - 3, py + 17 + hb_y))
        ear_r.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 10, py + 36 + ear_tip_wave * 0.9 + hb_y),
            AppKit.NSMakePoint(px - 8, py + 26 + ear_base_wave * 0.8 + hb_y),
            AppKit.NSMakePoint(px - 17, py + 32 + ear_tip_wave * 0.9 + hb_y)
        )
        ear_r.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 2, py + 18 + hb_y),
            AppKit.NSMakePoint(px - 4, py + 33 + ear_tip_wave * 0.9 + hb_y),
            AppKit.NSMakePoint(px + 1, py + 25 + hb_y)
        )
        ear_r.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.90, 0.88, 0.87, 1.0).set()
        ear_r.fill()

        # Interno Orecchio Posteriore
        ear_r_in = AppKit.NSBezierPath.bezierPath()
        ear_r_in.moveToPoint_(AppKit.NSMakePoint(px - 2, py + 19 + hb_y))
        ear_r_in.lineToPoint_(AppKit.NSMakePoint(px - 8, py + 32 + ear_tip_wave * 0.9 + hb_y))
        ear_r_in.lineToPoint_(AppKit.NSMakePoint(px, py + 21 + hb_y))
        ear_r_in.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.65, 0.72, 0.60).set()
        ear_r_in.fill()

        # 🐰 2. Front Ear (Orecchio Anteriore Floppy)
        ear_l = AppKit.NSBezierPath.bezierPath()
        ear_l.moveToPoint_(AppKit.NSMakePoint(px - 9, py + 16 + hb_y))
        ear_l.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 18, py + 35 + ear_tip_wave + hb_y),
            AppKit.NSMakePoint(px - 17, py + 24 + ear_base_wave + hb_y),
            AppKit.NSMakePoint(px - 25, py + 30 + ear_tip_wave + hb_y)
        )
        ear_l.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 4, py + 18 + hb_y),
            AppKit.NSMakePoint(px - 10, py + 32 + ear_tip_wave + hb_y),
            AppKit.NSMakePoint(px - 5, py + 24 + hb_y)
        )
        ear_l.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.96, 0.95, 1.0).set()
        ear_l.fill()

        # Interno Orecchio Anteriore Rosa Pastello
        ear_inner = AppKit.NSBezierPath.bezierPath()
        ear_inner.moveToPoint_(AppKit.NSMakePoint(px - 8, py + 18 + hb_y))
        ear_inner.lineToPoint_(AppKit.NSMakePoint(px - 16, py + 31 + ear_tip_wave + hb_y))
        ear_inner.lineToPoint_(AppKit.NSMakePoint(px - 6, py + 20 + hb_y))
        ear_inner.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.72, 0.78, 0.85).set()
        ear_inner.fill()

        # 🐰 3. Testa Rotonda Soffice
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.96, 0.95, 1.0).set()
        head = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 9, py + 2 + hb_y, 21, 19))
        head.fill()

        # 🐰 4. Musetto Morbido e Guancia Rosa (Zero Becco)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.82, 0.86, 0.65).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 1, py + 4 + hb_y, 9, 7)).fill()

        # Cuscinetto musetto bianco soffice
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 1.0, 1.0).set()
        muzzle = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 6, py + 3.5 + hb_y, 7.5, 6.5))
        muzzle.fill()

        # 🐰 5. Dente da Coniglietto (Cute Bunny Buck Tooth)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.95, 0.98, 1.0).set()
        tooth = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            AppKit.NSMakeRect(px + 8.5, py + 2.0 + hb_y, 3.2, 3.2), 1.0, 1.0
        )
        tooth.fill()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.70, 0.65, 0.70, 0.60).set()
        tooth.setLineWidth_(0.6)
        tooth.stroke()

        # 🐰 6. Occhio Grande da Coniglio con riflessi dolci
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 1.0, py + 12.5 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 8.0, py + 12.5 + hb_y),
                AppKit.NSMakePoint(px + 3.5, py + 15.5 + hb_y),
                AppKit.NSMakePoint(px + 5.5, py + 15.5 + hb_y)
            )
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.22, 0.15, 0.28, 1.0).set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.22, 0.15, 0.28, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1.5, py + 9.5 + hb_y, 5.5, 6.5)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3.0, py + 12.5 + hb_y, 2.2, 2.2)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.5, py + 10.5 + hb_y, 1.0, 1.0)).fill()

        # 🐰 7. Nasino a Bottone Rosa (Cute Button Bunny Nose)
        nose_twitch = 0.4 if (tick % 24) < 10 else 0.0
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.48, 0.62, 1.0).set()
        nose = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
            AppKit.NSMakeRect(px + 10.0, py + 7.0 + hb_y + nose_twitch, 3.5, 2.8)
        )
        nose.fill()

        # Fessura del musetto (Philtrum)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.85, 0.40, 0.55, 0.80).set()
        philtrum = AppKit.NSBezierPath.bezierPath()
        philtrum.moveToPoint_(AppKit.NSMakePoint(px + 10.5, py + 7.0 + hb_y + nose_twitch))
        philtrum.lineToPoint_(AppKit.NSMakePoint(px + 10.5, py + 4.8 + hb_y))
        philtrum.setLineWidth_(0.8)
        philtrum.stroke()

        # 🐰 8. Lentiggini/Punti Musetto da Coniglietto (Zero becco grigio)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.85, 0.55, 0.65, 0.70).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.0, py + 6.5 + hb_y, 1.1, 1.1)).fill()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 6.0, py + 5.8 + hb_y, 1.1, 1.1)).fill()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.8, py + 4.8 + hb_y, 1.1, 1.1)).fill()

    def _draw_platypus(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tail_bob = math.sin(tick * 0.16) * 3.5
        # Coda a castoro che ondeggia nel flusso
        tail_path = AppKit.NSBezierPath.bezierPath()
        tail_path.moveToPoint_(AppKit.NSMakePoint(px - 36, py - 4 + tail_bob * 0.3))
        tail_path.lineToPoint_(AppKit.NSMakePoint(px - 58, py + 4 + tail_bob))
        tail_path.lineToPoint_(AppKit.NSMakePoint(px - 62, py - 6 + tail_bob))
        tail_path.lineToPoint_(AppKit.NSMakePoint(px - 38, py - 12 + tail_bob * 0.3))
        tail_path.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.42, 0.26, 0.16, 1.0).set()
        tail_path.fill()

        # Testa e corpo verde acqua / ottanio (Perry Teal)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.65, 0.62, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 10, py + 2 + hb_y, 23, 19)).fill()

        # Becco piatto largo da ornitorinco
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.52, 0.12, 1.0).set()
        beak = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            AppKit.NSMakeRect(px + 4, py + 3 + hb_y, 19, 8), 3.0, 3.0
        )
        beak.fill()

        # Occhio con ammiccamento
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 2.0, py + 13.0 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 8.0, py + 13.0 + hb_y),
                AppKit.NSMakePoint(px + 4.5, py + 15.5 + hb_y),
                AppKit.NSMakePoint(px + 6.0, py + 15.5 + hb_y)
            )
            AppKit.NSColor.blackColor().set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.blackColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3, py + 11 + hb_y, 4.5, 4.5)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.5, py + 12.5 + hb_y, 1.5, 1.5)).fill()

    def _draw_squirrel(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tail_wave = math.sin(tick * 0.18) * 3.8
        tail = AppKit.NSBezierPath.bezierPath()
        tail.moveToPoint_(AppKit.NSMakePoint(px - 34, py - 4))
        tail.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 44, py + 26 + tail_wave),
            AppKit.NSMakePoint(px - 48, py + 8 + tail_wave * 0.5),
            AppKit.NSMakePoint(px - 56, py + 22 + tail_wave)
        )
        tail.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 26, py + 4),
            AppKit.NSMakePoint(px - 36, py + 24 + tail_wave),
            AppKit.NSMakePoint(px - 30, py + 12)
        )
        tail.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.78, 0.42, 0.22, 1.0).set()
        tail.fill()

        # Testa castana
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.82, 0.46, 0.25, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 9, py + 2 + hb_y, 21, 19)).fill()

        # Petto e guanciotte bianche
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.95, 0.90, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1, py + 3 + hb_y, 10, 8)).fill()

        # Musetto e nasino
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.25, 0.15, 0.12, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 10, py + 6 + hb_y, 3.5, 3.5)).fill()

        # Occhio vispo con ammiccamento
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 1.0, py + 12.0 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 7.0, py + 12.0 + hb_y),
                AppKit.NSMakePoint(px + 3.5, py + 14.5 + hb_y),
                AppKit.NSMakePoint(px + 5.0, py + 14.5 + hb_y)
            )
            AppKit.NSColor.blackColor().set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.blackColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2, py + 10 + hb_y, 4.5, 5.0)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3.5, py + 12 + hb_y, 1.8, 1.8)).fill()

    def _draw_fox(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        tail_sway = math.sin(tick * 0.18) * 3.2

        # 🦊 1. Fluffy S-curved Bushy Tail behind cockpit
        tail = AppKit.NSBezierPath.bezierPath()
        tail.moveToPoint_(AppKit.NSMakePoint(px - 34, py - 4))
        tail.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 48, py + 22 + tail_sway),
            AppKit.NSMakePoint(px - 46, py + 4 + tail_sway * 0.4),
            AppKit.NSMakePoint(px - 58, py + 16 + tail_sway)
        )
        tail.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 28, py + 2),
            AppKit.NSMakePoint(px - 42, py + 24 + tail_sway),
            AppKit.NSMakePoint(px - 32, py + 10)
        )
        tail.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.92, 0.38, 0.15, 1.0).set()
        tail.fill()

        # Cream-white fluffy tail tip
        tip = AppKit.NSBezierPath.bezierPath()
        tip.moveToPoint_(AppKit.NSMakePoint(px - 44, py + 15 + tail_sway))
        tip.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 48, py + 22 + tail_sway),
            AppKit.NSMakePoint(px - 47, py + 17 + tail_sway),
            AppKit.NSMakePoint(px - 52, py + 20 + tail_sway)
        )
        tip.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 40, py + 17 + tail_sway),
            AppKit.NSMakePoint(px - 45, py + 22 + tail_sway),
            AppKit.NSMakePoint(px - 42, py + 19 + tail_sway)
        )
        tip.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.95, 0.90, 1.0).set()
        tip.fill()

        # 🦊 2. Back Ear (Orecchio Posteriore con profondità 3D)
        back_ear = AppKit.NSBezierPath.bezierPath()
        back_ear.moveToPoint_(AppKit.NSMakePoint(px - 10, py + 15 + hb_y))
        back_ear.lineToPoint_(AppKit.NSMakePoint(px - 9, py + 27 + hb_y))
        back_ear.lineToPoint_(AppKit.NSMakePoint(px - 2, py + 18 + hb_y))
        back_ear.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.78, 0.28, 0.10, 1.0).set()
        back_ear.fill()

        back_tip = AppKit.NSBezierPath.bezierPath()
        back_tip.moveToPoint_(AppKit.NSMakePoint(px - 10, py + 23 + hb_y))
        back_tip.lineToPoint_(AppKit.NSMakePoint(px - 9, py + 27 + hb_y))
        back_tip.lineToPoint_(AppKit.NSMakePoint(px - 5, py + 22 + hb_y))
        back_tip.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.20, 0.12, 0.10, 1.0).set()
        back_tip.fill()

        # 🦊 3. Testa Rotonda e Morbida (Warm terracotta fox head)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.45, 0.18, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 10, py + 2 + hb_y, 22, 20)).fill()

        # 🦊 4. Front Ear (Orecchio Anteriore con ciuffo interno crema/rosa)
        front_ear = AppKit.NSBezierPath.bezierPath()
        front_ear.moveToPoint_(AppKit.NSMakePoint(px - 4, py + 17 + hb_y))
        front_ear.lineToPoint_(AppKit.NSMakePoint(px - 1, py + 29 + hb_y))
        front_ear.lineToPoint_(AppKit.NSMakePoint(px + 6, py + 17 + hb_y))
        front_ear.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.45, 0.18, 1.0).set()
        front_ear.fill()

        ear_tip = AppKit.NSBezierPath.bezierPath()
        ear_tip.moveToPoint_(AppKit.NSMakePoint(px - 3, py + 24 + hb_y))
        ear_tip.lineToPoint_(AppKit.NSMakePoint(px - 1, py + 29 + hb_y))
        ear_tip.lineToPoint_(AppKit.NSMakePoint(px + 3, py + 22 + hb_y))
        ear_tip.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.18, 0.12, 0.10, 1.0).set()
        ear_tip.fill()

        inner_ear = AppKit.NSBezierPath.bezierPath()
        inner_ear.moveToPoint_(AppKit.NSMakePoint(px - 2, py + 18 + hb_y))
        inner_ear.lineToPoint_(AppKit.NSMakePoint(px - 1, py + 24 + hb_y))
        inner_ear.lineToPoint_(AppKit.NSMakePoint(px + 3, py + 18 + hb_y))
        inner_ear.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.92, 0.84, 1.0).set()
        inner_ear.fill()

        # 🦊 5. Guanciotti Morbidi e Musetto Bianco Crema
        muzzle = AppKit.NSBezierPath.bezierPath()
        muzzle.moveToPoint_(AppKit.NSMakePoint(px - 1, py + 3 + hb_y))
        muzzle.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 14, py + 6.5 + hb_y),
            AppKit.NSMakePoint(px + 4, py + 2.5 + hb_y),
            AppKit.NSMakePoint(px + 11, py + 4.5 + hb_y)
        )
        muzzle.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 3, py + 11 + hb_y),
            AppKit.NSMakePoint(px + 13, py + 9.5 + hb_y),
            AppKit.NSMakePoint(px + 8, py + 11.5 + hb_y)
        )
        muzzle.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.95, 0.90, 1.0).set()
        muzzle.fill()

        # Blush guance rosa pesca
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.48, 0.40, 0.40).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1, py + 5.5 + hb_y, 7, 5)).fill()

        # 🦊 6. Nasino a Bottone e Sorriso Dolce
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.10, 0.10, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 12.0, py + 6.8 + hb_y, 3.2, 2.4)).fill()
        AppKit.NSColor.whiteColor().set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 13.0, py + 7.8 + hb_y, 1.0, 0.8)).fill()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.50, 0.20, 0.10, 0.85).set()
        smile = AppKit.NSBezierPath.bezierPath()
        smile.moveToPoint_(AppKit.NSMakePoint(px + 8.5, py + 5.5 + hb_y))
        smile.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 12.5, py + 6.2 + hb_y),
            AppKit.NSMakePoint(px + 10.0, py + 4.6 + hb_y),
            AppKit.NSMakePoint(px + 11.5, py + 4.8 + hb_y)
        )
        smile.setLineWidth_(0.9)
        smile.stroke()

        # 🦊 7. Occhio Furbo e Dolce con riflessi e ammiccamento
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 1.5, py + 13.0 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 7.5, py + 13.0 + hb_y),
                AppKit.NSMakePoint(px + 3.5, py + 15.8 + hb_y),
                AppKit.NSMakePoint(px + 5.5, py + 15.8 + hb_y)
            )
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.10, 0.08, 1.0).set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.10, 0.08, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2.0, py + 10.5 + hb_y, 4.8, 5.2)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3.6, py + 12.6 + hb_y, 2.0, 2.0)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.8, py + 11.2 + hb_y, 0.9, 0.9)).fill()

    def _draw_penguin(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        wing_flap = math.sin(tick * 0.22) * 3.0

        # 🐧 1. Flapping Little Wing / Flipper
        wing = AppKit.NSBezierPath.bezierPath()
        wing.moveToPoint_(AppKit.NSMakePoint(px - 14, py + 10 + hb_y))
        wing.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 18, py + 1 + hb_y + wing_flap),
            AppKit.NSMakePoint(px - 19, py + 7 + hb_y + wing_flap * 0.5),
            AppKit.NSMakePoint(px - 21, py + 3 + hb_y + wing_flap)
        )
        wing.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 12, py + 5 + hb_y),
            AppKit.NSMakePoint(px - 16, py - 1 + hb_y + wing_flap),
            AppKit.NSMakePoint(px - 13, py + 2 + hb_y)
        )
        wing.closePath()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.14, 0.16, 0.24, 1.0).set()
        wing.fill()

        # 🐧 2. Round Navy Body & Head
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.14, 0.16, 0.24, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 11, py + 1 + hb_y, 23, 21)).fill()

        # 🐧 3. Pearly White Heart/Oval Face & Belly Bib
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.97, 0.94, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 4, py + 2 + hb_y, 15, 17)).fill()

        # Soft baby penguin blush
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.45, 0.55, 0.42).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2, py + 5 + hb_y, 7, 5)).fill()

        # 🐧 4. Cute Little Gold/Orange Beak
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.65, 0.15, 1.0).set()
        beak = AppKit.NSBezierPath.bezierPath()
        beak.moveToPoint_(AppKit.NSMakePoint(px + 7.5, py + 9.5 + hb_y))
        beak.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 15.0, py + 7.0 + hb_y),
            AppKit.NSMakePoint(px + 10.5, py + 9.8 + hb_y),
            AppKit.NSMakePoint(px + 13.5, py + 8.8 + hb_y)
        )
        beak.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 7.5, py + 5.5 + hb_y),
            AppKit.NSMakePoint(px + 12.5, py + 5.8 + hb_y),
            AppKit.NSMakePoint(px + 9.5, py + 5.4 + hb_y)
        )
        beak.closePath()
        beak.fill()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.82, 0.35, 0.90).set()
        beak_hl = AppKit.NSBezierPath.bezierPath()
        beak_hl.moveToPoint_(AppKit.NSMakePoint(px + 8.5, py + 8.8 + hb_y))
        beak_hl.lineToPoint_(AppKit.NSMakePoint(px + 12.5, py + 7.8 + hb_y))
        beak_hl.setLineWidth_(0.8)
        beak_hl.stroke()

        # 🐧 5. Dapper Ruby Bow Tie (only when not wearing tuxedo)
        if self.outfit not in ("agent", "tuxedo") and "tuxedo" not in self.accessories:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.88, 0.22, 0.28, 1.0).set()
            bow_l = AppKit.NSBezierPath.bezierPath()
            bow_l.moveToPoint_(AppKit.NSMakePoint(px + 1, py + 3 + hb_y))
            bow_l.lineToPoint_(AppKit.NSMakePoint(px - 3, py + 5.5 + hb_y))
            bow_l.lineToPoint_(AppKit.NSMakePoint(px - 3, py + 1.5 + hb_y))
            bow_l.closePath()
            bow_l.fill()
            bow_r = AppKit.NSBezierPath.bezierPath()
            bow_r.moveToPoint_(AppKit.NSMakePoint(px + 1, py + 3 + hb_y))
            bow_r.lineToPoint_(AppKit.NSMakePoint(px + 5, py + 5.5 + hb_y))
            bow_r.lineToPoint_(AppKit.NSMakePoint(px + 5, py + 1.5 + hb_y))
            bow_r.closePath()
            bow_r.fill()
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.70, 0.15, 0.20, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 0.5, py + 2.0 + hb_y, 3, 3)).fill()

        # 🐧 6. Sparkling Baby Penguin Eyes with Blinking
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 1.0, py + 12.0 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 7.0, py + 12.0 + hb_y),
                AppKit.NSMakePoint(px + 3.0, py + 14.8 + hb_y),
                AppKit.NSMakePoint(px + 5.0, py + 14.8 + hb_y)
            )
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.14, 0.20, 1.0).set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.10, 0.12, 0.18, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1.5, py + 9.5 + hb_y, 4.8, 5.2)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3.0, py + 11.8 + hb_y, 2.0, 2.0)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4.2, py + 10.4 + hb_y, 0.9, 0.9)).fill()

    def _draw_panda(self, px: float, py: float, tick: int) -> None:
        hb_y = self._get_animal_bob(tick)
        ear_twitch = math.sin(tick * 0.15) * 0.6

        # 🐼 1. Furry Round Ears with 3D Depth
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.15, 0.18, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 11, py + 16 + hb_y + ear_twitch, 8, 8)).fill()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.12, 0.15, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 4, py + 16 + hb_y + ear_twitch, 8, 8)).fill()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.25, 0.25, 0.30, 0.6).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 5.5, py + 17.5 + hb_y + ear_twitch, 5, 5)).fill()

        # 🐼 2. Plump Cream-White Head
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.98, 0.96, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 10, py + 2 + hb_y, 22, 20)).fill()

        # 🐼 3. Soft Pink Blushing Cheeks
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.45, 0.58, 0.40).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1, py + 4.5 + hb_y, 7.5, 5)).fill()

        # 🐼 4. Characteristic Tilted Teardrop Eye Patch
        ctx = AppKit.NSGraphicsContext.currentContext()
        ctx.saveGraphicsState()
        patch_tf = AppKit.NSAffineTransform.transform()
        patch_tf.translateXBy_yBy_(px + 4.5, py + 12.0 + hb_y)
        patch_tf.rotateByDegrees_(-18.0)
        patch_tf.concat()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.12, 0.16, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(-3.5, -4.5, 7.0, 9.0)).fill()
        ctx.restoreGraphicsState()

        # 🐼 5. Sparkling Eyes inside Eye Patch with Blinking
        if self.is_eye_blinking(tick):
            eye_arc = AppKit.NSBezierPath.bezierPath()
            eye_arc.setLineWidth_(1.8)
            eye_arc.setLineCapStyle_(AppKit.NSLineCapStyleRound)
            eye_arc.moveToPoint_(AppKit.NSMakePoint(px + 2.0, py + 13.0 + hb_y))
            eye_arc.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 7.5, py + 13.0 + hb_y),
                AppKit.NSMakePoint(px + 4.0, py + 15.5 + hb_y),
                AppKit.NSMakePoint(px + 5.5, py + 15.5 + hb_y)
            )
            AppKit.NSColor.whiteColor().set()
            eye_arc.stroke()
        else:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.05, 0.05, 0.08, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2.5, py + 10.5 + hb_y, 4.5, 4.8)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 3.8, py + 12.5 + hb_y, 2.2, 2.2)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 5.0, py + 11.2 + hb_y, 1.0, 1.0)).fill()

        # 🐼 6. Cute Button Nose & Sweet Smile
        AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 1.0, 1.0, 0.80).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 6.0, py + 4.0 + hb_y, 7.5, 6.0)).fill()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.12, 0.15, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 9.5, py + 6.5 + hb_y, 3.2, 2.2)).fill()
        AppKit.NSColor.whiteColor().set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 10.5, py + 7.4 + hb_y, 0.9, 0.7)).fill()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.25, 0.20, 0.20, 0.85).set()
        mouth = AppKit.NSBezierPath.bezierPath()
        mouth.moveToPoint_(AppKit.NSMakePoint(px + 8.5, py + 5.2 + hb_y))
        mouth.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 11.0, py + 5.0 + hb_y),
            AppKit.NSMakePoint(px + 9.2, py + 4.2 + hb_y),
            AppKit.NSMakePoint(px + 10.5, py + 4.2 + hb_y)
        )
        mouth.setLineWidth_(0.85)
        mouth.stroke()

        # 🐼 7. Juicy Green Bamboo Shoot with Leaf
        bamboo_sway = math.sin(tick * 0.12) * 1.5
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.30, 0.72, 0.32, 1.0).set()
        bamboo = AppKit.NSBezierPath.bezierPath()
        bamboo.moveToPoint_(AppKit.NSMakePoint(px - 1, py + 5 + hb_y))
        bamboo.lineToPoint_(AppKit.NSMakePoint(px + 14, py + 1 + bamboo_sway))
        bamboo.setLineWidth_(2.2)
        bamboo.stroke()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.20, 0.55, 0.22, 1.0).set()
        joint = AppKit.NSBezierPath.bezierPath()
        joint.moveToPoint_(AppKit.NSMakePoint(px + 6, py + 5 + hb_y * 0.5))
        joint.lineToPoint_(AppKit.NSMakePoint(px + 7, py + 2.5 + hb_y * 0.5))
        joint.setLineWidth_(1.2)
        joint.stroke()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.38, 0.82, 0.38, 1.0).set()
        leaf = AppKit.NSBezierPath.bezierPath()
        leaf.moveToPoint_(AppKit.NSMakePoint(px + 14, py + 1 + bamboo_sway))
        leaf.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 20, py + 4 + bamboo_sway),
            AppKit.NSMakePoint(px + 16, py + 5 + bamboo_sway),
            AppKit.NSMakePoint(px + 18, py + 5 + bamboo_sway)
        )
        leaf.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 14, py + 1 + bamboo_sway),
            AppKit.NSMakePoint(px + 18, py + 2 + bamboo_sway),
            AppKit.NSMakePoint(px + 16, py + 1 + bamboo_sway)
        )
        leaf.closePath()
        leaf.fill()

    def _draw_outfit(self, px: float, py: float, tick: int) -> None:
        if self.outfit == "student":
            # 🎓 CAPPELLO DA LAUREA (Mortarboard Academic Cap with dangling tassel)
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.16, 0.22, 1.0).set()
            cap = AppKit.NSBezierPath.bezierPath()
            cap.moveToPoint_(AppKit.NSMakePoint(px - 14, py + 19))
            cap.lineToPoint_(AppKit.NSMakePoint(px + 3, py + 26))
            cap.lineToPoint_(AppKit.NSMakePoint(px + 18, py + 19))
            cap.lineToPoint_(AppKit.NSMakePoint(px + 1, py + 14))
            cap.closePath()
            cap.fill()

            # Nappina pendente dorata
            tassel_sway = math.sin(tick * 0.20) * 3.0
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.85, 0.35, 1.0).set()
            tassel = AppKit.NSBezierPath.bezierPath()
            tassel.moveToPoint_(AppKit.NSMakePoint(px + 2, py + 22))
            tassel.lineToPoint_(AppKit.NSMakePoint(px - 12 + tassel_sway, py + 10))
            tassel.setLineWidth_(1.4)
            tassel.stroke()

            # Occhiali rotondi da studioso
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.95, 0.80, 0.20, 1.0).set()
            lens = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1, py + 8, 7.5, 7.5))
            lens.setLineWidth_(1.2)
            lens.stroke()

        elif self.outfit == "chef":
            # 👨‍🍳 CAPPELLO DA CHEF (Pleated White Toque)
            AppKit.NSColor.whiteColor().set()
            toque = AppKit.NSBezierPath.bezierPath()
            toque.moveToPoint_(AppKit.NSMakePoint(px - 8, py + 16))
            toque.lineToPoint_(AppKit.NSMakePoint(px - 10, py + 27))
            toque.curveToPoint_controlPoint1_controlPoint2_(
                AppKit.NSMakePoint(px + 10, py + 28),
                AppKit.NSMakePoint(px - 4, py + 34),
                AppKit.NSMakePoint(px + 6, py + 34)
            )
            toque.lineToPoint_(AppKit.NSMakePoint(px + 8, py + 16))
            toque.closePath()
            toque.fill()
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.80, 0.82, 0.88, 1.0).set()
            toque.setLineWidth_(1.0)
            toque.stroke()

        elif self.outfit == "captain":
            # 🧑‍✈️ BERRETTO DA COMANDANTE DI VOLO (Navy Captain Cap with Gold Emblem)
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.16, 0.28, 1.0).set()
            cap = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 8, py + 16, 20, 8))
            cap.fill()
            # Visiera nera
            AppKit.NSColor.blackColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2, py + 14, 12, 4)).fill()
            # Fregio dorato
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.80, 0.25, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2, py + 19, 4, 4)).fill()

        elif self.outfit in ("agent", "tuxedo"):
            self._draw_tuxedo(px, py, tick)
            if self.animal == "platypus":
                self._draw_fedora(px, py, tick)
            else:
                self._draw_top_hat(px, py, tick)

        elif self.outfit == "concert":
            self._draw_headphones(px, py, tick)

        elif self.outfit == "gym":
            # 🏋️‍♂️ FASCETTA SPORTIVA ROSSA
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.92, 0.25, 0.25, 1.0).set()
            band = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                AppKit.NSMakeRect(px - 8, py + 14, 18, 5), 2.0, 2.0
            )
            band.fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px - 7, py + 15.5, 16, 1.5)).fill()

        elif self.outfit == "racer":
            # 🏎️ CASCO SPEED RACER
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.45, 0.15, 1.0).set()
            helmet = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 8, py + 12, 19, 14))
            helmet.fill()
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.18, 0.25, 0.85).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 2, py + 13, 10, 8)).fill()

        elif self.outfit == "zen":
            # 🌸 FIORE DI LOTO SULL'ORECCHIO
            AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.55, 0.75, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 6, py + 16, 8, 8)).fill()
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 4, py + 18, 4, 4)).fill()
            AppKit.NSColor.colorWithRed_green_blue_alpha_(1.0, 0.85, 0.20, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 3, py + 19, 2, 2)).fill()

        elif self.outfit == "banker":
            self._draw_banker_visor(px, py, tick)
            self._draw_gold_coin(px, py, tick)

        else:  # aviator
            # 🪖 OCCHIALONI DA AVIATORE CON CINGHIA
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.35, 0.25, 0.18, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px - 8, py + 13, 18, 3)).fill()
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.90, 0.75, 0.35, 1.0).set()
            goggle = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px, py + 9, 10, 10))
            goggle.setLineWidth_(1.6)
            goggle.stroke()
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.55, 0.88, 0.98, 0.75).set()
            goggle.fill()

    def _draw_fedora(self, px: float, py: float, tick: int) -> None:
        """Iconic brown fedora with black ribbon band - strictly for Perry the Platypus."""
        hb_y = self._get_animal_bob(tick)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.48, 0.28, 0.15, 1.0).set()
        brim = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 14, py + 16 + hb_y, 28, 6))
        brim.fill()
        crown = AppKit.NSBezierPath.bezierPath()
        crown.moveToPoint_(AppKit.NSMakePoint(px - 7, py + 18 + hb_y))
        crown.lineToPoint_(AppKit.NSMakePoint(px - 5, py + 28 + hb_y))
        crown.lineToPoint_(AppKit.NSMakePoint(px + 5, py + 29 + hb_y))
        crown.lineToPoint_(AppKit.NSMakePoint(px + 7, py + 18 + hb_y))
        crown.closePath()
        crown.fill()
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.15, 0.18, 1.0).set()
        band = AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px - 6.5, py + 18 + hb_y, 13, 3))
        band.fill()

    def _draw_top_hat(self, px: float, py: float, tick: int) -> None:
        """Dapper black formal silk top hat with satin ribbon band for work animals."""
        hb_y = self._get_animal_bob(tick)
        # Flared brim
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.08, 0.08, 0.12, 1.0).set()
        brim = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 13, py + 16 + hb_y, 26, 5))
        brim.fill()

        # Tall silk crown
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.11, 0.11, 0.16, 1.0).set()
        crown = AppKit.NSBezierPath.bezierPath()
        crown.moveToPoint_(AppKit.NSMakePoint(px - 7, py + 18 + hb_y))
        crown.lineToPoint_(AppKit.NSMakePoint(px - 8, py + 33 + hb_y))
        crown.lineToPoint_(AppKit.NSMakePoint(px + 8, py + 33 + hb_y))
        crown.lineToPoint_(AppKit.NSMakePoint(px + 7, py + 18 + hb_y))
        crown.closePath()
        crown.fill()

        # Crown top oval
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.14, 0.14, 0.20, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 8, py + 31.5 + hb_y, 16, 3)).fill()

        # Satin ribbon band
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.85, 0.22, 0.30, 1.0).set()
        band = AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px - 7, py + 18 + hb_y, 14, 3.2))
        band.fill()

        # Gold buckle
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.80, 0.25, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px + 3, py + 18.5 + hb_y, 2.2, 2.2)).fill()

    def _draw_tuxedo(self, px: float, py: float, tick: int) -> None:
        """Tailored black tuxedo jacket with satin lapels, white pleated shirt, black studs, and pocket square."""
        hb_y = self._get_animal_bob(tick)

        # 1. Tailored onyx jacket base hugging animal's round torso
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.08, 0.08, 0.12, 1.0).set()
        jacket = AppKit.NSBezierPath.bezierPath()
        jacket.moveToPoint_(AppKit.NSMakePoint(px - 4.5, py + 5.5 + hb_y))
        jacket.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 10.5, py + 1.2 + hb_y),
            AppKit.NSMakePoint(px - 7.8, py + 5.2 + hb_y),
            AppKit.NSMakePoint(px - 11.0, py + 3.2 + hb_y)
        )
        jacket.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 6.5, py + 1.2 + hb_y),
            AppKit.NSMakePoint(px - 6.0, py - 0.5 + hb_y),
            AppKit.NSMakePoint(px + 2.5, py - 0.5 + hb_y)
        )
        jacket.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 3.8, py + 4.8 + hb_y),
            AppKit.NSMakePoint(px + 7.2, py + 2.6 + hb_y),
            AppKit.NSMakePoint(px + 5.8, py + 4.2 + hb_y)
        )
        jacket.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 4.5, py + 5.5 + hb_y),
            AppKit.NSMakePoint(px + 1.0, py + 5.6 + hb_y),
            AppKit.NSMakePoint(px - 2.0, py + 5.6 + hb_y)
        )
        jacket.closePath()
        jacket.fill()

        # 2. Crisp white pleated shirt bib (curved V-neck)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.98, 1.0, 1.0).set()
        shirt = AppKit.NSBezierPath.bezierPath()
        shirt.moveToPoint_(AppKit.NSMakePoint(px - 2.4, py + 5.0 + hb_y))
        shirt.lineToPoint_(AppKit.NSMakePoint(px + 2.4, py + 5.0 + hb_y))
        shirt.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 0.1, py + 0.8 + hb_y),
            AppKit.NSMakePoint(px + 1.8, py + 2.8 + hb_y),
            AppKit.NSMakePoint(px + 0.8, py + 1.6 + hb_y)
        )
        shirt.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 2.4, py + 5.0 + hb_y),
            AppKit.NSMakePoint(px - 0.6, py + 1.6 + hb_y),
            AppKit.NSMakePoint(px - 1.8, py + 2.8 + hb_y)
        )
        shirt.closePath()
        shirt.fill()

        # Black studs
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.10, 0.10, 0.15, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 0.4, py + 2.6 + hb_y, 1.1, 1.1)).fill()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 0.4, py + 1.4 + hb_y, 1.1, 1.1)).fill()

        # 3. Satin peak lapels
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.18, 0.19, 0.26, 1.0).set()
        l_lapel = AppKit.NSBezierPath.bezierPath()
        l_lapel.moveToPoint_(AppKit.NSMakePoint(px - 3.8, py + 5.0 + hb_y))
        l_lapel.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 5.5, py + 3.4 + hb_y),
            AppKit.NSMakePoint(px - 4.8, py + 4.6 + hb_y),
            AppKit.NSMakePoint(px - 5.6, py + 4.0 + hb_y)
        )
        l_lapel.lineToPoint_(AppKit.NSMakePoint(px - 0.2, py + 0.9 + hb_y))
        l_lapel.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 2.0, py + 5.0 + hb_y),
            AppKit.NSMakePoint(px - 0.8, py + 2.2 + hb_y),
            AppKit.NSMakePoint(px - 1.6, py + 3.6 + hb_y)
        )
        l_lapel.closePath()
        l_lapel.fill()

        r_lapel = AppKit.NSBezierPath.bezierPath()
        r_lapel.moveToPoint_(AppKit.NSMakePoint(px + 3.6, py + 5.0 + hb_y))
        r_lapel.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 4.8, py + 3.2 + hb_y),
            AppKit.NSMakePoint(px + 4.4, py + 4.4 + hb_y),
            AppKit.NSMakePoint(px + 5.0, py + 3.8 + hb_y)
        )
        r_lapel.lineToPoint_(AppKit.NSMakePoint(px + 0.2, py + 0.9 + hb_y))
        r_lapel.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 2.0, py + 5.0 + hb_y),
            AppKit.NSMakePoint(px + 0.8, py + 2.2 + hb_y),
            AppKit.NSMakePoint(px + 1.6, py + 3.6 + hb_y)
        )
        r_lapel.closePath()
        r_lapel.fill()

        # 4. Pocket square (two white folded silk peaks)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.98, 1.0, 1.0).set()
        psquare = AppKit.NSBezierPath.bezierPath()
        psquare.moveToPoint_(AppKit.NSMakePoint(px - 7.5, py + 2.0 + hb_y))
        psquare.lineToPoint_(AppKit.NSMakePoint(px - 6.2, py + 3.8 + hb_y))
        psquare.lineToPoint_(AppKit.NSMakePoint(px - 5.5, py + 2.8 + hb_y))
        psquare.lineToPoint_(AppKit.NSMakePoint(px - 4.8, py + 3.6 + hb_y))
        psquare.lineToPoint_(AppKit.NSMakePoint(px - 4.2, py + 2.0 + hb_y))
        psquare.closePath()
        psquare.fill()

        # 5. Dapper ruby butterfly bow tie
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.88, 0.20, 0.26, 1.0).set()
        bow_l = AppKit.NSBezierPath.bezierPath()
        bow_l.moveToPoint_(AppKit.NSMakePoint(px + 0.1, py + 4.9 + hb_y))
        bow_l.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 3.6, py + 6.1 + hb_y),
            AppKit.NSMakePoint(px - 1.2, py + 5.7 + hb_y),
            AppKit.NSMakePoint(px - 2.8, py + 6.3 + hb_y)
        )
        bow_l.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 3.6, py + 3.7 + hb_y),
            AppKit.NSMakePoint(px - 4.0, py + 5.1 + hb_y),
            AppKit.NSMakePoint(px - 4.0, py + 4.5 + hb_y)
        )
        bow_l.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 0.1, py + 4.9 + hb_y),
            AppKit.NSMakePoint(px - 2.8, py + 3.5 + hb_y),
            AppKit.NSMakePoint(px - 1.2, py + 4.3 + hb_y)
        )
        bow_l.closePath()
        bow_l.fill()

        bow_r = AppKit.NSBezierPath.bezierPath()
        bow_r.moveToPoint_(AppKit.NSMakePoint(px + 0.1, py + 4.9 + hb_y))
        bow_r.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 3.6, py + 6.1 + hb_y),
            AppKit.NSMakePoint(px + 1.4, py + 5.7 + hb_y),
            AppKit.NSMakePoint(px + 2.8, py + 6.3 + hb_y)
        )
        bow_r.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 3.6, py + 3.7 + hb_y),
            AppKit.NSMakePoint(px + 4.0, py + 5.1 + hb_y),
            AppKit.NSMakePoint(px + 4.0, py + 4.5 + hb_y)
        )
        bow_r.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 0.1, py + 4.9 + hb_y),
            AppKit.NSMakePoint(px + 2.8, py + 3.5 + hb_y),
            AppKit.NSMakePoint(px + 1.4, py + 4.3 + hb_y)
        )
        bow_r.closePath()
        bow_r.fill()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.70, 0.14, 0.20, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 1.0, py + 3.9 + hb_y, 2.2, 2.0)).fill()

    def _draw_headphones(self, px: float, py: float, tick: int) -> None:
        """Cushioned over-ear DJ concert headphones with glowing accents and animated floating music notes."""
        hb_y = self._get_animal_bob(tick)

        # 1. Padded arched headband over top of crown
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.13, 0.18, 1.0).set()
        band = AppKit.NSBezierPath.bezierPath()
        band.moveToPoint_(AppKit.NSMakePoint(px - 4.5, py + 18.0 + hb_y))
        band.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 4.0, py + 21.0 + hb_y),
            AppKit.NSMakePoint(px - 4.0, py + 26.5 + hb_y),
            AppKit.NSMakePoint(px + 2.5, py + 27.5 + hb_y)
        )
        band.setLineWidth_(3.6)
        band.setLineCapStyle_(AppKit.NSLineCapStyleRound)
        band.stroke()

        # Headband top soft cushion (Catppuccin Mauve)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.80, 0.65, 0.98, 1.0).set()
        cushion = AppKit.NSBezierPath.bezierPath()
        cushion.moveToPoint_(AppKit.NSMakePoint(px - 2.5, py + 23.8 + hb_y))
        cushion.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 2.8, py + 24.2 + hb_y),
            AppKit.NSMakePoint(px - 1.5, py + 26.8 + hb_y),
            AppKit.NSMakePoint(px + 1.8, py + 27.0 + hb_y)
        )
        cushion.setLineWidth_(2.4)
        cushion.setLineCapStyle_(AppKit.NSLineCapStyleRound)
        cushion.stroke()

        # 2. Main DJ Ear-Cup on the side of the head (behind eye, unobscured face)
        cx = px - 4.5
        cy = py + 7.5 + hb_y
        # Outer black cushion
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.13, 0.18, 1.0).set()
        near_cup = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
            AppKit.NSMakeRect(cx - 4.5, cy, 9.0, 13.0)
        )
        near_cup.fill()

        # Glowing neon ring (Catppuccin Pink)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.76, 0.91, 1.0).set()
        near_led = AppKit.NSBezierPath.bezierPathWithOvalInRect_(
            AppKit.NSMakeRect(cx - 3.2, cy + 1.8, 6.4, 9.4)
        )
        near_led.setLineWidth_(1.6)
        near_led.stroke()

        # Core inner metallic disc
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.80, 0.65, 0.98, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(
            AppKit.NSMakeRect(cx - 1.8, cy + 3.8, 3.6, 5.4)
        ).fill()

        # Center metallic dot
        AppKit.NSColor.whiteColor().set()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(
            AppKit.NSMakeRect(cx - 0.9, cy + 5.2, 1.8, 2.6)
        ).fill()

        # 3. Animated floating music notes (♪ ♫)
        note_bob1 = math.sin(tick * 0.16) * 2.0
        note_bob2 = math.sin(tick * 0.16 + 1.8) * 2.0

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.98, 0.85, 0.40, 0.95).set()
        n1_x = px - 15.0
        n1_y = py + 22.0 + hb_y + note_bob1
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(n1_x, n1_y, 3.5, 2.6)).fill()
        stem1 = AppKit.NSBezierPath.bezierPath()
        stem1.moveToPoint_(AppKit.NSMakePoint(n1_x + 3.0, n1_y + 1.5))
        stem1.lineToPoint_(AppKit.NSMakePoint(n1_x + 3.0, n1_y + 7.5))
        stem1.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(n1_x + 6.0, n1_y + 5.5),
            AppKit.NSMakePoint(n1_x + 3.2, n1_y + 8.5),
            AppKit.NSMakePoint(n1_x + 5.5, n1_y + 7.5)
        )
        stem1.setLineWidth_(1.1)
        stem1.stroke()

        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.76, 0.91, 0.95).set()
        n2_x = px + 12.0
        n2_y = py + 23.0 + hb_y + note_bob2
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(n2_x, n2_y, 3.0, 2.2)).fill()
        AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(n2_x + 5.0, n2_y + 1.5, 3.0, 2.2)).fill()
        beam = AppKit.NSBezierPath.bezierPath()
        beam.moveToPoint_(AppKit.NSMakePoint(n2_x + 2.5, n2_y + 1.0))
        beam.lineToPoint_(AppKit.NSMakePoint(n2_x + 2.5, n2_y + 7.0))
        beam.lineToPoint_(AppKit.NSMakePoint(n2_x + 7.5, n2_y + 8.5))
        beam.lineToPoint_(AppKit.NSMakePoint(n2_x + 7.5, n2_y + 2.5))
        beam.setLineWidth_(1.0)
        beam.stroke()
        tbeam = AppKit.NSBezierPath.bezierPath()
        tbeam.moveToPoint_(AppKit.NSMakePoint(n2_x + 2.0, n2_y + 7.0))
        tbeam.lineToPoint_(AppKit.NSMakePoint(n2_x + 8.0, n2_y + 8.5))
        tbeam.setLineWidth_(1.8)
        tbeam.stroke()

    def _draw_accessories(self, px: float, py: float, tick: int) -> None:
        """Draws optional reusable accessory layers without changing animal geometry."""
        # Dedicated full accessories
        if "headphones" in self.accessories and self.outfit != "concert":
            self._draw_headphones(px, py, tick)
        if "tuxedo" in self.accessories and self.outfit not in ("agent", "tuxedo"):
            self._draw_tuxedo(px, py, tick)
        if "top_hat" in self.accessories and self.animal != "platypus" and self.outfit not in ("agent", "tuxedo"):
            self._draw_top_hat(px, py, tick)
        if "fedora" in self.accessories and self.animal == "platypus" and self.outfit not in ("agent", "tuxedo"):
            self._draw_fedora(px, py, tick)

        if "sunglasses" in self.accessories:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.08, 0.09, 0.13, 0.92).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 1, py + 9, 8, 5)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 10, py + 9, 8, 5)).fill()
        if "bow_tie" in self.accessories and self.animal != "penguin" and self.outfit not in ("agent", "tuxedo") and "tuxedo" not in self.accessories:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.85, 0.27, 0.30, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 1, py + 1, 6, 5)).fill()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px + 5, py + 1, 6, 5)).fill()
        if "briefcase" in self.accessories:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.55, 0.32, 0.17, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px - 28, py - 9, 12, 8)).fill()
        if "badge" in self.accessories:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.80, 0.25, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 2, py + 5, 4, 4)).fill()
        if "earpiece" in self.accessories:
            AppKit.NSColor.colorWithRed_green_blue_alpha_(0.15, 0.15, 0.18, 1.0).set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(px - 12, py + 10, 3, 3)).fill()
        if "banker_visor" in self.accessories and self.outfit != "banker":
            self._draw_banker_visor(px, py, tick)
        if "gold_coin" in self.accessories and self.outfit != "banker":
            self._draw_gold_coin(px, py, tick)

    def _draw_banker_visor(self, px: float, py: float, tick: int) -> None:
        """Classic translucent emerald green banker's visor with dark trim and strap."""
        hb_y = self._get_animal_bob(tick)
        # 1. Dark leather strap wrapping head
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.18, 0.14, 0.12, 1.0).set()
        strap = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            AppKit.NSMakeRect(px - 9, py + 14 + hb_y, 20, 4.5), 1.5, 1.5
        )
        strap.fill()

        # 2. Golden buckle on strap
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.82, 0.28, 1.0).set()
        AppKit.NSBezierPath.bezierPathWithRect_(AppKit.NSMakeRect(px - 8.5, py + 14.5 + hb_y, 2.5, 3.5)).fill()

        # 3. Translucent emerald-green visor bill/brim jutting forward
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.12, 0.78, 0.45, 0.82).set()
        brim = AppKit.NSBezierPath.bezierPath()
        brim.moveToPoint_(AppKit.NSMakePoint(px - 4, py + 15 + hb_y))
        brim.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px + 18, py + 11.5 + hb_y),
            AppKit.NSMakePoint(px + 5, py + 16 + hb_y),
            AppKit.NSMakePoint(px + 14, py + 14 + hb_y)
        )
        brim.lineToPoint_(AppKit.NSMakePoint(px + 16, py + 8.5 + hb_y))
        brim.curveToPoint_controlPoint1_controlPoint2_(
            AppKit.NSMakePoint(px - 3, py + 12.5 + hb_y),
            AppKit.NSMakePoint(px + 10, py + 9.5 + hb_y),
            AppKit.NSMakePoint(px + 3, py + 11.5 + hb_y)
        )
        brim.closePath()
        brim.fill()

        # 4. Mint/gloss shine reflection along visor brim
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.70, 0.98, 0.82, 0.75).set()
        shine = AppKit.NSBezierPath.bezierPath()
        shine.moveToPoint_(AppKit.NSMakePoint(px, py + 14.5 + hb_y))
        shine.lineToPoint_(AppKit.NSMakePoint(px + 16, py + 11 + hb_y))
        shine.setLineWidth_(1.0)
        shine.stroke()

    def _draw_gold_coin(self, px: float, py: float, tick: int) -> None:
        """Sparkling gold coin emblem with subtle twinkle."""
        hb_y = self._get_animal_bob(tick)
        cx = px - 3.5
        cy = py + 2.5 + hb_y

        # 1. Outer golden coin disk
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.96, 0.80, 0.22, 1.0).set()
        coin = AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(cx - 3.5, cy - 3.5, 7.0, 7.0))
        coin.fill()

        # 2. Coin rim
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.80, 0.60, 0.12, 1.0).set()
        coin.setLineWidth_(0.8)
        coin.stroke()

        # 3. Embossed Currency Symbol (mini $ bar)
        AppKit.NSColor.colorWithRed_green_blue_alpha_(0.58, 0.40, 0.08, 1.0).set()
        s_bar = AppKit.NSBezierPath.bezierPath()
        s_bar.moveToPoint_(AppKit.NSMakePoint(cx, cy - 2.2))
        s_bar.lineToPoint_(AppKit.NSMakePoint(cx, cy + 2.2))
        s_bar.setLineWidth_(0.7)
        s_bar.stroke()

        # 4. Sparkle twinkle
        twinkle = (tick % 30) < 8
        if twinkle:
            AppKit.NSColor.whiteColor().set()
            AppKit.NSBezierPath.bezierPathWithOvalInRect_(AppKit.NSMakeRect(cx + 1.2, cy + 1.2, 1.5, 1.5)).fill()
