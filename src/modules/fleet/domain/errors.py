from src.shared.errors import ConflictError, NotFoundError

class DroneAlreadyRegisteredError(ConflictError):
    """This customer has already registered a drone with this drone ID."""
    def __init__(self, message="A drone with this ID is already registered for this customer"):
        super().__init__(message)

class NetworkIdentifierError(ConflictError):
    """Exception raised when there is a conflict with the network identifier (IMSI or ICCID)."""
    def __init__(self, message="Network identifier conflict"):
        super().__init__(message)

class DroneNotFoundError(NotFoundError):
    """Exception raised when a drone is not found."""
    def __init__(self, message="Drone not found"):
        super().__init__(message)

