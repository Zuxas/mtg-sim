"""The opponent-name credibility cap is gone; the aggro floor stays.
Spec harness/specs/2026-09-30-remove-credibility-cap.md."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run_matchup as rm


def test_bo3_match_not_capped_vs_interactive_name():
    r = {"match": 84.3}
    rm._apply_caps(r, "Selesnya Landfall", "Four-Color Control")
    assert r["match"] == 84.3
    assert "match_capped" not in r


def test_g1_not_capped_vs_interactive_name():
    r = {}
    rm._apply_caps_g1(r, 90.0, "Selesnya Landfall", "Azorius Control")
    assert r["g1"] == 90.0
    assert "g1_capped" not in r


def test_aggro_floor_kept():
    r = {"match": 10.0}
    rm._apply_caps(r, "Mono Red Aggro", "Dimir Midrange")
    assert r["match"] == 25.0 and r["match_floored"]
    r = {}
    rm._apply_caps_g1(r, 10.0, "Mono Red Aggro", "Dimir Midrange")
    assert r["g1"] == 25.0 and r["g1_floored"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL NO-CAP TESTS PASS")
