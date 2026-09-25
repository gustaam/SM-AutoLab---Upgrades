# Validação automática de workflows e release.
# Testes de qualidade do projeto: arquitetura, workflows, versão, release e executável.

import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate import (
    _cli_all,
    parse_version,
    validate_dependencies,
    validate_pe,
    validate_quality,
    validate_version,
    validate_workflow_pins,
    validate_workflow_security,
)

class ConsolidatedValidationTests(unittest.TestCase):
    def test_cli_all_executa_validadores_de_dependencias_e_workflow(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("scripts.validate.validate_architecture") as architecture, \
                 patch("scripts.validate.validate_version") as version, \
                 patch("scripts.validate.validate_dependencies") as dependencies, \
                 patch("scripts.validate.validate_workflow_pins") as pins, \
                 patch("scripts.validate.validate_workflow_security") as security, \
                 patch("scripts.validate.validate_quality") as quality:
                self.assertEqual(_cli_all(root), 0)

            architecture.assert_called_once_with(root)
            version.assert_called_once_with(root / "VERSION")
            dependencies.assert_called_once_with(root)
            pins.assert_called_once_with(root)
            security.assert_called_once_with(root)
            quality.assert_called_once_with(root)

    def test_workflow_de_main_nao_dispara_release_manual(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "validate-main.yml").read_text(encoding="utf-8")
        self.assertNotIn("gh workflow run release.yml", workflow)
        self.assertIn("  push:\n    branches:\n      - main", workflow)
        self.assertIn("group: sm-autolab-validate-main-${{ github.ref }}", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        release = (root / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_run:", release)
        self.assertIn('- "Validate main for release"', release)
        self.assertIn('"${{ github.event.workflow_run.conclusion }}" -eq "success"', release)
        self.assertIn('"${{ github.event.workflow_run.event }}" -eq "push"', release)
        self.assertIn('$validatedHead = "${{ github.event.workflow_run.head_sha }}".Trim()', release)
        self.assertIn('$eligible = $mainHead -and ($validatedHead -eq $mainHead)', release)
        self.assertIn("releases/tags/$tag", release)
        self.assertIn("id: release_state", release)
        self.assertIn("already_published != 'true'", release)
        self.assertIn("EXPECTED_COMMIT", release)
        self.assertIn("refs/tags/$($env:RELEASE_TAG)^{commit}", release)
        self.assertNotIn("push:\n    tags:", release)
        self.assertNotIn("v3.0.0", release)
        self.assertNotIn("-Method Delete", release)
        self.assertNotIn("refs/tags/$oldTag", release)
        self.assertNotIn("  tag:", workflow)
        self.assertIn("group: sm-autolab-release", release)
        self.assertIn("Resolver Selenium Manager para o build", release)
        self.assertIn("--additional-hooks-dir hooks", release)
        self.assertIn("hook-selenium.webdriver.common.selenium_manager.py", release)
        self.assertNotIn('--add-binary "$env:SELENIUM_MANAGER_PATH;selenium\\webdriver\\common\\windows"', release)
        self.assertIn("Selenium Manager não encontrado no ambiente de build", release)
        self.assertIn("Preparar Chrome for Testing integrado", release)
        self.assertIn("scripts/prepare_chrome_for_testing.py", release)
        self.assertIn('build_resources\\chrome_for_testing;chrome_for_testing', release)
        self.assertNotIn('dist\\navegador\\chrome-win64\\chrome.exe', release)
        self.assertNotIn('dist\\navegador\\chromedriver-win64\\chromedriver.exe', release)
        self.assertIn("Chrome for Testing não foi encontrado no bundle do executável", release)
        interface = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("def _vincular_enter_confirmacao", interface)
        self.assertIn('win.bind("<ButtonPress-1>", self._planilha_clique_janela, add="+")', interface)
        self.assertIn('win.bind("<KeyPress>", self._planilha_teclar_janela, add="+")', interface)
        self.assertIn('win.bind("<Tab>", self._planilha_tabular_janela, add="+")', interface)
        self.assertIn("win.focus_force()", interface)
        self.assertIn("widget.focus_force()", interface)
        self.assertIn('return "break"\n\n\n    def _planilha_arrastar_selecao', interface)
        self.assertIn('widget.bind("<Return>", confirmar, add="+")', interface)
        self.assertIn('widget.bind("<KP_Enter>", confirmar, add="+")', interface)
        self.assertIn('text="Reiniciar"', interface)
        self.assertIn("self._vincular_enter_confirmacao(dialog, reiniciar, reiniciar_btn)", interface)
        self.assertIn("self._vincular_enter_confirmacao(popup, salvar, salvar_btn)", interface)
        interface_sem_espacos = "".join(interface.split())
        self.assertIn(
            "".join("self._vincular_enter_confirmacao(parent, reexecutar_erros, reexecutar_btn,".split()),
            interface_sem_espacos,
        )
        self.assertIn("COMPACT_WINDOW_WIDTH = 600", interface)
        self.assertIn("COMPACT_WINDOW_HEIGHT = 340", interface)
        self.assertIn("largura, altura = COMPACT_WINDOW_WIDTH, COMPACT_WINDOW_HEIGHT", interface)
        self.assertIn("ACTION_STOP_WIDTH = 140", interface)
        self.assertIn("ACTION_START_WIDTH = 150", interface)
        self.assertIn("ACTION_BUTTON_HEIGHT = 46", interface)
        self.assertIn("width=ACTION_STOP_WIDTH", interface)
        self.assertIn("width=ACTION_START_WIDTH", interface)
        self.assertIn("height=ACTION_BUTTON_HEIGHT", interface)
        self.assertIn("ACTION_STOP_WIDTH + ACTION_BUTTON_GAP + ACTION_START_WIDTH", interface)
        self.assertGreaterEqual(interface.count('font=("Segoe UI", 14, "bold")'), 2)
        build_bat = (root / "build_windows.bat").read_text(encoding="utf-8")
        self.assertIn("scripts\\prepare_chrome_for_testing.py", build_bat)
        self.assertIn('build_resources\\chrome_for_testing;chrome_for_testing', build_bat)
        self.assertNotIn('robocopy "build_resources\\chrome_for_testing" "dist\\navegador"', build_bat)
        self.assertIn('dist\\SM AutoLab.exe', build_bat)
        prepare = (root / "scripts" / "prepare_chrome_for_testing.py").read_text(encoding="utf-8")
        self.assertIn("last-known-good-versions-with-downloads.json", prepare)
        self.assertIn("known-good-versions-with-downloads.json", prepare)
        self.assertIn('VERSION_LOCK = Path("CHROME_FOR_TESTING_VERSION")', prepare)
        self.assertIn('PLATFORM = "win64"', prepare)
        self.assertIn('"chrome-win64" / "chrome.exe"', prepare)
        self.assertIn('"chromedriver-win64" / "chromedriver.exe"', prepare)
        self.assertIn("_safe_extract", prepare)
        self.assertIn("Selenium Manager e Chrome for Testing dentro do executável", release)
        self.assertIn("id: release_gate", release)
        self.assertIn("should_release=$($eligible.ToString().ToLower())", release)
        self.assertNotIn("    if: >-", release)

    def test_regressoes_visuais_e_de_rolagem_estao_protegidas(self):
        root = Path(__file__).resolve().parents[1]
        interface = (root / "interface.py").read_text(encoding="utf-8")
        self.assertIn("ARROW_SCROLL_UNITS = 12", interface)
        self.assertIn("_sm_autolab_tooltip_message", interface)
        self.assertNotIn("border_width=0 if dark_mode else 1", interface)
        self.assertIn('"border": ("#D4E6D9", "#132219")', interface)
        self.assertIn("border_width=1", interface)
        self.assertNotIn("image=self._obter_icone_menu_aplicativo()", interface)
        self.assertIn('fg_color=("#FFFFFF", "#2D3338")', interface)
        self.assertIn("def _configurar_icone_janela(self, janela=None):", interface)
        self.assertIn("janela.iconbitmap(str(icone))", interface)
        self.assertIn("self._configurar_icone_janela(popup)", interface)
        self.assertIn('text="Ajustes do Feegow"', interface)
        self.assertNotIn("image=self._obter_icone_menu_aplicativo()", interface)
        self.assertNotIn('compound="left"', interface)
        self.assertIn("DWMWA_CAPTION_COLOR = 35", interface)
        self.assertIn("DWMWA_TEXT_COLOR = 36", interface)
        self.assertIn("_configurar_titulo_dwm(hwnd, bool(dark))", interface)
        self.assertIn('"border": ("#D4E6D9", "#132219")', interface)
        self.assertIn('border_width=1,', interface)
        self.assertIn('detalhes_erros = execucao.get("erros_detalhes") or []', interface)

    def test_validadores_de_workflow_e_dependencias_continuam_disponiveis(self):
        self.assertTrue(callable(validate_dependencies))
        self.assertTrue(callable(validate_workflow_pins))
        self.assertTrue(callable(validate_workflow_security))


# tests/test_validate_executable.py

class ExecutableValidationTests(unittest.TestCase):
    def _write_pe(self, size=1_100_000, mz=b"MZ", pe=b"PE\x00\x00"):
        handle = tempfile.NamedTemporaryFile(delete=False)
        path = Path(handle.name)
        handle.close()
        data = bytearray(max(size, 0x100))
        data[:2] = mz
        struct.pack_into("<I", data, 0x3C, 0x80)
        data[0x80:0x84] = pe
        path.write_bytes(data)
        return path

    def test_validate_pe_aceita_executavel_pe_minimo(self):
        path = self._write_pe()
        try:
            result = validate_pe(path)
            self.assertEqual(result["pe_offset"], 0x80)
            self.assertGreaterEqual(result["size"], 1_000_000)
        finally:
            path.unlink(missing_ok=True)

    def test_rejeita_assinatura_mz(self):
        path = self._write_pe(mz=b"XX")
        try:
            with self.assertRaises(ValueError):
                validate_pe(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejeita_assinatura_pe(self):
        path = self._write_pe(pe=b"NOPE")
        try:
            with self.assertRaises(ValueError):
                validate_pe(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejeita_arquivo_pequeno(self):
        path = self._write_pe(size=1000)
        try:
            with self.assertRaises(ValueError):
                validate_pe(path)
        finally:
            path.unlink(missing_ok=True)


# tests/test_validate_quality.py

class QualityValidationTests(unittest.TestCase):
    def test_repositorio_atual_passa_na_validacao(self):
        root = Path(__file__).resolve().parents[1]
        result = validate_quality(root)
        self.assertGreaterEqual(result["modules"], 1)
        self.assertEqual(result["cycles"], [])

    def test_detecta_metodo_duplicado_direto_na_classe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(
                "class App:\n"
                "    def x(self): pass\n"
                "    def x(self): pass\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "método duplicado"):
                validate_quality(root)

    def test_detecta_import_wildcard(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text(
                "from config import *\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "import wildcard"):
                validate_quality(root)

    def test_detecta_ciclo_local(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "main.py").write_text("from interface import App\n", encoding="utf-8")
            (root / "interface.py").write_text("import main\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ciclo de importação"):
                validate_quality(root)


# tests/test_validate_version.py

class VersionValidationTests(unittest.TestCase):
    def test_parse_version_normaliza_prefixo_v(self):
        self.assertEqual(parse_version("v2.99.21"), (2, 99, 21))
        self.assertEqual(parse_version("2.99.21.1"), (2, 99, 21, 1))

    def test_parse_version_rejeita_formato_invalido(self):
        for value in ("", "v", "2.99", "2.99.x", "2.99.21.1.0"):
            self.assertEqual(parse_version(value), ())

    def test_validate_version_aceita_mesma_versao_anterior(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("2.99.21\n", encoding="utf-8")
            (root / "PREV").write_text("2.99.21\n", encoding="utf-8")
            self.assertEqual(
                validate_version(root / "VERSION", root / "PREV"),
                (2, 99, 21),
            )

    def test_validate_version_aceita_incremento(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("2.99.22\n", encoding="utf-8")
            (root / "PREV").write_text("2.99.21\n", encoding="utf-8")
            self.assertEqual(
                validate_version(root / "VERSION", root / "PREV"),
                (2, 99, 22),
            )

    def test_validate_version_rejeita_regressao(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "VERSION").write_text("2.99.20\n", encoding="utf-8")
            (root / "PREV").write_text("2.99.21\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_version(root / "VERSION", root / "PREV")
