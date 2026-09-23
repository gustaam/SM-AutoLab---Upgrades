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
        app._historico_arquivo_legado = root / "historico_legado.json"
        app._erros_arquivo = root / "historico_erros.json"
        app._historico_execucoes = []
        app._execucao_atual = None
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

    def test_limpar_historico_nao_reidrata_arquivo_legado(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = self._app_without_ui(root)
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app._historico_arquivo.write_text(
                json.dumps({
                    "version": 4,
                    "historico_execucoes": [
                        {"id": "antiga", "inicio": agora, "erros": 1}
                    ],
                }),
                encoding="utf-8",
            )
            app._historico_arquivo_legado.write_text(
                json.dumps({
                    "historico_execucoes": [
                        {"id": "legada", "inicio": agora, "erros": 3}
                    ],
                }),
                encoding="utf-8",
            )
            app._erros_arquivo.write_text(
                json.dumps({"erros": ["123"]}),
                encoding="utf-8",
            )
            app._historico_execucoes = [
                {"id": "antiga", "inicio": agora, "erros": 1}
            ]
            app._erros_codigos = ["123"]
            app.atualizar_status = lambda *_args: None
            app._add_activity = lambda *_args: None

            with patch("interface.messagebox.askyesno", return_value=True):
                app._limpar_historico()

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            erros = json.loads(app._erros_arquivo.read_text(encoding="utf-8"))
            self.assertEqual(dados["historico_execucoes"], [])
            self.assertIsNone(dados["execucao_atual"])
            self.assertEqual(erros["erros"], [])
            self.assertFalse(app._historico_arquivo_legado.exists())

    def test_carregamento_nao_reidrata_backup_de_historico_limpo(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = self._app_without_ui(root)
            app._historico_arquivo.write_text(
                json.dumps({
                    "version": 4,
                    "historico_execucoes": [],
                    "execucao_atual": None,
                }),
                encoding="utf-8",
            )
            app._historico_arquivo.with_name(
                app._historico_arquivo.name + ".bak"
            ).write_text(
                json.dumps({
                    "version": 3,
                    "historico_execucoes": [
                        {"id": "apagada", "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "erros": 2}
                    ],
                }),
                encoding="utf-8",
            )
            app._historico_arquivo_legado.write_text(
                json.dumps({
                    "historico_execucoes": [
                        {"id": "legada", "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "erros": 4}
                    ],
                }),
                encoding="utf-8",
            )

            app._carregar_estado_persistente()

            self.assertEqual(app._historico_execucoes, [])
            self.assertFalse(
                app._historico_arquivo.with_name(app._historico_arquivo.name + ".bak").exists()
            )
            self.assertFalse(app._historico_arquivo_legado.exists())

    def test_limpar_historico_remove_backups_residuais(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            app = self._app_without_ui(root)
            app._historico_execucoes = [
                {"id": "antiga", "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "erros": 1}
            ]
            app._erros_codigos = ["ABC123"]
            historico_backup = app._historico_arquivo.with_name(
                app._historico_arquivo.name + ".bak"
            )
            erros_backup = app._erros_arquivo.with_name(
                app._erros_arquivo.name + ".bak"
            )
            historico_backup.parent.mkdir(parents=True, exist_ok=True)
            historico_backup.write_text("{}\n", encoding="utf-8")
            erros_backup.write_text("{}\n", encoding="utf-8")
            app.atualizar_status = lambda *_args: None
            app._add_activity = lambda *_args: None

            with patch("interface.messagebox.askyesno", return_value=True):
                app._limpar_historico()

            self.assertFalse(historico_backup.exists())
            self.assertFalse(erros_backup.exists())

    def test_finalizacao_consolida_codigos_de_erro_de_todas_as_fontes(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            app._execucao_atual = {
                "id": "consolidada",
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Em andamento",
                "erros": 2,
                "codigos_erros": ["AAA"],
            }
            app._codigos_erros_execucao = ["BBB"]
            resultado = SimpleNamespace(
                total_planejado=2,
                sucessos=0,
                erros=2,
                processados=2,
                codigos_erros=["CCC"],
                itens=[
                    SimpleNamespace(status="Erro", codigo="DDD"),
                    {"status": "Erro", "codigo": "EEE"},
                ],
            )

            app._finalizar_historico_execucao(resultado)

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            registro = dados["historico_execucoes"][0]
            self.assertEqual(
                registro["codigos_erros"],
                ["BBB", "AAA", "CCC", "DDD", "EEE"],
            )
            self.assertEqual(registro["erros"], 2)

    def test_execucao_atual_recente_e_codigos_com_erro_sao_persistidos(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            app._execucao_atual = {
                "id": "recente",
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Em andamento",
                "erros": 1,
                "codigos_erros": ["ABC123"],
            }

            app._salvar_estado_persistente()

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            self.assertEqual(dados["execucao_atual"]["id"], "recente")
            self.assertEqual(dados["execucao_atual"]["codigos_erros"], ["ABC123"])

    def test_carregamento_recupera_execucao_atual_recente(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            app._execucao_atual = {
                "id": "recente",
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Em andamento",
                "erros": 1,
                "codigos_erros": ["ABC123"],
            }
            app._salvar_estado_persistente()

            app2 = self._app_without_ui(Path(temp))
            app2._carregar_estado_persistente()

            self.assertIsNotNone(app2._execucao_atual)
            self.assertEqual(app2._execucao_atual["id"], "recente")
            self.assertEqual(app2._execucao_atual["codigos_erros"], ["ABC123"])

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
