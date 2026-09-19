from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable, Iterable
from typing import Any


SM_AUTOLAB_GRADE_VIRTUAL_29926 = "SM-AUTOLAB-GRADE-VIRTUAL-29926"
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
    logical_top = min(total_rows - 1, int(fraction * total_rows + 1e-7))
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
        self._tags: dict[str, dict[str, Any]] = {}
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
            )
            self._pool.append(
                {
                    "background": background,
                    "line": line,
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

    def tag_configure(self, tag: str, **kwargs: Any):
        self._tags[tag] = dict(kwargs)

    def insert(self, parent: str, index: str, iid: str | None = None, values: Iterable[Any] = (), tags: Iterable[str] = ()):
        # Compatibility shim only. The virtual implementation never needs to
        # insert 10.000 graphical items; the logical data source remains primary.
        logical_iid = str(iid if iid is not None else "0")
        if self._value_provider is None:
            setattr(self, "_manual_values", getattr(self, "_manual_values", {}))
            self._manual_values[logical_iid] = tuple(
                "" if value is None else str(value) for value in values
            )
        self._focus_iid = logical_iid
        self._schedule_refresh()
        return logical_iid

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
            y = row * self._row_height - y_scroll + self._header_height
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

    def identify_row(self, y: int | float) -> str:
        try:
            body_y = float(y) - self._header_height
            if body_y < 0:
                return ""
            logical_y = float(self._canvas.canvasy(body_y))
            row = int(logical_y // self._row_height)
            return str(row) if 0 <= row < self._total_rows else ""
        except (TypeError, ValueError, tk.TclError):
            return ""

    def identify_column(self, x: int | float) -> str:
        try:
            canvas_x = float(self._canvas.canvasx(x))
        except (TypeError, ValueError, tk.TclError):
            return ""
        for idx, (name, _text, _width, _minwidth, _anchor, _stretch) in enumerate(self._columns, start=1):
            left = self._column_left(name)
            right = left + self._widths.get(name, 1)
            if left <= canvas_x < right:
                return f"#{idx}"
        return ""

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

    def event_generate(self, sequence, **kwargs: Any):
        return self._canvas.event_generate(sequence, **kwargs)


__all__ = [
    "SM_AUTOLAB_GRADE_VIRTUAL_29926",
    "VirtualGridTree",
    "visible_row_range",
]
