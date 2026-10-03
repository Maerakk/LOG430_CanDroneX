import pytest

from src.modules.fleet.domain.model import Drone, DroneId, Imsi, Iccid
from src.modules.fleet.domain.errors import NetworkIdentifierError
from src.modules.fleet.infrastructure.sql_repository import SqlDroneRepository
from src.modules.orders.domain.model import ServiceOrder
from src.modules.orders.infrastructure.sql_repository import SqlServiceOrderRepository
from tests.integration.conftest import TEST_CUSTOMER

IMSI = "999709999999901"
ICCID = "8999709999999999901"
C2_CHARACTERISTICS = {"sst": 2, "sd": "000001", "dnn": "c2", "five_qi": 7, "arp": 2,
                      "ambr_uplink_mbps": 20, "ambr_downlink_mbps": 20}


def make_drone(drone_id: str, imsi: str, iccid: str) -> Drone:
    return Drone.register(DroneId(drone_id), Imsi(imsi), Iccid(iccid), TEST_CUSTOMER)


def test_a_saved_drone_is_found_in_the_database(session_factory):
    repository = SqlDroneRepository(session_factory)
    repository.save(make_drone("DRN-TEST-1", IMSI, ICCID))

    found = repository.get(DroneId("DRN-TEST-1"), TEST_CUSTOMER)

    assert found is not None
    assert found.imsi == Imsi(IMSI)


def test_the_database_refuses_a_duplicate_imsi(session_factory):
    repository = SqlDroneRepository(session_factory)
    repository.save(make_drone("DRN-TEST-1", IMSI, ICCID))

    with pytest.raises(NetworkIdentifierError):
        repository.save(make_drone("DRN-TEST-2", IMSI, "8999709999999999902"))


def test_an_order_and_its_items_are_saved_together(session_factory):
    repository = SqlServiceOrderRepository(session_factory)
    order = ServiceOrder.create(TEST_CUSTOMER, "test-key-1", [("DRN-TEST-1", "C2", C2_CHARACTERISTICS)])
    repository.save(order)

    found = repository.get(order.order_id, TEST_CUSTOMER)

    assert len(found.items) == 1
    assert found.items[0].characteristics["arp"] == 2