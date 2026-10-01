from src.modules.fleet.domain.model import Imsi, Iccid, DroneId, Drone
from src.modules.fleet.domain.ports import DroneRepository

class FakeDroneRepository(DroneRepository):
    def __init__(self):
        self.drones: dict [tuple[str,str], Drone] = {}
        # Dictionary that fakes a database, with key as (drone_id, customer_id) and value as Drone object

    def save(self, drone: Drone) -> None:
        self.drones[(drone.drone_id.value, drone.customer_id)] = drone

    def get(self, drone_id: DroneId, customer_id: str) -> Drone | None:
        return self.drones.get((drone_id.value, customer_id), None)

    def imsi_in_use(self, imsi: Imsi) -> bool:
        return any(drone.imsi.value == imsi.value for drone in self.drones.values())

    def iccid_in_use(self, iccid: Iccid) -> bool:
        return any(drone.iccid.value == iccid.value for drone in self.drones.values())