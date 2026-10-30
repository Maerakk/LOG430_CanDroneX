from service_ordering.catalog.domain.port.inbound import CatalogQueryUseCase
from service_ordering.ordering.domain.model import ServiceCharacteristic
from service_ordering.ordering.domain.port.outbound import OfferedService, ServiceCatalog


class InProcessServiceCatalog(ServiceCatalog):
    def __init__(self, queries: CatalogQueryUseCase):
        self.queries = queries

    def find_orderable(self, specification_id: str) -> OfferedService | None:
        spec = self.queries.get(specification_id)
        if spec is None or not spec.is_orderable():
            return None
        characteristics = (ServiceCharacteristic("sliceType", "string", spec.slice_type),) + tuple(
            ServiceCharacteristic(c.name, c.value_type, c.value) for c in spec.characteristics)
        return OfferedService(spec.id, spec.name, characteristics)
