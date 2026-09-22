# Teste de inicialização real da interface.
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interface import App


def main() -> int:
    app = App()
    try:
        app.app.update_idletasks()
        print("Smoke UI: App inicializado e widgets construídos com sucesso.")
    finally:
        try:
            app.app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
