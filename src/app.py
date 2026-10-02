import logging
from flask import Flask

from src.modules.orders.application.services import PlaceServiceOrder, GetServiceOrder
from src.modules.orders.infrastructure.in_memory_repository import InMemoryServiceOrderRepository
from src.modules.orders.web.routes import create_orders_blueprint
from src.shared.problem import register_error_handlers

from src.modules.fleet.api import FleetFacade
from src.modules.fleet.application.services import RegisterDrone
from src.modules.fleet.infrastructure.in_memory_repository import InMemoryDroneRepository
from src.modules.fleet.web.routes import create_fleet_blueprint

from src.modules.catalog.api import CatalogFacade
from src.modules.catalog.domain.model import ServiceSpecification, ServiceType, ServiceCharacteristics
from src.modules.catalog.infrastructure.in_memory_repository import InMemoryServiceSpecificationRepository


def create_app() -> Flask:
    app = Flask(__name__)

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Register error handlers
    register_error_handlers(app)

    # Setup in-memory repositories
    drone_repository = InMemoryDroneRepository()
    catalog_repository = InMemoryServiceSpecificationRepository()

    # Pre-populate catalog with some service specifications
    catalog_repository.add_service_specification(
        ServiceSpecification(
            service_name="C&C Connectivity",
            service_type=ServiceType.C2,
            characteristics=ServiceCharacteristics(
                sst=2,
                sd="000001",
                dnn="c2",
                five_qi=7,
                arp=2,
                ambr_uplink_mbps=20,
                ambr_downlink_mbps=20
            )
        )
    )
    catalog_repository.add_service_specification(
        ServiceSpecification(
            service_name="Imagery Service",
            service_type=ServiceType.IMAGERY,
            characteristics=ServiceCharacteristics(
                sst=1,
                sd="000002",
                dnn="imagery",
                five_qi=9,
                arp=8,
                ambr_uplink_mbps=500,
                ambr_downlink_mbps=100
            )
        )
    )

    fleet_facade = FleetFacade(drone_repository)
    catalog_facade = CatalogFacade(catalog_repository)
    order_repository = InMemoryServiceOrderRepository()

    # Register blueprints
    app.register_blueprint(create_orders_blueprint(
        PlaceServiceOrder(order_repository, fleet_facade, catalog_facade),
        GetServiceOrder(order_repository),
    ))
    app.register_blueprint(create_fleet_blueprint(RegisterDrone(drone_repository)))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(port = 5000, debug=True)