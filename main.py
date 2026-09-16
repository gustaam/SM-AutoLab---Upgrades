from datetime import datetime

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


def _historico_minimo_arquivos(self):
    """Retorna a data mais antiga existente no histórico, sem janela fixa."""
    try:
        datas = []
        for item in self._carregar_historico_planilhas():
            try:
                datas.append(datetime.fromisoformat(str(item.get("saved_at", ""))).date())
            except Exception:
                continue
        return min(datas) if datas else datetime.now().date()
    except Exception:
        return datetime.now().date()


def _expandir_janela_arquivos(self):
    """Mantém a compatibilidade com código legado, mas sem limitar Arquivos a 60 dias."""
    try:
        import interface as interface_module

        hoje = datetime.now().date()
        minimo = _historico_minimo_arquivos(self)
        interface_module.ARQUIVOS_DIAS = max((hoje - minimo).days, 0) + 1
    except Exception:
        pass


def _corrigir_historico_ilimitado():
    """Remove em runtime a restrição fixa de 60 dias das rotinas de Arquivos."""
    if getattr(App, "_historico_ilimitado_aplicado", False):
        return

    original_toggle = App._toggle_data_selecionada
    original_click = App._clique_calendario_arquivos
    original_draw = App._desenhar_calendario_arquivos

    def toggle_data(self, data):
        _expandir_janela_arquivos(self)
        try:
            por_dia = self._dados_arquivos_por_dia()
        except Exception:
            por_dia = {}
        if data not in por_dia:
            return
        selecionadas = getattr(self, "_arquivos_datas_selecionadas", None)
        if not isinstance(selecionadas, set):
            selecionadas = set(selecionadas or ())
            self._arquivos_datas_selecionadas = selecionadas
        if data in selecionadas:
            selecionadas.remove(data)
            try:
                if getattr(self, "_arquivos_animacao_data", None) == data:
                    self._cancelar_animacao_selecao()
            except Exception:
                pass
        else:
            selecionadas.add(data)
            try:
                self._animar_selecao_data(data)
            except Exception:
                pass
        try:
            self._atualizar_contador_selecao()
        except Exception:
            pass
        try:
            self._desenhar_calendario_arquivos()
        except Exception:
            original_toggle(self, data)

    def click_calendar(self, event):
        _expandir_janela_arquivos(self)
        canvas = getattr(self, "_arquivos_calendar_canvas", None)
        if canvas is None:
            return
        try:
            item_id = canvas.find_closest(event.x, event.y)[0]
            tags = canvas.gettags(item_id)
        except Exception:
            return

        data = None
        for tag in tags:
            if str(tag).startswith("dia:"):
                try:
                    data = datetime.fromisoformat(str(tag)[4:]).date()
                except Exception:
                    data = None
                break
        if data is None:
            return

        try:
            por_dia = self._dados_arquivos_por_dia()
        except Exception:
            por_dia = {}
        if data not in por_dia:
            return

        if getattr(self, "_arquivos_modo_selecao", False):
            return self._toggle_data_selecionada(data)
        return self._mostrar_planilhas_do_dia(data)

    def draw_calendar(self, *args, **kwargs):
        _expandir_janela_arquivos(self)
        result = original_draw(self, *args, **kwargs)
        canvas = getattr(self, "_arquivos_calendar_canvas", None)
        if canvas is None:
            return result

        try:
            import customtkinter as ctk

            modo_escuro = str(ctk.get_appearance_mode()).lower() == "dark"
            por_dia = self._dados_arquivos_por_dia()
            hoje = datetime.now().date()
            bg_arquivo = "#EAF4FF" if not modo_escuro else "#183B54"
            bg_selecionado = "#D9ECFF" if not modo_escuro else "#244E6B"
            text = self._cor_fluente(self.TEXT)
            accent = self._cor_fluente(self.ACCENT)

            for data in sorted(por_dia):
                if data > hoje:
                    continue
                tag = f"dia:{data.isoformat()}"
                try:
                    itens = canvas.find_withtag(tag)
                except Exception:
                    continue
                if not itens:
                    continue
                selecionada = data in getattr(self, "_arquivos_datas_selecionadas", set())
                for item_id in itens:
                    try:
                        tipo = canvas.type(item_id)
                        if tipo == "rectangle":
                            canvas.itemconfigure(
                                item_id,
                                fill=bg_selecionado if selecionada else bg_arquivo,
                                outline=accent,
                                width=2 if selecionada else 1,
                            )
                        elif tipo == "text":
                            canvas.itemconfigure(item_id, fill=text)
                    except Exception:
                        pass
        except Exception:
            pass
        return result

    App._historico_ilimitado_original_toggle = original_toggle
    App._historico_ilimitado_original_click = original_click
    App._historico_ilimitado_original_draw = original_draw
    App._toggle_data_selecionada = toggle_data
    App._clique_calendario_arquivos = click_calendar
    App._desenhar_calendario_arquivos = draw_calendar
    App._historico_ilimitado_aplicado = True


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
    if not getattr(App, "_historico_ilimitado_aplicado", False):
        raise RuntimeError("A correção de histórico ilimitado não foi aplicada.")


if __name__ == "__main__":
    aplicar_patch_ui(App)
    _corrigir_historico_ilimitado()
    _validar_base_aplicacao()
    run_splash()
    app = App()
    app.app.mainloop()
