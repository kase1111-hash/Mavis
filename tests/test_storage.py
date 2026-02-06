"""Tests for mavis.storage -- atomic JSON I/O with file locking."""

import json
import os
import tempfile

import pytest

from mavis.storage import atomic_json_save, locked_json_load, locked_open


def test_atomic_json_save_and_load():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        atomic_json_save(path, {"key": "value", "count": 42})
        data = locked_json_load(path)
        assert data == {"key": "value", "count": 42}
    finally:
        os.unlink(path)


def test_locked_json_load_missing_file():
    assert locked_json_load("/tmp/nonexistent_mavis_test_file.json") is None


def test_locked_json_load_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        assert locked_json_load(path) is None
    finally:
        os.unlink(path)


def test_atomic_json_save_creates_directory():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "subdir", "data.json")
    try:
        atomic_json_save(path, {"nested": True})
        data = locked_json_load(path)
        assert data == {"nested": True}
    finally:
        import shutil
        shutil.rmtree(d)


def test_atomic_json_save_overwrites():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        atomic_json_save(path, {"v": 1})
        atomic_json_save(path, {"v": 2})
        data = locked_json_load(path)
        assert data == {"v": 2}
    finally:
        os.unlink(path)


def test_locked_open_read():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"hello": "world"}, f)
        path = f.name
    try:
        with locked_open(path, "r") as f:
            data = json.load(f)
        assert data == {"hello": "world"}
    finally:
        os.unlink(path)


def test_locked_open_write():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        with locked_open(path, "w") as f:
            json.dump({"written": True}, f)
        with locked_open(path, "r") as f:
            data = json.load(f)
        assert data == {"written": True}
    finally:
        os.unlink(path)
