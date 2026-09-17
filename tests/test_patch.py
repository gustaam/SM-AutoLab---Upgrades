import unittest
from pathlib import Path


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
        main = (root / "main.py").read_text(encoding="utf-8")
        interface = (root / "interface.py").read_text(encoding="utf-8")
        atualizacao = (root / "atualizacao.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn("from patch import aplicar_patch_ui", main)
        self.assertIn("def install_ui_29912", main)
        self.assertNotIn("from ui_fixes_29912 import", main)
        for content in (main, interface, atualizacao, build):
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
        main = (root / "main.py").read_text(encoding="utf-8")
        self.assertFalse((root / "ui_fixes_29912.py").exists())
        for marker in (
            "SM_AUTOLAB_UI_FIXES_29912",
            "_home_counter",
            "_calendar_click",
            "_create_history_tile",
            "_select_history_tile",
            "def install_ui_29912",
        ):
            self.assertIn(marker, main)

    def test_ctrl_click_e_selecao_multipla_estao_previstos(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("0x0004", main)
        self.assertIn("_arquivos_datas_selecionadas", main)
        self.assertIn("_hist_selected_tiles", main)

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
        main = (root / "main.py").read_text(encoding="utf-8")
        self.assertEqual(main.count("App.config_app = config_wrapper"), 1)
        self.assertNotIn("original_global_config = App.config_app", main)
        self.assertNotIn("def global_config_wrapper", main)
        self.assertIn('self.app.bind_all("<Button-1>", lambda event: _global_click(self, event), add="+")', main)

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

    def test_auxiliares_de_build_e_documentacao_foram_consolidados(self):
        root = Path(__file__).resolve().parents[1]
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        readme = (root / "README.md").read_text(encoding="utf-8")
        self.assertFalse((root / "version_info_template.txt").exists())
        self.assertFalse((root / "INTEGRATION_MANIFEST.txt").exists())
        self.assertNotIn("version_info_template.txt", build)
        for marker in ("VSVersionInfo(", "FixedFileInfo(", "StringFileInfo([", "Set-Content version_info.txt"):
            self.assertIn(marker, build)
        for marker in ("Mapa de integração", "_SOURCE_PATCH_BASE", "_SOURCE_PATCH_ARQUIVOS", "_SOURCE_PATCH_AJUSTES"):
            self.assertIn(marker, readme)


if __name__ == "__main__":
    unittest.main()
