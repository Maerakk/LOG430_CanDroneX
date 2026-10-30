from service_ordering.catalog.domain.model import ServiceSpecification
from service_ordering.catalog.domain.port.inbound import CatalogQueryUseCase
from service_ordering.catalog.domain.port.outbound import ServiceSpecificationRepository


class CatalogQueries(CatalogQueryUseCase):
    def __init__(self, repository: ServiceSpecificationRepository):
        self.repository = repository

    def get(self, specification_id: str) -> ServiceSpecification | None:
        return self.repository.get(specification_id)

    def list_all(self) -> list[ServiceSpecification]:
        return self.repository.list_all()
