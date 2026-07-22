"""Detect dotenv generation drift without reading or hashing its contents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aico.core.models import HealthStatus

FileGeneration = tuple[int, int, int, int, int, int]


def capture_file_generation(path: Path) -> FileGeneration | None:
    try:
        metadata = path.stat()
    except OSError:
        return None
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_mode,
        metadata.st_uid,
    )


@dataclass(frozen=True)
class RuntimeConfigSourceHealth:
    path: Path
    expected_generation: FileGeneration | None

    @classmethod
    def capture(cls, path: Path) -> RuntimeConfigSourceHealth:
        return cls(path=path, expected_generation=capture_file_generation(path))

    async def health_check(self) -> HealthStatus:
        current = capture_file_generation(self.path)
        return HealthStatus.OK if current == self.expected_generation else HealthStatus.FAILED
