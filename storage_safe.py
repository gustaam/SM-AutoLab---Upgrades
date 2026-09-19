from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def backup_path(path: Path) -> Path:
    path = Path(path)
    return path.with_name(path.name + ".bak")


def atomic_write_text(path: Path, text: str, *, backup: bool = True) -> None:
    """Grava no mesmo diretório e substitui o destino atomicamente."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(str(text))
            handle.flush()
            os.fsync(handle.fileno())

        if backup and path.exists():
            shutil.copy2(path, backup_path(path))

        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def atomic_write_json(
    path: Path,
    payload: Any,
    *,
    backup: bool = True,
) -> None:
    atomic_write_text(
        Path(path),
        json.dumps(payload, ensure_ascii=False, indent=2),
        backup=backup,
    )


def read_json_with_backup(path: Path, default: Any = None) -> Any:
    """Lê o JSON principal; em caso de corrupção, tenta o backup anterior."""
    path = Path(path)
    last_error: Exception | None = None
    for candidate in (path, backup_path(path)):
        if not candidate.exists():
            continue
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_error = exc
    if last_error is not None:
        return default
    return default


def restore_backup(path: Path) -> bool:
    path = Path(path)
    backup = backup_path(path)
    if not backup.exists():
        return False
    try:
        shutil.copy2(backup, path)
        return True
    except OSError:
        return False
