from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import get_storage_dir
from app.core.exceptions import StorageValidationError


class StorageService:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or get_storage_dir()).expanduser().resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def ensure_safe_path(self, relative_path: str) -> Path:
        candidate = (self.base_dir / relative_path).resolve()
        if candidate == self.base_dir or self.base_dir in candidate.parents:
            return candidate
        raise StorageValidationError("Resolved file path escapes the configured storage directory.")

    @staticmethod
    def build_relative_path(job_id: str, certificate_id: str) -> str:
        return str(Path("jobs") / job_id / f"{certificate_id}.pdf")

    @staticmethod
    def compute_checksum(file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as file_handle:
            for chunk in iter(lambda: file_handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()
