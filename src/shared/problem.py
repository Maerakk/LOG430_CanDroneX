from flask import jsonify, Flask

from src.shared.errors import NotFoundError, ConflictError, RuleViolationError, DomainError
from src.shared.authentification import UnauthorizedError

STATUS_BY_ERROR_TYPE = [
    (UnauthorizedError, 401, "Unauthorized"),
    (NotFoundError, 404, "Not Found"),
    (ConflictError, 409, "Conflict"),
    (RuleViolationError, 422, "Business Error"),
    (ValueError, 422, "Invalid Data"),
]

def problem(status: int, title: str, detail: str):
    """Create a problem response."""
    response = jsonify({
        "status": status,
        "title": title,
        "detail": detail
    })
    response.status_code = status
    response.content_type = "application/problem+json"
    return response

def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the Flask app."""
    @app.errorhandler(DomainError)
    @app.errorhandler(ValueError)
    def handle_domain_error(error):
        for error_type, status, title in STATUS_BY_ERROR_TYPE:
            if isinstance(error, error_type):
                return problem(status, title, str(error))
        # Default to 500 Internal Server Error for unhandled DomainErrors
        return problem(500, "Internal Server Error", "An unexpected error occurred.")