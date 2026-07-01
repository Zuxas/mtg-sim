"""Mulligan keep-routing baseline/validation capture (boros+amulet lanes).

Spec: harness/specs/2026-06-30-match-mulligan-keep-routing.md (Step 0 / Step 1 / Gate 0 / Gate 1)

Captures per-cell a_wins/b_wins/avg_turns for the SCOPED boros+amulet lanes via
the PRIMARY driver (engine.match_runner.run_match_set, single-hero: seat A = our
deck, seat B = opponent). Deterministic under a seeded gs.rng; PYTHONHASHSEED
must be pinned OUTSIDE this process (Gate 0 = two separate launches, byte-identical).

Usage:
    PYTHONHASHSEED=0 python scripts/mull_routing_capture.py [n]

Env passthrough (read inside match_runner._mull_mode):
    MULL_MODE=crude          -> force crude both seats (Gate 1 faithful-refactor)
    MULL_MODE_A / MULL_MODE_B -> per-seat override (Step 5 five-mode matrix)
    (unset)                  -> production default (keep on boros+amulet seats)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generate_matchup_data import load_deck_and_apl
from apl import get_match_apl
from engine.match_runner import run_match_set

FMT = "modern"
SEED = 42
N_WORKERS = 1

# (cell_label, hero_key, opp_key). Hero is seat A. Opponents chosen to route
# through run_match (NOT the combo-sampler KILL_DISTS set), so the mulligan
# path is actually exercised.
BOROS = "borosenergylowcurve"
AMULET = "amulettitan"
CELLS = [
    ("boros_vs_eldrazi_tron",   BOROS,  "eldrazitron"),
    ("boros_vs_uw_control",     BOROS,  "uwcontrol"),
    ("boros_vs_dimir_murktide", BOROS,  "dimirmurktide"),
    ("boros_vs_humans",         BOROS,  "humans"),
    ("boros_vs_sultai_midrange",BOROS,  "sultaimidrange"),
    ("boros_vs_izzet_prowess",  BOROS,  "izzetprowess"),
    ("boros_vs_amulet_titan",   BOROS,  AMULET),
    ("boros_vs_grixis_reanim",  BOROS,  "grixisreanimator"),
    ("amulet_vs_eldrazi_tron",  AMULET, "eldrazitron"),
    ("amulet_vs_uw_control",    AMULET, "uwcontrol"),
    ("amulet_vs_humans",        AMULET, "humans"),
    ("amulet_vs_izzet_prowess", AMULET, "izzetprowess"),
    ("amulet_vs_boros",         AMULET, BOROS),
]


def _load_main(key):
    main, _side, _gold = load_deck_and_apl(key, FMT)
    return main


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    mode_env = os.environ.get("MULL_MODE") or (
        "A=%s,B=%s" % (os.environ.get("MULL_MODE_A", "-"),
                       os.environ.get("MULL_MODE_B", "-")))
    print("# mull-routing capture  n=%d seed=%d n_workers=%d  PYTHONHASHSEED=%s  MULL_MODE=%s"
          % (n, SEED, N_WORKERS, os.environ.get("PYTHONHASHSEED", "UNSET"), mode_env))
    print("# %-26s %8s %6s %6s %8s  %-24s %-24s" %
          ("cell", "a_wins", "b_wins", "avgT", "n", "hero_cls", "opp_cls"))
    for label, a_key, b_key in CELLS:
        a_main = _load_main(a_key)
        b_main = _load_main(b_key)
        a_apl = get_match_apl(a_key) or load_deck_and_apl(a_key, FMT)[2]
        b_apl = get_match_apl(b_key) or load_deck_and_apl(b_key, FMT)[2]
        res = run_match_set(a_apl, a_main, b_apl, b_main,
                            n=n, seed=SEED, mix_play_draw=True, n_workers=N_WORKERS)
        print("%-28s %8d %6d %6.4f %8d  %-24s %-24s" % (
            label, res.a_wins, res.b_wins, res.avg_turns, n,
            type(a_apl).__name__, type(b_apl).__name__))


if __name__ == "__main__":
    main()
