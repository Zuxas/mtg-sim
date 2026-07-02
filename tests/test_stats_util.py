"""test_stats_util.py -- engine/stats_util.py Wilson band regression test.

Spec: harness/knowledge/tech/ext-eval-ml-calibration-2026-06-26.md section 1C
("FWR confidence bands"). Reporting-layer only; known values checked against
the mtg-meta-analyzer/analysis/wilson.py reference implementation.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.stats_util import wilson_bounds, wilson_bounds_pct, fmt_pct_band


def test_zero_n_does_not_crash_and_is_uninformative():
    assert wilson_bounds(0, 0) == (0.0, 1.0)
    assert wilson_bounds_pct(0.0, 0) == (0.0, 100.0)
    assert fmt_pct_band(0.0, 0) == "0.0% [0.0–100.0]"


def test_known_value_54_of_100():
    lo, hi = wilson_bounds(54, 100)
    assert abs(lo - 0.443) < 0.005, lo
    assert abs(hi - 0.634) < 0.005, hi


def test_pct_variant_matches_count_variant():
    lo, hi = wilson_bounds_pct(54.0, 100)
    assert abs(lo - 44.3) < 0.5 and abs(hi - 63.4) < 0.5


def test_band_narrows_with_n():
    lo_s, hi_s = wilson_bounds(54, 100)
    lo_l, hi_l = wilson_bounds(5400, 10000)
    assert (hi_l - lo_l) < (hi_s - lo_s)
    # both contain the point estimate
    assert lo_l < 0.54 < hi_l


def test_extremes_stay_in_bounds():
    lo, hi = wilson_bounds(0, 50)
    assert lo < 1e-12 and 0.0 < hi < 0.15
    lo, hi = wilson_bounds(50, 50)
    assert 0.85 < lo < 1.0 and hi > 1.0 - 1e-12


def test_bo3_set_results_band():
    """Bo3SetResults.match_wr_band_a threads the helper (a_wins/n)."""
    from engine.bo3_match import Bo3SetResults
    r = Bo3SetResults(n_matches=100, a_wins=54, b_wins=46)
    lo, hi = r.match_wr_band_a()
    assert abs(lo - 44.3) < 0.5 and abs(hi - 63.4) < 0.5
    # n=0 edge: must not crash, must be uninformative
    empty = Bo3SetResults()
    assert empty.match_wr_band_a() == (0.0, 100.0)
