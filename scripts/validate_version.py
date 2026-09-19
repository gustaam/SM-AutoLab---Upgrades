from __future__ import annotations

import argparse
from pathlib import Path


def parse_version(value: str) -> tuple[int, ...]:
    text = str(value).strip()
    if text.startswith(("v", "V")):
        text = text[1:]
    parts = text.split(".")
    if len(parts) not in (3, 4) or any(not part.isdigit() for part in parts):
        return ()
    return tuple(int(part) for part in parts)


def read_version(path: Path) -> tuple[int, ...]:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"Não foi possível ler VERSION: {exc}") from exc
    parsed = parse_version(value)
    if not parsed:
        raise ValueError(f"VERSION inválida: {value!r}")
    return parsed


def validate_version(current_path: Path, previous_path: Path | None = None) -> tuple[int, ...]:
    current = read_version(current_path)
    if previous_path is not None and previous_path.exists():
        previous = read_version(previous_path)
        if current < previous:
            raise ValueError(
                f"VERSION regrediu de {'.'.join(map(str, previous))} "
                f"para {'.'.join(map(str, current))}"
            )
    return current


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version_file", type=Path, nargs="?", default=Path("VERSION"))
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    parsed = validate_version(args.version_file, args.previous)
    print(f"VERSION válida: {'.'.join(map(str, parsed))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
