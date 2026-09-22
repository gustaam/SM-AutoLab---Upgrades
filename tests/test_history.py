# Testes de histórico persistente e retomada.

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from interface import App


class HistoryPersistenceTests(unittest.TestCase):
    def _app_without_ui(self, root: Path):
        app = App.__new__(App)
        app._historico_arquivo = root / "historico.json"
        app._historico_execucoes = []
        app._erros_codigos = []
        app._tema = "system"
        app._restaurar_historico_na_tela = lambda: None
        app._atualizar_contador_arquivos = lambda: None
        return app

    def test_finalizacao_preserva_execucao_com_mais_de_60_dias(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = self._app_without_ui(root)
            antiga = {
                "id": "antiga",
                "inicio": (datetime.now() - timedelta(days=61)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Concluída",
                "codigos_erros": [],
            }
            app._historico_execucoes = [antiga]
            app._execucao_atual = {
                "id": "nova",
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "planilha": "Planilha interna",
                "pagina": 1,
                "inicio_indice": 1,
            }
            resultado = SimpleNamespace(
                total_planejado=1,
                sucessos=1,
                erros=0,
                processados=1,
                itens=[],
            )

            app._finalizar_historico_execucao(resultado)

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            ids = {item["id"] for item in dados["historico_execucoes"]}
            self.assertEqual(ids, {"antiga", "nova"})

    def test_falha_preserva_execucao_com_mais_de_60_dias(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = self._app_without_ui(root)
            antiga = {
                "id": "antiga",
                "inicio": (datetime.now() - timedelta(days=61)).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Concluída",
                "codigos_erros": [],
            }
            app._historico_execucoes = [antiga]
            app._execucao_atual = {
                "id": "falha",
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "planilha": "Planilha interna",
                "pagina": 1,
                "inicio_indice": 1,
            }

            app._registrar_falha_historico("falha de teste")

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            ids = {item["id"] for item in dados["historico_execucoes"]}
            self.assertEqual(ids, {"antiga", "falha"})

    def test_falha_de_persistencia_e_registrada(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            with patch("interface.atomic_write_json", side_effect=OSError("disco cheio")),                  patch.object(app.__class__.__dict__.get("LOGGER", None) or __import__("interface").LOGGER, "exception") as logger:
                app._salvar_estado_persistente()

            logger.assert_called_once()


class LegacyResumeTests(unittest.TestCase):
    def test_retomada_legada_nao_acessa_widgets_removidos(self):
        app = App.__new__(App)
        app._closing = False
        app._retomada_dialogo_aberto = False
        app._execucao_atual = {
            "id": "legacy",
            "status": "Interrompida",
            "origem": "planilha_externa",
            "planilha": "antiga.xlsx",
            "pagina": 1,
            "inicio_indice": 1,
        }
        app.app = object()
        app._salvar_estado_persistente = lambda: None

        with patch("interface.messagebox.showwarning") as warning:
            app._verificar_retomada_pendente()

        self.assertEqual(app._execucao_atual["status"], "Retomada manual necessária")
        warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
