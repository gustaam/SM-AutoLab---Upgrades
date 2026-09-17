from __future__ import annotations

from datetime import datetime

import customtkinter as ctk


SM_AUTOLAB_UI_FIXES_29912 = "SM-AUTOLAB-2.99.12-UI-FIXES"


def _widget_inside(widget, ancestor):
    if widget is None or ancestor is None:
        return False
    try:
        child = str(widget)
        parent = str(ancestor)
    except Exception:
        return False
    return child == parent or child.startswith(parent + ".")


def _walk_children(widget):
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _walk_children(child)


def _home_counter(self):
    label = getattr(self, "arquivos_contador_label", None)
    if label is None:
        return

    total = 0
    try:
        total = int(self._count_saved_passwords() or 0)
    except Exception:
        pass
    if total <= 0:
        try:
            total = int(self._contar_codigos_mes(datetime.now()) or 0)
        except Exception:
            total = 0

    try:
        label.configure(text=f"{total} códigos no mês")
        label.pack_configure(side="left", padx=(8, 0))
    except Exception:
        pass


def _clear_history_selection(self):
    selected = getattr(self, "_hist_selected_tiles", set())
    if not isinstance(selected, set):
        selected = set()
        self._hist_selected_tiles = selected
    for tile in tuple(selected):
        try:
            tile.configure(border_color=self.BORDER, border_width=1, fg_color=self.CARD)
        except Exception:
            pass
    selected.clear()
    self._hist_selected_tile = None


def _select_history_tile(self, tile, ctrl=False):
    selected = getattr(self, "_hist_selected_tiles", set())
    if not isinstance(selected, set):
        selected = set()
        self._hist_selected_tiles = selected

    if ctrl:
        if tile in selected:
            selected.remove(tile)
        else:
            selected.add(tile)
    else:
        for other in tuple(selected):
            if other is not tile:
                try:
                    other.configure(border_color=self.BORDER, border_width=1, fg_color=self.CARD)
                except Exception:
                    pass
        selected.clear()
        selected.add(tile)

    self._hist_selected_tile = tile if tile in selected else None
    for other in tuple(selected):
        try:
            other.configure(
                border_color=self.ACCENT,
                border_width=1,
                fg_color=("#EAF4FF", "#1B3C53"),
            )
        except Exception:
            pass


def _bind_history_tile(self, tile):
    execucao = getattr(tile, "_sm_execucao", None)
    if execucao is None:
        return

    def on_click(event=None, current=tile):
        ctrl = bool(getattr(event, "state", 0) & 0x0004) if event is not None else False
        _select_history_tile(self, current, ctrl=ctrl)
        return "break"

    def on_double_click(_event=None, item=execucao, current=tile):
        _select_history_tile(self, current, ctrl=False)
        self._abrir_detalhe_historico(item)
        return "break"

    def on_enter(_event=None, current=tile):
        if current in getattr(self, "_hist_selected_tiles", set()):
            return
        try:
            current.configure(border_color=self.ACCENT_HOVER, fg_color=("#F3F3F3", "#3A3A3A"))
        except Exception:
            pass

    def on_leave(_event=None, current=tile):
        if current in getattr(self, "_hist_selected_tiles", set()):
            return
        try:
            current.configure(border_color=self.BORDER, fg_color=self.CARD)
        except Exception:
            pass

    for widget in _walk_children(tile):
        try:
            for sequence in ("<Button-1>", "<Double-Button-1>", "<Double-1>", "<Enter>", "<Leave>"):
                widget.unbind(sequence)
            widget.bind("<Button-1>", on_click)
            widget.bind("<Double-Button-1>", on_double_click)
            widget.bind("<Double-1>", on_double_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        except Exception:
            pass


def _create_history_tile(self, execucao, atual=False):
    parent = getattr(self, "historico_lista", None)
    if parent is None:
        return

    if not hasattr(self, "_hist_tiles"):
        self._hist_tiles = set()
    if not hasattr(self, "_hist_selected_tiles"):
        self._hist_selected_tiles = set()

    grid = getattr(self, "_hist_grid", None)
    try:
        valid_grid = grid is not None and grid.winfo_exists()
    except Exception:
        valid_grid = False
    if not valid_grid:
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(anchor="center", pady=(6, 8))
        self._hist_grid = grid

    count = len(grid.winfo_children())
    row, col = divmod(count, 5)

    tile = ctk.CTkFrame(
        grid,
        fg_color=self.CARD,
        corner_radius=8,
        border_width=1,
        border_color=self.BORDER,
        width=118,
        height=94,
    )
    tile.grid(row=row, column=col, padx=5, pady=5)
    tile.grid_propagate(False)
    tile._sm_execucao = execucao
    self._hist_tiles.add(tile)

    inicio = str(execucao.get("inicio", ""))
    status = str(execucao.get("status", ""))
    erros = int(execucao.get("erros", 0) or 0)
    dia = inicio.split(" ")[0] if inicio else ""
    hora = inicio.split(" ")[1] if " " in inicio else ""

    ctk.CTkLabel(tile, text="📁", font=("Segoe UI Emoji", 19), text_color=self.ACCENT).pack(pady=(5, 0))
    ctk.CTkLabel(tile, text=dia, text_color=self.TEXT, font=("Segoe UI", 9, "bold")).pack()
    ctk.CTkLabel(tile, text=hora, text_color=self.SUBTEXT, font=("Segoe UI", 8)).pack()
    ctk.CTkLabel(
        tile,
        text=f"{status} • {erros}",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8),
        wraplength=102,
    ).pack(pady=(2, 0))

    _bind_history_tile(self, tile)


def _restore_history(self, *args, **kwargs):
    result = self._ui_29912_original_restore(*args, **kwargs)
    try:
        self._hist_selected_tiles = set()
        self._hist_selected_tile = None
        for tile in tuple(getattr(self, "_hist_tiles", set())):
            _bind_history_tile(self, tile)
    except Exception:
        pass
    return result


def _calendar_click(self, event):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return "break"

    data = None
    try:
        items = canvas.find_overlapping(event.x, event.y, event.x, event.y)
    except Exception:
        items = ()
    for item_id in reversed(items):
        try:
            for tag in canvas.gettags(item_id):
                if str(tag).startswith("dia:"):
                    data = datetime.fromisoformat(str(tag)[4:]).date()
                    break
        except Exception:
            continue
        if data is not None:
            break
    if data is None:
        return "break"

    try:
        por_dia = self._dados_arquivos_por_dia()
    except Exception:
        por_dia = {}
    if data not in por_dia:
        return "break"

    ctrl = bool(getattr(event, "state", 0) & 0x0004)
    if ctrl or getattr(self, "_arquivos_modo_selecao", False):
        self._toggle_data_selecionada(data)
        return "break"

    selecionadas = getattr(self, "_arquivos_datas_selecionadas", None)
    if selecionadas:
        try:
            selecionadas.clear()
            self._cancelar_animacao_selecao()
            self._atualizar_contador_selecao()
            self._desenhar_calendario_arquivos()
        except Exception:
            pass
    self._mostrar_planilhas_do_dia(data)
    return "break"


def _global_click(self, event=None):
    widget = getattr(event, "widget", None) if event is not None else None

    selected_tiles = getattr(self, "_hist_selected_tiles", set())
    if selected_tiles and not any(_widget_inside(widget, tile) for tile in tuple(selected_tiles)):
        _clear_history_selection(self)

    selected_dates = getattr(self, "_arquivos_datas_selecionadas", set())
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if selected_dates and canvas is not None and not _widget_inside(widget, canvas):
        try:
            selected_dates.clear()
            self._cancelar_animacao_selecao()
            self._atualizar_contador_selecao()
            self._desenhar_calendario_arquivos()
        except Exception:
            pass


def install(App):
    if getattr(App, "_ui_29912_aplicado", False):
        return
    App._ui_29912_aplicado = True
    App._ui_29912_marker = SM_AUTOLAB_UI_FIXES_29912

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _home_counter(self))
        except Exception:
            _home_counter(self)
        return result

    App.config_app = config_wrapper

    original_save_exit = App._planilha_salvar_e_sair

    def save_exit_wrapper(self, *args, **kwargs):
        result = original_save_exit(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _home_counter(self))
        except Exception:
            _home_counter(self)
        return result

    App._planilha_salvar_e_sair = save_exit_wrapper

    original_save_start = getattr(App, "_planilha_salvar_e_iniciar", None)
    if original_save_start is not None:
        def save_start_wrapper(self, *args, **kwargs):
            result = original_save_start(self, *args, **kwargs)
            try:
                self.app.after_idle(lambda: _home_counter(self))
            except Exception:
                _home_counter(self)
            return result
        App._planilha_salvar_e_iniciar = save_start_wrapper

    App._criar_pasta_historico = _create_history_tile
    App._ui_29912_original_restore = App._restaurar_historico_na_tela
    App._restaurar_historico_na_tela = _restore_history
    App._clique_calendario_arquivos = _calendar_click
    App._atualizar_contador_principal_29912 = _home_counter

    original_global_config = App.config_app

    def global_config_wrapper(self, *args, **kwargs):
        result = original_global_config(self, *args, **kwargs)
        try:
            if not getattr(self, "_ui_29912_global_binding", False):
                self.app.bind_all("<Button-1>", lambda event: _global_click(self, event), add="+")
                self._ui_29912_global_binding = True
        except Exception:
            pass
        return result

    App.config_app = global_config_wrapper
