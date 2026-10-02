from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.modules.orders.domain.model import ServiceOrder, ServiceOrderItem
from src.modules.orders.domain.ports import ServiceOrderRepository
from src.modules.orders.domain.states import ItemState
from src.modules.orders.domain.errors import IdempotencyKeyConflictError
from src.modules.orders.infrastructure.orm_models import ServiceOrderRow, ServiceOrderItemRow


def to_row(order: ServiceOrder) -> ServiceOrderRow:
    return ServiceOrderRow(
        order_id=order.order_id,
        customer_id=order.customer_id,
        idempotency_key=order.idempotency_key,
        items=[
            ServiceOrderItemRow(
                item_id=item.item_id, drone_id=item.drone_id, service_type=item.service_type,
                characteristics=item.characteristics, state=item.state.value,
            )
            for item in order.items
        ],
    )


def to_domain(row: ServiceOrderRow) -> ServiceOrder:
    return ServiceOrder(
        order_id=row.order_id,
        customer_id=row.customer_id,
        idempotency_key=row.idempotency_key,
        items=[
            ServiceOrderItem(
                item_id=item.item_id, drone_id=item.drone_id, service_type=item.service_type,
                characteristics=dict(item.characteristics), state=ItemState(item.state),
            )
            for item in row.items
        ],
    )


class SqlServiceOrderRepository(ServiceOrderRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save(self, order: ServiceOrder) -> None:
        try:
            # Une seule transaction : la commande ET ses éléments, ou rien du tout
            with self.session_factory.begin() as session:
                session.merge(to_row(order))      # merge : insère, ou met à jour si elle existe déjà
        except IntegrityError:
            # La contrainte UNIQUE (client, clé d'idempotence) a refusé un doublon
            raise IdempotencyKeyConflictError("This idempotency key was already used.")

    def get(self, order_id: str, customer_id: str) -> ServiceOrder | None:
        with self.session_factory() as session:
            row = session.scalars(
                select(ServiceOrderRow).where(ServiceOrderRow.order_id == order_id,
                                              ServiceOrderRow.customer_id == customer_id)
            ).first()
            return to_domain(row) if row else None

    def find_by_idempotency_key(self, idempotency_key: str, customer_id: str) -> ServiceOrder | None:
        with self.session_factory() as session:
            row = session.scalars(
                select(ServiceOrderRow).where(ServiceOrderRow.idempotency_key == idempotency_key,
                                              ServiceOrderRow.customer_id == customer_id)
            ).first()
            return to_domain(row) if row else None

    def has_open_item(self, drone_id: str, service_type: str, customer_id: str) -> bool:
        with self.session_factory() as session:
            item_id = session.scalars(
                select(ServiceOrderItemRow.item_id)
                .join(ServiceOrderRow)
                .where(ServiceOrderRow.customer_id == customer_id,
                       ServiceOrderItemRow.drone_id == drone_id,
                       ServiceOrderItemRow.service_type == service_type,
                       ServiceOrderItemRow.state.in_(["PENDING", "ACTIVATING"]))
            ).first()
            return item_id is not None