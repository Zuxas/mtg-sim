"""
engine/game_events.py — Game event bus for adaptive APL

Provides a simple publish/subscribe system so the APL can observe
game events and update the opponent model in real time.

Events fired:
  - opponent_plays(card_name, turn)       → reduces P(card in hand)
  - opponent_taps_out(mana_used, turn)    → updates mana model
  - opponent_passes(mana_left, turn)      → signals held interaction
  - we_play_cavern(turn)                  → reduces FoW risk
  - opponent_hand_revealed(cards, turn)   → Thoughtseize/Gitaxian Probe

The APL subscribes to these events and updates OpponentHandModel,
which feeds into CFR decisions next turn.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class GameEvent:
    event_type: str
    turn:       int
    data:       dict = field(default_factory=dict)


class GameEventBus:
    """Lightweight event bus — publish events, subscribers update models."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: GameEvent):
        for handler in self._handlers.get(event.event_type, []):
            try:
                handler(event)
            except Exception:
                pass  # never crash the sim from an event handler

    def publish_opponent_play(self, card_name: str, turn: int):
        self.publish(GameEvent("opponent_plays", turn, {"card": card_name}))

    def publish_mana_state(self, mana_left: int, turn: int):
        self.publish(GameEvent("opponent_mana", turn, {"mana_left": mana_left}))

    def publish_hand_revealed(self, cards: list[str], turn: int):
        self.publish(GameEvent("hand_revealed", turn, {"cards": cards}))


# Global bus — shared between APL and game engine
_bus: Optional[GameEventBus] = None


def get_event_bus() -> GameEventBus:
    global _bus
    if _bus is None:
        _bus = GameEventBus()
    return _bus


def reset_event_bus():
    """Call at the start of each new game."""
    global _bus
    _bus = GameEventBus()
