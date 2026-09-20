"""Ponto único de compatibilidade histórica do SM AutoLab.

Desde a v2.99.29 a interface funcional é canônica em interface.py.
Este módulo permanece apenas para preservar o ponto de entrada já usado pelo
bootstrap e pelos scripts de build. Nenhum método da classe App é substituído
em runtime e nenhum módulo legado é carregado dinamicamente.
"""

from __future__ import annotations

PATCH_CONSOLIDADO_29929 = "SM-AUTOLAB-PATCH-CONSOLIDADO-29929"


def aplicar_patch_ui(app_class):
    """Marca a camada de compatibilidade como aplicada sem monkeypatching."""
    if getattr(app_class, "_patch_ui_aplicado", False):
        return
    app_class._patch_ui_aplicado = True
    app_class._patch_ui_marker = PATCH_CONSOLIDADO_29929
