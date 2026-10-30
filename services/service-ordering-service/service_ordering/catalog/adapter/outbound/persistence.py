from sqlalchemy import ForeignKey, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from service_ordering.catalog.domain.model import CharacteristicValue, ServiceSpecification

from service_ordering.catalog.domain.port.outbound import ServiceSpecificationRepository


class CatalogBase(DeclarativeBase):
    pass


class ServiceSpecificationRow(CatalogBase):
    __tablename__ = "service_specification"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    slice_type: Mapped[str] = mapped_column(String(16))
    lifecycle_status: Mapped[str] = mapped_column(String(16))
    characteristics: Mapped[list["CharacteristicRow"]] = relationship(lazy="selectin",
                                                                      order_by="CharacteristicRow.position")


class CharacteristicRow(CatalogBase):
    __tablename__ = "service_spec_characteristic"

    specification_id: Mapped[str] = mapped_column(ForeignKey("service_specification.id"), primary_key=True)
    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    position: Mapped[int]
    value_type: Mapped[str] = mapped_column(String(16))
    value: Mapped[str] = mapped_column(String(64))


def to_domain(row: ServiceSpecificationRow) -> ServiceSpecification:
    return ServiceSpecification(
        id=row.id, name=row.name, slice_type=row.slice_type, lifecycle_status=row.lifecycle_status,
        characteristics=tuple(
            CharacteristicValue(c.name, c.value_type, int(c.value) if c.value_type == "integer" else c.value)
            for c in row.characteristics),
    )


class SqlServiceSpecificationRepository(ServiceSpecificationRepository):
    # shortcut: catalogue lu une seule fois au démarrage, redémarrer le service après une modification
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._cache: dict[str, ServiceSpecification] | None = None

    def _all(self) -> dict[str, ServiceSpecification]:
        if self._cache is None:
            with self.session_factory() as session:
                rows = session.scalars(select(ServiceSpecificationRow).order_by(ServiceSpecificationRow.id))
                self._cache = {r.id: to_domain(r) for r in rows}
        return self._cache

    def get(self, specification_id: str) -> ServiceSpecification | None:
        return self._all().get(specification_id)

    def list_all(self) -> list[ServiceSpecification]:
        return list(self._all().values())


class InMemoryServiceSpecificationRepository(ServiceSpecificationRepository):
    def __init__(self, specifications: list[ServiceSpecification] = ()):
        self.specifications = {s.id: s for s in specifications}

    def get(self, specification_id: str) -> ServiceSpecification | None:
        return self.specifications.get(specification_id)

    def list_all(self) -> list[ServiceSpecification]:
        return list(self.specifications.values())
