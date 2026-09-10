"""Generate and compare Copilot projections using the pinned APM CLI."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ".github/apm-managed.json"
PROJECTIONS = (
    ".github/agents",
    ".github/instructions",
    ".github/prompts",
    ".agents/skills",
)


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def apm_binary() -> str:
    binary = os.environ.get("APM_BIN") or shutil.which("apm")
    if not binary:
        raise RuntimeError("Install APM with scripts/install_apm.py and set APM_BIN.")
    binary = str(Path(binary).resolve())
    version = (ROOT / ".apm-version").read_text().strip()
    output = subprocess.run(
        [binary, "--version"], check=True, capture_output=True, text=True
    ).stdout
    if f"version {version} " not in output:
        raise RuntimeError(f"This repository requires APM {version}: {output.strip()}")
    return binary


def run_apm(
    binary: str, cwd: Path, *arguments: str, success: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [binary, *arguments], cwd=cwd, text=True, capture_output=True
    )
    if (result.returncode == 0) != success:
        raise RuntimeError(
            f"Unexpected APM result ({result.returncode}): {' '.join(arguments)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def stage_source(destination: Path) -> None:
    destination.mkdir(parents=True)
    if (ROOT / ".apm").is_symlink() or (ROOT / "apm.yml").is_symlink():
        raise RuntimeError("Package source roots must not be symlinks")
    shutil.copy2(ROOT / "apm.yml", destination / "apm.yml")
    for path in (ROOT / ".apm").rglob("*"):
        if path.is_symlink():
            raise RuntimeError(f"Package sources must not contain symlinks: {path}")
    shutil.copytree(ROOT / ".apm", destination / ".apm")


def projection_files(directory: Path) -> dict[str, str]:
    files = {}
    for root in PROJECTIONS:
        for path in (directory / root).rglob("*"):
            if path.is_symlink():
                raise RuntimeError(f"Generated symlink is not allowed: {path}")
            if path.is_file():
                files[path.relative_to(directory).as_posix()] = digest(path)
    return dict(sorted(files.items()))


def allowed_managed_path(value: str) -> bool:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        return False
    if value == "apm.lock.yaml":
        return True
    for root in PROJECTIONS:
        prefix = root + "/"
        if value.startswith(prefix):
            return value[len(prefix):].split("/")[0].startswith("saba-")
    return False


def read_inventory(root: Path) -> dict[str, str]:
    path = root / INVENTORY
    assert_no_symlinks(root, path)
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict) or data.get("format") != 1 or not isinstance(data.get("files"), dict):
        raise RuntimeError("Invalid managed-file inventory")
    files = data["files"]
    for name, checksum in files.items():
        if (
            not allowed_managed_path(name)
            or not isinstance(checksum, str)
            or not re.fullmatch(r"[a-f0-9]{64}", checksum)
        ):
            raise RuntimeError(f"Unsafe managed-file inventory entry: {name}")
    return files


def assert_no_symlinks(root: Path, path: Path) -> None:
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise RuntimeError(f"Symlinked managed path: {candidate}")


def assert_unmodified(root: Path, recorded: dict[str, str]) -> None:
    for name, checksum in recorded.items():
        path = root / name
        assert_no_symlinks(root, path)
        if path.is_symlink() or not path.is_file() or digest(path) != checksum:
            raise RuntimeError(
                f"Managed file changed or missing: {name}. Review its change and "
                "restore the committed projection before regenerating from .apm."
            )


def synchronize(stage: Path, destination: Path, write: bool) -> None:
    recorded = read_inventory(destination)
    assert_unmodified(destination, recorded)
    expected = projection_files(stage)
    expected["apm.lock.yaml"] = digest(stage / "apm.lock.yaml")
    expected = dict(sorted(expected.items()))
    for name in expected:
        if not allowed_managed_path(name):
            raise RuntimeError(f"APM produced an unexpected path: {name}")
    inventory = json.dumps({"format": 1, "files": expected}, indent=2) + "\n"
    if not write:
        if recorded != expected:
            raise RuntimeError("Canonical artifacts changed. Run scripts/artifacts.py --write.")
        if (destination / INVENTORY).read_text() != inventory:
            raise RuntimeError("Managed inventory formatting drifted")
        return
    # Never adopt a pre-existing, unrecorded file silently.
    for name in expected.keys() - recorded.keys():
        if (destination / name).exists() or (destination / name).is_symlink():
            raise RuntimeError(f"Unmanaged file collision: {name}")
    # Refuse symlinked parent directories before writing any generated file.
    for name in expected:
        assert_no_symlinks(destination, destination / name)
    for name in recorded.keys() - expected.keys():
        (destination / name).unlink()
    for name in expected:
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stage / name, path)
    (destination / INVENTORY).parent.mkdir(parents=True, exist_ok=True)
    (destination / INVENTORY).write_text(inventory)


def consumer_smoke(binary: str, workspace: Path, source: Path) -> None:
    consumer = workspace / "different-service"
    consumer.mkdir()
    # JSON is valid YAML; let APM parse and write its own manifest and lockfile.
    (consumer / "apm.yml").write_text(json.dumps({
        "name": "independent-consumer",
        "version": "0.1.0",
        "targets": ["copilot"],
        "dependencies": {"apm": [str(source)]},
    }))
    unrelated = consumer / ".github/agents/existing-team-agent.agent.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("---\ndescription: Existing team agent\n---\nKeep this file.\n")
    original = unrelated.read_bytes()
    run_apm(binary, consumer, "install")
    installed = projection_files(consumer)
    for name, checksum in projection_files(source).items():
        if installed.get(name) != checksum:
            raise RuntimeError(f"Consumer projection mismatch: {name}")
    run_apm(binary, consumer, "audit", "--ci")
    run_apm(binary, consumer, "install", "--frozen")
    if installed != projection_files(consumer) or unrelated.read_bytes() != original:
        raise RuntimeError("Reinstallation changed projections or unrelated files")
    changed = consumer / ".github/agents/saba-api-builder.agent.md"
    changed.write_text(changed.read_text() + "\nUnreviewed edit.\n")
    result = run_apm(binary, consumer, "audit", "--ci", success=False)
    if result.returncode != 1 or not re.search(
        r"drift|integrity", result.stdout + result.stderr, re.IGNORECASE
    ):
        raise RuntimeError("Negative audit failed for a reason other than integrity/drift")
    print("Consumer install, frozen replay, unrelated-file preservation, and drift rejection passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--consumer-test", action="store_true")
    parser.add_argument("--export-source", type=Path)
    args = parser.parse_args()
    binary = apm_binary()
    # Validate existing recorded bytes before rebuilding anything.
    assert_unmodified(ROOT, read_inventory(ROOT))
    with tempfile.TemporaryDirectory(prefix="saba-apm-") as temporary:
        workspace = Path(temporary)
        source = workspace / "saba-enterprise-api-builder"
        stage_source(source)
        run_apm(binary, source, "install")
        run_apm(binary, source, "audit", "--ci")
        synchronize(source, ROOT, write=args.write)
        if args.consumer_test:
            consumer_smoke(binary, workspace, source)
    if args.export_source:
        destination = args.export_source.resolve()
        if destination.exists():
            raise RuntimeError("Export destination already exists; choose a new directory")
        stage_source(destination)
    print("APM projections written." if args.write else "APM projections match canonical sources.")


if __name__ == "__main__":
    main()
