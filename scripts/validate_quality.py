from __future__ import annotations

import ast
from pathlib import Path


PRODUCTION_FILES = (
    "main.py",
    "interface.py",
    "app.py",
    "automacao.py",
    "patch.py",
    "atualizacao.py",
    "ui_platform.py",
    "planilha_core.py",
    "storage_safe.py",
    "planilha_virtual_29926.py",
    "windows11_native_29925.py",
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


def main() -> int:
    result = validate_quality(Path("."))
    print(
        f"Qualidade estrutural: OK "
        f"({result['modules']} módulos, sem ciclos locais)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
