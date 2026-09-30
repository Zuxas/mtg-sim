"""Combo routing uses our deck: real match record (shrunk toward 50%) first, else engine games.
Spec harness/specs/2026-09-30-combo-routing-fix.md."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run_matchup as rm
from calibration import real_results as rr

NM = {
    "Ours":  {"deck_file": "x", "apl": "Ours", "labels": ["Ours", "Ours Alias"]},
    "Combo": {"deck_file": "y", "apl": "combostd", "labels": ["Combo"]},
}


def _db(n_wins, n_losses, draws=1):
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE matches (player1_arch TEXT, player2_arch TEXT, result TEXT,
                   format TEXT, event_date TEXT, source TEXT)""")
    rows = []
    for i in range(n_wins):   # alternate seats, our deck wins
        rows.append(("Ours", "Combo", "player1", "modern", "2026-06-01", "mtgmelee") if i % 2 else
                    ("Combo", "Ours Alias", "player2", "modern", "01/07/2026", "mtgmelee"))
    for _ in range(n_losses):
        rows.append(("Ours", "Combo", "player2", "modern", "2026-06-02", "mtgmelee"))
    for _ in range(draws):
        rows.append(("Ours", "Combo", "draw", "modern", "2026-06-03", "mtgmelee"))
    rows.append(("Ours", "Combo", "player1", "modern", "2026-05-01", "mtgmelee"))        # before window
    rows.append(("Ours", "Combo", "player1", "modern", "2026-06-04", "bracket_finals"))  # inferred row
    rows.append(("Ours", "Combo", "player1", "standard", "2026-09-01", "mtgmelee"))      # other format
    con.executemany("INSERT INTO matches VALUES (?,?,?,?,?,?)", rows)
    return con


def test_real_match_wr_counts_and_shrinks():
    rec = rr.real_match_wr(_db(30, 10), "Ours", "Combo", "modern", NM)
    assert (rec["wins"], rec["losses"], rec["draws"], rec["decisive"]) == (30, 10, 1, 40)
    assert rec["raw"] == 0.75
    assert abs(rec["shrunk"] - (30 + 25) / (40 + 50)) < 1e-12


def test_real_match_wr_opponent_view_and_apl_key():
    rec = rr.real_match_wr(_db(30, 10), "combostd", "Ours", "modern", NM)   # resolves via the apl key
    assert (rec["wins"], rec["losses"]) == (10, 30)


def test_real_match_wr_needs_20_decisive_and_a_window():
    assert rr.real_match_wr(_db(10, 9), "Ours", "Combo", "modern", NM) is None
    assert rr.real_match_wr(_db(30, 10), "Ours", "Combo", "pioneer", NM) is None
    assert rr.real_match_wr(_db(30, 10), "Ours", "Nobody", "modern", NM) is None


def test_combo_uses_real_record_when_present(monkeypatch=None):
    orig = rm._real_match
    called = {}
    try:
        def fake_fair(*a, **k):
            called["fair"] = True
        rm._run_fair_orig, rm._run_fair = rm._run_fair, fake_fair
        import calibration.real_results as R
        o_conn, o_wr = R.connect_ro, R.real_match_wr
        R.connect_ro = lambda: None
        R.real_match_wr = lambda con, a, b, f: {"wins": 30, "losses": 10, "draws": 0, "decisive": 40,
                                               "raw": 0.75, "shrunk": 55 / 90}
        res = {"our_deck": "Ours"}
        rm._run_combo(res, "Combo", "modern", 100, 42)
        assert "fair" not in called
        assert res["g1_source"] == "real" and res["match"] == round(100 * 55 / 90, 1)
        p = res["g1"] / 100
        assert abs(p * p * (3 - 2 * p) - 55 / 90) < 0.002
    finally:
        rm._run_fair = rm._run_fair_orig
        R.connect_ro, R.real_match_wr = o_conn, o_wr
        rm._real_match = orig


def test_combo_without_real_record_plays_engine_games():
    called = {}
    o_real, o_fair = rm._real_match, rm._run_fair
    try:
        rm._real_match = lambda *a: False
        rm._run_fair = lambda result, our, opp, fmt, n, seed, iw: called.update(args=(our, opp, fmt, n, seed, iw))
        res = {"our_deck": "Boros Energy"}
        rm._run_combo(res, "Goryo's Vengeance", "modern", 1000, 3042, 1)
        assert called["args"] == ("Boros Energy", "Goryo's Vengeance", "modern", 1000, 3042, 1)
        assert res["combo_route"] == "engine"
    finally:
        rm._real_match, rm._run_fair = o_real, o_fair


def test_run_matchup_no_longer_calls_the_humans_combo_model():
    src = open(rm.__file__, encoding="utf-8").read()
    assert "run_combo_matchup(" not in src
    assert "get_real_matchup(" not in src


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"[ok] {name}")
    print("ALL COMBO ROUTING TESTS PASS")
