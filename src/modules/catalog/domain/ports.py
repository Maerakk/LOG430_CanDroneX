from abc import ABC, abstractmethod
from src.modules.catalog.domain.model import ServiceSpecification, ServiceType

class ServiceSpecificationRepository(ABC):
    @abstractmethod
    def get(self, service_type: ServiceType) -> ServiceSpecification | None:
        pass

    @abstractmethod
    def get_list(self) -> list[ServiceSpecification]:
        pass