from abc import ABC, abstractmethod
from dataclasses import dataclass

from slice_activation.domain.model import NetworkConfiguration, Service


class ProvisioningRejected(Exception):
    """Le réseau a refusé la configuration."""


class ProvisioningTimeout(Exception):
    """Pas de réponse à temps : la configuration a peut-être été appliquée."""


class NetworkProvisioningPort(ABC):
    """Idempotent par service_id. Implémenté par MockOpen5GSAdapter en Phase 2, par Open5GS en Phase 3."""

    @abstractmethod
    def apply(self, configuration: NetworkConfiguration) -> None: ...


@dataclass(frozen=True)
class NetworkIdentity:
    drone_id: str
    imsi: str
    eligible: bool


class DroneIdentityProvider(ABC):
    @abstractmethod
    def network_identity(self, drone_id: str, client_id: str) -> NetworkIdentity | None: ...


class DuplicateOrderItem(Exception):
    pass


class ServiceInventory(ABC):
    @abstractmethod
    def add(self, service: Service) -> None:
        """Lève DuplicateOrderItem si l'élément de commande a déjà un service."""

    @abstractmethod
    def save_transition(self, service: Service) -> bool:
        """Enregistre l'état seulement si la base contient encore service.previous_state.

        False veut dire qu'un autre travailleur a déjà fait la transition.
        """

    @abstractmethod
    def get_by_id(self, service_id: str) -> Service | None: ...

    @abstractmethod
    def get(self, service_id: str, client_id: str) -> Service | None: ...

    @abstractmethod
    def find_by_order_item(self, order_item_id: str) -> Service | None: ...

    @abstractmethod
    def search(self, client_id: str, order_id: str | None = None) -> list[Service]: ...


class ActivationScheduler(ABC):
    @abstractmethod
    def schedule(self, service_id: str, order_id: str) -> None: ...
