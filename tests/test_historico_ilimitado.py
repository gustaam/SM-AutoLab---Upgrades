import unittest
from datetime import datetime
from types import SimpleNamespace

import main
from patch import aplicar_patch_ui


class HistoricoIlimitadoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        aplicar_patch_ui(main.App)
        main._corrigir_historico_ilimitado()

    def _fake_app(self, saved_at):
        app = object.__new__(main.App)
        app._saved_at = saved_at
        app.calls = []
        app._arquivos_datas_selecionadas = set()
        app._arquivos_modo_selecao = False
        app._arquivos_animacao_data = None

        app._carregar_historico_planilhas = lambda: [{"saved_at": saved_at, "id": "x"}]
        app._dados_arquivos_por_dia = lambda: {datetime.fromisoformat(saved_at).date(): [{}]}
        app._atualizar_contador_selecao = lambda: app.calls.append("contador")
        app._desenhar_calendario_arquivos = lambda: app.calls.append("desenhar")
        app._animar_selecao_data = lambda data: app.calls.append(("animar", data))
        app._cancelar_animacao_selecao = lambda: app.calls.append("cancelar")
        app._mostrar_planilhas_do_dia = lambda data: app.calls.append(("abrir", data))
        app._arquivos_calendar_canvas = None
        app.app = SimpleNamespace()
        return app

    def test_data_antiga_nao_e_rejeitada_na_selecao(self):
        data = datetime(2025, 1, 15).date()
        app = self._fake_app("2025-01-15T12:00:00")
        app._toggle_data_selecionada(data)
        self.assertIn(data, app._arquivos_datas_selecionadas)
        self.assertIn(("animar", data), app.calls)

    def test_data_antiga_e_aberta_fora_da_janela_original(self):
        data = datetime(2025, 1, 15).date()
        app = self._fake_app("2025-01-15T12:00:00")

        class Canvas:
            def find_closest(self, x, y):
                return (1,)

            def gettags(self, item):
                return ("dia:2025-01-15",)

        app._arquivos_calendar_canvas = Canvas()
        app._clique_calendario_arquivos(SimpleNamespace(x=10, y=10))
        self.assertIn(("abrir", data), app.calls)


if __name__ == "__main__":
    unittest.main()
