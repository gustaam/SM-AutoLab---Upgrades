import unittest
from pathlib import Path

from interface import (
    SM_AUTOLAB_GRADE_VIRTUAL_29926,
    visible_row_range,
)


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


if __name__ == "__main__":
    unittest.main()
