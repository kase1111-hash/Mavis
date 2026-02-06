"""Shared file I/O utilities for Mavis JSON store classes.

Provides atomic writes with file-locking to prevent data corruption
from concurrent process access.
"""

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from typing import Any


@contextmanager
def locked_open(path: str, mode: str = "r"):
    """Open a file with an advisory file lock.

    Uses LOCK_SH for read modes, LOCK_EX for write modes.
    The lock is released when the context manager exits.
    """
    f = open(path, mode)
    try:
        if "r" in mode and "w" not in mode and "a" not in mode and "+" not in mode:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        else:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield f
    finally:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        f.close()


def atomic_json_save(path: str, data: Any) -> None:
    """Write JSON data atomically with file locking.

    1. Creates a temp file in the same directory.
    2. Writes JSON data to the temp file.
    3. Atomically replaces the target file via os.replace().
    4. On failure, cleans up the temp file.

    An exclusive lock is held on the temp file during the write to
    prevent concurrent writers from clobbering each other.
    """
    dir_path = os.path.dirname(path) or "."
    os.makedirs(dir_path, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def locked_json_load(path: str) -> Any:
    """Read and parse a JSON file with a shared lock.

    Returns None if the file doesn't exist or is empty.
    """
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    with locked_open(path, "r") as f:
        return json.load(f)
