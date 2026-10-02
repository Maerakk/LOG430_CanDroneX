from src.modules.catalog.domain.model import ServiceType, ServiceSpecification
from src.modules.catalog.domain.ports import ServiceSpecificationRepository


class InMemoryServiceSpecificationRepository(ServiceSpecificationRepository):
    def __init__(self):
        self.service_specifications: dict[ServiceType, ServiceSpecification] = {}

    def get(self, service_type: ServiceType) -> ServiceSpecification | None:
        return self.service_specifications.get(service_type, None)

    def get_list(self) -> list[ServiceSpecification]:
        return list(self.service_specifications.values())

    def add_service_specification(self, service_spec: ServiceSpecification) -> None:
        self.service_specifications[service_spec.service_type] = service_spec

