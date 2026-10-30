from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from service_ordering.ordering.domain.model import (ItemAction, OrderedService, ServiceCharacteristic,
                                                    ServiceOrder, ServiceOrderItem)
from service_ordering.ordering.domain.port.outbound import DuplicateIdempotencyKey, ServiceOrderRepository
from service_ordering.ordering.domain.states import ItemState

BLOCKING = [s.value for s in ItemState if s.blocks_new_order]


class OrderingBase(DeclarativeBase):
    pass


class ServiceOrderRow(OrderingBase):
    __tablename__ = "service_order"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    client_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    items: Mapped[list["ServiceOrderItemRow"]] = relationship(cascade="all, delete-orphan", lazy="selectin",
                                                              order_by="ServiceOrderItemRow.item_id")


class ServiceOrderItemRow(OrderingBase):
    __tablename__ = "service_order_item"

    item_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("service_order.order_id"))
    client_id: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))
    drone_id: Mapped[str] = mapped_column(String(32))
    specification_id: Mapped[str] = mapped_column(String(64))
    specification_name: Mapped[str] = mapped_column(String(128))
    characteristics: Mapped[list] = mapped_column(JSON)
    service_id: Mapped[str | None] = mapped_column(String(40))
    state: Mapped[str] = mapped_column(String(16))


def _naive_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_row(order: ServiceOrder) -> ServiceOrderRow:
    return ServiceOrderRow(
        order_id=order.order_id, client_id=order.client_id, idempotency_key=order.idempotency_key,
        accepted_at=_naive_utc(order.accepted_at),
        items=[ServiceOrderItemRow(
            item_id=i.item_id, client_id=order.client_id, action=i.action.value, drone_id=i.drone_id,
            specification_id=i.service.specification_id, specification_name=i.service.specification_name,
            characteristics=[{"name": c.name, "valueType": c.value_type, "value": c.value}
                             for c in i.service.characteristics],
            service_id=i.service.service_id, state=i.state.value) for i in order.items],
    )


def to_domain(row: ServiceOrderRow) -> ServiceOrder:
    return ServiceOrder(
        order_id=row.order_id, client_id=row.client_id, idempotency_key=row.idempotency_key,
        accepted_at=row.accepted_at.replace(tzinfo=timezone.utc),
        items=[ServiceOrderItem(
            i.item_id, ItemAction(i.action), i.drone_id,
            OrderedService(i.specification_id, i.specification_name,
                           tuple(ServiceCharacteristic(c["name"], c["valueType"], c["value"])
                                 for c in i.characteristics),
                           i.service_id),
            ItemState(i.state)) for i in row.items],
    )


class SqlServiceOrderRepository(ServiceOrderRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def add(self, order: ServiceOrder) -> None:
        try:
            with self.session_factory.begin() as session:
                session.add(to_row(order))
        except IntegrityError as e:
            raise DuplicateIdempotencyKey() from e

    def update_items(self, order: ServiceOrder) -> None:
        with self.session_factory.begin() as session:
            for i in order.items:
                session.execute(update(ServiceOrderItemRow).where(ServiceOrderItemRow.item_id == i.item_id)
                                .values(service_id=i.service.service_id, state=i.state.value))

    def _one(self, *conditions) -> ServiceOrder | None:
        with self.session_factory() as session:
            row = session.scalars(select(ServiceOrderRow).where(*conditions)).first()
            return to_domain(row) if row else None

    def get(self, order_id: str, client_id: str) -> ServiceOrder | None:
        return self._one(ServiceOrderRow.order_id == order_id, ServiceOrderRow.client_id == client_id)

    def find_by_idempotency_key(self, idempotency_key: str, client_id: str) -> ServiceOrder | None:
        return self._one(ServiceOrderRow.idempotency_key == idempotency_key, ServiceOrderRow.client_id == client_id)

    def has_blocking_item(self, client_id: str, drone_id: str, specification_id: str) -> bool:
        with self.session_factory() as session:
            return session.scalars(select(ServiceOrderItemRow.item_id).where(
                ServiceOrderItemRow.client_id == client_id, ServiceOrderItemRow.drone_id == drone_id,
                ServiceOrderItemRow.specification_id == specification_id,
                ServiceOrderItemRow.state.in_(BLOCKING))).first() is not None


class InMemoryServiceOrderRepository(ServiceOrderRepository):
    def __init__(self):
        self.orders: dict[str, ServiceOrder] = {}

    def add(self, order: ServiceOrder) -> None:
        if self.find_by_idempotency_key(order.idempotency_key, order.client_id):
            raise DuplicateIdempotencyKey()
        self.orders[order.order_id] = order

    def update_items(self, order: ServiceOrder) -> None:
        self.orders[order.order_id] = order

    def get(self, order_id: str, client_id: str) -> ServiceOrder | None:
        order = self.orders.get(order_id)
        return order if order and order.client_id == client_id else None

    def find_by_idempotency_key(self, idempotency_key: str, client_id: str) -> ServiceOrder | None:
        return next((o for o in self.orders.values()
                     if o.idempotency_key == idempotency_key and o.client_id == client_id), None)

    def has_blocking_item(self, client_id: str, drone_id: str, specification_id: str) -> bool:
        return any(o.client_id == client_id and i.drone_id == drone_id and i.service.specification_id == specification_id
                   and i.state.blocks_new_order for o in self.orders.values() for i in o.items)
