import importlib.util
import re
from pathlib import Path

import pytest
import yaml

from candronex_common.testing import verifier

ROOT = Path(__file__).resolve().parents[2]


def flask_routes(app) -> set[tuple[str, str]]:
    routes = set()
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static" or rule.rule == "/health" or rule.rule.endswith("/openapi.yaml"):
            continue
        path = re.sub(r"<[^>]+>", "{}", rule.rule)  # le nom du paramètre peut différer (snake/camel)
        routes |= {(path, m.lower()) for m in rule.methods - {"HEAD", "OPTIONS"}}
    return routes


def spec_routes(service: str) -> set[tuple[str, str]]:
    spec = yaml.safe_load((ROOT / "services" / service / "openapi.yaml").read_text(encoding="utf-8"))
    return {(re.sub(r"{[^}]+}", "{}", p), m) for p, ops in spec["paths"].items() for m in ops}


def apps():
    from drone_management.adapter.outbound.in_memory import InMemoryDroneRepository
    from drone_management.main import create_app as drone
    from service_ordering.catalog.adapter.outbound.persistence import InMemoryServiceSpecificationRepository
    from service_ordering.main import create_app as ordering
    from service_ordering.ordering.adapter.outbound.persistence import InMemoryServiceOrderRepository
    from slice_activation.adapter.outbound.persistence import InMemoryServiceInventory
    from slice_activation.adapter.outbound.scheduler import InlineActivationScheduler
    from slice_activation.main import create_app as activation
    return {
        "drone-management-service": drone(InMemoryDroneRepository(), verifier()),
        "service-ordering-service": ordering(InMemoryServiceOrderRepository(), InMemoryServiceSpecificationRepository(),
                                             object(), object(), verifier()),
        "slice-activation-service": activation(InMemoryServiceInventory(), object(), object(),
                                               InlineActivationScheduler(), verifier()),
    }


@pytest.mark.parametrize("service, app", apps().items())
def test_openapi_matches_the_implemented_routes(service, app):
    assert flask_routes(app) == spec_routes(service)


@pytest.mark.parametrize("service, app", apps().items())
def test_openapi_is_served_by_each_service(service, app):
    api = {"drone-management-service": "drone-management", "service-ordering-service": "service-ordering",
           "slice-activation-service": "slice-activation"}[service]
    r = app.test_client().get(f"/api/{api}/v1/openapi.yaml")
    assert r.status_code == 200 and yaml.safe_load(r.data)["openapi"].startswith("3.")


def test_gateway_contract_is_up_to_date_and_declares_oauth2():
    spec = importlib.util.spec_from_file_location("build_openapi", ROOT / "gateway/build_openapi.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert (ROOT / "gateway/openapi.yaml").read_text(encoding="utf-8") == module.render(), \
        "lancer python gateway/build_openapi.py"
    oauth = module.build()["components"]["securitySchemes"]["oauth2"]
    assert oauth["flows"]["clientCredentials"]["tokenUrl"].endswith("/realms/candronex/protocol/openid-connect/token")


@pytest.mark.parametrize("path", ["gateway/openapi.yaml", *[f"services/{s}/openapi.yaml" for s in (
    "drone-management-service", "service-ordering-service", "slice-activation-service")]])
def test_every_ref_resolves(path):
    text = (ROOT / path).read_text(encoding="utf-8")
    components = yaml.safe_load(text)["components"]
    for kind, name in re.findall(r"#/components/(\w+)/(\w+)", text):
        assert name in components.get(kind, {}), f"{path} : #/components/{kind}/{name} introuvable"


def test_internal_routes_are_not_exposed_by_the_gateway():
    import json
    gateway = json.loads((ROOT / "gateway/krakend.json").read_text(encoding="utf-8"))
    public = {(e["endpoint"], e["method"]) for e in gateway["endpoints"]}
    assert ("/api/slice-activation/v1/service", "POST") not in public
    assert not any(path.endswith("/networkIdentity") for path, _ in public)
