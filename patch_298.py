from __future__ import annotations

import tkinter as tk
from datetime import datetime

import customtkinter as ctk


PATCH_298_MARKER = "SM-AUTOLAB-HISTORICO-ARQUIVOS-FIXES"


def _iter_descendants(widget):
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        yield from _iter_descendants(child)


def _historico_tem_erro(execucao):
    try:
        if int(execucao.get("erros", 0) or 0) > 0:
            return True
    except Exception:
        pass
    status = str(execucao.get("status", "")).strip().lower()
    return any(token in status for token in ("erro", "falha", "interromp"))


def _history_apply_selection(self, tile, selected):
    if tile is None:
        return
    try:
        tile.configure(
            border_color=self.ACCENT if selected else self.BORDER,
            border_width=1,
            fg_color=("#EAF4FF", "#1B3C53") if selected else ("#FFFFFF", "#2D3338"),
        )
    except Exception:
        pass


def _history_select_tile(self, tile):
    previous = getattr(self, "_hist_selected_tile", None)
    if previous is not None and previous is not tile:
        _history_apply_selection(self, previous, False)
    self._hist_selected_tile = tile
    _history_apply_selection(self, tile, True)


def _history_click_open(self, event=None, execucao=None, tile=None):
    if tile is not None:
        _history_select_tile(self, tile)
    if execucao is not None:
        self._abrir_detalhe_historico(execucao)
    return "break"


def _history_rebind_open(self):
    for tile in tuple(getattr(self, "_hist_tiles", set())):
        execucao = getattr(tile, "_sm_execucao", None)
        if execucao is None:
            continue
        def abrir(event=None, item=execucao, f=tile):
            return _history_click_open(self, event, item, f)
        for widget in _iter_descendants(tile):
            try:
                widget.bind("<Button-1>", abrir, add="+")
            except Exception:
                pass


def _criar_pasta_historico_298(self, execucao, atual=False):
    parent = getattr(self, "historico_lista", None)
    if parent is None:
        return
    if not hasattr(self, "_hist_tiles"):
        self._hist_tiles = set()
    if not hasattr(self, "_hist_selected_tile"):
        self._hist_selected_tile = None

    if not hasattr(self, "_hist_grid") or self._hist_grid is None:
        self._hist_grid = ctk.CTkFrame(parent, fg_color="transparent")
        self._hist_grid.pack(fill="x", padx=6, pady=4)

    count = len(self._hist_grid.winfo_children())
    row, col = divmod(count, 6)
    self._hist_grid.grid_columnconfigure(tuple(range(6)), weight=1)

    tile = ctk.CTkFrame(
        self._hist_grid,
        fg_color=("#FFFFFF", "#2D3338"),
        corner_radius=7,
        border_width=1,
        border_color=self.BORDER,
        width=86,
        height=70,
    )
    tile.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
    tile.grid_propagate(False)
    tile._sm_execucao = execucao
    self._hist_tiles.add(tile)

    inicio = str(execucao.get("inicio", ""))
    status = str(execucao.get("status", ""))
    erros = int(execucao.get("erros", 0) or 0)
    dia = inicio.split(" ")[0] if inicio else ""
    hora = inicio.split(" ")[1] if " " in inicio else ""

    icon = ctk.CTkLabel(tile, text="📁", font=("Segoe UI Emoji", 16), text_color=self.ACCENT)
    icon.pack(pady=(3, 0))
    ctk.CTkLabel(tile, text=dia, text_color=self.TEXT, font=("Segoe UI", 10, "bold")).pack()
    ctk.CTkLabel(tile, text=hora, text_color=self.SUBTEXT, font=("Segoe UI", 8)).pack()
    ctk.CTkLabel(
        tile,
        text=f"{status} • {erros} não exec.",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8),
        wraplength=78,
    ).pack(pady=(2, 0))

    def abrir(event=None, item=execucao, f=tile):
        return _history_click_open(self, event, item, f)

    def enter(_event=None, f=tile):
        if getattr(self, "_hist_selected_tile", None) is f:
            return
        try:
            f.configure(
                border_color=self.ACCENT_HOVER,
                fg_color=("#F3F3F3", "#3A3A3A"),
            )
        except Exception:
            pass

    def leave(_event=None, f=tile):
        if getattr(self, "_hist_selected_tile", None) is f:
            return
        try:
            f.configure(
                border_color=self.BORDER,
                fg_color=("#FFFFFF", "#2D3338"),
            )
        except Exception:
            pass

    for widget in _iter_descendants(tile):
        try:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")
            widget.bind("<Button-1>", abrir, add="+")
        except Exception:
            pass


def _restaurar_historico_298(self, *args, **kwargs):
    all_execucoes = list(getattr(self, "_historico_execucoes", []))
    current = getattr(self, "_execucao_atual", None)
    visible = [item for item in all_execucoes if isinstance(item, dict) and _historico_tem_erro(item)]
    visible_current = current if isinstance(current, dict) and _historico_tem_erro(current) else None

    self._historico_execucoes = visible
    self._execucao_atual = visible_current
    try:
        result = self._patch298_original_restaurar_historico(*args, **kwargs)
    finally:
        self._historico_execucoes = all_execucoes
        self._execucao_atual = current

    _history_rebind_open(self)
    return result


def _config_app_298(self, *args, **kwargs):
    result = self._patch298_original_config_app(*args, **kwargs)
    try:
        btn = self.tab_buttons.pop("Não executados", None)
        if btn is not None:
            btn.pack_forget()
            btn.destroy()
        if hasattr(self, "aba_erros"):
            self.aba_erros.pack_forget()
    except Exception:
        pass
    return result


def _filtrar_arquivos_298(self, itens):
    validos = []
    for item in itens or []:
        if not isinstance(item, dict):
            continue
        try:
            datetime.fromisoformat(str(item.get("saved_at", "")))
        except Exception:
            continue
        validos.append(item)
    validos.sort(key=lambda item: str(item.get("saved_at", "")))
    return validos


def _mes_minimo_arquivos_298(self):
    itens = self._carregar_historico_planilhas()
    datas = []
    for item in itens:
        try:
            datas.append(datetime.fromisoformat(str(item.get("saved_at", ""))))
        except Exception:
            pass
    if not datas:
        agora = datetime.now()
        return datetime(agora.year, agora.month, 1)
    mais_antiga = min(datas)
    return datetime(mais_antiga.year, mais_antiga.month, 1)


def _atualizar_limite_arquivos_298(self):
    """Ajusta a janela interna apenas para compatibilidade com os métodos antigos.
    O limite passa a ser calculado a partir do registro mais antigo disponível,
    portanto não existe uma janela fixa de 60 dias.
    """
    import interface as interface_module

    itens = self._carregar_historico_planilhas()
    hoje = datetime.now().date()
    datas = []
    for item in itens:
        try:
            datas.append(datetime.fromisoformat(str(item.get("saved_at", ""))).date())
        except Exception:
            pass
    if datas:
        interface_module.ARQUIVOS_DIAS = max((hoje - min(datas)).days, 0) + 1
    else:
        interface_module.ARQUIVOS_DIAS = 0


def _renderizar_calendario_298(self, *args, **kwargs):
    _atualizar_limite_arquivos_298(self)
    result = self._patch298_original_renderizar_calendario(*args, **kwargs)
    try:
        for widget in _iter_descendants(getattr(self, "_arquivos_body", None)):
            if isinstance(widget, ctk.CTkLabel):
                texto = str(widget.cget("text"))
                if "O histórico mantém até 60 dias." in texto:
                    widget.configure(text="O histórico de Arquivos é ilimitado.")
    except Exception:
        pass
    return result


def _desenhar_calendario_298(self, *args, **kwargs):
    _atualizar_limite_arquivos_298(self)
    return self._patch298_original_desenhar_calendario(*args, **kwargs)


def _clique_calendario_298(self, *args, **kwargs):
    _atualizar_limite_arquivos_298(self)
    return self._patch298_original_clique_calendario(*args, **kwargs)


def _mostrar_planilhas_dia_298(self, *args, **kwargs):
    _atualizar_limite_arquivos_298(self)
    return self._patch298_original_mostrar_planilhas_dia(*args, **kwargs)


def aplicar_patch_298(App):
    if getattr(App, "_patch_298_aplicado", False):
        return
    App._patch_298_aplicado = True

    App._patch298_original_config_app = App.config_app
    App.config_app = _config_app_298

    App._criar_pasta_historico = _criar_pasta_historico_298
    App._patch298_original_restaurar_historico = App._restaurar_historico_na_tela
    App._restaurar_historico_na_tela = _restaurar_historico_298

    App._patch298_original_filtrar_arquivos = App._filtrar_arquivos_60_dias
    App._filtrar_arquivos_60_dias = _filtrar_arquivos_298
    App._mes_minimo_arquivos = _mes_minimo_arquivos_298

    App._patch298_original_renderizar_calendario = App._renderizar_calendario_arquivos
    App._renderizar_calendario_arquivos = _renderizar_calendario_298
    App._patch298_original_desenhar_calendario = App._desenhar_calendario_arquivos
    App._desenhar_calendario_arquivos = _desenhar_calendario_298
    App._patch298_original_clique_calendario = App._clique_calendario_arquivos
    App._clique_calendario_arquivos = _clique_calendario_298
    App._patch298_original_mostrar_planilhas_dia = App._mostrar_planilhas_do_dia
    App._mostrar_planilhas_do_dia = _mostrar_planilhas_dia_298
