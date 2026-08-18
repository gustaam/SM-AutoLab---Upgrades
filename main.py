from splash import run_splash
from interface import App
from patch_v266 import aplicar_patch


if __name__ == "__main__":
    aplicar_patch(App)
    run_splash()
    app = App()
    app.app.mainloop()
