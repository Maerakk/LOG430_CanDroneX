from candronex_common.errors import ConflictError, NotFoundError, RuleViolationError


class ServiceNotFoundError(NotFoundError):
    pass


class DroneNotFoundError(NotFoundError):
    pass


class DroneNotEligibleError(RuleViolationError):
    pass


class OrderItemConflictError(ConflictError):
    pass
