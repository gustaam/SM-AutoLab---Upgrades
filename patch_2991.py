from __future__ import annotations

import calendar as pycalendar
import json
from datetime import datetime
import tkinter as tk


PATCH_2991_MARKER = "SM-AUTOLAB-PLANILHA-ARQUIVOS-UI"


def _iter_descendants(widget):
    if widget is None:
        return
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _iter_descendants(child)


def _widget_exists(widget):
    try:
        return bool(widget is not None and widget.winfo_exists())
    except Exception:
        return False


def _count_saved_passwords(self):
    try:
        path = getattr(self, "_planilha_arquivo", None)
        if path is None or not path.exists():
            return 0
        payload = json.loads(path.read_text(encoding="utf-8"))
        cells = payload.get("cells", {}) if isinstance(payload, dict) else {}
        if not isinstance(cells, dict):
            return 0
        total = 0
        for key, value in cells.items():
            try:
                _row, col = (int(part) for part in str(key).split(","))
            except Exception:
                continue
            if col == 1 and str(value).strip() != "":
                total += 1
        return total
    except Exception:
        return 0


def _update_saved_password_counter(self):
    label = getattr(self, "arquivos_contador_label", None)
    if label is None:
        return
    total = _count_saved_passwords(self)
    try:
        if total > 0:
            label.configure(text=f"{total} Códigos selecionados")
            label.pack_configure(side="left", padx=(8, 0))
        else:
            label.pack_forget()
    except Exception:
        pass


def _after_planilha_save_2991(self, result=None):
    try:
        self.app.after_idle(lambda: _update_saved_password_counter(self))
    except Exception:
        _update_saved_password_counter(self)
    return result


def _planilha_salvar_e_sair_2991(self, *args, **kwargs):
    result = self._patch2991_original_salvar_e_sair(*args, **kwargs)
    return _after_planilha_save_2991(self, result)


def _planilha_salvar_e_iniciar_2991(self, *args, **kwargs):
    result = self._patch2991_original_salvar_e_iniciar(*args, **kwargs)
    return _after_planilha_save_2991(self, result)


def _formatar_selecao_2991(self):
    total = len(getattr(self, "_arquivos_datas_selecionadas", set()))
    label = getattr(self, "_arquivos_contador_selecao", None)
    if label is not None:
        try:
            label.configure(text=f"{total} Selecionadas")
        except Exception:
            pass
    btn = getattr(self, "_arquivos_btn_apagar_selecionados", None)
    if btn is not None:
        try:
            btn.configure(state="normal" if total else "disabled")
        except Exception:
            pass


def _abrir_historico_planilha_2991(self, *args, **kwargs):
    result = self._patch2991_original_abrir_historico_planilha(*args, **kwargs)
    win = getattr(self, "_planilha_historico_window", None)
    if win is None or not _widget_exists(win):
        return result
    for widget in _iter_descendants(win):
        try:
            texto = str(widget.cget("text")) if hasattr(widget, "cget") else ""
        except Exception:
            texto = ""
        if "Ctrl + clique para selecionar várias datas" in texto:
            try:
                widget.destroy()
            except Exception:
                pass
    _formatar_selecao_2991(self)
    return result


def _draw_calendar_sunday_first_2991(self, *args, **kwargs):
    original_calendar = pycalendar.Calendar
    try:
        pycalendar.Calendar = lambda firstweekday=0: original_calendar(firstweekday=6)
        return self._patch2991_original_draw_calendar(*args, **kwargs)
    finally:
        pycalendar.Calendar = original_calendar


def _selection_cells(self):
    return getattr(self, "_planilha_celulas_selecionadas", set()) or set()


def _set_selection(self, cells, active=None):
    normalized = {
        (int(r), int(c))
        for r, c in cells
        if 0 <= int(r) < 10000 and 0 <= int(c) < 3
    }
    self._planilha_celulas_selecionadas = normalized
    self._planilha_linhas_selecionadas = {str(r) for r, _c in normalized}
    if active is not None:
        self._planilha_celula_ativa = (str(active[0]), int(active[1]))
    elif normalized:
        first = min(normalized)
        self._planilha_celula_ativa = (str(first[0]), first[1])
    else:
        self._planilha_celula_ativa = None
    try:
        self._planilha_desenhar_borda()
    except Exception:
        pass


def _rectangle(a, b):
    r1, c1 = int(a[0]), int(a[1])
    r2, c2 = int(b[0]), int(b[1])
    lo_r, hi_r = sorted((r1, r2))
    lo_c, hi_c = sorted((c1, c2))
    return {(r, c) for r in range(lo_r, hi_r + 1) for c in range(lo_c, hi_c + 1)}


def _planilha_clicar_celula_2991(self, event):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return "break"
    row = tree.identify_row(event.y)
    col_id = tree.identify_column(event.x)
    if not row or col_id not in ("#1", "#2", "#3"):
        return "break"
    col = int(col_id[1:]) - 1
    self._planilha_drag_anchor = (int(row), col)
    self._planilha_dragging = False
    self._planilha_drag_start_xy = (event.x, event.y)
    self._planilha_fechar_edicao()
    _set_selection(self, {(int(row), col)}, active=(int(row), col))
    tree.focus_set()
    return "break"


def _planilha_arrastar_selecao_2991(self, event):
    tree = getattr(self, "_planilha_tree", None)
    anchor = getattr(self, "_planilha_drag_anchor", None)
    if tree is None or anchor is None:
        return "break"
    start_x, start_y = getattr(self, "_planilha_drag_start_xy", (event.x, event.y))
    if not self._planilha_dragging and abs(event.x - start_x) < 4 and abs(event.y - start_y) < 4:
        return "break"
    row = tree.identify_row(event.y)
    col_id = tree.identify_column(event.x)
    if not row or col_id not in ("#1", "#2", "#3"):
        return "break"
    current = (int(row), int(col_id[1:]) - 1)
    self._planilha_dragging = True
    _set_selection(self, _rectangle(anchor, current), active=current)
    return "break"


def _planilha_soltar_selecao_2991(self, event):
    tree = getattr(self, "_planilha_tree", None)
    anchor = getattr(self, "_planilha_drag_anchor", None)
    if tree is None or anchor is None:
        return "break"
    row = tree.identify_row(event.y)
    col_id = tree.identify_column(event.x)
    if row and col_id in ("#1", "#2", "#3"):
        current = (int(row), int(col_id[1:]) - 1)
        cells = _rectangle(anchor, current) if getattr(self, "_planilha_dragging", False) else {current}
        _set_selection(self, cells, active=current)
    self._planilha_drag_anchor = None
    self._planilha_dragging = False
    return "break"


def _planilha_iniciar_digitacao_2991(self, event):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None or getattr(self, "_planilha_edit_entry", None) is not None:
        return
    active = getattr(self, "_planilha_celula_ativa", None)
    if not active:
        return
    if event.keysym in {
        "Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
        "Caps_Lock", "Num_Lock", "Escape", "Return"
    }:
        return
    texto = event.char or ""
    if texto and texto.isprintable() and not (event.state & 0x0004):
        iid, col = active
        self._planilha_editar_iid(iid, int(col))
        entry = getattr(self, "_planilha_edit_entry", None)
        if entry is not None:
            try:
                entry.delete(0, tk.END)
                entry.insert(0, texto)
            except Exception:
                pass
        return "break"


def _planilha_selecionar_tudo_2991(self):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return "break"
    cells = set()
    for key, value in self._planilha_data.items():
        try:
            row, col = (int(part) for part in str(key).split(","))
        except Exception:
            continue
        if 0 <= row < 10000 and 0 <= col < 3 and str(value).strip() != "":
            cells.add((row, col))
    _set_selection(self, cells)
    return "break"


def _planilha_copiar_2991(self, event=None):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return "break"
    cells = _selection_cells(self)
    if not cells:
        active = getattr(self, "_planilha_celula_ativa", None)
        if active:
            cells = {(int(active[0]), int(active[1]))}
    if not cells:
        return "break"
    min_r = min(r for r, _c in cells)
    max_r = max(r for r, _c in cells)
    min_c = min(c for _r, c in cells)
    max_c = max(c for _r, c in cells)
    output = []
    for r in range(min_r, max_r + 1):
        row_values = []
        for c in range(min_c, max_c + 1):
            try:
                row_values.append(str(tree.item(str(r), "values")[c]))
            except Exception:
                row_values.append("")
        output.append("\t".join(row_values))
    try:
        self.app.clipboard_clear()
        self.app.clipboard_append("\n".join(output))
    except Exception:
        pass
    return "break"


def _planilha_desenhar_borda_2991(self):
    self._patch2991_original_desenhar_borda()
    tree = getattr(self, "_planilha_tree", None)
    cells = _selection_cells(self)
    if tree is None or len(cells) <= 1:
        return
    min_r = min(r for r, _c in cells)
    max_r = max(r for r, _c in cells)
    min_c = min(c for _r, c in cells)
    max_c = max(c for _r, c in cells)
    boxes = []
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            bbox = tree.bbox(str(r), f"#{c + 1}")
            if bbox:
                boxes.append(bbox)
    if not boxes:
        return
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[0] + b[2] for b in boxes)
    y1 = max(b[1] + b[3] for b in boxes)
    cor = self.ACCENT[0] if isinstance(self.ACCENT, tuple) else self.ACCENT
    for px, py, pw, ph in (
        (x0, y0, x1 - x0, 2),
        (x0, y1 - 2, x1 - x0, 2),
        (x0, y0, 2, y1 - y0),
        (x1 - 2, y0, 2, y1 - y0),
    ):
        frame = tk.Frame(tree, width=max(int(pw), 1), height=max(int(ph), 1), bg=cor, bd=0, highlightthickness=0)
        frame.place(x=int(px), y=int(py))
        frame.lift()
        self._planilha_borda_widgets.append(frame)


def _install_planilha_bindings_2991(self):
    tree = getattr(self, "_planilha_tree", None)
    if tree is None:
        return
    for sequence in ("<ButtonPress-1>", "<B1-Motion>", "<ButtonRelease-1>"):
        try:
            tree.unbind(sequence)
        except Exception:
            pass
    tree.bind("<ButtonPress-1>", self._planilha_clicar_celula)
    tree.bind("<B1-Motion>", self._planilha_arrastar_selecao)
    tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao)
    tree.bind("<KeyPress>", self._planilha_iniciar_digitacao, add="+")

    try:
        old_menu = getattr(self, "_planilha_context_menu", None)
        if old_menu is not None:
            old_menu.destroy()
    except Exception:
        pass
    try:
        tree.unbind("<Button-3>")
    except Exception:
        pass

    menu = tk.Menu(tree, tearoff=False)

    def copy_action():
        self._planilha_copiar()

    def cut_action():
        cells = _selection_cells(self)
        if not cells:
            return
        self._planilha_push_undo()
        for r, c in cells:
            self._planilha_data.pop(f"{r},{c}", None)
            try:
                vals = list(tree.item(str(r), "values"))
                vals[c] = ""
                tree.item(str(r), values=vals)
            except Exception:
                pass
        self._planilha_marcar_alteracao()

    def delete_action():
        cells = _selection_cells(self)
        if not cells:
            return
        self._planilha_push_undo()
        for r, c in cells:
            self._planilha_data.pop(f"{r},{c}", None)
            try:
                vals = list(tree.item(str(r), "values"))
                vals[c] = ""
                tree.item(str(r), values=vals)
            except Exception:
                pass
        self._planilha_marcar_alteracao()
        _set_selection(self, set())

    menu.add_command(label="Recortar", command=cut_action)
    menu.add_command(label="Copiar", command=copy_action)
    menu.add_command(label="Colar", command=lambda: self._planilha_colar())
    menu.add_command(label="Colar sem formatação", command=lambda: self._planilha_colar())
    menu.add_separator()
    menu.add_command(label="Excluir", command=delete_action)
    menu.add_command(label="Selecionar tudo", command=self._planilha_selecionar_tudo)

    def on_right_click(event):
        row = tree.identify_row(event.y)
        col_id = tree.identify_column(event.x)
        if row and col_id in ("#1", "#2", "#3"):
            current = (int(row), int(col_id[1:]) - 1)
            if current not in _selection_cells(self):
                _set_selection(self, {current}, active=current)
            tree.focus_set()
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
        return "break"

    tree.bind("<Button-3>", on_right_click)
    self._planilha_context_menu = menu


def _abrir_planilha_2991(self, *args, **kwargs):
    result = self._patch2991_original_abrir_planilha(*args, **kwargs)
    try:
        self.app.after_idle(lambda: _install_planilha_bindings_2991(self))
    except Exception:
        _install_planilha_bindings_2991(self)
    return result


def _renomear_historico_ui_2991(self):
    buttons = getattr(self, "tab_buttons", {})
    btn = buttons.get("Histórico")
    if btn is not None:
        try:
            btn.configure(text="Histórico de erros")
        except Exception:
            pass
    for widget in _iter_descendants(getattr(self, "aba_historico", None)):
        try:
            text = str(widget.cget("text"))
        except Exception:
            continue
        if text == "Execuções dos últimos 60 dias":
            try:
                widget.configure(text="Execuções com erros")
            except Exception:
                pass


def _ajustar_tamanho_pasta_historico_2991(self, *args, **kwargs):
    result = self._patch2991_original_criar_pasta_historico(*args, **kwargs)
    tiles = getattr(self, "_hist_tiles", set())
    if not tiles:
        return result
    tile = next(reversed(tuple(tiles)))
    if _widget_exists(tile):
        try:
            tile.configure(width=90, height=90)
            tile.grid_propagate(False)
            children = tile.winfo_children()
            labels = [w for w in children if isinstance(w, ctk.CTkLabel)]
            for w in labels:
                text = str(w.cget("text"))
                if "•" in text:
                    w.configure(wraplength=82, font=("Segoe UI", 8))
        except Exception:
            pass
    return result


def _config_app_2991(self, *args, **kwargs):
    result = self._patch2991_original_config_app(*args, **kwargs)
    try:
        _renomear_historico_ui_2991(self)
        _update_saved_password_counter(self)
    except Exception:
        pass
    return result


def aplicar_patch_2991(App):
    if getattr(App, "_patch_2991_aplicado", False):
        return
    App._patch_2991_aplicado = True

    App._patch2991_original_config_app = App.config_app
    App.config_app = _config_app_2991

    App._patch2991_original_abrir_historico_planilha = App._abrir_historico_planilha
    App._abrir_historico_planilha = _abrir_historico_planilha_2991

    App._patch2991_original_draw_calendar = App._desenhar_calendario_arquivos
    App._desenhar_calendario_arquivos = _draw_calendar_sunday_first_2991

    App._patch2991_original_abrir_planilha = App.abrir_planilha
    App.abrir_planilha = _abrir_planilha_2991

    App._patch2991_original_desenhar_borda = App._planilha_desenhar_borda
    App._planilha_desenhar_borda = _planilha_desenhar_borda_2991

    App._planilha_clicar_celula = _planilha_clicar_celula_2991
    App._planilha_arrastar_selecao = _planilha_arrastar_selecao_2991
    App._planilha_soltar_selecao = _planilha_soltar_selecao_2991
    App._planilha_iniciar_digitacao = _planilha_iniciar_digitacao_2991
    App._planilha_selecionar_tudo = _planilha_selecionar_tudo_2991
    App._planilha_copiar = _planilha_copiar_2991

    App._patch2991_original_salvar_e_sair = App._planilha_salvar_e_sair
    App._planilha_salvar_e_sair = _planilha_salvar_e_sair_2991
    if hasattr(App, "_planilha_salvar_e_iniciar"):
        App._patch2991_original_salvar_e_iniciar = App._planilha_salvar_e_iniciar
        App._planilha_salvar_e_iniciar = _planilha_salvar_e_iniciar_2991

    App._patch2991_original_criar_pasta_historico = App._criar_pasta_historico
    App._criar_pasta_historico = _ajustar_tamanho_pasta_historico_2991

    App._atualizar_contador_selecao = _formatar_selecao_2991
