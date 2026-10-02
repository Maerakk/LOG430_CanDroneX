from functools import wraps
from flask import request, g

from src.shared.errors import DomainError

API_KEYS = {
    "demo_key_1": "CUST-001",
    "demo_key_2": "CUST-002",
}

class UnauthorizedError(DomainError):
    pass

def requires_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header:
            raise UnauthorizedError("Invalid or missing API key.")
        key = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else None
        customer_id = API_KEYS.get(key)
        if not customer_id:
            raise UnauthorizedError("Invalid or missing API key.")
        g.customer_id = customer_id
        return func(*args, **kwargs)
    return wrapper
