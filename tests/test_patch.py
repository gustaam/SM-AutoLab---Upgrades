# Testes de regressão arquitetural.

import unittest
from pathlib import Path


class CanonicalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_planilha_tem_apenas_abas_atividade_e_historico(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('for name in ("Atividade", "Histórico"):', source)
        self.assertNotIn('for name in ("Atividade", "Não executados", "Histórico"):', source)
        self.assertNotIn("self.aba_erros", source)
        self.assertNotIn("self.erros_frame", source)
        self.assertNotIn("self.erros_titulo", source)

    def test_main_bootstrap_uses_only_canonical_ui(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_CANONICAL_UI", source)
        self.assertIn("def install_ui(App):", source)
        self.assertNotIn("from patch import", source)
        self.assertNotIn("aplicar_patch_ui", source)
        self.assertNotIn("bind_all", source)

    def test_appearance_submenu_uses_canonical_hover_and_monitoring(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _configurar_hover_menu", source)
        self.assertIn('command=self._mostrar_menu_aparencia', source)
        self.assertIn('aparencia.bind("<Enter>", self._mostrar_menu_aparencia', source)
        self.assertIn('aparencia.bind("<Leave>", self._agendar_fechar_aparencia', source)
        self.assertIn("def _monitorar_menus", source)
        self.assertIn("self._ativar_clique_fora_menus()", source)
        self.assertIn("self._pointer_em_area_dos_menus", source)

    def test_planilha_mouse_events_use_one_hit_test(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("def identify_cell("), 1)
        for name in (
            "_planilha_clicar_celula",
            "_planilha_arrastar_selecao",
            "_planilha_soltar_selecao",
            "_planilha_duplo_clique_celula",
        ):
            start = source.index(f"def {name}")
            end = source.find("\n    def ", start + 1)
            block = source[start:end if end >= 0 else len(source)]
            self.assertIn("tree.identify_cell(event.x, event.y)", block)
        self.assertNotIn("bind_all", source)

    def test_legacy_patch_module_is_absent(self):
        self.assertFalse((self.root / "patch.py").exists())


if __name__ == "__main__":
    unittest.main()
