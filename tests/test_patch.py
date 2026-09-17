import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import main
from patch import aplicar_patch_ui


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
        atualizacao = (root / "atualizacao.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn("from patch import aplicar_patch_ui", main_content)
        self.assertIn("def install_ui_29912", main_content)
        self.assertNotIn("from ui_fixes_29912 import", main_content)
        for content in (main_content, interface, atualizacao, build):
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
        self.assertNotRegex(interface, r'"PORTAL_USUARIO"\s*:\s*"[^"\r\n]+"')
        self.assertNotRegex(interface, r'"PORTAL_SENHA"\s*:\s*"[^"\r\n]+"')

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

    def test_build_manual_usa_mesmo_fluxo_de_integracao_do_ci(self):
        root = Path(__file__).resolve().parents[1]
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn(
            "from main import _corrigir_historico_ilimitado, _validar_base_aplicacao, install_ui_29912",
            build,
        )
        self.assertIn(
            "aplicar_patch_ui(App); _corrigir_historico_ilimitado(); install_ui_29912(App); _validar_base_aplicacao()",
            build,
        )
        self.assertNotIn(
            "from main import _validar_base_aplicacao; aplicar_patch_ui(App); _validar_base_aplicacao()",
            build,
        )

    def test_arquivos_de_teste_auxiliares_foram_consolidados(self):
        root = Path(__file__).resolve().parent
        self.assertFalse((root / "test_ui_correcoes_29912.py").exists())
        self.assertFalse((root / "test_historico_ilimitado.py").exists())


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
        self.assertIn(data, app._arquivos_datas_datas_selecionadas if hasattr(app, "_arquivos_datas_datas_selecionadas") else app._arquivos_datas_selecionadas)
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


if __name__ == "__main__":
    unittest.main()
