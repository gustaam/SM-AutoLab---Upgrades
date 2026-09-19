import unittest
from pathlib import Path


class PlanilhaOpenPathTests(unittest.TestCase):
    def test_abrir_planilha_tem_uma_unica_implementacao(self):
        root = Path(__file__).resolve().parents[1]
        interface = (root / "interface.py").read_text(encoding="utf-8")
        main = (root / "main.py").read_text(encoding="utf-8")
        patch = (root / "patch.py").read_text(encoding="utf-8")

        self.assertEqual(interface.count("    def abrir_planilha(self, dados_iniciais=None):"), 1)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_297", patch)
        self.assertNotIn("App.abrir_planilha = open_planilha_wrapper", main)
        self.assertIn("self.abrir_planilha(cells)", interface)

    def test_snapshot_historico_reutiliza_a_mesma_abertura(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _abrir_snapshot_historico")
        end = source.index("def _fechar_historico_planilha", start)
        block = source[start:end]
        self.assertIn("self.abrir_planilha(cells)", block)


if __name__ == "__main__":
    unittest.main()
