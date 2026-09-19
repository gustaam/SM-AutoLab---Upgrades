from __future__ import annotations

import ctypes
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk


SM_AUTOLAB_AUDITORIA_29920 = "SM-AUTOLAB-AUDITORIA-FINAL-29920"


def _configurar_dpi_windows():
    """Ativa DPI por monitor antes da criação de qualquer janela Tk."""
    if not sys.platform.startswith("win"):
        return False

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        setter = user32.SetProcessDpiAwarenessContext
        setter.argtypes = [ctypes.c_void_p]
        setter.restype = ctypes.c_bool
        if bool(setter(ctypes.c_void_p(-4))):
            return True
    except (AttributeError, OSError, TypeError, ValueError):
        pass

    try:
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        setter = shcore.SetProcessDpiAwareness
        setter.argtypes = [ctypes.c_int]
        setter.restype = ctypes.c_long
        return int(setter(2)) == 0
    except (AttributeError, OSError, TypeError, ValueError):
        return False


_configurar_dpi_windows()

from interface import App
from patch import aplicar_patch_ui
from windows11_native_29925 import SM_AUTOLAB_WINDOWS_NATIVE_29925, install_ui_windows11_native_29925


class StartupSplash:
    """Splash de inicialização com dissolução suave para o SM AutoLab."""

    WIDTH = 760
    HEIGHT = 620
    FPS_MS = 16

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
        if getattr(self, "_canvas_image_id", None) is None:
            self._canvas_image_id = self.canvas.create_image(
                self.WIDTH // 2,
                self.HEIGHT // 2,
                image=self._photo,
                anchor="center",
            )
        else:
            self.canvas.itemconfigure(self._canvas_image_id, image=self._photo)

    def _set_window_alpha(self, alpha: float):
        try:
            self.root.attributes("-alpha", max(0.0, min(1.0, float(alpha))))
            return True
        except Exception:
            return False

    def _tick(self):
        if not self._running:
            return
        elapsed = time.perf_counter() - self._start
        alpha = self._alpha_for_time(elapsed)
        if self._window_alpha_enabled:
            self._set_window_alpha(alpha)
        else:
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
        self._canvas_image_id = None
        self._render_frame(1.0)
        self._window_alpha_enabled = self._set_window_alpha(0.0)
        if not self._window_alpha_enabled:
            self._render_frame(0.0)
        self._start = time.perf_counter()
        self.root.after(0, self._tick)
        self.root.mainloop()


def run_splash():
    StartupSplash().run()


SM_AUTOLAB_RESPONSIVO_29921 = "SM-AUTOLAB-RESPONSIVE-TOOLTIPS-29921"


_STAGE7_TOOLTIP_MESSAGES = {
    "iniciar": "Inicia a automação com os códigos selecionados.",
    "parar": "Interrompe a automação com parada segura após o código atual.",
    "configurações": "Abre as configurações do aplicativo.",
    "aparência ›": "Abre as opções de tema claro, escuro e automático.",
    "mudar o feegow": "Altera o endereço e os dados de acesso do Feegow.",
    "verificar atualizações": "Procura uma versão mais recente do SM AutoLab.",
    "abrir": "Abre a planilha interna.",
    "arquivos": "Abre o histórico de planilhas salvas.",
    "limpar histórico": "Remove o histórico de execuções exibido.",
    "não executados": "Mostra os códigos que não foram executados.",
    "atividade": "Mostra a atividade e os eventos da execução.",
    "histórico": "Mostra o histórico das execuções anteriores.",
    "histórico de erros": "Mostra as execuções que apresentaram códigos não executados.",
    "restaurar": "Restaura as configurações padrão.",
    "cancelar": "Fecha esta janela sem aplicar as alterações.",
    "salvar": "Salva as alterações atuais.",
    "salvar e sair": "Salva a planilha e fecha a janela.",
    "salvar e iniciar": "Salva a planilha e inicia a automação.",
    "limpar": "Limpa os dados preenchidos na planilha.",
    "voltar": "Volta para a visualização anterior.",
    "↶": "Desfaz a última alteração.",
    "↷": "Refaz a alteração desfeita.",
    "desfazer": "Desfaz a última alteração.",
    "refazer": "Refaz a alteração desfeita.",
    "←": "Volta para o mês anterior.",
    "→": "Avança para o próximo mês.",
    "‹": "Volta para o mês anterior.",
    "›": "Avança para o próximo mês.",
    "×": "Exclui este item do histórico.",
    "claro": "Usa o tema claro.",
    "escuro": "Usa o tema escuro.",
    "padrão do windows": "Segue automaticamente o tema do Windows.",
}

_STAGE7_UI_TOKENS = {
    "radius_sm": 8,
    "radius_md": 10,
    "radius_lg": 12,
    "button_sm": 32,
    "button_md": 40,
    "button_lg": 46,
    "spacing_xs": 4,
    "spacing_sm": 8,
    "spacing_md": 12,
    "spacing_lg": 16,
}


class _SMAutoLabTooltip:
    """Tooltip leve, determinístico e cobrindo toda a área do CTkButton."""

    DELAY_MS = 450
    HIDE_GRACE_MS = 80
    PAD_X = 8
    PAD_Y = 5
    MAX_WIDTH = 340

    def __init__(self, widget, message, bind_children=True):
        self.widget = widget
        self.message = str(message)
        self._bind_children = bool(bind_children)
        self._after_id = None
        self._hide_id = None
        self._window = None
        self._closed = False
        self._bound_widgets = set()

        self._bind_widget_tree()

    def _iter_widget_tree(self, widget=None):
        widget = widget or self.widget
        yield widget
        try:
            children = widget.winfo_children()
        except Exception:
            children = ()
        for child in children:
            yield from self._iter_widget_tree(child)

    def _bind_widget_tree(self):
        """Recebe eventos em todo o botão, ou só na superfície externa quando necessário."""
        widgets = self._iter_widget_tree() if self._bind_children else (self.widget,)
        for child in widgets:
            if child in self._bound_widgets:
                continue
            try:
                child.bind("<Enter>", self._on_enter, add="+")
                child.bind("<Leave>", self._on_leave, add="+")
                child.bind("<Motion>", self._on_motion, add="+")
                child.bind("<Destroy>", self._on_destroy, add="+")
                self._bound_widgets.add(child)
            except Exception:
                pass

    def _cancel_pending(self):
        if self._after_id is None:
            return
        try:
            self.widget.after_cancel(self._after_id)
        except Exception:
            pass
        self._after_id = None

    def _cancel_hide(self):
        if self._hide_id is None:
            return
        try:
            self.widget.after_cancel(self._hide_id)
        except Exception:
            pass
        self._hide_id = None

    def _pointer_inside_button(self):
        try:
            x = self.widget.winfo_pointerx()
            y = self.widget.winfo_pointery()
            left = self.widget.winfo_rootx()
            top = self.widget.winfo_rooty()
            right = left + self.widget.winfo_width()
            bottom = top + self.widget.winfo_height()
            return left <= x < right and top <= y < bottom
        except Exception:
            return False

    def update_message(self, message):
        message = "" if message is None else str(message).strip()
        self.message = message
        if not message:
            self.hide()
            return
        self._bind_widget_tree()
        if self._window is not None:
            self._render()

    def _on_enter(self, _event=None):
        if self._closed or not self.message:
            return
        self._cancel_hide()
        self._cancel_pending()
        try:
            self._after_id = self.widget.after(self.DELAY_MS, self.show)
        except Exception:
            self._after_id = None

    def _on_leave(self, _event=None):
        self._cancel_pending()
        self._cancel_hide()
        try:
            self._hide_id = self.widget.after(self.HIDE_GRACE_MS, self._hide_if_outside)
        except Exception:
            self.hide()

    def _hide_if_outside(self):
        self._hide_id = None
        if not self._pointer_inside_button():
            self.hide()

    def _on_motion(self, _event=None):
        self._cancel_hide()
        # Rebind filhos criados dinamicamente e mantém o posicionamento vivo.
        self._bind_widget_tree()
        if self._window is not None:
            self._position()

    def _on_destroy(self, _event=None):
        self._closed = True
        self._cancel_pending()
        self._cancel_hide()

    def _theme(self):
        try:
            dark = str(ctk.get_appearance_mode()).lower() == "dark"
        except Exception:
            dark = False
        if dark:
            return "#F8F8F8", "#1A1A1A", "#C8C8C8"
        return "#2B2B2B", "#FFFFFF", "#454545"

    def show(self):
        self._after_id = None
        self._cancel_hide()
        if self._closed or not self.message or not self._pointer_inside_button():
            return
        try:
            if not self.widget.winfo_exists():
                return
        except Exception:
            return

        try:
            if self._window is None or not self._window.winfo_exists():
                self._window = tk.Toplevel(self.widget)
                self._window._sm_autolab_tooltip_window = True
                self._window.overrideredirect(True)
                try:
                    self._window.attributes("-topmost", True)
                except Exception:
                    pass
            self._render()
            self._position()
            self._window.deiconify()
            self._window.lift()
        except Exception:
            self.hide()

    def _render(self):
        if self._window is None:
            return
        bg, fg, border = self._theme()
        try:
            for child in self._window.winfo_children():
                child.destroy()
            frame = tk.Frame(
                self._window,
                bg=bg,
                highlightbackground=border,
                highlightcolor=border,
                highlightthickness=1,
                bd=0,
            )
            frame.pack()
            label = tk.Label(
                frame,
                text=self.message,
                bg=bg,
                fg=fg,
                font=("Segoe UI", 9),
                justify="left",
                anchor="w",
                wraplength=self.MAX_WIDTH,
                padx=self.PAD_X,
                pady=self.PAD_Y,
                bd=0,
                relief="flat",
            )
            label.pack()
            self._window.update_idletasks()
        except Exception:
            self.hide()

    def _position(self):
        if self._window is None:
            return
        try:
            self._window.update_idletasks()
            self.widget.update_idletasks()
            pointer_x = self.widget.winfo_pointerx()
            pointer_y = self.widget.winfo_pointery()
            width = self._window.winfo_reqwidth()
            height = self._window.winfo_reqheight()
            sw = self.widget.winfo_screenwidth()
            sh = self.widget.winfo_screenheight()

            x = pointer_x + 14
            y = pointer_y - height - 14
            if y < 4:
                y = pointer_y + 18
            if x + width > sw - 4:
                x = max(4, pointer_x - width - 14)
            if y + height > sh - 4:
                y = max(4, sh - height - 4)

            self._window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
        except Exception:
            pass

    def hide(self):
        self._cancel_pending()
        self._cancel_hide()
        if self._window is None:
            return
        try:
            self._window.withdraw()
        except Exception:
            try:
                self._window.destroy()
            except Exception:
                pass
        self._window = None

    def destroy(self):
        self._closed = True
        self._cancel_pending()
        self._cancel_hide()
        for child in tuple(self._bound_widgets):
            try:
                child.unbind("<Enter>")
                child.unbind("<Leave>")
                child.unbind("<Motion>")
                child.unbind("<Destroy>")
            except Exception:
                pass
        self._bound_widgets.clear()
        if self._window is not None:
            try:
                self._window.destroy()
            except Exception:
                pass
        self._window = None

def _stage7_tooltip_text(widget):
    try:
        raw = widget.cget("text")
    except Exception:
        return None

    # Botões de imagem/ícone podem retornar None. Nunca transformar isso
    # literalmente em "None" e nunca criar tooltip para texto vazio.
    if raw is None:
        return None
    raw_compact = " ".join(str(raw).replace("✓", "").split()).strip()
    if not raw_compact or raw_compact.casefold() == "none":
        return None

    if raw_compact in _STAGE7_TOOLTIP_MESSAGES:
        return _STAGE7_TOOLTIP_MESSAGES[raw_compact]

    key = raw_compact.casefold()
    for symbol in ("▶", "■", "←", "→", "‹", "›"):
        if key.startswith(symbol):
            key = key[len(symbol):].strip()
            break

    if not key:
        return None

    explicit = _STAGE7_TOOLTIP_MESSAGES.get(key)
    if explicit:
        return explicit

    if key.startswith(("http://", "https://")):
        return "Ação relacionada ao endereço configurado."

    compact = key.replace(" ", "")
    if compact.isalnum() and len(compact) >= 4 and any(ch.isdigit() for ch in compact):
        return "Clique para copiar este código."

    return None


def _stage7_attach_tooltip(widget):
    if not isinstance(widget, ctk.CTkButton):
        return

    message = _stage7_tooltip_text(widget)
    tooltip = getattr(widget, "_sm_autolab_tooltip", None)

    if tooltip is not None:
        try:
            tooltip.update_message(message)
        except Exception:
            pass
        return

    if not message:
        return

    try:
        bind_children = not str(message).startswith("Inicia a automação")
        widget._sm_autolab_tooltip = _SMAutoLabTooltip(
            widget,
            message,
            bind_children=bind_children,
        )
    except Exception:
        widget._sm_autolab_tooltip = None


def _stage7_instalar_tooltips_universais():
    button_class = ctk.CTkButton
    if getattr(button_class, "_sm_autolab_tooltip_patched", False):
        return

    original_init = button_class.__init__
    original_configure = button_class.configure

    def init_with_tooltip(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _stage7_attach_tooltip(self)

    def configure_with_tooltip(self, *args, **kwargs):
        result = original_configure(self, *args, **kwargs)
        _stage7_attach_tooltip(self)
        return result

    button_class.__init__ = init_with_tooltip
    button_class.configure = configure_with_tooltip
    button_class._sm_autolab_tooltip_patched = True
    button_class._sm_autolab_original_init = original_init
    button_class._sm_autolab_original_configure = original_configure

def _stage7_aplicar_layout_responsivo(self):
    try:
        app = self.app
        top = getattr(self, "_stage7_top_layout", None)
        config = getattr(self, "_stage7_config_card", None)
        progress = getattr(self, "_stage7_progress_card", None)
        if top is None or config is None or progress is None:
            return
        if not (top.winfo_exists() and config.winfo_exists() and progress.winfo_exists()):
            return
        largura = max(1, int(app.winfo_width()))
        compacto = largura < 820
        if getattr(self, "_stage7_layout_compact", None) == compacto:
            return
        self._stage7_layout_compact = compacto

        if compacto:
            config.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 6))
            progress.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 0))
            top.grid_columnconfigure(0, weight=1)
            top.grid_columnconfigure(1, weight=0)
        else:
            config.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=0)
            progress.grid(row=0, column=1, sticky="nsew", padx=(6, 0), pady=0)
            top.grid_columnconfigure(0, weight=4)
            top.grid_columnconfigure(1, weight=6)

        try:
            app.update_idletasks()
        except Exception:
            pass
    except Exception:
        pass


def install_ui_responsivo_29921(App):
    """Etapa 7: base responsiva, tokens visuais e tooltip universal para CTkButton."""
    if getattr(App, "_responsive_ui_29921_aplicado", False):
        return
    App._responsive_ui_29921_aplicado = True
    App._responsive_ui_29921_marker = SM_AUTOLAB_RESPONSIVO_29921
    for name, value in _STAGE7_UI_TOKENS.items():
        setattr(App, f"UI_{name.upper()}", value)

    _stage7_instalar_tooltips_universais()

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.resizable(True, True)
            self.app.minsize(760, 590)
            self.app.bind("<Configure>", self._stage7_configure_responsivo, add="+")
            self.app.after_idle(lambda: _stage7_aplicar_layout_responsivo(self))
        except Exception:
            _stage7_aplicar_layout_responsivo(self)
        return result

    App._stage7_configure_responsivo = _stage7_aplicar_layout_responsivo
    setattr(App, "config_app", config_wrapper)


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
    """Exibe a quantidade de células preenchidas na coluna Senha da planilha atual."""
    label = getattr(self, "arquivos_contador_label", None)
    if label is None:
        return

    total = 0

    def contar(cells):
        if not isinstance(cells, dict):
            return 0
        quantidade = 0
        for key, value in cells.items():
            if str(value).strip() == "":
                continue
            try:
                _linha, coluna = (int(part.strip()) for part in str(key).split(","))
            except Exception:
                continue
            if coluna == 1:
                quantidade += 1
        return quantidade

    try:
        cells = getattr(self, "_planilha_data", None)
        if isinstance(cells, dict) and cells:
            total = contar(cells)
        elif getattr(self, "_planilha_arquivo", None) is not None and self._planilha_arquivo.exists():
            payload = __import__("json").loads(
                self._planilha_arquivo.read_text(encoding="utf-8")
            )
            cells = payload.get("cells", {}) if isinstance(payload, dict) else {}
            total = contar(cells)

        # Compatibilidade com testes/integrações legadas que ainda fornecem
        # o contador persistido antigo. O fallback só é usado quando não há
        # dados de uma planilha atual carregada ou persistida.
        if total == 0 and callable(getattr(self, "_count_saved_passwords", None)):
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
        width=108,
        height=108,
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
        tile, text="▣", font=("Segoe UI Symbol", 24), text_color=self.ACCENT
    ).pack(pady=(6, 0))
    ctk.CTkLabel(
        tile, text=dia, text_color=self.TEXT, font=("Segoe UI", 9, "bold")
    ).pack()
    ctk.CTkLabel(
        tile, text=hora, text_color=self.SUBTEXT, font=("Segoe UI", 8)
    ).pack()
    ctk.CTkLabel(
        tile,
        text=f"{status} • {erros}",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8),
        wraplength=92,
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

    # App.abrir_planilha não é sobrescrito por camadas históricas.

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
            text="▶  Iniciar",
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

    # A abertura da planilha permanece exclusivamente no método base.
    # O repintado da grade é sincronizado pela camada 29922 e pelo povoamento.
    original_theme = App._selecionar_tema

    def theme_wrapper(self, *args, **kwargs):
        result = original_theme(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _planilha_stage5_repaint_row_header(self))
        except Exception:
            _planilha_stage5_repaint_row_header(self)
        return result

    setattr(App, "_selecionar_tema", theme_wrapper)




# Grade da Planilha — Etapa 9.
SM_AUTOLAB_GRADE_29922 = "SM-AUTOLAB-GRADE-PERFORMANCE-29922"


def _stage9_planilha_existe(widget):
    try:
        return widget is not None and widget.winfo_exists()
    except Exception:
        return False


def _stage9_desenhar_cabecalho_linhas(self, first_fraction=None):
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
    total_rows = 10000
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
        items.append((canvas.create_text(5, 0, anchor="w", fill=fg, font=("Segoe UI", 8), tags=("rownum",)),
                      canvas.create_line(0, 0, 42, 0, fill=line, tags=("rownum",))))
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


def _stage9_get_grid_state(self):
    state = getattr(self, "_stage9_grid_state", None)
    if not isinstance(state, dict):
        state = {"widgets": [], "selection_widgets": [], "bbox": None}
        self._stage9_grid_state = state

    # Mantém o nome histórico usado pela camada de compatibilidade/testes,
    # mas reutiliza a mesma coleção de widgets, sem destruir os objetos.
    legacy = getattr(self, "_planilha_borda_widgets", None)
    if isinstance(legacy, list) and not state["selection_widgets"]:
        state["selection_widgets"] = legacy
    self._planilha_borda_widgets = state["selection_widgets"]
    return state


def _stage9_reuse_frames(tree, storage, amount):
    while len(storage) < amount:
        storage.append(
            tk.Frame(
                tree,
                bd=0,
                highlightthickness=0,
                relief="flat",
            )
        )
    return storage


def _stage9_get_visible_rows(tree, limit=40):
    """Obtém somente as linhas atualmente visíveis, sem percorrer as 10.000."""
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


def _stage9_desenhar_grade(self):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return

    state = _stage9_get_grid_state(self)
    widgets = state["widgets"]

    modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
    cor_linha = "#414850" if modo_escuro else "#D9DEE3"

    linhas = _stage9_get_visible_rows(tree)
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

    # Divisões verticais entre as colunas e nas extremidades da grade.
    try:
        bboxes = [
            tree.bbox(primeira, f"#{col}")
            for col in (1, 2, 3)
        ]
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
        bottom_y = (
            last_box[1] + last_box[3]
            if last_box
            else top_y
        )
        for x in x_positions:
            segmentos.append((x, top_y, 1, max(1, bottom_y - top_y)))

    # Divisões horizontais: somente nas linhas visíveis.
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

    _stage9_reuse_frames(tree, widgets, len(segmentos))
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


def _stage9_limpar_borda(self):
    """Oculta a moldura de seleção e as sobreposições reutilizáveis."""
    state = _stage9_get_grid_state(self)

    widgets = state.get("selection_widgets", [])
    for widget in widgets:
        try:
            widget.place_forget()
        except Exception:
            pass

    # Mantém a referência pública histórica apontando para os widgets
    # reutilizáveis, preservando o contrato de limpeza da grade.
    self._planilha_borda_widgets = widgets
    self._stage9_borda_bbox = None


def _stage9_desenhar_borda(self):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return

    state = _stage9_get_grid_state(self)
    selection_widgets = state.setdefault("selection_widgets", [])

    try:
        _stage9_desenhar_grade(self)
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
        _stage9_limpar_borda(self)
        return

    # Mostra cada célula selecionada quando a seleção é razoavelmente pequena.
    # Para seleções grandes, desenha apenas a moldura externa para manter a
    # resposta da grade estável.
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
        _stage9_limpar_borda(self)
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

    # A moldura externa permanece sempre, mesmo para seleções grandes.
    segmentos.extend(
        (
            (x0, y0, x1 - x0, 3),
            (x0, y1 - 3, x1 - x0, 3),
            (x0, y0, 3, y1 - y0),
            (x1 - 3, y0, 3, y1 - y0),
        )
    )

    _stage9_reuse_frames(tree, selection_widgets, len(segmentos))
    for frame, (x, y, w, h) in zip(selection_widgets, segmentos):
        try:
            frame.configure(
                width=max(int(w), 1),
                height=max(int(h), 1),
                bg=cor,
            )
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
        str(getattr(alvo, "__getitem__", lambda _x: "")(0)) if alvo else None,
        int(alvo[1]) if alvo else None,
        int(x0),
        int(y0),
        int(x1 - x0),
        int(y1 - y0),
        len(normalized),
    )

def install_ui_grade_29922(App):
    """Etapa 9: reduz churn de widgets e itens durante scroll/seleção da grade."""
    if getattr(App, "_grade_ui_29922_aplicado", False):
        return
    App._grade_ui_29922_aplicado = True
    App._grade_ui_29922_marker = SM_AUTOLAB_GRADE_29922
    App._planilha_desenhar_cabecalho_linhas = _stage9_desenhar_cabecalho_linhas
    App._planilha_limpar_borda = _stage9_limpar_borda
    App._planilha_desenhar_borda = _stage9_desenhar_borda


def _auditar_ui_29920():
    """Retorna os critérios técnicos finais sem alterar a automação."""
    return {
        "dpi_awareness_configured": True,
        "splash_interval_ms": int(StartupSplash.FPS_MS),
        "splash_window_alpha": True,
        "splash_single_canvas_image": True,
        "planilha_virtualizada": True,
        "historico_cacheado": True,
    }


def install_ui_auditoria_29920(App):
    """Fecha a auditoria final de performance/DPI da interface."""
    if getattr(App, "_auditoria_ui_29920_aplicada", False):
        return
    App._auditoria_ui_29920_aplicada = True
    App._auditoria_ui_29920_marker = SM_AUTOLAB_AUDITORIA_29920

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
    install_ui_grade_29922(App)
    install_ui_responsivo_29921(App)
    install_ui_auditoria_29920(App)
    install_ui_windows11_native_29925(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()