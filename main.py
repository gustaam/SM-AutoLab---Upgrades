from datetime import datetime

from splash import run_splash
from interface import App
from patch import aplicar_patch_ui

_REQUIRED_BASE_METHODS = (
    "abrir_historico_planilha",
    "_renderizar_calendario_arquivos",
    "_toggle_modo_selecao_arquivos",
    "_toggle_data_selecionada",
    "_apagar_datas_selecionadas",
    "_atualizar_contador_selecao",
    "_contar_codigos_mes",
)


def _historico_minimo_arquivos(self):
    """Retorna a data mais antiga existente no histórico, sem janela fixa."""
    try:
        datas = []
        for item in self._carregar_historico_planilhas():
            try:
                datas.append(datetime.fromisoformat(str(item.get("saved_at", ""))).date())
            except Exception:
                continue
        return min(datas) if datas else datetime.now().date()
    except Exception:
        return datetime.now().date()


def _expandir_janela_arquivos(self):
    """Mantém a compatibilidade com código legado, mas sem limitar Arquivos a 60 dias."""
    try:
        import interface as interface_module

        hoje = datetime.now().date()
        minimo = _historico_minimo_arquivos(self)
        interface_module.ARQUIVOS_DIAS = max((hoje - minimo).days, 0) + 1
    except Exception:
        pass


def _corrigir_historico_ilimitado():
    """Remove em runtime a restrição fixa de 60 dias das rotinas de Arquivos."""
    if getattr(App, "_historico_ilimitado_aplicado", False):
        return

    original_toggle = App._toggle_data_selecionada
    original_click = App._clique_calendario_arquivos
    original_draw = App._desenhar_calendario_arquivos

    def toggle_data(self, data):
        _expandir_janela_arquivos(self)
        try:
            por_dia = self._dados_arquivos_por_dia()
        except Exception:
            por_dia = {}
        if data not in por_dia:
            return
        selecionadas = getattr(self, "_arquivos_datas_selecionadas", None)
        if not isinstance(selecionadas, set):
            selecionadas = set(selecionadas or ())
            self._arquivos_datas_selecionadas = selecionadas
        if data in selecionadas:
            selecionadas.remove(data)
            try:
                if getattr(self, "_arquivos_animacao_data", None) == data:
                    self._cancelar_animacao_selecao()
            except Exception:
                pass
        else:
            selecionadas.add(data)
            try:
                self._animar_selecao_data(data)
            except Exception:
                pass
        try:
            self._atualizar_contador_selecao()
        except Exception:
            pass
        try:
            self._desenhar_calendario_arquivos()
        except Exception:
            original_toggle(self, data)

    def click_calendar(self, event):
        _expandir_janela_arquivos(self)
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

        if getattr(self, "_arquivos_modo_selecao", False):
            return self._toggle_data_selecionada(data)
        return self._mostrar_planilhas_do_dia(data)

    def draw_calendar(self, *args, **kwargs):
        _expandir_janela_arquivos(self)
        result = original_draw(self, *args, **kwargs)
        canvas = getattr(self, "_arquivos_calendar_canvas", None)
        if canvas is None:
            return result

        try:
            import customtkinter as ctk

            modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
            por_dia = self._dados_arquivos_por_dia()
            hoje = datetime.now().date()
            bg_arquivo = "#EAF4FF" if not modo_escuro else "#183B54"
            bg_selecionado = "#D9ECFF" if not modo_escuro else "#244E6B"
            text = self._cor_fluente(self.TEXT)
            accent = self._cor_fluente(self.ACCENT)

            for data in sorted(por_dia):
                if data > hoje:
                    continue
                tag = f"dia:{data.isoformat()}"
                try:
                    itens = canvas.find_withtag(tag)
                except Exception:
                    continue
                if not itens:
                    continue
                selecionada = data in getattr(self, "_arquivos_datas_selecionadas", set())
                for item_id in itens:
                    try:
                        tipo = canvas.type(item_id)
                        if tipo == "rectangle":
                            canvas.itemconfigure(
                                item_id,
                                fill=bg_selecionado if selecionada else bg_arquivo,
                                outline=accent,
                                width=2 if selecionada else 1,
                            )
                        elif tipo == "text":
                            canvas.itemconfigure(item_id, fill=text)
                    except Exception:
                        pass
        except Exception:
            pass
        return result

    App._historico_ilimitado_original_toggle = original_toggle
    App._historico_ilimitado_original_click = original_click
    App._historico_ilimitado_original_draw = original_draw
    App._toggle_data_selecionada = toggle_data
    App._clique_calendario_arquivos = click_calendar
    App._desenhar_calendario_arquivos = draw_calendar
    App._historico_ilimitado_aplicado = True


# Correções finais descobertas após o primeiro uso real da 2.99.11.
SM_AUTOLAB_UI_FIXES_29912 = "SM-AUTOLAB-2.99.12-UI-FIXES"


def _ui_29912_widget_inside(widget, ancestor):
    if widget is None or ancestor is None:
        return False
    try:
        child = str(widget)
        parent = str(ancestor)
    except Exception:
        return False
    return child == parent or child.startswith(parent + ".")


def _ui_29912_home_counter(self):
    """Mantém visível o contador da página inicial e evita o pack_forget do patch legado."""
    label = getattr(self, "arquivos_contador_label", None)
    if label is None:
        return

    total = 0
    try:
        # Quando existe uma planilha interna salva, o contador representa os
        # códigos presentes nela; caso contrário, usa o histórico do mês.
        total = int(self._count_saved_passwords() or 0)
    except Exception:
        total = 0
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


def _ui_29912_history_clear(self):
    selected = getattr(self, "_hist_selected_tiles", None)
    if not isinstance(selected, set):
        selected = set()
        self._hist_selected_tiles = selected
    for tile in tuple(selected):
        try:
            tile.configure(
                border_color=self.BORDER,
                border_width=1,
                fg_color=("#FFFFFF", "#2D3338"),
            )
        except Exception:
            pass
    selected.clear()
    self._hist_selected_tile = None


def _ui_29912_history_select(self, tile, ctrl=False):
    selected = getattr(self, "_hist_selected_tiles", None)
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
                    other.configure(
                        border_color=self.BORDER,
                        border_width=1,
                        fg_color=("#FFFFFF", "#2D3338"),
                    )
                except Exception:
                    pass
        selected.clear()
        selected.add(tile)

    # Mantém compatibilidade com as rotinas anteriores que conhecem uma pasta única.
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


def _ui_29912_history_bind(self, tile):
    execucao = getattr(tile, "_sm_execucao", None)
    if execucao is None:
        return

    def on_click(event=None, f=tile):
        ctrl = bool(getattr(event, "state", 0) & 0x0004) if event is not None else False
        _ui_29912_history_select(self, f, ctrl=ctrl)
        return "break"

    def on_double_click(_event=None, item=execucao, f=tile):
        _ui_29912_history_select(self, f, ctrl=False)
        self._abrir_detalhe_historico(item)
        return "break"

    def on_enter(_event=None, f=tile):
        selected = getattr(self, "_hist_selected_tiles", set())
        if f in selected:
            return
        try:
            f.configure(
                border_color=self.ACCENT_HOVER,
                fg_color=("#F3F3F3", "#3A3A3A"),
            )
        except Exception:
            pass

    def on_leave(_event=None, f=tile):
        selected = getattr(self, "_hist_selected_tiles", set())
        if f in selected:
            return
        try:
            f.configure(
                border_color=self.BORDER,
                fg_color=("#FFFFFF", "#2D3338"),
            )
        except Exception:
            pass

    try:
        from patch import _NS_PATCH_299
        descendants = _NS_PATCH_299["_iter_descendants"](tile)
    except Exception:
        descendants = (tile,)

    for widget in descendants:
        try:
            widget.unbind("<Button-1>")
            widget.unbind("<Double-Button-1>")
            widget.unbind("<Double-1>")
            widget.unbind("<Enter>")
            widget.unbind("<Leave>")
            widget.bind("<Button-1>", on_click)
            widget.bind("<Double-Button-1>", on_double_click)
            widget.bind("<Double-1>", on_double_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        except Exception:
            pass


def _ui_29912_history_create(self, execucao, atual=False):
    parent = getattr(self, "historico_lista", None)
    if parent is None:
        return

    if not hasattr(self, "_hist_tiles"):
        self._hist_tiles = set()
    if not hasattr(self, "_hist_selected_tiles"):
        self._hist_selected_tiles = set()

    grid = getattr(self, "_hist_grid", None)
    try:
        grid_exists = grid is not None and grid.winfo_exists()
    except Exception:
        grid_exists = False
    if not grid_exists:
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(anchor="center", pady=(6, 8))
        self._hist_grid = grid

    count = len(grid.winfo_children())
    row, col = divmod(count, 5)

    tile = ctk.CTkFrame(
        grid,
        fg_color=("#FFFFFF", "#2D3338"),
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

    ctk.CTkLabel(
        tile, text="📁", font=("Segoe UI Emoji", 19), text_color=self.ACCENT
    ).pack(pady=(5, 0))
    ctk.CTkLabel(
        tile, text=dia, text_color=self.TEXT, font=("Segoe UI", 9, "bold")
    ).pack(pady=(0, 0))
    ctk.CTkLabel(
        tile, text=hora, text_color=self.SUBTEXT, font=("Segoe UI", 8)
    ).pack(pady=(0, 0))
    ctk.CTkLabel(
        tile,
        text=f"{status} • {erros}",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8),
        wraplength=102,
    ).pack(pady=(2, 0))

    _ui_29912_history_bind(self, tile)


def _ui_29912_history_restore(self, *args, **kwargs):
    result = self._ui_29912_original_restore(*args, **kwargs)
    try:
        self._hist_selected_tiles = {
            tile for tile in getattr(self, "_hist_tiles", set())
            if tile is not None and tile.winfo_exists()
        }
        # A restauração não deve iniciar com todas as pastas selecionadas.
        self._hist_selected_tiles.clear()
        self._hist_selected_tile = None
        for tile in tuple(getattr(self, "_hist_tiles", set())):
            _ui_29912_history_bind(self, tile)
    except Exception:
        pass
    return result


def _ui_29912_calendar_click(self, event):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return "break"

    data = None
    try:
        itens = canvas.find_overlapping(event.x, event.y, event.x, event.y)
    except Exception:
        itens = ()
    for item_id in reversed(itens):
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
            self._atualizar_contador_selecao()
            self._cancelar_animacao_selecao()
            self._desenhar_calendario_arquivos()
        except Exception:
            pass
    self._mostrar_planilhas_do_dia(data)
    return "break"


def _ui_29912_calendar_rebind(self):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return
    try:
        canvas.unbind("<Button-1>")
    except Exception:
        pass
    try:
        canvas.bind("<Button-1>", self._clique_calendario_arquivos)
    except Exception:
        pass


def _ui_29912_global_click(self, event=None):
    widget = getattr(event, "widget", None) if event is not None else None

    selected_tiles = getattr(self, "_hist_selected_tiles", set())
    if selected_tiles and not any(_ui_29912_widget_inside(widget, tile) for tile in tuple(selected_tiles)):
        _ui_29912_history_clear(self)

    selected_dates = getattr(self, "_arquivos_datas_selecionadas", set())
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if selected_dates and canvas is not None and not _ui_29912_widget_inside(widget, canvas):
        try:
            selected_dates.clear()
            self._cancelar_animacao_selecao()
            self._atualizar_contador_selecao()
            self._desenhar_calendario_arquivos()
        except Exception:
            pass


def _ui_29912_wrap_save(self, original, *args, **kwargs):
    result = original(self, *args, **kwargs)
    try:
        self.app.after_idle(lambda: _ui_29912_home_counter(self))
    except Exception:
        _ui_29912_home_counter(self)
    return result


def _instalar_ui_29912():
    if getattr(App, "_ui_29912_aplicado", False):
        return
    App._ui_29912_aplicado = True
    App._ui_29912_marker = SM_AUTOLAB_UI_FIXES_29912

    # 1) contador da página inicial: mantém visibilidade e reconcilia o valor
    # com a planilha interna ou com o histórico do mês depois de cada salvamento.
    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _ui_29912_home_counter(self))
            self.app.after_idle(lambda: _ui_29912_calendar_rebind(self))
        except Exception:
            _ui_29912_home_counter(self)
        return result

    App.config_app = config_wrapper

    original_save_exit = App._planilha_salvar_e_sair

    def save_exit_wrapper(self, *args, **kwargs):
        return _ui_29912_wrap_save(self, original_save_exit, *args, **kwargs)

    App._planilha_salvar_e_sair = save_exit_wrapper

    original_save_start = getattr(App, "_planilha_salvar_e_iniciar", None)
    if original_save_start is not None:
        def save_start_wrapper(self, *args, **kwargs):
            return _ui_29912_wrap_save(self, original_save_start, *args, **kwargs)

        App._planilha_salvar_e_iniciar = save_start_wrapper

    # 2) histórico de erros: pastas maiores, próximas e com seleção múltipla.
    App._criar_pasta_historico = _ui_29912_history_create
    App._ui_29912_original_restore = App._restaurar_historico_na_tela
    App._restaurar_historico_na_tela = _ui_29912_history_restore

    # 3) Ctrl+clique no calendário funciona diretamente, sem exigir o botão
    # "Selecionar". A mesma convenção vale para as pastas do histórico.
    App._clique_calendario_arquivos = _ui_29912_calendar_click
    App._atualizar_contador_principal_29912 = _ui_29912_home_counter

    original_global_config = App.config_app

    def config_global_wrapper(self, *args, **kwargs):
        result = original_global_config(self, *args, **kwargs)
        try:
            if not getattr(self, "_ui_29912_global_binding", False):
                self.app.bind_all("<Button-1>", lambda event: _ui_29912_global_click(self, event), add="+")
                self._ui_29912_global_binding = True
        except Exception:
            pass
        return result

    App.config_app = config_global_wrapper



def _validar_base_aplicacao():
    """Impede inicializacao silenciosamente incompleta da base do aplicativo."""
    faltantes = [nome for nome in _REQUIRED_BASE_METHODS if not hasattr(App, nome)]
    if faltantes:
        raise RuntimeError(
            "A base do SM AutoLab esta incompleta. Componentes ausentes: "
            + ", ".join(faltantes)
        )
    if not getattr(App, "_patch_ui_aplicado", False):
        raise RuntimeError("A camada consolidada de correções não foi aplicada.")
    if not getattr(App, "_historico_ilimitado_aplicado", False):
        raise RuntimeError("A correção de histórico ilimitado não foi aplicada.")


if __name__ == "__main__":
    aplicar_patch_ui(App)
    _corrigir_historico_ilimitado()
    _instalar_ui_29912()
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
