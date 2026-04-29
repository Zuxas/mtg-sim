"""Veyran, Voice of Duality — {1}{U}{R} 2/2 Legendary Creature — Efreet Wizard

Oracle:
  Magecraft — Whenever you cast or copy an instant or sorcery spell,
  Veyran gets +1/+1 until end of turn.
  If you casting or copying an instant or sorcery spell causes a triggered
  ability of a permanent you control to trigger, that ability triggers an
  additional time.

Decks: Izzet Cauldron, Standard Izzet spells.

Key decisions:
- Cast T3 (1UR). 2/2 body, but grows fast with spells.
- Magecraft: +1/+1 per spell/copy = can become a large attacker.
  With 3 spells cast: 5/5. With 5 spells: 7/7.
- Doubling triggered abilities: CRITICAL with Prismari (storm doubles),
  Rootha (creates 2 tokens per trigger), Emeritus (2x prepared triggers)
- Sequencing: cast Veyran BEFORE other spell-enablers to maximize doubling
  e.g. T3: Veyran. T4: Silverquill. T5: cast spells, all casualty copies
  trigger Veyran, PLUS Silverquill triggers fire twice.
- Combat: attack when Veyran is pumped 4+ from prior spells this turn.

Spec: apl/card_specs/veyran.py
"""
from __future__ import annotations
from engine.match_state import safe_power, safe_toughness

NAME = "Veyran, Voice of Duality"
CMC = 3  # {1}{U}{R}
BASE_POWER = 2
BASE_TOUGHNESS = 2


def cast(gs, opponent=None) -> bool:
    """Cast Veyran early — maximizes doubling window.

    Ideal T3. Before Prismari (T6), Rootha (T4), Silverquill (T4).
    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Veyran: 2/2, magecraft +1/+1 per spell, doubles triggered abilities")
            return True
    return False


def is_active(gs) -> bool:
    """True if Veyran is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield if not c.is_land())


def apply_magecraft(gs) -> None:
    """Give Veyran +1/+1 until end of turn when a spell is cast/copied.

    Call whenever an instant/sorcery is cast or copied while Veyran is out.
    Also doubles triggered abilities — tracked separately by the APL.
    """
    for c in gs.zones.battlefield:
        if c.name == NAME:
            c.counters = getattr(c, 'counters', 0) + 1
            gs._log(f"  Veyran magecraft: +1/+1 (now {BASE_POWER + c.counters}/"
                    f"{BASE_TOUGHNESS + c.counters})")
            return


def current_power(gs) -> int:
    """Current power of Veyran (base + magecraft counters)."""
    for c in gs.zones.battlefield:
        if c.name == NAME:
            return BASE_POWER + getattr(c, 'counters', 0)
    return 0


def doubles_triggers(gs) -> bool:
    """True if Veyran is active — triggered abilities fire twice.

    APL should check this and fire relevant triggers twice when True.
    Affected: Prismari storm, Rootha combat, Silverquill casualty,
    Emeritus prepared, any magecraft trigger.
    """
    return is_active(gs)
