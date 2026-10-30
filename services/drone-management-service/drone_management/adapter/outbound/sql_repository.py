from sqlalchemy import String, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from drone_management.domain.errors import NetworkIdentityUnavailableError
from drone_management.domain.model import Drone, DroneId, DroneStatus, Iccid, Imsi
from drone_management.domain.port.outbound import DroneRepository


class Base(DeclarativeBase):
    pass


class DroneRow(Base):
    __tablename__ = "drone"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[str] = mapped_column(String(64))
    drone_id: Mapped[str] = mapped_column(String(32))
    imsi: Mapped[str] = mapped_column(String(15))
    iccid: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16))


def to_row(drone: Drone) -> DroneRow:
    return DroneRow(client_id=drone.client_id, drone_id=drone.drone_id.value, imsi=drone.imsi.value,
                    iccid=drone.iccid.value, status=drone.status.value)


def to_domain(row: DroneRow) -> Drone:
    return Drone(DroneId(row.drone_id), Imsi(row.imsi), Iccid(row.iccid), row.client_id, DroneStatus(row.status))


class SqlDroneRepository(DroneRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, drone: Drone) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(to_row(drone))
        except IntegrityError as e:
            raise NetworkIdentityUnavailableError("Network identity unavailable.") from e

    def get(self, drone_id: DroneId, client_id: str) -> Drone | None:
        with self.session_factory() as session:
            row = session.scalars(select(DroneRow).where(DroneRow.client_id == client_id,
                                                         DroneRow.drone_id == drone_id.value)).first()
            return to_domain(row) if row else None

    def list_by_client(self, client_id: str) -> list[Drone]:
        with self.session_factory() as session:
            rows = session.scalars(select(DroneRow).where(DroneRow.client_id == client_id)
                                   .order_by(DroneRow.id).limit(1000))
            return [to_domain(r) for r in rows]

    def imsi_in_use(self, imsi: Imsi) -> bool:
        with self.session_factory() as session:
            return session.scalars(select(DroneRow.id).where(DroneRow.imsi == imsi.value)).first() is not None

    def iccid_in_use(self, iccid: Iccid) -> bool:
        with self.session_factory() as session:
            return session.scalars(select(DroneRow.id).where(DroneRow.iccid == iccid.value)).first() is not None
