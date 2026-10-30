from flask import Blueprint, jsonify

from candronex_common.auth import requires_client
from service_ordering.catalog.domain.model import ServiceSpecification
from service_ordering.catalog.domain.port.inbound import CatalogQueryUseCase

BASE = "/api/service-catalog/v1"


def specification_to_json(spec: ServiceSpecification) -> dict:
    return {
        "id": spec.id,
        "name": spec.name,
        "sliceType": spec.slice_type,
        "lifecycleStatus": spec.lifecycle_status,
        "serviceSpecCharacteristic": [
            {"name": c.name, "valueType": c.value_type, "value": c.value} for c in spec.characteristics],
    }


def create_blueprint(queries: CatalogQueryUseCase) -> Blueprint:
    bp = Blueprint("service_catalog", __name__, url_prefix=BASE)

    @bp.get("/serviceSpecification")
    @requires_client
    def list_specifications():
        return jsonify([specification_to_json(s) for s in queries.list_all()])

    return bp
