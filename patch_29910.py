from __future__ import annotations


PATCH_29910_MARKER = "SM-AUTOLAB-ARQUIVOS-CONTADOR-SELECAO"


def _ensure_selection_state_29910(self):
    """Garante que o conjunto de datas selecionadas sempre exista."""
    selecionadas = getattr(self, "_arquivos_datas_selecionadas", None)
    if not isinstance(selecionadas, set):
        selecionadas = set(selecionadas or ())
        self._arquivos_datas_selecionadas = selecionadas
    if not hasattr(self, "_arquivos_contador_selecao"):
        self._arquivos_contador_selecao = None
    if not hasattr(self, "_arquivos_btn_apagar_selecionados"):
        self._arquivos_btn_apagar_selecionados = None


def _atualizar_contador_selecao_29910(self):
    """Deriva o contador diretamente do estado real da seleção."""
    _ensure_selection_state_29910(self)
    total = len(self._arquivos_datas_selecionadas)

    label = getattr(self, "_arquivos_contador_selecao", None)
    if label is not None:
        try:
            label.configure(text=f"{total} Selecionadas")
        except Exception:
            pass

    btn = getattr(self, "_arquivos_btn_apagar_selecionados", None)
    if btn is not None:
        try:
            btn.configure(state="normal" if total else "disabled")
        except Exception:
            pass


def _embrulhar_metodo_29910(App, nome, wrapper):
    original = getattr(App, nome, None)
    if original is None:
        return
    setattr(App, f"_patch29910_original_{nome.lstrip('_')}", original)
    setattr(App, nome, wrapper)


def _toggle_data_selecionada_29910(self, data):
    original = self._patch29910_original_toggle_data_selecionada
    result = original(data)
    _atualizar_contador_selecao_29910(self)
    return result


def _toggle_modo_selecao_29910(self):
    original = self._patch29910_original_toggle_modo_selecao_arquivos
    result = original()
    _atualizar_contador_selecao_29910(self)
    return result


def _desenhar_calendario_29910(self, *args, **kwargs):
    original = self._patch29910_original_desenhar_calendario_arquivos
    result = original(*args, **kwargs)
    _atualizar_contador_selecao_29910(self)
    return result


def _renderizar_calendario_29910(self, *args, **kwargs):
    original = self._patch29910_original_renderizar_calendario_arquivos
    result = original(*args, **kwargs)
    _atualizar_contador_selecao_29910(self)
    return result


def _mudar_mes_29910(self, *args, **kwargs):
    original = self._patch29910_original_mudar_mes_arquivos
    result = original(*args, **kwargs)
    _atualizar_contador_selecao_29910(self)
    return result


def _limpar_historico_29910(self, *args, **kwargs):
    original = self._patch29910_original_limpar_historico_planilhas
    result = original(*args, **kwargs)
    _atualizar_contador_selecao_29910(self)
    return result


def aplicar_patch_29910(App):
    """Reforça a sincronização do contador da seleção em Arquivos."""
    if getattr(App, "_patch_29910_aplicado", False):
        return
    App._patch_29910_aplicado = True

    App._atualizar_contador_selecao = _atualizar_contador_selecao_29910

    _embrulhar_metodo_29910(
        App,
        "_toggle_data_selecionada",
        _toggle_data_selecionada_29910,
    )
    _embrulhar_metodo_29910(
        App,
        "_toggle_modo_selecao_arquivos",
        _toggle_modo_selecao_29910,
    )
    _embrulhar_metodo_29910(
        App,
        "_desenhar_calendario_arquivos",
        _desenhar_calendario_29910,
    )
    _embrulhar_metodo_29910(
        App,
        "_renderizar_calendario_arquivos",
        _renderizar_calendario_29910,
    )
    _embrulhar_metodo_29910(
        App,
        "_mudar_mes_arquivos",
        _mudar_mes_29910,
    )
    _embrulhar_metodo_29910(
        App,
        "_limpar_historico_planilhas",
        _limpar_historico_29910,
    )
