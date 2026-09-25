# Testes do núcleo de automação e persistência.

import json
import tempfile
import unittest
from pathlib import Path

from app import (
    ResultadoCodigo,
    Resultados,
    atomic_write_json,
    atomic_write_text,
    backup_path,
    read_json_with_backup,
)

# tests/test_stage10.py

class ExecucaoPerformanceStage10Tests(unittest.TestCase):
    def test_resultados_inicia_com_contadores_zerados(self):
        resultados = Resultados(total=4)
        self.assertEqual(resultados.total_planejado, 4)
        self.assertEqual(resultados.processados, 0)
        self.assertEqual(resultados.sucessos, 0)
        self.assertEqual(resultados.erros, 0)

    def test_metricas_de_resultados_sao_incrementais(self):
        resultados = Resultados(total=4)
        self.assertEqual(resultados.processados, 0)
        self.assertEqual(resultados.sucessos, 0)
        self.assertEqual(resultados.erros, 0)

        resultados.registrar_sucesso(1, "A")
        resultados.registrar_erro(2, "B", "falha")
        resultados.registrar_sucesso(3, "C")

        self.assertEqual(resultados.processados, 3)
        self.assertEqual(resultados.sucessos, 2)
        self.assertEqual(resultados.erros, 1)
        self.assertEqual(len(resultados.itens), 3)

    def test_contadores_nao_dependem_de_recontagem_dos_itens(self):
        resultados = Resultados(total=2)
        resultados.itens = [
            ResultadoCodigo(1, "A", "Sucesso"),
            ResultadoCodigo(2, "B", "Erro", erro="falha"),
        ]

        self.assertEqual(resultados.sucessos, 0)
        self.assertEqual(resultados.erros, 0)

        resultados.registrar_sucesso(3, "C")
        self.assertEqual(resultados.sucessos, 1)
        self.assertEqual(resultados.erros, 0)


# tests/test_storage_safe.py

class ExecutionLifecycleTests(unittest.TestCase):
    def test_principal_interno_libera_referencia_de_automacao(self):
        source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(
            encoding="utf-8"
        )
        start = source.index("def principal_interno")
        end = source.index("def principal(", start)
        block = source[start:end]
        self.assertIn("aplicativo._automacao_atual = auto", block)
        self.assertIn("auto.fechar()", block)
        self.assertIn('aplicativo._automacao_atual = None', block)

    def test_principal_planilha_libera_referencia_de_automacao(self):
        source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(
            encoding="utf-8"
        )
        start = source.index("def principal(planilha_path")
        block = source[start:]
        self.assertIn("aplicativo._automacao_atual = auto", block)
        self.assertIn("auto.fechar()", block)
        self.assertIn('aplicativo._automacao_atual = None', block)


class SeleniumWindowBehaviorTests(unittest.TestCase):
    def test_runtime_selenium_usa_fluxo_padrao_antes_das_alteracoes_explicitas(self):
        source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('options.add_argument("--start-minimized")', source)
        self.assertIn("driver.minimize_window()", source)
        self.assertIn("def _bundle_cft()", source)
        self.assertIn("def _cache_cft(root, version)", source)
        self.assertIn("options.binary_location = str(browser_path)", source)
        self.assertIn("Service(executable_path=str(driver_path))", source)
        self.assertIn("webdriver.Chrome(service=service, options=options)", source)
        self.assertNotIn('options.browser_version = "stable"', source)
        self.assertIn('options.add_argument("--disable-extensions")', source)
        self.assertIn('options.add_argument("--disable-notifications")', source)
        self.assertIn('options.add_argument("--no-first-run")', source)
        self.assertIn("driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)", source)
        self.assertNotIn("SeleniumManager()", source)
        self.assertNotIn('subprocess.Popen(', source)
        self.assertNotIn("--cache-path", source)
        self.assertNotIn("--language-binding", source)

    def test_driver_e_executa_sem_forcar_navegador_embutido(self):
        source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("def _criar_driver(self):", source)
        self.assertIn("driver = webdriver.Chrome(options=options)", source)
        self.assertNotIn("def _bundled_chrome_paths", source)


class StorageSafeTests(unittest.TestCase):
    def test_escrita_atomica_cria_arquivo_e_backup_na_segunda_gravacao(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "estado.json"
            atomic_write_json(path, {"n": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"n": 1})
            self.assertFalse(backup_path(path).exists())

            atomic_write_json(path, {"n": 2})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"n": 2})
            self.assertEqual(json.loads(backup_path(path).read_text(encoding="utf-8")), {"n": 1})

    def test_falha_de_corrompimento_recupera_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "estado.json"
            atomic_write_json(path, {"versao": 1})
            atomic_write_json(path, {"versao": 2})

            path.write_text("{corrompido", encoding="utf-8")
            self.assertEqual(read_json_with_backup(path), {"versao": 1})

    def test_escrita_atomicamente_nao_deixa_tmp_no_final(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "estado.txt"
            atomic_write_text(path, "ok")
            leftovers = list(Path(temp).glob(".*.tmp"))
            self.assertEqual(leftovers, [])
            self.assertEqual(path.read_text(encoding="utf-8"), "ok")
