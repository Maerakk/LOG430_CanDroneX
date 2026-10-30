from abc import ABC, abstractmethod

from drone_management.domain.model import Drone, DroneId, Iccid, Imsi


class DroneRepository(ABC):
    @abstractmethod
    def save(self, drone: Drone) -> None: ...

    @abstractmethod
    def get(self, drone_id: DroneId, client_id: str) -> Drone | None: ...

    @abstractmethod
    def list_by_client(self, client_id: str) -> list[Drone]: ...

    @abstractmethod
    def imsi_in_use(self, imsi: Imsi) -> bool: ...

    @abstractmethod
    def iccid_in_use(self, iccid: Iccid) -> bool: ...
