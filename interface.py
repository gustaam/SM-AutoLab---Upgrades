from pathlib import Path
import json
import threading
import sys
from datetime import datetime
from tkinter import filedialog, messagebox, Canvas

import customtkinter as ctk

from app import ler_checkpoint, salvar_checkpoint, principal


class App:
    # Fluent 2 palettes. Dark mode usa um grafite próximo ao chrome moderno
    # do Windows/Edge, evitando preto puro.
    BG = ("#F5F5F5", "#24292E")
    CARD = ("#FFFFFF", "#2D3338")
    TEXT = ("#242424", "#F2F4F5")
    SUBTEXT = ("#616161", "#C2C7CB")
    BORDER = ("#E0E0E0", "#465058")
    ACCENT = ("#0F6CBD", "#4CC2FF")
    ACCENT_HOVER = ("#115EA3", "#77D1FF")
    SUCCESS = ("#107C10", "#6CCB5F")
    ERROR = ("#D13438", "#FF7074")
    WARNING = ("#CA5010", "#F4B65F")
    INFO = ("#0F6CBD", "#4CC2FF")

    THEME_LABELS = {
        "light": "Claro",
        "dark": "Escuro",
        "system": "Padrão do Windows",
    }

    def __init__(self):
        self.app = ctk.CTk()
        self._configurar_icone_janela()
        self.caminho = None
        self._parar = False
        self._closing = False
        self._checkpoint_indice_seguro = 0
        self._automacao_atual = None
        self._retomada_dialogo_aberto = False
        self._log_count = 0
        self._historico = []  # mantido para compatibilidade com versões anteriores
        self._historico_execucoes = []
        self._execucao_atual = None
        self._erros_codigos = []
        self._historico_arquivo = Path.home() / ".sm_autolab_historico.json"
        self._tema = "system"
        self._menu_config = None
        self._menu_aparencia = None
        self._menu_close_job = None
        self._tooltip = None
        self._status_blink_job = None
        self._status_blink_visible = True
        self._status_blink_fast = False
        self._carregar_estado_persistente()
        ctk.set_appearance_mode(self._tema)
        ctk.set_default_color_theme("blue")
        self.config_app()

    def _configurar_icone_janela(self):
        try:
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
            icone = base / "SM AutoLab.ico"
            if icone.exists():
                self.app.iconbitmap(str(icone))
        except Exception:
            # Ícone é somente visual; falha aqui não deve impedir a abertura.
            pass

    def config_app(self):
        self.app.title("SM AutoLab")
        self.app.geometry("900x600")
        self.app.resizable(False, False)
        self.app.configure(fg_color=self.BG)
        self.app.protocol("WM_DELETE_WINDOW", self._fechar_aplicativo)
        self.app.bind("<Configure>", self._reposicionar_menus, add="+")
        self.app.bind("<Unmap>", self._fechar_menus, add="+")

        # Abre a janela em tamanho maior e centralizada na tela.
        self.app.update_idletasks()
        largura = 900
        altura = 600
        tela_w = self.app.winfo_screenwidth()
        tela_h = self.app.winfo_screenheight()
        x = max((tela_w - largura) // 2, 0)
        y = max((tela_h - altura) // 2, 0)
        self.app.geometry(f"{largura}x{altura}+{x}+{y}")

        # Cabeçalho Fluent 2: maior e com ações de configuração.
        header = ctk.CTkFrame(
            self.app,
            fg_color=self.CARD,
            corner_radius=0,
            height=84
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title = ctk.CTkFrame(header, fg_color="transparent")
        title.pack(side="left", padx=20, pady=11)

        ctk.CTkLabel(
            title,
            text="SM AutoLab",
            text_color=self.TEXT,
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w")

        ctk.CTkLabel(
            title,
            text="Automação de lançamentos Feegow",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 13)
        ).pack(anchor="w", pady=(1, 0))

        right_header = ctk.CTkFrame(header, fg_color="transparent")
        right_header.pack(side="right", padx=18, pady=17)

        self.botao_configuracoes = ctk.CTkButton(
            right_header,
            text="Configurações",
            command=self._fixar_menu_configuracoes,
            width=128,
            height=40,
            corner_radius=7,
            fg_color=self.CARD,
            hover_color=("#F3F3F3", "#3A3A3A"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        )
        self.botao_configuracoes.pack(side="left", padx=(0, 10))
        self.botao_configuracoes.bind("<Enter>", self._mostrar_menu_configuracoes)
        self.botao_configuracoes.bind("<Leave>", self._agendar_fechar_menus)

        # Status com geometria fixa. A animação ocorre somente dentro do
        # canvas, sem alterar o tamanho do controle ou empurrar Configurações.
        self.status_pill = ctk.CTkFrame(
            right_header,
            width=190,
            height=40,
            corner_radius=20,
            fg_color=("#E7F5E7", "#21482A")
        )
        self.status_pill.pack(side="left")
        self.status_pill.pack_propagate(False)

        # Indicador e texto centralizados como um conjunto.
        self.status_indicator = Canvas(
            self.status_pill,
            width=18,
            height=18,
            bd=0,
            highlightthickness=0,
            relief="flat",
            bg="#E7F5E7"
        )
        self.status_indicator.place(x=31, y=13)

        self._status_halo = self.status_indicator.create_oval(
            2, 2, 16, 16,
            fill="#BCE7C1",
            outline=""
        )
        self._status_dot = self.status_indicator.create_oval(
            6, 6, 12, 12,
            fill="#107C10",
            outline=""
        )

        self.status_text = ctk.CTkLabel(
            self.status_pill,
            text="Pronto",
            text_color=self.SUCCESS,
            font=("Segoe UI", 13, "bold")
        )
        self.status_text.place(x=57, y=6)

        # Mantém a área principal rolável e o rodapé fixo para proteger
        # Iniciar/Parar em janelas compactas.
        main = ctk.CTkScrollableFrame(
            self.app,
            fg_color=self.BG,
            corner_radius=0,
            scrollbar_button_color=("#C8C8C8", "#626262"),
            scrollbar_button_hover_color=("#AFAFAF", "#777777")
        )
        main.pack(fill="both", expand=True, padx=14, pady=8)

        top = ctk.CTkFrame(main, fg_color="transparent")
        top.pack(fill="x", pady=(0, 7))
        top.grid_columnconfigure(0, weight=4)
        top.grid_columnconfigure(1, weight=6)

        config = self._card(top)
        config.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._section_title(config, "Seleção")

        file_row = ctk.CTkFrame(config, fg_color="transparent")
        file_row.pack(fill="x", padx=14, pady=(10, 5))
        ctk.CTkLabel(file_row, text="Planilha", text_color=self.TEXT,
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 8))
        self.arquivo_label = ctk.CTkLabel(
            file_row, text="Nenhuma selecionada", text_color=self.SUBTEXT,
            font=("Segoe UI", 13), anchor="w"
        )
        self.arquivo_label.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.botao_planilha = ctk.CTkButton(
            file_row, text="Selecionar", command=self.config_caminho,
            width=100, height=32, corner_radius=6,
            fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER,
            font=("Segoe UI", 12, "bold")
        )
        self.botao_planilha.pack(side="right")

        page_row = ctk.CTkFrame(config, fg_color="transparent")
        page_row.pack(fill="x", padx=14, pady=(1, 9))
        ctk.CTkLabel(page_row, text="Página", text_color=self.TEXT,
                     font=("Segoe UI", 12, "bold")).pack(side="left", padx=(0, 8))
        self.pagina = ctk.CTkEntry(
            page_row, width=62, height=32, corner_radius=6,
            border_color=self.BORDER, fg_color=self.CARD,
            text_color=self.TEXT, font=("Segoe UI", 13)
        )
        self.pagina.pack(side="left")
        self.pagina.insert(0, "1")

        progress = self._card(top)
        progress.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ph = ctk.CTkFrame(progress, fg_color="transparent")
        ph.pack(fill="x", padx=14, pady=(11, 5))
        ctk.CTkLabel(ph, text="Progresso", text_color=self.TEXT,
                     font=("Segoe UI", 14, "bold")).pack(side="left")
        self.percentual_label = ctk.CTkLabel(
            ph, text="0%", text_color=self.TEXT,
            font=("Segoe UI", 20, "bold")
        )
        self.percentual_label.pack(side="right")
        self.progresso = ctk.CTkProgressBar(
            progress, height=8, corner_radius=4,
            fg_color=("#E5E5E5", "#454C52"), progress_color=self.ACCENT
        )
        self.progresso.set(0)
        self.progresso.pack(fill="x", padx=14, pady=(0, 2))
        self.progresso_label = ctk.CTkLabel(
            progress, text="0 / 0", text_color=self.SUBTEXT,
            font=("Segoe UI", 12)
        )
        self.progresso_label.pack(anchor="w", padx=14, pady=(0, 9))

        stats = ctk.CTkFrame(main, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 6))
        stats.grid_columnconfigure((0, 1, 2), weight=1)
        self.sucesso_card = self._stat_card(stats, "✓", "Sucesso", "0", self.SUCCESS)
        self.sucesso_card.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.erro_card = self._stat_card(stats, "!", "Erros", "0", self.ERROR)
        self.erro_card.grid(row=0, column=1, sticky="ew", padx=5)
        self.codigo_card = self._stat_card(stats, "›", "Código atual", "—", self.INFO)
        self.codigo_card.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        activity_card = self._card(main)
        activity_card.pack(fill="x", pady=(0, 5))
        activity_card.configure(height=205)
        activity_card.pack_propagate(False)
        self._section_title(activity_card, "Acompanhamento")

        # Fluent-inspired tab row, like the reference image.
        tabs = ctk.CTkFrame(activity_card, fg_color=("#F3F3F3", "#343A40"), corner_radius=7)
        tabs.pack(pady=(5, 5), padx=14)

        self.tab_buttons = {}
        for name in ("Atividade", "Erros", "Histórico"):
            btn = ctk.CTkButton(
                tabs, text=name, command=lambda n=name: self._selecionar_aba(n),
                width=86, height=30, corner_radius=6,
                fg_color=("#E5F1FB", "#183B54") if name == "Atividade" else "transparent",
                hover_color="#EDEDED",
                text_color=self.TEXT, font=("Segoe UI", 11, "bold")
            )
            btn.pack(side="left", padx=2, pady=2)
            self.tab_buttons[name] = btn

        self.tab_area = ctk.CTkFrame(activity_card, fg_color="transparent")
        self.tab_area.pack(fill="both", expand=True, padx=14, pady=(0, 5))

        self.aba_atividade = ctk.CTkFrame(self.tab_area, fg_color="transparent")
        self.aba_erros = ctk.CTkFrame(self.tab_area, fg_color="transparent")
        self.aba_historico = ctk.CTkFrame(self.tab_area, fg_color="transparent")

        # Activity tab
        self.atividade = ctk.CTkTextbox(
            self.aba_atividade, height=90, corner_radius=7,
            fg_color=("#FAFAFA", "#252A2F"), border_width=1, border_color=self.BORDER,
            text_color=self.SUBTEXT, font=("Consolas", 10), wrap="word"
        )
        self.atividade.pack(fill="both", expand=True)
        self.atividade.configure(state="disabled")

        # Errors tab: each code is directly copyable.
        erro_info = ctk.CTkFrame(self.aba_erros, fg_color="transparent")
        erro_info.pack(fill="x", pady=(0, 6))
        self.erros_titulo = ctk.CTkLabel(
            erro_info, text="Nenhum código com erro", text_color=self.SUBTEXT,
            font=("Segoe UI", 12, "bold")
        )
        self.erros_titulo.pack(side="left")
        ctk.CTkLabel(
            erro_info, text="Clique no código para copiar", text_color=self.SUBTEXT,
            font=("Segoe UI", 10)
        ).pack(side="right")

        self.erros_frame = ctk.CTkScrollableFrame(
            self.aba_erros, height=80, fg_color=("#FAFAFA", "#252A2F"),
            corner_radius=7, border_width=1, border_color=self.BORDER
        )
        self.erros_frame.pack(fill="both", expand=True)
        self._limpar_erros_visuais(salvar=False)

        # Restore persisted errors after the UI is ready.
        self._renderizar_erros_persistentes()

        # History tab: executions shown as expandable folders.
        history_header = ctk.CTkFrame(self.aba_historico, fg_color="transparent")
        history_header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(
            history_header, text="Execuções recentes (máx. 5)",
            text_color=self.TEXT, font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        self.botao_limpar_historico = ctk.CTkButton(
            history_header, text="Limpar histórico", command=self._limpar_historico,
            width=108, height=28, corner_radius=6,
            fg_color="#FFFFFF", hover_color="#FDE7E9", border_width=1,
            border_color="#E0E0E0", text_color=self.ERROR,
            font=("Segoe UI", 11, "bold")
        )
        self.botao_limpar_historico.pack(side="right")

        self.historico_lista = ctk.CTkScrollableFrame(
            self.aba_historico, fg_color=("#FAFAFA", "#252A2F"),
            corner_radius=7, border_width=1, border_color=self.BORDER
        )
        self.historico_lista.pack(fill="both", expand=True)

        self._restaurar_historico_na_tela()

        self._selecionar_aba("Atividade")

        actions = ctk.CTkFrame(self.app, fg_color=self.CARD, corner_radius=0)
        actions.pack(fill="x", side="bottom", pady=(0, 0))
        actions.configure(height=72)
        actions.pack_propagate(False)
        self.status_label = ctk.CTkLabel(
            actions, text="Pronto para iniciar", text_color=self.SUBTEXT,
            font=("Segoe UI", 13, "bold")
        )
        self.status_label.pack(side="left", padx=22, pady=11)

        buttons = ctk.CTkFrame(actions, fg_color="transparent")
        buttons.pack(side="right", padx=20, pady=11)
        self.botao_parar = ctk.CTkButton(
            buttons, text="■  Parar", command=self.parar,
            width=140, height=46, corner_radius=8,
            fg_color=self.CARD, hover_color=("#FDECEC", "#3A2424"),
            border_width=1, border_color=self.ERROR, text_color=self.ERROR,
            font=("Segoe UI", 14, "bold"), state="disabled"
        )
        self.botao_parar.pack(side="left", padx=(0, 7))
        self.botao_iniciar = ctk.CTkButton(
            buttons, text="▶  Iniciar", command=self.iniciar_thread,
            width=150, height=46, corner_radius=8,
            fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER,
            font=("Segoe UI", 14, "bold")
        )
        self.botao_iniciar.pack(side="left")

        self._add_activity("Sistema pronto para iniciar.", self.INFO)
        self._iniciar_pisca_status()
        self.app.after(350, self._verificar_retomada_pendente)


    def _reposicionar_menus(self, _event=None):
        if self._closing:
            return

        # When the native window moves, keep the floating menus attached.
        try:
            if self._menu_config is not None and self._menu_config.winfo_exists():
                bx = self.botao_configuracoes.winfo_rootx()
                by = self.botao_configuracoes.winfo_rooty() + self.botao_configuracoes.winfo_height() + 4
                self._menu_config.geometry(f"205x94+{max(bx - 40, 0)}+{max(by, 0)}")
            if self._menu_aparencia is not None and self._menu_aparencia.winfo_exists():
                if self._menu_config is not None and self._menu_config.winfo_exists():
                    self._menu_config.update_idletasks()
                    x = self._menu_config.winfo_rootx() + self._menu_config.winfo_width() - 2
                    y = self._menu_config.winfo_rooty()
                    self._menu_aparencia.geometry(f"225x158+{max(x,0)}+{max(y,0)}")
        except Exception:
            pass

    def _fixar_menu_configuracoes(self):
        self._mostrar_menu_configuracoes()

    def _mostrar_menu_configuracoes(self, _event=None):
        self._cancelar_fechar_menus()
        if self._menu_config is not None:
            try:
                if self._menu_config.winfo_exists():
                    return
            except Exception:
                pass

        menu = ctk.CTkToplevel(self.app)
        self._menu_config = menu
        menu.overrideredirect(True)
        menu.transient(self.app)
        menu.attributes("-topmost", True)
        menu.configure(fg_color=self.CARD, border_width=1, border_color=self.BORDER)

        aparencia = ctk.CTkButton(
            menu,
            text="Aparência  ›",
            command=self._mostrar_menu_aparencia,
            width=190,
            height=38,
            corner_radius=6,
            fg_color=self.CARD,
            hover_color=("#F3F3F3", "#3A3A3A"),
            text_color=self.TEXT,
            font=("Segoe UI", 12)
        )
        aparencia.pack(fill="x", padx=6, pady=(7, 3))
        aparencia.bind("<Enter>", self._mostrar_menu_aparencia)
        aparencia.bind("<Enter>", self._cancelar_fechar_menus, add="+")
        aparencia.bind("<Leave>", self._agendar_fechar_menus)

        mudar = ctk.CTkButton(
            menu,
            text="Mudar o Feegow",
            command=self._abrir_popup_feegow,
            width=190,
            height=38,
            corner_radius=6,
            fg_color=self.CARD,
            hover_color=("#F3F3F3", "#3A3A3A"),
            text_color=self.TEXT,
            font=("Segoe UI", 12)
        )
        mudar.pack(fill="x", padx=6, pady=(3, 7))
        mudar.bind("<Enter>", self._entrar_mudar_feegow)
        mudar.bind("<Leave>", self._agendar_fechar_menus)

        menu.bind("<Enter>", self._cancelar_fechar_menus)
        menu.bind("<Leave>", self._agendar_fechar_menus)

        self.app.update_idletasks()
        x = self.botao_configuracoes.winfo_rootx()
        y = self.botao_configuracoes.winfo_rooty() + self.botao_configuracoes.winfo_height() + 4
        menu.geometry(f"205x94+{x-40}+{y}")
        menu.lift()

    def _mostrar_menu_aparencia(self, _event=None):
        self._cancelar_fechar_menus()
        if self._menu_aparencia is not None:
            try:
                if self._menu_aparencia.winfo_exists():
                    return
            except Exception:
                pass
        if self._menu_config is None:
            self._mostrar_menu_configuracoes()
            return

        self._menu_config.update_idletasks()
        x = self._menu_config.winfo_rootx() + self._menu_config.winfo_width() - 2
        y = self._menu_config.winfo_rooty()

        sub = ctk.CTkToplevel(self.app)
        self._menu_aparencia = sub
        sub.overrideredirect(True)
        sub.transient(self.app)
        sub.attributes("-topmost", True)
        sub.configure(fg_color=self.CARD, border_width=1, border_color=self.BORDER)

        titulo = ctk.CTkLabel(
            sub, text="Aparência", text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        )
        titulo.pack(anchor="w", padx=12, pady=(9, 4))

        for modo, rotulo in (
            ("light", "Claro"),
            ("dark", "Escuro"),
            ("system", "Padrão do Windows"),
        ):
            marcado = "✓  " if modo == self._tema else "   "
            btn = ctk.CTkButton(
                sub,
                text=marcado + rotulo,
                command=lambda m=modo: self._selecionar_tema(m),
                width=210,
                height=34,
                corner_radius=6,
                fg_color=self.CARD,
                hover_color=("#F3F3F3", "#3A3A3A"),
                text_color=self.TEXT,
                font=("Segoe UI", 11)
            )
            btn.pack(fill="x", padx=6, pady=2)
            btn.configure(anchor="w")
            btn.bind("<Enter>", self._cancelar_fechar_menus)
            btn.bind("<Leave>", self._agendar_fechar_aparencia)

        sub.bind("<Enter>", self._cancelar_fechar_menus)
        sub.bind("<Leave>", self._agendar_fechar_aparencia)

        sub.geometry(f"225x158+{max(x,0)}+{max(y,0)}")
        sub.lift()

    def _entrar_mudar_feegow(self, _event=None):
        # O submenu Aparência deve desaparecer ao sair da opção Aparência.
        self._cancelar_fechar_menus()
        if self._menu_aparencia is not None:
            try:
                self._menu_aparencia.destroy()
            except Exception:
                pass
            self._menu_aparencia = None

    def _agendar_fechar_aparencia(self, _event=None):
        self._cancelar_fechar_menus()
        self._menu_close_job = self.app.after(160, self._fechar_submenu_aparencia)

    def _fechar_submenu_aparencia(self):
        self._menu_close_job = None
        if self._menu_aparencia is not None:
            try:
                self._menu_aparencia.destroy()
            except Exception:
                pass
            self._menu_aparencia = None

    def _cancelar_fechar_menus(self, _event=None):
        if self._menu_close_job is not None:
            try:
                self.app.after_cancel(self._menu_close_job)
            except Exception:
                pass
            self._menu_close_job = None

    def _agendar_fechar_menus(self, _event=None):
        self._cancelar_fechar_menus()
        self._menu_close_job = self.app.after(280, self._fechar_menus)

    def _fechar_menus(self):
        self._menu_close_job = None
        for attr in ("_menu_aparencia", "_menu_config"):
            menu = getattr(self, attr, None)
            if menu is not None:
                try:
                    menu.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)

    def _selecionar_tema(self, tema):
        if tema not in ("light", "dark", "system"):
            return
        self._tema = tema
        ctk.set_appearance_mode(tema)
        self._salvar_estado_persistente()
        self._fechar_menus()
        self._add_activity(
            f"Aparência alterada para {self.THEME_LABELS[tema]}.",
            self.INFO
        )

    def _abrir_popup_feegow(self):
        self._cancelar_fechar_menus()
        self._fechar_menus()

        try:
            from config import carregar_configuracoes, salvar_configuracoes
            dados = carregar_configuracoes()
        except Exception:
            dados = {
                "SITE_URL": "https://franchising.feegow.com/pre-v8.1/extranet/?P=Login&Licenca=15003",
                "PORTAL_USUARIO": "",
                "PORTAL_SENHA": "",
            }

        popup = ctk.CTkToplevel(self.app)
        popup.title("Mudar o Feegow")
        popup.geometry("560x400")
        popup.resizable(False, False)
        popup.transient(self.app)
        popup.grab_set()

        ctk.CTkLabel(
            popup, text="Mudar o Feegow",
            text_color=self.TEXT, font=("Segoe UI", 19, "bold")
        ).pack(anchor="w", padx=22, pady=(20, 2))

        ctk.CTkLabel(
            popup,
            text="Altere o endereço e os dados de acesso utilizados pela automação.",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=22, pady=(0, 14))

        form = ctk.CTkFrame(popup, fg_color="transparent")
        form.pack(fill="x", padx=22)

        ctk.CTkLabel(
            form, text="Endereço do Feegow",
            text_color=self.TEXT, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 4))
        site_entry = ctk.CTkEntry(
            form, height=36, corner_radius=6,
            fg_color=self.CARD, border_color=self.BORDER,
            text_color=self.TEXT, font=("Segoe UI", 11)
        )
        site_entry.pack(fill="x", pady=(0, 12))
        site_entry.insert(0, dados.get("SITE_URL", ""))

        ctk.CTkLabel(
            form, text="Usuário",
            text_color=self.TEXT, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 4))
        user_entry = ctk.CTkEntry(
            form, height=36, corner_radius=6,
            fg_color=self.CARD, border_color=self.BORDER,
            text_color=self.TEXT, font=("Segoe UI", 11)
        )
        user_entry.pack(fill="x", pady=(0, 12))
        user_entry.insert(0, dados.get("PORTAL_USUARIO", ""))

        ctk.CTkLabel(
            form, text="Senha",
            text_color=self.TEXT, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(0, 4))
        pass_entry = ctk.CTkEntry(
            form, height=36, corner_radius=6,
            fg_color=self.CARD, border_color=self.BORDER,
            text_color=self.TEXT, font=("Segoe UI", 11),
        )
        pass_entry.pack(fill="x")
        pass_entry.insert(0, dados.get("PORTAL_SENHA", ""))

        actions = ctk.CTkFrame(popup, fg_color="transparent")
        actions.pack(fill="x", padx=22, pady=(22, 30))

        valores_iniciais = {
            "SITE_URL": str(dados.get("SITE_URL", "")),
            "PORTAL_USUARIO": str(dados.get("PORTAL_USUARIO", "")),
            "PORTAL_SENHA": str(dados.get("PORTAL_SENHA", "")),
        }

        def valores_atuais():
            return {
                "SITE_URL": site_entry.get(),
                "PORTAL_USUARIO": user_entry.get(),
                "PORTAL_SENHA": pass_entry.get(),
            }

        def atualizar_estado_salvar(_event=None):
            alterado = valores_atuais() != valores_iniciais
            salvar_btn.configure(
                state="normal" if alterado else "disabled",
                fg_color=self.ACCENT if alterado else ("#E5E5E5", "#454C52"),
                hover_color=self.ACCENT_HOVER if alterado else ("#E5E5E5", "#454C52"),
                text_color="#FFFFFF" if alterado else ("#8A8A8A", "#AEB4B9")
            )

        def restaurar():
            try:
                from config import restaurar_configuracoes
                novos = restaurar_configuracoes()
                site_entry.delete(0, "end")
                site_entry.insert(0, novos["SITE_URL"])
                user_entry.delete(0, "end")
                user_entry.insert(0, novos["PORTAL_USUARIO"])
                pass_entry.delete(0, "end")
                pass_entry.insert(0, novos["PORTAL_SENHA"])
                atualizar_estado_salvar()
            except Exception as exc:
                messagebox.showerror(
                    "Não foi possível restaurar",
                    str(exc),
                    parent=popup
                )

        def salvar():
            try:
                from config import salvar_configuracoes
                salvar_configuracoes(
                    site_entry.get(),
                    user_entry.get(),
                    pass_entry.get()
                )
                messagebox.showinfo(
                    "Feegow atualizado",
                    "Os dados foram salvos e serão usados na próxima execução.",
                    parent=popup
                )
                popup.destroy()
            except Exception as exc:
                messagebox.showerror(
                    "Não foi possível salvar",
                    str(exc),
                    parent=popup
                )

        # Detecta alterações reais em qualquer campo.
        for campo in (site_entry, user_entry, pass_entry):
            campo.bind("<KeyRelease>", atualizar_estado_salvar)

        ctk.CTkButton(
            actions,
            text="Restaurar",
            command=restaurar,
            width=110,
            height=40,
            corner_radius=7,
            fg_color=self.CARD,
            hover_color=("#F3F3F3", "#3A3A3A"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        ctk.CTkFrame(
            actions, fg_color="transparent"
        ).pack(side="left", fill="x", expand=True)

        # Ordem visual: Cancelar à esquerda e Salvar à direita.
        ctk.CTkButton(
            actions,
            text="Cancelar",
            command=popup.destroy,
            width=110,
            height=40,
            corner_radius=7,
            fg_color=self.CARD,
            hover_color=("#F3F3F3", "#3A3A3A"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="right", padx=(8, 0))

        salvar_btn = ctk.CTkButton(
            actions,
            text="Salvar",
            command=salvar,
            width=110,
            height=40,
            corner_radius=7,
            fg_color=("#E5E5E5", "#454C52"),
            hover_color=("#E5E5E5", "#454C52"),
            text_color=("#8A8A8A", "#AEB4B9"),
            state="disabled",
            font=("Segoe UI", 12, "bold")
        )
        salvar_btn.pack(side="right")
        atualizar_estado_salvar()


    def _selecionar_aba(self, nome):
        for frame in (self.aba_atividade, self.aba_erros, self.aba_historico):
            frame.pack_forget()
        mapa = {
            "Atividade": self.aba_atividade,
            "Erros": self.aba_erros,
            "Histórico": self.aba_historico,
        }
        mapa[nome].pack(fill="both", expand=True)
        for n, btn in self.tab_buttons.items():
            btn.configure(
                fg_color=("#E5F1FB", "#183B54") if n == nome else "transparent",
                text_color=self.ACCENT if n == nome else self.TEXT
            )

    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=10,
                            border_width=1, border_color=self.BORDER)

    def _section_title(self, parent, text):
        ctk.CTkLabel(
            parent, text=text, text_color=self.TEXT,
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="w", padx=14, pady=(10, 0))

    def _stat_card(self, parent, icon, title, value, accent):
        card = ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=10,
                            border_width=1, border_color=self.BORDER, height=80)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=14, pady=8)
        icon_sizes = {"✓": 18, "!": 22, "›": 30}
        icon_font = icon_sizes.get(str(icon), 22)
        ctk.CTkLabel(
            row,
            text=icon,
            width=44,
            height=44,
            corner_radius=22,
            fg_color=("#F3F3F3", "#3A3A3A"),
            text_color=accent,
            font=("Segoe UI", icon_font, "bold")
        ).pack(side="left", padx=(0, 12))

        text_box = ctk.CTkFrame(row, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(text_box, text=title, text_color=self.SUBTEXT,
                     font=("Segoe UI", 10)).pack(anchor="w")
        value_label = ctk.CTkLabel(text_box, text=value, text_color=self.TEXT,
                                   font=("Segoe UI", 16, "bold"), anchor="w")
        value_label.pack(anchor="w")
        card.value_label = value_label
        return card

    def _set_stat(self, card, value):
        card.value_label.configure(text=str(value))

    def _add_activity(self, text, kind="info"):
        prefix = {self.SUCCESS: "✓", self.ERROR: "✕", self.WARNING: "!", self.INFO: "→"}.get(kind, "→")
        line = f"{datetime.now():%H:%M:%S}  {prefix}  {text}\n"
        self.atividade.configure(state="normal")
        self.atividade.insert("end", line)
        self._log_count += 1
        if self._log_count > 80:
            self.atividade.delete("1.0", "2.0")
            self._log_count -= 1
        self.atividade.see("end")
        self.atividade.configure(state="disabled")

    def _carregar_estado_persistente(self):
        try:
            if not self._historico_arquivo.exists():
                return
            dados = json.loads(self._historico_arquivo.read_text(encoding="utf-8"))
            execucoes = dados.get("historico_execucoes", [])
            erros = dados.get("erros", [])
            tema = dados.get("tema", "system")
            if tema in ("light", "dark", "system"):
                self._tema = tema
            if isinstance(execucoes, list):
                self._historico_execucoes = [x for x in execucoes if isinstance(x, dict)][-5:]
            if isinstance(erros, list):
                self._erros_codigos = [str(x) for x in erros][-200:]
        except Exception:
            self._historico_execucoes = []
            self._erros_codigos = []

    def _salvar_estado_persistente(self):
        try:
            dados = {
                "historico_execucoes": self._historico_execucoes[-5:],
                "erros": self._erros_codigos[-200:],
                "tema": self._tema,
                "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            tmp = self._historico_arquivo.with_suffix(".tmp")
            tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._historico_arquivo)
        except Exception:
            pass

    def _renderizar_erros_persistentes(self):
        if not hasattr(self, "erros_frame"):
            return
        for w in self.erros_frame.winfo_children():
            w.destroy()
        for codigo in self._erros_codigos:
            self._criar_botao_erro(codigo)
        self.erros_titulo.configure(
            text=f"{len(self._erros_codigos)} código(s) com erro" if self._erros_codigos
            else "Nenhum código com erro"
        )

    def _criar_botao_erro(self, codigo, parent=None):
        codigo = str(codigo)
        parent = parent or self.erros_frame

        btn = ctk.CTkButton(
            parent,
            text=codigo,
            command=lambda c=codigo: self._copiar_codigo(c),
            height=28,
            corner_radius=5,
            fg_color=("#FDE7E9", "#4B2529"),
            hover_color=("#FAD2D5", "#603034"),
            text_color=self.ERROR,
            border_width=1,
            border_color=("#F1B8BC", "#7A4448"),
            font=("Segoe UI", 10),
            anchor="w"
        )
        btn.pack(fill="x", padx=6, pady=3)
        btn.bind("<Enter>", lambda e, b=btn: self._mostrar_tooltip(b, "Copiar"))
        btn.bind("<Leave>", self._agendar_fechar_tooltip)
        return btn

    def _mostrar_tooltip(self, widget, texto):
        self._fechar_tooltip()
        try:
            x = widget.winfo_rootx() + widget.winfo_width() - 66
            y = widget.winfo_rooty() - 34

            tip = ctk.CTkToplevel(self.app)
            self._tooltip = tip
            tip.overrideredirect(True)
            tip.configure(
                fg_color=("#2B2B2B", "#3A4147"),
                border_width=1,
                border_color=self.BORDER
            )
            ctk.CTkLabel(
                tip,
                text=texto,
                text_color=("#FFFFFF", "#242424"),
                font=("Segoe UI", 10)
            ).pack(padx=9, pady=5)
            tip.geometry(f"+{max(x, 0)}+{max(y, 0)}")
            tip.lift()
        except Exception:
            self._tooltip = None

    def _agendar_fechar_tooltip(self, _event=None):
        self.app.after(80, self._fechar_tooltip)

    def _fechar_tooltip(self):
        if self._tooltip is not None:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None

    def _limpar_erros_visuais(self, salvar=True):
        for w in self.erros_frame.winfo_children():
            w.destroy()
        self._erros_codigos = []
        self.erros_titulo.configure(text="Nenhum código com erro")
        if salvar:
            self._salvar_estado_persistente()

    def _add_erro_codigo(self, codigo):
        codigo = str(codigo)
        if codigo in self._erros_codigos:
            return
        self._erros_codigos.append(codigo)
        self.erros_titulo.configure(text=f"{len(self._erros_codigos)} código(s) com erro")
        self._criar_botao_erro(codigo)
        self._salvar_estado_persistente()

    def _copiar_codigo(self, codigo):
        self.app.clipboard_clear()
        self.app.clipboard_append(str(codigo))
        self.app.update()
        self._add_activity(f"Código {codigo} copiado.", self.INFO)
        self.atualizar_status("Código copiado")

    def _verificar_retomada_pendente(self):
        if self._retomada_dialogo_aberto or self._closing:
            return
        pendente = self._execucao_atual
        if not isinstance(pendente, dict):
            return

        status = str(pendente.get("status", "")).lower()
        if "interrompida" not in status and "andamento" not in status:
            return

        planilha_nome = str(pendente.get("planilha", "")).strip()
        pagina = int(pendente.get("pagina", 1) or 1)
        inicio = int(pendente.get("checkpoint", pendente.get("inicio_indice", 1)) or 1)
        proximo = max(1, inicio)

        # The persisted record stores only the spreadsheet filename, so resolve
        # it from the last selected path when available. The path itself is also
        # restored by the normal persistent state when present.
        caminho = self.caminho
        if not caminho:
            caminho = self._localizar_planilha_pendente(planilha_nome)
        if caminho and Path(caminho).exists():
            self.caminho = str(caminho)
            self.planilha_label.configure(text=Path(caminho).name)
            try:
                self.pagina.delete(0, "end")
                self.pagina.insert(0, str(pagina))
            except Exception:
                pass

        self._retomada_dialogo_aberto = True
        try:
            detalhes = (
                "Foi encontrado um processamento interrompido.\n\n"
                f"Planilha: {planilha_nome or Path(caminho).name if caminho else 'não identificada'}\n"
                f"Página: {pagina}\n"
                f"Próximo código: {proximo}\n\n"
                "Deseja continuar de onde parou?"
            )
            resposta = messagebox.askyesno(
                "Retomar processamento",
                detalhes,
                parent=self.app
            )
            if resposta:
                if caminho and Path(caminho).exists():
                    # iniciar_thread() lerá o checkpoint e retomará no índice seguro.
                    self.iniciar_thread()
                else:
                    messagebox.showwarning(
                        "Planilha não encontrada",
                        "A planilha do processamento interrompido não foi localizada. "
                        "Selecione a planilha e clique em Iniciar para continuar.",
                        parent=self.app
                    )
            else:
                self._add_activity("Retomada recusada na abertura do aplicativo.", self.INFO)
        finally:
            self._retomada_dialogo_aberto = False

    def _localizar_planilha_pendente(self, nome):
        if not nome:
            return None
        # Prefer common user folders; avoid a broad recursive scan of the whole
        # drive during startup.
        candidatos = [
            Path.cwd(),
            Path.home() / "Downloads",
            Path.home() / "Documents",
            Path.home() / "Desktop",
            Path.home() / "OneDrive" / "Documents",
            Path.home() / "OneDrive" / "Desktop",
        ]
        encontrados=[]
        for base in candidatos:
            try:
                if not base.exists():
                    continue
                for p in base.glob(nome):
                    if p.is_file():
                        encontrados.append(p)
            except Exception:
                continue
            if encontrados:
                return str(encontrados[0])
        return None

    def _iniciar_historico_execucao(self, planilha, pagina, inicio):
        agora = datetime.now()
        self._execucao_atual = {
            "id": agora.strftime("%Y%m%d_%H%M%S_%f"),
            "inicio": agora.strftime("%Y-%m-%d %H:%M:%S"),
            "fim": "",
            "status": "Em andamento",
            "planilha": Path(planilha).name if planilha else "",
            "pagina": int(pagina) + 1,
            "inicio_indice": int(inicio) + 1,
            "total": 0,
            "sucessos": 0,
            "erros": 0,
            "codigos_erros": [],
        }
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()

    def _finalizar_historico_execucao(self, resultado, status="Concluída"):
        if not self._execucao_atual:
            return
        self._execucao_atual["fim"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._execucao_atual["status"] = status
        self._execucao_atual["total"] = int(getattr(resultado, "total_planejado", 0) or 0)
        self._execucao_atual["sucessos"] = int(getattr(resultado, "sucessos", 0) or 0)
        self._execucao_atual["erros"] = int(getattr(resultado, "erros", 0) or 0)
        self._execucao_atual["codigos_erros"] = [str(item.codigo) for item in resultado.itens if item.status == "Erro"]
        self._historico_execucoes.append(dict(self._execucao_atual))
        self._historico_execucoes = self._historico_execucoes[-5:]
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()

    def _registrar_falha_historico(self, mensagem):
        if not self._execucao_atual:
            return
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._execucao_atual["fim"] = agora
        self._execucao_atual["status"] = "Erro geral"
        self._execucao_atual["mensagem"] = str(mensagem)
        self._historico_execucoes.append(dict(self._execucao_atual))
        self._historico_execucoes = self._historico_execucoes[-5:]
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()

    def _restaurar_historico_na_tela(self):
        if not hasattr(self, "historico_lista"):
            return
        for w in self.historico_lista.winfo_children():
            w.destroy()

        if self._execucao_atual:
            self._criar_pasta_historico(self._execucao_atual, atual=True)

        historico_visivel = self._historico_execucoes[-4:] if self._execucao_atual else self._historico_execucoes[-5:]

        if not historico_visivel and not self._execucao_atual:
            ctk.CTkLabel(
                self.historico_lista, text="Nenhuma execução registrada ainda.",
                text_color=self.SUBTEXT, font=("Segoe UI", 10)
            ).pack(anchor="w", padx=8, pady=8)
            return

        for execucao in reversed(historico_visivel):
            self._criar_pasta_historico(execucao)

    def _criar_pasta_historico(self, execucao, atual=False):
        container = ctk.CTkFrame(
            self.historico_lista, fg_color="#FFFFFF", corner_radius=7,
            border_width=1, border_color=self.BORDER
        )
        container.pack(fill="x", padx=4, pady=4)

        inicio = execucao.get("inicio", "")
        status = execucao.get("status", "")
        erros = int(execucao.get("erros", 0) or 0)
        icone = "📂"
        texto = f"{icone}  {inicio}  •  {status}  •  {erros} erro(s)"

        detalhe = ctk.CTkFrame(container, fg_color=("#FAFAFA", "#252A2F"), corner_radius=5)
        aberto = {"valor": False}

        def alternar():
            if aberto["valor"]:
                detalhe.pack_forget()
                aberto["valor"] = False
                botao.configure(text=texto)
            else:
                self._preencher_detalhe_pasta(detalhe, execucao)
                detalhe.pack(fill="x", padx=6, pady=(0, 6))
                aberto["valor"] = True
                botao.configure(text=f"{texto}  ▲")

        botao = ctk.CTkButton(
            container, text=texto, command=alternar,
            height=32, corner_radius=5,
            fg_color=("#FFF4CE", "#4B3A1A") if atual else "#F5F5F5",
            hover_color="#EDEDED", text_color=self.TEXT,
            font=("Segoe UI", 11, "bold"), anchor="w"
        )
        botao.pack(fill="x", padx=6, pady=6)

    def _preencher_detalhe_pasta(self, parent, execucao):
        for w in parent.winfo_children():
            w.destroy()

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
            text=(f"Início: {inicio}    Fim: {fim}\n"
                   f"Planilha: {planilha}    Página: {pagina}\n"
                   f"Status: {status}    Processados: {total}    Sucesso: {sucessos}    Erros: {erros}"),
            text_color=self.SUBTEXT, font=("Segoe UI", 9), anchor="w", justify="left"
        ).pack(fill="x", padx=8, pady=(7, 4))

        if erros and codigos:
            ctk.CTkLabel(
                parent, text="Códigos com erro (clique para copiar):",
                text_color=self.ERROR, font=("Segoe UI", 11, "bold"), anchor="w"
            ).pack(fill="x", padx=8, pady=(0, 3))
            for codigo in codigos:
                self._criar_botao_erro(codigo, parent=parent)
        else:
            ctk.CTkLabel(
                parent, text="Nenhum código apresentou erro nessa execução.",
                text_color=self.SUCCESS, font=("Segoe UI", 10)
            ).pack(anchor="w", padx=8, pady=(3, 8))

    def _limpar_historico(self):
        if not self._historico_execucoes and not self._execucao_atual:
            self.atualizar_status("Histórico já está vazio")
            return
        confirmar = messagebox.askyesno(
            "Limpar histórico",
            "Tem certeza que deseja apagar todas as execuções salvas no histórico?\n\n"
            "Essa ação não apaga a aba 'Erros' da execução atual."
        )
        if not confirmar:
            return
        self._historico_execucoes = []
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()
        self._add_activity("Histórico de execuções apagado.", self.WARNING)
        self.atualizar_status("Histórico limpo")

    def _add_historico(self, text):
        # Mantido por compatibilidade: os detalhes da execução agora ficam agrupados em pastas.
        # Não cria entradas individuais no histórico visual.
        if self._execucao_atual:
            eventos = self._execucao_atual.setdefault("eventos", [])
            eventos.append(f"{datetime.now():%Y-%m-%d %H:%M:%S}  {text}")
            eventos[:] = eventos[-30:]
            self._salvar_estado_persistente()

    def config_caminho(self):
        caminho = filedialog.askopenfilename(
            filetypes=[("Planilhas Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
            title="Selecionar planilha"
        )
        if caminho:
            self.caminho = caminho
            self.arquivo_label.configure(text=Path(caminho).name, text_color=self.TEXT)
            self._add_activity(f"Planilha selecionada: {Path(caminho).name}", self.INFO)
            self._add_historico(f"Planilha selecionada: {Path(caminho).name}")

    def iniciar_thread(self):
        if not self.caminho:
            messagebox.showerror("Planilha necessária", "Selecione uma planilha antes de iniciar.")
            return
        pagina = self.pagina.get().strip()
        if not pagina.isdigit() or int(pagina) < 1:
            messagebox.showerror("Página inválida", "A página deve ser um número maior ou igual a 1.")
            return
        sheet = int(pagina) - 1
        inicio = ler_checkpoint(self.caminho, sheet)
        start = 0
        if inicio is not None:
            try:
                import pandas as pd
                total = len(pd.read_excel(self.caminho, sheet_name=sheet))
            except Exception:
                total = None
            if total is None or inicio < total:
                if messagebox.askyesno(
                    "Retomar processamento",
                    f"Foi encontrado um processamento interrompido.\n\n"
                    f"Próximo código: {inicio + 1}\n\nDeseja continuar de onde parou?"
                ):
                    start = inicio
                    self._add_activity(f"Retomando a partir do código {inicio + 1}.", self.WARNING)
                else:
                    self._add_activity("Retomada recusada. Começando do primeiro código.", self.INFO)
        self._iniciar_historico_execucao(self.caminho, sheet, start)
        self._checkpoint_indice_seguro = int(start)
        self._parar = False
        self.botao_iniciar.configure(state="disabled")
        self.botao_planilha.configure(state="disabled")
        self.botao_parar.configure(state="normal")
        self.progresso.set(0)
        self.progresso_label.configure(text="0 / 0")
        self.percentual_label.configure(text="0%")
        self._set_stat(self.sucesso_card, 0)
        self._set_stat(self.erro_card, 0)
        self._set_stat(self.codigo_card, "—")
        self._limpar_erros_visuais()
        self._add_activity("Iniciando automação...", self.INFO)
        self._add_historico("Nova execução iniciada.")
        self.atualizar_status("Iniciando")
        threading.Thread(target=self._executar, args=(sheet, start), daemon=True).start()

    def _executar(self, sheet, start):
        try:
            resultado = principal(self.caminho, sheet, self, start)
            if not self._closing:
                self.app.after(0, lambda: self._finalizar(resultado))
        except Exception as exc:
            if not self._closing:
                self.app.after(0, lambda: self._falha_geral(str(exc)))

    def _falha_geral(self, msg):
        self.botao_iniciar.configure(state="normal")
        self.botao_planilha.configure(state="normal")
        self.botao_parar.configure(state="disabled")
        self._add_activity("Processo interrompido por erro.", self.ERROR)
        self._registrar_falha_historico(msg)
        self.atualizar_status("Processo interrompido por erro")
        messagebox.showerror("Erro no processo", msg)

    def _finalizar(self, resultado):
        self.botao_iniciar.configure(state="normal")
        self.botao_planilha.configure(state="normal")
        self.botao_parar.configure(state="disabled")
        if self._parar:
            self._add_activity("Processo parado. Ponto de retomada salvo.", self.WARNING)
            self._finalizar_historico_execucao(resultado, "Parada pelo usuário")
            self.atualizar_status("Parado pelo usuário")
        else:
            self._add_activity("Processo finalizado.", self.SUCCESS)
            self._finalizar_historico_execucao(resultado, "Concluída")
            self.atualizar_status("Processo finalizado")
        for item in resultado.itens:
            if item.status == "Erro":
                self._add_erro_codigo(item.codigo)
        self._selecionar_aba("Erros" if resultado.erros else "Atividade")
        if resultado.erros == 0 and not self._parar:
            messagebox.showinfo(
                "Processo concluído",
                f"Processados: {resultado.processados}\nSucesso: {resultado.sucessos}\nErros: 0"
            )
        elif resultado.erros > 0:
            messagebox.showwarning(
                "Processo concluído com erros",
                f"Processados: {resultado.processados}\n"
                f"Sucesso: {resultado.sucessos}\n"
                f"Erros: {resultado.erros}\n\n"
                "Os códigos com erro estão na aba 'Erros'."
            )

    def parar(self):
        self._parar = True
        self.atualizar_status("Parando após o código atual...")
        self._add_activity("Solicitação de parada recebida.", self.WARNING)
        self._add_historico("Usuário solicitou parada segura.")

    def atualizar_status(self, texto):
        if self._closing:
            return
        self.app.after(0, lambda: self._aplicar_status(texto))

    def _iniciar_pisca_status(self, rapido=None):
        if rapido is not None:
            self._status_blink_fast = bool(rapido)

        if self._status_blink_job is not None:
            try:
                self.app.after_cancel(self._status_blink_job)
            except Exception:
                pass
            self._status_blink_job = None

        # Muitos frames + intervalo curto = pulso visual contínuo, em vez de
        # aparência de GIF. A geometria permanece idêntica.
        self._status_anim_frame = 0
        self._status_anim_frames = 28 if self._status_blink_fast else 36
        self._status_anim_interval = 28 if self._status_blink_fast else 32
        self._executar_pisca_status()

    @staticmethod
    def _interpolar_cor(c1, c2, fator):
        def rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        a = rgb(c1)
        b = rgb(c2)
        v = tuple(round(a[i] + (b[i] - a[i]) * fator) for i in range(3))
        return "#" + "".join(f"{x:02X}" for x in v)

    def _executar_pisca_status(self):
        try:
            import math

            frames = max(2, int(self._status_anim_frames))
            idx = self._status_anim_frame % frames

            # Seno suavizado: sobe e desce sem saltos perceptíveis.
            fase = (2.0 * math.pi * idx) / frames
            fator = (math.sin(fase - math.pi / 2.0) + 1.0) / 2.0
            # Curva suave para manter o ponto visível mesmo no vale.
            fator = fator * fator * (3.0 - 2.0 * fator)

            if self._status_blink_fast:
                # Azul/ciano mais discreto durante execução.
                halo_base, halo_brilho = "#3B7285", "#8FD4EC"
                dot_base, dot_brilho = "#2F6F87", "#65B8DB"
            else:
                halo_base, halo_brilho = "#4E8054", "#C9F0CC"
                dot_base, dot_brilho = "#2F7437", "#6ECB72"

            halo = self._interpolar_cor(halo_base, halo_brilho, fator)
            dot = self._interpolar_cor(dot_base, dot_brilho, fator)

            modo_escuro = ctk.get_appearance_mode().lower() == "dark"
            if self._status_blink_fast:
                canvas_bg = "#183B54" if modo_escuro else "#E5F1FB"
            else:
                canvas_bg = "#21482A" if modo_escuro else "#E7F5E7"
            self.status_indicator.configure(bg=canvas_bg)
            self.status_indicator.itemconfigure(
                self._status_halo,
                fill=halo
            )
            self.status_indicator.itemconfigure(
                self._status_dot,
                fill=dot
            )

            self._status_anim_frame = idx + 1
            self._status_blink_job = self.app.after(
                self._status_anim_interval,
                self._executar_pisca_status
            )
        except Exception:
            self._status_blink_job = None

    def _aplicar_status(self, texto):
        self.status_label.configure(text=texto.replace("Status:", "").strip())
        low = texto.lower()

        if "process" in low and "erro" not in low:
            self._status_text_base = "Processando"
            self._status_blink_fast = True
            cor_texto = self.INFO
            cor_pill = ("#E5F1FB", "#183B54")
        elif "parando" in low:
            self._status_text_base = "Parando"
            self._status_blink_fast = True
            cor_texto = self.WARNING
            cor_pill = ("#FFF4CE", "#4B3A1A")
        elif "erro" in low or "interromp" in low:
            self._status_text_base = "Atenção"
            self._status_blink_fast = True
            cor_texto = self.ERROR
            cor_pill = ("#FDE7E9", "#4B2529")
        else:
            self._status_text_base = "Pronto"
            self._status_blink_fast = False
            cor_texto = self.SUCCESS
            cor_pill = ("#E7F5E7", "#21482A")

        self.status_pill.configure(fg_color=cor_pill)
        self.status_text.configure(
            text=self._status_text_base,
            text_color=cor_texto,
            font=("Segoe UI", 13, "bold")
        )
        modo = ctk.get_appearance_mode().lower()
        canvas_bg = cor_pill[1] if modo == "dark" else cor_pill[0]
        self.status_indicator.configure(bg=canvas_bg)
        self._iniciar_pisca_status()

    def atualizar_progresso(self, processados, total, sucessos, erros, codigo):
        if self._closing:
            return
        self.app.after(0, lambda: self._aplicar_progresso(processados, total, sucessos, erros, codigo))

    def _aplicar_progresso(self, processados, total, sucessos, erros, codigo):
        self._checkpoint_indice_seguro = int(processados)
        pct = processados / total if total else 0
        self.progresso.set(pct)
        self.progresso_label.configure(text=f"{processados} / {total}")
        self.percentual_label.configure(text=f"{pct:.0%}")
        self._set_stat(self.sucesso_card, sucessos)
        self._set_stat(self.erro_card, erros)
        self._set_stat(self.codigo_card, codigo)
        self.status_label.configure(text=f"Processando código {processados} de {total}")
        self._status_text_base = "Processando"
        self.status_pill.configure(fg_color=("#E5F1FB", "#183B54"))
        self.status_text.configure(text="Processando", text_color=self.INFO)
        self._status_blink_fast = True
        # O estado já atualiza a animação; reiniciar o temporizador a cada código
        # tornaria o efeito irregular.
        if getattr(self, "_status_blink_job", None) is None:
            self._iniciar_pisca_status()
        if erros and erros > len(self._erros_codigos):
            # The actual error code is added at finalization; keep counter live.
            pass

    def mostrar_erro(self, mensagem):
        self.app.after(0, lambda: messagebox.showerror("Erro", mensagem))

    def deve_parar(self):
        return self._parar

    def _fechar_aplicativo(self):
        # Salva imediatamente o último ponto confirmado antes de destruir a
        # janela. O código que estava em execução não é contabilizado como
        # concluído e será repetido na retomada.
        self._closing = True

        if self._execucao_atual and self.caminho:
            try:
                pagina = int(self._execucao_atual.get("pagina", 1)) - 1
                indice = max(0, int(self._checkpoint_indice_seguro))
                salvar_checkpoint(self.caminho, pagina, indice)
                self._execucao_atual["status"] = "Interrompida — ponto salvo"
                self._execucao_atual["checkpoint"] = indice
                self._salvar_estado_persistente()
            except Exception:
                # Mesmo que o histórico visual falhe, não impedir o fechamento
                # nem mascarar o comportamento de saída do aplicativo.
                try:
                    pagina = max(0, int(self.pagina.get()) - 1)
                    salvar_checkpoint(
                        self.caminho,
                        pagina,
                        max(0, int(self._checkpoint_indice_seguro))
                    )
                except Exception:
                    pass

        # Fechar o navegador associado à execução antes de destruir a interface.
        auto = getattr(self, "_automacao_atual", None)
        if auto is not None:
            try:
                auto.fechar()
            except Exception:
                pass

        if self._status_blink_job is not None:
            try:
                self.app.after_cancel(self._status_blink_job)
            except Exception:
                pass
            self._status_blink_job = None

        self._fechar_menus()
        self.app.destroy()

    def run(self):
        self.app.mainloop()
