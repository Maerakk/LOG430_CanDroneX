from src.shared.errors import RuleViolationError, ConflictError, NotFoundError


class InvalidOrderError(RuleViolationError):
    """Exception raised when an order is invalid."""
    def __init__(self, message="Invalid order"):
        self.message = message
        super().__init__(self.message)

class OrderNotFoundError(NotFoundError):
    """Exception raised when an order is not found."""
    def __init__(self, message="Order not found"):
        self.message = message
        super().__init__(self.message)

class DroneNotEligibleError(RuleViolationError):
    """Exception raised when a drone is not eligible for the requested service."""
    def __init__(self, message="Drone not eligible for the requested service"):
        self.message = message
        super().__init__(self.message)

class UnknownServiceTypeError(RuleViolationError):
    """Exception raised when an unknown service type is requested."""
    def __init__(self, message="Unknown service type"):
        self.message = message
        super().__init__(self.message)

class ServiceAlreadyOrderedError(ConflictError):
    """Exception raised when a service has already been ordered for the drone."""
    def __init__(self, message="Service has already been ordered for the drone"):
        self.message = message
        super().__init__(self.message)

class IdempotencyKeyConflictError(ConflictError):
    """Exception raised when there is a conflict with the idempotency key."""
    def __init__(self, message="Idempotency key conflict"):
        self.message = message
        super().__init__(self.message)

class DroneNotFoundError(NotFoundError):
    """Exception raised when a drone is not found."""
    def __init__(self, message="Drone not found"):
        self.message = message
        super().__init__(self.message)