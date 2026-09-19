import unittest
from pathlib import Path


class PlanilhaDeterministicOpenTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_abertura_e_interacao_estao_na_implementacao_canonica(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        patch = (self.root / "patch.py").read_text(encoding="utf-8")
        self.assertIn("def abrir_planilha(self, dados_iniciais=None):", interface)
        self.assertIn('self._planilha_implementacao = "grade-final-29922"', interface)
        self.assertIn('tree.bind("<ButtonPress-1>", self._planilha_clicar_celula, add="+")', interface)
        self.assertIn('tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")', interface)
        self.assertIn('tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")', interface)
        self.assertIn("self._planilha_desenhar_borda()", interface)
        self.assertNotIn("def _abrir_planilha_2991", patch)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_297", patch)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_2991", patch)

    def test_povoamento_redesenha_grade_depois_de_cada_lote(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def _povoar_lote():")
        end = interface.index("self._planilha_povoamento_job = tree.after(1, _povoar_lote)", start)
        block = interface[start:end]
        self.assertIn("self._planilha_desenhar_borda()", block)
        self.assertIn("self._planilha_desenhar_cabecalho_linhas()", block)
        self.assertIn("self._planilha_povoamento_proxima_linha = fim", block)

    def test_snapshot_historico_reutiliza_a_mesma_abertura(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def _mostrar_planilhas_do_dia")
        end = interface.index("def abrir_historico_planilha", start)
        block = interface[start:end]
        self.assertIn("command=lambda it=item: self._excluir_historico_planilha(it)", block)

        # A rota do snapshot deve convergir para abrir_planilha(), sem criar
        # um Treeview alternativo.
        snapshot_start = interface.index("def _preparar_planilha_do_dia")
        snapshot_end = interface.index("def _fechar_historico_planilha", snapshot_start)
        snapshot_block = interface[snapshot_start:snapshot_end]
        self.assertIn("self.abrir_planilha(cells)", snapshot_block)


if __name__ == "__main__":
    unittest.main()
