# Testes da inicialização, dashboard e integração da camada principal.
import unittest
from pathlib import Path
from types import SimpleNamespace

import main

# tests/test_config_menu_position.py

class ConfigMenuPositionTests(unittest.TestCase):
    def test_menu_configuracoes_e_ancorado_abaixo_do_botao(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _reposicionar_menus")
        end = source.index("def _fixar_menu_configuracoes", start)
        block = source[start:end]
        self.assertIn("menu_x = bx", block)
        self.assertNotIn("bx - 40", block)
        self.assertIn("self._menu_config.place_configure(", block)


# tests/test_dashboard.py

class DashboardStage3Tests(unittest.TestCase):
    def test_dashboard_stage3_marker_and_entry_point(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_DASHBOARD_29917", source)
        self.assertIn("def install_ui_dashboard_29917", source)
        self.assertIn("install_ui_dashboard_29917(App)", source)
        self.assertIn('setattr(App, "_selecionar_tema", theme_wrapper)', source)

    def test_dashboard_clamp_is_safe(self):
        self.assertEqual(main._dashboard_clamp(-1), 0.0)
        self.assertEqual(main._dashboard_clamp(0), 0.0)
        self.assertEqual(main._dashboard_clamp(0.42), 0.42)
        self.assertEqual(main._dashboard_clamp(2), 1.0)
        self.assertEqual(main._dashboard_clamp("invalido"), 0.0)

    def test_dashboard_layer_is_visual_only(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "main.py").read_text(encoding="utf-8")
        stage = source.split("SM_AUTOLAB_DASHBOARD_29917", 1)[1].split('if __name__ == "__main__":', 1)[0]
        self.assertNotIn("threading.Thread", stage)


# tests/test_saved_sheet_counter.py

class SavedSheetCounterTests(unittest.TestCase):
    def test_home_counter_conta_apenas_senhas_da_planilha_atual(self):
        class FakeLabel:
            def __init__(self):
                self.text = None
            def configure(self, **kwargs):
                self.text = kwargs.get("text")
            def winfo_manager(self):
                return "pack"
            def pack_configure(self, **kwargs):
                pass
            def pack_forget(self):
                self.text = None

        class AppStub:
            arquivos_contador_label = FakeLabel()
            _planilha_data = {
                "0,0": "10",
                "0,1": "senha-1",
                "0,2": "item",
                "1,1": "senha-2",
                "2,0": "20",
            }
            _planilha_arquivo = SimpleNamespace(exists=lambda: False)

        main._home_counter(AppStub)
        self.assertEqual(AppStub.arquivos_contador_label.text, "2 Códigos salvos")


# tests/test_status_indicator.py

class StatusIndicatorTests(unittest.TestCase):
    def test_pronto_mantem_pulso_verde(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('self._status_text_base == "Pronto"', source)
        self.assertIn("self._iniciar_pisca_status()", source)


# tests/test_tooltips.py

class TooltipRegressionTests(unittest.TestCase):
    class _FakeButton:
        def __init__(self, value):
            self.value = value

        def cget(self, name):
            if name != "text":
                raise KeyError(name)
            return self.value

    def test_none_nao_vira_tooltip_literal(self):
        self.assertIsNone(main._stage7_tooltip_text(self._FakeButton(None)))

    def test_texto_vazio_nao_cria_tooltip(self):
        self.assertIsNone(main._stage7_tooltip_text(self._FakeButton("   ")))

    def test_botao_conhecido_tem_descricao(self):
        self.assertEqual(
            main._stage7_tooltip_text(self._FakeButton("Iniciar")),
            "Inicia a automação com os códigos selecionados.",
        )

    def test_codigo_com_digitos_tem_descricao_de_copia(self):
        self.assertEqual(
            main._stage7_tooltip_text(self._FakeButton("ABC123")),
            "Clique para copiar este código.",
        )

    def test_texto_generico_nao_recebe_descricao_inventada(self):
        self.assertIsNone(main._stage7_tooltip_text(self._FakeButton("Botão genérico")))

    def test_menu_aparencia_tem_handler_para_filhos_internos(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("_iterar_descendentes_ui(aparencia)", block)
        self.assertIn("_abrir_aparencia_por_clique", block)
        self.assertIn('bind("<Button-1>", _abrir_aparencia_por_clique', block)

    def test_menu_aparencia_usa_deteccao_global_do_cursor(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _garantir_menu_aparencia_aberto_se_hover", start)
        block = source[start:end]
        self.assertIn('self.app.bind(', block)
        self.assertIn('" <Motion>"'.replace(" ",""), block)

    def test_menu_aparencia_abre_por_hover(self):
        source = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("_abrir_aparencia_por_hover", block)
        self.assertIn("_garantir_menu_aparencia_aberto", block)
        self.assertIn('bind("<Enter>", _abrir_aparencia_por_hover', block)

    def test_historico_de_erros_tem_tooltip(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        self.assertIn('"histórico de erros":', source)

    def test_iniciar_preserva_legenda(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        self.assertIn('text="▶  Iniciar"', source)

    def test_tooltip_cobre_filhos_internos_do_ctkbutton(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        start = source.index("class _SMAutoLabTooltip:")
        end = source.index("def _stage7_tooltip_text", start)
        block = source[start:end]
        self.assertIn("def _iter_widget_tree", block)
        self.assertIn("def _bind_widget_tree", block)
        self.assertIn('child.bind("<Enter>"', block)
        self.assertIn('child.bind("<Leave>"', block)
        self.assertIn("HIDE_GRACE_MS", block)
        self.assertIn("_pointer_inside_button", block)
