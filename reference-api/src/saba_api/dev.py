"""Development-only key and token CLI. Never use these keys for production."""

import argparse
import json
import os
import time
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm


def generate_keys(directory: Path) -> None:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    private_path = directory / "private.pem"
    public_path = directory / "jwks.json"
    if private_path.exists() or public_path.exists():
        raise SystemExit("Key files already exist. Remove them explicitly before generating a new development identity.")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
    public.update(kid=str(uuid4()), alg="RS256", use="sig")
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    with os.fdopen(os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as output:
        output.write(pem)
    with public_path.open("x") as output:
        json.dump({"keys": [public]}, output)
    print(f"Development keys written to {directory}. Never share private.pem or use these keys in production.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    keys = subcommands.add_parser("keys", help="Generate an ephemeral local RSA identity")
    keys.add_argument("--directory", type=Path, default=Path(".local"))
    token = subcommands.add_parser("token", help="Print a short-lived development token to stdout")
    token.add_argument("--directory", type=Path, default=Path(".local"))
    token.add_argument("--issuer", required=True)
    token.add_argument("--audience", required=True)
    token.add_argument("--subject", default="local-user")
    token.add_argument("--scope", default="purchase-requests:read purchase-requests:write")
    args = parser.parse_args()
    if args.command == "keys":
        generate_keys(args.directory)
        return
    if not args.subject.strip() or len(args.subject) > 200:
        parser.error("--subject must be nonblank and at most 200 characters.")
    private_path = args.directory / "private.pem"
    if private_path.stat().st_mode & 0o077:
        parser.error("Development private.pem must have mode 600 (no group or other access).")
    private = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    public = json.loads((args.directory / "jwks.json").read_text())
    now = int(time.time())
    print(
        jwt.encode(
            {
                "iss": args.issuer,
                "aud": args.audience,
                "sub": args.subject,
                "iat": now,
                "exp": now + 900,
                "scope": args.scope,
            },
            private,
            algorithm="RS256",
            headers={"kid": public["keys"][0]["kid"]},
        )
    )


if __name__ == "__main__":
    main()
