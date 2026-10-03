from sqlalchemy import String, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.shared.db import Base


class ServiceOrderRow(Base):
    __tablename__ = "service_order"
    __table_args__ = {"schema": "orders"}

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(32))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    items: Mapped[list["ServiceOrderItemRow"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ServiceOrderItemRow.item_id")


class ServiceOrderItemRow(Base):
    __tablename__ = "service_order_item"
    __table_args__ = {"schema": "orders"}

    item_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.service_order.order_id"))
    drone_id: Mapped[str] = mapped_column(String(32))
    service_type: Mapped[str] = mapped_column(String(16))
    characteristics: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16))