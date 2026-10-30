import logging
import os
from datetime import datetime, timezone
from typing import Callable

from candronex_common import context
from slice_activation.domain.errors import (DroneNotEligibleError, DroneNotFoundError, OrderItemConflictError,
                                            ServiceNotFoundError)
from slice_activation.domain.model import Service, ServiceState
from slice_activation.domain.port.inbound import (ActivateServiceUseCase, ActivationCommand,
                                                  InventoryQueryUseCase, RequestActivationUseCase)
from slice_activation.domain.port.outbound import (ActivationScheduler, DroneIdentityProvider, DuplicateOrderItem,
                                                   NetworkProvisioningPort, ProvisioningRejected, ProvisioningTimeout,
                                                   ServiceInventory)

log = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RequestActivation(RequestActivationUseCase):
    """Un seul Service par élément de commande : une demande rejouée rend le service existant."""

    def __init__(self, inventory: ServiceInventory, drones: DroneIdentityProvider, scheduler: ActivationScheduler):
        self.inventory = inventory
        self.drones = drones
        self.scheduler = scheduler

    def execute(self, cmd: ActivationCommand) -> tuple[Service, bool]:
        context.order_id.set(cmd.order_id)
        existing = self._existing(cmd)
        if existing:
            return existing, False

        identity = self.drones.network_identity(cmd.drone_id, cmd.client_id)
        if identity is None:
            raise DroneNotFoundError(f"Drone '{cmd.drone_id}' not found.")
        if not identity.eligible:
            raise DroneNotEligibleError(f"Drone '{cmd.drone_id}' is not eligible for service.")

        service = Service.request(cmd.client_id, cmd.order_id, cmd.order_item_id, cmd.drone_id, identity.imsi,
                                  cmd.specification_id, cmd.characteristics, cmd.accepted_at)
        try:
            self.inventory.add(service)
        except DuplicateOrderItem:
            return self._existing(cmd), False
        log.info("activation request received", extra={"fields": {
            "serviceId": service.service_id, "specification": cmd.specification_id}})
        self.scheduler.schedule(service.service_id, service.order_id)
        return service, True

    def _existing(self, cmd: ActivationCommand) -> Service | None:
        existing = self.inventory.find_by_order_item(cmd.order_item_id)
        if existing is None:
            return None
        if not existing.same_request(cmd.client_id, cmd.drone_id, cmd.specification_id):
            raise OrderItemConflictError(f"Order item '{cmd.order_item_id}' already has a different service.")
        return existing


class ActivateService(ActivateServiceUseCase):
    def __init__(self, inventory: ServiceInventory, network: NetworkProvisioningPort,
                 max_attempts: int = int(os.environ.get("ACTIVATION_MAX_ATTEMPTS", "3")),
                 clock: Callable[[], datetime] = utc_now):
        self.inventory = inventory
        self.network = network
        self.max_attempts = max_attempts
        self.clock = clock

    def execute(self, service_id: str) -> None:
        service = self.inventory.get_by_id(service_id)
        if service is None or service.state != ServiceState.PENDING:
            return
        context.order_id.set(service.order_id)
        service.start_activation()
        if not self.inventory.save_transition(service):
            return  # déjà pris par un autre travailleur

        config = service.network_configuration()
        while True:
            fields = {"serviceId": service_id, "attempt": service.attempts}
            log.info("calling NetworkProvisioningPort.apply", extra={"fields": fields})
            try:
                self.network.apply(config)
                service.activate(self.clock())
                log.info("activation succeeded", extra={"fields": fields})
                break
            except ProvisioningRejected as e:
                service.fail(f"NETWORK_REJECTED: {e}")
                log.warning("activation failed: network rejected the configuration", extra={"fields": fields})
                break
            except ProvisioningTimeout:
                if service.attempts >= self.max_attempts:
                    service.mark_unknown()
                    log.error("activation outcome unknown: no answer after retries", extra={"fields": fields})
                    break
                log.warning("network timeout, retrying", extra={"fields": fields})
                service.retry()
                self.inventory.save_transition(service)
            except Exception:
                service.fail("INTERNAL_ERROR")
                log.exception("activation failed: unexpected error", extra={"fields": fields})
                break
        self.inventory.save_transition(service)


class InventoryQueries(InventoryQueryUseCase):
    def __init__(self, inventory: ServiceInventory):
        self.inventory = inventory

    def get(self, service_id: str, client_id: str) -> Service:
        service = self.inventory.get(service_id, client_id)
        if service is None:
            raise ServiceNotFoundError(f"Service '{service_id}' not found.")
        return service

    def search(self, client_id: str, order_id: str | None) -> list[Service]:
        return self.inventory.search(client_id, order_id)
