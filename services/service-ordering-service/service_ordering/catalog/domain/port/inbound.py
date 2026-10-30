from abc import ABC, abstractmethod

from service_ordering.catalog.domain.model import ServiceSpecification


class CatalogQueryUseCase(ABC):
    @abstractmethod
    def get(self, specification_id: str) -> ServiceSpecification | None: ...

    @abstractmethod
    def list_all(self) -> list[ServiceSpecification]: ...
