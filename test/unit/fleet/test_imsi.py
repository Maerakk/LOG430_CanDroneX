import pytest
from src.modules.fleet.domain.model import Imsi

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