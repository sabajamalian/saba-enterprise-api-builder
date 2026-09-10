import json
import logging
from uuid import UUID

import httpx
import pytest

from tests.contracts import assert_problem


@pytest.mark.parametrize("supplied", ["", "bad space", "bad/identifier", "bad?query", "a" * 65, "\u00e9"])
def test_invalid_correlation_is_replaced(client, supplied):
    response = client.get("/missing", headers={"X-Correlation-ID": supplied.encode("latin-1")})
    body = assert_problem(response, 404)
    UUID(body["correlation_id"])
    assert body["correlation_id"] != supplied


def test_duplicate_correlation_is_replaced(client):
    response = client.get("/health", headers=[("X-Correlation-ID", "first"), ("X-Correlation-ID", "second")])
    UUID(response.headers["x-correlation-id"])


@pytest.mark.parametrize("correlation", ["a", "a" * 64])
def test_correlation_length_boundaries(client, correlation):
    response = client.get("/health", headers={"X-Correlation-ID": correlation})
    assert response.headers["x-correlation-id"] == correlation


def test_problem_instance_encodes_path_without_query(client):
    response = client.get("/missing%3Fpath%23fragment%20space?secret=omitted")
    body = assert_problem(response, 404)
    assert body["instance"] == "/missing%3Fpath%23fragment%20space"
    assert "omitted" not in response.text


def test_valid_correlation_all_responses_and_safe_logs(client, authorization, purchase, caplog):
    caplog.set_level(logging.INFO, logger="saba_api.requests")
    correlation = "Trace_2026.09-09"
    headers = {**authorization, "X-Correlation-ID": correlation}
    purchase["description"] = "secret-body-text"
    created = client.post("/api/v1/purchase-requests?search=secret-query-text", json=purchase, headers=headers)
    assert created.status_code == 201 and created.headers["x-correlation-id"] == correlation
    resource_id = created.json()["id"]
    client.get(f"/api/v1/purchase-requests/{resource_id}", headers=headers)
    response = client.get("/not-a-resource-secret-path?search=secret-query-text", headers=headers)
    assert assert_problem(response, 404)["correlation_id"] == correlation
    records = [record for record in caplog.records if record.name == "saba_api.requests"]
    text = "\n".join(record.message for record in records)
    for secret in ("secret-body-text", "secret-query-text", "not-a-resource-secret-path", resource_id, authorization["Authorization"]):
        assert secret not in text
    parsed = [json.loads(record.message) for record in records]
    assert len(parsed) == 3
    assert all(entry["event"] == "request_completed" for entry in parsed)
    assert all(entry["correlation_id"] == correlation for entry in parsed)
    assert all(set(entry) == {"event", "method", "route", "status", "correlation_id", "duration_ms"} for entry in parsed)


def test_unexpected_error_is_safe_problem_and_logged(app, client, caplog):
    @app.get("/_failure")
    def failure():
        raise RuntimeError("secret-token-value secret-body-value")

    caplog.set_level(logging.INFO, logger="saba_api.requests")
    response = client.get("/_failure?password=secret-query-value", headers={"X-Correlation-ID": "Failure.Trace"})
    body = assert_problem(response, 500)
    assert body["correlation_id"] == "Failure.Trace"
    assert body["detail"] == "An unexpected error occurred."
    records = [record for record in caplog.records if record.name == "saba_api.requests"]
    assert len(records) == 2
    assert json.loads(records[0].message) == {"event": "request_failed", "correlation_id": "Failure.Trace"}
    assert json.loads(records[1].message)["status"] == 500
    assert all(record.exc_info is None for record in records)
    assert "secret-" not in response.text + "".join(record.message for record in records)


@pytest.mark.parametrize("malformed", [
    {"detail": "invalid"},
    {"type": "https://saba.example/problems/http-422", "title": "Invalid", "status": 200, "detail": "Invalid", "instance": "/", "correlation_id": "test"},
])
def test_contract_negative_fixture_rejects_malformed_problem(malformed):
    response = httpx.Response(
        422, json=malformed,
        headers={"Content-Type": "application/problem+json", "X-Correlation-ID": "test"},
    )
    with pytest.raises((AssertionError, KeyError)):
        assert_problem(response, 422)


def test_contract_negative_fixture_rejects_wrong_media_type():
    response = httpx.Response(500, json={"detail": "Internal server error"})
    with pytest.raises(AssertionError):
        assert_problem(response, 500)
