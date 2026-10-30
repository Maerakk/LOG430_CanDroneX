"""Scénario UC-02 -> UC-04 -> UC-06 par la passerelle. --failure : mock à 100 % d'échec."""
import os
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
ENV = dict(line.split("=", 1) for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines()
           if "=" in line and not line.startswith("#"))
TOKEN_URL = "http://localhost:8081/realms/candronex/protocol/openid-connect/token"
GW = f"http://localhost:{ENV.get('GATEWAY_PORT', '8080')}"
FAILURES = 0


def token(client_id: str) -> str:
    secret = ENV[client_id.split("-")[0].upper() + "_DEMO_SECRET"]
    r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials", "client_id": client_id,
                                       "client_secret": secret}, timeout=10)
    r.raise_for_status()
    return r.json()["access_token"]


def call(method: str, path: str, tok: str | None, body=None, **headers) -> requests.Response:
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return requests.request(method, GW + path, json=body, headers=headers, timeout=10)


def check(label: str, expected, actual) -> None:
    global FAILURES
    ok = expected == actual
    FAILURES += not ok
    print(f"  {'OK   ' if ok else 'ECHEC'}  {label:<60} {actual}" + ("" if ok else f"  (attendu {expected})"))


def compose(*args: str, **env: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=ROOT, env={**os.environ, **env}, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def main(failure: bool) -> int:
    if failure:
        print("== Relance de slice-activation-service avec MOCK_FAILURE_RATE=1")
        compose("up", "-d", "slice-activation-service", MOCK_FAILURE_RATE="1")
        time.sleep(4)

    print("== 1. Jetons OAuth2 client credentials auprès du Keycloak fourni")
    insp, aero = token("inspectra-demo"), token("aerotech-demo")
    print("  jetons obtenus pour inspectra-demo et aerotech-demo")

    n = random.randint(1_000_000, 9_999_999)
    drone = {"droneId": f"DRN-{n}", "imsi": f"30272000{n}", "iccid": f"893027200000{n}"}
    print(f"== 2. UC-02 : enregistrer le drone {drone['droneId']}")
    check("POST drone", 201, call("POST", "/api/drone-management/v1/drone", insp, drone).status_code)
    check("POST drone rejoué (même demande)", 200, call("POST", "/api/drone-management/v1/drone", insp, drone).status_code)
    check("POST drone sans jeton", 401, call("POST", "/api/drone-management/v1/drone", None, drone).status_code)
    check("POST drone jeton invalide", 401, call("POST", "/api/drone-management/v1/drone", "abc.def.ghi", drone).status_code)
    check("POST drone IMSI invalide (règle métier)", 422, call("POST", "/api/drone-management/v1/drone", insp, {
        "droneId": f"X-{n}", "imsi": "123", "iccid": "8930272000000000999"}).status_code)
    check("POST drone champ manquant (requête mal formée)", 400,
          call("POST", "/api/drone-management/v1/drone", insp, {"droneId": f"X-{n}"}).status_code)

    print("== 3. UC-04 : commander C2 / URLLC et Imagerie / eMBB")
    order = {"orderItem": [
        {"action": "add", "droneId": drone["droneId"], "service": {"serviceSpecification": {"id": "SPEC-C2-URLLC"}}},
        {"action": "add", "droneId": drone["droneId"], "service": {"serviceSpecification": {"id": "SPEC-IMAGERY-EMBB"}}}]}
    key = f"demo-{n}"
    created = call("POST", "/api/service-ordering/v1/serviceOrder", insp, order,
                   **{"Idempotency-Key": key, "X-Correlation-Id": key})
    check("POST commande", 201, created.status_code)
    order_id = created.json()["id"]
    replay = call("POST", "/api/service-ordering/v1/serviceOrder", insp, order, **{"Idempotency-Key": key})
    check("POST commande rejouée : même commande", (200, order_id), (replay.status_code, replay.json()["id"]))
    check("POST commande sans Idempotency-Key", 400,
          call("POST", "/api/service-ordering/v1/serviceOrder", insp, order).status_code)
    check("POST commande pour le drone d'un autre client", 404,
          call("POST", "/api/service-ordering/v1/serviceOrder", aero, order, **{"Idempotency-Key": key}).status_code)

    print("== 4. UC-06 : activation en arrière-plan (MockOpen5GSAdapter)")
    deadline = time.monotonic() + 15
    while True:
        o = call("GET", f"/api/service-ordering/v1/serviceOrder/{order_id}", insp).json()
        if o["state"] not in ("ACKNOWLEDGED", "IN_PROGRESS") or time.monotonic() > deadline:
            break
        time.sleep(0.3)
    check(f"état global de la commande {order_id}", "FAILED" if failure else "COMPLETED", o["state"])
    for item in o["orderItem"]:
        svc = call("GET", f"/api/slice-activation/v1/service/{item['service']['id']}", insp).json()
        check(f"service {svc['serviceSpecification']['id']} ({svc['id']})", "FAILED" if failure else "ACTIVE", svc["state"])
        if failure:
            print(f"         failureReason : {svc['failureReason']}")
        else:
            print(f"         acceptedAt -> activatedAt : "
                  f"{(parse(svc['activatedAt']) - parse(svc['acceptedAt'])).total_seconds() * 1000:.0f} ms")
    services = call("GET", f"/api/slice-activation/v1/service?orderId={order_id}", insp).json()
    check("inventaire : une seule association par élément", 2, len(services))
    check("nouvelle commande du même service " + ("en échec (permise)" if failure else "actif (refusée)"),
          201 if failure else 409, call("POST", "/api/service-ordering/v1/serviceOrder", insp, order,
                                        **{"Idempotency-Key": f"{key}-bis"}).status_code)

    print("== 5. Isolation entre clients")
    check("aerotech lit la commande d'inspectra", 404,
          call("GET", f"/api/service-ordering/v1/serviceOrder/{order_id}", aero).status_code)
    check("aerotech lit un service d'inspectra", 404,
          call("GET", f"/api/slice-activation/v1/service/{o['orderItem'][0]['service']['id']}", aero).status_code)
    check("aerotech lit le drone d'inspectra", 404,
          call("GET", f"/api/drone-management/v1/drone/{drone['droneId']}", aero).status_code)

    if failure:
        print("== Remise du mock a 0 % d'échec")
        compose("up", "-d", "slice-activation-service", MOCK_FAILURE_RATE="0")

    print(f"\nSuivre la commande dans les journaux : docker compose logs | grep {order_id}")
    print("Tous les cas sont conformes." if not FAILURES else f"{FAILURES} cas en échec.")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main("--failure" in sys.argv))
