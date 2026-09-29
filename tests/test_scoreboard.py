"""
tests/test_scoreboard.py -- spec harness/specs/2026-09-30-sim-real-scoreboard.md

Run: python tests/test_scoreboard.py   (or via pytest)

S1 metric math against hand-computed values; S2 real-result rules on an
in-memory DB (mirror, draw, dd/mm/yy date, unmapped label, bracket row).
"""
import math
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from calibration import real_results as rr
from calibration.scoreboard import (bo3, cell_stats, correlation_and_spread, headline,
                                   list_check, trust_band)

MAP = {"Alpha": {"deck_file": "x", "apl": "Alpha", "labels": ["Alpha", "Alpha Old"]},
       "Beta": {"deck_file": "y", "apl": "Beta", "labels": ["Beta"]}}


def test_s1_bo3_conversion():
    assert bo3(0.5) == 0.5
    assert math.isclose(bo3(0.6), 0.36 * 1.8)            # 0.648
    assert math.isclose(bo3(0.4), 1 - bo3(0.6))          # symmetric
    print("[ok] S1 Bo3 conversion p^2(3-2p)")


def test_s1_cell_and_headline():
    # sim 240/400 G1 = 0.60 -> match 0.648; real 300-200 (+10 draws) = 0.60
    c = cell_stats(240, 400, {"wins": 300, "losses": 200, "draws": 10, "n": 510})
    assert c["sim_g1"] == 0.6 and c["sim_match"] == 0.648
    assert c["real_wr"] == 0.6 and c["real_decisive"] == 500 and c["real_draws"] == 10
    assert math.isclose(c["delta"], 0.048, abs_tol=1e-4)
    assert c["trust"] == "trusted" and c["real_clear"] and c["same_side"]
    # Wilson 95% for 300/500: centre ~0.5996, half ~0.0428 -> 0.557..0.642; 0.648 is outside
    assert 0.55 < c["real_lo"] < 0.56 and 0.64 < c["real_hi"] < 0.645 and c["miss"]
    d = cell_stats(160, 400, {"wins": 55, "losses": 45, "draws": 0, "n": 100})   # sim favours B, real ~even
    h = headline([c, d])
    # weighted MAE = (500*0.048 + 100*|0.352-0.55|) / 600
    assert math.isclose(h["weighted_mae_pp"], round(100 * (500 * 0.048 + 100 * 0.198) / 600, 2))
    assert h["direction_cells"] == 1 and h["direction_agree"] == 1.0   # d's real CI straddles 50%
    assert trust_band(99) == "noise" and trust_band(100) == "directional"
    print("[ok] S1 cell stats + weighted headline")


def test_s1_list_check():
    prof = {"A": 1.0, "B": 0.8, "C": 0.05}
    lc = list_check({"A", "C", "Z"}, prof)
    assert lc["missing_staples"] == ["B"]
    assert lc["rare_in_real"] == ["C", "Z"]
    assert math.isclose(lc["cosine"], round(1.05 / (math.sqrt(3) * math.sqrt(1 + 0.64 + 0.0025)), 3))
    print("[ok] S1 list check")


def test_s1_correlation_and_spread():
    xs, ys = [0.9, 0.1, 0.7], [0.6, 0.4, 0.55]      # sim far more one-sided than real
    m = correlation_and_spread(xs, ys)
    assert m["spread_sim_pp"] == round(100 * (0.4 + 0.4 + 0.2) / 3, 2)
    assert m["spread_real_pp"] == round(100 * (0.1 + 0.1 + 0.05) / 3, 2)
    assert m["spread_ratio"] == 4.0
    assert m["pearson_r"] > 0.99 and 0.2 < m["slope_real_on_sim"] < 0.3
    print("[ok] S1 correlation + spread (overconfidence ratio)")


def _db():
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE matches (player1_arch TEXT, player2_arch TEXT, result TEXT,
                   format TEXT, event_date TEXT, source TEXT)""")
    rows = [
        ("Alpha", "Beta", "player1", "modern", "2026-06-01", "mtgmelee"),     # Alpha win
        ("Beta", "Alpha Old", "player1", "modern", "02/06/26", "mtgmelee"),   # Beta win, dd/mm/yy, alias label
        ("Alpha", "Beta", "draw", "modern", "2026-06-03", "mtgmelee"),        # draw
        ("Alpha", "Alpha", "player1", "modern", "2026-06-04", "mtgmelee"),    # mirror -> excluded
        ("Alpha", "Gamma", "player1", "modern", "2026-06-05", "mtgmelee"),    # unmapped -> excluded
        ("Alpha", "Beta", "player1", "modern", "2026-06-06", "bracket_sf"),   # inferred -> excluded
        ("Alpha", "Beta", "player1", "modern", "2026-04-01", "mtgmelee"),     # before since
        ("Alpha", "Beta", "player1", "standard", "2026-06-01", "mtgmelee"),   # other format
        ("Beta", "Alpha", "player2", "modern", "15/07/26", "mtgmelee"),       # Alpha win, flipped seats
    ]
    con.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?)", rows)
    return con


def test_s2_real_matchups_rules():
    r = rr.real_matchups(_db(), "modern", "2026-05-15", MAP)
    cov = r.pop("_coverage")
    assert list(r) == [("Alpha", "Beta")]
    assert r[("Alpha", "Beta")] == {"wins": 2, "losses": 1, "draws": 1, "n": 4}
    assert cov["rows"] == 6 and cov["mapped_rows"] == 5 and cov["unmapped_labels"] == {"Gamma": 1}
    print("[ok] S2 mirror / draw / dd-mm-yy / alias / unmapped / bracket / window / seat flip")


def test_s2_field_shares():
    s = rr.real_field_shares(_db(), "modern", "2026-05-15", MAP)
    assert math.isclose(s["Alpha"], 7 / 12) and math.isclose(s["Beta"], 4 / 12)
    assert math.isclose(s["_unmapped"], 1 / 12)
    print("[ok] S2 field shares")


def main() -> int:
    test_s1_bo3_conversion()
    test_s1_cell_and_headline()
    test_s1_list_check()
    test_s1_correlation_and_spread()
    test_s2_real_matchups_rules()
    test_s2_field_shares()
    print("ALL SCOREBOARD UNIT GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
