"""I8 determinism (lint + guard), policy-RNG isolation, and fresh-process replay of stored
JSON records under different PYTHONHASHSEED values (spec sections 8, 11 I8, gate M3)."""
import ast
import json
import os
import random
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from engine.v2.game import Game
from tests.v2.helpers import tgame
from engine.v2.policies import BasicScriptedPolicy, RandomLegalPolicy
from engine.v2.record import make_record
from tests.v2.decks import RG, WU

V2 = os.path.join(ROOT, "engine", "v2")


def test_lint_no_global_random_time_or_datetime():
    bad = []
    for dirpath, _d, files in os.walk(V2):
        for f in files:
            if not f.endswith(".py"):
                continue
            tree = ast.parse(open(os.path.join(dirpath, f), encoding="utf-8").read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    bad += [(f, a.name) for a in node.names if a.name.split(".")[0] in ("time", "datetime")]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in ("time", "datetime"):
                        bad.append((f, node.module))
                    if node.module == "random":
                        bad += [(f, f"from random import {a.name}") for a in node.names if a.name != "Random"]
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    v = node.func.value
                    if isinstance(v, ast.Name) and v.id == "random" and node.func.attr != "Random":
                        bad.append((f, f"random.{node.func.attr}()"))
    assert not bad, bad


def test_guard_global_random_is_never_used():
    names = ["random", "randrange", "randint", "choice", "choices", "shuffle", "sample", "uniform", "getrandbits"]
    saved = {n: getattr(random, n) for n in names}

    def boom(*a, **k):
        raise AssertionError("engine used the global random module")
    try:
        for n in names:
            setattr(random, n, boom)
        for seed in range(3):
            tgame(RG, WU, seed, starting_player=seed % 2).run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 1)])
            tgame(RG, WU, seed, starting_player=seed % 2).run([BasicScriptedPolicy(), BasicScriptedPolicy()])
    finally:
        for n, fn in saved.items():
            setattr(random, n, fn)


class _NoisyScripted:
    """Consumes a seed-dependent amount of its OWN RNG per decision, then decides exactly like
    BasicScriptedPolicy. If policy randomness could leak into the game, logs would differ."""

    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.inner = BasicScriptedPolicy()

    def choose(self, obs, actions):
        for _ in range(self.rng.randrange(6)):
            self.rng.random()
        return self.inner.choose(obs, actions)


def test_policy_rng_cannot_perturb_game_rng_after_policy_decisions():
    post_decision_shuffles = 0
    for seed in range(20):
        plain = tgame(RG, WU, seed, starting_player=seed % 2)
        plain.run([BasicScriptedPolicy(), BasicScriptedPolicy()])
        noisy = tgame(RG, WU, seed, starting_player=seed % 2)
        noisy.run([_NoisyScripted(seed * 11 + 1), _NoisyScripted(seed * 13 + 2)])
        assert plain.s.log.head == noisy.s.log.head
        assert plain.s.full_state_hash() == noisy.s.full_state_hash()        # includes the game RNG state
        post_decision_shuffles += sum(t.kind == "mulligan_execute" for t in plain.s.log.transitions)
    # the comparison covers game shuffles made AFTER a policy decision (a declared mulligan)
    assert post_decision_shuffles >= 1, "no compared game mulliganed; extend the seed range"


_REPLAYER = r"""
import json, sys
sys.path.insert(0, %r)
from engine.v2.record import replay
recs = json.load(open(%r))
for r in recs:
    replay(r)
print("REPLAYED", len(recs))
"""


def _records(n):
    recs = []
    for seed in range(n):
        g = tgame(RG, WU, 700 + seed, starting_player=seed % 2, turn_limit=4 if seed % 7 == 0 else 50)
        g.run([RandomLegalPolicy(seed), RandomLegalPolicy(seed + 100)])
        recs.append(make_record(g, policy_seeds=[seed, seed + 100]))
    return recs


def test_stored_json_records_replay_in_fresh_processes_with_other_hash_seeds():
    recs = _records(16)
    assert any(r["result"][-1] == "turn_limit" for r in recs)
    assert any(any(a[0] == "DeclareMulligan" for a in r["actions"]) for r in recs)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "records.json")
        json.dump(recs, open(path, "w"))
        for hashseed in (None, "4242", "7"):
            env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
            if hashseed is not None:
                env["PYTHONHASHSEED"] = hashseed
            out = subprocess.run([sys.executable, "-c", _REPLAYER % (ROOT, path)], capture_output=True,
                                 text=True, cwd=ROOT, env=env)
            assert f"REPLAYED {len(recs)}" in out.stdout, (hashseed, out.stdout[-500:], out.stderr[-2000:])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("DETERMINISM TESTS PASS")
