import re
from urllib.parse import urlsplit

import httpx


def assert_problem(response: httpx.Response, status: int) -> dict:
    """Reusable contract assertion. Never accept success-shaped error responses."""
    assert response.status_code == status
    assert response.headers["content-type"].split(";")[0] == "application/problem+json"
    body = response.json()
    assert isinstance(body, dict)
    for name in ("type", "title", "detail", "instance", "correlation_id"):
        assert isinstance(body[name], str) and body[name]
    assert body["status"] == status
    assert urlsplit(body["type"]).scheme in ("http", "https")
    assert body["instance"].startswith("/") and "?" not in body["instance"]
    assert re.fullmatch(r"[A-Za-z0-9._-]{1,64}", body["correlation_id"])
    assert response.headers["x-correlation-id"] == body["correlation_id"]
    if status == 401:
        assert response.headers["www-authenticate"].startswith("Bearer")
    if "errors" in body:
        assert isinstance(body["errors"], list)
        for error in body["errors"]:
            assert set(error) == {"path", "code"}
            assert isinstance(error["path"], list)
            assert all(isinstance(part, (str, int)) for part in error["path"])
            assert isinstance(error["code"], str) and error["code"]
    return body
