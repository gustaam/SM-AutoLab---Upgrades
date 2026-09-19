import unittest
from pathlib import Path


class ConfigMenuPositionTests(unittest.TestCase):
    def test_menu_configuracoes_e_ancorado_abaixo_do_botao(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _reposicionar_menus")
        end = source.index("def _fixar_menu_configuracoes", start)
        block = source[start:end]
        self.assertIn("menu_x = bx", block)
        self.assertNotIn("bx - 40", block)
        self.assertIn("self._menu_config.place_configure(", block)


if __name__ == "__main__":
    unittest.main()
