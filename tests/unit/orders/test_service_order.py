from src.modules.orders.domain.model import ServiceOrder
from src.modules.orders.domain.states import ItemState, OrderState
import pytest
from src.modules.orders.domain.errors import InvalidOrderError

C2_CHARACTERISTICS = {
    "sst": 2,
    "sd": "000001",
    "dnn": "c2",
    "five_qi": 7,
    "arp": 2,
    "ambr_uplink_mbps": 20,
    "ambr_downlink_mbps": 20
}

IMAGERY_CHARACTERISTICS = {
    "sst": 1,
    "sd": "000002",
    "dnn": "imagery",
    "five_qi": 9,
    "arp": 8,
    "ambr_uplink_mbps": 500,
    "ambr_downlink_mbps": 100
}

def test_valid_order():
    order = ServiceOrder.create("CUST-001", "IDEMPOTENCY-001", [
        ("DRN-0231", "C2", C2_CHARACTERISTICS),
        ("DRN-0231", "IMAGERY", IMAGERY_CHARACTERISTICS)
    ])
    assert len(order.items) == 2
    assert all(item.state == ItemState.PENDING for item in order.items)
    assert order.state == OrderState.ACKNOWLEDGED

def test_an_empty_order_is_refused():
    with pytest.raises(InvalidOrderError):
        ServiceOrder.create("CUST-001", "KEY-1", [])

def test_an_order_for_two_drones_is_refused():
    with pytest.raises(InvalidOrderError):
        ServiceOrder.create("CUST-001", "KEY-1", [
            ("DRN-0231", "C2", C2_CHARACTERISTICS),
            ("DRN-0999", "IMAGERY", IMAGERY_CHARACTERISTICS),
        ])

def test_the_same_service_twice_is_refused():
    with pytest.raises(InvalidOrderError):
        ServiceOrder.create("CUST-001", "KEY-1", [
            ("DRN-0231", "C2", C2_CHARACTERISTICS),
            ("DRN-0231", "C2", C2_CHARACTERISTICS),
        ])

def test_characteristics_are_frozen_in_the_order():
    characteristics = dict(C2_CHARACTERISTICS)
    order = ServiceOrder.create("CUST-001", "KEY-1", [("DRN-0231", "C2", characteristics)])
    characteristics["arp"] = 15
    assert order.items[0].characteristics["arp"] == 2