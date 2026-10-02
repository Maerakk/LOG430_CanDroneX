from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.modules.fleet.domain.model import Drone, DroneId, Imsi, Iccid, DroneStatus
from src.modules.fleet.domain.ports import DroneRepository
from src.modules.fleet.domain.errors import NetworkIdentifierError
from src.modules.fleet.infrastructure.orm_models import DroneRow


def to_row(drone: Drone) -> DroneRow:
    return DroneRow(
        customer_id=drone.customer_id,
        drone_id=drone.drone_id.value,
        imsi=drone.imsi.value,
        iccid=drone.iccid.value,
        status=drone.status.value,
    )


def to_domain(row: DroneRow) -> Drone:
    return Drone(
        drone_id=DroneId(row.drone_id),
        imsi=Imsi(row.imsi),
        iccid=Iccid(row.iccid),
        customer_id=row.customer_id,
        status=DroneStatus(row.status),
    )


class SqlDroneRepository(DroneRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, drone: Drone) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(to_row(drone))
        except IntegrityError:
            raise NetworkIdentifierError("Network identity unavailable.")

    def get(self, drone_id: DroneId, customer_id: str) -> Drone | None:
        with self.session_factory() as session:
            row = session.scalars(
                select(DroneRow).where(DroneRow.customer_id == customer_id,
                                       DroneRow.drone_id == drone_id.value)
            ).first()
            return to_domain(row) if row else None

    def imsi_in_use(self, imsi: Imsi) -> bool:
        with self.session_factory() as session:
            return session.scalars(select(DroneRow.id).where(DroneRow.imsi == imsi.value)).first() is not None

    def iccid_in_use(self, iccid: Iccid) -> bool:
        with self.session_factory() as session:
            return session.scalars(select(DroneRow.id).where(DroneRow.iccid == iccid.value)).first() is not None