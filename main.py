import sys


# Modo auxiliar do atualizador integrado: o próprio executável pode iniciar
# uma cópia temporária como processo auxiliar para substituir a versão
# instalada depois que ela for encerrada.
if "--sm-autolab-update-helper" in sys.argv:
    from atualizacao import _cli
    raise SystemExit(_cli())

from splash import run_splash
from interface import App
from patch_base import aplicar_patch_base
from patch_arquivos import aplicar_patch_arquivos
from patch_ajustes import aplicar_patch_ajustes


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
    # Ordem fixa: base, Arquivos/calendario e ajustes finais.
    # A main continua sendo a fonte de verdade para qualquer release.
    aplicar_patch_base(App)
    aplicar_patch_arquivos(App)
    aplicar_patch_ajustes(App)
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
