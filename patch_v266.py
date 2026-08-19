from __future__ import annotations

import json
from datetime import datetime, timedelta
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


def _garantir_pasta_planilha(self):
    self._planilha_arquivo.parent.mkdir(parents=True, exist_ok=True)


def _carregar_historico_planilhas_v266(self):
    _garantir_pasta_planilha(self)
    path = self._planilha_historico_arquivo
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        itens = data.get("items", []) if isinstance(data, dict) else []
        if not isinstance(itens, list):
            return []
        agora = datetime.now()
        limite = agora - timedelta(days=30)
        filtrados = []
        for item in itens:
            if not isinstance(item, dict):
                continue
            try:
                salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            if limite <= salvo <= agora:
                filtrados.append(item)
        if filtrados != itens:
            try:
                self._salvar_historico_planilhas(filtrados)
            except Exception:
                pass
        return filtrados
    except Exception:
        return []


def _salvar_historico_planilhas_v266(self, itens):
    _garantir_pasta_planilha(self)
    agora = datetime.now()
    limite = agora - timedelta(days=30)
    validos = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        try:
            salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
        except Exception:
            continue
        if limite <= salvo <= agora:
            validos.append(item)
    # Sem limite de quantidade: somente a janela de 30 dias.
    payload = {"version": 2, "items": validos}
    tmp = self._planilha_historico_arquivo.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(self._planilha_historico_arquivo)


def _registrar_historico_planilha_v266(self, cells, timestamp=None):
    cells = {str(k): str(v) for k, v in (cells or {}).items() if str(v) != ""}
    if not cells:
        return
    agora = timestamp or datetime.now()
    itens = self._carregar_historico_planilhas()
    linhas = set()
    for chave, valor in cells.items():
        if not str(valor).strip():
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
    if itens and itens[-1].get("cells") == cells:
        itens[-1] = entrada
    else:
        itens.append(entrada)
    self._salvar_historico_planilhas(itens)


def _excluir_historico_planilha_v266(self, item):
    ident = str(item.get("id", ""))
    itens = self._carregar_historico_planilhas()
    self._salvar_historico_planilhas([
        x for x in itens if str(x.get("id", "")) != ident
    ])
    self.abrir_historico_planilha()


def _limpar_historico_planilhas_v266(self):
    from tkinter import messagebox

    itens = self._carregar_historico_planilhas()
    win = getattr(self, "_planilha_historico_window", None)
    if not itens:
        messagebox.showinfo("Arquivos", "Não há arquivos no histórico.", parent=win)
        return
    if not messagebox.askyesno(
        "Limpar Arquivos",
        "Tem certeza que deseja apagar todos os arquivos do histórico?",
        parent=win,
    ):
        return
    self._salvar_historico_planilhas([])
    self.abrir_historico_planilha()


def _abrir_snapshot_historico_v266(self, item):
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


def _abrir_historico_planilha_v266(self):
    import customtkinter as ctk

    self._fechar_historico_planilha()
    itens = list(reversed(self._carregar_historico_planilhas()))
    win = ctk.CTkToplevel(self.app)
    self._planilha_historico_window = win
    win.title("Arquivos — SM AutoLab")
    win.geometry("760x460")
    win.minsize(650, 380)
    win.transient(self.app)
    win.configure(fg_color=self.BG)
    win.protocol("WM_DELETE_WINDOW", self._fechar_historico_planilha)

    header = ctk.CTkFrame(win, fg_color="transparent")
    header.pack(fill="x", padx=20, pady=(18, 10))
    ctk.CTkLabel(
        header, text="Arquivos", text_color=self.TEXT,
        font=("Segoe UI", 20, "bold")
    ).pack(side="left")
    ctk.CTkButton(
        header, text="Limpar histórico", command=self._limpar_historico_planilhas,
        width=125, height=34, corner_radius=7, fg_color=self.CARD,
        hover_color=("#FDECEC", "#3A2424"), border_width=1,
        border_color=self.ERROR, text_color=self.ERROR,
        font=("Segoe UI", 11, "bold")
    ).pack(side="right")
    ctk.CTkLabel(
        win, text="Planilhas salvas nos últimos 30 dias.",
        text_color=self.SUBTEXT, font=("Segoe UI", 11)
    ).pack(anchor="w", padx=20, pady=(0, 12))

    body = ctk.CTkScrollableFrame(win, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
    if not itens:
        ctk.CTkLabel(
            body, text="Nenhum arquivo no histórico.",
            text_color=self.SUBTEXT, font=("Segoe UI", 11)
        ).pack(anchor="center", pady=40)
        return

    for item in itens:
        saved = str(item.get("saved_at", ""))
        try:
            dt = datetime.fromisoformat(saved)
            dia, hora = dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M")
        except Exception:
            dia, hora = saved, ""
        filled = int(item.get("filled", 0) or 0)
        card = ctk.CTkFrame(
            body, fg_color=self.CARD, corner_radius=10,
            border_width=1, border_color=self.BORDER
        )
        card.pack(fill="x", pady=5)
        left = ctk.CTkFrame(card, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=14, pady=10)
        ctk.CTkLabel(
            left, text=dia, text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        ).pack(anchor="w")
        ctk.CTkLabel(
            left, text=f"{hora}  •  {filled} linhas preenchidas",
            text_color=self.SUBTEXT, font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 0))
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=10, pady=8)
        ctk.CTkButton(
            actions, text="Abrir", width=78, height=34, corner_radius=7,
            fg_color=self.ACCENT, hover_color=self.ACCENT_HOVER,
            text_color="#FFFFFF", font=("Segoe UI", 11, "bold"),
            command=lambda it=item: self._abrir_snapshot_historico(it)
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            actions, text="×", width=34, height=34, corner_radius=7,
            fg_color=self.CARD, hover_color=("#FDECEC", "#3A2424"),
            border_width=1, border_color=self.ERROR, text_color=self.ERROR,
            font=("Segoe UI", 16, "bold"),
            command=lambda it=item: self._excluir_historico_planilha(it)
        ).pack(side="left")


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

    # Keep original status renderer available to the patched method.
    app_class.__v265_aplicar_status = app_class._aplicar_status

    app_class._planilha_atualizar_contador = _planilha_atualizar_contador_v266
    app_class._carregar_historico_planilhas = _carregar_historico_planilhas_v266
    app_class._salvar_historico_planilhas = _salvar_historico_planilhas_v266
    app_class._registrar_historico_planilha = _registrar_historico_planilha_v266
    app_class._excluir_historico_planilha = _excluir_historico_planilha_v266
    app_class._limpar_historico_planilhas = _limpar_historico_planilhas_v266
    app_class._abrir_snapshot_historico = _abrir_snapshot_historico_v266
    app_class.abrir_historico_planilha = _abrir_historico_planilha_v266
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
