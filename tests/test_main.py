# Testes de inicialização.

# Testes de inicialização.

import unittest
from pathlib import Path


class CanonicalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_main_bootstrap_uses_only_canonical_ui(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_CANONICAL_UI", source)
        self.assertIn("def install_ui(App):", source)
        self.assertIn("App._ui_runtime_mode = \"canonical\"", source)
        self.assertNotIn("from patch import", source)
        self.assertNotIn("bind_all", source)
        self.assertNotIn("install_ui_29912(", source)
        self.assertNotIn("install_ui_fluent_29916(", source)
        self.assertNotIn("install_ui_micro_29918(", source)
        self.assertNotIn("install_ui_windows11_native_29925(", source)
        self.assertLess(len(source.splitlines()), 500)

    def test_main_build_keeps_single_bootstrap_entry(self):
        for filename in ("build_windows.bat", ".github/workflows/validate-main.yml", ".github/workflows/release.yml"):
            source = (self.root / filename).read_text(encoding="utf-8")
            self.assertIn(
                "from interface import App; from main import install_ui, _validar_base_aplicacao",
                source,
            )
            self.assertIn("install_ui(App); _validar_base_aplicacao()", source)

    def test_appearance_submenu_owns_hover_events(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("def _configurar_hover_menu", source)
        self.assertIn("command=self._mostrar_menu_aparencia", block)
        self.assertIn('aparencia.bind("<Enter>", self._mostrar_menu_aparencia', block)
        self.assertIn('aparencia.bind("<Leave>", self._agendar_fechar_menus', block)
        self.assertIn("for widget in self._iterar_descendentes_ui(aparencia):", block)
        self.assertIn('widget.bind("<Enter>", self._mostrar_menu_aparencia', block)
        self.assertIn('widget.bind("<Leave>", self._agendar_fechar_menus', block)
        self.assertNotIn('self.app.bind_all("<Button-1>"', source)

    def test_appearance_hover_compatibility_method_is_real(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _garantir_menu_aparencia_aberto_se_hover")
        end = source.index("def _garantir_menu_aparencia_aberto(self)", start)
        block = source[start:end]
        self.assertIn("return self._mostrar_menu_aparencia(event)", block)

    def test_iniciar_footer_does_not_create_a_white_strip(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        actions_start = source.index("actions = ctk.CTkFrame(")
        actions_end = source.index("self.status_label =", actions_start)
        actions_block = source[actions_start:actions_end]
        self.assertIn('fg_color="transparent"', actions_block)
        self.assertIn('height=68', actions_block)
        self.assertIn('actions.pack(fill="x", side="bottom")', actions_block)

    def test_iniciar_has_one_canonical_text_owner(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('text="Iniciar"'), 1)
        self.assertIn('text_color="#FFFFFF"', source)

    def test_tooltips_e_hover_dos_cards_estao_na_interface_canonica(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("class _SMAutoLabTooltip:", source)
        self.assertIn("def _ui_install_button_tooltips", source)
        self.assertIn("_ui_install_button_tooltips()", source)
        self.assertIn("def _ui_bind_card_hover", source)
        self.assertIn('"Executados": "Mostra a quantidade de códigos executados com sucesso."', source)
        self.assertIn('"Não executados": "Mostra a quantidade de códigos que apresentaram erro durante a execução."', source)
        self.assertIn('"Código atual": "Mostra o código que está sendo processado no momento."', source)
        self.assertIn("_ui_bind_card_hover(card, accent)", source)
        self.assertNotIn("install_ui_micro_29918", source)
        self.assertNotIn("bind_all", source)

    def test_stat_cards_mantem_feedback_visual_e_tooltip(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _stat_card")
        end = source.index("def _set_stat", start)
        block = source[start:end]
        self.assertIn("_ui_bind_card_hover(card, accent)", block)
        self.assertIn("_SMAutoLabTooltip(", block)
        self.assertIn("card_tooltips =", block)

    def test_tooltip_fecha_no_clique_foco_ou_destruicao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("class _SMAutoLabTooltip:")
        end = source.index("def _ui_tooltip_text", start)
        block = source[start:end]
        self.assertIn('child.bind("<ButtonPress>", self._on_press, add="+")', block)
        self.assertIn('child.bind("<FocusOut>", self._on_focus_out, add="+")', block)
        self.assertIn("self._destroy_window()", block)
        self.assertIn("def _destroy_window(self):", block)
        self.assertNotIn('self._window.withdraw()', block)

    def test_botao_abrir_continua_com_tooltip_canonico(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("self.botao_planilha = ctk.CTkButton(")
        end = source.index("self.botao_planilha.pack", start)
        block = source[start:end]
        self.assertIn('text="Abrir"', block)
        self.assertIn("command=self.abrir_planilha", block)
        self.assertIn('"abrir": "Abre a planilha interna."', source)

    def test_legacy_patch_module_is_absent(self):
        self.assertFalse((self.root / "patch.py").exists())

    def test_interface_has_no_global_mouse_binding(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn("bind_all", source)
        self.assertNotIn('bind("<Button-1>", on_click', source)


if __name__ == "__main__":
    unittest.main()
