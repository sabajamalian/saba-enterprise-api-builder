from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from saba_api.database import PurchaseRequest
from saba_api.main import create_app
from tests.contracts import assert_problem

BASE = "/api/v1/purchase-requests"


def test_create_get_list_and_persistence(client, app, settings, authorization, purchase):
    created = client.post(BASE, json=purchase, headers=authorization)
    assert created.status_code == 201
    body = created.json()
    UUID(body["id"])
    assert body["amount"] == "1234.56"
    assert body["created_at"].endswith("Z")
    assert set(body) == {"id", "title", "description", "amount", "currency", "created_at"}
    assert client.get(f"{BASE}/{body['id']}", headers=authorization).json() == body
    assert client.get(BASE, headers=authorization).json() == {"items": [body], "limit": 25, "offset": 0}
    with app.state.sessions() as session:
        record = session.scalar(select(PurchaseRequest))
        assert record.owner_id == "alice"
        assert record.amount_cents == 123456
        assert record.amount == Decimal("1234.56")
    with TestClient(create_app(settings)) as restarted:
        assert restarted.get(f"{BASE}/{body['id']}", headers=authorization).json() == body


def test_health_is_public(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_isolation_and_missing_resource(client, token_factory, authorization, purchase):
    created = client.post(BASE, json=purchase, headers=authorization).json()
    other = {"Authorization": f"Bearer {token_factory(subject='bob')}"}
    assert client.get(BASE, headers=other).json()["items"] == []
    assert_problem(client.get(f"{BASE}/{created['id']}", headers=other), 404)
    assert_problem(client.get(f"{BASE}/{uuid4()}", headers=authorization), 404)
    second = client.post(BASE, json=purchase, headers=other).json()
    assert [item["id"] for item in client.get(BASE, headers=other).json()["items"]] == [second["id"]]
    assert [item["id"] for item in client.get(BASE, headers=authorization).json()["items"]] == [created["id"]]


@pytest.mark.parametrize("field,value", [
    ("owner_id", "bob"), ("extra", "secret-extra-value"), ("title", ""), ("title", "   "),
    ("title", "x" * 121), ("description", "x" * 2001), ("title", 123),
    ("currency", "usd"), ("currency", "US"), ("currency", "USDD"), ("currency", "123"),
    ("amount", 1.01), ("amount", 1), ("amount", "0"), ("amount", "0.00"),
    ("amount", "-0.01"), ("amount", "1000000000.00"), ("amount", "1.001"),
    ("amount", "NaN"), ("amount", "Infinity"), ("amount", "1e2"), ("amount", "01.00"),
    ("amount", " 1.00"), ("amount", None), ("amount", "1\n"), ("currency", "USD\n"),
])
def test_body_validation(client, authorization, purchase, field, value):
    response = client.post(BASE, json={**purchase, field: value}, headers=authorization)
    problem = assert_problem(response, 422)
    assert problem["errors"]
    assert "secret-extra-value" not in response.text


@pytest.mark.parametrize("amount,expected", [("0.01", "0.01"), ("999999999.99", "999999999.99"), ("1", "1.00"), ("0.1", "0.10")])
def test_exact_money_boundaries(client, authorization, purchase, amount, expected):
    response = client.post(BASE, json={**purchase, "amount": amount}, headers=authorization)
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == expected
    assert client.get(f"{BASE}/{body['id']}", headers=authorization).json()["amount"] == expected


def test_unknown_field_paths_and_invalid_json_are_redacted(client, authorization, purchase):
    response = client.post(BASE, json={**purchase, "secret-property-name": "secret-value"}, headers=authorization)
    body = assert_problem(response, 422)
    assert body["errors"] == [{"path": ["body", "<unknown>"], "code": "extra_forbidden"}]
    assert "secret-" not in response.text
    malformed = client.post(BASE, content='{"secret-value":', headers={**authorization, "Content-Type": "application/json"})
    assert_problem(malformed, 422)
    assert "secret-value" not in malformed.text


def test_invalid_uuid(client, authorization):
    assert_problem(client.get(f"{BASE}/not-a-uuid", headers=authorization), 422)


@pytest.mark.parametrize("query", ["limit=0", "limit=-1", "limit=101", "offset=-1", "limit=1.5", "offset=nope", "offset=9223372036854775808"])
def test_pagination_rejects_out_of_bounds(client, authorization, query):
    assert_problem(client.get(f"{BASE}?{query}", headers=authorization), 422)


def test_pagination_defaults_bounds_and_tiebreaker(client, app, authorization, purchase):
    with app.state.sessions() as session:
        common = {"owner_id": "alice", "title": purchase["title"], "description": "", "amount_cents": 1, "currency": "USD"}
        for index in reversed(range(105)):
            session.add(PurchaseRequest(
                **common, id=str(UUID(int=index + 1)), created_at=datetime(2026, 1, 1)
            ))
        session.add(PurchaseRequest(
            **common, id=str(UUID(int=1000)), created_at=datetime(2025, 1, 1)
        ))
        session.commit()
    page = client.get(BASE, headers=authorization).json()
    assert len(page["items"]) == 25
    assert [item["id"] for item in page["items"]] == [str(UUID(int=1000))] + [str(UUID(int=n)) for n in range(1, 25)]
    maximum = client.get(f"{BASE}?limit=100&offset=1", headers=authorization).json()
    assert len(maximum["items"]) == 100
    assert maximum["items"][-1]["id"] == str(UUID(int=100))
    assert client.get(f"{BASE}?limit=1&offset=105", headers=authorization).json()["items"][0]["id"] == str(UUID(int=105))
    assert client.get(f"{BASE}?offset=106", headers=authorization).json()["items"] == []


def test_not_found_and_method_headers(client):
    assert_problem(client.get("/missing"), 404)
    response = client.delete(BASE)
    assert_problem(response, 405)
    assert "Allow" in response.headers


def test_openapi_contract(client):
    document = client.get("/openapi.json").json()
    security = document["components"]["securitySchemes"]["BearerAuth"]
    assert security["type"] == "http" and security["scheme"] == "bearer"
    assert "purchase-requests:read" in security["description"]
    assert "purchase-requests:write" in security["description"]
    operations = [
        (BASE, "post", "createPurchaseRequest", "purchase-requests:write"),
        (BASE, "get", "listPurchaseRequests", "purchase-requests:read"),
        (BASE + "/{request_id}", "get", "getPurchaseRequest", "purchase-requests:read"),
    ]
    for path, method, operation_id, scope in operations:
        operation = document["paths"][path][method]
        assert operation["operationId"] == operation_id
        assert operation["security"] == [{"BearerAuth": []}]
        assert operation["x-required-scopes"] == [scope]
        for status in ("401", "403", "404", "405", "422", "500", "503"):
            response_contract = operation["responses"][status]
            content = response_contract["content"]
            assert set(content) == {"application/problem+json"}
            assert set(content["application/problem+json"]["schema"]["required"]) == {
                "type", "title", "status", "detail", "instance", "correlation_id",
            }
            assert "X-Correlation-ID" in response_contract["headers"]
            if status in ("401", "403"):
                assert "WWW-Authenticate" in response_contract["headers"]
            if status == "405":
                assert "Allow" in response_contract["headers"]
            if status == "503":
                assert "Retry-After" in response_contract["headers"]
    body = document["components"]["schemas"]["PurchaseRequestCreate"]
    assert body["additionalProperties"] is False
    assert body["properties"]["amount"]["type"] == "string"
    pagination = {param["name"]: param["schema"] for param in document["paths"][BASE]["get"]["parameters"]}
    assert pagination["limit"]["minimum"] == 1 and pagination["limit"]["maximum"] == 100
    assert pagination["limit"]["default"] == 25 and pagination["offset"]["minimum"] == 0

    def check_refs(node):
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"]
                assert ref.startswith("#/")
                target = document
                for part in ref[2:].split("/"):
                    target = target[part]
            for value in node.values():
                check_refs(value)
        elif isinstance(node, list):
            for value in node:
                check_refs(value)
    check_refs(document)
