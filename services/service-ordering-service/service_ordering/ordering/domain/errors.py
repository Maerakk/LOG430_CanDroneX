from candronex_common.errors import ConflictError, InvalidValueError, NotFoundError, RuleViolationError


class InvalidOrderError(RuleViolationError):
    pass


class OrderNotFoundError(NotFoundError):
    pass


class DroneNotFoundError(NotFoundError):
    pass


class DroneNotEligibleError(RuleViolationError):
    pass


class UnknownServiceSpecificationError(RuleViolationError):
    pass


class ServiceAlreadyOrderedError(ConflictError):
    pass


class IdempotencyKeyConflictError(ConflictError):
    pass


class InvalidIdempotencyKeyError(InvalidValueError):
    pass
