from flask import Blueprint, jsonify, request, g

from src.shared.authentification import requires_api_key
from src.modules.fleet.application.services import RegisterDrone

REQUIRED_FIELDS = ["droneId", "imsi", "iccid"]

def create_fleet_blueprint(register_drone_service: RegisterDrone) -> Blueprint:
    blueprint = Blueprint("fleet", __name__, url_prefix="/api/v1/drones")

    @blueprint.post("")
    @requires_api_key
    def register_drone():
        data = request.get_json(silent=True) or {}
        missing = [field for field in REQUIRED_FIELDS if field not in data]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        drone = register_drone_service.execute(data["droneId"], data["imsi"], data["iccid"], g.customer_id)
        body = {
            "droneId": drone.drone_id.value,
            "status": drone.status.value,
            "imsi": drone.imsi.masked()
        }
        return jsonify(body), 201

    return blueprint