"""test_combo_model_format.py -- issue #25.

run_combo_matchup was always called without a format, so every Modern combo
deck got the generic Legacy fallback kill distribution, and it wrote the
distribution it looked up into the class-level ComboKillSampler.KILL_DISTS.
"""
import sys, os, io, copy, random, contextlib, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import combo_model
from engine.combo_model import run_combo_matchup
from engine.match_runner import ComboKillSampler
from format_config import get_format
import run_matchup, parallel_sim


def _quiet(fn):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        return fn(), out.getvalue()


def test_format_changes_the_result():
    assert "neobrand" in get_format("modern")["combo_kill_dists"]
    legacy, _ = _quiet(lambda: run_combo_matchup("Neobrand", n=2000, game=1, seed=1))
    modern, _ = _quiet(lambda: run_combo_matchup("Neobrand", n=2000, game=1, seed=1,
                                                 format_name="modern"))
    assert legacy["win_pct"] - modern["win_pct"] > 30, (legacy["win_pct"], modern["win_pct"])
    assert modern["format"] == "modern"


def test_class_table_is_not_mutated():
    before = copy.deepcopy(ComboKillSampler.KILL_DISTS)
    _quiet(lambda: run_combo_matchup("Neobrand", n=200, game=1, seed=1, format_name="modern"))
    _quiet(lambda: run_combo_matchup("Belcher", n=200, game=2, seed=1, format_name="modern"))
    assert ComboKillSampler.KILL_DISTS == before


def test_sampler_takes_a_distribution_for_one_instance():
    rng = random.Random(1)
    assert ComboKillSampler("Anything", rng, dist={2: 100})._kill_t == 2
    assert ComboKillSampler("Anything", rng).dist == {4: 50, 5: 30, 6: 20}


def test_other_deck_is_flagged_and_warned_once():
    combo_model._WARNED_DECKS.clear()
    r1, out1 = _quiet(lambda: run_combo_matchup("Neobrand", n=100, seed=1,
                                                format_name="modern", our_deck="Boros Energy"))
    r2, out2 = _quiet(lambda: run_combo_matchup("Belcher", n=100, seed=1,
                                                format_name="modern", our_deck="Boros Energy"))
    assert r1["our_side_modeled"] is False and "[!COMBO MODEL]" in out1 and out1.isascii()
    assert out2 == "", "warn once per deck"
    r3, out3 = _quiet(lambda: run_combo_matchup("Neobrand", n=100, seed=1, our_deck="Legacy Humans"))
    assert r3["our_side_modeled"] is True and out3 == ""


def test_both_callers_pass_the_format():
    for mod in (run_matchup, parallel_sim):
        src = inspect.getsource(mod)
        calls = src.count("run_combo_matchup(opp_name")
        assert calls and src.count("format_name=format_name, our_deck=our_deck") == calls, mod.__name__


if __name__ == "__main__":
    test_format_changes_the_result()
    test_class_table_is_not_mutated()
    test_sampler_takes_a_distribution_for_one_instance()
    test_other_deck_is_flagged_and_warned_once()
    test_both_callers_pass_the_format()
    print("test_combo_model_format: OK")
