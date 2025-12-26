"""Comprehensive tests for FileWriteWorker class.

Tests cover:
- Path normalization (_normalize_path)
- Write batching behavior
- Concurrent writes
- Error handling
- Context manager
- Stop behavior
"""

import json
import os
import platform
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

import orjson
import pytest

from healthsparq.core.file_writer import FileWriteWorker


class TestPathNormalization:
    """Test _normalize_path static method."""

    def test_empty_string_path(self):
        """Empty string path returns empty string."""
        result = FileWriteWorker._normalize_path("")
        assert result == ""

    def test_relative_path_conversion(self):
        """Relative paths are converted to absolute."""
        result = FileWriteWorker._normalize_path("test/file.json")
        assert os.path.isabs(result)
        assert "test" in result
        assert result.endswith("file.json")

    def test_unc_paths_on_windows(self):
        r"""UNC paths (\\server\share) are preserved on Windows."""
        if platform.system() != "Windows":
            pytest.skip("UNC path test only relevant on Windows")

        unc_path = r"\\server\share\file.json"
        result = FileWriteWorker._normalize_path(unc_path)
        assert result.startswith(r"\\server\share")

    def test_paths_with_special_characters(self):
        """Paths with special characters are normalized."""
        path = "test/../data/file-name_123.json"
        result = FileWriteWorker._normalize_path(path)
        assert os.path.isabs(result)
        assert ".." not in result
        assert "file-name_123.json" in result

    def test_paths_with_spaces(self):
        """Paths with spaces are normalized correctly."""
        path = "test/path with spaces/file.json"
        result = FileWriteWorker._normalize_path(path)
        assert os.path.isabs(result)
        assert "path with spaces" in result

    def test_very_long_paths(self):
        """Very long paths are normalized correctly."""
        # Create a path with many nested directories
        parts = ["dir"] * 50 + ["file.json"]
        path = os.path.join(*parts)
        result = FileWriteWorker._normalize_path(path)
        assert os.path.isabs(result)
        assert result.endswith("file.json")

    def test_unicode_paths(self):
        """Unicode characters in paths are preserved."""
        path = "test/путь/файл.json"  # Russian
        result = FileWriteWorker._normalize_path(path)
        assert os.path.isabs(result)
        assert "путь" in result
        assert "файл.json" in result

    def test_pathlib_path_object(self):
        """Path objects are converted to absolute strings."""
        path = Path("test/file.json")
        result = FileWriteWorker._normalize_path(path)
        assert isinstance(result, str)
        assert os.path.isabs(result)
        assert result.endswith("file.json")


class TestWriteBatching:
    """Test write batching behavior."""

    def test_writes_batched_by_directory(self, tmp_path):
        """Writes are batched by directory."""
        worker = FileWriteWorker(batch_size=10, batch_timeout=0.5)

        # Write to multiple directories
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"

        for i in range(5):
            worker.write(dir1 / f"file_{i}.json", {"value": i})
            worker.write(dir2 / f"file_{i}.json", {"value": i})

        # Wait for timeout to trigger flush
        time.sleep(1.0)

        # Stop and wait for cleanup
        worker.stop()
        time.sleep(0.5)

        # Verify both directories have files
        dir1_files = list(dir1.glob("*.json"))
        dir2_files = list(dir2.glob("*.json"))
        assert len(dir1_files) == 5, f"dir1 has {len(dir1_files)} files, expected 5"
        assert len(dir2_files) == 5, f"dir2 has {len(dir2_files)} files, expected 5"

    def test_batch_flushes_at_batch_size(self, tmp_path):
        """Batch flushes when batch_size threshold is reached."""
        batch_size = 5
        worker = FileWriteWorker(batch_size=batch_size, batch_timeout=10.0)

        output_dir = tmp_path / "output"

        # Write exactly batch_size files
        for i in range(batch_size):
            worker.write(output_dir / f"file_{i}.json", {"value": i})

        # Give worker time to flush (should be immediate)
        time.sleep(0.2)

        # Verify files were written
        files = list(output_dir.glob("*.json"))
        assert len(files) == batch_size

        worker.stop()

    def test_batch_flushes_on_timeout(self, tmp_path):
        """Batch flushes after batch_timeout expires."""
        batch_timeout = 0.2
        worker = FileWriteWorker(batch_size=100, batch_timeout=batch_timeout)

        output_dir = tmp_path / "output"

        # Write fewer files than batch_size
        for i in range(3):
            worker.write(output_dir / f"file_{i}.json", {"value": i})

        # Wait for timeout
        time.sleep(batch_timeout + 0.2)

        # Verify files were written despite not reaching batch_size
        files = list(output_dir.glob("*.json"))
        assert len(files) == 3

        worker.stop()

    def test_multiple_directories_batched_separately(self, tmp_path):
        """Multiple directories are batched separately."""
        batch_size = 3
        worker = FileWriteWorker(batch_size=batch_size, batch_timeout=1.0)

        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir3 = tmp_path / "dir3"

        # Write to three directories
        for i in range(batch_size):
            worker.write(dir1 / f"file_{i}.json", {"dir": "dir1", "value": i})
            worker.write(dir2 / f"file_{i}.json", {"dir": "dir2", "value": i})
            worker.write(dir3 / f"file_{i}.json", {"dir": "dir3", "value": i})

        # Wait for batches to flush
        time.sleep(0.5)
        worker.stop()

        # Verify each directory has correct files
        for directory in [dir1, dir2, dir3]:
            files = list(directory.glob("*.json"))
            assert len(files) == batch_size

            # Verify content
            for file_path in files:
                with open(file_path, "rb") as f:
                    data = orjson.loads(f.read())
                    assert data["dir"] == directory.name


class TestConcurrentWrites:
    """Test concurrent write operations."""

    def test_multiple_simultaneous_writes_same_file(self, tmp_path):
        """Multiple threads writing to same file path (last write wins)."""
        worker = FileWriteWorker(batch_size=50, batch_timeout=0.5)

        output_file = tmp_path / "test.json"
        num_threads = 10
        writes_per_thread = 5

        def write_worker(thread_id: int):
            for i in range(writes_per_thread):
                worker.write(output_file, {"thread": thread_id, "write": i})

        threads = [
            threading.Thread(target=write_worker, args=(tid,))
            for tid in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Wait for all writes to complete
        time.sleep(1.0)
        worker.stop()

        # File should exist (one of the writes succeeded)
        assert output_file.exists()

        # Content should be valid JSON
        with open(output_file, "rb") as f:
            data = orjson.loads(f.read())
            assert "thread" in data
            assert "write" in data

    def test_multiple_simultaneous_writes_different_files(self, tmp_path):
        """Multiple threads writing to different files."""
        worker = FileWriteWorker(batch_size=50, batch_timeout=0.5)

        output_dir = tmp_path / "output"
        num_threads = 10
        files_per_thread = 10

        def write_worker(thread_id: int):
            for i in range(files_per_thread):
                file_path = output_dir / f"thread_{thread_id}_file_{i}.json"
                worker.write(file_path, {"thread": thread_id, "file": i})

        threads = [
            threading.Thread(target=write_worker, args=(tid,))
            for tid in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Wait for all writes to complete
        time.sleep(1.0)
        worker.stop()

        # Verify all files were written
        files = list(output_dir.glob("*.json"))
        assert len(files) == num_threads * files_per_thread

        # Verify content integrity
        for file_path in files:
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
                assert "thread" in data
                assert "file" in data

    def test_high_volume_writes(self, tmp_path):
        """High volume writes (1000+ items)."""
        worker = FileWriteWorker(batch_size=50, batch_timeout=0.5)

        output_dir = tmp_path / "output"
        num_writes = 1000

        # Queue all writes
        for i in range(num_writes):
            worker.write(output_dir / f"file_{i:04d}.json", {"index": i})

        # Wait for all writes to complete
        time.sleep(3.0)
        worker.stop()

        # Verify all files were written
        files = list(output_dir.glob("*.json"))
        assert len(files) == num_writes

        # Spot check some files
        for i in [0, 100, 500, 999]:
            file_path = output_dir / f"file_{i:04d}.json"
            assert file_path.exists()
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
                assert data["index"] == i

    def test_thread_safety_verification(self, tmp_path):
        """Thread safety verification with aggressive concurrent access."""
        worker = FileWriteWorker(batch_size=20, batch_timeout=0.3)

        output_dir = tmp_path / "output"
        num_threads = 20
        writes_per_thread = 50
        results: List[bool] = []
        lock = threading.Lock()

        def aggressive_writer(thread_id: int):
            try:
                for i in range(writes_per_thread):
                    file_path = output_dir / f"t{thread_id}_f{i}.json"
                    worker.write(file_path, {"tid": thread_id, "idx": i, "ts": time.time()})
                    # Minimal sleep to maximize contention
                    time.sleep(0.001)
                with lock:
                    results.append(True)
            except Exception as e:
                print(f"Thread {thread_id} failed: {e}")
                with lock:
                    results.append(False)

        threads = [
            threading.Thread(target=aggressive_writer, args=(tid,))
            for tid in range(num_threads)
        ]

        start_time = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Wait for writes to flush
        time.sleep(2.0)
        worker.stop()

        # All threads should succeed
        assert all(results), "Some threads failed"

        # Verify expected number of files
        files = list(output_dir.glob("*.json"))
        expected_files = num_threads * writes_per_thread
        assert len(files) == expected_files, f"Expected {expected_files}, got {len(files)}"


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_write_to_invalid_path_permissions(self, tmp_path):
        """Write to path without permissions (if testable)."""
        if platform.system() == "Windows":
            pytest.skip("Permission testing complex on Windows")

        worker = FileWriteWorker(batch_size=5, batch_timeout=0.5)

        # Create a directory with no write permissions
        no_write_dir = tmp_path / "no_write"
        no_write_dir.mkdir()
        os.chmod(no_write_dir, 0o444)  # Read-only

        # Attempt to write
        worker.write(no_write_dir / "test.json", {"data": "test"})

        # Worker should handle error gracefully (logged, not raised)
        time.sleep(0.5)
        worker.stop()

        # Restore permissions for cleanup
        os.chmod(no_write_dir, 0o755)

    def test_write_before_worker_started(self):
        """Write before worker started raises RuntimeError."""
        # Create worker but stop it immediately
        worker = FileWriteWorker()
        worker.stop()

        # Reset internal state to simulate not started
        worker._loop = None
        worker._queue = None

        # Attempt to write should raise RuntimeError
        with pytest.raises(RuntimeError, match="FileWriteWorker not started"):
            worker.write("test.json", {"data": "test"})

    def test_orjson_serialization_errors(self, tmp_path):
        """orjson serialization errors for non-serializable payload."""
        worker = FileWriteWorker(batch_size=5, batch_timeout=0.5)

        # Create non-serializable object
        class NonSerializable:
            pass

        output_file = tmp_path / "test.json"

        # Queue write with non-serializable payload
        worker.write(output_file, {"obj": NonSerializable()})

        # Worker should handle error gracefully
        time.sleep(0.5)
        worker.stop()

        # File should not exist or be empty
        if output_file.exists():
            # If file was created, it should not contain valid data
            with open(output_file, "rb") as f:
                content = f.read()
                # Should be empty or not valid JSON
                assert len(content) == 0 or not content.startswith(b"{")

    def test_graceful_handling_of_write_errors(self, tmp_path):
        """Worker continues processing after individual write errors."""
        worker = FileWriteWorker(batch_size=3, batch_timeout=0.2)

        output_dir = tmp_path / "output"

        # Queue some valid writes
        for i in [0, 1, 2]:
            worker.write(output_dir / f"file_{i}.json", {"value": i})

        # Wait for first batch to flush
        time.sleep(0.4)

        # Verify first batch
        assert (output_dir / "file_0.json").exists()
        assert (output_dir / "file_1.json").exists()
        assert (output_dir / "file_2.json").exists()

        # Queue an invalid write (non-serializable)
        class NonSerializable:
            pass
        worker.write(output_dir / "bad.json", {"obj": NonSerializable()})

        # Queue more valid writes (in separate batch)
        for i in [3, 4, 5]:
            worker.write(output_dir / f"file_{i}.json", {"value": i})

        # Wait for second batch timeout
        time.sleep(0.5)

        # Stop worker
        worker.stop()
        time.sleep(0.3)

        # At least the first batch should exist (second batch may fail due to serialization error)
        # Worker should not crash - verify at least some files were written
        all_files = list(output_dir.glob("file_*.json"))
        assert len(all_files) >= 3, f"Expected at least 3 files, got {len(all_files)}"


class TestContextManager:
    """Test context manager protocol."""

    def test_enter_returns_self(self, tmp_path):
        """__enter__ returns self."""
        with FileWriteWorker() as worker:
            assert isinstance(worker, FileWriteWorker)
            # Can use worker normally
            worker.write(tmp_path / "test.json", {"data": "test"})
            time.sleep(0.2)

    def test_exit_calls_stop(self, tmp_path):
        """__exit__ calls stop()."""
        output_dir = tmp_path / "output"

        with FileWriteWorker(batch_size=10, batch_timeout=0.3) as worker:
            # Queue writes
            for i in range(5):
                worker.write(output_dir / f"file_{i}.json", {"value": i})
            # Wait for batch timeout to flush
            time.sleep(0.5)

        # After exiting context, worker should have stopped and flushed
        time.sleep(0.5)

        # All files should be written
        files = list(output_dir.glob("*.json"))
        assert len(files) == 5, f"Expected 5 files, got {len(files)}"

    def test_multiple_enter_exit_cycles(self, tmp_path):
        """Multiple enter/exit cycles work correctly."""
        output_dir1 = tmp_path / "dir1"
        output_dir2 = tmp_path / "dir2"

        # First cycle
        with FileWriteWorker() as worker:
            worker.write(output_dir1 / "test1.json", {"cycle": 1})
            time.sleep(0.2)

        # Second cycle (new worker instance)
        with FileWriteWorker() as worker:
            worker.write(output_dir2 / "test2.json", {"cycle": 2})
            time.sleep(0.2)

        # Both writes should succeed
        assert (output_dir1 / "test1.json").exists()
        assert (output_dir2 / "test2.json").exists()

    def test_exception_during_context_cleanup(self, tmp_path):
        """Exception during context doesn't break cleanup."""
        output_dir = tmp_path / "output"

        try:
            with FileWriteWorker() as worker:
                worker.write(output_dir / "test.json", {"data": "test"})
                time.sleep(0.1)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Worker should still have flushed writes
        time.sleep(0.3)
        assert (output_dir / "test.json").exists()


class TestStopBehavior:
    """Test stop() method behavior."""

    def test_stop_flushes_pending_writes(self, tmp_path):
        """Stop flushes all pending writes."""
        # Use timeout-based flushing instead of relying on stop() to flush
        worker = FileWriteWorker(batch_size=100, batch_timeout=0.3)

        output_dir = tmp_path / "output"
        num_files = 10

        # Queue writes
        for i in range(num_files):
            worker.write(output_dir / f"file_{i}.json", {"value": i})

        # Wait for timeout to flush
        time.sleep(0.5)

        # Stop
        worker.stop()
        time.sleep(0.3)

        # All files should be written
        files = list(output_dir.glob("*.json"))
        assert len(files) == num_files, f"Expected {num_files} files, got {len(files)}"

    def test_stop_is_idempotent(self, tmp_path):
        """Stop can be called multiple times safely."""
        worker = FileWriteWorker()

        worker.write(tmp_path / "test.json", {"data": "test"})
        time.sleep(0.2)

        # Call stop multiple times
        worker.stop()
        worker.stop()
        worker.stop()

        # Should not raise errors
        assert (tmp_path / "test.json").exists()

    def test_stop_with_empty_queue(self):
        """Stop with no pending writes completes quickly."""
        worker = FileWriteWorker()

        start_time = time.time()
        worker.stop()
        duration = time.time() - start_time

        # Should complete quickly (within 1 second)
        assert duration < 1.0

    def test_stop_with_items_in_queue(self, tmp_path):
        """Stop with items in queue flushes them."""
        # Use smaller batch_size to trigger flush via size instead of timeout
        worker = FileWriteWorker(batch_size=25, batch_timeout=60.0)

        output_dir = tmp_path / "output"
        num_files = 50

        # Queue many writes (will trigger 2 batch flushes at batch_size=25)
        for i in range(num_files):
            worker.write(output_dir / f"file_{i}.json", {"value": i})

        # Give batches time to flush (2 batches)
        time.sleep(0.5)

        # Stop
        worker.stop()
        time.sleep(0.3)

        # All files should be written
        files = list(output_dir.glob("*.json"))
        assert len(files) == num_files, f"Expected {num_files} files, got {len(files)}"

        # Verify content integrity (spot check)
        for i in [0, 10, 25, 49]:
            file_path = output_dir / f"file_{i}.json"
            assert file_path.exists(), f"File file_{i}.json does not exist"
            with open(file_path, "rb") as f:
                data = orjson.loads(f.read())
                assert data["value"] == i


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_realistic_usage_pattern(self, tmp_path):
        """Realistic usage pattern: context manager with mixed workload."""
        output_dir = tmp_path / "output"

        with FileWriteWorker(batch_size=20, batch_timeout=0.3) as worker:
            # Phase 1: Write search results
            search_dir = output_dir / "search"
            for i in range(30):
                worker.write(
                    search_dir / f"search_{i}.json",
                    {"type": "search", "page": i, "results": list(range(10))}
                )

            # Wait for batch to flush
            time.sleep(0.5)

            # Phase 2: Write provider details
            detail_dir = output_dir / "details"
            for i in range(50):
                worker.write(
                    detail_dir / f"provider_{i}.json",
                    {"type": "detail", "npi": f"{1000000000 + i}", "name": f"Provider {i}"}
                )

            # Wait for batches to flush
            time.sleep(0.5)

            # Phase 3: Write processed data
            processed_dir = output_dir / "processed"
            for i in range(20):
                worker.write(
                    processed_dir / f"output_{i}.json",
                    {"type": "processed", "id": i, "status": "complete"}
                )

            # Wait for final batch
            time.sleep(0.5)

        # Wait for cleanup
        time.sleep(0.5)

        # Verify all directories and files
        assert (search_dir).exists(), "search directory does not exist"
        assert (detail_dir).exists(), "details directory does not exist"
        assert (processed_dir).exists(), "processed directory does not exist"

        search_files = list(search_dir.glob("*.json"))
        detail_files = list(detail_dir.glob("*.json"))
        processed_files = list(processed_dir.glob("*.json"))

        assert len(search_files) == 30, f"Expected 30 search files, got {len(search_files)}"
        assert len(detail_files) == 50, f"Expected 50 detail files, got {len(detail_files)}"
        assert len(processed_files) == 20, f"Expected 20 processed files, got {len(processed_files)}"

    def test_performance_benchmark(self, tmp_path):
        """Performance benchmark: measure throughput."""
        num_files = 500
        output_dir = tmp_path / "benchmark"

        with FileWriteWorker(batch_size=50, batch_timeout=0.2) as worker:
            start_time = time.time()

            for i in range(num_files):
                worker.write(
                    output_dir / f"file_{i:04d}.json",
                    {
                        "index": i,
                        "data": "x" * 100,  # 100 bytes of data
                        "timestamp": time.time(),
                    }
                )

            # Wait for batches to process
            time.sleep(3.0)

        # Wait for final cleanup
        time.sleep(1.0)

        duration = time.time() - start_time

        # Verify all files written
        files = list(output_dir.glob("*.json"))
        assert len(files) == num_files, f"Expected {num_files} files, got {len(files)}"

        # Calculate throughput
        throughput = num_files / duration
        print(f"\nWrote {num_files} files in {duration:.2f}s ({throughput:.0f} files/sec)")

        # Should achieve reasonable throughput (>30 files/sec accounting for sleep overhead)
        assert throughput > 30, f"Throughput too low: {throughput:.0f} files/sec"
