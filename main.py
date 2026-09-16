from splash import run_splash
from interface import App
from patch import aplicar_patch_ui

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
    if not getattr(App, "_patch_ui_aplicado", False):
        raise RuntimeError("A camada consolidada de correções não foi aplicada.")


if __name__ == "__main__":
    aplicar_patch_ui(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
