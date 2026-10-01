from dataclasses import dataclass
from enum import Enum

@dataclass(frozen=True)
class Imsi:
    value: str

    def __post_init__(self):
        if not self.value.isdigit() or len(self.value) != 15 or not self.value.isascii():
            raise ValueError("IMSI must be a 15-digit numeric string.")

    def mcc(self) -> str:
        return self.value[:3]

    def mnc(self) -> str:
        return self.value[3:5]

    def masked(self) -> str:
        return self.value[:5] + "******" + self.value[-4:]

@dataclass(frozen=True)
class Iccid:
    value: str

    def __post_init__(self):
        if not self.value.isdigit() or len(self.value) not in [19, 20] or not self.value.isascii():
            raise ValueError("ICCID must be a 19-digit or 20-digit numeric string.")

    def masked(self) -> str:
        return self.value[:6] + "*" * (len(self.value) - 9) + self.value[-3:]

@dataclass(frozen=True)
class DroneId:
    value: str

    def __post_init__(self):
        if not 3<= len(self.value) <= 32 or not self.value.isascii() or not self.value.replace("-", "").isalnum():
            raise ValueError("Drone ID must be a 3-32 character ASCII string containing only alphanumeric characters and hyphens.")

class DroneStatus(Enum):
    ACTIVE = "active"
    RETIRED = "retired"
    SUSPENDED = "suspended"

@dataclass(eq=False)
class Drone:
    drone_id: DroneId
    imsi: Imsi
    iccid: Iccid
    customer_id: str
    status: DroneStatus

    @classmethod
    def register(cls, id: DroneId, imsi: Imsi, iccid: Iccid, customer_id: str) -> 'Drone':
        return cls(
            drone_id=id,
            imsi=imsi,
            iccid=iccid,
            customer_id=customer_id,
            status=DroneStatus.ACTIVE)

    def is_eligible(self,) -> bool:
        return self.status == DroneStatus.ACTIVE

    def __eq__(self, other) -> bool:
        if not isinstance(other, Drone):
            return NotImplemented
        return (self.drone_id == other.drone_id and
                self.customer_id == other.customer_id)
