from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from service_ordering.ordering.domain.model import ServiceCharacteristic, ServiceOrder
from service_ordering.ordering.domain.states import ItemState


@dataclass(frozen=True)
class DroneReference:
    drone_id: str
    eligible: bool


class DroneDirectory(ABC):
    @abstractmethod
    def find(self, drone_id: str, client_id: str) -> DroneReference | None: ...


@dataclass(frozen=True)
class OfferedService:
    specification_id: str
    name: str
    characteristics: tuple[ServiceCharacteristic, ...]


class ServiceCatalog(ABC):
    @abstractmethod
    def find_orderable(self, specification_id: str) -> OfferedService | None: ...


@dataclass(frozen=True)
class ActivationRequest:
    order_id: str
    order_item_id: str
    drone_id: str
    specification_id: str
    characteristics: tuple[ServiceCharacteristic, ...]
    accepted_at: datetime


@dataclass(frozen=True)
class ActivationStatus:
    service_id: str
    order_item_id: str
    state: ItemState


class ServiceActivation(ABC):
    """Commandes -> Activation seulement, pour éviter un cycle. Peut lever ServiceUnavailableError."""

    @abstractmethod
    def request_activation(self, request: ActivationRequest) -> ActivationStatus: ...

    @abstractmethod
    def statuses(self, order_id: str) -> list[ActivationStatus]: ...


class DuplicateIdempotencyKey(Exception):
    pass


class ServiceOrderRepository(ABC):
    @abstractmethod
    def add(self, order: ServiceOrder) -> None:
        """Lève DuplicateIdempotencyKey si la clé existe déjà pour ce client."""

    @abstractmethod
    def update_items(self, order: ServiceOrder) -> None: ...

    @abstractmethod
    def get(self, order_id: str, client_id: str) -> ServiceOrder | None: ...

    @abstractmethod
    def find_by_idempotency_key(self, idempotency_key: str, client_id: str) -> ServiceOrder | None: ...

    @abstractmethod
    def has_blocking_item(self, client_id: str, drone_id: str, specification_id: str) -> bool: ...
