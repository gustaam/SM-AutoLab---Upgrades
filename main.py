from __future__ import annotations

import ctypes
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from interface import App
from patch import aplicar_patch_ui


class StartupSplash:
    """Splash de inicialização com dissolução suave para o SM AutoLab."""

    WIDTH = 760
    HEIGHT = 620
    FPS_MS = 8

    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.configure(bg="#FFFFFF")
        self.root.attributes("-topmost", True)

        self.canvas = tk.Canvas(
            self.root,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg="#FFFFFF",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        self._load_assets()
        self._center()
        self._photo = None
        self._start = time.perf_counter()
        self._running = True

    def _resource_path(self, name: str) -> Path:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "assets" / name

    def _load_assets(self):
        self.bg = Image.new("RGBA", (self.WIDTH, self.HEIGHT), (255, 255, 255, 255))

        self.main_logo = Image.open(
            self._resource_path("laboratorio_principal.png")
        ).convert("RGBA")
        main_side = 400
        self.main_logo = self.main_logo.resize(
            (main_side, main_side),
            Image.Resampling.LANCZOS,
        )

        self.powered_logo = Image.open(
            self._resource_path("feegow_powered.png")
        ).convert("RGBA")
        secondary_width = 180
        secondary_height = max(
            1,
            round(
                self.powered_logo.height * secondary_width / self.powered_logo.width
            ),
        )
        self.powered_logo = self.powered_logo.resize(
            (secondary_width, secondary_height),
            Image.Resampling.LANCZOS,
        )

        self.font_path_candidates = [
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/SegoeUI.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        ]
        self.font_path = next(
            (p for p in self.font_path_candidates if p.exists()), None
        )

        if self.font_path:
            self.powered_font = ImageFont.truetype(str(self.font_path), 17)
        else:
            self.powered_font = ImageFont.load_default()

        self.main_pos = (
            (self.WIDTH - self.main_logo.width) // 2,
            70,
        )
        self.powered_pos = (
            self.WIDTH - self.powered_logo.width - 20,
            self.HEIGHT - self.powered_logo.height - 22,
        )

    @staticmethod
    def _smoothstep(x: float) -> float:
        x = max(0.0, min(1.0, x))
        return x * x * (3.0 - 2.0 * x)

    def _alpha_for_time(self, t: float) -> float:
        if t < 1.00:
            return self._smoothstep(t / 1.00)
        if t < 1.82:
            return 1.0
        if t < 3.00:
            return 1.0 - self._smoothstep((t - 1.82) / 1.18)
        return 0.0

    def _render_frame(self, alpha: float):
        frame = self.bg.copy()

        logo = self.main_logo.copy()
        logo.putalpha(logo.getchannel("A").point(lambda a: int(a * alpha)))
        frame.alpha_composite(logo, dest=self.main_pos)

        powered = Image.new(
            "RGBA",
            (self.powered_logo.width + 16, 24),
            (255, 255, 255, 0),
        )
        pdraw = ImageDraw.Draw(powered)
        text = "Powered by"
        bbox = pdraw.textbbox((0, 0), text, font=self.powered_font)
        tw = bbox[2] - bbox[0]
        pdraw.text(
            (powered.width - tw - 8, 2),
            text,
            fill=(100, 106, 112, int(235 * alpha)),
            font=self.powered_font,
        )
        powered.putalpha(
            powered.getchannel("A").point(lambda a: int(a * alpha))
        )

        powered_x = self.powered_pos[0] - 2
        powered_y = self.powered_pos[1] - 18
        frame.alpha_composite(powered, dest=(powered_x, powered_y))

        logo2 = self.powered_logo.copy()
        logo2.putalpha(
            logo2.getchannel("A").point(lambda a: int(a * alpha))
        )
        frame.alpha_composite(logo2, dest=self.powered_pos)

        self._photo = ImageTk.PhotoImage(frame)
        self.canvas.delete("all")
        self.canvas.create_image(
            self.WIDTH // 2,
            self.HEIGHT // 2,
            image=self._photo,
            anchor="center",
        )

    def _tick(self):
        if not self._running:
            return
        elapsed = time.perf_counter() - self._start
        alpha = self._alpha_for_time(elapsed)
        self._render_frame(alpha)

        if elapsed >= 3.0:
            self._running = False
            self.root.after(10, self.close)
            return

        self.root.after(self.FPS_MS, self._tick)

    def _center(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max((sw - self.WIDTH) // 2, 0)
        y = max((sh - self.HEIGHT) // 2, 0)
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}+{x}+{y}")

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self._render_frame(0.0)
        self._start = time.perf_counter()
        self.root.after(0, self._tick)
        self.root.mainloop()


def run_splash():
    StartupSplash().run()


# Correções finais de UI consolidadas diretamente no módulo de entrada.
SM_AUTOLAB_UI_FIXES_29912 = "SM-AUTOLAB-2.99.12-UI-FIXES"


def _widget_inside(widget, ancestor):
    if widget is None or ancestor is None:
        return False
    try:
        child = str(widget)
        parent = str(ancestor)
    except Exception:
        return False
    return child == parent or child.startswith(parent + ".")


def _walk_children(widget):
    if widget is None:
        return
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _walk_children(child)


def _ctrl_pressed(event=None):
    """Detecta Ctrl de forma consistente, inclusive em widgets Tk/CTk no Windows."""
    try:
        state = int(getattr(event, "state", 0) or 0)
    except Exception:
        state = 0
    if state & 0x0004:
        return True

    if sys.platform.startswith("win"):
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000)
        except Exception:
            pass
    return False


def _home_counter(self):
    """Exibe exclusivamente a quantidade de senhas salvas na planilha persistida."""
    label = getattr(self, "arquivos_contador_label", None)
    if label is None:
        return

    try:
        total = max(0, int(self._count_saved_passwords() or 0))
    except Exception:
        total = 0

    try:
        if total > 0:
            label.configure(text=f"{total} Códigos salvos")
            if label.winfo_manager() != "pack":
                label.pack(side="left", padx=(8, 0))
            else:
                label.pack_configure(side="left", padx=(8, 0))
        else:
            label.pack_forget()
    except Exception:
        pass


def _clear_history_selection(self):
    selected = getattr(self, "_hist_selected_tiles", set())
    if not isinstance(selected, set):
        selected = set()
        self._hist_selected_tiles = selected
    for tile in tuple(selected):
        try:
            tile.configure(border_color=self.BORDER, border_width=1, fg_color=self.CARD)
        except Exception:
            pass
    selected.clear()
    self._hist_selected_tile = None


def _select_history_tile(self, tile, ctrl=False):
    selected = getattr(self, "_hist_selected_tiles", set())
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
                    other.configure(border_color=self.BORDER, border_width=1, fg_color=self.CARD)
                except Exception:
                    pass
        selected.clear()
        selected.add(tile)

    self._hist_selected_tile = tile if tile in selected else (next(iter(selected), None))
    for other in tuple(selected):
        try:
            other.configure(
                border_color=self.ACCENT,
                border_width=1,
                fg_color=("#EAF4FF", "#1B3C53"),
            )
        except Exception:
            pass


def _bind_history_tile(self, tile):
    execucao = getattr(tile, "_sm_execucao", None)
    if execucao is None:
        return

    def on_click(event=None, current=tile):
        _select_history_tile(self, current, ctrl=_ctrl_pressed(event))
        return "break"

    def on_double_click(_event=None, item=execucao, current=tile):
        _select_history_tile(self, current, ctrl=False)
        self._abrir_detalhe_historico(item)
        return "break"

    def on_enter(_event=None, current=tile):
        if current in getattr(self, "_hist_selected_tiles", set()):
            return
        try:
            current.configure(border_color=self.ACCENT_HOVER, fg_color=("#EAF4FC", "#263F50"))
        except Exception:
            pass

    def on_leave(_event=None, current=tile):
        if current in getattr(self, "_hist_selected_tiles", set()):
            return
        try:
            current.configure(border_color=self.BORDER, fg_color=self.CARD)
        except Exception:
            pass

    for widget in _walk_children(tile):
        try:
            for sequence in (
                "<Button-1>",
                "<Control-Button-1>",
                "<Double-Button-1>",
                "<Double-1>",
                "<Enter>",
                "<Leave>",
            ):
                widget.unbind(sequence)
            widget.bind("<Button-1>", on_click)
            widget.bind("<Control-Button-1>", on_click)
            widget.bind("<Double-Button-1>", on_double_click)
            widget.bind("<Double-1>", on_double_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
        except Exception:
            pass


def _create_history_tile(self, execucao, atual=False):
    parent = getattr(self, "historico_lista", None)
    if parent is None:
        return

    if not hasattr(self, "_hist_tiles"):
        self._hist_tiles = set()
    if not hasattr(self, "_hist_selected_tiles"):
        self._hist_selected_tiles = set()

    grid = getattr(self, "_hist_grid", None)
    try:
        valid_grid = grid is not None and grid.winfo_exists()
    except Exception:
        valid_grid = False
    if not valid_grid:
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(anchor="center", pady=(4, 6))
        self._hist_grid = grid

    count = len(grid.winfo_children())
    row, col = divmod(count, 5)
    for index in range(5):
        try:
            grid.grid_columnconfigure(index, weight=0)
        except Exception:
            pass

    tile = ctk.CTkFrame(
        grid,
        fg_color=self.CARD,
        corner_radius=8,
        border_width=1,
        border_color=self.BORDER,
        width=128,
        height=104,
    )
    tile.grid(row=row, column=col, padx=2, pady=2, sticky="nw")
    tile.grid_propagate(False)
    tile._sm_execucao = execucao
    self._hist_tiles.add(tile)

    inicio = str(execucao.get("inicio", ""))
    status = str(execucao.get("status", ""))
    erros = int(execucao.get("erros", 0) or 0)
    dia = inicio.split(" ")[0] if inicio else ""
    hora = inicio.split(" ")[1] if " " in inicio else ""

    ctk.CTkLabel(
        tile, text="📁", font=("Segoe UI Emoji", 21), text_color=self.ACCENT
    ).pack(pady=(6, 0))
    ctk.CTkLabel(
        tile, text=dia, text_color=self.TEXT, font=("Segoe UI", 10, "bold")
    ).pack()
    ctk.CTkLabel(
        tile, text=hora, text_color=self.SUBTEXT, font=("Segoe UI", 8)
    ).pack()
    ctk.CTkLabel(
        tile,
        text=f"{status} • {erros}",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8),
        wraplength=112,
    ).pack(pady=(2, 0))

    _bind_history_tile(self, tile)


def _restore_history(self, *args, **kwargs):
    result = self._ui_29912_original_restore(*args, **kwargs)
    try:
        self._hist_selected_tiles = set()
        self._hist_selected_tile = None
        for tile in tuple(getattr(self, "_hist_tiles", set())):
            _bind_history_tile(self, tile)
    except Exception:
        pass
    return result


def _calendar_click(self, event):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return "break"

    data = None
    try:
        items = canvas.find_overlapping(event.x, event.y, event.x, event.y)
    except Exception:
        items = ()
    for item_id in reversed(items):
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

    ctrl = _ctrl_pressed(event)
    if ctrl or getattr(self, "_arquivos_modo_selecao", False):
        self._toggle_data_selecionada(data)
        return "break"

    selecionadas = getattr(self, "_arquivos_datas_selecionadas", None)
    if selecionadas:
        try:
            selecionadas.clear()
            self._cancelar_animacao_selecao()
            self._atualizar_contador_selecao()
            self._desenhar_calendario_arquivos()
        except Exception:
            pass
    self._mostrar_planilhas_do_dia(data)
    return "break"


def _bind_calendar_controls(self):
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if canvas is None:
        return
    try:
        canvas.unbind("<Button-1>")
        canvas.unbind("<Control-Button-1>")
        canvas.bind("<Button-1>", self._clique_calendario_arquivos)
        canvas.bind("<Control-Button-1>", self._clique_calendario_arquivos)
    except Exception:
        pass


def _global_click(self, event=None):
    # Ctrl+clique deve preservar a seleção atual para permitir acrescentar
    # outro item, exatamente como no Windows Explorer.
    if _ctrl_pressed(event):
        return

    widget = getattr(event, "widget", None) if event is not None else None

    selected_tiles = getattr(self, "_hist_selected_tiles", set())
    if selected_tiles and not any(_widget_inside(widget, tile) for tile in tuple(selected_tiles)):
        _clear_history_selection(self)

    selected_dates = getattr(self, "_arquivos_datas_selecionadas", set())
    canvas = getattr(self, "_arquivos_calendar_canvas", None)
    if selected_dates and canvas is not None and not _widget_inside(widget, canvas):
        try:
            selected_dates.clear()
            self._cancelar_animacao_selecao()
            self._atualizar_contador_selecao()
            self._desenhar_calendario_arquivos()
        except Exception:
            pass


def install_ui_29912(App):
    if getattr(App, "_ui_29912_aplicado", False):
        return
    App._ui_29912_aplicado = True
    App._ui_29912_marker = SM_AUTOLAB_UI_FIXES_29912

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _home_counter(self))
        except Exception:
            _home_counter(self)
        try:
            if not getattr(self, "_ui_29912_global_binding", False):
                self.app.bind_all("<Button-1>", lambda event: _global_click(self, event), add="+")
                self._ui_29912_global_binding = True
        except Exception:
            pass
        return result

    App.config_app = config_wrapper

    original_save_exit = App._planilha_salvar_e_sair

    def save_exit_wrapper(self, *args, **kwargs):
        result = original_save_exit(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _home_counter(self))
        except Exception:
            _home_counter(self)
        return result

    App._planilha_salvar_e_sair = save_exit_wrapper

    original_save_start = getattr(App, "_planilha_salvar_e_iniciar", None)
    if original_save_start is not None:
        def save_start_wrapper(self, *args, **kwargs):
            result = original_save_start(self, *args, **kwargs)
            try:
                self.app.after_idle(lambda: _home_counter(self))
            except Exception:
                _home_counter(self)
            return result
        App._planilha_salvar_e_iniciar = save_start_wrapper

    App._criar_pasta_historico = _create_history_tile
    App._ui_29912_original_restore = App._restaurar_historico_na_tela
    App._restaurar_historico_na_tela = _restore_history
    App._clique_calendario_arquivos = _calendar_click
    App._atualizar_contador_principal_29912 = _home_counter

    original_render = App._renderizar_calendario_arquivos

    def render_calendar_wrapper(self, *args, **kwargs):
        result = original_render(self, *args, **kwargs)
        _bind_calendar_controls(self)
        return result

    App._renderizar_calendario_arquivos = render_calendar_wrapper


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



# Camada visual Fluent 2 — refinamento não invasivo da interface principal.
SM_AUTOLAB_FLUENT_UI_29916 = "SM-AUTOLAB-FLUENT-2-29916"


def _fluent_cor(cor, modo=None):
    try:
        if isinstance(cor, tuple):
            if modo is None:
                modo = str(ctk.get_appearance_mode()).lower()
            return cor[1] if modo == "dark" else cor[0]
        return str(cor)
    except Exception:
        return "#0F6CBD"


def _fluent_bind_button_feedback(app, widget, base_border_width):
    if getattr(widget, "_fluent_interactions_bound", False):
        return
    widget._fluent_interactions_bound = True

    try:
        base_color = widget.cget("border_color")
    except Exception:
        base_color = None

    def restore():
        try:
            if not widget.winfo_exists():
                return
            focused = widget.focus_get() is widget
            width = max(1, int(base_border_width)) if focused else int(base_border_width)
            color = app.ACCENT_HOVER if focused else base_color
            widget.configure(border_width=width, border_color=color)
        except Exception:
            pass

    def on_focus_in(_event=None):
        if getattr(widget, "_fluent_no_focus_ring", False):
            return
        try:
            widget.configure(
                border_width=max(1, int(base_border_width)),
                border_color=app.ACCENT_HOVER,
            )
        except Exception:
            pass

    def on_focus_out(_event=None):
        try:
            widget.configure(
                border_width=int(base_border_width),
                border_color=base_color,
            )
        except Exception:
            pass

    def on_press(_event=None):
        if getattr(widget, "_fluent_no_press", False):
            return
        try:
            if str(widget.cget("state")) == "disabled":
                return
        except Exception:
            pass
        try:
            widget.configure(
                border_width=max(2, int(base_border_width) + 1),
                border_color=app.ACCENT_HOVER,
            )
            old_job = getattr(widget, "_fluent_press_job", None)
            if old_job is not None:
                try:
                    widget.after_cancel(old_job)
                except Exception:
                    pass
            widget._fluent_press_job = widget.after(90, restore)
        except Exception:
            pass

    widget.bind("<FocusIn>", on_focus_in, add="+")
    widget.bind("<FocusOut>", on_focus_out, add="+")
    widget.bind("<ButtonPress-1>", on_press, add="+")


def _fluent_aplicar_estilo_widget(app, widget, card_radius=10):
    """Aplica acabamento visual + feedback de interação sem alterar comandos."""
    try:
        if isinstance(widget, ctk.CTkFrame):
            fg = widget.cget("fg_color")
            if fg != "transparent" and widget is not getattr(widget, "_fluent_header", None):
                widget.configure(corner_radius=card_radius)
        elif isinstance(widget, ctk.CTkButton):
            altura = int(widget.cget("height") or 32)
            raio = 10 if altura >= 40 else 8
            widget.configure(corner_radius=raio, cursor="hand2")
            try:
                base_border_width = int(widget.cget("border_width") or 0)
            except Exception:
                base_border_width = 0
            _fluent_bind_button_feedback(app, widget, base_border_width)
        elif isinstance(widget, ctk.CTkProgressBar):
            widget.configure(height=10, corner_radius=5)
        elif isinstance(widget, ctk.CTkTextbox):
            widget.configure(corner_radius=9)
        elif isinstance(widget, ctk.CTkEntry):
            widget.configure(corner_radius=8)
            try:
                widget.configure(cursor="ibeam")
            except Exception:
                pass
            try:
                _fluent_bind_button_feedback(app, widget, int(widget.cget("border_width") or 0))
            except Exception:
                pass
    except Exception:
        pass


def _fluent_marcar_hover(widget, base, hover):
    try:
        widget.configure(hover_color=hover)
    except Exception:
        pass


def _aplicar_fluent_ui_29916(self):
    """Refina a tela inicial com superfícies, estados e microdetalhes Fluent 2."""
    try:
        self.app.configure(fg_color=self.BG)
        children = self.app.winfo_children()
    except Exception:
        return

    # Cabeçalho: superfície elevada com uma linha de acento discreta.
    header = next(
        (w for w in children if isinstance(w, ctk.CTkFrame)),
        None,
    )
    if header is not None:
        try:
            header._fluent_header = True
            header.configure(
                fg_color=self.CARD,
                border_width=0,
                corner_radius=0,
            )
            accent_line = getattr(self, "_fluent_accent_line", None)
            if accent_line is None or not accent_line.winfo_exists():
                accent_line = ctk.CTkFrame(
                    header,
                    height=2,
                    corner_radius=1,
                    fg_color=self.ACCENT,
                )
                accent_line.place(relx=0, rely=1.0, relwidth=1.0, anchor="sw")
                self._fluent_accent_line = accent_line
        except Exception:
            pass

    # Acabamento consistente das superfícies que já existem.
    for widget in children:
        try:
            if widget is header:
                continue
            for descendant in _walk_children(widget):
                _fluent_aplicar_estilo_widget(self, descendant)
        except Exception:
            continue

    # Botões principais: estados hover coerentes com o Fluent 2.
    try:
        self.botao_iniciar.configure(
            corner_radius=10,
            height=46,
            hover_color=self.ACCENT_HOVER,
        )
        self.botao_parar.configure(
            corner_radius=10,
            height=46,
            hover_color=("#FDECEC", "#43282A"),
        )
        self.botao_configuracoes.configure(
            corner_radius=10,
            height=40,
            hover_color=("#EAF4FC", "#263F50"),
        )
        self.botao_planilha.configure(
            corner_radius=8,
            hover_color=self.ACCENT_HOVER,
        )
        self.botao_historico_planilha.configure(
            corner_radius=8,
            hover_color=("#EAF4FC", "#263F50"),
        )
    except Exception:
        pass

    # Cartões de métricas: trilho lateral de acento para hierarquia visual.
    for card, accent in (
        (getattr(self, "sucesso_card", None), self.SUCCESS),
        (getattr(self, "erro_card", None), self.ERROR),
        (getattr(self, "codigo_card", None), self.INFO),
    ):
        if card is None:
            continue
        try:
            rail = getattr(card, "_fluent_accent_rail", None)
            if rail is None or not rail.winfo_exists():
                rail = ctk.CTkFrame(card, width=3, corner_radius=1, fg_color=accent)
                rail.place(x=0, rely=0.18, relheight=0.64, anchor="nw")
                card._fluent_accent_rail = rail
        except Exception:
            pass

    # Separador do rodapé: mantém as ações visualmente ancoradas sem alterar
    # a área clicável nem a posição dos botões.
    try:
        actions = next(
            (w for w in self.app.winfo_children()
             if isinstance(w, ctk.CTkFrame) and w is not header and w.winfo_height() >= 60),
            None,
        )
        if actions is not None:
            separator = getattr(actions, "_fluent_separator", None)
            if separator is None or not separator.winfo_exists():
                separator = ctk.CTkFrame(actions, height=1, corner_radius=0, fg_color=self.BORDER)
                separator.place(relx=0, rely=0, relwidth=1, anchor="nw")
                actions._fluent_separator = separator
    except Exception:
        pass

    # Tabs: superfície discreta e estado ativo mais próximo do Fluent.
    for nome, botao in getattr(self, "tab_buttons", {}).items():
        try:
            botao.configure(
                corner_radius=8,
                hover_color=("#E8F2FC", "#204965"),
                font=("Segoe UI", 11, "bold"),
            )
        except Exception:
            pass

    # Status: contorno sutil e indicador preservado.
    try:
        self.status_pill.configure(
            border_width=1,
            border_color=("#C5E4C8", "#37653E"),
            corner_radius=20,
        )
    except Exception:
        pass

    # Barra de progresso mais suave visualmente.
    try:
        self.progresso.configure(height=10, corner_radius=5)
    except Exception:
        pass

    # Pequena microinteração: o acento do cabeçalho respira lentamente,
    # sem deslocar nenhum controle e sem interferir na automação.
    def _pulse_accent(step=0):
        line = getattr(self, "_fluent_accent_line", None)
        if line is None:
            return
        try:
            if not line.winfo_exists() or getattr(self, "_closing", False):
                return
            # Alterna entre o azul base e o hover em baixa frequência.
            color = self.ACCENT if step % 2 == 0 else self.ACCENT_HOVER
            line.configure(fg_color=color)
            self._fluent_accent_job = self.app.after(
                1800, lambda: _pulse_accent(step + 1)
            )
        except Exception:
            self._fluent_accent_job = None

    try:
        old_job = getattr(self, "_fluent_accent_job", None)
        if old_job is not None:
            self.app.after_cancel(old_job)
        self._fluent_accent_job = None
        self.app.after(500, _pulse_accent)
    except Exception:
        pass


def _fluent_animar_entrada(app):
    if getattr(app, "_fluent_entry_animation_done", False):
        return
    app._fluent_entry_animation_done = True

    try:
        app.attributes("-alpha", 0.94)
    except Exception:
        return

    total_frames = 7
    interval_ms = 24

    def tick(frame=0):
        try:
            if getattr(app, "_closing", False) or not app.winfo_exists():
                return
            if frame >= total_frames:
                app.attributes("-alpha", 1.0)
                return
            fator = (frame + 1) / total_frames
            app.attributes("-alpha", 0.94 + (0.06 * fator))
            app.after(interval_ms, lambda: tick(frame + 1))
        except Exception:
            try:
                app.attributes("-alpha", 1.0)
            except Exception:
                pass

    app.after_idle(tick)


def install_ui_fluent_29916(App):
    """Instala a camada visual sem substituir a arquitetura funcional existente."""
    if getattr(App, "_fluent_ui_29916_aplicado", False):
        return
    App._fluent_ui_29916_aplicado = True
    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _aplicar_fluent_ui_29916(self))
            self.app.after_idle(lambda: _fluent_animar_entrada(self.app))
        except Exception:
            _aplicar_fluent_ui_29916(self)
        return result

    setattr(App, "config_app", config_wrapper)


# Dashboard moderno — Stage 3.
SM_AUTOLAB_DASHBOARD_29917 = "SM-AUTOLAB-DASHBOARD-29917"


def _dashboard_clamp(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _dashboard_exists(widget):
    try:
        return widget is not None and widget.winfo_exists()
    except Exception:
        return False


def _dashboard_cor(value, modo=None):
    try:
        if isinstance(value, tuple):
            modo = modo or str(ctk.get_appearance_mode()).lower()
            return value[1] if modo == "dark" else value[0]
        return str(value)
    except Exception:
        return "#0F6CBD"


def _dashboard_refrescar(self, progresso=None):
    hero = getattr(self, "_dashboard_hero", None)
    if not _dashboard_exists(hero):
        return

    try:
        pct = _dashboard_clamp(
            self.progresso.get() if progresso is None else progresso
        )
    except Exception:
        pct = _dashboard_clamp(progresso)

    modo = str(ctk.get_appearance_mode()).lower()
    bg = _dashboard_cor(self.CARD, modo)
    border = _dashboard_cor(self.BORDER, modo)
    text = _dashboard_cor(self.TEXT, modo)
    accent = _dashboard_cor(self.ACCENT, modo)
    track = "#D7DEE5" if modo != "dark" else "#414A51"

    try:
        hero.configure(fg_color=self.CARD, border_color=self.BORDER)
        canvas = hero._dashboard_ring
        canvas.configure(bg=bg)
        canvas.itemconfigure(hero._dashboard_ring_track, outline=track)
        canvas.itemconfigure(
            hero._dashboard_ring_value,
            outline=accent,
            extent=-359.5 * pct if pct else 0,
        )
        canvas.itemconfigure(
            hero._dashboard_ring_text,
            text=f"{pct:.0%}",
            fill=text,
        )
    except Exception:
        pass

    try:
        status_widget = getattr(self, "status_text", None)
        status = str(status_widget.cget("text")).strip() if status_widget is not None else "Pronto"
        low = status.lower()
        if "process" in low:
            status_bg = ("#E5F1FB", "#183B54")
            status_color = self.INFO
        elif "erro" in low or "atenção" in low:
            status_bg = ("#FDE7E9", "#4B2529")
            status_color = self.ERROR
        elif "parand" in low:
            status_bg = ("#FFF4CE", "#4B3A1A")
            status_color = self.WARNING
        else:
            status_bg = ("#E7F5E7", "#21482A")
            status_color = self.SUCCESS
        hero._dashboard_status.configure(
            fg_color=status_bg,
            text_color=status_color,
            text=status,
        )
    except Exception:
        pass

    try:
        caminho = getattr(self, "caminho", None)
        if caminho:
            fonte = Path(str(caminho)).name
        else:
            total_codigos = 0
            try:
                total_codigos = len(self._extrair_codigos_planilha())
            except Exception:
                pass
            fonte = "Planilha interna" if total_codigos else "Nenhuma selecionada"
        hero._dashboard_source_value.configure(text=fonte, text_color=text)
    except Exception:
        pass

    try:
        pagina_widget = getattr(self, "pagina", None)
        pagina = "—"
        if pagina_widget is not None:
            raw = str(pagina_widget.get()).strip()
            if raw:
                pagina = f"Página {max(1, int(raw))}"
        if not getattr(self, "caminho", None):
            pagina = "Interna" if getattr(self, "_execucao_atual", None) else pagina
        hero._dashboard_page_value.configure(text=pagina, text_color=text)
    except Exception:
        pass

    try:
        codigo = "—"
        card_label = getattr(getattr(self, "codigo_card", None), "value_label", None)
        if card_label is not None:
            codigo = str(card_label.cget("text")).strip() or "—"
        hero._dashboard_code_value.configure(text=codigo, text_color=text)
    except Exception:
        pass

    try:
        sucessos = str(self.sucesso_card.value_label.cget("text"))
        erros = str(self.erro_card.value_label.cget("text"))
        hero._dashboard_success.configure(text=f"{sucessos} executados")
        hero._dashboard_errors.configure(text=f"{erros} não executados")
    except Exception:
        pass


def _dashboard_chipe(self, parent, caption, initial, width):
    chip = ctk.CTkFrame(
        parent,
        fg_color=("#F7F9FB", "#30373D"),
        corner_radius=9,
        border_width=1,
        border_color=self.BORDER,
        width=width,
        height=42,
    )
    chip.pack_propagate(False)
    ctk.CTkLabel(
        chip,
        text=caption.upper(),
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8, "bold"),
    ).pack(anchor="w", padx=10, pady=(5, 0))
    value = ctk.CTkLabel(
        chip,
        text=initial,
        text_color=self.TEXT,
        font=("Segoe UI", 10, "bold"),
        anchor="w",
    )
    value.pack(fill="x", padx=10, pady=(0, 4))
    return chip, value


def _dashboard_criar(self):
    if _dashboard_exists(getattr(self, "_dashboard_hero", None)):
        _dashboard_refrescar(self)
        return

    try:
        scroll = next(
            (
                widget
                for widget in self.app.winfo_children()
                if isinstance(widget, ctk.CTkScrollableFrame)
            ),
            None,
        )
        if scroll is None:
            return

        children = scroll.winfo_children()
        first = children[0] if children else None

        hero = ctk.CTkFrame(
            scroll,
            fg_color=self.CARD,
            corner_radius=12,
            border_width=1,
            border_color=self.BORDER,
            height=128,
        )
        pack_options = {"fill": "x", "pady": (0, 8)}
        if first is not None:
            pack_options["before"] = first
        hero.pack(**pack_options)
        hero.pack_propagate(False)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=(16, 4), pady=14)

        title_row = ctk.CTkFrame(left, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(
            title_row,
            text="PAINEL DE CONTROLE",
            text_color=self.ACCENT,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left")
        hero._dashboard_status = ctk.CTkLabel(
            title_row,
            text="Pronto",
            text_color=self.SUCCESS,
            fg_color=("#E7F5E7", "#21482A"),
            corner_radius=12,
            font=("Segoe UI", 8, "bold"),
            width=88,
            height=22,
        )
        hero._dashboard_status.pack(side="right", padx=(8, 0))

        ctk.CTkLabel(
            left,
            text="Automação Feegow",
            text_color=self.TEXT,
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        ctk.CTkLabel(
            left,
            text="Acompanhe a sessão atual sem perder de vista a próxima ação.",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(0, 8))

        chips = ctk.CTkFrame(left, fg_color="transparent")
        chips.pack(fill="x")
        source_chip, hero._dashboard_source_value = _dashboard_chipe(
            self, chips, "Fonte", "Nenhuma selecionada", 160
        )
        source_chip.pack(side="left", fill="x", expand=True, padx=(0, 6))
        page_chip, hero._dashboard_page_value = _dashboard_chipe(
            self, chips, "Página", "—", 112
        )
        page_chip.pack(side="left", fill="x", expand=True, padx=(0, 6))
        code_chip, hero._dashboard_code_value = _dashboard_chipe(
            self, chips, "Código", "—", 112
        )
        code_chip.pack(side="left", fill="x", expand=True)

        metrics = ctk.CTkFrame(left, fg_color="transparent")
        metrics.pack(fill="x", pady=(5, 0))
        hero._dashboard_success = ctk.CTkLabel(
            metrics, text="0 executados", text_color=self.SUCCESS,
            font=("Segoe UI", 8, "bold")
        )
        hero._dashboard_success.pack(side="left")
        hero._dashboard_errors = ctk.CTkLabel(
            metrics, text="0 não executados", text_color=self.ERROR,
            font=("Segoe UI", 8, "bold")
        )
        hero._dashboard_errors.pack(side="left", padx=(12, 0))

        side = ctk.CTkFrame(hero, fg_color="transparent", width=116)
        side.pack(side="right", fill="y", padx=(4, 16), pady=10)
        side.pack_propagate(False)

        ring = tk.Canvas(
            side,
            width=92,
            height=92,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=_dashboard_cor(self.CARD),
        )
        ring.pack(anchor="center")
        track_id = ring.create_oval(
            6, 6, 86, 86,
            outline="#D7DEE5",
            width=7,
        )
        value_id = ring.create_arc(
            6, 6, 86, 86,
            start=90,
            extent=0,
            style="arc",
            outline=_dashboard_cor(self.ACCENT),
            width=7,
        )
        text_id = ring.create_text(
            46, 46,
            text="0%",
            fill=_dashboard_cor(self.TEXT),
            font=("Segoe UI", 16, "bold"),
        )
        ctk.CTkLabel(
            side,
            text="CONCLUÍDO",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="center", pady=(0, 1))

        hero._dashboard_ring = ring
        hero._dashboard_ring_track = track_id
        hero._dashboard_ring_value = value_id
        hero._dashboard_ring_text = text_id

        self._dashboard_hero = hero
        _dashboard_refrescar(self)
    except Exception:
        self._dashboard_hero = None


def _dashboard_aplicar_metricas(self):
    for card in (
        getattr(self, "sucesso_card", None),
        getattr(self, "erro_card", None),
        getattr(self, "codigo_card", None),
    ):
        try:
            card.configure(corner_radius=12, height=88)
            card.value_label.configure(font=("Segoe UI", 19, "bold"))
        except Exception:
            pass
    try:
        self.percentual_label.configure(font=("Segoe UI", 24, "bold"))
        self.progresso.configure(height=11, corner_radius=5)
    except Exception:
        pass
    _dashboard_refrescar(self)


def install_ui_dashboard_29917(App):
    """Instala o dashboard moderno da Stage 3 sem trocar a lógica funcional."""
    if getattr(App, "_dashboard_ui_29917_aplicado", False):
        return
    App._dashboard_ui_29917_aplicado = True

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _dashboard_criar(self))
            self.app.after_idle(lambda: _dashboard_aplicar_metricas(self))
        except Exception:
            _dashboard_criar(self)
            _dashboard_aplicar_metricas(self)
        return result

    setattr(App, "config_app", config_wrapper)

    original_progress = App._aplicar_progresso

    def progress_wrapper(self, *args, **kwargs):
        result = original_progress(self, *args, **kwargs)
        try:
            porcentagem = args[0] / args[1] if len(args) >= 2 and args[1] else 0
            _dashboard_refrescar(self, porcentagem)
        except Exception:
            pass
        return result

    App._aplicar_progresso = progress_wrapper

    original_status = App._aplicar_status

    def status_wrapper(self, *args, **kwargs):
        result = original_status(self, *args, **kwargs)
        try:
            _dashboard_refrescar(self)
        except Exception:
            pass
        return result

    App._aplicar_status = status_wrapper

    original_theme = App._selecionar_tema

    def theme_wrapper(self, *args, **kwargs):
        result = original_theme(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _dashboard_refrescar(self))
        except Exception:
            _dashboard_refrescar(self)
        return result

    setattr(App, "_selecionar_tema", theme_wrapper)




# Planilha e Histórico — Stage 5.
SM_AUTOLAB_PLANILHA_29919 = "SM-AUTOLAB-PLANILHA-HISTORICO-29919"


def _planilha_stage5_exists(widget):
    try:
        return widget is not None and widget.winfo_exists()
    except Exception:
        return False


def _planilha_stage5_repaint_row_header(self):
    try:
        if _planilha_stage5_exists(getattr(self, "_planilha_row_header", None)):
            self._planilha_desenhar_cabecalho_linhas()
    except Exception:
        pass


def install_ui_planilha_29919(App):
    """Integra os acabamentos e otimizações da Etapa 5."""
    if getattr(App, "_planilha_ui_29919_aplicado", False):
        return
    App._planilha_ui_29919_aplicado = True

    original_open = App.abrir_planilha

    def open_wrapper(self, *args, **kwargs):
        result = original_open(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _planilha_stage5_repaint_row_header(self))
        except Exception:
            _planilha_stage5_repaint_row_header(self)
        return result

    setattr(App, "abrir_planilha", open_wrapper)

    original_theme = App._selecionar_tema

    def theme_wrapper(self, *args, **kwargs):
        result = original_theme(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _planilha_stage5_repaint_row_header(self))
        except Exception:
            _planilha_stage5_repaint_row_header(self)
        return result

    setattr(App, "_selecionar_tema", theme_wrapper)

# Microinterações discretas — Stage 4.
SM_AUTOLAB_MICRO_29918 = "SM-AUTOLAB-MICRO-29918"


def _micro_widget_exists(widget):
    try:
        return widget is not None and widget.winfo_exists()
    except Exception:
        return False


def _micro_pulse_border(widget, accent, duration_ms=180, pulse_width=2):
    if not _micro_widget_exists(widget):
        return

    try:
        if not hasattr(widget, "_micro_base_border_color"):
            widget._micro_base_border_color = widget.cget("border_color")
            widget._micro_base_border_width = int(widget.cget("border_width") or 0)

        base_color = widget._micro_base_border_color
        base_width = int(widget._micro_base_border_width)

        old_job = getattr(widget, "_micro_pulse_job", None)
        if old_job is not None:
            try:
                widget.after_cancel(old_job)
            except Exception:
                pass

        widget.configure(
            border_width=max(base_width, int(pulse_width)),
            border_color=accent,
        )

        def restore():
            try:
                if widget.winfo_exists():
                    widget.configure(
                        border_width=base_width,
                        border_color=base_color,
                    )
            except Exception:
                pass
            try:
                widget._micro_pulse_job = None
            except Exception:
                pass

        widget._micro_pulse_job = widget.after(max(1, int(duration_ms)), restore)
    except Exception:
        pass


def _micro_bind_button(app, widget):
    if not isinstance(widget, ctk.CTkButton):
        return
    try:
        _fluent_bind_button_feedback(
            app,
            widget,
            int(widget.cget("border_width") or 0),
        )
    except Exception:
        pass


def _micro_bind_tree_buttons(app, root):
    if not _micro_widget_exists(root):
        return
    for widget in _walk_children(root):
        try:
            _micro_bind_button(app, widget)
        except Exception:
            continue


def _micro_bind_hover_region(widget, accent):
    if not _micro_widget_exists(widget):
        return
    if getattr(widget, "_micro_hover_bound", False):
        return

    try:
        widget._micro_hover_bound = True
        widget._micro_hover_accent = accent
        widget._micro_base_border_color = widget.cget("border_color")
        widget._micro_base_border_width = int(widget.cget("border_width") or 0)

        def inside(current):
            if current is None:
                return False
            try:
                return _widget_inside(current, widget)
            except Exception:
                return False

        def enter(_event=None):
            try:
                if not widget.winfo_exists():
                    return
                widget.configure(
                    border_width=max(1, int(widget._micro_base_border_width)),
                    border_color=widget._micro_hover_accent,
                )
            except Exception:
                pass

        def leave(_event=None):
            def restore_if_outside():
                try:
                    if not widget.winfo_exists():
                        return
                    current = widget.winfo_containing(
                        widget.winfo_pointerx(),
                        widget.winfo_pointery(),
                    )
                    if not inside(current):
                        widget.configure(
                            border_width=int(widget._micro_base_border_width),
                            border_color=widget._micro_base_border_color,
                        )
                except Exception:
                    pass

            try:
                widget.after_idle(restore_if_outside)
            except Exception:
                restore_if_outside()

        for child in _walk_children(widget):
            try:
                child.bind("<Enter>", enter, add="+")
                child.bind("<Leave>", leave, add="+")
            except Exception:
                pass
    except Exception:
        pass


def _micro_confirm_error_button(self, button, codigo):
    if not _micro_widget_exists(button):
        return
    try:
        original_text = str(button.cget("text"))
        old_job = getattr(button, "_micro_copy_job", None)
        if old_job is not None:
            try:
                button.after_cancel(old_job)
            except Exception:
                pass

        button.configure(
            text="✓ Copiado",
            text_color=self.SUCCESS,
        )

        def restore():
            try:
                if button.winfo_exists():
                    button.configure(
                        text=original_text,
                        text_color=self.ERROR,
                    )
            except Exception:
                pass
            try:
                button._micro_copy_job = None
            except Exception:
                pass

        button._micro_copy_job = button.after(700, restore)
    except Exception:
        pass


def _micro_dashboard_complete(self):
    hero = getattr(self, "_dashboard_hero", None)
    if not _micro_widget_exists(hero):
        return

    try:
        canvas = hero._dashboard_ring
        canvas.itemconfigure(
            hero._dashboard_ring_value,
            outline=self.SUCCESS,
        )
        old_job = getattr(self, "_micro_dashboard_complete_job", None)
        if old_job is not None:
            try:
                self.app.after_cancel(old_job)
            except Exception:
                pass

        def restore():
            try:
                if _micro_widget_exists(hero):
                    canvas.itemconfigure(
                        hero._dashboard_ring_value,
                        outline=_dashboard_cor(self.ACCENT),
                    )
            except Exception:
                pass
            self._micro_dashboard_complete_job = None

        self._micro_dashboard_complete_job = self.app.after(420, restore)
    except Exception:
        pass


def _micro_bind_dashboard_regions(self):
    for attr, accent in (
        ("sucesso_card", self.SUCCESS),
        ("erro_card", self.ERROR),
        ("codigo_card", self.INFO),
    ):
        card = getattr(self, attr, None)
        if card is not None:
            _micro_bind_hover_region(card, self.ACCENT_HOVER)


def install_ui_micro_29918(App):
    """Instala feedbacks transitórios e não invasivos, sem tocar na lógica da automação."""
    if getattr(App, "_micro_ui_29918_aplicado", False):
        return
    App._micro_ui_29918_aplicado = True

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self._micro_ui_29918_ready = True
            self.app.after_idle(lambda: _micro_bind_tree_buttons(self.app, self.app))
            self.app.after_idle(lambda: _micro_bind_dashboard_regions(self))
        except Exception:
            self._micro_ui_29918_ready = True
            _micro_bind_tree_buttons(self.app, self.app)
            _micro_bind_dashboard_regions(self)
        return result

    setattr(App, "config_app", config_wrapper)

    original_progress = App._aplicar_progresso

    def progress_wrapper(self, *args, **kwargs):
        before = {}
        for attr in ("sucesso_card", "erro_card", "codigo_card"):
            try:
                card = getattr(self, attr)
                before[attr] = str(card.value_label.cget("text"))
            except Exception:
                before[attr] = None

        result = original_progress(self, *args, **kwargs)

        try:
            accents = {
                "sucesso_card": self.SUCCESS,
                "erro_card": self.ERROR,
                "codigo_card": self.INFO,
            }
            for attr, accent in accents.items():
                card = getattr(self, attr, None)
                if card is None:
                    continue
                try:
                    after = str(card.value_label.cget("text"))
                except Exception:
                    after = None
                if before.get(attr) != after:
                    _micro_pulse_border(card, accent, duration_ms=180, pulse_width=2)

            try:
                total = int(args[1]) if len(args) >= 2 else 0
                processados = int(args[0]) if args else 0
                if total > 0 and processados >= total:
                    _micro_dashboard_complete(self)
            except Exception:
                pass
        except Exception:
            pass
        return result

    App._aplicar_progresso = progress_wrapper

    original_status = App._aplicar_status

    def status_wrapper(self, *args, **kwargs):
        try:
            previous = str(self.status_text.cget("text"))
        except Exception:
            previous = None

        result = original_status(self, *args, **kwargs)

        try:
            current = str(self.status_text.cget("text"))
        except Exception:
            current = None

        if getattr(self, "_micro_ui_29918_ready", False) and previous != current:
            _micro_pulse_border(self.status_pill, self.ACCENT_HOVER, duration_ms=150, pulse_width=2)
        return result

    App._aplicar_status = status_wrapper

    original_select_tab = App._selecionar_aba

    def select_tab_wrapper(self, nome, *args, **kwargs):
        result = original_select_tab(self, nome, *args, **kwargs)
        try:
            if getattr(self, "_micro_ui_29918_ready", False):
                button = getattr(self, "tab_buttons", {}).get(nome)
                if button is not None:
                    _micro_pulse_border(
                        button,
                        self.ACCENT_HOVER,
                        duration_ms=130,
                        pulse_width=2,
                    )
        except Exception:
            pass
        return result

    App._selecionar_aba = select_tab_wrapper

    original_create_error = App._criar_botao_erro

    def create_error_wrapper(self, codigo, parent=None):
        button = original_create_error(self, codigo, parent=parent)
        try:
            _micro_bind_button(self.app, button)

            def copy_with_feedback(code=str(codigo), current_button=button):
                self._copiar_codigo(code)
                _micro_confirm_error_button(self, current_button, code)

            button.configure(command=copy_with_feedback)
        except Exception:
            pass
        return button

    App._criar_botao_erro = create_error_wrapper

    original_show_config = App._mostrar_menu_configuracoes

    def show_config_wrapper(self, *args, **kwargs):
        result = original_show_config(self, *args, **kwargs)
        try:
            _micro_bind_tree_buttons(self.app, getattr(self, "_menu_config", None))
        except Exception:
            pass
        return result

    App._mostrar_menu_configuracoes = show_config_wrapper

    original_show_appearance = App._mostrar_menu_aparencia

    def show_appearance_wrapper(self, *args, **kwargs):
        result = original_show_appearance(self, *args, **kwargs)
        try:
            _micro_bind_tree_buttons(self.app, getattr(self, "_menu_aparencia", None))
        except Exception:
            pass
        return result

    App._mostrar_menu_aparencia = show_appearance_wrapper

    original_open_files_history = App.abrir_historico_planilha

    def open_files_history_wrapper(self, *args, **kwargs):
        result = original_open_files_history(self, *args, **kwargs)
        try:
            _micro_bind_tree_buttons(self.app, getattr(self, "_planilha_historico_window", None))
        except Exception:
            pass
        return result

    App.abrir_historico_planilha = open_files_history_wrapper


if __name__ == "__main__":
    aplicar_patch_ui(App)
    _corrigir_historico_ilimitado()
    install_ui_29912(App)
    install_ui_fluent_29916(App)
    install_ui_dashboard_29917(App)
    install_ui_micro_29918(App)
    install_ui_planilha_29919(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
