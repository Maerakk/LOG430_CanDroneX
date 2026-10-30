import logging

from candronex_common.errors import InvalidValueError
from drone_management.domain.errors import (DroneAlreadyRegisteredError, DroneNotFoundError,
                                            NetworkIdentityUnavailableError)
from drone_management.domain.model import Drone, DroneId, Iccid, Imsi
from drone_management.domain.port.inbound import GetDroneUseCase, ListDronesUseCase, RegisterDroneUseCase
from drone_management.domain.port.outbound import DroneRepository

log = logging.getLogger(__name__)


class RegisterDrone(RegisterDroneUseCase):
    def __init__(self, repository: DroneRepository):
        self.repository = repository

    def execute(self, drone_id: str, imsi: str, iccid: str, client_id: str) -> tuple[Drone, bool]:
        """Rejouer la même demande rend le drone existant."""
        drone_id, imsi, iccid = DroneId(drone_id), Imsi(imsi), Iccid(iccid)

        existing = self.repository.get(drone_id, client_id)
        if existing is not None:
            if existing.same_identity(imsi, iccid):
                return existing, False
            raise DroneAlreadyRegisteredError(f"Drone '{drone_id.value}' is already registered with another identity.")

        if self.repository.imsi_in_use(imsi) or self.repository.iccid_in_use(iccid):
            raise NetworkIdentityUnavailableError("Network identity unavailable.")

        drone = Drone.register(drone_id, imsi, iccid, client_id)
        self.repository.save(drone)
        log.info("drone registered", extra={"fields": {"droneId": drone_id.value, "imsi": imsi.masked()}})
        return drone, True


class GetDrone(GetDroneUseCase):
    def __init__(self, repository: DroneRepository):
        self.repository = repository

    def execute(self, drone_id: str, client_id: str) -> Drone:
        try:
            drone = self.repository.get(DroneId(drone_id), client_id)
        except InvalidValueError:
            drone = None
        if drone is None:
            # même réponse si le drone appartient à un autre client
            raise DroneNotFoundError(f"Drone '{drone_id}' not found.")
        return drone


class ListDrones(ListDronesUseCase):
    def __init__(self, repository: DroneRepository):
        self.repository = repository

    def execute(self, client_id: str) -> list[Drone]:
        return self.repository.list_by_client(client_id)
