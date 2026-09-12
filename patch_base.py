"""Camada de compatibilidade da base do aplicativo.

O módulo preserva a implementação legada já validada em ``patch_v266.py`` sem
expor o número histórico no ponto de entrada principal da aplicação.
"""

from patch_v266 import aplicar_patch as aplicar_patch_base

__all__ = ["aplicar_patch_base"]
