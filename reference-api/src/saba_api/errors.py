import json
import logging
import re
import time
from http import HTTPStatus
from urllib.parse import quote
from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from saba_api.schemas import Problem

logger = logging.getLogger("saba_api.requests")
CORRELATION_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,64}", flags=re.ASCII)
DETAILS = {
    401: "A valid bearer token is required.",
    403: "The token does not grant the required scope.",
    404: "The requested resource was not found.",
    405: "The HTTP method is not allowed for this resource.",
    422: "The request failed validation.",
    500: "An unexpected error occurred.",
    503: "Identity verification is temporarily unavailable.",
}


def problem_response(
    status: int,
    scope: Scope,
    headers: dict[str, str] | None = None,
    errors: list[dict] | None = None,
) -> JSONResponse:
    try:
        title = HTTPStatus(status).phrase
    except ValueError:
        title = "Request failed"
    content = {
        "type": f"https://saba.example/problems/http-{status}",
        "title": title,
        "status": status,
        "detail": DETAILS.get(status, "The request could not be completed."),
        "instance": quote(scope["path"], safe="/:@!$&'()*+,;=-._~"),
        "correlation_id": scope["state"]["correlation_id"],
    }
    if errors is not None:
        content["errors"] = errors
    return JSONResponse(content, status_code=status, media_type="application/problem+json", headers=headers)


async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
    return problem_response(exc.status_code, request.scope, headers=exc.headers)


async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    allowed = {"body", "query", "path", "header", "title", "description", "amount", "currency", "request_id", "limit", "offset"}
    errors = [
        {
            "path": [part if isinstance(part, int) or part in allowed else "<unknown>" for part in error["loc"]],
            "code": error["type"],
        }
        for error in exc.errors()
    ]
    return problem_response(422, request.scope, errors=errors)


def error_responses(*statuses: int) -> dict:
    schema = Problem.model_json_schema()
    definitions = schema.pop("$defs", {})
    # Inline the one nested model so its references don't point at the OpenAPI root.
    for option in schema["properties"]["errors"]["anyOf"]:
        if option.get("type") == "array":
            option["items"] = definitions["ValidationIssue"]
    return {
        status: {
            "description": DETAILS[status],
            "content": {"application/problem+json": {"schema": schema}},
            "headers": {
                "X-Correlation-ID": {"schema": {"type": "string"}, "description": "Validated or generated request correlation ID"},
                **({"WWW-Authenticate": {"schema": {"type": "string"}}} if status in (401, 403) else {}),
                **({"Allow": {"schema": {"type": "string"}}} if status == 405 else {}),
                **({"Retry-After": {"schema": {"type": "string"}, "description": "Seconds before retrying identity verification"}} if status == 503 else {}),
            },
        }
        for status in statuses
    }


class RequestBoundary:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        values = [value.decode("latin-1") for key, value in scope["headers"] if key.lower() == b"x-correlation-id"]
        supplied = values[0] if len(values) == 1 else ""
        correlation_id = supplied if CORRELATION_PATTERN.fullmatch(supplied) else str(uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        started = time.monotonic()
        status = 500
        response_started = False

        async def send_with_correlation(message: Message) -> None:
            nonlocal status, response_started
            if message["type"] == "http.response.start":
                status = message["status"]
                response_started = True
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-correlation-id"]
                message["headers"] = headers + [(b"x-correlation-id", correlation_id.encode("ascii"))]
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        except Exception:
            # This is the single unexpected-error boundary. Exception text and traceback
            # may contain credentials or request data and must not reach these logs.
            logger.error(json.dumps({"event": "request_failed", "correlation_id": correlation_id}))
            if response_started:
                raise
            await problem_response(500, scope)(scope, receive, send_with_correlation)
        finally:
            route = scope.get("route")
            logger.info(
                json.dumps(
                    {
                        "event": "request_completed",
                        "method": scope["method"],
                        "route": getattr(route, "path", "<unmatched>"),
                        "status": status,
                        "correlation_id": correlation_id,
                        "duration_ms": round((time.monotonic() - started) * 1000, 3),
                    }
                )
            )
