from dataclasses import dataclass

from src.modules.fleet.domain.model import DroneId
from src.modules.fleet.domain.ports import DroneRepository

@dataclass(frozen=True)
class DroneReference:
    drone_id: str
    is_eligible: bool

class FleetFacade:
    def __init__(self, drone_repository: DroneRepository):
        self.drone_repository = drone_repository

    def get_drone_reference(self, drone_id: str, customer_id: str) -> DroneReference | None:
        drone = self.drone_repository.get(DroneId(drone_id), customer_id)
        if drone is None:
            return None
        return DroneReference(drone_id=drone.drone_id.value, is_eligible=drone.is_eligible())