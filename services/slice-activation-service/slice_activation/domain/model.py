import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from candronex_common.errors import ConflictError, InvalidValueError


class ServiceState(Enum):
    PENDING = "PENDING"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"  # le réseau n'a jamais répondu : configuration peut-être appliquée


class InvalidTransitionError(ConflictError):
    pass


@dataclass(frozen=True)
class Characteristic:
    name: str
    value_type: str
    value: int | str


@dataclass(frozen=True)
class NetworkConfiguration:
    """Configuration à appliquer, dans le vocabulaire du domaine. service_id sert de clé d'idempotence."""
    service_id: str
    imsi: str
    slice_type: str
    sst: int
    sd: str
    dnn: str
    five_qi: int
    arp: int
    ambr_uplink_mbps: int
    ambr_downlink_mbps: int

    REQUIRED = {"sliceType": str, "sst": int, "sd": str, "dnn": str, "5qi": int, "arp": int,
                "ambrUplinkMbps": int, "ambrDownlinkMbps": int}

    @classmethod
    def build(cls, service_id: str, imsi: str, characteristics: tuple[Characteristic, ...]) -> "NetworkConfiguration":
        values = {c.name: c.value for c in characteristics}
        for name, kind in cls.REQUIRED.items():
            if not isinstance(values.get(name), kind):
                raise InvalidValueError(f"Characteristic '{name}' is missing or not a {kind.__name__}.")
        if not 1 <= values["sst"] <= 255 or len(values["sd"]) != 6:
            raise InvalidValueError("S-NSSAI is invalid (sst 1-255, sd 6 hex digits).")
        return cls(service_id, imsi, values["sliceType"], values["sst"], values["sd"], values["dnn"],
                   values["5qi"], values["arp"], values["ambrUplinkMbps"], values["ambrDownlinkMbps"])


@dataclass(eq=False)
class Service:
    service_id: str
    client_id: str
    order_id: str
    order_item_id: str
    drone_id: str
    imsi: str  # jamais renvoyé par l'API
    specification_id: str
    characteristics: tuple[Characteristic, ...]
    accepted_at: datetime
    state: ServiceState = ServiceState.PENDING
    activated_at: datetime | None = None
    failure_reason: str | None = None
    attempts: int = 0
    previous_state: ServiceState | None = field(default=None, repr=False)

    @classmethod
    def request(cls, client_id: str, order_id: str, order_item_id: str, drone_id: str, imsi: str,
                specification_id: str, characteristics: tuple[Characteristic, ...],
                accepted_at: datetime) -> "Service":
        service = cls(f"SVC-{uuid.uuid4().hex[:12]}", client_id, order_id, order_item_id, drone_id, imsi,
                      specification_id, characteristics, accepted_at)
        service.network_configuration()  # refuse une configuration inapplicable dès la demande
        return service

    def network_configuration(self) -> NetworkConfiguration:
        return NetworkConfiguration.build(self.service_id, self.imsi, self.characteristics)

    def same_request(self, client_id: str, drone_id: str, specification_id: str) -> bool:
        return (self.client_id, self.drone_id, self.specification_id) == (client_id, drone_id, specification_id)

    def _move(self, allowed_from: tuple[ServiceState, ...], to: ServiceState) -> None:
        if self.state not in allowed_from:
            raise InvalidTransitionError(f"Service {self.service_id} cannot go from {self.state.value} to {to.value}.")
        self.previous_state, self.state = self.state, to

    def start_activation(self) -> None:
        self._move((ServiceState.PENDING,), ServiceState.ACTIVATING)
        self.attempts += 1

    def retry(self) -> None:
        # délai dépassé : on ne sait pas si le réseau a appliqué la config, on réessaie
        self._move((ServiceState.ACTIVATING,), ServiceState.ACTIVATING)
        self.attempts += 1

    def activate(self, now: datetime) -> None:
        self._move((ServiceState.ACTIVATING,), ServiceState.ACTIVE)
        self.activated_at = now

    def fail(self, reason: str) -> None:
        self._move((ServiceState.ACTIVATING,), ServiceState.FAILED)
        self.failure_reason = reason

    def mark_unknown(self) -> None:
        self._move((ServiceState.ACTIVATING,), ServiceState.UNKNOWN)
        self.failure_reason = "NETWORK_TIMEOUT"
