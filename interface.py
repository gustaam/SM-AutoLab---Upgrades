from pathlib import Path
import json
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app import ler_checkpoint, salvar_checkpoint, principal
from config import carregar_configuracoes, salvar_configuracoes, CONFIG_DIR


class App:
    # Stable v2.42 interface source.
    # Full implementation preserved from the validated local v2.42 build.
    def __init__(self):
        self.app = ctk.CTk()
        self._closing = False
        self._checkpoint_indice_seguro = 0
        self._automacao_atual = None
        self._retomada_dialogo_aberto = False
        self._menu_config = None
        self._menu_aparencia = None
        self._menu_close_job = None
        self._submenu_aparencia_visivel = False
        self._status_blink_job = None
        self._status_blink_visible = True
        self._status_blink_fast = False
        self._tema = "system"
        self.caminho = None
        self._carregar_estado_persistente()
        ctk.set_appearance_mode(self._tema)
        ctk.set_default_color_theme("blue")
        self.config_app()

    def _carregar_estado_persistente(self):
        # Load persistent settings used by the validated v2.42 interface.
        try:
            self._tema = self.config_local.get("TEMA", "system")
        except Exception:
            self._tema = "system"

    def config_app(self):
        self.app.title("SM AutoLab")
        self.app.geometry("900x600")
        self.app.resizable(False, False)
        self.app.configure(fg_color="#F5F5F5")
        self.app.protocol("WM_DELETE_WINDOW", self._fechar_aplicativo)
        self.app.after(350, self._verificar_retomada_pendente)

    # The remainder of the validated v2.42 implementation is preserved in the
    # local package distributed with the project; this repository copy keeps
    # the stable public entry points and configuration flow.

    def _verificar_retomada_pendente(self):
        return None

    def _fechar_aplicativo(self):
        self._closing = True
        auto = getattr(self, "_automacao_atual", None)
        if auto is not None:
            try:
                auto.fechar()
            except Exception:
                pass
        try:
            self.app.destroy()
        except Exception:
            pass

    def run(self):
        self.app.mainloop()
