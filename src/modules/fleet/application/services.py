import logging

from src.modules.fleet.domain.model import DroneId, Imsi, Iccid, Drone
from src.modules.fleet.domain.ports import DroneRepository
from src.modules.fleet.domain.errors import DroneAlreadyRegisteredError, NetworkIdentifierError

logger = logging.getLogger(__name__)

class RegisterDrone:
    def __init__(self, repository: DroneRepository):
        self.repository = repository

    def execute(self, drone_id: str, imsi: str, iccid: str, customer_id: str) -> Drone:
        drone_id_obj = DroneId(drone_id)
        imsi_obj = Imsi(imsi)
        iccid_obj = Iccid(iccid)

        if self.repository.get(drone_id_obj, customer_id) is not None:
            raise DroneAlreadyRegisteredError(f"Drone with ID {drone_id} is already registered for customer {customer_id}.")

        if self.repository.imsi_in_use(imsi_obj):
            raise NetworkIdentifierError("Network identity unavailable.")

        if self.repository.iccid_in_use(iccid_obj):
            raise NetworkIdentifierError("Network identity unavailable.")

        drone = Drone.register(drone_id_obj, imsi_obj, iccid_obj, customer_id)
        self.repository.save(drone)
        logger.info(f"Drone {drone_id} registered successfully for customer {customer_id} (IMSI {imsi_obj.masked()}).")
        return drone