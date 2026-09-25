# Interface desktop completa: planilha virtualizada, histórico, dashboard, rolagem e integração Windows 11.
from __future__ import annotations

import calendar as pycalendar
import ctypes
import hashlib
import logging
import json
import os
import re
import subprocess
import shutil
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

LOGGER = logging.getLogger(__name__)
from tkinter import Canvas, Entry, Menu, messagebox, simpledialog, ttk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from app import (
    atomic_write_json,
    backup_path,
    read_json_with_backup,
    carregar_configuracoes,
    excluir_checkpoint_interno,
    ler_checkpoint_interno,
    principal_interno,
    restaurar_configuracoes,
    salvar_checkpoint_interno,
    salvar_configuracoes,
)

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

_UI_TOOLTIP_MESSAGES = {
    "iniciar": "Inicia a automação com os códigos selecionados.",
    "parar": "Interrompe a automação com parada segura após o código atual.",
    "configurações": "Abre as configurações do aplicativo.",
    "aparência ›": "Abre as opções de tema claro, escuro e automático.",
    "ajustes do feegow": "Altera o endereço e os dados de acesso do Feegow.",
    "verificar atualizações": "Procura uma versão mais recente do SM AutoLab.",
    "abrir": "Abre a planilha interna.",
    "arquivos": "Abre o histórico de planilhas salvas.",
    "limpar histórico": "Remove o histórico de execuções exibido.",
    "atividade": "Mostra a atividade e os eventos da execução.",
    "histórico": "Mostra o histórico das execuções anteriores.",
    "restaurar": "Restaura as configurações padrão.",
    "cancelar": "Fecha esta janela sem aplicar as alterações.",
    "salvar": "Salva as alterações atuais.",
    "salvar e sair": "Salva a planilha e fecha a janela.",
    "salvar e iniciar": "Salva a planilha e inicia a automação.",
    "limpar": "Limpa os dados preenchidos na planilha.",
    "voltar": "Volta para a visualização anterior.",
    "desfazer": "Desfaz a última alteração.",
    "refazer": "Refaz a alteração desfeita.",
    "claro": "Usa o tema claro.",
    "escuro": "Usa o tema escuro.",
    "padrão do windows": "Segue automaticamente o tema do Windows.",
    "atividade": "Mostra os eventos da execução atual.",
    "histórico": "Mostra as execuções anteriores.",
    "↶": "Desfaz a última alteração.",
    "↷": "Refaz a última alteração.",
    "‹": "Mostra o mês anterior.",
    "›": "Mostra o mês seguinte.",
}

class _SMAutoLabTooltip:
    """Tooltip leve para controles da interface, sem bindings globais."""
    DELAY_MS = 450
    HIDE_GRACE_MS = 120
    MAX_WIDTH = 340

    def __init__(self, widget, message, bind_children=True):
        self.widget = widget
        self.message = str(message or "").strip()
        self.bind_children = bool(bind_children)
        self._after_id = None
        self._hide_id = None
        self._window = None
        self._rendered_message = None
        self._closed = False
        self._bindings = []

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
        widgets = self._iter_widget_tree() if self.bind_children else (self.widget,)
        for child in widgets:
            if any(bound is child for bound, _ in self._bindings):
                continue
            try:
                enter_id = child.bind("<Enter>", self._on_enter, add="+")
                leave_id = child.bind("<Leave>", self._on_leave, add="+")
                press_id = child.bind("<ButtonPress>", self._on_press, add="+")
                focus_id = child.bind("<FocusOut>", self._on_focus_out, add="+")
                destroy_id = child.bind("<Destroy>", self._on_destroy, add="+")
                self._bindings.extend([
                    (child, ("<Enter>", enter_id)),
                    (child, ("<Leave>", leave_id)),
                    (child, ("<ButtonPress>", press_id)),
                    (child, ("<FocusOut>", focus_id)),
                    (child, ("<Destroy>", destroy_id)),
                ])
            except Exception:
                pass

    def _cancel_after(self, attr):
        job = getattr(self, attr, None)
        if job is None:
            return
        try:
            self.widget.after_cancel(job)
        except Exception:
            pass
        setattr(self, attr, None)

    def _inside(self):
        try:
            x = self.widget.winfo_pointerx()
            y = self.widget.winfo_pointery()
            left = self.widget.winfo_rootx()
            top = self.widget.winfo_rooty()
            return left <= x < left + self.widget.winfo_width() and top <= y < top + self.widget.winfo_height()
        except Exception:
            return False

    def update_message(self, message):
        message = str(message or "").strip()
        if message == self.message:
            return
        self.message = message
        self._rendered_message = None
        if not self.message:
            self.hide()
            return
        self._bind_widget_tree()

    def _on_enter(self, _event=None):
        if self._closed or not self.message:
            return
        self._cancel_after("_hide_id")
        self._cancel_after("_after_id")
        try:
            self._after_id = self.widget.after(self.DELAY_MS, self.show)
        except Exception:
            self._after_id = None

    def _on_leave(self, _event=None):
        self._cancel_after("_after_id")
        self._cancel_after("_hide_id")
        try:
            self._hide_id = self.widget.after(self.HIDE_GRACE_MS, self._hide_if_outside)
        except Exception:
            self.hide()

    def _hide_if_outside(self):
        self._hide_id = None
        if not self._inside():
            self.hide()

    def _on_motion(self, _event=None):
        self._cancel_after("_hide_id")
        if self._window is not None:
            self._position()

    def _on_press(self, _event=None):
        # Cliques no controle encerram imediatamente o tooltip. Isso evita
        # que a janela auxiliar permaneça sobre uma nova janela aberta pelo
        # comando do botão, como acontece no botão "Abrir".
        self.hide()

    def _on_focus_out(self, _event=None):
        self.hide()

    def _on_destroy(self, _event=None):
        self._closed = True
        self._cancel_after("_after_id")
        self._cancel_after("_hide_id")
        self._destroy_window()

    def _render(self):
        if self._window is None:
            return
        dark = str(ctk.get_appearance_mode()).lower() == "dark"
        bg, fg, border = (
            ("#1A1A1A", "#F8F8F8", "#C8C8C8")
            if dark else
            ("#2B2B2B", "#FFFFFF", "#454545")
        )
        try:
            for child in self._window.winfo_children():
                child.destroy()
            frame = tk.Frame(self._window, bg=bg, highlightbackground=border, highlightthickness=1, bd=0)
            frame.pack()
            label = tk.Label(
                frame,
                text=self.message,
                bg=bg,
                fg=fg,
                font=("Segoe UI", 9),
                justify="left",
                wraplength=self.MAX_WIDTH,
                padx=8,
                pady=5,
                bd=0,
            )
            label.pack()
            self._window.update_idletasks()
            self._rendered_message = self.message
        except Exception:
            self.hide()

    def show(self):
        self._after_id = None
        self._cancel_after("_hide_id")
        if self._closed or not self.message or not self._inside():
            return
        try:
            if not self.widget.winfo_exists():
                return
            if self._window is None or not self._window.winfo_exists():
                self._window = tk.Toplevel(self.widget)
                self._window._sm_autolab_tooltip_window = True
                self._window.overrideredirect(True)
                self._rendered_message = None
            if self._rendered_message != self.message:
                self._render()
            self._position()
            self._window.deiconify()
            self._window.lift()
        except Exception:
            self.hide()

    def _position(self):
        if self._window is None:
            return
        try:
            pointer_x = self.widget.winfo_pointerx()
            pointer_y = self.widget.winfo_pointery()
            self._window.update_idletasks()
            width = self._window.winfo_reqwidth()
            height = self._window.winfo_reqheight()
            sw = self.widget.winfo_screenwidth()
            sh = self.widget.winfo_screenheight()
            x = pointer_x + 14
            y = pointer_y - height - 14
            if x + width > sw - 4:
                x = max(4, pointer_x - width - 14)
            if y < 4:
                y = pointer_y + 18
            if y + height > sh - 4:
                y = max(4, sh - height - 4)
            self._window.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
        except Exception:
            pass

    def _destroy_window(self):
        window = self._window
        self._window = None
        if window is None:
            return
        try:
            window.destroy()
        except Exception:
            pass

    def hide(self):
        self._cancel_after("_after_id")
        self._cancel_after("_hide_id")
        self._destroy_window()

    def destroy(self):
        self._closed = True
        self._cancel_after("_after_id")
        self._cancel_after("_hide_id")
        for widget, binding in tuple(self._bindings):
            sequence, funcid = binding
            try:
                widget.unbind(sequence, funcid)
            except Exception:
                pass
        self._bindings.clear()
        self._destroy_window()

def _ui_tooltip_text(widget):
    try:
        raw = widget.cget("text")
    except Exception:
        return None
    text = " ".join(str(raw or "").replace("✓", "").split()).strip()
    if not text:
        return None
    key = text.casefold()
    if key in _UI_TOOLTIP_MESSAGES:
        return _UI_TOOLTIP_MESSAGES[key]
    while key and key[0] in "▶■←→‹›":
        key = key[1:].strip()
    if key in _UI_TOOLTIP_MESSAGES:
        return _UI_TOOLTIP_MESSAGES[key]
    if key.replace(" ", "").isalnum() and len(key) >= 4 and any(ch.isdigit() for ch in key):
        return "Clique para copiar este código."
    return None

def _ui_attach_tooltip(widget):
    explicit_message = str(
        getattr(widget, "_sm_autolab_tooltip_message", "") or ""
    ).strip()
    message = explicit_message or _ui_tooltip_text(widget)
    tooltip = getattr(widget, "_sm_autolab_tooltip", None)
    if tooltip is not None:
        tooltip.update_message(message)
        return
    if not message:
        return
    try:
        widget._sm_autolab_tooltip = _SMAutoLabTooltip(
            widget,
            message,
            bind_children=isinstance(widget, ctk.CTkButton),
        )
    except Exception:
        widget._sm_autolab_tooltip = None

def _ui_scan_tooltips(root):
    if root is None:
        return
    stack = [root]
    while stack:
        widget = stack.pop()
        _ui_attach_tooltip(widget)
        try:
            stack.extend(widget.winfo_children())
        except Exception:
            pass

def _ui_install_button_tooltips():
    cls = ctk.CTkButton
    if getattr(cls, "_sm_autolab_tooltip_installed", False):
        return
    original_init = cls.__init__

    def init_with_tooltip(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _ui_attach_tooltip(self)

    cls.__init__ = init_with_tooltip
    cls._sm_autolab_tooltip_installed = True

def _ui_bind_card_hover(card, accent):
    if card is None or getattr(card, "_sm_card_hover_installed", False):
        return
    try:
        card._sm_card_hover_installed = True
        card._sm_card_base_border = card.cget("border_color")
        card._sm_card_base_width = int(card.cget("border_width") or 0)

        def inside():
            try:
                current = card.winfo_containing(card.winfo_pointerx(), card.winfo_pointery())
                return current is not None and (
                    str(current) == str(card) or str(current).startswith(str(card) + ".")
                )
            except Exception:
                return False

        def enter(_event=None):
            try:
                if card.winfo_exists():
                    card.configure(
                        border_width=max(1, card._sm_card_base_width),
                        border_color=(
                            card._sm_card_base_border
                            if ctk.get_appearance_mode().lower() == "dark"
                            else accent
                        ),
                    )
            except Exception:
                pass

        def leave(_event=None):
            def restore():
                try:
                    if card.winfo_exists() and not inside():
                        card.configure(
                            border_width=card._sm_card_base_width,
                            border_color=card._sm_card_base_border,
                        )
                except Exception:
                    pass
            try:
                card.after_idle(restore)
            except Exception:
                restore()

        for child in _walk_widgets(card):
            try:
                child.bind("<Enter>", enter, add="+")
                child.bind("<Leave>", leave, add="+")
            except Exception:
                pass
    except Exception:
        pass

def _walk_widgets(widget):
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _walk_widgets(child)


class _SMWindowsRoundedScrollbar(tk.Canvas):
    """Barra de rolagem arredondada com setas, inspirada no padrão do Windows."""

    ARROW_SIZE = 16
    MIN_THUMB = 28
    REPEAT_DELAY = 420
    REPEAT_INTERVAL = 55
    ARROW_SCROLL_UNITS = 12
    ARROW_PRESSED_COLOR = "#454545"

    def __init__(self, master, orient="vertical", command=None, **kwargs):
        self.orient = str(orient or "vertical").lower()
        self.command = command
        self._first = 0.0
        self._last = 1.0
        self._drag_offset = None
        self._repeat_job = None
        self._hover_part = None
        self._pressed_part = None
        self._bg_color = "#F3F3F3"
        self._thumb_color = "#C8C8C8"
        self._thumb_hover_color = "#AFAFAF"
        self._arrow_color = "#707070"
        self._arrow_hover_color = "#595959"
        kwargs.setdefault("width", self.ARROW_SIZE)
        kwargs.setdefault("height", self.ARROW_SIZE)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("borderwidth", 0)
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("takefocus", False)
        kwargs.setdefault("bg", self._bg_color)
        super().__init__(master, **kwargs)

        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")
        self.bind("<B1-Motion>", self._on_motion, add="+")
        self.bind("<Motion>", self._on_motion_hover, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<Configure>", lambda _event: self._redraw(), add="+")
        self.after_idle(self._redraw)

    def set_colors(
        self,
        bg_color,
        thumb_color,
        thumb_hover_color,
        arrow_color,
        arrow_hover_color,
    ):
        self._bg_color = bg_color
        self._thumb_color = thumb_color
        self._thumb_hover_color = thumb_hover_color
        self._arrow_color = arrow_color
        self._arrow_hover_color = arrow_hover_color
        try:
            self.configure(bg=self._bg_color)
        except Exception:
            pass
        self._redraw()

    def set(self, first, last):
        try:
            self._first = max(0.0, min(1.0, float(first)))
            self._last = max(self._first, min(1.0, float(last)))
        except (TypeError, ValueError):
            self._first, self._last = 0.0, 1.0
        self._redraw()

    def get(self):
        return self._first, self._last

    def _dimensions(self):
        width = max(1, int(self.winfo_width()))
        height = max(1, int(self.winfo_height()))
        return width, height

    def _track_bounds(self):
        width, height = self._dimensions()
        if self.orient == "horizontal":
            start = self.ARROW_SIZE
            end = max(start + 1, width - self.ARROW_SIZE)
        else:
            start = self.ARROW_SIZE
            end = max(start + 1, height - self.ARROW_SIZE)
        return start, end

    def _thumb_geometry(self):
        start, end = self._track_bounds()
        track_length = max(1.0, end - start)
        visible = max(0.0, min(1.0, self._last - self._first))
        thumb_length = max(self.MIN_THUMB, track_length * visible)
        thumb_length = min(track_length, thumb_length)
        movable = max(0.0, track_length - thumb_length)
        # O primeiro valor do yview/xview vai somente até (1 - visible).
        # Normaliza esse intervalo para que o polegar percorra todo o trilho
        # e encoste na seta final quando a área rolável chegar ao fim.
        scrollable_range = max(0.0, 1.0 - visible)
        if scrollable_range > 0.0:
            position_fraction = self._first / scrollable_range
        else:
            position_fraction = 0.0
        position_fraction = max(0.0, min(1.0, position_fraction))
        thumb_start = start + movable * position_fraction
        thumb_start = max(start, min(end - thumb_length, thumb_start))
        thumb_end = thumb_start + thumb_length
        return start, end, thumb_start, thumb_end

    @staticmethod
    def _rounded_rect(canvas, x0, y0, x1, y1, radius, fill, tag):
        radius = max(1, min(float(radius), (x1 - x0) / 2.0, (y1 - y0) / 2.0))
        canvas.create_rectangle(
            x0 + radius, y0, x1 - radius, y1,
            fill=fill, outline="", tags=tag
        )
        canvas.create_rectangle(
            x0, y0 + radius, x1, y1 - radius,
            fill=fill, outline="", tags=tag
        )
        canvas.create_oval(
            x0, y0, x0 + 2 * radius, y0 + 2 * radius,
            fill=fill, outline="", tags=tag
        )
        canvas.create_oval(
            x1 - 2 * radius, y0, x1, y0 + 2 * radius,
            fill=fill, outline="", tags=tag
        )
        canvas.create_oval(
            x0, y1 - 2 * radius, x0 + 2 * radius, y1,
            fill=fill, outline="", tags=tag
        )
        canvas.create_oval(
            x1 - 2 * radius, y1 - 2 * radius, x1, y1,
            fill=fill, outline="", tags=tag
        )

    def _redraw(self):
        try:
            self.delete("all")
            width, height = self._dimensions()
            self.configure(bg=self._bg_color)

            if self.orient == "horizontal":
                start, end, thumb_start, thumb_end = self._thumb_geometry()
                center = height / 2.0
                thumb_half = max(2.0, min(height / 2.0 - 1.0, 6.0))
                self._rounded_rect(
                    self,
                    thumb_start,
                    center - thumb_half,
                    thumb_end,
                    center + thumb_half,
                    thumb_half,
                    self._thumb_color if self._hover_part != "thumb" else self._thumb_hover_color,
                    "thumb",
                )
                arrow_fill_left = (
                    self.ARROW_PRESSED_COLOR
                    if self._pressed_part == "decrement"
                    else self._arrow_hover_color
                    if self._hover_part == "decrement"
                    else self._arrow_color
                )
                arrow_fill_right = (
                    self.ARROW_PRESSED_COLOR
                    if self._pressed_part == "increment"
                    else self._arrow_hover_color
                    if self._hover_part == "increment"
                    else self._arrow_color
                )
                cy = center
                self.create_polygon(
                    11, cy, 5, cy - 4, 5, cy + 4,
                    fill=arrow_fill_left, outline="", tags="decrement"
                )
                self.create_polygon(
                    width - 5, cy, width - 11, cy - 4, width - 11, cy + 4,
                    fill=arrow_fill_right, outline="", tags="increment"
                )
            else:
                start, end, thumb_start, thumb_end = self._thumb_geometry()
                center = width / 2.0
                thumb_half = max(2.0, min(width / 2.0 - 1.0, 6.0))
                self._rounded_rect(
                    self,
                    center - thumb_half,
                    thumb_start,
                    center + thumb_half,
                    thumb_end,
                    thumb_half,
                    self._thumb_color if self._hover_part != "thumb" else self._thumb_hover_color,
                    "thumb",
                )
                arrow_fill_up = (
                    self.ARROW_PRESSED_COLOR
                    if self._pressed_part == "decrement"
                    else self._arrow_hover_color
                    if self._hover_part == "decrement"
                    else self._arrow_color
                )
                arrow_fill_down = (
                    self.ARROW_PRESSED_COLOR
                    if self._pressed_part == "increment"
                    else self._arrow_hover_color
                    if self._hover_part == "increment"
                    else self._arrow_color
                )
                cx = center
                self.create_polygon(
                    cx, 5, cx - 4, 11, cx + 4, 11,
                    fill=arrow_fill_up, outline="", tags="decrement"
                )
                self.create_polygon(
                    cx, height - 5, cx - 4, height - 11, cx + 4, height - 11,
                    fill=arrow_fill_down, outline="", tags="increment"
                )
        except Exception:
            pass

    def _position_from_event(self, event):
        return event.x if self.orient == "horizontal" else event.y

    def _is_in_thumb(self, position):
        _, _, thumb_start, thumb_end = self._thumb_geometry()
        return thumb_start <= position <= thumb_end

    def _region(self, position):
        width, height = self._dimensions()
        total = width if self.orient == "horizontal" else height
        if position < self.ARROW_SIZE:
            return "decrement"
        if position >= total - self.ARROW_SIZE:
            return "increment"
        if self._is_in_thumb(position):
            return "thumb"
        return "track"

    def _run_command(self, *args):
        if callable(self.command):
            try:
                self.command(*args)
            except Exception:
                pass

    def _scroll_one(self, direction):
        self._run_command(
            "scroll",
            int(direction) * self.ARROW_SCROLL_UNITS,
            "units",
        )

    def _start_repeat(self, direction):
        self._cancel_repeat()
        self._scroll_one(direction)

        def repeat():
            self._repeat_job = None
            if self._drag_offset is None:
                self._scroll_one(direction)
                self._repeat_job = self.after(self.REPEAT_INTERVAL, repeat)

        self._repeat_job = self.after(self.REPEAT_DELAY, repeat)

    def _cancel_repeat(self):
        job = self._repeat_job
        self._repeat_job = None
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass

    def _on_press(self, event):
        position = self._position_from_event(event)
        region = self._region(position)
        if region == "decrement":
            self._drag_offset = None
            self._pressed_part = "decrement"
            self._redraw()
            self._start_repeat(-1)
        elif region == "increment":
            self._drag_offset = None
            self._pressed_part = "increment"
            self._redraw()
            self._start_repeat(1)
        elif region == "thumb":
            self._cancel_repeat()
            _, _, thumb_start, _ = self._thumb_geometry()
            self._drag_offset = position - thumb_start
        else:
            self._cancel_repeat()
            _, _, thumb_start, thumb_end = self._thumb_geometry()
            if position < thumb_start:
                self._run_command("scroll", -1, "pages")
            elif position > thumb_end:
                self._run_command("scroll", 1, "pages")

    def _on_motion(self, event):
        if self._drag_offset is None:
            return
        start, end, thumb_start, thumb_end = self._thumb_geometry()
        thumb_length = thumb_end - thumb_start
        movable = max(1.0, (end - start) - thumb_length)
        position = self._position_from_event(event)
        target = position - self._drag_offset
        fraction = max(0.0, min(1.0, (target - start) / movable))
        self._run_command("moveto", fraction)
        self._hover_part = "thumb"
        self._redraw()

    def _on_release(self, _event):
        self._cancel_repeat()
        self._drag_offset = None
        if self._pressed_part is not None:
            self._pressed_part = None
            self._redraw()

    def _on_motion_hover(self, event):
        if self._drag_offset is not None:
            return
        region = self._region(self._position_from_event(event))
        if region != self._hover_part:
            self._hover_part = region
            self._redraw()

    def _on_leave(self, _event):
        if self._drag_offset is None:
            self._hover_part = None
            self._redraw()

    def destroy(self):
        self._cancel_repeat()
        return super().destroy()


def _ui_windows_scrollbar_colors():
    """Paleta visual da barra arredondada usada em todo o aplicativo."""
    dark = str(ctk.get_appearance_mode()).lower() == "dark"
    if dark:
        return {
            "bg": "#252525",
            "thumb": "#626262",
            "thumb_hover": "#777777",
            "arrow": "#C2C2C2",
            "arrow_hover": "#FFFFFF",
        }
    return {
        "bg": "#F3F3F3",
        "thumb": "#C8C8C8",
        "thumb_hover": "#AFAFAF",
        "arrow": "#707070",
        "arrow_hover": "#595959",
    }


def _ui_update_windows_scrollbar(scrollable):
    """Atualiza a barra arredondada conforme o tema atual."""
    bar = getattr(scrollable, "_sm_windows_scrollbar", None)
    if bar is None:
        return
    try:
        if not bar.winfo_exists():
            return
        colors = _ui_windows_scrollbar_colors()
        bar.set_colors(
            colors["bg"],
            colors["thumb"],
            colors["thumb_hover"],
            colors["arrow"],
            colors["arrow_hover"],
        )
    except Exception:
        pass


def _ui_install_windows_scrollbar(scrollable):
    """Instala a barra arredondada com setas em um CTkScrollableFrame."""
    try:
        if getattr(scrollable, "_sm_windows_scrollbar", None) is not None:
            _ui_update_windows_scrollbar(scrollable)
            return

        parent = getattr(scrollable, "_parent_frame", None)
        canvas = getattr(scrollable, "_parent_canvas", None)
        old_scrollbar = getattr(scrollable, "_scrollbar", None)
        if parent is None or canvas is None:
            return

        if old_scrollbar is not None:
            try:
                old_scrollbar.grid_remove()
            except Exception:
                try:
                    old_scrollbar.grid_forget()
                except Exception:
                    pass

        colors = _ui_windows_scrollbar_colors()
        bar = _SMWindowsRoundedScrollbar(
            parent,
            orient="vertical",
            command=canvas.yview,
            width=16,
            bg=colors["bg"],
        )
        bar.grid(row=1, column=1, sticky="ns", padx=0, pady=0)
        bar.set_colors(
            colors["bg"],
            colors["thumb"],
            colors["thumb_hover"],
            colors["arrow"],
            colors["arrow_hover"],
        )
        canvas.configure(yscrollcommand=bar.set)
        scrollable._sm_windows_scrollbar = bar
    except Exception:
        LOGGER.debug("Não foi possível instalar a barra arredondada.", exc_info=True)


def _ui_install_scrollbar_autopatch():
    """Faz com que todo CTkScrollableFrame use a barra arredondada com setas."""
    cls = ctk.CTkScrollableFrame
    if getattr(cls, "_sm_windows_scrollbar_installed", False):
        return

    original_init = cls.__init__

    def init_with_windows_scrollbar(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _ui_install_windows_scrollbar(self)

    cls.__init__ = init_with_windows_scrollbar
    cls._sm_windows_scrollbar_installed = True


def _ui_make_windows_scrollbar(parent, orient, command):
    """Cria a mesma barra arredondada para widgets Tk."""
    colors = _ui_windows_scrollbar_colors()
    bar = _SMWindowsRoundedScrollbar(
        parent,
        orient=orient,
        command=command,
        width=16 if orient == "vertical" else 120,
        height=16 if orient == "horizontal" else 120,
        bg=colors["bg"],
    )
    bar.set_colors(
        colors["bg"],
        colors["thumb"],
        colors["thumb_hover"],
        colors["arrow"],
        colors["arrow_hover"],
    )
    return bar


def _ui_refresh_all_windows_scrollbars(root):
    """Reaplica o tema a todas as barras arredondadas."""
    if root is None:
        return
    stack = [root]
    while stack:
        widget = stack.pop()
        if isinstance(widget, _SMWindowsRoundedScrollbar):
            try:
                colors = _ui_windows_scrollbar_colors()
                widget.set_colors(
                    colors["bg"],
                    colors["thumb"],
                    colors["thumb_hover"],
                    colors["arrow"],
                    colors["arrow_hover"],
                )
            except Exception:
                pass
        elif isinstance(widget, tk.Scrollbar):
            try:
                colors = _ui_windows_scrollbar_colors()
                widget.configure(
                    bg=colors["thumb"],
                    activebackground=colors["thumb_hover"],
                    troughcolor=colors["bg"],
                )
            except Exception:
                pass
        try:
            stack.extend(widget.winfo_children())
        except Exception:
            pass


_ui_install_scrollbar_autopatch()

_ui_install_button_tooltips()

REPO = "gustaam/SM-AutoLab---Upgrades"
API_RELEASES = f"https://api.github.com/repos/{REPO}/releases?per_page=30"
USER_AGENT = "SM AutoLab"
UPDATE_CHANNEL = "SM-AUTOLAB-RESET-2026-09"
LOGGER = logging.getLogger("sm_autolab.interface")

MANIFEST_ASSET_NAMES = {
    "release-manifest.json",
    "sm autolab release manifest.json",
    "sm.autolab.release.manifest.json",
}

def _normalize_asset_name(value: str) -> str:
    """Normaliza nomes para aceitar diferenças de separador e capitalização."""
    text = str(value or "").strip().lower()
    return re.sub(r"[\s._-]+", "", text)

def _version_tuple(value: str) -> tuple[int, ...]:
    """Converte versões numéricas em tupla sem truncar componentes."""
    value = str(value or "").strip().lstrip("vV")
    if not re.fullmatch(r"\d+(?:\.\d+)*", value):
        return ()
    parts = [int(piece) for piece in value.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)

def current_version(base: Path | None = None) -> str:
    base = base or Path(getattr(__import__("sys"), "_MEIPASS", Path(__file__).resolve().parent))
    try:
        value = (base / "VERSION").read_text(encoding="utf-8").strip()
        if value:
            return value.lstrip("vV")
    except OSError:
        pass
    return ""

def fetch_releases(timeout: int = 8) -> list[dict]:
    request = urllib.request.Request(
        API_RELEASES,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data if isinstance(data, list) else []

def _is_manifest_asset(asset: dict) -> bool:
    name = _normalize_asset_name(str(asset.get("name", "")))
    return name in {_normalize_asset_name(item) for item in MANIFEST_ASSET_NAMES}

def _release_asset_by_name(assets: list[dict], expected_name: str) -> dict | None:
    expected = _normalize_asset_name(expected_name)
    if not expected:
        return None
    return next(
        (
            asset
            for asset in assets
            if _normalize_asset_name(str(asset.get("name", ""))) == expected
        ),
        None,
    )

def _load_release_manifest(release: dict, timeout: int = 8) -> dict | None:
    assets = release.get("assets") or []
    manifest_asset = next((a for a in assets if _is_manifest_asset(a)), None)
    if manifest_asset is None:
        return None
    url = str(manifest_asset.get("browser_download_url") or "")
    if not url or not url.lower().startswith("https://github.com/"):
        return None
    try:
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            manifest = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(manifest, dict) or manifest.get("channel") != UPDATE_CHANNEL:
        return None
    release_version = str(release.get("tag_name", "")).strip().lstrip("vV")
    manifest_version = str(manifest.get("version", "")).strip().lstrip("vV")
    manifest_tag = str(manifest.get("tag", "")).strip().lstrip("vV")
    if not release_version or manifest_version != release_version or manifest_tag != release_version:
        return None
    main_asset = _release_asset_by_name(assets, str(manifest.get("main_asset", "")))
    if main_asset is None:
        return None
    main_name = str(main_asset.get("name", "")).strip().lower()
    if not main_name.endswith(".exe") or "updater" in _normalize_asset_name(main_name):
        return None
    asset_digest = str(main_asset.get("digest") or "").strip().lower()
    if asset_digest.startswith("sha256:"):
        asset_digest = asset_digest.split(":", 1)[1]
    manifest_digest = str(manifest.get("main_sha256") or "").strip().lower()
    if manifest_digest and not re.fullmatch(r"[0-9a-f]{64}", manifest_digest):
        return None
    if asset_digest and not re.fullmatch(r"[0-9a-f]{64}", asset_digest):
        return None
    if asset_digest and manifest_digest and manifest_digest != asset_digest:
        return None
    return manifest

def find_update(timeout: int = 8, current_override: str | None = None) -> dict | None:
    current = str(current_override or "").strip()
    if not current:
        current = current_version()
    current_tuple = _version_tuple(current)
    if not current_tuple:
        return None
    compatible: list[tuple[dict, tuple[int, ...], dict]] = []
    try:
        releases = fetch_releases(timeout)
    except Exception:
        return None
    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = str(release.get("tag_name", "")).strip().lstrip("vV")
        version_tuple = _version_tuple(tag)
        if not tag or not version_tuple or version_tuple <= current_tuple:
            continue
        manifest = _load_release_manifest(release, timeout)
        if manifest is None:
            continue
        compatible.append((release, version_tuple, manifest))
    if not compatible:
        return None
    release, _, manifest = max(compatible, key=lambda item: item[1])
    latest = str(release.get("tag_name", "")).strip().lstrip("vV")
    assets = release.get("assets") or []
    asset = _release_asset_by_name(assets, str(manifest.get("main_asset", "")))
    if asset is None:
        return None
    digest = str(asset.get("digest") or "")
    if digest.lower().startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    if not digest:
        digest = str(manifest.get("main_sha256") or "")
    if not digest:
        return None
    return {
        "version": latest,
        "current": current,
        "name": release.get("name") or f"SM AutoLab v{latest}",
        "url": release.get("html_url") or "",
        "download_url": asset.get("browser_download_url") or "",
        "sha256": digest,
        "asset_name": asset.get("name") or "",
        "release_url": release.get("html_url") or "",
    }

def download_file(
    url: str,
    destination: Path,
    expected_sha256: str = "",
    progress_callback=None,
) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    hasher = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as output:
        try:
            total_bytes = int(response.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            total_bytes = 0
        downloaded_bytes = 0
        last_percent = -1

        if progress_callback is not None:
            try:
                progress_callback(0, total_bytes)
            except Exception:
                pass

        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            hasher.update(chunk)
            downloaded_bytes += len(chunk)

            if progress_callback is not None:
                if total_bytes > 0:
                    percent = int(downloaded_bytes * 100 / total_bytes)
                    if percent != last_percent:
                        last_percent = percent
                        try:
                            progress_callback(downloaded_bytes, total_bytes)
                        except Exception:
                            pass
                elif downloaded_bytes == len(chunk):
                    try:
                        progress_callback(downloaded_bytes, total_bytes)
                    except Exception:
                        pass

        if progress_callback is not None:
            try:
                progress_callback(downloaded_bytes, total_bytes)
            except Exception:
                pass

    if expected_sha256 and hasher.hexdigest().lower() != expected_sha256.lower():
        try:
            destination.unlink()
        except OSError:
            pass
        raise RuntimeError("A verificação SHA-256 da atualização falhou.")
def _escape_cmd_path(value: str) -> str:
    """Escapa caracteres especiais para uso em arquivo .cmd sem expansão de variáveis."""
    return (
        str(value)
        .replace("^", "^^")
        .replace("&", "^&")
        .replace("|", "^|")
        .replace("<", "^<")
        .replace(">", "^>")
        .replace("%", "%%")
        .replace("!", "^^!")
    )

def _sanitize_pyinstaller_environment(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Remove o estado interno herdado do PyInstaller antes do reinício."""
    source = dict(os.environ if environ is None else environ)
    return {
        key: value
        for key, value in source.items()
        if not key.upper().startswith("_PYI_") and key.upper() != "_MEIPASS2"
    }

def _prepare_independent_restart_environment(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Prepara o ambiente para que a nova onefile seja tratada como instância independente."""
    env = _sanitize_pyinstaller_environment(environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env

def _schedule_replace_after_exit(
    target: Path,
    downloaded: Path,
    expected_version: str = "",
) -> tuple[bool, str]:
    """Abre o instalador visual em uma cópia temporária do executável atualizado."""
    try:
        installer = downloaded.parent / f"{target.stem}.installer.exe"
        installer.unlink(missing_ok=True)
        shutil.copy2(downloaded, installer)

        backup = downloaded.parent / f"{target.name}.sm_autolab_backup"
        failed = downloaded.parent / f"{target.name}.sm_autolab_failed"
        health = downloaded.parent / "startup.ok"
        for path in (backup, failed, health):
            path.unlink(missing_ok=True)

        env = _prepare_independent_restart_environment()
        env.update({
            "SM_AUTOLAB_INSTALLER": "1",
            "SM_AUTOLAB_INSTALLER_TARGET": str(target),
            "SM_AUTOLAB_INSTALLER_PAYLOAD": str(downloaded),
            "SM_AUTOLAB_INSTALLER_INSTALLER": str(installer),
            "SM_AUTOLAB_INSTALLER_EXPECTED": str(expected_version or ""),
            "SM_AUTOLAB_INSTALLER_BACKUP": str(backup),
            "SM_AUTOLAB_INSTALLER_FAILED": str(failed),
            "SM_AUTOLAB_INSTALLER_HEALTH": str(health),
            "SM_AUTOLAB_UPDATE_CLEANUP_DIR": str(downloaded.parent),
        })
        flags = 0
        startupinfo = None
        if os.name == "nt":
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        subprocess.Popen(
            [str(installer)],
            cwd=str(downloaded.parent),
            close_fds=True,
            creationflags=flags,
            startupinfo=startupinfo,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            shell=False,
        )
        return True, ""
    except (OSError, shutil.Error) as exc:
        return False, str(exc)

def launch_updater(update: dict, progress_callback=None) -> tuple[bool, str]:
    if os.name != "nt":
        return False, "A atualização automática integrada só está disponível no Windows."
    if not update.get("download_url"):
        return False, "A release encontrada não possui um executável correspondente à versão."

    target = Path(__import__("sys").executable).resolve()
    if target.suffix.lower() != ".exe" or not getattr(__import__("sys"), "frozen", False):
        return False, "A atualização automática integrada só está disponível no executável do SM AutoLab."

    temp_dir = Path(tempfile.mkdtemp(prefix="sm_autolab_update_"))
    downloaded = temp_dir / target.name
    try:
        download_file(
            str(update["download_url"]),
            downloaded,
            str(update.get("sha256") or ""),
            progress_callback=progress_callback,
        )
        ok, error = _schedule_replace_after_exit(
            target,
            downloaded,
            expected_version=str(update.get("version") or ""),
        )
        if not ok:
            raise RuntimeError(error or "Não foi possível preparar a substituição da atualização.")
        return True, ""
    except Exception as exc:
        try:
            if downloaded.exists():
                downloaded.unlink()
        except OSError:
            pass
        try:
            script = temp_dir / "apply_update.cmd"
            if script.exists():
                script.unlink()
        except OSError:
            pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass
        return False, str(exc)

from typing import Iterable, Mapping, Sequence

MAX_ROWS = 10_000
MAX_COLS = 3

def rectangle_selection(start: Sequence[int], end: Sequence[int]) -> set[tuple[int, int]]:
    """Retorna todas as células dentro de um retângulo inclusivo."""
    r1, c1 = int(start[0]), int(start[1])
    r2, c2 = int(end[0]), int(end[1])
    lo_r, hi_r = sorted((r1, r2))
    lo_c, hi_c = sorted((c1, c2))
    return {
        (row, col)
        for row in range(lo_r, hi_r + 1)
        for col in range(lo_c, hi_c + 1)
        if 0 <= row < MAX_ROWS and 0 <= col < MAX_COLS
    }

def non_empty_cells(cells: Mapping[str, object] | None) -> set[tuple[int, int]]:
    """Converte o armazenamento esparso em células preenchidas válidas."""
    result: set[tuple[int, int]] = set()
    for key, value in (cells or {}).items():
        if str(value).strip() == "":
            continue
        try:
            row, col = (int(part.strip()) for part in str(key).split(","))
        except (TypeError, ValueError):
            continue
        if 0 <= row < MAX_ROWS and 0 <= col < MAX_COLS:
            result.add((row, col))
    return result

def filled_row_count(cells: Mapping[str, object] | None) -> int:
    """Conta quantas linhas possuem ao menos uma célula preenchida."""
    return len({row for row, _ in non_empty_cells(cells)})

def extract_column(cells: Mapping[str, object] | None, column: int = 1) -> list[str]:
    """Extrai valores não vazios de uma coluna, na ordem das linhas."""
    items: list[tuple[int, str]] = []
    for key, value in (cells or {}).items():
        try:
            row, col = (int(part.strip()) for part in str(key).split(","))
        except (TypeError, ValueError):
            continue
        if col != int(column) or not 0 <= row < MAX_ROWS:
            continue
        text = str(value).strip()
        if text:
            items.append((row, text))
    items.sort(key=lambda item: item[0])
    return [text for _, text in items]

def parse_paste_text(text: object) -> list[list[str]]:
    """Interpreta texto copiado de planilhas, com TAB ou separadores por espaço."""
    if text is None:
        return []

    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    while normalized.endswith("\n"):
        normalized = normalized[:-1]
    if not normalized:
        return []

    rows: list[list[str]] = []
    has_tab = "\t" in normalized
    for raw_row in normalized.split("\n"):
        if has_tab:
            row_values = raw_row.split("\t")
        else:
            parts = raw_row.strip().split(None, 2)
            if len(parts) >= 3:
                row_values = parts[:3]
            elif len(parts) == 2:
                row_values = parts
            else:
                row_values = [raw_row]
        rows.append(row_values)

    while rows and all(value == "" for value in rows[-1]):
        rows.pop()
    return rows

def apply_paste(
    cells: Mapping[str, object] | None,
    rows: Sequence[Sequence[object]],
    start_row: int,
    start_col: int,
) -> tuple[dict[str, str], bool]:
    """Aplica uma matriz colada ao armazenamento esparso da planilha."""
    result = {str(key): str(value) for key, value in (cells or {}).items() if str(value) != ""}
    row0 = int(start_row)
    col0 = int(start_col)
    if not rows or row0 < 0 or row0 >= MAX_ROWS or col0 >= MAX_COLS:
        return result, False

    changed = False
    for row_offset, values in enumerate(rows):
        row = row0 + row_offset
        if row >= MAX_ROWS:
            break
        for col_offset, value in enumerate(values[:MAX_COLS]):
            col = col0 + col_offset
            if col >= MAX_COLS or col < 0:
                break
            key = f"{row},{col}"
            text = str(value)
            if text:
                if result.get(key) != text:
                    changed = True
                result[key] = text
            else:
                if key in result:
                    changed = True
                result.pop(key, None)
    return result, changed

def clear_cells(
    cells: Mapping[str, object] | None,
    selected: Iterable[Sequence[int]],
) -> tuple[dict[str, str], bool]:
    """Limpa as células selecionadas e informa se houve alteração."""
    result = {str(key): str(value) for key, value in (cells or {}).items() if str(value) != ""}
    changed = False
    for cell in selected:
        try:
            row, col = int(cell[0]), int(cell[1])
        except (TypeError, ValueError, IndexError):
            continue
        if not 0 <= row < MAX_ROWS or not 0 <= col < MAX_COLS:
            continue
        key = f"{row},{col}"
        if key in result:
            result.pop(key, None)
            changed = True
    return result, changed

def undo_state(
    undo: Sequence[Mapping[str, object]],
    redo: Sequence[Mapping[str, object]],
    current: Mapping[str, object],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]] | None:
    """Calcula o próximo estado de Undo sem depender de Tkinter."""
    if not undo:
        return None
    new_undo = [dict(item) for item in undo[:-1]]
    new_redo = [dict(item) for item in redo]
    new_redo.append({str(key): str(value) for key, value in current.items()})
    new_current = {str(key): str(value) for key, value in undo[-1].items()}
    return new_undo, new_redo, new_current

def redo_state(
    undo: Sequence[Mapping[str, object]],
    redo: Sequence[Mapping[str, object]],
    current: Mapping[str, object],
) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, str]] | None:
    """Calcula o próximo estado de Redo sem depender de Tkinter."""
    if not redo:
        return None
    new_undo = [dict(item) for item in undo]
    new_undo.append({str(key): str(value) for key, value in current.items()})
    new_redo = [dict(item) for item in redo[:-1]]
    new_current = {str(key): str(value) for key, value in redo[-1].items()}
    return new_undo, new_redo, new_current

import math
from collections.abc import Callable
from typing import Any

SM_AUTOLAB_GRADE_VIRTUAL = "SM-AUTOLAB-GRADE-VIRTUAL"
DEFAULT_TOTAL_ROWS = 10000
DEFAULT_ROW_HEIGHT = 28
DEFAULT_OVERSCAN = 3

def _clamp_fraction(value: float) -> float:
    return max(0.0, min(1.0, float(value)))

def visible_row_range(
    first_fraction: float,
    viewport_height: int,
    total_rows: int = DEFAULT_TOTAL_ROWS,
    row_height: int = DEFAULT_ROW_HEIGHT,
    overscan: int = DEFAULT_OVERSCAN,
) -> tuple[int, int]:
    """Mapeia a viewport lógica para um intervalo pequeno de linhas."""
    total_rows = max(0, int(total_rows))
    row_height = max(1, int(row_height))
    overscan = max(0, int(overscan))
    if total_rows == 0:
        return 0, 0

    fraction = _clamp_fraction(first_fraction)
    viewport_rows = max(1, math.ceil(max(1, int(viewport_height)) / row_height))
    pool_size = viewport_rows + overscan * 2
    scrollable_rows = max(0, total_rows - viewport_rows)
    # Tk Canvas reports the first fraction relative to the entire scrollregion.
    # Convert that directly to a logical row before applying overscan.
    logical_top = min(total_rows, int(fraction * total_rows + 1e-7))

    start = max(0, logical_top - overscan)
    end = min(total_rows, start + pool_size)
    if end - start < pool_size:
        start = max(0, end - pool_size)
    return start, end

class VirtualGridTree(tk.Frame):
    """API mínima compatível com a planilha usando um pool fixo de Canvas."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        columns: Iterable[tuple[str, str, int, int, str, bool]],
        total_rows: int = DEFAULT_TOTAL_ROWS,
        row_height: int = DEFAULT_ROW_HEIGHT,
        header_height: int = DEFAULT_ROW_HEIGHT,
        value_provider: Callable[[int], Iterable[Any]] | None = None,
        bg: str = "#FFFFFF",
        header_bg: str = "#F5F5F5",
        fg: str = "#242424",
        header_fg: str = "#242424",
        border: str = "#E0E0E0",
        even_bg: str = "#FFFFFF",
        odd_bg: str = "#FBFBFB",
    ):
        super().__init__(master, bd=0, highlightthickness=0)
        self._columns = list(columns)
        self._total_rows = max(0, int(total_rows))
        self._row_height = max(1, int(row_height))
        self._header_height = max(1, int(header_height))
        self._value_provider = value_provider

        self._bg = bg
        self._header_bg = header_bg
        self._fg = fg
        self._header_fg = header_fg
        self._border = border
        self._even_bg = even_bg
        self._odd_bg = odd_bg

        self._widths = {
            name: max(1, int(width))
            for name, _text, width, _minwidth, _anchor, _stretch in self._columns
        }
        self._minimum_widths = {
            name: max(1, int(minwidth))
            for name, _text, _width, minwidth, _anchor, _stretch in self._columns
        }
        self._anchors = {
            name: anchor
            for name, _text, _width, _minwidth, anchor, _stretch in self._columns
        }
        self._headings = {
            name: text
            for name, text, _width, _minwidth, _anchor, _stretch in self._columns
        }
        self._focus_iid = ""
        self._refresh_job = None
        self._xscrollcommand = None
        self._yscrollcommand = None
        self._pool: list[dict[str, Any]] = []

        # Convert the pool to a list after initialisation for deterministic
        # typing and easy reuse.
        self._pool = []
        self._header_items: dict[str, int] = {}
        self._header_lines: list[int] = []

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._header = tk.Canvas(
            self,
            height=self._header_height,
            bg=self._header_bg,
            highlightthickness=1,
            highlightbackground=self._border,
            bd=0,
        )
        self._header.grid(row=0, column=0, sticky="ew")

        self._canvas = tk.Canvas(
            self,
            bg=self._bg,
            highlightthickness=1,
            highlightbackground=self._border,
            bd=0,
            takefocus=True,
        )
        self._canvas.grid(row=1, column=0, sticky="nsew")

        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", lambda _event: self.yview_scroll(-3, "units"))
        self._canvas.bind("<Button-5>", lambda _event: self.yview_scroll(3, "units"))

        self._scroll_anchor = self._canvas.create_rectangle(
            0,
            0,
            1,
            max(1, self._total_rows * self._row_height),
            outline="",
            fill=self._bg,
            tags=("virtual-scroll-anchor",),
        )

        self._redraw_header()
        self._update_scrollregion()
        self._schedule_refresh()

    @property
    def total_rows(self) -> int:
        return self._total_rows

    @property
    def row_height(self) -> int:
        return self._row_height

    @property
    def visible_pool_size(self) -> int:
        return len(self._pool)

    def _total_width(self) -> int:
        return max(
            1,
            sum(self._widths.get(name, 1) for name, *_rest in self._columns),
        )

    def _update_scrollregion(self) -> None:
        total_width = self._total_width()
        total_height = max(1, self._total_rows * self._row_height)
        self._canvas.configure(scrollregion=(0, 0, total_width, total_height))
        self._header.configure(scrollregion=(0, 0, total_width, self._header_height))
        try:
            self._canvas.coords(
                self._scroll_anchor,
                0,
                0,
                1,
                total_height,
            )
        except tk.TclError:
            pass

    def _column_left(self, name: str) -> int:
        left = 0
        for column_name, _text, _width, _minwidth, _anchor, _stretch in self._columns:
            if column_name == name:
                return left
            left += self._widths.get(column_name, 1)
        return left

    def _redraw_header(self) -> None:
        self._header.delete("all")
        self._header_items.clear()
        self._header_lines.clear()

        total_width = self._total_width()
        self._header.create_rectangle(
            0,
            0,
            total_width,
            self._header_height,
            fill=self._header_bg,
            outline=self._border,
            width=1,
        )

        x = 0
        for name, text, _width, _minwidth, anchor, _stretch in self._columns:
            width = self._widths.get(name, 1)
            text_anchor = "w" if anchor == "w" else ("e" if anchor == "e" else "center")
            if text_anchor == "w":
                text_x = x + 8
            elif text_anchor == "e":
                text_x = x + width - 8
            else:
                text_x = x + width / 2
            self._header_items[name] = self._header.create_text(
                text_x,
                self._header_height / 2,
                text=str(text),
                fill=self._header_fg,
                font=("Segoe UI", 10, "bold"),
                anchor=text_anchor,
            )
            self._header_lines.append(
                self._header.create_line(
                    x + width,
                    0,
                    x + width,
                    self._header_height,
                    fill=self._border,
                )
            )
            x += width
        self._update_scrollregion()

    def _on_canvas_configure(self, _event=None) -> None:
        self._ensure_pool()
        self._schedule_refresh()

    def _on_mousewheel(self, event) -> str:
        try:
            delta = int(event.delta)
        except (AttributeError, TypeError, ValueError):
            delta = 0
        if delta == 0:
            return "break"
        units = -max(1, abs(delta) // 120) if delta > 0 else max(1, abs(delta) // 120)
        self.yview_scroll(units, "units")
        return "break"

    def _schedule_refresh(self) -> None:
        if self._refresh_job is not None:
            return
        try:
            self._refresh_job = self.after_idle(self._refresh_visible)
        except tk.TclError:
            self._refresh_job = None

    def _ensure_pool(self) -> None:
        height = max(1, self._canvas.winfo_height())
        viewport_rows = max(1, math.ceil(height / self._row_height))
        target = min(
            max(8, viewport_rows + DEFAULT_OVERSCAN * 2 + 2),
            max(8, self._total_rows + DEFAULT_OVERSCAN),
        )
        while len(self._pool) < target:
            background = self._canvas.create_rectangle(
                0,
                0,
                1,
                self._row_height,
                outline="",
                fill=self._even_bg,
                tags=("virtual-row",),
            )
            vertical_lines = []
            column_x = 0
            for name, _text, _width, _minwidth, _anchor, _stretch in self._columns[:-1]:
                column_x += self._widths.get(name, 1)
                vertical_lines.append(
                    self._canvas.create_line(
                        column_x,
                        0,
                        column_x,
                        self._row_height,
                        fill=self._border,
                        tags=("virtual-column-line",),
                    )
                )

            cells = [
                self._canvas.create_text(
                    0,
                    self._row_height / 2,
                    text="",
                    fill=self._fg,
                    font=("Segoe UI", 9),
                    anchor="w",
                    tags=("virtual-cell",),
                )
                for _name, _text, _width, _minwidth, _anchor, _stretch in self._columns
            ]
            line = self._canvas.create_line(
                0,
                self._row_height - 1,
                self._total_width(),
                self._row_height - 1,
                fill=self._border,
                tags=("virtual-row-line",),
            )
            self._pool.append(
                {
                    "background": background,
                    "line": line,
                    "vertical_lines": vertical_lines,
                    "cells": cells,
                }
            )

    def _values_for_row(self, row: int) -> tuple[str, ...]:
        if self._value_provider is None:
            return tuple("" for _ in self._columns)
        try:
            values = tuple(
                "" if value is None else str(value)
                for value in self._value_provider(row)
            )
        except Exception:
            values = ()
        expected = len(self._columns)
        return values[:expected] + tuple("" for _ in range(max(0, expected - len(values))))

    def _refresh_visible(self) -> None:
        self._refresh_job = None
        try:
            self._ensure_pool()
            first = float(self._canvas.yview()[0])
            height = max(1, self._canvas.winfo_height())
            start, end = visible_row_range(
                first,
                height,
                self._total_rows,
                self._row_height,
                DEFAULT_OVERSCAN,
            )
            width = self._total_width()

            for offset, slot in enumerate(self._pool):
                logical_row = start + offset
                visible = logical_row < end and logical_row < self._total_rows
                if not visible:
                    self._canvas.itemconfigure(slot["background"], state="hidden")
                    self._canvas.itemconfigure(slot["line"], state="hidden")
                    for cell in slot["cells"]:
                        self._canvas.itemconfigure(cell, state="hidden")
                    for line_id in slot["vertical_lines"]:
                        self._canvas.itemconfigure(line_id, state="hidden")
                    continue

                y0 = logical_row * self._row_height
                row_values = self._values_for_row(logical_row)
                row_bg = self._odd_bg if logical_row % 2 else self._even_bg
                self._canvas.coords(
                    slot["background"],
                    0,
                    y0,
                    width,
                    y0 + self._row_height,
                )
                self._canvas.itemconfigure(
                    slot["background"],
                    fill=row_bg,
                    state="normal",
                )
                self._canvas.coords(
                    slot["line"],
                    0,
                    y0 + self._row_height - 1,
                    width,
                    y0 + self._row_height - 1,
                )
                self._canvas.itemconfigure(
                    slot["line"],
                    fill=self._border,
                    state="normal",
                )

                column_x = 0
                for idx, (name, _text, _width, _minwidth, _anchor, _stretch) in enumerate(self._columns[:-1]):
                    column_x += self._widths.get(name, 1)
                    line_id = slot["vertical_lines"][idx]
                    self._canvas.coords(
                        line_id,
                        column_x,
                        y0,
                        column_x,
                        y0 + self._row_height,
                    )
                    self._canvas.itemconfigure(
                        line_id,
                        fill=self._border,
                        state="normal",
                    )

                x = 0
                for idx, (
                    name,
                    _text,
                    _width,
                    _minwidth,
                    anchor,
                    _stretch,
                ) in enumerate(self._columns):
                    column_width = self._widths.get(name, 1)
                    value = row_values[idx] if idx < len(row_values) else ""
                    text_anchor = "w" if anchor == "w" else ("e" if anchor == "e" else "center")
                    if text_anchor == "w":
                        text_x = x + 7
                    elif text_anchor == "e":
                        text_x = x + column_width - 7
                    else:
                        text_x = x + column_width / 2
                    self._canvas.coords(
                        slot["cells"][idx],
                        text_x,
                        y0 + self._row_height / 2,
                    )
                    self._canvas.itemconfigure(
                        slot["cells"][idx],
                        text=value,
                        fill=self._fg,
                        anchor=text_anchor,
                        state="normal",
                    )
                    x += column_width

            try:
                self._header.xview_moveto(float(self._canvas.xview()[0]))
            except (tk.TclError, TypeError, ValueError):
                pass
            self._update_scroll_callbacks()
        except tk.TclError:
            pass

    def _update_scroll_callbacks(self) -> None:
        try:
            first, last = self._canvas.yview()
            if self._yscrollcommand is not None:
                self._yscrollcommand(first, last)
            first_x, last_x = self._canvas.xview()
            self._header.xview_moveto(first_x)
            if self._xscrollcommand is not None:
                self._xscrollcommand(first_x, last_x)
        except (tk.TclError, TypeError, ValueError):
            pass

    def refresh(self) -> None:
        self._ensure_pool()
        self._refresh_visible()

    # Minimal Treeview-like API consumed by interface.py.
    def heading(self, column: str, option: str | None = None, **kwargs: Any):
        if kwargs and "text" in kwargs:
            self._headings[column] = kwargs["text"]
            self._redraw_header()
            return None
        if option == "text":
            return self._headings.get(column, "")
        return {"text": self._headings.get(column, "")}

    def column(self, column: str, option: str | None = None, **kwargs: Any):
        if kwargs:
            if "minwidth" in kwargs:
                self._minimum_widths[column] = max(1, int(kwargs["minwidth"]))
            if "width" in kwargs:
                self._widths[column] = max(
                    self._minimum_widths.get(column, 1),
                    int(kwargs["width"]),
                )
            if "anchor" in kwargs:
                self._anchors[column] = str(kwargs["anchor"])
            self._redraw_header()
            self._schedule_refresh()
            return None
        if option == "width":
            return self._widths.get(column, 0)
        return {
            "width": self._widths.get(column, 0),
            "minwidth": self._minimum_widths.get(column, 0),
            "anchor": self._anchors.get(column, "w"),
        }

    def configure(self, cnf=None, **kwargs: Any):
        if cnf:
            kwargs.update(cnf)
        if "yscrollcommand" in kwargs:
            self._yscrollcommand = kwargs.pop("yscrollcommand")
        if "xscrollcommand" in kwargs:
            self._xscrollcommand = kwargs.pop("xscrollcommand")
        if kwargs:
            try:
                super().configure(**kwargs)
            except tk.TclError:
                try:
                    self._canvas.configure(**kwargs)
                except tk.TclError:
                    pass
        self._schedule_refresh()

    config = configure

    def get_children(self, item: str = "") -> tuple[str, ...]:
        try:
            first = float(self._canvas.yview()[0])
            height = max(1, self._canvas.winfo_height())
        except (tk.TclError, TypeError, ValueError):
            first = 0.0
            height = 1
        start, end = visible_row_range(
            first,
            height,
            self._total_rows,
            self._row_height,
            DEFAULT_OVERSCAN,
        )
        return tuple(str(row) for row in range(start, end))

    def next(self, iid: str) -> str:
        current = int(iid)
        visible = self.get_children("")
        try:
            index = visible.index(str(current))
        except ValueError:
            return ""
        return visible[index + 1] if index + 1 < len(visible) else ""

    def focus(self, iid: str | None = None):
        if iid is not None:
            self._focus_iid = str(iid)
            return None
        return self._focus_iid

    def focus_set(self):
        try:
            self._canvas.focus_set()
        except tk.TclError:
            pass

    def item(self, iid: str, option: str | None = None, **kwargs: Any):
        values = self._values_for_row(int(str(iid)))
        if "values" in kwargs:
            if self._value_provider is None:
                setattr(self, "_manual_values", getattr(self, "_manual_values", {}))
                self._manual_values[str(iid)] = tuple(
                    "" if value is None else str(value)
                    for value in kwargs["values"]
                )
            self._schedule_refresh()
            values = self._values_for_row(int(str(iid)))
        if option == "values":
            return values
        if kwargs:
            return None
        return {"values": values}

    def bbox(self, iid: str, column: str | None = None):
        try:
            row = int(str(iid))
            if row < 0 or row >= self._total_rows:
                return None
            first, last = visible_row_range(
                float(self._canvas.yview()[0]),
                max(1, self._canvas.winfo_height()),
                self._total_rows,
                self._row_height,
                DEFAULT_OVERSCAN,
            )
            if row < first or row >= last:
                return None
            x_scroll = float(self._canvas.canvasx(0))
            y_scroll = float(self._canvas.canvasy(0))
            y = row * self._row_height - y_scroll
            if column is None:
                x = -x_scroll
                width = self._total_width()
            else:
                index = int(str(column).lstrip("#")) - 1
                name = self._columns[index][0]
                x = self._column_left(name) - x_scroll
                width = self._widths[name]
            return int(round(x)), int(round(y)), int(width), self._row_height
        except (ValueError, IndexError, TypeError, tk.TclError):
            return None

    def cell_bbox(self, iid: str, column: str) -> tuple[int, int, int, int] | None:
        """Retorna a caixa da célula em coordenadas lógicas do Canvas.
        
        Diferente de bbox(), os valores não são relativos à viewport. Isso é
        necessário para desenhar a seleção como item nativo do Canvas, que usa
        coordenadas do scrollregion e acompanha a rolagem automaticamente.
        """
        try:
            row = int(str(iid))
            if row < 0 or row >= self._total_rows:
                return None
            index = int(str(column).lstrip("#")) - 1
            if index < 0 or index >= len(self._columns):
                return None
            name = self._columns[index][0]
            x = self._column_left(name)
            y = row * self._row_height
            width = self._widths.get(name, 1)
            return int(x), int(y), int(width), int(self._row_height)
        except (ValueError, IndexError, TypeError):
            return None

    def identify_row(self, y: int | float) -> str:
        """Identifica a linha usando coordenadas relativas ao Canvas da grade.
        Os bindings de mouse da planilha são instalados no Canvas interno; por
        isso event.y já começa em 0 no topo da primeira linha. O cabeçalho
        horizontal pertence a outro Canvas e não deve ser descontado aqui.
        """
        try:
            logical_y = float(self._canvas.canvasy(float(y)))
            row = int(logical_y // self._row_height)
            return str(row) if 0 <= row < self._total_rows else ""
        except (TypeError, ValueError, tk.TclError):
            return ""

    def identify_column(self, x: int | float) -> str:
        """Identifica a coluna usando coordenadas relativas ao Canvas da grade."""
        try:
            canvas_x = float(self._canvas.canvasx(float(x)))
        except (TypeError, ValueError, tk.TclError):
            return ""
        for idx, (name, _text, _width, _minwidth, _anchor, _stretch) in enumerate(self._columns, start=1):
            left = self._column_left(name)
            right = left + self._widths.get(name, 1)
            if left <= canvas_x < right:
                return f"#{idx}"
        return ""

    def identify_cell(self, x: int | float, y: int | float) -> tuple[int, int] | None:
        """Converte coordenadas do Canvas diretamente em (linha, coluna).
        
        Todas as interações de mouse da planilha passam por este único hit-test,
        evitando divergências entre seleção, arraste, duplo clique e contexto.
        """
        row_id = self.identify_row(y)
        col_id = self.identify_column(x)
        if not row_id or not col_id:
            return None
        try:
            return int(row_id), int(col_id[1:]) - 1
        except (TypeError, ValueError):
            return None

    def see(self, iid: str):
        if self._total_rows <= 0:
            return
        try:
            row = max(0, min(self._total_rows - 1, int(str(iid))))
        except (TypeError, ValueError):
            return

        height = max(1, self._canvas.winfo_height())
        viewport_rows = max(1, int(height / self._row_height))
        current = float(self._canvas.yview()[0])
        start, end = visible_row_range(
            current,
            height,
            self._total_rows,
            self._row_height,
            DEFAULT_OVERSCAN,
        )
        if row < start:
            target = max(0, row - DEFAULT_OVERSCAN)
        elif row >= end:
            target = max(0, row - viewport_rows + 1)
        else:
            return
        self._canvas.yview_moveto(target / max(1, self._total_rows))
        self._update_scroll_callbacks()
        self._schedule_refresh()

    def yview(self, *args):
        if not args:
            return self._canvas.yview()
        self._canvas.yview(*args)
        self._update_scroll_callbacks()
        self._schedule_refresh()

    def xview(self, *args):
        if not args:
            return self._canvas.xview()
        self._canvas.xview(*args)
        self._update_scroll_callbacks()
        self._schedule_refresh()

    def yview_scroll(self, number: int, what: str):
        self._canvas.yview_scroll(int(number), what)
        self._update_scroll_callbacks()
        self._schedule_refresh()

    def xview_scroll(self, number: int, what: str):
        self._canvas.xview_scroll(int(number), what)
        self._update_scroll_callbacks()
        self._schedule_refresh()

    def bind(self, sequence=None, func=None, add=None):
        return self._canvas.bind(sequence, func, add)

__all__ = [
    "SM_AUTOLAB_GRADE_VIRTUAL",
    "VirtualGridTree",
    "visible_row_range",
]

# Windows/DWM helpers used directly by the canonical UI.

DWMWA_TRANSITIONS_FORCEDISABLED = 3
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWCP_ROUND = 2
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2
DWMSBT_TRANSIENTWINDOW = 3
DWMSBT_TABBEDWINDOW = 4

def desabilitar_transicoes_dwm(window) -> bool:
    """Desabilita apenas as transições DWM desta janela, sem alterar o Windows globalmente."""
    if os.name != "nt" or window is None:
        return False
    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
        return _set_dwm_attribute(
            hwnd,
            DWMWA_TRANSITIONS_FORCEDISABLED,
            ctypes.c_int(1),
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return False

def _windows11_available():
    if os.name != "nt":
        return False
    try:
        return int(sys.getwindowsversion().build) >= 22000
    except (AttributeError, OSError, TypeError, ValueError):
        return False

def _windows11_backdrops_available():
    if not _windows11_available():
        return False
    try:
        return int(sys.getwindowsversion().build) >= 22621
    except (AttributeError, OSError, TypeError, ValueError):
        return False

def _set_dwm_attribute(hwnd, attribute, value):
    try:
        dwmapi = ctypes.WinDLL("dwmapi", use_last_error=True)
        setter = dwmapi.DwmSetWindowAttribute
        setter.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        setter.restype = ctypes.c_long
        result = setter(
            wintypes.HWND(hwnd),
            wintypes.DWORD(attribute),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        return int(result) == 0
    except (AttributeError, OSError, TypeError, ValueError):
        return False

def _windows_colorref(hex_color):
    valor = str(hex_color or "").strip().lstrip("#")
    if len(valor) != 6:
        return ctypes.c_uint32(0)
    try:
        vermelho = int(valor[0:2], 16)
        verde = int(valor[2:4], 16)
        azul = int(valor[4:6], 16)
    except ValueError:
        return ctypes.c_uint32(0)
    return ctypes.c_uint32((azul << 16) | (verde << 8) | vermelho)


def _configurar_titulo_dwm(hwnd, dark: bool):
    """Define explicitamente a cor da barra de título e do texto no Windows 11."""
    if not _windows11_available():
        return False
    cor_fundo = _windows_colorref("#252A2E" if dark else "#F5F5F5")
    cor_texto = _windows_colorref("#FFFFFF" if dark else "#1F1F1F")
    ok_fundo = _set_dwm_attribute(hwnd, DWMWA_CAPTION_COLOR, cor_fundo)
    ok_texto = _set_dwm_attribute(hwnd, DWMWA_TEXT_COLOR, cor_texto)
    return ok_fundo and ok_texto


def aplicar_backdrop_sistema(window, material="mica", dark=None):
    """Aplica Mica/Mica Alt/Acrylic via DWM; retorna False quando indisponível."""
    if window is None or not _windows11_backdrops_available():
        return False
    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
    except Exception:
        return False
    materiais = {
        "mica": DWMSBT_MAINWINDOW,
        "acrylic": DWMSBT_TRANSIENTWINDOW,
        "mica_alt": DWMSBT_TABBEDWINDOW,
    }
    backdrop = materiais.get(str(material).lower())
    if backdrop is None:
        return False
    ok = _set_dwm_attribute(
        hwnd,
        DWMWA_SYSTEMBACKDROP_TYPE,
        ctypes.c_int(backdrop),
    )
    _set_dwm_attribute(hwnd, 20, ctypes.c_int(1 if bool(dark) else 0))
    _configurar_titulo_dwm(hwnd, bool(dark))
    _set_dwm_attribute(hwnd, 33, ctypes.c_int(DWMWCP_ROUND))
    return ok

def atualizar_backdrop_tema(window, dark: bool):
    """Atualiza somente o modo claro/escuro do backdrop existente."""
    if window is None or not _windows11_backdrops_available():
        return False
    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
    except Exception:
        return False
    _set_dwm_attribute(hwnd, 20, ctypes.c_int(1 if dark else 0))
    return _configurar_titulo_dwm(hwnd, bool(dark))

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
# Histórico: Data, Hora, Processados, Executados, Erros, Status e indicador.
# Não exibe mais o nome da planilha nem a duração na listagem.
# Data/Hora ficam ancorados à esquerda. O grande espaçador absorve a
# largura livre e empurra Processados, Executados, Erros, Status e o indicador
# para o extremo direito. Os pesos das cinco colunas finais ainda permitem
# adaptação contínua quando a janela diminui.
HISTORICO_COL_PESOS = (0, 0, 18, 4, 4, 3, 5, 1, 0)
HISTORICO_COL_MINS = (72, 60, 8, 60, 60, 46, 58, 16, 0)

class App:
    INICIAR_LABEL = "Iniciar"

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
        "light": "Clara",
        "dark": "Escura",
        "system": "Padrão do Windows",
    }
    VIEW_LABELS = {
        "complete": "Completa",
        "compact": "Compacta",
    }

    def __init__(self, startup_update_info=None, startup_update_checked=False):
        self.app = ctk.CTk()
        self._startup_update_info = startup_update_info
        self._startup_update_checked = bool(startup_update_checked)
        self._configurar_icone_janela()
        self._parar = False
        self._closing = False
        self._checkpoint_indice_seguro = 0
        self._automacao_atual = None
        self._retomada_dialogo_aberto = False
        self._log_count = 0
        self._historico_execucoes = []
        self._execucao_atual = None
        self._erros_codigos = []
        self._codigos_erros_execucao = []
        self._historico_arquivo = Path.home() / "SM AutoLab" / "historico_execucoes.json"
        self._erros_arquivo = Path.home() / "SM AutoLab" / "historico_erros.json"
        self._historico_arquivo_legado = Path.home() / ".sm_autolab_historico.json"
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
        self._planilha_edit_context = None
        self._planilha_context_menu = None
        self._planilha_celula_ativa = None
        self._planilha_linhas_selecionadas = set()
        # Cache de leitura do histórico para evitar I/O e JSON.loads repetidos.
        self._planilha_historico_cache = None
        self._planilha_historico_cache_signature = None
        self._tema = "system"
        self._visualizacao = "complete"
        self._menu_config = None
        self._menu_aparencia = None
        self._menu_visualizacao = None
        self._menu_visualizacao_btn = None
        self._menu_visualizacao_close_job = None
        self._menu_close_job = None
        self._menu_reposition_job = None
        self._menu_reposition_binding = None
        self._menu_aparencia_close_job = None
        self._menu_monitor_job = None
        self._historico_selecionados = set()
        self._historico_tiles = {}
        self._arquivos_datas_selecionadas = set()
        self._stat_icon_font_cache = {}
        self._planilha_historico_window = None
        self._historico_compacto_window = None
        self._historico_notificacao_badge = None
        self._historico_notificacao_reposition_job = None
        self._historico_compacto_notificacao_badge = None
        self._visualizacao_reinicio_dialog = None
        self._arquivos_body = None
        self._arquivos_calendar_canvas = None
        self._arquivos_mes = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._arquivos_data_selecionada = None
        self._arquivos_calendar_widget = None
        self.arquivos_contador_label = None
        self._status_blink_job = None
        self._status_blink_visible = True
        self._status_blink_fast = False
        self._status_finalizado_job = None
        self._execucao_inicio_monotonic = None
        self._execucao_timer_job = None
        self._execucao_inicio_indice = 0
        self._execucao_total = 0
        self._ultimo_tempo_decorrido_segundos = 0.0
        self._ultimo_codigos_medidos = 0
        self._tempo_decorrido_label = None
        self._tempo_estimado_label = None
        self._arquivos_tempo_decorrido_label = None
        self._arquivos_media_codigo_label = None
        self._atualizacao_janela = None
        self._atualizacao_barra = None
        self._atualizacao_label = None
        self._atualizacao_em_andamento = False
        self._execucao_titulo_label = None
        self._execucao_subtitulo_label = None
        self._execucao_indicador_label = None
        self._execucao_progresso_card = None
        self._historico_reflow_job = None
        self._historico_layout_width = 0
        self._activity_card = None
        self._ultimo_tamanho_app_config = None
        self._app_restore_job = None
        self._carregar_estado_persistente()
        ctk.set_appearance_mode(self._tema)
        ctk.set_default_color_theme("blue")
        self.config_app()
        self._instalar_atalhos_teclado()
        self._sinalizar_inicio_atualizacao()

    def _sinalizar_inicio_atualizacao(self):
        """Compatibilidade: o health-check agora é sinalizado pelo bootstrap."""
        return

    def _configurar_icone_janela(self, janela=None):
        """Aplica o ícone oficial do aplicativo à barra de título da janela."""
        janela = janela or self.app
        try:
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
            icone = base / "SM AutoLab.ico"
            if icone.exists():
                janela.iconbitmap(str(icone))
        except Exception:
            # Ícone é somente visual; falha aqui não deve impedir a abertura.
            pass

    def _centralizar_janela(self, janela, largura=None, altura=None):
        """Centraliza uma janela no monitor em que o Tk a posicionou."""
        try:
            janela.update_idletasks()
            if largura is None or altura is None:
                largura = max(1, int(janela.winfo_width()))
                altura = max(1, int(janela.winfo_height()))
            else:
                largura = max(1, int(largura))
                altura = max(1, int(altura))
            tela_w = max(1, int(janela.winfo_screenwidth()))
            tela_h = max(1, int(janela.winfo_screenheight()))
            x = max((tela_w - largura) // 2, 0)
            y = max((tela_h - altura) // 2, 0)
            janela.geometry(f"{largura}x{altura}+{x}+{y}")
            janela.update_idletasks()
        except Exception:
            pass

    def _agendar_estabilizacao_apos_retomada(self, _event=None):
        if self._closing:
            return
        # Não fazemos relayout nem repaint artificial no restore. O DWM está
        # configurado para não animar a transição dessa janela.
        try:
            desabilitar_transicoes_dwm(self.app)
        except Exception:
            pass

    def _estabilizar_apos_retomada(self):
        return

    def _preparar_minimizacao(self, _event=None):
        if self._closing:
            return
        self._fechar_menus()

    def config_app(self):
        self.app.title("SM AutoLab")
        self.app.geometry("900x600")
        self.app.minsize(760, 590)
        self.app.resizable(True, True)
        self.app.configure(fg_color=self.BG)
        self.app.protocol("WM_DELETE_WINDOW", self._fechar_aplicativo)
        # O problema observado no vídeo ocorre durante a transição nativa de
        # minimizar/restaurar. Desabilitamos essa transição somente nesta janela.
        try:
            desabilitar_transicoes_dwm(self.app)
        except Exception:
            pass
        self.app.bind("<Unmap>", self._preparar_minimizacao, add="+")
        self.app.bind("<Map>", self._agendar_estabilizacao_apos_retomada, add="+")

        # Abre a janela em tamanho maior e centralizada na tela.
        self.app.update_idletasks()
        largura = 900
        altura = 600
        tela_w = self.app.winfo_screenwidth()
        tela_h = self.app.winfo_screenheight()
        x = max((tela_w - largura) // 2, 0)
        y = max((tela_h - altura) // 2, 0)
        self.app.geometry(f"{largura}x{altura}+{x}+{y}")

        if self._visualizacao == "compact":
            self._configurar_dashboard_compacto()
            return

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
        self._main_scrollable = main

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
        self.progresso_label.pack(anchor="w", padx=14, pady=(0, 7))

        time_row = ctk.CTkFrame(progress, fg_color="transparent")
        time_row.pack(fill="x", padx=10, pady=(0, 10))
        time_row.grid_columnconfigure((0, 1), weight=1)

        elapsed_box = ctk.CTkFrame(
            time_row, fg_color=("#F3F7FA", "#24343D"),
            corner_radius=8, height=42
        )
        elapsed_box.grid(row=0, column=0, sticky="ew", padx=(4, 3))
        elapsed_box.grid_propagate(False)
        ctk.CTkLabel(
            elapsed_box, text="Tempo decorrido", text_color=self.SUBTEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(9, 6))
        self._tempo_decorrido_label = ctk.CTkLabel(
            elapsed_box, text="00:00:00", text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        )
        self._tempo_decorrido_label.pack(side="right", padx=(2, 9))

        eta_box = ctk.CTkFrame(
            time_row, fg_color=("#F3F7FA", "#24343D"),
            corner_radius=8, height=42
        )
        eta_box.grid(row=0, column=1, sticky="ew", padx=(3, 4))
        eta_box.grid_propagate(False)
        ctk.CTkLabel(
            eta_box, text="Tempo estimado restante", text_color=self.SUBTEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(8, 4))
        self._tempo_estimado_label = ctk.CTkLabel(
            eta_box, text="—", text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        )
        self._tempo_estimado_label.pack(side="right", padx=(2, 9))

        stats = ctk.CTkFrame(main, fg_color="transparent")
        stats.pack(fill="x", pady=(0, 8))
        stats.grid_columnconfigure((0, 1, 2), weight=1)
        self.sucesso_card = self._stat_card(stats, "✓", "Executados", "0", self.SUCCESS)
        self.sucesso_card.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.erro_card = self._stat_card(stats, "!", "Não executados", "0", self.ERROR)
        self.erro_card.grid(row=0, column=1, sticky="ew", padx=5)
        self.codigo_card = self._stat_card(stats, "▥", "Código atual", "—", self.INFO)
        self.codigo_card.grid(row=0, column=2, sticky="ew", padx=(5, 0))
        self._execucao_progresso_card = None

        activity_card = self._card(main)
        activity_card.pack(fill="x", pady=(0, 6))
        # Altura adaptável: preserva espaço para o histórico sem esconder
        # conteúdo quando a janela principal fica maior ou menor.
        activity_card.configure(height=340)
        activity_card.pack_propagate(False)
        self._activity_card = activity_card
        self.app.bind("<Configure>", self._ajustar_altura_acompanhamento, add="+")

        # Fluent-inspired tab row, like the reference image.
        tabs = ctk.CTkFrame(activity_card, fg_color=("#F3F3F3", "#343A40"), corner_radius=8,
                           border_width=1, border_color=self.BORDER)
        tabs.pack(pady=(5, 5), padx=14)

        self.tab_buttons = {}
        for name in ("Atividade", "Histórico"):
            btn = ctk.CTkButton(
                tabs, text=name, command=lambda n=name: self._selecionar_aba(n),
                width={"Atividade": 92, "Histórico": 92}[name],
                height=26, corner_radius=8,
                fg_color=("#E5F1FB", "#183B54") if name == "Atividade" else "transparent",
                hover_color=("#E8F2FC", "#204965"),
                text_color=self.TEXT, font=("Segoe UI", 11, "bold")
            )
            btn.pack(side="left", padx=2, pady=2)
            btn._fluent_no_press = True
            btn._fluent_no_focus_ring = True
            self.tab_buttons[name] = btn

        # Ponto vermelho real: Canvas + oval evita o efeito de "cilindro"
        # do CTkLabel em dimensões muito pequenas.
        self._historico_notificacao_badge = self._criar_ponto_notificacao(
            self.tab_buttons["Histórico"],
            self._fundo_ponto_notificacao(self.tab_buttons["Histórico"]),
        )
        self._historico_notificacao_badge.place_forget()
        self._historico_notificacao_badge.bind(
            "<Button-1>",
            lambda _e: self._selecionar_aba("Histórico"),
            add="+",
        )
        tabs.bind("<Configure>", self._reposicionar_badge_historico, add="+")
        self.app.after_idle(self._reposicionar_badge_historico)
        self.app.after_idle(self._sincronizar_pontos_notificacao)

        self.tab_area = ctk.CTkFrame(activity_card, fg_color="transparent")
        self.tab_area.pack(fill="both", expand=True, padx=14, pady=(0, 5))

        self.aba_atividade = ctk.CTkFrame(self.tab_area, fg_color="transparent")
        self.aba_historico = ctk.CTkFrame(self.tab_area, fg_color="transparent")

        # Activity tab
        self.atividade = ctk.CTkTextbox(
            self.aba_atividade, height=90, corner_radius=8,
            fg_color=("#FAFAFA", "#252A2F"), border_width=1, border_color=self.BORDER,
            text_color=self.TEXT, font=("Consolas", 10), wrap="word"
        )
        self.atividade.pack(fill="both", expand=True)
        self.atividade.configure(state="disabled")

        # History tab: executions shown as expandable folders.
        history_header = ctk.CTkFrame(self.aba_historico, fg_color="transparent")
        history_header.pack(fill="x", pady=(0, 5))
        self.botao_apagar_historico_selecionados = ctk.CTkButton(
            history_header, text="Apagar selecionados", command=self._apagar_historico_selecionados,
            width=128, height=28, corner_radius=8,
            fg_color=self.CARD, hover_color=("#FDECEC", "#3A2424"),
            border_width=1, border_color=self.ERROR, text_color=self.ERROR,
            font=("Segoe UI", 11, "bold")
        )
        self.botao_apagar_historico_selecionados.pack(side="right", padx=(0, 6))
        self.botao_apagar_historico_selecionados.pack_forget()

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
        self.historico_lista.bind("<Escape>", self._limpar_selecao_historico, add="+")

        self._restaurar_historico_na_tela()

        self._selecionar_aba("Atividade")

        actions = ctk.CTkFrame(
            self.app,
            fg_color="transparent",
            corner_radius=0,
            height=68,
        )
        actions.pack(fill="x", side="bottom")
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
            buttons,
            text=self.INICIAR_LABEL,
            command=self.iniciar_thread,
            width=150,
            height=46,
            corner_radius=8,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER,
            text_color="#FFFFFF",
            border_width=0,
            font=("Segoe UI", 14, "bold"),
        )
        self.botao_iniciar.pack(side="left")

        # Tooltips passam a ser gerenciados globalmente pela camada visual da Etapa 7.
        _ui_scan_tooltips(self.app)
        self._atualizar_contador_arquivos()
        self._add_activity("Sistema pronto para iniciar.", self.INFO)
        self._aplicar_status("Pronto")
        self.app.after(350, self._verificar_retomada_pendente)
        self._agendar_verificacao_atualizacao()




    def _configurar_dashboard_compacto(self):
        """Cria a dashboard mínima da visualização Compacta."""
        self.app.title("SM AutoLab")
        largura, altura = 500, 270
        self.app.geometry(f"{largura}x{altura}")
        self.app.minsize(largura, altura)
        self.app.maxsize(largura, altura)
        self.app.resizable(False, False)
        self.app.configure(fg_color=self.BG)
        self.app.protocol("WM_DELETE_WINDOW", self._fechar_aplicativo)
        try:
            desabilitar_transicoes_dwm(self.app)
        except Exception:
            pass

        self.app.update_idletasks()
        tela_w = self.app.winfo_screenwidth()
        tela_h = self.app.winfo_screenheight()
        x = max((tela_w - largura) // 2, 0)
        y = max((tela_h - altura) // 2, 0)
        self.app.geometry(f"{largura}x{altura}+{x}+{y}")

        header = ctk.CTkFrame(
            self.app, fg_color=self.CARD, corner_radius=0, height=58
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(side="left", anchor="w", padx=16, pady=(9, 0))
        ctk.CTkLabel(
            title_row, text="SM AutoLab", text_color=self.TEXT,
            font=("Segoe UI", 20, "bold")
        ).pack(side="left")
        ctk.CTkLabel(
            title_row, text=f"v{APP_VERSION}", text_color=self.SUBTEXT,
            font=("Segoe UI", 10, "bold")
        ).pack(side="left", padx=(8, 0), pady=(6, 0))

        self.botao_configuracoes = ctk.CTkButton(
            header,
            text="Configurações",
            command=self._alternar_menu_configuracoes,
            width=124,
            height=36,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 11, "bold"),
        )
        self.botao_configuracoes.pack(side="right", padx=12, pady=11)

        progress_area = ctk.CTkFrame(self.app, fg_color="transparent")
        progress_area.pack(fill="x", padx=18, pady=(7, 0))

        progress_header = ctk.CTkFrame(progress_area, fg_color="transparent", height=28)
        progress_header.pack(fill="x")
        progress_header.pack_propagate(False)

        ctk.CTkLabel(
            progress_header,
            text="Progresso",
            text_color=self.TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(side="left")

        self.percentual_label = ctk.CTkLabel(
            progress_header,
            text="0%",
            text_color=self.TEXT,
            font=("Segoe UI", 20, "bold"),
        )
        self.percentual_label.pack(side="right")

        # Mesma barra do modo completo.
        self.progresso = ctk.CTkProgressBar(
            progress_area,
            height=10,
            corner_radius=5,
            fg_color=self.BORDER,
            progress_color=self.ACCENT,
        )
        self.progresso.set(0)
        self.progresso.pack(fill="x", pady=(0, 2))

        self.progresso_label = ctk.CTkLabel(
            progress_area,
            text="0 / 0",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 12),
        )
        self.progresso_label.pack(anchor="w")

        self._execucao_progresso_card = None

        # Elementos opcionais do dashboard completo não existem no modo compacto.
        self.sucesso_card = None
        self.erro_card = None
        self.codigo_card = None
        self.atividade = None
        self.status_label = None
        self.status_text = None
        self.status_pill = None
        self.status_indicator = None

        actions = ctk.CTkFrame(self.app, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(18, 10))

        # Mantém os três botões como um único grupo centralizado.
        # 3 x 130 px + 2 x 6 px de espaçamento interno + 6 px de margem
        # em cada botão = 408 px, deixando margens externas idênticas.
        top_row = ctk.CTkFrame(
            actions,
            fg_color="transparent",
            width=408,
            height=44,
        )
        top_row.pack(anchor="center")
        top_row.pack_propagate(False)

        top_buttons = []
        for text_value, command in (
            ("Abrir", self.abrir_planilha),
            ("Arquivos", self.abrir_historico_planilha),
            ("Histórico", self._abrir_historico_compacto),
        ):
            button = ctk.CTkButton(
                top_row,
                text=text_value,
                command=command,
                width=130,
                height=38,
                corner_radius=8,
                fg_color=self.ACCENT if text_value == "Abrir" else self.CARD,
                hover_color=self.ACCENT_HOVER if text_value == "Abrir" else ("#EAF4FC", "#263F50"),
                border_width=0 if text_value == "Abrir" else 1,
                border_color=self.BORDER,
                text_color="#FFFFFF" if text_value == "Abrir" else self.TEXT,
                font=("Segoe UI", 11, "bold"),
            )
            button.pack(side="left", padx=3, pady=3)
            top_buttons.append(button)

        bottom_row = ctk.CTkFrame(actions, fg_color="transparent")
        bottom_row.pack(anchor="center", pady=(8, 0))

        # Mantém as ações principais do modo compacto com exatamente
        # as mesmas dimensões visuais do modo completo.
        self.botao_parar = ctk.CTkButton(
            bottom_row,
            text="Parar",
            command=self.parar,
            width=140,
            height=46,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#FDECEC", "#3A2424"),
            border_width=1,
            border_color=self.ERROR,
            text_color=self.ERROR,
            font=("Segoe UI", 11, "bold"),
            state="disabled",
        )
        self.botao_parar.pack(side="left", padx=3, pady=3)

        self.botao_iniciar = ctk.CTkButton(
            bottom_row,
            text=self.INICIAR_LABEL,
            command=self.iniciar_thread,
            width=150,
            height=46,
            corner_radius=8,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER,
            border_width=0,
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        )
        self.botao_iniciar.pack(side="left", padx=3, pady=3)

        self.botao_planilha = top_buttons[0]
        self.botao_historico_planilha = top_buttons[1]
        self.botao_historico_compacto = top_buttons[2]

        # Mesmo ponto vermelho real no modo compacto.
        self._historico_compacto_notificacao_badge = self._criar_ponto_notificacao(
            self.botao_historico_compacto,
            self._fundo_ponto_notificacao(self.botao_historico_compacto),
        )
        self._historico_compacto_notificacao_badge.place_forget()
        self.botao_historico_compacto.bind(
            "<Configure>", self._reposicionar_badge_historico_compacto, add="+"
        )
        top_row.bind(
            "<Configure>", self._reposicionar_badge_historico_compacto, add="+"
        )
        self.app.after_idle(self._reposicionar_badge_historico_compacto)
        self.app.after_idle(self._sincronizar_pontos_notificacao)
        self._atualizar_badge_historico()

        _ui_scan_tooltips(self.app)
        self._atualizar_contador_arquivos()
        self.app.after(350, self._verificar_retomada_pendente)
        self.app.after(1200, self._verificar_atualizacao_automatica)

    def _abrir_historico_compacto(self):
        # Recalcula antes de abrir para nunca deixar um badge órfão visível.
        self._atualizar_badge_historico()
        win = getattr(self, "_historico_compacto_window", None)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.lift()
                    self._atualizar_badge_historico()
                    return
            except Exception:
                pass

        win = ctk.CTkToplevel(self.app)
        self._historico_compacto_window = win
        self._configurar_icone_janela(win)
        win.title("Histórico")
        win.geometry("700x390")
        win.minsize(620, 330)
        win.resizable(True, True)
        win.transient(self.app)
        self._centralizar_janela(win, 700, 390)

        header = ctk.CTkFrame(
            win, fg_color=self.CARD, corner_radius=0, height=52
        )
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="Histórico",
            text_color=self.TEXT,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left", padx=14, pady=10)

        lista = ctk.CTkScrollableFrame(
            win,
            fg_color=self.BG,
            corner_radius=0,
            scrollbar_button_color=("#C8C8C8", "#626262"),
            scrollbar_button_hover_color=("#AFAFAF", "#777777"),
        )
        lista.pack(fill="both", expand=True, padx=10, pady=10)

        # Usa exatamente a mesma fonte de dados do histórico normal, incluindo
        # uma execução atual que já possua códigos não executados.
        itens = self._historico_execucoes_visiveis()
        self._atualizar_badge_historico()

        if not itens:
            ctk.CTkLabel(
                lista,
                text="Nenhuma execução com códigos não executados registrada ainda.",
                text_color=self.SUBTEXT,
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=8, pady=10)
        else:
            grid = ctk.CTkFrame(lista, fg_color="transparent")
            grid.pack(fill="x", padx=2, pady=2)

            headers = (
                "Data",
                "Hora",
                "",
                "Processados",
                "Executados",
                "Erros",
                "Status",
                "",
                "",
            )
            widths = HISTORICO_COL_MINS
            weights = HISTORICO_COL_PESOS

            for col, (label_text, width, weight) in enumerate(
                zip(headers, widths, weights)
            ):
                grid.grid_columnconfigure(
                    col,
                    minsize=width,
                    weight=weight,
                    uniform="historico_compacto",
                )
                if label_text:
                    ctk.CTkLabel(
                        grid,
                        text=label_text,
                        text_color=self.SUBTEXT,
                        font=("Segoe UI", 9, "bold"),
                        anchor="center",
                    ).grid(
                        row=0,
                        column=col,
                        sticky="ew",
                        padx=4,
                        pady=(2, 4),
                    )

            for row_index, item in enumerate(reversed(itens), start=1):
                inicio = str(item.get("inicio", "") or "")
                data = self._formatar_data_historico(inicio)
                horario = inicio.split(" ", 1)[1] if " " in inicio else ""

                try:
                    total = int(
                        item.get("total", 0)
                        or item.get("processados", 0)
                        or 0
                    )
                except (TypeError, ValueError):
                    total = 0

                try:
                    executados = int(item.get("sucessos", 0) or 0)
                except (TypeError, ValueError):
                    executados = 0

                try:
                    erros = max(
                        int(item.get("erros", 0) or 0),
                        len(item.get("codigos_erros", []) or []),
                        len(item.get("erros_detalhes", []) or []),
                    )
                except (TypeError, ValueError):
                    erros = 0

                status = str(item.get("status", "") or "Erro").strip() or "Erro"
                if len(status) > 18:
                    status = status[:17] + "…"
                pendente = self._historico_tem_erros_pendentes_reexecucao(item)

                row = ctk.CTkFrame(
                    grid,
                    fg_color=self.CARD,
                    corner_radius=7,
                    border_width=1,
                    border_color=self.BORDER,
                    height=42,
                )
                row.grid(
                    row=row_index,
                    column=0,
                    columnspan=9,
                    sticky="ew",
                    pady=2,
                )
                row.grid_propagate(False)

                for col, (width, weight) in enumerate(zip(widths, weights)):
                    row.grid_columnconfigure(
                        col,
                        minsize=width,
                        weight=weight,
                        uniform="historico_compacto_row",
                    )

                valores = (
                    (data, "center"),
                    (horario, "center"),
                    ("", "center"),
                    (str(total), "center"),
                    (str(executados), "center"),
                    (str(erros), "center"),
                    (status, "center"),
                )
                labels = []
                for col, (valor, anchor) in enumerate(valores):
                    if col == 3:       # Processados
                        cor = self.INFO
                    elif col == 4:     # Executados
                        cor = self.SUCCESS
                    elif col == 5:     # Erros
                        cor = self.ERROR
                    else:
                        cor = self.TEXT

                    label = ctk.CTkLabel(
                        row,
                        text=valor,
                        text_color=cor,
                        font=("Segoe UI", 9, "normal"),
                        anchor=anchor,
                    )
                    label.grid(
                        row=0,
                        column=col,
                        sticky="ew",
                        padx=5,
                        pady=2,
                    )
                    labels.append(label)

                indicador = self._criar_ponto_notificacao(
                    row,
                    self._cor(self.CARD),
                )
                if pendente:
                    indicador.place(
                        relx=1.0,
                        rely=0.5,
                        x=-3,
                        anchor="e",
                    )
                else:
                    indicador.place_forget()

                abrir_detalhe = (
                    lambda _e, execucao=item:
                    self._abrir_detalhe_historico(execucao)
                )
                for child in (row, *labels):
                    child.bind("<Button-1>", abrir_detalhe, add="+")
                    try:
                        child.configure(cursor="hand2")
                    except Exception:
                        pass
                indicador.bind("<Button-1>", abrir_detalhe, add="+")
                try:
                    indicador.configure(cursor="hand2")
                except Exception:
                    pass

        def fechar():
            self._historico_compacto_window = None
            try:
                win.destroy()
            except Exception:
                pass

        win.protocol("WM_DELETE_WINDOW", fechar)
        win.bind("<Control-KeyPress-f>", self._abrir_busca_historico_execucoes, add="+")
        win.bind("<Control-KeyPress-F>", self._abrir_busca_historico_execucoes, add="+")
        _ui_scan_tooltips(win)

    def _reposicionar_menus(self, _event=None):
        if self._closing:
            return
        if _event is not None:
            if getattr(self, "_menu_reposition_job", None) is not None:
                return
            try:
                self._menu_reposition_job = self.app.after_idle(self._reposicionar_menus)
            except Exception:
                self._menu_reposition_job = None
            return

        self._menu_reposition_job = None
        try:
            if self._menu_config is not None and self._menu_config.winfo_exists():
                app_x = self.app.winfo_rootx()
                app_y = self.app.winfo_rooty()
                bx = self.botao_configuracoes.winfo_rootx() - app_x
                by = self.botao_configuracoes.winfo_rooty() - app_y + self.botao_configuracoes.winfo_height() + 4
                menu_width = max(218, self._menu_config.winfo_reqwidth())
                menu_height = max(1, self._menu_config.winfo_reqheight())
                app_width = max(1, self.app.winfo_width())
                app_height = max(1, self.app.winfo_height())

                # O menu é sempre ancorado ao botão Configurações.
                # Assim, a posição não muda incorretamente ao alternar entre
                # a visualização Completa e a Compacta.
                menu_x = bx
                if menu_x + menu_width > app_width - 6:
                    menu_x = max(6, app_width - menu_width - 6)
                menu_y = max(0, by)

                self._menu_config.place_configure(
                    x=int(menu_x),
                    y=int(menu_y),
                )
                self._menu_config.lift()

            if self._menu_aparencia is not None and self._menu_aparencia.winfo_exists():
                app_x = self.app.winfo_rootx()
                app_y = self.app.winfo_rooty()
                sub_width = max(225, self._menu_aparencia.winfo_reqwidth(), self._menu_aparencia.winfo_width())
                app_width = max(1, self.app.winfo_width())
                app_height = max(1, self.app.winfo_height())

                if self._menu_config is not None and self._menu_config.winfo_exists():
                    config_root_x = self._menu_config.winfo_rootx() - app_x
                    config_root_y = self._menu_config.winfo_rooty() - app_y
                    config_width = self._menu_config.winfo_width()
                    button_y = self._menu_aparencia_btn.winfo_rooty() - app_y if self._menu_aparencia_btn is not None else config_root_y
                    button_height = self._menu_aparencia_btn.winfo_height() if self._menu_aparencia_btn is not None else self._menu_config.winfo_height()
                    left_x = config_root_x - sub_width + 2
                    right_x = config_root_x + config_width - 2
                    if left_x >= 6:
                        x = left_x
                    else:
                        x = min(right_x, max(6, app_width - sub_width - 6))
                    submenu_height = max(1, self._menu_aparencia.winfo_reqheight())
                    if getattr(self, "_visualizacao", "complete") == "compact":
                        y = max(6, min(button_y, app_height - submenu_height - 6))
                    else:
                        y = max(6, button_y + max(0, (button_height - submenu_height) // 2))
                else:
                    button_x = self.botao_configuracoes.winfo_rootx() - app_x
                    button_y = self.botao_configuracoes.winfo_rooty() - app_y
                    button_width = self.botao_configuracoes.winfo_width()
                    x = button_x - sub_width + 2
                    if x < 6:
                        x = button_x + button_width - 2
                    x = min(x, max(6, app_width - sub_width - 6))
                    y = max(6, button_y)

                self._menu_aparencia.place_configure(x=int(x), y=int(y))
                self._menu_aparencia.lift()

            if self._menu_visualizacao is not None and self._menu_visualizacao.winfo_exists():
                app_x = self.app.winfo_rootx()
                app_y = self.app.winfo_rooty()
                sub_width = max(225, self._menu_visualizacao.winfo_reqwidth(), self._menu_visualizacao.winfo_width())
                app_width = max(1, self.app.winfo_width())
                app_height = max(1, self.app.winfo_height())
                if self._menu_config is not None and self._menu_config.winfo_exists():
                    config_root_x = self._menu_config.winfo_rootx() - app_x
                    config_root_y = self._menu_config.winfo_rooty() - app_y
                    config_width = self._menu_config.winfo_width()
                    btn = getattr(self, "_menu_visualizacao_btn", None)
                    button_y = btn.winfo_rooty() - app_y if btn is not None else config_root_y
                    button_height = btn.winfo_height() if btn is not None else self._menu_config.winfo_height()
                    left_x = config_root_x - sub_width + 2
                    right_x = config_root_x + config_width - 2
                    x = left_x if left_x >= 6 else min(right_x, max(6, app_width - sub_width - 6))
                    submenu_height = max(1, self._menu_visualizacao.winfo_reqheight())
                    if getattr(self, "_visualizacao", "complete") == "compact":
                        y = max(6, min(button_y, app_height - submenu_height - 6))
                    else:
                        y = max(6, button_y + max(0, (button_height - submenu_height) // 2))
                else:
                    btn_x = self.botao_configuracoes.winfo_rootx() - app_x
                    btn_y = self.botao_configuracoes.winfo_rooty() - app_y
                    btn_w = self.botao_configuracoes.winfo_width()
                    x = btn_x - sub_width + 2
                    if x < 6:
                        x = btn_x + btn_w - 2
                    x = min(x, max(6, app_width - sub_width - 6))
                    y = max(6, btn_y)
                self._menu_visualizacao.place_configure(x=int(x), y=int(y))
                self._menu_visualizacao.lift()

        except Exception:
            pass

    def _fixar_menu_configuracoes(self):
        self._mostrar_menu_configuracoes()

    def _agendar_verificacao_atualizacao(self):
        if self._startup_update_checked:
            info = self._startup_update_info
            self._startup_update_checked = False
            self._startup_update_info = None
            if info:
                self.app.after(250, lambda data=info: self._mostrar_resultado_atualizacao(data))
            return
        self.app.after(700, self._verificar_atualizacao_automatica)

    def _instalar_atalhos_teclado(self):
        try:
            self.app.bind("<Control-KeyPress-o>", self._atalho_abrir_planilha, add="+")
            self.app.bind("<Control-KeyPress-O>", self._atalho_abrir_planilha, add="+")
            self.app.bind("<Control-Return>", self._atalho_iniciar, add="+")
            self.app.bind("<Control-KP_Enter>", self._atalho_iniciar, add="+")
            self.app.bind("<Escape>", self._atalho_escape, add="+")
            self.app.bind("<Control-KeyPress-h>", self._atalho_historico, add="+")
            self.app.bind("<Control-KeyPress-H>", self._atalho_historico, add="+")
            self.app.bind("<Control-KeyPress-f>", self._atalho_buscar_contexto, add="+")
            self.app.bind("<Control-KeyPress-F>", self._atalho_buscar_contexto, add="+")
        except Exception:
            LOGGER.debug("Não foi possível instalar atalhos de teclado.", exc_info=True)

    def _atalho_abrir_planilha(self, _event=None):
        if self._closing:
            return "break"
        self.abrir_planilha()
        return "break"

    def _atalho_iniciar(self, _event=None):
        if self._closing or self._atualizacao_em_andamento:
            return "break"
        if getattr(self, "_planilha_window", None) is not None:
            try:
                if self._planilha_window.winfo_exists():
                    self._planilha_salvar_e_iniciar()
                    return "break"
            except Exception:
                pass
        self.iniciar_thread()
        return "break"

    def _atalho_escape(self, _event=None):
        if getattr(self, "_planilha_tem_entry_em_foco", lambda: False)():
            return
        if getattr(self, "_planilha_window", None) is not None:
            try:
                if self._planilha_window.winfo_exists():
                    return
            except Exception:
                pass
        if self._atualizacao_em_andamento:
            return "break"
        self._fechar_menus()
        if getattr(self, "_automacao_atual", None) is not None and not self._parar:
            self.parar()
        return "break"

    def _atalho_historico(self, _event=None):
        if self._closing:
            return "break"
        if getattr(self, "_visualizacao", "complete") == "compact":
            self._abrir_historico_compacto()
        else:
            try:
                self._selecionar_aba("Histórico")
            except Exception:
                pass
        return "break"

    def _atalho_buscar_contexto(self, _event=None):
        if self._closing:
            return "break"
        try:
            foco = self.app.focus_get()
            topo = foco.winfo_toplevel() if foco is not None else self.app
        except Exception:
            topo = self.app
        if topo is getattr(self, "_planilha_window", None):
            return self._abrir_busca_planilha()
        if topo is getattr(self, "_planilha_historico_window", None):
            return self._abrir_busca_arquivos()
        if topo is getattr(self, "_historico_compacto_window", None):
            return self._abrir_busca_historico_execucoes()
        return "break"

    def _abrir_busca_planilha(self, _event=None):
        win = getattr(self, "_planilha_window", None)
        if win is None:
            return "break"
        try:
            if not win.winfo_exists():
                return "break"
        except Exception:
            return "break"
        termo = simpledialog.askstring(
            "Localizar na planilha",
            "Digite o texto que deseja localizar:",
            parent=win,
        )
        termo = str(termo or "").strip()
        if not termo:
            return "break"
        termo_cf = termo.casefold()
        correspondencias = []
        for chave, valor in (self._planilha_data or {}).items():
            try:
                row, col = (int(part.strip()) for part in str(chave).split(","))
            except (TypeError, ValueError):
                continue
            if termo_cf in str(valor or "").casefold():
                correspondencias.append((row, col))
        correspondencias.sort()
        if not correspondencias:
            messagebox.showinfo(
                "Localizar",
                f'Nenhum resultado encontrado para "{termo}".',
                parent=win,
            )
            return "break"
        row, col = correspondencias[0]
        tree = getattr(self, "_planilha_tree", None)
        if tree is not None:
            try:
                self._planilha_fechar_edicao()
                self._planilha_definir_selecao(
                    {(row, col)}, active=(row, col), ctrl_multiselect=False
                )
                tree.focus(str(row))
                tree.see(str(row))
                tree.focus_set()
            except Exception:
                LOGGER.debug(
                    "Falha ao posicionar resultado da busca na planilha.",
                    exc_info=True,
                )
        return "break"

    def _abrir_busca_arquivos(self, _event=None):
        win = getattr(self, "_planilha_historico_window", None)
        if win is None:
            return "break"
        try:
            if not win.winfo_exists():
                return "break"
        except Exception:
            return "break"
        termo = simpledialog.askstring(
            "Localizar em Arquivos",
            "Digite o código, item, data, hora ou outro texto:",
            parent=win,
        )
        termo = str(termo or "").strip()
        if not termo:
            return "break"
        termo_cf = termo.casefold()
        resultados = []
        for item in reversed(self._carregar_historico_planilhas()):
            if not isinstance(item, dict):
                continue
            saved = str(item.get("saved_at", "") or "")
            try:
                dt = datetime.fromisoformat(saved)
                campos = (
                    dt.strftime("%d/%m/%Y"),
                    dt.strftime("%H:%M"),
                    dt.strftime("%d/%m/%Y %H:%M"),
                )
            except Exception:
                campos = (saved,)
            valores = [*campos, str(item.get("filled", "") or "")]
            cells = item.get("cells", {}) or {}
            if isinstance(cells, dict):
                valores.extend(str(valor) for valor in cells.values())
            if any(termo_cf in valor.casefold() for valor in valores):
                resultados.append(item)
        if not resultados:
            messagebox.showinfo(
                "Localizar",
                f'Nenhum resultado encontrado para "{termo}".',
                parent=win,
            )
            return "break"
        item = resultados[0]
        try:
            data = datetime.fromisoformat(str(item.get("saved_at", ""))).date()
        except Exception:
            data = None
        if data is not None:
            self._mostrar_planilhas_do_dia(
                data, destaque_id=str(item.get("id", ""))
            )
        return "break"

    def _abrir_busca_historico_execucoes(self, _event=None):
        win = getattr(self, "_historico_compacto_window", None)
        if win is None:
            return "break"
        try:
            if not win.winfo_exists():
                return "break"
        except Exception:
            return "break"
        termo = simpledialog.askstring(
            "Localizar no Histórico",
            "Digite o código, status, data ou outro texto:",
            parent=win,
        )
        termo = str(termo or "").strip()
        if not termo:
            return "break"
        termo_cf = termo.casefold()
        for item in reversed(self._historico_execucoes_visiveis()):
            valores = [
                str(item.get("inicio", "") or ""),
                str(item.get("fim", "") or ""),
                str(item.get("status", "") or ""),
                str(item.get("planilha", "") or ""),
                *self._historico_codigos_de_erro(item),
            ]
            if any(termo_cf in valor.casefold() for valor in valores):
                self._abrir_detalhe_historico(item)
                return "break"
        messagebox.showinfo(
            "Localizar",
            f'Nenhum resultado encontrado para "{termo}".',
            parent=win,
        )
        return "break"

    def _verificar_atualizacao_automatica(self):
        """Verifica silenciosamente se há uma Release mais nova.
        Só apresenta a tela de atualização quando existe versão superior
        com executável correspondente. Falhas de rede não interrompem o app.
        """
        if self._closing:
            return

        def worker():
            try:
                info = find_update(current_override=APP_VERSION)
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
                info=find_update(current_override=APP_VERSION)
                self.app.after(0,lambda:self._mostrar_resultado_atualizacao(info))
            except Exception as exc:
                self.app.after(0,lambda:self._mostrar_resultado_atualizacao({
                    "error":str(exc)
                }))

        import threading
        threading.Thread(target=worker,daemon=True).start()

    @staticmethod
    def _formatar_tamanho_atualizacao(valor):
        try:
            valor = float(valor)
        except (TypeError, ValueError):
            return "0 B"
        unidades = ("B", "KB", "MB", "GB")
        indice = 0
        while valor >= 1024 and indice < len(unidades) - 1:
            valor /= 1024
            indice += 1
        if indice == 0:
            return f"{int(valor)} {unidades[indice]}"
        return f"{valor:.1f} {unidades[indice]}"

    def _mostrar_progresso_atualizacao(self, version):
        self._atualizacao_em_andamento = True
        janela = getattr(self, "_atualizacao_janela", None)
        try:
            if janela is not None and janela.winfo_exists():
                janela.lift()
                return
        except Exception:
            pass

        janela = ctk.CTkToplevel(self.app)
        janela.title("Atualização")
        janela.geometry("430x165")
        janela.resizable(False, False)
        janela.transient(self.app)
        janela.grab_set()
        self._centralizar_janela(janela, 430, 165)
        try:
            janela.attributes("-topmost", True)
        except Exception:
            pass
        janela.protocol("WM_DELETE_WINDOW", lambda: None)
        janela.configure(fg_color=self.BG)

        ctk.CTkLabel(
            janela,
            text=f"Baixando atualização v{version}",
            text_color=self.TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=22, pady=(18, 3))

        label = ctk.CTkLabel(
            janela,
            text="Preparando download...",
            text_color=self.SUBTEXT,
            font=("Segoe UI", 10),
        )
        label.pack(anchor="w", padx=22, pady=(0, 8))

        barra = ctk.CTkProgressBar(
            janela,
            width=386,
            height=12,
            corner_radius=5,
            mode="determinate",
            progress_color=self.ACCENT,
        )
        barra.set(0)
        barra.pack(padx=22, pady=(0, 5))

        self._atualizacao_janela = janela
        self._atualizacao_barra = barra
        self._atualizacao_label = label

        # Garante que a janela e a barra sejam compostas antes de iniciar o
        # download em outra thread. O topmost é removido logo depois.
        try:
            janela.update_idletasks()
            janela.deiconify()
            janela.lift()
            janela.focus_force()
            janela.update()
            janela.after(250, lambda: janela.attributes("-topmost", False))
        except Exception:
            pass

    def _atualizacao_atualizar_progresso(self, baixado, total):
        janela = getattr(self, "_atualizacao_janela", None)
        barra = getattr(self, "_atualizacao_barra", None)
        label = getattr(self, "_atualizacao_label", None)
        if janela is None or barra is None or label is None:
            return
        try:
            if total and total > 0:
                proporcao = max(0.0, min(1.0, float(baixado) / float(total)))
                barra.set(proporcao)
                label.configure(
                    text=(
                        f"{proporcao * 100:.0f}%  •  "
                        f"{self._formatar_tamanho_atualizacao(baixado)} de "
                        f"{self._formatar_tamanho_atualizacao(total)}"
                    )
                )
            else:
                label.configure(
                    text=f"{self._formatar_tamanho_atualizacao(baixado)} baixados"
                )
        except Exception:
            pass

    def _fechar_progresso_atualizacao(self):
        janela = getattr(self, "_atualizacao_janela", None)
        self._atualizacao_janela = None
        self._atualizacao_barra = None
        self._atualizacao_label = None
        if janela is not None:
            try:
                janela.grab_release()
            except Exception:
                pass
            try:
                janela.destroy()
            except Exception:
                pass

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

        self._mostrar_progresso_atualizacao(version)

        def progresso(baixado, total):
            try:
                self.app.after(
                    0,
                    lambda d=baixado, t=total: self._atualizacao_atualizar_progresso(d, t),
                )
            except Exception:
                pass

        def finalizar_download(ok, msg):
            self._atualizacao_em_andamento = False
            if not ok:
                self._fechar_progresso_atualizacao()
                messagebox.showerror(
                    "Atualização",
                    f"Não foi possível baixar a atualização.\n\n{msg}",
                    parent=self.app
                )
                return
            try:
                if self._atualizacao_label is not None:
                    self._atualizacao_label.configure(
                        text=f"Download concluído • verificando v{version}..."
                    )
                if self._atualizacao_barra is not None:
                    self._atualizacao_barra.set(1)
                self.app.update_idletasks()
            except Exception:
                pass

            def concluir():
                self._fechar_progresso_atualizacao()
                self._add_activity(
                    f"Atualização para v{version} verificada e pronta para reiniciar.",
                    self.INFO
                )
                self._fechar_aplicativo()

            self.app.after(180, concluir)

        def worker():
            ok, msg = launch_updater(info, progress_callback=progresso)
            try:
                self.app.after(0, lambda: finalizar_download(ok, msg))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

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

    def _configurar_hover_menu(self, root):
        """Mantém os menus responsivos ao movimento do ponteiro."""
        if root is None:
            return
        for widget in self._iterar_descendentes_ui(root):
            try:
                widget.bind("<Enter>", self._cancelar_fechar_menus, add="+")
            except Exception:
                pass

    def _widget_recebe_pointer(self, widget):
        if widget is None:
            return False
        try:
            if not widget.winfo_exists():
                return False
            x = widget.winfo_pointerx()
            y = widget.winfo_pointery()
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            return left <= x < left + widget.winfo_width() and top <= y < top + widget.winfo_height()
        except Exception:
            return False

    def _pointer_no_menu_config(self):
        return self._widget_recebe_pointer(getattr(self, "_menu_config", None))

    def _pointer_no_menu_aparencia(self):
        return self._widget_recebe_pointer(getattr(self, "_menu_aparencia", None))

    def _pointer_no_botao_aparencia(self):
        return self._widget_recebe_pointer(getattr(self, "_menu_aparencia_btn", None))

    def _pointer_no_menu_visualizacao(self):
        return self._widget_recebe_pointer(getattr(self, "_menu_visualizacao", None))

    def _pointer_no_botao_visualizacao(self):
        return self._widget_recebe_pointer(getattr(self, "_menu_visualizacao_btn", None))

    def _pointer_em_area_dos_menus(self):
        return (
            self._pointer_no_menu_config()
            or self._pointer_no_menu_aparencia()
            or self._pointer_no_botao_aparencia()
            or self._pointer_no_menu_visualizacao()
            or self._pointer_no_botao_visualizacao()
            or self._widget_recebe_pointer(getattr(self, "botao_configuracoes", None))
        )

    def _ativar_clique_fora_menus(self):
        if self._menu_monitor_job is None:
            self._menu_monitor_job = self.app.after(80, self._monitorar_menus)

    def _desativar_clique_fora_menus(self):
        job = self._menu_monitor_job
        self._menu_monitor_job = None
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass

    def _clique_fora_menus(self, _event=None):
        if not self._pointer_em_area_dos_menus():
            self._fechar_menus()

    def _monitorar_menus(self):
        self._menu_monitor_job = None
        config_aberto = self._menu_config is not None and self._menu_config.winfo_exists()
        sub_aberto = self._menu_aparencia is not None and self._menu_aparencia.winfo_exists()
        vis_aberto = self._menu_visualizacao is not None and self._menu_visualizacao.winfo_exists()
        if not config_aberto and not sub_aberto and not vis_aberto:
            return

        if not self._pointer_em_area_dos_menus():
            self._fechar_menus()
            return

        if sub_aberto:
            if self._pointer_no_menu_aparencia() or self._pointer_no_botao_aparencia():
                self._cancelar_fechar_aparencia()
            else:
                self._agendar_fechar_aparencia()

        if vis_aberto:
            if self._pointer_no_menu_visualizacao() or self._pointer_no_botao_visualizacao():
                self._cancelar_fechar_visualizacao()
            else:
                self._agendar_fechar_visualizacao()

        self._menu_monitor_job = self.app.after(100, self._monitorar_menus)

    def _fechar_menu_aparencia(self):
        self._cancelar_fechar_aparencia()
        sub = getattr(self, "_menu_aparencia", None)
        if sub is not None:
            try:
                if sub.winfo_exists():
                    sub.destroy()
            except Exception:
                pass
        self._menu_aparencia = None

    def _cancelar_fechar_aparencia(self, _event=None):
        job = getattr(self, "_menu_aparencia_close_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
            self._menu_aparencia_close_job = None

    def _agendar_fechar_aparencia(self, _event=None):
        if self._menu_aparencia_close_job is not None:
            return
        try:
            self._menu_aparencia_close_job = self.app.after(120, self._fechar_aparencia_se_fora)
        except Exception:
            self._menu_aparencia_close_job = None

    def _fechar_aparencia_se_fora(self):
        self._menu_aparencia_close_job = None
        if not self._pointer_no_menu_aparencia() and not self._pointer_no_botao_aparencia():
            self._fechar_menu_aparencia()

    def _cancelar_fechar_visualizacao(self, _event=None):
        job = getattr(self, "_menu_visualizacao_close_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
            self._menu_visualizacao_close_job = None

    def _agendar_fechar_visualizacao(self, _event=None):
        if self._menu_visualizacao_close_job is not None:
            return
        try:
            self._menu_visualizacao_close_job = self.app.after(120, self._fechar_visualizacao_se_fora)
        except Exception:
            self._menu_visualizacao_close_job = None

    def _fechar_visualizacao_se_fora(self):
        self._menu_visualizacao_close_job = None
        if not self._pointer_no_menu_visualizacao() and not self._pointer_no_botao_visualizacao():
            self._fechar_menu_visualizacao()

    def _fechar_menu_visualizacao(self):
        self._cancelar_fechar_visualizacao()
        sub = getattr(self, "_menu_visualizacao", None)
        if sub is not None:
            try:
                if sub.winfo_exists():
                    sub.destroy()
            except Exception:
                pass
        self._menu_visualizacao = None

    def _mostrar_menu_configuracoes(self, _event=None):
        """Abre o menu principal de configurações sem bindings concorrentes."""
        self._cancelar_fechar_menus()

        if self._menu_config is not None:
            try:
                if self._menu_config.winfo_exists():
                    self._reposicionar_menus()
                    self._menu_config.lift()
                    return
            except Exception:
                self._menu_config = None

        menu = ctk.CTkFrame(
            self.app,
            fg_color=self.CARD,
            corner_radius=10,
            border_width=1,
            border_color=self.BORDER,
            width=218,
            height=210,
        )
        menu.place_forget()
        menu.pack_propagate(False)
        self._menu_config = menu

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
            anchor="w",
        )
        aparencia.pack(fill="x", padx=7, pady=(3, 3))
        self._menu_aparencia_btn = aparencia

        self._configurar_hover_menu(self._menu_config)
        self._ativar_clique_fora_menus()
        if self._menu_reposition_binding is None:
            self._menu_reposition_binding = self.app.bind(
                "<Configure>", self._reposicionar_menus, add="+"
            )
        aparencia.bind("<Enter>", self._mostrar_menu_aparencia, add="+")
        aparencia.bind("<Enter>", self._cancelar_fechar_aparencia, add="+")
        aparencia.bind("<Leave>", self._agendar_fechar_aparencia, add="+")
        for widget in self._iterar_descendentes_ui(aparencia):
            if widget is aparencia:
                continue
            try:
                widget.bind("<Enter>", self._mostrar_menu_aparencia, add="+")
                widget.bind("<Leave>", self._agendar_fechar_aparencia, add="+")
            except Exception:
                pass
        visualizacao = ctk.CTkButton(
            menu,
            text="Visualização  ›",
            command=self._mostrar_menu_visualizacao,
            width=202,
            height=40,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            text_color=self.TEXT,
            font=("Segoe UI", 12),
            anchor="w",
        )
        visualizacao.pack(fill="x", padx=7, pady=(3, 3))
        self._menu_visualizacao_btn = visualizacao
        visualizacao.bind("<Enter>", self._mostrar_menu_visualizacao, add="+")
        visualizacao.bind("<Enter>", self._cancelar_fechar_visualizacao, add="+")
        visualizacao.bind("<Leave>", self._agendar_fechar_visualizacao, add="+")
        for widget in self._iterar_descendentes_ui(visualizacao):
            if widget is visualizacao:
                continue
            try:
                widget.bind("<Enter>", self._mostrar_menu_visualizacao, add="+")
                widget.bind("<Leave>", self._agendar_fechar_visualizacao, add="+")
            except Exception:
                pass

        mudar = ctk.CTkButton(
            menu,
            text="Ajustes do Feegow",
            command=self._abrir_popup_feegow,
            width=202,
            height=40,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            text_color=self.TEXT,
            font=("Segoe UI", 12),
            anchor="w",
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
            anchor="w",
        )
        atualizar.pack(fill="x", padx=7, pady=(8, 3))

        _ui_scan_tooltips(self._menu_config)

        self.app.update_idletasks()
        self._reposicionar_menus()

    def _garantir_menu_aparencia_aberto_se_hover(self, event=None):
        return self._mostrar_menu_aparencia(event)

    def _garantir_menu_aparencia_aberto(self):
        if self._menu_config is None or not self._menu_config.winfo_exists():
            self._mostrar_menu_configuracoes()
        if self._menu_aparencia is None or not self._menu_aparencia.winfo_exists():
            self._mostrar_menu_aparencia()


    def _mostrar_menu_visualizacao(self, _event=None):
        """Abre o submenu de visualização no mesmo padrão de Aparência."""
        self._cancelar_fechar_menus()
        self._fechar_menu_aparencia()
        self._cancelar_fechar_visualizacao()

        if self._menu_config is None or not self._menu_config.winfo_exists():
            self._mostrar_menu_configuracoes()
            self.app.after_idle(lambda: self._mostrar_menu_visualizacao())
            return

        if self._menu_visualizacao is not None:
            try:
                if self._menu_visualizacao.winfo_exists():
                    self._reposicionar_menus()
                    self._menu_visualizacao.lift()
                    return
            except Exception:
                self._menu_visualizacao = None

        sub = ctk.CTkFrame(
            self.app, fg_color=self.CARD, corner_radius=10,
            border_width=1, border_color=self.BORDER, width=225, height=118
        )
        sub.place_forget()
        sub.pack_propagate(False)
        self._menu_visualizacao = sub

        ctk.CTkLabel(
            sub, text="Visualização", text_color=self.TEXT,
            font=("Segoe UI", 12, "bold"), anchor="w"
        ).pack(fill="x", padx=12, pady=(9, 4))

        for modo in ("complete", "compact"):
            rotulo = self.VIEW_LABELS[modo]
            marcado = "✓  " if modo == self._visualizacao else "    "
            btn = ctk.CTkButton(
                sub,
                text=marcado + rotulo,
                command=lambda m=modo: self._selecionar_visualizacao(m),
                width=210, height=34, corner_radius=8,
                fg_color=("#E5F1FB", "#183B54") if modo == self._visualizacao else self.CARD,
                hover_color=("#EAF4FC", "#263F50"),
                text_color=self.ACCENT if modo == self._visualizacao else self.TEXT,
                font=("Segoe UI", 11, "bold") if modo == self._visualizacao else ("Segoe UI", 11),
                anchor="w",
            )
            btn.pack(fill="x", padx=6, pady=2)

        self._configurar_hover_menu(sub)
        for widget in self._iterar_descendentes_ui(sub):
            try:
                widget.bind("<Enter>", self._cancelar_fechar_visualizacao, add="+")
                widget.bind("<Leave>", self._agendar_fechar_visualizacao, add="+")
            except Exception:
                pass
        _ui_scan_tooltips(sub)

        self.app.update_idletasks()
        self._reposicionar_menus()

    def _selecionar_visualizacao(self, visualizacao):
        if visualizacao not in ("complete", "compact"):
            return
        if visualizacao == self._visualizacao:
            self._fechar_menus()
            return

        self._visualizacao = visualizacao
        self._salvar_estado_persistente()
        self._fechar_menus()
        self._perguntar_reinicio_visualizacao()

    def _perguntar_reinicio_visualizacao(self):
        """Pergunta se a nova visualização deve ser aplicada imediatamente."""
        dialog = ctk.CTkToplevel(self.app)
        self._visualizacao_reinicio_dialog = dialog
        self._configurar_icone_janela(dialog)
        dialog.title("Visualização alterada")
        dialog.geometry("340x160")
        dialog.resizable(False, False)
        dialog.transient(self.app)
        dialog.grab_set()
        self._centralizar_janela(dialog, 340, 160)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)

        body = ctk.CTkFrame(dialog, fg_color=self.BG)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        ctk.CTkLabel(
            body,
            text=f"A visualização {self.VIEW_LABELS[self._visualizacao]} foi selecionada.",
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold"),
            wraplength=290,
        ).pack(anchor="w", pady=(0, 7))

        ctk.CTkLabel(
            body,
            text="Deseja reiniciar agora para aplicar a mudança?",
            text_color=self.TEXT,
            font=("Segoe UI", 11),
            wraplength=340,
        ).pack(anchor="w")

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", side="bottom", pady=(12, 0))

        def depois():
            try:
                dialog.grab_release()
            except Exception:
                pass
            try:
                dialog.destroy()
            except Exception:
                pass
            self._visualizacao_reinicio_dialog = None

        def reiniciar():
            try:
                dialog.grab_release()
            except Exception:
                pass
            try:
                dialog.destroy()
            except Exception:
                pass
            self._visualizacao_reinicio_dialog = None
            self._reiniciar_aplicativo()

        ctk.CTkButton(
            actions,
            text="Depois",
            command=depois,
            width=95,
            height=34,
            corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#EAF4FC", "#263F50"),
            border_width=1,
            border_color=self.BORDER,
            text_color=self.TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="right")

        ctk.CTkButton(
            actions,
            text="Reiniciar",
            command=reiniciar,
            width=105,
            height=36,
            corner_radius=8,
            fg_color=self.ACCENT,
            hover_color=self.ACCENT_HOVER,
            text_color="#FFFFFF",
            font=("Segoe UI", 11, "bold"),
        ).pack(side="right", padx=(0, 8))

        _ui_scan_tooltips(dialog)

    def _reiniciar_aplicativo(self):
        """Reinicia a mesma instalação em uma nova instância independente."""
        try:
            self._salvar_estado_persistente()
            executable = Path(sys.executable).resolve()
            if executable.suffix.lower() != ".exe" or not getattr(sys, "frozen", False):
                raise RuntimeError(
                    "O reinício automático exige a versão executável do SM AutoLab."
                )

            env = _prepare_independent_restart_environment()
            flags = 0
            startupinfo = None
            if os.name == "nt":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

            subprocess.Popen(
                [str(executable), *sys.argv[1:]],
                cwd=str(executable.parent),
                close_fds=True,
                creationflags=flags,
                startupinfo=startupinfo,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=env,
                shell=False,
            )
        except Exception as exc:
            messagebox.showerror(
                "Não foi possível reiniciar",
                f"O modo foi salvo, mas o aplicativo não pôde ser reiniciado automaticamente.\n\n{exc}",
                parent=self.app,
            )
            return

        self._fechar_aplicativo()

    def _mostrar_menu_aparencia(self, _event=None):
        """Abre o submenu de aparência; um segundo clique não o fecha acidentalmente."""
        self._cancelar_fechar_menus()
        self._fechar_menu_visualizacao()
        self._cancelar_fechar_aparencia()

        if self._menu_config is None or not self._menu_config.winfo_exists():
            self._mostrar_menu_configuracoes()
            self.app.after_idle(lambda: self._mostrar_menu_aparencia())
            return

        if self._menu_aparencia is not None:
            try:
                if self._menu_aparencia.winfo_exists():
                    self._reposicionar_menus()
                    self._menu_aparencia.lift()
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
            height=158,
        )
        sub.place_forget()
        sub.pack_propagate(False)
        self._menu_aparencia = sub

        ctk.CTkLabel(
            sub,
            text="Aparência",
            text_color=self.TEXT,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x", padx=12, pady=(9, 4))

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
                anchor="w",
            )
            btn.pack(fill="x", padx=6, pady=2)

        self._configurar_hover_menu(sub)
        for widget in self._iterar_descendentes_ui(sub):
            try:
                widget.bind("<Enter>", self._cancelar_fechar_aparencia, add="+")
                widget.bind("<Leave>", self._agendar_fechar_aparencia, add="+")
            except Exception:
                pass
        _ui_scan_tooltips(sub)

        self.app.update_idletasks()
        self._reposicionar_menus()
    def _cancelar_fechar_menus(self, _event=None):
        if self._menu_close_job is not None:
            try:
                self.app.after_cancel(self._menu_close_job)
            except Exception:
                pass
            self._menu_close_job = None

    def _agendar_fechar_menus(self, _event=None):
        self._cancelar_fechar_menus()
        try:
            self._menu_close_job = self.app.after(180, self._fechar_menus_se_fora)
        except Exception:
            self._menu_close_job = None

    def _fechar_menus_se_fora(self):
        self._menu_close_job = None
        if not self._pointer_em_area_dos_menus():
            self._fechar_menus()

    def _fechar_menus(self):
        self._menu_close_job = None
        job = getattr(self, "_menu_reposition_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
            self._menu_reposition_job = None
        self._desativar_clique_fora_menus()
        binding = getattr(self, "_menu_reposition_binding", None)
        if binding:
            try:
                self.app.unbind("<Configure>", binding)
            except Exception:
                pass
        self._menu_reposition_binding = None
        hover_binding = getattr(self, "_config_hover_binding", None)
        if hover_binding:
            try:
                self.app.unbind("<Motion>", hover_binding)
            except Exception:
                pass
        self._config_hover_binding = None
        self._menu_aparencia_btn = None
        self._menu_visualizacao_btn = None
        self._cancelar_fechar_visualizacao()
        for attr in ("_menu_visualizacao", "_menu_aparencia", "_menu_config"):
            menu = getattr(self, attr, None)
            if menu is not None:
                try:
                    menu.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)

    def _sincronizar_tema_ui(self):
        if self._closing:
            return
        try:
            dark = str(ctk.get_appearance_mode()).lower() == "dark"
            janelas = (
                getattr(self, "app", None),
                getattr(self, "_planilha_window", None),
                getattr(self, "_planilha_historico_window", None),
                getattr(self, "_historico_compacto_window", None),
                getattr(self, "_visualizacao_reinicio_dialog", None),
            )
            for win in janelas:
                if win is None:
                    continue
                _ui_refresh_all_windows_scrollbars(win)
                atualizar_backdrop_tema(win, dark)
            self._atualizar_icones_cards_estatistica()
            self._sincronizar_pontos_notificacao()
            self._planilha_desenhar_cabecalho_linhas()
            self._planilha_desenhar_borda()
        except Exception:
            LOGGER.debug("Falha ao sincronizar widgets após mudança de tema.", exc_info=True)

    def _agendar_sincronizacao_tema(self):
        try:
            self.app.after_idle(self._sincronizar_tema_ui)
            self.app.after(80, self._sincronizar_tema_ui)
            self.app.after(220, self._sincronizar_tema_ui)
        except Exception:
            pass

    def _selecionar_tema(self, tema):
        if tema not in ("light", "dark", "system"):
            return
        self._tema = tema
        ctk.set_appearance_mode(tema)
        self._agendar_sincronizacao_tema()
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

            dados = carregar_configuracoes()
        except Exception:
            dados = {
                "SITE_URL": "https://franchising.feegow.com/pre-v8.1/extranet/?P=Login&Licenca=15003",
                "PORTAL_USUARIO": "",
                "PORTAL_SENHA": "",
            }

        popup = ctk.CTkToplevel(self.app)
        self._configurar_icone_janela(popup)
        popup.title("Ajustes do Feegow")
        popup.geometry("560x420")
        popup.resizable(False, False)
        popup.transient(self.app)
        popup.grab_set()
        popup.configure(fg_color=self.BG)
        self._centralizar_janela(popup, 560, 420)
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
            popup_header, text="Ajustes do Feegow",
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
        _ui_scan_tooltips(popup)

    def _historico_codigos_de_erro(self, execucao):
        if not isinstance(execucao, dict):
            return []
        fontes = [
            execucao.get("codigos_erros"),
            execucao.get("erros_codigos"),
            execucao.get("codigos_erro"),
            execucao.get("codigos"),
            execucao.get("codigo_erro"),
        ]
        detalhes = execucao.get("erros_detalhes") or []
        if isinstance(detalhes, list):
            fontes.append([
                item.get("codigo") or item.get("code")
                for item in detalhes
                if isinstance(item, dict)
            ])
        codigos = []
        for fonte in fontes:
            if isinstance(fonte, str):
                fonte = [fonte]
            for codigo in fonte or []:
                texto = str(codigo or "").strip()
                if texto and texto not in codigos:
                    codigos.append(texto)
        return codigos

    def _historico_tem_erros_pendentes_reexecucao(self, execucao):
        if not self._historico_execucao_tem_erros(execucao):
            return False
        codigos = self._historico_codigos_de_erro(execucao)
        if not codigos:
            # Contador de erros sem códigos concretos não representa nada que
            # o usuário possa reexecutar; portanto, não gera notificação.
            return False
        reexecutados = {
            str(c).strip()
            for c in (execucao.get("codigos_erros_reexecutados") or [])
            if str(c).strip()
        }
        return any(codigo not in reexecutados for codigo in codigos)

    def _historico_tem_erros_pendentes(self):
        return bool(self._historico_execucoes_visiveis())

    def _historico_execucoes_com_erros(self):
        """Retorna todas as execuções históricas que ainda possuem erro registrado."""
        fontes = list(getattr(self, "_historico_execucoes", []))
        atual = getattr(self, "_execucao_atual", None)
        if isinstance(atual, dict):
            fontes.append(atual)

        unicos = {}
        for item in fontes:
            if not isinstance(item, dict):
                continue
            if not self._historico_execucao_tem_erros(item):
                continue
            unicos[self._id_historico_execucao(item)] = item
        return list(unicos.values())

    def _historico_execucoes_visiveis(self):
        """Retorna somente as execuções que ainda possuem códigos reexecutáveis."""
        return [
            item
            for item in self._historico_execucoes_com_erros()
            if self._historico_tem_erros_pendentes_reexecucao(item)
        ]

    @staticmethod
    def _cor(valor):
        """Retorna uma cor única para widgets Tk que não aceitam tuplas."""
        if isinstance(valor, (tuple, list)):
            indice = 1 if str(ctk.get_appearance_mode()).lower() == "dark" else 0
            return str(valor[min(indice, len(valor) - 1)])
        return str(valor)

    def _fundo_ponto_notificacao(self, widget):
        """Obtém a cor efetivamente visível atrás do ponto."""
        atual = None
        try:
            atual = widget.cget("fg_color")
        except Exception:
            atual = None

        atual_widget = widget
        while atual is not None:
            valor = self._cor(atual)
            if valor.strip().lower() != "transparent":
                return valor
            try:
                atual_widget = atual_widget.master
                atual = atual_widget.cget("fg_color")
            except Exception:
                break

        return self._cor(self.CARD)

    def _sincronizar_pontos_notificacao(self):
        pares = (
            (
                getattr(self, "_historico_notificacao_badge", None),
                getattr(self, "tab_buttons", {}).get("Histórico"),
            ),
            (
                getattr(self, "_historico_compacto_notificacao_badge", None),
                getattr(self, "botao_historico_compacto", None),
            ),
        )
        for badge, btn in pares:
            if badge is None or btn is None:
                continue
            try:
                if not badge.winfo_exists() or not btn.winfo_exists():
                    continue
                badge.configure(bg=self._fundo_ponto_notificacao(btn))
                badge.itemconfigure(
                    1,
                    fill=self._cor(self.ERROR),
                    outline=self._cor(self.ERROR),
                )
            except Exception:
                LOGGER.debug("Falha ao sincronizar ponto de notificação.", exc_info=True)

    def _criar_ponto_notificacao(self, parent, fundo=None):
        ponto = Canvas(
            parent,
            width=7,
            height=7,
            highlightthickness=0,
            bd=0,
            relief="flat",
            bg=self._cor(fundo if fundo is not None else self.CARD),
        )
        ponto.create_oval(
            1, 1, 6, 6,
            fill=self._cor(self.ERROR),
            outline=self._cor(self.ERROR),
        )
        return ponto

    def _reposicionar_badge_historico(self, _event=None):
        badge = getattr(self, "_historico_notificacao_badge", None)
        btn = getattr(self, "tab_buttons", {}).get("Histórico")
        if badge is None or btn is None:
            return
        try:
            if not badge.winfo_exists() or not btn.winfo_exists():
                return
            if not self._historico_tem_erros_pendentes():
                badge.place_forget()
                return
            badge.place(
                relx=1.0,
                rely=0.0,
                x=-2,
                y=2,
                anchor="ne",
            )
            badge.lift()
        except Exception:
            pass

    def _reposicionar_badge_historico_compacto(self, _event=None):
        badge = getattr(self, "_historico_compacto_notificacao_badge", None)
        btn = getattr(self, "botao_historico_compacto", None)
        if badge is None or btn is None:
            return
        try:
            if not badge.winfo_exists() or not btn.winfo_exists():
                return
            if not self._historico_tem_erros_pendentes():
                badge.place_forget()
                return
            badge.place(
                relx=1.0,
                rely=0.0,
                x=-2,
                y=2,
                anchor="ne",
            )
            badge.lift()
        except Exception:
            pass

    def _atualizar_badge_historico(self):
        pendente = self._historico_tem_erros_pendentes()

        badge = getattr(self, "_historico_notificacao_badge", None)
        btn = getattr(self, "tab_buttons", {}).get("Histórico")
        if badge is not None and btn is not None:
            try:
                if pendente:
                    self._reposicionar_badge_historico()
                else:
                    badge.place_forget()
            except Exception:
                pass

        badge_compacto = getattr(self, "_historico_compacto_notificacao_badge", None)
        btn_compacto = getattr(self, "botao_historico_compacto", None)
        if badge_compacto is not None and btn_compacto is not None:
            try:
                if pendente:
                    self._reposicionar_badge_historico_compacto()
                else:
                    badge_compacto.place_forget()
            except Exception:
                pass

    def _selecionar_aba(self, nome):
        for frame in (self.aba_atividade, self.aba_historico):
            frame.pack_forget()
        mapa = {
            "Atividade": self.aba_atividade,
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
        self._sincronizar_pontos_notificacao()
        self._atualizar_badge_historico()

    def _card(self, parent):
        return ctk.CTkFrame(parent, fg_color=self.CARD, corner_radius=10,
                            border_width=1, border_color=self.BORDER)

    def _section_title(self, parent, text):
        ctk.CTkLabel(
            parent, text=text, text_color=self.TEXT,
            font=("Segoe UI", 16, "bold")
        ).pack(anchor="w", padx=14, pady=(10, 0))

    def _stat_card(self, parent, icon, title, value, accent):
        palettes = {
            "Executados": {
                "card": ("#EEF9F1", "#1E3325"),
                "border": ("#D4E6D9", "#132219"),
                "icon": ("#27AE60", "#2FAE63"),
                "title": ("#167A43", "#70D995"),
                "value": ("#123B27", "#ECFFF1"),
            },
            "Não executados": {
                "card": ("#FFF1F2", "#3A2528"),
                "border": ("#F0D7DA", "#241619"),
                "icon": ("#E53935", "#F15B5B"),
                "title": ("#C62828", "#FF8A8A"),
                "value": ("#541A1D", "#FFF0F0"),
            },
            "Código atual": {
                "card": ("#EEF6FF", "#1C2D3D"),
                "border": ("#D8E7F5", "#15222E"),
                "icon": ("#1976D2", "#3F9BEF"),
                "title": ("#125AA3", "#73B8FF"),
                "value": ("#102E4A", "#EDF7FF"),
            },
        }
        palette = palettes.get(
            str(title),
            {
                "card": self.CARD,
                "border": self.BORDER,
                "icon": self.CARD,
                "title": self.SUBTEXT,
                "value": self.TEXT,
            },
        )

        dark_mode = ctk.get_appearance_mode().lower() == "dark"
        card = ctk.CTkFrame(
            parent,
            fg_color=palette["card"],
            corner_radius=10,
            border_width=1,
            border_color=palette.get("border", self.BORDER),
            height=80,
        )
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=12, pady=8)

        icon_sizes = {"✓": 21, "!": 21, "▥": 21, "›": 21}
        icon_font = icon_sizes.get(str(icon), 21)
        icon_holder_size = 44
        icon_holder = Canvas(
            row,
            width=icon_holder_size,
            height=icon_holder_size,
            bd=0,
            highlightthickness=0,
            relief="flat",
            bg=self._cor_fluente(palette["card"]),
        )
        icon_holder.pack(side="left", padx=(0, 11))
        card._sm_stat_icon_canvas = icon_holder
        card._sm_stat_icon_data = (
            icon,
            icon_font,
            palette["card"],
            palette["icon"],
        )
        self._render_stat_icon(card)

        text_box = ctk.CTkFrame(row, fg_color="transparent")
        text_box.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(
            text_box,
            text=title,
            text_color=palette["title"],
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        value_font = ("Segoe UI", 15) if str(title) == "Código atual" else ("Segoe UI", 19, "bold")
        value_label = ctk.CTkLabel(
            text_box,
            text=value,
            text_color=palette["value"],
            font=value_font,
            anchor="w",
        )
        value_label.pack(anchor="w")
        card.value_label = value_label

        card_tooltips = {
            "Executados": "Mostra a quantidade de códigos executados com sucesso.",
            "Não executados": "Mostra a quantidade de códigos que apresentaram erro durante a execução.",
            "Código atual": "Mostra o código que está sendo processado no momento.",
        }
        card._sm_autolab_tooltip_message = card_tooltips.get(title, "")
        _ui_bind_card_hover(card, accent)
        if card._sm_autolab_tooltip_message:
            try:
                card._sm_autolab_tooltip = _SMAutoLabTooltip(
                    card,
                    card._sm_autolab_tooltip_message,
                    bind_children=True,
                )
            except Exception:
                card._sm_autolab_tooltip = None
        return card

    def _fonte_icone_estatistica(self, size):
        size = max(8, int(size))
        cached = self._stat_icon_font_cache.get(size)
        if cached is not None:
            return cached
        fonts_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        candidates = (
            fonts_dir / "segoeuib.ttf",
            fonts_dir / "segoeui.ttf",
            fonts_dir / "arial.ttf",
        )
        for path in candidates:
            try:
                if path.exists():
                    font = ImageFont.truetype(str(path), size)
                    self._stat_icon_font_cache[size] = font
                    return font
            except Exception:
                pass
        font = ImageFont.load_default()
        self._stat_icon_font_cache[size] = font
        return font

    def _criar_imagem_icone_estatistica(self, icon, icon_font, card_color, icon_color):
        scale = 4
        logical = 44
        size = logical * scale
        background = self._cor_fluente(card_color)
        foreground = self._cor_fluente(icon_color)
        image = Image.new("RGB", (size, size), background)
        draw = ImageDraw.Draw(image)
        draw.ellipse((scale, scale, size - scale - 1, size - scale - 1), fill=foreground)

        white = "#FFFFFF"
        stroke = max(2, 2 * scale)
        if str(icon) == "✓":
            draw.line(
                [(14 * scale, 23 * scale), (19 * scale, 29 * scale), (31 * scale, 16 * scale)],
                fill=white, width=stroke, joint="curve"
            )
        elif str(icon) == "▥":
            draw.rounded_rectangle(
                (15 * scale, 10 * scale, 29 * scale, 34 * scale),
                radius=2 * scale, outline=white, width=stroke
            )
            draw.line([(19 * scale, 17 * scale), (25 * scale, 17 * scale)], fill=white, width=scale)
            draw.line([(19 * scale, 22 * scale), (25 * scale, 22 * scale)], fill=white, width=scale)
        else:
            font = self._fonte_icone_estatistica(icon_font * scale)
            bbox = draw.textbbox((0, 0), str(icon), font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (size - text_width) / 2 - bbox[0]
            y = (size - text_height) / 2 - bbox[1]
            draw.text((x, y), str(icon), font=font, fill=white)

        return ImageTk.PhotoImage(image.resize((logical, logical), Image.Resampling.LANCZOS))

    def _render_stat_icon(self, card):
        canvas = getattr(card, "_sm_stat_icon_canvas", None)
        data = getattr(card, "_sm_stat_icon_data", None)
        if canvas is None or data is None:
            return
        icon, icon_font, card_color, icon_color = data
        try:
            photo = self._criar_imagem_icone_estatistica(
                icon, icon_font, card_color, icon_color
            )
            canvas.configure(bg=self._cor_fluente(card_color))
            canvas.delete("all")
            canvas.create_image(22, 22, image=photo)
            card._sm_stat_icon_photo = photo
        except Exception:
            pass

    def _atualizar_icones_cards_estatistica(self):
        for card in (
            getattr(self, "sucesso_card", None),
            getattr(self, "erro_card", None),
            getattr(self, "codigo_card", None),
        ):
            self._render_stat_icon(card)

    @staticmethod
    def _formatar_duracao(segundos):
        total = max(0, int(round(float(segundos or 0))))
        horas, resto = divmod(total, 3600)
        minutos, segundos = divmod(resto, 60)
        return f"{horas:02d}:{minutos:02d}:{segundos:02d}"

    def _iniciar_metricas_execucao(self, start, total):
        self._execucao_inicio_monotonic = time.monotonic()
        self._execucao_inicio_indice = int(start)
        self._execucao_total = int(total)
        self._ultimo_tempo_decorrido_segundos = 0.0
        self._ultimo_codigos_medidos = 0
        self._atualizar_metricas_execucao()

    def _parar_metricas_execucao(self):
        # Atualiza uma última vez antes de encerrar o cronômetro para preservar
        # os números exibidos na tela de Arquivos após a execução.
        if getattr(self, "_execucao_inicio_monotonic", None) is not None:
            try:
                self._atualizar_metricas_execucao()
            except Exception:
                pass

        job = getattr(self, "_execucao_timer_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
        self._execucao_timer_job = None
        self._execucao_inicio_monotonic = None

    def _atualizar_metricas_execucao(self):
        if self._closing:
            self._execucao_timer_job = None
            return
        inicio = getattr(self, "_execucao_inicio_monotonic", None)
        if inicio is None:
            return
        try:
            decorrido = max(0.0, time.monotonic() - inicio)
        except Exception:
            decorrido = 0.0

        processados = int(getattr(self, "_checkpoint_indice_seguro", 0))
        concluidos = max(0, processados - int(self._execucao_inicio_indice))
        self._ultimo_tempo_decorrido_segundos = decorrido
        self._ultimo_codigos_medidos = concluidos

        if self._tempo_decorrido_label is not None:
            self._tempo_decorrido_label.configure(text=self._formatar_duracao(decorrido))

        if self._arquivos_tempo_decorrido_label is not None:
            self._arquivos_tempo_decorrido_label.configure(
                text=self._formatar_duracao(decorrido)
            )
        if self._arquivos_media_codigo_label is not None:
            if concluidos > 0 and decorrido > 0:
                media = concluidos / (decorrido / 60.0)
                self._arquivos_media_codigo_label.configure(
                    text=f"{media:.1f} cód/min"
                )
            else:
                self._arquivos_media_codigo_label.configure(text="—")

        if self._tempo_estimado_label is not None:
            restantes = max(0, int(self._execucao_total) - processados)
            if concluidos > 0 and decorrido > 0 and restantes > 0:
                por_item = decorrido / concluidos
                estimado = por_item * restantes
                self._tempo_estimado_label.configure(text=self._formatar_duracao(estimado))
            elif restantes == 0 and int(self._execucao_total) > 0:
                self._tempo_estimado_label.configure(text="00:00:00")
            else:
                self._tempo_estimado_label.configure(text="—")

        try:
            self._execucao_timer_job = self.app.after(500, self._atualizar_metricas_execucao)
        except Exception:
            self._execucao_timer_job = None

    def _ajustar_altura_acompanhamento(self, _event=None):
        """Adapta a área de histórico à altura da janela principal."""
        card = getattr(self, "_activity_card", None)
        if card is None:
            return
        try:
            janela_w = int(self.app.winfo_width())
            janela_h = max(590, int(self.app.winfo_height()))
        except Exception:
            return

        tamanho = (janela_w, janela_h)
        anterior_tamanho = getattr(self, "_ultimo_tamanho_app_config", None)
        if anterior_tamanho == tamanho:
            return
        self._ultimo_tamanho_app_config = tamanho

        try:
            altura = max(300, min(440, janela_h - 260))
            atual = int(card.cget("height") or 0)
            if abs(atual - altura) > 3:
                card.configure(height=altura)
        except Exception:
            pass

        lista = getattr(self, "historico_lista", None)
        if lista is None:
            return
        try:
            largura = int(lista.winfo_width())
        except Exception:
            return
        if largura < 200:
            return
        anterior = int(getattr(self, "_historico_layout_width", 0) or 0)
        if abs(largura - anterior) < 40:
            return
        self._historico_layout_width = largura
        if getattr(self, "_historico_reflow_job", None) is not None:
            try:
                self.app.after_cancel(self._historico_reflow_job)
            except Exception:
                pass
        self._historico_reflow_job = self.app.after(
            100, self._restaurar_historico_na_tela
        )

    def _set_stat(self, card, value):
        if card is None:
            return
        label = getattr(card, "value_label", None)
        if label is not None:
            label.configure(text=str(value))

    def _add_activity(self, text, kind="info"):
        atividade = getattr(self, "atividade", None)
        if atividade is None:
            return
        prefix = {self.SUCCESS: "✓", self.ERROR: "✕", self.WARNING: "!", self.INFO: "→"}.get(kind, "→")
        line = f"{datetime.now():%H:%M:%S}  {prefix}  {text}\n"
        atividade.configure(state="normal")
        atividade.insert("end", line)
        self._log_count += 1
        if self._log_count > 80:
            atividade.delete("1.0", "2.0")
            self._log_count -= 1
        atividade.see("end")
        atividade.configure(state="disabled")

    def _carregar_estado_persistente(self):
        try:
            registros = []
            erros = []
            tema = "system"
            visualizacao = "complete"
            usou_legado = False

            if self._historico_arquivo.exists():
                fontes = [self._historico_arquivo]
            elif self._historico_arquivo_legado.exists():
                fontes = [self._historico_arquivo_legado]
                usou_legado = True
            else:
                fontes = []

            execucao_pendente = None
            for caminho in fontes:
                try:
                    with caminho.open("r", encoding="utf-8") as handle:
                        dados = json.load(handle)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    # O arquivo principal é a fonte de verdade. Nunca recupere
                    # automaticamente um .bak, pois ele pode conter histórico
                    # explicitamente apagado pelo usuário.
                    continue
                if not isinstance(dados, dict):
                    continue

                execucoes = dados.get("historico_execucoes", [])
                if isinstance(execucoes, list):
                    registros.extend(
                        item for item in execucoes if isinstance(item, dict)
                    )

                lista_erros = dados.get("erros", [])
                if isinstance(lista_erros, list):
                    erros.extend(
                        str(item).strip()
                        for item in lista_erros
                        if str(item).strip()
                    )

                valor_tema = dados.get("tema")
                if valor_tema in ("light", "dark", "system"):
                    tema = valor_tema
                valor_visualizacao = dados.get("visualizacao")
                if valor_visualizacao in ("complete", "compact"):
                    visualizacao = valor_visualizacao

                atual = dados.get("execucao_atual")
                if isinstance(atual, dict):
                    execucao_pendente = dict(atual)

            if self._erros_arquivo.exists():
                try:
                    with self._erros_arquivo.open("r", encoding="utf-8") as handle:
                        dados_erros = json.load(handle)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    dados_erros = {}
                if isinstance(dados_erros, dict):
                    lista_dedicada = dados_erros.get("erros", [])
                    if isinstance(lista_dedicada, list):
                        erros.extend(
                            str(item).strip()
                            for item in lista_dedicada
                            if str(item).strip()
                        )

            unicos = {}
            for item in registros:
                chave = str(item.get("id", "")).strip()
                if not chave:
                    chave = (
                        str(item.get("inicio", "")),
                        str(item.get("planilha", "")),
                        str(item.get("pagina", "")),
                    )
                unicos[chave] = item

            self._tema = tema
            self._visualizacao = visualizacao

            # Este arquivo representa exclusivamente o histórico de execuções
            # com erro. Registros bem-sucedidos de versões antigas são removidos
            # na memória e também persistidos de volta, evitando que reapareçam.
            self._historico_execucoes = [
                item for item in unicos.values()
                if self._historico_execucao_tem_erros(item)
            ]
            self._execucao_atual = None

            if isinstance(execucao_pendente, dict):
                status = str(execucao_pendente.get("status", "")).strip().casefold()
                if any(
                    marcador in status
                    for marcador in ("em andamento", "interrompida", "parando")
                ):
                    self._execucao_atual = execucao_pendente

            erros_reconstruidos = []
            for execucao in self._historico_execucoes:
                for codigo in execucao.get("codigos_erros", []) or []:
                    texto = str(codigo).strip()
                    if texto and texto not in erros_reconstruidos:
                        erros_reconstruidos.append(texto)

            if self._execucao_atual:
                for codigo in self._execucao_atual.get("codigos_erros", []) or []:
                    texto = str(codigo).strip()
                    if texto and texto not in erros_reconstruidos:
                        erros_reconstruidos.append(texto)

            for codigo in erros:
                texto = str(codigo).strip()
                if texto and texto not in erros_reconstruidos:
                    erros_reconstruidos.append(texto)

            self._erros_codigos = erros_reconstruidos[-200:]

            if usou_legado:
                self._salvar_estado_persistente(backup=False)
            elif self._erros_codigos and not self._erros_arquivo.exists():
                self._salvar_erros_persistentes(backup=False)

            # Uma vez existente o arquivo canônico, a fonte legada deixa de ser
            # válida e é removida para impedir reidratação por versões antigas.
            try:
                if self._historico_arquivo.exists():
                    self._historico_arquivo_legado.unlink(missing_ok=True)
            except OSError:
                pass

            # Backups de histórico nunca podem ressuscitar dados apagados.
            for caminho in (
                backup_path(self._historico_arquivo),
                backup_path(self._historico_arquivo_legado),
                backup_path(self._erros_arquivo),
            ):
                try:
                    caminho.unlink(missing_ok=True)
                except OSError:
                    pass
        except Exception:
            LOGGER.exception("Falha ao carregar o histórico persistente.")
            self._historico_execucoes = []
            self._execucao_atual = None
            self._erros_codigos = []

    def _salvar_estado_persistente(self, *, backup=True):
        try:
            dados = {
                "version": 4,
                "historico_execucoes": self._historico_execucoes,
                "execucao_atual": (
                    dict(self._execucao_atual)
                    if isinstance(self._execucao_atual, dict)
                    else None
                ),
                "tema": self._tema,
                "visualizacao": getattr(self, "_visualizacao", "complete"),
                "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._historico_arquivo.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self._historico_arquivo, dados, backup=backup)
        except Exception:
            LOGGER.exception("Falha ao salvar o histórico de execuções.")

    def _salvar_erros_persistentes(self, *, backup=True):
        try:
            dados = {
                "version": 1,
                "erros": self._erros_codigos[-200:],
                "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._erros_arquivo.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self._erros_arquivo, dados, backup=backup)
        except Exception:
            LOGGER.exception("Falha ao salvar o histórico de erros.")

    def _criar_botao_erro(self, codigo, parent, command=None):
        codigo = str(codigo)
        if command is None:
            command = lambda c=codigo: self._copiar_codigo(c)
        btn = ctk.CTkButton(
            parent, text=codigo, command=command,
            height=30, corner_radius=8, fg_color=("#FDE7E9", "#4B2529"),
            hover_color=("#FAD2D5", "#603034"), text_color=self.ERROR,
            border_width=1, border_color=("#F1B8BC", "#7A4448"),
            font=("Segoe UI", 11, "bold"), anchor="w"
        )
        btn.pack(fill="x", padx=6, pady=3)
        return btn

    def _add_erro_codigo(self, codigo):
        codigo = str(codigo)
        if codigo in self._erros_codigos:
            return
        self._erros_codigos.append(codigo)
        self._salvar_erros_persistentes()

    def _registrar_codigo_erro_historico(self, codigo, numero=None, erro=""):
        """Registra imediatamente o código que falhou na execução atual."""
        if not self._execucao_atual:
            return
        texto = str(codigo or "").strip()
        if not texto:
            return

        codigos_execucao = getattr(self, "_codigos_erros_execucao", [])
        if texto not in codigos_execucao:
            codigos_execucao.append(texto)
        self._codigos_erros_execucao = codigos_execucao

        codigos = self._execucao_atual.setdefault("codigos_erros", [])
        if texto not in codigos:
            codigos.append(texto)

        # Persistência em dois campos independentes: mesmo que a consolidação
        # final seja interrompida, o código já fica associado à execução.
        detalhes = self._execucao_atual.setdefault("erros_detalhes", [])
        if not isinstance(detalhes, list):
            detalhes = []
            self._execucao_atual["erros_detalhes"] = detalhes

        existente = next(
            (
                item for item in detalhes
                if isinstance(item, dict)
                and str(item.get("codigo", "")).strip() == texto
            ),
            None,
        )
        if existente is None:
            detalhes.append({
                "numero": int(numero) if str(numero).isdigit() else None,
                "codigo": texto,
                "erro": str(erro or ""),
                "horario": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
        else:
            if str(erro or "").strip():
                existente["erro"] = str(erro)
            if existente.get("numero") is None and str(numero).isdigit():
                existente["numero"] = int(numero)

        self._execucao_atual["erros"] = max(
            int(self._execucao_atual.get("erros", 0) or 0),
            len(codigos),
            len(detalhes),
        )
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

        origem = str(pendente.get("origem", "")).strip()
        if origem != "planilha_interna":
            # A planilha externa pertence ao fluxo legado, que não faz mais
            # parte da interface canônica. Não tente acessar widgets removidos
            # (planilha_label/pagina) nem iniciar a automação interna com dados
            # que não foram carregados pela grade atual.
            self._retomada_dialogo_aberto = True
            try:
                pendente["status"] = "Retomada manual necessária"
                pendente["mensagem"] = (
                    "A execução interrompida pertence ao fluxo antigo de "
                    "planilha externa e não pode ser retomada automaticamente "
                    "pela interface atual."
                )
                self._salvar_estado_persistente()
                messagebox.showwarning(
                    "Retomada antiga",
                    "Foi encontrada uma execução interrompida de uma versão "
                    "anterior do SM AutoLab. O fluxo antigo de planilha externa "
                    "não está mais disponível para retomada automática. "
                    "Abra a planilha interna e inicie uma nova execução.",
                    parent=self.app,
                )
            finally:
                self._retomada_dialogo_aberto = False
            return

        try:
            codigos = self._extrair_codigos_planilha()
            interno = ler_checkpoint_interno(codigos) if codigos else None
            if interno is not None:
                inicio = int(interno)
        except Exception:
            pass

        proximo = max(1, inicio)
        self._retomada_dialogo_aberto = True
        try:
            detalhes = (
                "Foi encontrado um processamento interrompido.\n\n"
                f"Planilha: {planilha_nome or 'Planilha interna'}\n"
                f"Página: {pagina}\n"
                f"Próximo código: {proximo}\n\n"
                "Deseja continuar de onde parou?"
            )
            resposta = messagebox.askyesno(
                "Retomar processamento",
                detalhes,
                parent=self.app,
            )
            if resposta:
                self.iniciar_thread()
            else:
                self._add_activity(
                    "Retomada recusada na abertura do aplicativo.",
                    self.INFO,
                )
        finally:
            self._retomada_dialogo_aberto = False

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
            "erros_detalhes": [],
        }
        self._codigos_erros_execucao = []
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()

    def _remover_erros_resolvidos_por_reexecucao(self, resultado, origem_id):
        """Retira do histórico os códigos que passaram a ser executados com sucesso."""
        if not origem_id or not isinstance(resultado, object):
            return

        execucao_original = next(
            (
                item
                for item in self._historico_execucoes
                if self._id_historico_execucao(item) == str(origem_id)
            ),
            None,
        )
        if not isinstance(execucao_original, dict):
            return

        resolvidos = set()
        for item in getattr(resultado, "itens", []) or []:
            if isinstance(item, dict):
                codigo = str(item.get("codigo") or item.get("code") or "").strip()
                estado = str(item.get("status", "")).strip().casefold()
            else:
                codigo = str(getattr(item, "codigo", "")).strip()
                estado = str(getattr(item, "status", "")).strip().casefold()
            if codigo and estado in {"sucesso", "executado", "processado"}:
                resolvidos.add(codigo)

        if not resolvidos:
            return

        codigos_originais = self._historico_codigos_de_erro(execucao_original)
        restantes = [codigo for codigo in codigos_originais if codigo not in resolvidos]

        detalhes = execucao_original.get("erros_detalhes") or []
        if isinstance(detalhes, list):
            detalhes = [
                detalhe
                for detalhe in detalhes
                if not isinstance(detalhe, dict)
                or str(detalhe.get("codigo", "")).strip() not in resolvidos
            ]

        execucao_original["codigos_erros"] = restantes
        execucao_original["erros_detalhes"] = detalhes
        execucao_original["erros"] = max(
            0,
            len(restantes),
            len(
                [
                    detalhe
                    for detalhe in detalhes
                    if isinstance(detalhe, dict)
                    and str(detalhe.get("codigo", "")).strip()
                ]
            ),
        )
        execucao_original["codigos_erros_reexecutados"] = [
            codigo
            for codigo in (execucao_original.get("codigos_erros_reexecutados") or [])
            if str(codigo).strip() not in resolvidos
        ]

        if not restantes and execucao_original.get("erros", 0) <= 0:
            self._historico_execucoes = [
                item
                for item in self._historico_execucoes
                if self._id_historico_execucao(item) != str(origem_id)
            ]

        self._erros_codigos = [
            codigo
            for codigo in self._erros_codigos
            if codigo not in resolvidos
        ]
        self._salvar_erros_persistentes()

    def _finalizar_historico_execucao(self, resultado, status="Concluída"):
        if not self._execucao_atual:
            return
        self._execucao_atual["fim"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._execucao_atual["status"] = status
        self._execucao_atual["total"] = int(getattr(resultado, "total_planejado", 0) or 0)
        self._execucao_atual["sucessos"] = int(getattr(resultado, "sucessos", 0) or 0)
        self._execucao_atual["erros"] = int(getattr(resultado, "erros", 0) or 0)
        self._execucao_atual["processados"] = int(getattr(resultado, "processados", 0) or 0)

        # Consolida os detalhes estruturados e todos os códigos conhecidos.
        # O histórico passa a ter uma fonte explícita para renderização dos erros.
        detalhes_erros = []
        detalhes_fonte = getattr(resultado, "erros_detalhes", []) or []
        if isinstance(detalhes_fonte, list):
            for detalhe in detalhes_fonte:
                if not isinstance(detalhe, dict):
                    continue
                codigo = str(detalhe.get("codigo", "") or "").strip()
                if not codigo:
                    continue
                detalhes_erros.append({
                    "numero": (
                        int(detalhe.get("numero"))
                        if str(detalhe.get("numero", "")).isdigit()
                        else None
                    ),
                    "codigo": codigo,
                    "erro": str(detalhe.get("erro", "") or ""),
                    "horario": str(detalhe.get("horario", "") or ""),
                })

        for item in getattr(resultado, "itens", []) or []:
            if isinstance(item, dict):
                item_status = str(item.get("status", "")).strip().casefold()
                codigo = str(item.get("codigo") or item.get("code") or "").strip()
                erro = str(item.get("erro") or item.get("error") or "").strip()
                numero = item.get("numero")
                horario = str(item.get("horario", "") or "")
            else:
                item_status = str(getattr(item, "status", "")).strip().casefold()
                codigo = str(getattr(item, "codigo", "")).strip()
                erro = str(getattr(item, "erro", "") or "").strip()
                numero = getattr(item, "numero", None)
                horario = str(getattr(item, "horario", "") or "")
            if item_status in {"erro", "não executado", "nao executado"} and codigo:
                if not any(
                    str(d.get("codigo", "")).strip() == codigo
                    for d in detalhes_erros
                ):
                    detalhes_erros.append({
                        "numero": int(numero) if str(numero).isdigit() else None,
                        "codigo": codigo,
                        "erro": erro,
                        "horario": horario,
                    })

        codigos_erros = []
        for fonte in (
            getattr(self, "_codigos_erros_execucao", []),
            self._execucao_atual.get("codigos_erros", []) or [],
            getattr(resultado, "codigos_erros", []) or [],
            [detalhe.get("codigo") for detalhe in detalhes_erros],
        ):
            for codigo in fonte or []:
                texto = str(codigo).strip()
                if texto and texto not in codigos_erros:
                    codigos_erros.append(texto)

        for codigo in codigos_erros:
            if not any(
                str(detalhe.get("codigo", "")).strip() == codigo
                for detalhe in detalhes_erros
            ):
                detalhes_erros.append({
                    "numero": None,
                    "codigo": codigo,
                    "erro": "",
                    "horario": "",
                })

        self._execucao_atual["codigos_erros"] = codigos_erros
        self._execucao_atual["erros_detalhes"] = detalhes_erros
        self._execucao_atual["erros"] = max(
            int(self._execucao_atual.get("erros", 0) or 0),
            int(getattr(resultado, "erros", 0) or 0),
            len(codigos_erros),
            len(detalhes_erros),
        )

        # Uma reexecução pertence à execução original. Códigos que voltaram
        # a ser processados com sucesso deixam de aparecer no histórico de erros.
        origem_reexecucao = self._execucao_atual.get("reexecucao_de")
        eh_reexecucao = bool(origem_reexecucao)
        if eh_reexecucao:
            self._remover_erros_resolvidos_por_reexecucao(
                resultado,
                origem_reexecucao,
            )

        # O histórico de erros nunca recebe uma execução totalmente bem-sucedida.
        # Uma execução normal só é arquivada aqui quando houve pelo menos um erro real.
        if not eh_reexecucao and self._historico_execucao_tem_erros(self._execucao_atual):
            self._historico_execucoes.append(dict(self._execucao_atual))

        self._execucao_atual = None
        self._codigos_erros_execucao = []
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
        self._execucao_atual["erros"] = max(
            int(self._execucao_atual.get("erros", 0) or 0),
            1,
        )
        if not self._execucao_atual.get("reexecucao_de"):
            self._historico_execucoes.append(dict(self._execucao_atual))
        self._execucao_atual = None
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()
        self._atualizar_contador_arquivos()

    def _restaurar_historico_na_tela(self):
        if not hasattr(self, "historico_lista"):
            return
        for w in self.historico_lista.winfo_children():
            w.destroy()
        self._hist_grid = None

        filtrado = [item for item in self._historico_execucoes if self._historico_execucao_tem_erros(item)]
        if len(filtrado) != len(self._historico_execucoes):
            self._historico_execucoes = filtrado
            self._salvar_estado_persistente()

        self._historico_tiles = {}
        self._historico_reflow_job = None
        try:
            self._historico_layout_width = int(self.historico_lista.winfo_width())
        except Exception:
            self._historico_layout_width = 0

        historico_visivel = list(filtrado)
        if (
            self._execucao_atual
            and self._historico_execucao_tem_erros(self._execucao_atual)
            and self._id_historico_execucao(self._execucao_atual)
            not in {self._id_historico_execucao(item) for item in historico_visivel}
        ):
            historico_visivel.append(self._execucao_atual)

        if not historico_visivel:
            self._historico_selecionados.clear()
            self._atualizar_visual_selecao_historico()
            self._atualizar_botao_apagar_historico()
            ctk.CTkLabel(
                self.historico_lista,
                text="Nenhuma execução com erros registrada ainda.",
                text_color=self.SUBTEXT,
                font=("Segoe UI",10),
            ).pack(anchor="w",padx=8,pady=12)
            return

        validos={self._id_historico_execucao(item) for item in historico_visivel}
        self._historico_selecionados.intersection_update(validos)

        self._hist_grid=ctk.CTkFrame(self.historico_lista,fg_color="transparent")
        self._hist_grid.pack(fill="x",padx=8,pady=5)
        headers=("Data","Hora","","Processados","Executados","Erros","Status","","")
        for col, (texto, peso, minimo) in enumerate(
            zip(headers, HISTORICO_COL_PESOS, HISTORICO_COL_MINS)
        ):
            self._hist_grid.grid_columnconfigure(
                col,
                weight=peso,
                minsize=minimo,
                uniform="historico",
            )
            if texto:
                ctk.CTkLabel(
                    self._hist_grid,text=texto,text_color=self.SUBTEXT,
                    font=("Segoe UI",9,"bold"),
                    anchor="w" if col==2 else "center",
                ).grid(row=0,column=col,sticky="ew",padx=5,pady=(2,4))
        for execucao in reversed(historico_visivel):
            self._criar_pasta_historico(execucao)
        self._atualizar_visual_selecao_historico()
        self._atualizar_botao_apagar_historico()
        self._atualizar_badge_historico()

    @staticmethod
    def _historico_execucao_tem_erros(execucao):
        if not isinstance(execucao, dict):
            return False
        try:
            if int(execucao.get("erros", 0) or 0) > 0:
                return True
        except (TypeError, ValueError):
            pass

        if any(
            str(codigo).strip()
            for codigo in (execucao.get("codigos_erros", []) or [])
        ):
            return True

        detalhes = execucao.get("erros_detalhes", []) or []
        if isinstance(detalhes, list) and any(
            isinstance(item, dict)
            and (
                str(item.get("codigo", "")).strip()
                or str(item.get("status", "")).strip().casefold()
                in {"erro", "não executado", "nao executado"}
            )
            for item in detalhes
        ):
            return True

        status = str(execucao.get("status", "")).strip().casefold()
        return status in {
            "erro geral",
            "não executado",
            "nao executado",
            "não executada",
            "nao executada",
        }

    def _id_historico_execucao(self, execucao):
        if not isinstance(execucao, dict):
            return str(id(execucao))
        valor = str(execucao.get("id", "")).strip()
        if valor:
            return valor
        return "|".join(
            str(execucao.get(campo, "")).strip()
            for campo in ("inicio", "fim", "planilha", "pagina")
        )

    def _formatar_data_historico(self, valor):
        texto = str(valor or "").strip()
        if not texto:
            return ""
        data = texto.split(" ", 1)[0]
        try:
            return datetime.strptime(data, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return data

    def _criar_pasta_historico(self, execucao, atual=False):
        """Renderiza uma execução em linha resumida alinhada ao cabeçalho."""
        parent = self._hist_grid
        if parent is None:
            parent = self.historico_lista
            self._hist_grid = ctk.CTkFrame(parent, fg_color="transparent")
            self._hist_grid.pack(fill="x", padx=8, pady=5)
            parent = self._hist_grid

        for col, (peso, minimo) in enumerate(
            zip(HISTORICO_COL_PESOS, HISTORICO_COL_MINS)
        ):
            parent.grid_columnconfigure(
                col,
                weight=peso,
                minsize=minimo,
                uniform="historico",
            )

        execucao_id = self._id_historico_execucao(execucao)
        inicio = str(execucao.get("inicio", "") or "")
        data = self._formatar_data_historico(inicio)
        horario = inicio.split(" ", 1)[1] if " " in inicio else ""

        try:
            total = int(
                execucao.get("total", 0)
                or execucao.get("processados", 0)
                or 0
            )
        except (TypeError, ValueError):
            total = 0

        try:
            sucessos = int(execucao.get("sucessos", 0) or 0)
        except (TypeError, ValueError):
            sucessos = 0

        try:
            erros = max(
                int(execucao.get("erros", 0) or 0),
                len(execucao.get("codigos_erros", []) or []),
                len(execucao.get("erros_detalhes", []) or []),
            )
        except (TypeError, ValueError):
            erros = 0

        status = str(execucao.get("status", "") or "Erro").strip() or "Erro"
        if len(status) > 18:
            status = status[:17] + "…"

        row_index = len(parent.winfo_children())
        row = ctk.CTkFrame(
            parent,
            fg_color=self.CARD,
            corner_radius=7,
            border_width=1,
            border_color=self.BORDER,
            height=42,
        )
        row.grid(
            row=row_index,
            column=0,
            columnspan=9,
            sticky="ew",
            pady=2,
        )
        row.grid_propagate(False)

        for col, (peso, minimo) in enumerate(
            zip(HISTORICO_COL_PESOS, HISTORICO_COL_MINS)
        ):
            row.grid_columnconfigure(
                col,
                weight=peso,
                minsize=minimo,
                uniform="historico",
            )

        valores = (
            (data, "center"),
            (horario, "center"),
            ("", "center"),
            (str(total), "center"),
            (str(sucessos), "center"),
            (str(erros), "center"),
            (status, "center"),
        )
        labels = []
        for col, (valor, anchor) in enumerate(valores):
            if col == 3:       # Processados
                cor = self.INFO
            elif col == 4:     # Executados
                cor = self.SUCCESS
            elif col == 5:     # Erros
                cor = self.ERROR
            else:
                cor = self.TEXT

            label = ctk.CTkLabel(
                row,
                text=valor,
                text_color=cor,
                font=("Segoe UI", 9, "normal"),
                anchor=anchor,
            )
            label.grid(row=0, column=col, sticky="ew", padx=5, pady=2)
            labels.append(label)

        pendente = self._historico_tem_erros_pendentes_reexecucao(execucao)
        indicador = self._criar_ponto_notificacao(
            row,
            self._cor(self.CARD),
        )
        if pendente:
            indicador.place(
                relx=1.0,
                rely=0.5,
                x=-3,
                anchor="e",
            )
        else:
            indicador.place_forget()

        self._historico_tiles[execucao_id] = row

        def atualizar_visual(hover=False):
            selecionado = execucao_id in self._historico_selecionados
            if selecionado:
                row.configure(
                    border_color=self.ACCENT,
                    fg_color=("#EAF4FF", "#1B3C53"),
                )
            elif hover:
                row.configure(
                    border_color=self.ACCENT_HOVER,
                    fg_color=("#EAF4FC", "#263F50"),
                )
            else:
                row.configure(
                    border_color=self.BORDER,
                    fg_color=self.CARD,
                )

        def clicar(event=None):
            ctrl = bool(
                event is not None and (getattr(event, "state", 0) & 0x0004)
            )
            if ctrl:
                if execucao_id in self._historico_selecionados:
                    self._historico_selecionados.remove(execucao_id)
                else:
                    self._historico_selecionados.add(execucao_id)
                self._atualizar_visual_selecao_historico()
                self._atualizar_botao_apagar_historico()
                return "break"

            self._historico_selecionados.clear()
            self._atualizar_visual_selecao_historico()
            self._atualizar_botao_apagar_historico()
            self._abrir_detalhe_historico(execucao)
            return "break"

        widgets = (row, *labels, indicador)
        for widget in widgets:
            try:
                widget.configure(cursor="hand2")
            except Exception:
                pass
            widget.bind("<Enter>", lambda _e: atualizar_visual(True))
            widget.bind("<Leave>", lambda _e: atualizar_visual(False))
            widget.bind("<Button-1>", clicar)
            widget.bind("<Escape>", self._limpar_selecao_historico, add="+")
        return row

    def _atualizar_visual_selecao_historico(self):
        for execucao_id, tile in getattr(self, "_historico_tiles", {}).items():
            try:
                if not tile.winfo_exists():
                    continue
                if execucao_id in self._historico_selecionados:
                    tile.configure(
                        border_color=self.ACCENT,
                        fg_color=("#EAF4FF", "#1B3C53"),
                    )
                else:
                    tile.configure(
                        border_color=self.BORDER,
                        fg_color=("#FFFFFF", "#2D3338"),
                    )
            except Exception:
                pass

    def _atualizar_botao_apagar_historico(self):
        btn = getattr(self, "botao_apagar_historico_selecionados", None)
        if btn is None:
            return
        try:
            quantidade = len(self._historico_selecionados)
            if quantidade:
                texto = f"Apagar {quantidade} selecionado" if quantidade == 1 else f"Apagar {quantidade} selecionados"
                btn.configure(text=texto)
                btn.pack(side="right", padx=(0, 6))
            else:
                btn.configure(text="Apagar selecionados")
                btn.pack_forget()
        except Exception:
            pass

    def _limpar_selecao_historico(self, _event=None):
        self._historico_selecionados.clear()
        self._atualizar_visual_selecao_historico()
        self._atualizar_botao_apagar_historico()
        return "break"

    def _apagar_historico_selecionados(self):
        selecionados = set(self._historico_selecionados)
        if not selecionados:
            return
        confirmar = messagebox.askyesno(
            "Apagar selecionados",
            f"Tem certeza que deseja apagar {len(selecionados)} execução(ões) selecionada(s) do histórico?",
            parent=self.app,
        )
        if not confirmar:
            return
        antes = len(self._historico_execucoes)
        self._historico_execucoes = [
            item for item in self._historico_execucoes
            if self._id_historico_execucao(item) not in selecionados
        ]
        removidos = antes - len(self._historico_execucoes)
        self._historico_selecionados.clear()
        self._salvar_estado_persistente()
        self._restaurar_historico_na_tela()
        self._atualizar_botao_apagar_historico()
        self._add_activity(f"{removidos} execução(ões) removida(s) do histórico.", self.WARNING)
        self.atualizar_status("Seleções apagadas")

    def _abrir_detalhe_historico(self, execucao):
        win = ctk.CTkToplevel(self.app)
        self._configurar_icone_janela(win)
        win.title("Execução — SM AutoLab")
        win.geometry("680x500")
        win.minsize(560, 400)
        win.resizable(True, True)
        win.transient(self.app)
        self._centralizar_janela(win, 680, 500)
        try:
            aplicar_backdrop_sistema(
                win, "acrylic",
                dark=ctk.get_appearance_mode().lower() == "dark"
            )
        except Exception:
            pass
        self._preencher_detalhe_pasta(win, execucao)
        _ui_scan_tooltips(win)

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
        detalhes_erros = execucao.get("erros_detalhes") or []
        if not isinstance(detalhes_erros, list):
            detalhes_erros = execucao.get("erros_detalhes") or []
        if not isinstance(detalhes_erros, list):
            detalhes_erros = []
        codigos_detalhe = [
            item.get("codigo")
            for item in detalhes_erros
            if isinstance(item, dict) and str(item.get("codigo", "")).strip()
        ]
        codigos_raw = (
            codigos_detalhe
            or execucao.get("codigos_erros")
            or execucao.get("erros_codigos")
            or execucao.get("codigos_erro")
            or execucao.get("codigos")
            or execucao.get("codigo_erro")
            or []
        )
        if isinstance(codigos_raw, str):
            codigos_raw = [codigos_raw]

        # Compatibilidade com históricos mais antigos que guardavam os itens
        # processados, mas não criavam explicitamente a lista codigos_erros.
        if not codigos_raw:
            registros_antigos = (
                execucao.get("resultados")
                or execucao.get("itens")
                or execucao.get("erros_detalhes")
                or []
            )
            if isinstance(registros_antigos, list):
                codigos_raw = [
                    item for item in registros_antigos
                    if isinstance(item, dict)
                    and (
                        str(item.get("status", "")).strip().casefold() == "erro"
                        or item.get("erro")
                        or item.get("error")
                    )
                ]

        codigos = []
        for item in codigos_raw:
            if isinstance(item, dict):
                item = item.get("codigo") or item.get("code") or ""
            item = str(item).strip()
            if item and item not in codigos:
                codigos.append(item)

        ctk.CTkLabel(
            parent,
            text=(f"Início: {inicio}    Fim: {fim}\n"
                   f"Planilha: {planilha}    Página: {pagina}\n"
                   f"Status: {status}    Processados: {total}    Executados: {sucessos}    Não executados: {erros}"),
            text_color=self.SUBTEXT, font=("Segoe UI", 9), anchor="w", justify="left"
        ).pack(fill="x", padx=8, pady=(7, 4))

        if erros and not codigos:
            ctk.CTkLabel(
                parent,
                text="Os códigos desta execução não foram armazenados no histórico desta versão.",
                text_color=self.ERROR,
                font=("Segoe UI", 10, "bold"),
                anchor="w",
                justify="left",
                wraplength=620,
            ).pack(fill="x", padx=12, pady=(6, 10))

        if erros and codigos:
            header = ctk.CTkFrame(parent, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(4, 5))
            ctk.CTkLabel(
                header,
                text="Códigos não executados (clique para copiar):",
                text_color=self.ERROR,
                font=("Segoe UI", 11, "bold"),
                anchor="w",
            ).pack(side="left")

            # Cada execução histórica pode ser reexecutada uma única vez por
            # código. Se a reexecução falhar novamente, ela gera uma nova
            # execução no histórico, onde os códigos voltam a ser elegíveis.
            codigos_reexecutados = {
                str(c).strip()
                for c in (execucao.get("codigos_erros_reexecutados") or [])
                if str(c).strip()
            }
            codigos_reexecutaveis = [
                codigo for codigo in codigos
                if codigo not in codigos_reexecutados
            ]

            def reexecutar_erros():
                if not codigos_reexecutaveis:
                    return "break"

                # Marca a execução original antes de iniciar a nova tentativa,
                # evitando que o botão volte a aparecer após o fechamento/
                # reabertura da janela.
                atuais = set(
                    str(c).strip()
                    for c in (execucao.get("codigos_erros_reexecutados") or [])
                    if str(c).strip()
                )
                atuais.update(codigos_reexecutaveis)
                execucao["codigos_erros_reexecutados"] = sorted(atuais)

                for item in self._historico_execucoes:
                    if self._id_historico_execucao(item) == self._id_historico_execucao(execucao):
                        item["codigos_erros_reexecutados"] = list(execucao["codigos_erros_reexecutados"])
                        break

                self._salvar_estado_persistente()
                self._restaurar_historico_na_tela()
                try:
                    parent.destroy()
                except Exception:
                    pass

                self._add_activity(
                    f"Reexecutando {len(codigos_reexecutaveis)} código(s) que apresentaram erro.",
                    self.WARNING,
                )
                self._origem_reexecucao = "reexecucao_erros"
                self._reexecucao_origem_id = self._id_historico_execucao(execucao)
                self._iniciar_automacao_interna(
                    list(codigos_reexecutaveis),
                    ignorar_checkpoint=True,
                )
                return "break"

            reexecutar_btn = ctk.CTkButton(
                header,
                text=(
                    f"Reexecutar {len(codigos_reexecutaveis)} erro"
                    if len(codigos_reexecutaveis) == 1
                    else f"Reexecutar {len(codigos_reexecutaveis)} erros"
                ),
                command=reexecutar_erros,
                width=150,
                height=26,
                corner_radius=8,
                fg_color=self.CARD,
                hover_color=("#E8F4FF", "#203B4D"),
                border_width=1,
                border_color=self.ACCENT,
                text_color=self.ACCENT,
                font=("Segoe UI", 10, "bold"),
            )
            if codigos_reexecutaveis:
                reexecutar_btn.pack(side="right", padx=(6, 0))

            selecionados = set()
            botoes = {}

            def atualizar_selecao_erros():
                if selecionados:
                    apagar_btn.pack(side="right")
                else:
                    apagar_btn.pack_forget()
                for codigo, btn in botoes.items():
                    try:
                        if codigo in selecionados:
                            btn.configure(
                                fg_color=("#DDEEFF", "#214F70"),
                                border_color=self.ACCENT,
                                text_color=self.ACCENT,
                            )
                        else:
                            btn.configure(
                                fg_color=("#FDE7E9", "#4B2529"),
                                border_color=("#F1B8BC", "#7A4448"),
                                text_color=self.ERROR,
                            )
                    except Exception:
                        pass

            def apagar_selecionados_erros():
                if not selecionados:
                    return "break"
                restantes = [codigo for codigo in codigos if codigo not in selecionados]
                removidos = len(codigos) - len(restantes)
                execucao["codigos_erros"] = restantes
                execucao["erros"] = max(0, erros - removidos)
                self._historico_execucoes = [
                    dict(execucao_item) if execucao_item is not execucao else dict(execucao)
                    for execucao_item in self._historico_execucoes
                ]
                selecionados.clear()
                self._salvar_estado_persistente()
                self._restaurar_historico_na_tela()
                self._preencher_detalhe_pasta(parent, execucao)
                return "break"

            apagar_btn = ctk.CTkButton(
                header,
                text="Apagar selecionados",
                command=apagar_selecionados_erros,
                width=128,
                height=26,
                corner_radius=8,
                fg_color=self.CARD,
                hover_color=("#FDECEC", "#3A2424"),
                border_width=1,
                border_color=self.ERROR,
                text_color=self.ERROR,
                font=("Segoe UI", 10, "bold"),
            )
            apagar_btn.pack(side="right")
            apagar_btn.pack_forget()

            # O histórico de uma execução normalmente contém poucos códigos.
            # Usar um CTkFrame simples aqui evita o estado de canvas vazio observado
            # em algumas combinações de Tk/CustomTkinter ao criar a janela de detalhe.
            erros_area = ctk.CTkFrame(
                parent,
                fg_color="transparent",
                corner_radius=0,
            )
            erros_area.pack(fill="x", padx=6, pady=(0, 8))

            def selecionar_erro(codigo, event=None):
                ctrl = bool(event is not None and (getattr(event, "state", 0) & 0x0004))
                if not ctrl:
                    return None
                if codigo in selecionados:
                    selecionados.remove(codigo)
                else:
                    selecionados.add(codigo)
                atualizar_selecao_erros()
                try:
                    parent.focus_set()
                except Exception:
                    pass
                return "break"

            for codigo in codigos:
                btn = self._criar_botao_erro(
                    codigo,
                    parent=erros_area,
                    command=lambda c=codigo: self._copiar_codigo(c),
                )
                botoes[codigo] = btn
                btn.bind("<ButtonRelease-1>", lambda event, c=codigo: selecionar_erro(c, event), add="+")
                btn.bind("<Escape>", lambda _event: (selecionados.clear(), atualizar_selecao_erros(), "break")[2], add="+")
                try:
                    btn.configure(cursor="hand2")
                except Exception:
                    pass

            parent.bind("<Escape>", lambda _event: (selecionados.clear(), atualizar_selecao_erros(), "break")[2], add="+")
            parent.bind("<Delete>", lambda _event: apagar_selecionados_erros(), add="+")
            atualizar_selecao_erros()

        elif erros:
            ctk.CTkLabel(
                parent,
                text=f"{erros} código(s) não executado(s), sem código detalhado disponível.",
                text_color=self.ERROR,
                font=("Segoe UI", 10),
                wraplength=560,
                justify="left",
            ).pack(anchor="w", padx=12, pady=(5, 10))
        else:
            ctk.CTkLabel(
                parent,
                text="Nenhum código apresentou erro nessa execução.",
                text_color=self.SUCCESS,
                font=("Segoe UI", 10),
            ).pack(anchor="w", padx=12, pady=(5, 10))


    def _limpar_historico(self):
        if not self._historico_execucoes and not self._execucao_atual:
            for caminho in (
                self._historico_arquivo_legado,
                backup_path(self._historico_arquivo),
                backup_path(self._historico_arquivo_legado),
                backup_path(self._erros_arquivo),
            ):
                try:
                    caminho.unlink(missing_ok=True)
                except OSError:
                    pass
            self.atualizar_status("Histórico já está vazio")
            return
        confirmar = messagebox.askyesno(
            "Limpar histórico",
            "Tem certeza que deseja apagar todas as execuções salvas no histórico?\n\n"
            "Os códigos associados a essas execuções também serão removidos do histórico."
        )
        if not confirmar:
            return
        self._historico_execucoes = []
        self._execucao_atual = None
        self._erros_codigos = []
        self._salvar_estado_persistente(backup=False)
        self._salvar_erros_persistentes(backup=False)
        for caminho in (
            self._historico_arquivo_legado,
            backup_path(self._historico_arquivo),
            backup_path(self._historico_arquivo_legado),
            backup_path(self._erros_arquivo),
        ):
            try:
                caminho.unlink(missing_ok=True)
            except OSError:
                pass
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
        source = self._planilha_data if cells is None else cells
        snapshot = {}
        for key, value in (source or {}).items():
            texto = str(value)
            if texto != "":
                snapshot[str(key)] = texto
        payload = {
            "version": 1,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "processed_fingerprint": "",
            "processed_at": "",
            "cells": snapshot,
        }
        atomic_write_json(self._planilha_arquivo, payload)

        # Confirma a persistência real antes de registrar a operação como salva.
        try:
            with self._planilha_arquivo.open("r", encoding="utf-8") as handle:
                confirm = json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise IOError("A planilha foi gravada, mas não foi possível conferir o arquivo principal.") from exc
        saved = confirm.get("cells", {}) if isinstance(confirm, dict) else {}
        if not isinstance(saved, dict):
            saved = {}
        normalized = {}
        for key, value in saved.items():
            texto = str(value)
            if texto != "":
                normalized[str(key)] = texto
        if normalized != snapshot:
            raise IOError(
                "A planilha foi gravada, mas a conferência do arquivo "
                "não corresponde aos dados atuais.",
            )
    @staticmethod
    @staticmethod
    def _planilha_fingerprint(cells):
        """Gera uma impressão estável do conteúdo relevante da planilha."""
        normalizados = {
            str(chave): str(valor)
            for chave, valor in (cells or {}).items()
            if str(valor) != ""
        }
        payload = json.dumps(
            sorted(normalizados.items()),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


    def _planilha_foi_processada(self, cells):
        """Retorna True quando a revisão salva já foi concluída pela automação."""
        fingerprint = self._planilha_fingerprint(cells)

        # O marcador persistido continua válido mesmo depois de o histórico
        # visual ser apagado pelo usuário.
        try:
            data = read_json_with_backup(self._planilha_arquivo, {})
            if (
                isinstance(data, dict)
                and str(data.get("processed_fingerprint", "")).strip() == fingerprint
            ):
                return True
        except Exception:
            pass

        # Fallback para execuções registradas antes do marcador persistido.
        for execucao in reversed(getattr(self, "_historico_execucoes", [])):
            if not isinstance(execucao, dict):
                continue
            if str(execucao.get("origem", "")).strip() != "planilha_interna":
                continue
            status = str(execucao.get("status", "")).strip().casefold()
            if status != "concluída":
                continue
            if str(execucao.get("planilha_fingerprint", "")).strip() == fingerprint:
                return True
        return False

    def _marcar_planilha_interna_processada(self, cells):
        """Persiste que a revisão salva foi processada com sucesso."""
        try:
            self._garantir_pasta_planilha()
            data = read_json_with_backup(self._planilha_arquivo, {})
            if not isinstance(data, dict):
                data = {}
            data["version"] = 1
            data["cells"] = {
                str(chave): str(valor)
                for chave, valor in (cells or {}).items()
                if str(valor) != ""
            }
            data["processed_fingerprint"] = self._planilha_fingerprint(cells)
            data["processed_at"] = datetime.now().isoformat(timespec="seconds")
            atomic_write_json(self._planilha_arquivo, data)
        except Exception:
            LOGGER.exception("Falha ao registrar a planilha interna como processada.")


    def _planilha_atualizar_estado_salvamento(self, estado):
        label = getattr(self, "_planilha_estado_salvamento_label", None)
        if label is None:
            return
        tem_dados = any(
            str(valor or "").strip()
            for valor in (self._planilha_data or {}).values()
        )
        estados = {
            "salvo": (
                "Salvo ✓" if tem_dados else "Planilha vazia",
                self.SUCCESS if tem_dados else self.SUBTEXT,
            ),
            "alterado": ("Alterações não salvas", self.WARNING),
            "salvando": ("Salvando…", self.INFO),
            "erro": ("Falha ao salvar", self.ERROR),
        }
        texto, cor = estados.get(str(estado), ("", self.SUBTEXT))
        try:
            label.configure(text=texto, text_color=cor)
        except Exception:
            pass

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
        self._planilha_atualizar_estado_salvamento("alterado")
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

        recuperar_rascunho = False
        if dados_iniciais is None:
            self._preparar_planilha_do_dia()
            ultima = self._carregar_planilha_interna()
            if ultima:
                if self._planilha_foi_processada(ultima):
                    self._planilha_apagar_rascunho()
                    self._planilha_data = {}
                else:
                    recuperar = messagebox.askyesno(
                        "Recuperar última planilha",
                        "A última planilha salva ainda não foi processada.\\n\\n"
                        "Deseja recuperá-la?",
                        parent=self.app,
                    )
                    if recuperar:
                        self._planilha_data = dict(ultima)
                        recuperar_rascunho = True
                    else:
                        self._planilha_apagar_rascunho()
                        self._planilha_data = {}
            else:
                self._planilha_data = {}
                recuperar_rascunho = True
        else:
            self._planilha_data={str(k):str(v) for k,v in dados_iniciais.items() if str(v)!=""}
        self._planilha_salva_data=dict(self._planilha_data)
        self._planilha_undo=[]
        self._planilha_redo=[]
        self._planilha_efetuou_alteracao=False
        self._planilha_estado_salvamento_label=None
        self._planilha_contador_label=None
        win=ctk.CTkToplevel(self.app)
        self._planilha_window=win
        win.title("Planilha — SM AutoLab")
        win.geometry("1080x720")
        win.minsize(900, 600)
        win.configure(fg_color=self.BG)
        win.transient(self.app)
        self._centralizar_janela(win, 1080, 720)
        try:
            aplicar_backdrop_sistema(
                win, "mica_alt",
                dark=ctk.get_appearance_mode().lower() == "dark"
            )
        except Exception:
            pass
        win.protocol("WM_DELETE_WINDOW", self._planilha_fechar_pela_janela)
        win.bind("<Control-KeyPress-f>", self._abrir_busca_planilha, add="+")
        win.bind("<Control-KeyPress-F>", self._abrir_busca_planilha, add="+")
        win.bind("<Control-KeyPress-s>", self._planilha_atalho_salvar, add="+")
        win.bind("<Control-KeyPress-S>", self._planilha_atalho_salvar, add="+")
        win.bind("<Control-Return>", self._atalho_iniciar, add="+")
        win.bind("<Control-KP_Enter>", self._atalho_iniciar, add="+")
        # Restaurar rascunho após a janela existir para que o diálogo tenha parent válido.
        try:
            win.iconbitmap(str(Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))/"SM AutoLab.ico"))
        except Exception:
            pass

        if recuperar_rascunho:
            self._planilha_recuperar_rascunho_se_houver()

        toolbar=ctk.CTkFrame(
            win,
            fg_color=("#FFFFFF", "#2D3338"),
            corner_radius=0,
            height=64,
        )
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
        tem_dados = any(
            str(valor or "").strip()
            for valor in (self._planilha_data or {}).values()
        )
        self._planilha_estado_salvamento_label = ctk.CTkLabel(
            title_bar,
            text="Planilha vazia" if not tem_dados else "Salvo ✓",
            text_color=self.SUBTEXT if not tem_dados else self.SUCCESS,
            font=("Segoe UI",10,"bold")
        )
        self._planilha_estado_salvamento_label.pack(side="left", padx=(14,0))
        self._planilha_atualizar_estado_salvamento("salvo")
        actions=ctk.CTkFrame(toolbar,fg_color="transparent"); actions.pack(side="right",padx=16,pady=9)
        ctk.CTkButton(actions,text="Limpar",command=self._planilha_limpar,width=80,height=36,corner_radius=8,fg_color=self.CARD,hover_color=("#FDECEC","#3A2424"),border_width=1,border_color=self.ERROR,text_color=self.ERROR,font=("Segoe UI",12,"bold")).pack(side="left",padx=4)
        ctk.CTkButton(actions,text="Salvar",command=self._planilha_salvar,width=95,height=36,corner_radius=8,fg_color=self.CARD,hover_color=("#EAF4FC","#263F50"),border_width=1,border_color=self.BORDER,text_color=self.TEXT,font=("Segoe UI",12,"bold")).pack(side="left",padx=4)
        ctk.CTkButton(actions,text="Salvar e Iniciar",command=self._planilha_salvar_e_iniciar,width=150,height=46,corner_radius=8,fg_color=self.ACCENT,hover_color=self.ACCENT_HOVER,font=("Segoe UI",14,"bold")).pack(side="left",padx=4)

        body=ctk.CTkFrame(win,fg_color=self.BG,corner_radius=0)
        body.pack(fill="both",expand=True,padx=12,pady=12)
        modo_escuro = ctk.get_appearance_mode().lower() == "dark"
        tree_bg = "#2D3338" if modo_escuro else "#FFFFFF"
        tree_header = "#343A40" if modo_escuro else "#F5F5F5"
        tree_fg = "#F2F4F5" if modo_escuro else "#242424"
        tree_border = "#465058" if modo_escuro else "#E0E0E0"
        row_header_bg = "#252A2F" if modo_escuro else "#F7F7F7"

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

        # Virtualização do cabeçalho de linhas: o cabeçalho continua enxuto e
        # independente da quantidade total de registros lógicos.
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

        y=_ui_make_windows_scrollbar(body,"vertical",tree.yview)
        x=_ui_make_windows_scrollbar(body,"horizontal",tree.xview)
        tree.configure(yscrollcommand=_sync_row_header,xscrollcommand=x.set)

        row_header_frame.grid(row=0,column=0,sticky="ns")
        tree.grid(row=0,column=1,sticky="nsew")
        y.grid(row=0,column=2,sticky="ns")
        x.grid(row=1,column=1,sticky="ew")
        self._planilha_scrollbars = (y, x)
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
                total = tree.total_rows
                row_height = tree.row_height
                viewport_height = max(1, int(row_header.winfo_height()))
                viewport_rows = max(1, (viewport_height + row_height - 1) // row_height)
                first_row = min(
                    max(0, total - viewport_rows),
                    int(first * total + 0.0001),
                )
                row_index = first_row + int(event.y / row_height)
                row_index = max(0, min(row_index, total - 1))
                iid = str(row_index)
                tree.focus(iid)
                tree.see(iid)
                cells = {(row_index, col) for col in range(3)}
                self._planilha_definir_selecao(cells, active=(row_index, 0))
            except Exception:
                pass
            return "break"
        row_header.bind("<Button-1>", _clicar_cabecalho)

        tree.focus("")
        # Etapa 13: virtualização real; não há inserção gradual de 10.000 itens.
        self._planilha_celulas_selecionadas = set()
        self._planilha_drag_anchor = None
        self._planilha_drag_start_xy = None
        self._planilha_dragging = False
        self._planilha_ultimo_clique = None
        # A grade virtual continua recebendo mouse diretamente pelo Tree API.
        # Não há interceptação adicional de teclado para digitação por um clique.
        tree.bind("<ButtonPress-1>", self._planilha_clicar_celula)
        tree.bind("<B1-Motion>", self._planilha_arrastar_selecao)
        tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao)
        tree.bind("<Return>", self._planilha_editar_selecao)
        tree.bind("<KP_Enter>", self._planilha_editar_selecao)
        tree.bind("<Tab>", self._planilha_tabular)
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
        tree.bind("<Shift-Insert>", self._planilha_atalho_colar, add="+")
        def _planilha_botao_direito(event):
            current = tree.identify_cell(event.x, event.y)
            if current is not None:
                row, col = current
                self._planilha_definir_selecao({current}, active=current)
                tree.focus(str(row))
                tree.focus_set()
            try:
                self._planilha_fechar_edicao()
                self._atualizar_menu_contexto_planilha()
                if self._planilha_context_menu is not None:
                    self._planilha_context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                try:
                    if self._planilha_context_menu is not None:
                        self._planilha_context_menu.grab_release()
                except Exception:
                    pass
            return "break"
        tree.bind("<Button-3>", _planilha_botao_direito)
        tree._canvas.bind("<Button-3>", _planilha_botao_direito, add="+")
        tree.bind("<Shift-Insert>", self._planilha_atalho_colar, add="+")
        self._planilha_tree=tree
        self._planilha_row_header=row_header
        self._planilha_context_menu = self._criar_menu_contexto_planilha(tree)
        self._planilha_implementacao = "grade-virtual"
        tree.refresh()
        # Todos os atalhos da planilha ficam limitados ao Canvas/Entry.
        # Isso evita que menus e controles externos disputem eventos globais.
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
        inicio, _ = visible_row_range(
            fraction,
            altura,
            total_rows,
            row_height,
            overscan=0,
        )
        visiveis = max(1, int(altura / row_height) + 3)
        fim = min(total_rows, inicio + visiveis)
        modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
        bg = "#252A2F" if modo_escuro else "#F7F7F7"
        fg = "#AEB4B9" if modo_escuro else "#6B6B6B"
        line = "#384148" if modo_escuro else "#EEEEEE"
        border = "#465058" if modo_escuro else "#E0E0E0"
        canvas.configure(bg=bg, highlightbackground=border)

        state = getattr(self, "_virtual_grid_row_header_state", None)
        # A planilha pode ser fechada e aberta novamente no mesmo App. Cada
        # abertura cria um novo Canvas, portanto os IDs de itens do cabeçalho
        # anterior não podem ser reutilizados no Canvas atual.
        if (
            not isinstance(state, dict)
            or state.get("canvas") is not canvas
        ):
            state = {"canvas": canvas, "items": []}
            self._virtual_grid_row_header_state = state
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
        """Remove a seleção desenhada diretamente no Canvas da grade."""
        tree = getattr(self, "_planilha_tree", None)
        canvas = getattr(tree, "_canvas", None) if tree is not None else None
        if canvas is None:
            return
        try:
            canvas.delete("planilha-selection")
        except tk.TclError:
            pass

    def _planilha_desenhar_borda(self):
        """Desenha a seleção diretamente no Canvas da grade, sem widgets sobrepostos."""
        tree = getattr(self, "_planilha_tree", None)
        if tree is None:
            return

        canvas = getattr(tree, "_canvas", None)
        if canvas is None:
            return

        try:
            canvas.delete("planilha-selection")
        except tk.TclError:
            return

        cells = getattr(self, "_planilha_celulas_selecionadas", set()) or set()
        active = getattr(self, "_planilha_celula_ativa", None)
        normalized = set()

        for cell in cells:
            try:
                row, col = int(cell[0]), int(cell[1])
            except Exception:
                continue
            if 0 <= row < MAX_ROWS and 0 <= col < 3:
                normalized.add((row, col))

        if active:
            try:
                row, col = int(active[0]), int(active[1])
                if 0 <= row < MAX_ROWS and 0 <= col < 3:
                    normalized.add((row, col))
            except Exception:
                pass

        if not normalized:
            return

        cor = self._cor_fluente(self.ACCENT)
        try:
            visible_start, visible_end = visible_row_range(
                float(canvas.yview()[0]),
                max(1, int(canvas.winfo_height())),
                MAX_ROWS,
                tree.row_height,
                DEFAULT_OVERSCAN,
            )
        except (tk.TclError, TypeError, ValueError):
            visible_start, visible_end = 0, MAX_ROWS

        for row, col in sorted(normalized):
            # Só desenha o que está na viewport; a seleção continua sendo
            # armazenada integralmente no estado canônico.
            if row < visible_start or row >= visible_end:
                continue
            bbox = tree.cell_bbox(str(row), f"#{col + 1}")
            if not bbox:
                continue
            x, y, width, height = bbox
            canvas.create_rectangle(
                x + 1,
                y + 1,
                x + width - 1,
                y + height - 1,
                outline=cor,
                width=2,
                fill="",
                tags=("planilha-selection",),
            )

        try:
            canvas.tag_raise("planilha-selection")
        except tk.TclError:
            pass

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

        self._planilha_desenhar_borda()

    def _planilha_retangulo_selecao(self, inicio, fim):
        return rectangle_selection(inicio, fim)


    def _planilha_clicar_celula(self, event):
        tree = self._planilha_tree
        if tree is None:
            return "break"
        current = tree.identify_cell(event.x, event.y)
        if current is None:
            return "break"

        agora = time.monotonic()
        anterior = getattr(self, "_planilha_ultimo_clique", None)
        duplo_clique = False
        if isinstance(anterior, tuple) and len(anterior) == 3:
            anterior_cell, anterior_t, anterior_xy = anterior
            duplo_clique = (
                anterior_cell == current
                and agora - float(anterior_t) <= 0.45
                and abs(event.x - anterior_xy[0]) <= 8
                and abs(event.y - anterior_xy[1]) <= 8
            )
        self._planilha_ultimo_clique = (
            current,
            agora,
            (event.x, event.y),
        )

        if duplo_clique:
            self._planilha_duplo_clique_celula(event)
            self._planilha_ultimo_clique = None
            return "break"

        active = getattr(self, "_planilha_celula_ativa", None)
        shift = bool(getattr(event, "state", 0) & 0x0001)
        if shift and active:
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
        tree.focus(str(current[0]))
        tree.focus_set()
        return "break"


    def _planilha_arrastar_selecao(self, event):
        tree = self._planilha_tree
        anchor = getattr(self, "_planilha_drag_anchor", None)
        if tree is None or anchor is None:
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

        current = tree.identify_cell(event.x, event.y)
        if current is None:
            return "break"

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

        current = tree.identify_cell(event.x, event.y)
        if current is not None:
            cells = (
                self._planilha_retangulo_selecao(anchor, current)
                if getattr(self, "_planilha_dragging", False)
                else {current}
            )
            self._planilha_definir_selecao(cells, active=current)
            tree.focus(str(current[0]))

        if getattr(self, "_planilha_dragging", False):
            self._planilha_ultimo_clique = None
        self._planilha_drag_anchor = None
        self._planilha_drag_start_xy = None
        self._planilha_dragging = False
        return "break"


    def _planilha_duplo_clique_celula(self, event):
        tree = self._planilha_tree
        if tree is None:
            return "break"

        current = tree.identify_cell(event.x, event.y)
        if current is None:
            return "break"

        row, col_index = current
        self._planilha_definir_selecao({current}, active=current)
        tree.focus(str(row))
        tree.focus_set()
        self._planilha_editar_iid(str(row), col_index)
        return "break"

    def _planilha_selecionar_tudo(self):
        if self._planilha_tree:
            self._planilha_definir_selecao(
                non_empty_cells(self._planilha_data),
            )
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

    def _planilha_tabular(self, event=None):
        """Avança uma célula à direita e, no fim da linha, para a primeira da próxima."""
        tree = self._planilha_tree
        active = getattr(self, "_planilha_celula_ativa", None)
        if tree is None or not active:
            return "break"

        try:
            row = int(active[0])
            col = int(active[1])
        except (TypeError, ValueError, IndexError):
            return "break"

        # Ctrl/Shift+Tab ficam reservados ao comportamento nativo de navegação.
        state = int(getattr(event, "state", 0) or 0) if event is not None else 0
        if state & 0x0004:
            return "break"

        if col + 1 < MAX_COLS:
            next_row, next_col = row, col + 1
        elif row + 1 < MAX_ROWS:
            next_row, next_col = row + 1, 0
        else:
            # Não existe uma linha seguinte além do limite lógico da planilha.
            next_row, next_col = row, col

        self._planilha_fechar_edicao()
        current = (next_row, next_col)
        self._planilha_definir_selecao({current}, active=current)
        tree.focus(str(next_row))
        tree.focus_set()
        tree.see(str(next_row))
        self._planilha_desenhar_borda()
        return "break"

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

    def _planilha_editar_iid(self,iid,col_index):
        tree=self._planilha_tree
        if tree is None:return
        if self._planilha_edit_entry is not None:
            self._planilha_commit_edit(True)
        bbox=tree.bbox(iid,f"#{col_index+1}")
        if not bbox:return
        self._planilha_celula_ativa=(iid,col_index)
        self._planilha_linhas_selecionadas={iid}
        self._planilha_limpar_borda()
        x,y,w,h=bbox
        vals=list(tree.item(iid,"values")); old=str(vals[col_index])
        entry=Entry(tree._canvas, bd=1, relief="solid", justify="left", font=("Segoe UI",11), highlightthickness=0)
        entry.insert(0,old); entry.place(x=x+1,y=y+1,width=max(w-2,40),height=max(h-2,24))
        self._planilha_edit_entry=entry
        self._planilha_edit_context = {
            "entry": entry,
            "iid": str(iid),
            "col_index": int(col_index),
            "old": old,
        }
        entry.focus_set()
        entry.select_range(0,"end")
        entry.bind("<Control-KeyPress-v>", self._planilha_colar_entry, add="+")
        entry.bind("<Control-KeyPress-V>", self._planilha_colar_entry, add="+")
        entry.bind("<<Paste>>", self._planilha_colar_entry, add="+")
        # Os demais atalhos permanecem nativos enquanto a célula está sendo editada.
        def finish(save=True):
            self._planilha_commit_edit(save)
        entry.bind("<Return>",lambda e:(finish(True),"break")[1])
        entry.bind("<Tab>",lambda e:(finish(True), self._planilha_tabular(e))[1])
        entry.bind("<Escape>",lambda e:(finish(False),"break")[1])
        entry.bind("<FocusOut>",lambda e:finish(True))

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

    def _criar_menu_contexto_planilha(self, tree):
        menu = Menu(
            tree,
            tearoff=False,
            font=("Segoe UI", 10),
            borderwidth=0,
            relief="flat",
        )
        menu.add_command(label="Editar", command=lambda: self._planilha_editar_selecao())
        menu.add_separator()
        menu.add_command(label="Desfazer", command=self._planilha_desfazer)
        menu.add_command(label="Refazer", command=self._planilha_refazer)
        menu.add_separator()
        menu.add_command(label="Cortar", command=self._planilha_recortar)
        menu.add_command(label="Copiar", command=self._planilha_copiar)
        menu.add_command(label="Colar", command=self._planilha_colar)
        menu.add_command(label="Excluir", command=self._planilha_limpar_celulas_selecionadas)
        menu.add_separator()
        menu.add_command(label="Selecionar tudo", command=self._planilha_selecionar_tudo)
        return menu

    def _atualizar_menu_contexto_planilha(self):
        menu = getattr(self, "_planilha_context_menu", None)
        if menu is None:
            return
        try:
            tem_celula = bool(
                getattr(self, "_planilha_celulas_selecionadas", set())
                or getattr(self, "_planilha_celula_ativa", None)
            )
            tem_undo = bool(getattr(self, "_planilha_undo", []))
            tem_redo = bool(getattr(self, "_planilha_redo", []))
            menu.entryconfig("Editar", state="normal" if tem_celula else "disabled")
            menu.entryconfig("Cortar", state="normal" if tem_celula else "disabled")
            menu.entryconfig("Copiar", state="normal" if tem_celula else "disabled")
            menu.entryconfig("Excluir", state="normal" if tem_celula else "disabled")
            menu.entryconfig("Desfazer", state="normal" if tem_undo else "disabled")
            menu.entryconfig("Refazer", state="normal" if tem_redo else "disabled")
        except Exception:
            pass

    def _planilha_copiar(self,event=None):
        tree=self._planilha_tree
        if not tree:return "break"
        rows=tuple(sorted(getattr(self, "_planilha_linhas_selecionadas", set()), key=lambda v:int(v)))
        if not rows and self._planilha_celula_ativa:
            rows=(self._planilha_celula_ativa[0],)
        if not rows:return "break"
        vals=["\t".join(map(str,tree.item(i,"values"))) for i in rows]
        self.app.clipboard_clear(); self.app.clipboard_append("\n".join(vals)); return "break"

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
        tree = self._planilha_tree
        if tree is None:
            return
        refresh = getattr(tree, "refresh", None)
        if callable(refresh):
            refresh()
            try:
                tree.after_idle(self._planilha_desenhar_borda)
            except Exception:
                self._planilha_desenhar_borda()
            return
        for iid in tree.get_children():
            i = int(iid)
            vals = [self._planilha_data.get(f"{i},{c}", "") for c in range(3)]
            tree.item(
                iid,
                values=vals,
                tags=("even" if i % 2 == 0 else "odd",),
            )
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

    def _planilha_commit_edit(self, save=True):
        entry = getattr(self, "_planilha_edit_entry", None)
        context = getattr(self, "_planilha_edit_context", None)
        if entry is None or not isinstance(context, dict):
            return
        if context.get("entry") is not entry:
            return

        iid = str(context.get("iid", ""))
        col_index = int(context.get("col_index", 0))
        old = str(context.get("old", ""))
        try:
            new = entry.get() if save else old
        except Exception:
            new = old

        tree = getattr(self, "_planilha_tree", None)
        try:
            entry.destroy()
        except Exception:
            pass
        self._planilha_edit_entry = None
        self._planilha_edit_context = None

        if tree is not None and save and new != old:
            try:
                vals = list(tree.item(iid, "values"))
                while len(vals) < 3:
                    vals.append("")
                vals[col_index] = new
                tree.item(iid, values=vals)
                self._planilha_push_undo()
                self._planilha_redo = []
                key = f"{int(iid)},{col_index}"
                if new:
                    self._planilha_data[key] = new
                else:
                    self._planilha_data.pop(key, None)
                self._planilha_marcar_alteracao()
            except Exception:
                pass

        try:
            self._planilha_desenhar_borda()
        except Exception:
            pass

    def _planilha_fechar_edicao(self):
        self._planilha_commit_edit(True)

    def _planilha_atalho_salvar(self, event=None):
        # Ctrl+S também conclui uma edição de célula antes de salvar.
        self._planilha_salvar()
        return "break"

    def _planilha_salvar(self):
        self._planilha_fechar_edicao()
        self._planilha_atualizar_estado_salvamento("salvando")
        try:
            self._salvar_planilha_interna_data()
            self._registrar_historico_planilha(self._planilha_data)
            self._planilha_salva_data = dict(self._planilha_data)
            self._planilha_apagar_rascunho()
            self._planilha_efetuou_alteracao = False
            self._planilha_atualizar_contador()
            self._planilha_atualizar_estado_salvamento("salvo")
            self._add_activity("Planilha interna salva.", self.SUCCESS)
            return True
        except Exception as exc:
            self._planilha_atualizar_estado_salvamento("erro")
            messagebox.showerror(
                "Não foi possível salvar",
                str(exc),
                parent=self._planilha_window,
            )
            return False

    def _planilha_encerrar_janela(self):
        """Fecha a janela da planilha de forma robusta, sem depender do foco."""
        win=self._planilha_window
        self._planilha_window=None
        self._planilha_tree=None
        self._planilha_row_header=None
        job = getattr(self, "_planilha_borda_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
            self._planilha_edit_entry=None
        self._planilha_edit_context=None
        if self._planilha_context_menu is not None:
            try:
                self._planilha_context_menu.destroy()
            except Exception:
                pass
        self._planilha_context_menu=None

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
        if not self._planilha_salvar():
            return
        self._planilha_encerrar_janela()

    def _extrair_codigos_planilha(self):
        """Retorna todos os códigos preenchidos na segunda coluna (Senha)."""
        return extract_column(self._planilha_data, column=1)

    def _validar_planilha_antes_execucao(self, cells=None):
        """Valida a estrutura da planilha antes de iniciar a automação."""
        cells = self._planilha_data if cells is None else cells
        rows = {}

        for key, value in (cells or {}).items():
            try:
                row, col = (int(part.strip()) for part in str(key).split(","))
            except (TypeError, ValueError):
                continue
            if row < 0 or col < 0 or col >= 3:
                continue
            texto = str(value or "").strip()
            if texto:
                rows.setdefault(row, {})[col] = texto

        avisos = []
        codigos_por_chave = {}

        for row in sorted(rows):
            data = rows[row]
            quantidade = data.get(0, "")
            codigo = data.get(1, "")
            item = data.get(2, "")
            numero_linha = row + 1

            if not codigo:
                if quantidade or item:
                    avisos.append(
                        f"Linha {numero_linha}: não possui código na coluna Senha e será ignorada."
                    )
                continue

            chave_codigo = codigo.casefold()
            anteriores = codigos_por_chave.setdefault(chave_codigo, [])
            anteriores.append(numero_linha)

            if not quantidade:
                avisos.append(
                    f"Linha {numero_linha}: código {codigo} está sem quantidade."
                )
            else:
                quantidade_normalizada = quantidade.replace(" ", "").replace(",", ".")
                try:
                    valor = float(quantidade_normalizada)
                    quantidade_valida = valor > 0 and valor.is_integer()
                except (TypeError, ValueError):
                    quantidade_valida = False
                if not quantidade_valida:
                    avisos.append(
                        f"Linha {numero_linha}: quantidade \"{quantidade}\" não é um número inteiro positivo."
                    )

        for codigo, linhas in codigos_por_chave.items():
            if len(linhas) > 1:
                avisos.append(
                    f"Código {codigo.upper()} aparece nas linhas {', '.join(map(str, linhas))} "
                    "e será executado uma vez por ocorrência."
                )

        if not avisos:
            return True

        limite = 12
        exibidos = avisos[:limite]
        detalhes = "\n".join(f"• {texto}" for texto in exibidos)
        if len(avisos) > limite:
            detalhes += f"\n• ... e mais {len(avisos) - limite} ponto(s) de atenção."

        mensagem = (
            f"Foram encontrados {len(avisos)} ponto(s) de atenção na planilha.\n\n"
            f"{detalhes}\n\n"
            "Deseja continuar mesmo assim?"
        )
        return messagebox.askyesno(
            "Validação da planilha",
            mensagem,
            parent=self._planilha_window or self.app,
        )

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

            # O arquivo é permanente. Registros antigos não são removidos aqui.
            validos = [item for item in itens if isinstance(item, dict)]
            validos.sort(key=lambda item: str(item.get("saved_at", "")))

            self._planilha_historico_cache = list(validos)
            self._planilha_historico_cache_signature = (
                self._assinatura_historico_planilhas() or assinatura
            )
            return list(validos)
        except Exception:
            self._invalidar_cache_historico_planilhas()
            return []

    def _salvar_historico_planilhas(self, itens):
        self._garantir_pasta_planilha()
        validos = [item for item in (itens or []) if isinstance(item, dict)]
        validos.sort(key=lambda item: str(item.get("saved_at", "")))
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
            ultimo_saved = str(ultimo.get("saved_at", ""))
            try:
                ultimo_data = datetime.fromisoformat(ultimo_saved).date()
            except Exception:
                ultimo_data = None

            if ultimo.get("cells") == cells and ultimo_data == agora.date():
                entrada["id"] = ultimo.get("id", entrada["id"])
                entrada["filled"] = ultimo.get("filled", len(linhas))
                itens[-1] = entrada
            else:
                itens.append(entrada)
        else:
            itens.append(entrada)
        self._salvar_historico_planilhas(itens)

    def _preparar_planilha_do_dia(self):
        """Arquiva uma versão anterior sem apagar a planilha atualmente salva."""
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
                # Cria o snapshot histórico da versão anterior, mas mantém a
                # planilha salva como está para que nenhum dado do usuário seja
                # perdido somente porque o aplicativo foi aberto em outro dia.
                self._registrar_historico_planilha(cells, salvo)
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
        """Retorna a quantidade de códigos efetivamente registrados em Arquivos no mês exibido.

        O contador do calendário deve refletir a mesma fonte usada para os
        destaques dos dias: o histórico de planilhas salvas. Execuções sem um
        snapshot salvo não criam indicação no calendário e, portanto, não entram
        neste contador.
        """
        referencia = referencia or datetime.now()
        if hasattr(referencia, "year") and hasattr(referencia, "month"):
            ano = int(referencia.year)
            mes = int(referencia.month)
        else:
            hoje = datetime.now()
            ano, mes = hoje.year, hoje.month

        total = 0
        try:
            for item in self._historico_planilhas_visiveis():
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
                total += max(0, preenchidas)
        except Exception:
            return 0
        return total

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
        """Retorna o mês mais antigo existente no histórico de Arquivos."""
        itens = self._carregar_historico_planilhas()
        datas = []
        for item in itens:
            try:
                datas.append(datetime.fromisoformat(str(item.get("saved_at", ""))))
            except Exception:
                continue
        if not datas:
            return self._mes_atual_arquivos()
        mais_antigo = min(datas)
        return datetime(mais_antigo.year, mais_antigo.month, 1)

    def _mes_atual_arquivos(self):
        agora = datetime.now()
        return datetime(agora.year, agora.month, 1)

    def _historico_planilhas_visiveis(self):
        """Retorna todo o histórico válido de Arquivos, sem limite artificial de quantidade."""
        agora = datetime.now()
        visiveis = []
        for item in self._carregar_historico_planilhas():
            try:
                salvo = datetime.fromisoformat(str(item.get("saved_at", "")))
            except Exception:
                continue
            if salvo <= agora:
                visiveis.append(item)
        return visiveis

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
        itens = self._historico_planilhas_visiveis()
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
            text="Os dias com planilhas salvas ficam destacados. O histórico de arquivos não possui limite de quantidade.",
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
        mes = self._arquivos_mes
        if not mes:
            mes = self._mes_atual_arquivos()
            self._arquivos_mes = mes

        itens = self._historico_planilhas_visiveis()
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
                valido = self._mes_minimo_arquivos().date() <= data <= hoje
                tem_arquivo = data in por_dia
                eh_hoje = data == hoje
                selecionado = data in self._arquivos_datas_selecionadas
                fill = bg
                outline = border
                fg = text if valido else disabled
                width = 1
                if selecionado and valido:
                    fill = "#DDEEFF" if not modo_escuro else "#214F70"
                    outline = accent
                    width = 2
                elif tem_arquivo and valido:
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
            item_ids = canvas.find_overlapping(event.x, event.y, event.x, event.y)
        except Exception:
            return
        data = None
        for item_id in reversed(item_ids):
            for tag in canvas.gettags(item_id):
                if tag.startswith("dia:"):
                    try:
                        data = datetime.fromisoformat(tag[4:]).date()
                    except Exception:
                        data = None
                    break
            if data is not None:
                break
        if data is None:
            return

        hoje = datetime.now().date()
        if not (self._mes_minimo_arquivos().date() <= data <= hoje):
            return

        ctrl = bool(getattr(event, "state", 0) & 0x0004)
        if ctrl:
            if data in self._arquivos_datas_selecionadas:
                self._arquivos_datas_selecionadas.remove(data)
            else:
                self._arquivos_datas_selecionadas.add(data)
            self._atualizar_botao_apagar_datas_arquivos()
            self._desenhar_calendario_arquivos()
            return "break"

        self._arquivos_datas_selecionadas = {data}
        self._atualizar_botao_apagar_datas_arquivos()
        self._desenhar_calendario_arquivos()
        self._mostrar_planilhas_do_dia(data)
        return "break"

    def _atualizar_botao_apagar_datas_arquivos(self):
        btn = getattr(self, "_arquivos_btn_apagar_selecionados", None)
        if btn is None:
            return
        try:
            quantidade = len(self._arquivos_datas_selecionadas)
            if quantidade:
                texto = f"Apagar {quantidade} selecionada" if quantidade == 1 else f"Apagar {quantidade} selecionadas"
                btn.configure(text=texto)
                btn.pack(side="right", padx=(0, 6))
            else:
                btn.configure(text="Apagar selecionados")
                btn.pack_forget()
        except Exception:
            pass

    def _apagar_datas_arquivos_selecionadas(self):
        selecionadas = set(self._arquivos_datas_selecionadas)
        if not selecionadas:
            return "break"

        itens = self._carregar_historico_planilhas()
        restantes = []
        removidos = 0
        for item in itens:
            try:
                data = datetime.fromisoformat(str(item.get("saved_at", ""))).date()
            except Exception:
                restantes.append(item)
                continue
            if data in selecionadas:
                removidos += 1
            else:
                restantes.append(item)

        confirmar = messagebox.askyesno(
            "Apagar selecionados",
            f"Tem certeza que deseja apagar os arquivos de {len(selecionadas)} data(s) selecionada(s)?\n\n"
            f"Isso removerá {removidos} planilha(s) do histórico.",
            parent=self._planilha_historico_window,
        )
        if not confirmar:
            return "break"

        self._salvar_historico_planilhas(restantes)
        self._arquivos_datas_selecionadas.clear()
        self._arquivos_data_selecionada = None
        self._atualizar_botao_apagar_datas_arquivos()
        self._desenhar_calendario_arquivos()
        self._atualizar_contador_arquivos(self._arquivos_mes)
        return "break"

    def _mudar_mes_arquivos(self, direcao):
        atual = self._arquivos_mes or self._mes_atual_arquivos()
        novo = self._mes_proximo(atual) if direcao > 0 else self._mes_anterior(atual)
        if novo < self._mes_minimo_arquivos() or novo > self._mes_atual_arquivos():
            return
        self._arquivos_mes = novo
        self._arquivos_datas_selecionadas.clear()
        self._atualizar_botao_apagar_datas_arquivos()
        self._atualizar_contador_arquivos(novo)
        self._desenhar_calendario_arquivos()

    def _mostrar_planilhas_do_dia(self, data, destaque_id=None):
        if self._arquivos_body is None:
            return
        hoje = datetime.now().date()
        if data < self._mes_minimo_arquivos().date() or data > hoje:
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
        self._arquivos_datas_selecionadas.clear()
        self._atualizar_botao_apagar_datas_arquivos()
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

        metricas = ctk.CTkFrame(self._arquivos_body, fg_color="transparent")
        metricas.pack(fill="x", pady=(0, 8))
        metricas.grid_columnconfigure((0, 1), weight=1)

        tempo_box = ctk.CTkFrame(
            metricas, fg_color=("#F3F7FA", "#24343D"), corner_radius=8, height=42
        )
        tempo_box.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        tempo_box.grid_propagate(False)
        ctk.CTkLabel(
            tempo_box, text="Tempo decorrido", text_color=self.SUBTEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(9, 6))
        self._arquivos_tempo_decorrido_label = ctk.CTkLabel(
            tempo_box,
            text=self._formatar_duracao(getattr(self, "_ultimo_tempo_decorrido_segundos", 0)),
            text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        )
        self._arquivos_tempo_decorrido_label.pack(side="right", padx=(2, 9))

        media_box = ctk.CTkFrame(
            metricas, fg_color=("#F3F7FA", "#24343D"), corner_radius=8, height=42
        )
        media_box.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        media_box.grid_propagate(False)
        ultimo_tempo = float(getattr(self, "_ultimo_tempo_decorrido_segundos", 0) or 0)
        ultimo_codigos = int(getattr(self, "_ultimo_codigos_medidos", 0) or 0)
        media_inicial = (
            f"{ultimo_codigos / (ultimo_tempo / 60.0):.1f} cód/min"
            if ultimo_codigos > 0 and ultimo_tempo > 0
            else "—"
        )
        ctk.CTkLabel(
            media_box, text="Média por código (cód/min)", text_color=self.SUBTEXT,
            font=("Segoe UI", 9, "bold")
        ).pack(side="left", padx=(9, 6))
        self._arquivos_media_codigo_label = ctk.CTkLabel(
            media_box, text=media_inicial, text_color=self.TEXT,
            font=("Segoe UI", 13, "bold")
        )
        self._arquivos_media_codigo_label.pack(side="right", padx=(2, 9))
        self._atualizar_metricas_execucao()

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
            card = ctk.CTkFrame(
                lista,
                fg_color=self.CARD,
                corner_radius=8,
                border_width=1,
                border_color=(
                    self.ACCENT
                    if str(item.get("id", "")) == str(destaque_id or "")
                    else self.BORDER
                ),
            )
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
        win.bind("<Control-KeyPress-f>", self._abrir_busca_arquivos, add="+")
        win.bind("<Control-KeyPress-F>", self._abrir_busca_arquivos, add="+")
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
        self._centralizar_janela(win, 820, 650)

        header = ctk.CTkFrame(win, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 8))
        ctk.CTkLabel(header, text="Arquivos", text_color=self.TEXT, font=("Segoe UI", 20, "bold")).pack(side="left")
        self._arquivos_contador_janela = ctk.CTkLabel(header, text="0 códigos no mês", text_color=self.SUBTEXT, font=("Segoe UI", 10, "bold"))
        self._arquivos_contador_janela.pack(side="left", padx=(10, 0))
        self._arquivos_btn_apagar_selecionados = ctk.CTkButton(
            header,
            text="Apagar selecionados",
            command=self._apagar_datas_arquivos_selecionadas,
            width=150, height=32, corner_radius=8,
            fg_color=self.CARD,
            hover_color=("#FDECEC", "#3A2424"),
            border_width=1, border_color=self.ERROR,
            text_color=self.ERROR, font=("Segoe UI", 10, "bold")
        )
        self._arquivos_btn_apagar_selecionados.pack(side="right", padx=(0, 6))
        self._arquivos_btn_apagar_selecionados.pack_forget()

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
        _ui_scan_tooltips(win)

    def _planilha_salvar_e_iniciar(self):
        self._planilha_fechar_edicao()
        self._planilha_atualizar_estado_salvamento("salvando")
        if not self._validar_planilha_antes_execucao():
            return
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
            self._planilha_atualizar_estado_salvamento("salvo")
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

    def _iniciar_automacao_interna(self, codigos, ignorar_checkpoint=False):
        codigos=[str(c).strip() for c in codigos if str(c).strip()]
        if not codigos:
            messagebox.showwarning("Nenhum código","A coluna 'Senha' está vazia.",parent=self.app)
            return

        inicio = None if ignorar_checkpoint else ler_checkpoint_interno(codigos)
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
        self._execucao_atual["origem"] = getattr(self, "_origem_reexecucao", "planilha_interna")
        if getattr(self, "_reexecucao_origem_id", None):
            self._execucao_atual["reexecucao_de"] = self._reexecucao_origem_id
            self._reexecucao_origem_id = None
        self._origem_reexecucao = "planilha_interna"
        self._execucao_atual["planilha_fingerprint"] = self._planilha_fingerprint(self._planilha_data)
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
        if self._execucao_progresso_card is not None:
            self._set_stat(self._execucao_progresso_card, f"{(start / len(codigos)):.0%}" if codigos else "0%")
        self._iniciar_metricas_execucao(start, len(codigos))
        self._erros_codigos = []
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
        if not self._validar_planilha_antes_execucao():
            return
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
        self._parar_metricas_execucao()
        if self._execucao_titulo_label is not None:
            self._execucao_titulo_label.configure(text="Execução interrompida")
        if self._execucao_subtitulo_label is not None:
            self._execucao_subtitulo_label.configure(text="Ocorreu um erro durante o processamento.")
        if self._execucao_indicador_label is not None:
            self._execucao_indicador_label.configure(text="●  Atenção", text_color=self.ERROR)
        self.botao_iniciar.configure(state="normal")
        self.botao_planilha.configure(state="normal")
        self.botao_parar.configure(state="disabled")
        self._add_activity("Processo interrompido por erro.", self.ERROR)
        self._registrar_falha_historico(msg)
        self._aplicar_status("Processo interrompido por erro")
        messagebox.showerror("Erro no processo", msg)

    def _finalizar(self, resultado):
        self._parar_metricas_execucao()
        if self._execucao_titulo_label is not None:
            self._execucao_titulo_label.configure(
                text="Execução interrompida" if self._parar else "Execução concluída"
            )
        if self._execucao_subtitulo_label is not None:
            self._execucao_subtitulo_label.configure(
                text="O ponto de retomada foi salvo." if self._parar else "Processamento finalizado."
            )
        if self._execucao_indicador_label is not None:
            self._execucao_indicador_label.configure(
                text="●  Interrompida" if self._parar else "●  Concluída",
                text_color=self.WARNING if self._parar else self.SUCCESS
            )
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
            try:
                self._marcar_planilha_interna_processada(self._planilha_data)
            except Exception:
                pass
            self._finalizar_historico_execucao(resultado, "Concluída")
            # Aplicar imediatamente: evita que a messagebox bloqueie a atualização
            # do cabeçalho deixando-o visualmente em "Processando".
            self._aplicar_status("Finalizado")

        for item in resultado.itens:
            if item.status == "Erro":
                self._add_erro_codigo(item.codigo)
        if getattr(self, "_visualizacao", "complete") != "compact":
            self._selecionar_aba("Atividade")

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
                "Os códigos com erro estão disponíveis nos detalhes do histórico."
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

    def _aplicar_status(self, texto):
        if getattr(self, "_visualizacao", "complete") == "compact":
            return
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
        self._iniciar_pisca_status()

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
        self._atualizar_metricas_execucao()
        if getattr(self, "_visualizacao", "complete") == "compact":
            return
        self.status_label.configure(
            text=f"Processando código {processados} de {total}",
            text_color=self.INFO,
        )
        self._status_text_base = "Processando"
        self.status_pill.configure(fg_color=("#E5F1FB", "#183B54"))
        self.status_text.configure(text="Processando", text_color=self.INFO)
        if self._execucao_titulo_label is not None:
            self._execucao_titulo_label.configure(text="Execução em andamento")
        if self._execucao_subtitulo_label is not None:
            self._execucao_subtitulo_label.configure(
                text="Automatizando autorizações. Aguarde..."
            )
        if self._execucao_indicador_label is not None:
            self._execucao_indicador_label.configure(
                text="●  Em andamento", text_color=self.INFO
            )
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

                if str(self._execucao_atual.get("origem", "")) == "planilha_interna":
                    codigos = self._extrair_codigos_planilha()
                    if codigos:
                        salvar_checkpoint_interno(codigos, indice)

                self._salvar_estado_persistente()
            except Exception:
                # O fechamento nunca deve ser impedido por uma falha de persistência.
                logging.getLogger(__name__).exception(
                    "Falha ao salvar checkpoint durante o fechamento do aplicativo."
                )

        # Consolida também o histórico quando o aplicativo é fechado sem uma
        # execução ativa, garantindo a migração do arquivo legado para o arquivo
        # canônico e evitando perda de dados após atualizações/reinicializações.
        self._salvar_estado_persistente()

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

        for job_attr in (
            "_fluent_accent_job",
            "_progress_anim_job",
            "_micro_dashboard_complete_job",
            "_execucao_timer_job",
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
        win = getattr(self, "_historico_compacto_window", None)
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass
            self._historico_compacto_window = None
        self.app.destroy()

    def run(self):
        self.app.mainloop()

