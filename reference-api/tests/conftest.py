import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from saba_api.main import create_app
from saba_api.settings import Settings

ISSUER = "https://identity.example.test"
AUDIENCE = "saba-reference-api"


def pytest_configure(config):
    (config.rootpath / ".local").mkdir(exist_ok=True)


@pytest.fixture(scope="session")
def key_material():
    result = {}
    for kid in ("key-one", "key-two", "untrusted"):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
        public.update(kid=kid, alg="RS256", use="sig")
        result[kid] = (private, public)
    return result


@pytest.fixture(scope="session")
def jwks_file(tmp_path_factory, key_material):
    path = tmp_path_factory.mktemp("identity") / "jwks.json"
    path.write_text(json.dumps({"keys": [key_material["key-one"][1]]}))
    return path


@pytest.fixture
def settings(tmp_path, jwks_file):
    return Settings(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_path=jwks_file,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
    )


@pytest.fixture
def token_factory(key_material):
    def make(*, subject="alice", scope="purchase-requests:read purchase-requests:write", claims=None, omit=(), headers=None, key="key-one", algorithm="RS256"):
        now = int(time.time())
        payload = {"iss": ISSUER, "aud": AUDIENCE, "sub": subject, "iat": now, "exp": now + 300, "scope": scope}
        payload.update(claims or {})
        for claim in omit:
            payload.pop(claim, None)
        signing_key = key_material[key][0] if algorithm.startswith("RS") else "x" * 64
        return jwt.encode(payload, signing_key, algorithm=algorithm, headers={"kid": key, **(headers or {})})

    return make


@pytest.fixture
def app(settings):
    return create_app(settings)


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def authorization(token_factory):
    return {"Authorization": f"Bearer {token_factory()}"}


@pytest.fixture
def purchase():
    return {"title": "Research equipment", "description": "One workstation", "amount": "1234.56", "currency": "USD"}
