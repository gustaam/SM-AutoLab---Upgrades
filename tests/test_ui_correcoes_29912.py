import unittest
from datetime import date
from types import SimpleNamespace

import main

_calendar_click = main._calendar_click
_ctrl_pressed = main._ctrl_pressed
_home_counter = main._home_counter
_select_history_tile = main._select_history_tile


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


class UIFixes29912Tests(unittest.TestCase):
    def test_ctrl_pressed_uses_control_mask(self):
        self.assertTrue(_ctrl_pressed(SimpleNamespace(state=0x0004)))
        self.assertFalse(_ctrl_pressed(SimpleNamespace(state=0)))

    def test_home_counter_uses_only_saved_passwords(self):
        label = FakeLabel()

        class AppStub:
            arquivos_contador_label = label

            def _count_saved_passwords(self):
                return 7

            def _contar_codigos_mes(self, _referencia=None):
                raise AssertionError("contador mensal não deve ser usado")

        _home_counter(AppStub())
        self.assertEqual(label.configured[-1]["text"], "7 Códigos salvos")
        self.assertTrue(label.packed)

    def test_home_counter_hides_when_empty(self):
        label = FakeLabel()

        class AppStub:
            arquivos_contador_label = label

            def _count_saved_passwords(self):
                return 0

        _home_counter(AppStub())
        self.assertFalse(label.packed)

    def test_home_counter_reappears_after_being_hidden(self):
        label = FakeLabel()
        label.packed = False

        class AppStub:
            arquivos_contador_label = label

            def _count_saved_passwords(self):
                return 3

        _home_counter(AppStub())
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

        _select_history_tile(app, first, ctrl=False)
        _select_history_tile(app, second, ctrl=True)
        self.assertEqual(app._hist_selected_tiles, {first, second})

        _select_history_tile(app, first, ctrl=True)
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

        _calendar_click(AppStub(), SimpleNamespace(state=0x0004, x=10, y=10))
        self.assertEqual(calls, [("toggle", target)])


if __name__ == "__main__":
    unittest.main()
