from __future__ import annotations

import sys
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageTk

from interface import App
from patch import aplicar_patch_ui
from ui_fixes_29912 import install as install_ui_29912


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
    install_ui_29912(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
