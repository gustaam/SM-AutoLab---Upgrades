import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import atualizacao
import main
from patch import aplicar_patch_ui


class FakeLabel:
    def __init__(self):
        self.configured = []
        self.packed = True
        self.packed_options = {}

    def configure(self, **kwargs):
        self.configured.append(kwargs)

    def winfo_manager(self):
        return "pack" if self.packed else ""

    def pack(self, **kwargs):
        self.packed = True
        self.packed_options = kwargs

    def pack_configure(self, **kwargs):
        self.packed_options.update(kwargs)

    def pack_forget(self):
        self.packed = False


class FakeTile:
    def __init__(self, name):
        self.name = name
        self.options = {}

    def configure(self, **kwargs):
        self.options.update(kwargs)

    def __repr__(self):
        return f"FakeTile({self.name})"


class FakeCanvas:
    def find_overlapping(self, *_args):
        return (1,)

    def gettags(self, _item_id):
        return ("dia:2026-09-17",)


class TestPatch(unittest.TestCase):
    def test_instrucao_ctrl_clique_foi_removida(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("main.py", "interface.py", "patch.py"):
            self.assertNotIn("Ctrl + clique para selecionar várias datas", (root / name).read_text(encoding="utf-8"))

    def test_componentes_base_estao_fisicamente_consolidados(self):
        root = Path(__file__).resolve().parents[1]
        patch = (root / "patch.py").read_text(encoding="utf-8")
        for name in ("patch_base.py", "patch_arquivos.py", "patch_ajustes.py"):
            self.assertFalse((root / name).exists(), msg=f"{name} ainda existe")
        for marker in (
            "_SOURCE_PATCH_BASE", "_SOURCE_PATCH_ARQUIVOS", "_SOURCE_PATCH_AJUSTES",
            "_NS_PATCH_BASE", "_NS_PATCH_ARQUIVOS", "_NS_PATCH_AJUSTES",
        ):
            self.assertIn(marker, patch)

    def test_ponto_de_entrada_atualizado(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        interface = (root / "interface.py").read_text(encoding="utf-8")
        atualizacao_content = (root / "atualizacao.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn("from patch import aplicar_patch_ui", main_content)
        self.assertIn("def install_ui_29912", main_content)
        self.assertNotIn("from ui_fixes_29912 import", main_content)
        for content in (main_content, interface, atualizacao_content, build):
            self.assertNotIn("from patch_base import", content)
            self.assertNotIn("from patch_arquivos import", content)
            self.assertNotIn("from patch_ajustes import", content)
        self.assertIn("from patch import aplicar_patch_ui", build)

    def test_artifacts_temporarios_da_etapa_b_nao_existirem(self):
        root = Path(__file__).resolve().parents[1]
        self.assertFalse((root / ".etapa-b-trigger").exists())
        self.assertFalse((root / ".github" / "workflows" / "_fix_patch_b_import.yml").exists())

    def test_correcoes_ui_pos_release_estao_na_camda_final(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        self.assertFalse((root / "ui_fixes_29912.py").exists())
        for marker in (
            "SM_AUTOLAB_UI_FIXES_29912",
            "_home_counter",
            "_calendar_click",
            "_create_history_tile",
            "_select_history_tile",
            "def install_ui_29912",
        ):
            self.assertIn(marker, main_content)

    def test_ctrl_click_e_selecao_multipla_estao_previstos(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("0x0004", main_content)
        self.assertIn("_arquivos_datas_selecionadas", main_content)
        self.assertIn("_hist_selected_tiles", main_content)

    def test_credenciais_nao_estao_literalmente_no_codigo(self):
        root = Path(__file__).resolve().parents[1]
        config = (root / "config.py").read_text(encoding="utf-8")
        interface = (root / "interface.py").read_text(encoding="utf-8")
        self.assertRegex(config, r'DEFAULT_PORTAL_USUARIO\s*=\s*""')
        self.assertRegex(config, r'DEFAULT_PORTAL_SENHA\s*=\s*""')
        self.assertNotRegex(interface, r'"PORTAL_USUARIO"\s*=\s*"[^"\r\n]+"')
        self.assertNotRegex(interface, r'"PORTAL_SENHA"\s*=\s*"[^"\r\n]+"')

    def test_automacao_usa_imports_explicitos(self):
        root = Path(__file__).resolve().parents[1]
        automacao = (root / "automacao.py").read_text(encoding="utf-8")
        self.assertNotIn("from config import *", automacao)
        self.assertIn("from config import (", automacao)
        for symbol in (
            "ALERT_TIMEOUT", "CODE_INPUT_XPATH", "CONFIRM_BUTTON_XPATH",
            "ELEMENT_TIMEOUT", "INPUT_DELAY", "LOGIN_BUTTON_XPATH",
            "LOGIN_PASSWORD_XPATH", "LOGIN_TIMEOUT", "LOGIN_USER_XPATH",
            "PAGE_LINK_XPATH", "PAGE_LOAD_TIMEOUT", "PORTAL_SENHA",
            "PORTAL_USUARIO", "RECOVERY_TIMEOUT", "SITE_URL",
            "carregar_configuracoes",
        ):
            self.assertIn(symbol, automacao)

    def test_config_app_tem_apenas_um_wrapper(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        self.assertEqual(main_content.count("App.config_app = config_wrapper"), 1)
        self.assertNotIn("original_global_config = App.config_app", main_content)
        self.assertNotIn("def global_config_wrapper", main_content)
        self.assertIn('self.app.bind_all("<Button-1>", lambda event: _global_click(self, event), add="+")', main_content)

    def test_build_manual_usa_ponto_de_entrada_unico_da_ui(self):
        root = Path(__file__).resolve().parents[1]
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            build,
        )
        self.assertIn(
            "install_ui(App); _validar_base_aplicacao()",
            build,
        )

    def test_arquivos_de_teste_auxiliares_foram_consolidados(self):
        root = Path(__file__).resolve().parent
        self.assertFalse((root / "test_atualizacao.py").exists())
        self.assertFalse((root / "test_ui_correcoes_29912.py").exists())
        self.assertFalse((root / "test_historico_ilimitado.py").exists())




class AuditoriaStage6Tests(unittest.TestCase):
    def test_stage6_marcador_e_integracao(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_AUDITORIA_29920", main_content)
        self.assertIn("def _configurar_dpi_windows", main_content)
        self.assertIn("def install_ui_auditoria_29920", main_content)
        self.assertIn("install_ui_auditoria_29920(App)", main_content)

    def test_stage6_splash_reduz_trabalho_por_frame(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("FPS_MS = 16", content)
        self.assertIn("self._canvas_image_id", content)
        self.assertIn("self.canvas.itemconfigure(self._canvas_image_id, image=self._photo)", content)
        self.assertNotIn('self.canvas.delete("all")', content)

    def test_stage6_dpi_por_monitor_com_fallback(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SetProcessDpiAwarenessContext", content)
        self.assertIn("ctypes.c_void_p(-4)", content)
        self.assertIn("SetProcessDpiAwareness", content)
        self.assertIn("setter(2)", content)

    def test_stage6_preserva_a_inicializacao_unificada(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("def install_ui(App):", content)
        self.assertIn("install_ui_29912(App)", content)
        self.assertIn("install_ui_fluent_29916(App)", content)
        self.assertIn("install_ui_dashboard_29917(App)", content)
        self.assertIn("install_ui_micro_29918(App)", content)
        self.assertIn("install_ui_planilha_29919(App)", content)
        self.assertIn("install_ui_responsivo_29921(App)", content)
        self.assertIn("install_ui_auditoria_29920(App)", content)
        self.assertIn("install_ui_windows11_native_29925(App)", content)
        self.assertNotIn("install_ui_grade_29922(App)", content)


class PlanilhaPerformanceStage8Tests(unittest.TestCase):
    def test_stage8_povoamento_incremental_da_grade(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("self._planilha_povoamento_job", content)
        self.assertIn("self._planilha_povoamento_proxima_linha", content)
        self.assertIn("for i in range(300)", content)
        self.assertIn("fim = min(10000, inicio + 500)", content)
        self.assertIn("tree.after(1, _povoar_lote)", content)
        self.assertIn("self._planilha_povoamento_concluido = True", content)

    def test_stage8_preserva_cancelamento_do_povoamento(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("self._planilha_tree.after_cancel(self._planilha_povoamento_job)", content)


class ResponsivoTooltipsStage7Tests(unittest.TestCase):
    def test_stage7_marcador_integracao_e_boot(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_RESPONSIVO_29921", main_content)
        self.assertIn("def install_ui_responsivo_29921", main_content)
        self.assertIn("install_ui_responsivo_29921(App)", main_content)
        self.assertIn('"radius_sm": 8', main_content)

    def test_stage7_tooltips_cobrem_acoes_principais_e_navegacao(self):
        self.assertEqual(
            main._stage7_tooltip_text(SimpleNamespace(cget=lambda key: "▶  Iniciar")),
            "Inicia a automação com os códigos selecionados.",
        )
        self.assertEqual(
            main._stage7_tooltip_text(SimpleNamespace(cget=lambda key: "‹")),
            "Volta para o mês anterior.",
        )
        self.assertEqual(
            main._stage7_tooltip_text(SimpleNamespace(cget=lambda key: "↶")),
            "Desfaz a última alteração.",
        )
        self.assertEqual(
            main._stage7_tooltip_text(SimpleNamespace(cget=lambda key: "ABC123")),
            "Clique para copiar este código.",
        )

    def test_stage7_layout_e_janela_sao_redimensionaveis(self):
        root = Path(__file__).resolve().parents[1]
        interface = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('self.app.minsize(760, 590)', interface)
        self.assertIn('self.app.resizable(True, True)', interface)
        self.assertIn('self._stage7_top_layout = top', interface)
        self.assertIn('self._stage7_config_card = config', interface)
        self.assertIn('self._stage7_progress_card = progress', interface)
        self.assertIn("Tooltips passam a ser gerenciados globalmente", interface)
        self.assertNotIn("#DETALHES BOTÕES", interface)

    def test_stage7_normaliza_prefixos_de_botoes(self):
        self.assertEqual(
            main._stage7_tooltip_text(SimpleNamespace(cget=lambda key: "■  Parar")),
            "Interrompe a automação com parada segura após o código atual.",
        )
        self.assertEqual(
            main._stage7_tooltip_text(SimpleNamespace(cget=lambda key: "✓  Claro")),
            "Usa o tema claro.",
        )


class PlanilhaStage5Tests(unittest.TestCase):
    def test_stage5_integracao_e_marcador(self):
        root = Path(__file__).resolve().parents[1]
        main_content = (root / "main.py").read_text(encoding="utf-8")
        interface_content = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_PLANILHA_29919", main_content)
        self.assertIn("def install_ui_planilha_29919", main_content)
        self.assertIn("def _planilha_desenhar_cabecalho_linhas", interface_content)
        self.assertIn("Virtualização do cabeçalho de linhas", interface_content)

    def test_stage5_nao_cria_os_10_mil_itens_de_canvas_do_cabecalho(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "for i in range(10000):\n            y_text = i * row_height",
            content,
        )
        self.assertIn('canvas.delete("rownum")', content)

    def test_stage5_historico_tem_cache_por_assinatura(self):
        root = Path(__file__).resolve().parents[1]
        content = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _assinatura_historico_planilhas", content)
        self.assertIn("_planilha_historico_cache_signature", content)


class UIFixes29912Tests(unittest.TestCase):
    def test_ctrl_pressed_uses_control_mask(self):
        self.assertTrue(main._ctrl_pressed(SimpleNamespace(state=0x0004)))
        self.assertFalse(main._ctrl_pressed(SimpleNamespace(state=0)))

    def test_home_counter_uses_only_saved_passwords(self):
        label = FakeLabel()

        class AppStub:
            arquivos_contador_label = label

            def _count_saved_passwords(self):
                return 7

            def _contar_codigos_mes(self, _referencia=None):
                raise AssertionError("contador mensal não deve ser usado")

        main._home_counter(AppStub())
        self.assertEqual(label.configured[-1]["text"], "7 Códigos salvos")
        self.assertTrue(label.packed)

    def test_home_counter_hides_when_empty(self):
        label = FakeLabel()

        class AppStub:
            arquivos_contador_label = label

            def _count_saved_passwords(self):
                return 0

        main._home_counter(AppStub())
        self.assertFalse(label.packed)

    def test_home_counter_reappears_after_being_hidden(self):
        label = FakeLabel()
        label.packed = False

        class AppStub:
            arquivos_contador_label = label

            def _count_saved_passwords(self):
                return 3

        main._home_counter(AppStub())
        self.assertTrue(label.packed)
        self.assertEqual(label.packed_options["side"], "left")

    def test_history_ctrl_click_accumulates_and_toggles_tiles(self):
        class AppStub:
            _hist_selected_tiles = set()
            _hist_selected_tile = None
            BORDER = "border"
            ACCENT = "accent"

        app = AppStub()
        first = FakeTile("first")
        second = FakeTile("second")

        main._select_history_tile(app, first, ctrl=False)
        main._select_history_tile(app, second, ctrl=True)
        self.assertEqual(app._hist_selected_tiles, {first, second})

        main._select_history_tile(app, first, ctrl=True)
        self.assertEqual(app._hist_selected_tiles, {second})
        self.assertIs(app._hist_selected_tile, second)

    def test_calendar_ctrl_click_requests_toggle(self):
        canvas = FakeCanvas()
        calls = []
        target = date(2026, 9, 17)

        class AppStub:
            _arquivos_calendar_canvas = canvas
            _arquivos_modo_selecao = False

            def _dados_arquivos_por_dia(self):
                return {target: [{}]}

            def _toggle_data_selecionada(self, data):
                calls.append(("toggle", data))

            def _mostrar_planilhas_do_dia(self, data):
                calls.append(("open", data))

        main._calendar_click(AppStub(), SimpleNamespace(state=0x0004, x=10, y=10))
        self.assertEqual(calls, [("toggle", target)])


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


class VersionComparisonTests(unittest.TestCase):
    def test_fourth_component_is_not_truncated(self):
        self.assertLess(atualizacao._version_tuple("2.99.9"), atualizacao._version_tuple("2.99.9.1"))
        self.assertLess(atualizacao._version_tuple("2.99.9.1"), atualizacao._version_tuple("2.99.10"))

    def test_trailing_zero_component_is_equivalent(self):
        self.assertEqual(atualizacao._version_tuple("2.99.9"), atualizacao._version_tuple("v2.99.9.0"))
        self.assertEqual(atualizacao._version_tuple("2.99.9.1"), atualizacao._version_tuple("2.99.9.1.0"))

    def test_invalid_version_is_rejected(self):
        self.assertEqual(atualizacao._version_tuple("2.99.x"), ())
        self.assertEqual(atualizacao._version_tuple(""), ())
        self.assertEqual(atualizacao._version_tuple("v"), ())


class UpdateEnvironmentTests(unittest.TestCase):
    def test_sanitize_pyinstaller_environment_removes_internal_state(self):
        source = {
            "PATH": "C:\\Windows",
            "TEMP": "C:\\Temp",
            "_PYI_PARENT_PROCESS_LEVEL": "1",
            "_PYI_APPLICATION_HOME_DIR": "C:\\Temp\\_MEI123",
            "_MEIPASS2": "C:\\Temp\\_MEI123",
            "_PyI_MixedCase": "legacy",
        }
        clean = atualizacao._sanitize_pyinstaller_environment(source)
        self.assertEqual(clean["PATH"], "C:\\Windows")
        self.assertEqual(clean["TEMP"], "C:\\Temp")
        self.assertNotIn("_PYI_PARENT_PROCESS_LEVEL", clean)
        self.assertNotIn("_PYI_APPLICATION_HOME_DIR", clean)
        self.assertNotIn("_MEIPASS2", clean)
        self.assertNotIn("_PyI_MixedCase", clean)

    def test_prepare_independent_restart_sets_pyinstaller_reset(self):
        source = {
            "PATH": "C:\\Windows",
            "_PYI_ARCHIVE_FILE": "C:\\old\\SM.AutoLab.exe",
            "_PYI_PARENT_PROCESS_LEVEL": "1",
            "PYINSTALLER_RESET_ENVIRONMENT": "0",
        }
        restart_env = atualizacao._prepare_independent_restart_environment(source)
        self.assertEqual(restart_env["PATH"], "C:\\Windows")
        self.assertEqual(restart_env["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        self.assertNotIn("_PYI_ARCHIVE_FILE", restart_env)
        self.assertNotIn("_PYI_PARENT_PROCESS_LEVEL", restart_env)


class UpdateDiscoveryTests(unittest.TestCase):
    def _release(self, tag: str) -> dict:
        return {
            "tag_name": tag,
            "draft": False,
            "prerelease": False,
            "name": f"SM AutoLab {tag.lstrip('vV')}",
            "html_url": "https://example.invalid/release",
            "assets": [{
                "name": "SM.AutoLab.exe",
                "browser_download_url": "https://example.invalid/app.exe",
                "digest": "sha256:abc123",
            }],
        }

    def test_discovers_four_component_release_from_three_component_current_version(self):
        release = self._release("v2.99.9.1")
        manifest = {
            "channel": atualizacao.UPDATE_CHANNEL,
            "version": "2.99.9.1",
            "tag": "v2.99.9.1",
            "main_asset": "SM AutoLab.exe",
        }
        with patch.object(atualizacao, "current_version", return_value="2.99.9"), patch.object(
            atualizacao, "fetch_releases", return_value=[release]
        ), patch.object(atualizacao, "_load_release_manifest", return_value=manifest):
            update = atualizacao.find_update()
        self.assertIsNotNone(update)
        self.assertEqual(update["version"], "2.99.9.1")
        self.assertEqual(update["asset_name"], "SM.AutoLab.exe")
        self.assertEqual(update["sha256"], "abc123")

    def test_discovers_standard_successor_from_four_component_current_version(self):
        release = self._release("v2.99.10")
        manifest = {
            "channel": atualizacao.UPDATE_CHANNEL,
            "version": "2.99.10",
            "tag": "v2.99.10",
            "main_asset": "SM AutoLab.exe",
        }
        with patch.object(atualizacao, "current_version", return_value="2.99.9.1"), patch.object(
            atualizacao, "fetch_releases", return_value=[release]
        ), patch.object(atualizacao, "_load_release_manifest", return_value=manifest):
            update = atualizacao.find_update()
        self.assertIsNotNone(update)
        self.assertEqual(update["version"], "2.99.10")

    def test_does_not_offer_same_version_with_different_prefix(self):
        release = self._release("V2.99.9.0")
        with patch.object(atualizacao, "current_version", return_value="2.99.9"), patch.object(
            atualizacao, "fetch_releases", return_value=[release]
        ):
            self.assertIsNone(atualizacao.find_update())

    def test_rejects_manifest_when_asset_digest_does_not_match(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return (
                    b'{"channel":"SM-AUTOLAB-RESET-2026-09","version":"2.99.10",'
                    b'"tag":"v2.99.10","main_asset":"SM AutoLab.exe",'
                    b'"main_sha256":"1111111111111111111111111111111111111111111111111111111111111111"}'
                )

        release = {
            "tag_name": "v2.99.10",
            "assets": [
                {
                    "name": "SM AutoLab Release Manifest.json",
                    "browser_download_url": "https://github.com/gustaam/SM-AutoLab---Upgrades/releases/download/v2.99.10/SM%20AutoLab%20Release%20Manifest.json",
                },
                {
                    "name": "SM AutoLab.exe",
                    "browser_download_url": "https://github.com/gustaam/SM-AutoLab---Upgrades/releases/download/v2.99.10/SM%20AutoLab.exe",
                    "digest": "sha256:2222222222222222222222222222222222222222222222222222222222222222",
                },
            ],
        }
        with patch.object(atualizacao.urllib.request, "urlopen", return_value=FakeResponse()):
            self.assertIsNone(atualizacao._load_release_manifest(release))



class GradePerformanceStage9Tests(unittest.TestCase):
    def test_stage9_marker_e_metodos_estao_na_implementacao_canonica(self):
        root = Path(__file__).resolve().parents[1]
        interface = (root / "interface.py").read_text(encoding="utf-8")
        main_source = (root / "main.py").read_text(encoding="utf-8")
        self.assertEqual(
            main.SM_AUTOLAB_GRADE_29922,
            "SM-AUTOLAB-GRADE-PERFORMANCE-29922",
        )
        self.assertIn("def _planilha_desenhar_grade", interface)
        self.assertIn("def _planilha_stage9_get_grid_state", interface)
        self.assertIn("def _planilha_stage9_get_visible_rows", interface)
        self.assertNotIn("def install_ui_grade_29922", main_source)
        self.assertNotIn("def _stage9_desenhar_borda", main_source)

    def test_stage9_row_header_reuses_canvas_items(self):
        class Canvas:
            def __init__(self):
                self.next_id = 1
                self.calls = []
            def winfo_height(self): return 84
            def configure(self, **kwargs): self.calls.append(("configure", kwargs))
            def create_text(self, *args, **kwargs):
                i=self.next_id; self.next_id+=1; self.calls.append(("create_text",i)); return i
            def create_line(self, *args, **kwargs):
                i=self.next_id; self.next_id+=1; self.calls.append(("create_line",i)); return i
            def coords(self, *args): self.calls.append(("coords", args))
            def itemconfigure(self, *args, **kwargs): self.calls.append(("itemconfigure", args, kwargs))
        class Tree:
            def yview(self): return (0.0, 0.01)
        class AppStub:
            _planilha_row_header = Canvas()
            _planilha_tree = Tree()
        app=AppStub()
        main.App._planilha_desenhar_cabecalho_linhas(app)
        created=sum(1 for c in app._planilha_row_header.calls if c[0] in ("create_text","create_line"))
        main.App._planilha_desenhar_cabecalho_linhas(app)
        created_again=sum(1 for c in app._planilha_row_header.calls if c[0] in ("create_text","create_line"))
        self.assertEqual(created_again, created)

    def test_stage9_border_cleanup_hides_instead_of_destroying(self):
        class FrameStub:
            def __init__(self): self.hidden=0
            def place_forget(self): self.hidden += 1
        class AppStub:
            _planilha_borda_widgets=[FrameStub(),FrameStub()]
        # O método canônico é chamado diretamente na classe base.
        AppStub._planilha_stage9_get_grid_state = lambda self: {
            "widgets": [], "selection_widgets": self._planilha_borda_widgets, "bbox": None
        }
        main.App._planilha_limpar_borda(AppStub)
        self.assertEqual([w.hidden for w in AppStub._planilha_borda_widgets], [1,1])

    def test_stage9_boot_usa_a_entrada_unica(self):
        source=Path(main.__file__).read_text(encoding="utf-8")
        self.assertIn("install_ui(App)", source)
        self.assertNotIn("install_ui_grade_29922(App)", source)


if __name__ == "__main__":
    unittest.main()