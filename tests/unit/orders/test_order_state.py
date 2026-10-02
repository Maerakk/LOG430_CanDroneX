from src.modules.orders.domain.states import ItemState, OrderState, compute_order_state

def test_all_pending_is_acknowledged():
    assert compute_order_state([ItemState.PENDING, ItemState.PENDING]) == OrderState.ACKNOWLEDGED

def test_all_active_is_completed():
    assert compute_order_state([ItemState.ACTIVE, ItemState.ACTIVE]) == OrderState.COMPLETED

def test_c2_active_and_imagery_failed_is_partially_completed():
    assert compute_order_state([ItemState.ACTIVE, ItemState.FAILED]) == OrderState.PARTIALLY_COMPLETED

def test_one_failed_and_one_pending_is_in_progress():
    assert compute_order_state([ItemState.FAILED, ItemState.PENDING]) == OrderState.IN_PROGRESS

def test_one_active_and_one_pending_is_in_progress():
    assert compute_order_state([ItemState.ACTIVE, ItemState.PENDING]) == OrderState.IN_PROGRESS

def test_all_failed_is_failed():
    assert compute_order_state([ItemState.FAILED, ItemState.FAILED]) == OrderState.FAILED

def test_all_cancelled_is_cancelled():
    assert compute_order_state([ItemState.CANCELLED, ItemState.CANCELLED]) == OrderState.CANCELLED