from candronex_common.errors import ServiceUnavailableError
from candronex_common.http_client import ServiceClient
from service_ordering.ordering.adapter.inbound.rest import iso
from service_ordering.ordering.domain.port.outbound import (ActivationRequest, ActivationStatus, DroneDirectory,
                                                            DroneReference, ServiceActivation)
from service_ordering.ordering.domain.states import ItemState


class HttpDroneDirectory(DroneDirectory):
    def __init__(self, base_url: str):
        self.client = ServiceClient(base_url, "drone-management-service")

    def find(self, drone_id: str, client_id: str) -> DroneReference | None:
        # le service des drones déduit le client du jeton retransmis
        r = self.client.request("GET", f"/api/drone-management/v1/drone/{drone_id}")
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise ServiceUnavailableError(f"drone-management-service answered {r.status_code}.")
        body = r.json()
        return DroneReference(body["droneId"], bool(body["eligible"]))


class HttpServiceActivation(ServiceActivation):
    def __init__(self, base_url: str):
        self.client = ServiceClient(base_url, "slice-activation-service")

    @staticmethod
    def _status(body: dict) -> ActivationStatus:
        return ActivationStatus(body["id"], body["orderItemId"], ItemState(body["state"]))

    def request_activation(self, request: ActivationRequest) -> ActivationStatus:
        r = self.client.request("POST", "/api/slice-activation/v1/service", json={
            "orderId": request.order_id,
            "orderItemId": request.order_item_id,
            "droneId": request.drone_id,
            "serviceSpecification": {"id": request.specification_id},
            "serviceCharacteristic": [{"name": c.name, "valueType": c.value_type, "value": c.value}
                                      for c in request.characteristics],
            "acceptedAt": iso(request.accepted_at),
        })
        if r.status_code not in (200, 202):
            raise ServiceUnavailableError(f"slice-activation-service refused the request ({r.status_code}).")
        return self._status(r.json())

    def statuses(self, order_id: str) -> list[ActivationStatus]:
        r = self.client.request("GET", "/api/slice-activation/v1/service", params={"orderId": order_id})
        if r.status_code != 200:
            raise ServiceUnavailableError(f"slice-activation-service answered {r.status_code}.")
        return [self._status(s) for s in r.json()]
