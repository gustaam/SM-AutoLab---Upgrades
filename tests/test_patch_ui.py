import unittest

from patch_ui import _remover_instrucao_ctrl_clique


class _Widget:
    def __init__(self, text="", children=None):
        self._text = text
        self._children = list(children or [])
        self.destroyed = False

    def winfo_children(self):
        return self._children

    def cget(self, name):
        if name != "text":
            raise ValueError(name)
        return self._text

    def destroy(self):
        self.destroyed = True


class _App:
    def __init__(self, window):
        self._planilha_historico_window = window


class TestPatchUI(unittest.TestCase):
    def test_remove_instrucao_ctrl_clique(self):
        alvo = _Widget("Ctrl + clique para selecionar várias datas")
        outro = _Widget("Arquivos")
        window = _Widget(children=[outro, alvo])
        app = _App(window)

        _remover_instrucao_ctrl_clique(app)

        self.assertTrue(alvo.destroyed)
        self.assertFalse(outro.destroyed)


if __name__ == "__main__":
    unittest.main()
