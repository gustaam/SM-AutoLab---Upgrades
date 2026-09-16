import unittest
from datetime import datetime

import main


class _FakeApp:
    _arquivos_datas_selecionadas = set()
    _arquivos_modo_selecao = False
    _arquivos_animacao_data = None

    def __init__(self, saved_at):
        self._saved_at = saved_at
        self.calls = []

    def _carregar_historico_planilhas(self):
        return [{"saved_at": self._saved_at, "id": "x"}]

    def _dados_arquivos_por_dia(self):
        return {datetime.fromisoformat(self._saved_at).date(): [{}]}

    def _atualizar_contador_selecao(self):
        self.calls.append("contador")

    def _desenhar_calendario_arquivos(self):
        self.calls.append("desenhar")

    def _animar_selecao_data(self, data):
        self.calls.append(("animar", data))

    def _cancelar_animacao_selecao(self):
        self.calls.append("cancelar")

    def _mostrar_planilhas_do_dia(self, data):
        self.calls.append(("abrir", data))


class HistoricoIlimitadoTests(unittest.TestCase):
    def test_data_antiga_nao_e_rejeitada_na_selecao(self):
        main._corrigir_historico_ilimitado()
        data = datetime(2025, 1, 15).date()
        app = _FakeApp("2025-01-15T12:00:00")
        app._arquivos_datas_selecionadas = set()
        app._toggle_data_selecionada(data)
        self.assertIn(data, app._arquivos_datas_selecionadas)

    def test_data_antiga_e_aberta_fora_da_janela_original(self):
        main._corrigir_historico_ilimitado()
        data = datetime(2025, 1, 15).date()
        app = _FakeApp("2025-01-15T12:00:00")
        class Event:
            x = 10
            y = 10
        class Canvas:
            def find_closest(self, x, y):
                return (1,)
            def gettags(self, item):
                return ("dia:2025-01-15",)
        app._arquivos_calendar_canvas = Canvas()
        app._clique_calendario_arquivos(Event())
        self.assertIn(("abrir", data), app.calls)


if __name__ == "__main__":
    unittest.main()
