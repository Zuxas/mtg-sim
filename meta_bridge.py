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

DB_PATH = os.path.join(
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
