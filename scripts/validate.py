# Validador do projeto: arquitetura, dependências, versão, workflows e executável Windows.
from __future__ import annotations

import argparse
import ast
import re
import struct
from pathlib import Path

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(\.\d+)?$")
ACTION_USE_RE = re.compile(r"^\s*uses:\s*([^\s]+)\s*$", re.MULTILINE)
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
REQUIRED_PYTHON_VERSION = "3.14.7"
REQUIRED_PIP_VERSION = "26.2.1"

BUILD_MARKERS = ("VSVersionInfo(", "FixedFileInfo(", "StringFileInfo([", "Set-Content version_info.txt")

ACTION_RUNTIME_REFS = {
    "actions/checkout": "3d3c42e5aac5ba805825da76410c181273ba90b1",
    "actions/setup-python": "5fda3b95a4ea91299a34e894583c3862153e4b97",
    "softprops/action-gh-release": "efb35369e0ad2afab669f228072c1b0d510eae64",
}
REQUIREMENT_PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[^\s#]+$")

REQUIRED_PATHS = (
    "main.py", "interface.py", "app.py", "requirements.txt",
    "VERSION", "SM AutoLab.ico", "assets", "build_windows.bat", "scripts/validate.py",
    "tests/test_patch.py", "tests/test_main.py", "tests/test_planilha.py",
    "tests/test_app.py", "tests/test_validation.py", "scripts/smoke_ui.py",
)

OBSOLETE_PATHS = (
    "version_info_template.txt", "ui_fixes_29912.py", "planilha.py", "resultados.py", "splash.py", "execution_center_29924.py", "tests/test_stage11.py",
    "patch_base.py", "patch_arquivos.py", "patch_ajustes.py", "patch_v266.py", "patch_v267.py",
    "patch_v266_new.py", "updater.py", "patch_297.py", "patch_298.py", "patch_299.py",
    "patch_2991.py", "patch_29910.py", "patch_ui.py", "tests/test_atualizacao.py",
    "tests/test_ui_correcoes_29912.py", "tests/test_historico_ilimitado.py", ".etapa-b-trigger",
    ".github/workflows/_fix_patch_b_import.yml", ".github/workflows/create-release-tag.yml",
    "automacao.py", "atualizacao.py", "planilha_core.py", "planilha_virtual_29926.py", "storage_safe.py",
    "ui_platform.py", "windows11_native_29925.py", "patch.py",
    "tests/test_config_menu_position.py", "tests/test_dashboard.py", "tests/test_planilha_behavior.py",
    "tests/test_planilha_core.py", "tests/test_planilha_deterministic_open.py", "tests/test_planilha_grid.py",
    "tests/test_planilha_open_path.py", "tests/test_saved_sheet_counter.py", "tests/test_stage10.py",
    "tests/test_stage12.py", "tests/test_stage13.py", "tests/test_status_indicator.py",
    "tests/test_storage_safe.py", "tests/test_tooltips.py", "tests/test_validate_executable.py",
    "tests/test_validate_quality.py", "tests/test_validate_version.py",
)

LEGACY_IMPORTS = (
    "from patch_base import", "from patch_arquivos import", "from patch_ajustes import", "from patch_297 import",
    "from patch_298 import", "from patch_299 import", "from patch_2991 import", "from patch_29910 import",
    "from patch_ui import", "from planilha import", "from resultados import", "from splash import",
    "from ui_fixes_29912 import",
)

LEGACY_IMPORT_CHECK_PATHS = (
    "main.py", "interface.py", "app.py", "build_windows.bat",
)

WORKFLOW_PATHS = (
    ".github/workflows/validate-main.yml",
    ".github/workflows/release.yml",
)

TEST_MARKERS = (
    "class CanonicalRuntimeTests",
    "test_main_bootstrap_uses_only_canonical_ui",
    "test_appearance_submenu_uses_canonical_hover_and_monitoring",
    "test_planilha_mouse_events_use_one_hit_test",
    "test_legacy_patch_module_is_absent",
)

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
    if "python -m pip install pyinstaller==6.22.3" not in read_text(root, ".github/workflows/release.yml"):
        fail("release.yml deve instalar PyInstaller pelo módulo pip do Python configurado")
    if "%PYTHON% -m pip install pyinstaller==6.22.3" not in build:
        fail("build_windows.bat deve instalar PyInstaller pelo interpretador Python configurado")
    release = read_text(root, ".github/workflows/release.yml")
    if "python -m pip install pyinstaller==6.22.3" not in release:
        fail("release.yml deve fixar PyInstaller em 6.22.3")
    if "python -m PyInstaller --noconfirm --clean" not in release:
        fail("release.yml deve executar PyInstaller pelo interpretador Python configurado")


def validate_workflow_security(root: Path) -> None:
    validate = read_text(root, ".github/workflows/validate-main.yml")
    release = read_text(root, ".github/workflows/release.yml")
    if "\n  tag:\n" in validate:
        fail("validate-main.yml não deve manter um job tag concorrente com release.yml")
    expected_group = "group: sm-autolab-release-${{ github.event_name == 'workflow_run' && 'automatic' || github.event.inputs.release_tag }}"
    if expected_group not in release:
        fail("release.yml deve serializar releases automáticas por um grupo único")
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


def validate_architecture(root: Path) -> None:
    version = read_text(root, "VERSION").strip()
    if not VERSION_RE.fullmatch(version):
        fail(f"VERSION inválida: {version}")

    for relative in REQUIRED_PATHS:
        if not (root / relative).exists():
            fail(f"recurso obrigatório ausente: {relative}")

    for relative in OBSOLETE_PATHS:
        if (root / relative).exists():
            fail(f"arquivo/artefato obsoleto ainda presente: {relative}")

    main = read_text(root, "main.py")
    interface = read_text(root, "interface.py")
    app = read_text(root, "app.py")
    build = read_text(root, "build_windows.bat")
    tests = read_text(root, "tests/test_patch.py")

    if len(main.splitlines()) > 500:
        fail("main.py voltou a concentrar camadas legadas; mantenha o bootstrap enxuto")

    require_markers("main.py", main, (
        "SM_AUTOLAB_CANONICAL_UI",
        "class StartupSplash",
        "def _configurar_dpi_windows",
        "def _validar_base_aplicacao",
        "def install_ui(App)",
        "from interface import App, SM_AUTOLAB_GRADE_VIRTUAL",
    ))
    require_markers("app.py", app, ("class Resultados", "def carregar_codigos"))
    require_markers("tests/test_patch.py", tests, TEST_MARKERS)

    require_markers("interface.py", interface, (
        "def abrir_planilha(self, dados_iniciais=None):",
        "class VirtualGridTree",
        "def identify_cell",
        "def _planilha_clicar_celula",
        "def _planilha_arrastar_selecao",
        "def _planilha_soltar_selecao",
        "def _planilha_duplo_clique_celula",
        "def _planilha_desenhar_borda",
        'command=self._mostrar_menu_aparencia',
        'aparencia.bind("<Enter>", self._mostrar_menu_aparencia',
        'aparencia.bind("<Leave>", self._agendar_fechar_aparencia',
        'def _monitorar_menus',
        'tree.bind("<ButtonPress-1>", self._planilha_clicar_celula',
        'tree.bind("<B1-Motion>", self._planilha_arrastar_selecao',
        'tree.bind("<ButtonRelease-1>", self._planilha_soltar_selecao',
        "entry=Entry(tree._canvas",
        'tags=("virtual-column-line",)',
        'tags=("planilha-selection",)',
    ))
    
    for legacy in (
        "from patch import",
        "aplicar_patch_ui",
        "install_ui_29912(",
        "install_ui_fluent_29916(",
        "install_ui_dashboard_29917(",
        "install_ui_micro_29918(",
        "install_ui_planilha_29919(",
        "install_ui_responsivo_29921(",
        "install_ui_auditoria_29920(",
        "install_ui_windows11_native_29925(",
        "_fluent_animar_entrada",
        "bind_all",
    ):
        if legacy in main:
            fail(f"camada/runtime legado detectado em main.py: {legacy}")

    for legacy in (
        "bind_all",
        "Frame(tree,",
        'Entry(tree, bd=1, relief="solid"',
        "ttk.Treeview(",
        "def _planilha_povoamento_",
    ):
        if legacy in interface:
            fail(f"estrutura/evento legado detectado em interface.py: {legacy}")

    if interface.count("    def abrir_planilha(self, dados_iniciais=None):") != 1:
        fail("interface.py deve conter exatamente uma implementação de abrir_planilha")
    if interface.count("def identify_cell(") != 1:
        fail("VirtualGridTree deve ter exatamente um hit-test canônico de célula")

    if not re.search(r"def\s+find_update\s*\(", interface) or not re.search(r"def\s+launch_updater\s*\(", interface):
        fail("motor integrado de atualização não encontrado em interface.py")
    if re.search(r"SM[ ._]?AutoLab[ ._-]?Updater\.exe|updater\.py|--sm-autolab-updater|--sm-autolab-update-helper", interface):
        fail("referência ao atualizador separado detectada")

    if not re.search(r'DEFAULT_PORTAL_USUARIO\s*=\s*""', app):
        fail("usuário padrão não está vazio em app.py")
    if not re.search(r'DEFAULT_PORTAL_SENHA\s*=\s*""', app):
        fail("senha padrão não está vazia em app.py")
    if re.search(r'"PORTAL_USUARIO"\s*:\s*"[^"\r\n]+"', interface):
        fail("valor de acesso literal encontrado em interface.py para PORTAL_USUARIO")
    if re.search(r'"PORTAL_SENHA"\s*:\s*"[^"\r\n]+"', interface):
        fail("valor de acesso literal encontrado em interface.py para PORTAL_SENHA")

    if "Canvas(" not in interface:
        fail("interface.py não contém Canvas para a grade/calendário")

    for relative in OBSOLETE_PATHS:
        if relative in build:
            fail(f"build_windows.bat ainda referencia artefato legado: {relative}")

    if "SM AutoLab" not in build:
        fail("build_windows.bat não contém a rotina de build do SM AutoLab")
    if "from interface import App; from main import install_ui, _validar_base_aplicacao" not in build:
        fail("build_windows.bat não usa o ponto de entrada canônico")
    if "install_ui(App); _validar_base_aplicacao()" not in build:
        fail("build_windows.bat não executa o bootstrap canônico")

    release = read_text(root, ".github/workflows/release.yml")
    release_flow = "from interface import App; from main import install_ui, _validar_base_aplicacao; install_ui(App); _validar_base_aplicacao()"
    if release_flow not in release:
        fail("release.yml não usa o mesmo ponto de entrada consolidado da validação da main")
    for marker in BUILD_MARKERS:
        if marker not in build:
            fail(f"build_windows.bat não contém o metadado esperado: {marker}")


PRODUCTION_FILES = (
    "main.py",
    "interface.py",
    "app.py",
)


def _module_name(relative: str) -> str:
    return Path(relative).stem


def _local_imports(tree: ast.AST, local_modules: set[str]) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in local_modules:
                    imports.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".", 1)[0]
                if root in local_modules:
                    imports.add(root)
    return imports


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visiting: list[str] = []
    active: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            start = visiting.index(node)
            cycles.append(visiting[start:] + [node])
            return
        if node in visited:
            return
        active.add(node)
        visiting.append(node)
        for target in sorted(graph.get(node, ())):
            visit(target)
        visiting.pop()
        active.remove(node)
        visited.add(node)

    for node in sorted(graph):
        visit(node)
    return cycles


def validate_quality(root: Path) -> dict[str, object]:
    root = Path(root)
    trees: dict[str, ast.Module] = {}
    errors: list[str] = []
    local_modules = {
        _module_name(relative)
        for relative in PRODUCTION_FILES
        if (root / relative).exists()
    }

    for relative in PRODUCTION_FILES:
        path = root / relative
        if not path.exists():
            continue
        try:
            trees[_module_name(relative)] = ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
        except (OSError, SyntaxError) as exc:
            errors.append(f"{relative}: {exc}")

    graph: dict[str, set[str]] = {}
    for module, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if any(alias.name == "*" for alias in node.names):
                    errors.append(f"{module}: import wildcard não permitido")
            elif isinstance(node, ast.Import):
                if any(alias.name == "*" for alias in node.names):
                    errors.append(f"{module}: import wildcard não permitido")

        for class_node in (node for node in tree.body if isinstance(node, ast.ClassDef)):
            names: set[str] = set()
            for member in class_node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if member.name in names:
                        errors.append(
                            f"{module}.{class_node.name}: método duplicado {member.name}"
                        )
                    names.add(member.name)

        graph[module] = _local_imports(tree, local_modules)

    cycles = _find_cycles(graph)
    errors.extend(
        "ciclo de importação: " + " -> ".join(cycle)
        for cycle in cycles
        if len(cycle) > 1
    )

    if errors:
        raise ValueError("; ".join(errors))

    return {
        "modules": len(trees),
        "cycles": [],
        "checked_files": tuple(sorted(trees)),
    }

def parse_version(value: str) -> tuple[int, ...]:
    text = str(value).strip()
    if text.startswith(("v", "V")):
        text = text[1:]
    parts = text.split(".")
    if len(parts) not in (3, 4) or any(not part.isdigit() for part in parts):
        return ()
    return tuple(int(part) for part in parts)


def read_version(path: Path) -> tuple[int, ...]:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ValueError(f"Não foi possível ler VERSION: {exc}") from exc
    parsed = parse_version(value)
    if not parsed:
        raise ValueError(f"VERSION inválida: {value!r}")
    return parsed


def validate_version(current_path: Path, previous_path: Path | None = None) -> tuple[int, ...]:
    current = read_version(current_path)
    if previous_path is not None and previous_path.exists():
        previous = read_version(previous_path)
        if current < previous:
            raise ValueError(
                f"VERSION regrediu de {'.'.join(map(str, previous))} "
                f"para {'.'.join(map(str, current))}"
            )
    return current

MIN_EXECUTABLE_SIZE = 1_000_000


def validate_pe(path: Path, min_size: int = MIN_EXECUTABLE_SIZE) -> dict[str, object]:
    """Valida as propriedades mínimas de um executável PE sem executá-lo."""
    if not path.exists():
        raise ValueError(f"Executável não encontrado: {path}")

    size = path.stat().st_size
    if size < min_size:
        raise ValueError(
            f"Executável suspeitamente pequeno: {size} bytes < {min_size}"
        )

    with path.open("rb") as handle:
        header = handle.read(0x40)
        if len(header) < 0x40 or header[:2] != b"MZ":
            raise ValueError("Executável não possui assinatura MZ válida.")

        pe_offset = struct.unpack_from("<I", header, 0x3C)[0]
        if pe_offset < 0x40:
            raise ValueError(f"Offset PE inválido: {pe_offset}")

        handle.seek(pe_offset)
        signature = handle.read(4)
        if signature != b"PE\x00\x00":
            raise ValueError("Executável não possui assinatura PE válida.")

    return {"path": str(path), "size": size, "pe_offset": pe_offset}


def _cli_all(root: Path) -> int:
    validate_architecture(root)
    validate_version(root / "VERSION")
    validate_dependencies(root)
    validate_workflow_pins(root)
    validate_workflow_security(root)
    validate_quality(root)
    print("Validação consolidada: OK")
    return 0


def _cli_architecture(root: Path) -> int:
    validate_architecture(root)
    print("Validação de arquitetura consolidada: OK")
    return 0


def _cli_version(path: Path, previous: Path | None = None) -> int:
    parsed = validate_version(path, previous)
    print(f"VERSION válida: {'.'.join(map(str, parsed))}")
    return 0


def _cli_quality(root: Path) -> int:
    result = validate_quality(root)
    print(
        f"Qualidade estrutural: OK "
        f"({result['modules']} módulos, sem ciclos locais)."
    )
    return 0


def _cli_executable(path: Path, min_size: int = MIN_EXECUTABLE_SIZE) -> int:
    result = validate_pe(path, min_size)
    print(
        f"PE válido: {result['path']} "
        f"({result['size']} bytes, offset PE {result['pe_offset']})."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validação consolidada do SM AutoLab.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("all", help="Arquitetura, VERSION, dependências, workflows e qualidade.")

    subparsers.add_parser("architecture", help="Arquitetura e integração.")

    version_parser = subparsers.add_parser("version", help="Valida VERSION.")
    version_parser.add_argument("version_file", type=Path, nargs="?", default=Path("VERSION"))
    version_parser.add_argument("--previous", type=Path)

    subparsers.add_parser("quality", help="Qualidade estrutural.")

    executable_parser = subparsers.add_parser("executable", help="Valida um PE.")
    executable_parser.add_argument("executable", type=Path)
    executable_parser.add_argument("--min-size", type=int, default=MIN_EXECUTABLE_SIZE)

    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.command == "all":
        return _cli_all(root)
    if args.command == "architecture":
        return _cli_architecture(root)
    if args.command == "version":
        return _cli_version(args.version_file, args.previous)
    if args.command == "quality":
        return _cli_quality(root)
    return _cli_executable(args.executable, args.min_size)


if __name__ == "__main__":
    raise SystemExit(main())
