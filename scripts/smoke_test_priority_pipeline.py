#!/usr/bin/env python3
"""
Smoke test for the priority-queue/telemetry pipeline.

Writes a dozen fake telemetry events covering one game where:
  - Cut Down is drawn in the opener, cast T2, resolves, kills a creature
  - Lightning Strike is drawn T3, cast T3, resolves
  - Sunfall is drawn T5, cast T6, countered

Then verifies summarize_telemetry and build_priority_queue produce
well-shaped output.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from engine.card_telemetry import TelemetryCollector


def emit_fake_events() -> None:
    raw_path = Path("data/telemetry/raw_games.jsonl")
    # Reset so the smoke-test output is deterministic.
    if raw_path.exists():
        raw_path.unlink()

    collector = TelemetryCollector()
    common = dict(
        run_id="smoke-run-1",
        match_id="smoke-match-1",
        game_id="smoke-game-1",
        deck_id="dimir_midrange",
        opponent_deck_id="boros_aggro",
    )

    # Opener: Cut Down in hand, Lightning Strike and Sunfall in library.
    collector.record_draw(card_name="Cut Down",  turn_number=0, opening_hand=True,  effect_family="single_target_removal", **common)
    collector.record_draw(card_name="Lightning Strike", turn_number=3, opening_hand=False, effect_family="burn_and_drain",      **common)
    collector.record_draw(card_name="Sunfall",   turn_number=5, opening_hand=False, effect_family="sweeper_removal",         **common)

    # Cast / resolve lanes
    collector.record_cast(card_name="Cut Down", turn_number=2, mana_spent=1, legal_cast=True, effect_family="single_target_removal", **common)
    collector.record_resolve(card_name="Cut Down", turn_number=2, resolved=True, targets_selected=1, effect_executed=True, effect_family="single_target_removal", **common)
    collector.record_zone_transition(card_name="Heartfire Hero", from_zone="battlefield", to_zone="graveyard",
                                     reason="Cut Down kill", turn_number=2, died=True, **common)

    collector.record_cast(card_name="Lightning Strike", turn_number=3, mana_spent=2, legal_cast=True, effect_family="burn_and_drain", **common)
    collector.record_resolve(card_name="Lightning Strike", turn_number=3, resolved=True, targets_selected=1, effect_executed=True, effect_family="burn_and_drain", **common)

    collector.record_cast(card_name="Sunfall", turn_number=6, mana_spent=6, legal_cast=True, effect_family="sweeper_removal", **common)
    collector.record_resolve(card_name="Sunfall", turn_number=6, resolved=False, countered=True, effect_family="sweeper_removal", **common)

    # Game end: we won.
    collector.record_game_end(won=True, turns_in_game=9, end_reason="opponent at 0", final_life_total=12,
                              opponent_final_life_total=0, illegal_event_count=0, **common)

    print(f"Emitted fake events to {raw_path}")


def run_script(script_name: str) -> None:
    script_path = REPO_ROOT / "scripts" / script_name
    print(f"\n--- running {script_name} ---")
    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    print(result.stdout.strip() or "(no stdout)")
    if result.returncode != 0:
        print(f"STDERR:\n{result.stderr}")
        sys.exit(result.returncode)


def verify_shape() -> None:
    summary_path = Path("data/telemetry/card_summary_latest.json")
    queue_path = Path("data/priority_queue/standard_matrix_queue.json")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))

    assert isinstance(summary, dict),  f"summary must be dict, got {type(summary)}"
    assert isinstance(queue, list),    f"queue must be list, got {type(queue)}"
    assert len(queue) > 0, "queue is empty — no standard decklists parsed?"

    # Each of our 3 cast cards should appear in the summary with times_cast >= 1.
    for name in ("Cut Down", "Lightning Strike", "Sunfall"):
        assert name in summary, f"{name} missing from summary"
        row = summary[name]
        assert row["times_cast"] >= 1, f"{name} times_cast should be >= 1"

    # Queue row sanity: top entry must have the score_mode flipped to full (telemetry present).
    top = queue[0]
    required_fields = {"card_name", "priority_score", "score_mode",
                       "cast_rate", "resolve_rate", "opening_hand_rate",
                       "handler_status", "effect_family"}
    missing = required_fields - set(top.keys())
    assert not missing, f"top queue row missing fields: {missing}"
    assert top["score_mode"] == "full", f"expected score_mode=full after telemetry, got {top['score_mode']}"

    print("\n--- TOP 10 QUEUE ROWS ---")
    print(f"{'#':>3}  {'score':>7}  {'mode':<9}  {'status':<10}  card")
    for i, row in enumerate(queue[:10], 1):
        print(f"{i:>3}  {row['priority_score']:>7.4f}  {row['score_mode']:<9}  {row['handler_status']:<10}  {row['card_name']}")

    cut_down = summary.get("Cut Down", {})
    print("\n--- CUT DOWN SUMMARY ---")
    for k in ("total_games", "times_cast", "times_resolved", "cast_rate",
              "resolve_rate", "opening_hand_rate", "games_won_when_cast"):
        print(f"  {k}: {cut_down.get(k)}")

    print(f"\nQueue size: {len(queue)} cards")
    print(f"Cards with telemetry: {sum(1 for r in queue if r['total_games'] > 0)}")
    print("\nSMOKE TEST PASSED")


def main() -> None:
    emit_fake_events()
    run_script("summarize_telemetry.py")
    run_script("build_priority_queue.py")
    verify_shape()


if __name__ == "__main__":
    main()
