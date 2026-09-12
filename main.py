from splash import run_splash
from interface import App
from patch_v266 import aplicar_patch
from patch_v267 import aplicar_patch_v267


if __name__ == "__main__":
    # Ordem obrigatória: primeiro correções legadas, depois as melhorias
    # do histórico de Arquivos. Isso garante que a segunda camada não seja
    # sobrescrita por código anterior e que todo release carregue os patches.
    aplicar_patch(App)
    aplicar_patch_v267(App)
    run_splash()
    app = App()
    app.app.mainloop()
