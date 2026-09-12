from splash import run_splash
from interface import App
from patch_base import aplicar_patch_base
from patch_arquivos import aplicar_patch_arquivos


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


if __name__ == "__main__":
    # Ordem fixa da inicializacao: camada base, depois Arquivos/calendario.
    # Os nomes dos modulos sao neutros para que a numeracao da versao nunca
    # determine quais funcionalidades entram em um release.
    aplicar_patch_base(App)
    aplicar_patch_arquivos(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
