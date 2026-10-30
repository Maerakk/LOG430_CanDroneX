# contextvars plutôt que flask.g pour que les threads d'activation y aient accès
from contextvars import ContextVar

correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
order_id: ContextVar[str | None] = ContextVar("order_id", default=None)
client_id: ContextVar[str | None] = ContextVar("client_id", default=None)
authorization: ContextVar[str | None] = ContextVar("authorization", default=None)
