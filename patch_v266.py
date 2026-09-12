from __future__ import annotations

from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk


def _linhas_preenchidas(self):
    linhas = set()
    for chave, valor in getattr(self, "_planilha_data", {}).items():
        if str(valor).strip() == "":
            continue
        try:
            linha, coluna = [int(x) for x in str(chave).split(",")]
        except Exception:
            continue
        if 0 <= linha < 10000 and 0 <= coluna < 3:
            linhas.add(linha)
    return linhas


def _planilha_atualizar_contador_v266(self):
    n = len(_linhas_preenchidas(self))
    label = getattr(self, "_planilha_contador_label", None)
    if label is not None:
        try:
            label.configure(text=f"{n} linhas preenchidas")
        except Exception:
            pass
    try:
        estado = getattr(self, "planilha_estado_label", None)
        if estado is not None:
            estado.configure(text="Planilha pronta" if n else "")
    except Exception:
        pass


def _contar_codigos_mes_apenas_arquivos(self, referencia=None):
    """Conta somente os códigos que ainda existem no histórico de Arquivos."""
    referencia = referencia or datetime.now()
    ano = int(getattr(referencia, "year", datetime.now().year))
    mes = int(getattr(referencia, "month", datetime.now().month))
    total = 0
    try:
        itens = self._carregar_historico_planilhas()
    except Exception:
        itens = []
    for item in itens:
        try:
            salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
        except Exception:
            continue
        if salvo.year != ano or salvo.month != mes:
            continue
        try:
            total += max(0, int(item.get("filled", 0) or 0))
        except Exception:
            continue
    return total


def _inicializar_selecao_arquivos(self):
    if not hasattr(self, "_arquivos_datas_selecionadas"):
        self._arquivos_datas_selecionadas = set()
    if not hasattr(self, "_arquivos_modo_selecao"):
        self._arquivos_modo_selecao = False
    if not hasattr(self, "_arquivos_animando_data"):
        self._arquivos_animando_data = None
    if not hasattr(self, "_arquivos_animacao_job"):
        self._arquivos_animacao_job = None
    if not hasattr(self, "_arquivos_selecao_contador"):
        self._arquivos_selecao_contador = None
    if not hasattr(self, "_arquivos_btn_selecionar"):
        self._arquivos_btn_selecionar = None
    if not hasattr(self, "_arquivos_btn_apagar_selecionados"):
        self._arquivos_btn_apagar_selecionados = None


def _atualizar_contador_selecao(self):
    _inicializar_selecao_arquivos(self)
    quantidade = len(self._arquivos_datas_selecionadas)
    label = getattr(self, "_arquivos_selecao_contador", None)
    if label is not None:
        try:
            label.configure(text=f"{quantidade} célula(s) selecionada(s)")
        except Exception:
            pass

    botao = getattr(self, "_arquivos_btn_apagar_selecionados", None)
    if botao is not None:
        try:
            ativo = quantidade > 0
            botao.configure(
                state="normal" if ativo else "disabled",
                fg_color=self.CARD if ativo else ("#EDEDED", "#34393E"),
                text_color=self.ERROR if ativo else ("#A0A0A0", "#6F767D"),
                border_color=self.ERROR if ativo else self.BORDER,
                hover_color=("#FDECEC", "#3A2424") if ativo else ("#EDEDED", "#34393E"),
            )
        except Exception:
            pass


def _iniciar_modo_selecao_arquivos(self):
    _inicializar_selecao_arquivos(self)
    self._arquivos_modo_selecao = not self._arquivos_modo_selecao
    if not self._arquivos_modo_selecao:
        self._arquivos_datas_selecionadas.clear()
        self._arquivos_animando_data = None
        if self._arquivos_animacao_job is not None:
            try:
                self.app.after_cancel(self._arquivos_animacao_job)
            except Exception:
                pass
            self._arquivos_animacao_job = None

    botao = getattr(self, "_arquivos_btn_selecionar", None)
    if botao is not None:
        try:
            ativo = self._arquivos_modo_selecao
            botao.configure(
                text="Sair da seleção" if ativo else "Selecionar",
                fg_color=self.ACCENT if ativo else self.CARD,
                hover_color=self.ACCENT_HOVER if ativo else ("#F3F3F3", "#3A3A3A"),
                text_color="#FFFFFF" if ativo else self.TEXT,
            )
        except Exception:
            pass
    _atualizar_contador_selecao(self)
    self._desenhar_calendario_arquivos()


def _extrair_data_do_item_calendario(canvas, item_id):
    try:
        tags = canvas.gettags(item_id)
    except Exception:
        return None
    for tag in tags:
        if str(tag).startswith("dia:"):
            try:
                return datetime.fromisoformat(str(tag)[4:]).date()
            except Exception:
                return None
    return None


def _iniciar_animacao_selecao_data(self, data, passo=0):
    _inicializar_selecao_arquivos(self)
    if self._arquivos_calendar_canvas is None:
        return
    if data not in self._arquivos_datas_selecionadas or passo >= 6:
        self._arquivos_animando_data = None
        self._arquivos_animacao_job = None
        self._desenhar_calendario_arquivos()
        return
    self._arquivos_animando_data = data
    self._desenhar_calendario_arquivos()
    try:
        self._arquivos_animacao_job = self.app.after(
            90, lambda: self._iniciar_animacao_selecao_data(data, passo + 1)
        )
    except Exception:
        self._arquivos_animacao_job = None


def _toggle_data_selecionada(self, data):
    _inicializar_selecao_arquivos(self)
    if data in self._arquivos_datas_selecionadas:
        self._arquivos_datas_selecionadas.remove(data)
        if self._arquivos_animando_data == data:
            self._arquivos_animando_data = None
            if self._arquivos_animacao_job is not None:
                try:
                    self.app.after_cancel(self._arquivos_animacao_job)
                except Exception:
                    pass
                self._arquivos_animacao_job = None
    else:
        self._arquivos_datas_selecionadas.add(data)
        if self._arquivos_animacao_job is not None:
            try:
                self.app.after_cancel(self._arquivos_animacao_job)
            except Exception:
                pass
            self._arquivos_animacao_job = None
        _iniciar_animacao_selecao_data(self, data)
    _atualizar_contador_selecao(self)
    self._desenhar_calendario_arquivos()


def _clique_calendario_arquivos_selecao(self, event):
    _inicializar_selecao_arquivos(self)
    canvas = self._arquivos_calendar_canvas
    if canvas is None:
        return
    try:
        item_id = canvas.find_closest(event.x, event.y)[0]
    except Exception:
        return
    data = _extrair_data_do_item_calendario(canvas, item_id)
    if data is None:
        return
    hoje = datetime.now().date()
    limite = hoje - timedelta(days=60)
    if not (limite <= data <= hoje):
        return
    if self._arquivos_modo_selecao:
        _toggle_data_selecionada(self, data)
        return
    self._mostrar_planilhas_do_dia(data)


def _desenhar_calendario_arquivos_com_selecao(self):
    """Mantém o calendário original e desenha a camada visual das seleções."""
    _inicializar_selecao_arquivos(self)
    self._desenhar_calendario_arquivos_original_v266()
    canvas = self._arquivos_calendar_canvas
    if canvas is None or not canvas.winfo_exists():
        return
    if not self._arquivos_datas_selecionadas:
        return

    modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
    cor_borda = self._cor_fluente(self.ACCENT)
    cor_preenchimento = "#DDEEFF" if not modo_escuro else "#1F4D6B"
    cor_animacao = self._cor_fluente(self.ACCENT_HOVER)
    for data in sorted(self._arquivos_datas_selecionadas):
        tag = f"dia:{data.isoformat()}"
        itens = canvas.find_withtag(tag)
        if not itens:
            continue
        caixas = [
            canvas.bbox(item)
            for item in itens
            if canvas.type(item) == "rectangle" and canvas.bbox(item) is not None
        ]
        if not caixas:
            continue
        x0 = min(b[0] for b in caixas)
        y0 = min(b[1] for b in caixas)
        x1 = max(b[2] for b in caixas)
        y1 = max(b[3] for b in caixas)
        animando = data == self._arquivos_animando_data
        canvas.create_rectangle(
            x0, y0, x1, y1,
            fill=cor_preenchimento,
            outline=cor_animacao if animando else cor_borda,
            width=3 if animando else 2,
            tags=(tag, f"selecionado:{data.isoformat()}"),
        )
        canvas.tag_raise(f"selecionado:{data.isoformat()}")


def _apagar_datas_selecionadas(self):
    _inicializar_selecao_arquivos(self)
    selecionadas = set(self._arquivos_datas_selecionadas)
    if not selecionadas:
        return

    itens = self._carregar_historico_planilhas()
    manter = []
    remover = []
    codigos_removidos = 0
    for item in itens:
        try:
            data_item = datetime.fromisoformat(str(item.get("saved_at", ""))).date()
        except Exception:
            manter.append(item)
            continue
        if data_item in selecionadas:
            remover.append(item)
            try:
                codigos_removidos += max(0, int(item.get("filled", 0) or 0))
            except Exception:
                pass
        else:
            manter.append(item)

    if not remover:
        self._arquivos_datas_selecionadas.clear()
        _atualizar_contador_selecao(self)
        self._desenhar_calendario_arquivos()
        return

    confirmar = messagebox.askyesno(
        "Apagar selecionados",
        f"Apagar o histórico de {len(selecionadas)} data(s) selecionada(s)?\n\n"
        f"Serão removidas {len(remover)} planilha(s) e {codigos_removidos} código(s) do histórico.",
        parent=self._planilha_historico_window,
    )
    if not confirmar:
        return

    self._salvar_historico_planilhas(manter)
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    self._arquivos_animando_data = None
    if self._arquivos_animacao_job is not None:
        try:
            self.app.after_cancel(self._arquivos_animacao_job)
        except Exception:
            pass
        self._arquivos_animacao_job = None
    botao = getattr(self, "_arquivos_btn_selecionar", None)
    if botao is not None:
        try:
            botao.configure(
                text="Selecionar", fg_color=self.CARD,
                hover_color=("#F3F3F3", "#3A3A3A"), text_color=self.TEXT,
            )
        except Exception:
            pass
    _atualizar_contador_selecao(self)
    self._atualizar_contador_arquivos(self._arquivos_mes)
    self._desenhar_calendario_arquivos()
    try:
        self._add_activity(
            f"{len(remover)} data(s) removida(s) do histórico de Arquivos ({codigos_removidos} códigos).",
            self.WARNING,
        )
    except Exception:
        pass


def _limpar_historico_planilhas_selecao(self):
    _inicializar_selecao_arquivos(self)
    itens = self._carregar_historico_planilhas()
    if not itens:
        messagebox.showinfo(
            "Arquivos", "Não há arquivos no histórico.", parent=self._planilha_historico_window
        )
        return
    confirmar = messagebox.askyesno(
        "Limpar todo histórico",
        "Tem certeza que deseja apagar todos os arquivos do histórico?",
        parent=self._planilha_historico_window,
    )
    if not confirmar:
        return
    self._salvar_historico_planilhas([])
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    self._arquivos_animando_data = None
    if self._arquivos_animacao_job is not None:
        try:
            self.app.after_cancel(self._arquivos_animacao_job)
        except Exception:
            pass
        self._arquivos_animacao_job = None
    self._arquivos_data_selecionada = None
    _atualizar_contador_selecao(self)
    self._renderizar_calendario_arquivos()


def _fechar_historico_planilha_selecao(self):
    _inicializar_selecao_arquivos(self)
    if self._arquivos_animacao_job is not None:
        try:
            self.app.after_cancel(self._arquivos_animacao_job)
        except Exception:
            pass
        self._arquivos_animacao_job = None
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    self._arquivos_animando_data = None
    self._arquivos_selecao_contador = None
    self._arquivos_btn_selecionar = None
    self._arquivos_btn_apagar_selecionados = None
    self._fechar_historico_planilha_original_v266()


def _abrir_historico_planilha_selecao(self):
    _inicializar_selecao_arquivos(self)
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
    try:
        self.app.update_idletasks()
        px = self.app.winfo_rootx() + max(0, (self.app.winfo_width() - 820) // 2)
        py = self.app.winfo_rooty() + max(0, (self.app.winfo_height() - 650) // 2)
        win.geometry(f"820x650+{px}+{py}")
    except Exception:
        pass

    header = ctk.CTkFrame(win, fg_color="transparent")
    header.pack(fill="x", padx=18, pady=(16, 8))
    ctk.CTkLabel(
        header, text="Arquivos", text_color=self.TEXT,
        font=("Segoe UI", 20, "bold")
    ).pack(side="left")
    self._arquivos_contador_janela = ctk.CTkLabel(
        header, text="0 códigos no mês", text_color=self.SUBTEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_contador_janela.pack(side="left", padx=(10, 0))
    self._arquivos_selecao_contador = ctk.CTkLabel(
        header, text="0 célula(s) selecionada(s)", text_color=self.SUBTEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_selecao_contador.pack(side="left", padx=(10, 0))

    actions = ctk.CTkFrame(header, fg_color="transparent")
    actions.pack(side="right")
    self._arquivos_btn_selecionar = ctk.CTkButton(
        actions, text="Selecionar", command=self._iniciar_modo_selecao_arquivos,
        width=92, height=32, corner_radius=7, fg_color=self.CARD,
        hover_color=("#F3F3F3", "#3A3A3A"), border_width=1,
        border_color=self.BORDER, text_color=self.TEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_btn_selecionar.pack(side="left", padx=(0, 6))
    self._arquivos_btn_apagar_selecionados = ctk.CTkButton(
        actions, text="Apagar selecionados", command=self._apagar_datas_selecionadas,
        width=132, height=32, corner_radius=7, fg_color=("#EDEDED", "#34393E"),
        hover_color=("#EDEDED", "#34393E"), border_width=1,
        border_color=self.BORDER, text_color=("#A0A0A0", "#6F767D"),
        font=("Segoe UI", 10, "bold"), state="disabled"
    )
    self._arquivos_btn_apagar_selecionados.pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        actions, text="Limpar todo histórico", command=self._limpar_historico_planilhas,
        width=132, height=32, corner_radius=7, fg_color=self.CARD,
        hover_color=("#FDECEC", "#3A2424"), border_width=1,
        border_color=self.ERROR, text_color=self.ERROR,
        font=("Segoe UI", 10, "bold")
    ).pack(side="left")

    self._arquivos_body = ctk.CTkFrame(win, fg_color="transparent")
    self._arquivos_body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    hoje = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    self._arquivos_mes = hoje
    self._arquivos_data_selecionada = None
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    self._arquivos_animando_data = None
    self._atualizar_contador_arquivos()
    _atualizar_contador_selecao(self)
    self._renderizar_calendario_arquivos()
    win.update_idletasks()


def _aplicar_status_finalizado_v266(self, texto):
    low = str(texto).lower()
    if "finalizado" not in low:
        if getattr(self, "_status_finalizado_job", None) is not None:
            try:
                self.app.after_cancel(self._status_finalizado_job)
            except Exception:
                pass
            self._status_finalizado_job = None
        return self.__v265_aplicar_status(texto)

    if getattr(self, "_status_finalizado_job", None) is not None:
        try:
            self.app.after_cancel(self._status_finalizado_job)
        except Exception:
            pass
    self._status_text_base = "Finalizado"
    self._status_blink_fast = False
    cor_texto = self.SUCCESS
    cor_pill = ("#E7F5E7", "#21482A")
    try:
        self.status_label.configure(text="Finalizado")
        self.status_pill.configure(fg_color=cor_pill)
        self.status_text.configure(
            text="Finalizado", text_color=cor_texto,
            font=("Segoe UI", 13, "bold")
        )
        modo = ctk.get_appearance_mode().lower()
        self.status_indicator.configure(bg=cor_pill[1] if modo == "dark" else cor_pill[0])
        self._iniciar_pisca_status()
    except Exception:
        pass
    self._status_finalizado_job = self.app.after(
        10000, lambda: self.__v265_aplicar_status("Pronto")
    )


def aplicar_patch(app_class):
    if getattr(app_class, "_v266_patch_aplicado", False):
        return

    app_class.__v265_aplicar_status = app_class._aplicar_status
    app_class._planilha_atualizar_contador = _planilha_atualizar_contador_v266
    app_class._contar_codigos_mes = _contar_codigos_mes_apenas_arquivos
    app_class._atualizar_contador_selecao = _atualizar_contador_selecao
    app_class._inicializar_selecao_arquivos = _inicializar_selecao_arquivos
    app_class._iniciar_modo_selecao_arquivos = _iniciar_modo_selecao_arquivos
    app_class._toggle_data_selecionada = _toggle_data_selecionada
    app_class._clique_calendario_arquivos = _clique_calendario_arquivos_selecao
    app_class._apagar_datas_selecionadas = _apagar_datas_selecionadas

    app_class._desenhar_calendario_arquivos_original_v266 = app_class._desenhar_calendario_arquivos
    app_class._fechar_historico_planilha_original_v266 = app_class._fechar_historico_planilha
    app_class._desenhar_calendario_arquivos = _desenhar_calendario_arquivos_com_selecao
    app_class._fechar_historico_planilha = _fechar_historico_planilha_selecao
    app_class.abrir_historico_planilha = _abrir_historico_planilha_selecao
    app_class._limpar_historico_planilhas = _limpar_historico_planilhas_selecao
    app_class._aplicar_status = _aplicar_status_finalizado_v266

    original_config = app_class.config_app

    def config_app_v266(self):
        original_config(self)
        try:
            if hasattr(self, "botao_historico_planilha"):
                self.botao_historico_planilha.configure(text="Arquivos")
        except Exception:
            pass

    app_class.config_app = config_app_v266
    app_class._status_finalizado_job = None
    app_class._v266_patch_aplicado = True
