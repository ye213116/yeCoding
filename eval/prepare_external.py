"""Extract the pinned upstream source fixture without network access or installation."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def prepare(destination: Path) -> Path:
    metadata = json.loads((FIXTURES / "python-dotenv-v1.1.1.json").read_text())
    archive = FIXTURES / "python-dotenv-v1.1.1.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != metadata["archive_sha256"]:
        raise ValueError("upstream source archive checksum mismatch")
    destination = destination.resolve()
    if destination.exists():
        raise FileExistsError(f"destination already exists: {destination}")
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.namelist():
            if not (destination / member).resolve().is_relative_to(destination):
                raise ValueError("unsafe archive member")
        destination.mkdir(parents=True)
        bundle.extractall(destination)
    root = destination / metadata["scope"]
    for relative, expected in metadata["source_files_sha256"].items():
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"source checksum mismatch: {relative}")
    return root


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(tempfile.gettempdir()) / "yecoding-eval-python-dotenv-v1.1.1",
    )
    args = parser.parse_args()
    print(prepare(args.out))


if __name__ == "__main__":
    main()
