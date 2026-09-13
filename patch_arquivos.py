from __future__ import annotations

from datetime import datetime, timedelta
import calendar as pycalendar
import tkinter as tk
import customtkinter as ctk


ARQUIVOS_COMPONENT_MARKER = "SM-AUTOLAB-ARQUIVOS-SELECAO"


def _ensure_selection_state(self):
    if not hasattr(self, "_arquivos_modo_selecao"):
        self._arquivos_modo_selecao = False
    if not hasattr(self, "_arquivos_datas_selecionadas"):
        self._arquivos_datas_selecionadas = set()
    if not hasattr(self, "_arquivos_animacao_data"):
        self._arquivos_animacao_data = None
    if not hasattr(self, "_arquivos_animacao_frame"):
        self._arquivos_animacao_frame = 0
    if not hasattr(self, "_arquivos_animacao_job"):
        self._arquivos_animacao_job = None
    if not hasattr(self, "_arquivos_btn_selecionar"):
        self._arquivos_btn_selecionar = None
    if not hasattr(self, "_arquivos_btn_apagar_selecionados"):
        self._arquivos_btn_apagar_selecionados = None
    if not hasattr(self, "_arquivos_contador_selecao"):
        self._arquivos_contador_selecao = None


def _dados_arquivos_por_dia(self):
    por_dia = {}
    for item in self._carregar_historico_planilhas():
        try:
            dt = datetime.fromisoformat(str(item.get("saved_at", "")))
        except Exception:
            continue
        por_dia.setdefault(dt.date(), []).append(item)
    return por_dia


def _contar_codigos_mes_arquivos(self, referencia=None):
    """Conta exclusivamente os códigos presentes no histórico de Arquivos."""
    referencia = referencia or datetime.now()
    ano = int(getattr(referencia, "year", datetime.now().year))
    mes = int(getattr(referencia, "month", datetime.now().month))
    total = 0
    try:
        for item in self._carregar_historico_planilhas():
            try:
                salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            if salvo.year != ano or salvo.month != mes:
                continue
            try:
                total += max(0, int(item.get("filled", 0) or 0))
            except Exception:
                pass
    except Exception:
        return 0
    return total


def _formatar_contador_arquivos_arquivos(self, referencia=None):
    valor = self._contar_codigos_mes(referencia)
    return f"{valor:,}".replace(",", ".") + " códigos no mês"


def _atualizar_contador_arquivos_arquivos(self, referencia=None):
    if referencia is None:
        referencia = datetime.now()
    try:
        texto_main = self._formatar_contador_arquivos(referencia)
    except Exception:
        texto_main = self._formatar_contador_arquivos()

    label_main = getattr(self, "arquivos_contador_label", None)
    if label_main is not None:
        try:
            label_main.configure(text=texto_main)
        except Exception:
            pass

    label_janela = getattr(self, "_arquivos_contador_janela", None)
    if label_janela is not None:
        try:
            label_janela.configure(text=self._formatar_contador_arquivos(referencia))
        except Exception:
            pass


def _atualizar_contador_selecao_arquivos(self):
    _ensure_selection_state(self)
    total = len(self._arquivos_datas_selecionadas)
    texto = f"{total} célula selecionada" if total == 1 else f"{total} células selecionadas"
    label = getattr(self, "_arquivos_contador_selecao", None)
    if label is not None:
        try:
            label.configure(text=texto)
        except Exception:
            pass

    btn = getattr(self, "_arquivos_btn_apagar_selecionados", None)
    if btn is not None:
        try:
            if total:
                btn.configure(
                    state="normal",
                    fg_color=self.ERROR,
                    hover_color=("#B02A2E", "#E0575B"),
                    border_color=self.ERROR,
                    text_color="#FFFFFF",
                )
            else:
                btn.configure(
                    state="disabled",
                    fg_color=("#F1F1F1", "#353A3F"),
                    hover_color=("#F1F1F1", "#353A3F"),
                    border_color=self.BORDER,
                    text_color=self.SUBTEXT,
                )
        except Exception:
            pass


def _cancelar_animacao_selecao_arquivos(self):
    job = getattr(self, "_arquivos_animacao_job", None)
    if job is not None:
        try:
            self.app.after_cancel(job)
        except Exception:
            pass
    self._arquivos_animacao_job = None
    self._arquivos_animacao_data = None
    self._arquivos_animacao_frame = 0


def _animar_selecao_data_arquivos(self, data):
    _ensure_selection_state(self)
    self._cancelar_animacao_selecao()
    self._arquivos_animacao_data = data
    self._arquivos_animacao_frame = 0
    self._executar_animacao_selecao()


def _executar_animacao_selecao_arquivos(self):
    if getattr(self, "_arquivos_calendar_canvas", None) is None:
        self._cancelar_animacao_selecao()
        return
    if self._arquivos_animacao_data is None:
        return
    if self._arquivos_animacao_frame >= 10:
        data = self._arquivos_animacao_data
        self._cancelar_animacao_selecao()
        self._desenhar_calendario_arquivos()
        return
    self._arquivos_animacao_frame += 1
    self._desenhar_calendario_arquivos()
    self._arquivos_animacao_job = self.app.after(55, self._executar_animacao_selecao)


def _toggle_modo_selecao_arquivos_arquivos(self):
    _ensure_selection_state(self)
    self._arquivos_modo_selecao = not self._arquivos_modo_selecao
    if not self._arquivos_modo_selecao:
        self._cancelar_animacao_selecao()
    btn = getattr(self, "_arquivos_btn_selecionar", None)
    if btn is not None:
        try:
            if self._arquivos_modo_selecao:
                btn.configure(
                    text="Selecionar",
                    fg_color=self.ACCENT,
                    hover_color=self.ACCENT_HOVER,
                    text_color="#FFFFFF",
                    border_color=self.ACCENT,
                )
            else:
                btn.configure(
                    text="Selecionar",
                    fg_color=self.CARD,
                    hover_color=("#F3F3F3", "#3A3A3A"),
                    text_color=self.TEXT,
                    border_color=self.BORDER,
                )
        except Exception:
            pass
    self._atualizar_contador_selecao()
    self._desenhar_calendario_arquivos()


def _toggle_data_selecionada_arquivos(self, data):
    _ensure_selection_state(self)
    por_dia = _dados_arquivos_por_dia(self)
    hoje = datetime.now().date()
    limite = hoje - timedelta(days=60)
    if not (limite <= data <= hoje) or data not in por_dia:
        return

    if data in self._arquivos_datas_selecionadas:
        self._arquivos_datas_selecionadas.remove(data)
    else:
        self._arquivos_datas_selecionadas.add(data)
    self._atualizar_contador_selecao()
    self._animar_selecao_data(data)


def _apagar_datas_selecionadas_arquivos(self):
    _ensure_selection_state(self)
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

    confirmar = ctk.CTkInputDialog if False else None
    from tkinter import messagebox
    texto = (
        f"Excluir as planilhas de {len(selecionadas)} célula(s) selecionada(s)?\n\n"
        f"Isso removerá {removidos} arquivo(s) do histórico."
    )
    if not messagebox.askyesno(
        "Apagar selecionados",
        texto,
        parent=self._planilha_historico_window,
    ):
        return

    self._salvar_historico_planilhas(restantes)
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    self._cancelar_animacao_selecao()
    self._atualizar_contador_selecao()
    self._atualizar_contador_arquivos(self._arquivos_mes)
    self._renderizar_calendario_arquivos()


def _limpar_historico_planilhas_arquivos(self):
    from tkinter import messagebox
    itens = self._carregar_historico_planilhas()
    if not itens:
        messagebox.showinfo(
            "Arquivos",
            "Não há arquivos no histórico.",
            parent=self._planilha_historico_window,
        )
        return
    if not messagebox.askyesno(
        "Limpar todo histórico",
        "Tem certeza que deseja apagar todo o histórico de arquivos?",
        parent=self._planilha_historico_window,
    ):
        return
    self._salvar_historico_planilhas([])
    _ensure_selection_state(self)
    self._arquivos_datas_selecionadas.clear()
    self._arquivos_modo_selecao = False
    self._cancelar_animacao_selecao()
    self._atualizar_contador_selecao()
    self._atualizar_contador_arquivos(self._arquivos_mes)
    self._renderizar_calendario_arquivos()


def _clique_calendario_arquivos_arquivos(self, event):
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
        if tag.startswith("dia:"):
            try:
                data = datetime.fromisoformat(tag[4:]).date()
            except Exception:
                data = None
            break
    if data is None:
        return

    por_dia = _dados_arquivos_por_dia(self)
    if data not in por_dia:
        return

    if getattr(self, "_arquivos_modo_selecao", False):
        self._toggle_data_selecionada(data)
        return

    hoje = datetime.now().date()
    limite = hoje - timedelta(days=60)
    if limite <= data <= hoje:
        self._mostrar_planilhas_do_dia(data)


def _desenhar_calendario_arquivos_arquivos(self):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None or not canvas.winfo_exists():
        return
    _ensure_selection_state(self)
    canvas.delete("all")

    hoje = datetime.now().date()
    limite = hoje - timedelta(days=60)
    mes = self._arquivos_mes or self._mes_atual_arquivos()
    self._arquivos_mes = mes
    por_dia = _dados_arquivos_por_dia(self)

    try:
        self._arquivos_mes_label.configure(text=f"{self._nome_mes(mes.month)} {mes.year}")
        self._atualizar_contador_arquivos(mes)
        self._atualizar_contador_selecao()
        self._arquivos_btn_mes_anterior.configure(
            state="normal" if mes > self._mes_minimo_arquivos() else "disabled"
        )
        self._arquivos_btn_mes_proximo.configure(
            state="normal" if mes < self._mes_atual_arquivos() else "disabled"
        )
    except Exception:
        pass

    modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
    bg = self._cor_fluente(self.CARD)
    border = self._cor_fluente(self.BORDER)
    text = self._cor_fluente(self.TEXT)
    subtext = self._cor_fluente(self.SUBTEXT)
    accent = self._cor_fluente(self.ACCENT)
    disabled = "#555B61" if modo_escuro else "#B7B7B7"
    today_fill = "#E8F1FB" if not modo_escuro else "#20384B"
    selected_fill = "#D9ECFF" if not modo_escuro else "#244E6B"

    largura = max(canvas.winfo_width(), 640)
    altura = max(canvas.winfo_height(), 330)
    margem_x = 8
    margem_y = 4
    header_h = 30
    grid_top = margem_y + header_h
    col_w = (largura - 2 * margem_x) / 7
    row_h = (altura - grid_top - 8) / 6

    nomes = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
    for col, nome in enumerate(nomes):
        x0 = margem_x + col * col_w
        x1 = x0 + col_w
        canvas.create_text(
            (x0 + x1) / 2,
            margem_y + header_h / 2,
            text=nome,
            fill=subtext,
            font=("Segoe UI", 9, "bold"),
        )

    calendario = pycalendar.Calendar(firstweekday=0)
    semanas = calendario.monthdayscalendar(mes.year, mes.month)
    while len(semanas) < 6:
        semanas.append([0] * 7)

    for row in range(6):
        y0 = grid_top + row * row_h + 2
        y1 = grid_top + (row + 1) * row_h - 2
        for col in range(7):
            dia = semanas[row][col]
            if not dia:
                continue
            data = mes.replace(day=dia).date()
            x0 = margem_x + col * col_w + 3
            x1 = margem_x + (col + 1) * col_w - 3
            centro_x = (x0 + x1) / 2
            centro_y = (y0 + y1) / 2
            valido = limite <= data <= hoje
            tem_arquivo = data in por_dia
            eh_hoje = data == hoje
            selecionada = data in self._arquivos_datas_selecionadas

            fill = bg
            outline = border
            fg = text if valido else disabled
            width = 1

            if tem_arquivo and valido:
                fill = "#EAF4FF" if not modo_escuro else "#183B54"
                outline = accent
                width = 1
            if eh_hoje and valido:
                fill = today_fill
                outline = accent
                width = 2
            if selecionada and valido and tem_arquivo:
                fill = selected_fill
                outline = accent
                width = 2
                if data == self._arquivos_animacao_data:
                    pulse = self._arquivos_animacao_frame % 4
                    width = 2 + (pulse // 2)

            tag = f"dia:{data.isoformat()}"
            canvas.create_rectangle(
                x0, y0, x1, y1,
                fill=fill, outline=outline, width=width, tags=(tag,)
            )
            canvas.create_text(
                centro_x, centro_y - 3,
                text=str(dia), fill=fg,
                font=("Segoe UI", 11, "bold" if (tem_arquivo or eh_hoje or selecionada) else "normal"),
                tags=(tag,)
            )
            if tem_arquivo and valido:
                canvas.create_oval(
                    centro_x - 3, y1 - 14, centro_x + 3, y1 - 8,
                    fill=accent, outline="", tags=(tag,)
                )
            if selecionada and valido and tem_arquivo:
                canvas.create_oval(
                    centro_x - 5, y0 + 7, centro_x + 5, y0 + 17,
                    fill=accent, outline="", tags=(tag,)
                )
                canvas.create_text(
                    centro_x, y0 + 12,
                    text="✓", fill="#FFFFFF",
                    font=("Segoe UI", 7, "bold"), tags=(tag,)
                )


def _renderizar_calendario_arquivos_arquivos(self):
    if self._arquivos_body is None:
        return
    _ensure_selection_state(self)
    for widget in self._arquivos_body.winfo_children():
        widget.destroy()

    card = ctk.CTkFrame(
        self._arquivos_body,
        fg_color=self.CARD,
        corner_radius=12,
        border_width=1,
        border_color=self.BORDER,
    )
    card.pack(fill="both", expand=True, padx=8, pady=(0, 4))

    intro = ctk.CTkFrame(card, fg_color="transparent")
    intro.pack(fill="x", padx=18, pady=(14, 4))
    ctk.CTkLabel(
        intro,
        text="Selecione uma data",
        text_color=self.TEXT,
        font=("Segoe UI", 15, "bold"),
    ).pack(anchor="w")
    ctk.CTkLabel(
        intro,
        text="Os dias com planilhas salvas ficam destacados. O histórico mantém até 60 dias.",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 9),
    ).pack(anchor="w", pady=(2, 0))

    nav = ctk.CTkFrame(card, fg_color="transparent")
    nav.pack(fill="x", padx=18, pady=(10, 8))
    self._arquivos_btn_mes_anterior = ctk.CTkButton(
        nav, text="‹", width=38, height=32, corner_radius=7,
        fg_color=self.CARD, hover_color=self.ACCENT_HOVER,
        border_width=1, border_color=self.BORDER, text_color=self.TEXT,
        font=("Segoe UI", 17, "bold"), command=lambda: self._mudar_mes_arquivos(-1)
    )
    self._arquivos_btn_mes_anterior.pack(side="left")
    self._arquivos_mes_label = ctk.CTkLabel(
        nav, text="", text_color=self.TEXT, font=("Segoe UI", 14, "bold")
    )
    self._arquivos_mes_label.pack(side="left", expand=True)
    self._arquivos_btn_mes_proximo = ctk.CTkButton(
        nav, text="›", width=38, height=32, corner_radius=7,
        fg_color=self.CARD, hover_color=self.ACCENT_HOVER,
        border_width=1, border_color=self.BORDER, text_color=self.TEXT,
        font=("Segoe UI", 17, "bold"), command=lambda: self._mudar_mes_arquivos(1)
    )
    self._arquivos_btn_mes_proximo.pack(side="right")

    hint = ctk.CTkFrame(card, fg_color="transparent")
    hint.pack(fill="x", padx=18, pady=(0, 4))
    ctk.CTkLabel(
        hint, text="●", text_color=self._cor_fluente(self.ACCENT),
        font=("Segoe UI", 12, "bold")
    ).pack(side="left")
    ctk.CTkLabel(
        hint, text=" possui planilhas salvas", text_color=self.SUBTEXT,
        font=("Segoe UI", 9)
    ).pack(side="left", padx=(4, 0))

    canvas = tk.Canvas(
        card, height=360, highlightthickness=0, bd=0, relief="flat",
        bg=self._cor_fluente(self.CARD),
    )
    canvas.pack(fill="both", expand=True, padx=18, pady=(2, 16))
    canvas.bind("<Button-1>", self._clique_calendario_arquivos)
    canvas.bind("<Configure>", lambda _e: self._desenhar_calendario_arquivos())
    self._arquivos_calendar_canvas = canvas
    self._desenhar_calendario_arquivos()


def _mudar_mes_arquivos_arquivos(self, direcao):
    atual = self._arquivos_mes or self._mes_atual_arquivos()
    novo = self._mes_proximo(atual) if direcao > 0 else self._mes_anterior(atual)
    if novo < self._mes_minimo_arquivos() or novo > self._mes_atual_arquivos():
        return
    self._arquivos_mes = novo
    self._atualizar_contador_arquivos(novo)
    self._desenhar_calendario_arquivos()


def _fechar_historico_planilha_arquivos(self):
    _ensure_selection_state(self)
    self._cancelar_animacao_selecao()
    w = getattr(self, "_planilha_historico_window", None)
    if w is not None:
        try:
            w.destroy()
        except Exception:
            pass
    self._planilha_historico_window = None
    self._arquivos_body = None
    self._arquivos_calendar_canvas = None
    self._arquivos_calendar_widget = None


def _abrir_historico_planilha_arquivos(self):
    _ensure_selection_state(self)
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
    self._arquivos_contador_selecao = ctk.CTkLabel(
        header, text="0 células selecionadas", text_color=self.SUBTEXT,
        font=("Segoe UI", 10)
    )
    self._arquivos_contador_selecao.pack(side="left", padx=(10, 0))

    actions = ctk.CTkFrame(header, fg_color="transparent")
    actions.pack(side="right")
    self._arquivos_btn_selecionar = ctk.CTkButton(
        actions, text="Selecionar", command=self._toggle_modo_selecao_arquivos,
        width=86, height=32, corner_radius=7, fg_color=self.CARD,
        hover_color=("#F3F3F3", "#3A3A3A"), border_width=1,
        border_color=self.BORDER, text_color=self.TEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_btn_selecionar.pack(side="left", padx=(0, 6))
    self._arquivos_btn_apagar_selecionados = ctk.CTkButton(
        actions, text="Apagar selecionados", command=self._apagar_datas_selecionadas,
        width=132, height=32, corner_radius=7, state="disabled",
        fg_color=("#F1F1F1", "#353A3F"), hover_color=("#F1F1F1", "#353A3F"),
        border_width=1, border_color=self.BORDER, text_color=self.SUBTEXT,
        font=("Segoe UI", 10, "bold")
    )
    self._arquivos_btn_apagar_selecionados.pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        actions, text="Limpar todo histórico", command=self._limpar_historico_planilhas,
        width=142, height=32, corner_radius=7, fg_color=self.CARD,
        hover_color=("#FDECEC", "#3A2424"), border_width=1,
        border_color=self.ERROR, text_color=self.ERROR,
        font=("Segoe UI", 10, "bold")
    ).pack(side="left")

    self._arquivos_body = ctk.CTkFrame(win, fg_color="transparent")
    self._arquivos_body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    hoje = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    self._arquivos_mes = hoje
    self._atualizar_contador_arquivos(hoje)
    self._atualizar_contador_selecao()
    self._renderizar_calendario_arquivos()
    win.update_idletasks()


def _excluir_historico_planilha_arquivos(self, item):
    ident = str(item.get("id", ""))
    itens = self._carregar_historico_planilhas()
    novos = [x for x in itens if str(x.get("id", "")) != ident]
    self._salvar_historico_planilhas(novos)
    try:
        self._atualizar_contador_arquivos(self._arquivos_mes or datetime.now())
    except Exception:
        pass
    if self._arquivos_data_selecionada is not None:
        self._mostrar_planilhas_do_dia(self._arquivos_data_selecionada)
    else:
        self._renderizar_calendario_arquivos()


def _registrar_historico_planilha_arquivos(self, cells, timestamp=None):
    if not hasattr(self, "__base_registrar_historico_planilha"):
        return
    self.__base_registrar_historico_planilha(cells, timestamp)
    try:
        self._atualizar_contador_arquivos(self._arquivos_mes or datetime.now())
    except Exception:
        pass


def _instalar_metodos_arquivos(app_class):
    app_class._contar_codigos_mes = _contar_codigos_mes_arquivos
    app_class._formatar_contador_arquivos = _formatar_contador_arquivos_arquivos
    app_class._atualizar_contador_arquivos = _atualizar_contador_arquivos_arquivos
    app_class._atualizar_contador_selecao = _atualizar_contador_selecao_arquivos
    app_class._cancelar_animacao_selecao = _cancelar_animacao_selecao_arquivos
    app_class._animar_selecao_data = _animar_selecao_data_arquivos
    app_class._executar_animacao_selecao = _executar_animacao_selecao_arquivos
    app_class._toggle_modo_selecao_arquivos = _toggle_modo_selecao_arquivos_arquivos
    app_class._toggle_data_selecionada = _toggle_data_selecionada_arquivos
    app_class._apagar_datas_selecionadas = _apagar_datas_selecionadas_arquivos
    app_class._limpar_historico_planilhas = _limpar_historico_planilhas_arquivos
    app_class._clique_calendario_arquivos = _clique_calendario_arquivos_arquivos
    app_class._desenhar_calendario_arquivos = _desenhar_calendario_arquivos_arquivos
    app_class._renderizar_calendario_arquivos = _renderizar_calendario_arquivos_arquivos
    app_class._mudar_mes_arquivos = _mudar_mes_arquivos_arquivos
    app_class._fechar_historico_planilha = _fechar_historico_planilha_arquivos
    app_class.abrir_historico_planilha = _abrir_historico_planilha_arquivos
    app_class._excluir_historico_planilha = _excluir_historico_planilha_arquivos
    app_class._registrar_historico_planilha = _registrar_historico_planilha_arquivos


def aplicar_patch_arquivos(app_class):
    if getattr(app_class, "_patch_arquivos_aplicado", False):
        return
    app_class._patch_arquivos_aplicado = True
    app_class.__base_registrar_historico_planilha = app_class._registrar_historico_planilha
    original_init = app_class.__init__

    def init_arquivos(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._arquivos_modo_selecao = False
        self._arquivos_datas_selecionadas = set()
        self._arquivos_animacao_data = None
        self._arquivos_animacao_frame = 0
        self._arquivos_animacao_job = None
        self._arquivos_btn_selecionar = None
        self._arquivos_btn_apagar_selecionados = None
        self._arquivos_contador_selecao = None

    app_class.__init__ = init_arquivos
    _instalar_metodos_arquivos(app_class)
