from abc import ABC, abstractmethod
from src.modules.fleet.domain.model import Imsi, Iccid, DroneId, Drone

class DroneRepository(ABC):
    @abstractmethod
    def save(self, drone: Drone) -> None:
        pass

    @abstractmethod
    def get(self, drone_id: DroneId, customer_id: str) -> Drone:
        pass

    @abstractmethod
    def imsi_in_use(self, imsi: Imsi) -> bool:
        pass

    @abstractmethod
    def iccid_in_use(self, iccid: Iccid) -> bool:
        pass

    