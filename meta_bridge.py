"""
meta_bridge.py — Bridge between mtg-sim and mtg-meta-analyzer database

Pulls real tournament data:
  - Field shares per format (from match frequency)
  - G1 win rates from matchup_matrix (actual tournament results)
  - Guide content for sideboard plans

Falls back to format_config.py estimates when DB data is unavailable.
"""

import os, sqlite3
from functools import lru_cache

# The analyzer's own MTG_META_DB wins (its live DB may sit outside the checkout).
DB_PATH = os.environ.get("MTG_META_DB") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "mtg-meta-analyzer", "data", "mtg_meta.db"
)

# Canonical DB names → names we use in format_config/parallel_launcher
# Keys are what we call them, values are what the DB calls them
NAME_MAP = {
    # Modern
    "Domain Zoo":         "Domain Aggro",
    "Dimir Murktide":     "Dimir Frog",
    "Izzet Affinity":     "Affinity",
    "Grinding Breach":    "Grinding Breach",
    "Goryo's Vengeance":  "Esper Reanimator",
    "Temur Breach":       "Simic Ritual",
    "Esper Blink":        "Esper Blink",
    "Jeskai Blink":       "Jeskai Blink",
    "Orzhov Blink":       "Orzhov Blink",
    # Standard
    "Izzet Cauldron":     "Izzet Cauldron",
    "Gruul Aggro":        "Gruul Aggro",
    "Boros Aggro":        "Boros Aggro",
    "Simic Ouroboroid":   "Simic Ouroboroid",
    "Sultai Reanimator":  "Sultai Reanimator",
    # Pioneer
    "Rakdos Aggro":       "Rakdos Aggro",
    "Jund Sacrifice":     "Rakdos Sacrifice",
    "Selesnya Company":   "Selesnya Company",
}

def _normalize(name: str) -> str:
    """Translate our deck name to the DB's archetype name."""
    return NAME_MAP.get(name, name)


def _conn():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH)


@lru_cache(maxsize=8)
def get_real_field(format_name: str, top_n: int = 15) -> dict:
    """
    Real field shares from actual match frequency in the DB.
    Returns {archetype: share_pct} sorted by share descending.
    """
    conn = _conn()
    if not conn:
        from format_config import get_field
        return get_field(format_name, top_n)

    cur = conn.cursor()
    cur.execute("""
        SELECT player1_arch, COUNT(*) as cnt
        FROM matches
        WHERE format=? AND player1_arch != ''
        GROUP BY player1_arch
        ORDER BY cnt DESC
        LIMIT ?
    """, (format_name, top_n))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        from format_config import get_field
        return get_field(format_name, top_n)

    total = sum(r[1] for r in rows)
    return {arch: round(cnt / total * 100, 1) for arch, cnt in rows}


@lru_cache(maxsize=64)
def get_real_matchup(our_deck: str, opp_deck: str,
                     format_name: str, min_matches: int = 20) -> float | None:
    """Real G1 win rate from tournament matchup_matrix. Returns None if insufficient data."""
    conn = _conn()
    if not conn:
        return None

    our_db  = _normalize(our_deck)
    opp_db  = _normalize(opp_deck)

    cur = conn.cursor()
    # Try direct lookup
    cur.execute("""
        SELECT winrate, matches FROM matchup_matrix
        WHERE format=? AND archetype_a=? AND archetype_b=? AND matches >= ?
    """, (format_name, our_db, opp_db, min_matches))
    row = cur.fetchone()
    if row:
        conn.close()
        return round(row[0] * 100, 1)

    # Try reversed
    cur.execute("""
        SELECT (1.0 - winrate) * 100, matches FROM matchup_matrix
        WHERE format=? AND archetype_a=? AND archetype_b=? AND matches >= ?
    """, (format_name, opp_db, our_db, min_matches))
    row = cur.fetchone()
    conn.close()
    return round(row[0], 1) if row else None


def get_all_matchups(our_deck: str, format_name: str,
                     top_n: int = 15, min_matches: int = 30) -> dict:
    """
    Get all real matchup win rates for our deck vs the field.
    Returns {opp_name: win_pct} where data exists.
    """
    field = get_real_field(format_name, top_n)
    results = {}
    for opp in field:
        wp = get_real_matchup(our_deck, opp, format_name, min_matches)
        if wp is not None:
            results[opp] = wp
    return results


def get_guide_content(archetype: str, format_name: str,
                      guide_type: str = "Guide") -> list[str]:
    """
    Fetch guide URLs for an archetype from the DB.
    Returns list of URLs.
    """
    conn = _conn()
    if not conn:
        return []

    cur = conn.cursor()
    cur.execute("""
        SELECT url, author, date FROM guides
        WHERE format=? AND archetype=? AND type=?
        ORDER BY date DESC LIMIT 5
    """, (format_name, archetype, guide_type))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]


def data_quality(format_name: str) -> dict:
    """Report on data quality for a format."""
    conn = _conn()
    if not conn:
        return {"available": False}

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM matches WHERE format=?", (format_name,))
    match_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM matchup_matrix
        WHERE format=? AND matches >= 30
    """, (format_name,))
    reliable_pairs = cur.fetchone()[0]

    conn.close()
    return {
        "available":      True,
        "match_count":    match_count,
        "reliable_pairs": reliable_pairs,
        "quality":        "high" if match_count > 10000 else
                          "medium" if match_count > 2000 else "low",
    }


if __name__ == "__main__":
    for fmt in ["modern", "standard", "pioneer", "legacy"]:
        q = data_quality(fmt)
        print(f"\n{fmt.upper()}: {q['quality']} quality — "
              f"{q.get('match_count',0):,} matches, "
              f"{q.get('reliable_pairs',0)} reliable matchup pairs")
        field = get_real_field(fmt, 5)
        for arch, pct in field.items():
            real_wp = get_real_matchup("Boros Energy", arch, fmt)
            wp_str  = f"  BE win%={real_wp:.0f}%" if real_wp else ""
            print(f"  {arch:<35} {pct:.1f}%{wp_str}")


class MetaBridge:
    """Object interface the gauntlet / event drivers import (bo3_gauntlet,
    gauntlet_any_deck, event_simulator, generate_matchup_data, sim_bridge).
    It was dropped when this module became plain functions in f8191fe, so
    every `from meta_bridge import MetaBridge` raised ImportError and the
    drivers fell back or stopped. Field shares are percents, like
    get_real_field() and format_config.get_field()."""

    def __init__(self, format_name: str = "modern", min_matches: int = 10):
        self.format = format_name.lower()
        self.min_matches = min_matches

    def field_shares(self, top_n: int = 15) -> dict:
        """{archetype: share_pct}, largest first."""
        return dict(get_real_field(self.format, top_n))

    def real_matchup_matrix(self) -> dict:
        """{(arch_a, arch_b): win_pct_for_a} from matchup_matrix, both
        directions, pairs with >= min_matches games. A stored row for a
        direction always wins over the 100-minus complement of the other.
        {} without a DB (or with a warning if the query fails)."""
        conn = _conn()
        if not conn:
            return {}
        try:
            rows = conn.execute(
                "SELECT archetype_a, archetype_b, winrate FROM matchup_matrix "
                "WHERE format=? AND matches >= ? AND archetype_a != archetype_b",
                (self.format, self.min_matches)).fetchall()
        except sqlite3.Error as e:
            print(f"  [MetaBridge] matchup query failed: {e}")
            return {}
        finally:
            conn.close()
        out, stored = {}, set()
        for a, b, wr in rows:
            out[(a, b)] = round(wr * 100, 1)
            stored.add((a, b))
            if (b, a) not in stored:
                out[(b, a)] = round(100 - wr * 100, 1)
        return out

    def field_summary(self, top_n: int = 15) -> list:
        """[{rank, archetype, share, matches}] for sim_bridge --show-field."""
        conn = _conn()
        counts = {}
        if conn:
            try:
                counts = dict(conn.execute(
                    "SELECT player1_arch, COUNT(*) FROM matches "
                    "WHERE format=? AND player1_arch != '' GROUP BY player1_arch",
                    (self.format,)).fetchall())
            except sqlite3.Error as e:
                print(f"  [MetaBridge] match count query failed: {e}")
            finally:
                conn.close()
        return [{"rank": i, "archetype": a, "share": pct, "matches": counts.get(a, 0)}
                for i, (a, pct) in enumerate(self.field_shares(top_n).items(), 1)]

    def matchup_coverage(self) -> dict:
        m = self.real_matchup_matrix()
        archs = {a for a, _ in m} | {b for _, b in m}
        possible = len(archs) * (len(archs) - 1)
        return {"archetypes": len(archs), "pairs_with_data": len(m),
                "possible_pairs": possible,
                "coverage_pct": round(len(m) / possible * 100, 1) if possible else 0}
