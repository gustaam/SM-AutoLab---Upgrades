from __future__ import annotations

import ctypes
import os
import sys


DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMWCP_ROUND = 2

DWMSBT_MAINWINDOW = 2
DWMSBT_TRANSIENTWINDOW = 3
DWMSBT_TABBEDWINDOW = 4

MIN_BACKDROP_BUILD = 22621


def _is_supported_windows() -> bool:
    if os.name != "nt":
        return False
    try:
        return int(sys.getwindowsversion().build) >= MIN_BACKDROP_BUILD
    except AttributeError:
        return False


def _set_dwm_attribute(hwnd: int, attribute: int, value: ctypes._SimpleCData) -> bool:
    try:
        dwmapi = ctypes.WinDLL("dwmapi")
        setter = dwmapi.DwmSetWindowAttribute
        setter.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_uint,
        ]
        setter.restype = ctypes.c_long
        payload = ctypes.byref(value)
        result = setter(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(attribute),
            payload,
            ctypes.c_uint(ctypes.sizeof(value)),
        )
        return int(result) == 0
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def aplicar_backdrop_sistema(window, material="mica", dark=None):
    """Aplica Mica/Mica Alt/Acrylic via DWM; retorna False quando indisponível."""
    if window is None or not _is_supported_windows():
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

    ok = _set_dwm_attribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.c_int(backdrop))

    if dark is None:
        try:
            dark = str(window.tk.call("tk", "windowingsystem")).lower() == "win32" and bool(
                window.cget("fg") == ""
            )
        except Exception:
            dark = False

    dark_value = ctypes.c_int(1 if bool(dark) else 0)
    _set_dwm_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, dark_value)

    corner = ctypes.c_int(DWMWCP_ROUND)
    _set_dwm_attribute(hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, corner)
    return ok


def atualizar_backdrop_tema(window, dark: bool):
    """Atualiza somente o modo claro/escuro do backdrop existente."""
    if window is None or not _is_supported_windows():
        return False

    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
    except Exception:
        return False

    return _set_dwm_attribute(
        hwnd,
        DWMWA_USE_IMMERSIVE_DARK_MODE,
        ctypes.c_int(1 if dark else 0),
    )
