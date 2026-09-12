from splash import run_splash
from interface import App
from patch_v266 import aplicar_patch
from patch_v267 import aplicar_patch_v267


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
    # Ordem obrigatória: primeiro correções legadas, depois as melhorias
    # do histórico de Arquivos. Isso garante que a segunda camada não seja
    # sobrescrita por código anterior e que todo release carregue os patches.
    aplicar_patch(App)
    aplicar_patch_v267(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
