"""Async file writer with directory-based batching.

Provides efficient file I/O with batching and background processing.
"""

import asyncio
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional, Union

import orjson


class FileWriteWorker:
    """Async file writer with directory-based batching for optimized I/O.

    Features:
    - Async I/O for non-blocking writes
    - Directory-based batching to reduce filesystem overhead
    - Bounded queue with backpressure
    - Automatic batch flushing on timeout or size
    - Works in both sync and async contexts via background thread
    """

    def __init__(
        self,
        queue_size: int = 1000,
        batch_size: int = 50,
        batch_timeout: float = 0.1,
    ):
        """Initialize the file write worker.

        Args:
            queue_size: Maximum queue size before backpressure
            batch_size: Files per batch before flushing
            batch_timeout: Seconds before auto-flushing batches
        """
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        self._queue_size = queue_size

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._queue: Optional[asyncio.Queue] = None
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False
        self._started = threading.Event()

        self._start_background_loop()

    @staticmethod
    def _normalize_path(path: Union[str, Path]) -> str:
        """Normalize a file path, handling UNC paths correctly on Windows."""
        path_str = str(path)
        if not path_str:
            return path_str
        if path_str.startswith("\\\\"):
            return os.path.normpath(path_str)
        return os.path.abspath(os.path.normpath(path_str))

    def _start_background_loop(self) -> None:
        """Start a background thread running an async event loop."""

        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._queue = asyncio.Queue(maxsize=self._queue_size)
            self._running = True
            self._worker_task = self._loop.create_task(self._worker_loop())
            self._started.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()
        self._started.wait()

    async def _worker_loop(self) -> None:
        """Main worker loop - processes writes with directory-based batching."""
        batches: dict[str, list[tuple[str, Any]]] = defaultdict(list)
        last_flush_time = time.monotonic()

        while self._running:
            item_retrieved = False
            try:
                try:
                    file_path, payload = await asyncio.wait_for(
                        self._queue.get(), timeout=self._batch_timeout
                    )
                    item_retrieved = True
                except asyncio.TimeoutError:
                    if batches:
                        await self._flush_all_batches(batches)
                        last_flush_time = time.monotonic()
                    continue
                except asyncio.CancelledError:
                    break

                normalized_path = self._normalize_path(file_path)
                directory = self._normalize_path(os.path.dirname(normalized_path))
                batches[directory].append((normalized_path, payload))

                if len(batches[directory]) >= self._batch_size:
                    await self._flush_batch(directory, batches[directory])
                    batches[directory].clear()

                current_time = time.monotonic()
                if current_time - last_flush_time >= self._batch_timeout:
                    await self._flush_all_batches(batches)
                    last_flush_time = current_time

                self._queue.task_done()

            except Exception as e:
                if item_retrieved:
                    try:
                        self._queue.task_done()
                    except ValueError:
                        pass
                if "Event loop is closed" not in str(e):
                    print(f"Error in file write worker: {e}")

        if batches:
            try:
                await self._flush_all_batches(batches)
            except Exception as e:
                if "Event loop is closed" not in str(e):
                    print(f"Error flushing final batches: {e}")

    async def _flush_batch(
        self, directory: str, batch: list[tuple[str, Any]]
    ) -> None:
        """Flush a single directory's batch of writes."""
        os.makedirs(directory, exist_ok=True)
        for file_path, payload in batch:
            await self._write_file(file_path, payload)

    async def _flush_all_batches(
        self, batches: dict[str, list[tuple[str, Any]]]
    ) -> None:
        """Flush all directory batches."""
        for directory, batch in list(batches.items()):
            if batch:
                await self._flush_batch(directory, batch)
                batch.clear()

    async def _write_file(self, file_path: str, payload: Any) -> None:
        """Write payload to file as JSON."""
        data = orjson.dumps(payload)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_write, file_path, data)

    @staticmethod
    def _sync_write(file_path: str, data: bytes) -> None:
        """Synchronous file write."""
        with open(file_path, "wb") as f:
            f.write(data)

    def write(self, file_path: Union[str, Path], payload: Any) -> None:
        """Queue a file for writing.

        Thread-safe method to queue writes from any context.

        Args:
            file_path: Destination file path
            payload: Data to serialize as JSON
        """
        if self._loop is None or self._queue is None:
            raise RuntimeError("FileWriteWorker not started")

        asyncio.run_coroutine_threadsafe(
            self._queue.put((str(file_path), payload)), self._loop
        )

    def stop(self) -> None:
        """Stop the worker and flush remaining writes."""
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=5.0)

    def __enter__(self) -> "FileWriteWorker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
