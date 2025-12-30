"""
Storage adapter layer for Sapphire package.

Wraps core.io DataStore abstraction for phase-specific storage.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional, Union

from core.io import create_store, BackendType, DataStore
from sapphire.config.schema import StorageBackend
from sapphire.core.exceptions import StorageError


def _backend_type_from_storage(storage: StorageBackend) -> BackendType:
    """Convert Sapphire StorageBackend to core.io BackendType."""
    mapping = {
        StorageBackend.JSON_FILES: BackendType.JSON_FILES,
        StorageBackend.SQLITE: BackendType.SQLITE,
        StorageBackend.JSONL: BackendType.JSONL,
        StorageBackend.AUTO: BackendType.AUTO,
    }
    return mapping.get(storage, BackendType.AUTO)


@contextmanager
def create_phase_store(
    base_dir: Path,
    phase_name: str,
    storage_backend: StorageBackend = StorageBackend.SQLITE,
    read_only: bool = False,
) -> Iterator[DataStore]:
    """Create a DataStore for a specific phase.

    Args:
        base_dir: Base output directory (e.g., Path("20251230"))
        phase_name: Phase name for subdirectory (e.g., "provider_ids", "provider_details")
        storage_backend: Storage backend type
        read_only: If True, open store in read-only mode

    Yields:
        DataStore: Configured store for the phase

    Raises:
        StorageError: If store creation fails

    Example:
        with create_phase_store(Path("20251230"), "provider_ids") as store:
            store.put("TX/Dallas/results.json", {"providers": [...]})
    """
    try:
        backend = _backend_type_from_storage(storage_backend)
        phase_dir = base_dir / "raw" / phase_name

        # Determine file path based on backend
        if backend == BackendType.SQLITE:
            store_path = str(phase_dir) + ".db"
        elif backend == BackendType.JSONL:
            store_path = str(phase_dir) + ".jsonl"
        else:
            store_path = str(phase_dir)
            phase_dir.mkdir(parents=True, exist_ok=True)

        store = create_store(store_path, backend=backend)
        try:
            yield store
        finally:
            if not read_only:
                store.flush()
            store.close()

    except Exception as e:
        raise StorageError(
            f"Failed to create store for phase '{phase_name}': {e}",
            details={"base_dir": str(base_dir), "phase_name": phase_name},
        ) from e


def get_output_path(
    base_dir: Path,
    curr_date: str,
    subdir: str = "processed",
    filename: str = "providers.jsonl",
) -> Path:
    """Get the output file path for normalized data.

    Args:
        base_dir: Project base directory
        curr_date: Current date string (YYYYMMDD)
        subdir: Subdirectory (default: "processed")
        filename: Output filename (default: "providers.jsonl")

    Returns:
        Path to output file
    """
    output_dir = base_dir / curr_date / subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


class PhaseStore:
    """Convenience wrapper for phase-specific storage operations.

    Provides simplified interface for common phase operations while
    delegating core functionality to the underlying DataStore.
    """

    def __init__(self, store: DataStore, phase_name: str):
        self._store = store
        self._phase_name = phase_name

    def save_result(self, key: str, data: dict) -> None:
        """Save a result to the store."""
        self._store.put(key, data)

    def get_result(self, key: str) -> Optional[dict]:
        """Get a result from the store."""
        return self._store.get(key)

    def exists(self, key: str) -> bool:
        """Check if a key exists in the store."""
        return self._store.exists(key)

    def iter_results(self) -> Iterator[tuple[str, dict]]:
        """Iterate over all results."""
        return iter(self._store)

    def count(self) -> int:
        """Get the number of results."""
        return len(self._store)

    def flush(self) -> None:
        """Flush any pending writes."""
        self._store.flush()
