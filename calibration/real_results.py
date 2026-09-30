"""
calibration/real_results.py -- real match results from the meta-analyzer DB,
READ-ONLY (sqlite mode=ro). Spec harness/specs/2026-09-30-sim-real-scoreboard.md.

`matches` rows: player1_arch, player2_arch, result in {'player1','player2','draw'},
format, event_date (ISO or dd/mm/yy), source. Real rows are Bo3 MATCH results.

Rules: mirrors excluded; draws counted in n but not in the win rate; labels not
in the name map excluded (and reported as coverage); inferred bracket rows
(source bracket_*) excluded -- their pairing is guessed and player1 always wins.
"""
from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict

# Copy of mtg-meta-analyzer db/helpers.py::SQL_NORM_DATE -- matches.event_date and
# events.date hold BOTH 'YYYY-MM-DD' and 'dd/mm/yy'; a plain >= on the raw column
# compares '2026-03-14' < '18/03/26' lexically. Normalize to ISO first.
SQL_NORM_DATE = (
    "(CASE WHEN instr({col},'/')>0 AND length({col})=10 "
    "THEN substr({col},7,4)||'-'||substr({col},4,2)||'-'||substr({col},1,2) "
    "WHEN instr({col},'/')>0 "
    "THEN '20'||substr({col},7,2)||'-'||substr({col},4,2)||'-'||substr({col},1,2) "
    "ELSE substr({col},1,10) END)"
)

HERE = os.path.dirname(os.path.abspath(__file__))


def load_name_map(fmt: str) -> dict:
    with open(os.path.join(HERE, f"name_map_{fmt}.json"), encoding="utf-8") as f:
        m = json.load(f)
    return {k: v for k, v in m.items() if not k.startswith("_")}


def label_index(name_map: dict) -> dict[str, str]:
    """DB label -> modeled deck name."""
    out = {}
    for deck, spec in name_map.items():
        for label in spec["labels"]:
            out[label] = deck
    return out


def connect_ro(db_path: str | None = None) -> sqlite3.Connection:
    if db_path is None:
        from db_bridge import _resolve_meta_db
        db_path = _resolve_meta_db()
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


def _rows(con, fmt: str, since: str, until: str | None):
    nd = SQL_NORM_DATE.format(col="event_date")
    q = (f"SELECT player1_arch, player2_arch, result FROM matches "
         f"WHERE format = ? AND {nd} >= ? AND (source IS NULL OR source NOT LIKE 'bracket%')")
    args = [fmt, since]
    if until:
        q += f" AND {nd} <= ?"
        args.append(until)
    return con.execute(q, args).fetchall()


def real_matchups(con, fmt: str, since: str, name_map: dict, until: str | None = None) -> dict:
    """{(a, b): {'wins': a's wins, 'losses', 'draws', 'n'}} with a < b alphabetically,
    plus '_coverage': {'rows', 'mapped_rows', 'unmapped_labels': {label: appearances}}."""
    idx = label_index(name_map)
    cells: dict = defaultdict(lambda: {"wins": 0, "losses": 0, "draws": 0, "n": 0})
    unmapped: dict = defaultdict(int)
    rows = mapped = 0
    for p1, p2, result in _rows(con, fmt, since, until):
        rows += 1
        a, b = idx.get(p1), idx.get(p2)
        for lab, d in ((p1, a), (p2, b)):
            if d is None and lab:
                unmapped[lab] += 1
        if a is None or b is None:
            continue
        mapped += 1
        if a == b:
            continue                         # mirror
        if a > b:                            # orient so the first deck is alphabetical
            a, b = b, a
            result = {"player1": "player2", "player2": "player1"}.get(result, result)
        c = cells[(a, b)]
        c["n"] += 1
        if result == "player1":
            c["wins"] += 1
        elif result == "player2":
            c["losses"] += 1
        else:
            c["draws"] += 1
    out = dict(cells)
    out["_coverage"] = {"rows": rows, "mapped_rows": mapped,
                        "unmapped_labels": dict(sorted(unmapped.items(), key=lambda x: -x[1]))}
    return out


def real_field_shares(con, fmt: str, since: str, name_map: dict, until: str | None = None) -> dict:
    """Share of all real match appearances (both seats) per modeled deck; the rest is
    reported as '_unmapped'."""
    idx = label_index(name_map)
    counts: dict = defaultdict(int)
    total = 0
    for p1, p2, _r in _rows(con, fmt, since, until):
        for lab in (p1, p2):
            if not lab:
                continue
            total += 1
            counts[idx.get(lab, "_unmapped")] += 1
    return {k: v / total for k, v in counts.items()} if total else {}


def real_list_profile(con, fmt: str, since: str, labels: list[str]) -> tuple[int, dict]:
    """(n_decks, {card: share of decks running it}) for real mainboards under `labels`."""
    nd = SQL_NORM_DATE.format(col="e.date")
    q = ",".join("?" * len(labels))
    n = con.execute(
        f"""SELECT COUNT(*) FROM decks d JOIN events e ON e.id = d.event_id
            WHERE e.format = ? AND d.archetype IN ({q}) AND {nd} >= ?""",
        (fmt, *labels, since)).fetchone()[0]
    prof: dict = {}
    if n:
        for card, k in con.execute(
                f"""SELECT c.name, COUNT(DISTINCT d.id) FROM decks d
                    JOIN events e ON e.id = d.event_id
                    JOIN deck_cards dc ON dc.deck_id = d.id AND dc.is_sideboard = 0
                    JOIN cards c ON c.id = dc.card_id
                    WHERE e.format = ? AND d.archetype IN ({q}) AND {nd} >= ?
                    GROUP BY c.name""", (fmt, *labels, since)):
            prof[card] = k / n
    return n, prof


# ---------------------------------------------------------------- real matchup for the launcher
# Spec harness/specs/2026-09-30-combo-routing-fix.md (A1/A2). The window matches each
# format's real field (format_config): Modern post-ban, Standard current meta.
REAL_WINDOWS = {"modern": "2026-05-15", "standard": "2026-08-15"}
SHRINK_K = 50        # pseudo-matches at 50%: 0.25 / 0.07^2 (real Modern spread ~7pp from 50%)
MIN_DECISIVE = 20


def _norm(s: str) -> str:
    return s.lower().strip().replace(" ", "").replace("-", "").replace("'", "")


def resolve_labels(key: str, name_map: dict) -> list[str] | None:
    """DB labels for a launcher/field key: the name-map deck name, its `field_key`,
    or its `apl` key (e.g. "Dimir Midrange Std" -> apl `dimirmidrangestd`)."""
    for deck, spec in name_map.items():
        if key == deck or key == spec.get("field_key"):
            return spec["labels"]
    for deck, spec in name_map.items():
        if _norm(key) == _norm(spec.get("apl", "")):
            return spec["labels"]
    return None


def real_match_wr(con, our_key: str, opp_key: str, fmt: str, name_map: dict | None = None,
                  min_decisive: int = MIN_DECISIVE, k: int = SHRINK_K) -> dict | None:
    """Real Bo3 MATCH result of our deck vs the opponent in the format's window.
    Returns {"wins", "losses", "draws", "decisive", "raw", "shrunk"} (rates in 0..1) or
    None when the format has no window, a key is unmapped, or decisive < min_decisive.
    shrunk = (wins + k/2) / (decisive + k)."""
    since = REAL_WINDOWS.get(fmt)
    if since is None:
        return None
    if name_map is None:
        name_map = load_name_map(fmt)
    ours, theirs = resolve_labels(our_key, name_map), resolve_labels(opp_key, name_map)
    if not ours or not theirs or set(ours) & set(theirs):
        return None
    ours, theirs = set(ours), set(theirs)
    w = l = d = 0
    for p1, p2, result in _rows(con, fmt, since, None):
        if p1 in ours and p2 in theirs:
            our_seat = "player1"
        elif p2 in ours and p1 in theirs:
            our_seat = "player2"
        else:
            continue
        if result == our_seat:
            w += 1
        elif result in ("player1", "player2"):
            l += 1
        else:
            d += 1
    dec = w + l
    if dec < min_decisive:
        return None
    return {"wins": w, "losses": l, "draws": d, "decisive": dec,
            "raw": w / dec, "shrunk": (w + k / 2) / (dec + k)}
