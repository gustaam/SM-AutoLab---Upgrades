import unittest

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


if __name__ == "__main__":
    unittest.main()
