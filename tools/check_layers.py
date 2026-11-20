"""
Reads every .py file without running it and reports the following:
- Layer stack violations - an import from a higher layer, or from another package in the same layer.
- Import cycles between modules (top-level imports only).
- `if TYPE_CHECKING:` blocks.
- Imports of project modules inside functions, other than the allowed ones in ALLOWED_FUNCTION_IMPORTS.

Exits with 1 when it finds anything.

Usage:
    uv run python tools/check_layers.py          # checks src/ next to this tools/ folder
    uv run python tools/check_layers.py path/to/src
"""

import ast
import sys
from pathlib import Path

# Keep in sync with the layer table in architecture.md
LAYERS = {
    "core": 0,
    "logger": 1,
    "utils": 1,
    "patchers": 2,
    "stores": 2,
    "updater": 2,
    "remote_messages": 2,
    "patch_patterns": 2,
    "app": 3,
    "ui": 4,
    "main": 5,
    "cli": 5,
}
ENTRY_POINT_LAYER = 5  # main.py and cli.py sit on top and may import anything

# (importing module, imported module) pairs allowed inside a function, each for a startup-order reason
ALLOWED_FUNCTION_IMPORTS = {
    ("main", "ui"),  # Loaded after `start()`, so --no-conn gets setup before `requests` loads
}

DEFAULT_SRC = Path(__file__).resolve().parent.parent / "src"


def find_modules(src: Path) -> dict[str, Path]:
    """
    {dot module name: file} for every .py file in `src`.

    A package's __init__.py is the package itself.
    """
    modules = {}

    for file_path in src.rglob("*.py"):
        if "__pycache__" in file_path.parts:
            continue

        parts = list(file_path.relative_to(src).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]

        modules[".".join(parts)] = file_path

    return modules


def imported_modules(node: ast.AST, module_name: str, is_package: bool, modules: dict[str, Path]) -> list[str]:
    """
    Dot names of what an import brings in.
    `from pkg import sub` counts as importing the submodule `pkg.sub` when it is one, otherwise count as `pkg` itself.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    if node.level == 0:
        target = node.module
    else:
        # Relative import. Start from this module's package and go up one level per extra dot
        base = module_name.split(".")
        if not is_package:
            base = base[:-1]
        if node.level > 1:
            base = base[: len(base) - (node.level - 1)]
        if node.module:
            base = base + [node.module]
        target = ".".join(base)

    names = []
    for alias in node.names:
        submodule = f"{target}.{alias.name}"
        if submodule in modules:
            name = submodule
        else:
            name = target

        # `from pkg import a, b` imports `pkg` once
        if name not in names:
            names.append(name)
    return names


def node_ids_inside(nodes: list[ast.AST]) -> set[int]:
    """ids of every node inside `nodes. Check later if an import is in one of them."""
    ids = set()
    for node in nodes:
        for child in ast.walk(node):
            ids.add(id(child))
    return ids


def layer_of(module_name: str) -> int:
    return LAYERS[module_name.split(".")[0]]


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Groups of modules that import each other, directly or through others (Tarjan algorithm)."""
    index_of = {}
    lowest_reachable = {}
    stack = []
    on_stack = set()
    cycles = []

    def visit(module: str) -> None:
        index_of[module] = len(index_of)
        lowest_reachable[module] = index_of[module]
        stack.append(module)
        on_stack.add(module)

        for imported in graph.get(module, set()):
            if imported not in graph:
                continue
            if imported not in index_of:
                visit(imported)
                lowest_reachable[module] = min(lowest_reachable[module], lowest_reachable[imported])
            elif imported in on_stack:
                lowest_reachable[module] = min(lowest_reachable[module], index_of[imported])

        # `module` = first found of a group. Take while group off the stack.
        if lowest_reachable[module] == index_of[module]:
            group = []
            while True:
                member = stack.pop()
                on_stack.discard(member)
                group.append(member)
                if member == module:
                    break
            if len(group) > 1:
                cycles.append(sorted(group))

    sys.setrecursionlimit(10000)
    for module in graph:
        if module not in index_of:
            visit(module)

    return cycles


def check(src: Path) -> bool:
    """Print every problem found in `src`. True when no problems."""
    modules = find_modules(src)
    violations = []
    type_checking_blocks = []
    function_imports = []
    graph = {}

    for module_name, file_path in modules.items():
        tree = ast.parse(file_path.read_text(encoding="utf-8-sig"))
        is_package = file_path.name == "__init__.py"

        type_checking_nodes = []
        function_nodes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test):
                type_checking_nodes.append(node)
                type_checking_blocks.append(f"{module_name}:{node.lineno}")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_nodes.append(node)

        inside_type_checking = node_ids_inside(type_checking_nodes)
        inside_functions = node_ids_inside(function_nodes)

        top_level_imports = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue

            for imported in imported_modules(node, module_name, is_package, modules):
                imported_package = imported.split(".")[0]
                if imported_package not in LAYERS:
                    continue  # Standard library or a dependency

                own_package = module_name.split(".")[0]
                is_other_package = own_package != imported_package
                is_entry_point = layer_of(module_name) == ENTRY_POINT_LAYER
                if is_other_package and not is_entry_point and layer_of(imported) >= layer_of(module_name):
                    violations.append(
                        f"{module_name}:{node.lineno} imports {imported} "
                        f"(layer {layer_of(imported)} from layer {layer_of(module_name)})"
                    )

                if id(node) in inside_functions:
                    if (module_name, imported) not in ALLOWED_FUNCTION_IMPORTS:
                        function_imports.append(f"{module_name}:{node.lineno} imports {imported}")
                elif id(node) not in inside_type_checking:
                    top_level_imports.add(imported)

        graph[module_name] = top_level_imports

    cycles = find_cycles(graph)

    _print_section("Layer violations", violations)
    _print_section("Import cycles", [" <-> ".join(cycle) for cycle in cycles])
    _print_section("TYPE_CHECKING blocks", type_checking_blocks)
    _print_section("Project imports inside functions", function_imports)

    found_problems = violations or cycles or type_checking_blocks or function_imports
    return not found_problems


def _print_section(title: str, lines: list[str]) -> None:
    print(f"{title}:")
    if not lines:
        print("  none")
    for line in lines:
        print(f"  {line}")


def main() -> int:
    if len(sys.argv) > 1:
        src = Path(sys.argv[1])
    else:
        src = DEFAULT_SRC

    if not src.is_dir():
        print(f"Not a folder: {src}")
        return 1

    if check(src):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
