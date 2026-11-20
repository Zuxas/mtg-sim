"""
test_hashseed_determinism.py -- a seeded game gives the same result in every
process.

Python randomizes string hashing per process (PYTHONHASHSEED), which changes
the iteration order of a set of card names. Any decision that depends on
that order makes "same seed" mean different games in different processes,
and worker processes on Windows are separate processes. Izzet Lessons' learn
step fell back to the first element of such a set.

Plays a few seeded games of every Standard field deck against one opponent
on both engines, in two subprocesses with different hash seeds, and compares
the outcomes.
"""
from __future__ import annotations
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES = 6
OPPONENT = "azoriusmomo"

CHILD = r"""
import json, os, random, sys
sys.path.insert(0, sys.argv[1])
sys.stdout = open(os.devnull, "w")
from engine.match_runner import _run_single_match
from scripts.compare_engines import _load
from scripts.full_field_gauntlet import STANDARD_DECKS
opp = _load(sys.argv[2])
out = {}
for key in STANDARD_DECKS.values():
    deck = _load(key)
    if deck is None or key == sys.argv[2]:
        continue
    rng = random.Random(11)
    for eng in ("runner", "core"):
        res = []
        for i in range(int(sys.argv[3])):
            s = rng.randint(0, 999999)
            m = _run_single_match((s, deck[0], opp[0], deck[1], opp[1],
                                   i % 2 == 0, False, eng))
            res.append([bool(m.won), m.kill_turn])
        out[key + "/" + eng] = res
sys.__stdout__.write(json.dumps(out))
"""


def _run(hash_seed):
    env = dict(os.environ, PYTHONHASHSEED=str(hash_seed))
    p = subprocess.run([sys.executable, "-c", CHILD, ROOT, OPPONENT, str(GAMES)],
                       capture_output=True, text=True, env=env, cwd=ROOT)
    if p.returncode != 0:
        raise SystemExit("child failed:\n" + p.stderr[-2000:])
    return json.loads(p.stdout)


def main():
    a, b = _run(1), _run(2)
    assert a.keys() == b.keys() and len(a) >= 20, len(a)
    diff = sorted(k for k in a if a[k] != b[k])
    assert not diff, "results depend on PYTHONHASHSEED for: " + ", ".join(diff)
    print(f"PASS: {len(a)} deck/engine cells x {GAMES} seeded games are "
          "identical under two hash seeds")


if __name__ == "__main__":
    main()
