import unittest

from patch_29910 import aplicar_patch_29910, _atualizar_contador_selecao_29910


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


class _FakeApp:
    _arquivos_datas_selecionadas = set()

    def __init__(self):
        self._arquivos_datas_selecionadas = set()
        self._arquivos_contador_selecao = _Label()
        self._arquivos_btn_apagar_selecionados = _Button()
        self.draw_calls = 0

    def _toggle_data_selecionada(self, data):
        if data in self._arquivos_datas_selecionadas:
            self._arquivos_datas_selecionadas.remove(data)
        else:
            self._arquivos_datas_selecionadas.add(data)

    def _toggle_modo_selecao_arquivos(self):
        if self._arquivos_datas_selecionadas:
            self._arquivos_datas_selecionadas.clear()

    def _desenhar_calendario_arquivos(self):
        self.draw_calls += 1

    def _renderizar_calendario_arquivos(self):
        self.draw_calls += 1

    def _mudar_mes_arquivos(self, _direcao):
        self.draw_calls += 1

    def _limpar_historico_planilhas(self):
        self._arquivos_datas_selecionadas.clear()


class TestContadorSelecao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        aplicar_patch_29910(_FakeApp)

    def test_contador_reflete_zero_e_multiplas_datas(self):
        app = _FakeApp()

        _atualizar_contador_selecao_29910(app)
        self.assertEqual(app._arquivos_contador_selecao.text, "0 Selecionadas")
        self.assertEqual(app._arquivos_btn_apagar_selecionados.state, "disabled")

        app._arquivos_datas_selecionadas.update({"2026-09-01", "2026-09-02"})
        _atualizar_contador_selecao_29910(app)
        self.assertEqual(app._arquivos_contador_selecao.text, "2 Selecionadas")
        self.assertEqual(app._arquivos_btn_apagar_selecionados.state, "normal")

    def test_clique_atualiza_contador_imediatamente(self):
        app = _FakeApp()

        app._toggle_data_selecionada("2026-09-01")
        self.assertEqual(app._arquivos_contador_selecao.text, "1 Selecionadas")

        app._toggle_data_selecionada("2026-09-02")
        self.assertEqual(app._arquivos_contador_selecao.text, "2 Selecionadas")

        app._toggle_data_selecionada("2026-09-01")
        self.assertEqual(app._arquivos_contador_selecao.text, "1 Selecionadas")

    def test_redesenhar_recalcula_contador(self):
        app = _FakeApp()
        app._arquivos_datas_selecionadas.update({"2026-09-01", "2026-09-02", "2026-09-03"})

        app._desenhar_calendario_arquivos()

        self.assertEqual(app.draw_calls, 1)
        self.assertEqual(app._arquivos_contador_selecao.text, "3 Selecionadas")

    def test_sair_do_modo_de_selecao_zera_contador(self):
        app = _FakeApp()
        app._arquivos_datas_selecionadas.update({"2026-09-01", "2026-09-02"})

        app._toggle_modo_selecao_arquivos()

        self.assertEqual(app._arquivos_contador_selecao.text, "0 Selecionadas")
        self.assertEqual(app._arquivos_btn_apagar_selecionados.state, "disabled")


if __name__ == "__main__":
    unittest.main()
