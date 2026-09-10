import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import httpx
import pytest
from fastapi.testclient import TestClient

from saba_api.auth import IdentityUnavailable, InvalidCredentials, KeyStore, MAX_JWKS_BYTES, parse_jwks
from saba_api.main import create_app
from tests.contracts import assert_problem


@pytest.fixture
def remote_settings(settings):
    return replace(settings, jwks_path=None, jwks_url="https://identity.example.test/keys")


@pytest.fixture
def clock():
    class Clock:
        now = 0.0

        def __call__(self):
            return self.now
    return Clock()


def test_remote_cache_rotation_unknown_kid_and_concurrency(remote_settings, key_material, clock):
    calls = []
    published = ["key-one"]

    def handle(request):
        calls.append(request)
        assert str(request.url) == remote_settings.jwks_url
        assert request.extensions["timeout"]["connect"] == 2.0
        assert request.extensions["timeout"]["read"] == 5.0
        return httpx.Response(200, json={"keys": [key_material[kid][1] for kid in published]})

    with httpx.Client(transport=httpx.MockTransport(handle), timeout=httpx.Timeout(5, connect=2), follow_redirects=False) as client:
        store = KeyStore(remote_settings, client, clock=clock)
        assert store.get("key-one").key_size == 2048
        assert store.get("key-one").key_size == 2048
        assert len(calls) == 1
        published.append("key-two")
        with pytest.raises(InvalidCredentials):
            store.get("key-two")
        assert len(calls) == 1
        clock.now = 31
        with ThreadPoolExecutor(max_workers=8) as pool:
            assert all(key.key_size == 2048 for key in pool.map(store.get, ["key-two"] * 24))
        assert len(calls) == 2
        clock.now = 62

        def unknown(_):
            with pytest.raises(InvalidCredentials):
                store.get("unknown")

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(unknown, range(24)))
        assert len(calls) == 3
        clock.now = 363
        published[:] = ["key-two"]
        with pytest.raises(InvalidCredentials):
            store.get("key-one")
        assert len(calls) == 4


def test_issuer_outage_cooldown_and_recovery(remote_settings, key_material, clock):
    calls = 0
    outage = True

    def handle(request):
        nonlocal calls
        calls += 1
        if outage:
            raise httpx.ConnectError("sensitive provider error", request=request)
        return httpx.Response(200, json={"keys": [key_material["key-one"][1]]})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        store = KeyStore(remote_settings, client, clock=clock)
        for _ in range(10):
            with pytest.raises(IdentityUnavailable):
                store.get("key-one")
        assert calls == 1
        outage = False
        clock.now = 31
        assert store.get("key-one").key_size == 2048
        assert calls == 2
        outage = True
        clock.now = 61
        with pytest.raises(IdentityUnavailable):
            store.get("key-two")
        assert calls == 3
        # An unexpired known key remains usable during a failed unknown-key refresh.
        assert store.get("key-one").key_size == 2048
        clock.now = 332
        with pytest.raises(IdentityUnavailable):
            store.get("key-one")
        assert calls == 4
        with pytest.raises(IdentityUnavailable):
            store.get("key-one")
        assert calls == 4


@pytest.mark.parametrize("kind", ["timeout", "500", "redirect", "oversize", "malformed", "invalid-key"])
def test_retrieval_failures_are_safe_503(remote_settings, token_factory, kind):
    calls = []

    def handle(request):
        calls.append(request)
        if kind == "timeout":
            raise httpx.ReadTimeout("secret-provider-error", request=request)
        if kind == "500":
            return httpx.Response(500, text="secret-provider-error")
        if kind == "redirect":
            return httpx.Response(302, headers={"Location": "https://untrusted.example/keys"})
        if kind == "oversize":
            return httpx.Response(200, content=b"x" * (MAX_JWKS_BYTES + 1))
        if kind == "malformed":
            return httpx.Response(200, content=b"secret-provider-error")
        return httpx.Response(200, json={"keys": []})

    application = create_app(remote_settings, jwks_transport=httpx.MockTransport(handle))
    with TestClient(application) as client:
        token = token_factory(headers={"jku": "https://attacker.invalid/keys"})
        for _ in range(2):
            response = client.get(
                "/api/v1/purchase-requests",
                headers={"Authorization": f"Bearer {token}", "X-Correlation-ID": "provider-outage"},
            )
            assert_problem(response, 503)
            assert response.headers["retry-after"] == "30"
            assert "secret-provider-error" not in response.text
    assert len(calls) == 1
    assert str(calls[0].url) == remote_settings.jwks_url


def test_remote_verified_token_and_unknown_key(remote_settings, key_material, token_factory):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"keys": [key_material["key-one"][1]]}))
    with TestClient(create_app(remote_settings, jwks_transport=transport)) as client:
        good = {"Authorization": f"Bearer {token_factory()}"}
        assert client.get("/api/v1/purchase-requests", headers=good).status_code == 200
        bad = {"Authorization": f"Bearer {token_factory(headers={'kid': 'missing'})}"}
        assert_problem(client.get("/api/v1/purchase-requests", headers=bad), 401)


def test_slow_stream_has_elapsed_retrieval_bound(remote_settings, clock):
    class SlowStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"keys":'
            clock.now += 6
            yield b'[]}'

    transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=SlowStream()))
    with httpx.Client(transport=transport) as client:
        store = KeyStore(remote_settings, client, clock=clock)
        with pytest.raises(IdentityUnavailable):
            store.get("key-one")


def test_compressed_jwks_is_rejected(remote_settings, key_material, clock):
    import gzip
    payload = json.dumps({"keys": [key_material["key-one"][1]]}).encode()
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, content=gzip.compress(payload), headers={"Content-Encoding": "gzip"})
    )
    with httpx.Client(transport=transport) as client:
        store = KeyStore(remote_settings, client, clock=clock)
        with pytest.raises(IdentityUnavailable):
            store.get("key-one")


@pytest.mark.parametrize("document", [
    [], {}, {"keys": []}, {"keys": [None]}, {"keys": ["text"]}, {"keys": [{}]},
    {"keys": [{"kty": "RSA", "kid": "x", "n": "invalid", "e": "bad"}]},
    {"keys": [{"kty": "RSA", "kid": "x", "d": "private"}]},
    {"keys": [{}] * 33},
])
def test_malformed_jwks_is_rejected(document):
    with pytest.raises((ValueError, TypeError)):
        parse_jwks(json.dumps(document).encode())


def test_duplicate_key_id_and_weak_key_rejected(key_material):
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jwt.algorithms import RSAAlgorithm
    key = key_material["key-one"][1]
    with pytest.raises(ValueError):
        parse_jwks(json.dumps({"keys": [key, key]}).encode())
    weak = json.loads(RSAAlgorithm.to_jwk(rsa.generate_private_key(public_exponent=65537, key_size=1024).public_key()))
    weak["kid"] = "weak"
    with pytest.raises(ValueError):
        parse_jwks(json.dumps({"keys": [weak]}).encode())
