from datetime import datetime, timedelta, timezone

import pytest

from candronex_common.errors import InvalidValueError
from candronex_common.testing import auth_headers, verifier
from slice_activation.adapter.outbound.mock_open5gs import MockOpen5GSAdapter
from slice_activation.adapter.outbound.persistence import InMemoryServiceInventory
from slice_activation.adapter.outbound.scheduler import InlineActivationScheduler
from slice_activation.application.use_cases import ActivateService, RequestActivation
from slice_activation.domain.port.inbound import ActivationCommand
from slice_activation.domain.errors import DroneNotFoundError, OrderItemConflictError
from slice_activation.domain.model import Characteristic, InvalidTransitionError, Service, ServiceState
from slice_activation.domain.port.outbound import (DroneIdentityProvider, NetworkIdentity, NetworkProvisioningPort,
                                                   ProvisioningTimeout)
from slice_activation.main import create_app

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc)
C2_CHARS = (Characteristic("sliceType", "string", "URLLC"), Characteristic("sst", "integer", 2),
            Characteristic("sd", "string", "000001"), Characteristic("dnn", "string", "c2"),
            Characteristic("5qi", "integer", 82), Characteristic("arp", "integer", 1),
            Characteristic("ambrUplinkMbps", "integer", 20), Characteristic("ambrDownlinkMbps", "integer", 20))


class FakeDrones(DroneIdentityProvider):
    def network_identity(self, drone_id, client_id):
        if (drone_id, client_id) == ("DRN-0231", "inspectra-demo"):
            return NetworkIdentity(drone_id, "302720000010231", True)
        return None


def command(item="SO-1-1", client="inspectra-demo", drone="DRN-0231"):
    return ActivationCommand(client, "SO-1", item, drone, "SPEC-C2-URLLC", C2_CHARS, NOW)


def build(network: NetworkProvisioningPort):
    inventory, scheduler = InMemoryServiceInventory(), InlineActivationScheduler()
    scheduler.activate = ActivateService(inventory, network, max_attempts=3, clock=lambda: NOW + timedelta(seconds=1)).execute
    return inventory, RequestActivation(inventory, FakeDrones(), scheduler)


def mock(**kwargs):
    return MockOpen5GSAdapter(**{"latency_min_ms": 0, "latency_max_ms": 0, "failure_rate": 0, "timeout_rate": 0,
                                 "sleep": lambda s: None, **kwargs})


def test_service_lifecycle():
    s = Service.request("c", "SO-1", "SO-1-1", "D", "302720000010231", "S", C2_CHARS, NOW)
    assert s.state == ServiceState.PENDING
    s.start_activation()
    s.activate(NOW)
    assert s.state == ServiceState.ACTIVE and s.activated_at == NOW
    with pytest.raises(InvalidTransitionError):
        s.start_activation()


def test_configuration_without_snssai_is_refused():
    with pytest.raises(InvalidValueError):
        Service.request("c", "SO-1", "SO-1-1", "D", "302720000010231", "S", C2_CHARS[:1], NOW)


def test_activation_succeeds():
    network = mock()
    inventory, request = build(network)
    service, created = request.execute(command())
    stored = inventory.get_by_id(service.service_id)
    assert created and stored.state == ServiceState.ACTIVE
    assert stored.activated_at - stored.accepted_at == timedelta(seconds=1)
    assert list(network.applied) == [service.service_id]


def test_activation_fails_when_the_network_rejects_it():
    inventory, request = build(mock(failure_rate=1.0))
    service, _ = request.execute(command())
    stored = inventory.get_by_id(service.service_id)
    assert stored.state == ServiceState.FAILED and stored.failure_reason.startswith("NETWORK_REJECTED")
    assert stored.activated_at is None


def test_timeout_is_indeterminate_and_retried_before_failing():
    network = mock(timeout_rate=1.0)
    inventory, request = build(network)
    service, _ = request.execute(command())
    stored = inventory.get_by_id(service.service_id)
    assert network.apply_calls == 3 and stored.attempts == 3
    assert stored.state == ServiceState.UNKNOWN and stored.failure_reason == "NETWORK_TIMEOUT"


def test_timeout_then_success_becomes_active():
    class Flaky(NetworkProvisioningPort):
        calls = 0

        def apply(self, configuration):
            self.calls += 1
            if self.calls == 1:
                raise ProvisioningTimeout()

    inventory, request = build(Flaky())
    service, _ = request.execute(command())
    assert inventory.get_by_id(service.service_id).state == ServiceState.ACTIVE


def test_replayed_request_creates_neither_a_second_service_nor_a_second_configuration():
    network = mock()
    inventory, request = build(network)
    first, _ = request.execute(command())
    again, created = request.execute(command())
    assert not created and again.service_id == first.service_id
    assert len(inventory.services) == 1 and network.apply_calls == 1


def test_same_order_item_for_another_drone_is_a_conflict():
    _, request = build(mock())
    request.execute(command())
    with pytest.raises(OrderItemConflictError):
        request.execute(command(drone="DRN-9999"))


def test_drone_of_another_client_is_not_found():
    _, request = build(mock())
    with pytest.raises(DroneNotFoundError):
        request.execute(command(client="aerotech-demo"))


def test_two_workers_cannot_activate_the_same_service():
    network = mock()
    inventory = InMemoryServiceInventory()
    service = Service.request("c", "SO-1", "SO-1-1", "D", "302720000010231", "S", C2_CHARS, NOW)
    inventory.add(service)
    worker = ActivateService(inventory, network)
    worker.execute(service.service_id)
    worker.execute(service.service_id)
    assert network.apply_calls == 1


def test_mock_latency_is_within_the_configured_bounds():
    slept = []
    network = MockOpen5GSAdapter(300, 1500, 0, 0, sleep=slept.append)
    for i in range(200):
        network.apply(Service.request("c", "O", f"I{i}", "D", "302720000010231", "S", C2_CHARS, NOW)
                      .network_configuration())
    assert all(0.3 <= s <= 1.5 for s in slept) and max(slept) - min(slept) > 0.5


def test_mock_reads_its_parameters_from_the_environment(monkeypatch):
    monkeypatch.setenv("MOCK_LATENCY_MIN_MS", "10")
    monkeypatch.setenv("MOCK_LATENCY_MAX_MS", "20")
    monkeypatch.setenv("MOCK_FAILURE_RATE", "1")
    network = MockOpen5GSAdapter()
    assert (network.latency_min_ms, network.latency_max_ms, network.failure_rate) == (10, 20, 1)


def test_mock_refuses_an_invalid_configuration():
    with pytest.raises(ValueError):
        MockOpen5GSAdapter(1500, 300, 0, 0)


@pytest.fixture
def client():
    scheduler = InlineActivationScheduler()
    app = create_app(InMemoryServiceInventory(), mock(), FakeDrones(), scheduler, verifier())
    return app.test_client()


URL = "/api/slice-activation/v1/service"
BODY = {"orderId": "SO-1", "orderItemId": "SO-1-1", "droneId": "DRN-0231",
        "serviceSpecification": {"id": "SPEC-C2-URLLC"}, "acceptedAt": "2026-10-29T12:00:00.000Z",
        "serviceCharacteristic": [{"name": c.name, "valueType": c.value_type, "value": c.value} for c in C2_CHARS]}


def test_rest_request_202_replay_200_and_imsi_never_returned(client):
    first = client.post(URL, json=BODY, headers=auth_headers())
    assert first.status_code == 202
    assert client.post(URL, json=BODY, headers=auth_headers()).status_code == 200
    r = client.get(f"{URL}/{first.json['id']}", headers=auth_headers())
    assert r.json["state"] == "ACTIVE" and r.json["activatedAt"]
    assert "302720000010231" not in r.get_data(as_text=True)


def test_rest_other_client_sees_nothing(client):
    service_id = client.post(URL, json=BODY, headers=auth_headers()).json["id"]
    assert client.get(f"{URL}/{service_id}", headers=auth_headers("aerotech-demo")).status_code == 404
    assert client.get(URL, query_string={"orderId": "SO-1"}, headers=auth_headers("aerotech-demo")).json == []


def test_rest_without_token_is_401(client):
    assert client.post(URL, json=BODY).status_code == 401


def test_rest_malformed_date_is_400(client):
    assert client.post(URL, json={**BODY, "acceptedAt": "hier"}, headers=auth_headers()).status_code == 400
