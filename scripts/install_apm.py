"""Install a pinned official APM release locally; print its executable path."""

import hashlib
import platform
import re
import subprocess
import tarfile
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = (ROOT / ".apm-version").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise SystemExit("Invalid .apm-version: expected an explicit release version")
    system = platform.system().lower()
    arch = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x86_64"}.get(
        platform.machine().lower()
    )
    if system not in {"darwin", "linux"} or arch is None:
        raise SystemExit(
            "This helper supports macOS/Linux arm64/x86_64. Install the pinned "
            "official APM release for your platform and set APM_BIN manually."
        )
    name = f"apm-{system}-{arch}"
    tools = ROOT / ".local" / "tools"
    executable = tools / name / "apm"
    if not executable.exists():
        tools.mkdir(parents=True, exist_ok=True)
        archive_name = f"{name}.tar.gz"
        base = f"https://github.com/microsoft/apm/releases/download/v{version}"
        with tempfile.TemporaryDirectory(prefix="download-", dir=tools) as directory:
            archive = Path(directory) / archive_name
            with urllib.request.urlopen(f"{base}/{archive_name}", timeout=60) as response:
                archive.write_bytes(response.read())
            with urllib.request.urlopen(
                f"{base}/{archive_name}.sha256", timeout=30
            ) as response:
                expected = response.read().decode().split()[0]
            if not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
                raise SystemExit("Invalid checksum from official release")
            with archive.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            if actual != expected.lower():
                raise SystemExit("APM release checksum mismatch")
            with tarfile.open(archive) as bundle:
                if any(Path(member.name).parts[0] != name for member in bundle.getmembers()):
                    raise SystemExit("Unexpected archive layout")
                bundle.extractall(tools, filter="data")
    result = subprocess.run(
        [str(executable), "--version"], check=True, text=True, capture_output=True
    )
    if f"version {version} " not in result.stdout:
        raise SystemExit(
            f"Existing APM at {executable} does not match {version}. "
            "Move that specific tool directory aside before reinstalling."
        )
    print(executable)


if __name__ == "__main__":
    main()
