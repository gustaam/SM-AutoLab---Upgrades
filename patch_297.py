from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk

import customtkinter as ctk


PATCH_297_MARKER = "SM-AUTOLAB-2.99.7-INTERFACE-CORRECTIONS"


def _iter_descendants(widget):
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = []
    for child in children:
        yield from _iter_descendants(child)


def _is_descendant(widget, ancestor):
    current = widget
    while current is not None:
        if current is ancestor:
            return True
        try:
            current = current.nametowidget(current.winfo_parent())
        except Exception:
            return False
    return False


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
    if previous is tile:
        return
    if previous is not None:
        _history_apply_selection(self, previous, False)
    self._hist_selected_tile = tile
    _history_apply_selection(self, tile, True)


def _history_clear_selection(self, _event=None):
    previous = getattr(self, "_hist_selected_tile", None)
    if previous is not None:
        _history_apply_selection(self, previous, False)
    self._hist_selected_tile = None


def _history_click_outside(self, event=None):
    widget = getattr(event, "widget", None) if event is not None else None
    folders = getattr(self, "_hist_tiles", set())
    if widget is not None:
        for tile in tuple(folders):
            if _is_descendant(widget, tile):
                return
    _history_clear_selection(self)


def _criar_pasta_historico_297(self, execucao, atual=False):
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
    self._hist_tiles.add(tile)

    inicio = str(execucao.get("inicio", ""))
    status = str(execucao.get("status", ""))
    erros = int(execucao.get("erros", 0) or 0)
    dia = inicio.split(" ")[0] if inicio else ""
    hora = inicio.split(" ")[1] if " " in inicio else ""

    icon = ctk.CTkLabel(tile, text="📁", font=("Segoe UI Emoji", 16), text_color=self.ACCENT)
    icon.pack(pady=(3, 0))
    ctk.CTkLabel(
        tile, text=dia, text_color=self.TEXT,
        font=("Segoe UI", 10, "bold")
    ).pack()
    ctk.CTkLabel(
        tile, text=hora, text_color=self.SUBTEXT,
        font=("Segoe UI", 8)
    ).pack()
    ctk.CTkLabel(
        tile, text=f"{status} • {erros} não exec.",
        text_color=self.SUBTEXT, font=("Segoe UI", 8), wraplength=78
    ).pack(pady=(2, 0))

    def selecionar(_event=None, f=tile):
        _history_select_tile(self, f)

    def abrir(_event=None, item=execucao, f=tile):
        _history_select_tile(self, f)
        self._abrir_detalhe_historico(item)

    # A pasta não reage ao simples movimento do mouse. Somente clique altera seleção.
    for widget in _iter_descendants(tile):
        try:
            widget.bind("<Button-1>", selecionar, add="+")
            widget.bind("<Double-Button-1>", abrir, add="+")
        except Exception:
            pass


def _restaurar_historico_297(self, *args, **kwargs):
    self._hist_tiles = set()
    self._hist_selected_tile = None
    result = self.__patch297_original_restaurar_historico(*args, **kwargs)
    lista = getattr(self, "historico_lista", None)
    if lista is not None:
        # Clique em qualquer área fora das pastas remove a seleção.
        for widget in _iter_descendants(lista):
            try:
                widget.bind("<Button-1>", lambda event: _history_click_outside(self, event), add="+")
            except Exception:
                pass
        # As ligações dos tiles são adicionadas novamente por último para que
        # um clique dentro de uma pasta volte a selecionar apenas aquela pasta.
        for tile in tuple(getattr(self, "_hist_tiles", set())):
            def selecionar(_event=None, f=tile):
                _history_select_tile(self, f)
            for widget in _iter_descendants(tile):
                try:
                    widget.bind("<Button-1>", selecionar, add="+")
                except Exception:
                    pass
    return result


def _preencher_detalhe_pasta_297(self, parent, execucao):
    for widget in parent.winfo_children():
        widget.destroy()

    inicio = execucao.get("inicio", "")
    fim = execucao.get("fim", "") or "Em andamento"
    planilha = execucao.get("planilha", "")
    pagina = execucao.get("pagina", "")
    status = execucao.get("status", "")
    total = execucao.get("total", 0)
    sucessos = execucao.get("sucessos", 0)
    erros = int(execucao.get("erros", 0) or 0)
    codigos = [str(x) for x in execucao.get("codigos_erros", [])]

    ctk.CTkLabel(
        parent,
        text=(
            f"Início: {inicio}    Fim: {fim}\n"
            f"Planilha: {planilha}    Página: {pagina}\n"
            f"Status: {status}    Processados: {total}    Executados: {sucessos}    Não executados: {erros}"
        ),
        text_color=self.SUBTEXT, font=("Segoe UI", 9), anchor="w", justify="left"
    ).pack(fill="x", padx=8, pady=(7, 4))

    if erros and codigos:
        ctk.CTkLabel(
            parent,
            text="Códigos não executados (clique para copiar):",
            text_color=self.ERROR, font=("Segoe UI", 11, "bold"), anchor="w"
        ).pack(fill="x", padx=8, pady=(0, 3))
        lista = ctk.CTkScrollableFrame(parent, fg_color="transparent", height=270)
        lista.pack(fill="both", expand=True, padx=4, pady=(0, 5))
        for codigo in codigos:
            self._criar_botao_erro(codigo, parent=lista)
    else:
        ctk.CTkLabel(
            parent, text="Nenhum código apresentou erro nessa execução.",
            text_color=self.SUCCESS, font=("Segoe UI", 10)
        ).pack(anchor="w", padx=8, pady=(3, 8))


def _formatar_selecao_297(self):
    total = len(getattr(self, "_arquivos_datas_selecionadas", set()))
    label = getattr(self, "_arquivos_contador_selecao", None)
    if label is not None:
        try:
            label.configure(text=f"{total} Selecionadas")
        except Exception:
            pass

    btn = getattr(self, "_arquivos_btn_apagar_selecionados", None)
    if btn is not None:
        try:
            btn.configure(state="normal" if total else "disabled")
        except Exception:
            pass


def _toggle_data_297(self, data):
    if not hasattr(self, "_arquivos_datas_selecionadas"):
        self._arquivos_datas_selecionadas = set()
    hoje = datetime.now().date()
    try:
        limite = hoje.replace() - __import__("datetime").timedelta(days=60)
    except Exception:
        return
    if not (limite <= data <= hoje):
        return
    try:
        if data not in self._dados_arquivos_por_dia():
            return
    except Exception:
        return
    if data in self._arquivos_datas_selecionadas:
        self._arquivos_datas_selecionadas.remove(data)
    else:
        self._arquivos_datas_selecionadas.add(data)
    try:
        self._animar_selecao_data(data)
    except Exception:
        pass
    _formatar_selecao_297(self)
    self._desenhar_calendario_arquivos()


def _clique_calendario_297(self, event):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return
    try:
        item_id = canvas.find_closest(event.x, event.y)[0]
        tags = canvas.gettags(item_id)
    except Exception:
        return
    data = None
    for tag in tags:
        if str(tag).startswith("dia:"):
            try:
                data = datetime.fromisoformat(str(tag)[4:]).date()
            except Exception:
                data = None
            break
    if data is None:
        return
    try:
        por_dia = self._dados_arquivos_por_dia()
    except Exception:
        por_dia = {}
    if data not in por_dia:
        return

    # No calendário, múltipla seleção usa o mesmo gesto do Windows Explorer:
    # mantenha Ctrl pressionado enquanto clica nas datas.
    ctrl = bool(getattr(event, "state", 0) & 0x0004)
    if ctrl:
        _toggle_data_297(self, data)
        return

    if getattr(self, "_arquivos_datas_selecionadas", None):
        self._arquivos_datas_selecionadas.clear()
        _formatar_selecao_297(self)
        try:
            self._cancelar_animacao_selecao()
        except Exception:
            pass
        self._desenhar_calendario_arquivos()
    hoje = datetime.now().date()
    limite = hoje - __import__("datetime").timedelta(days=60)
    if limite <= data <= hoje:
        self._mostrar_planilhas_do_dia(data)


def _abrir_historico_planilha_297(self):
    # Mantém a janela atual, mas remove o botão manual de seleção. A instrução
    # fica visível para deixar claro o gesto Ctrl + clique.
    self._ensure_selection_state()
    self._fechar_historico_planilha()
    win = tk.Toplevel(self.app)
    self._planilha_historico_window = win
    win.title("Arquivos — SM AutoLab")
    win.geometry("820x650")
    win.minsize(760, 590)
    win.resizable(True, True)
    win.transient(self.app)
    win.configure(bg=self._cor_fluente(self.BG))
    win.protocol("WM_DELETE_WINDOW", self._fechar_historico_planilha)

    header = ctk.CTkFrame(win, fg_color="transparent")
    header.pack(fill="x", padx=18, pady=(16, 8))
    ctk.CTkLabel(header, text="Arquivos", text_color=self.TEXT, font=("Segoe UI", 20, "bold")).pack(side="left")
    self._arquivos_contador_janela = ctk.CTkLabel(
        header, text="0 códigos no mês", text_color=self.SUBTEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_contador_janela.pack(side="left", padx=(10, 0))
    self._arquivos_contador_selecao = ctk.CTkLabel(
        header, text="0 Selecionadas", text_color=self.SUBTEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_contador_selecao.pack(side="left", padx=(10, 0))

    actions = ctk.CTkFrame(header, fg_color="transparent")
    actions.pack(side="right")
    ctk.CTkLabel(
        actions, text="Ctrl + clique para selecionar várias datas",
        text_color=self.SUBTEXT, font=("Segoe UI", 9)
    ).pack(side="left", padx=(0, 10))
    self._arquivos_btn_apagar_selecionados = ctk.CTkButton(
        actions, text="Apagar selecionados", command=self._apagar_datas_selecionadas,
        width=132, height=32, corner_radius=7, state="disabled",
        fg_color=("#F1F1F1", "#353A3F"), hover_color=("#F1F1F1", "#353A3F"),
        border_width=1, border_color=self.BORDER, text_color=self.SUBTEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_btn_apagar_selecionados.pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        actions, text="Limpar histórico", command=self._limpar_historico_planilhas,
        width=125, height=32, corner_radius=7, fg_color=self.CARD,
        hover_color=("#FDECEC", "#3A2424"), border_width=1,
        border_color=self.ERROR, text_color=self.ERROR,
        font=("Segoe UI", 10, "bold")
    ).pack(side="left")

    self._arquivos_body = ctk.CTkFrame(win, fg_color="transparent")
    self._arquivos_body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    hoje = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    self._arquivos_mes = hoje
    self._arquivos_datas_selecionadas.clear()
    self._formatar_contador_selecao()
    self._atualizar_contador_arquivos(hoje)
    self._renderizar_calendario_arquivos()
    win.update_idletasks()


def _install_planilha_context_menu(self):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return
    try:
        tree.unbind("<Button-3>")
    except Exception:
        pass

    def current_cell():
        alvo = getattr(self, "_planilha_celula_ativa", None)
        if not alvo:
            return None, None
        iid, col = alvo
        try:
            value = str(tree.item(iid, "values")[int(col)])
        except Exception:
            value = ""
        return iid, int(col), value

    def copy_cell():
        iid, col, value = current_cell()
        if iid is None:
            return
        try:
            self.app.clipboard_clear()
            self.app.clipboard_append(value)
        except Exception:
            pass

    def cut_cell():
        iid, col, value = current_cell()
        if iid is None:
            return
        self._planilha_undo.append(self._planilha_snapshot())
        self._planilha_undo = self._planilha_undo[-50:]
        vals = list(tree.item(iid, "values"))
        vals[col] = ""
        tree.item(iid, values=vals)
        try:
            self._planilha_data.pop(f"{int(iid)},{col}", None)
        except Exception:
            pass
        self._planilha_marcar_alteracao()
        self._planilha_desenhar_borda()
        try:
            self.app.clipboard_clear()
            self.app.clipboard_append(value)
        except Exception:
            pass

    def paste_normal():
        try:
            self._planilha_colar()
        except Exception:
            pass

    def paste_plain():
        # A grade trabalha com texto sem formatação; esta opção faz a mesma
        # transferência de valores, sem trazer qualquer estilo externo.
        try:
            self._planilha_colar()
        except Exception:
            pass

    def delete_cell():
        iid, col, _value = current_cell()
        if iid is None:
            return
        self._planilha_undo.append(self._planilha_snapshot())
        self._planilha_undo = self._planilha_undo[-50:]
        vals = list(tree.item(iid, "values"))
        vals[col] = ""
        tree.item(iid, values=vals)
        try:
            self._planilha_data.pop(f"{int(iid)},{col}", None)
        except Exception:
            pass
        self._planilha_marcar_alteracao()
        self._planilha_desenhar_borda()

    menu = tk.Menu(tree, tearoff=False)
    menu.add_command(label="Recortar", command=cut_cell)
    menu.add_command(label="Copiar", command=copy_cell)
    menu.add_command(label="Colar", command=paste_normal)
    menu.add_command(label="Colar sem Formatação", command=paste_plain)
    menu.add_separator()
    menu.add_command(label="Excluir", command=delete_cell)
    menu.add_command(label="Selecionar tudo", command=self._planilha_selecionar_tudo)

    def on_right_click(event):
        row = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not row or col not in ("#1", "#2", "#3"):
            return "break"
        self._planilha_celula_ativa = (row, int(col[1:]) - 1)
        self._planilha_linhas_selecionadas = {row}
        try:
            tree.focus_set()
            self._planilha_desenhar_borda()
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    tree.bind("<Button-3>", on_right_click)
    self._planilha_context_menu = menu


def _abrir_planilha_297(self, *args, **kwargs):
    result = self.__patch297_original_abrir_planilha(*args, **kwargs)
    try:
        _install_planilha_context_menu(self)
    except Exception:
        pass
    return result


def _renderizar_calendario_297(self):
    result = self.__patch297_original_renderizar_calendario(*(), **{})
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is not None:
        try:
            canvas.unbind("<Button-1>")
        except Exception:
            pass
        canvas.bind("<Button-1>", self._clique_calendario_arquivos)
    _formatar_selecao_297(self)
    return result


def aplicar_patch_297(App):
    if getattr(App, "_patch_297_aplicado", False):
        return
    App._patch_297_aplicado = True

    App._criar_pasta_historico = _criar_pasta_historico_297
    App.__patch297_original_restaurar_historico = App._restaurar_historico_na_tela
    App._restaurar_historico_na_tela = _restaurar_historico_297
    App._preencher_detalhe_pasta = _preencher_detalhe_pasta_297

    App._formatar_contador_selecao = _formatar_selecao_297
    App._toggle_data_selecionada = _toggle_data_297
    App._clique_calendario_arquivos = _clique_calendario_297

    App.__patch297_original_abrir_historico = App.abrir_historico_planilha
    App.abrir_historico_planilha = _abrir_historico_planilha_297

    App.__patch297_original_abrir_planilha = App.abrir_planilha
    App.abrir_planilha = _abrir_planilha_297

    App.__patch297_original_renderizar_calendario = App._renderizar_calendario_arquivos
    App._renderizar_calendario_arquivos = _renderizar_calendario_297
