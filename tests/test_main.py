# Testes da inicialização e do runtime principal.

import unittest
from pathlib import Path


class CanonicalRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_main_bootstrap_uses_only_canonical_ui(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        self.assertIn("SM_AUTOLAB_CANONICAL_UI", source)
        self.assertIn("def install_ui(App):", source)
        self.assertIn("App._ui_runtime_mode = \"canonical\"", source)
        self.assertNotIn("from patch import", source)
        self.assertNotIn("bind_all", source)
        self.assertNotIn("install_ui_29912(", source)
        self.assertNotIn("install_ui_fluent_29916(", source)
        self.assertNotIn("install_ui_micro_29918(", source)
        self.assertNotIn("install_ui_windows11_native_29925(", source)
        self.assertLess(len(source.splitlines()), 500)

    def test_interface_nao_mantem_helpers_legados_sem_referencia(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        for marker in (
            "def _localizar_planilha_pendente",
            "def _filtrar_arquivos_60_dias",
            "def _agendar_fechar_aparencia",
            "self.caminho",
            "self.pagina",
            "salvar_checkpoint,",
        ):
            self.assertNotIn(marker, source)

    def test_main_build_keeps_single_bootstrap_entry(self):
        for filename in ("build_windows.bat", ".github/workflows/validate-main.yml", ".github/workflows/release.yml"):
            source = (self.root / filename).read_text(encoding="utf-8")
            self.assertIn(
                "from interface import App; from main import install_ui, _validar_base_aplicacao",
                source,
            )
            self.assertIn("install_ui(App); _validar_base_aplicacao()", source)

    def test_appearance_submenu_owns_hover_events(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("def _configurar_hover_menu", source)
        self.assertIn("command=self._mostrar_menu_aparencia", block)
        self.assertIn('aparencia.bind("<Enter>", self._mostrar_menu_aparencia', block)
        self.assertIn('aparencia.bind("<Leave>", self._agendar_fechar_menus', block)
        self.assertIn("for widget in self._iterar_descendentes_ui(aparencia):", block)
        self.assertIn('widget.bind("<Enter>", self._mostrar_menu_aparencia', block)
        self.assertIn('widget.bind("<Leave>", self._agendar_fechar_menus', block)
        self.assertNotIn('self.app.bind_all("<Button-1>"', source)

    def test_appearance_hover_compatibility_method_is_real(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _garantir_menu_aparencia_aberto_se_hover")
        end = source.index("def _garantir_menu_aparencia_aberto(self)", start)
        block = source[start:end]
        self.assertIn("return self._mostrar_menu_aparencia(event)", block)

    def test_iniciar_footer_does_not_create_a_white_strip(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        actions_start = source.index("actions = ctk.CTkFrame(")
        actions_end = source.index("self.status_label =", actions_start)
        actions_block = source[actions_start:actions_end]
        self.assertIn('fg_color="transparent"', actions_block)
        self.assertIn('height=68', actions_block)
        self.assertIn('actions.pack(fill="x", side="bottom")', actions_block)

    def test_iniciar_has_one_canonical_text_owner(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('text="Iniciar"'), 1)
        self.assertIn('text_color="#FFFFFF"', source)

    def test_interface_importa_escrita_atomica_usada_pelo_salvamento(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("from app import (")
        end = source.index(")", start) + 1
        imports = source[start:end]
        self.assertIn("atomic_write_json,", imports)
        self.assertIn("atomic_write_json(", source)

    def test_dashboard_execucao_tem_metricas_de_tempo_e_progresso(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("self._tempo_decorrido_label", source)
        self.assertIn("self._tempo_estimado_label", source)
        self.assertIn("def _iniciar_metricas_execucao", source)
        self.assertIn("def _atualizar_metricas_execucao", source)
        self.assertIn('text="Execução em andamento"', source)
        self.assertIn('text="Tempo decorrido"', source)
        self.assertIn('text="Tempo estimado restante"', source)
        self.assertIn('self.erro_card = self._stat_card(stats, "!", "Não executados"', source)
        self.assertNotIn('self._execucao_progresso_card = self._stat_card(stats, "▮", "Progresso"', source)

    def test_dashboard_formatador_de_tempo_e_seguro(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('return f"{horas:02d}:{minutos:02d}:{segundos:02d}"', source)
        self.assertIn("restantes = max(0, int(self._execucao_total) - processados)", source)
        self.assertIn('self._tempo_estimado_label.configure(text="—")', source)

    def test_finalizacao_nao_tenta_abrir_aba_removida(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _finalizar(self, resultado):")
        end = source.index("def parar(self):", start)
        block = source[start:end]
        self.assertIn('self._selecionar_aba("Atividade")', block)
        self.assertNotIn('self._selecionar_aba("Não executados"', block)

    def test_validacao_pre_execucao_da_planilha_estah_integrada(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _validar_planilha_antes_execucao")
        end = source.index("def _contar_codigos_mes", start)
        block = source[start:end]
        self.assertIn("rows = {}", block)
        self.assertIn("codigos_por_chave", block)
        self.assertIn("quantidade_valida", block)
        self.assertIn("messagebox.askyesno", block)
        self.assertIn("Linha {numero_linha}: não possui código", block)
        self.assertIn("será executado uma vez por ocorrência", block)
        self.assertIn("if not self._validar_planilha_antes_execucao():", source)
        self.assertGreaterEqual(source.count("if not self._validar_planilha_antes_execucao():"),
                                2)

    def test_atualizador_tem_backup_health_check_e_rollback(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _schedule_replace_after_exit")
        end = source.index("def launch_updater", start)
        block = source[start:end]
        self.assertIn(".sm_autolab_backup", block)
        self.assertIn(".sm_autolab_failed", block)
        self.assertIn("startup.ok", block)
        self.assertIn("rollback", block.lower())
        self.assertIn("Start-Process -FilePath $env:SM_TARGET -PassThru", block)
        self.assertIn('if exist "%SM_HEALTH%" goto success', block)
        self.assertIn('taskkill /PID %SM_PID%', block)
        self.assertIn('move /Y "%SM_BACKUP%" "%SM_TARGET%"', block)
        self.assertIn('restart_env["SM_AUTOLAB_UPDATE_HEALTH"]', block)

    def test_bootstrap_sinaliza_inicio_bem_sucedido_para_atualizacao(self):
        source = (self.root / "main.py").read_text(encoding="utf-8")
        self.assertIn("def _sinalizar_inicializacao_atualizacao_sucesso", source)
        self.assertIn("SM_AUTOLAB_UPDATE_HEALTH", source)
        self.assertIn("os.getpid()", source)
        self.assertIn("_sinalizar_inicializacao_atualizacao_sucesso()", source)
        self.assertLess(len(source.splitlines()), 500)

    def test_dashboard_retorna_ao_layout_base_com_tempos_no_card_de_progresso(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("top = ctk.CTkFrame(main, fg_color=\"transparent\")")
        end = source.index("stats = ctk.CTkFrame(main, fg_color=\"transparent\")", start)
        block = source[start:end]
        self.assertIn('self._tempo_decorrido_label = ctk.CTkLabel(', block)
        self.assertIn('text="Tempo decorrido"', block)
        self.assertIn('text="Tempo estimado restante"', block)
        self.assertIn("time_row = ctk.CTkFrame(progress, fg_color=\"transparent\")", block)
        self.assertNotIn("execution_header = self._card(main)", block)

    def test_dashboard_nao_tem_card_separado_de_progresso(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn('self._execucao_progresso_card = self._stat_card(stats, "▮", "Progresso"', source)
        self.assertIn('self.codigo_card = self._stat_card(stats, "▥", "Código atual"', source)
        self.assertIn('self.erro_card = self._stat_card(stats, "!", "Não executados"', source)

    def test_historico_execucao_migra_e_reconstroi_erros(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _carregar_estado_persistente")
        end = source.index("def _salvar_estado_persistente", start)
        block = source[start:end]
        self.assertIn("self._historico_arquivo_legado", block)
        self.assertIn("registros.extend", block)
        self.assertIn("unicos =", block)
        self.assertIn('execucao.get("codigos_erros", [])', block)
        self.assertIn("self._erros_codigos = erros_reconstruidos[-200:]", block)

    def test_historico_planilha_mesmo_conteudo_em_dias_diferentes_cria_novo_registro(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _registrar_historico_planilha")
        end = source.index("def _preparar_planilha_do_dia", start)
        block = source[start:end]
        self.assertIn("ultimo_data == agora.date()", block)
        self.assertIn("itens.append(entrada)", block)
        self.assertIn("ultimo.get(\"cells\") == cells", block)

    def test_historico_pastas_tem_dimensao_e_layout_responsivos(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_pasta_historico")
        end = source.index("def _abrir_detalhe_historico", start)
        block = source[start:end]
        self.assertIn("width=132", block)
        self.assertIn("height=102", block)
        self.assertIn("colunas = max(3, min(6", block)
        self.assertIn("wraplength=116", block)
    def test_interface_remove_titulo_historico_de_execucoes(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn('text="Histórico de execuções"', source)
        self.assertNotIn('text="histórico de execuções"', source)

    def test_area_de_historico_tem_altura_adaptavel(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _ajustar_altura_acompanhamento", source)
        self.assertIn("altura = max(300, min(440, janela_h - 260))", source)
        self.assertIn('self.app.bind("<Configure>", self._ajustar_altura_acompanhamento, add="+")', source)

    def test_cards_de_estatisticas_usam_cores_e_icones_por_categoria(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _stat_card")
        end = source.index("@staticmethod", start)
        block = source[start:end]
        self.assertIn('"Executados": {', block)
        self.assertIn('"Não executados": {', block)
        self.assertIn('"Código atual": {', block)
        self.assertIn('"card": ("#EEF9F1", "#1E3325")', block)
        self.assertIn('"card": ("#FFF1F2", "#3A2528")', block)
        self.assertIn('"card": ("#EEF6FF", "#1C2D3D")', block)
        self.assertIn('"icon": ("#27AE60", "#2FAE63")', block)
        self.assertIn('"icon": ("#E53935", "#F15B5B")', block)
        self.assertIn('"icon": ("#1976D2", "#3F9BEF")', block)
        self.assertIn('self.codigo_card = self._stat_card(stats, "▥", "Código atual"', source)
        self.assertIn('icon_sizes = {"✓": 21, "!": 21, "▥": 21, "›": 21}', block)

    def test_planilha_sincroniza_edicao_antes_de_salvar(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _planilha_commit_edit")
        end = source.index("def _planilha_fechar_edicao", start)
        block = source[start:end]
        self.assertIn("entry.get() if save else old", block)
        self.assertIn("tree.item(iid, values=vals)", block)
        self.assertIn('self._planilha_data[key] = new', block)
        self.assertIn("self._planilha_marcar_alteracao()", block)
        self.assertIn("self._planilha_edit_context = None", block)

    def test_menu_contexto_da_planilha_abre_e_oferece_acoes_de_edicao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_menu_contexto_planilha")
        end = source.index("def _atualizar_menu_contexto_planilha", start)
        block = source[start:end]
        for label in ("Editar", "Desfazer", "Refazer", "Cortar", "Copiar", "Colar", "Excluir", "Selecionar tudo"):
            self.assertIn(f'label="{label}"', block)
        self.assertIn('tree.bind("<Button-3>", _planilha_botao_direito)', source)
        self.assertIn("self._planilha_context_menu.tk_popup(event.x_root, event.y_root)", source)

    def test_ajustes_do_feegow_e_janela_normal_por_padrao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn("Mudar o Feegow", source)
        self.assertNotIn("mudar o feegow", source)
        self.assertGreaterEqual(source.count("Ajustes do Feegow"), 3)
        self.assertNotIn('self.app.state("zoomed")', source)

    def test_interface_importa_leitura_json_usada_pelos_historicos_e_planilha(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("from app import (")
        end = source.index(")", start) + 1
        imports = source[start:end]
        self.assertIn("atomic_write_json,", imports)
        self.assertIn("read_json_with_backup,", imports)
        self.assertIn("read_json_with_backup(", source)

    def test_historicos_nao_sao_excluidos_pelo_limite_de_60_dias(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _carregar_estado_persistente")
        end = source.index("def _salvar_estado_persistente", start)
        load_block = source[start:end]
        self.assertIn("self._historico_execucoes = list(unicos.values())", load_block)
        self.assertNotIn("_filtrar_historico_execucoes_60_dias(list(unicos.values()))", load_block)

        start = source.index("def _salvar_estado_persistente")
        end = source.index("def _criar_botao_erro", start)
        save_block = source[start:end]
        self.assertIn('"historico_execucoes": self._historico_execucoes', save_block)
        self.assertNotIn("_filtrar_historico_execucoes_60_dias(self._historico_execucoes)", save_block)

        start = source.index("def _carregar_historico_planilhas")
        end = source.index("def _registrar_historico_planilha", start)
        sheet_block = source[start:end]
        self.assertIn("validos = [item for item in itens if isinstance(item, dict)]", sheet_block)
        self.assertNotIn("_salvar_historico_planilhas(filtrados)", sheet_block)

    def test_historico_usa_widget_de_icone_correto_ao_criar_pasta(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_pasta_historico")
        end = source.index("def _abrir_detalhe_historico", start)
        block = source[start:end]
        self.assertIn('icone = "📁"', block)
        self.assertIn("icone_widget = ctk.CTkLabel(", block)
        self.assertIn("for w in (tile,icone_widget):", block)
        self.assertNotIn("for w in (tile,icone):", block)

    def test_tempo_estimado_usa_mesma_fonte_do_tempo_decorrido(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("elapsed_box = ctk.CTkFrame(")
        end = source.index("stats = ctk.CTkFrame(main", start)
        block = source[start:end]
        self.assertIn('text="Tempo decorrido"', block)
        self.assertIn('text="Tempo estimado restante"', block)
        self.assertIn('font=("Segoe UI", 8, "bold")', block)

    def test_planilha_salva_e_recarrega_dados_pelo_mesmo_caminho(self):
        import tempfile
        import interface

        with tempfile.TemporaryDirectory() as temp_dir:
            obj = object.__new__(interface.App)
            obj._planilha_arquivo = Path(temp_dir) / "planilha_interna.json"
            cells = {
                "0,0": "1",
                "0,1": "B06A91P89YOB",
                "0,2": "Hemograma",
            }
            obj._planilha_data = dict(cells)
            obj._salvar_planilha_interna_data()
            self.assertEqual(obj._carregar_planilha_interna(), cells)

    def test_planilha_botao_direito_esta_ligado_ao_canvas_interno(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('tree.bind("<Button-3>", _planilha_botao_direito)', source)
        self.assertIn('tree._canvas.bind("<Button-3>", _planilha_botao_direito, add="+")', source)
        self.assertIn("def _criar_menu_contexto_planilha", source)
        for label in ("Editar", "Copiar", "Colar", "Excluir", "Selecionar tudo"):
            self.assertIn(f'label="{label}"', source[source.index("def _criar_menu_contexto_planilha"):])

    def test_icones_dos_cards_usam_container_circular_fixo(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _stat_card")
        end = source.index("@staticmethod", start)
        block = source[start:end]
        self.assertIn("icon_holder = ctk.CTkLabel(", block)
        self.assertIn("width=icon_holder_size,", block)
        self.assertIn("height=icon_holder_size,", block)
        self.assertIn("icon_holder_size = 44", block)
        self.assertIn("corner_radius=icon_holder_size // 2", block)
        self.assertIn('fg_color=palette["icon"]', block)
        self.assertIn('text_color="#FFFFFF"', block)
    def test_cartoes_do_historico_usam_data_e_tamanho_fixos(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _formatar_data_historico")
        end = source.index("def _abrir_detalhe_historico", start)
        block = source[start:end]
        self.assertIn('strftime("%d/%m/%Y")', block)
        self.assertIn("tile_width = 144", block)
        self.assertIn("tile_height = 116", block)
        self.assertIn("grid_propagate(False)", block)
        self.assertNotIn('sticky="nsew"', block)
        self.assertNotIn('text=titulo[:24]', block)
        self.assertNotIn('text="Concluída"', block)
        self.assertIn("wraplength=tile_width - 20", block)

    def test_data_do_historico_e_formatada_no_padrao_brasileiro(self):
        import interface
        obj = object.__new__(interface.App)
        self.assertEqual(
            obj._formatar_data_historico("2026-09-21 21:47:26"),
            "21/09/2026",
        )

    def test_tooltips_e_hover_dos_cards_estao_na_interface_canonica(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("class _SMAutoLabTooltip:", source)
        self.assertIn("def _ui_install_button_tooltips", source)
        self.assertIn("_ui_install_button_tooltips()", source)
        self.assertIn("def _ui_bind_card_hover", source)
        self.assertIn('"Executados": "Mostra a quantidade de códigos executados com sucesso."', source)
        self.assertIn('"Não executados": "Mostra a quantidade de códigos que apresentaram erro durante a execução."', source)
        self.assertIn('"Código atual": "Mostra o código que está sendo processado no momento."', source)
        self.assertIn("_ui_bind_card_hover(card, accent)", source)
        self.assertNotIn("install_ui_micro_29918", source)
        self.assertNotIn("bind_all", source)

    def test_stat_cards_mantem_feedback_visual_e_tooltip(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _stat_card")
        end = source.index("def _set_stat", start)
        block = source[start:end]
        self.assertIn("_ui_bind_card_hover(card, accent)", block)
        self.assertIn("_SMAutoLabTooltip(", block)
        self.assertIn("card_tooltips =", block)

    def test_tooltip_fecha_no_clique_foco_ou_destruicao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("class _SMAutoLabTooltip:")
        end = source.index("def _ui_tooltip_text", start)
        block = source[start:end]
        self.assertIn('child.bind("<ButtonPress>", self._on_press, add="+")', block)
        self.assertIn('child.bind("<FocusOut>", self._on_focus_out, add="+")', block)
        self.assertIn("self._destroy_window()", block)
        self.assertIn("def _destroy_window(self):", block)
        self.assertNotIn('self._window.withdraw()', block)

    def test_botao_abrir_continua_com_tooltip_canonico(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("self.botao_planilha = ctk.CTkButton(")
        end = source.index("self.botao_planilha.pack", start)
        block = source[start:end]
        self.assertIn('text="Abrir"', block)
        self.assertIn("command=self.abrir_planilha", block)
        self.assertIn('"abrir": "Abre a planilha interna."', source)

    def test_legacy_patch_module_is_absent(self):
        self.assertFalse((self.root / "patch.py").exists())

    def test_interface_has_no_global_mouse_binding(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn("bind_all", source)
        self.assertNotIn('bind("<Button-1>", on_click', source)


if __name__ == "__main__":
    unittest.main()
