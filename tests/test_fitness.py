"""
tests/test_fitness.py -- Phase 3 tests for APL caching + fitness scoring.

Fully offline: APL generation, the goldfish sim, and the APL provider are all
injected, so no oracle DB and no Claude call are needed.

Run: python tests/test_fitness.py
"""

import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from gen.generator import DeckCandidate
from gen.apl_cache import decklist_hash, package_set_key, get_apl_for_candidate
from gen.fitness import (field_winrate, speed_score, compute_fitness,
                         verdict_for, evaluate)

FAKE_APL_SRC = """
from apl.base_apl import BaseAPL
class CacheTestAPL(BaseAPL):
    name = "CacheTest"
    def keep(self, hand, mulligans, on_play): return True
    def bottom(self, hand, n): return list(hand)[:n]
    def main_phase(self, gs): pass
"""


class FakeRes:
    """Minimal SimulationResults stand-in."""
    def __init__(self, dist, win_rate=0.6, mull=10.0):
        self._dist = dist
        self._wr = win_rate
        self._mull = mull
        self.kill_turns = [t for t, p in dist.items() for _ in range(int(p))]
    def kill_turn_distribution(self): return self._dist
    def win_rate(self): return self._wr
    def avg_kill_turn(self):
        return sum(self.kill_turns) / len(self.kill_turns) if self.kill_turns else None
    def median_kill_turn(self):
        s = sorted(self.kill_turns); return s[len(s) // 2] if s else None
    def mull_rate(self): return self._mull


def main():
    failures = []

    def check(cond, msg):
        print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
        if not cond:
            failures.append(msg)

    # --- decklist_hash ---------------------------------------------------
    mb1 = {"Lightning Bolt": 4, "Mountain": 20, "Goblin Guide": 4}
    mb2 = {"Goblin Guide": 4, "Lightning Bolt": 4, "Mountain": 20}    # reordered
    check(decklist_hash(mb1) == decklist_hash(mb2), "decklist_hash is order-independent")
    check(decklist_hash(mb1) != decklist_hash({**mb1, "Mountain": 19}),
          "decklist_hash changes with contents")

    # --- APL cache reuse tiers (injected generator, temp dirs) -----------
    calls = {"n": 0}
    def fake_gen(pb):
        calls["n"] += 1
        return FAKE_APL_SRC

    base = DeckCandidate(name="Burn A", mainboard=mb1, packages=["mono_red_core"])
    twin = DeckCandidate(name="Burn A copy", mainboard=dict(mb2), packages=["mono_red_core"])
    variant = DeckCandidate(name="Burn A manabase variant",
                            mainboard={**mb1, "Mountain": 19, "Sunbaked Canyon": 1},
                            packages=["mono_red_core"])

    with tempfile.TemporaryDirectory() as d:
        cache_dir = os.path.join(d, "auto_apls")
        reg = os.path.join(d, "registry.json")
        kw = dict(generate_fn=fake_gen, cache_dir=cache_dir, registry_path=reg)

        apl1, i1 = get_apl_for_candidate(base, **kw)
        check(apl1 is not None and i1["source"] == "generated", "tier 3: first deck generates")
        check(calls["n"] == 1, "one generate call so far")

        apl2, i2 = get_apl_for_candidate(twin, **kw)
        check(i2["source"] == "hash_hit", "tier 1: identical decklist is a hash hit")
        check(calls["n"] == 1, "hash hit triggers no new generate")

        apl3, i3 = get_apl_for_candidate(variant, **kw)
        check(i3["source"] == "sibling", "tier 2: manabase variant reuses package-set sibling")
        check(calls["n"] == 1, "sibling reuse triggers no new generate")

        # fallback when generation raises
        def boom(pb): raise RuntimeError("no network")
        apl4, i4 = get_apl_for_candidate(
            DeckCandidate(name="Other", mainboard={"X": 60}, packages=["combo_core"]),
            generate_fn=boom, cache_dir=cache_dir, registry_path=reg)
        check(i4["source"] == "fallback" and i4["fidelity"] == "low",
              "generation failure falls back to low-fidelity GenericAPL")

    # --- field race math -------------------------------------------------
    fast_field = {"Slowpoke": ({8: 100.0}, 1.0)}
    slow_field = {"Speedy": ({3: 100.0}, 1.0)}
    fw_fast, _ = field_winrate({3: 90.0, 4: 10.0}, fast_field, n=4000)
    fw_slow, _ = field_winrate({12: 90.0, 13: 10.0}, slow_field, n=4000)
    check(fw_fast > 80.0, f"fast deck wins the race vs a slow field ({fw_fast})")
    check(fw_slow < 20.0, f"slow deck loses the race vs a fast field ({fw_slow})")

    check(speed_score({3: 50.0, 4: 30.0}) > speed_score({9: 50.0, 10: 30.0}),
          "speed_score rewards faster kills")
    check(compute_fitness(60, 70, 80, 90) > compute_fitness(40, 40, 40, 40),
          "compute_fitness monotonic in its inputs")

    # --- verdict mapping + fidelity cap ----------------------------------
    check(verdict_for(60.0, "high") == "strong", "high field_wr + high fidelity -> strong")
    check(verdict_for(60.0, "low") == "playable", "fidelity gate caps a strong deck to playable")
    check(verdict_for(48.0, "high") == "weak", "mid field_wr -> weak")
    check(verdict_for(30.0, "high") == "ass", "low field_wr -> ass")

    # --- evaluate end-to-end with injected sim + apl ---------------------
    fast = DeckCandidate(name="Fast Combo", mainboard={"A": 60}, packages=["combo_core"],
                         metadata={"fidelity": "high"})
    rep = evaluate(
        fast,
        sim_runner=lambda c, n, fmt, pk, apl: FakeRes({3: 90.0, 4: 10.0}, win_rate=0.7),
        apl_provider=lambda c: (object(), {"source": "generated", "fidelity": "high"}),
    )
    check(rep.verdict == "strong", f"fast high-fidelity deck judged strong (got {rep.verdict})")
    check(rep.field_wr > 58.0, f"fast deck has high field_wr ({rep.field_wr})")
    check(rep.goldfish["win_rate"] == 70.0, "goldfish win rate threaded through")

    rep_low = evaluate(
        fast,
        sim_runner=lambda c, n, fmt, pk, apl: FakeRes({3: 90.0, 4: 10.0}, win_rate=0.7),
        apl_provider=lambda c: (object(), {"source": "fallback", "fidelity": "low"}),
    )
    check(rep_low.verdict == "playable", "same deck capped to playable when fidelity low")

    rep_bad = evaluate(
        DeckCandidate(name="Slow", mainboard={"A": 60}, packages=["x"], metadata={"fidelity": "high"}),
        sim_runner=lambda c, n, fmt, pk, apl: FakeRes({12: 90.0, 13: 10.0}, win_rate=0.2),
        apl_provider=lambda c: (object(), {"source": "generated", "fidelity": "high"}),
    )
    check(rep_bad.verdict in ("ass", "weak"), f"slow weak deck judged poorly ({rep_bad.verdict})")

    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s)")
        sys.exit(1)
    print("All fitness + apl-cache checks passed.")


if __name__ == "__main__":
    main()
