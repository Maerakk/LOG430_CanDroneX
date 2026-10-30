class CanDroneXError(Exception):
    status = 500
    title = "Internal Server Error"
    slug = "internal-error"

    def __init__(self, message: str | None = None):
        self.message = message or self.title
        super().__init__(self.message)


class BadRequestError(CanDroneXError):
    status, title, slug = 400, "Bad Request", "bad-request"


class UnauthorizedError(CanDroneXError):
    status, title, slug = 401, "Unauthorized", "unauthorized"


class NotFoundError(CanDroneXError):
    status, title, slug = 404, "Not Found", "not-found"


class ConflictError(CanDroneXError):
    status, title, slug = 409, "Conflict", "conflict"


class RuleViolationError(CanDroneXError):
    status, title, slug = 422, "Business Rule Violation", "business-rule"


class InvalidValueError(RuleViolationError):
    title, slug = "Invalid Value", "invalid-value"


class ServiceUnavailableError(CanDroneXError):
    status, title, slug = 503, "Service Unavailable", "service-unavailable"
