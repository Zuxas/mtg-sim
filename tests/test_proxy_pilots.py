"""Own match pilots replace the proxy pilots (spec harness/specs/2026-09-30-proxy-pilots.md)."""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import apl
from apl.aware_match_apl import AwareMatchAPL
from apl.deck_pilot import DeckPilotMixin
from data.card import Card
from generate_matchup_data import load_deck_and_apl

PILOTS = {("Four-Color Control", "standard"): "FourColorControlStandardMatchAPL",
          ("Dimir Midrange", "modern"): "DimirMidrangeModernMatchAPL",
          ("Boros Dragons", "standard"): "BorosDragonsStandardMatchAPL"}


def test_registry_points_at_own_pilots():
    for (key, fmt), cls in PILOTS.items():
        assert type(apl.get_match_apl(key, fmt)).__name__ == cls


def test_extra_counter_validity_is_opt_in():
    assert AwareMatchAPL.EXTRA_COUNTER_VALIDITY == {}
    fcc = apl.get_match_apl("Four-Color Control", "standard")
    spell = Card(name="Some Creature", mana_cost="{3}", cmc=3, type_line="Creature", oracle_text="")

    class _Pool:
        def can_cast(self, *a): return True
        def total(self): return 5

    class _GS:
        pass
    gs = _GS()
    gs.mana_pool = _Pool()
    nml = Card(name="No More Lies", mana_cost="{W}{U}", cmc=2, type_line="Instant", oracle_text="")
    gs.zones = type("Z", (), {"hand": [nml], "lands_on_battlefield": lambda self: []})()
    assert fcc._r1_choose_counter(gs, spell) is nml          # via EXTRA_COUNTER_VALIDITY
    class _Plain(AwareMatchAPL):
        def keep(self, hand, mulligans, on_play): return True
        def bottom(self, hand, n): return hand[:n]
        def main_phase(self, gs): return None
    plain = _Plain()
    assert plain._r1_choose_counter(gs, spell) is None       # not in the engine table


def test_pilots_never_cast_counters_proactively():
    class _P(DeckPilotMixin):
        COUNTER_CARDS = {"Counterspell"}
    cs = Card(name="Counterspell", mana_cost="{U}{U}", cmc=2, type_line="Instant", oracle_text="")
    cast = []

    class _Pool:
        def can_cast(self, *a): return True

    class _GS:
        mana_pool = _Pool()
        zones = type("Z", (), {"hand": [cs]})()
        def cast_spell(self, c):
            cast.append(c.name)
            return True
    p = _P()
    p._cast_in_order(_GS(), ["Counterspell"])
    p._cast_rest_noncounter(_GS())
    assert cast == []


def test_pilots_run_on_the_launcher_engine():
    from engine.match_engine import run_match
    for (key, fmt), _cls in PILOTS.items():
        opp = "Izzet Spellementals" if fmt == "standard" else "Eldrazi Tron"
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            ours, theirs = load_deck_and_apl(key, fmt)[0], load_deck_and_apl(opp, fmt)[0]
            for i in range(10):
                run_match(apl.get_match_apl(key, fmt), ours, apl.get_match_apl(opp, fmt), theirs,
                          on_play=(i % 2 == 0), seed=42 + i)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL PROXY PILOT TESTS PASS")
