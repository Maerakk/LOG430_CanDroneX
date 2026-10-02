import logging
from flask import Flask

from src.modules.catalog.api import CatalogFacade
from src.modules.catalog.infrastructure.sql_repository import SqlServiceSpecificationRepository

from src.modules.orders.application.services import PlaceServiceOrder, GetServiceOrder
from src.modules.orders.infrastructure.sql_repository import SqlServiceOrderRepository
from src.modules.orders.web.routes import create_orders_blueprint

from src.modules.fleet.api import FleetFacade
from src.modules.fleet.application.services import RegisterDrone
from src.modules.fleet.web.routes import create_fleet_blueprint
from src.modules.fleet.infrastructure.sql_repository import SqlDroneRepository


from src.shared.problem import register_error_handlers
from src.shared.db import SessionFactory


def create_app() -> Flask:
    app = Flask(__name__)

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Register error handlers
    register_error_handlers(app)

    # Setup SQL repositories
    drone_repository = SqlDroneRepository(SessionFactory)
    catalog_repository = SqlServiceSpecificationRepository(SessionFactory)
    order_repository = SqlServiceOrderRepository(SessionFactory)

    fleet_facade = FleetFacade(drone_repository)
    catalog_facade = CatalogFacade(catalog_repository)

    # Register blueprints
    app.register_blueprint(create_orders_blueprint(
        PlaceServiceOrder(order_repository, fleet_facade, catalog_facade),
        GetServiceOrder(order_repository),
    ))
    app.register_blueprint(create_fleet_blueprint(RegisterDrone(drone_repository)))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)