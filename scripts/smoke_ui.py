"""Smoke test real da interface: instancia o App completo e encerra o Tk."""
from __future__ import annotations

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
