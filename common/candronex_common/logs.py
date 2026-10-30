import json
import logging
import sys
from datetime import datetime, timezone

from candronex_common import context


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "service": self.service,
            "level": record.levelname,
            "logger": "audit" if record.name == "audit" else "app",
            "message": record.getMessage(),
            "orderId": context.order_id.get(),
            "correlationId": context.correlation_id.get(),
            "clientId": context.client_id.get(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps({k: v for k, v in entry.items() if v is not None}, ensure_ascii=False)


def configure(service: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def audit(action: str, resource: str, **fields) -> None:
    logging.getLogger("audit").info(action, extra={"fields": {"resource": resource, **fields}})
