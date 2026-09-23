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
                "erros": 1,
                "codigos_erros": ["ABC123"],
            }
            resultado = SimpleNamespace(
                total_planejado=1,
                sucessos=0,
                erros=1,
                processados=1,
                codigos_erros=["ABC123"],
                erros_detalhes=[
                    {"numero": 1, "codigo": "ABC123", "erro": "falha", "horario": "10:00:00"}
                ],
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

    def test_detalhe_historico_renderiza_erros_em_frame_direto(self):
        source = Path(__file__).resolve().parents[1].joinpath("interface.py").read_text(encoding="utf-8")
        start = source.index("def _preencher_detalhe_pasta")
        end = source.index("def _limpar_historico", start)
        block = source[start:end]
        self.assertIn("erros_area = ctk.CTkFrame(", block)
        self.assertNotIn("erros_area = ctk.CTkScrollableFrame(", block)

    def test_historico_reconhece_detalhes_de_nao_executados(self):
        execucao = {
            "status": "Concluída",
            "erros": 0,
            "codigos_erros": [],
            "erros_detalhes": [
                {"codigo": "ABC123", "erro": "Falha de teste"}
            ],
        }
        self.assertTrue(App._historico_execucao_tem_erros(execucao))

    def test_historico_visivel_inclui_execucao_atual_com_erro(self):
        app = App.__new__(App)
        app._historico_execucoes = [
            {
                "id": "anterior",
                "erros": 1,
                "codigos_erros": ["OLD"],
            }
        ]
        app._execucao_atual = {
            "id": "atual",
            "erros": 1,
            "codigos_erros": ["NEW"],
        }

        ids = [item["id"] for item in app._historico_execucoes_visiveis()]
        self.assertEqual(ids, ["anterior", "atual"])

    def test_finalizacao_nao_arquiva_execucao_sem_erros(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app._execucao_atual = {
                "id": "sucesso",
                "inicio": agora,
                "status": "Em andamento",
                "erros": 0,
                "codigos_erros": [],
                "erros_detalhes": [],
            }
            resultado = SimpleNamespace(
                total_planejado=2,
                sucessos=2,
                erros=0,
                processados=2,
                codigos_erros=[],
                erros_detalhes=[],
                itens=[
                    SimpleNamespace(status="Sucesso", codigo="111"),
                    SimpleNamespace(status="Sucesso", codigo="222"),
                ],
            )

            app._finalizar_historico_execucao(resultado)

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            self.assertEqual(dados["historico_execucoes"], [])

    def test_registro_de_erro_persiste_codigo_detalhe_e_mensagem_imediatamente(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app._execucao_atual = {
                "id": "erro-imediato",
                "inicio": agora,
                "status": "Em andamento",
                "erros": 0,
                "codigos_erros": [],
                "erros_detalhes": [],
            }
            app._codigos_erros_execucao = []

            app._registrar_codigo_erro_historico(
                "ABC123",
                numero=4,
                erro="Falha de teste",
            )

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            atual = dados["execucao_atual"]
            self.assertEqual(atual["codigos_erros"], ["ABC123"])
            self.assertEqual(atual["erros"], 1)
            self.assertEqual(atual["erros_detalhes"][0]["codigo"], "ABC123")
            self.assertEqual(atual["erros_detalhes"][0]["numero"], 4)
            self.assertEqual(atual["erros_detalhes"][0]["erro"], "Falha de teste")

    def test_carregamento_remove_execucoes_sem_erros_do_historico_de_erros(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            app._historico_arquivo.write_text(
                json.dumps({
                    "version": 4,
                    "historico_execucoes": [
                        {"id": "ok", "inicio": agora, "status": "Concluída", "erros": 0},
                        {"id": "erro", "inicio": agora, "status": "Concluída", "erros": 1, "codigos_erros": ["ABC"]},
                    ],
                    "execucao_atual": None,
                }),
                encoding="utf-8",
            )

            app._carregar_estado_persistente()

            self.assertEqual(
                [item["id"] for item in app._historico_execucoes],
                ["erro"],
            )

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
            self.assertEqual(registro["erros"], 5)

    def test_finalizacao_persiste_detalhes_dos_codigos_com_erro(self):
        with tempfile.TemporaryDirectory() as temp:
            app = self._app_without_ui(Path(temp))
            app._execucao_atual = {
                "id": "erros-detalhados",
                "inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Em andamento",
                "erros": 2,
                "codigos_erros": [],
            }
            resultado = SimpleNamespace(
                total_planejado=2,
                sucessos=0,
                erros=2,
                processados=2,
                codigos_erros=["12345", "67890"],
                erros_detalhes=[
                    {"numero": 1, "codigo": "12345", "erro": "falha", "horario": "10:00:00"},
                    {"numero": 2, "codigo": "67890", "erro": "falha", "horario": "10:01:00"},
                ],
                itens=[],
            )

            app._finalizar_historico_execucao(resultado)

            dados = json.loads(app._historico_arquivo.read_text(encoding="utf-8"))
            registro = dados["historico_execucoes"][0]
            self.assertEqual(registro["codigos_erros"], ["12345", "67890"])
            self.assertEqual(registro["erros_detalhes"][0]["codigo"], "12345")
            self.assertEqual(registro["erros_detalhes"][1]["codigo"], "67890")

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
