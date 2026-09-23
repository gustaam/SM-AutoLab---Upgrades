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
        self.assertIn("self._ativar_clique_fora_menus()", block)
        self.assertIn("def _pointer_em_area_dos_menus", source)
        self.assertIn("def _clique_fora_menus", source)
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
        self.assertIn('INICIAR_LABEL = "Iniciar"', source)
        self.assertEqual(source.count("text=self.INICIAR_LABEL"), 2)
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
        self.assertIn('start "" /b "%SM_TARGET%"', block)
        self.assertIn('if exist "%SM_HEALTH%" goto success', block)
        self.assertIn('taskkill /PID %SM_PID%', block)
        self.assertIn('move /Y "%SM_BACKUP%" "%SM_TARGET%"', block)
        self.assertIn('>nul choice /n /t 1 /d y', block)
        self.assertNotIn("powershell", block.lower())
        self.assertNotIn("timeout /t 1 /nobreak", block)
        self.assertIn('restart_env["SM_AUTOLAB_UPDATE_HEALTH"]', block)

    def test_atualizador_exibe_barra_de_download(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def download_file(")
        end = source.index("def _escape_cmd_path", start)
        block = source[start:end]
        self.assertIn("Content-Length", block)
        self.assertIn("progress_callback", block)
        self.assertIn("progress_callback(downloaded_bytes, total_bytes)", block)
        self.assertIn("def _mostrar_progresso_atualizacao", source)
        self.assertIn("ctk.CTkProgressBar(", source)
        self.assertIn("Baixando atualização v", source)
        self.assertIn("def _atualizacao_atualizar_progresso", source)

    def test_restore_desabilita_transicoes_dwm_por_janela(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("DWMWA_TRANSITIONS_FORCEDISABLED = 3", source)
        self.assertIn("def desabilitar_transicoes_dwm", source)
        self.assertIn("ctypes.c_int(1)", source[source.index("def desabilitar_transicoes_dwm"):source.index("def _windows11_available")])
        self.assertIn("desabilitar_transicoes_dwm(self.app)", source)
        self.assertIn('self.app.bind("<Unmap>", self._preparar_minimizacao, add="+")', source)
        start = source.index("def _agendar_estabilizacao_apos_retomada")
        end = source.index("def config_app", start)
        block = source[start:end]
        self.assertIn("desabilitar_transicoes_dwm(self.app)", block)
        self.assertIn("def _estabilizar_apos_retomada", block)
        self.assertNotIn("_redraw_window_now", source)
        self.assertNotIn("WM_SETREDRAW = 0x000B", source)

    def test_codigo_atual_usa_fonte_menor_sem_negrito(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _stat_card")
        end = source.index("def _set_stat", start)
        block = source[start:end]
        self.assertIn('value_font = ("Segoe UI", 17) if str(title) == "Código atual" else ("Segoe UI", 19, "bold")', block)
        self.assertIn("font=value_font", block)

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

    def test_historico_de_erros_tem_arquivo_separado(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('historico_erros.json', source)
        start = source.index("def _salvar_estado_persistente")
        end = source.index("def _salvar_erros_persistentes", start)
        block = source[start:end]
        self.assertNotIn('self._erros_codigos[-200:]', block)
        erros_start = end
        erros_end = source.index("def _criar_botao_erro", erros_start)
        erros_block = source[erros_start:erros_end]
        self.assertIn('self._erros_codigos[-200:]', erros_block)
        self.assertIn("self._salvar_erros_persistentes()", source)

    def test_pastas_do_historico_usam_largura_da_janela_no_primeiro_layout(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_pasta_historico")
        end = source.index("def _atualizar_visual_selecao_historico", start)
        block = source[start:end]
        self.assertIn("largura_parent = int(parent.winfo_width())", block)
        self.assertIn("largura_app = int(self.app.winfo_width())", block)
        self.assertIn("largura_app - 80", block)
        self.assertIn("tile.grid(row=row, column=col, padx=1, pady=1)", block)

    def test_icones_de_estatistica_problematicos_sao_vetoriais(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_imagem_icone_estatistica")
        end = source.index("def _render_stat_icon", start)
        block = source[start:end]
        self.assertIn('if str(icon) == "✓":', block)
        self.assertIn('elif str(icon) == "▥":', block)
        self.assertIn("draw.line(", block)
        self.assertIn("draw.rounded_rectangle(", block)

    def test_janela_principal_nao_usa_backdrop_mica(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def config_app")
        end = source.index("def _reposicionar_menus", start)
        block = source[start:end]
        self.assertNotIn('aplicar_backdrop_sistema(self.app, "mica"', block)

    def test_restore_da_janela_tem_handler_sem_relayout(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('self.app.bind("<Map>", self._agendar_estabilizacao_apos_retomada', source)
        self.assertIn('self.app.bind("<Unmap>", self._preparar_minimizacao, add="+")', source)
        self.assertIn("def _estabilizar_apos_retomada", source)
        start = source.index("def _agendar_estabilizacao_apos_retomada")
        end = source.index("def config_app", start)
        block = source[start:end]
        self.assertIn("desabilitar_transicoes_dwm(self.app)", block)
        self.assertNotIn("self.app.update_idletasks()", block)
        self.assertNotIn("_redraw_window_now(self.app)", block)

    def test_pronto_reinicia_pulso_verde(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _aplicar_status")
        end = source.index("def atualizar_progresso", start)
        block = source[start:end]
        self.assertIn("self._iniciar_pisca_status()", block)
        self.assertIn('self._status_blink_fast = False', block)

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
        self.assertIn("tile_width = 112", block)
        self.assertIn("tile_height = 84", block)
        self.assertIn("colunas = max(1, min(8", block)
        self.assertIn("wraplength=tile_width - 6", block)
        self.assertNotIn('text=titulo[:24]', block)
        self.assertNotIn("sticky=\"nsew\"", block)
        self.assertIn("def _formatar_data_historico", source)
        self.assertIn('strftime("%d/%m/%Y")', source)
    def test_interface_remove_titulo_historico_de_execucoes(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn('text="Histórico de execuções"', source)
        self.assertNotIn('text="histórico de execuções"', source)

    def test_area_de_historico_tem_altura_adaptavel(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _ajustar_altura_acompanhamento", source)
        self.assertIn("altura = max(300, min(440, janela_h - 260))", source)
        self.assertIn('self.app.bind("<Configure>", self._ajustar_altura_acompanhamento, add="+")', source)

    def test_icones_dos_cards_sao_atualizados_ao_mudar_o_tema(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _atualizar_icones_cards_estatistica", source)
        start = source.index("def _atualizar_icones_cards_estatistica")
        end = source.index("@staticmethod", start)
        block = source[start:end]
        self.assertIn("self._render_stat_icon(card)", block)
        self.assertIn("def _render_stat_icon", source)
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
        self.assertIn("self._historico_execucoes = [", load_block)
        self.assertIn("if self._historico_execucao_tem_erros(item)", load_block)
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
        self.assertIn("icon = ctk.CTkLabel(", block)
        self.assertIn("widgets = (tile, icon, date_label, time_label, error_label)", block)
        self.assertIn('widget.bind("<Button-1>", clicar)', block)
        self.assertNotIn('widget.bind("<Double-1>"', block)

    def test_tempo_estimado_usa_mesma_fonte_do_tempo_decorrido(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("elapsed_box = ctk.CTkFrame(")
        end = source.index("stats = ctk.CTkFrame(main", start)
        block = source[start:end]
        self.assertIn('text="Tempo decorrido"', block)
        self.assertIn('text="Tempo estimado restante"', block)
        self.assertIn('font=("Segoe UI", 8, "bold")', block)

    def test_planilha_recupera_ultima_apenas_quando_nao_processada(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _planilha_fingerprint", source)
        self.assertIn("def _planilha_foi_processada", source)
        self.assertIn('status != "concluída"', source)
        self.assertIn('"A última planilha salva ainda não foi processada.', source)

    def test_planilha_processada_abre_nova_vazia_e_apaga_rascunho(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def abrir_planilha(self, dados_iniciais=None):")
        end = source.index("def _", start + 10)
        block = source[start:end]
        self.assertIn("if self._planilha_foi_processada(ultima):", block)
        self.assertIn("self._planilha_apagar_rascunho()", block)
        self.assertIn("self._planilha_data = {}", block)

    def test_historico_de_erros_renderiza_pasta_apenas_com_erros(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _restaurar_historico_na_tela")
        end = source.index("def _id_historico_execucao", start)
        block = source[start:end]
        self.assertIn("self._historico_execucao_tem_erros(item)", block)
        self.assertIn('Nenhuma execução com erros registrada ainda.', block)

    def test_historico_de_erros_considera_erro_geral(self):
        import interface
        self.assertTrue(interface.App._historico_execucao_tem_erros({"erros": 1}))
        self.assertTrue(interface.App._historico_execucao_tem_erros({"status": "Erro geral", "erros": 0}))
        self.assertFalse(interface.App._historico_execucao_tem_erros({"status": "Concluída", "erros": 0}))

    def test_planilha_processada_persiste_e_impede_reabertura_da_mesma_revisao(self):
        import interface
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            obj = object.__new__(interface.App)
            obj._planilha_arquivo = Path(temp_dir) / "planilha_interna.json"
            obj._planilha_data = {"0,0": "1", "0,1": "ABC", "0,2": "Item"}
            obj._salvar_planilha_interna_data()

            self.assertFalse(obj._planilha_foi_processada(obj._planilha_data))
            obj._marcar_planilha_interna_processada(obj._planilha_data)
            self.assertTrue(obj._planilha_foi_processada(obj._planilha_data))

            data = interface.read_json_with_backup(obj._planilha_arquivo, {})
            self.assertEqual(
                data.get("processed_fingerprint"),
                obj._planilha_fingerprint(obj._planilha_data),
            )

    def test_planilha_nova_revisao_limpa_marcador_de_processamento(self):
        import interface
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            obj = object.__new__(interface.App)
            obj._planilha_arquivo = Path(temp_dir) / "planilha_interna.json"
            obj._planilha_data = {"0,0": "1", "0,1": "ABC"}
            obj._salvar_planilha_interna_data()
            obj._marcar_planilha_interna_processada(obj._planilha_data)
            obj._planilha_data = {"0,0": "2", "0,1": "XYZ"}
            obj._salvar_planilha_interna_data()

            data = interface.read_json_with_backup(obj._planilha_arquivo, {})
            self.assertEqual(data.get("processed_fingerprint"), "")
            self.assertFalse(obj._planilha_foi_processada(obj._planilha_data))

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
        self.assertIn("icon_holder = Canvas(", block)
        self.assertIn("width=icon_holder_size,", block)
        self.assertIn("height=icon_holder_size,", block)
        self.assertIn("icon_holder_size = 44", block)
        self.assertIn("card._sm_stat_icon_data = (", block)
        self.assertIn("self._render_stat_icon(card)", block)
    def test_cartoes_do_historico_usam_data_e_tamanho_fixos(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _formatar_data_historico")
        end = source.index("def _abrir_detalhe_historico", start)
        block = source[start:end]
        self.assertIn('strftime("%d/%m/%Y")', block)
        self.assertIn("tile_width = 112", block)
        self.assertIn("tile_height = 84", block)
        self.assertIn("grid_propagate(False)", block)
        self.assertNotIn('sticky="nsew"', block)
        self.assertNotIn('text=titulo[:24]', block)
        self.assertNotIn('text="Concluída"', block)
        self.assertIn("wraplength=tile_width - 6", block)

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
        self.assertIn("self._rendered_message = None", block)
        self.assertIn("self._rendered_message != self.message", block)
        self.assertIn("self._destroy_window()", block)
        self.assertIn("def _destroy_window(self):", block)
        self.assertNotIn('child.bind("<Motion>"', block)
        self.assertNotIn('self._window.attributes("-topmost", True)', block)
        self.assertNotIn("original_configure = cls.configure", block)

    def test_tooltips_canonicos_cobrem_botoes_e_acoes_da_interface(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        for key in ("atividade", "histórico", "↶", "↷", "‹", "›"):
            self.assertIn(f'"{key}":', source)

    def test_reexecucao_nao_cria_novo_registro_no_historico(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _finalizar_historico_execucao")
        end = source.index("def _registrar_falha_historico", start)
        block = source[start:end]

        self.assertIn('eh_reexecucao = bool(self._execucao_atual.get("reexecucao_de"))', block)
        self.assertIn(
            'if not eh_reexecucao and self._historico_execucao_tem_erros(self._execucao_atual):',
            block,
        )

        start = source.index("def _registrar_falha_historico")
        end = source.index("def _restaurar_historico_na_tela", start)
        fail_block = source[start:end]
        self.assertIn('if not self._execucao_atual.get("reexecucao_de"):', fail_block)

    def test_reexecucao_de_erros_fica_registrada_e_nao_reaparece_na_mesma_execucao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _abrir_detalhe_historico")
        end = source.index("def _preencher_detalhe_pasta", start)
        open_block = source[start:end]
        detail_start = source.index("def _preencher_detalhe_pasta")
        detail_end = source.index("def _limpar_historico", detail_start)
        detail_block = source[detail_start:detail_end]

        self.assertIn("codigos_erros_reexecutados", detail_block)
        self.assertIn("codigos_reexecutaveis", detail_block)
        self.assertIn("self._iniciar_automacao_interna(", detail_block)
        self.assertIn("ignorar_checkpoint=True", detail_block)

        self.assertIn('getattr(self, "_origem_reexecucao", "planilha_interna")', source)
        self.assertIn('"reexecucao_de"', source)

    def test_botoes_de_exclusao_mostram_contagem_da_selecao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")

        start = source.index("def _atualizar_botao_apagar_historico")
        end = source.index("def _limpar_selecao_historico", start)
        history_block = source[start:end]
        self.assertIn('f"Apagar {quantidade} selecionado"', history_block)
        self.assertIn('f"Apagar {quantidade} selecionados"', history_block)
        self.assertIn("btn.configure(text=texto)", history_block)

        start = source.index("def _atualizar_botao_apagar_datas_arquivos")
        end = source.index("def _apagar_datas_arquivos_selecionadas", start)
        date_block = source[start:end]
        self.assertIn('f"Apagar {quantidade} selecionada"', date_block)
        self.assertIn('f"Apagar {quantidade} selecionadas"', date_block)
        self.assertIn("btn.configure(text=texto)", date_block)

    def test_historico_apagar_selecionados_tem_visibilidade_condicional(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('text="Apagar selecionados"', source)
        self.assertIn("def _atualizar_botao_apagar_historico", source)
        self.assertIn("btn.pack_forget()", source)
        self.assertIn("def _apagar_historico_selecionados", source)
        self.assertIn('self._historico_selecionados', source)

    def test_planilha_nao_usa_ctrl_clique_para_selecao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _planilha_clicar_celula")
        end = source.index("def _planilha_arrastar_selecao", start)
        block = source[start:end]
        self.assertNotIn("0x0004", block)
        self.assertNotIn("ctrl_multiselect", block)
        self.assertNotIn("botao_planilha_apagar_selecionados", source)
        self.assertNotIn("def _planilha_apagar_selecionados", source)

    def test_historico_erros_aceita_ctrl_clique_e_apagar_selecionados(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _preencher_detalhe_pasta")
        end = source.index("def _limpar_historico", start)
        block = source[start:end]
        self.assertIn('getattr(event, "state", 0)', block)
        self.assertIn("0x0004", block)
        self.assertIn("selecionados = set()", block)
        self.assertIn('text="Apagar selecionados"', block)
        self.assertIn("apagar_selecionados_erros", block)

    def test_historico_pastas_ficam_mais_quadradas(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_pasta_historico")
        end = source.index("def _atualizar_visual_selecao_historico", start)
        block = source[start:end]
        self.assertIn("tile_width = 112", block)
        self.assertIn("tile_height = 84", block)
        self.assertIn("icon.pack(pady=(2, 0))", block)
        self.assertIn("error_label.pack(fill=\"x\", padx=2, pady=(2, 0))", block)
        self.assertIn("minsize=0", block)
        self.assertIn("tile.grid(row=row, column=col, padx=1, pady=1)", block)

    def test_menus_configuracoes_trocam_ordem_aparencia_atualizacoes(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _garantir_menu_aparencia_aberto_se_hover", start)
        block = source[start:end]
        self.assertLess(block.index('text="Aparência  ›"'), block.index('text="Visualização  ›"'))
        self.assertLess(block.index('text="Visualização  ›"'), block.index('text="Ajustes do Feegow"'))
        self.assertLess(block.index('text="Ajustes do Feegow"'), block.index('text="Verificar atualizações"'))

    def test_labels_de_aparencia_e_visualizacao(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('text="Aparência  ›"', source)
        self.assertNotIn('text="Aparências  ›"', source)
        self.assertIn('text="Visualização  ›"', source)
        self.assertIn('"light": "Clara"', source)
        self.assertIn('"dark": "Escura"', source)

    def test_visualizacao_compacta_posiciona_configuracoes_no_cabecalho(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _configurar_dashboard_compacto")
        end = source.index("def _abrir_historico_compacto", start)
        block = source[start:end]
        self.assertIn('header,\n            text="Configurações"', block)
        self.assertIn('self.botao_configuracoes.pack(side="right"', block)
        self.assertIn('("Abrir", self.abrir_planilha),', block)
        self.assertIn('("Arquivos", self.abrir_historico_planilha),', block)
        self.assertIn('("Histórico", self._abrir_historico_compacto),', block)
        self.assertIn('text="Parar"', block)
        self.assertIn("text=self.INICIAR_LABEL", block)
        self.assertIn('bottom_row.pack(anchor="center"', block)
        self.assertIn('largura, altura = 500, 280', block)
        self.assertIn('self.progresso = ctk.CTkProgressBar(', block)
        self.assertIn('height=10,', block)
        self.assertIn('fg_color=self.BORDER', block)
        self.assertIn('progress_color=self.ACCENT', block)
        self.assertIn("actions.pack(fill="x", padx=18, pady=(27, 10))", block)
        self.assertIn("menu_y = 58", source)

    def test_atualizacao_usa_mesma_versao_da_interface(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def find_update")
        end = source.index("def download_file", start)
        block = source[start:end]
        self.assertIn("current_override: str | None = None", block)
        self.assertIn("current = str(current_override or \"\").strip()", block)
        self.assertIn("find_update(current_override=APP_VERSION)", source)

    def test_reinicio_usa_nova_instancia_independente(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _reiniciar_aplicativo")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("_prepare_independent_restart_environment()", block)
        self.assertIn("subprocess.Popen(", block)
        self.assertIn("sys.argv[1:]", block)
        self.assertIn("CREATE_NEW_PROCESS_GROUP", block)
        self.assertNotIn("tasklist /FI", block)

    def test_atualizador_sinaliza_inicio_saudavel_e_reseta_ambiente(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn('set "PYINSTALLER_RESET_ENVIRONMENT=1"', source)
        self.assertIn('set "SM_AUTOLAB_HEALTH_FILE=%SM_HEALTH%"', source)
        self.assertIn("def _sinalizar_inicio_atualizacao", source)
        self.assertIn("SM_AUTOLAB_HEALTH_FILE", source)

    def test_troca_visualizacao_oferece_reinicio_agora_ou_depois(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _selecionar_visualizacao")
        end = source.index("def _mostrar_menu_aparencia", start)
        block = source[start:end]
        self.assertIn("self._perguntar_reinicio_visualizacao()", block)
        self.assertNotIn('messagebox.showinfo(', block)
        self.assertIn('text="Reiniciar"', source)
        self.assertIn('text="Depois"', source)
        self.assertIn("def _reiniciar_aplicativo", source)
        self.assertIn("_prepare_independent_restart_environment", source)

        self.assertIn('dialog.geometry("340x160")', source)
    def test_status_animation_reproduz_configuracao_da_v2_99_35(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _iniciar_pisca_status")
        end = source.index("def _interpolar_cor", start)
        block = source[start:end]
        self.assertIn("self._status_anim_frames = 28 if self._status_blink_fast else 36", block)
        self.assertIn("self._status_anim_interval = 28 if self._status_blink_fast else 32", block)
        exec_start = source.index("def _executar_pisca_status", start)
        exec_end = source.index("def _parar_pisca_status", exec_start)
        exec_block = source[exec_start:exec_end]
        self.assertIn("import math", exec_block)
        self.assertIn("math.sin", exec_block)
        self.assertIn("self.status_indicator.configure(bg=canvas_bg)", exec_block)
        self.assertIn("self.status_indicator.itemconfigure(", exec_block)

    def test_scrollbars_usam_referencia_arredondada_com_setas(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("class _SMWindowsRoundedScrollbar(tk.Canvas):", source)
        self.assertIn("ARROW_SIZE = 16", source)
        self.assertIn("ARROW_SCROLL_UNITS = 12", source)
        self.assertIn("scrollable_range = max(0.0, 1.0 - visible)", source)
        self.assertIn("position_fraction = self._first / scrollable_range", source)
        self.assertNotIn('text="Acompanhamento"', source)
        self.assertIn("height=26, corner_radius=8,", source)
        self.assertIn("def _rounded_rect", source)
        self.assertIn("create_polygon", source)
        self.assertIn("_ui_install_scrollbar_autopatch()", source)
        self.assertNotIn("ttk.Scrollbar", source)

    def test_reposicionamento_de_menus_e_coalescido(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _reposicionar_menus")
        end = source.index("def _fixar_menu_configuracoes", start)
        block = source[start:end]
        self.assertIn("self.app.after_idle(self._reposicionar_menus)", block)
        self.assertNotIn("self.app.update_idletasks()", block)

    def test_planilha_nao_tem_modo_ctrl_selecao_exclusivo(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn("_planilha_ctrl_multiselect", source)
        self.assertNotIn("def _planilha_limpar_selecao", source)

    def test_menus_nao_sao_criados_visiveis_em_00(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _mostrar_menu_configuracoes")
        end = source.index("def _garantir_menu_aparencia_aberto_se_hover", start)
        block = source[start:end]
        self.assertIn("menu.place_forget()", block)
        self.assertNotIn("menu.place(x=0, y=0)", block)

        start = source.index("def _mostrar_menu_aparencia")
        end = source.index("def _cancelar_fechar_menus", start)
        block = source[start:end]
        self.assertIn("sub.place_forget()", block)
        self.assertNotIn("sub.place(x=0, y=0)", block)

    def test_reposicionamento_dos_menus_so_fica_ligado_enquanto_aberto(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertNotIn('self.app.bind("<Configure>", self._reposicionar_menus, add="+")', source)
        self.assertIn('self.app.bind(\n                "<Configure>", self._reposicionar_menus, add="+"', source)
        self.assertIn("self.app.unbind(\"<Configure>\", binding)", source)

    def test_resize_sem_mudanca_de_tamanho_nao_refaz_layout_do_acompanhamento(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _ajustar_altura_acompanhamento")
        end = source.index("def _set_stat", start)
        block = source[start:end]
        self.assertIn("anterior_tamanho == tamanho", block)
        self.assertIn("return", block)

    def test_menu_configuracoes_fecha_ao_sair_da_area(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _monitorar_menus", source)
        self.assertIn("def _pointer_em_area_dos_menus", source)
        self.assertIn("if not self._pointer_em_area_dos_menus():", source)
        self.assertIn("self._fechar_menus()", source[source.index("def _monitorar_menus"):source.index("def _fechar_menu_aparencia")])
        self.assertNotIn("_SMAutoLabMenuEvents", source)

    def test_menu_aparencia_fecha_ao_mudar_para_outro_item(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _monitorar_menus")
        end = source.index("def _cancelar_fechar_menus", start)
        block = source[start:end]
        self.assertIn("self._pointer_no_menu_aparencia()", block)
        self.assertIn("self._pointer_no_botao_aparencia()", block)
        self.assertIn("self._agendar_fechar_aparencia()", block)
        self.assertIn("self._cancelar_fechar_aparencia()", block)
        self.assertIn("if self._menu_aparencia_close_job is not None:", source)
        self.assertIn("self._menu_aparencia_close_job = self.app.after(120,", source)
        self.assertIn('aparencia.bind("<Enter>", self._cancelar_fechar_aparencia, add="+")', source)
        self.assertIn('widget.bind("<Enter>", self._cancelar_fechar_aparencia, add="+")', source)
        self.assertIn("def _fechar_menu_aparencia", source)

    def test_icones_estatisticos_usa_imagem_superamostrada_para_bordas_suaves(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("from PIL import Image, ImageDraw, ImageFont, ImageTk", source)
        self.assertIn("def _criar_imagem_icone_estatistica", source)
        start = source.index("def _criar_imagem_icone_estatistica")
        end = source.index("def _render_stat_icon", start)
        block = source[start:end]
        self.assertIn("scale = 4", block)
        self.assertIn("Image.Resampling.LANCZOS", block)
        self.assertIn("ImageTk.PhotoImage", block)

    def test_history_pasta_aceita_clique_unico_e_ctrl_multiseleciona(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _criar_pasta_historico")
        end = source.index("def _abrir_detalhe_historico", start)
        block = source[start:end]
        self.assertIn("getattr(event, \"state\", 0)", block)
        self.assertIn("0x0004", block)
        self.assertIn("self._historico_selecionados.add(execucao_id)", block)
        self.assertIn('widget.bind("<Button-1>", clicar)', block)
        self.assertNotIn('widget.bind("<Double-1>"', block)

    def test_history_detalhes_recuperam_codigos_de_erro(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _preencher_detalhe_pasta")
        end = source.index("def _limpar_historico", start)
        block = source[start:end]
        self.assertIn('execucao.get("codigos_erros")', block)
        self.assertIn('execucao.get("erros_codigos")', block)
        self.assertIn('execucao.get("codigos_erro")', block)
        self.assertIn('item.get("codigo")', block)

    def test_contador_arquivos_ignora_execucoes_sem_planilha_salva(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _contar_codigos_mes")
        end = source.index("def _formatar_contador_arquivos", start)
        block = source[start:end]
        self.assertIn("self._historico_planilhas_visiveis()", block)
        self.assertNotIn("self._historico_execucoes", block)
        self.assertIn('int(item.get("filled", 0) or 0)', block)

    def test_calendar_aceita_ctrl_multiseleção_e_hit_test_exato(self):
        source = (self.root / "interface.py").read_text(encoding="utf-8")
        start = source.index("def _clique_calendario_arquivos")
        end = source.index("def _mudar_mes_arquivos", start)
        block = source[start:end]
        self.assertIn("canvas.find_overlapping", block)
        self.assertIn("getattr(event, \"state\", 0)", block)
        self.assertIn("0x0004", block)
        self.assertIn("self._arquivos_datas_selecionadas.add(data)", block)
        self.assertIn("self._atualizar_botao_apagar_datas_arquivos()", block)
        self.assertIn("self._mostrar_planilhas_do_dia(data)", block)
        self.assertIn("def _apagar_datas_arquivos_selecionadas", source)
        self.assertIn('text="Apagar selecionados"', source)

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
