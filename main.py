# Bootstrap da aplicação: inicialização, splash, DPI e integração da interface.
from __future__ import annotations

import ctypes
import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk


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

from interface import App, SM_AUTOLAB_GRADE_VIRTUAL


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



SM_AUTOLAB_CANONICAL_UI = "SM-AUTOLAB-CANONICAL-UI-29929"


_REQUIRED_BASE_METHODS = (
    "abrir_planilha",
    "abrir_historico_planilha",
    "_renderizar_calendario_arquivos",
    "_mostrar_planilhas_do_dia",
    "_contar_codigos_mes",
    "_selecionar_tema",
    "_mostrar_menu_configuracoes",
    "_mostrar_menu_aparencia",
    "_planilha_clicar_celula",
    "_planilha_editar_iid",
    "iniciar_thread",
)


def _validar_base_aplicacao():
    """Valida que a aplicação expõe somente a entrada funcional canônica."""
    faltantes = [nome for nome in _REQUIRED_BASE_METHODS if not hasattr(App, nome)]
    if faltantes:
        raise RuntimeError(
            "A base do SM AutoLab esta incompleta. Componentes ausentes: "
            + ", ".join(faltantes)
        )

    if not hasattr(App, "_ui_runtime_instalado"):
        raise RuntimeError("A entrada canônica da UI não foi inicializada.")

    if getattr(App, "_ui_runtime_mode", None) != "canonical":
        raise RuntimeError("A UI não está usando o runtime canônico.")


def install_ui(App):
    """Inicializa somente o runtime canônico; não injeta wrappers ou eventos globais."""
    if getattr(App, "_ui_runtime_instalado", False):
        return
    App._ui_runtime_instalado = True
    App._ui_runtime_mode = "canonical"
    App._ui_runtime_marker = SM_AUTOLAB_CANONICAL_UI_29929


if __name__ == "__main__":
    install_ui(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
