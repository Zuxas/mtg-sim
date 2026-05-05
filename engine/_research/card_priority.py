"""
Scoring helpers for prioritizing MTG card handler work.

Design goals:
- shallow imports only
- runnable without loading the full engine
- tunable weights clearly marked

NOTE: Moved to engine/_research/ on 2026-04-27 -- this file is part of the
priority-queue research pipeline that was started but not yet wired into
the simulator. See engine/_research/README.md for status and revival path.
The file path data/priority_queue/severities.json referenced below is
relative to mtg-sim root, not the _research dir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

# -----------------------------------------------------------------------------
# Severity rubric
# -----------------------------------------------------------------------------
# tunable: adjust these defaults after the first queue run if the ranking feels off.

SEVERITY_LABELS: Dict[int, str] = {
    5: "core card currently noop or materially wrong",
    4: "common high-impact effect, parser likely wrong or partial",
    3: "meaningful support card, medium-frequency",
    2: "niche support or lower-frequency sideboard card",
    1: "corner-case, cosmetic, or low-impact rider",
}

# Severities are loaded from data/priority_queue/severities.json at import time.
# Runtime overrides via tag_severity() are also honored.
SEVERITIES_JSON_PATH = Path("data/priority_queue/severities.json")
HAND_TAGGED_SEVERITIES: Dict[str, int] = {}


def _load_severities_from_json() -> None:
    """Load persisted severity tags. Called at import and safe to re-run."""
    if not SEVERITIES_JSON_PATH.exists():
        return
    try:
        data = json.loads(SEVERITIES_JSON_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    for card_name, severity in data.items():
        try:
            severity_int = int(severity)
        except (TypeError, ValueError):
            continue
        if severity_int in SEVERITY_LABELS:
            HAND_TAGGED_SEVERITIES[str(card_name)] = severity_int


_load_severities_from_json()

DEFAULT_SEVERITY = 3  # tunable


def tag_severity(card_name: str, severity: int) -> None:
    """Register / override a hand-tagged severity score for a card."""
    if severity not in SEVERITY_LABELS:
        raise ValueError(f"Invalid severity {severity}; must be one of {sorted(SEVERITY_LABELS)}")
    HAND_TAGGED_SEVERITIES[card_name] = severity


def get_severity(card_name: str, fallback: Optional[int] = None) -> int:
    """Return the hand-tagged severity for a card, or a fallback/default."""
    if card_name in HAND_TAGGED_SEVERITIES:
        return HAND_TAGGED_SEVERITIES[card_name]
    return DEFAULT_SEVERITY if fallback is None else fallback


# -----------------------------------------------------------------------------
# Handler status scoring helpers
# -----------------------------------------------------------------------------

HANDLER_CONFIDENCE_PENALTY: Dict[str, float] = {
    "verified": 0.0,
    "partial": 0.5,
    "auto": 1.0,
    "noop": 1.0,
    "missing": 1.0,
    "fallback": 1.0,
    "unknown": 0.7,
}

KNOWN_BAD_STATUSES = {"noop", "missing", "auto", "fallback", "partial"}


@dataclass
class CardStats:
    """Static + aggregated telemetry fields used for prioritization."""

    card_name: str
    effect_family: str = ""
    handler_status: str = "unknown"

    # Static card/deck presence fields
    copies_total: int = 0
    decks_present_in: int = 0
    meta_share_sum: float = 0.0
    meta_share_weighted_copies: float = 0.0

    # Hand tagging / rubric
    effect_severity: int = DEFAULT_SEVERITY
    complexity_penalty: float = 0.0

    # Optional freeform notes
    notes: str = ""

    # Aggregated telemetry fields
    total_games: int = 0
    times_drawn: int = 0
    times_in_opening_hand: int = 0
    times_cast: int = 0
    times_resolved: int = 0
    times_countered: int = 0
    times_fizzled: int = 0
    times_entered_battlefield: int = 0
    times_died: int = 0
    times_moved_zones: int = 0
    sum_turn_cast: int = 0
    first_turn_cast_min: Optional[int] = None
    games_won_when_cast: int = 0
    games_played_when_cast: int = 0
    times_seen_total: int = 0
    illegal_event_count: int = 0

    # Derived / cacheable fields
    priority_score: float = 0.0
    score_mode: str = "bootstrap"
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def cast_rate(self) -> float:
        return safe_div(self.times_cast, self.total_games)

    @property
    def resolve_rate(self) -> float:
        return safe_div(self.times_resolved, self.times_cast)

    @property
    def opening_hand_rate(self) -> float:
        return safe_div(self.times_in_opening_hand, self.total_games)

    @property
    def avg_turn_cast(self) -> float:
        return safe_div(self.sum_turn_cast, self.times_cast)

    @property
    def sim_presence_rate(self) -> float:
        return safe_div(self.times_seen_total, self.total_games)

    @property
    def illegal_event_rate(self) -> float:
        return safe_div(self.illegal_event_count, self.total_games)

    @property
    def win_rate_when_cast(self) -> float:
        return safe_div(self.games_won_when_cast, self.games_played_when_cast)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["cast_rate"] = self.cast_rate
        data["resolve_rate"] = self.resolve_rate
        data["opening_hand_rate"] = self.opening_hand_rate
        data["avg_turn_cast"] = self.avg_turn_cast
        data["sim_presence_rate"] = self.sim_presence_rate
        data["illegal_event_rate"] = self.illegal_event_rate
        data["win_rate_when_cast"] = self.win_rate_when_cast
        data["severity_label"] = SEVERITY_LABELS.get(self.effect_severity, "unknown")
        return data


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def clamp01(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def normalize_value(value: float, min_value: float, max_value: float) -> float:
    """Min-max normalize a single value into [0, 1]."""
    if max_value <= min_value:
        return 0.0
    return clamp01((value - min_value) / (max_value - min_value))


def normalize_dict(values: Mapping[str, float]) -> Dict[str, float]:
    """Min-max normalize a dict of named numeric values into [0, 1]."""
    if not values:
        return {}
    min_value = min(values.values())
    max_value = max(values.values())
    return {key: normalize_value(val, min_value, max_value) for key, val in values.items()}


def apply_hand_tagged_severity(stats: CardStats) -> CardStats:
    stats.effect_severity = get_severity(stats.card_name, stats.effect_severity)
    return stats


def confidence_penalty_for_status(handler_status: str) -> float:
    return HANDLER_CONFIDENCE_PENALTY.get(handler_status, HANDLER_CONFIDENCE_PENALTY["unknown"])


def bootstrap_score(card_stats: CardStats, normalized_fields: Optional[Mapping[str, float]] = None) -> float:
    """
    Static prior used before telemetry exists.

    Formula from plan:
        0.55 * normalized(meta_share_weighted_copies)
      + 0.25 * normalized(meta_share_sum)
      + 0.20 * normalized(effect_severity)
      - 0.10 * normalized(complexity_penalty)
    """
    card_stats = apply_hand_tagged_severity(card_stats)
    nf = normalized_fields or {}

    meta_weighted = nf.get("meta_share_weighted_copies", card_stats.meta_share_weighted_copies)
    meta_sum = nf.get("meta_share_sum", card_stats.meta_share_sum)
    severity = nf.get("effect_severity", float(card_stats.effect_severity))
    complexity = nf.get("complexity_penalty", card_stats.complexity_penalty)

    # tunable: weights
    score = (
        0.55 * meta_weighted
        + 0.25 * meta_sum
        + 0.20 * severity
        - 0.10 * complexity
    )
    return float(score)


def compute_win_impact_proxy(card_stats: CardStats, global_deck_win_rate: float = 0.5) -> float:
    """
    Stability-biased proxy rather than noisy raw WR swing.
    """
    sample_weight = min(1.0, safe_div(card_stats.games_played_when_cast, 50))
    return sample_weight * abs(card_stats.win_rate_when_cast - global_deck_win_rate)


def full_score(
    card_stats: CardStats,
    normalized_fields: Optional[Mapping[str, float]] = None,
    *,
    global_deck_win_rate: float = 0.5,
) -> float:
    """
    Telemetry-aware full scoring formula.

    Formula from plan:
        0.30 * normalized(meta_share_weighted_copies)
      + 0.20 * normalized(cast_rate)
      + 0.10 * normalized(resolve_rate)
      + 0.10 * normalized(opening_hand_rate)
      + 0.20 * normalized(effect_severity)
      + 0.10 * normalized(win_impact_proxy)
      - 0.08 * normalized(complexity_penalty)
      - 0.07 * normalized(confidence_penalty)
    """
    card_stats = apply_hand_tagged_severity(card_stats)
    nf = normalized_fields or {}

    win_impact_proxy = compute_win_impact_proxy(card_stats, global_deck_win_rate=global_deck_win_rate)

    meta_weighted = nf.get("meta_share_weighted_copies", card_stats.meta_share_weighted_copies)
    cast_rate = nf.get("cast_rate", card_stats.cast_rate)
    resolve_rate = nf.get("resolve_rate", card_stats.resolve_rate)
    opening_hand_rate = nf.get("opening_hand_rate", card_stats.opening_hand_rate)
    severity = nf.get("effect_severity", float(card_stats.effect_severity))
    complexity = nf.get("complexity_penalty", card_stats.complexity_penalty)
    confidence_penalty = nf.get(
        "confidence_penalty",
        confidence_penalty_for_status(card_stats.handler_status),
    )
    win_impact = nf.get("win_impact_proxy", win_impact_proxy)

    # tunable: weights
    score = (
        0.30 * meta_weighted
        + 0.20 * cast_rate
        + 0.10 * resolve_rate
        + 0.10 * opening_hand_rate
        + 0.20 * severity
        + 0.10 * win_impact
        - 0.08 * complexity
        - 0.07 * confidence_penalty
    )
    return float(score)


def build_normalized_field_maps(cards: Mapping[str, CardStats], *, global_deck_win_rate: float = 0.5) -> Dict[str, Dict[str, float]]:
    """
    Build min-max normalized field maps keyed by field name, then by card name.

    This keeps the scoring functions simple and side-effect-free.
    """
    if not cards:
        return {}

    fields: Dict[str, Dict[str, float]] = {
        "meta_share_weighted_copies": {},
        "meta_share_sum": {},
        "effect_severity": {},
        "complexity_penalty": {},
        "cast_rate": {},
        "resolve_rate": {},
        "opening_hand_rate": {},
        "win_impact_proxy": {},
        "confidence_penalty": {},
    }

    for card_name, stats in cards.items():
        stats = apply_hand_tagged_severity(stats)
        fields["meta_share_weighted_copies"][card_name] = stats.meta_share_weighted_copies
        fields["meta_share_sum"][card_name] = stats.meta_share_sum
        fields["effect_severity"][card_name] = float(stats.effect_severity)
        fields["complexity_penalty"][card_name] = stats.complexity_penalty
        fields["cast_rate"][card_name] = stats.cast_rate
        fields["resolve_rate"][card_name] = stats.resolve_rate
        fields["opening_hand_rate"][card_name] = stats.opening_hand_rate
        fields["win_impact_proxy"][card_name] = compute_win_impact_proxy(stats, global_deck_win_rate=global_deck_win_rate)
        fields["confidence_penalty"][card_name] = confidence_penalty_for_status(stats.handler_status)

    return {field_name: normalize_dict(values) for field_name, values in fields.items()}


def score_cards(
    cards: Mapping[str, CardStats],
    *,
    use_telemetry: bool,
    global_deck_win_rate: float = 0.5,
) -> Dict[str, CardStats]:
    """
    Score a set of CardStats and return updated copies with priority_score populated.
    """
    normalized = build_normalized_field_maps(cards, global_deck_win_rate=global_deck_win_rate)
    scored: Dict[str, CardStats] = {}

    for card_name, stats in cards.items():
        per_card_normalized = {field_name: values.get(card_name, 0.0) for field_name, values in normalized.items()}
        if use_telemetry:
            stats.priority_score = full_score(stats, per_card_normalized, global_deck_win_rate=global_deck_win_rate)
            stats.score_mode = "full"
        else:
            stats.priority_score = bootstrap_score(stats, per_card_normalized)
            stats.score_mode = "bootstrap"
        scored[card_name] = stats

    return scored
