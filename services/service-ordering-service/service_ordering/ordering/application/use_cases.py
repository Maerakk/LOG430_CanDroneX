import logging
from datetime import datetime, timezone
from typing import Callable

from candronex_common import context
from candronex_common.errors import ServiceUnavailableError
from service_ordering.ordering.domain.errors import (DroneNotEligibleError, DroneNotFoundError,
                                                     IdempotencyKeyConflictError, OrderNotFoundError,
                                                     ServiceAlreadyOrderedError, UnknownServiceSpecificationError)
from service_ordering.ordering.domain.model import ItemRequest, OrderedService, ServiceOrder
from service_ordering.ordering.domain.port.inbound import GetServiceOrderUseCase, PlaceServiceOrderUseCase
from service_ordering.ordering.domain.port.outbound import (ActivationRequest, DroneDirectory, DuplicateIdempotencyKey,
                                                            ServiceActivation, ServiceCatalog, ServiceOrderRepository)

log = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ActivationTracker:
    """Demande l'activation des éléments qui ne l'ont pas encore et recopie l'état des services.

    Sans danger à rejouer : slice-activation ne crée qu'un service par élément.
    Si le service des slices ne répond pas, la commande garde son dernier état connu.
    """

    def __init__(self, activation: ServiceActivation, repository: ServiceOrderRepository):
        self.activation = activation
        self.repository = repository

    def refresh(self, order: ServiceOrder) -> None:
        if all(i.state.is_final for i in order.items):
            return
        changed = False
        try:
            for item in order.items:
                if item.activation_requested:
                    continue
                status = self.activation.request_activation(ActivationRequest(
                    order.order_id, item.item_id, item.drone_id, item.service.specification_id,
                    item.service.characteristics, order.accepted_at))
                changed |= item.track(status.service_id, status.state)
                log.info("activation requested", extra={"fields": {"serviceId": status.service_id}})
            if any(not i.state.is_final for i in order.items):
                by_item = {s.order_item_id: s for s in self.activation.statuses(order.order_id)}
                for item in order.items:
                    if item.item_id in by_item:
                        changed |= item.track(by_item[item.item_id].service_id, by_item[item.item_id].state)
        except ServiceUnavailableError:
            log.warning("activation service unavailable, order keeps its last known state")
        if changed:
            self.repository.update_items(order)


class PlaceServiceOrder(PlaceServiceOrderUseCase):
    def __init__(self, repository: ServiceOrderRepository, drones: DroneDirectory, catalog: ServiceCatalog,
                 tracker: ActivationTracker, clock: Callable[[], datetime] = utc_now):
        self.repository = repository
        self.drones = drones
        self.catalog = catalog
        self.tracker = tracker
        self.clock = clock

    def execute(self, client_id: str, idempotency_key: str, requests: list[ItemRequest]) -> tuple[ServiceOrder, bool]:
        """Une demande rejouée rend la commande existante."""
        ServiceOrder.check_idempotency_key(idempotency_key)
        replayed = self._replay(client_id, idempotency_key, requests)
        if replayed:
            return replayed, False

        ServiceOrder.validate(requests)
        drone_id = requests[0].drone_id
        drone = self.drones.find(drone_id, client_id)
        if drone is None:
            raise DroneNotFoundError(f"Drone '{drone_id}' not found.")
        if not drone.eligible:
            raise DroneNotEligibleError(f"Drone '{drone_id}' is not eligible for service.")

        items = []
        for r in requests:
            offer = self.catalog.find_orderable(r.specification_id)
            if offer is None:
                raise UnknownServiceSpecificationError(f"Service specification '{r.specification_id}' is not orderable.")
            if self.repository.has_blocking_item(client_id, drone_id, r.specification_id):
                raise ServiceAlreadyOrderedError(
                    f"Service '{r.specification_id}' is already being activated or active for drone '{drone_id}'.")
            items.append((r, OrderedService(offer.specification_id, offer.name, offer.characteristics)))

        order = ServiceOrder.create(client_id, idempotency_key, self.clock(), items)
        try:
            self.repository.add(order)
        except DuplicateIdempotencyKey:
            # deux requêtes identiques en même temps : la base a gardé la première
            replayed = self._replay(client_id, idempotency_key, requests)
            if replayed:
                return replayed, False
            raise
        context.order_id.set(order.order_id)
        log.info("service order accepted", extra={"fields": {"droneId": drone_id}})

        self.tracker.refresh(order)
        return order, True

    def _replay(self, client_id: str, key: str, requests: list[ItemRequest]) -> ServiceOrder | None:
        existing = self.repository.find_by_idempotency_key(key, client_id)
        if existing is None:
            return None
        if not existing.matches(requests):
            raise IdempotencyKeyConflictError("This Idempotency-Key was already used for a different order.")
        context.order_id.set(existing.order_id)
        log.info("service order replayed")
        self.tracker.refresh(existing)
        return existing


class GetServiceOrder(GetServiceOrderUseCase):
    def __init__(self, repository: ServiceOrderRepository, tracker: ActivationTracker):
        self.repository = repository
        self.tracker = tracker

    def execute(self, order_id: str, client_id: str) -> ServiceOrder:
        order = self.repository.get(order_id, client_id)
        if order is None:
            raise OrderNotFoundError(f"Service order '{order_id}' not found.")
        context.order_id.set(order.order_id)
        self.tracker.refresh(order)
        return order
