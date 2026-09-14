from __future__ import annotations

from datetime import datetime, timedelta
from tkinter import messagebox

AJUSTES_COMPONENT_MARKER = "SM-AUTOLAB-AJUSTES-ARQUIVOS"


def _estado(self):
    if not hasattr(self, "_arquivos_datas_selecionadas"):
        self._arquivos_datas_selecionadas = set()
    if not hasattr(self, "_arquivos_modo_selecao"):
        self._arquivos_modo_selecao = False


def _data_clicada(self, event):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return None
    try:
        itens = canvas.find_overlapping(event.x, event.y, event.x, event.y)
    except Exception:
        return None
    for item_id in reversed(itens):
        try:
            for tag in canvas.gettags(item_id):
                if str(tag).startswith("dia:"):
                    return datetime.fromisoformat(str(tag)[4:]).date()
        except Exception:
            continue
    return None


def _atualizar_rotulos(self):
    _estado(self)
    total = len(self._arquivos_datas_selecionadas)

    label = getattr(self, "_arquivos_contador_selecao", None)
    if label is not None:
        try:
            label.configure(text=f"{total} selecionados")
        except Exception:
            pass

    btn_selecionar = getattr(self, "_arquivos_btn_selecionar", None)
    if btn_selecionar is not None:
        try:
            btn_selecionar.configure(
                text="Sair da seleção" if self._arquivos_modo_selecao else "Selecionar"
            )
        except Exception:
            pass

    btn_apagar = getattr(self, "_arquivos_btn_apagar_selecionados", None)
    if btn_apagar is not None:
        try:
            btn_apagar.configure(state="normal" if total else "disabled")
        except Exception:
            pass

    def visitar(widget):
        try:
            filhos = widget.winfo_children()
        except Exception:
            filhos = []
        for filho in filhos:
            visitar(filho)
        try:
            if widget.cget("text") == "Limpar todo histórico":
                widget.configure(text="Limpar histórico")
        except Exception:
            pass

    win = getattr(self, "_planilha_historico_window", None)
    if win is not None:
        visitar(win)


def _toggle_data_selecionada_ajuste(self, data):
    _estado(self)
    hoje = datetime.now().date()
    limite = hoje - timedelta(days=60)
    if not (limite <= data <= hoje):
        return

    try:
        por_dia = self._dados_arquivos_por_dia()
        if data not in por_dia:
            return
    except Exception:
        return

    if data in self._arquivos_datas_selecionadas:
        self._arquivos_datas_selecionadas.remove(data)
        if getattr(self, "_arquivos_animacao_data", None) == data:
            try:
                self._cancelar_animacao_selecao()
            except Exception:
                pass
    else:
        self._arquivos_datas_selecionadas.add(data)
        try:
            self._animar_selecao_data(data)
        except Exception:
            pass

    try:
        self._atualizar_contador_selecao()
    except Exception:
        pass
    self._desenhar_calendario_arquivos()
    _atualizar_rotulos(self)


def _clique_calendario_ajuste(self, event):
    _estado(self)
    if not getattr(self, "_arquivos_modo_selecao", False):
        return self.__ajustes_click_original(event)
    data = _data_clicada(self, event)
    if data is None:
        return
    hoje = datetime.now().date()
    limite = hoje - timedelta(days=60)
    if limite <= data <= hoje:
        _toggle_data_selecionada_ajuste(self, data)


def _desenhar_calendario_ajuste(self):
    self.__ajustes_draw_original()
    _estado(self)
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None or not canvas.winfo_exists():
        return
    import customtkinter as ctk
    modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
    fill = "#D9ECFF" if not modo_escuro else "#244E6B"
    accent = self._cor_fluente(self.ACCENT)
    for data in sorted(self._arquivos_datas_selecionadas):
        tag = f"dia:{data.isoformat()}"
        try:
            itens = canvas.find_withtag(tag)
        except Exception:
            continue
        caixas = []
        for item in itens:
            try:
                if canvas.type(item) == "rectangle":
                    box = canvas.bbox(item)
                    if box:
                        caixas.append(box)
            except Exception:
                pass
        if not caixas:
            continue
        x0 = min(b[0] for b in caixas)
        y0 = min(b[1] for b in caixas)
        x1 = max(b[2] for b in caixas)
        y1 = max(b[3] for b in caixas)
        try:
            ret = canvas.create_rectangle(
                x0, y0, x1, y1, fill=fill, outline=accent, width=2,
                tags=(f"selecao_ajuste:{data.isoformat()}",),
            )
            canvas.tag_lower(ret)
            canvas.create_oval(
                x1 - 18, y0 + 6, x1 - 8, y0 + 16, fill=accent, outline="",
                tags=(f"selecao_ajuste:{data.isoformat()}",),
            )
            canvas.create_text(
                x1 - 13, y0 + 11, text="✓", fill="#FFFFFF",
                font=("Segoe UI", 7, "bold"), tags=(f"selecao_ajuste:{data.isoformat()}",),
            )
        except Exception:
            continue


def _apagar_datas_selecionadas_ajuste(self):
    _estado(self)
    selecionadas = set(self._arquivos_datas_selecionadas)
    if not selecionadas:
        return

    itens = self._carregar_historico_planilhas()
    restantes = []
    removidos = 0
    for item in itens:
        try:
            dt = datetime.fromisoformat(str(item.get("saved_at", "")))
        except Exception:
            restantes.append(item)
            continue
        if dt.date() in selecionadas:
            removidos += 1
        else:
            restantes.append(item)

    if not messagebox.askyesno(
        "Apagar selecionados",
        f"Excluir os {len(selecionadas)} selecionados?\n\nIsso removerá {removidos} arquivo(s) do histórico.",
        parent=self._planilha_historico_window,
    ):
        return

    self._salvar_historico_planilhas(restantes)
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    try:
        self._cancelar_animacao_selecao()
    except Exception:
        pass
    try:
        self._atualizar_contador_selecao()
    except Exception:
        pass
    try:
        self._atualizar_contador_arquivos(self._arquivos_mes)
    except Exception:
        pass
    self._renderizar_calendario_arquivos()
    _atualizar_rotulos(self)


def _limpar_historico_planilhas_ajuste(self):
    _estado(self)
    itens = self._carregar_historico_planilhas()
    if not itens:
        messagebox.showinfo(
            "Arquivos",
            "Não há arquivos no histórico.",
            parent=self._planilha_historico_window,
        )
        return

    if not messagebox.askyesno(
        "Limpar histórico",
        "Tem certeza que deseja apagar todo o histórico de arquivos existente?",
        parent=self._planilha_historico_window,
    ):
        return

    # Limpar histórico sempre apaga TODO o histórico, sem limitar a operação
    # ao mês exibido ou às datas selecionadas.
    self._salvar_historico_planilhas([])
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    try:
        self._cancelar_animacao_selecao()
    except Exception:
        pass
    try:
        self._atualizar_contador_selecao()
    except Exception:
        pass
    try:
        self._atualizar_contador_arquivos(self._arquivos_mes)
    except Exception:
        pass
    self._renderizar_calendario_arquivos()
    _atualizar_rotulos(self)


def aplicar_patch_ajustes(app_class):
    if getattr(app_class, "_patch_ajustes_aplicado", False):
        return
    app_class._patch_ajustes_aplicado = True
    app_class.__ajustes_click_original = app_class._clique_calendario_arquivos
    app_class._clique_calendario_arquivos = _clique_calendario_ajuste
    app_class._toggle_data_selecionada = _toggle_data_selecionada_ajuste
    app_class.__ajustes_draw_original = app_class._desenhar_calendario_arquivos
    app_class._desenhar_calendario_arquivos = _desenhar_calendario_ajuste
    app_class._apagar_datas_selecionadas = _apagar_datas_selecionadas_ajuste
    app_class._limpar_historico_planilhas = _limpar_historico_planilhas_ajuste
    original_abrir = app_class.abrir_historico_planilha

    def abrir_com_ajustes(self, *args, **kwargs):
        resultado = original_abrir(self, *args, **kwargs)
        try:
            _atualizar_rotulos(self)
        except Exception:
            pass
        return resultado

    app_class.abrir_historico_planilha = abrir_com_ajustes
