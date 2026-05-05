#!/usr/bin/env python3
"""
Aggregate raw JSONL telemetry into per-card summaries.

Outputs:
- data/telemetry/card_summary_latest.json
- data/telemetry/card_summary.parquet (if parquet engine available)
- data/telemetry/card_summary.csv (always)

Design goals:
- stdlib-first
- avoid pandas
- graceful parquet fallback if pyarrow/parquet isn't installed
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

# Allow running from anywhere: repo root is the parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)

RAW_PATH = Path("data/telemetry/raw_games.jsonl")
JSON_SUMMARY_PATH = Path("data/telemetry/card_summary_latest.json")
CSV_SUMMARY_PATH = Path("data/telemetry/card_summary.csv")
PARQUET_SUMMARY_PATH = Path("data/telemetry/card_summary.parquet")


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def load_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def nested_defaultdict():
    return defaultdict(int)


def summarize_events(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    per_card: Dict[str, Dict[str, Any]] = {}
    seen_game_card = set()
    seen_game_card_opening = set()
    seen_game_card_cast = set()

    for row in rows:
        event_type = row.get("event_type", "")
        game_id = row.get("game_id", "")
        card_name = row.get("card_name", "")
        payload = row.get("payload", {}) or {}

        if not card_name and event_type != "game_end":
            continue

        if card_name not in per_card and card_name:
            per_card[card_name] = {
                "card_name": card_name,
                "total_games": 0,
                "times_drawn": 0,
                "times_in_opening_hand": 0,
                "times_cast": 0,
                "times_resolved": 0,
                "times_countered": 0,
                "times_fizzled": 0,
                "times_entered_battlefield": 0,
                "times_died": 0,
                "times_moved_zones": 0,
                "sum_turn_cast": 0,
                "first_turn_cast_min": None,
                "games_won_when_cast": 0,
                "games_played_when_cast": 0,
                "times_seen_total": 0,
                "illegal_event_count": 0,
                "handler_source_used": "",
                "effect_family": "",
            }

        if not card_name:
            continue

        summary = per_card[card_name]
        summary["handler_source_used"] = payload.get("handler_source_used", summary["handler_source_used"])
        summary["effect_family"] = payload.get("effect_family", summary["effect_family"])

        seen_key = (game_id, card_name)
        if seen_key not in seen_game_card:
            seen_game_card.add(seen_key)
            summary["total_games"] += 1
            summary["times_seen_total"] += 1

        if event_type == "draw":
            summary["times_drawn"] += 1
            if payload.get("opening_hand"):
                summary["times_in_opening_hand"] += 1
                seen_game_card_opening.add(seen_key)

        elif event_type == "cast":
            summary["times_cast"] += 1
            turn_number = payload.get("turn_number")
            if isinstance(turn_number, int):
                summary["sum_turn_cast"] += turn_number
                current_min = summary["first_turn_cast_min"]
                if current_min is None or turn_number < current_min:
                    summary["first_turn_cast_min"] = turn_number
            if not payload.get("legal_cast", True):
                summary["illegal_event_count"] += 1

            if seen_key not in seen_game_card_cast:
                seen_game_card_cast.add(seen_key)
                summary["games_played_when_cast"] += 1

        elif event_type == "resolve":
            if payload.get("resolved"):
                summary["times_resolved"] += 1
            if payload.get("countered"):
                summary["times_countered"] += 1
            if payload.get("fizzled"):
                summary["times_fizzled"] += 1

        elif event_type == "zone_transition":
            summary["times_moved_zones"] += 1
            if payload.get("entered_battlefield"):
                summary["times_entered_battlefield"] += 1
            if payload.get("died"):
                summary["times_died"] += 1

    # Second pass for game_end -> games_won_when_cast
    # We map by game_id and deck_id presence, then attribute to cards cast in that same game.
    cast_presence_by_game_and_card = set()
    for row in rows:
        if row.get("event_type") == "cast" and row.get("card_name"):
            cast_presence_by_game_and_card.add((row.get("game_id", ""), row.get("card_name", "")))

    for row in rows:
        if row.get("event_type") != "game_end":
            continue
        game_id = row.get("game_id", "")
        payload = row.get("payload", {}) or {}
        won = bool(payload.get("won", False))
        illegal_count = int(payload.get("illegal_event_count", 0))

        for candidate_game_id, card_name in cast_presence_by_game_and_card:
            if candidate_game_id != game_id or card_name not in per_card:
                continue
            if won:
                per_card[card_name]["games_won_when_cast"] += 1
            per_card[card_name]["illegal_event_count"] += illegal_count

    # Derived rates
    for summary in per_card.values():
        total_games = summary["total_games"]
        times_cast = summary["times_cast"]
        times_resolved = summary["times_resolved"]
        games_played_when_cast = summary["games_played_when_cast"]

        summary["cast_rate"] = safe_div(times_cast, total_games)
        summary["resolve_rate"] = safe_div(times_resolved, times_cast)
        summary["opening_hand_rate"] = safe_div(summary["times_in_opening_hand"], total_games)
        summary["avg_turn_cast"] = safe_div(summary["sum_turn_cast"], times_cast)
        summary["sim_presence_rate"] = safe_div(summary["times_seen_total"], total_games)
        summary["illegal_event_rate"] = safe_div(summary["illegal_event_count"], total_games)
        summary["win_rate_when_cast"] = safe_div(summary["games_won_when_cast"], games_played_when_cast)

    return dict(sorted(per_card.items(), key=lambda item: item[0]))


def write_json_summary(path: Path, summary: Dict[str, Dict[str, Any]]) -> None:
    ensure_parent_dir(path)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def write_csv_summary(path: Path, summary: Dict[str, Dict[str, Any]]) -> None:
    ensure_parent_dir(path)
    fieldnames = [
        "card_name",
        "total_games",
        "times_drawn",
        "times_in_opening_hand",
        "times_cast",
        "times_resolved",
        "times_countered",
        "times_fizzled",
        "times_entered_battlefield",
        "times_died",
        "times_moved_zones",
        "sum_turn_cast",
        "first_turn_cast_min",
        "games_won_when_cast",
        "games_played_when_cast",
        "times_seen_total",
        "illegal_event_count",
        "cast_rate",
        "resolve_rate",
        "opening_hand_rate",
        "avg_turn_cast",
        "sim_presence_rate",
        "illegal_event_rate",
        "win_rate_when_cast",
        "handler_source_used",
        "effect_family",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in summary.values():
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_parquet_summary(path: Path, summary: Dict[str, Dict[str, Any]]) -> bool:
    """
    Best effort parquet export without requiring pandas.

    Returns True on success, False if parquet libraries are unavailable.
    """
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except Exception:
        return False

    ensure_parent_dir(path)
    rows = list(summary.values())
    if not rows:
        table = pa.table({})
    else:
        columns = {}
        for key in rows[0].keys():
            columns[key] = [row.get(key) for row in rows]
        table = pa.table(columns)
    pq.write_table(table, path)
    return True


def main() -> None:
    rows = list(load_jsonl(RAW_PATH))
    summary = summarize_events(rows)

    write_json_summary(JSON_SUMMARY_PATH, summary)
    write_csv_summary(CSV_SUMMARY_PATH, summary)
    parquet_ok = write_parquet_summary(PARQUET_SUMMARY_PATH, summary)

    print(f"Read {len(rows)} telemetry events from {RAW_PATH}")
    print(f"Wrote {len(summary)} card summaries to {JSON_SUMMARY_PATH}")
    print(f"CSV written to {CSV_SUMMARY_PATH}")
    print(f"Parquet written: {'yes' if parquet_ok else 'no (pyarrow not installed)'}")


if __name__ == "__main__":
    main()
