from src.modules.catalog.domain.model import ServiceSpecification, ServiceType, ServiceCharacteristics
from src.modules.catalog.api import CatalogFacade
from src.modules.catalog.infrastructure.in_memory_repository import InMemoryServiceSpecificationRepository

C2 = ServiceSpecification(
    service_name="C2 Service",
    service_type=ServiceType.C2,
    characteristics=ServiceCharacteristics(
        sst=2,
        sd="000001",
        dnn="c2",
        five_qi=7,
        arp=2,
        ambr_uplink_mbps=20,
        ambr_downlink_mbps=20
    ),
)

def create_facade_with_c2_service() -> CatalogFacade:
    fake_repo = InMemoryServiceSpecificationRepository()
    fake_repo.add_service_specification(C2)
    return CatalogFacade(fake_repo)

def test_existing_service_type_returns_specification():
    facade = create_facade_with_c2_service()
    spec_view = facade.get_service_specification("C2")
    assert spec_view is not None
    assert spec_view.service_name == "C2 Service"
    assert spec_view.service_type == "C2"
    assert spec_view.characteristics["sst"] == 2
    assert spec_view.characteristics["sd"] == "000001"
    assert spec_view.characteristics["dnn"] == "c2"
    assert spec_view.characteristics["five_qi"] == 7
    assert spec_view.characteristics["arp"] == 2
    assert spec_view.characteristics["ambr_uplink_mbps"] == 20
    assert spec_view.characteristics["ambr_downlink_mbps"] == 20

def test_non_existing_service_type_returns_none():
    facade = create_facade_with_c2_service()
    spec_view = facade.get_service_specification("IMAGERY")
    assert spec_view is None

def test_unknown_service_type_returns_none():
    facade = create_facade_with_c2_service()
    spec_view = facade.get_service_specification("UNKNOWN")
    assert spec_view is None