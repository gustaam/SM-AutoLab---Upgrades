import unittest
from types import SimpleNamespace

from interface import App


class FakeTree:
    def __init__(self, rows):
        self.rows = {str(k): list(v) for k, v in rows.items()}
        self._focus = next(iter(self.rows), "")

    def get_children(self):
        return tuple(self.rows)

    def focus(self):
        return self._focus

    def item(self, iid, mode=None, **kwargs):
        if "values" in kwargs:
            self.rows[str(iid)] = list(kwargs["values"])
        values = self.rows[str(iid)]
        return values if mode == "values" else {"values": tuple(values)}

    def __call__(self, iid, mode=None):
        return self.item(iid, mode)

    def set_focus(self, iid):
        self._focus = str(iid)


class PlanilhaBehaviorTests(unittest.TestCase):
    def _app(self, rows=None):
        app = App.__new__(App)
        app._planilha_data = {}
        app._planilha_undo = []
        app._planilha_redo = []
        app._planilha_tree = FakeTree(rows or {
            0: ("1", "ABC", "Item"),
            1: ("2", "DEF", "Outro"),
            2: ("", "", ""),
        })
        app._planilha_celulas_selecionadas = set()
        app._planilha_celula_ativa = None
        app._planilha_linhas_selecionadas = set()
        app._planilha_edit_entry = None
        app._changed = False
        app._planilha_atualizar_grade = lambda: None
        app._planilha_marcar_alteracao = lambda: setattr(app, "_changed", True)
        app._planilha_desenhar_borda = lambda: None
        app._planilha_fechar_edicao = lambda: None
        class Clipboard:
            value = ""
            def clipboard_get(self):
                return Clipboard.value
        app.app = Clipboard()
        return app

    def test_selecao_retangular_executa_operacao_real(self):
        app = self._app()
        self.assertEqual(
            App._planilha_retangulo_selecao(app, (1, 1), (2, 2)),
            {(1, 1), (1, 2), (2, 1), (2, 2)},
        )

    def test_copiar_e_colar_operam_sobre_armazenamento(self):
        app = self._app()
        app._planilha_data = {
            "0,0": "1", "0,1": "ABC", "0,2": "Item",
            "1,0": "2", "1,1": "DEF", "1,2": "Outro",
        }
        app._planilha_celulas_selecionadas = {(0, 0), (0, 1), (0, 2)}
        app._planilha_celula_ativa = ("1", 0)

        captured = {"text": None}
        app.app.clipboard_clear = lambda: None
        app.app.clipboard_append = lambda value: captured.__setitem__("text", value)

        self.assertEqual(App._planilha_copiar(app), "break")
        self.assertEqual(captured["text"], "1\tABC\tItem")

        app.app.clipboard_get = lambda: "9\tXYZ\tNovo"
        self.assertEqual(App._planilha_colar(app), "break")
        self.assertEqual(app._planilha_data["1,0"], "9")
        self.assertEqual(app._planilha_data["1,1"], "XYZ")
        self.assertEqual(app._planilha_data["1,2"], "Novo")
        self.assertTrue(app._changed)

    def test_limpar_e_undo_redo_restauram_estado(self):
        app = self._app()
        app._planilha_data = {"0,0": "1", "0,1": "ABC", "1,1": "DEF"}
        app._planilha_celulas_selecionadas = {(0, 1)}

        self.assertEqual(App._planilha_limpar_celulas_selecionadas(app), "break")
        self.assertNotIn("0,1", app._planilha_data)

        # O fluxo real de edição registra o estado antes da mutação.
        app._planilha_push_undo()
        app._planilha_data["0,1"] = "ABC"
        app._planilha_redo = []
        App._planilha_desfazer(app)
        self.assertNotIn("0,1", app._planilha_data)

        App._planilha_refazer(app)
        self.assertEqual(app._planilha_data["0,1"], "ABC")

    def test_contador_e_extracao_de_senhas_usam_dados_reais(self):
        app = self._app()
        app._planilha_data = {
            "0,0": "1",
            "0,1": "ABC",
            "2,1": "DEF",
            "4,2": "Item",
            "9,1": " ",
        }
        class Label:
            def __init__(self): self.text = None
            def configure(self, **kwargs): self.text = kwargs["text"]
        app._planilha_contador_label = Label()

        App._planilha_atualizar_contador(app)
        self.assertEqual(app._planilha_contador_label.text, "3 linhas preenchidas")
        self.assertEqual(App._extrair_codigos_planilha(app), ["ABC", "DEF"])

    def test_selecionar_tudo_seleciona_apenas_celulas_preenchidas(self):
        app = self._app()
        app._planilha_data = {"0,0": "1", "0,1": "ABC", "2,2": "Item"}
        App._planilha_selecionar_tudo(app)
        self.assertEqual(
            app._planilha_celulas_selecionadas,
            {(0, 0), (0, 1), (2, 2)},
        )


if __name__ == "__main__":
    unittest.main()
