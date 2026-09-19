import unittest
from pathlib import Path


class StatusIndicatorTests(unittest.TestCase):
    def test_pronto_mantem_pulso_verde(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('self._status_text_base == "Pronto"', source)
        self.assertIn("self._iniciar_pisca_status()", source)


if __name__ == "__main__":
    unittest.main()
