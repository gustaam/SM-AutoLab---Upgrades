import unittest
from pathlib import Path

import main


class TooltipRegressionTests(unittest.TestCase):
    class _FakeButton:
        def __init__(self, value):
            self.value = value

        def cget(self, name):
            if name != "text":
                raise KeyError(name)
            return self.value

    def test_none_nao_vira_tooltip_literal(self):
        self.assertIsNone(main._stage7_tooltip_text(self._FakeButton(None)))

    def test_texto_vazio_nao_cria_tooltip(self):
        self.assertIsNone(main._stage7_tooltip_text(self._FakeButton("   ")))

    def test_botao_conhecido_tem_descricao(self):
        self.assertEqual(
            main._stage7_tooltip_text(self._FakeButton("Iniciar")),
            "Inicia a automação com os códigos selecionados.",
        )

    def test_codigo_com_digitos_tem_descricao_de_copia(self):
        self.assertEqual(
            main._stage7_tooltip_text(self._FakeButton("ABC123")),
            "Clique para copiar este código.",
        )

    def test_texto_generico_nao_recebe_descricao_inventada(self):
        self.assertIsNone(main._stage7_tooltip_text(self._FakeButton("Botão genérico")))

    def test_menu_aparencia_tem_handler_para_filhos_internos(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("_iterar_descendentes_ui(aparencia)", block)
        self.assertIn("_abrir_aparencia_por_clique", block)
        self.assertIn('bind("<Button-1>", _abrir_aparencia_por_clique', block)

    def test_menu_aparencia_abre_por_hover(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("_abrir_aparencia_por_hover", block)
        self.assertIn("_garantir_menu_aparencia_aberto", block)
        self.assertIn('bind("<Enter>", _abrir_aparencia_por_hover', block)

    def test_historico_de_erros_tem_tooltip(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        self.assertIn('"histórico de erros":', source)

    def test_iniciar_preserva_legenda(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        self.assertIn('text="▶  Iniciar"', source)

    def test_tooltip_cobre_filhos_internos_do_ctkbutton(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        start = source.index("class _SMAutoLabTooltip:")
        end = source.index("def _stage7_tooltip_text", start)
        block = source[start:end]
        self.assertIn("def _iter_widget_tree", block)
        self.assertIn("def _bind_widget_tree", block)
        self.assertIn('child.bind("<Enter>"', block)
        self.assertIn('child.bind("<Leave>"', block)
        self.assertIn("HIDE_GRACE_MS", block)
        self.assertIn("_pointer_inside_button", block)


if __name__ == "__main__":
    unittest.main()
