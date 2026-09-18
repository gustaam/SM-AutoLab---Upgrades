import unittest
from pathlib import Path

import main


class DashboardStage3Tests(unittest.TestCase):
    def test_dashboard_stage3_marker_and_entry_point(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_DASHBOARD_29917", source)
        self.assertIn("def install_ui_dashboard_29917", source)
        self.assertIn("install_ui_dashboard_29917(App)", source)
        self.assertIn('setattr(App, "_selecionar_tema", theme_wrapper)', source)

    def test_dashboard_clamp_is_safe(self):
        self.assertEqual(main._dashboard_clamp(-1), 0.0)
        self.assertEqual(main._dashboard_clamp(0), 0.0)
        self.assertEqual(main._dashboard_clamp(0.42), 0.42)
        self.assertEqual(main._dashboard_clamp(2), 1.0)
        self.assertEqual(main._dashboard_clamp("invalido"), 0.0)

    def test_dashboard_layer_is_visual_only(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "main.py").read_text(encoding="utf-8")
        stage = source.split("SM_AUTOLAB_DASHBOARD_29917", 1)[1].split('if __name__ == "__main__":', 1)[0]
        self.assertNotIn("threading.Thread", stage)


if __name__ == "__main__":
    unittest.main()
