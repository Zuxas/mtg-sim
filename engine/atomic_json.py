"""
Atomic JSON read-modify-write helpers.

Closes the read-modify-write race documented in
harness/knowledge/tech/cache-key-audit-2026-04-28.md (Findings 1, 4, 5)
and the IMPERFECTIONS entries:
  - sim-matchup-matrix-rmw-race
  - auto-apl-registry-rmw-race-latent
  - optimization-memory-rmw-race-latent

Strategy:
  - Sentinel-lockfile serialization via os.O_CREAT | os.O_EXCL
    (cross-platform; works on Windows where fcntl.flock does not).
    A second writer spins on the lock with backoff until the first
    releases. Stale locks (older than `stale_lock_s`) are forcibly
    reclaimed.
  - Within the lock: tempfile + os.replace for crash safety (no
    torn writes if the process dies mid-write).
"""
from __future__ import annotations

import json
import os
import random
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Optional


def atomic_write_json(path: str | Path, data: Any, indent: int = 2) -> None:
    """Atomically replace path with `data` serialized as JSON.

    Crash-safe (tempfile + os.replace) but does NOT serialize concurrent
    writers — use atomic_rmw_json when the new value depends on the old.
    """
    p = str(path)
    d = os.path.dirname(p) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".atomic_", suffix=".tmp.json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tf:
            json.dump(data, tf, indent=indent, default=str)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _acquire_lock(
    lock_path: str,
    *,
    timeout_s: float,
    base_delay_ms: float,
    max_delay_s: float,
    stale_lock_s: float,
) -> int:
    """Acquire an O_EXCL lock by creating a sentinel file. Returns fd.
    Spins with exponential backoff up to `timeout_s`. If an existing
    lockfile is older than `stale_lock_s`, forcibly remove it (crash
    recovery)."""
    deadline = time.time() + timeout_s
    attempt = 0
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            return fd
        except FileExistsError:
            try:
                age = time.time() - os.stat(lock_path).st_mtime
                if age > stale_lock_s:
                    os.unlink(lock_path)
                    continue
            except OSError:
                pass
            if time.time() > deadline:
                raise TimeoutError(
                    f"atomic_rmw_json: could not acquire lock {lock_path} within {timeout_s}s"
                )
            delay_s = min(
                max_delay_s,
                (base_delay_ms / 1000.0) * (2 ** attempt) * (0.5 + random.random()),
            )
            time.sleep(delay_s)
            attempt += 1


def _release_lock(fd: int, lock_path: str) -> None:
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        os.unlink(lock_path)
    except OSError:
        pass


def atomic_rmw_json(
    path: str | Path,
    mutator: Callable[[Any], None],
    default_factory: Callable[[], Any] = dict,
    timeout_s: float = 30.0,
    base_delay_ms: float = 5.0,
    max_delay_s: float = 0.5,
    stale_lock_s: float = 60.0,
    indent: int = 2,
) -> Any:
    """Read-modify-write a JSON file under a cross-platform sentinel lock.

    1. Acquire `<path>.lock` via O_CREAT|O_EXCL (spins with backoff).
    2. Read current state (or default_factory() if absent / unparseable).
    3. Apply mutator(data) in place.
    4. Write to tempfile, os.replace into final path (crash-safe).
    5. Release lock.

    Stale locks older than `stale_lock_s` are reclaimed (crashed prior writer).

    Returns the mutated data after successful write.

    Raises TimeoutError if the lock can't be acquired within `timeout_s`.
    """
    p = str(path)
    d = os.path.dirname(p) or "."
    os.makedirs(d, exist_ok=True)
    lock_path = p + ".lock"

    fd = _acquire_lock(
        lock_path,
        timeout_s=timeout_s,
        base_delay_ms=base_delay_ms,
        max_delay_s=max_delay_s,
        stale_lock_s=stale_lock_s,
    )
    try:
        # Read current
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                data = default_factory()
        else:
            data = default_factory()

        # Mutate
        mutator(data)

        # Atomic write via tempfile + replace (crash safety inside the lock)
        wfd, tmp = tempfile.mkstemp(prefix=".atomic_", suffix=".tmp.json", dir=d)
        try:
            with os.fdopen(wfd, "w", encoding="utf-8") as tf:
                json.dump(data, tf, indent=indent, default=str)
            os.replace(tmp, p)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

        return data
    finally:
        _release_lock(fd, lock_path)
