from enum import Enum

class ItemState(Enum):
    PENDING = "PENDING"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class OrderState(Enum):
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

def compute_order_state(item_states: list[ItemState]) -> OrderState:
    # Initialisation
    if all(state == ItemState.PENDING for state in item_states):
        return OrderState.ACKNOWLEDGED

    # Not finished, at least one item is still activating
    if any(state in (ItemState.ACTIVATING, ItemState.PENDING) for state in item_states):
        return OrderState.IN_PROGRESS

    # Everything is completed
    if all(state == ItemState.ACTIVE for state in item_states):
        return OrderState.COMPLETED
    if all(state == ItemState.CANCELLED for state in item_states):
        return OrderState.CANCELLED
    if any(state == ItemState.ACTIVE for state in item_states):
        return OrderState.PARTIALLY_COMPLETED

    # At least one item failed
    return OrderState.FAILED