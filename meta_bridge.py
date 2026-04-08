"""
meta_bridge.py — Connect mtg-sim to the MTG Meta Analyzer database

Replaces the goldfish-race approach in sim_bridge.py with real match data
where available. Falls back to goldfish simulation when real data is thin.

Three integration points:
  1. get_real_matchup_wrs(format)     → real G1 win rates from 262k+ matches
  2. get_field(format, top_n)         → actual meta standings (who plays what)
  3. get_avg_decklist(archetype, fmt) → real tournament average deck

Usage from sim_bridge.py:
  from meta_bridge import MetaBridge
  bridge = MetaBridge(format_name="legacy")
  wrs    = bridge.real_matchup_matrix()     # {(A, B): win_pct}
  field  = bridge.field_shares()            # {archetype: fraction}
  deck   = bridge.get_decklist("Humans")    # {card_name: qty}
"""

import os
import sys

# Path to the meta-analyzer
_META_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "mtg-meta-analyzer")
)
if _META_PATH not in sys.path:
    sys.path.insert(0, _META_PATH)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_conn():
    from db.database import get_connection
    return get_connection()


def _normalize(name: str) -> str:
    """Normalize an archetype name via the meta-analyzer pipeline."""
    try:
        from analysis.archetypes import normalize
        return normalize(name)
    except Exception:
        return name


# ──────────────────────────────────────────────────────────────────────────────
# MetaBridge
# ──────────────────────────────────────────────────────────────────────────────

class MetaBridge:
    """
    Bridge between mtg-sim and the MTG Meta Analyzer database.

    Parameters
    ----------
    format_name : str   e.g. "legacy", "modern", "pioneer", "standard"
    min_matches : int   minimum real matches required to trust a matchup
    since       : str   ISO date string (e.g. "2025-01-01"), or None for all time
    """

    def __init__(
        self,
        format_name: str = "legacy",
        min_matches: int = 10,
        since: str | None = None,
    ):
        self.format   = format_name.lower()
        self.min_matches = min_matches
        self.since    = since
        self._cache_matchups = None
        self._cache_field    = None

    # ── 1. Real matchup win rates ─────────────────────────────────────────────

    def real_matchup_matrix(self) -> dict[tuple[str, str], float]:
        """
        Return {(arch_A, arch_B): win_pct_for_A} from real match results.

        Only includes pairings with >= min_matches games.
        Win pct is expressed as 0-100.
        """
        if self._cache_matchups is not None:
            return self._cache_matchups

        q = """
            SELECT player1_arch AS a, player2_arch AS b,
                   SUM(CASE WHEN winner_arch = player1_arch THEN 1.0
                             WHEN result = 'player1'       THEN 1.0
                             ELSE 0.0 END) AS wins,
                   COUNT(*) AS n
            FROM matches
            WHERE lower(format) = ?
              AND player1_arch != '' AND player2_arch != ''
              AND player1_arch IS NOT NULL AND player2_arch IS NOT NULL
        """
        params = [self.format]
        if self.since:
            q += " AND event_date >= ?"
            params.append(self.since)
        q += " GROUP BY player1_arch, player2_arch HAVING n >= ?"
        params.append(self.min_matches)

        matrix: dict[tuple[str, str], float] = {}
        try:
            with _get_conn() as conn:
                rows = conn.execute(q, params).fetchall()

            for r in rows:
                a = _normalize(r["a"])
                b = _normalize(r["b"])
                if a == b:
                    continue
                wp = round(r["wins"] / r["n"] * 100, 1)
                matrix[(a, b)] = wp
                # Ensure symmetric complement exists
                if (b, a) not in matrix:
                    matrix[(b, a)] = round(100 - wp, 1)

        except Exception as e:
            print(f"  [MetaBridge] matchup query failed: {e}")

        self._cache_matchups = matrix
        return matrix

    def matchup_coverage(self) -> dict:
        """Report how many real matchup pairs we have vs total possible."""
        m = self.real_matchup_matrix()
        archs = {a for a, _ in m} | {b for _, b in m}
        possible = len(archs) * (len(archs) - 1)
        return {
            "archetypes":     len(archs),
            "pairs_with_data": len(m),
            "possible_pairs":  possible,
            "coverage_pct":   round(len(m) / possible * 100, 1) if possible else 0,
        }

    # ── 2. Field composition ──────────────────────────────────────────────────

    def field_shares(self, top_n: int = 15) -> dict[str, float]:
        """
        Return {archetype: fraction} for the top_n archetypes in this format.

        Uses real match appearance counts as the population proxy.
        """
        if self._cache_field is not None:
            return self._cache_field

        q = """
            SELECT player1_arch AS arch, COUNT(*) AS n
            FROM matches WHERE lower(format) = ?
              AND player1_arch != '' AND player1_arch IS NOT NULL
        """
        params = [self.format]
        if self.since:
            q += " AND event_date >= ?"
            params.append(self.since)
        q += """
            GROUP BY player1_arch
            UNION ALL
            SELECT player2_arch, COUNT(*) FROM matches
            WHERE lower(format) = ?
              AND player2_arch != '' AND player2_arch IS NOT NULL
        """
        params.append(self.format)
        if self.since:
            q += " AND event_date >= ?"
            params.append(self.since)
        q += " GROUP BY player2_arch"

        counts: dict[str, int] = {}
        try:
            with _get_conn() as conn:
                rows = conn.execute(q, params).fetchall()
            for r in rows:
                arch = _normalize(r["arch"])
                counts[arch] = counts.get(arch, 0) + r["n"]
        except Exception as e:
            print(f"  [MetaBridge] field query failed: {e}")
            return {}

        # Sort and take top_n
        sorted_archs = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
        total = sum(v for _, v in sorted_archs) or 1
        shares = {a: round(n / total, 4) for a, n in sorted_archs}

        self._cache_field = shares
        return shares

    def field_summary(self, top_n: int = 15) -> list[dict]:
        """Return field as a list of dicts with rank, archetype, share, match_count."""
        q = """
            SELECT arch, SUM(n) AS total FROM (
                SELECT player1_arch AS arch, COUNT(*) AS n
                FROM matches WHERE lower(format) = ?
                  AND player1_arch != ''
                GROUP BY player1_arch
                UNION ALL
                SELECT player2_arch, COUNT(*) FROM matches
                WHERE lower(format) = ?
                  AND player2_arch != ''
                GROUP BY player2_arch
            ) GROUP BY arch ORDER BY total DESC LIMIT ?
        """
        rows = []
        try:
            with _get_conn() as conn:
                rows = conn.execute(q, [self.format, self.format, top_n]).fetchall()
        except Exception as e:
            print(f"  [MetaBridge] field_summary failed: {e}")

        total = sum(r["total"] for r in rows) or 1
        return [
            {
                "rank":      i + 1,
                "archetype": _normalize(r["arch"]),
                "share":     round(r["total"] / total * 100, 1),
                "matches":   r["total"],
            }
            for i, r in enumerate(rows)
        ]

    # ── 3. Real decklists ─────────────────────────────────────────────────────

    def get_decklist(
        self,
        archetype: str,
        top_n_decks: int = 20,
    ) -> dict[str, float]:
        """
        Return an average mainboard decklist for an archetype from the DB.

        Returns {card_name: avg_copies} using cards that appear in >= 50%
        of the sampled top_n_decks tournament lists.

        This replaces the hardcoded decklists in sim's gauntlet CSV.
        """
        q = """
            SELECT dc.deck_id, c.name, dc.quantity
            FROM decks d
            JOIN events e   ON e.id  = d.event_id
            JOIN deck_cards dc ON dc.deck_id = d.id
            JOIN cards c    ON c.id  = dc.card_id
            WHERE lower(e.format) = ?
              AND lower(d.archetype) LIKE lower(?)
              AND dc.is_sideboard = 0
              AND d.id IN (
                  SELECT id FROM decks
                  WHERE event_id IN (SELECT id FROM events WHERE lower(format)=?)
                    AND lower(archetype) LIKE lower(?)
                  ORDER BY id DESC
                  LIMIT ?
              )
        """
        arch_pattern = f"%{archetype.lower()}%"
        params = [self.format, arch_pattern, self.format, arch_pattern, top_n_decks]

        deck_cards: dict[int, dict[str, int]] = {}
        try:
            with _get_conn() as conn:
                rows = conn.execute(q, params).fetchall()
            for r in rows:
                deck_cards.setdefault(r["deck_id"], {})[r["name"]] = r["quantity"]
        except Exception as e:
            print(f"  [MetaBridge] decklist query failed: {e}")
            return {}

        if not deck_cards:
            return {}

        n_decks = len(deck_cards)
        card_totals: dict[str, list[int]] = {}
        for cards in deck_cards.values():
            for name, qty in cards.items():
                card_totals.setdefault(name, []).append(qty)

        # Only include cards in >= 50% of decks
        avg_deck = {}
        for name, qtys in card_totals.items():
            if len(qtys) >= n_decks * 0.5:
                avg_deck[name] = round(sum(qtys) / len(qtys), 1)

        return avg_deck

    def get_decklist_integer(
        self,
        archetype: str,
        top_n_decks: int = 20,
    ) -> dict[str, int]:
        """
        Same as get_decklist but rounds to whole card counts (for sim use).
        Caps each card at 4 copies.
        """
        avg = self.get_decklist(archetype, top_n_decks)
        return {k: min(4, max(1, round(v))) for k, v in avg.items() if v >= 0.5}
