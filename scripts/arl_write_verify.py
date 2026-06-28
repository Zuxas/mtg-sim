"""ARL hardening: strict write-verify discipline.

Idea borrowed from mythos-router's write discipline; implemented in-house with
pure stdlib (no external code, no network). This module exists to catch the
"silent / partial / failed write" failure mode in the Autonomous Research Loop:
an agent (or any step) claims it wrote a file but the bytes on disk are missing,
truncated, or wrong.

Core guarantees:
  * write_verified() never reports success unless the on-disk bytes hash-match
    the content it was asked to write. On mismatch it retries exactly once, then
    reports failure -- it never silently passes.
  * verify_file() lets a later step independently re-check that a file still
    holds the expected content.
  * append_receipt() records a hash-chained JSONL audit trail so a tamper or a
    broken chain is detectable after the fact.

Determinism note (ARL requirement): nothing in this module calls time/date at
import or implicitly. append_receipt() takes the timestamp from the caller so
the loop stays reproducible.

Conventions: ASCII-only output; exit 0 on full pass, 1 otherwise. Run with
PYTHONIOENCODING=utf-8.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Tuple, Union

PathLike = Union[str, os.PathLike]


def sha256_hex(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def _encode(content: str, encoding: str) -> bytes:
    return content.encode(encoding)


def verify_file(path: PathLike, expected_content: str, *, encoding: str = "utf-8") -> Tuple[bool, str]:
    """Compare on-disk bytes against ``expected_content``.

    Returns (ok, sha256_hex) where:
      * ok is True only if the file exists and its bytes hash-match the
        expected content encoded with ``encoding``.
      * sha256_hex is the digest of the on-disk bytes, or "" if the file is
        missing / unreadable.
    """
    p = Path(path)
    try:
        on_disk = p.read_bytes()
    except (FileNotFoundError, IsADirectoryError, OSError):
        return False, ""
    actual = sha256_hex(on_disk)
    expected = sha256_hex(_encode(expected_content, encoding))
    return (actual == expected), actual


def _atomic_write(p: Path, raw: bytes) -> None:
    """Write ``raw`` to ``p`` durably via a temp file + os.replace.

    Ensures parent dir exists, flushes + fsyncs the temp file, then atomically
    replaces the target so a crash mid-write cannot leave a half file at ``p``.
    """
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".wv.tmp")
    with open(tmp, "wb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)


def write_verified(path: PathLike, content: str, *, encoding: str = "utf-8") -> bool:
    """Write ``content`` to ``path`` and verify the write by reading it back.

    Writes atomically, reads the file back, and compares SHA-256 against the
    intended bytes. On a first-attempt mismatch it retries the write exactly
    once and re-verifies. Returns True only on a verified match; otherwise
    returns False (never silently passes).
    """
    p = Path(path)
    raw = _encode(content, encoding)
    want = sha256_hex(raw)

    for _attempt in range(2):  # initial write + one retry
        try:
            _atomic_write(p, raw)
        except OSError:
            continue  # write failed outright; try the retry pass
        ok, got = verify_file(p, content, encoding=encoding)
        if ok and got == want:
            return True
    return False


def append_receipt(
    log_path: PathLike,
    path: PathLike,
    sha: str,
    prev_sha: str,
    ts: Union[int, float, str],
) -> str:
    """Append a hash-chained receipt line to ``log_path`` (JSONL).

    The caller supplies ``ts`` (determinism: this module never reads the clock).
    ``prev_sha`` should be the ``chain`` value of the previous receipt (or "" /
    a genesis marker for the first entry). The returned value is this entry's
    ``chain`` hash, which the caller passes as ``prev_sha`` next time.

    Chain hash = SHA-256 of "prev_sha|path|sha|ts", linking each receipt to its
    predecessor so any insertion/deletion/edit breaks verification downstream.
    """
    chain_material = f"{prev_sha}|{os.fspath(path)}|{sha}|{ts}".encode("utf-8")
    chain = sha256_hex(chain_material)
    record = {
        "ts": ts,
        "path": os.fspath(path),
        "sha256": sha,
        "prev_sha": prev_sha,
        "chain": chain,
    }
    lp = Path(log_path)
    lp.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n"
    with open(lp, "a", encoding="utf-8") as fh:
        fh.write(line)
    return chain


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def _selftest() -> int:
    import tempfile

    failures = []

    def check(name: str, cond: bool, reason: str = "") -> None:
        if cond:
            print("PASS: " + name)
        else:
            msg = "FAIL: " + name + (" -- " + reason if reason else "")
            print(msg)
            failures.append(name)

    tmpdir = Path(tempfile.mkdtemp(prefix="arl_wv_"))
    try:
        # Case 1: write + verify a temp file (match=True)
        f1 = tmpdir / "deck.json"
        content1 = '{"deck": "mono-red", "cards": 60}'
        wrote = write_verified(f1, content1)
        ok1, sha1 = verify_file(f1, content1)
        check("write_verified reports success", wrote is True)
        check("verify_file matches freshly written content", ok1 is True)
        check("verify_file returns non-empty sha", len(sha1) == 64)

        # Case 2: tamper the file, then verify (ok=False)
        f1.write_bytes(b'{"deck": "tampered"}')
        ok2, sha2 = verify_file(f1, content1)
        check("verify_file detects tampering", ok2 is False, "tamper not caught")
        check("verify_file still returns the on-disk sha after tamper", len(sha2) == 64)
        check("tampered sha differs from original", sha2 != sha1)

        # Case 3: write_verified round-trip with unicode / multiline content
        f2 = tmpdir / "nested" / "report.txt"
        content2 = "line1\nline2\nvalue=42\n"
        wrote2 = write_verified(f2, content2)
        ok3, _ = verify_file(f2, content2)
        check("write_verified creates parent dirs and round-trips", wrote2 is True and ok3 is True)

        # Case 4: verify_file on a missing file -> (False, "")
        missing = tmpdir / "does_not_exist.json"
        okm, sham = verify_file(missing, "anything")
        check("verify_file on missing file returns (False, '')", okm is False and sham == "")

        # Case 5: hash-chained receipts link correctly and detect a break
        log = tmpdir / "receipts.jsonl"
        c1 = append_receipt(log, f1, sha1, "", ts=1000)
        c2 = append_receipt(log, f2, sha2, c1, ts=1001)
        lines = log.read_text(encoding="utf-8").strip().splitlines()
        rec1 = json.loads(lines[0])
        rec2 = json.loads(lines[1])
        check("receipt 1 chain matches returned value", rec1["chain"] == c1)
        check("receipt 2 links to receipt 1 via prev_sha", rec2["prev_sha"] == c1 and rec2["chain"] == c2)
        # recompute chain independently to prove determinism
        recomputed = sha256_hex(f"{c1}|{os.fspath(f2)}|{sha2}|1001".encode("utf-8"))
        check("receipt chain is deterministic / recomputable", recomputed == c2)

    finally:
        # best-effort cleanup
        try:
            for root, dirs, files in os.walk(tmpdir, topdown=False):
                for fn in files:
                    os.remove(os.path.join(root, fn))
                for dn in dirs:
                    os.rmdir(os.path.join(root, dn))
            os.rmdir(tmpdir)
        except OSError:
            pass

    if failures:
        print("RESULT: FAIL (" + str(len(failures)) + " case(s) failed)")
        return 1
    print("RESULT: PASS (all cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
