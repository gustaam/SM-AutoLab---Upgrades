from __future__ import annotations

from patch_base import aplicar_patch_base
from patch_arquivos import aplicar_patch_arquivos
from patch_ajustes import aplicar_patch_ajustes
from patch_297 import aplicar_patch_297
from patch_298 import aplicar_patch_298
from patch_299 import aplicar_patch_299
from patch_2991 import aplicar_patch_2991
from patch_29910 import aplicar_patch_29910


def _iter_descendants(widget):
    if widget is None:
        return
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        children = ()
    for child in children:
        yield from _iter_descendants(child)


def _remover_instrucao_ctrl_clique(self):
    """Remove definitivamente a instrução visual de seleção por Ctrl+clique."""
    win = getattr(self, "_planilha_historico_window", None)
    if win is None:
        return
    for widget in _iter_descendants(win):
        try:
            texto = str(widget.cget("text"))
        except Exception:
            continue
        if "Ctrl + clique para selecionar várias datas" in texto:
            try:
                widget.destroy()
            except Exception:
                pass


def _abrir_historico_sem_instrucao(self, *args, **kwargs):
    result = self._patch_ui_original_abrir_historico(*args, **kwargs)
    try:
        self.app.after_idle(lambda: _remover_instrucao_ctrl_clique(self))
    except Exception:
        _remover_instrucao_ctrl_clique(self)
    return result


def aplicar_patch_ui(App):
    """Entrada única para todas as correções versionadas da interface."""
    if getattr(App, "_patch_ui_aplicado", False):
        return

    aplicar_patch_base(App)
    aplicar_patch_arquivos(App)
    aplicar_patch_ajustes(App)
    aplicar_patch_297(App)
    aplicar_patch_298(App)
    aplicar_patch_299(App)
    aplicar_patch_2991(App)
    aplicar_patch_29910(App)

    App._patch_ui_original_abrir_historico = App._abrir_historico_planilha
    App._abrir_historico_planilha = _abrir_historico_sem_instrucao
    App._patch_ui_aplicado = True
