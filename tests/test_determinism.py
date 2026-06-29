"""test_determinism.py -- Stage 1.7 regression test.

Two consecutive run_match_set calls with the same seed must produce
bit-identical results, regardless of the global random module's
state at entry. Pre-Stage-1.7, naked random.foo() consumers in
engine code (zones.shuffle, opponent.py, race.py, several handler
sites) leaked through global random state changes between calls,
producing per-matchup variance up to ±2.5pp at n=1000.

Spec: harness/specs/2026-04-28-stage-1.7-event-bus-determinism.md
"""
import sys, os, random, subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from data.deck import load_deck_from_file
from engine.match_runner import run_match_set
from apl.boros_energy import BorosEnergyAPL


def _be_deck():
    main, _ = load_deck_from_file('decks/boros_energy_modern.txt')
    return main


def test_match_set_deterministic_across_consecutive_calls():
    """Two seed=42 mirror runs in same process must match bit-exactly."""
    deck = _be_deck()
    r1 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=20, seed=42, mix_play_draw=True)
    r2 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=20, seed=42, mix_play_draw=True)
    assert r1.a_wins == r2.a_wins, f"a_wins drift: {r1.a_wins} vs {r2.a_wins}"
    assert r1.b_wins == r2.b_wins, f"b_wins drift: {r1.b_wins} vs {r2.b_wins}"
    assert r1.avg_turns == r2.avg_turns, \
        f"avg_turns drift: {r1.avg_turns} vs {r2.avg_turns}"


def test_match_set_preserves_global_random_state():
    """run_match_set's save/seed/restore must leave global random unchanged."""
    deck = _be_deck()
    random.seed(12345)
    pre_state = random.getstate()
    run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                  n=5, seed=42, mix_play_draw=True)
    post_state = random.getstate()
    assert pre_state == post_state, \
        "global random state mutated by run_match_set; save/restore broken"


def test_match_set_deterministic_under_polluted_global_random():
    """Even if caller's global random advances between calls, results match."""
    deck = _be_deck()
    random.seed(0)
    r1 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=10, seed=42, mix_play_draw=True)
    # Pollute global random heavily between calls
    for _ in range(1000):
        random.random()
    r2 = run_match_set(BorosEnergyAPL(), deck, BorosEnergyAPL(), deck,
                       n=10, seed=42, mix_play_draw=True)
    assert r1.a_wins == r2.a_wins and r1.avg_turns == r2.avg_turns, \
        "pollution of global random leaked through Stage 1.7 guard"


def test_n_workers_determinism():
    """Different n_workers values must produce bit-identical aggregates."""
    deck = _be_deck()
    args = dict(apl_a=BorosEnergyAPL(), deck_a=deck,
                apl_b=BorosEnergyAPL(), deck_b=deck,
                n=50, seed=42, mix_play_draw=True)
    r1 = run_match_set(**args, n_workers=1)
    r4 = run_match_set(**args, n_workers=4)
    r8 = run_match_set(**args, n_workers=8)
    assert r1.a_wins == r4.a_wins == r8.a_wins, \
        f"a_wins not invariant: n1={r1.a_wins} n4={r4.a_wins} n8={r8.a_wins}"
    assert r1.avg_turns == r4.avg_turns == r8.avg_turns, \
        f"avg_turns not invariant: n1={r1.avg_turns} n4={r4.avg_turns} n8={r8.avg_turns}"


# ---------------------------------------------------------------------------
# Cross-process determinism (IMPERFECTIONS: engine-apl-nondeterminism-id-based-
# ordering). The Stage-1.7 tests above prove same-process / global-random-state
# determinism. They do NOT catch object-identity / set-iteration ordering that
# varies by PYTHONHASHSEED across processes: iterating a *set* of strings (e.g.
# BOUNCE_LANDS in the Amulet goldfish APL) yields a hash-seed-dependent order,
# so the SAME seed produced different avg_kill_turn in different processes
# (measured: 6.117 vs 5.900 at seed=42). These tests spawn child processes at
# pinned (0, 1) and unpinned PYTHONHASHSEED and assert bit-identical results.
# ---------------------------------------------------------------------------

_CHILD_SRC = r'''
import sys, os
sys.path.insert(0, {repo!r})
os.chdir({repo!r})
from data.deck import load_deck_from_file
target, n, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
if target == "amulet":
    from engine.runner import run_simulation
    from apl.amulet_titan import AmuletTitanAPL
    main, _ = load_deck_from_file("decks/amulet_titan_modern.txt")
    res = run_simulation(AmuletTitanAPL(), main, n=n, seed=seed)
    print("RESULT", res.won_games, res.n_games, "%.6f" % (res.avg_kill_turn() or 0))
else:
    from engine.match_runner import run_match_set
    from apl.boros_energy_match import BorosEnergyMatchAPL
    main, _ = load_deck_from_file("decks/boros_energy_modern.txt")
    r = run_match_set(BorosEnergyMatchAPL(), main, BorosEnergyMatchAPL(), main,
                      n=n, seed=seed, mix_play_draw=True)
    print("RESULT", r.a_wins, r.b_wins, "%.6f" % r.avg_turns)
'''.format(repo=REPO_ROOT)


def _run_child(target, n, seed, hashseed):
    """Run one sim in a fresh process at a given PYTHONHASHSEED; return RESULT line.

    hashseed=None leaves PYTHONHASHSEED unset (randomized hashing) -- this is the
    'unpinned' case the imperfection requires alongside the pinned cases.
    """
    env = dict(os.environ)
    if hashseed is None:
        env.pop("PYTHONHASHSEED", None)
    else:
        env["PYTHONHASHSEED"] = str(hashseed)
    env["PYTHONIOENCODING"] = "utf-8"
    out = subprocess.run([sys.executable, "-c", _CHILD_SRC, target, str(n), str(seed)],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="replace", env=env, cwd=REPO_ROOT)
    for line in out.stdout.splitlines():
        if line.startswith("RESULT"):
            return line.strip()
    raise AssertionError(
        f"child ({target} n={n} seed={seed} hs={hashseed}) produced no RESULT line.\n"
        f"stdout:\n{out.stdout}\nstderr:\n{out.stderr}")


def _assert_cross_process_identical(target, n, seeds):
    for seed in seeds:
        results = {hs: _run_child(target, n, seed, hs) for hs in (0, 1, None)}
        uniq = set(results.values())
        assert len(uniq) == 1, \
            f"{target} cross-process drift at seed={seed} (max-dev != 0): {results}"


def test_amulet_goldfish_cross_process_deterministic():
    """Amulet goldfish: same seed must give bit-identical results across processes.

    Regression guard for the BOUNCE_LANDS set-iteration nondeterminism. n=60 is
    sized to the divergence observed pre-fix (every probed seed drifted at n=60).
    """
    _assert_cross_process_identical("amulet", 60, (42, 1, 100))


def test_boros_match_cross_process_deterministic():
    """Boros Energy match mirror: bit-identical across PYTHONHASHSEED at same seed.

    The imperfection named the Boros mirror as nondeterministic; the residual
    APL id() usage is identity bookkeeping the engine reads via
    blocker_assignments.get(id(atk)) (not an ordering key), so no APL change was
    needed -- this asserts the mirror is in fact cross-process stable.
    """
    _assert_cross_process_identical("boros", 120, (42, 1))


if __name__ == "__main__":
    test_match_set_deterministic_across_consecutive_calls()
    test_match_set_preserves_global_random_state()
    test_match_set_deterministic_under_polluted_global_random()
    test_n_workers_determinism()
    print("ALL 4 STAGE-1.7 TESTS PASS")
    test_amulet_goldfish_cross_process_deterministic()
    test_boros_match_cross_process_deterministic()
    print("ALL 2 CROSS-PROCESS DETERMINISM TESTS PASS")
    print("ALL 6 TESTS PASS")
