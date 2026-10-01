"""Replay version compatibility: records from engines before v2-m1.1 are refused with a clear
compatibility error before any rules / card-data / event-log / state check; compatible
records keep exact-replay and hash-mismatch behaviour."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import ENGINE_VERSION
from engine.v2.game import Game
from tests.v2.helpers import tgame
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import ReplayMismatch, ReplayVersionError, make_record, replay
from tests.v2.decks import RG, WU


def _record():
    g = tgame(RG, WU, 77, starting_player=1, turn_limit=8)
    g.run([RandomLegalPolicy(5), RandomLegalPolicy(6)])
    return make_record(g)


def _error(fn):
    try:
        fn()
    except Exception as e:                                       # noqa: BLE001
        return e
    raise AssertionError("expected an error")


def _corrupt_everything_else(rec):
    """Make every later check fail too, proving the version check runs first."""
    rec["config"] = dict(rec["config"], definitions_hash="0" * 64, rules_sha256="0" * 64)
    rec["transition_hashes"] = ["f" * 64]
    rec["full_state_hash"] = "e" * 64


def test_record_without_engine_version_is_legacy_and_refused_first():
    rec = _record()
    del rec["engine_version"]
    rec["config"] = dict(rec["config"], engine_version="v2-m1.0")
    _corrupt_everything_else(rec)
    before = copy.deepcopy(rec)
    e = _error(lambda: replay(rec))
    assert isinstance(e, ReplayVersionError) and not isinstance(e, ReplayMismatch)
    msg = str(e)
    assert "found none (no record-level engine_version field; config says 'v2-m1.0')" in msg
    assert f"required '{ENGINE_VERSION}'" in msg
    assert "predates v2-m1.1" in msg
    assert "compatibility problem, not corrupted game data" in msg
    assert rec == before                                           # not upgraded or rewritten


def test_record_with_older_engine_version_is_refused_first():
    rec = _record()
    rec["engine_version"] = "v2-m1.0"
    _corrupt_everything_else(rec)
    before = copy.deepcopy(rec)
    e = _error(lambda: replay(rec))
    assert isinstance(e, ReplayVersionError)
    msg = str(e)
    assert "found 'v2-m1.0'" in msg and f"required '{ENGINE_VERSION}'" in msg
    assert "predates v2-m1.1" in msg and "compatibility problem, not corrupted game data" in msg
    assert rec == before


def test_record_from_a_different_non_legacy_version_is_refused_without_predates_claim():
    rec = _record()
    rec["engine_version"] = "v2-m9.0"
    msg = str(_error(lambda: replay(rec)))
    assert "found 'v2-m9.0'" in msg and "predates" not in msg and "compatibility problem" in msg


def test_compatible_record_with_correct_hashes_replays():
    rec = _record()
    assert rec["engine_version"] == ENGINE_VERSION
    g = replay(rec)
    assert g.s.full_state_hash() == rec["full_state_hash"]


def test_compatible_record_with_incorrect_hash_is_a_replay_mismatch():
    rec = _record()
    i = len(rec["transition_hashes"]) // 2
    rec["transition_hashes"][i] = "0" * 64
    e = _error(lambda: replay(rec))
    assert isinstance(e, ReplayMismatch) and not isinstance(e, ReplayVersionError)
    assert f"first differing transition {i}" in str(e)
    rec = _record()
    rec["full_state_hash"] = "0" * 64
    e = _error(lambda: replay(rec))
    assert isinstance(e, ReplayMismatch) and "final full_state_hash differs" in str(e)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("REPLAY VERSION TESTS PASS")
