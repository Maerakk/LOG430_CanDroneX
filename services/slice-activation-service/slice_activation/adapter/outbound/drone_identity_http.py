from candronex_common.errors import ServiceUnavailableError
from candronex_common.http_client import ServiceClient
from slice_activation.domain.port.outbound import DroneIdentityProvider, NetworkIdentity


class HttpDroneIdentityProvider(DroneIdentityProvider):
    def __init__(self, base_url: str):
        self.client = ServiceClient(base_url, "drone-management-service")

    def network_identity(self, drone_id: str, client_id: str) -> NetworkIdentity | None:
        r = self.client.request("GET", f"/api/drone-management/v1/drone/{drone_id}/networkIdentity")
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise ServiceUnavailableError(f"drone-management-service answered {r.status_code}.")
        body = r.json()
        return NetworkIdentity(body["droneId"], body["imsi"], bool(body["eligible"]))
