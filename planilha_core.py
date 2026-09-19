from __future__ import annotations

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
