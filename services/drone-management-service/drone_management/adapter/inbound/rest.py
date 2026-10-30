from flask import Blueprint, g, jsonify

from candronex_common.auth import requires_client
from candronex_common.logs import audit
from candronex_common.web import json_body, required
from drone_management.domain.port.inbound import GetDroneUseCase, ListDronesUseCase, RegisterDroneUseCase
from drone_management.domain.model import Drone

BASE = "/api/drone-management/v1"


def drone_to_json(drone: Drone) -> dict:
    return {
        "droneId": drone.drone_id.value,
        "status": drone.status.value,
        "eligible": drone.is_eligible(),
        "imsi": drone.imsi.masked(),
        "iccid": drone.iccid.masked(),
    }


def create_blueprint(register: RegisterDroneUseCase, get: GetDroneUseCase,
                     list_drones: ListDronesUseCase) -> Blueprint:
    bp = Blueprint("drone_management", __name__, url_prefix=BASE)

    @bp.post("/drone")
    @requires_client
    def register_drone():
        data = json_body()
        drone, created = register.execute(required(data, "droneId"), required(data, "imsi"),
                                          required(data, "iccid"), g.client_id)
        if created:
            audit("drone.registered", drone.drone_id.value)
        headers = {"Location": f"{BASE}/drone/{drone.drone_id.value}"}
        return jsonify(drone_to_json(drone)), (201 if created else 200), headers

    @bp.get("/drone")
    @requires_client
    def list_my_drones():
        return jsonify([drone_to_json(d) for d in list_drones.execute(g.client_id)])

    @bp.get("/drone/<drone_id>")
    @requires_client
    def get_drone(drone_id: str):
        return jsonify(drone_to_json(get.execute(drone_id, g.client_id)))

    # Route interne (absente de la passerelle) : seul slice-activation-service reçoit l'IMSI
    @bp.get("/drone/<drone_id>/networkIdentity")
    @requires_client
    def get_network_identity(drone_id: str):
        drone = get.execute(drone_id, g.client_id)
        return jsonify({"droneId": drone.drone_id.value, "imsi": drone.imsi.value, "eligible": drone.is_eligible()})

    return bp
