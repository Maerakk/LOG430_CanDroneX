import os
from pathlib import Path

from flask import Flask, send_file

from candronex_common import auth, logs, web
from service_ordering.catalog.adapter.inbound import rest as catalog_rest
from service_ordering.catalog.application.queries import CatalogQueries
from service_ordering.catalog.domain.port.outbound import ServiceSpecificationRepository
from service_ordering.ordering.adapter.inbound import rest as ordering_rest
from service_ordering.ordering.adapter.outbound.catalog_in_process import InProcessServiceCatalog
from service_ordering.ordering.application.use_cases import ActivationTracker, GetServiceOrder, PlaceServiceOrder
from service_ordering.ordering.domain.port.outbound import DroneDirectory, ServiceActivation, ServiceOrderRepository

SERVICE = "service-ordering-service"
OPENAPI = Path(__file__).resolve().parent.parent / "openapi.yaml"


def create_app(orders: ServiceOrderRepository | None = None,
               specifications: ServiceSpecificationRepository | None = None,
               drones: DroneDirectory | None = None,
               activation: ServiceActivation | None = None,
               verifier: auth.TokenVerifier | None = None) -> Flask:
    logs.configure(SERVICE)
    if orders is None or specifications is None:
        from candronex_common.db import session_factory
        from service_ordering.catalog.adapter.outbound.persistence import SqlServiceSpecificationRepository
        from service_ordering.ordering.adapter.outbound.persistence import SqlServiceOrderRepository
        sessions = session_factory()
        orders = orders or SqlServiceOrderRepository(sessions)
        specifications = specifications or SqlServiceSpecificationRepository(sessions)
    if drones is None or activation is None:
        from service_ordering.ordering.adapter.outbound.http_clients import HttpDroneDirectory, HttpServiceActivation
        drones = drones or HttpDroneDirectory(os.environ.get("DRONE_MANAGEMENT_URL", "http://drone-management-service:8000"))
        activation = activation or HttpServiceActivation(
            os.environ.get("SLICE_ACTIVATION_URL", "http://slice-activation-service:8000"))

    catalog = CatalogQueries(specifications)
    tracker = ActivationTracker(activation, orders)

    app = Flask(SERVICE)
    web.install(app)
    auth.install(app, verifier or auth.TokenVerifier())
    app.register_blueprint(catalog_rest.create_blueprint(catalog))
    app.register_blueprint(ordering_rest.create_blueprint(
        PlaceServiceOrder(orders, drones, InProcessServiceCatalog(catalog), tracker),
        GetServiceOrder(orders, tracker)))

    @app.get(f"{ordering_rest.BASE}/openapi.yaml")
    def openapi():
        return send_file(OPENAPI, mimetype="application/yaml")

    return app
