from pathlib import Path
from atualizacao import find_update, launch_updater
import json
import calendar as pycalendar
import tkinter as tk
import threading
import sys
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, Canvas, Frame, ttk, TclError, Entry
import customtkinter as ctk

from ui_platform import aplicar_backdrop_sistema, atualizar_backdrop_tema
from planilha_virtual_29926 import VirtualGridTree, SM_AUTOLAB_GRADE_VIRTUAL_29926

from storage_safe import atomic_write_json, read_json_with_backup

from planilha_core import (
    MAX_ROWS,
    apply_paste,
    clear_cells,
    extract_column,
    filled_row_count,
    non_empty_cells,
    parse_paste_text,
    rectangle_selection,
    redo_state,
    undo_state,
)

from app import (ler_checkpoint, salvar_checkpoint, principal, principal_interno, ler_checkpoint_interno, salvar_checkpoint_interno, excluir_checkpoint_interno)


def _ler_versao_aplicativo():
    """Lê a versão embutida no executável/projeto."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    caminho = base / "VERSION"
    try:
        valor = caminho.read_text(encoding="utf-8").strip()
        if valor:
            return valor.lstrip("vV")
    except OSError:
        pass
    return "desconhecida"


APP_VERSION = _ler_versao_aplicativo()
HISTORICO_DIAS = 60
ARQUIVOS_DIAS = 60
SM_AUTOLAB_GRADE_29922 = "SM-AUTOLAB-GRADE-PERFORMANCE-29922"


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
        self._planilha_arquivo = Path.home() / "SM AutoLab" / "planilha_interna.json"
        self._planilha_rascunho_arquivo = Path.home() / "SM AutoLab" / "planilha_rascunho.json"
        self._planilha_historico_arquivo = Path.home() / "SM AutoLab" / "planilha_historico.json"
        self._planilha_salva_data = {}
        self._planilha_efetuou_alteracao = False
        self._planilha_window = None
        self._planilha_tree = None
        self._planilha_data = {}
        self._planilha_undo = []
        self._planilha_redo = []
        self._planilha_edit_entry = None
        self._planilha_celula_ativa = None
        self._planilha_linhas_selecionadas = set()
        self._planilha_borda_widgets = []
        # Cache de leitura do histórico para evitar I/O e JSON.loads repetidos.
        self._planilha_historico_cache = None
        self._planilha_historico_cache_signature = None
        self._tema = "system"
        self._menu_config = None
        self._menu_aparencia = None
        self._menu_close_job = None
        self._planilha_historico_window = None
        self._arquivos_body = None
        self._arquivos_calendar_widget = None
        self._arquivos_calendar_canvas = None
        self._arquivos_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._arquivos_data_selecionada = None
        self._arquivos_calendar_widget = None
        self.arquivos_contador_label = None
        self._status_blink_job = None
        self._status_blink_visible = True
        self._status_blink_fast = False
        self._status_finalizado_job = None
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
        self.app.minsize(760, 590)
        self.app.resizable(True, True)
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

        title_row = ctk.CTkFrame(title, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text="SM AutoLab",
            text_color=self.TEXT,
            font=("Segoe UI", 23, "bold")
        ).pack(side="left")

        ctk.CTkLabel(
            title_row,
            text=f"v{APP_VERSION}",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(9, 0), pady=(7, 0))

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
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        )
        self.botao_configuracoes.pack(side="left", padx=(0, 10))
        self.botao_configuracoes.configure(command=self._alternar_menu_configuracoes)

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

        # Halo amplo e ponto central para um indicador mais limpo e legível.
        self._status_halo = self.status_indicator.create_oval(
            1, 1, 17, 17,
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
        self.status_text.place(x=57, y=7)

        # Mantém a área principal rolável e o rodapé fixo para proteger
        # Iniciar/Parar em janelas compactas.
        main = ctk.CTkScrollableFrame(
            self.app,
            fg_color=self.BG,
            corner_radius=0,
            scrollbar_button_color=("#C8C8C8", "#626262"),
            scrollbar_button_hover_color=("#AFAFAF", "#777777")
        )
        main.pack(fill="both", expand=True, padx=16, pady=8)

        top = ctk.CTkFrame(main, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))
        top.grid_columnconfigure(0, weight=4)
        top.grid_columnconfigure(1, weight=6)

        config = self._card(top)
        config.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._stage7_top_layout = top
        self._stage7_config_card = config
        self._section_title(config, "Planilhas")

        plan_buttons = ctk.CTkFrame(config, fg_color="transparent")
        plan_buttons.pack(fill="x", padx=14, pady=(14, 10))
        self.botao_planilha = ctk.CTkButton(
            plan_buttons, text="Abrir", command=self.abrir_planilha,
            width=118, height=32, corner_radius=8,
            fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER,
            font=("Segoe UI", 12, "bold")
        )
        self.botao_planilha.pack(side="left", padx=(0, 8))
        self.botao_historico_planilha = ctk.CTkButton(
            plan_buttons, text="Arquivos", command=self.abrir_historico_planilha,
            width=92, height=32, corner_radius=8,
            fg_color=self.CARD, hover_color=("#EAF4FC", "#263F50"),
            border_width=1, border_color=self.BORDER, text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        )
        self.botao_historico_planilha.pack(side="left")
        self.arquivos_contador_label = ctk.CTkLabel(
            plan_buttons,
            text="0 códigos no mês",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 9, "bold")
        )
        self.arquivos_contador_label.pack(side="left", padx=(8, 0))
        self.planilha_estado_label = ctk.CTkLabel(
            config,
            text="",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 10)
        )
        self.planilha_estado_label.pack(anchor="w", padx=14, pady=(0, 10))

        progress = self._card(top)
        progress.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        self._stage7_progress_card = progress
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
            progress, height=10, corner_radius=5,
            fg_color=self.BORDER, progress_color=self.ACCENT
        )
        self.progresso.set(0)
        self.progresso.pack(fill="x", padx=14, pady=(0, 2))
        self.progresso_label = ctk.CTkLabel(
            progress, text="0 / 0", text_color=self.SUBTEXT,
            font=("Segoe UI", 12)
        )
        self.progresso_label.pack(anchor="w", padx=14, pady=(0, 9))

        stats = ctk.CTkFrame(main, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 8))
        stats.grid_columnconfigure((0, 1, 2), weight=1)
        self.sucesso_card = self._stat_card(stats, "✓", "Executados", "0", self.SUCCESS)
        self.sucesso_card.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.erro_card = self._stat_card(stats, "!", "Não executados", "0", self.ERROR)
        self.erro_card.grid(row=0, column=1, sticky="ew", padx=5)
        self.codigo_card = self._stat_card(stats, "›", "Código atual", "—", self.INFO)
        self.codigo_card.grid(row=0, column=2, sticky="ew", padx=(5, 0))

        activity_card = self._card(main)
        activity_card.pack(fill="x", pady=(0, 6))
        # Área de acompanhamento mais alta para manter as pastas do histórico visíveis.
        activity_card.configure(height=285)
        activity_card.pack_propagate(False)
        self._section_title(activity_card, "Acompanhamento")

        # Fluent-inspired tab row, like the reference image.
        tabs = ctk.CTkFrame(activity_card, fg_color=("#F3F3F3", "#343A40"), corner_radius=8,
                           border_width=1, border_color=self.BORDER)
        tabs.pack(pady=(5, 5), padx=14)

        self.tab_buttons = {}
        for name in ("Atividade", "Não executados", "Histórico"):
            btn = ctk.CTkButton(
                tabs, text=name, command=lambda n=name: self._selecionar_aba(n),
                width={"Atividade": 92, "Não executados": 122, "Histórico": 92}[name],
                height=30, corner_radius=8,
                fg_color=("#E5F1FB", "#183B54") if name == "Atividade" else "transparent",
                hover_color=("#E8F2FC", "#204965"),
                text_color=self.TEXT, font=("Segoe UI", 11, "bold")
            )
            btn.pack(side="left", padx=2, pady=2)
            btn._fluent_no_press = True
            btn._fluent_no_focus_ring = True
            self.tab_buttons[name] = btn

        self.tab_area = ctk.CTkFrame(activity_card, fg_color="transparent")
        self.tab_area.pack(fill="both", expand=True, padx=14, pady=(0, 5))

        self.aba_atividade = ctk.CTkFrame(self.tab_area, fg_color="transparent")
        self.aba_erros = ctk.CTkFrame(self.tab_area, fg_color="transparent")
        self.aba_historico = ctk.CTkFrame(self.tab_area, fg_color="transparent")

        # Activity tab
        self.atividade = ctk.CTkTextbox(
            self.aba_atividade, height=90, corner_radius=8,
            fg_color=("#FAFAFA", "#252A2F"), border_width=1, border_color=self.BORDER,
            text_color=self.TEXT, font=("Consolas", 10), wrap="word"
        )
        self.atividade.pack(fill="both", expand=True)
        self.atividade.configure(state="disabled")

        # Errors tab: each code is directly copyable.
        erro_info = ctk.CTkFrame(self.aba_erros, fg_color="transparent")
        erro_info.pack(fill="x", pady=(0, 6))
        self.erros_titulo = ctk.CTkLabel(
            erro_info, text="Nenhum código não executado", text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        )
        self.erros_titulo.pack(side="left", padx=(1, 0))
        ctk.CTkLabel(
            erro_info, text="Clique no código para copiar", text_color=self.SUBTEXT,
            font=("Segoe UI", 10)
        ).pack(side="right")

        self.erros_frame = ctk.CTkScrollableFrame(
            self.aba_erros, height=80, fg_color=("#FAFAFA", "#252A2F"),
            corner_radius=8, border_width=1, border_color=self.BORDER
        )
        self.erros_frame.pack(fill="both", expand=True)
        self._limpar_erros_visuais(salvar=False)

        # Restore persisted errors after the UI is ready.
        self._renderizar_erros_persistentes()

        # History tab: executions shown as expandable folders.
        history_header = ctk.CTkFrame(self.aba_historico, fg_color="transparent")
        history_header.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(
            history_header, text="Histórico de execuções",
            text_color=self.TEXT, font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        self.botao_limpar_historico = ctk.CTkButton(
            history_header, text="Limpar histórico", command=self._limpar_historico,
            width=108, height=28, corner_radius=8,
            fg_color=self.CARD, hover_color=("#FDE7E9", "#4B2529"),
            border_width=1, border_color=self.BORDER, text_color=self.ERROR,
            font=("Segoe UI", 11, "bold")
        )
        self.botao_limpar_historico.pack(side="right")

        self.historico_lista = ctk.CTkScrollableFrame(
            self.aba_historico, fg_color=("#FAFAFA", "#252A2F"),
            corner_radius=8, border_width=1, border_color=self.BORDER
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

        # Tooltips passam a ser gerenciados globalmente pela camada visual da Etapa 7.
        try:
            aplicar_backdrop_sistema(self.app, "mica", dark=ctk.get_appearance_mode().lower() == "dark")
        except Exception:
            pass

        self._atualizar_contador_arquivos()
        self._add_activity("Sistema pronto para iniciar.", self.INFO)
        self._iniciar_pisca_status()
        self.app.after(350, self._verificar_retomada_pendente)
        self.app.after(1200, self._verificar_atualizacao_automatica)

    def _reposicionar_menus(self, _event=None):
        if self._closing:
            return
        try:
            if self._menu_config is not None and self._menu_config.winfo_exists():
                self.app.update_idletasks()
                app_x = self.app.winfo_rootx()
                app_y = self.app.winfo_rooty()
                bx = self.botao_configuracoes.winfo_rootx() - app_x
                by = self.botao_configuracoes.winfo_rooty() - app_y + self.botao_configuracoes.winfo_height() + 4
                menu_width = max(218, self._menu_config.winfo_reqwidth())
                app_width = max(1, self.app.winfo_width())
                # O menu nasce no mesmo eixo X do botão Configurações.
                menu_x = bx
                if menu_x + menu_width > app_width - 6:
                    menu_x = max(6, app_width - menu_width - 6)
                self._menu_config.place_configure(
                    x=int(menu_x),
                    y=int(max(0, by)),
                )
                self._menu_config.lift()

            if self._menu_aparencia is not None and self._menu_aparencia.winfo_exists():
                self.app.update_idletasks()
                app_x = self.app.winfo_rootx()
                app_y = self.app.winfo_rooty()
                if self._menu_config is not None and self._menu_config.winfo_exists():
                    x = self._menu_config.winfo_rootx() - app_x + self._menu_config.winfo_width() - 2
                    y = self._menu_config.winfo_rooty() - app_y
                else:
                    x = self.botao_configuracoes.winfo_rootx() - app_x + self.botao_configuracoes.winfo_width()
                    y = self.botao_configuracoes.winfo_rooty() - app_y
                self._menu_aparencia.place(x=max(0, x), y=max(0, y))
                self._menu_aparencia.lift()
        except Exception:
            pass

    def _fixar_menu_configuracoes(self):
        self._mostrar_menu_configuracoes()

    def _verificar_atualizacao_automatica(self):
        """Verifica silenciosamente se há uma Release mais nova.
        Só apresenta a tela de atualização quando existe versão superior
        com executável correspondente. Falhas de rede não interrompem o app.
        """
        if self._closing:
            return

        def worker():
            try:
                info = find_update()
            except Exception:
                return

            if not info:
                return
            if not info.get("version") or not info.get("download_url"):
                return

            try:
                self.app.after(
                    0,
                    lambda data=info: self._mostrar_resultado_atualizacao(data)
                )
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _verificar_atualizacoes_interativo(self):
        self._fechar_menus()

        def worker():
            try:
                info=find_update()
                self.app.after(0,lambda:self._mostrar_resultado_atualizacao(info))
            except Exception as exc:
                self.app.after(0,lambda:self._mostrar_resultado_atualizacao({
                    "error":str(exc)
                }))

        import threading
        threading.Thread(target=worker,daemon=True).start()

    def _mostrar_resultado_atualizacao(self, info):
        if info and info.get("error"):
            messagebox.showerror(
                "Atualizações",
                f"Não foi possível verificar atualizações.\n\n{info['error']}",
                parent=self.app
            )
            return

        if not info:
            try:
                versao_atual = info.get("current") if info else None
            except Exception:
                versao_atual = None
            if not versao_atual:
                try:
                    from updater import current_version
                    versao_atual = current_version()
                except Exception:
                    versao_atual = APP_VERSION
            messagebox.showinfo(
                "Atualizações",
                f"Você já está usando a versão mais recente do SM AutoLab.\n\n"
                f"Versão atual: v{versao_atual}",
                parent=self.app
            )
            return

        version=info.get("version","")
        if not info.get("download_url"):
            messagebox.showwarning(
                "Atualização disponível",
                f"A versão v{version} está disponível, mas ainda não há um "
                "executável publicado para download.",
                parent=self.app
            )
            return

        resposta=messagebox.askyesno(
            "Atualização disponível",
            f"Uma nova versão do SM AutoLab está disponível.\n\n"
            f"Versão instalada: v{info.get('current','')}\n"
            f"Nova versão: v{version}\n\n"
            "Deseja baixar e instalar agora?",
            parent=self.app
        )
        if not resposta:
            return

        ok,msg=launch_updater(info)
        if not ok:
            messagebox.showerror(
                "Atualização",
                f"Não foi possível iniciar o atualizador.\n\n{msg}",
                parent=self.app
            )
            return

        self._add_activity(
            f"Atualização para v{version} iniciada.",
            self.INFO
        )
        self._fechar_aplicativo()

    def _alternar_menu_configuracoes(self):
        if self._menu_config is not None:
            try:
                if self._menu_config.winfo_exists():
                    self._fechar_menus()
                    return
            except Exception:
                pass
        self._mostrar_menu_configuracoes()

    def _iterar_descendentes_ui(self, widget):
        yield widget
        try:
            children = widget.winfo_children()
        except Exception:
            children = ()
        for child in children:
            yield from self._iterar_descendentes_ui(child)

    def _mostrar_menu_configuracoes(self, _event=None):
        self._cancelar_fechar_menus()

        if self._menu_config is not None:
            try:
                if self._menu_config.winfo_exists():
                    return
            except Exception:
                pass

        menu = ctk.CTkFrame(
            self.app,
            fg_color=self.CARD,
            corner_radius=10,
            border_width=1,
            border_color=self.BORDER,
            width=218,
            height=150
        )
        menu.place(x=0, y=0)
        menu.pack_propagate(False)
        self._menu_config = menu

        try:
            menu.bind("<Enter>", lambda _event=None: self._cancelar_fechar_menus(), add="+")
            menu.bind("<Leave>", lambda _event=None: self._agendar_fechar_menus(), add="+")
        except Exception:
            pass

        aparencia = ctk.CTkButton(
            menu,
            text="Aparência  ›",
            command=self._mostrar_menu_aparencia,
            width=202,
            height=40,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            text_color=self.TEXT,
            font=("Segoe UI", 12),
            anchor="w"
        )
        aparencia.pack(fill="x", padx=7, pady=(8, 3))
        self._menu_aparencia_btn = aparencia

        # Usa a posição real do cursor na janela para que o hover funcione
        # independentemente de o ponteiro estar sobre o frame, texto ou
        # qualquer widget interno do CTkButton.
        def _hover_global_config(event=None):
            try:
                if self._menu_config is None or not self._menu_config.winfo_exists():
                    return
                self._menu_config.update_idletasks()
                self._garantir_menu_aparencia_aberto_se_hover(event)
            except Exception:
                pass

        try:
            self._config_hover_binding = self.app.bind(
                "<Motion>",
                _hover_global_config,
                add="+",
            )
        except Exception:
            self._config_hover_binding = None

        # Compatibilidade com o binding direto do botão, além da detecção
        # global acima.
        # Aparência funciona como submenu em cascata: passar o mouse pela
        # opção já abre o submenu; o clique continua funcionando como alternativa.
        def _abrir_aparencia_por_hover(_event=None):
            self._garantir_menu_aparencia_aberto()
            return "break"

        def _abrir_aparencia_por_clique(event=None):
            self._garantir_menu_aparencia_aberto()
            return "break"

        for _widget in self._iterar_descendentes_ui(aparencia):
            try:
                _widget.bind("<Enter>", _abrir_aparencia_por_hover, add="+")
                _widget.bind("<Button-1>", _abrir_aparencia_por_clique, add="+")
            except Exception:
                pass
        try:
            aparencia.bind("<Enter>", _abrir_aparencia_por_hover, add="+")
            aparencia.bind("<Button-1>", _abrir_aparencia_por_clique, add="+")
        except Exception:
            pass

        mudar = ctk.CTkButton(
            menu,
            text="Mudar o Feegow",
            command=self._abrir_popup_feegow,
            width=202,
            height=40,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            text_color=self.TEXT,
            font=("Segoe UI", 12),
            anchor="w"
        )
        mudar.pack(fill="x", padx=7, pady=(3, 3))

        atualizar = ctk.CTkButton(
            menu,
            text="Verificar atualizações",
            command=self._verificar_atualizacoes_interativo,
            width=202,
            height=40,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            text_color=self.TEXT,
            font=("Segoe UI", 12),
            anchor="w"
        )
        atualizar.pack(fill="x", padx=7, pady=(3, 8))

        # Explicit close/toggle: clicking Configurações again closes the menu.
        self.app.update_idletasks()
        self._reposicionar_menus()

    def _garantir_menu_aparencia_aberto_se_hover(self, event=None):
        menu = getattr(self, "_menu_config", None)
        aparencia = getattr(self, "_menu_aparencia_btn", None)
        if menu is None or aparencia is None:
            return
        try:
            if not menu.winfo_exists() or not aparencia.winfo_exists():
                return
            x = self.app.winfo_pointerx() - menu.winfo_rootx()
            y = self.app.winfo_pointery() - menu.winfo_rooty()
            ay = aparencia.winfo_y()
            ah = aparencia.winfo_height()
            ax = aparencia.winfo_x()
            aw = aparencia.winfo_width()
            if ax <= x < ax + aw and ay <= y < ay + ah:
                self._garantir_menu_aparencia_aberto()
        except Exception:
            pass

    def _garantir_menu_aparencia_aberto(self):
        self._cancelar_fechar_menus()
        menu = getattr(self, "_menu_aparencia", None)
        try:
            if menu is not None and menu.winfo_exists():
                return
        except Exception:
            pass
        self._mostrar_menu_aparencia()

    def _mostrar_menu_aparencia(self, _event=None):
        self._cancelar_fechar_menus()

        if self._menu_config is None or not self._menu_config.winfo_exists():
            self._mostrar_menu_configuracoes()
            return

        if self._menu_aparencia is not None:
            try:
                if self._menu_aparencia.winfo_exists():
                    # Clique explícito na própria opção alterna o submenu.
                    self._menu_aparencia.destroy()
                    self._menu_aparencia = None
                    return
            except Exception:
                self._menu_aparencia = None

        sub = ctk.CTkFrame(
            self.app,
            fg_color=self.CARD,
            corner_radius=10,
            border_width=1,
            border_color=self.BORDER,
            width=225,
            height=158
        )
        sub.place(x=0, y=0)
        sub.pack_propagate(False)
        self._menu_aparencia = sub

        titulo = ctk.CTkLabel(
            sub,
            text="Aparência",
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold"),
            anchor="w"
        )
        titulo.pack(fill="x", padx=12, pady=(9, 4))

        for modo in ("light", "dark", "system"):
            rotulo = self.THEME_LABELS[modo]
            marcado = "✓  " if modo == self._tema else "    "
            btn = ctk.CTkButton(
                sub,
                text=marcado + rotulo,
                command=lambda m=modo: self._selecionar_tema(m),
                width=210,
                height=34,
                corner_radius=8,
                fg_color=("#E5F1FB", "#183B54") if modo == self._tema else self.CARD,
                hover_color=("#EAF4FC", "#263F50"),
                text_color=self.ACCENT if modo == self._tema else self.TEXT,
                font=("Segoe UI", 11, "bold") if modo == self._tema else ("Segoe UI", 11),
                anchor="w"
            )
            btn.pack(fill="x", padx=6, pady=2)

        self.app.update_idletasks()
        self._reposicionar_menus()

        # Ao entrar no submenu, cancelamos o fechamento pendente para que ele
        # permaneça aberto enquanto o usuário escolhe o modo.
        for _widget in self._iterar_descendentes_ui(sub):
            try:
                _widget.bind("<Enter>", lambda _event=None: self._cancelar_fechar_menus(), add="+")
                _widget.bind("<Leave>", lambda _event=None: self._agendar_fechar_menus(), add="+")
            except Exception:
                pass

    def _entrar_mudar_feegow(self, _event=None):
        if self._menu_aparencia is not None:
            try:
                self._menu_aparencia.destroy()
            except Exception:
                pass
            self._menu_aparencia = None

    def _agendar_fechar_aparencia(self, _event=None):
        # Kept for compatibility with older bindings.
        self._cancelar_fechar_menus()

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
        # Fecha o submenu somente depois de uma pequena tolerância, permitindo
        # mover o ponteiro de Aparência até as opções sem fechar o menu.
        self._cancelar_fechar_menus()
        try:
            self._menu_close_job = self.app.after(
                220,
                self._fechar_menus,
            )
        except Exception:
            self._menu_close_job = None

    def _fechar_menus(self):
        self._menu_close_job = None
        hover_binding = getattr(self, "_config_hover_binding", None)
        if hover_binding:
            try:
                self.app.unbind("<Motion>", hover_binding)
            except Exception:
                pass
        self._config_hover_binding = None
        self._menu_aparencia_btn = None
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
        try:
            dark = ctk.get_appearance_mode().lower() == "dark"
            atualizar_backdrop_tema(self.app, dark)
            for attr in ("_planilha_window", "_planilha_historico_window"):
                win = getattr(self, attr, None)
                if win is not None:
                    atualizar_backdrop_tema(win, dark)
        except Exception:
            pass
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
        popup.geometry("560x420")
        popup.resizable(False, False)
        popup.transient(self.app)
        popup.grab_set()
        popup.configure(fg_color=self.BG)
        try:
            aplicar_backdrop_sistema(
                popup, "acrylic",
                dark=ctk.get_appearance_mode().lower() == "dark"
            )
        except Exception:
            pass

        popup_header = ctk.CTkFrame(
            popup,
            fg_color=self.CARD,
            corner_radius=0,
            height=86,
        )
        popup_header.pack(fill="x")
        popup_header.pack_propagate(False)

        ctk.CTkLabel(
            popup_header, text="Mudar o Feegow",
            text_color=self.TEXT, font=("Segoe UI", 19, "bold")
        ).pack(anchor="w", padx=22, pady=(19, 2))

        ctk.CTkLabel(
            popup_header,
            text="Altere o endereço e os dados de acesso utilizados pela automação.",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 11)
        ).pack(anchor="w", padx=22, pady=(0, 12))

        form = ctk.CTkFrame(
            popup,
            fg_color=self.CARD,
            corner_radius=10,
            border_width=1,
            border_color=self.BORDER,
        )
        form.pack(fill="x", padx=22, pady=(12, 0))

        ctk.CTkLabel(
            form, text="Endereço do Feegow",
            text_color=self.TEXT, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 4))
        site_entry = ctk.CTkEntry(
            form, height=36, corner_radius=8,
            fg_color=self.CARD, border_color=self.BORDER,
            text_color=self.TEXT, font=("Segoe UI", 11)
        )
        site_entry.pack(fill="x", padx=14, pady=(0, 12))
        site_entry.insert(0, dados.get("SITE_URL", ""))

        ctk.CTkLabel(
            form, text="Usuário",
            text_color=self.TEXT, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=14, pady=(0, 4))
        user_entry = ctk.CTkEntry(
            form, height=36, corner_radius=8,
            fg_color=self.CARD, border_color=self.BORDER,
            text_color=self.TEXT, font=("Segoe UI", 11)
        )
        user_entry.pack(fill="x", padx=14, pady=(0, 12))
        user_entry.insert(0, dados.get("PORTAL_USUARIO", ""))

        ctk.CTkLabel(
            form, text="Senha",
            text_color=self.TEXT, font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", padx=14, pady=(0, 4))
        pass_entry = ctk.CTkEntry(
            form, height=36, corner_radius=8,
            fg_color=self.CARD, border_color=self.BORDER,
            text_color=self.TEXT, font=("Segoe UI", 11),
        )
        pass_entry.pack(fill="x", padx=14, pady=(0, 14))
        pass_entry.insert(0, dados.get("PORTAL_SENHA", ""))

        actions = ctk.CTkFrame(popup, fg_color="transparent")
        actions.pack(fill="x", padx=22, pady=(12, 18))

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
                fg_color=self.ACCENT if alterado else self.BORDER,
                hover_color=self.ACCENT_HOVER if alterado else self.BORDER,
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
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        ctk.CTkFrame(actions, fg_color="transparent").pack(
            side="left", fill="x", expand=True
        )

        ctk.CTkButton(
            actions,
            text="Cancelar",
            command=popup.destroy,
            width=110,
            height=40,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=(0, 8))

        salvar_btn = ctk.CTkButton(
            actions,
            text="Salvar",
            command=salvar,
            width=110,
            height=40,
            corner_radius=8,
            fg_color=("#E5E5E5", "#454C52"),
            hover_color=("#E5E5E5", "#454C52"),
            text_color=("#8A8A8A", "#AEB4B9"),
            state="disabled",
            font=("Segoe UI", 12, "bold")
        )
        salvar_btn.pack(side="left")
        atualizar_estado_salvar()


    def _selecionar_aba(self, nome):
        for frame in (self.aba_atividade, self.aba_erros, self.aba_historico):
            frame.pack_forget()
        mapa = {
            "Atividade": self.aba_atividade,
            "Não executados": self.aba_erros,
            "Histórico": self.aba_historico,
        }
        mapa[nome].pack(fill="both", expand=True)
        for n, btn in self.tab_buttons.items():
            ativo = n == nome
            btn.configure(
                fg_color=("#E5F1FB", "#183B54") if ativo else "transparent",
                hover_color=("#E8F2FC", "#204965"),
                border_width=1 if ativo else 0,
                border_color=self.ACCENT if ativo else self.BORDER,
                text_color=self.ACCENT if ativo else self.TEXT,
                font=("Segoe UI", 11, "bold"),
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
            fg_color=("#F3F8FC", "#243D4B"),
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

    def _filtrar_historico_execucoes_60_dias(self, execucoes):
        agora = datetime.now()
        limite = agora - timedelta(days=HISTORICO_DIAS)
        validas = []
        for execucao in execucoes or []:
            if not isinstance(execucao, dict):
                continue
            try:
                inicio = datetime.fromisoformat(str(execucao.get("inicio", "")))
            except Exception:
                continue
            if limite <= inicio <= agora:
                validas.append(execucao)
        return validas

    def _carregar_estado_persistente(self):
        try:
            if not self._historico_arquivo.exists():
                return
            dados = read_json_with_backup(self._historico_arquivo, {})
            execucoes = dados.get("historico_execucoes", [])
            erros = dados.get("erros", [])
            tema = dados.get("tema", "system")
            if tema in ("light", "dark", "system"):
                self._tema = tema
            if isinstance(execucoes, list):
                self._historico_execucoes = self._filtrar_historico_execucoes_60_dias(execucoes)
            if isinstance(erros, list):
                self._erros_codigos = [str(x) for x in erros][-200:]
        except Exception:
            self._historico_execucoes = []
            self._erros_codigos = []

    def _salvar_estado_persistente(self):
        try:
            self._historico_execucoes = self._filtrar_historico_execucoes_60_dias(self._historico_execucoes)
            dados = {
                "historico_execucoes": self._historico_execucoes,
                "erros": self._erros_codigos[-200:],
                "tema": self._tema,
                "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            atomic_write_json(self._historico_arquivo, dados)
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
            text=f"{len(self._erros_codigos)} código(s) não executado(s)" if self._erros_codigos
            else "Nenhum código não executado"
        )

    def _criar_botao_erro(self, codigo, parent=None):
        codigo = str(codigo)
        parent = parent or self.erros_frame
        btn = ctk.CTkButton(
            parent, text=codigo, command=lambda c=codigo: self._copiar_codigo(c),
            height=30, corner_radius=8, fg_color=("#FDE7E9", "#4B2529"),
            hover_color=("#FAD2D5", "#603034"), text_color=self.ERROR,
            border_width=1, border_color=("#F1B8BC", "#7A4448"),
            font=("Segoe UI", 11, "bold"), anchor="w"
        )
        btn.pack(fill="x", padx=6, pady=3)
        return btn

    def _limpar_erros_visuais(self, salvar=True):
        for w in self.erros_frame.winfo_children():
            w.destroy()
        self._erros_codigos = []
        self.erros_titulo.configure(text="Nenhum código não executado")
        if salvar:
            self._salvar_estado_persistente()

    def _add_erro_codigo(self, codigo):
        codigo = str(codigo)
        if codigo in self._erros_codigos:
            return
        self._erros_codigos.append(codigo)
        self.erros_titulo.configure(text=f"{len(self._erros_codigos)} código(s) não executado(s)")
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

        if str(pendente.get("origem", "")) == "planilha_interna":
            try:
                codigos = self._extrair_codigos_planilha()
                interno = ler_checkpoint_interno(codigos) if codigos else None
                if interno is not None:
                    inicio = int(interno)
            except Exception:
                pass

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
                if str(pendente.get("origem", "")) == "planilha_interna":
                    self.iniciar_thread()
                elif caminho and Path(caminho).exists():
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
        self._execucao_atual["processados"] = int(getattr(resultado, "processados", 0) or 0)
        self._execucao_atual["codigos_erros"] = [str(item.codigo) for item in resultado.itens if item.status == "Erro"]
        self._historico_execucoes.append(dict(self._execucao_atual))
        self._historico_execucoes = self._filtrar_historico_execucoes_60_dias(self._historico_execucoes)
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()
        self._atualizar_contador_arquivos()

    def _registrar_falha_historico(self, mensagem):
        if not self._execucao_atual:
            return
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._execucao_atual["fim"] = agora
        self._execucao_atual["status"] = "Erro geral"
        self._execucao_atual["mensagem"] = str(mensagem)
        self._historico_execucoes.append(dict(self._execucao_atual))
        self._historico_execucoes = self._filtrar_historico_execucoes_60_dias(self._historico_execucoes)
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()
        self._atualizar_contador_arquivos()

    def _restaurar_historico_na_tela(self):
        if not hasattr(self, "historico_lista"):
            return
        for w in self.historico_lista.winfo_children():
            w.destroy()
        self._hist_grid=None

        if self._execucao_atual:
            self._criar_pasta_historico(self._execucao_atual, atual=True)

        historico_visivel = list(self._historico_execucoes)

        if not historico_visivel and not self._execucao_atual:
            ctk.CTkLabel(
                self.historico_lista, text="Nenhuma execução registrada ainda.",
                text_color=self.SUBTEXT, font=("Segoe UI", 10)
            ).pack(anchor="w", padx=8, pady=8)
            return

        for execucao in reversed(historico_visivel):
            self._criar_pasta_historico(execucao)

    def _criar_pasta_historico(self, execucao, atual=False):
        container = ctk.CTkFrame(self.historico_lista, fg_color=("#FFFFFF", "#2D3338"), corner_radius=8, border_width=1, border_color=self.BORDER, width=92, height=78)
        container.pack_propagate(False)
        # grid of compact folders, centered in the history panel
        # use a dedicated parent row grid when possible
        parent=self.historico_lista
        if not hasattr(self, "_hist_grid") or self._hist_grid is None:
            self._hist_grid=ctk.CTkFrame(parent,fg_color="transparent")
            self._hist_grid.pack(fill="x",padx=6,pady=4)
        # distribute in 6 compact columns
        count=len(self._hist_grid.winfo_children())
        row=count//6; col=count%6
        self._hist_grid.grid_columnconfigure(tuple(range(6)),weight=1)
        tile=ctk.CTkFrame(self._hist_grid,fg_color=("#FFFFFF", "#2D3338"),corner_radius=8,border_width=1,border_color=self.BORDER,width=92,height=78)
        tile.grid(row=row,column=col,padx=3,pady=3,sticky="nsew")
        tile.grid_propagate(False)
        inicio=execucao.get("inicio",""); status=execucao.get("status",""); erros=int(execucao.get("erros",0) or 0)
        icon=ctk.CTkLabel(tile,text="📁",font=("Segoe UI Emoji",18),text_color=self.ACCENT); icon.pack(pady=(5,0))
        ctk.CTkLabel(tile,text=inicio.split(" ")[0] if inicio else "",text_color=self.TEXT,font=("Segoe UI",8,"bold")).pack()
        ctk.CTkLabel(tile,text=inicio.split(" ")[1] if " " in inicio else "",text_color=self.SUBTEXT,font=("Segoe UI",7)).pack()
        ctk.CTkLabel(tile,text=f"{status} • {erros} não exec.",text_color=self.SUBTEXT,font=("Segoe UI",7),wraplength=82).pack(pady=(3,0))
        detalhe=ctk.CTkToplevel(self.app) if False else None
        def selecionar(_e=None):
            for sibling in self._hist_grid.winfo_children():
                sibling.configure(border_color=self.BORDER, fg_color=("#FFFFFF", "#2D3338"))
            tile.configure(border_color=self.ACCENT, fg_color=("#EAF4FF", "#1B3C53"))
        def abrir(_e=None):
            selecionar(); self._abrir_detalhe_historico(execucao)
        def enter(_e=None):
            tile.configure(border_color=self.ACCENT_HOVER, fg_color=("#EAF4FC", "#263F50"))
        def leave(_e=None):
            # keep selection highlight if selected; otherwise restore neutral
            if tile.cget("border_color") not in (self.ACCENT,):
                tile.configure(border_color=self.BORDER, fg_color=("#FFFFFF", "#2D3338"))
        for w in (tile,icon):
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            w.bind("<Enter>", enter); w.bind("<Leave>", leave); w.bind("<Button-1>", selecionar); w.bind("<Double-1>", abrir)
        tile.bind("<Double-1>", abrir)

    def _abrir_detalhe_historico(self, execucao):
        win=ctk.CTkToplevel(self.app); win.title("Histórico — SM AutoLab"); win.geometry("650x470"); win.resizable(False,False); win.transient(self.app)
        try:
            aplicar_backdrop_sistema(win, "acrylic", dark=ctk.get_appearance_mode().lower() == "dark")
        except Exception:
            pass
        ctk.CTkLabel(win,text=execucao.get("inicio",""),text_color=self.TEXT,font=("Segoe UI",18,"bold")).pack(anchor="w",padx=18,pady=(16,2))
        self._preencher_detalhe_pasta(win,execucao)

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
                   f"Status: {status}    Processados: {total}    Executados: {sucessos}    Não executados: {erros}"),
            text_color=self.SUBTEXT, font=("Segoe UI", 9), anchor="w", justify="left"
        ).pack(fill="x", padx=8, pady=(7, 4))

        if erros and codigos:
            ctk.CTkLabel(
                parent, text="Códigos não executados (clique para copiar):",
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
            "Essa ação não apaga a aba 'Não executados' da execução atual."
        )
        if not confirmar:
            return
        self._historico_execucoes = []
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()
        self._atualizar_contador_arquivos()
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

    def _garantir_pasta_planilha(self):
        self._planilha_arquivo.parent.mkdir(parents=True, exist_ok=True)

    def _carregar_planilha_interna(self):
        self._garantir_pasta_planilha()
        if not self._planilha_arquivo.exists():
            return {}
        try:
            data=read_json_with_backup(self._planilha_arquivo, {})
            cells=data.get("cells", {}) if isinstance(data, dict) else {}
            return {str(k): str(v) for k,v in cells.items() if str(v) != ""}
        except Exception:
            return {}

    def _salvar_planilha_interna_data(self, cells=None):
        self._garantir_pasta_planilha()
        if cells is None:
            cells=self._planilha_data
        payload={"version":1,"updated_at":datetime.now().isoformat(timespec="seconds"),"cells":cells}
        atomic_write_json(self._planilha_arquivo, payload)

    def _planilha_tem_alteracoes(self):
        return self._planilha_data != self._planilha_salva_data

    def _planilha_salvar_rascunho(self):
        try:
            self._garantir_pasta_planilha()
            payload={"version":1,"updated_at":datetime.now().isoformat(timespec="seconds"),"cells":dict(self._planilha_data)}
            atomic_write_json(self._planilha_rascunho_arquivo, payload)
        except Exception:
            pass

    def _planilha_apagar_rascunho(self):
        try:
            if self._planilha_rascunho_arquivo.exists(): self._planilha_rascunho_arquivo.unlink()
        except Exception: pass

    def _planilha_carregar_rascunho(self):
        if not self._planilha_rascunho_arquivo.exists(): return None
        try:
            data=read_json_with_backup(self._planilha_rascunho_arquivo, None)
            cells=data.get("cells",{}) if isinstance(data,dict) else {}
            return {str(k):str(v) for k,v in cells.items() if str(v)!=""} if isinstance(cells,dict) else None
        except Exception: return None

    def _planilha_recuperar_rascunho_se_houver(self):
        draft=self._planilha_carregar_rascunho()
        if draft is None: return
        if draft == self._planilha_salva_data:
            self._planilha_apagar_rascunho(); return
        restaurar=messagebox.askyesno("Recuperar alterações","Foram encontradas alterações feitas na planilha que ainda não haviam sido salvas.\n\nDeseja restaurar essas últimas alterações?",parent=self._planilha_window)
        if restaurar:
            self._planilha_data=dict(draft); self._planilha_efetuou_alteracao=True
        else:
            self._planilha_apagar_rascunho(); self._planilha_data=dict(self._planilha_salva_data)

    def _planilha_marcar_alteracao(self):
        self._planilha_efetuou_alteracao=True
        self._planilha_salvar_rascunho()
        self._planilha_atualizar_contador()
        try:
            if self._planilha_window is not None:
                self._planilha_window.title("* Planilha — SM AutoLab" if self._planilha_tem_alteracoes() else "Planilha — SM AutoLab")
        except Exception: pass

    def abrir_planilha(self, dados_iniciais=None):
        if self._planilha_window is not None:
            try:
                if self._planilha_window.winfo_exists():
                    self._planilha_window.lift(); return
            except Exception:
                pass

        if dados_iniciais is None:
            self._preparar_planilha_do_dia()
            self._planilha_data=self._carregar_planilha_interna()
        else:
            self._planilha_data={str(k):str(v) for k,v in dados_iniciais.items() if str(v)!=""}
        self._planilha_salva_data=dict(self._planilha_data)
        self._planilha_undo=[]
        self._planilha_redo=[]
        self._planilha_efetuou_alteracao=False
        self._planilha_contador_label=None
        win=ctk.CTkToplevel(self.app)
        self._planilha_window=win
        win.title("Planilha — SM AutoLab")
        win.geometry("1080x720")
        win.minsize(900, 600)
        win.configure(fg_color=self.BG)
        win.transient(self.app)
        try:
            aplicar_backdrop_sistema(
                win, "mica_alt",
                dark=ctk.get_appearance_mode().lower() == "dark"
            )
        except Exception:
            pass
        win.protocol("WM_DELETE_WINDOW", self._planilha_fechar_pela_janela)
        # Restaurar rascunho após a janela existir para que o diálogo tenha parent válido.
        try:
            win.iconbitmap(str(Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"SM AutoLab.ico"))
        except Exception:
            pass

        self._planilha_recuperar_rascunho_se_houver()

        toolbar=ctk.CTkFrame(win, fg_color=self.CARD, corner_radius=0, height=64)
        toolbar.pack(fill="x"); toolbar.pack_propagate(False)
        title_bar=ctk.CTkFrame(toolbar, fg_color="transparent")
        title_bar.pack(side="left", padx=18, pady=8)
        ctk.CTkLabel(title_bar,text="Planilha",text_color=self.TEXT,font=("Segoe UI",20,"bold")).pack(side="left")
        undo_row=ctk.CTkFrame(title_bar, fg_color="transparent")
        undo_row.pack(side="left", padx=(16,0))
        for glyph, cmd, label in (("↶", self._planilha_desfazer, "Desfazer"), ("↷", self._planilha_refazer, "Refazer")):
            b=ctk.CTkButton(undo_row,text=glyph,command=cmd,width=34,height=34,corner_radius=8,fg_color="transparent",hover_color=("#EAF4FC","#263F50"),text_color=self.TEXT,font=("Segoe UI Symbol",20,"bold"))
            b.pack(side="left", padx=1)
            b.configure(cursor="hand2")
        self._planilha_contador_label=ctk.CTkLabel(title_bar,text="0 preenchidas",text_color=self.SUBTEXT,font=("Segoe UI",10))
        self._planilha_contador_label.pack(side="left", padx=(10,0))
        actions=ctk.CTkFrame(toolbar,fg_color="transparent"); actions.pack(side="right",padx=16,pady=9)
        ctk.CTkButton(actions,text="Limpar",command=self._planilha_limpar,width=80,height=36,corner_radius=8,fg_color=self.CARD,hover_color=("#FDECEC","#3A2424"),border_width=1,border_color=self.ERROR,text_color=self.ERROR,font=("Segoe UI",12,"bold")).pack(side="left",padx=4)
        ctk.CTkButton(actions,text="Salvar e Sair",command=self._planilha_salvar_e_sair,width=115,height=36,corner_radius=8,fg_color=self.CARD,hover_color=("#EAF4FC","#263F50"),border_width=1,border_color=self.BORDER,text_color=self.TEXT,font=("Segoe UI",12,"bold")).pack(side="left",padx=4)
        ctk.CTkButton(actions,text="Salvar e Iniciar",command=self._planilha_salvar_e_iniciar,width=150,height=46,corner_radius=8,fg_color=self.ACCENT,hover_color=self.ACCENT_HOVER,font=("Segoe UI",14,"bold")).pack(side="left",padx=4)

        body=ctk.CTkFrame(win,fg_color=self.BG,corner_radius=0)
        body.pack(fill="both",expand=True,padx=12,pady=12)
        style=ttk.Style(win)
        try: style.theme_use("vista")
        except TclError: pass
        modo_escuro = ctk.get_appearance_mode().lower() == "dark"
        tree_bg = "#2D3338" if modo_escuro else "#FFFFFF"
        tree_header = "#343A40" if modo_escuro else "#F5F5F5"
        tree_fg = "#F2F4F5" if modo_escuro else "#242424"
        tree_border = "#465058" if modo_escuro else "#E0E0E0"
        tree_selected = "#1B3C53" if modo_escuro else "#EAF4FF"
        row_header_bg = "#252A2F" if modo_escuro else "#F7F7F7"
        row_header_text = "#AEB4B9" if modo_escuro else "#6B6B6B"
        row_header_line = "#384148" if modo_escuro else "#EEEEEE"
        style.configure("SM.Treeview", font=("Segoe UI",9), rowheight=28, background=tree_bg, fieldbackground=tree_bg, borderwidth=1, relief="solid", foreground=tree_fg)
        style.map(
            "SM.Treeview",
            background=[("selected", tree_selected), ("focus", tree_bg), ("!focus", tree_bg)],
            foreground=[("selected", tree_fg), ("focus", tree_fg), ("!focus", tree_fg)]
        )
        style.configure("SM.Treeview.Heading", font=("Segoe UI",11,"bold"), relief="solid", borderwidth=1, background=tree_header, foreground=tree_fg)

        # A numeração das linhas é um cabeçalho lateral separado da grade.
        # Ela não pertence às células da planilha, não pode ser editada e
        # permanece fixa durante a rolagem horizontal, como no Excel/Google Sheets.
        row_header_frame = ctk.CTkFrame(body, fg_color=tree_bg, corner_radius=0)
        row_header_frame.grid_rowconfigure(1, weight=1)
        row_header_frame.grid_columnconfigure(0, weight=1)
        row_header_top = Canvas(
            row_header_frame, width=42, height=28, bg=tree_header,
            highlightthickness=1, highlightbackground=tree_border, bd=0
        )
        row_header_top.create_line(0, 27, 42, 27, fill=tree_border)
        row_header_top.grid(row=0, column=0, sticky="ew")
        row_header = Canvas(
            row_header_frame, width=42, bg=row_header_bg, highlightthickness=1,
            highlightbackground=tree_border, bd=0
        )
        row_header.grid(row=1, column=0, sticky="nsew")

        tree=VirtualGridTree(
            body,
            columns=(
                ("c1", "Qtd", 70, 50, "w", False),
                ("c2", "Senha", 160, 110, "w", False),
                ("c3", "Item", 770, 300, "w", True),
            ),
            total_rows=10000,
            row_height=28,
            header_height=28,
            value_provider=lambda row: (
                self._planilha_data.get(f"{row},0", "") or "",
                self._planilha_data.get(f"{row},1", "") or "",
                self._planilha_data.get(f"{row},2", "") or "",
            ),
            bg=tree_bg,
            header_bg=tree_header,
            fg=tree_fg,
            header_fg=tree_fg,
            border=tree_border,
            even_bg="#FFFFFF" if not modo_escuro else "#2D3338",
            odd_bg="#FBFBFB" if not modo_escuro else "#292F34",
        )

        def _ajustar_larguras_planilha(_event=None):
            try:
                total=max(tree.winfo_width(), 300)
                qtd=max(50, int(total*0.07))
                senha=max(110, int(total*0.16))
                item=max(300, total-qtd-senha-4)
                tree.column("c1", width=qtd)
                tree.column("c2", width=senha)
                tree.column("c3", width=item)
            except Exception:
                pass
        tree.bind("<Configure>", _ajustar_larguras_planilha, add="+")

        # A grade virtual usa uma janela fixa de objetos Canvas para representar
        # apenas a viewport lógica; os 10.000 registros continuam em _planilha_data.
        def _sync_row_header(first, last):
            y.set(first, last)
            try:
                self._planilha_desenhar_cabecalho_linhas(float(first))
            except Exception:
                pass
            try:
                tree.after_idle(self._planilha_desenhar_borda)
            except Exception:
                pass

        y=ttk.Scrollbar(body,orient="vertical",command=tree.yview)
        x=ttk.Scrollbar(body,orient="horizontal",command=tree.xview)
        tree.configure(yscrollcommand=_sync_row_header,xscrollcommand=x.set)

        row_header_frame.grid(row=0,column=0,sticky="ns")
        tree.grid(row=0,column=1,sticky="nsew")
        y.grid(row=0,column=2,sticky="ns")
        x.grid(row=1,column=1,sticky="ew")
        body.grid_rowconfigure(0,weight=1)
        body.grid_columnconfigure(1,weight=1)

        def _rolar_cabecalho(event):
            delta = -1 if event.delta > 0 else 1
            tree.yview_scroll(delta, "units")
            return "break"
        row_header.bind("<MouseWheel>", _rolar_cabecalho)

        def _clicar_cabecalho(event):
            try:
                first = float(tree.yview()[0])
                total = 10000
                row_index = int(first * total + (event.y / row_height))
                row_index = max(0, min(row_index, total - 1))
                iid = str(row_index)
                tree.focus(iid)
                tree.see(iid)
                self._planilha_linhas_selecionadas = {iid}
                self._planilha_celula_ativa = (iid, 0)
                self._planilha_desenhar_borda()
            except Exception:
                pass
            return "break"
        row_header.bind("<Button-1>", _clicar_cabecalho)

        tree.focus("")
        tree.tag_configure("even", background="#FFFFFF")
        tree.tag_configure("odd", background="#FBFBFB")

        # Etapa 13: virtualização real; não há inserção gradual de 10.000 itens.
        self._planilha_povoamento_job = None
        self._planilha_povoamento_concluido = True
        self._planilha_povoamento_proxima_linha = 10000
        self._planilha_celulas_selecionadas = set()
        self._planilha_drag_anchor = None
        self._planilha_drag_start_xy = None
        self._planilha_dragging = False
        tree.bind("<ButtonPress-1>", self._planilha_clicar_celula, add="+")
        tree.bind("<B1-Motion>", self._planilha_arrastar_selecao, add="+")
        tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao, add="+")
        tree.bind("<Double-Button-1>", self._planilha_duplo_clique_celula, add="+")
        tree.bind("<Return>", self._planilha_editar_selecao)
        tree.bind("<Control-KeyPress-z>", self._planilha_atalho_desfazer, add="+")
        tree.bind("<Control-KeyPress-y>", self._planilha_atalho_refazer, add="+")
        tree.bind("<Control-KeyPress-a>", self._planilha_atalho_selecionar_tudo, add="+")
        tree.bind("<Control-KeyPress-c>", self._planilha_atalho_copiar, add="+")
        tree.bind("<Control-KeyPress-x>", self._planilha_recortar, add="+")
        tree.bind("<Delete>", self._planilha_atalho_excluir, add="+")
        tree.bind("<BackSpace>", self._planilha_atalho_excluir, add="+")
        tree.bind("<Control-KeyPress-v>", self._planilha_atalho_colar, add="+")
        tree.bind("<Control-KeyPress-V>", self._planilha_atalho_colar, add="+")
        tree.bind("<<Paste>>", self._planilha_atalho_colar, add="+")
        def _planilha_botao_direito(event):
            row=tree.identify_row(event.y); col=tree.identify_column(event.x)
            if row and col in ("#1","#2","#3"):
                self._planilha_celula_ativa=(row,int(col[1:])-1)
                self._planilha_linhas_selecionadas={row}
                tree.focus_set()
                self._planilha_desenhar_borda()
            return "break"
        tree.bind("<Button-3>", _planilha_botao_direito)
        tree.bind("<Shift-Insert>", self._planilha_atalho_colar, add="+")
        self._planilha_tree=tree
        self._planilha_row_header=row_header
        self._planilha_implementacao = "grade-virtual-29926"
        tree.refresh()
        # Fallback global: alguns ambientes Windows/Tk não entregam Ctrl+V ao
        # Treeview, mesmo com o binding local. Interceptamos somente enquanto
        # o foco estiver dentro da planilha, evitando afetar o restante do app.
        if not getattr(self, "_planilha_paste_global_instalado", False):
            self._planilha_paste_global_instalado = True

            def _planilha_paste_global(event):
                if self._planilha_foco_pertence_a_grade():
                    return self._planilha_colar_teclado(event)
                return None

            self._planilha_paste_global_callback = _planilha_paste_global
            self.app.bind_all(
                "<Control-KeyPress-v>",
                _planilha_paste_global,
                add="+",
            )
            self.app.bind_all(
                "<Control-KeyPress-V>",
                _planilha_paste_global,
                add="+",
            )

        # Fallbacks de teclado para ambientes Tk/Windows que não propagam
        # algum atalho do Treeview. O foco é sempre validado antes.
        if not getattr(self, "_planilha_shortcuts_global_instalado", False):
            self._planilha_shortcuts_global_instalado = True

            def _shortcut_global(handler):
                def callback(event):
                    if not self._planilha_foco_pertence_a_grade():
                        return None
                    if self._planilha_tem_entry_em_foco():
                        return None
                    return handler(event)
                return callback

            self.app.bind_all("<Control-KeyPress-z>", _shortcut_global(self._planilha_atalho_desfazer), add="+")
            self.app.bind_all("<Control-KeyPress-y>", _shortcut_global(self._planilha_atalho_refazer), add="+")
            self.app.bind_all("<Control-KeyPress-a>", _shortcut_global(self._planilha_atalho_selecionar_tudo), add="+")
            self.app.bind_all("<Control-KeyPress-c>", _shortcut_global(self._planilha_atalho_copiar), add="+")
            self.app.bind_all("<Control-KeyPress-x>", _shortcut_global(self._planilha_recortar), add="+")
            self.app.bind_all("<Delete>", _shortcut_global(self._planilha_atalho_excluir), add="+")
            self.app.bind_all("<BackSpace>", _shortcut_global(self._planilha_atalho_excluir), add="+")
        # Primeira repintura após a viewport estar realmente montada.
        try:
            tree.update_idletasks()
            self._planilha_desenhar_borda()
            self._planilha_desenhar_cabecalho_linhas()
            tree.after(25, self._planilha_desenhar_borda)
            tree.after(25, self._planilha_desenhar_cabecalho_linhas)
        except Exception:
            pass

        row_header.bind(
            "<Configure>",
            lambda _e: self._planilha_desenhar_cabecalho_linhas(),
            add="+",
        )
        self._planilha_desenhar_cabecalho_linhas()

    def _planilha_stage9_get_grid_state(self):
        state = getattr(self, "_stage9_grid_state", None)
        if not isinstance(state, dict):
            state = {"widgets": [], "selection_widgets": [], "bbox": None}
            self._stage9_grid_state = state
        legacy = getattr(self, "_planilha_borda_widgets", None)
        if isinstance(legacy, list) and not state["selection_widgets"]:
            state["selection_widgets"] = legacy
        self._planilha_borda_widgets = state["selection_widgets"]
        return state

    @staticmethod
    def _planilha_stage9_reuse_frames(tree, storage, amount):
        while len(storage) < amount:
            storage.append(
                Frame(tree, bd=0, highlightthickness=0, relief="flat")
            )
        return storage

    @staticmethod
    def _planilha_stage9_get_visible_rows(tree, limit=40):
        rows = []
        try:
            first = tree.identify_row(1)
            if not first:
                children = tree.get_children("")
                first = children[0] if children else None
            current = first
            for _ in range(limit):
                if not current:
                    break
                rows.append(current)
                current = tree.next(current)
        except Exception:
            return []
        return rows

    def _planilha_desenhar_cabecalho_linhas(self, first_fraction=None):
        """Reutiliza itens Canvas do cabeçalho em vez de recriá-los a cada rolagem."""
        canvas = getattr(self, "_planilha_row_header", None)
        tree = getattr(self, "_planilha_tree", None)
        if canvas is None or tree is None:
            return
        try:
            altura = max(int(canvas.winfo_height()), 28)
        except Exception:
            altura = 360
        try:
            fraction = float(first_fraction) if first_fraction is not None else float(tree.yview()[0])
        except Exception:
            fraction = 0.0
        fraction = max(0.0, min(1.0, fraction))
        row_height = 28
        total_rows = MAX_ROWS
        inicio = max(0, min(total_rows - 1, int(fraction * total_rows + 0.0001)))
        visiveis = max(1, int(altura / row_height) + 3)
        fim = min(total_rows, inicio + visiveis)
        modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
        bg = "#252A2F" if modo_escuro else "#F7F7F7"
        fg = "#AEB4B9" if modo_escuro else "#6B6B6B"
        line = "#384148" if modo_escuro else "#EEEEEE"
        border = "#465058" if modo_escuro else "#E0E0E0"
        canvas.configure(bg=bg, highlightbackground=border)

        state = getattr(self, "_stage9_row_header_state", None)
        if not isinstance(state, dict):
            state = {"items": []}
            self._stage9_row_header_state = state
        items = state["items"]
        quantidade = max(0, fim - inicio)
        while len(items) < quantidade:
            items.append(
                (
                    canvas.create_text(
                        5, 0, anchor="w", fill=fg,
                        font=("Segoe UI", 8), tags=("rownum",)
                    ),
                    canvas.create_line(
                        0, 0, 42, 0, fill=line, tags=("rownum",)
                    ),
                )
            )
        for pos, logical_row in enumerate(range(inicio, fim)):
            y0 = pos * row_height
            text_id, line_id = items[pos]
            canvas.coords(text_id, 5, y0 + row_height // 2)
            canvas.itemconfigure(text_id, text=str(logical_row + 1), fill=fg, state="normal")
            canvas.coords(line_id, 0, y0 + row_height, 42, y0 + row_height)
            canvas.itemconfigure(line_id, fill=line, state="normal")
        for text_id, line_id in items[quantidade:]:
            canvas.itemconfigure(text_id, state="hidden")
            canvas.itemconfigure(line_id, state="hidden")
        top_line = state.get("top_line")
        if top_line is None:
            top_line = canvas.create_line(0, 0, 42, 0, fill=border, tags=("rownum",))
            state["top_line"] = top_line
        else:
            canvas.coords(top_line, 0, 0, 42, 0)
        canvas.itemconfigure(top_line, fill=border, state="normal")

    def _planilha_limpar_borda(self):
        """Oculta a moldura de seleção e as sobreposições reutilizáveis."""
        state = self._planilha_stage9_get_grid_state()
        widgets = state.get("selection_widgets", [])
        for widget in widgets:
            try:
                widget.place_forget()
            except Exception:
                pass
        self._planilha_borda_widgets = widgets
        self._stage9_borda_bbox = None

    def _planilha_desenhar_borda(self):
        tree = getattr(self, "_planilha_tree", None)
        if tree is None:
            return

        state = self._planilha_stage9_get_grid_state()
        selection_widgets = state.setdefault("selection_widgets", [])

        try:
            self._planilha_desenhar_grade()
        except Exception:
            pass

        cells = getattr(self, "_planilha_celulas_selecionadas", set()) or set()
        normalized = set()
        for cell in cells:
            try:
                normalized.add((int(cell[0]), int(cell[1])))
            except Exception:
                continue

        alvo = getattr(self, "_planilha_celula_ativa", None)
        if alvo:
            try:
                normalized.add((int(alvo[0]), int(alvo[1])))
            except Exception:
                pass

        if not normalized:
            self._planilha_limpar_borda()
            return

        draw_cells = normalized if len(normalized) <= 250 else set()
        boxes = []
        if draw_cells:
            for row, col in sorted(draw_cells):
                try:
                    bbox = tree.bbox(str(row), f"#{col + 1}")
                except Exception:
                    bbox = None
                if bbox:
                    boxes.append(bbox)

        active_box = None
        if alvo:
            try:
                active_box = tree.bbox(str(alvo[0]), f"#{int(alvo[1]) + 1}")
            except Exception:
                active_box = None

        if not boxes and active_box:
            boxes = [active_box]
        if not boxes:
            self._planilha_limpar_borda()
            return

        x0 = min(box[0] for box in boxes)
        y0 = min(box[1] for box in boxes)
        x1 = max(box[0] + box[2] for box in boxes)
        y1 = max(box[1] + box[3] for box in boxes)

        cor = self.ACCENT[0] if isinstance(self.ACCENT, tuple) else self.ACCENT
        segmentos = []
        for bbox in boxes:
            x, y, w, h = bbox
            segmentos.extend(
                (
                    (x, y, w, 2),
                    (x, y + h - 2, w, 2),
                    (x, y, 2, h),
                    (x + w - 2, y, 2, h),
                )
            )
        segmentos.extend(
            (
                (x0, y0, x1 - x0, 3),
                (x0, y1 - 3, x1 - x0, 3),
                (x0, y0, 3, y1 - y0),
                (x1 - 3, y0, 3, y1 - y0),
            )
        )

        self._planilha_stage9_reuse_frames(tree, selection_widgets, len(segmentos))
        for frame, (x, y, w, h) in zip(selection_widgets, segmentos):
            try:
                frame.configure(width=max(int(w), 1), height=max(int(h), 1), bg=cor)
                frame.place(x=int(x), y=int(y))
                frame.lift()
            except Exception:
                pass
        for frame in selection_widgets[len(segmentos):]:
            try:
                frame.place_forget()
            except Exception:
                pass

        self._stage9_borda_bbox = (
            str(alvo[0]) if alvo else None,
            int(alvo[1]) if alvo else None,
            int(x0),
            int(y0),
            int(x1 - x0),
            int(y1 - y0),
            len(normalized),
        )

    def _planilha_desenhar_grade(self):
        tree = getattr(self, "_planilha_tree", None)
        if tree is None:
            return
        state = self._planilha_stage9_get_grid_state()
        widgets = state["widgets"]

        modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
        cor_linha = "#414850" if modo_escuro else "#D9DEE3"
        linhas = self._planilha_stage9_get_visible_rows(tree)
        if not linhas:
            for widget in widgets:
                try:
                    widget.place_forget()
                except Exception:
                    pass
            state["bbox"] = None
            return

        segmentos = []
        primeira = linhas[0]
        try:
            bboxes = [tree.bbox(primeira, f"#{col}") for col in (1, 2, 3)]
        except Exception:
            bboxes = []

        if len(bboxes) == 3 and all(bboxes):
            x_positions = [
                bboxes[0][0],
                bboxes[1][0],
                bboxes[2][0],
                bboxes[2][0] + bboxes[2][2],
            ]
            top_y = bboxes[0][1]
            last_box = tree.bbox(linhas[-1], "#1")
            bottom_y = last_box[1] + last_box[3] if last_box else top_y
            for x in x_positions:
                segmentos.append((x, top_y, 1, max(1, bottom_y - top_y)))

        for iid in linhas:
            bbox = tree.bbox(iid, "#1")
            if not bbox:
                continue
            x, y, w, h = bbox
            try:
                right_box = tree.bbox(iid, "#3")
                right = right_box[0] + right_box[2] if right_box else tree.winfo_width()
            except Exception:
                right = tree.winfo_width()
            segmentos.append((x, y + h - 1, max(1, right - x), 1))

        self._planilha_stage9_reuse_frames(tree, widgets, len(segmentos))
        for frame, (x, y, w, h) in zip(widgets, segmentos):
            try:
                frame.configure(width=max(int(w), 1), height=max(int(h), 1), bg=cor_linha)
                frame.place(x=int(x), y=int(y))
                frame.lower()
            except Exception:
                pass
        for frame in widgets[len(segmentos):]:
            try:
                frame.place_forget()
            except Exception:
                pass

        state["bbox"] = (
            int(bboxes[0][0]),
            int(bboxes[0][1]),
            int(bboxes[-1][0] + bboxes[-1][2] - bboxes[0][0]),
            int(bottom_y - bboxes[0][1]),
        )

    def _planilha_definir_selecao(self, cells, active=None):
        """Mantém seleção de células em um único estado canônico."""
        normalized = set()
        for cell in cells or ():
            try:
                row, col = int(cell[0]), int(cell[1])
            except Exception:
                continue
            if 0 <= row < 10000 and 0 <= col < 3:
                normalized.add((row, col))

        self._planilha_celulas_selecionadas = normalized
        self._planilha_linhas_selecionadas = {str(row) for row, _ in normalized}

        if active is not None:
            self._planilha_celula_ativa = (str(int(active[0])), int(active[1]))
        elif normalized:
            row, col = min(normalized)
            self._planilha_celula_ativa = (str(row), col)
        else:
            self._planilha_celula_ativa = None

        try:
            self._planilha_desenhar_borda()
        except Exception:
            pass

    def _planilha_retangulo_selecao(self, inicio, fim):
        return rectangle_selection(inicio, fim)

    def _planilha_clicar_celula(self, event):
        tree = self._planilha_tree
        if tree is None:
            return "break"

        row = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if not row or col_id not in ("#1", "#2", "#3"):
            return "break"

        current = (int(row), int(col_id[1:]) - 1)
        selected = set(getattr(self, "_planilha_celulas_selecionadas", set()) or ())
        active = getattr(self, "_planilha_celula_ativa", None)

        ctrl = bool(getattr(event, "state", 0) & 0x0004)
        shift = bool(getattr(event, "state", 0) & 0x0001)

        if ctrl:
            if current in selected:
                selected.remove(current)
            else:
                selected.add(current)
            self._planilha_definir_selecao(selected, active=current)

        elif shift and active:
            self._planilha_definir_selecao(
                self._planilha_retangulo_selecao(active, current),
                active=current,
            )
        else:
            self._planilha_definir_selecao({current}, active=current)

        self._planilha_drag_anchor = current
        self._planilha_drag_start_xy = (event.x, event.y)
        self._planilha_dragging = False
        self._planilha_fechar_edicao()
        tree.focus_set()
        return "break"

    def _planilha_arrastar_selecao(self, event):
        tree = self._planilha_tree
        anchor = getattr(self, "_planilha_drag_anchor", None)
        if tree is None or anchor is None:
            return "break"

        row = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if not row or col_id not in ("#1", "#2", "#3"):
            return "break"

        start_x, start_y = getattr(
            self, "_planilha_drag_start_xy", (event.x, event.y)
        )
        if (
            not getattr(self, "_planilha_dragging", False)
            and abs(event.x - start_x) < 4
            and abs(event.y - start_y) < 4
        ):
            return "break"

        current = (int(row), int(col_id[1:]) - 1)
        self._planilha_dragging = True
        self._planilha_definir_selecao(
            self._planilha_retangulo_selecao(anchor, current),
            active=current,
        )
        return "break"

    def _planilha_soltar_selecao(self, event):
        tree = self._planilha_tree
        anchor = getattr(self, "_planilha_drag_anchor", None)
        if tree is None or anchor is None:
            return "break"

        row = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if row and col_id in ("#1", "#2", "#3"):
            current = (int(row), int(col_id[1:]) - 1)
            if getattr(self, "_planilha_dragging", False):
                cells = self._planilha_retangulo_selecao(anchor, current)
            else:
                cells = {(int(row), int(col_id[1:]) - 1)}
            self._planilha_definir_selecao(cells, active=current)

        self._planilha_drag_anchor = None
        self._planilha_drag_start_xy = None
        self._planilha_dragging = False
        return "break"

    def _planilha_duplo_clique_celula(self, event):
        tree = self._planilha_tree
        if tree is None:
            return "break"
        row = tree.identify_row(event.y)
        col = tree.identify_column(event.x)
        if not row or col not in ("#1", "#2", "#3"):
            return "break"
        self._planilha_celula_ativa = (row, int(col[1:])-1)
        self._planilha_linhas_selecionadas = {row}
        tree.focus_set()
        self._planilha_desenhar_borda()
        self._planilha_editar_iid(row, int(col[1:])-1)
        return "break"

    def _planilha_selecionar_tudo(self):
        if self._planilha_tree:
            self._planilha_definir_selecao(non_empty_cells(self._planilha_data))
        return "break"

    def _planilha_atualizar_contador(self):
        n = filled_row_count(self._planilha_data)
        if self._planilha_contador_label is not None:
            self._planilha_contador_label.configure(text=f"{n} linhas preenchidas")
        try:
            if hasattr(self, "planilha_estado_label"):
                self.planilha_estado_label.configure(text="Planilha pronta" if n > 0 else "")
        except Exception:
            pass

    def _planilha_snapshot(self):
        return dict(self._planilha_data)

    def _planilha_push_undo(self):
        self._planilha_undo.append(self._planilha_snapshot())
        self._planilha_undo=self._planilha_undo[-50:]

    def _planilha_editar_selecao(self,event=None):
        if self._planilha_tree:
            alvo = getattr(self, "_planilha_celula_ativa", None)
            if alvo:
                self._planilha_editar_iid(alvo[0], int(alvo[1]))
            else:
                focus=self._planilha_tree.focus()
                if focus:
                    self._planilha_editar_iid(focus,0)
        return "break"

    def _planilha_editar_celula(self,event):
        tree=self._planilha_tree
        if tree is None: return
        row=tree.identify_row(event.y); col=tree.identify_column(event.x)
        if not row or col not in ("#1","#2","#3"): return
        self._planilha_editar_iid(row,int(col[1:])-1)

    def _planilha_editar_iid(self,iid,col_index):
        tree=self._planilha_tree
        if tree is None:return
        if self._planilha_edit_entry is not None:
            try:self._planilha_edit_entry.destroy()
            except Exception:pass
            self._planilha_edit_entry=None
        bbox=tree.bbox(iid,f"#{col_index+1}")
        if not bbox:return
        self._planilha_celula_ativa=(iid,col_index)
        self._planilha_linhas_selecionadas={iid}
        self._planilha_limpar_borda()
        x,y,w,h=bbox
        vals=list(tree.item(iid,"values")); old=str(vals[col_index])
        entry=Entry(tree, bd=1, relief="solid", justify="left", font=("Segoe UI",11), highlightthickness=0)
        entry.insert(0,old); entry.place(x=x+1,y=y+1,width=max(w-2,40),height=max(h-2,24))
        self._planilha_edit_entry=entry
        entry.focus_set()
        entry.select_range(0,"end")
        entry.bind("<Control-KeyPress-v>", self._planilha_colar_entry, add="+")
        entry.bind("<Control-KeyPress-V>", self._planilha_colar_entry, add="+")
        entry.bind("<<Paste>>", self._planilha_colar_entry, add="+")
        # Os demais atalhos permanecem nativos enquanto a célula está sendo editada.
        def finish(save=True):
            if self._planilha_edit_entry is not entry:return
            new=entry.get() if save else old
            try: entry.destroy()
            except Exception: pass
            self._planilha_edit_entry=None
            self._planilha_desenhar_borda()
            if save and new!=old:
                self._planilha_push_undo(); self._planilha_redo=[]
                vals[col_index]=new
                tree.item(iid,values=vals)
                key=f"{int(iid)},{col_index}"
                if new: self._planilha_data[key]=new
                else: self._planilha_data.pop(key,None)
                self._planilha_marcar_alteracao()
        entry.bind("<Return>",lambda e:(finish(True),"break")[1]); entry.bind("<Escape>",lambda e:(finish(False),"break")[1]); entry.bind("<FocusOut>",lambda e:finish(True))

    def _planilha_tem_entry_em_foco(self):
        entry = getattr(self, "_planilha_edit_entry", None)
        if entry is None:
            return False
        try:
            return self.app.focus_get() is entry
        except Exception:
            return False

    def _planilha_limpar_celulas_selecionadas(self):
        tree = self._planilha_tree
        if tree is None:
            return "break"

        selected = set(getattr(self, "_planilha_celulas_selecionadas", set()) or ())
        active = getattr(self, "_planilha_celula_ativa", None)
        if not selected and active:
            selected = {(int(active[0]), int(active[1]))}
        if not selected:
            return "break"

        updated, changed = clear_cells(self._planilha_data, selected)
        if not changed:
            return "break"

        self._planilha_push_undo()
        self._planilha_redo = []
        self._planilha_data = updated
        self._planilha_atualizar_grade()
        self._planilha_marcar_alteracao()
        self._planilha_desenhar_borda()
        return "break"

    def _planilha_recortar(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return None
        self._planilha_copiar(event)
        return self._planilha_limpar_celulas_selecionadas()

    def _planilha_atalho_desfazer(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return None
        self._planilha_desfazer()
        return "break"

    def _planilha_atalho_refazer(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return None
        self._planilha_refazer()
        return "break"

    def _planilha_atalho_selecionar_tudo(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return None
        return self._planilha_selecionar_tudo()

    def _planilha_atalho_copiar(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return None
        return self._planilha_copiar(event)

    def _planilha_atalho_colar(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return self._planilha_colar_entry(event)
        return self._planilha_colar(event)

    def _planilha_atalho_excluir(self, event=None):
        if self._planilha_tem_entry_em_foco():
            return None
        return self._planilha_limpar_celulas_selecionadas()

    def _planilha_copiar(self,event=None):
        tree=self._planilha_tree
        if not tree:return "break"
        rows=tuple(sorted(getattr(self, "_planilha_linhas_selecionadas", set()), key=lambda v:int(v)))
        if not rows and self._planilha_celula_ativa:
            rows=(self._planilha_celula_ativa[0],)
        if not rows:return "break"
        vals=["\t".join(map(str,tree.item(i,"values"))) for i in rows]
        self.app.clipboard_clear(); self.app.clipboard_append("\n".join(vals)); return "break"

    def _planilha_foco_pertence_a_grade(self):
        """Retorna True quando o foco atual está dentro da janela/grade da planilha."""
        tree = getattr(self, "_planilha_tree", None)
        if tree is None:
            return False
        try:
            focused = self.app.focus_get()
        except Exception:
            focused = None
        if focused is None:
            return False

        # A edição da célula usa um Entry filho do Treeview; nesse caso o
        # foco continua pertencendo à planilha, mas o paste deve ser nativo.
        current = focused
        try:
            tree_path = str(tree)
            while current is not None:
                if str(current) == tree_path:
                    return True
                parent_path = current.winfo_parent()
                if not parent_path:
                    break
                current = current._nametowidget(parent_path)
        except Exception:
            try:
                return str(focused).startswith(str(tree))
            except Exception:
                return False
        return False

    def _planilha_colar_entry(self, event=None):
        """Fallback de Ctrl+V para o Entry usado na edição de uma célula."""
        entry = getattr(self, "_planilha_edit_entry", None)
        if entry is None:
            return "break"
        try:
            value = self.app.clipboard_get()
        except Exception:
            try:
                value = self.app.clipboard_get(type="PRIMARY")
            except Exception:
                return "break"
        try:
            entry.delete(0, "end")
            entry.insert(0, str(value).replace("\r\n", "\n").replace("\r", "\n"))
        except Exception:
            return "break"
        return "break"

    def _planilha_colar_teclado(self, event=None):
        """Handler redundante de teclado para tornar Ctrl+V independente do Tk."""
        entry = getattr(self, "_planilha_edit_entry", None)
        if entry is not None:
            try:
                focused = self.app.focus_get()
            except Exception:
                focused = None
            if focused is entry:
                return self._planilha_colar_entry(event)
        return self._planilha_colar(event)

    def _planilha_colar(self, event=None):
        tree = self._planilha_tree
        if tree is None:
            return "break"

        self._planilha_fechar_edicao()
        try:
            text = self.app.clipboard_get()
        except Exception:
            try:
                text = self.app.clipboard_get(type="PRIMARY")
            except Exception:
                return "break"

        rows_data = parse_paste_text(text)
        if not rows_data:
            return "break"

        alvo = getattr(self, "_planilha_celula_ativa", None)
        if alvo:
            start_i = int(alvo[0])
            start_col = int(alvo[1])
        else:
            focus_i = tree.focus()
            start_i = int(focus_i) if focus_i else 0
            start_col = 0

        updated, pasted = apply_paste(
            self._planilha_data,
            rows_data,
            start_i,
            start_col,
        )
        if not pasted:
            return "break"

        self._planilha_push_undo()
        self._planilha_redo = []
        self._planilha_data = updated
        self._planilha_atualizar_grade()
        self._planilha_marcar_alteracao()
        return "break"

    def _planilha_limpar(self):
        if not self._planilha_data:
            return
        if not messagebox.askyesno("Limpar planilha","Tem certeza que deseja limpar a planilha?",parent=self._planilha_window):return
        self._planilha_push_undo()
        self._planilha_redo=[]
        self._planilha_data={}
        self._planilha_atualizar_grade()
        self._planilha_atualizar_contador()
        self._planilha_marcar_alteracao()

    def _planilha_atualizar_grade(self):
        tree=self._planilha_tree
        if not tree:return
        refresh=getattr(tree, "refresh", None)
        if callable(refresh):
            refresh()
            return
        for iid in tree.get_children():
            i=int(iid); vals=[self._planilha_data.get(f"{i},{c}","") for c in range(3)]; tree.item(iid,values=vals,tags=("even" if i % 2 == 0 else "odd",))

    def _planilha_desfazer(self):
        state = undo_state(
            self._planilha_undo,
            self._planilha_redo,
            self._planilha_data,
        )
        if state is None:
            return
        self._planilha_undo, self._planilha_redo, self._planilha_data = state
        self._planilha_atualizar_grade()
        self._planilha_marcar_alteracao()

    def _planilha_refazer(self):
        state = redo_state(
            self._planilha_undo,
            self._planilha_redo,
            self._planilha_data,
        )
        if state is None:
            return
        self._planilha_undo, self._planilha_redo, self._planilha_data = state
        self._planilha_atualizar_grade()
        self._planilha_marcar_alteracao()

    def _planilha_fechar_edicao(self):
        if self._planilha_edit_entry is not None:
            try:self._planilha_edit_entry.destroy()
            except Exception:pass
            self._planilha_edit_entry=None

    def _planilha_encerrar_janela(self):
        """Fecha a janela da planilha de forma robusta, sem depender do foco."""
        win=self._planilha_window
        self._planilha_window=None
        self._planilha_tree=None
        self._planilha_row_header=None
        self._planilha_edit_entry=None

        if win is None:
            return

        def destroy_win():
            try:
                if win.winfo_exists():
                    try:
                        win.grab_release()
                    except Exception:
                        pass
                    try:
                        win.withdraw()
                    except Exception:
                        pass
                    win.destroy()
            except Exception:
                pass
            try:
                self.app.lift()
                self.app.update_idletasks()
            except Exception:
                pass

        try:
            self.app.after_idle(destroy_win)
        except Exception:
            destroy_win()

    def _planilha_fechar_sem_salvar_confirmado(self):
        self._planilha_apagar_rascunho()
        self._planilha_efetuou_alteracao=False
        self._planilha_encerrar_janela()

    def _planilha_fechar_pela_janela(self):
        """Fechamento pelo X: pergunta apenas se houver alterações não salvas."""
        self._planilha_fechar_edicao()
        if self._planilha_tem_alteracoes():
            resposta=messagebox.askyesnocancel(
                "Sair da planilha",
                "Existem alterações que ainda não foram salvas.\n\n"
                "Deseja salvar antes de sair?",
                parent=self._planilha_window
            )
            if resposta is None:
                return
            if resposta:
                self._planilha_salvar_e_sair()
            else:
                self._planilha_fechar_sem_salvar_confirmado()
            return

        self._planilha_encerrar_janela()

    def _planilha_salvar_e_sair(self):
        self._planilha_fechar_edicao()
        try:
            self._salvar_planilha_interna_data()
            self._registrar_historico_planilha(self._planilha_data)
            self._planilha_salva_data=dict(self._planilha_data)
            self._planilha_apagar_rascunho()
            self._planilha_efetuou_alteracao=False
            self._planilha_atualizar_contador()
            self._add_activity("Planilha interna salva.",self.SUCCESS)
        except Exception as exc:
            messagebox.showerror(
                "Não foi possível salvar",
                str(exc),
                parent=self._planilha_window
            )
            return

        self._planilha_encerrar_janela()

    def _extrair_codigos_planilha(self):
        """Retorna todos os códigos preenchidos na segunda coluna (Senha)."""
        return extract_column(self._planilha_data, column=1)


    def _filtrar_arquivos_60_dias(self, itens):
        agora = datetime.now()
        limite = agora - timedelta(days=ARQUIVOS_DIAS)
        validos = []
        for item in itens or []:
            if not isinstance(item, dict):
                continue
            try:
                salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            if limite <= salvo <= agora:
                validos.append(item)
        validos.sort(key=lambda item: str(item.get("saved_at", "")))
        return validos

    def _assinatura_historico_planilhas(self):
        try:
            stat = self._planilha_historico_arquivo.stat()
            return (int(stat.st_mtime_ns), int(stat.st_size))
        except OSError:
            return None

    def _invalidar_cache_historico_planilhas(self):
        self._planilha_historico_cache = None
        self._planilha_historico_cache_signature = None

    def _carregar_historico_planilhas(self):
        self._garantir_pasta_planilha()
        assinatura = self._assinatura_historico_planilhas()
        if assinatura is None:
            self._invalidar_cache_historico_planilhas()
            return []

        if (
            self._planilha_historico_cache is not None
            and self._planilha_historico_cache_signature == assinatura
        ):
            return list(self._planilha_historico_cache)

        try:
            data = read_json_with_backup(self._planilha_historico_arquivo, {})
            itens = data.get("items", []) if isinstance(data, dict) else []
            if not isinstance(itens, list):
                self._invalidar_cache_historico_planilhas()
                return []

            filtrados = self._filtrar_arquivos_60_dias(itens)
            if filtrados != itens:
                try:
                    self._salvar_historico_planilhas(filtrados)
                    return list(filtrados)
                except Exception:
                    pass

            self._planilha_historico_cache = list(filtrados)
            self._planilha_historico_cache_signature = (
                self._assinatura_historico_planilhas() or assinatura
            )
            return list(filtrados)
        except Exception:
            self._invalidar_cache_historico_planilhas()
            return []

    def _salvar_historico_planilhas(self, itens):
        self._garantir_pasta_planilha()
        validos = self._filtrar_arquivos_60_dias(itens)
        payload = {"version": 3, "items": validos}
        atomic_write_json(self._planilha_historico_arquivo, payload)
        self._planilha_historico_cache = list(validos)
        self._planilha_historico_cache_signature = (
            self._assinatura_historico_planilhas()
        )

    def _registrar_historico_planilha(self, cells, timestamp=None):
        cells = {str(k): str(v) for k, v in cells.items() if str(v) != ""}
        if not cells:
            return
        agora = timestamp or datetime.now()
        itens = self._carregar_historico_planilhas()
        linhas = set()
        for chave, valor in cells.items():
            if str(valor).strip() == "":
                continue
            try:
                linha, coluna = [int(x) for x in str(chave).split(",")]
            except Exception:
                continue
            if 0 <= coluna < 3:
                linhas.add(linha)
        entrada = {
            "id": agora.strftime("%Y%m%d_%H%M%S_%f"),
            "saved_at": agora.isoformat(timespec="seconds"),
            "cells": cells,
            "filled": len(linhas),
        }
        if itens:
            ultimo = itens[-1]
            if ultimo.get("cells") == cells:
                entrada["id"] = ultimo.get("id", entrada["id"])
                entrada["saved_at"] = ultimo.get("saved_at", entrada["saved_at"])
                entrada["filled"] = ultimo.get("filled", len(linhas))
                itens[-1] = entrada
            else:
                itens.append(entrada)
        else:
            itens.append(entrada)
        self._salvar_historico_planilhas(itens)

    def _preparar_planilha_do_dia(self):
        """Rota a planilha salva de dia anterior para o histórico de Arquivos."""
        self._garantir_pasta_planilha()
        if not self._planilha_arquivo.exists():
            return
        try:
            data = read_json_with_backup(self._planilha_arquivo, {})
            cells = data.get("cells", {}) if isinstance(data, dict) else {}
            updated_at = data.get("updated_at") if isinstance(data, dict) else None
            if not isinstance(cells, dict) or not cells or not updated_at:
                return
            salvo = datetime.fromisoformat(str(updated_at))
            if salvo.date() < datetime.now().date():
                self._registrar_historico_planilha(cells, salvo)
                payload = {"version": 1, "updated_at": datetime.now().isoformat(timespec="seconds"), "cells": {}}
                atomic_write_json(self._planilha_arquivo, payload)
        except Exception:
            pass

    def _abrir_snapshot_historico(self, item):
        cells = item.get("cells", {}) if isinstance(item, dict) else {}
        if not isinstance(cells, dict):
            return
        self._fechar_historico_planilha()
        self.abrir_planilha(cells)
        try:
            if self._planilha_window is not None:
                self._planilha_window.title("Arquivo — Planilha — SM AutoLab")
        except Exception:
            pass

    def _fechar_historico_planilha(self):
        w = getattr(self, "_planilha_historico_window", None)
        if w is not None:
            try:
                w.destroy()
            except Exception:
                pass
        self._planilha_historico_window = None
        self._arquivos_body = None

    def _excluir_historico_planilha(self, item):
        ident = str(item.get("id", ""))
        itens = self._carregar_historico_planilhas()
        novos = [x for x in itens if str(x.get("id", "")) != ident]
        self._salvar_historico_planilhas(novos)
        if self._arquivos_data_selecionada is not None:
            self._mostrar_planilhas_do_dia(self._arquivos_data_selecionada)
        else:
            self._renderizar_calendario_arquivos()

    def _limpar_historico_planilhas(self):
        itens = self._carregar_historico_planilhas()
        if not itens:
            messagebox.showinfo("Arquivos", "Não há arquivos no histórico.", parent=self._planilha_historico_window)
            return
        confirmar = messagebox.askyesno(
            "Limpar Arquivos",
            "Tem certeza que deseja apagar todos os arquivos do histórico?",
            parent=self._planilha_historico_window
        )
        if not confirmar:
            return
        self._salvar_historico_planilhas([])
        self._arquivos_data_selecionada = None
        self._renderizar_calendario_arquivos()

    def _contar_codigos_mes(self, referencia=None):
        """Retorna a quantidade de códigos do mês exibido no calendário.

        A fonte principal é o histórico de execuções. Quando o mês não possui
        registros de execução (por exemplo, históricos antigos migrados apenas
        como planilhas salvas), faz fallback para o histórico de Arquivos e soma
        as linhas preenchidas das planilhas daquele mês. Isso evita que meses
        antigos apareçam como zero apesar de possuírem arquivos registrados.
        """
        referencia = referencia or datetime.now()
        if hasattr(referencia, "year") and hasattr(referencia, "month"):
            ano = int(referencia.year)
            mes = int(referencia.month)
        else:
            hoje = datetime.now()
            ano, mes = hoje.year, hoje.month

        total_execucoes = 0
        encontrou_execucao = False
        for execucao in self._filtrar_historico_execucoes_60_dias(self._historico_execucoes):
            try:
                inicio = datetime.fromisoformat(str(execucao.get("inicio", "")))
            except Exception:
                continue
            if inicio.year != ano or inicio.month != mes:
                continue
            encontrou_execucao = True

            # Compatibilidade com históricos antigos: algumas execuções
            # podem ter processados=0/ausente mesmo tendo códigos concluídos.
            # Nesses casos, usamos a soma Executados + Não executados; como
            # último recurso, usamos o total planejado.
            processados = int(execucao.get("processados", 0) or 0)
            sucessos = int(execucao.get("sucessos", 0) or 0)
            erros = int(execucao.get("erros", 0) or 0)
            planejados = int(execucao.get("total", 0) or 0)

            if processados > 0:
                quantidade = processados
            elif (sucessos + erros) > 0:
                quantidade = sucessos + erros
            else:
                quantidade = planejados
            total_execucoes += quantidade

        if encontrou_execucao and total_execucoes > 0:
            return total_execucoes

        # Fallback para meses que possuem Arquivos salvos, mas não possuem
        # histórico de execução compatível (situação comum em dados antigos).
        total_arquivos = 0
        try:
            for item in self._carregar_historico_planilhas():
                try:
                    salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
                except Exception:
                    continue
                if salvo.year != ano or salvo.month != mes:
                    continue
                try:
                    preenchidas = int(item.get("filled", 0) or 0)
                except Exception:
                    preenchidas = 0
                total_arquivos += max(0, preenchidas)
        except Exception:
            total_arquivos = 0
        return total_arquivos

    def _formatar_contador_arquivos(self, referencia=None):
        valor = self._contar_codigos_mes(referencia)
        return f"{valor:,}".replace(",", ".") + " códigos no mês"

    def _atualizar_contador_arquivos(self, referencia=None):
        """Atualiza os contadores. O contador da janela usa o mês exibido no calendário."""
        texto_main = self._formatar_contador_arquivos()
        if self.arquivos_contador_label is not None:
            try:
                self.arquivos_contador_label.configure(text=texto_main)
            except Exception:
                pass

        label = getattr(self, "_arquivos_contador_janela", None)
        if label is not None:
            try:
                texto_janela = self._formatar_contador_arquivos(referencia)
                label.configure(text=texto_janela)
            except Exception:
                pass

    def _mes_anterior(self, data):
        if data.month == 1:
            return data.replace(year=data.year - 1, month=12, day=1)
        return data.replace(month=data.month - 1, day=1)

    def _mes_proximo(self, data):
        if data.month == 12:
            return data.replace(year=data.year + 1, month=1, day=1)
        return data.replace(month=data.month + 1, day=1)

    @staticmethod
    def _nome_mes(mes):
        meses = (
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
        )
        return meses[mes - 1]

    def _cor_fluente(self, valor):
        """Resolve uma cor CTk (tupla claro/escuro) para um widget tkinter nativo."""
        if isinstance(valor, (tuple, list)):
            modo = str(ctk.get_appearance_mode()).lower()
            return str(valor[1] if modo == "dark" else valor[0])
        return str(valor)

    def _mes_minimo_arquivos(self):
        limite = datetime.now().date() - timedelta(days=ARQUIVOS_DIAS)
        return datetime(limite.year, limite.month, 1)

    def _mes_atual_arquivos(self):
        agora = datetime.now()
        return datetime(agora.year, agora.month, 1)

    def _renderizar_calendario_arquivos(self):
        """Renderiza um calendário Fluent 2 nativo, sem dependências externas."""
        if self._arquivos_body is None:
            return

        for widget in self._arquivos_body.winfo_children():
            widget.destroy()
        self._arquivos_data_selecionada = None
        self._arquivos_calendar_canvas = None
        self._arquivos_calendar_widget = None

        hoje = datetime.now().date()
        limite = hoje - timedelta(days=ARQUIVOS_DIAS)
        itens = self._carregar_historico_planilhas()
        por_dia = {}
        for item in itens:
            try:
                dt = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            por_dia.setdefault(dt.date(), []).append(item)

        card = ctk.CTkFrame(
            self._arquivos_body, fg_color=self.CARD, corner_radius=12,
            border_width=1, border_color=self.BORDER
        )
        card.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        intro = ctk.CTkFrame(card, fg_color="transparent")
        intro.pack(fill="x", padx=18, pady=(14, 4))
        ctk.CTkLabel(
            intro, text="Selecione uma data", text_color=self.TEXT,
            font=("Segoe UI", 15, "bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            intro,
            text="Os dias com planilhas salvas ficam destacados. O histórico mantém até 60 dias.",
            text_color=self.SUBTEXT, font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(2, 0))

        nav = ctk.CTkFrame(card, fg_color="transparent")
        nav.pack(fill="x", padx=18, pady=(10, 8))
        self._arquivos_btn_mes_anterior = ctk.CTkButton(
            nav, text="‹", width=38, height=32, corner_radius=8,
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
            nav, text="›", width=38, height=32, corner_radius=8,
            fg_color=self.CARD, hover_color=self.ACCENT_HOVER,
            border_width=1, border_color=self.BORDER, text_color=self.TEXT,
            font=("Segoe UI", 17, "bold"), command=lambda: self._mudar_mes_arquivos(1)
        )
        self._arquivos_btn_mes_proximo.pack(side="right")

        hint = ctk.CTkFrame(card, fg_color="transparent")
        hint.pack(fill="x", padx=18, pady=(0, 4))
        dot_color = self._cor_fluente(self.ACCENT)
        ctk.CTkLabel(
            hint, text="●", text_color=dot_color, font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        ctk.CTkLabel(
            hint, text=" possui planilhas salvas", text_color=self.SUBTEXT,
            font=("Segoe UI", 9)
        ).pack(side="left", padx=(4, 0))

        canvas = tk.Canvas(
            card,
            height=360,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=self._cor_fluente(self.CARD),
        )
        canvas.pack(fill="both", expand=True, padx=18, pady=(2, 16))
        canvas.bind("<Button-1>", self._clique_calendario_arquivos)
        canvas.bind("<Configure>", lambda _e: self._desenhar_calendario_arquivos())
        self._arquivos_calendar_canvas = canvas
        self._desenhar_calendario_arquivos()

    def _desenhar_calendario_arquivos(self):
        canvas = self._arquivos_calendar_canvas
        if canvas is None or not canvas.winfo_exists():
            return
        canvas.delete("all")

        hoje = datetime.now().date()
        limite = hoje - timedelta(days=ARQUIVOS_DIAS)
        mes = self._arquivos_mes
        if not mes:
            mes = self._mes_atual_arquivos()
            self._arquivos_mes = mes

        itens = self._carregar_historico_planilhas()
        por_dia = {}
        for item in itens:
            try:
                dt = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            por_dia.setdefault(dt.date(), []).append(item)

        modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
        bg = self._cor_fluente(self.CARD)
        border = self._cor_fluente(self.BORDER)
        text = self._cor_fluente(self.TEXT)
        subtext = self._cor_fluente(self.SUBTEXT)
        accent = self._cor_fluente(self.ACCENT)
        accent_hover = self._cor_fluente(self.ACCENT_HOVER)
        disabled = "#555B61" if modo_escuro else "#B7B7B7"
        today_fill = "#E8F1FB" if not modo_escuro else "#20384B"
        today_outline = accent

        self._arquivos_mes_label.configure(text=f"{self._nome_mes(mes.month)} {mes.year}")
        # O contador da janela acompanha exatamente o mês atualmente exibido.
        self._atualizar_contador_arquivos(mes)
        self._arquivos_btn_mes_anterior.configure(
            state="normal" if mes > self._mes_minimo_arquivos() else "disabled"
        )
        self._arquivos_btn_mes_proximo.configure(
            state="normal" if mes < self._mes_atual_arquivos() else "disabled"
        )

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
                (x0 + x1) / 2, margem_y + header_h / 2,
                text=nome, fill=subtext, font=("Segoe UI", 9, "bold")
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
                fill = bg
                outline = border
                fg = text if valido else disabled
                width = 1
                if tem_arquivo and valido:
                    fill = "#EAF4FF" if not modo_escuro else "#183B54"
                    outline = accent
                    width = 1
                elif eh_hoje and valido:
                    fill = today_fill
                    outline = today_outline
                    width = 2

                canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=fill, outline=outline, width=width,
                    tags=(f"dia:{data.isoformat()}",)
                )
                canvas.create_text(
                    centro_x, centro_y - 3,
                    text=str(dia), fill=fg,
                    font=("Segoe UI", 11, "bold" if (tem_arquivo or eh_hoje) else "normal"),
                    tags=(f"dia:{data.isoformat()}",)
                )
                if tem_arquivo and valido:
                    canvas.create_oval(
                        centro_x - 3, y1 - 14, centro_x + 3, y1 - 8,
                        fill=accent, outline="", tags=(f"dia:{data.isoformat()}",)
                    )

    def _clique_calendario_arquivos(self, event):
        canvas = self._arquivos_calendar_canvas
        if canvas is None:
            return
        try:
            item_id = canvas.find_closest(event.x, event.y)[0]
        except Exception:
            return
        tags = canvas.gettags(item_id)
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
        hoje = datetime.now().date()
        limite = hoje - timedelta(days=ARQUIVOS_DIAS)
        if limite <= data <= hoje:
            self._mostrar_planilhas_do_dia(data)

    def _mudar_mes_arquivos(self, direcao):
        atual = self._arquivos_mes or self._mes_atual_arquivos()
        novo = self._mes_proximo(atual) if direcao > 0 else self._mes_anterior(atual)
        if novo < self._mes_minimo_arquivos() or novo > self._mes_atual_arquivos():
            return
        self._arquivos_mes = novo
        self._atualizar_contador_arquivos(novo)
        self._desenhar_calendario_arquivos()

    def _mostrar_planilhas_do_dia(self, data):
        if self._arquivos_body is None:
            return
        hoje = datetime.now().date()
        limite = hoje - timedelta(days=ARQUIVOS_DIAS)
        if data < limite or data > hoje:
            return
        itens = []
        for item in self._carregar_historico_planilhas():
            try:
                dt = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            if dt.date() == data:
                itens.append(item)

        self._arquivos_data_selecionada = data
        for widget in self._arquivos_body.winfo_children():
            widget.destroy()

        header = ctk.CTkFrame(self._arquivos_body, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))
        ctk.CTkButton(
            header, text="← Voltar", command=self._renderizar_calendario_arquivos,
            width=88, height=30, corner_radius=8, fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"), border_width=1,
            border_color=self.BORDER, text_color=self.TEXT, font=("Segoe UI", 10, "bold")
        ).pack(side="left")
        ctk.CTkLabel(
            header, text=data.strftime("%d/%m/%Y"), text_color=self.TEXT,
            font=("Segoe UI", 15, "bold")
        ).pack(side="left", padx=12)

        if not itens:
            ctk.CTkLabel(
                self._arquivos_body, text="Nenhuma planilha foi salva nesta data.",
                text_color=self.SUBTEXT, font=("Segoe UI", 10)
            ).pack(anchor="w", pady=24)
            return

        ctk.CTkLabel(
            self._arquivos_body, text=f"{len(itens)} planilha(s) salva(s) nesta data",
            text_color=self.SUBTEXT, font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 6))

        lista = ctk.CTkScrollableFrame(self._arquivos_body, fg_color="transparent")
        lista.pack(fill="both", expand=True)
        for item in reversed(itens):
            saved = str(item.get("saved_at", ""))
            try:
                dt = datetime.fromisoformat(saved)
                hora = dt.strftime("%H:%M")
            except Exception:
                hora = ""
            filled = int(item.get("filled", 0) or 0)
            card = ctk.CTkFrame(lista, fg_color=self.CARD, corner_radius=8, border_width=1, border_color=self.BORDER)
            card.pack(fill="x", pady=4)
            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", fill="x", expand=True, padx=10, pady=8)
            ctk.CTkLabel(left, text=f"{hora}  •  {filled} linhas preenchidas", text_color=self.TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", padx=8, pady=6)
            ctk.CTkButton(
                actions, text="Abrir", width=70, height=30, corner_radius=8,
                fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER,
                text_color="#FFFFFF", font=("Segoe UI", 10, "bold"),
                command=lambda it=item: self._abrir_snapshot_historico(it)
            ).pack(side="left", padx=(0, 5))
            ctk.CTkButton(
                actions, text="×", width=30, height=30, corner_radius=8,
                fg_color=self.CARD, hover_color=("#FDECEC", "#3A2424"),
                border_width=1, border_color=self.ERROR, text_color=self.ERROR,
                font=("Segoe UI", 14, "bold"), command=lambda it=item: self._excluir_historico_planilha(it)
            ).pack(side="left")

    def abrir_historico_planilha(self):
        self._fechar_historico_planilha()
        # Janela nativa para maximizar a estabilidade do container; o conteúdo continua Fluent 2.
        win = tk.Toplevel(self.app)
        self._planilha_historico_window = win
        win.title("Arquivos — SM AutoLab")
        win.geometry("820x650")
        win.minsize(760, 590)
        win.resizable(True, True)
        win.transient(self.app)
        win.configure(bg=self._cor_fluente(self.BG))
        try:
            aplicar_backdrop_sistema(
                win, "mica_alt",
                dark=ctk.get_appearance_mode().lower() == "dark"
            )
        except Exception:
            pass
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
        ctk.CTkLabel(header, text="Arquivos", text_color=self.TEXT, font=("Segoe UI", 20, "bold")).pack(side="left")
        self._arquivos_contador_janela = ctk.CTkLabel(header, text="0 códigos no mês", text_color=self.SUBTEXT, font=("Segoe UI", 10, "bold"))
        self._arquivos_contador_janela.pack(side="left", padx=(10, 0))
        ctk.CTkButton(
            header, text="Limpar histórico", command=self._limpar_historico_planilhas,
            width=125, height=32, corner_radius=8, fg_color=self.CARD,
            hover_color=("#FDECEC", "#3A2424"), border_width=1, border_color=self.ERROR,
            text_color=self.ERROR, font=("Segoe UI", 10, "bold")
        ).pack(side="right")
        self._arquivos_body = ctk.CTkFrame(win, fg_color="transparent")
        self._arquivos_body.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        hoje = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._arquivos_mes = hoje
        self._arquivos_data_selecionada = None
        self._atualizar_contador_arquivos()
        self._renderizar_calendario_arquivos()
        win.update_idletasks()

    def _fechar_janela_planilha(self):
        self._planilha_encerrar_janela()

    def _planilha_salvar_e_iniciar(self):
        self._planilha_fechar_edicao()
        codigos=self._extrair_codigos_planilha()
        if not codigos:
            messagebox.showwarning(
                "Nenhum código",
                "Preencha os códigos na coluna 'Senha' antes de iniciar.",
                parent=self._planilha_window
            )
            return

        try:
            self._salvar_planilha_interna_data()
            self._registrar_historico_planilha(self._planilha_data)
            self._planilha_salva_data=dict(self._planilha_data)
            self._planilha_apagar_rascunho()
            self._planilha_efetuou_alteracao=False
            self._planilha_atualizar_contador()
        except Exception as exc:
            messagebox.showerror(
                "Não foi possível salvar",
                str(exc),
                parent=self._planilha_window
            )
            return

        # Close first. Only after Tk processes the destroy do we start Chrome.
        win=self._planilha_window
        self._planilha_window=None
        self._planilha_tree=None
        self._planilha_row_header=None
        self._planilha_edit_entry=None

        def iniciar_depois_de_fechar():
            try:
                if win is not None and win.winfo_exists():
                    try:
                        win.grab_release()
                    except Exception:
                        pass
                    try:
                        win.withdraw()
                    except Exception:
                        pass
                    win.destroy()
            except Exception:
                pass

            try:
                self.app.lift()
                self.app.update_idletasks()
            except Exception:
                pass

            self._iniciar_automacao_interna(codigos)

        try:
            self.app.after_idle(iniciar_depois_de_fechar)
        except Exception:
            iniciar_depois_de_fechar()

    def _iniciar_automacao_interna(self, codigos):
        codigos=[str(c).strip() for c in codigos if str(c).strip()]
        if not codigos:
            messagebox.showwarning("Nenhum código","A coluna 'Senha' está vazia.",parent=self.app)
            return

        inicio=ler_checkpoint_interno(codigos)
        start=0
        if inicio is not None and inicio < len(codigos):
            resposta=messagebox.askyesno(
                "Retomar processamento",
                f"Foi encontrado um processamento interrompido.\n\n"
                f"Próximo código: {inicio+1} de {len(codigos)}.\n\n"
                "Deseja continuar de onde parou?",
                parent=self.app
            )
            if resposta:
                start=inicio
                self._add_activity(
                    f"Retomando a partir do código {inicio+1}.",self.WARNING
                )
            else:
                excluir_checkpoint_interno()
                self._add_activity(
                    "Retomada recusada. Começando do primeiro código.",self.INFO
                )

        self._iniciar_historico_execucao("Planilha interna",0,start)
        self._execucao_atual["origem"] = "planilha_interna"
        self._execucao_atual["total"] = len(codigos)
        self._execucao_atual["checkpoint"] = int(start)
        self._execucao_atual["proximo_indice"] = int(start)
        self._execucao_atual["ultimo_codigo"] = ""
        self._execucao_atual["status"] = "Em andamento"
        self._checkpoint_indice_seguro = int(start)
        self._salvar_estado_persistente()
        self._parar=False
        self.botao_iniciar.configure(state="disabled")
        self.botao_planilha.configure(state="disabled")
        self.botao_parar.configure(state="normal")
        self.progresso.set(0)
        self.progresso_label.configure(text=f"{start} / {len(codigos)}")
        self.percentual_label.configure(
            text=f"{(start/len(codigos)*100):.0f}%"
        )
        self._set_stat(self.sucesso_card,0)
        self._set_stat(self.erro_card,0)
        self._set_stat(self.codigo_card,"—")
        self._limpar_erros_visuais()
        self._add_activity(
            f"Iniciando automação com {len(codigos)} código(s) da coluna 'Senha'.",
            self.INFO
        )
        self._add_historico("Nova execução iniciada pela planilha interna.")
        self.atualizar_status("Iniciando")
        threading.Thread(
            target=self._executar_interno,
            args=(codigos,start),
            daemon=True
        ).start()

    def _executar_interno(self,codigos,start):
        try:
            resultado=principal_interno(codigos,self,start)
            if not self._closing:
                self.app.after(0,lambda:self._finalizar(resultado))
        except Exception as exc:
            if not self._closing:
                self.app.after(0,lambda:self._falha_geral(str(exc)))

    def iniciar_thread(self):
        """Inicia diretamente a partir dos códigos salvos na coluna Senha."""
        codigos=self._extrair_codigos_planilha()
        if not codigos:
            self.abrir_planilha()
            messagebox.showwarning(
                "Nenhum código",
                "Preencha os códigos na coluna 'Senha' da planilha.",
                parent=self._planilha_window
            )
            return
        self._iniciar_automacao_interna(codigos)

    def _falha_geral(self, msg):
        self.botao_iniciar.configure(state="normal")
        self.botao_planilha.configure(state="normal")
        self.botao_parar.configure(state="disabled")
        self._add_activity("Processo interrompido por erro.", self.ERROR)
        self._registrar_falha_historico(msg)
        self._aplicar_status("Processo interrompido por erro")
        messagebox.showerror("Erro no processo", msg)

    def _finalizar(self, resultado):
        self.botao_iniciar.configure(state="normal")
        self.botao_planilha.configure(state="normal")
        self.botao_parar.configure(state="disabled")

        # A planilha que originou a execução passa a constar imediatamente em
        # Anteriores quando o processamento termina.
        try:
            cells = self._carregar_planilha_interna()
            if cells:
                self._registrar_historico_planilha(cells)
        except Exception:
            pass

        if self._parar:
            self._add_activity("Processo parado. Ponto de retomada salvo.", self.WARNING)
            self._finalizar_historico_execucao(resultado, "Parada pelo usuário")
            self._aplicar_status("Parado pelo usuário")
        else:
            self._add_activity("Processo finalizado.", self.SUCCESS)
            self._finalizar_historico_execucao(resultado, "Concluída")
            # Aplicar imediatamente: evita que a messagebox bloqueie a atualização
            # do cabeçalho deixando-o visualmente em "Processando".
            self._aplicar_status("Finalizado")

        for item in resultado.itens:
            if item.status == "Erro":
                self._add_erro_codigo(item.codigo)
        self._selecionar_aba("Não executados" if resultado.erros else "Atividade")

        if resultado.erros == 0 and not self._parar:
            messagebox.showinfo(
                "Processo concluído",
                f"Processados: {resultado.processados}\nExecutados: {resultado.sucessos}\nNão executados: 0"
            )
        elif resultado.erros > 0:
            messagebox.showwarning(
                "Processo concluído",
                f"Processados: {resultado.processados}\n"
                f"Executados: {resultado.sucessos}\n"
                f"Não executados: {resultado.erros}\n\n"
                "Os códigos não executados estão na aba 'Não executados'."
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

    def _parar_pisca_status(self, manter_estado=True):
        try:
            job = getattr(self, "_status_blink_job", None)
            if job is not None:
                self.app.after_cancel(job)
            self._status_blink_job = None

            if manter_estado and getattr(self, "status_indicator", None) is not None:
                modo_escuro = ctk.get_appearance_mode().lower() == "dark"
                canvas_bg = "#21482A" if modo_escuro else "#E7F5E7"
                self.status_indicator.configure(bg=canvas_bg)
                self.status_indicator.itemconfigure(self._status_halo, fill="#4E8054")
                self.status_indicator.itemconfigure(self._status_dot, fill="#2F7437")
        except Exception:
            self._status_blink_job = None

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

    def _agendar_retorno_pronto(self):
        if self._status_finalizado_job is not None:
            try:self.app.after_cancel(self._status_finalizado_job)
            except Exception:pass
        self._status_finalizado_job=self.app.after(10000,lambda:self._aplicar_status("Pronto"))

    def _aplicar_status(self, texto):
        self.status_label.configure(text=texto.replace("Status:", "").strip())
        low = texto.lower()

        if "process" in low and "erro" not in low:
            self._status_text_base = "Processando"
            self._status_blink_fast = True
            cor_texto = self.INFO
            cor_pill = ("#E5F1FB", "#183B54")
            cor_borda = ("#B7D7EF", "#2C5E7A")
        elif "parando" in low:
            self._status_text_base = "Parando"
            self._status_blink_fast = True
            cor_texto = self.WARNING
            cor_pill = ("#FFF4CE", "#4B3A1A")
            cor_borda = ("#F0C36A", "#725B28")
        elif "erro" in low or "interromp" in low:
            self._status_text_base = "Atenção"
            self._status_blink_fast = True
            cor_texto = self.ERROR
            cor_pill = ("#FDE7E9", "#4B2529")
            cor_borda = ("#F1A6AA", "#7A3D42")
        elif "finalizado" in low:
            self._status_text_base = "Finalizado"
            self._status_blink_fast = False
            cor_texto = self.SUCCESS
            cor_pill = ("#E7F5E7", "#21482A")
            cor_borda = ("#C5E4C8", "#37653E")
        else:
            self._status_text_base = "Pronto"
            self._status_blink_fast = False
            cor_texto = self.SUCCESS
            cor_pill = ("#E7F5E7", "#21482A")
            cor_borda = ("#C5E4C8", "#37653E")

        self.status_pill.configure(fg_color=cor_pill, border_color=cor_borda)
        self.status_text.configure(
            text=self._status_text_base,
            text_color=cor_texto,
            font=("Segoe UI", 13, "bold")
        )
        self.status_label.configure(text_color=cor_texto)
        modo = ctk.get_appearance_mode().lower()
        canvas_bg = cor_pill[1] if modo == "dark" else cor_pill[0]
        self.status_indicator.configure(bg=canvas_bg)
        if self._status_blink_fast or self._status_text_base == "Pronto":
            self._iniciar_pisca_status()
        else:
            self._parar_pisca_status()

    def atualizar_progresso(self, processados, total, sucessos, erros, codigo):
        if self._closing:
            return
        self.app.after(0, lambda: self._aplicar_progresso(processados, total, sucessos, erros, codigo))

    def _animar_progresso(self, destino):
        try:
            atual=float(self.progresso.get())
        except Exception:
            atual=0.0

        destino=max(0.0,min(1.0,float(destino)))

        # Cancel any previous progress animation so multiple callbacks cannot
        # fight each other when successive codes finish quickly.
        job=getattr(self,"_progress_anim_job",None)
        if job is not None:
            try:self.app.after_cancel(job)
            except Exception:pass
            self._progress_anim_job=None

        distancia=destino-atual
        if abs(distancia)<0.0005:
            self.progresso.set(destino)
            return

        # Slow, steady, linear movement (~420 ms per code-step).
        duracao_ms=420
        intervalo_ms=20
        passos=max(1,int(duracao_ms/intervalo_ms))
        passo=distancia/passos

        def tick(i=0, valor=atual):
            if self._closing:
                self._progress_anim_job=None
                return
            novo=destino if i>=passos else valor+passo
            self.progresso.set(max(0.0,min(1.0,novo)))
            if i<passos:
                self._progress_anim_job=self.app.after(
                    intervalo_ms,lambda:tick(i+1,novo)
                )
            else:
                self._progress_anim_job=None

        tick()

    def _aplicar_progresso(self, processados, total, sucessos, erros, codigo):
        self._checkpoint_indice_seguro = int(processados)
        if self._execucao_atual:
            self._execucao_atual["status"] = "Em andamento"
            self._execucao_atual["checkpoint"] = int(processados)
            self._execucao_atual["proximo_indice"] = int(processados)
            self._execucao_atual["total"] = int(total)
            self._execucao_atual["ultimo_codigo"] = str(codigo)
            self._execucao_atual["ultimo_checkpoint"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._salvar_estado_persistente()
        pct = processados / total if total else 0
        self._animar_progresso(pct)
        self.progresso_label.configure(text=f"{processados} / {total}")
        self.percentual_label.configure(text=f"{pct:.0%}")
        self._set_stat(self.sucesso_card, sucessos)
        self._set_stat(self.erro_card, erros)
        self._set_stat(self.codigo_card, codigo)
        self.status_label.configure(
            text=f"Processando código {processados} de {total}",
            text_color=self.INFO,
        )
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

        if self._execucao_atual:
            try:
                indice = max(0, int(self._checkpoint_indice_seguro))
                self._execucao_atual["status"] = "Interrompida — ponto salvo"
                self._execucao_atual["checkpoint"] = indice
                self._execucao_atual["proximo_indice"] = indice
                self._execucao_atual["interrompida_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if str(self._execucao_atual.get("origem", "")) == "planilha_interna" and not self.caminho:
                    codigos = self._extrair_codigos_planilha()
                    if codigos:
                        salvar_checkpoint_interno(codigos, indice)
                elif self.caminho:
                    pagina = int(self._execucao_atual.get("pagina", 1)) - 1
                    salvar_checkpoint(self.caminho, pagina, indice)

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
        if self._status_finalizado_job is not None:
            try:self.app.after_cancel(self._status_finalizado_job)
            except Exception:pass
            self._status_finalizado_job=None

        if getattr(self, "_planilha_povoamento_job", None) is not None:
            try:
                if self._planilha_tree is not None:
                    self._planilha_tree.after_cancel(self._planilha_povoamento_job)
            except Exception:
                pass
            self._planilha_povoamento_job = None

        for job_attr in (
            "_fluent_accent_job",
            "_progress_anim_job",
            "_micro_dashboard_complete_job",
        ):
            job = getattr(self, job_attr, None)
            if job is not None:
                try:
                    self.app.after_cancel(job)
                except Exception:
                    pass
                try:
                    setattr(self, job_attr, None)
                except Exception:
                    pass

        self._fechar_menus()
        self.app.destroy()

    def run(self):
        self.app.mainloop()

