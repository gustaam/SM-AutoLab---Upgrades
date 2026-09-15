from __future__ import annotations

import tkinter as tk

import customtkinter as ctk


PATCH_299_MARKER = "SM-AUTOLAB-SELECTION-STABILITY-FIX"


def _iter_descendants(widget):
    if widget is None:
        return
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        yield from _iter_descendants(child)


def _is_descendant(widget, ancestor):
    if widget is None or ancestor is None:
        return False
    current = widget
    while current is not None:
        if current is ancestor:
            return True
        try:
            current = current.nametowidget(current.winfo_parent())
        except Exception:
            return False
    return False


def _history_clear_selection_299(self):
    previous = getattr(self, "_hist_selected_tile", None)
    if previous is not None:
        try:
            previous.configure(
                border_color=self.BORDER,
                border_width=1,
                fg_color=("#FFFFFF", "#2D3338"),
            )
        except Exception:
            pass
    self._hist_selected_tile = None


def _history_select_tile_299(self, tile):
    previous = getattr(self, "_hist_selected_tile", None)
    if previous is tile:
        return
    if previous is not None:
        try:
            previous.configure(
                border_color=self.BORDER,
                border_width=1,
                fg_color=("#FFFFFF", "#2D3338"),
            )
        except Exception:
            pass
    self._hist_selected_tile = tile
    try:
        tile.configure(
            border_color=self.ACCENT,
            border_width=1,
            fg_color=("#EAF4FF", "#1B3C53"),
        )
    except Exception:
        pass


def _history_rebind_open_299(self):
    """Rebinds history folders without accumulating callbacks on every redraw."""
    for tile in tuple(getattr(self, "_hist_tiles", set())):
        execucao = getattr(tile, "_sm_execucao", None)
        if execucao is None:
            continue

        def abrir(event=None, item=execucao, f=tile):
            _history_select_tile_299(self, f)
            self._abrir_detalhe_historico(item)
            return "break"

        for widget in _iter_descendants(tile):
            try:
                # Important: no add="+". Repeated history redraws must not
                # stack identical callbacks and make a second click execute
                # the same action many times.
                widget.bind("<Enter>", lambda _event: None)
                widget.bind("<Leave>", lambda _event: None)
                widget.bind("<Button-1>", abrir)
            except Exception:
                pass


def _history_click_outside_299(self, event=None):
    widget = getattr(event, "widget", None) if event is not None else None
    for tile in tuple(getattr(self, "_hist_tiles", set())):
        if _is_descendant(widget, tile):
            return
    _history_clear_selection_299(self)


def _restaurar_historico_299(self, *args, **kwargs):
    result = self._patch299_original_restaurar_historico(*args, **kwargs)
    _history_rebind_open_299(self)
    lista = getattr(self, "historico_lista", None)
    if lista is not None:
        # A single stable binding on the history container handles clicks
        # outside any folder. The folder bindings above handle clicks inside.
        try:
            lista.bind("<Button-1>", lambda event: _history_click_outside_299(self, event))
        except Exception:
            pass
    return result


def _instalar_deselecao_global_299(self):
    """Deselects the active item when left-clicking outside its own widget."""
    if getattr(self, "_patch299_global_binding", False):
        return
    self._patch299_global_binding = True

    def on_click(event=None):
        widget = getattr(event, "widget", None) if event is not None else None

        # Histórico: folder selection is cleared outside the selected folder.
        for tile in tuple(getattr(self, "_hist_tiles", set())):
            if _is_descendant(widget, tile):
                break
        else:
            _history_clear_selection_299(self)

        # Arquivos: Ctrl+click multi-selection remains intact when clicking
        # inside a selected calendar cell. Clicking elsewhere clears it.
        selected_dates = getattr(self, "_arquivos_datas_selecionadas", None)
        canvas = getattr(self, "_arquivos_calendar_canvas", None)
        if selected_dates and canvas is not None:
            if not _is_descendant(widget, canvas):
                try:
                    selected_dates.clear()
                    self._formatar_contador_selecao()
                    self._cancelar_animacao_selecao()
                    self._desenhar_calendario_arquivos()
                except Exception:
                    pass

        # Planilha: clear the active cell unless the click is inside the
        # currently active cell/editor or the spreadsheet itself is handling
        # a new cell click.
        active = getattr(self, "_planilha_celula_ativa", None)
        tree = getattr(self, "_planilha_tree", None)
        if active and tree is not None:
            if not _is_descendant(widget, tree):
                try:
                    self._planilha_celula_ativa = None
                    if hasattr(self, "_planilha_borda_widgets"):
                        for border in list(self._planilha_borda_widgets):
                            try:
                                border.destroy()
                            except Exception:
                                pass
                        self._planilha_borda_widgets = []
                except Exception:
                    pass

    try:
        self.app.bind_all("<Button-1>", on_click, add="+")
    except Exception:
        self._patch299_global_binding = False


def _config_app_299(self, *args, **kwargs):
    result = self._patch299_original_config_app(*args, **kwargs)
    self.app.after_idle(lambda: _instalar_deselecao_global_299(self))
    return result


def aplicar_patch_299(App):
    if getattr(App, "_patch_299_aplicado", False):
        return
    App._patch_299_aplicado = True

    App._patch299_original_config_app = App.config_app
    App.config_app = _config_app_299

    # Replace the patch-298 rebinder that accumulated callbacks with each
    # history refresh and also restore the intended no-hover interaction.
    App._history_rebind_open = _history_rebind_open_299
    App._restaurar_historico_na_tela = _restaurar_historico_299
