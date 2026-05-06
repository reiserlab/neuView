"""Tests for the atomic_write context manager."""

import json
import threading
from unittest.mock import patch

import pytest

from neuview.utils.atomic_write import atomic_write

pytestmark = pytest.mark.unit


def test_writes_text_content(tmp_path):
    target = tmp_path / "out.txt"
    with atomic_write(target) as f:
        f.write("hello")
    assert target.read_text() == "hello"


def test_writes_json_content(tmp_path):
    target = tmp_path / "out.json"
    with atomic_write(target) as f:
        json.dump({"k": "v"}, f)
    assert json.loads(target.read_text()) == {"k": "v"}


def test_overwrites_existing_file(tmp_path):
    target = tmp_path / "out.txt"
    target.write_text("old")
    with atomic_write(target) as f:
        f.write("new")
    assert target.read_text() == "new"


def test_no_temp_file_left_after_success(tmp_path):
    target = tmp_path / "out.txt"
    with atomic_write(target) as f:
        f.write("ok")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["out.txt"]


def test_exception_in_body_removes_temp_and_does_not_create_target(tmp_path):
    target = tmp_path / "out.txt"
    with pytest.raises(RuntimeError, match="boom"):
        with atomic_write(target) as f:
            f.write("partial")
            raise RuntimeError("boom")
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_exception_does_not_overwrite_existing_target(tmp_path):
    target = tmp_path / "out.txt"
    target.write_text("original")
    with pytest.raises(RuntimeError):
        with atomic_write(target) as f:
            f.write("partial")
            raise RuntimeError("boom")
    assert target.read_text() == "original"


def test_failed_replace_cleans_up_temp_file(tmp_path):
    target = tmp_path / "out.txt"
    with patch(
        "neuview.utils.atomic_write.os.replace",
        side_effect=OSError("simulated rename failure"),
    ):
        with pytest.raises(OSError, match="simulated"):
            with atomic_write(target) as f:
                f.write("ok")
    assert not target.exists()
    assert list(tmp_path.iterdir()) == []


def test_binary_mode(tmp_path):
    target = tmp_path / "out.bin"
    payload = b"\x00\x01\x02\xff"
    with atomic_write(target, mode="wb", encoding=None) as f:
        f.write(payload)
    assert target.read_bytes() == payload


def test_accepts_str_path(tmp_path):
    target = tmp_path / "out.txt"
    with atomic_write(str(target)) as f:
        f.write("ok")
    assert target.read_text() == "ok"


def test_concurrent_writes_yield_complete_file(tmp_path):
    """Two threads atomically writing the same target must each leave a
    complete file. The final content matches one of them — never a mix."""
    target = tmp_path / "out.txt"
    payload_a = "A" * 10_000
    payload_b = "B" * 10_000
    barrier = threading.Barrier(2)
    errors = []

    def worker(payload):
        try:
            barrier.wait(timeout=5)
            for _ in range(20):
                with atomic_write(target) as f:
                    f.write(payload)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=worker, args=(payload_a,)),
        threading.Thread(target=worker, args=(payload_b,)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    final = target.read_text()
    assert final in (payload_a, payload_b), "torn write — final content is mixed"
    # No temp file should remain.
    leftovers = [p.name for p in tmp_path.iterdir() if p.name != "out.txt"]
    assert leftovers == [], f"Temp file leaked: {leftovers}"
