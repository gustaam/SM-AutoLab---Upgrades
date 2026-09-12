"""Camada das funcionalidades de Arquivos e calendario.

O codigo funcional permanece na camada de compatibilidade existente, mas o
ponto de entrada atual usa um nome neutro para nao vincular a funcionalidade a
uma numeracao historica de versao.
"""

from patch_v267 import aplicar_patch_v267 as aplicar_patch_arquivos

__all__ = ["aplicar_patch_arquivos"]
