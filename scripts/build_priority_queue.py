#!/usr/bin/env python3
"""
Build a ranked priority queue for the current Standard matrix card pool.

Inputs:
- decklists from decks/*_standard.txt
- optional aggregated telemetry at data/telemetry/card_summary_latest.json
- optional handler registries if importable

Outputs:
- data/priority_queue/standard_matrix_queue.json

Design goals:
- shallow imports
- no full engine load required
- graceful fallback if handler registries are not importable
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Set, Tuple

# Allow running from anywhere: repo root is the parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from engine.card_priority import (
    CardStats,
    get_severity,
    score_cards,
)
from engine.effect_family_registry import CARD_TO_FAMILY

# Meta shares are loaded from data/priority_queue/meta_share_by_deck.json
# if the file exists. Populate it via scripts/build_meta_shares.py, which
# reads from the meta-analyzer DB. Absent file → empty dict (bootstrap).
DEFAULT_META_SHARE_PATH = Path("data/priority_queue/meta_share_by_deck.json")
META_SHARE_BY_DECK: Dict[str, float] = {}

DEFAULT_QUEUE_PATH = Path("data/priority_queue/standard_matrix_queue.json")
DEFAULT_QUEUE_CSV_PATH = Path("data/priority_queue/standard_matrix_queue.csv")
DEFAULT_TELEMETRY_SUMMARY_PATH = Path("data/telemetry/card_summary_latest.json")
DECKS_DIR = Path("decks")
DEFAULT_META_DB_PATH = Path(os.environ.get(
    "MTG_META_DB",
    Path(__file__).resolve().parent.parent.parent / "mtg-meta-analyzer" / "data" / "mtg_meta.db"
))


def load_meta_share_by_deck(path: Path = DEFAULT_META_SHARE_PATH) -> Dict[str, float]:
    """Load deck-slug → meta share dict. Empty dict if the file is absent."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in data.items()}

CARD_LINE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*(?:\([A-Z0-9]+\)\s+\d+)?\s*$")


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def slugify_deck_name(path: Path) -> str:
    name = path.stem.lower()
    if name.endswith("_standard"):
        name = name[:-9]
    return name


def parse_decklist_file(path: Path) -> Counter:
    """
    Very permissive parser for decklists like:
      4 Lightning Strike
      2 Torch the Tower (WOE) 153
    """
    counts: Counter = Counter()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith(("sideboard", "companion", "#")):
            continue
        match = CARD_LINE_RE.match(line)
        if not match:
            continue
        qty = int(match.group(1))
        card_name = match.group(2).strip()
        counts[card_name] += qty
    return counts


def load_standard_decklists(decks_dir: Path = DECKS_DIR) -> Dict[str, Counter]:
    decklists: Dict[str, Counter] = {}
    for path in sorted(decks_dir.glob("*_standard.txt")):
        decklists[slugify_deck_name(path)] = parse_decklist_file(path)
    return decklists


def load_decklists_from_db(
    db_path: Path = DEFAULT_META_DB_PATH,
    *,
    window_from: Optional[str] = None,
    window_to: Optional[str] = None,
) -> Dict[str, Counter]:
    """
    Build synthetic per-archetype decklists by aggregating deck_cards from the
    meta DB, keyed by slugified archetype name.

    window_from / window_to are ISO dates (YYYY-MM-DD). If set, filters to
    events in that window; otherwise uses all Standard events.

    This gives the queue access to the full Standard card pool, not just the
    subset committed as local *_standard.txt files.
    """
    if not db_path.exists():
        return {}

    def iso_to_sortable(iso_date: str) -> str:
        return iso_date[2:4] + "-" + iso_date[5:7] + "-" + iso_date[8:10]

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()

    where_clauses = ["LOWER(e.format) = 'standard'"]
    params: List[str] = []
    if window_from:
        where_clauses.append(
            "substr(e.date,7,2)||'-'||substr(e.date,4,2)||'-'||substr(e.date,1,2) >= ?"
        )
        params.append(iso_to_sortable(window_from))
    if window_to:
        where_clauses.append(
            "substr(e.date,7,2)||'-'||substr(e.date,4,2)||'-'||substr(e.date,1,2) <= ?"
        )
        params.append(iso_to_sortable(window_to))
    where_sql = " AND ".join(where_clauses)

    cur.execute(
        f"""
        SELECT d.archetype, c.name, SUM(dc.quantity) AS qty
        FROM deck_cards dc
        JOIN decks d ON dc.deck_id = d.id
        JOIN events e ON d.event_id = e.id
        JOIN cards c ON dc.card_id = c.id
        WHERE {where_sql}
        GROUP BY d.archetype, c.name
        """,
        params,
    )

    decklists: Dict[str, Counter] = {}
    for archetype, card_name, qty in cur.fetchall():
        if not archetype or not card_name:
            continue
        slug = (
            archetype.lower()
            .replace("/", "_").replace("-", "_").replace("'", "")
            .replace(",", "").replace(".", "").replace(" ", "_")
        )
        if slug not in decklists:
            decklists[slug] = Counter()
        decklists[slug][card_name] += int(qty or 0)
    return decklists


def merge_decklists(primary: Dict[str, Counter], fallback: Dict[str, Counter]) -> Dict[str, Counter]:
    """
    Merge two decklist sources. Entries in `primary` win on key collision —
    local decklists represent curated/runnable versions and should take
    precedence over DB aggregations.
    """
    merged: Dict[str, Counter] = dict(primary)
    for slug, counts in fallback.items():
        if slug not in merged:
            merged[slug] = counts
    return merged


def load_json_if_exists(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_telemetry_summary(path: Path = DEFAULT_TELEMETRY_SUMMARY_PATH) -> Dict[str, dict]:
    data = load_json_if_exists(path)
    if not data:
        return {}
    if isinstance(data, dict):
        return data
    raise ValueError(f"Telemetry summary at {path} must be a JSON object keyed by card name.")


HANDLER_DICT_NAMES = frozenset({
    "ETB_EFFECTS", "SPELL_EFFECTS", "SAGA_EFFECTS", "CLASS_DEFS",
    "_LORD_EFFECTS", "_COST_REDUCTIONS", "_CONDITIONAL_EVASION",
    "_SPELL_HANDLERS", "_ETB_HANDLERS",
    "LANDFALL_GROW", "LANDFALL_TOKEN", "LANDFALL_ASCENSION",
    "MATCH_REMOVAL",
})


def scan_handler_statuses() -> Dict[str, str]:
    """
    Determine handler status by importing the authoritative registries.

    The card_effects module's install loop merges card_handlers_verified
    entries into ETB_EFFECTS/SPELL_EFFECTS at import time, so a successful
    import gives us the true registered set. AST fallback is used ONLY if
    the imports fail, and is restricted to dict-literal keys assigned to
    handler registries — never arbitrary string constants.
    """
    statuses: Dict[str, str] = {}
    import_ok = False

    try:
        from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS  # type: ignore
        from engine.sagas import SAGA_EFFECTS  # type: ignore
        from engine.classes import CLASS_DEFS  # type: ignore
        from engine.game_state import _LORD_EFFECTS, _COST_REDUCTIONS  # type: ignore
        from engine.match_state import _CONDITIONAL_EVASION  # type: ignore
        from apl.match_apl import MatchAPL  # type: ignore

        for registry in (ETB_EFFECTS, SPELL_EFFECTS, SAGA_EFFECTS, CLASS_DEFS,
                         _LORD_EFFECTS, _COST_REDUCTIONS, _CONDITIONAL_EVASION,
                         MatchAPL.MATCH_REMOVAL):
            for key in registry:
                statuses[str(key)] = "verified"
        import_ok = True
    except Exception:
        pass

    try:
        import engine.auto_handlers as auto_handlers  # type: ignore

        for attr_name in dir(auto_handlers):
            attr = getattr(auto_handlers, attr_name)
            if isinstance(attr, dict):
                for key in attr.keys():
                    statuses.setdefault(str(key), "auto")
    except Exception:
        pass

    # AST fallback ONLY if imports failed. Restricted to dict-literal keys.
    if not import_ok:
        verified_path = Path("engine/card_handlers_verified.py")
        if verified_path.exists():
            for name in extract_dict_keys_from_source(
                verified_path.read_text(encoding="utf-8"),
                target_dict_names=HANDLER_DICT_NAMES,
            ):
                statuses[name] = "verified"

    return statuses


def extract_dict_keys_from_source(
    source_text: str,
    target_dict_names: Set[str],
) -> Set[str]:
    """
    Extract string keys from dict literals that are assigned-to or .update()'d
    on one of the target names. This avoids the false-positive problem of
    scanning every string constant in a source file.

    Patterns matched:
        TARGET = { "key": ..., ... }
        TARGET.update({ "key": ..., ... })
    """
    results: Set[str] = set()
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return results

    for node in ast.walk(tree):
        dict_node: Optional[ast.Dict] = None

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in target_dict_names:
                    if isinstance(node.value, ast.Dict):
                        dict_node = node.value
                        break

        elif isinstance(node, ast.Call):
            func = node.func
            if (isinstance(func, ast.Attribute)
                    and func.attr == "update"
                    and isinstance(func.value, ast.Name)
                    and func.value.id in target_dict_names
                    and node.args
                    and isinstance(node.args[0], ast.Dict)):
                dict_node = node.args[0]

        if dict_node is None:
            continue
        for key in dict_node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                results.add(key.value)
    return results


def build_card_stats(
    decklists: Mapping[str, Counter],
    handler_statuses: Mapping[str, str],
    telemetry_summary: Mapping[str, dict],
) -> Dict[str, CardStats]:
    all_card_names: Set[str] = set()
    copies_total: Counter = Counter()
    decks_present_in: Counter = Counter()
    meta_share_sum: Dict[str, float] = defaultdict(float)
    meta_share_weighted_copies: Dict[str, float] = defaultdict(float)

    for deck_name, counts in decklists.items():
        deck_meta = META_SHARE_BY_DECK.get(deck_name, 0.0)
        for card_name, qty in counts.items():
            all_card_names.add(card_name)
            copies_total[card_name] += qty
            decks_present_in[card_name] += 1
            meta_share_sum[card_name] += deck_meta
            meta_share_weighted_copies[card_name] += deck_meta * qty

    stats_by_card: Dict[str, CardStats] = {}
    for card_name in sorted(all_card_names):
        telemetry = telemetry_summary.get(card_name, {})
        status = handler_statuses.get(card_name, "missing")
        stats = CardStats(
            card_name=card_name,
            effect_family=CARD_TO_FAMILY.get(card_name, ""),
            handler_status=status,
            copies_total=copies_total[card_name],
            decks_present_in=decks_present_in[card_name],
            meta_share_sum=meta_share_sum[card_name],
            meta_share_weighted_copies=meta_share_weighted_copies[card_name],
            effect_severity=get_severity(card_name),
            complexity_penalty=0.0,  # tunable: populate manually later if desired
            total_games=int(telemetry.get("total_games", 0)),
            times_drawn=int(telemetry.get("times_drawn", 0)),
            times_in_opening_hand=int(telemetry.get("times_in_opening_hand", 0)),
            times_cast=int(telemetry.get("times_cast", 0)),
            times_resolved=int(telemetry.get("times_resolved", 0)),
            times_countered=int(telemetry.get("times_countered", 0)),
            times_fizzled=int(telemetry.get("times_fizzled", 0)),
            times_entered_battlefield=int(telemetry.get("times_entered_battlefield", 0)),
            times_died=int(telemetry.get("times_died", 0)),
            times_moved_zones=int(telemetry.get("times_moved_zones", 0)),
            sum_turn_cast=int(telemetry.get("sum_turn_cast", 0)),
            first_turn_cast_min=telemetry.get("first_turn_cast_min"),
            games_won_when_cast=int(telemetry.get("games_won_when_cast", 0)),
            games_played_when_cast=int(telemetry.get("games_played_when_cast", 0)),
            times_seen_total=int(telemetry.get("times_seen_total", 0)),
            illegal_event_count=int(telemetry.get("illegal_event_count", 0)),
        )
        stats_by_card[card_name] = stats

    return stats_by_card


def write_queue_json(path: Path, scored_cards: Mapping[str, CardStats]) -> None:
    ensure_parent_dir(path)
    sorted_rows = sorted(
        (stats.to_dict() for stats in scored_cards.values()),
        key=lambda row: (-row["priority_score"], row["card_name"]),
    )
    path.write_text(json.dumps(sorted_rows, indent=2, sort_keys=False), encoding="utf-8")


def write_queue_csv(path: Path, scored_cards: Mapping[str, CardStats]) -> None:
    ensure_parent_dir(path)
    rows = sorted(
        (stats.to_dict() for stats in scored_cards.values()),
        key=lambda row: (-row["priority_score"], row["card_name"]),
    )
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    headers = [
        "card_name",
        "effect_family",
        "handler_status",
        "copies_total",
        "decks_present_in",
        "meta_share_sum",
        "meta_share_weighted_copies",
        "effect_severity",
        "cast_rate",
        "resolve_rate",
        "opening_hand_rate",
        "avg_turn_cast",
        "games_won_when_cast",
        "games_played_when_cast",
        "priority_score",
        "score_mode",
        "notes",
    ]
    lines = [",".join(headers)]
    for row in rows:
        values = [escape_csv(row.get(header, "")) for header in headers]
        lines.append(",".join(values))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def escape_csv(value: object) -> str:
    text = str(value)
    if any(ch in text for ch in [",", '"', "\n"]):
        return '"' + text.replace('"', '""') + '"'
    return text


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--source", choices=("decks", "db", "both"), default="decks",
        help="Card pool source. 'decks'=local *_standard.txt only (default, "
             "scope matches what sim can run); 'db'=aggregate from mtg_meta.db; "
             "'both'=union (local decklists win on collision).",
    )
    ap.add_argument("--db", default=str(DEFAULT_META_DB_PATH),
                    help="Path to mtg_meta.db (used when --source=db|both)")
    ap.add_argument("--from", dest="from_date",
                    help="YYYY-MM-DD window start for DB source")
    ap.add_argument("--to", dest="to_date",
                    help="YYYY-MM-DD window end for DB source")
    return ap.parse_args()


def main() -> None:
    args = parse_args()

    global META_SHARE_BY_DECK
    META_SHARE_BY_DECK = load_meta_share_by_deck()

    if args.source == "decks":
        decklists = load_standard_decklists()
    elif args.source == "db":
        decklists = load_decklists_from_db(
            Path(args.db), window_from=args.from_date, window_to=args.to_date,
        )
    else:  # both
        local = load_standard_decklists()
        db = load_decklists_from_db(
            Path(args.db), window_from=args.from_date, window_to=args.to_date,
        )
        decklists = merge_decklists(local, db)

    telemetry_summary = load_telemetry_summary()
    handler_statuses = scan_handler_statuses()

    stats_by_card = build_card_stats(decklists, handler_statuses, telemetry_summary)
    use_telemetry = any(stats.total_games > 0 for stats in stats_by_card.values())

    # Cards hand-tagged severity 1 are by definition "nothing to tune here"
    # — basic lands, cosmetic riders, etc. Exclude them from the queue so
    # raw meta-weight can't float them to the top.
    before_filter = len(stats_by_card)
    stats_by_card = {
        name: stats for name, stats in stats_by_card.items()
        if get_severity(name, stats.effect_severity) > 1
    }
    filtered_count = before_filter - len(stats_by_card)

    scored_cards = score_cards(stats_by_card, use_telemetry=use_telemetry)
    write_queue_json(DEFAULT_QUEUE_PATH, scored_cards)
    write_queue_csv(DEFAULT_QUEUE_CSV_PATH, scored_cards)

    print(f"Wrote {len(scored_cards)} cards to {DEFAULT_QUEUE_PATH}")
    print(f"Source: {args.source}  ({len(decklists)} decks)")
    print(f"Filtered out {filtered_count} severity-1 cards (cosmetic/done)")
    print(f"Telemetry mode: {'full' if use_telemetry else 'bootstrap'}")
    print(f"Meta shares loaded: {len(META_SHARE_BY_DECK)} decks")


if __name__ == "__main__":
    main()
