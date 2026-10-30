import logging
import re
import uuid

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from candronex_common import context
from candronex_common.errors import BadRequestError, CanDroneXError

CORRELATION_HEADER = "X-Correlation-Id"
VALID_CORRELATION = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
PROBLEM_BASE = "https://candronex.example/problems/"

log = logging.getLogger(__name__)


def problem(status: int, title: str, detail: str, slug: str):
    response = jsonify({
        "type": PROBLEM_BASE + slug,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.path,
        "correlationId": context.correlation_id.get(),
    })
    response.status_code = status
    response.content_type = "application/problem+json"
    if status == 401:
        response.headers["WWW-Authenticate"] = 'Bearer realm="candronex"'
    return response


def json_body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequestError("The request body must be a JSON object.")
    return data


def required(data: dict, name: str, kind: type = str):
    value = data.get(name)
    if value is None or not isinstance(value, kind) or (kind is str and not value.strip()):
        raise BadRequestError(f"Field '{name}' is required and must be a {kind.__name__}.")
    return value


def install(app: Flask) -> None:
    @app.before_request
    def read_correlation():
        cid = request.headers.get(CORRELATION_HEADER, "")
        g.correlation_id = cid if VALID_CORRELATION.match(cid) else str(uuid.uuid4())
        context.correlation_id.set(g.correlation_id)
        context.order_id.set(None)
        context.client_id.set(None)
        context.authorization.set(None)

    @app.after_request
    def send_correlation(response):
        if "correlation_id" in g:
            response.headers[CORRELATION_HEADER] = g.correlation_id
        return response

    @app.errorhandler(CanDroneXError)
    def known_error(error: CanDroneXError):
        if error.status >= 500:
            log.error("request failed: %s", error.message)
        return problem(error.status, error.title, error.message, error.slug)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return problem(error.code or 500, error.name, error.description or error.name,
                       error.name.lower().replace(" ", "-"))

    @app.errorhandler(Exception)
    def unexpected(error: Exception):
        log.exception("unexpected error")
        return problem(500, "Internal Server Error", "An unexpected error occurred.", "internal-error")

    @app.get("/health")
    def health():
        return {"status": "UP"}
