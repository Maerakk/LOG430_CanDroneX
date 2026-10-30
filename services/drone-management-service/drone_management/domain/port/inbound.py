from abc import ABC, abstractmethod

from drone_management.domain.model import Drone


class RegisterDroneUseCase(ABC):
    @abstractmethod
    def execute(self, drone_id: str, imsi: str, iccid: str, client_id: str) -> tuple[Drone, bool]:
        """Retourne (drone, créé)."""


class GetDroneUseCase(ABC):
    @abstractmethod
    def execute(self, drone_id: str, client_id: str) -> Drone: ...


class ListDronesUseCase(ABC):
    @abstractmethod
    def execute(self, client_id: str) -> list[Drone]: ...
