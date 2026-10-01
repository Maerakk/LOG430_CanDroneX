class DomainError(Exception):
    """Base class for domain-specific exceptions."""
    def __init__(self, message="A domain error occurred"):
        self.message = message
        super().__init__(self.message)

class NotfoundError(DomainError):
    """Exception raised when a requested resource is not found."""
    def __init__(self, message="Resource not found"):
        self.message = message
        super().__init__(self.message)

class ConflictError(DomainError):
    """Exception raised when there is a conflict with the current state of the resource."""
    def __init__(self, message="Resource conflict"):
        self.message = message
        super().__init__(self.message)