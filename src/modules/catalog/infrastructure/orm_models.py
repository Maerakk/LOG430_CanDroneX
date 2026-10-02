from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db import Base


class ServiceSpecificationRow(Base):
    __tablename__ = "service_specification"
    __table_args__ = {"schema": "catalog"}

    service_type: Mapped[str] = mapped_column(String(16), primary_key=True)
    service_name: Mapped[str] = mapped_column(String(64))
    sst: Mapped[int]
    sd: Mapped[str] = mapped_column(String(6))
    dnn: Mapped[str] = mapped_column(String(32))
    five_qi: Mapped[int]
    arp: Mapped[int]
    ambr_uplink_mbps: Mapped[int]
    ambr_downlink_mbps: Mapped[int]