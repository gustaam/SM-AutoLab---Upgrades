import unittest

from patch_ui import _atualizar_contador_selecao_29910


class _Label:
    def __init__(self):
        self.text = None

    def configure(self, **kwargs):
        self.text = kwargs.get("text")


class _Button:
    def __init__(self):
        self.state = None

    def configure(self, **kwargs):
        self.state = kwargs.get("state")


class TestContadorSelecao(unittest.TestCase):
    def test_contador_reflete_estado_real(self):
        app = type("FakeApp", (), {})()
        app._arquivos_datas_selecionadas = set()
        app._arquivos_contador_selecao = _Label()
        app._arquivos_btn_apagar_selecionados = _Button()
        _atualizar_contador_selecao_29910(app)
        self.assertEqual(app._arquivos_contador_selecao.text, "0 Selecionadas")
        self.assertEqual(app._arquivos_btn_apagar_selecionados.state, "disabled")
        app._arquivos_datas_selecionadas.update({1, 2})
        _atualizar_contador_selecao_29910(app)
        self.assertEqual(app._arquivos_contador_selecao.text, "2 Selecionadas")
        self.assertEqual(app._arquivos_btn_apagar_selecionados.state, "normal")


if __name__ == "__main__":
    unittest.main()
