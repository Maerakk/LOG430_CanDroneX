from flask import Blueprint, g, jsonify, request

from candronex_common.auth import requires_client
from candronex_common.errors import BadRequestError
from candronex_common.logs import audit
from candronex_common.web import json_body, required
from service_ordering.ordering.domain.model import ItemRequest, ServiceOrder
from service_ordering.ordering.domain.port.inbound import GetServiceOrderUseCase, PlaceServiceOrderUseCase

BASE = "/api/service-ordering/v1"


def iso(dt) -> str:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def order_to_json(order: ServiceOrder) -> dict:
    return {
        "id": order.order_id,
        "state": order.state.value,
        "acceptedAt": iso(order.accepted_at),
        "orderItem": [{
            "id": item.item_id,
            "action": item.action.value,
            "state": item.state.value,
            "droneId": item.drone_id,
            "service": {
                "id": item.service.service_id,
                "serviceSpecification": {"id": item.service.specification_id,
                                         "name": item.service.specification_name},
                "serviceCharacteristic": [{"name": c.name, "valueType": c.value_type, "value": c.value}
                                          for c in item.service.characteristics],
            },
        } for item in order.items],
    }


def parse_items(data: dict) -> list[ItemRequest]:
    items = required(data, "orderItem", list)
    parsed = []
    for item in items:
        if not isinstance(item, dict):
            raise BadRequestError("Each orderItem must be a JSON object.")
        service = required(item, "service", dict)
        specification = required(service, "serviceSpecification", dict)
        parsed.append(ItemRequest(required(item, "action"), required(item, "droneId"), required(specification, "id")))
    return parsed


def create_blueprint(place: PlaceServiceOrderUseCase, get: GetServiceOrderUseCase) -> Blueprint:
    bp = Blueprint("service_ordering", __name__, url_prefix=BASE)

    @bp.post("/serviceOrder")
    @requires_client
    def place_order():
        key = request.headers.get("Idempotency-Key")
        if not key:
            raise BadRequestError("The Idempotency-Key header is required.")
        order, created = place.execute(g.client_id, key, parse_items(json_body()))
        if created:
            audit("service-order.placed", order.order_id)
        headers = {"Location": f"{BASE}/serviceOrder/{order.order_id}"}
        return jsonify(order_to_json(order)), (201 if created else 200), headers

    @bp.get("/serviceOrder/<order_id>")
    @requires_client
    def get_order(order_id: str):
        return jsonify(order_to_json(get.execute(order_id, g.client_id)))

    return bp
