from __future__ import annotations

import customtkinter as ctk


PATCH_299_MARKER = "SM-AUTOLAB-SELECTION-STABILITY-FIX"


def _iter_descendants(widget):
    """Percorre um widget e seus filhos de forma segura."""
    if widget is None:
        return
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _iter_descendants(child)


def _widget_inside(widget, ancestor):
    """Retorna True quando widget é o próprio ancestor ou um filho dele."""
    if widget is None or ancestor is None:
        return False
    try:
        widget_path = str(widget)
        ancestor_path = str(ancestor)
    except Exception:
        return False
    return widget_path == ancestor_path or widget_path.startswith(ancestor_path + ".")


def _widget_exists(widget):
    try:
        return bool(widget is not None and widget.winfo_exists())
    except Exception:
        return False


def _history_clear_selection_299(self):
    previous = getattr(self, "_hist_selected_tile", None)
    if previous is not None and _widget_exists(previous):
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
    if previous is not None and _widget_exists(previous):
        try:
            previous.configure(
                border_color=self.BORDER,
                border_width=1,
                fg_color=("#FFFFFF", "#2D3338"),
            )
        except Exception:
            pass
    self._hist_selected_tile = tile
    if _widget_exists(tile):
        try:
            tile.configure(
                border_color=self.ACCENT,
                border_width=1,
                fg_color=("#EAF4FF", "#1B3C53"),
            )
        except Exception:
            pass


def _history_open_once_299(self, event=None, execucao=None, tile=None):
    """Abre uma pasta somente pelo clique, sem callbacks acumulados."""
    if tile is not None:
        _history_select_tile_299(self, tile)
    if execucao is not None:
        self._abrir_detalhe_historico(execucao)
    return "break"


def _history_hover_299(tile, entering, self):
    """Aplica o mesmo feedback visual de hover dos demais controles."""
    if not _widget_exists(tile) or getattr(self, "_hist_selected_tile", None) is tile:
        return
    try:
        if entering:
            tile.configure(
                border_color=self.ACCENT_HOVER,
                border_width=1,
                fg_color=("#F3F3F3", "#3A3A3A"),
            )
        else:
            tile.configure(
                border_color=self.BORDER,
                border_width=1,
                fg_color=("#FFFFFF", "#2D3338"),
            )
    except Exception:
        pass


def _history_bind_tile_299(self, tile):
    """Instala exatamente um conjunto de eventos no tile atual."""
    execucao = getattr(tile, "_sm_execucao", None)
    if execucao is None:
        return

    def abrir(event=None, item=execucao, f=tile):
        return _history_open_once_299(self, event, item, f)

    def entrar(event=None, f=tile):
        _history_hover_299(f, True, self)

    def sair(event=None, f=tile):
        _history_hover_299(f, False, self)

    for widget in _iter_descendants(tile):
        try:
            # O widget pode ter vindo de um redraw anterior. Removemos
            # explicitamente qualquer binding anterior antes de instalar o
            # conjunto atual; nunca usamos add="+" aqui.
            widget.unbind("<Button-1>")
            widget.unbind("<Enter>")
            widget.unbind("<Leave>")
            widget.bind("<Button-1>", abrir)
            widget.bind("<Enter>", entrar)
            widget.bind("<Leave>", sair)
        except Exception:
            pass


def _limpar_widgets_historico_299(self):
    """Destrói o grid anterior e zera todas as referências de tiles antigos."""
    _history_clear_selection_299(self)
    old_tiles = tuple(getattr(self, "_hist_tiles", set()))
    for tile in old_tiles:
        try:
            if _widget_exists(tile):
                for widget in _iter_descendants(tile):
                    try:
                        widget.unbind("<Button-1>")
                        widget.unbind("<Enter>")
                        widget.unbind("<Leave>")
                    except Exception:
                        pass
                tile.destroy()
        except Exception:
            pass

    grid = getattr(self, "_hist_grid", None)
    if grid is not None and _widget_exists(grid):
        try:
            grid.destroy()
        except Exception:
            pass

    self._hist_tiles = set()
    self._hist_grid = None


def _criar_pasta_historico_299(self, execucao, atual=False):
    """Cria uma pasta pequena e quadrada, no estilo de ícone médio do Windows."""
    parent = getattr(self, "historico_lista", None)
    if parent is None:
        return

    if not hasattr(self, "_hist_tiles"):
        self._hist_tiles = set()
    if not hasattr(self, "_hist_selected_tile"):
        self._hist_selected_tile = None

    if not _widget_exists(getattr(self, "_hist_grid", None)):
        self._hist_grid = ctk.CTkFrame(parent, fg_color="transparent")
        self._hist_grid.pack(fill="x", padx=6, pady=4)

    count = len(self._hist_grid.winfo_children())
    row, col = divmod(count, 7)
    self._hist_grid.grid_columnconfigure(tuple(range(7)), weight=1)

    tile = ctk.CTkFrame(
        self._hist_grid,
        fg_color=("#FFFFFF", "#2D3338"),
        corner_radius=6,
        border_width=1,
        border_color=self.BORDER,
        width=72,
        height=72,
    )
    tile.grid(row=row, column=col, padx=3, pady=3, sticky="nw")
    tile.grid_propagate(False)
    tile._sm_execucao = execucao
    self._hist_tiles.add(tile)

    inicio = str(execucao.get("inicio", ""))
    status = str(execucao.get("status", ""))
    erros = int(execucao.get("erros", 0) or 0)
    dia = inicio.split(" ")[0] if inicio else ""
    hora = inicio.split(" ")[1] if " " in inicio else ""

    ctk.CTkLabel(
        tile,
        text="📁",
        font=("Segoe UI Emoji", 17),
        text_color=self.ACCENT,
    ).pack(pady=(4, 0))
    ctk.CTkLabel(
        tile,
        text=dia,
        text_color=self.TEXT,
        font=("Segoe UI", 8, "bold"),
    ).pack(pady=(0, 0))
    ctk.CTkLabel(
        tile,
        text=hora,
        text_color=self.SUBTEXT,
        font=("Segoe UI", 7),
    ).pack(pady=(0, 0))
    ctk.CTkLabel(
        tile,
        text=f"{status} • {erros}",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 7),
        wraplength=64,
    ).pack(pady=(1, 0))

    _history_bind_tile_299(self, tile)


def _history_rebind_open_299(self):
    """Revalida apenas os tiles vivos; nunca reutiliza widgets destruídos."""
    tiles = set()
    for tile in tuple(getattr(self, "_hist_tiles", set())):
        if not _widget_exists(tile):
            continue
        tiles.add(tile)
        _history_bind_tile_299(self, tile)
    self._hist_tiles = tiles


def _history_click_outside_299(self, event=None):
    widget = getattr(event, "widget", None) if event is not None else None
    selected = getattr(self, "_hist_selected_tile", None)
    if selected is None:
        return
    if not _widget_inside(widget, selected):
        _history_clear_selection_299(self)


def _restaurar_historico_299(self, *args, **kwargs):
    # Primeiro destrói os tiles anteriores. Assim, nenhum callback ou
    # referência de uma pasta antiga sobrevive ao novo redraw.
    _limpar_widgets_historico_299(self)
    result = self._patch299_original_restaurar_historico(*args, **kwargs)
    _history_rebind_open_299(self)
    return result


def _limpar_selecao_arquivos_299(self):
    selected_dates = getattr(self, "_arquivos_datas_selecionadas", None)
    if not selected_dates:
        return
    try:
        selected_dates.clear()
        if hasattr(self, "_formatar_contador_selecao"):
            self._formatar_contador_selecao()
        if hasattr(self, "_cancelar_animacao_selecao"):
            self._cancelar_animacao_selecao()
        if hasattr(self, "_desenhar_calendario_arquivos"):
            self._desenhar_calendario_arquivos()
    except Exception:
        pass


def _limpar_selecao_planilha_299(self):
    active = getattr(self, "_planilha_celula_ativa", None)
    if not active:
        return
    self._planilha_celula_ativa = None
    for border in list(getattr(self, "_planilha_borda_widgets", []) or []):
        try:
            border.destroy()
        except Exception:
            pass
    self._planilha_borda_widgets = []


def _instalar_deselecao_global_299(self):
    """Aplica comportamento semelhante ao Windows para cliques externos."""
    if getattr(self, "_patch299_global_binding", False):
        return
    self._patch299_global_binding = True

    def on_click(event=None):
        widget = getattr(event, "widget", None) if event is not None else None

        selected_tile = getattr(self, "_hist_selected_tile", None)
        if selected_tile is not None and not _widget_inside(widget, selected_tile):
            _history_clear_selection_299(self)

        selected_dates = getattr(self, "_arquivos_datas_selecionadas", None)
        calendar_canvas = getattr(self, "_arquivos_calendar_canvas", None)
        if selected_dates and calendar_canvas is not None and not _widget_inside(widget, calendar_canvas):
            self.app.after_idle(lambda: _limpar_selecao_arquivos_299(self))

        active = getattr(self, "_planilha_celula_ativa", None)
        tree = getattr(self, "_planilha_tree", None)
        if active and tree is not None and not _widget_inside(widget, tree):
            _limpar_selecao_planilha_299(self)

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
    App._patch299_original_restaurar_historico = App._restaurar_historico_na_tela

    # Substitui a criação antiga por uma versão que administra explicitamente
    # o ciclo de vida dos tiles e seus callbacks.
    App._criar_pasta_historico = _criar_pasta_historico_299
    App._history_rebind_open = _history_rebind_open_299
    App._restaurar_historico_na_tela = _restaurar_historico_299
