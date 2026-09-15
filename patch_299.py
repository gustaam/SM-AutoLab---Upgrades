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
    """Retorna True quando widget é o próprio ancestor ou um filho dele.

    Usa o caminho Tk do widget em vez de nametowidget(), evitando exceções
    em árvores de widgets CustomTkinter e tornando o teste barato para o
    clique global.
    """
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


def _history_rebind_open_299(self):
    """Instala apenas o clique nas pastas; hover não participa da seleção."""
    tiles = set()
    for tile in tuple(getattr(self, "_hist_tiles", set())):
        if not _widget_exists(tile):
            continue
        tiles.add(tile)
        execucao = getattr(tile, "_sm_execucao", None)
        if execucao is None:
            continue

        def abrir(event=None, item=execucao, f=tile):
            return _history_open_once_299(self, event, item, f)

        for widget in _iter_descendants(tile):
            try:
                # Remove callbacks antigos do patch-298. Em especial, Enter/
                # Leave não podem alterar a aparência/seleção da pasta.
                widget.unbind("<Enter>")
                widget.unbind("<Leave>")
                widget.unbind("<Button-1>")
                widget.bind("<Button-1>", abrir)
            except Exception:
                pass

    # Não manter referências a pastas destruídas após uma atualização da tela.
    self._hist_tiles = tiles


def _history_click_outside_299(self, event=None):
    widget = getattr(event, "widget", None) if event is not None else None
    for tile in tuple(getattr(self, "_hist_tiles", set())):
        if _widget_inside(widget, tile):
            return
    _history_clear_selection_299(self)


def _restaurar_historico_299(self, *args, **kwargs):
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
    """Aplica comportamento semelhante ao Windows para cliques externos.

    Histórico: clique fora da pasta selecionada desmarca a pasta.
    Arquivos: clique fora do calendário limpa a seleção Ctrl+clique.
    Planilha: clique fora da área da planilha limpa a célula ativa.
    """
    if getattr(self, "_patch299_global_binding", False):
        return
    self._patch299_global_binding = True

    def on_click(event=None):
        widget = getattr(event, "widget", None) if event is not None else None

        # Histórico.
        selected_tile = getattr(self, "_hist_selected_tile", None)
        if selected_tile is not None and not _widget_inside(widget, selected_tile):
            _history_clear_selection_299(self)

        # Arquivos. O redesenho é adiado para depois do evento de mouse para
        # não destruir/recriar o Canvas enquanto o Tk ainda está despachando
        # o mesmo Button-1.
        selected_dates = getattr(self, "_arquivos_datas_selecionadas", None)
        calendar_canvas = getattr(self, "_arquivos_calendar_canvas", None)
        if selected_dates and calendar_canvas is not None and not _widget_inside(widget, calendar_canvas):
            self.app.after_idle(lambda: _limpar_selecao_arquivos_299(self))

        # Planilha. Clique dentro do Treeview mantém a seleção para que o
        # próprio handler possa escolher outra célula; somente fora limpa.
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

    # O patch 298 cria os callbacks iniciais. O patch 299 os substitui por
    # handlers estáveis, sem hover e sem acumulação após redesenhos.
    App._history_rebind_open = _history_rebind_open_299
    App._restaurar_historico_na_tela = _restaurar_historico_299
