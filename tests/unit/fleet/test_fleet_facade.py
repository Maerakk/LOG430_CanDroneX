from src.modules.fleet.api import FleetFacade
from src.modules.fleet.application.services import RegisterDrone
from src.modules.fleet.domain.model import DroneId, DroneStatus
from src.modules.fleet.infrastructure.in_memory_repository import InMemoryDroneRepository


def setup():
    repository = InMemoryDroneRepository()
    RegisterDrone(repository).execute("DRN-0231", "999700000010231", "8999970000000010231", "CUST-001")
    return repository, FleetFacade(repository)


def test_an_active_drone_is_eligible():
    _, facade = setup()
    reference = facade.get_drone_reference("DRN-0231", "CUST-001")
    assert reference.is_eligible
    assert reference.drone_id == "DRN-0231"


def test_an_unknown_drone_returns_none():
    _, facade = setup()
    assert facade.get_drone_reference("DRN-9999", "CUST-001") is None


def test_a_drone_of_another_customer_returns_none():
    _, facade = setup()
    assert facade.get_drone_reference("DRN-0231", "CUST-002") is None


def test_a_suspended_drone_is_not_eligible():
    repository, facade = setup()
    repository.get(DroneId("DRN-0231"), "CUST-001").status = DroneStatus.SUSPENDED
    assert not facade.get_drone_reference("DRN-0231", "CUST-001").is_eligible