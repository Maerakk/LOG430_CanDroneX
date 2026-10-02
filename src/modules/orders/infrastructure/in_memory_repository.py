from src.modules.orders.domain.model import ServiceOrder
from src.modules.orders.domain.ports import ServiceOrderRepository
from src.modules.orders.domain.states import ItemState


class InMemoryServiceOrderRepository(ServiceOrderRepository):
    def __init__(self):
        self.orders: dict[tuple[str, str], ServiceOrder] = {}
        # Dictionary that fakes a database, with key as (order_id, customer_id) and value as ServiceOrder object

    def save(self, order: ServiceOrder) -> None:
        self.orders[(order.order_id, order.customer_id)] = order

    def get(self, order_id: str, customer_id: str) -> ServiceOrder | None:
        return self.orders.get((order_id, customer_id), None)

    def find_by_idempotency_key(self, idempotency_key: str, customer_id: str) -> ServiceOrder | None:
        for order in self.orders.values():
            if order.idempotency_key == idempotency_key and order.customer_id == customer_id:
                return order
        return None

    def has_open_item(self, drone_id: str, service_type: str, customer_id: str) -> bool:
        for order in self.orders.values():
            if order.customer_id != customer_id:
                continue
            for item in order.items:
                if (item.drone_id == drone_id and
                        item.service_type == service_type and
                        item.state in (ItemState.PENDING, ItemState.ACTIVATING)):
                    return True
        return False