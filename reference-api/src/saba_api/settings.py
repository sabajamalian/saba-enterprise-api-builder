import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    issuer: str
    audience: str
    jwks_path: Path | None = None
    jwks_url: str | None = None
    database_url: str = "sqlite:///.local/purchase-requests.db"
    jwks_cache_seconds: float = 300
    jwks_refresh_seconds: float = 30

    def __post_init__(self) -> None:
        if not self.issuer.strip() or not self.audience.strip():
            raise ValueError("SABA_ISSUER and SABA_AUDIENCE must be nonblank.")
        if bool(self.jwks_path) == bool(self.jwks_url):
            raise ValueError("Configure exactly one of SABA_JWKS_PATH or SABA_JWKS_URL.")
        if self.jwks_url:
            url = urlsplit(self.jwks_url)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.fragment
                or any(character.isspace() for character in self.jwks_url)
            ):
                raise ValueError("SABA_JWKS_URL must be a trusted HTTPS URL without credentials or fragment.")
            if url.port is not None and not 1 <= url.port <= 65535:
                raise ValueError("SABA_JWKS_URL must use a valid HTTPS port.")
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("The reference implementation supports only SQLite database URLs.")
        if not 1 <= self.jwks_refresh_seconds <= self.jwks_cache_seconds <= 3600:
            raise ValueError("JWKS refresh/cache intervals must satisfy 1 <= refresh <= cache <= 3600.")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            issuer=os.environ.get("SABA_ISSUER", ""),
            audience=os.environ.get("SABA_AUDIENCE", ""),
            jwks_path=Path(os.environ["SABA_JWKS_PATH"]) if os.environ.get("SABA_JWKS_PATH") else None,
            jwks_url=os.environ.get("SABA_JWKS_URL") or None,
            database_url=os.environ.get("SABA_DATABASE_URL", "sqlite:///.local/purchase-requests.db"),
        )
