import uuid
from dataclasses import dataclass

from src.modules.orders.domain.states import OrderState, ItemState, compute_order_state
from src.modules.orders.domain.errors import InvalidOrderError

@dataclass(eq=False)
class ServiceOrderItem:
    item_id: str
    drone_id: str
    service_type: str
    characteristics: dict[str, int | str]
    state: ItemState = ItemState.PENDING

@dataclass(eq=False)
class ServiceOrder:
    order_id: str
    customer_id: str
    idempotency_key: str
    items: list[ServiceOrderItem]

    @property
    def state(self) -> OrderState:
        return compute_order_state([item.state for item in self.items])

    @classmethod
    def create(cls, customer_id: str, idempotency_key: str, items: list[tuple[str,str,dict]]) -> 'ServiceOrder':

        if not items:
            raise InvalidOrderError("Order must contain at least one item.")

        drone_ids = {drone_id for drone_id, _, _ in items}
        if len(set(drone_ids)) > 1:
            raise InvalidOrderError("Order must be placed for a single drone")

        service_types = [service_type for _, service_type, _ in items]
        if len(service_types) != len(set(service_types)):
            raise InvalidOrderError("A service type can only be ordered once per order")

        order_id = f"SO-{uuid.uuid4().hex[:8]}"
        items = [
            ServiceOrderItem(
                item_id=f"{order_id}-{index}",
                drone_id=drone_id,
                service_type = service_type,
                characteristics=dict(characteristics),
            ) for index, (drone_id, service_type, characteristics) in enumerate(items, start=1)
        ]
        return cls(
            order_id=order_id,
            customer_id=customer_id,
            idempotency_key=idempotency_key,
            items=items)
