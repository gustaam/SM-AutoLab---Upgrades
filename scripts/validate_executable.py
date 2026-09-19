from __future__ import annotations

import argparse
import struct
from pathlib import Path


MIN_EXECUTABLE_SIZE = 1_000_000


def validate_pe(path: Path, min_size: int = MIN_EXECUTABLE_SIZE) -> dict[str, object]:
    """Valida as propriedades mínimas de um executável PE sem executá-lo."""
    if not path.exists():
        raise ValueError(f"Executável não encontrado: {path}")

    size = path.stat().st_size
    if size < min_size:
        raise ValueError(
            f"Executável suspeitamente pequeno: {size} bytes < {min_size}"
        )

    with path.open("rb") as handle:
        header = handle.read(0x40)
        if len(header) < 0x40 or header[:2] != b"MZ":
            raise ValueError("Executável não possui assinatura MZ válida.")

        pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
        if pe_offset < 0x40:
            raise ValueError(f"Offset PE inválido: {pe_offset}")

        handle.seek(pe_offset)
        signature = handle.read(4)
        if signature != b"PE\x00\x00":
            raise ValueError("Executável não possui assinatura PE válida.")

    return {"path": str(path), "size": size, "pe_offset": pe_offset}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=Path)
    parser.add_argument("--min-size", type=int, default=MIN_EXECUTABLE_SIZE)
    args = parser.parse_args()

    result = validate_pe(args.executable, args.min_size)
    print(
        f"PE válido: {result['path']} "
        f"({result['size']} bytes, offset PE {result['pe_offset']})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
