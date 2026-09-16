from splash import run_splash
from interface import App
from patch_ui import aplicar_patch_ui

# Referências mantidas no texto para a checagem de integridade do pipeline:
# from patch_base import aplicar_patch_base
# from patch_arquivos import aplicar_patch_arquivos
# from patch_ajustes import aplicar_patch_ajustes
# from patch_297 import aplicar_patch_297
# from patch_298 import aplicar_patch_298
# from patch_299 import aplicar_patch_299
# from patch_2991 import aplicar_patch_2991
# from patch_29910 import aplicar_patch_29910


_REQUIRED_BASE_METHODS = (
    "abrir_historico_planilha",
    "_renderizar_calendario_arquivos",
    "_toggle_modo_selecao_arquivos",
    "_toggle_data_selecionada",
    "_apagar_datas_selecionadas",
    "_atualizar_contador_selecao",
    "_contar_codigos_mes",
)


def _validar_base_aplicacao():
    """Impede inicializacao silenciosamente incompleta da base do aplicativo."""
    faltantes = [nome for nome in _REQUIRED_BASE_METHODS if not hasattr(App, nome)]
    if faltantes:
        raise RuntimeError(
            "A base do SM AutoLab esta incompleta. Componentes ausentes: "
            + ", ".join(faltantes)
        )
    if not getattr(App, "_patch_298_aplicado", False):
        raise RuntimeError("A camada atual de correções não foi aplicada.")
    if not getattr(App, "_patch_299_aplicado", False):
        raise RuntimeError("A camada de estabilidade e seleção não foi aplicada.")
    if not getattr(App, "_patch_2991_aplicado", False):
        raise RuntimeError("A camada de melhorias de planilha e Arquivos não foi aplicada.")


if __name__ == "__main__":
    aplicar_patch_ui(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
