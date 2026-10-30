from enum import Enum


class ItemState(Enum):
    PENDING = "PENDING"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"  # délai dépassé : on ne sait pas si le réseau a appliqué la configuration
    CANCELLED = "CANCELLED"

    @property
    def is_final(self) -> bool:
        return self in (ItemState.ACTIVE, ItemState.FAILED, ItemState.CANCELLED)

    @property
    def blocks_new_order(self) -> bool:
        return self in (ItemState.PENDING, ItemState.ACTIVATING, ItemState.ACTIVE, ItemState.UNKNOWN)


class OrderState(Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def compute_order_state(item_states: list[ItemState]) -> OrderState:
    if all(s == ItemState.PENDING for s in item_states):
        return OrderState.ACKNOWLEDGED
    if any(s in (ItemState.PENDING, ItemState.ACTIVATING, ItemState.UNKNOWN) for s in item_states):
        return OrderState.IN_PROGRESS
    if all(s == ItemState.ACTIVE for s in item_states):
        return OrderState.COMPLETED
    if all(s == ItemState.CANCELLED for s in item_states):
        return OrderState.CANCELLED
    if any(s == ItemState.ACTIVE for s in item_states):
        return OrderState.PARTIALLY_COMPLETED
    return OrderState.FAILED
