from src.modules.fleet.api import FleetFacade
from src.modules.fleet.application.services import RegisterDrone
from src.modules.catalog.api import CatalogFacade
from src.modules.catalog.domain.model import ServiceSpecification, ServiceType, ServiceCharacteristics
from src.modules.orders.application.services import PlaceServiceOrder
from src.modules.fleet.infrastructure.in_memory_repository import InMemoryDroneRepository
from src.modules.catalog.infrastructure.in_memory_repository import InMemoryServiceSpecificationRepository
from src.modules.orders.infrastructure.in_memory_repository import InMemoryServiceOrderRepository
import pytest
from src.modules.orders.domain.errors import (
    DroneNotFoundError, UnknownServiceTypeError, ServiceAlreadyOrderedError, IdempotencyKeyConflictError,
)

CUSTOMER_1 = "CUST-001"
CUSTOMER_2 = "CUST-002"
DRONE = "DRN-0231"
C2_AND_IMAGERY_ITEMS = [(DRONE, "C2"), (DRONE, "IMAGERY")]

def create_service() -> PlaceServiceOrder:
    drone_repository = InMemoryDroneRepository()
    RegisterDrone(drone_repository).execute(DRONE, "999700000010231", "8999970000000010231", CUSTOMER_1)

    catalog_repository = InMemoryServiceSpecificationRepository()
    catalog_repository.add_service_specification(ServiceSpecification( "C&C Connectivity", ServiceType.C2, ServiceCharacteristics( sst=2, sd="000001", dnn="c2", five_qi=7, arp=2, ambr_uplink_mbps=20, ambr_downlink_mbps=20)))
    catalog_repository.add_service_specification(ServiceSpecification( "Imagery Service", ServiceType.IMAGERY, ServiceCharacteristics( sst=1, sd="000002", dnn="imagery", five_qi=9, arp=8, ambr_uplink_mbps=500, ambr_downlink_mbps=100)))

    return PlaceServiceOrder(InMemoryServiceOrderRepository(), FleetFacade(drone_repository), CatalogFacade(catalog_repository))

def test_valid():
    order = create_service().execute(CUSTOMER_1, "key-1", C2_AND_IMAGERY_ITEMS)
    assert len(order.items) == 2
    assert order.items[0].characteristics["arp"] == 2


def test_replaying_the_same_request_returns_the_same_order():
    service = create_service()
    first = service.execute(CUSTOMER_1, "key-1", C2_AND_IMAGERY_ITEMS)
    replay = service.execute(CUSTOMER_1, "key-1", C2_AND_IMAGERY_ITEMS)
    assert replay.order_id == first.order_id


def test_same_key_with_different_content_is_refused():
    service = create_service()
    service.execute(CUSTOMER_1, "key-1", C2_AND_IMAGERY_ITEMS)
    with pytest.raises(IdempotencyKeyConflictError):
        service.execute(CUSTOMER_1, "key-1", [(DRONE, "C2")])


def test_drone_of_another_customer_is_not_found():
    with pytest.raises(DroneNotFoundError):
        create_service().execute(CUSTOMER_2, "key-1", C2_AND_IMAGERY_ITEMS)


def test_unknown_service_type_is_refused():
    with pytest.raises(UnknownServiceTypeError):
        create_service().execute(CUSTOMER_1, "key-1", [(DRONE, "VIDEO")])


def test_a_service_already_ordered_is_refused():
    service = create_service()
    service.execute(CUSTOMER_1, "key-1", [(DRONE, "C2")])
    with pytest.raises(ServiceAlreadyOrderedError):
        service.execute(CUSTOMER_1, "key-2", [(DRONE, "C2")])