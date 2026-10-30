import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum

from service_ordering.ordering.domain.errors import InvalidIdempotencyKeyError, InvalidOrderError
from service_ordering.ordering.domain.states import ItemState, OrderState, compute_order_state


class ItemAction(Enum):
    ADD = "add"


@dataclass(frozen=True)
class ServiceCharacteristic:
    name: str
    value_type: str
    value: int | str


@dataclass(frozen=True)
class ItemRequest:
    action: str
    drone_id: str
    specification_id: str


@dataclass(frozen=True)
class OrderedService:
    specification_id: str
    specification_name: str
    characteristics: tuple[ServiceCharacteristic, ...]  # copiées du catalogue à la commande
    service_id: str | None = None  # attribué par slice-activation-service


@dataclass(eq=False)
class ServiceOrderItem:
    item_id: str
    action: ItemAction
    drone_id: str
    service: OrderedService
    state: ItemState = ItemState.PENDING

    @property
    def activation_requested(self) -> bool:
        return self.service.service_id is not None

    def track(self, service_id: str, state: ItemState) -> bool:
        changed = (self.service.service_id, self.state) != (service_id, state)
        self.service = replace(self.service, service_id=service_id)
        self.state = state
        return changed


@dataclass(eq=False)
class ServiceOrder:
    order_id: str
    client_id: str
    idempotency_key: str
    accepted_at: datetime
    items: list[ServiceOrderItem] = field(default_factory=list)

    @property
    def state(self) -> OrderState:
        return compute_order_state([i.state for i in self.items])

    def matches(self, requests: list[ItemRequest]) -> bool:
        mine = {(i.action.value, i.drone_id, i.service.specification_id) for i in self.items}
        return mine == {(r.action, r.drone_id, r.specification_id) for r in requests}

    @staticmethod
    def check_idempotency_key(key: str) -> None:
        if not (1 <= len(key) <= 64 and key.isascii() and key.isprintable()):
            raise InvalidIdempotencyKeyError("Idempotency-Key must be 1 to 64 printable ASCII characters.")

    @staticmethod
    def validate(requests: list[ItemRequest]) -> None:
        if not requests:
            raise InvalidOrderError("An order must contain at least one item.")
        if any(r.action != ItemAction.ADD.value for r in requests):
            raise InvalidOrderError("Only the 'add' action is supported.")
        if len({r.drone_id for r in requests}) > 1:
            raise InvalidOrderError("An order must target a single drone.")
        specs = [r.specification_id for r in requests]
        if len(specs) != len(set(specs)):
            raise InvalidOrderError("A service specification can only appear once per order.")

    @classmethod
    def create(cls, client_id: str, idempotency_key: str, accepted_at: datetime,
               items: list[tuple[ItemRequest, OrderedService]]) -> "ServiceOrder":
        cls.check_idempotency_key(idempotency_key)
        cls.validate([r for r, _ in items])
        order_id = f"SO-{uuid.uuid4().hex[:12]}"
        return cls(
            order_id=order_id, client_id=client_id, idempotency_key=idempotency_key, accepted_at=accepted_at,
            items=[ServiceOrderItem(f"{order_id}-{n}", ItemAction(r.action), r.drone_id, service)
                   for n, (r, service) in enumerate(items, start=1)],
        )
