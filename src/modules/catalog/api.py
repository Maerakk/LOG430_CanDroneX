from dataclasses import dataclass, asdict

from src.modules.catalog.domain.model import ServiceType
from src.modules.catalog.domain.ports import ServiceSpecificationRepository

@dataclass(frozen=True)
class ServiceSpecificationView:
    service_name: str
    service_type: str
    characteristics: dict[str, int | str]

class CatalogFacade:
    def __init__(self, service_specification_repository: ServiceSpecificationRepository):
        self.service_specification_repository = service_specification_repository

    def get_service_specification(self, service_type: str) -> ServiceSpecificationView | None:
        try:
            service_type_enum = ServiceType(service_type)
        except ValueError:
            return None
        service_spec = self.service_specification_repository.get(service_type_enum)
        if service_spec is None:
            return None
        return ServiceSpecificationView(
            service_name=service_spec.service_name,
            service_type=service_spec.service_type.value,
            characteristics=asdict(service_spec.characteristics)
        )