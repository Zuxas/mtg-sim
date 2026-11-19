"""match_engine: mana must not pile up from turn to turn (CR 500.4).

The pool was never emptied, so unspent mana was banked forever: a player with
six lands and nothing to cast had 21 mana on turn 6.

Run: python tests/test_mana_does_not_accumulate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from apl.match_apl import GenericMatchAPL
from engine import match_engine, match_runner


def _lands(n=60):
    out = []
    for _ in range(n):
        c = Card(name="Mountain", mana_cost="", cmc=0.0, type_line="Basic Land - Mountain")
        c.tags = {Tag.LAND}
        out.append(c)
    return out


def _pools(engine):
    seen = []

    class Watcher(GenericMatchAPL):
        def keep(self, *a, **k):
            return True

        def main_phase_match(self, gs, opponent):
            out = super().main_phase_match(gs, opponent)
            lands = sum(1 for c in gs.zones.battlefield if c.is_land())
            seen.append((lands, gs.mana_pool.total()))
            return out

    engine.run_match(Watcher(), _lands(), GenericMatchAPL(), _lands(),
                     on_play=True, seed=1, max_turns=6)
    return seen


def test_match_engine_pool_never_exceeds_lands():
    seen = _pools(match_engine)
    assert len(seen) == 6
    for lands, mana in seen:
        assert mana <= lands, f"{mana} mana from {lands} lands: {seen}"


def test_match_runner_agrees():
    for lands, mana in _pools(match_runner):
        assert mana <= lands


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_mana_does_not_accumulate: OK")
