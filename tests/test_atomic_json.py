"""test_atomic_json.py -- engine/atomic_json.py regression test.

Validates the lockfile-based RMW serializer that closes the
read-modify-write race documented in
harness/knowledge/tech/cache-key-audit-2026-04-28.md (Findings 1, 4, 5).

Pre-fix: concurrent canonical+variant gauntlets racing on
data/sim_matchup_matrix.json could lose entries (last-writer-wins).
Post-fix: 8 concurrent worker threads x 25 RMW ops = 200 entries,
all preserved.

Spec: closes IMPERFECTIONS:sim-matchup-matrix-rmw-race +
auto-apl-registry-rmw-race-latent + optimization-memory-rmw-race-latent.
"""
import json
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.atomic_json import atomic_rmw_json, atomic_write_json


def test_atomic_write_json_basic():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    try:
        atomic_write_json(tmp.name, {"hello": "world", "n": 42})
        with open(tmp.name) as f:
            assert json.load(f) == {"hello": "world", "n": 42}
    finally:
        os.unlink(tmp.name)


def test_atomic_rmw_json_sequential_merge():
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    try:
        atomic_rmw_json(tmp.name, lambda d: d.update({"a": 1}), default_factory=dict)
        atomic_rmw_json(tmp.name, lambda d: d.update({"b": 2}), default_factory=dict)
        with open(tmp.name) as f:
            assert json.load(f) == {"a": 1, "b": 2}
    finally:
        os.unlink(tmp.name)
        if os.path.exists(tmp.name + ".lock"):
            os.unlink(tmp.name + ".lock")


def test_atomic_rmw_json_concurrent_writers():
    """8 threads x 25 ops = 200 unique entries; all must survive."""
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    try:
        atomic_write_json(tmp.name, {})
        NUM_WORKERS = 8
        PER_WORKER = 25
        errors = []

        def worker(wid):
            try:
                for i in range(PER_WORKER):
                    key = f"w{wid}_k{i}"
                    atomic_rmw_json(
                        tmp.name,
                        lambda d, k=key, v=wid: d.update({k: v}),
                        default_factory=dict,
                    )
            except Exception as e:
                errors.append((wid, type(e).__name__, str(e)))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(NUM_WORKERS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"worker errors: {errors[:3]}"
        with open(tmp.name) as f:
            data = json.load(f)
        assert len(data) == NUM_WORKERS * PER_WORKER, (
            f"lost entries: got {len(data)}, expected {NUM_WORKERS * PER_WORKER}"
        )
    finally:
        os.unlink(tmp.name)
        if os.path.exists(tmp.name + ".lock"):
            os.unlink(tmp.name + ".lock")


if __name__ == "__main__":
    test_atomic_write_json_basic()
    print("PASS: test_atomic_write_json_basic")
    test_atomic_rmw_json_sequential_merge()
    print("PASS: test_atomic_rmw_json_sequential_merge")
    test_atomic_rmw_json_concurrent_writers()
    print("PASS: test_atomic_rmw_json_concurrent_writers")
    print("ALL ATOMIC JSON TESTS PASS")
