from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes

import customtkinter as ctk

from ui_platform import aplicar_backdrop_sistema, atualizar_backdrop_tema


SM_AUTOLAB_WINDOWS_NATIVE_29925 = "SM-AUTOLAB-WINDOWS-NATIVE-29925"

DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
DWMWA_SYSTEMBACKDROP_TYPE = 38

DWMWCP_ROUND = 2
DWMSBT_AUTO = 0
DWMSBT_NONE = 1
DWMSBT_MAINWINDOW = 2
DWMSBT_TRANSIENTWINDOW = 3
DWMSBT_TABBEDWINDOW = 4

DWMWA_COLOR_DEFAULT = 0xFFFFFFFF

SPI_GETHIGHCONTRAST = 0x0042
HCF_HIGHCONTRASTON = 0x00000001

_NATIVE_CONTROL_CLASSES = frozenset(
    {
        "syslistview32",
        "systreeview32",
        "listbox",
        "combobox",
        "scrollbar",
        "msctls_progress32",
        "systabcontrol32",
    }
)


class _HIGHCONTRAST(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwFlags", wintypes.DWORD),
        ("lpszDefaultScheme", wintypes.LPWSTR),
    ]


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


def _high_contrast_enabled():
    if not _windows11_available():
        return False
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        getter = user32.SystemParametersInfoW
        getter.argtypes = [
            wintypes.UINT,
            wintypes.UINT,
            ctypes.c_void_p,
            wintypes.UINT,
        ]
        getter.restype = wintypes.BOOL
        value = _HIGHCONTRAST()
        value.cbSize = ctypes.sizeof(_HIGHCONTRAST)
        if not getter(
            SPI_GETHIGHCONTRAST,
            value.cbSize,
            ctypes.byref(value),
            0,
        ):
            return False
        return bool(value.dwFlags & HCF_HIGHCONTRASTON)
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


def _set_native_frame(hwnd, *, dark, high_contrast, material=None):
    if not _windows11_available():
        return False

    changed = False

    dark_value = ctypes.c_int(1 if dark and not high_contrast else 0)
    changed = _set_dwm_attribute(
        hwnd,
        20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
        dark_value,
    ) or changed

    corner = ctypes.c_int(DWMWCP_ROUND)
    changed = _set_dwm_attribute(
        hwnd,
        33,  # DWMWA_WINDOW_CORNER_PREFERENCE
        corner,
    ) or changed

    if high_contrast:
        backdrop = ctypes.c_int(DWMSBT_NONE)
        _set_dwm_attribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, backdrop)
        default_color = ctypes.c_uint(DWMWA_COLOR_DEFAULT)
        _set_dwm_attribute(hwnd, DWMWA_BORDER_COLOR, default_color)
        _set_dwm_attribute(hwnd, DWMWA_CAPTION_COLOR, default_color)
        _set_dwm_attribute(hwnd, DWMWA_TEXT_COLOR, default_color)
        return changed

    if _windows11_backdrops_available() and material:
        material_values = {
            "mica": DWMSBT_MAINWINDOW,
            "mica_alt": DWMSBT_TABBEDWINDOW,
            "acrylic": DWMSBT_TRANSIENTWINDOW,
        }
        backdrop_type = material_values.get(material, DWMSBT_AUTO)
        backdrop = ctypes.c_int(backdrop_type)
        changed = _set_dwm_attribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            backdrop,
        ) or changed

    return changed


def _widget_hwnd(widget):
    try:
        return int(widget.winfo_id())
    except Exception:
        return None


def _native_class_name(hwnd):
    if hwnd is None or os.name != "nt":
        return ""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        getter = user32.GetClassNameW
        getter.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        getter.restype = ctypes.c_int
        buffer = ctypes.create_unicode_buffer(256)
        length = getter(wintypes.HWND(hwnd), buffer, len(buffer))
        return buffer.value[:length].lower()
    except (AttributeError, OSError, TypeError, ValueError):
        return ""


def _set_window_theme(hwnd, dark, high_contrast):
    if hwnd is None or os.name != "nt" or high_contrast:
        return False

    class_name = _native_class_name(hwnd)
    if class_name not in _NATIVE_CONTROL_CLASSES:
        return False

    try:
        uxtheme = ctypes.WinDLL("uxtheme", use_last_error=True)
        setter = uxtheme.SetWindowTheme
        setter.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        setter.restype = ctypes.HRESULT
        # The public Explorer theme keeps native controls on the Windows
        # visual-style pipeline. Dark/light colors are controlled separately
        # by the application and DWM.
        result = setter(wintypes.HWND(hwnd), "Explorer", None)
        return int(result) == 0
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def _walk_widgets(widget):
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _walk_widgets(child)


def _get_toplevels(root):
    result = [root]
    try:
        stack = root.tk.call("wm", "stackorder", root._w)
        for item in stack:
            try:
                window = root.nametowidget(str(item))
            except Exception:
                continue
            if window not in result:
                result.append(window)
    except Exception:
        pass
    return result


def _material_for_window(window, root):
    if window is root:
        return "mica"

    try:
        title = str(window.title()).strip().lower()
    except Exception:
        title = ""

    if any(
        token in title
        for token in (
            "mudar o feegow",
            "detalhe",
            "erro",
            "aviso",
            "confirma",
        )
    ):
        return "acrylic"

    if any(
        token in title
        for token in (
            "planilha",
            "arquivo",
            "histórico",
            "historico",
        )
    ):
        return "mica_alt"

    return "mica_alt"


def _native_apply_window(window, root, dark, high_contrast):
    hwnd = _widget_hwnd(window)
    if hwnd is None:
        return

    material = _material_for_window(window, root)
    signature = (bool(dark), bool(high_contrast), material)
    if getattr(window, "_sm_windows11_native_signature", None) == signature:
        return

    if high_contrast:
        _set_native_frame(
            hwnd,
            dark=dark,
            high_contrast=True,
            material=None,
        )
        try:
            atualizar_backdrop_tema(window, False)
        except Exception:
            pass
    else:
        try:
            aplicar_backdrop_sistema(
                window,
                material,
                dark=dark,
            )
        except Exception:
            _set_native_frame(
                hwnd,
                dark=dark,
                high_contrast=False,
                material=material,
            )

    window._sm_windows11_native_signature = signature


def _native_apply_controls(root, dark, high_contrast):
    for widget in _walk_widgets(root):
        hwnd = _widget_hwnd(widget)
        class_name = _native_class_name(hwnd)
        if class_name not in _NATIVE_CONTROL_CLASSES:
            continue
        signature = (bool(dark), bool(high_contrast), class_name)
        if getattr(widget, "_sm_windows11_control_signature", None) == signature:
            continue
        _set_window_theme(hwnd, dark, high_contrast)
        widget._sm_windows11_control_signature = signature


def _stage12_refresh(self, force=False):
    if getattr(self, "_closing", False):
        return

    root = getattr(self, "app", None)
    if root is None:
        return

    try:
        dark = str(ctk.get_appearance_mode()).lower() == "dark"
    except Exception:
        dark = False

    high_contrast = _high_contrast_enabled()
    signature = (dark, high_contrast)

    if force or signature != getattr(self, "_windows11_native_theme_signature", None):
        for window in _get_toplevels(root):
            _native_apply_window(window, root, dark, high_contrast)
        _native_apply_controls(root, dark, high_contrast)
        self._windows11_native_theme_signature = signature
    else:
        # New Toplevels can appear without a theme change.
        for window in _get_toplevels(root):
            _native_apply_window(window, root, dark, high_contrast)
        _native_apply_controls(root, dark, high_contrast)


def _stage12_watch(self):
    if getattr(self, "_closing", False):
        return
    try:
        _stage12_refresh(self)
    except Exception:
        pass
    try:
        self._windows11_native_watch_job = self.app.after(
            1200,
            lambda: _stage12_watch(self),
        )
    except Exception:
        self._windows11_native_watch_job = None


def install_ui_windows11_native_29925(App):
    """Camada nativa Windows 11 sobre Tk/CustomTkinter, sem trocar o núcleo funcional."""
    if getattr(App, "_windows11_native_29925_aplicado", False):
        return

    App._windows11_native_29925_aplicado = True
    App._windows11_native_29925_marker = SM_AUTOLAB_WINDOWS_NATIVE_29925

    original_config = App.config_app

    def config_wrapper(self, *args, **kwargs):
        result = original_config(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _stage12_refresh(self, force=True))
            self.app.after(900, lambda: _stage12_watch(self))
        except Exception:
            try:
                _stage12_refresh(self, force=True)
            except Exception:
                pass
        return result

    App.config_app = config_wrapper

    original_theme = App._selecionar_tema

    def theme_wrapper(self, *args, **kwargs):
        result = original_theme(self, *args, **kwargs)
        try:
            self.app.after_idle(lambda: _stage12_refresh(self, force=True))
        except Exception:
            pass
        return result

    App._selecionar_tema = theme_wrapper

    original_close = App._fechar_aplicativo

    def close_wrapper(self, *args, **kwargs):
        job = getattr(self, "_windows11_native_watch_job", None)
        if job is not None:
            try:
                self.app.after_cancel(job)
            except Exception:
                pass
            self._windows11_native_watch_job = None
        return original_close(self, *args, **kwargs)

    App._fechar_aplicativo = close_wrapper


__all__ = [
    "SM_AUTOLAB_WINDOWS_NATIVE_29925",
    "_high_contrast_enabled",
    "_material_for_window",
    "install_ui_windows11_native_29925",
]
