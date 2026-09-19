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
        self.assertNotIn("def _abrir_planilha_2991", patch)
        self.assertNotIn("App._planilha_clicar_celula = _planilha_clicar_celula_2991", patch)
        self.assertNotIn("App._planilha_arrastar_selecao = _planilha_arrastar_selecao_2991", patch)
        self.assertNotIn("App._planilha_soltar_selecao = _planilha_soltar_selecao_2991", patch)
        self.assertIn('self._planilha_implementacao = "grade-final-29922"', interface)
        self.assertIn('tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")', interface)
        self.assertIn('tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")', interface)
        self.assertIn("self.abrir_planilha(cells)", interface)



    def test_atalhos_de_edicao_da_grade_estao_robustos(self):
        interface = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        for binding in (
            'tree.bind("<Control-KeyPress-z>", self._planilha_atalho_desfazer, add="+")',
            'tree.bind("<Control-KeyPress-y>", self._planilha_atalho_refazer, add="+")',
            'tree.bind("<Control-KeyPress-a>", self._planilha_atalho_selecionar_tudo, add="+")',
            'tree.bind("<Control-KeyPress-c>", self._planilha_atalho_copiar, add="+")',
            'tree.bind("<Control-KeyPress-x>", self._planilha_recortar, add="+")',
            'tree.bind("<Delete>", self._planilha_atalho_excluir, add="+")',
            'tree.bind("<BackSpace>", self._planilha_atalho_excluir, add="+")',
            'tree.bind("<Control-KeyPress-v>", self._planilha_atalho_colar, add="+")',
        ):
            self.assertIn(binding, interface)
        self.assertIn("def _planilha_atalho_desfazer", interface)
        self.assertIn("def _planilha_atalho_refazer", interface)
        self.assertIn("def _planilha_atalho_selecionar_tudo", interface)
        self.assertIn("def _planilha_atalho_copiar", interface)
        self.assertIn("def _planilha_recortar", interface)
        self.assertIn("def _planilha_atalho_excluir", interface)
        self.assertIn("def _planilha_tem_entry_em_foco", interface)

    def test_ctrl_v_tem_fallback_local_global_e_virtual(self):
        interface = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        self.assertIn('tree.bind("<Control-KeyPress-v>", self._planilha_colar_teclado, add="+")', interface)
        self.assertIn('tree.bind("<Control-KeyPress-V>", self._planilha_colar_teclado, add="+")', interface)
        self.assertIn('tree.bind("<<Paste>>", self._planilha_colar_teclado, add="+")', interface)
        self.assertIn('self.app.bind_all(\n                "<Control-KeyPress-v>"', interface)
        self.assertIn('self.app.bind_all(\n                "<Control-KeyPress-V>"', interface)
        self.assertIn("def _planilha_foco_pertence_a_grade(self):", interface)
        self.assertIn("def _planilha_colar_entry(self, event=None):", interface)

    def test_entry_da_edicao_tem_paste_proprio(self):
        interface = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def _planilha_editar_iid")
        end = interface.index("def _planilha_copiar", start)
        block = interface[start:end]
        self.assertIn('entry.bind("<Control-KeyPress-v>", self._planilha_colar_entry, add="+")', block)
        self.assertIn('entry.bind("<<Paste>>", self._planilha_colar_entry, add="+")', block)

    def test_snapshot_historico_reutiliza_a_mesma_abertura(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _abrir_snapshot_historico")
        end = source.index("def _fechar_historico_planilha", start)
        block = source[start:end]
        self.assertIn("self.abrir_planilha(cells)", block)


if __name__ == "__main__":
    unittest.main()
