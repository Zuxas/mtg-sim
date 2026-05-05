"""
Lightweight append-only telemetry logger.

Design goals:
- shallow imports only
- cheap event writes to JSONL
- no buffering complexity

NOTE: Moved to engine/_research/ on 2026-04-27 -- this file is part of the
priority-queue research pipeline that was started but not yet wired into
the simulator. See engine/_research/README.md for status and revival path.
The DEFAULT_TELEMETRY_PATH below is relative to mtg-sim root, not _research.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_TELEMETRY_PATH = Path("data/telemetry/raw_games.jsonl")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class TelemetryEvent:
    event_type: str
    timestamp_utc: str
    run_id: str
    match_id: str
    game_id: str
    deck_id: str
    opponent_deck_id: str
    card_name: str = ""
    payload: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data["payload"] is None:
            data["payload"] = {}
        return data


class TelemetryCollector:
    """
    Append-only JSONL event writer.

    You can call these methods directly from the sim loop / resolver layer:
    - record_draw(...)
    - record_cast(...)
    - record_resolve(...)
    - record_zone_transition(...)
    - record_game_end(...)
    """

    def __init__(self, output_path: os.PathLike[str] | str = DEFAULT_TELEMETRY_PATH) -> None:
        self.output_path = Path(output_path)
        ensure_parent_dir(self.output_path)

    def _append_event(
        self,
        *,
        event_type: str,
        run_id: str,
        match_id: str,
        game_id: str,
        deck_id: str,
        opponent_deck_id: str,
        card_name: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = TelemetryEvent(
            event_type=event_type,
            timestamp_utc=utc_now_iso(),
            run_id=run_id,
            match_id=match_id,
            game_id=game_id,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            card_name=card_name,
            payload=payload or {},
        )
        with self.output_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_dict(), sort_keys=True))
            handle.write("\n")

    def record_draw(
        self,
        *,
        run_id: str,
        match_id: str,
        game_id: str,
        deck_id: str,
        opponent_deck_id: str,
        card_name: str,
        turn_number: int,
        opening_hand: bool = False,
        handler_source_used: str = "",
        effect_family: str = "",
    ) -> None:
        self._append_event(
            event_type="draw",
            run_id=run_id,
            match_id=match_id,
            game_id=game_id,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            card_name=card_name,
            payload={
                "turn_number": turn_number,
                "opening_hand": opening_hand,
                "handler_source_used": handler_source_used,
                "effect_family": effect_family,
            },
        )

    def record_cast(
        self,
        *,
        run_id: str,
        match_id: str,
        game_id: str,
        deck_id: str,
        opponent_deck_id: str,
        card_name: str,
        turn_number: int,
        mana_spent: Optional[int] = None,
        legal_cast: bool = True,
        handler_source_used: str = "",
        effect_family: str = "",
    ) -> None:
        self._append_event(
            event_type="cast",
            run_id=run_id,
            match_id=match_id,
            game_id=game_id,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            card_name=card_name,
            payload={
                "turn_number": turn_number,
                "mana_spent": mana_spent,
                "legal_cast": legal_cast,
                "handler_source_used": handler_source_used,
                "effect_family": effect_family,
            },
        )

    def record_resolve(
        self,
        *,
        run_id: str,
        match_id: str,
        game_id: str,
        deck_id: str,
        opponent_deck_id: str,
        card_name: str,
        turn_number: int,
        resolved: bool,
        countered: bool = False,
        fizzled: bool = False,
        targets_selected: int = 0,
        effect_executed: bool = False,
        handler_source_used: str = "",
        effect_family: str = "",
    ) -> None:
        self._append_event(
            event_type="resolve",
            run_id=run_id,
            match_id=match_id,
            game_id=game_id,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            card_name=card_name,
            payload={
                "turn_number": turn_number,
                "resolved": resolved,
                "countered": countered,
                "fizzled": fizzled,
                "targets_selected": targets_selected,
                "effect_executed": effect_executed,
                "handler_source_used": handler_source_used,
                "effect_family": effect_family,
            },
        )

    def record_zone_transition(
        self,
        *,
        run_id: str,
        match_id: str,
        game_id: str,
        deck_id: str,
        opponent_deck_id: str,
        card_name: str,
        from_zone: str,
        to_zone: str,
        reason: str = "",
        turn_number: Optional[int] = None,
        entered_battlefield: bool = False,
        died: bool = False,
        handler_source_used: str = "",
        effect_family: str = "",
    ) -> None:
        self._append_event(
            event_type="zone_transition",
            run_id=run_id,
            match_id=match_id,
            game_id=game_id,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            card_name=card_name,
            payload={
                "from_zone": from_zone,
                "to_zone": to_zone,
                "reason": reason,
                "turn_number": turn_number,
                "entered_battlefield": entered_battlefield,
                "died": died,
                "handler_source_used": handler_source_used,
                "effect_family": effect_family,
            },
        )

    def record_game_end(
        self,
        *,
        run_id: str,
        match_id: str,
        game_id: str,
        deck_id: str,
        opponent_deck_id: str,
        won: bool,
        turns_in_game: int,
        end_reason: str,
        final_life_total: Optional[int] = None,
        opponent_final_life_total: Optional[int] = None,
        illegal_event_count: int = 0,
    ) -> None:
        self._append_event(
            event_type="game_end",
            run_id=run_id,
            match_id=match_id,
            game_id=game_id,
            deck_id=deck_id,
            opponent_deck_id=opponent_deck_id,
            payload={
                "won": won,
                "turns_in_game": turns_in_game,
                "end_reason": end_reason,
                "final_life_total": final_life_total,
                "opponent_final_life_total": opponent_final_life_total,
                "illegal_event_count": illegal_event_count,
            },
        )
