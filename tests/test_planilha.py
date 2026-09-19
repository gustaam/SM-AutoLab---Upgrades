import unittest
from pathlib import Path
from types import SimpleNamespace

from interface import (
    App,
    MAX_COLS,
    MAX_ROWS,
    SM_AUTOLAB_GRADE_VIRTUAL_29926,
    SM_AUTOLAB_WINDOWS_NATIVE_29925,
    _material_for_window,
    apply_paste,
    clear_cells,
    extract_column,
    filled_row_count,
    non_empty_cells,
    parse_paste_text,
    rectangle_selection,
    redo_state,
    undo_state,
    visible_row_range,
)

# tests/test_planilha_behavior.py

class FakeTree:
    def __init__(self, rows):
        self.rows = {str(k): list(v) for k, v in rows.items()}
        self._focus = next(iter(self.rows), "")

    def get_children(self):
        return tuple(self.rows)

    def focus(self):
        return self._focus

    def item(self, iid, mode=None, **kwargs):
        if "values" in kwargs:
            self.rows[str(iid)] = list(kwargs["values"])
        values = self.rows[str(iid)]
        return values if mode == "values" else {"values": tuple(values)}

    def __call__(self, iid, mode=None):
        return self.item(iid, mode)

    def set_focus(self, iid):
        self._focus = str(iid)


class PlanilhaBehaviorTests(unittest.TestCase):
    def _app(self, rows=None):
        app = App.__new__(App)
        app._planilha_data = {}
        app._planilha_undo = []
        app._planilha_redo = []
        app._planilha_tree = FakeTree(rows or {
            0: ("1", "ABC", "Item"),
            1: ("2", "DEF", "Outro"),
            2: ("", "", ""),
        })
        app._planilha_celulas_selecionadas = set()
        app._planilha_celula_ativa = None
        app._planilha_linhas_selecionadas = set()
        app._planilha_edit_entry = None
        app._changed = False
        app._planilha_atualizar_grade = lambda: None
        app._planilha_marcar_alteracao = lambda: setattr(app, "_changed", True)
        app._planilha_desenhar_borda = lambda: None
        app._planilha_fechar_edicao = lambda: None
        class Clipboard:
            value = ""
            def clipboard_get(self):
                return Clipboard.value
        app.app = Clipboard()
        return app

    def test_selecao_retangular_executa_operacao_real(self):
        app = self._app()
        self.assertEqual(
            App._planilha_retangulo_selecao(app, (1, 1), (2, 2)),
            {(1, 1), (1, 2), (2, 1), (2, 2)},
        )

    def test_copiar_e_colar_operam_sobre_armazenamento(self):
        app = self._app()
        app._planilha_data = {
            "0,0": "1", "0,1": "ABC", "0,2": "Item",
            "1,0": "2", "1,1": "DEF", "1,2": "Outro",
        }
        app._planilha_celulas_selecionadas = {(0, 0), (0, 1), (0, 2)}
        app._planilha_linhas_selecionadas = {"0"}
        app._planilha_celula_ativa = ("1", 0)

        captured = {"text": None}
        app.app.clipboard_clear = lambda: None
        app.app.clipboard_append = lambda value: captured.__setitem__("text", value)

        self.assertEqual(App._planilha_copiar(app), "break")
        self.assertEqual(captured["text"], "1\tABC\tItem")

        app.app.clipboard_get = lambda: "9\tXYZ\tNovo"
        self.assertEqual(App._planilha_colar(app), "break")
        self.assertEqual(app._planilha_data["1,0"], "9")
        self.assertEqual(app._planilha_data["1,1"], "XYZ")
        self.assertEqual(app._planilha_data["1,2"], "Novo")
        self.assertTrue(app._changed)

    def test_limpar_e_undo_redo_restauram_estado(self):
        app = self._app()
        app._planilha_data = {"0,0": "1", "0,1": "ABC", "1,1": "DEF"}
        app._planilha_celulas_selecionadas = {(0, 1)}

        self.assertEqual(App._planilha_limpar_celulas_selecionadas(app), "break")
        self.assertNotIn("0,1", app._planilha_data)

        # O fluxo real de edição registra o estado antes da mutação.
        app._planilha_push_undo()
        app._planilha_data["0,1"] = "ABC"
        app._planilha_redo = []
        App._planilha_desfazer(app)
        self.assertNotIn("0,1", app._planilha_data)

        App._planilha_refazer(app)
        self.assertEqual(app._planilha_data["0,1"], "ABC")

    def test_contador_e_extracao_de_senhas_usam_dados_reais(self):
        app = self._app()
        app._planilha_data = {
            "0,0": "1",
            "0,1": "ABC",
            "2,1": "DEF",
            "4,2": "Item",
            "9,1": " ",
        }
        class Label:
            def __init__(self): self.text = None
            def configure(self, **kwargs): self.text = kwargs["text"]
        app._planilha_contador_label = Label()

        App._planilha_atualizar_contador(app)
        self.assertEqual(app._planilha_contador_label.text, "3 linhas preenchidas")
        self.assertEqual(App._extrair_codigos_planilha(app), ["ABC", "DEF"])

    def test_selecionar_tudo_seleciona_apenas_celulas_preenchidas(self):
        app = self._app()
        app._planilha_data = {"0,0": "1", "0,1": "ABC", "2,2": "Item"}
        App._planilha_selecionar_tudo(app)
        self.assertEqual(
            app._planilha_celulas_selecionadas,
            {(0, 0), (0, 1), (2, 2)},
        )


# tests/test_planilha_core.py

class PlanilhaCoreTests(unittest.TestCase):
    def test_retangulo_de_selecao_e_inclusivo_e_limitado(self):
        self.assertEqual(
            rectangle_selection((2, 1), (4, 2)),
            {(2, 1), (2, 2), (3, 1), (3, 2), (4, 1), (4, 2)},
        )
        self.assertEqual(
            rectangle_selection((-2, -1), (1, 1)),
            {(0, 0), (0, 1), (1, 0), (1, 1)},
        )
        self.assertEqual(rectangle_selection((MAX_ROWS, 0), (MAX_ROWS + 2, 2)), set())

    def test_non_empty_cells_descarta_invalidos_e_vazios(self):
        cells = {
            "0,0": "Qtd",
            "1,1": "ABC",
            "2,2": " ",
            "bad": "x",
            "10000,0": "fora",
            "-1,0": "fora",
            "0,3": "fora",
        }
        self.assertEqual(non_empty_cells(cells), {(0, 0), (1, 1)})
        self.assertEqual(filled_row_count(cells), 2)

    def test_parse_paste_com_tab_e_normaliza_quebras(self):
        self.assertEqual(
            parse_paste_text("1\tABC\tItem 1\r\n2\tDEF\tItem 2\r\n"),
            [["1", "ABC", "Item 1"], ["2", "DEF", "Item 2"]],
        )

    def test_parse_paste_sem_tab_preserva_item_com_espacos(self):
        self.assertEqual(
            parse_paste_text("1 ABC Item completo\n2 DEF Outro item"),
            [["1", "ABC", "Item completo"], ["2", "DEF", "Outro item"]],
        )

    def test_parse_paste_vazio_retorna_lista_vazia(self):
        self.assertEqual(parse_paste_text(" \r\n"), [[" "]])
        self.assertEqual(parse_paste_text(""), [])

    def test_apply_paste_esparso_e_remove_celula_vazia(self):
        original = {"0,0": "1", "0,1": "ABC", "4,2": "Item"}
        result, changed = apply_paste(
            original,
            [["2", "DEF", "Novo"]],
            start_row=0,
            start_col=0,
        )
        self.assertTrue(changed)
        self.assertEqual(
            result,
            {"0,0": "2", "0,1": "DEF", "0,2": "Novo", "4,2": "Item"},
        )

        result, changed = apply_paste(
            result,
            [["", "", ""]],
            start_row=0,
            start_col=0,
        )
        self.assertTrue(changed)
        self.assertNotIn("0,0", result)
        self.assertNotIn("0,1", result)
        self.assertNotIn("0,2", result)

    def test_apply_paste_respeita_limites(self):
        result, changed = apply_paste(
            {"9999,2": "fim"},
            [["A", "B", "C"], ["D", "E", "F"]],
            start_row=9999,
            start_col=2,
        )
        self.assertTrue(changed)
        self.assertEqual(result.get("9999,2"), "A")
        self.assertNotIn("10000,2", result)
        self.assertEqual(MAX_COLS, 3)

    def test_clear_cells_remove_apenas_selecao_preenchida(self):
        original = {"0,0": "1", "0,1": "ABC", "1,1": "DEF"}
        result, changed = clear_cells(original, {(0, 1), (1, 0), (8, 8)})
        self.assertTrue(changed)
        self.assertEqual(result, {"0,0": "1", "1,1": "DEF"})

        result, changed = clear_cells(result, {(1, 0)})
        self.assertFalse(changed)
        self.assertEqual(result, {"0,0": "1", "1,1": "DEF"})

    def test_extract_column_ordena_por_linha(self):
        cells = {"5,1": "555", "1,1": "111", "3,0": "x", "4,1": "   "}
        self.assertEqual(extract_column(cells, 1), ["111", "555"])

    def test_undo_e_redo_sao_puros_e_preservam_snapshots(self):
        original = {"0,0": "A"}
        changed = {"0,0": "B"}
        state = undo_state([original], [], changed)
        self.assertEqual(state[0], [])
        self.assertEqual(state[1], [changed])
        self.assertEqual(state[2], original)

        state = redo_state(state[0], state[1], state[2])
        self.assertEqual(state[0], [original])
        self.assertEqual(state[1], [])
        self.assertEqual(state[2], changed)

    def test_undo_sem_historico_nao_altera_estado(self):
        self.assertIsNone(undo_state([], [], {"0,0": "A"}))
        self.assertIsNone(redo_state([], [], {"0,0": "A"}))


# tests/test_planilha_deterministic_open.py

class PlanilhaDeterministicOpenTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_abertura_e_interacao_estao_na_implementacao_canonica(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        patch = (self.root / "patch.py").read_text(encoding="utf-8")
        self.assertIn("def abrir_planilha(self, dados_iniciais=None):", interface)
        self.assertIn('self._planilha_implementacao = "grade-virtual-29926"', interface)
        self.assertIn('tree=VirtualGridTree(', interface)
        self.assertIn('tree.bind("<ButtonPress-1>", self._planilha_clicar_celula, add="+")', interface)
        self.assertIn('tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")', interface)
        self.assertIn('tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")', interface)
        self.assertIn("self._planilha_desenhar_borda()", interface)
        self.assertNotIn("def _abrir_planilha_2991", patch)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_297", patch)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_2991", patch)

    def test_virtualizacao_substitui_povoamento_incremental(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def abrir_planilha")
        end = interface.index("    def _planilha_stage9_get_grid_state", start)
        block = interface[start:end]
        self.assertIn("VirtualGridTree(", block)
        self.assertIn("value_provider=", block)
        self.assertIn('self._planilha_implementacao = "grade-virtual-29926"', block)
        self.assertNotIn("def _povoar_lote():", block)
        self.assertNotIn("for i in range(300):", block)
        self.assertNotIn("fim = min(10000, inicio + 500)", block)
        self.assertNotIn("tree.insert(", block)
        self.assertNotIn("_planilha_povoamento_", interface)

    def test_snapshot_historico_reutiliza_a_mesma_abertura(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def _mostrar_planilhas_do_dia")
        end = interface.index("def abrir_historico_planilha", start)
        block = interface[start:end]
        self.assertIn("command=lambda it=item: self._excluir_historico_planilha(it)", block)

        # A rota do snapshot deve convergir para abrir_planilha(), sem criar
        # um Treeview alternativo.
        snapshot_start = interface.index("def _preparar_planilha_do_dia")
        snapshot_end = interface.index("def _fechar_historico_planilha", snapshot_start)
        snapshot_block = interface[snapshot_start:snapshot_end]
        self.assertIn("self.abrir_planilha(cells)", snapshot_block)


# tests/test_planilha_grid.py

class PlanilhaGridSelectionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_pastas_do_historico_sao_quadradas(self):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text(encoding="utf-8")
        start = source.index("def _create_history_tile")
        end = source.index("def _restore_history", start)
        block = source[start:end]
        self.assertIn("width=108", block)
        self.assertIn("height=108", block)
        self.assertNotIn("width=128", block)
        self.assertNotIn("height=104", block)

    def test_grade_visual_e_selecao_estao_na_implementacao_canonica(self):
        interface = (self.root / "interface.py").read_text(encoding="utf-8")
        patch = (self.root / "patch.py").read_text(encoding="utf-8")
        for marker in (
            'SM_AUTOLAB_GRADE_29922 = "SM-AUTOLAB-GRADE-PERFORMANCE-29922"',
            "def _planilha_desenhar_grade",
            "def _planilha_stage9_get_visible_rows",
            "def _planilha_desenhar_borda",
            "_planilha_celulas_selecionadas",
        ):
            self.assertIn(marker, interface)
        self.assertIn('tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")', interface)
        self.assertIn('tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")', interface)
        self.assertNotIn("_planilha_clicar_celula_2991", patch)
        self.assertNotIn("_planilha_arrastar_selecao_2991", patch)
        self.assertNotIn("_planilha_soltar_selecao_2991", patch)

    def test_grade_e_reutilizavel_e_nao_percorre_10000_linhas_para_desenho(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _planilha_desenhar_grade")
        end = source.index("    def _planilha_atualizar_contador", start)
        block = source[start:end]
        self.assertIn("_planilha_stage9_get_visible_rows(tree)", block)
        self.assertNotIn("range(10000)", block)

    def test_selecao_multipla_tem_moldura_por_celula_em_selecoes_pequenas(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _planilha_desenhar_borda")
        end = source.index("    def _planilha_desenhar_grade", start)
        block = source[start:end]
        self.assertIn("len(normalized) <= 250", block)
        self.assertIn("segmentos.extend", block)
        self.assertIn("frame.lift()", block)


# tests/test_planilha_open_path.py

class PlanilhaOpenPathTests(unittest.TestCase):
    def test_abrir_planilha_tem_uma_unica_implementacao(self):
        root = Path(__file__).resolve().parents[1]
        interface = (root / "interface.py").read_text(encoding="utf-8")
        main = (root / "main.py").read_text(encoding="utf-8")
        patch = (root / "patch.py").read_text(encoding="utf-8")

        self.assertEqual(interface.count("    def abrir_planilha(self, dados_iniciais=None):"), 1)
        self.assertNotIn("App.abrir_planilha = _abrir_planilha_297", patch)
        self.assertNotIn("App.abrir_planilha = open_planilha_wrapper", main)
        self.assertNotIn("def _abrir_planilha_2991", patch)
        self.assertNotIn("App._planilha_clicar_celula = _planilha_clicar_celula_2991", patch)
        self.assertNotIn("App._planilha_arrastar_selecao = _planilha_arrastar_selecao_2991", patch)
        self.assertNotIn("App._planilha_soltar_selecao = _planilha_soltar_selecao_2991", patch)
        self.assertIn('self._planilha_implementacao = "grade-virtual-29926"', interface)
        self.assertIn("class VirtualGridTree", interface)
        self.assertIn('tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")', interface)
        self.assertIn('tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")', interface)
        self.assertIn("self.abrir_planilha(cells)", interface)



    def test_atalhos_de_edicao_da_grade_estao_robustos(self):
        interface = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        for binding in (
            'tree.bind("<Control-KeyPress-z>", self._planilha_atalho_desfazer, add="+")',
            'tree.bind("<Control-KeyPress-y>", self._planilha_atalho_refazer, add="+")',
            'tree.bind("<Control-KeyPress-a>", self._planilha_atalho_selecionar_tudo, add="+")',
            'tree.bind("<Control-KeyPress-c>", self._planilha_atalho_copiar, add="+")',
            'tree.bind("<Control-KeyPress-x>", self._planilha_recortar, add="+")',
            'tree.bind("<Delete>", self._planilha_atalho_excluir, add="+")',
            'tree.bind("<BackSpace>", self._planilha_atalho_excluir, add="+")',
            'tree.bind("<Control-KeyPress-v>", self._planilha_atalho_colar, add="+")',
        ):
            self.assertIn(binding, interface)
        self.assertIn("def _planilha_atalho_desfazer", interface)
        self.assertIn("def _planilha_atalho_refazer", interface)
        self.assertIn("def _planilha_atalho_selecionar_tudo", interface)
        self.assertIn("def _planilha_atalho_copiar", interface)
        self.assertIn("def _planilha_recortar", interface)
        self.assertIn("def _planilha_atalho_excluir", interface)
        self.assertIn("def _planilha_tem_entry_em_foco", interface)

    def test_ctrl_v_tem_fallback_local_global_e_virtual(self):
        interface = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        self.assertIn('tree.bind("<Control-KeyPress-v>", self._planilha_atalho_colar, add="+")', interface)
        self.assertIn('tree.bind("<Control-KeyPress-V>", self._planilha_atalho_colar, add="+")', interface)
        self.assertIn('tree.bind("<<Paste>>", self._planilha_atalho_colar, add="+")', interface)
        self.assertIn("def _planilha_colar_teclado(self, event=None):", interface)
        self.assertIn('self.app.bind_all(\n                "<Control-KeyPress-v>"', interface)
        self.assertIn('self.app.bind_all(\n                "<Control-KeyPress-V>"', interface)
        self.assertIn("def _planilha_foco_pertence_a_grade(self):", interface)
        self.assertIn("def _planilha_colar_entry(self, event=None):", interface)

    def test_entry_da_edicao_tem_paste_proprio(self):
        interface = (Path(__file__).resolve().parents[1] / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def _planilha_editar_iid")
        end = interface.index("def _planilha_copiar", start)
        block = interface[start:end]
        self.assertIn('entry.bind("<Control-KeyPress-v>", self._planilha_colar_entry, add="+")', block)
        self.assertIn('entry.bind("<<Paste>>", self._planilha_colar_entry, add="+")', block)

    def test_snapshot_historico_reutiliza_a_mesma_abertura(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _abrir_snapshot_historico")
        end = source.index("def _fechar_historico_planilha", start)
        block = source[start:end]
        self.assertIn("self.abrir_planilha(cells)", block)


# tests/test_stage12.py

class Windows11NativeStage12Tests(unittest.TestCase):
    def test_stage12_marker(self):
        self.assertEqual(
            SM_AUTOLAB_WINDOWS_NATIVE_29925,
            "SM-AUTOLAB-WINDOWS-NATIVE-29925",
        )

    def test_material_hierarchy(self):
        class Root:
            def title(self):
                return "SM AutoLab"

        class Secondary:
            def __init__(self, title):
                self._title = title

            def title(self):
                return self._title

        root = Root()
        self.assertEqual(_material_for_window(root, root), "mica")
        self.assertEqual(
            _material_for_window(Secondary("Planilha — SM AutoLab"), root),
            "mica_alt",
        )
        self.assertEqual(
            _material_for_window(Secondary("Mudar o Feegow"), root),
            "acrylic",
        )

    def test_main_build_and_workflows_integrate_stage12(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "main.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        validate = (root / ".github" / "workflows" / "validate-main.yml").read_text(encoding="utf-8")
        release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("install_ui_windows11_native_29925", main)
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            build,
        )
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            validate,
        )
        self.assertIn(
            "from interface import App; from main import install_ui, _validar_base_aplicacao",
            release,
        )

    def test_native_layer_has_accessibility_and_dwm_paths(self):
        source = (
            Path(__file__).resolve().parents[1] / "interface.py"
        ).read_text(encoding="utf-8")
        self.assertIn("SystemParametersInfoW", source)
        self.assertIn("DwmSetWindowAttribute", source)
        self.assertIn("SetWindowTheme", source)
        self.assertIn("DWMWA_SYSTEMBACKDROP_TYPE", source)
        self.assertIn("DWMWCP_ROUND", source)


# tests/test_stage13.py

class VirtualGridStage13Tests(unittest.TestCase):
    def test_marker(self):
        self.assertEqual(
            SM_AUTOLAB_GRADE_VIRTUAL_29926,
            "SM-AUTOLAB-GRADE-VIRTUAL-29926",
        )

    def test_visible_range_is_small_even_for_ten_thousand_rows(self):
        start, end = visible_row_range(
            first_fraction=0.5,
            viewport_height=280,
            total_rows=10000,
            row_height=28,
            overscan=3,
        )
        self.assertEqual((start, end), (4992, 5008))
        self.assertLess(end - start, 100)

    def test_visible_range_clamps_at_document_edges(self):
        self.assertEqual(
            visible_row_range(0.0, 280, 10000, 28, 3),
            (0, 16),
        )
        self.assertEqual(
            visible_row_range(1.0, 280, 10000, 28, 3),
            (9984, 10000),
        )

    def test_interface_uses_virtual_grid_without_ten_thousand_insertions(self):
        root = Path(__file__).resolve().parents[1]
        interface = (root / "interface.py").read_text(encoding="utf-8")
        start = interface.index("def abrir_planilha")
        end = interface.index("    def _planilha_stage9_get_grid_state", start)
        block = interface[start:end]

        self.assertIn("VirtualGridTree(", block)
        self.assertIn("value_provider=", block)
        self.assertIn("total_rows=10000", block)
        self.assertIn('self._planilha_implementacao = "grade-virtual-29926"', block)
        self.assertNotIn("ttk.Treeview(body", block)
        self.assertNotIn("range(10000)", block)
        self.assertNotIn("range(300)", block)
        self.assertNotIn("tree.insert(", block)

    def test_virtual_grid_refreshes_a_bounded_pool(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        refresh_start = source.index("def _refresh_visible")
        refresh_end = source.index(
            "    def _update_scroll_callbacks",
            refresh_start,
        )
        refresh = source[refresh_start:refresh_end]
        self.assertIn("visible_row_range(", refresh)
        self.assertIn("for offset, slot in enumerate(self._pool):", refresh)
        self.assertNotIn("range(self._total_rows)", refresh)

    def test_mouse_hit_testing_uses_canvas_coordinates_without_header_offset(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "interface.py").read_text(encoding="utf-8")
        identify_start = source.index("    def identify_row")
        identify_end = source.index("    def identify_column", identify_start)
        identify = source[identify_start:identify_end]
        self.assertIn("canvasy(float(y))", identify)
        self.assertNotIn("body_y = float(y) - self._header_height", identify)

    def test_main_build_and_validation_keep_single_ui_entry(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "main.py").read_text(encoding="utf-8")
        build = (root / "build_windows.bat").read_text(encoding="utf-8")
        validate = (root / ".github" / "workflows" / "validate-main.yml").read_text(encoding="utf-8")
        release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_GRADE_VIRTUAL_29926", main)
        for source in (build, validate, release):
            self.assertIn("install_ui(App); _validar_base_aplicacao()", source)
