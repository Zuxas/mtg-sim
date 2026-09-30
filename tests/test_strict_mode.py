"""Strict simulation mode (spec harness/specs/2026-09-30-strict-mode.md).
Every guarded site is silent by default and raises StrictModeError under MTG_SIM_STRICT=1."""
import contextlib
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.strict import StrictModeError, is_strict


@contextlib.contextmanager
def strict(on: bool):
    old = os.environ.get("MTG_SIM_STRICT")
    if on:
        os.environ["MTG_SIM_STRICT"] = "1"
    else:
        os.environ.pop("MTG_SIM_STRICT", None)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("MTG_SIM_STRICT", None)
        else:
            os.environ["MTG_SIM_STRICT"] = old


def _raises(fn) -> bool:
    try:
        fn()
    except StrictModeError:
        return True
    return False


class _GS:
    def __init__(self):
        self.logged = []

    def _log(self, m):
        self.logged.append(m)


def _card(name="Strict Probe Card"):
    return Card(name=name, mana_cost="{1}", cmc=1, type_line="Instant", oracle_text="")


def test_flag():
    with strict(False):
        assert not is_strict()
    with strict(True):
        assert is_strict()


def test_card_handler_errors():
    from engine import card_effects as ce

    def boom(gs, card):
        raise ValueError("handler bug")
    ce.ETB_EFFECTS["Strict Probe Card"] = boom
    ce.SPELL_EFFECTS["Strict Probe Card"] = boom
    try:
        with strict(False):
            g = _GS()
            ce.on_etb(g, _card())
            ce.on_spell_resolve(g, _card())
            assert len(g.logged) == 2
        with strict(True):
            assert _raises(lambda: ce.on_etb(_GS(), _card()))
            assert _raises(lambda: ce.on_spell_resolve(_GS(), _card()))
    finally:
        del ce.ETB_EFFECTS["Strict Probe Card"], ce.SPELL_EFFECTS["Strict Probe Card"]


def test_effect_primitives():
    from engine.effect_primitives import run_effects, PRIMITIVES

    def boom(gs, ctx, **k):
        raise ValueError("primitive bug")
    PRIMITIVES["_strict_probe"] = boom
    try:
        with strict(False):
            run_effects(_GS(), {}, [("no_such_primitive", {}), ("_strict_probe", {})])
        with strict(True):
            assert _raises(lambda: run_effects(_GS(), {}, [("no_such_primitive", {})]))
            assert _raises(lambda: run_effects(_GS(), {}, [("_strict_probe", {})]))
    finally:
        del PRIMITIVES["_strict_probe"]


def test_sideboard_application():
    import engine.bo3_match as bm
    orig = bm.apply_sideboard_plan
    bm.apply_sideboard_plan = lambda *a: (_ for _ in ()).throw(ValueError("sb bug"))
    try:
        main = [_card("A")]
        with strict(False):
            assert bm._apply_sb(main, [], ["1 B"], ["1 A"]) is main
        with strict(True):
            assert _raises(lambda: bm._apply_sb(main, [], ["1 B"], ["1 A"]))
    finally:
        bm.apply_sideboard_plan = orig


def test_match_runner_apl_exception():
    from engine import match_runner as mr
    from apl import get_match_apl
    from generate_matchup_data import load_deck_and_apl
    with contextlib.redirect_stdout(io.StringIO()):
        deck = load_deck_and_apl("Izzet Prowess", "modern")[0]
    bad = get_match_apl("Izzet Prowess", "modern")

    def boom(*a, **k):
        raise ValueError("apl bug")
    bad.main_phase_match = boom
    # Other test modules set SIM_DEBUG=1 at import (it also re-raises); isolate from it.
    saved_debug = os.environ.pop("SIM_DEBUG", None)
    try:
        _match_runner_case(mr, bad, deck, get_match_apl)
    finally:
        if saved_debug is not None:
            os.environ["SIM_DEBUG"] = saved_debug


def _match_runner_case(mr, bad, deck, get_match_apl):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        with strict(False):
            mr.run_match(bad, deck, get_match_apl("Izzet Prowess", "modern"), deck, on_play=True, seed=1)
        with strict(True):
            try:
                mr.run_match(bad, deck, get_match_apl("Izzet Prowess", "modern"), deck, on_play=True, seed=1)
                raised = False
            except (StrictModeError, ValueError):
                raised = True
    assert raised


def test_run_matchup_strict_branches():
    import run_matchup as rm
    with strict(True):
        r = {"match": 10.0}
        rm._apply_caps(r, "Mono Red Aggro", "Dimir Midrange")
        assert r["match"] == 10.0 and "match_floored" not in r
        assert rm._real_match({}, "Boros Energy", "Goryo's Vengeance", "modern") is False
    with strict(False):
        r = {"match": 10.0}
        rm._apply_caps(r, "Mono Red Aggro", "Dimir Midrange")
        assert r["match"] == 25.0


def test_run_matchup_no_bo3_fallback():
    import run_matchup as rm
    import engine.bo3_match as bm
    orig = bm.run_bo3_set

    def boom(*a, **k):
        raise ValueError("bo3 crash")
    bm.run_bo3_set = boom
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with strict(True):
                assert _raises(lambda: rm._run_fair({"our_deck": "Four-Color Control"}, "Four-Color Control",
                                                    "Izzet Spellementals", "standard", 4, 42, 1))
    finally:
        bm.run_bo3_set = orig


def test_fidelity_blocks():
    from fidelity import deck_fidelity, preflight
    assert deck_fidelity("Izzet Prowess", "modern")["ok"]
    assert any("61" in b for b in deck_fidelity("Amulet Titan", "modern")["blocks"])
    assert any("Umezawa's Jitte" in b for b in deck_fidelity("Boros Energy", "modern")["blocks"])
    assert any("54" in b for b in deck_fidelity("Dimir Tempo", "legacy")["blocks"])
    assert _raises(lambda: preflight("Amulet Titan", "modern"))

    import generate_matchup_data as gmd
    orig = gmd.load_deck_and_apl
    gmd.load_deck_and_apl = lambda k, f: ([_card("Island")] * 59 + [_card("Totally Unknown Card Zzq")], [], None)
    try:
        assert any("unresolved" in b for b in deck_fidelity("Izzet Prowess", "modern")["blocks"])
    finally:
        gmd.load_deck_and_apl = orig


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL STRICT MODE TESTS PASS")
