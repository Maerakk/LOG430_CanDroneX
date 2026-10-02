from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db import Base


class DroneRow(Base):
    __tablename__ = "drone"
    __table_args__ = {"schema": "fleet"}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(32))
    drone_id: Mapped[str] = mapped_column(String(32))
    imsi: Mapped[str] = mapped_column(String(15))
    iccid: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16))