"""test_meta_bridge_class.py -- meta_bridge.MetaBridge, the object interface
bo3_gauntlet / gauntlet_any_deck / event_simulator / generate_matchup_data /
sim_bridge import. It was missing (ImportError), so those drivers silently
fell back or stopped.

Run: python tests/test_meta_bridge_class.py
"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import meta_bridge  # noqa: E402
from meta_bridge import MetaBridge  # noqa: E402


def _db():
    path = os.path.join(tempfile.mkdtemp(), "mtg_meta.db")
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE matches (player1_arch TEXT, player2_arch TEXT, format TEXT)")
    c.executemany("INSERT INTO matches VALUES (?, ?, 'modern')",
                  [("Boros Energy", "Eldrazi Tron")] * 6 + [("Eldrazi Tron", "Boros Energy")] * 3
                  + [("Living End", "Boros Energy")] * 1)
    c.execute("CREATE TABLE matchup_matrix (format TEXT, archetype_a TEXT, archetype_b TEXT, "
              "winrate REAL, matches INTEGER, fetched_at TEXT)")
    c.executemany("INSERT INTO matchup_matrix VALUES ('modern', ?, ?, ?, ?, 'x')",
                  [("Eldrazi Tron", "Boros Energy", 0.45, 25),    # stored reverse row wins
                   ("Boros Energy", "Eldrazi Tron", 0.58, 40),
                   ("Boros Energy", "Living End", 0.70, 3),       # below min_matches
                   ("Boros Energy", "Boros Energy", 0.50, 99)])   # mirror, skipped
    c.commit()
    c.close()
    return path


def _with_db(fn):
    old = meta_bridge.DB_PATH
    meta_bridge.DB_PATH = _db()
    meta_bridge.get_real_field.cache_clear()
    try:
        fn()
    finally:
        meta_bridge.DB_PATH = old
        meta_bridge.get_real_field.cache_clear()


def test_field_shares_are_percents():
    def check():
        f = MetaBridge("Modern").field_shares(top_n=5)
        assert f == {"Boros Energy": 60.0, "Eldrazi Tron": 30.0, "Living End": 10.0}
    _with_db(check)


def test_matrix_has_both_directions_and_respects_min_matches():
    def check():
        m = MetaBridge("modern", min_matches=10).real_matchup_matrix()
        assert m == {("Boros Energy", "Eldrazi Tron"): 58.0, ("Eldrazi Tron", "Boros Energy"): 45.0}
        cov = MetaBridge("modern", min_matches=10).matchup_coverage()
        assert cov == {"archetypes": 2, "pairs_with_data": 2, "possible_pairs": 2,
                       "coverage_pct": 100.0}
    _with_db(check)


def test_field_summary_rows():
    def check():
        rows = MetaBridge("modern").field_summary(top_n=2)
        assert rows[0] == {"rank": 1, "archetype": "Boros Energy", "share": 66.7, "matches": 6}
        assert [r["archetype"] for r in rows] == ["Boros Energy", "Eldrazi Tron"]
    _with_db(check)


def test_no_db_falls_back_quietly():
    old = meta_bridge.DB_PATH
    meta_bridge.DB_PATH = os.path.join(tempfile.mkdtemp(), "missing.db")
    meta_bridge.get_real_field.cache_clear()
    try:
        b = MetaBridge("modern")
        assert b.real_matchup_matrix() == {}
        assert b.field_shares(top_n=3)          # format_config estimates
    finally:
        meta_bridge.DB_PATH = old
        meta_bridge.get_real_field.cache_clear()


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS: {name}")
    print("ALL META BRIDGE TESTS PASS")
