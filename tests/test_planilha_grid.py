import unittest
from pathlib import Path


class PlanilhaGridSelectionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_grade_visual_e_selecao_estao_na_camada_final(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        patch = (self.root / "patch.py").read_text(encoding="utf-8")
        for marker in (
            "def _stage9_desenhar_grade",
            "def _stage9_get_visible_rows",
            "def _stage9_desenhar_borda",
            "_planilha_celulas_selecionadas",
        ):
            self.assertIn(marker, source)
        self.assertIn("<B1-Motion>", patch)
        self.assertIn("<ButtonRelease-1>", patch)

    def test_grade_e_reutilizavel_e_nao_percorre_10000_linhas_para_desenho(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        start = source.index("def _stage9_desenhar_grade")
        end = source.index("def _stage9_limpar_borda", start)
        block = source[start:end]
        self.assertIn("_stage9_get_visible_rows(tree)", block)
        self.assertNotIn("range(10000)", block)

    def test_selecao_multipla_tem_moldura_por_celula_em_selecoes_pequenas(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        start = source.index("def _stage9_desenhar_borda")
        end = source.index("def install_ui_grade_29922", start)
        block = source[start:end]
        self.assertIn("len(normalized) <= 250", block)
        self.assertIn("segmentos.extend", block)
        self.assertIn("frame.lift()", block)


if __name__ == "__main__":
    unittest.main()
