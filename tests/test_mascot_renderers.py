import unittest
from ui.common.mascot_catalog import ANIMALS, ACCESSORIES

class TestMascotRenderers(unittest.TestCase):
    def test_macos_modular_renderer_all_animals_and_ticks(self):
        try:
            import AppKit
        except ImportError:
            self.skipTest("AppKit not available on this platform")

        from ui.macos.banner.renderers.modular_renderer import ModularPilotRenderer

        size = AppKit.NSMakeSize(120, 120)
        image = AppKit.NSImage.alloc().initWithSize_(size)
        image.lockFocus()

        try:
            for animal, _ in ANIMALS:
                # Test with default outfit, student outfit, work/agent, concert, tuxedo, and banker outfits
                for outfit in ("aviator", "student", "agent", "concert", "tuxedo", "banker"):
                    renderer = ModularPilotRenderer(
                        animal=animal,
                        outfit=outfit,
                        accessories=("sunglasses", "bow_tie", "badge", "earpiece", "headphones", "tuxedo", "top_hat", "banker_visor", "gold_coin")
                    )
                    # Tick 10 (open eyes) and Tick 76 (blinking eye window)
                    for tick in (10, 76):
                        try:
                            renderer.draw_pilot(60, 60, tick)
                        except Exception as e:
                            self.fail(f"ModularPilotRenderer failed for animal='{animal}', outfit='{outfit}', tick={tick}: {e}")
        finally:
            image.unlockFocus()

    def test_linux_qt_modular_renderer_all_animals(self):
        try:
            from PyQt6.QtGui import QImage, QPainter
            from ui.linux.banner.renderers.modular_renderer import QtModularRenderer
        except (ImportError, ModuleNotFoundError):
            self.skipTest("PyQt6 not available in this environment")

        img = QImage(120, 120, QImage.Format.Format_ARGB32)
        p = QPainter(img)
        try:
            for animal, _ in ANIMALS:
                for outfit in ("aviator", "student", "agent", "concert", "tuxedo", "banker"):
                    renderer = QtModularRenderer(
                        animal=animal,
                        outfit=outfit,
                        accessories=("sunglasses", "bow_tie", "badge", "earpiece", "headphones", "tuxedo", "top_hat", "banker_visor", "gold_coin")
                    )
                    for tick in (10, 76):
                        try:
                            renderer.draw_pilot(p, 60, 60, tick)
                        except Exception as e:
                            self.fail(f"QtModularRenderer failed for animal='{animal}', outfit='{outfit}', tick={tick}: {e}")
        finally:
            p.end()

    def test_perry_fedora_and_concert_rules(self):
        from ui.common.mascot_catalog import normalize_accessories

        # 1. Perry the Platypus always has fedora, never top_hat
        perry_acc = normalize_accessories(outfit="agent", animal="platypus")
        self.assertIn("fedora", perry_acc)
        self.assertNotIn("top_hat", perry_acc)

        perry_tux = normalize_accessories(outfit="tuxedo", animal="platypus")
        self.assertIn("fedora", perry_tux)
        self.assertNotIn("top_hat", perry_tux)

        # 2. Non-platypus animals in work/agent/tuxedo NEVER get fedora; they get top_hat & tuxedo
        for non_perry in ("penguin", "duck", "owl", "bunny", "fox", "squirrel", "panda"):
            work_acc = normalize_accessories(outfit="agent", animal=non_perry)
            self.assertNotIn("fedora", work_acc)
            self.assertIn("top_hat", work_acc)
            self.assertIn("tuxedo", work_acc)

            tux_acc = normalize_accessories(outfit="tuxedo", animal=non_perry)
            self.assertNotIn("fedora", tux_acc)
            self.assertIn("top_hat", tux_acc)
            self.assertIn("tuxedo", tux_acc)

        # 3. Concert outfit always includes headphones
        concert_acc = normalize_accessories(outfit="concert", animal="fox")
        self.assertIn("headphones", concert_acc)

        # 4. Banker outfit always includes banker_visor and gold_coin
        banker_acc = normalize_accessories(outfit="banker", animal="duck")
        self.assertIn("banker_visor", banker_acc)
        self.assertIn("gold_coin", banker_acc)


if __name__ == "__main__":
    unittest.main()
