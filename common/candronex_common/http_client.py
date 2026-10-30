import logging
import os

import requests
from requests.adapters import HTTPAdapter

from candronex_common import context
from candronex_common.errors import ServiceUnavailableError

log = logging.getLogger(__name__)

CONNECT_TIMEOUT = 1
READ_TIMEOUT = float(os.environ.get("HTTP_READ_TIMEOUT_S", "3"))


class ServiceClient:
    def __init__(self, base_url: str, name: str):
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.session = requests.Session()
        self.session.mount("http://", HTTPAdapter(pool_maxsize=64))

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Renvoie les réponses 2xx et 4xx. Délai dépassé, connexion refusée ou 5xx : 503."""
        headers = kwargs.pop("headers", {})
        if context.authorization.get():
            headers["Authorization"] = context.authorization.get()
        if context.correlation_id.get():
            headers["X-Correlation-Id"] = context.correlation_id.get()
        try:
            response = self.session.request(method, self.base_url + path, headers=headers,
                                            timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), **kwargs)
        except requests.RequestException as e:
            log.warning("%s unreachable: %s %s (%s)", self.name, method, path, type(e).__name__)
            raise ServiceUnavailableError(f"{self.name} is unavailable.") from e
        if response.status_code >= 500:
            log.warning("%s answered %s: %s %s", self.name, response.status_code, method, path)
            raise ServiceUnavailableError(f"{self.name} is unavailable.")
        return response
