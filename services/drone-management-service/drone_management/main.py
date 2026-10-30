from pathlib import Path

from flask import Flask, send_file

from candronex_common import auth, logs, web
from drone_management.adapter.inbound.rest import BASE, create_blueprint
from drone_management.application.use_cases import GetDrone, ListDrones, RegisterDrone
from drone_management.domain.port.outbound import DroneRepository

SERVICE = "drone-management-service"
OPENAPI = Path(__file__).resolve().parent.parent / "openapi.yaml"


def create_app(repository: DroneRepository | None = None, verifier: auth.TokenVerifier | None = None) -> Flask:
    logs.configure(SERVICE)
    if repository is None:
        from candronex_common.db import session_factory
        from drone_management.adapter.outbound.sql_repository import SqlDroneRepository
        repository = SqlDroneRepository(session_factory())

    app = Flask(SERVICE)
    web.install(app)
    auth.install(app, verifier or auth.TokenVerifier())
    app.register_blueprint(create_blueprint(RegisterDrone(repository), GetDrone(repository), ListDrones(repository)))

    @app.get(f"{BASE}/openapi.yaml")
    def openapi():
        return send_file(OPENAPI, mimetype="application/yaml")

    return app
