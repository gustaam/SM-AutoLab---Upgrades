from __future__ import annotations

import customtkinter as ctk


SM_AUTOLAB_EXECUTION_29924 = "SM-AUTOLAB-EXECUTION-CENTER-29924"

_CENTER_WIDTH = 348
_CENTER_HEIGHT = 108


def _stage11_snapshot(processados, total, sucessos, erros, codigo=""):
    total = max(0, int(total or 0))
    processados = max(0, int(processados or 0))
    sucessos = max(0, int(sucessos or 0))
    erros = max(0, int(erros or 0))
    if total:
        processados = min(processados, total)
        percentual = max(0.0, min(1.0, processados / total))
    else:
        percentual = 0.0
    return {
        "processados": processados,
        "total": total,
        "sucessos": sucessos,
        "erros": erros,
        "codigo": str(codigo or "").strip(),
        "percentual": percentual,
    }


def _stage11_final_percentual(processados, total, status):
    snapshot = _stage11_snapshot(processados, total, 0, 0)
    if "parado" in str(status or "").lower():
        return snapshot["percentual"]
    return 1.0 if snapshot["total"] else 0.0


def format_execution_center(processados, total, sucessos, erros, codigo=""):
    """Gera os textos estáveis exibidos pelo Centro de execução."""
    snapshot = _stage11_snapshot(processados, total, sucessos, erros, codigo)
    total = snapshot["total"]
    processados = snapshot["processados"]
    if total:
        status = f"Processando código {processados} de {total}"
    else:
        status = "Preparando execução"
    ultimo = snapshot["codigo"] or "—"
    resumo = (
        f'{processados} processados  •  '
        f'{snapshot["sucessos"]} executados  •  '
        f'{snapshot["erros"]} não executados'
    )
    return {
        **snapshot,
        "status": status,
        "ultimo": ultimo,
        "resumo": resumo,
    }


def _stage11_exists(widget):
    try:
        return widget is not None and widget.winfo_exists()
    except Exception:
        return False


def _stage11_ensure_center(self):
    panel = getattr(self, "_stage11_execution_center", None)
    if _stage11_exists(panel):
        return panel

    panel = ctk.CTkFrame(
        self.app,
        width=_CENTER_WIDTH,
        height=_CENTER_HEIGHT,
        corner_radius=12,
        fg_color=self.CARD,
        border_width=1,
        border_color=self.BORDER,
    )
    panel.place(
        relx=1.0,
        rely=1.0,
        x=-18,
        y=-84,
        anchor="se",
    )
    panel.place_forget()
    panel.pack_propagate(False)

    header = ctk.CTkFrame(panel, fg_color="transparent")
    header.pack(fill="x", padx=12, pady=(9, 0))

    ctk.CTkLabel(
        header,
        text="Centro de execução",
        text_color=self.TEXT,
        font=("Segoe UI", 11, "bold"),
    ).pack(side="left")

    progress_value = ctk.CTkLabel(
        header,
        text="0%",
        text_color=self.ACCENT,
        font=("Segoe UI", 11, "bold"),
    )
    progress_value.pack(side="right")

    status = ctk.CTkLabel(
        panel,
        text="Preparando execução",
        text_color=self.INFO,
        font=("Segoe UI", 10, "bold"),
        anchor="w",
    )
    status.pack(fill="x", padx=12, pady=(4, 0))

    code = ctk.CTkLabel(
        panel,
        text="Atual: —",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 9),
        anchor="w",
    )
    code.pack(fill="x", padx=12, pady=(1, 0))

    bar = ctk.CTkProgressBar(
        panel,
        height=7,
        corner_radius=4,
        fg_color=self.BORDER,
        progress_color=self.ACCENT,
    )
    bar.set(0)
    bar.pack(fill="x", padx=12, pady=(5, 2))

    summary = ctk.CTkLabel(
        panel,
        text="0 processados  •  0 executados  •  0 não executados",
        text_color=self.SUBTEXT,
        font=("Segoe UI", 8),
        anchor="w",
    )
    summary.pack(fill="x", padx=12, pady=(0, 6))

    panel._stage11_status = status
    panel._stage11_code = code
    panel._stage11_progress = bar
    panel._stage11_progress_value = progress_value
    panel._stage11_summary = summary

    self._stage11_execution_center = panel
    self._stage11_hide_job = None
    self._stage11_motion_job = None
    return panel


def _stage11_show(self):
    panel = _stage11_ensure_center(self)
    if not _stage11_exists(panel):
        return

    if self._stage11_hide_job is not None:
        try:
            self.app.after_cancel(self._stage11_hide_job)
        except Exception:
            pass
        self._stage11_hide_job = None

    target = -84
    frame = {"value": 0}
    panel.place(relx=1.0, rely=1.0, x=-18, y=target + 26, anchor="se")
    panel.lift()

    old_job = getattr(self, "_stage11_motion_job", None)
    if old_job is not None:
        try:
            self.app.after_cancel(old_job)
        except Exception:
            pass

    def tick():
        if getattr(self, "_closing", False) or not _stage11_exists(panel):
            return
        frame["value"] += 1
        fator = min(1.0, frame["value"] / 8.0)
        eased = 1.0 - (1.0 - fator) ** 3
        y = target + round((1.0 - eased) * 26)
        panel.place(relx=1.0, rely=1.0, x=-18, y=y, anchor="se")
        if fator < 1.0:
            self._stage11_motion_job = self.app.after(16, tick)
        else:
            self._stage11_motion_job = None

    tick()


def _stage11_update(self, processados, total, sucessos, erros, codigo=""):
    panel = _stage11_ensure_center(self)
    if not _stage11_exists(panel):
        return

    data = format_execution_center(processados, total, sucessos, erros, codigo)
    _stage11_show(self)
    panel._stage11_status.configure(text=data["status"], text_color=self.INFO)
    panel._stage11_code.configure(
        text=f'Atual: {data["ultimo"]}',
        text_color=self.TEXT if data["codigo"] else self.SUBTEXT,
    )
    panel._stage11_progress.set(data["percentual"])
    panel._stage11_progress_value.configure(text=f'{data["percentual"]:.0%}')
    panel._stage11_summary.configure(text=data["resumo"])


def _stage11_finish(self, resultado, status):
    panel = _stage11_ensure_center(self)
    if not _stage11_exists(panel):
        return

    total = int(getattr(resultado, "total_planejado", 0) or 0)
    processados = int(getattr(resultado, "processados", 0) or 0)
    sucessos = int(getattr(resultado, "sucessos", 0) or 0)
    erros = int(getattr(resultado, "erros", 0) or 0)
    itens = getattr(resultado, "itens", []) or []
    codigo = str(getattr(itens[-1], "codigo", "") or "") if itens else ""

    data = format_execution_center(
        processados,
        total,
        sucessos,
        erros,
        codigo,
    )
    _stage11_show(self)

    concluida = "parado" not in status.lower() and "erro" not in status.lower()
    cor = self.SUCCESS if concluida else self.WARNING if "parado" in status.lower() else self.ERROR
    panel._stage11_status.configure(text=status, text_color=cor)
    panel._stage11_code.configure(
        text=f'Último: {data["ultimo"]}',
        text_color=self.TEXT if data["codigo"] else self.SUBTEXT,
    )
    final_percentual = _stage11_final_percentual(processados, total, status)
    panel._stage11_progress.set(final_percentual)
    panel._stage11_progress_value.configure(
        text=f"{final_percentual:.0%}" if total else "0%",
        text_color=cor,
    )
    panel._stage11_summary.configure(
        text=f'{processados} processados  •  {sucessos} executados  •  {erros} não executados'
    )

    if self._stage11_hide_job is not None:
        try:
            self.app.after_cancel(self._stage11_hide_job)
        except Exception:
            pass
    self._stage11_hide_job = self.app.after(3600, lambda: panel.place_forget())


def install_ui_execution_center_29924(App):
    """Etapa 11: Centro de execução flutuante com feedback de progresso."""
    if getattr(App, "_execution_center_29924_aplicado", False):
        return
    App._execution_center_29924_aplicado = True
    App._execution_center_29924_marker = SM_AUTOLAB_EXECUTION_29924

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _stage11_ensure_center(self))
        except Exception:
            _stage11_ensure_center(self)
        return result

    App.config_app = config_wrapper

    original_start = App._iniciar_automacao_interna

    def start_wrapper(self, codigos, *args, **kwargs):
        try:
            _stage11_ensure_center(self)
            _stage11_show(self)
        except Exception:
            pass
        return original_start(self, codigos, *args, **kwargs)

    App._iniciar_automacao_interna = start_wrapper

    original_progress = App._aplicar_progresso

    def progress_wrapper(self, processados, total, sucessos, erros, codigo, *args, **kwargs):
        result = original_progress(self, processados, total, sucessos, erros, codigo, *args, **kwargs)
        try:
            self.app.after(
                0,
                lambda: _stage11_update(
                    self, processados, total, sucessos, erros, codigo
                ),
            )
        except Exception:
            pass
        return result

    App._aplicar_progresso = progress_wrapper

    original_finish = App._finalizar

    def finish_wrapper(self, resultado, *args, **kwargs):
        result = original_finish(self, resultado, *args, **kwargs)
        try:
            status = "Parado pelo usuário" if getattr(self, "_parar", False) else (
                "Concluída" if int(getattr(resultado, "erros", 0) or 0) == 0 else "Concluída com atenção"
            )
            _stage11_finish(self, resultado, status)
        except Exception:
            pass
        return result

    App._finalizar = finish_wrapper

    original_failure = App._falha_geral

    def failure_wrapper(self, msg, *args, **kwargs):
        result = original_failure(self, msg, *args, **kwargs)
        try:
            panel = _stage11_ensure_center(self)
            _stage11_show(self)
            panel._stage11_status.configure(text="Processo interrompido por erro", text_color=self.ERROR)
            panel._stage11_summary.configure(text=str(msg))
            panel._stage11_progress_value.configure(text="ERRO", text_color=self.ERROR)
            if self._stage11_hide_job is not None:
                self.app.after_cancel(self._stage11_hide_job)
            self._stage11_hide_job = self.app.after(4200, lambda: panel.place_forget())
        except Exception:
            pass
        return result

    App._falha_geral = failure_wrapper

    original_close = App._fechar_aplicativo

    def close_wrapper(self, *args, **kwargs):
        try:
            for attr in ("_stage11_hide_job", "_stage11_motion_job"):
                job = getattr(self, attr, None)
                if job is not None:
                    try:
                        self.app.after_cancel(job)
                    except Exception:
                        pass
                    setattr(self, attr, None)
            panel = getattr(self, "_stage11_execution_center", None)
            if _stage11_exists(panel):
                panel.place_forget()
        except Exception:
            pass
        return original_close(self, *args, **kwargs)

    App._fechar_aplicativo = close_wrapper


__all__ = [
    "SM_AUTOLAB_EXECUTION_29924",
    "format_execution_center",
    "install_ui_execution_center_29924",
]
