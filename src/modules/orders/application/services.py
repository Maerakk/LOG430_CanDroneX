import logging

from src.modules.fleet.api import FleetFacade
from src.modules.catalog.api import CatalogFacade
from src.modules.orders.domain.model import ServiceOrder
from src.modules.orders.domain.ports import ServiceOrderRepository
from src.modules.orders.domain.errors import (DroneNotEligibleError, UnknownServiceTypeError,
                                              ServiceAlreadyOrderedError, IdempotencyKeyConflictError,
                                              DroneNotFoundError, OrderNotFoundError
                                              )

logger = logging.getLogger(__name__)

class PlaceServiceOrder:
    def __init__(self, order_repository: ServiceOrderRepository, fleet_facade: FleetFacade, catalog_facade: CatalogFacade):
        self.order_repository = order_repository
        self.fleet_facade = fleet_facade
        self.catalog_facade = catalog_facade

    def execute(self, customer_id: str, idempotency_key: str, items: list[tuple[str,str]]) -> ServiceOrder:

        # Check for idempotency key conflict
        existing_order = self.order_repository.find_by_idempotency_key(idempotency_key, customer_id)
        if existing_order is not None:
            existing_request = {(item.drone_id, item.service_type) for item in existing_order.items}
            if existing_request == set(items):
                    logger.info(f"Idempotent request detected for customer '{customer_id}' with idempotency key '{idempotency_key}'. Returning existing order '{existing_order.order_id}'.")
                    return existing_order
            raise IdempotencyKeyConflictError(f"An order with idempotency key '{idempotency_key}' already exists for customer '{customer_id}'.")

        # Check if the drone exists, is eligible, and is owned by the client
        for drone_id in {drone_id for drone_id, _ in items}:
            drone_ref = self.fleet_facade.get_drone_reference(drone_id, customer_id)
            if drone_ref is None:
                raise DroneNotFoundError(f"Drone '{drone_id}' does not exist or is not owned by customer '{customer_id}'.")
            if not drone_ref.is_eligible:
                raise DroneNotEligibleError(f"Drone '{drone_id}' is not eligible for service.")

        # Check if the service type exists
        items_characteristics = []
        for drone_id, service_type in items:
            service_spec = self.catalog_facade.get_service_specification(service_type)
            if service_spec is None:
                raise UnknownServiceTypeError(f"Service type '{service_type}' does not exist.")
            items_characteristics.append((drone_id, service_type, service_spec.characteristics))

        # Check if the service has already been ordered for the drone
        for drone_id, service_type in items:
            if self.order_repository.has_open_item(drone_id, service_type, customer_id):
                raise ServiceAlreadyOrderedError(f"Service '{service_type}' has already been ordered for drone '{drone_id}' and is still open.")

        # Create the service order
        order = ServiceOrder.create(customer_id, idempotency_key, items_characteristics)
        self.order_repository.save(order)
        logger.info(f"Service order '{order.order_id}' created for customer '{customer_id}' with idempotency key '{idempotency_key}'.")
        return order

class GetServiceOrder:
    def __init__(self, order_repository: ServiceOrderRepository):
        self.order_repository = order_repository

    def execute(self, order_id: str, customer_id: str) -> ServiceOrder:
        order = self.order_repository.get(order_id, customer_id)
        if order is None:
            raise OrderNotFoundError(f"Service order '{order_id}' not found for customer '{customer_id}'.")
        return order