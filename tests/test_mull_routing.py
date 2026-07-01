"""test_mull_routing.py -- match mulligan keep-routing (spec 2026-06-30).

Unit-level coverage for engine.match_runner._do_mulligan_runner and the mode
selector _mull_mode:
  - crude mode is byte-faithful to the old inline block (concat order + cap 3)
  - keep mode routes through apl.keep()/apl.bottom()
  - london_crude mode uses the crude predicate + generic_bottom
  - the mode selector gates keep to boros+amulet, honoring env overrides
  - a RAISING keep()/bottom() degrades to crude / generic_bottom (never crashes)

Run: python tests/test_mull_routing.py   (or via pytest)
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.match_runner import (
    _do_mulligan_runner, _mull_mode, _crude_keep, _KEEP_ROUTED_APLS,
)


# --- lightweight fixtures -------------------------------------------------

def land(name="Plains"):
    return Card(name=name, mana_cost="", cmc=0, type_line="Basic Land - Plains")


def spell(name="Bolt"):
    return Card(name=name, mana_cost="{1}", cmc=1, type_line="Sorcery")


class FakeResult:
    def __init__(self):
        self.mulligans_a = 0
        self.mulligans_b = 0


class FakeGS:
    """Mirrors the TwoPlayerGameState surface _do_mulligan_runner touches:
    rng, on_play, hand_a/b, lib_a/b, draw_a/b (rng-free pop from the front)."""
    def __init__(self, lib_a, lib_b, on_play=True, seed=0):
        self.rng = random.Random(seed)
        self.on_play = on_play
        self.hand_a, self.hand_b = [], []
        self.lib_a, self.lib_b = list(lib_a), list(lib_b)

    def _draw(self, side, n):
        lib = self.lib_a if side == "a" else self.lib_b
        hand = self.hand_a if side == "a" else self.hand_b
        drawn = []
        for _ in range(n):
            if lib:
                drawn.append(lib.pop(0))
        hand.extend(drawn)
        return drawn

    def draw_a(self, n=1):
        return self._draw("a", n)

    def draw_b(self, n=1):
        return self._draw("b", n)


def _mixed_lib(n_lands_top, total=60):
    """A library whose first 7 cards contain exactly n_lands_top lands, then
    the remainder is all lands (so a redraw after a mull tends to hit >= 2)."""
    top = [land(f"L{i}") for i in range(n_lands_top)] + \
          [spell(f"S{i}") for i in range(7 - n_lands_top)]
    rest = [land(f"R{i}") for i in range(total - 7)]
    return top + rest


# --- crude faithfulness ---------------------------------------------------

def _inline_reference(gs, side, result):
    """Verbatim replica of the OLD inline block for one seat (the Gate-1
    contract at unit granularity)."""
    lib_attr = "lib_a" if side == "a" else "lib_b"
    hand_attr = "hand_a" if side == "a" else "hand_b"
    mull_attr = "mulligans_a" if side == "a" else "mulligans_b"
    draw = gs.draw_a if side == "a" else gs.draw_b
    draw(7)
    for _ in range(3):
        lands = sum(1 for c in getattr(gs, hand_attr) if c.is_land())
        if lands < 2:
            setattr(gs, lib_attr, getattr(gs, hand_attr) + getattr(gs, lib_attr))
            setattr(gs, hand_attr, [])
            gs.rng.shuffle(getattr(gs, lib_attr))
            draw(max(4, 7 - getattr(result, mull_attr) - 1))
            setattr(result, mull_attr, getattr(result, mull_attr) + 1)
        else:
            break


def test_crude_byte_faithful_to_inline_reference():
    for n_lands_top in (0, 1, 2, 4):
        lib = _mixed_lib(n_lands_top)
        # reference
        g1, r1 = FakeGS(lib, lib, seed=123), FakeResult()
        _inline_reference(g1, "a", r1)
        # extracted crude mode, identical seed + lib
        g2, r2 = FakeGS(lib, lib, seed=123), FakeResult()
        _do_mulligan_runner(g2, "a", apl=None, result=r2, mode="crude")
        names1 = [c.name for c in g1.hand_a]
        names2 = [c.name for c in g2.hand_a]
        assert names1 == names2, f"crude hand diverged (top={n_lands_top}): {names1} vs {names2}"
        assert r1.mulligans_a == r2.mulligans_a, "crude mulligan count diverged"


def test_crude_no_mull_on_two_lands():
    lib = _mixed_lib(2)
    gs, res = FakeGS(lib, lib, seed=1), FakeResult()
    _do_mulligan_runner(gs, "a", apl=None, result=res, mode="crude")
    assert res.mulligans_a == 0
    assert len(gs.hand_a) == 7


# --- mode selector gating -------------------------------------------------

class BorosEnergyMatchAPL:      # name matches the production keep-routed set
    pass


class AmuletTitanMatchAPL:
    pass


class SomeFieldMatchAPL:        # any other deck -> crude
    pass


def test_mode_selector_production_default():
    for k in ("MULL_MODE", "MULL_MODE_A", "MULL_MODE_B"):
        os.environ.pop(k, None)
    assert "BorosEnergyMatchAPL" in _KEEP_ROUTED_APLS
    assert "AmuletTitanMatchAPL" in _KEEP_ROUTED_APLS
    assert _mull_mode("a", BorosEnergyMatchAPL()) == "keep"
    assert _mull_mode("b", AmuletTitanMatchAPL()) == "keep"
    assert _mull_mode("a", SomeFieldMatchAPL()) == "crude"


def test_mode_selector_env_overrides():
    try:
        os.environ["MULL_MODE"] = "crude"
        # global override forces crude even for boros
        assert _mull_mode("a", BorosEnergyMatchAPL()) == "crude"
        os.environ["MULL_MODE_A"] = "keep"   # per-seat wins over global
        assert _mull_mode("a", SomeFieldMatchAPL()) == "keep"
        assert _mull_mode("b", SomeFieldMatchAPL()) == "crude"
    finally:
        for k in ("MULL_MODE", "MULL_MODE_A", "MULL_MODE_B"):
            os.environ.pop(k, None)


# --- keep-mode routing ----------------------------------------------------

class RecordingAPL:
    """keep() keeps only on >= 3 lands; records that it was consulted."""
    def __init__(self):
        self.keep_calls = 0
        self.bottom_calls = 0

    def keep(self, hand, mulligans, on_play):
        self.keep_calls += 1
        return sum(1 for c in hand if c.is_land()) >= 3

    def bottom(self, hand, n):
        self.bottom_calls += 1
        # bottom the highest-index spells first (deterministic)
        spells = [c for c in hand if not c.is_land()]
        return spells[:n]


def test_keep_mode_consults_apl_keep():
    # first 7 has 2 lands (crude would KEEP) but RecordingAPL wants 3 -> it mulls.
    lib = _mixed_lib(2)
    apl = RecordingAPL()
    gs, res = FakeGS(lib, lib, seed=7), FakeResult()
    _do_mulligan_runner(gs, "a", apl=apl, result=res, mode="keep")
    assert apl.keep_calls >= 1, "apl.keep was never consulted in keep mode"
    # kept hand always has 7 cards on the table minus bottomed (mull>0 bottoms N)
    assert len(gs.hand_a) == 7 - res.mulligans_a
    if res.mulligans_a > 0:
        assert apl.bottom_calls >= 1, "apl.bottom not consulted after a mulligan"


def test_london_crude_uses_crude_predicate():
    # london_crude keeps on the crude lands>=2 predicate; first 7 has 2 lands.
    lib = _mixed_lib(2)
    gs, res = FakeGS(lib, lib, seed=3), FakeResult()
    _do_mulligan_runner(gs, "a", apl=None, result=res, mode="london_crude")
    assert res.mulligans_a == 0
    assert len(gs.hand_a) == 7


# --- fallback safety ------------------------------------------------------

class RaisingKeepAPL:
    def keep(self, hand, mulligans, on_play):
        raise RuntimeError("boom in keep")

    def bottom(self, hand, n):
        return []


class RaisingBottomAPL:
    def keep(self, hand, mulligans, on_play):
        # mull the first hand, keep the next -> deterministically forces a
        # bottom() call at mulligans >= 1 regardless of the London reshuffle.
        return mulligans >= 1

    def bottom(self, hand, n):
        raise RuntimeError("boom in bottom")


def test_fallback_raising_keep_degrades_to_crude():
    # first 7 has 2 lands -> crude predicate keeps; must NOT crash.
    lib = _mixed_lib(2)
    apl = RaisingKeepAPL()
    gs, res = FakeGS(lib, lib, seed=5), FakeResult()
    _do_mulligan_runner(gs, "a", apl=apl, result=res, mode="keep")
    assert res.mulligans_a == 0
    assert len(gs.hand_a) == 7
    assert _crude_keep(gs.hand_a) is True


def test_fallback_raising_keep_mulls_bad_hand():
    # all-spell library -> the crude fallback predicate (lands>=2) is never
    # satisfied, so a raising keep() mulls to the forced cap; still no crash.
    lib = [spell(f"S{i}") for i in range(60)]
    apl = RaisingKeepAPL()
    gs, res = FakeGS(lib, lib, seed=5), FakeResult()
    _do_mulligan_runner(gs, "a", apl=apl, result=res, mode="keep")
    assert res.mulligans_a >= 1


def test_fallback_raising_bottom_uses_generic_bottom():
    # keep true at mull>0 forces a bottom() call; raising bottom -> generic_bottom.
    lib = [land(f"L{i}") for i in range(60)]  # plenty of cards to redraw
    apl = RaisingBottomAPL()
    gs, res = FakeGS(lib, lib, seed=9), FakeResult()
    _do_mulligan_runner(gs, "a", apl=apl, result=res, mode="keep")
    # keeps at mulligans==1, London bottoms N -> hand is 7 - mulligans, no crash
    assert res.mulligans_a == 1
    assert len(gs.hand_a) == 7 - res.mulligans_a


def test_keep_mode_deterministic_same_seed():
    lib = _mixed_lib(1)
    apl = RecordingAPL()
    outs = []
    for _ in range(2):
        gs, res = FakeGS(lib, lib, seed=99), FakeResult()
        _do_mulligan_runner(gs, "a", apl=apl, result=res, mode="keep")
        outs.append(([c.name for c in gs.hand_a], res.mulligans_a))
    assert outs[0] == outs[1], "keep mode not deterministic under fixed seed"


ALL_TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failed = 0
    for t in ALL_TESTS:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(ALL_TESTS) - failed}/{len(ALL_TESTS)} passed")
    sys.exit(1 if failed else 0)
