from flask import Blueprint, jsonify, request, g

from src.shared.authentification import requires_api_key
from src.modules.orders.application.services import PlaceServiceOrder, GetServiceOrder
from src.modules.orders.domain.model import ServiceOrder

def order_to_json(order: ServiceOrder) -> dict:
    return {
        "order_id": order.order_id,
        "state": order.state.value,
        "items": [
            {
                "item_id": item.item_id,
                "drone_id": item.drone_id,
                "service_type": item.service_type,
                "state": item.state.value,
                "characteristics": item.characteristics
            }
            for item in order.items
        ]
    }

def create_orders_blueprint(place_service_order: PlaceServiceOrder, get_service_order: GetServiceOrder) -> Blueprint:
    blueprint = Blueprint('orders', __name__, url_prefix="/api/v1/service-orders")

    @blueprint.post("")
    @requires_api_key
    def place_order():
        idempotency_key = request.headers.get("Idempotency-Key")
        if not idempotency_key:
            raise ValueError("Missing Idempotency-Key header")

        data = request.get_json(silent=True) or {}
        customer_id = g.customer_id
        order_items = data.get('items', [])
        items = [(item.get("droneId"), item.get("serviceType")) for item in order_items]
        order = place_service_order.execute(customer_id, idempotency_key, items)
        return jsonify(order_to_json(order)), 201

    @blueprint.get("/<order_id>")
    @requires_api_key
    def get_order(order_id):
        order = get_service_order.execute(order_id, g.customer_id)
        if order is None:
            return jsonify({"error": "Order not found"}), 404
        return jsonify(order_to_json(order)), 200
    return blueprint