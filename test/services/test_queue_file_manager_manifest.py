"""Tests for QueueFileManager.update_cache_manifest concurrency."""

import asyncio
import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from neuview.services.queue_file_manager import QueueFileManager

pytestmark = pytest.mark.unit


@pytest.fixture
def manager(tmp_path):
    config = SimpleNamespace(output=SimpleNamespace(directory=str(tmp_path)))
    return QueueFileManager(config)


@pytest.fixture
def manifest_path(tmp_path) -> Path:
    return tmp_path / ".cache" / "manifest.json"


def test_update_writes_valid_manifest(manager, manifest_path):
    asyncio.run(manager.update_cache_manifest(["A", "B"]))
    data = json.loads(manifest_path.read_text())
    assert sorted(data["neuron_types"]) == ["A", "B"]
    assert data["count"] == 2
    assert "created_at" in data and "updated_at" in data


def test_repeated_updates_accumulate(manager, manifest_path):
    asyncio.run(manager.update_cache_manifest(["A"]))
    asyncio.run(manager.update_cache_manifest(["B"]))
    asyncio.run(manager.update_cache_manifest(["A", "C"]))
    data = json.loads(manifest_path.read_text())
    assert sorted(data["neuron_types"]) == ["A", "B", "C"]
    assert data["count"] == 3


def test_concurrent_updates_do_not_lose_entries(manager, manifest_path):
    """Without a lock, two threads that both load v0, mutate, and write back
    would race and one entry would be lost. With FileLock + atomic write,
    every type from every caller must end up in the final manifest."""
    types = [f"type_{i:02d}" for i in range(16)]
    barrier = threading.Barrier(len(types))
    errors = []

    def worker(neuron_type):
        try:
            barrier.wait(timeout=5)
            asyncio.run(manager.update_cache_manifest([neuron_type]))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(t,)) for t in types]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Worker errors: {errors}"
    data = json.loads(manifest_path.read_text())
    assert sorted(data["neuron_types"]) == sorted(types)
    assert data["count"] == len(types)


def test_no_temp_file_left_behind(manager, tmp_path):
    asyncio.run(manager.update_cache_manifest(["A"]))
    cache_dir = tmp_path / ".cache"
    leftovers = [p.name for p in cache_dir.iterdir() if p.name.endswith(".tmp")]
    assert leftovers == [], f"Temp file leaked: {leftovers}"
