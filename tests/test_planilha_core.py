import unittest

from planilha_core import (
    MAX_COLS,
    MAX_ROWS,
    apply_paste,
    clear_cells,
    extract_column,
    filled_row_count,
    non_empty_cells,
    parse_paste_text,
    rectangle_selection,
    redo_state,
    undo_state,
)


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
        self.assertEqual(result.get("9999,2"), "C")
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


if __name__ == "__main__":
    unittest.main()
