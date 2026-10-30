from abc import ABC, abstractmethod

from service_ordering.ordering.domain.model import ItemRequest, ServiceOrder


class PlaceServiceOrderUseCase(ABC):
    @abstractmethod
    def execute(self, client_id: str, idempotency_key: str, requests: list[ItemRequest]) -> tuple[ServiceOrder, bool]:
        """Retourne (commande, créée)."""


class GetServiceOrderUseCase(ABC):
    @abstractmethod
    def execute(self, order_id: str, client_id: str) -> ServiceOrder: ...
