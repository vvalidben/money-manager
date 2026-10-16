"""Guards the layer boundaries.

core/domain  →  no Qt, no SQLAlchemy, no outer layers
ai           →  no Qt, no SQLAlchemy, no persistence / services (pure provider layer)
persistence  →  no Qt, no services, no UI
services     →  no Qt, no UI
ui           →  no persistence / SQLAlchemy (talks to services only)
"""

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "money_manager"

UI = ("PySide6", "money_manager.ui", "money_manager.app")
FORBIDDEN_IMPORTS = {
    "core": UI + ("sqlalchemy", "money_manager.domain", "money_manager.persistence",
                  "money_manager.services", "money_manager.ai"),
    "domain": UI + ("sqlalchemy", "money_manager.persistence", "money_manager.services",
                    "money_manager.ai"),
    "ai": UI + ("sqlalchemy", "money_manager.persistence", "money_manager.services"),
    "persistence": UI + ("money_manager.services", "money_manager.ai"),
    "services": UI,
    "ui": ("sqlalchemy", "money_manager.persistence"),
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_layer_respects_boundaries(layer: str) -> None:
    forbidden = FORBIDDEN_IMPORTS[layer]
    offenders = [
        f"{path.relative_to(PACKAGE_ROOT)} imports {module}"
        for path in (PACKAGE_ROOT / layer).rglob("*.py")
        for module in _imported_modules(path)
        if module.startswith(forbidden)
    ]

    assert offenders == []
