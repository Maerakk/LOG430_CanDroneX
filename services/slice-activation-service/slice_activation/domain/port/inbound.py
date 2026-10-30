from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from slice_activation.domain.model import Characteristic, Service


@dataclass(frozen=True)
class ActivationCommand:
    client_id: str
    order_id: str
    order_item_id: str
    drone_id: str
    specification_id: str
    characteristics: tuple[Characteristic, ...]
    accepted_at: datetime


class RequestActivationUseCase(ABC):
    @abstractmethod
    def execute(self, cmd: ActivationCommand) -> tuple[Service, bool]:
        """Retourne (service, créé)."""


class ActivateServiceUseCase(ABC):
    @abstractmethod
    def execute(self, service_id: str) -> None: ...


class InventoryQueryUseCase(ABC):
    @abstractmethod
    def get(self, service_id: str, client_id: str) -> Service: ...

    @abstractmethod
    def search(self, client_id: str, order_id: str | None) -> list[Service]: ...
