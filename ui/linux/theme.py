from PyQt6.QtGui import QColor
from ui.common.theme import CatppuccinMocha, PILOT_THEME_COLORS

class Theme:
    """Catppuccin Mocha Color Palette for Linux PyQt6."""
    # Dark Base Surfaces
    CRUST = QColor(CatppuccinMocha.CRUST_HEX)
    MANTLE = QColor(CatppuccinMocha.MANTLE_HEX)
    BASE = QColor(CatppuccinMocha.BASE_HEX)
    SURFACE0 = QColor(CatppuccinMocha.SURFACE0_HEX)
    SURFACE1 = QColor(CatppuccinMocha.SURFACE1_HEX)
    SURFACE2 = QColor(CatppuccinMocha.SURFACE2_HEX)
    OVERLAY0 = QColor(CatppuccinMocha.OVERLAY0_HEX)
    OVERLAY1 = QColor(CatppuccinMocha.OVERLAY1_HEX)
    OVERLAY2 = QColor(CatppuccinMocha.OVERLAY2_HEX)

    # Typography & Text
    TEXT = QColor(CatppuccinMocha.TEXT_HEX)
    SUBTEXT1 = QColor(CatppuccinMocha.SUBTEXT1_HEX)
    SUBTEXT0 = QColor(CatppuccinMocha.SUBTEXT0_HEX)

    # Accent Colors
    MAUVE = QColor(CatppuccinMocha.MAUVE_HEX)
    BLUE = QColor(CatppuccinMocha.BLUE_HEX)
    SAPPHIRE = QColor(CatppuccinMocha.SAPPHIRE_HEX)
    SKY = QColor(CatppuccinMocha.SKY_HEX)
    TEAL = QColor(CatppuccinMocha.TEAL_HEX)
    GREEN = QColor(CatppuccinMocha.GREEN_HEX)
    YELLOW = QColor(CatppuccinMocha.YELLOW_HEX)
    PEACH = QColor(CatppuccinMocha.PEACH_HEX)
    MAROON = QColor(CatppuccinMocha.MAROON_HEX)
    RED = QColor(CatppuccinMocha.RED_HEX)
    FLAMINGO = QColor(CatppuccinMocha.FLAMINGO_HEX)
    ROSEWATER = QColor(CatppuccinMocha.ROSEWATER_HEX)
    LAVENDER = QColor(CatppuccinMocha.LAVENDER_HEX)

    # Pilot mappings
    PILOT_COLORS = PILOT_THEME_COLORS

    @classmethod
    def get_color(cls, name: str, alpha: int = 255) -> QColor:
        color = getattr(cls, name.upper(), cls.TEXT)
        c = QColor(color)
        c.setAlpha(alpha)
        return c

    @classmethod
    def rgba_str(cls, qcolor: QColor, alpha: float = 1.0) -> str:
        """Returns css rgba(r, g, b, a) string."""
        return f"rgba({qcolor.red()}, {qcolor.green()}, {qcolor.blue()}, {alpha:.2f})"


def get_asset_path(filename: str) -> str:
    """Resolves asset path from workspace or system package directory."""
    import os
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidate = os.path.join(root_dir, "assets", filename)
    if os.path.exists(candidate):
        return candidate
    opt_candidate = os.path.join("/opt", "flightdeck", "assets", filename)
    if os.path.exists(opt_candidate):
        return opt_candidate
    return candidate


def get_combo_box_qss(bg_color: str = "#313244", min_width: int = 150) -> str:
    """Returns standardized Catppuccin Mocha stylesheet for QComboBox including dropdown popup and arrow."""
    arrow_path = get_asset_path("chevron_down.svg").replace("\\", "/")
    return f"""
        QComboBox {{
            background-color: {bg_color};
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 6px;
            padding: 3px 26px 3px 10px;
            font-size: 11.5px;
            min-width: {min_width}px;
        }}
        QComboBox:hover {{
            border-color: #89b4fa;
            background-color: #363a4f;
        }}
        QComboBox:focus {{
            border-color: #cba6f7;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: none;
        }}
        QComboBox::down-arrow {{
            image: url("{arrow_path}");
            width: 11px;
            height: 11px;
            margin-right: 8px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #1e1e2e;
            color: #cdd6f4;
            selection-background-color: #45475a;
            selection-color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 8px;
            padding: 4px;
            outline: 0px;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px 10px;
            border-radius: 4px;
            min-height: 24px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: #313244;
            color: #cdd6f4;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #45475a;
            color: #cdd6f4;
        }}
    """


def get_menu_qss() -> str:
    """Returns standardized Catppuccin Mocha stylesheet for QMenu and QMenuBar."""
    return """
        QMenuBar {
            background-color: #11111b;
            color: #cdd6f4;
            border-bottom: 1px solid #313244;
            padding: 2px 8px;
            font-size: 12px;
        }
        QMenuBar::item {
            background: transparent;
            padding: 4px 10px;
            border-radius: 6px;
            color: #cdd6f4;
        }
        QMenuBar::item:selected {
            background-color: #313244;
            color: #89b4fa;
        }
        QMenuBar::item:pressed {
            background-color: #45475a;
        }
        QMenu {
            background-color: #181825;
            color: #cdd6f4;
            border: 1px solid #45475a;
            border-radius: 8px;
            padding: 6px;
        }
        QMenu::item {
            background-color: transparent;
            color: #cdd6f4;
            padding: 6px 28px 6px 14px;
            border-radius: 6px;
            font-size: 12px;
        }
        QMenu::item:selected {
            background-color: #313244;
            color: #89b4fa;
        }
        QMenu::item:disabled {
            color: #585b70;
        }
        QMenu::separator {
            height: 1px;
            background-color: #313244;
            margin: 4px 6px;
        }
        QMenu::indicator {
            width: 14px;
            height: 14px;
            margin-left: 6px;
        }
    """
