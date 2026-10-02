from abc import ABC, abstractmethod
from src.modules.orders.domain.model import ServiceOrder

class ServiceOrderRepository(ABC):
    @abstractmethod
    def save(self, order: ServiceOrder) -> None:
        pass

    @abstractmethod
    def get(self, order_id: str, customer_id: str) -> ServiceOrder | None:
        pass

    @abstractmethod
    def find_by_idempotency_key(self, idempotency_key: str, customer_id: str) -> ServiceOrder | None:
        pass

    @abstractmethod
    def has_open_item(self, drone_id: str, service_type: str, customer_id: str) -> bool:
        pass