"""M5 (unsupported cards + card-data identity), M6 (isolation), I9 (policy isolation)."""
import ast
import dataclasses
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from engine.card_db import UnknownCardError
from engine.v2 import cards
from engine.v2.cards import CardDataMismatch, UnsupportedCardError, definitions, definitions_hash
from engine.v2.game import Game
from engine.v2.observation import Observation
from engine.v2.policies import RandomLegalPolicy
from engine.v2.record import make_record, replay
from tests.v2.decks import RG, WU


def _raises(exc, fn):
    try:
        fn()
    except exc:
        return True
    return False


def test_unsupported_and_unknown_cards_refused_before_start():
    assert _raises(UnsupportedCardError, lambda: Game.new(RG[:-1] + ["Llanowar Elves"], WU, 0))
    assert _raises(UnknownCardError, lambda: Game.new(RG[:-1] + ["Grizly Bears"], WU, 0))


def test_definitions_hash_stable_across_processes():
    code = "import sys; sys.path.insert(0, r'%s'); from engine.v2.cards import definitions_hash; print(definitions_hash())" % ROOT
    outs = [subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT).stdout.strip().splitlines()[-1]
            for _ in range(2)]
    assert outs[0] == outs[1] == definitions_hash()


def test_definitions_hash_changes_with_one_printed_field():
    defs = dict(definitions())
    base = definitions_hash(defs)
    defs["Grizzly Bears"] = dataclasses.replace(defs["Grizzly Bears"], power=3)
    assert definitions_hash(defs) != base


def test_replay_refuses_other_card_data():
    g = Game.new(RG, WU, 3, turn_limit=2)
    g.run([RandomLegalPolicy(1), RandomLegalPolicy(2)])
    rec = make_record(g)
    replay(rec)                                                     # identical data replays
    rec["config"] = dict(rec["config"], definitions_hash="0" * 64)
    assert _raises(CardDataMismatch, lambda: replay(rec))


def test_installed_oracle_file_mismatch_blocks_new_games():
    orig = cards._sha256_file
    try:
        cards._sha256_file = lambda path: "not-the-pinned-hash"
        cards.oracle_file_sha256.cache_clear()
        cards.definitions.cache_clear()
        assert _raises(CardDataMismatch, lambda: Game.new(RG, WU, 0))
    finally:
        cards._sha256_file = orig
        cards.oracle_file_sha256.cache_clear()
        cards.definitions.cache_clear()
    Game.new(RG, WU, 0)                                             # restored


def test_engine_v2_imports_only_itself_card_db_and_stdlib():
    allowed_engine = {"engine.card_db"}
    bad = []
    v2 = os.path.join(ROOT, "engine", "v2")
    for dirpath, _d, files in os.walk(v2):
        for f in files:
            if not f.endswith(".py"):
                continue
            tree = ast.parse(open(os.path.join(dirpath, f), encoding="utf-8").read())
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module]
                for m in mods:
                    top = m.split(".")[0]
                    if top == "engine" and not (m.startswith("engine.v2") or m in allowed_engine):
                        bad.append((f, m))
                    elif top in ("apl", "data", "calibration", "run_matchup", "generate_matchup_data"):
                        bad.append((f, m))
    assert not bad, bad


def test_observations_are_frozen_plain_values():
    g = Game.new(RG, WU, 1)
    obs = g.observe(0)
    assert _raises(dataclasses.FrozenInstanceError, lambda: setattr(obs, "turn", 99))
    from engine.v2.state import GameState
    from engine.v2.objects import GameObject, StackEntry

    def walk(x):
        if isinstance(x, (GameState, GameObject, StackEntry, dict, list, set)):
            raise AssertionError(f"mutable engine object leaked into an observation: {type(x)}")
        if dataclasses.is_dataclass(x):
            for fld in dataclasses.fields(x):
                walk(getattr(x, fld.name))
        elif isinstance(x, tuple):
            for i in x:
                walk(i)
    walk(obs)
    assert isinstance(obs, Observation)


def test_policy_rng_is_separate_from_game_rng():
    g1 = Game.new(RG, WU, 7, turn_limit=3)
    g2 = Game.new(RG, WU, 7, turn_limit=3)
    g1.run([RandomLegalPolicy(1), RandomLegalPolicy(2)])
    g2.run([RandomLegalPolicy(1), RandomLegalPolicy(2)])
    assert g1.s.log.head == g2.s.log.head                          # same seeds -> identical games
    shuffles = lambda g: [e for t in g.s.log.transitions for e in t.events if e.kind == "Shuffled"][:2]   # noqa: E731
    g3 = Game.new(RG, WU, 7, turn_limit=3)
    g3.run([RandomLegalPolicy(999), RandomLegalPolicy(998)])
    assert shuffles(g1) == shuffles(g3)                            # policy seeds cannot move game shuffles


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("M5/M6/I9 TESTS PASS")
