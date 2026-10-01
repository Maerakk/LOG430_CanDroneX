from dataclasses import dataclass

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