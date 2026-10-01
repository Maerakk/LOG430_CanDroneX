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