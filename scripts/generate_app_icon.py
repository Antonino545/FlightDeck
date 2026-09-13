"""
High-Fidelity Application Icon Generator for FlightDeck.
Renders the vintage biplane in the official Apple flight direction (climbing up-right)
on a solid dark squircle background (macOS & iOS Dark Mode style).
"""
import math
import os
import sys

def create_superellipse_path(QPainterPath, cx: float, cy: float, rx: float, ry: float, n: float = 4.6, steps: int = 720):
    """Generates a mathematically continuous G2 squircle / superellipse curve path."""
    path = QPainterPath()
    for i in range(steps + 1):
        theta = 2.0 * math.pi * i / steps
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        x = cx + rx * (1.0 if cos_t >= 0 else -1.0) * (abs(cos_t) ** (2.0 / n))
        y = cy + ry * (1.0 if sin_t >= 0 else -1.0) * (abs(sin_t) ** (2.0 / n))
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()
    return path


def create_app_icon_qt(output_path="assets/icon.png", size=1024, mode="dark"):
    from PyQt6.QtCore import Qt, QRectF, QPointF
    from PyQt6.QtGui import (
        QImage, QPainter, QPainterPath, QColor, QPen, QBrush
    )

    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    s = size / 512.0
    # Apple macOS Official Icon Grid: 824x824 squircle centered in 1024x1024 canvas (100px margins at 1024)
    margin = size * 0.0976
    w_sq = size - 2 * margin
    rx = w_sq / 2.0
    ry = w_sq / 2.0
    cx = size / 2.0
    cy = size / 2.0

    is_light = (mode == "light")

    # 1. Apple macOS Dock Subtle Drop Shadow (Guarantees depth on white and light backgrounds)
    shadow_alpha = 55 if is_light else 85
    shadow_path = create_superellipse_path(QPainterPath, cx, cy + 18 * s, rx, ry, n=4.6, steps=720)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(0, 0, 0, shadow_alpha)))
    p.fillPath(shadow_path, p.brush())

    # 2. Main Apple Squircle Background
    bg_path = create_superellipse_path(QPainterPath, cx, cy, rx, ry, n=4.6, steps=720)
    if is_light:
        # Ceramic White / Light Platinum
        p.setBrush(QBrush(QColor(246, 247, 250)))
    else:
        # Deep Solid Black / Graphite
        p.setBrush(QBrush(QColor(18, 18, 22)))
    p.fillPath(bg_path, p.brush())

    # 3. Apple HIG Perimeter Rim Stroke (Guarantees squircle contour is crisp on both black and white themes)
    if is_light:
        edge_pen = QPen(QColor(0, 0, 0, 24), 1.2 * s)
    else:
        edge_pen = QPen(QColor(255, 255, 255, 42), 1.2 * s)
    p.strokePath(bg_path, edge_pen)

    # Top specular highlight inside squircle
    top_bevel = create_superellipse_path(QPainterPath, cx, cy + 1.0 * s, rx - 1.2 * s, ry - 1.2 * s, n=4.6, steps=720)
    bevel_pen = QPen(QColor(255, 255, 255, 220 if is_light else 32), 1.0 * s)
    p.strokePath(top_bevel, bevel_pen)

    p.save()
    p.setClipPath(bg_path)

    # 4. Apple Direction: Climbing diagonally up and to the right (-35 degrees)
    p.save()
    p.translate(cx, cy)
    p.rotate(-35)

    plane_scale = 0.88
    plane_cx = 15.0 * s * plane_scale
    plane_cy = 0.0
    ps = s * plane_scale

    red_wing = QColor(228, 42, 55) if is_light else QColor(235, 60, 72)
    strut_color = QColor(55, 60, 75) if is_light else QColor(70, 74, 90)
    body_pen_color = QColor(40, 32, 28) if is_light else QColor(45, 35, 30)

    # Top Biplane Wing (behind fuselage)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(red_wing))
    top_wing = QPainterPath()
    top_wing.moveTo(plane_cx - 60 * ps, plane_cy - 46 * ps)
    top_wing.lineTo(plane_cx + 60 * ps, plane_cy - 46 * ps)
    top_wing.lineTo(plane_cx + 44 * ps, plane_cy - 33 * ps)
    top_wing.lineTo(plane_cx - 44 * ps, plane_cy - 33 * ps)
    top_wing.closeSubpath()
    p.fillPath(top_wing, p.brush())

    # Top wing crisp edge trim
    p.setPen(QPen(QColor(255, 255, 255, 240), 2.2 * ps))
    p.drawLine(QPointF(plane_cx - 60 * ps, plane_cy - 46 * ps), QPointF(plane_cx + 60 * ps, plane_cy - 46 * ps))
    p.setPen(Qt.PenStyle.NoPen)

    # Wing Struts
    strut_pen = QPen(strut_color, 2.5 * ps, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(strut_pen)
    p.drawLine(QPointF(plane_cx - 28 * ps, plane_cy - 33 * ps), QPointF(plane_cx - 24 * ps, plane_cy - 10 * ps))
    p.drawLine(QPointF(plane_cx + 28 * ps, plane_cy - 33 * ps), QPointF(plane_cx + 24 * ps, plane_cy - 10 * ps))
    p.setPen(Qt.PenStyle.NoPen)

    # Timone di Coda (Tail Rudder)
    p.setBrush(QBrush(red_wing))
    tail = QPainterPath()
    tail.moveTo(plane_cx - 110 * ps, plane_cy)
    tail.lineTo(plane_cx - 172 * ps, plane_cy - 72 * ps)
    tail.lineTo(plane_cx - 146 * ps, plane_cy)
    tail.closeSubpath()
    p.fillPath(tail, p.brush())

    # Tail fin crisp white chevron racing stripe
    tail_deco = QPainterPath()
    tail_deco.moveTo(plane_cx - 130 * ps, plane_cy - 12 * ps)
    tail_deco.lineTo(plane_cx - 152 * ps, plane_cy - 50 * ps)
    tail_deco.lineTo(plane_cx - 144 * ps, plane_cy - 50 * ps)
    tail_deco.lineTo(plane_cx - 124 * ps, plane_cy - 12 * ps)
    tail_deco.closeSubpath()
    p.setBrush(QBrush(QColor(255, 255, 255, 245)))
    p.fillPath(tail_deco, p.brush())

    # Fusoliera Vintage Crema / Avorio
    p.setBrush(QBrush(QColor(215, 192, 160) if is_light else QColor(218, 196, 165)))
    body_shade = QRectF(plane_cx - 128 * ps, plane_cy - 38 * ps, 226 * ps, 80 * ps)
    p.drawEllipse(body_shade)

    # Main ivory fuselage
    p.setBrush(QBrush(QColor(253, 246, 230) if is_light else QColor(252, 244, 225)))
    body_pen = QPen(body_pen_color, 4.4 * ps if is_light else 4.2 * ps)
    p.setPen(body_pen)
    body_rect = QRectF(plane_cx - 130 * ps, plane_cy - 50 * ps, 230 * ps, 90 * ps)
    p.drawEllipse(body_rect)

    # Striscia Rossa Racing sulla Fiancata
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(red_wing))
    p.drawRoundedRect(QRectF(plane_cx - 105 * ps, plane_cy - 8 * ps, 175 * ps, 16 * ps), 4 * ps, 4 * ps)

    # White pin-stripe accent on racing stripe
    p.setPen(QPen(QColor(255, 255, 255, 235), 1.8 * ps))
    p.drawLine(QPointF(plane_cx - 100 * ps, plane_cy), QPointF(plane_cx + 65 * ps, plane_cy))
    p.setPen(Qt.PenStyle.NoPen)

    # Cockpit & Sleek Aerodynamic Bubble Canopy
    canopy_rect = QRectF(plane_cx - 42 * ps, plane_cy - 62 * ps, 84 * ps, 64 * ps)
    canopy_bg = QColor(56, 150, 245) if is_light else QColor(116, 199, 236)
    p.setBrush(QBrush(canopy_bg))
    p.setPen(QPen(QColor(255, 255, 255, 240), 2.6 * ps))
    p.drawEllipse(canopy_rect)

    # Canopy inner cockpit depth
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor(16, 25, 38) if is_light else QColor(20, 30, 45)))
    p.drawEllipse(QRectF(plane_cx - 36 * ps, plane_cy - 44 * ps, 72 * ps, 42 * ps))

    # Flight deck artificial horizon / HUD line inside canopy
    hud_color = QColor(0, 220, 160) if is_light else QColor(166, 227, 161)
    hud_pen = QPen(hud_color, 2.0 * ps, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(hud_pen)
    p.drawLine(QPointF(plane_cx - 14 * ps, plane_cy - 22 * ps), QPointF(plane_cx + 14 * ps, plane_cy - 22 * ps))
    p.setPen(Qt.PenStyle.NoPen)

    # Canopy specular curved shine
    shine_path = QPainterPath()
    shine_path.moveTo(plane_cx - 22 * ps, plane_cy - 44 * ps)
    shine_path.quadTo(plane_cx, plane_cy - 56 * ps, plane_cx + 18 * ps, plane_cy - 46 * ps)
    shine_pen = QPen(QColor(255, 255, 255, 245), 2.8 * ps, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.strokePath(shine_path, shine_pen)

    # Ala Inferiore Vintage
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(red_wing))
    wing = QPainterPath()
    wing.moveTo(plane_cx - 50 * ps, plane_cy + 8 * ps)
    wing.lineTo(plane_cx + 50 * ps, plane_cy + 8 * ps)
    wing.lineTo(plane_cx + 20 * ps, plane_cy + 75 * ps)
    wing.lineTo(plane_cx - 30 * ps, plane_cy + 75 * ps)
    wing.closeSubpath()
    p.fillPath(wing, p.brush())

    # White tip trim on lower wing
    p.setPen(QPen(QColor(255, 255, 255, 240), 2.4 * ps))
    p.drawLine(QPointF(plane_cx - 30 * ps, plane_cy + 75 * ps), QPointF(plane_cx + 20 * ps, plane_cy + 75 * ps))
    p.setPen(Qt.PenStyle.NoPen)

    # Wingtip navigation strobe light (Sapphire)
    p.setBrush(QBrush(QColor(56, 189, 248) if is_light else QColor(116, 215, 255)))
    p.drawEllipse(QRectF(plane_cx + 16 * ps, plane_cy + 79 * ps, 7 * ps, 7 * ps))

    # Ogiva Anteriore (Dark nose cone)
    p.setBrush(QBrush(QColor(38, 42, 54) if is_light else QColor(42, 45, 58)))
    p.drawEllipse(QRectF(plane_cx + 95 * ps, plane_cy - 14 * ps, 26 * ps, 26 * ps))

    # Elica con Motion Blur Rotante (Contrast tuned for light/white and dark/black)
    if is_light:
        prop_pen_outer = QPen(QColor(80, 90, 110, 110), 9.0 * ps, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(prop_pen_outer)
        p.drawLine(QPointF(plane_cx + 108 * ps, plane_cy - 60 * ps), QPointF(plane_cx + 108 * ps, plane_cy + 60 * ps))
        prop_pen = QPen(QColor(255, 255, 255, 240), 4.5 * ps, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(prop_pen)
        p.drawLine(QPointF(plane_cx + 108 * ps, plane_cy - 56 * ps), QPointF(plane_cx + 108 * ps, plane_cy + 56 * ps))
    else:
        prop_pen = QPen(QColor(230, 235, 245, 225), 8.0 * ps, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(prop_pen)
        p.drawLine(QPointF(plane_cx + 108 * ps, plane_cy - 60 * ps), QPointF(plane_cx + 108 * ps, plane_cy + 60 * ps))

    p.restore()
    p.restore()
    p.end()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path)
    print(f"[OK] Icon ({mode}) successfully generated: {output_path} ({size}x{size})")


def generate_all_app_icons(base_dir="assets", size=1024):
    """Generates the full set of icons: dark, light, and default universal."""
    dark_path = os.path.join(base_dir, "icon_dark.png")
    light_path = os.path.join(base_dir, "icon_light.png")
    default_path = os.path.join(base_dir, "icon.png")

    create_app_icon_qt(dark_path, size=size, mode="dark")
    create_app_icon_qt(light_path, size=size, mode="light")
    # Universal default is the dark icon with luminous HIG rim, which stands out on both black & white
    create_app_icon_qt(default_path, size=size, mode="dark")


def create_app_icon(output_path="assets/icon.png", size=1024):
    base_dir = os.path.dirname(os.path.abspath(output_path))
    generate_all_app_icons(base_dir, size)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assets/icon.png"
    create_app_icon(out, 1024)
