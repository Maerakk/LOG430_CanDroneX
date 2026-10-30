import logging
from concurrent.futures import ThreadPoolExecutor

from candronex_common import context
from slice_activation.domain.port.outbound import ActivationScheduler

log = logging.getLogger(__name__)


class ThreadPoolActivationScheduler(ActivationScheduler):
    # shortcut: la file est en mémoire et se perd si le conteneur s'arrête. Un courtier de messages la remplacera en Phase 3.
    def __init__(self, workers: int):
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="activation")
        self.activate = None

    def schedule(self, service_id: str, order_id: str) -> None:
        correlation = context.correlation_id.get()

        def run():
            context.correlation_id.set(correlation)
            context.order_id.set(order_id)
            try:
                self.activate(service_id)
            except Exception:
                log.exception("activation worker crashed", extra={"fields": {"serviceId": service_id}})

        self.executor.submit(run)


class InlineActivationScheduler(ActivationScheduler):
    """Pour les tests : active tout de suite."""

    def __init__(self):
        self.activate = None

    def schedule(self, service_id: str, order_id: str) -> None:
        self.activate(service_id)
