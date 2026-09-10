import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm

from saba_api.settings import Settings

MAX_JWKS_BYTES = 1_048_576
MAX_KEYS = 32
MAX_TOKEN_LENGTH = 16_384
JWKS_FETCH_SECONDS = 5.0


class InvalidCredentials(Exception):
    pass


class IdentityUnavailable(Exception):
    pass


def parse_jwks(data: bytes) -> dict[str, RSAPublicKey]:
    if len(data) > MAX_JWKS_BYTES:
        raise ValueError("JWKS exceeds the size limit.")
    document = json.loads(data)
    if not isinstance(document, dict):
        raise ValueError("JWKS must be an object.")
    keys = document.get("keys")
    if not isinstance(keys, list) or not 1 <= len(keys) <= MAX_KEYS:
        raise ValueError("JWKS must contain 1 to 32 keys.")
    result: dict[str, RSAPublicKey] = {}
    for key in keys:
        if not isinstance(key, dict):
            raise ValueError("Invalid JWKS key.")
        # Ignore other supported provider algorithms, but never use them for this API.
        if key.get("kty") != "RSA" or key.get("alg", "RS256") != "RS256" or key.get("use", "sig") != "sig":
            continue
        kid = key.get("kid")
        if not isinstance(kid, str) or not 1 <= len(kid) <= 128 or kid in result:
            raise ValueError("RSA signing keys require unique bounded key IDs.")
        if any(part in key for part in ("d", "p", "q", "dp", "dq", "qi", "oth")):
            raise ValueError("Only public JWKS keys are accepted.")
        if "key_ops" in key and (
            not isinstance(key["key_ops"], list) or key["key_ops"] != ["verify"]
        ):
            continue
        public_key = RSAAlgorithm.from_jwk(key)
        if not isinstance(public_key, RSAPublicKey) or public_key.key_size < 2048:
            raise ValueError("RSA public keys must be at least 2048 bits.")
        result[kid] = public_key
    if not result:
        raise ValueError("JWKS has no usable RS256 public signing key.")
    return result


def read_local_jwks(path: Path) -> dict[str, RSAPublicKey]:
    with path.open("rb") as source:
        return parse_jwks(source.read(MAX_JWKS_BYTES + 1))


class KeyStore:
    def __init__(
        self,
        settings: Settings,
        client: httpx.Client,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings
        self.client = client
        self.clock = clock
        self.lock = threading.Lock()
        self.keys: dict[str, RSAPublicKey] = {}
        self.expires_at = 0.0
        self.refresh_after = 0.0
        self.failed = False
        if settings.jwks_path:
            try:
                self.keys = read_local_jwks(settings.jwks_path)
            except (OSError, ValueError, TypeError, jwt.PyJWTError) as exc:
                raise ValueError("SABA_JWKS_PATH must contain a readable, valid public RS256 JWKS.") from exc

    def _retrieve(self) -> dict[str, RSAPublicKey]:
        try:
            deadline = self.clock() + JWKS_FETCH_SECONDS
            with self.client.stream("GET", self.settings.jwks_url, headers={"Accept-Encoding": "identity"}) as response:
                response.raise_for_status()
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise ValueError("Compressed JWKS responses are not accepted.")
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_JWKS_BYTES or self.clock() > deadline:
                        raise ValueError("JWKS exceeds the retrieval bounds.")
                return parse_jwks(bytes(body))
        except (httpx.HTTPError, ValueError, TypeError, jwt.PyJWTError) as exc:
            raise IdentityUnavailable() from exc

    def get(self, kid: str) -> RSAPublicKey:
        # One refresh per process, including concurrent unknown-kid requests and outages.
        with self.lock:
            if self.settings.jwks_path:
                if kid not in self.keys:
                    raise InvalidCredentials()
                return self.keys[kid]
            now = self.clock()
            if now < self.expires_at and kid in self.keys:
                return self.keys[kid]
            if now < self.refresh_after:
                if self.failed or now >= self.expires_at:
                    raise IdentityUnavailable()
                raise InvalidCredentials()
            self.refresh_after = now + self.settings.jwks_refresh_seconds
            try:
                keys = self._retrieve()
            except IdentityUnavailable:
                self.failed = True
                raise
            self.keys = keys
            self.failed = False
            self.expires_at = self.clock() + self.settings.jwks_cache_seconds
            if kid not in self.keys:
                raise InvalidCredentials()
            return self.keys[kid]


@dataclass(frozen=True)
class Principal:
    subject: str
    scopes: frozenset[str]


class TokenVerifier:
    def __init__(self, settings: Settings, keys: KeyStore) -> None:
        self.settings = settings
        self.keys = keys

    def verify(self, token: str) -> Principal:
        if len(token) > MAX_TOKEN_LENGTH:
            raise InvalidCredentials()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if (
                header.get("alg") != "RS256"
                or not isinstance(kid, str)
                or not 1 <= len(kid) <= 128
                or "crit" in header
            ):
                raise InvalidCredentials()
            # jku/x5u, if present, are never consulted. Only the configured key store is trusted.
            key = self.keys.get(kid)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self.settings.issuer,
                audience=self.settings.audience,
                options={"require": ["sub", "iat", "exp", "iss", "aud"]},
            )
            subject = claims["sub"]
            if not isinstance(subject, str) or not subject.strip() or len(subject) > 200:
                raise InvalidCredentials()
            for name in ("iat", "exp", "nbf"):
                if name in claims and type(claims[name]) is not int:
                    raise InvalidCredentials()
            scope = claims.get("scope", "")
            if not isinstance(scope, str) or len(scope) > 4096:
                raise InvalidCredentials()
            return Principal(subject=subject, scopes=frozenset(scope.split()))
        except (jwt.PyJWTError, ValueError, TypeError, OverflowError) as exc:
            raise InvalidCredentials() from exc
