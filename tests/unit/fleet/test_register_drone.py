import pytest
from src.modules.fleet.application.services import RegisterDrone
from src.modules.fleet.domain.model import DroneStatus
from src.modules.fleet.domain.errors import DroneAlreadyRegisteredError, NetworkIdentifierError
from tests.unit.fakes import FakeDroneRepository

IMSI_1 = "999701234567890" # 999-70 used on all the project
ICCID_1 = "89112233445566778899"
IMSI_2 = "999700000000123"
ICCID_2 = "8900000000000000123"

CUSTOMER_1 = "CUST-001"
CUSTOMER_2 = "CUST-002"

DRONE_1 = "DRONE-0001"

def create_service() -> RegisterDrone:
    return RegisterDrone(FakeDroneRepository())

def test_register_drone():
    service = create_service()
    drone = service.execute(DRONE_1, IMSI_1, ICCID_1, CUSTOMER_1)
    assert drone.status == DroneStatus.ACTIVE

def test_register_drone_already_registered():
    service = create_service()
    drone = service.execute(DRONE_1, IMSI_1, ICCID_1, CUSTOMER_1)
    with pytest.raises(DroneAlreadyRegisteredError):
        service.execute(DRONE_1, IMSI_2, ICCID_2, CUSTOMER_2)

def test_same_drone_registered_different_customers():
    service = create_service()
    service.execute(DRONE_1, IMSI_1, ICCID_1, CUSTOMER_1)

    drone = service.execute(DRONE_1, IMSI_2, ICCID_2, CUSTOMER_2)

    assert drone.customer_id == CUSTOMER_2
    assert drone.status == DroneStatus.ACTIVE

def test_imsi_already_used():
    service = create_service()
    service.execute(DRONE_1, IMSI_1, ICCID_1, CUSTOMER_1)
    with pytest.raises(NetworkIdentifierError):
        service.execute(DRONE_1, IMSI_1, ICCID_2, CUSTOMER_2)

def test_iccid_already_used():
    service = create_service()
    service.execute(DRONE_1, IMSI_1, ICCID_1, CUSTOMER_1)
    with pytest.raises(NetworkIdentifierError):
        service.execute(DRONE_1, IMSI_2, ICCID_1, CUSTOMER_2)

def test_invalid_imsi():
    service = create_service()
    with pytest.raises(ValueError):
        service.execute(DRONE_1, "1234", ICCID_1, CUSTOMER_1)