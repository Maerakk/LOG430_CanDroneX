import threading
import time

import pytest
import requests
from werkzeug.serving import make_server

from candronex_common.testing import auth_headers, verifier
from drone_management.adapter.outbound.in_memory import InMemoryDroneRepository
from drone_management.main import create_app as drone_app
from service_ordering.catalog.adapter.outbound.persistence import InMemoryServiceSpecificationRepository
from service_ordering.catalog.domain.model import CharacteristicValue as CV, ServiceSpecification
from service_ordering.main import create_app as ordering_app
from service_ordering.ordering.adapter.outbound.http_clients import HttpDroneDirectory, HttpServiceActivation
from service_ordering.ordering.adapter.outbound.persistence import InMemoryServiceOrderRepository
from slice_activation.adapter.outbound.drone_identity_http import HttpDroneIdentityProvider
from slice_activation.adapter.outbound.mock_open5gs import MockOpen5GSAdapter
from slice_activation.adapter.outbound.persistence import InMemoryServiceInventory
from slice_activation.adapter.outbound.scheduler import ThreadPoolActivationScheduler
from slice_activation.main import create_app as activation_app


def characteristics(sst, sd, dnn, five_qi, arp, up, down):
    return (CV("sst", "integer", sst), CV("sd", "string", sd), CV("dnn", "string", dnn), CV("5qi", "integer", five_qi),
            CV("arp", "integer", arp), CV("ambrUplinkMbps", "integer", up), CV("ambrDownlinkMbps", "integer", down))


C2, IMG = "SPEC-C2-URLLC", "SPEC-IMAGERY-EMBB"
SPECS = [ServiceSpecification(C2, "C2 Connectivity", "URLLC", "active", characteristics(2, "000001", "c2", 82, 1, 20, 20)),
         ServiceSpecification(IMG, "Imagery Connectivity", "eMBB", "active",
                              characteristics(1, "000002", "imagery", 9, 8, 100, 500))]


class Server:
    def __init__(self, app):
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()


def stack(failure_rate=0.0):
    drones = Server(drone_app(InMemoryDroneRepository(), verifier()))
    network = MockOpen5GSAdapter(5, 30, failure_rate, 0)
    inventory = InMemoryServiceInventory()
    activation = Server(activation_app(inventory, network, HttpDroneIdentityProvider(drones.url),
                                       ThreadPoolActivationScheduler(8), verifier()))
    ordering = Server(ordering_app(InMemoryServiceOrderRepository(), InMemoryServiceSpecificationRepository(SPECS),
                                   HttpDroneDirectory(drones.url), HttpServiceActivation(activation.url), verifier()))
    return {"drones": drones, "activation": activation, "ordering": ordering, "network": network,
            "inventory": inventory}


@pytest.fixture
def ok_stack():
    s = stack()
    yield s
    for name in ("drones", "activation", "ordering"):
        s[name].stop()


@pytest.fixture
def failing_stack():
    s = stack(failure_rate=1.0)  # taux d'échec forcé à 100 %
    yield s
    for name in ("drones", "activation", "ordering"):
        s[name].stop()


DRONE = {"droneId": "DRN-0231", "imsi": "302720000010231", "iccid": "8930272000000010231"}
ORDER = {"orderItem": [{"action": "add", "droneId": "DRN-0231", "service": {"serviceSpecification": {"id": C2}}},
                       {"action": "add", "droneId": "DRN-0231", "service": {"serviceSpecification": {"id": IMG}}}]}


def register_and_order(s, key="order-1", client="inspectra-demo"):
    r = requests.post(f"{s['drones'].url}/api/drone-management/v1/drone", json=DRONE, headers=auth_headers(client))
    assert r.status_code in (200, 201)
    return requests.post(f"{s['ordering'].url}/api/service-ordering/v1/serviceOrder", json=ORDER,
                         headers=auth_headers(client, **{"Idempotency-Key": key, "X-Correlation-Id": "it-1"}))


def wait_for_final_state(s, order_id, client="inspectra-demo", timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        order = requests.get(f"{s['ordering'].url}/api/service-ordering/v1/serviceOrder/{order_id}",
                             headers=auth_headers(client)).json()
        if order["state"] not in ("ACKNOWLEDGED", "IN_PROGRESS"):
            return order
        time.sleep(0.05)
    raise AssertionError("order did not reach a final state")


def test_order_with_c2_and_imagery_reaches_active(ok_stack):
    r = register_and_order(ok_stack)
    assert r.status_code == 201
    assert all(item["service"]["id"] for item in r.json()["orderItem"])
    order = wait_for_final_state(ok_stack, r.json()["id"])
    assert order["state"] == "COMPLETED"
    assert [i["state"] for i in order["orderItem"]] == ["ACTIVE", "ACTIVE"]
    assert len(ok_stack["network"].applied) == 2


def test_forced_failure_leads_to_failed_without_inconsistent_state(failing_stack):
    r = register_and_order(failing_stack)
    order = wait_for_final_state(failing_stack, r.json()["id"])
    assert order["state"] == "FAILED" and [i["state"] for i in order["orderItem"]] == ["FAILED", "FAILED"]
    services = requests.get(f"{failing_stack['activation'].url}/api/slice-activation/v1/service",
                            params={"orderId": r.json()["id"]}, headers=auth_headers()).json()
    assert all(s["state"] == "FAILED" and s["activatedAt"] is None and s["failureReason"] for s in services)
    assert failing_stack["network"].applied == {}


def test_replayed_order_creates_no_duplicate_anywhere(ok_stack):
    first = register_and_order(ok_stack)
    wait_for_final_state(ok_stack, first.json()["id"])
    replay = register_and_order(ok_stack)
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]
    assert len(ok_stack["inventory"].services) == 2       # pas de deuxième association slice <-> drone
    assert ok_stack["network"].apply_calls == 2           # pas de configuration réseau en double


def test_new_order_for_an_active_service_is_refused(ok_stack):
    first = register_and_order(ok_stack)
    wait_for_final_state(ok_stack, first.json()["id"])
    again = register_and_order(ok_stack, key="order-2")
    assert again.status_code == 409


def test_calls_without_a_valid_token_are_refused_by_every_service(ok_stack):
    for url in (f"{ok_stack['drones'].url}/api/drone-management/v1/drone",
                f"{ok_stack['ordering'].url}/api/service-ordering/v1/serviceOrder/SO-x",
                f"{ok_stack['activation'].url}/api/slice-activation/v1/service"):
        assert requests.get(url).status_code == 401
        assert requests.get(url, headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_other_client_cannot_reach_the_order_nor_its_services(ok_stack):
    order_id = register_and_order(ok_stack).json()["id"]
    r = requests.get(f"{ok_stack['ordering'].url}/api/service-ordering/v1/serviceOrder/{order_id}",
                     headers=auth_headers("aerotech-demo"))
    assert r.status_code == 404 and r.headers["Content-Type"] == "application/problem+json"
    services = requests.get(f"{ok_stack['activation'].url}/api/slice-activation/v1/service",
                            params={"orderId": order_id}, headers=auth_headers("aerotech-demo")).json()
    assert services == []


def test_order_for_a_drone_of_another_client_is_404(ok_stack):
    register_and_order(ok_stack)
    r = requests.post(f"{ok_stack['ordering'].url}/api/service-ordering/v1/serviceOrder", json=ORDER,
                      headers=auth_headers("aerotech-demo", **{"Idempotency-Key": "k"}))
    assert r.status_code == 404


def test_unavailable_drone_service_gives_503_problem(ok_stack):
    ok_stack["drones"].stop()
    r = requests.post(f"{ok_stack['ordering'].url}/api/service-ordering/v1/serviceOrder", json=ORDER,
                      headers=auth_headers(**{"Idempotency-Key": "k"}))
    assert r.status_code == 503 and r.json()["type"].endswith("/service-unavailable")
