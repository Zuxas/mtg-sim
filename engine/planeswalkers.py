"""engine/planeswalkers.py -- Planeswalker loyalty + ability dispatch.

Stage 3 of the T1.3+T1.4 transform infrastructure arc (2026-04-26).

Planeswalkers in mtg-sim are represented as Card objects with a
loyalty: int field (added Stage 1, defaults from card_db). Their
activated abilities are dispatched via the PLANESWALKER_ABILITIES
registry below: card_name -> {loyalty_change: handler}. Each
handler is (card, gs) -> None and applies the ability's *effect*;
the loyalty change itself (the cost) is applied by
activate_planeswalker_ability before calling the handler.

Per-turn budget per CR 606.3 (one loyalty ability per planeswalker
per turn) is tracked on the GameState via gs._pw_activated_this_turn:
set[str] of card names. Lazy reset on first activation each turn
detects gs.turn change and clears the set -- this avoids the need
to wire a hook into engine/game_state.py's next_turn() method, which
matters for keeping module-extension changes (this file) decoupled
from the load-bearing engine state machine.

Stage 3 deliverable: dispatch infrastructure only. PLANESWALKER_ABILITIES
is empty in this commit; Stage 5 fills it with Ajani Avenger handlers
when the front-face Cat-die transform consumer lands.

Death by 0 loyalty: state-based action per CR 704.5i. Implemented as
inline check after handler fires (the handler may itself reduce
loyalty, e.g. via the conditional-bolt 0-ability that pings face for
N damage but doesn't change loyalty further -- here we only check the
ability's own loyalty cost, which is the change parameter).
"""
from typing import Callable


# ── Registry ────────────────────────────────────────────────────────
#
# Keyed by the planeswalker's actual card name (post-transform name
# for DFC PWs like Ajani Avenger). Inner dict is keyed by loyalty
# change (positive for +N, 0 for the 0 ability, negative for -N).
# Handlers receive (card, gs) and apply the ability's effect; loyalty
# adjustment is handled by activate_planeswalker_ability around the
# handler call.

PLANESWALKER_ABILITIES: dict[str, dict[int, Callable]] = {
    # Stage 5 will register: "Ajani, Nacatl Avenger": {2: ..., 0: ..., -4: ...}
}


def activate_planeswalker_ability(card, gs, change: int) -> bool:
    """Activate a +N / 0 / -N loyalty ability on a planeswalker.

    Per CR 606.3: a player may activate a loyalty ability of a
    planeswalker they control as a sorcery, only if no loyalty ability
    of that planeswalker has been activated this turn. Per CR 704.5i:
    if a planeswalker has 0 or less loyalty, it's put into its owner's
    graveyard as a state-based action.

    Args:
      card: the planeswalker (must be on battlefield)
      gs: GameState
      change: loyalty cost as a signed integer
                +N adds N counters
                0  no change
                -N removes N counters

    Returns:
      True if the ability fired (loyalty changed, handler called).
      False if rejected (no handler registered, already activated this
      turn, or card not in PLANESWALKER_ABILITIES at all).

    Side effects on success:
      - card.loyalty += change
      - gs._pw_activated_this_turn.add(card.name)
      - handler(card, gs) called
      - If card.loyalty <= 0 after the change, the card moves to
        graveyard.
    """
    # Lazy per-turn reset: detect turn-number change since last call.
    # This avoids wiring a hook into engine/game_state.py.
    last_turn = getattr(gs, "_pw_activation_turn", -1)
    if gs.turn != last_turn:
        gs._pw_activation_turn = gs.turn
        gs._pw_activated_this_turn = set()

    # Per-turn budget: one loyalty ability per PW per turn.
    if card.name in gs._pw_activated_this_turn:
        return False

    # Look up handler by card name + loyalty change.
    abilities = PLANESWALKER_ABILITIES.get(card.name, {})
    handler = abilities.get(change)
    if handler is None:
        return False

    # Apply loyalty change (the "cost") BEFORE handler resolution
    # per CR 606.3 -- the cost is paid as the ability is announced;
    # the effect resolves afterward.
    card.loyalty += change
    gs._pw_activated_this_turn.add(card.name)

    # Fire the effect.
    try:
        handler(card, gs)
    except Exception as e:
        gs._log(f"  PW {card.name} ability {change:+d} error: {e}")

    # State-based action: loyalty <= 0 -> graveyard.
    if card.loyalty <= 0 and card in gs.zones.battlefield:
        gs.zones.battlefield.remove(card)
        gs.zones.graveyard.append(card)
        gs._log(f"  {card.name} loyalty 0, sent to graveyard")

    return True
