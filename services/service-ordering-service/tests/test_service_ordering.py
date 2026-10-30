import pytest

from candronex_common.errors import ServiceUnavailableError
from candronex_common.testing import auth_headers, verifier
from service_ordering.catalog.adapter.outbound.persistence import InMemoryServiceSpecificationRepository
from service_ordering.catalog.application.queries import CatalogQueries
from service_ordering.catalog.domain.model import CharacteristicValue, ServiceSpecification
from service_ordering.main import create_app
from service_ordering.ordering.adapter.outbound.catalog_in_process import InProcessServiceCatalog
from service_ordering.ordering.adapter.outbound.persistence import InMemoryServiceOrderRepository
from service_ordering.ordering.application.use_cases import ActivationTracker, GetServiceOrder, PlaceServiceOrder
from service_ordering.ordering.domain.errors import (DroneNotEligibleError, DroneNotFoundError,
                                                     IdempotencyKeyConflictError, InvalidOrderError,
                                                     ServiceAlreadyOrderedError, UnknownServiceSpecificationError)
from service_ordering.ordering.domain.model import ItemRequest
from service_ordering.ordering.domain.port.outbound import (ActivationStatus, DroneDirectory, DroneReference,
                                                            ServiceActivation)
from service_ordering.ordering.domain.states import ItemState, OrderState, compute_order_state

C2, IMG = "SPEC-C2-URLLC", "SPEC-IMAGERY-EMBB"
SPECS = [
    ServiceSpecification(C2, "C2 Connectivity", "URLLC", "active", (CharacteristicValue("sst", "integer", 2),)),
    ServiceSpecification(IMG, "Imagery Connectivity", "eMBB", "active", (CharacteristicValue("sst", "integer", 1),)),
    ServiceSpecification("SPEC-OLD", "Retired offer", "eMBB", "retired", ()),
]


class FakeDrones(DroneDirectory):
    def __init__(self):
        self.drones = {("DRN-0231", "inspectra-demo"): True, ("DRN-OFF", "inspectra-demo"): False}

    def find(self, drone_id, client_id):
        eligible = self.drones.get((drone_id, client_id))
        return None if eligible is None else DroneReference(drone_id, eligible)


class FakeActivation(ServiceActivation):
    def __init__(self):
        self.services: dict[str, ActivationStatus] = {}
        self.available = True

    def request_activation(self, request):
        if not self.available:
            raise ServiceUnavailableError("down")
        return self.services.setdefault(request.order_item_id, ActivationStatus(
            f"SVC-{request.order_item_id}", request.order_item_id, ItemState.PENDING))

    def statuses(self, order_id):
        if not self.available:
            raise ServiceUnavailableError("down")
        return [s for s in self.services.values() if s.order_item_id.startswith(order_id)]

    def finish(self, state: ItemState):
        self.services = {k: ActivationStatus(v.service_id, k, state) for k, v in self.services.items()}


def both(drone="DRN-0231"):
    return [ItemRequest("add", drone, C2), ItemRequest("add", drone, IMG)]


@pytest.fixture
def ctx():
    orders, activation = InMemoryServiceOrderRepository(), FakeActivation()
    tracker = ActivationTracker(activation, orders)
    catalog = InProcessServiceCatalog(CatalogQueries(InMemoryServiceSpecificationRepository(SPECS)))
    return {"place": PlaceServiceOrder(orders, FakeDrones(), catalog, tracker),
            "get": GetServiceOrder(orders, tracker), "activation": activation, "orders": orders}


@pytest.mark.parametrize("states, expected", [
    ([ItemState.PENDING, ItemState.PENDING], OrderState.ACKNOWLEDGED),
    ([ItemState.ACTIVATING, ItemState.PENDING], OrderState.IN_PROGRESS),
    ([ItemState.ACTIVE, ItemState.ACTIVATING], OrderState.IN_PROGRESS),
    ([ItemState.ACTIVE, ItemState.ACTIVE], OrderState.COMPLETED),
    ([ItemState.ACTIVE, ItemState.FAILED], OrderState.PARTIALLY_COMPLETED),
    ([ItemState.FAILED, ItemState.FAILED], OrderState.FAILED),
    ([ItemState.ACTIVE, ItemState.UNKNOWN], OrderState.IN_PROGRESS),
    ([ItemState.CANCELLED, ItemState.CANCELLED], OrderState.CANCELLED),
])
def test_order_state_is_derived_from_items(states, expected):
    assert compute_order_state(states) == expected


def test_order_with_two_services_requests_their_activation(ctx):
    order, created = ctx["place"].execute("inspectra-demo", "key-1", both())
    assert created and order.state == OrderState.ACKNOWLEDGED
    assert all(i.activation_requested for i in order.items)
    c2 = order.items[0].service
    assert c2.specification_name == "C2 Connectivity"
    assert ("sliceType", "URLLC") in {(c.name, c.value) for c in c2.characteristics}


def test_replay_returns_the_same_order_without_duplicate(ctx):
    first, _ = ctx["place"].execute("inspectra-demo", "key-1", both())
    again, created = ctx["place"].execute("inspectra-demo", "key-1", list(reversed(both())))
    assert not created and again.order_id == first.order_id
    assert len(ctx["orders"].orders) == 1 and len(ctx["activation"].services) == 2


def test_same_key_for_another_request_is_a_conflict(ctx):
    ctx["place"].execute("inspectra-demo", "key-1", both())
    with pytest.raises(IdempotencyKeyConflictError):
        ctx["place"].execute("inspectra-demo", "key-1", both()[:1])


def test_same_key_from_another_client_is_another_order(ctx):
    ctx["place"].execute("inspectra-demo", "key-1", both())
    with pytest.raises(DroneNotFoundError):  # et pas un rejeu : la clé est propre à chaque client
        ctx["place"].execute("aerotech-demo", "key-1", both())


@pytest.mark.parametrize("requests", [
    [], [ItemRequest("delete", "DRN-0231", C2)],
    [ItemRequest("add", "DRN-0231", C2), ItemRequest("add", "DRN-OTHER", IMG)],
    [ItemRequest("add", "DRN-0231", C2), ItemRequest("add", "DRN-0231", C2)],
])
def test_invalid_orders_are_refused(ctx, requests):
    with pytest.raises(InvalidOrderError):
        ctx["place"].execute("inspectra-demo", "key-1", requests)


def test_unknown_or_retired_offer_is_refused(ctx):
    for spec in ("C2", "SPEC-OLD"):
        with pytest.raises(UnknownServiceSpecificationError):
            ctx["place"].execute("inspectra-demo", f"key-{spec}", [ItemRequest("add", "DRN-0231", spec)])


def test_drone_of_another_client_and_ineligible_drone(ctx):
    with pytest.raises(DroneNotFoundError):
        ctx["place"].execute("aerotech-demo", "key-1", both())
    with pytest.raises(DroneNotEligibleError):
        ctx["place"].execute("inspectra-demo", "key-2", both("DRN-OFF"))


@pytest.mark.parametrize("state", [ItemState.PENDING, ItemState.ACTIVE, ItemState.UNKNOWN])
def test_service_in_progress_or_active_blocks_a_new_order(ctx, state):
    order, _ = ctx["place"].execute("inspectra-demo", "key-1", both())
    ctx["activation"].finish(state)
    ctx["get"].execute(order.order_id, "inspectra-demo")
    with pytest.raises(ServiceAlreadyOrderedError):
        ctx["place"].execute("inspectra-demo", "key-2", both()[:1])


def test_failed_service_can_be_ordered_again(ctx):
    order, _ = ctx["place"].execute("inspectra-demo", "key-1", both())
    ctx["activation"].finish(ItemState.FAILED)
    assert ctx["get"].execute(order.order_id, "inspectra-demo").state == OrderState.FAILED
    _, created = ctx["place"].execute("inspectra-demo", "key-2", both()[:1])
    assert created


def test_order_follows_the_service_states(ctx):
    order, _ = ctx["place"].execute("inspectra-demo", "key-1", both())
    ctx["activation"].finish(ItemState.ACTIVE)
    assert ctx["get"].execute(order.order_id, "inspectra-demo").state == OrderState.COMPLETED


def test_activation_unavailable_keeps_the_order_and_retries_later(ctx):
    ctx["activation"].available = False
    order, created = ctx["place"].execute("inspectra-demo", "key-1", both())
    assert created and not any(i.activation_requested for i in order.items)
    ctx["activation"].available = True
    order = ctx["get"].execute(order.order_id, "inspectra-demo")
    assert all(i.activation_requested for i in order.items)


def test_other_client_cannot_read_the_order(ctx):
    from service_ordering.ordering.domain.errors import OrderNotFoundError
    order, _ = ctx["place"].execute("inspectra-demo", "key-1", both())
    with pytest.raises(OrderNotFoundError):
        ctx["get"].execute(order.order_id, "aerotech-demo")


@pytest.fixture
def client():
    app = create_app(InMemoryServiceOrderRepository(), InMemoryServiceSpecificationRepository(SPECS),
                     FakeDrones(), FakeActivation(), verifier())
    return app.test_client()


URL = "/api/service-ordering/v1/serviceOrder"
BODY = {"orderItem": [{"action": "add", "droneId": "DRN-0231", "service": {"serviceSpecification": {"id": C2}}},
                      {"action": "add", "droneId": "DRN-0231", "service": {"serviceSpecification": {"id": IMG}}}]}


def test_rest_create_201_then_replay_200(client):
    headers = auth_headers(**{"Idempotency-Key": "k-1"})
    first = client.post(URL, json=BODY, headers=headers)
    assert first.status_code == 201 and first.json["state"] == "ACKNOWLEDGED"
    assert first.json["orderItem"][0]["service"]["serviceSpecification"]["id"] == C2
    replay = client.post(URL, json=BODY, headers=headers)
    assert replay.status_code == 200 and replay.json["id"] == first.json["id"]


@pytest.mark.parametrize("body, headers", [
    (BODY, {}),                                            # Idempotency-Key absente
    ({"orderItem": "x"}, {"Idempotency-Key": "k"}),        # type incorrect
    ({"orderItem": [{"action": "add", "droneId": "DRN-0231"}]}, {"Idempotency-Key": "k"}),  # service manquant
])
def test_rest_malformed_order_is_400(client, body, headers):
    assert client.post(URL, json=body, headers=auth_headers(**headers)).status_code == 400


def test_rest_business_rule_is_422(client):
    body = {"orderItem": [{"action": "add", "droneId": "DRN-0231", "service": {"serviceSpecification": {"id": "C2"}}}]}
    r = client.post(URL, json=body, headers=auth_headers(**{"Idempotency-Key": "k"}))
    assert r.status_code == 422 and r.json["type"].endswith("/business-rule")


def test_rest_without_token_is_401(client):
    assert client.post(URL, json=BODY, headers={"Idempotency-Key": "k"}).status_code == 401
    assert client.get("/api/service-catalog/v1/serviceSpecification").status_code == 401


def test_rest_catalog_lists_offers_by_id(client):
    r = client.get("/api/service-catalog/v1/serviceSpecification", headers=auth_headers())
    assert [s["id"] for s in r.json] == [C2, IMG, "SPEC-OLD"]
