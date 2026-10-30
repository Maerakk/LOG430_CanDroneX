from dataclasses import dataclass
from enum import Enum

from candronex_common.errors import InvalidValueError


@dataclass(frozen=True)
class Imsi:
    value: str

    def __post_init__(self):
        if not (isinstance(self.value, str) and self.value.isascii() and self.value.isdigit() and len(self.value) == 15):
            raise InvalidValueError("IMSI must be a 15-digit numeric string.")

    def masked(self) -> str:
        return self.value[:5] + "******" + self.value[-4:]


@dataclass(frozen=True)
class Iccid:
    value: str

    def __post_init__(self):
        if not (isinstance(self.value, str) and self.value.isascii() and self.value.isdigit()
                and len(self.value) in (19, 20)):
            raise InvalidValueError("ICCID must be a 19 or 20-digit numeric string.")

    def masked(self) -> str:
        return self.value[:6] + "*" * (len(self.value) - 9) + self.value[-3:]


@dataclass(frozen=True)
class DroneId:
    value: str

    def __post_init__(self):
        if not (isinstance(self.value, str) and 3 <= len(self.value) <= 32 and self.value.isascii()
                and self.value.replace("-", "").isalnum()):
            raise InvalidValueError("Drone ID must be 3 to 32 ASCII letters, digits or hyphens.")


class DroneStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


@dataclass(eq=False)
class Drone:
    drone_id: DroneId
    imsi: Imsi
    iccid: Iccid
    client_id: str
    status: DroneStatus

    @classmethod
    def register(cls, drone_id: DroneId, imsi: Imsi, iccid: Iccid, client_id: str) -> "Drone":
        return cls(drone_id, imsi, iccid, client_id, DroneStatus.ACTIVE)

    def is_eligible(self) -> bool:
        return self.status == DroneStatus.ACTIVE

    def same_identity(self, imsi: Imsi, iccid: Iccid) -> bool:
        return self.imsi == imsi and self.iccid == iccid

    def __eq__(self, other) -> bool:
        if not isinstance(other, Drone):
            return NotImplemented
        return self.drone_id == other.drone_id and self.client_id == other.client_id
