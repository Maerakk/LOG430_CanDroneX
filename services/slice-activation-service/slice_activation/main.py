import os
from pathlib import Path

from flask import Flask, send_file

from candronex_common import auth, logs, web
from slice_activation.adapter.inbound.rest import BASE, create_blueprint
from slice_activation.adapter.outbound.scheduler import ThreadPoolActivationScheduler
from slice_activation.application.use_cases import ActivateService, InventoryQueries, RequestActivation
from slice_activation.domain.port.outbound import (ActivationScheduler, DroneIdentityProvider, NetworkProvisioningPort,
                                                   ServiceInventory)

SERVICE = "slice-activation-service"
OPENAPI = Path(__file__).resolve().parent.parent / "openapi.yaml"


def create_app(inventory: ServiceInventory | None = None,
               network: NetworkProvisioningPort | None = None,
               drones: DroneIdentityProvider | None = None,
               scheduler: ActivationScheduler | None = None,
               verifier: auth.TokenVerifier | None = None) -> Flask:
    logs.configure(SERVICE)
    if inventory is None:
        from candronex_common.db import session_factory
        from slice_activation.adapter.outbound.persistence import SqlServiceInventory
        inventory = SqlServiceInventory(session_factory())
    if network is None:
        # Phase 3 : remplacer par l'adaptateur Open5GS, rien d'autre ne change
        from slice_activation.adapter.outbound.mock_open5gs import MockOpen5GSAdapter
        network = MockOpen5GSAdapter()
    if drones is None:
        from slice_activation.adapter.outbound.drone_identity_http import HttpDroneIdentityProvider
        drones = HttpDroneIdentityProvider(os.environ.get("DRONE_MANAGEMENT_URL", "http://drone-management-service:8000"))
    if scheduler is None:
        scheduler = ThreadPoolActivationScheduler(int(os.environ.get("ACTIVATION_WORKERS", "40")))
    scheduler.activate = ActivateService(inventory, network).execute

    app = Flask(SERVICE)
    web.install(app)
    auth.install(app, verifier or auth.TokenVerifier())
    app.register_blueprint(create_blueprint(RequestActivation(inventory, drones, scheduler), InventoryQueries(inventory)))

    @app.get(f"{BASE}/openapi.yaml")
    def openapi():
        return send_file(OPENAPI, mimetype="application/yaml")

    return app
