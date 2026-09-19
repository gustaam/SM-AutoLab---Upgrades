from __future__ import annotations

import re
from pathlib import Path


VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(\.\d+)?$")
ACTION_USE_RE = re.compile(r"^\s*uses:\s*([^\s]+)\s*$", re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
REQUIRED_PYTHON_VERSION = "3.14.7"
REQUIRED_PIP_VERSION = "26.2.1"

ACTION_RUNTIME_REFS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
    "softprops/action-gh-release": "efb35369e0ad2afab669f228072c1b0d510eae64",
}
REQUIREMENT_PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[^\s#]+$")

REQUIRED_PATHS = (
    "main.py", "interface.py", "app.py", "config.py", "patch.py", "requirements.txt",
    "VERSION", "SM AutoLab.ico", "assets", "build_windows.bat", "scripts/validate_architecture.py",
    "scripts/validate_executable.py", "scripts/validate_version.py", "scripts/validate_quality.py",
    "tests/test_patch.py", "tests/test_planilha_open_path.py", "tests/test_planilha_core.py",
    "tests/test_validate_executable.py", "tests/test_storage_safe.py", "tests/test_validate_quality.py",
    "tests/test_stage12.py", "tests/test_stage13.py",
)

OBSOLETE_PATHS = (
    "version_info_template.txt", "ui_fixes_29912.py", "planilha.py", "resultados.py", "splash.py", "execution_center_29924.py", "tests/test_stage11.py",
    "patch_base.py", "patch_arquivos.py", "patch_ajustes.py", "patch_v266.py", "patch_v267.py",
    "patch_v266_new.py", "updater.py", "patch_297.py", "patch_298.py", "patch_299.py",
    "patch_2991.py", "patch_29910.py", "patch_ui.py", "tests/test_atualizacao.py",
    "tests/test_ui_correcoes_29912.py", "tests/test_historico_ilimitado.py", ".etapa-b-trigger",
    ".github/workflows/_fix_patch_b_import.yml",
    "automacao.py", "atualizacao.py", "planilha_core.py", "planilha_virtual_29926.py", "storage_safe.py",
    "ui_platform.py", "windows11_native_29925.py",
)

LEGACY_IMPORTS = (
    "from patch_base import", "from patch_arquivos import", "from patch_ajustes import", "from patch_297 import",
    "from patch_298 import", "from patch_299 import", "from patch_2991 import", "from patch_29910 import",
    "from patch_ui import", "from planilha import", "from resultados import", "from splash import",
    "from ui_fixes_29912 import",
)

LEGACY_IMPORT_CHECK_PATHS = (
    "main.py", "interface.py", "app.py", "config.py", "build_windows.bat",
)

WORKFLOW_PATHS = (
    ".github/workflows/validate-main.yml",
    ".github/workflows/release.yml",
)

PATCH_MARKERS = (
    "ARQUIVOS_COMPONENT_MARKER", "AJUSTES_COMPONENT_MARKER", "_SOURCE_PATCH_BASE", "_SOURCE_PATCH_ARQUIVOS",
    "_SOURCE_PATCH_AJUSTES", "_NS_PATCH_BASE", "_NS_PATCH_ARQUIVOS", "_NS_PATCH_AJUSTES", "PATCH_297_MARKER",
    "PATCH_298_MARKER", "PATCH_299_MARKER", "PATCH_2991_MARKER", "PATCH_29910_MARKER", "_historico_tem_erro",
    "_history_rebind_open_299", "_history_click_outside_299", "_instalar_deselecao_global_299",
    "_count_saved_passwords", "firstweekday", "_atualizar_contador_selecao_29910",
    "_ensure_selection_state_29910", "def aplicar_patch_ui",
)

UI_MARKERS = (
    "SM_AUTOLAB_UI_FIXES_29912", "_home_counter", "_calendar_click", "_create_history_tile",
    "_select_history_tile", "def install_ui_29912",
)

TEST_MARKERS = (
    "class VersionComparisonTests", "class UpdateEnvironmentTests", "class UpdateDiscoveryTests",
    "class UIFixes29912Tests", "class HistoricoIlimitadoTests", "class GradePerformanceStage9Tests", "class PlanilhaVirtualStage13Tests", "test_arquivos_de_teste_auxiliares_foram_consolidados",
)

BUILD_MARKERS = ("VSVersionInfo(", "FixedFileInfo(", "StringFileInfo([", "Set-Content version_info.txt")


def fail(message: str) -> None:
    raise SystemExit(f"ERRO: {message}")


def read_text(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError as exc:
        fail(f"não foi possível ler {relative}: {exc}")


def require_markers(name: str, content: str, markers: tuple[str, ...]) -> None:
    for marker in markers:
        if marker not in content:
            fail(f"{name} não contém: {marker}")


def validate_dependencies(root: Path) -> None:
    content = read_text(root, "requirements.txt")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        fail("requirements.txt está vazio")
    for line in lines:
        if not REQUIREMENT_PIN_RE.fullmatch(line):
            fail(f"dependência sem versão exata em requirements.txt: {line}")


def validate_workflow_pins(root: Path) -> None:
    for relative in WORKFLOW_PATHS:
        content = read_text(root, relative)
        matches = ACTION_USE_RE.findall(content)
        if not matches:
            fail(f"{relative} não contém nenhuma GitHub Action para validar")
        for action_ref in matches:
            if "@" not in action_ref:
                fail(f"GitHub Action sem ref em {relative}: {action_ref}")
            action_name, revision = action_ref.rsplit("@", 1)
            if not action_name or not SHA_RE.fullmatch(revision):
                fail(f"GitHub Action não está fixada em SHA de commit em {relative}: {action_ref}")
            expected_revision = ACTION_RUNTIME_REFS.get(action_name)
            if expected_revision is None:
                fail(f"GitHub Action não autorizada em {relative}: {action_ref}")
            if revision.lower() != expected_revision:
                fail(f"GitHub Action desatualizada em {relative}: {action_ref}")


def validate_workflow_runtime(root: Path) -> None:
    for relative in WORKFLOW_PATHS:
        content = read_text(root, relative)
        if f'python-version: "{REQUIRED_PYTHON_VERSION}"' not in content:
            fail(f"{relative} deve fixar Python em {REQUIRED_PYTHON_VERSION}")
        if f"python -m pip install pip=={REQUIRED_PIP_VERSION}" not in content:
            fail(f"{relative} deve fixar pip em {REQUIRED_PIP_VERSION}")
        if "python -m pip install -r requirements.txt" not in content:
            fail(f"{relative} deve instalar requirements.txt usando o mesmo interpretador Python")

    build = read_text(root, "build_windows.bat")
    if "pip check" not in build:
        fail("build_windows.bat deve validar a consistência das dependências com pip check")
    if "python -m pip install -r requirements.txt" not in read_text(root, ".github/workflows/validate-main.yml"):
        fail("validate-main.yml deve instalar dependências pelo módulo pip do Python configurado")
    if "python -m pip check" not in read_text(root, ".github/workflows/validate-main.yml"):
        fail("validate-main.yml deve validar a consistência das dependências com pip check")
    if "python -m pip install -r requirements.txt" not in read_text(root, ".github/workflows/release.yml"):
        fail("release.yml deve instalar dependências pelo módulo pip do Python configurado")
    if "python -m pip check" not in read_text(root, ".github/workflows/release.yml"):
        fail("release.yml deve validar a consistência das dependências com pip check")
    if "sys.version_info[:3] == (3, 14, 7)" not in build:
        fail("build_windows.bat deve exigir Python 3.14.7")
    if f"pip install pip=={REQUIRED_PIP_VERSION}" not in build:
        fail(f"build_windows.bat deve fixar pip em {REQUIRED_PIP_VERSION}")
    if "python -m pip install pyinstaller==6.22.2" not in read_text(root, ".github/workflows/release.yml"):
        fail("release.yml deve instalar PyInstaller pelo módulo pip do Python configurado")
    if "%PYTHON% -m pip install pyinstaller==6.22.2" not in build:
        fail("build_windows.bat deve instalar PyInstaller pelo interpretador Python configurado")
    release = read_text(root, ".github/workflows/release.yml")
    if "python -m pip install pyinstaller==6.22.2" not in release:
        fail("release.yml deve fixar PyInstaller em 6.22.2")
    if "python -m PyInstaller --noconfirm --clean" not in release:
        fail("release.yml deve executar PyInstaller pelo interpretador Python configurado")


def validate_workflow_security(root: Path) -> None:
    release = read_text(root, ".github/workflows/release.yml")
    validate_workflow_runtime(root)
    if "permissions: {}" not in release:
        fail("release.yml deve começar com permissões vazias por padrão")
    if "jobs:\n  release:\n    permissions:\n      contents: write" not in release:
        fail("release.yml deve conceder contents: write somente ao job de release")
    if "RELEASE_TAG: ${{ github.event.inputs.release_tag || github.ref_name }}" not in release:
        fail("release.yml não centraliza a tag recebida em RELEASE_TAG")
    for relative in WORKFLOW_PATHS:
        content = read_text(root, relative)
        if "fetch-depth: 1\n          persist-credentials: false" not in content:
            fail(f"{relative} deve desativar a persistência de credenciais do checkout")
    for marker in ("$tag = $env:RELEASE_TAG", "if ($version -ne $tagVersion)"):
        if marker not in release:
            fail(f"release.yml não usa a entrada de tag de forma segura: {marker}")


def validate(root: Path) -> None:
    version = read_text(root, "VERSION").strip()
    if not VERSION_RE.fullmatch(version):
        fail(f"VERSION inválida: {version}")

    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            fail(f"recurso obrigatório ausente: {relative}")

    for relative in OBSOLETE_PATHS:
        if (root / relative).exists():
            fail(f"arquivo/artefato obsoleto ainda presente: {relative}")

    contents = {relative: read_text(root, relative) for relative in (
        "main.py", "interface.py", "app.py", "config.py", "patch.py", "build_windows.bat", "tests/test_patch.py",
    )}

    main = contents["main.py"]
    interface = contents["interface.py"]
    app = contents["app.py"]
    config = contents["config.py"]
    patch = contents["patch.py"]
    build = contents["build_windows.bat"]
    tests = contents["tests/test_patch.py"]

    require_markers("main.py", main, (
        "from patch import aplicar_patch_ui", "def install_ui_29912", "def install_ui_fluent_29916", "class StartupSplash",
        "def _corrigir_historico_ilimitado", "def _validar_base_aplicacao",
        "SM_AUTOLAB_PLANILHA_29919", "def install_ui_planilha_29919",
        "SM_AUTOLAB_AUDITORIA_29920", "def _configurar_dpi_windows",
        "def install_ui_auditoria_29920", "SM_AUTOLAB_RESPONSIVO_29921",
        "def install_ui_responsivo_29921",
        "def install_ui(App)",
        "SM_AUTOLAB_GRADE_VIRTUAL_29926", "SM_AUTOLAB_WINDOWS_NATIVE_29925",
        "from interface import App, SM_AUTOLAB_GRADE_VIRTUAL_29926, install_ui_windows11_native_29925", "install_ui_windows11_native_29925(App)",
    ))
    require_markers("app.py", app, ("class Resultados", "def carregar_codigos"))
    require_markers("patch.py", patch, PATCH_MARKERS)
    require_markers("main.py", main, UI_MARKERS)

    for legacy_grid in (
        "ttk.Treeview(",
        "ttk.Style(",
        "_planilha_povoamento_",
    ):
        if legacy_grid in interface:
            fail(f"estrutura legada da grade detectada em interface.py: {legacy_grid}")
    for legacy_virtual in (
        "def tag_configure(",
        "def insert(",
        "def event_generate(",
    ):
        if legacy_virtual in interface:
            fail(f"compatibilidade Treeview obsoleta em interface.py: {legacy_virtual}")

    # A planilha tem uma única implementação de abertura e uma única camada
    # final de interação. Overrides históricos não podem voltar ao runtime.
    if interface.count("    def abrir_planilha(self, dados_iniciais=None):") != 1:
        fail("interface.py deve conter exatamente uma implementação de abrir_planilha")
    for legacy in (
        "App.abrir_planilha = _abrir_planilha_297",
        "App.abrir_planilha = _abrir_planilha_2991",
        "App.abrir_planilha = open_planilha_wrapper",
        "App._planilha_clicar_celula = _planilha_clicar_celula_2991",
        "App._planilha_arrastar_selecao = _planilha_arrastar_selecao_2991",
        "App._planilha_soltar_selecao = _planilha_soltar_selecao_2991",
        "def _abrir_planilha_2991",
        "def _abrir_planilha_297",
        "def _install_planilha_context_menu",
    ):
        if legacy in patch or legacy in main:
            fail(f"override legado da planilha detectado: {legacy}")
    require_markers(
        "main.py",
        main,
        (
            "SM_AUTOLAB_PLANILHA_29919",
            "def install_ui_planilha_29919",
            "SM_AUTOLAB_AUDITORIA_29920",
            "def _configurar_dpi_windows",
            "def install_ui_auditoria_29920",
            "SM_AUTOLAB_RESPONSIVO_29921",
            "def install_ui_responsivo_29921",
            "def install_ui(App)",
            "FPS_MS = 16",
            "SetProcessDpiAwarenessContext",
            "ctypes.c_void_p(-4)",
            "SetProcessDpiAwareness",
            "setter(2)",
        ),
    )
    require_markers("interface.py", interface, ("def abrir_planilha(self, dados_iniciais=None):", "self._planilha_implementacao = \"grade-virtual-29926\"",
        "SM_AUTOLAB_GRADE_29922", "def _planilha_desenhar_grade", "def _planilha_stage9_get_grid_state", "def _planilha_desenhar_cabecalho_linhas", "def _assinatura_historico_planilhas", "_stage7_top_layout", "_stage7_progress_card", "Tooltips passam a ser gerenciados globalmente", "tree=VirtualGridTree(", "value_provider=", "total_rows=10000", "tree.bind(\"<B1-Motion>\", self._planilha_arrastar_selecao, add=\"+\")", "tree.bind(\"<ButtonRelease-1>\", self._planilha_soltar_selecao, add=\"+\")"))

    require_markers("tests/test_patch.py", tests, TEST_MARKERS)
    require_markers("planilha_core.py", planilha_core, (
        "def rectangle_selection", "def parse_paste_text", "def apply_paste",
        "def clear_cells", "def undo_state", "def redo_state",
    ))
    stage12_test = read_text(root, "tests/test_stage12.py")
    require_markers("tests/test_stage12.py", stage12_test, ("class Windows11NativeStage12Tests", "SM_AUTOLAB_WINDOWS_NATIVE_29925", "install_ui_windows11_native_29925", "SystemParametersInfoW", "SetWindowTheme"))
    stage13_test = read_text(root, "tests/test_stage13.py")
    require_markers("tests/test_stage13.py", stage13_test, ("class VirtualGridStage13Tests", "SM_AUTOLAB_GRADE_VIRTUAL_29926", "VirtualGridTree", "visible_row_range"))
    validate_dependencies(root)
    validate_workflow_pins(root)
    validate_workflow_security(root)

    for legacy_import in LEGACY_IMPORTS:
        for relative in LEGACY_IMPORT_CHECK_PATHS:
            if relative in contents and legacy_import in contents[relative]:
                fail(f"import legado detectado em {relative}: {legacy_import}")

    if "Ctrl + clique para selecionar várias datas" in patch:
        fail("instrução visual antiga ainda presente em patch.py")
    if "tkcalendar" in interface:
        fail("dependência tkcalendar detectada")
    if not re.search(r"def\s+find_update\s*\(", interface) or not re.search(r"def\s+launch_updater\s*\(", interface):
        fail("motor integrado de atualização não encontrado em interface.py")
    if re.search(r"SM[ ._]?AutoLab[ ._-]?Updater\.exe|updater\.py|--sm-autolab-updater|--sm-autolab-update-helper", interface):
        fail("referência ao atualizador separado detectada")

    if not re.search(r'DEFAULT_PORTAL_USUARIO\s*=\s*""', config):
        fail("usuário padrão não está vazio em config.py")
    if not re.search(r'DEFAULT_PORTAL_SENHA\s*=\s*""', config):
        fail("senha padrão não está vazia em config.py")
    if re.search(r'"PORTAL_USUARIO"\s*:\s*"[^"\r\n]+"', interface):
        fail("valor de acesso literal encontrado em interface.py para PORTAL_USUARIO")
    if re.search(r'"PORTAL_SENHA"\s*:\s*"[^"\r\n]+"', interface):
        fail("valor de acesso literal encontrado em interface.py para PORTAL_SENHA")

    if not re.search(r"def _renderizar_calendario_arquivos", interface):
        fail("interface.py não contém o calendário de Arquivos")
    if "Canvas(" not in interface:
        fail("interface.py não contém o calendário nativo Canvas")

    build_exclusions = {
        "tests/test_atualizacao.py", "tests/test_ui_correcoes_29912.py", "tests/test_historico_ilimitado.py",
        ".etapa-b-trigger", ".github/workflows/_fix_patch_b_import.yml",
    }
    for relative in OBSOLETE_PATHS:
        if relative not in build_exclusions and relative in build:
            fail(f"build_windows.bat ainda referencia artefato legado: {relative}")

    if "SM AutoLab" not in build:
        fail("build_windows.bat não contém a rotina de build do SM AutoLab")
    if "from interface import App; from main import install_ui, _validar_base_aplicacao" not in build:
        fail("build_windows.bat não usa o mesmo ponto de entrada da UI")
    if "install_ui(App); _validar_base_aplicacao()" not in build:
        fail("build_windows.bat não executa o ponto de entrada consolidado")

    release = read_text(root, ".github/workflows/release.yml")
    release_flow = "from interface import App; from main import install_ui, _validar_base_aplicacao; install_ui(App); _validar_base_aplicacao()"
    if release_flow not in release:
        fail("release.yml não usa o mesmo ponto de entrada consolidado da validação da main")
    for marker in BUILD_MARKERS:
        if marker not in build:
            fail(f"build_windows.bat não contém o metadado esperado: {marker}")


if __name__ == "__main__":
    repository_root = Path(__file__).resolve().parents[1]
    validate(repository_root)
    print("Validação de arquitetura consolidada: OK")