"""Règles de dépendance de l'architecture hexagonale, vérifiées sur le code (comme ArchUnit dans le cours)."""
import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = [ROOT / "services/drone-management-service/drone_management",
            ROOT / "services/service-ordering-service/service_ordering/ordering",
            ROOT / "services/service-ordering-service/service_ordering/catalog",
            ROOT / "services/slice-activation-service/slice_activation"]
FRAMEWORKS = {"flask", "werkzeug", "sqlalchemy", "pymysql", "requests", "jwt", "gunicorn"}


def imports(folder: Path) -> list[tuple[str, str]]:
    found = []
    for file in folder.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                found += [(file.name, alias.name) for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.append((file.name, node.module))
    return found


@pytest.mark.parametrize("package", PACKAGES, ids=lambda p: p.name)
def test_domain_depends_on_no_framework_and_no_adapter(package):
    for file, module in imports(package / "domain"):
        assert module.split(".")[0] not in FRAMEWORKS, f"{file} importe {module}"
        assert ".adapter" not in module and ".application" not in module, f"{file} importe {module}"
        assert module.split(".")[0] != "candronex_common" or module == "candronex_common.errors", \
            f"{file} importe {module}"


@pytest.mark.parametrize("package", PACKAGES, ids=lambda p: p.name)
def test_application_depends_on_no_framework_and_no_adapter(package):
    for file, module in imports(package / "application"):
        assert module.split(".")[0] not in FRAMEWORKS, f"{file} importe {module}"
        assert ".adapter" not in module, f"{file} importe {module}"


def test_services_do_not_import_each_other():
    names = {"drone_management", "service_ordering", "slice_activation"}
    for service_dir in (ROOT / "services").iterdir():
        for package in [p for p in service_dir.iterdir() if p.name in names]:
            for file, module in imports(package):
                other = module.split(".")[0]
                assert other not in names - {package.name}, f"{package.name}/{file} importe {module}"
