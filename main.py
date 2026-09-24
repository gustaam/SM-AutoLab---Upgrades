# Ponto de entrada do SM AutoLab: inicialização, splash e preparação da interface desktop.
from __future__ import annotations
import ctypes
import os
import shutil
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
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
from interface import APP_VERSION, find_update
class StartupSplash:
    """Splash de inicialização com dissolução suave para o SM AutoLab."""
    WIDTH = 760
    HEIGHT = 620
    FPS_MS = 16
    def __init__(self, ready_event=None):
        self._ready_event = ready_event
        self._fadeout_started = None
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
        if t < 0.55:
            return self._smoothstep(t / 0.55)
        return 1.0
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
        ready = self._ready_event is None or self._ready_event.is_set()
        if ready and elapsed >= 0.90 and self._fadeout_started is None:
            self._fadeout_started = time.perf_counter()
        if self._fadeout_started is not None:
            fade_elapsed = time.perf_counter() - self._fadeout_started
            alpha = 1.0 - self._smoothstep(min(1.0, fade_elapsed / 0.28))
        else:
            fade_elapsed = 0.0
            alpha = self._alpha_for_time(elapsed)
        if self._window_alpha_enabled:
            self._set_window_alpha(alpha)
        else:
            self._render_frame(alpha)
        if self._fadeout_started is not None and fade_elapsed >= 0.28:
            self._running = False
            self.root.after(10, self.close)
            return
        if elapsed >= 2.80:
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
def _sinalizar_inicializacao_atualizacao_sucesso():
    """Sinaliza somente depois que o loop Tk já estiver ativo."""
    caminho = str(os.environ.get("SM_AUTOLAB_UPDATE_HEALTH", "")).strip()
    if not caminho:
        return
    try:
        destino = Path(caminho)
        destino.parent.mkdir(parents=True, exist_ok=True)
        expected = str(
            os.environ.get("SM_AUTOLAB_UPDATE_EXPECTED_VERSION", "")
        ).strip()
        lines = []
        if expected:
            lines.append(f"version={expected}")
        lines.append(f"pid={os.getpid()}")
        destino.write_text(
            "\n".join(lines) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _agendar_limpeza_atualizacao():
    """Remove a pasta temporária somente após a confirmação da nova versão."""
    caminho = str(os.environ.get("SM_AUTOLAB_UPDATE_CLEANUP_DIR", "")).strip()
    health_caminho = str(os.environ.get("SM_AUTOLAB_UPDATE_HEALTH", "")).strip()
    if not caminho or not health_caminho:
        return

    diretorio = Path(caminho)
    health = Path(health_caminho)

    def worker():
        # O health file está dentro da pasta temporária. Nunca remova a pasta
        # antes de ele existir, pois o instalador usa esse arquivo para confirmar
        # que a nova versão inicializou de fato.
        deadline = time.time() + 60.0
        while time.time() < deadline:
            try:
                if health.exists():
                    break
            except OSError:
                pass
            time.sleep(0.25)
        else:
            # Sem confirmação, deixe os arquivos disponíveis para diagnóstico
            # ou reversão da atualização.
            return

        # Pequena margem para o processo instalador terminar de ler o marcador.
        time.sleep(1.5)

        for _ in range(30):
            try:
                shutil.rmtree(diretorio, ignore_errors=False)
                if not diretorio.exists():
                    return
            except OSError:
                time.sleep(0.5)

    threading.Thread(
        target=worker,
        name="SM-AutoLab-Update-Cleanup",
        daemon=True,
    ).start()

def run_splash(ready_event=None):
    StartupSplash(ready_event=ready_event).run()
SM_AUTOLAB_CANONICAL_UI = "SM-AUTOLAB-CANONICAL-UI"
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
def _update_installer_mode():
    """Executa a atualização em uma janela gráfica, sem abrir prompt de comando."""
    if os.environ.get("SM_AUTOLAB_INSTALLER") != "1":
        return False
    import shutil
    import subprocess
    from tkinter import ttk
    target = Path(os.environ["SM_AUTOLAB_INSTALLER_TARGET"]).resolve()
    payload = Path(os.environ["SM_AUTOLAB_INSTALLER_PAYLOAD"]).resolve()
    installer = Path(os.environ.get("SM_AUTOLAB_INSTALLER_INSTALLER", sys.executable)).resolve()
    expected = os.environ.get("SM_AUTOLAB_INSTALLER_EXPECTED", "").strip()
    backup = Path(os.environ["SM_AUTOLAB_INSTALLER_BACKUP"]).resolve()
    failed = Path(os.environ["SM_AUTOLAB_INSTALLER_FAILED"]).resolve()
    health = Path(os.environ["SM_AUTOLAB_INSTALLER_HEALTH"]).resolve()
    root = tk.Tk()
    root.title("SM AutoLab — Atualização")
    root.resizable(False, False)
    root.configure(bg="#F5F5F5")
    root.attributes("-topmost", True)
    width, height = 470, 210
    root.update_idletasks()
    root.geometry(
        f"{width}x{height}+"
        f"{max((root.winfo_screenwidth()-width)//2,0)}+"
        f"{max((root.winfo_screenheight()-height)//2,0)}"
    )
    # Exibe a janela do instalador explicitamente antes de iniciar a troca.
    root.deiconify()
    root.lift()
    root.focus_force()
    root.update_idletasks()
    title_var = tk.StringVar(value="Atualização do SM AutoLab")
    status_var = tk.StringVar(value=f"Preparando a instalação da v{expected or 'nova versão'}…")
    tk.Label(root,textvariable=title_var,bg="#F5F5F5",fg="#242424",
             font=("Segoe UI",14,"bold")).pack(anchor="w",padx=24,pady=(24,4))
    tk.Label(root,textvariable=status_var,bg="#F5F5F5",fg="#616161",
             font=("Segoe UI",10),wraplength=420,justify="left").pack(anchor="w",padx=24,pady=(0,16))
    progress=ttk.Progressbar(root,mode="indeterminate",length=422)
    progress.pack(padx=24,pady=(0,16))
    progress.start(10)
    def clean_env(env):
        for key in (
            "SM_AUTOLAB_INSTALLER","SM_AUTOLAB_INSTALLER_TARGET",
            "SM_AUTOLAB_INSTALLER_PAYLOAD","SM_AUTOLAB_INSTALLER_INSTALLER",
            "SM_AUTOLAB_INSTALLER_EXPECTED","SM_AUTOLAB_INSTALLER_BACKUP",
            "SM_AUTOLAB_INSTALLER_FAILED","SM_AUTOLAB_INSTALLER_HEALTH",
            "SM_AUTOLAB_UPDATE_HEALTH","SM_AUTOLAB_UPDATE_EXPECTED_VERSION",
            "SM_AUTOLAB_UPDATE_CLEANUP_DIR",
            "PYINSTALLER_RESET_ENVIRONMENT",
        ):
            env.pop(key, None)
        return env
    def launch(path, env):
        flags = 0
        startupinfo = None
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        return subprocess.Popen(
            [str(path)],
            cwd=str(path.parent),
            close_fds=True,
            creationflags=flags,
            startupinfo=startupinfo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            shell=False,
        )
    def health_ok():
        try:
            lines=health.read_text(encoding="utf-8",errors="ignore").splitlines()
        except (OSError,UnicodeError):
            return False
        return (not expected) or f"version={expected}" in lines
    def cleanup_later():
        try:
            progress.stop()
        except Exception:
            pass
        root.destroy()
    def set_ui(title,status):
        root.after(0,lambda:(title_var.set(title),status_var.set(status)))
    def worker():
        try:
            set_ui("Atualização do SM AutoLab","Aguardando o encerramento da versão atual…")
            deadline=time.time()+35
            while time.time()<deadline:
                try:
                    backup.unlink(missing_ok=True)
                    os.replace(str(target),str(backup))
                    break
                except OSError:
                    time.sleep(0.25)
            else:
                raise RuntimeError("A versão atual não pôde ser encerrada para a substituição.")
            set_ui("Atualização do SM AutoLab",f"Instalando a v{expected or 'nova versão'}…")
            os.replace(str(payload),str(target))
            health.unlink(missing_ok=True)
            env=clean_env(os.environ.copy())
            env["PYINSTALLER_RESET_ENVIRONMENT"]="1"
            env["SM_AUTOLAB_UPDATE_HEALTH"]=str(health)
            env["SM_AUTOLAB_UPDATE_EXPECTED_VERSION"]=expected
            env["SM_AUTOLAB_UPDATE_CLEANUP_DIR"]=str(payload.parent)
            set_ui("Atualização do SM AutoLab","Iniciando e verificando a nova versão…")
            launch(target,env)
            deadline=time.time()+28
            while time.time()<deadline:
                if health_ok():
                    set_ui(
                        "Atualização concluída",
                        "Verificação da instalação concluída. A nova versão foi iniciada com sucesso.",
                    )
                    root.after(0,lambda:root.after(1600,cleanup_later))
                    return
                time.sleep(0.25)
            raise RuntimeError("A nova versão não confirmou uma inicialização válida.")
        except Exception as exc:
            set_ui("Falha na atualização","A atualização falhou. Restaurando a versão anterior…")
            try:
                failed.unlink(missing_ok=True)
                if target.exists():
                    os.replace(str(target),str(failed))
            except OSError:
                pass
            restored=False
            try:
                os.replace(str(backup),str(target))
                restored=True
            except OSError:
                pass
            try:
                payload.unlink(missing_ok=True)
                health.unlink(missing_ok=True)
                failed.unlink(missing_ok=True)
            except OSError:
                pass
            if restored:
                try:
                    launch(target,clean_env(os.environ.copy()))
                except OSError:
                    pass
                set_ui("Atualização revertida","A versão anterior foi restaurada. A atualização não foi aplicada.")
            else:
                set_ui("Falha na atualização",f"Não foi possível restaurar a versão anterior.\n{exc}")
            root.after(0,lambda:root.after(3200,cleanup_later))
    threading.Thread(target=worker,name="SM-AutoLab-Updater",daemon=True).start()
    root.mainloop()
    return True
def install_ui(App):
    """Inicializa somente o runtime canônico; não injeta wrappers ou eventos globais."""
    if getattr(App, "_ui_runtime_instalado", False):
        return
    App._ui_runtime_instalado = True
    App._ui_runtime_mode = "canonical"
    App._ui_runtime_marker = SM_AUTOLAB_CANONICAL_UI
if __name__ == "__main__":
    if _update_installer_mode():
        raise SystemExit(0)
    _agendar_limpeza_atualizacao()
    install_ui(App)
    _validar_base_aplicacao()
    startup_update = {"info": None}
    update_ready = threading.Event()
    def _preverificar_atualizacao():
        try:
            startup_update["info"] = find_update(current_override=APP_VERSION)
        except Exception:
            startup_update["info"] = None
        finally:
            update_ready.set()
    threading.Thread(
        target=_preverificar_atualizacao,
        name="SM-AutoLab-Startup-Update",
        daemon=True,
    ).start()
    run_splash(update_ready)
    app = App(
        startup_update_info=startup_update["info"],
        startup_update_checked=update_ready.is_set(),
    )
    # Confirma somente com o Tk já entregue ao event loop.
    # A limpeza temporária aguarda este marcador antes de executar.
    app.app.after_idle(_sinalizar_inicializacao_atualizacao_sucesso)
    app.app.mainloop()
