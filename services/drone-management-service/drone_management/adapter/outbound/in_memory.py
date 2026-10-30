from drone_management.domain.model import Drone, DroneId, Iccid, Imsi
from drone_management.domain.port.outbound import DroneRepository


class InMemoryDroneRepository(DroneRepository):
    def __init__(self):
        self.drones: dict[tuple[str, str], Drone] = {}

    def save(self, drone: Drone) -> None:
        self.drones[(drone.drone_id.value, drone.client_id)] = drone

    def get(self, drone_id: DroneId, client_id: str) -> Drone | None:
        return self.drones.get((drone_id.value, client_id))

    def list_by_client(self, client_id: str) -> list[Drone]:
        return [d for d in self.drones.values() if d.client_id == client_id]

    def imsi_in_use(self, imsi: Imsi) -> bool:
        return any(d.imsi == imsi for d in self.drones.values())

    def iccid_in_use(self, iccid: Iccid) -> bool:
        return any(d.iccid == iccid for d in self.drones.values())
