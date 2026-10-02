from sqlalchemy import select

from src.modules.catalog.domain.model import ServiceSpecification, ServiceType, ServiceCharacteristics
from src.modules.catalog.domain.ports import ServiceSpecificationRepository
from src.modules.catalog.infrastructure.orm_models import ServiceSpecificationRow


def to_domain(row: ServiceSpecificationRow) -> ServiceSpecification:
    return ServiceSpecification(
        service_name=row.service_name,
        service_type=ServiceType(row.service_type),
        characteristics=ServiceCharacteristics(
            sst=row.sst, sd=row.sd, dnn=row.dnn, five_qi=row.five_qi, arp=row.arp,
            ambr_uplink_mbps=row.ambr_uplink_mbps, ambr_downlink_mbps=row.ambr_downlink_mbps,
        ),
    )


class SqlServiceSpecificationRepository(ServiceSpecificationRepository):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def get(self, service_type: ServiceType) -> ServiceSpecification | None:
        with self.session_factory() as session:
            row = session.get(ServiceSpecificationRow, service_type.value)   # recherche par clé primaire
            return to_domain(row) if row else None

    def get_list(self) -> list[ServiceSpecification]:
        with self.session_factory() as session:
            return [to_domain(row) for row in session.scalars(select(ServiceSpecificationRow))]