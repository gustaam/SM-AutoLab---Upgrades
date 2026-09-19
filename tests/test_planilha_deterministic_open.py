import unittest
from pathlib import Path


class PlanilhaDeterministicOpenTests(unittest.TestCase):
    def test_abertura_instala_bindings_sem_depender_de_after_idle(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "patch.py").read_text(encoding="utf-8")
        start = source.index("def _abrir_planilha_2991")
        end = source.index("def _renomear_historico_ui_2991", start)
        block = source[start:end]
        self.assertIn("_install_planilha_bindings_2991(self)", block)
        self.assertIn("_planilha_finalizar_inicializacao_visual_2991", block)
        self.assertIn("self._planilha_desenhar_borda()", block)
        self.assertIn("self._planilha_desenhar_cabecalho_linhas()", block)

    def test_rotina_de_abertura_tem_segunda_passada_visual(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "patch.py").read_text(encoding="utf-8")
        self.assertIn("def _planilha_finalizar_inicializacao_visual_2991", source)
        self.assertIn("self.app.after_idle(lambda: _planilha_finalizar_inicializacao_visual_2991(self))", source)


if __name__ == "__main__":
    unittest.main()
