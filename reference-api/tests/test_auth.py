import time

import pytest

from tests.contracts import assert_problem

BASE = "/api/v1/purchase-requests"


@pytest.mark.parametrize("authorization", [None, "", "Basic abc", "Bearer", "Bearer invalid-token"])
def test_missing_or_malformed_credentials(client, authorization):
    headers = {} if authorization is None else {"Authorization": authorization}
    assert_problem(client.get(BASE, headers=headers), 401)


@pytest.mark.parametrize("claims", [
    {"iss": "https://wrong.example.test"}, {"aud": "wrong-audience"},
    {"exp": 1}, {"iat": int(time.time()) + 3600}, {"nbf": int(time.time()) + 3600},
    {"sub": ""}, {"sub": " \t "}, {"sub": 12}, {"sub": "s" * 201},
    {"iat": None}, {"exp": None}, {"exp": "9999999999"}, {"iat": True}, {"nbf": "1"},
    {"scope": ["purchase-requests:read"]},
])
def test_invalid_claims(client, token_factory, claims):
    token = token_factory(claims=claims)
    assert_problem(client.get(BASE, headers={"Authorization": f"Bearer {token}"}), 401)


@pytest.mark.parametrize("claim", ["sub", "iat", "exp", "iss", "aud"])
def test_required_claims(client, token_factory, claim):
    token = token_factory(omit=[claim])
    assert_problem(client.get(BASE, headers={"Authorization": f"Bearer {token}"}), 401)


@pytest.mark.parametrize("options", [
    {"algorithm": "HS256"}, {"algorithm": "RS384"},
    {"headers": {"kid": "unknown"}}, {"headers": {"kid": ""}}, {"headers": {"kid": "a" * 129}},
    {"key": "untrusted", "headers": {"kid": "key-one"}},
    {"headers": {"crit": ["unrecognized"]}},
])
def test_invalid_algorithms_signature_and_headers(client, token_factory, options):
    token = token_factory(**options)
    assert_problem(client.get(BASE, headers={"Authorization": f"Bearer {token}"}), 401)


def test_unsigned_and_oversized_tokens(client):
    import jwt
    unsigned = jwt.encode({"sub": "alice"}, key=None, algorithm="none", headers={"kid": "key-one"})
    for token in (unsigned, "a" * 16385):
        assert_problem(client.get(BASE, headers={"Authorization": f"Bearer {token}"}), 401)


@pytest.mark.parametrize("header", [{"alg": "RS256"}, {"alg": "RS256", "kid": None}, {"alg": "RS256", "kid": 123}])
def test_missing_or_nonstring_kid(client, token_factory, header):
    import json
    from jwt.utils import base64url_encode
    token = token_factory()
    _, payload, signature = token.split(".")
    without_kid = ".".join([base64url_encode(json.dumps(header).encode()).decode(), payload, signature])
    assert_problem(client.get(BASE, headers={"Authorization": f"Bearer {without_kid}"}), 401)


def test_untrusted_key_urls_never_supply_keys(client, token_factory):
    token = token_factory(headers={"jku": "https://attacker.invalid/jwks", "x5u": "https://attacker.invalid/key"})
    assert client.get(BASE, headers={"Authorization": f"Bearer {token}"}).status_code == 200


@pytest.mark.parametrize("scope", ["", "purchase-requests:reader", "other:read"])
def test_authenticated_missing_scope_is_forbidden(client, token_factory, scope):
    token = token_factory(scope=scope)
    response = client.get(BASE, headers={"Authorization": f"Bearer {token}"})
    assert_problem(response, 403)
    assert 'scope="purchase-requests:read"' in response.headers["www-authenticate"]


def test_read_and_write_permissions_are_separate(client, token_factory, purchase):
    reader = {"Authorization": f"Bearer {token_factory(scope='purchase-requests:read')}"}
    writer = {"Authorization": f"Bearer {token_factory(scope='purchase-requests:write')}"}
    assert client.get(BASE, headers=reader).status_code == 200
    assert_problem(client.post(BASE, headers=reader, json=purchase), 403)
    response = client.post(BASE, headers=writer, json=purchase)
    assert response.status_code == 201
    assert_problem(client.get(f"{BASE}/{response.json()['id']}", headers=writer), 403)
    assert_problem(client.get(BASE, headers=writer), 403)


def test_missing_scope_claim_is_forbidden(client, token_factory):
    token = token_factory(omit=["scope"])
    assert_problem(client.get(BASE, headers={"Authorization": f"Bearer {token}"}), 403)


def test_audience_list_is_supported(client, token_factory):
    token = token_factory(claims={"aud": ["another-api", "saba-reference-api"]})
    assert client.get(BASE, headers={"Authorization": f"Bearer {token}"}).status_code == 200
