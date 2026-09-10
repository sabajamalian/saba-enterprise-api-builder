import json
import stat
import subprocess
import sys

import jwt
import pytest
from fastapi.testclient import TestClient

from saba_api.auth import parse_jwks
from saba_api.dev import generate_keys
from saba_api.main import create_app
from saba_api.settings import Settings


def test_configuration_is_required_at_startup(monkeypatch):
    for name in ("SABA_ISSUER", "SABA_AUDIENCE", "SABA_JWKS_PATH", "SABA_JWKS_URL"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="SABA_ISSUER and SABA_AUDIENCE"):
        with TestClient(create_app()):
            pass


@pytest.mark.parametrize("arguments", [
    {}, {"jwks_path": "path", "jwks_url": "https://id.test/keys"},
    {"jwks_url": "http://id.test/keys"}, {"jwks_url": "https://user:password@id.test/keys"},
    {"jwks_url": "https://@id.test/keys"},
    {"jwks_url": "https://id.test/keys#fragment"}, {"jwks_url": "https:///keys"},
    {"jwks_url": "file:///keys"}, {"jwks_url": "https://id.test/keys", "database_url": "postgresql://db"},
    {"jwks_url": "https://id.test:abc/keys"}, {"jwks_url": "https://id.test:0/keys"},
    {"jwks_url": "https://id.test /keys"},
    {"jwks_url": "https://id.test/keys", "jwks_refresh_seconds": 0},
    {"jwks_url": "https://id.test/keys", "jwks_cache_seconds": 4000},
])
def test_invalid_configuration(arguments):
    with pytest.raises(ValueError):
        Settings(issuer="https://id.test", audience="api", **arguments)


def test_local_jwks_errors_fail_startup(tmp_path):
    path = tmp_path / "jwks.json"
    settings = Settings(issuer="id", audience="api", jwks_path=path)
    for data in (None, "not-json", '{"keys": []}'):
        if data is not None:
            path.write_text(data)
        with pytest.raises(ValueError, match="SABA_JWKS_PATH"):
            with TestClient(create_app(settings)):
                pass


def test_environment_configuration(monkeypatch, settings):
    monkeypatch.setenv("SABA_ISSUER", settings.issuer)
    monkeypatch.setenv("SABA_AUDIENCE", settings.audience)
    monkeypatch.setenv("SABA_JWKS_PATH", str(settings.jwks_path))
    monkeypatch.setenv("SABA_DATABASE_URL", settings.database_url)
    monkeypatch.delenv("SABA_JWKS_URL", raising=False)
    assert Settings.from_env() == settings
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200


def test_development_cli_permissions_no_overwrite_and_verified_token(tmp_path):
    directory = tmp_path / ".local"
    generated = subprocess.run(
        [sys.executable, "-m", "saba_api.dev", "keys", "--directory", str(directory)],
        check=True, capture_output=True, text=True,
    )
    assert "PRIVATE KEY" not in generated.stdout
    private = directory / "private.pem"
    assert stat.S_IMODE(private.stat().st_mode) == 0o600
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    original = private.read_bytes()
    with pytest.raises(SystemExit, match="already exist"):
        generate_keys(directory)
    assert private.read_bytes() == original
    command = [
        sys.executable, "-m", "saba_api.dev", "token", "--directory", str(directory),
        "--issuer", "https://local.example", "--audience", "local-api", "--subject", "local-user",
    ]
    issued = subprocess.run(command, check=True, capture_output=True, text=True)
    public = parse_jwks((directory / "jwks.json").read_bytes())
    token = issued.stdout.strip()
    claims = jwt.decode(token, next(iter(public.values())), algorithms=["RS256"], issuer="https://local.example", audience="local-api")
    assert claims["sub"] == "local-user" and claims["exp"] - claims["iat"] == 900
    assert claims["scope"] == "purchase-requests:read purchase-requests:write"
    private.chmod(0o644)
    rejected = subprocess.run(command, capture_output=True, text=True)
    assert rejected.returncode != 0 and rejected.stdout == ""
    private.chmod(0o600)
