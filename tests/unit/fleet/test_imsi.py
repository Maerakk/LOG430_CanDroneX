import pytest
from src.modules.fleet.domain.model import Imsi
from src.modules.fleet.domain.model import Iccid
from src.modules.fleet.domain.model import DroneId

def test_imsi_passed():
    imsi_value = "123456789012345"
    imsi = Imsi(imsi_value)
    assert imsi.value == imsi_value
    assert imsi.mcc() == "123"
    assert imsi.mnc() == "45"
    assert imsi.masked() == "12345******2345"

def test_imsi_too_short():
    with pytest.raises(ValueError):
        Imsi("12345678901234")  # 14 digits

def test_iccid_passed():
    iccid_value = "1234567890123456789"
    iccid = Iccid(iccid_value)
    assert iccid.value == iccid_value
    assert iccid.masked() == "123456**********789"

def test_iccid_too_short():
    with pytest.raises(ValueError):
        Iccid("123456789012345678")  # 18 digits

def test_droneid_passed():
    drone_id_value = "drone-123"
    drone_id = DroneId(drone_id_value)
    assert drone_id.value == drone_id_value

def test_droneid_too_short():
    with pytest.raises(ValueError):
        DroneId("dr")  # 2 characters