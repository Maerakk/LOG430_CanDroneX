from datetime import datetime

from flask import Blueprint, g, jsonify, request

from candronex_common.auth import requires_client
from candronex_common.errors import BadRequestError
from candronex_common.logs import audit
from candronex_common.web import json_body, required
from slice_activation.domain.model import Characteristic, Service
from slice_activation.domain.port.inbound import (ActivationCommand, InventoryQueryUseCase,
                                                  RequestActivationUseCase)

BASE = "/api/slice-activation/v1"


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z") if dt else None


def service_to_json(s: Service) -> dict:
    return {
        "id": s.service_id,
        "state": s.state.value,
        "droneId": s.drone_id,
        "orderId": s.order_id,
        "orderItemId": s.order_item_id,
        "serviceSpecification": {"id": s.specification_id},
        "serviceCharacteristic": [{"name": c.name, "valueType": c.value_type, "value": c.value}
                                  for c in s.characteristics],
        "acceptedAt": iso(s.accepted_at),
        "activatedAt": iso(s.activated_at),
        "failureReason": s.failure_reason,
    }


def parse_command(data: dict, client_id: str) -> ActivationCommand:
    characteristics = []
    for c in required(data, "serviceCharacteristic", list):
        if not isinstance(c, dict) or not isinstance(c.get("name"), str) or "value" not in c:
            raise BadRequestError("Each serviceCharacteristic needs a name and a value.")
        characteristics.append(Characteristic(c["name"], str(c.get("valueType", "string")), c["value"]))
    try:
        accepted_at = datetime.fromisoformat(required(data, "acceptedAt").replace("Z", "+00:00"))
    except ValueError as e:
        raise BadRequestError("acceptedAt must be an ISO 8601 date-time.") from e
    if accepted_at.tzinfo is None:
        raise BadRequestError("acceptedAt must include a time zone.")
    return ActivationCommand(client_id, required(data, "orderId"), required(data, "orderItemId"),
                             required(data, "droneId"), required(required(data, "serviceSpecification", dict), "id"),
                             tuple(characteristics), accepted_at)


def create_blueprint(request_activation: RequestActivationUseCase, queries: InventoryQueryUseCase) -> Blueprint:
    bp = Blueprint("slice_activation", __name__, url_prefix=BASE)

    # Route interne, appelée seulement par service-ordering-service
    @bp.post("/service")
    @requires_client
    def request_service_activation():
        cmd = parse_command(json_body(), g.client_id)
        service, created = request_activation.execute(cmd)
        if created:
            audit("service.activation-requested", service.service_id)
        headers = {"Location": f"{BASE}/service/{service.service_id}"}
        return jsonify(service_to_json(service)), (202 if created else 200), headers

    @bp.get("/service")
    @requires_client
    def search_services():
        return jsonify([service_to_json(s) for s in queries.search(g.client_id, request.args.get("orderId"))])

    @bp.get("/service/<service_id>")
    @requires_client
    def get_service(service_id: str):
        return jsonify(service_to_json(queries.get(service_id, g.client_id)))

    return bp
