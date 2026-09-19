import unittest
from pathlib import Path


class PlanilhaDeterministicOpenTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_abertura_e_interacao_estao_na_implementacao_canonica(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        patch = (self.root / "patch.py").read_text(encoding="utf-8")
        self.assertIn("def abrir_planilha(self, dados_iniciais=None):", interface)
        self.assertIn('self._planilha_implementacao = "grade-virtual-29926"', interface)
        self.assertIn('tree=VirtualGridTree(', interface)
        self.assertIn('tree.bind("<ButtonPress-1>", self._planilha_clicar_celula, add="+")', interface)
        self.assertIn('tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")', interface)
        self.assertIn('tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")', interface)
        self.assertIn("self._planilha_desenhar_borda()", interface)
        self.assertNotIn("def _abrir_planilha_2991", patch)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_297", patch)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_2991", patch)

    def test_virtualizacao_substitui_povoamento_incremental(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def abrir_planilha")
        end = interface.index("    def _planilha_stage9_get_grid_state", start)
        block = interface[start:end]
        self.assertIn("VirtualGridTree(", block)
        self.assertIn("value_provider=", block)
        self.assertIn('self._planilha_implementacao = "grade-virtual-29926"', block)
        self.assertNotIn("def _povoar_lote():", block)
        self.assertNotIn("for i in range(300):", block)
        self.assertNotIn("fim = min(10000, inicio + 500)", block)
        self.assertNotIn("tree.insert(", block)

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
