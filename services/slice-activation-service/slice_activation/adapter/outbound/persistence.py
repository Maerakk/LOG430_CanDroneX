import copy
import threading
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from slice_activation.domain.model import Characteristic, Service, ServiceState
from slice_activation.domain.port.outbound import DuplicateOrderItem, ServiceInventory


def _naive(dt: datetime | None) -> datetime | None:
    return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt else None


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt else None


class Base(DeclarativeBase):
    pass


class ServiceRow(Base):
    __tablename__ = "service"

    service_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64))
    order_id: Mapped[str] = mapped_column(String(32))
    order_item_id: Mapped[str] = mapped_column(String(40))
    drone_id: Mapped[str] = mapped_column(String(32))
    imsi: Mapped[str] = mapped_column(String(15))
    specification_id: Mapped[str] = mapped_column(String(64))
    characteristics: Mapped[list] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16))
    accepted_at: Mapped[datetime] = mapped_column(DateTime)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime)
    failure_reason: Mapped[str | None] = mapped_column(String(128))
    attempts: Mapped[int]


def to_row(s: Service) -> ServiceRow:
    return ServiceRow(
        service_id=s.service_id, client_id=s.client_id, order_id=s.order_id, order_item_id=s.order_item_id,
        drone_id=s.drone_id, imsi=s.imsi, specification_id=s.specification_id,
        characteristics=[{"name": c.name, "valueType": c.value_type, "value": c.value} for c in s.characteristics],
        state=s.state.value, accepted_at=_naive(s.accepted_at), activated_at=_naive(s.activated_at),
        failure_reason=s.failure_reason, attempts=s.attempts)


def to_domain(r: ServiceRow) -> Service:
    return Service(
        r.service_id, r.client_id, r.order_id, r.order_item_id, r.drone_id, r.imsi, r.specification_id,
        tuple(Characteristic(c["name"], c["valueType"], c["value"]) for c in r.characteristics),
        _aware(r.accepted_at), ServiceState(r.state), _aware(r.activated_at), r.failure_reason, r.attempts)


class SqlServiceInventory(ServiceInventory):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def add(self, service: Service) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(to_row(service))
        except IntegrityError as e:
            raise DuplicateOrderItem() from e

    def save_transition(self, service: Service) -> bool:
        expected = service.previous_state or service.state
        with self.session_factory.begin() as session:
            result = session.execute(
                update(ServiceRow)
                .where(ServiceRow.service_id == service.service_id, ServiceRow.state == expected.value)
                .values(state=service.state.value, activated_at=_naive(service.activated_at),
                        failure_reason=service.failure_reason, attempts=service.attempts))
            return result.rowcount == 1

    def _one(self, *conditions) -> Service | None:
        with self.session_factory() as session:
            row = session.scalars(select(ServiceRow).where(*conditions)).first()
            return to_domain(row) if row else None

    def get_by_id(self, service_id: str) -> Service | None:
        return self._one(ServiceRow.service_id == service_id)

    def get(self, service_id: str, client_id: str) -> Service | None:
        return self._one(ServiceRow.service_id == service_id, ServiceRow.client_id == client_id)

    def find_by_order_item(self, order_item_id: str) -> Service | None:
        return self._one(ServiceRow.order_item_id == order_item_id)

    def search(self, client_id: str, order_id: str | None = None) -> list[Service]:
        query = select(ServiceRow).where(ServiceRow.client_id == client_id)
        if order_id:
            query = query.where(ServiceRow.order_id == order_id)
        with self.session_factory() as session:
            return [to_domain(r) for r in session.scalars(query.order_by(ServiceRow.order_item_id).limit(200))]


class InMemoryServiceInventory(ServiceInventory):
    def __init__(self):
        self.services: dict[str, Service] = {}
        self._lock = threading.Lock()

    def add(self, service: Service) -> None:
        with self._lock:
            if any(s.order_item_id == service.order_item_id for s in self.services.values()):
                raise DuplicateOrderItem()
            self.services[service.service_id] = copy.deepcopy(service)

    def save_transition(self, service: Service) -> bool:
        expected = service.previous_state or service.state
        with self._lock:
            stored = self.services.get(service.service_id)
            if stored is None or stored.state != expected:
                return False
            self.services[service.service_id] = copy.deepcopy(service)
            return True

    def _find(self, predicate) -> Service | None:
        with self._lock:
            return copy.deepcopy(next((s for s in self.services.values() if predicate(s)), None))

    def get_by_id(self, service_id: str) -> Service | None:
        return self._find(lambda s: s.service_id == service_id)

    def get(self, service_id: str, client_id: str) -> Service | None:
        return self._find(lambda s: s.service_id == service_id and s.client_id == client_id)

    def find_by_order_item(self, order_item_id: str) -> Service | None:
        return self._find(lambda s: s.order_item_id == order_item_id)

    def search(self, client_id: str, order_id: str | None = None) -> list[Service]:
        with self._lock:
            return [copy.deepcopy(s) for s in self.services.values()
                    if s.client_id == client_id and (not order_id or s.order_id == order_id)]
