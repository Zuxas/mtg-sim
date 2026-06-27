"""R5 no-regression match-path check (runnable in BOTH trees).

Exercises engine.match_runner.run_match_set / _resolve_combat directly so the
gate-OFF combat edit is actually covered (goldfish never calls _resolve_combat).
Prints a_wins/b_wins/avg_turns as a stable fingerprint to diff across trees.

  NR-3a: Tron vs Boros, Tron's WANTS_PW_LOYALTY FORCED OFF -> must match clean tree.
  NR-2 : a non-PW match (borosenergy vs murktide) -> gate off naturally.

Usage: PYTHONIOENCODING=utf-8 python scripts/r5_nr_match_check.py <a_key> <b_key> [n] [force_off]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_matchup_data import load_deck_and_apl
from apl import get_match_apl
from engine.match_runner import run_match_set

FMT = "modern"


def _load_main(key):
    main, _side, _gold = load_deck_and_apl(key, FMT)
    return main


def main():
    a_key = sys.argv[1]
    b_key = sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    force_off = len(sys.argv) > 4 and sys.argv[4] == "force_off"

    a_main = _load_main(a_key)
    b_main = _load_main(b_key)
    a_apl = get_match_apl(a_key) or load_deck_and_apl(a_key, FMT)[2]
    b_apl = get_match_apl(b_key) or load_deck_and_apl(b_key, FMT)[2]

    if force_off:
        # Force the R5 gate OFF on whichever side carries it (no-op in clean tree).
        for apl in (a_apl, b_apl):
            if hasattr(apl, "WANTS_PW_LOYALTY"):
                apl.WANTS_PW_LOYALTY = False
                type(apl).WANTS_PW_LOYALTY = False

    res = run_match_set(a_apl, a_main, b_apl, b_main,
                        n=n, seed=42, mix_play_draw=True, n_workers=1)
    print("FINGERPRINT a_wins=%d b_wins=%d avg_turns=%.6f n=%d" % (
        res.a_wins, res.b_wins, res.avg_turns, n))


if __name__ == "__main__":
    main()
