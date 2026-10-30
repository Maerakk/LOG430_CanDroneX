"""Génère gateway/openapi.yaml à partir des contrats des services et des routes de krakend.json."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SERVICES = {"drone-management-service": "Drone_", "service-ordering-service": "Ordering_",
            "slice-activation-service": "Activation_"}
TOKEN_URL = "http://localhost:8081/realms/candronex/protocol/openid-connect/token"


SERVICE_BY_API = {"drone-management": "drone-management-service", "service-ordering": "service-ordering-service",
                  "service-catalog": "service-ordering-service", "slice-activation": "slice-activation-service"}


def public_routes() -> dict[tuple[str, str], str]:
    gateway = json.loads((ROOT / "gateway/krakend.json").read_text(encoding="utf-8"))
    return {(e["endpoint"], e["method"].lower()): SERVICE_BY_API[e["endpoint"].split("/")[2]]
            for e in gateway["endpoints"] if "auth/validator" in e.get("extra_config", {})}


def build() -> dict:
    routes = public_routes()
    spec = {
        "openapi": "3.0.3",
        "info": {"title": "CanDroneX API publique (passerelle)", "version": "1.0.0",
                 "description": "Point d'entrée unique des clients B2B. Le jeton s'obtient en OAuth2 client credentials "
                                "auprès du Keycloak fourni (realm candronex, audience candronex-api). "
                                "La passerelle transmet l'en-tête Authorization sans le modifier, et chaque "
                                "microservice vérifie le jeton puis filtre les données par la claim azp."},
        "servers": [{"url": "http://localhost:8080", "description": "API Gateway (KrakenD)"}],
        "security": [{"oauth2": []}],
        "paths": {},
        "components": {"securitySchemes": {"oauth2": {
            "type": "oauth2", "description": "Flux client credentials, sans utilisateur humain.",
            "flows": {"clientCredentials": {"tokenUrl": TOKEN_URL, "scopes": {}}}}},
            "schemas": {}, "parameters": {}, "responses": {}},
    }
    for service, prefix in SERVICES.items():
        text = (ROOT / "services" / service / "openapi.yaml").read_text(encoding="utf-8")
        for kind in ("schemas", "parameters", "responses"):
            text = text.replace(f"#/components/{kind}/", f"#/components/{kind}/{prefix}")
        source = yaml.safe_load(text)
        for kind in ("schemas", "parameters", "responses"):
            for name, value in source["components"].get(kind, {}).items():
                spec["components"][kind][prefix + name] = value
        for path, operations in source["paths"].items():
            for method, operation in operations.items():
                if routes.get((path, method)) == service:
                    operation = {**operation, "tags": [service]}
                    operation.pop("security", None)
                    spec["paths"].setdefault(path, {})[method] = operation
    missing = set(routes) - {(p, m) for p, ops in spec["paths"].items() for m in ops}
    if missing:
        raise SystemExit(f"Routes de la passerelle absentes des contrats : {sorted(missing)}")
    return spec


def render() -> str:
    return "# Généré par gateway/build_openapi.py, ne pas modifier à la main.\n" + \
        yaml.safe_dump(build(), sort_keys=False, allow_unicode=True, width=120)


if __name__ == "__main__":
    (ROOT / "gateway/openapi.yaml").write_text(render(), encoding="utf-8")
    print("gateway/openapi.yaml regenere")
