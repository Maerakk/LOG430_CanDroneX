import logging
import os
import random
import threading
import time

from slice_activation.domain.model import NetworkConfiguration
from slice_activation.domain.port.outbound import NetworkProvisioningPort, ProvisioningRejected, ProvisioningTimeout

log = logging.getLogger(__name__)


class MockOpen5GSAdapter(NetworkProvisioningPort):
    """Simule le cœur 5G sans s'y connecter. Paramètres : MOCK_LATENCY_MIN_MS, MOCK_LATENCY_MAX_MS,
    MOCK_FAILURE_RATE, MOCK_TIMEOUT_RATE."""

    def __init__(self, latency_min_ms=None, latency_max_ms=None, failure_rate=None, timeout_rate=None,
                 sleep=time.sleep):
        env = os.environ.get
        self.latency_min_ms = float(env("MOCK_LATENCY_MIN_MS", "300") if latency_min_ms is None else latency_min_ms)
        self.latency_max_ms = float(env("MOCK_LATENCY_MAX_MS", "1500") if latency_max_ms is None else latency_max_ms)
        self.failure_rate = float(env("MOCK_FAILURE_RATE", "0") if failure_rate is None else failure_rate)
        self.timeout_rate = float(env("MOCK_TIMEOUT_RATE", "0") if timeout_rate is None else timeout_rate)
        if not (0 <= self.latency_min_ms <= self.latency_max_ms and 0 <= self.failure_rate <= 1
                and 0 <= self.timeout_rate <= 1):
            raise ValueError("Invalid MockOpen5GSAdapter configuration.")
        self.sleep = sleep
        self.applied: dict[str, NetworkConfiguration] = {}
        self.apply_calls = 0
        self._lock = threading.Lock()

    def apply(self, configuration: NetworkConfiguration) -> None:
        with self._lock:
            self.apply_calls += 1
        latency = random.uniform(self.latency_min_ms, self.latency_max_ms)
        draw = random.random()
        self.sleep(latency / 1000)
        if draw < self.timeout_rate:
            raise ProvisioningTimeout(f"no answer after {latency:.0f} ms")
        if draw < self.timeout_rate + self.failure_rate:
            raise ProvisioningRejected("simulated network failure")
        with self._lock:
            self.applied.setdefault(configuration.service_id, configuration)
        log.info("mock 5G core: configuration applied", extra={"fields": {
            "serviceId": configuration.service_id, "latencyMs": round(latency),
            "sst": configuration.sst, "sd": configuration.sd, "dnn": configuration.dnn}})
