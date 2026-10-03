from dataclasses import dataclass
from enum import Enum

class ServiceType(Enum):
    C2 = "C2"
    IMAGERY = "IMAGERY"

@dataclass(frozen=True)
class ServiceCharacteristics:
    # Network characteristics (Dossier de Domaine 7.3)
    sst: int
    sd: str
    dnn: str
    five_qi: int
    arp: int
    ambr_uplink_mbps: int
    ambr_downlink_mbps: int

@dataclass(frozen=True)
class ServiceSpecification:
    # Specifications for a service
    service_name: str
    service_type: ServiceType
    characteristics: ServiceCharacteristics