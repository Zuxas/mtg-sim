"""
test_engine_switch.py -- run_match_set(engine=...) plays the same seeded games
on either match engine (#62, migration step 1).

Checks:
1. The default is the runner: omitting engine equals engine="runner".
2. engine="core" plays exactly the games match_engine.run_match would play
   for the same per-game seeds and play/draw order.
3. engine="core" gives the same aggregate for n_workers=1 and n_workers=2.
4. An unknown engine name is refused.
"""
from __future__ import annotations
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.match_apl import MatchAPL, RemovalAwareGoldfishAdapter
from engine import match_engine
from engine.match_runner import run_match_set
from generate_matchup_data import load_deck_and_apl

N, SEED = 40, 7


def _load(name):
    main, _, apl = load_deck_and_apl(name, "modern")
    if not main:
        raise SystemExit(f"deck load failed: {name}")
    return apl, main


def _key(r):
    return (r.a_wins, r.b_wins, r.ties, r.kill_turns)


def main():
    apl_a, deck_a = _load("Boros Energy")
    apl_b, deck_b = _load("Domain Zoo")
    args = (apl_a, deck_a, apl_b, deck_b)

    default = run_match_set(*args, n=N, seed=SEED)
    runner = run_match_set(*args, n=N, seed=SEED, engine="runner")
    assert _key(default) == _key(runner), "default engine is not the runner"
    print("PASS: default engine is the runner")

    core = run_match_set(*args, n=N, seed=SEED, engine="core")
    rng = random.Random(SEED)
    seeds = [rng.randint(0, 999999) for _ in range(N)]
    wins, turns = 0, []
    for i, s in enumerate(seeds):
        random.seed(s)
        a, b = (x if isinstance(x, MatchAPL) else RemovalAwareGoldfishAdapter(x)
                for x in (type(apl_a)(), type(apl_b)()))
        m = match_engine.run_match(a, deck_a, b, deck_b,
                                   on_play=(i % 2 == 0), seed=s)
        wins += m.winner == 'a'
        turns.append(m.kill_turn)
    assert (core.a_wins, core.kill_turns) == (wins, turns), \
        f"core switch {core.a_wins} wins != direct core {wins} wins"
    assert core.a_wins + core.b_wins == N
    print(f"PASS: engine='core' plays the core engine's games "
          f"(core {core.a_wins}/{N}, runner {runner.a_wins}/{N})")

    par = run_match_set(*args, n=N, seed=SEED, engine="core", n_workers=2)
    assert _key(par) == _key(core), "core engine differs between 1 and 2 workers"
    print("PASS: engine='core' is the same with 1 and 2 workers")

    try:
        run_match_set(*args, n=1, engine="nope")
    except ValueError:
        print("PASS: unknown engine refused")
    else:
        raise AssertionError("unknown engine accepted")


if __name__ == "__main__":
    main()
