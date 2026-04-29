"""Serra Paragon — {2}{W}{W} 3/4 Creature — Angel

Oracle:
  Flying
  Once during each of your turns, you may play a land from your graveyard
  or cast a permanent spell with mana value 3 or less from your graveyard
  without paying its mana cost. If a permanent you cast this way would be
  put into your graveyard, exile it instead.

Decks: Jeskai Control, Azorius Control, any white-based control.

Key decisions:
- Cast T4 (2WW). 3/4 flying is solid.
- Once per turn: replay a land OR cast any permanent CMC ≤ 3 from GY free.
  Best targets: Teferi (CMC 3), Brazen Borrower (CMC 3), removal enchantments,
  any 1-2 drop that died.
- Targets go to exile if they would die again (not permanent recursion,
  but still one free cast per permanent).
- With Ral's −2: recur Serra Paragon if it dies, then it recurses others.
- Lands from GY: useful if you've been milling/cycling.
- Priority: CMC 3 permanents > CMC 2 > CMC 1 > lands (usually).

Spec: apl/card_specs/serra_paragon.py
"""
from __future__ import annotations
from data.card import Tag

NAME = "Serra Paragon"
CMC = 4   # {2}{W}{W}
MAX_RECUR_CMC = 3


def cast(gs, opponent=None) -> bool:
    """Cast Serra Paragon T4. Immediately enables GY recursion.

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == NAME and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Serra Paragon: 3/4 flying, once/turn cast CMC<=3 perm from GY free")
            return True
    return False


def is_active(gs) -> bool:
    """True if Serra Paragon is on the battlefield."""
    return any(c.name == NAME for c in gs.zones.battlefield)


def use_recursion(gs, opponent=None) -> bool:
    """Once per turn: cast the best CMC<=3 permanent from GY for free.

    Returns True if a permanent was recast.
    """
    if not is_active(gs):
        return False
    if getattr(gs, '_serra_used_this_turn', False):
        return False

    # Find best CMC<=3 permanent in GY (not land)
    targets = [c for c in gs.zones.graveyard
               if not c.is_land()
               and getattr(c, 'cmc', 0) <= MAX_RECUR_CMC
               and (c.has(Tag.CREATURE) or c.has(Tag.ENCHANTMENT)
                    or c.has(Tag.ARTIFACT))]

    if not targets:
        # Try land from GY
        lands = [c for c in gs.zones.graveyard if c.is_land()]
        if lands and not gs.land_played:
            land = lands[0]
            gs.zones.graveyard.remove(land)
            gs.zones.battlefield.append(land)
            gs._serra_used_this_turn = True
            gs._log(f"  Serra Paragon: replay {land.name} from GY")
            return True
        return False

    # Pick highest CMC target (most value)
    target = max(targets, key=lambda c: getattr(c, 'cmc', 0))
    gs.zones.graveyard.remove(target)
    gs.zones.battlefield.append(target)
    target.turn_entered = gs.turn
    target.summoning_sickness = True
    # If it would die again, it goes to exile instead (track with flag)
    target._serra_recast = True
    gs._serra_used_this_turn = True
    gs._log(f"  Serra Paragon: free cast {target.name} (CMC {getattr(target,'cmc',0)}) "
            f"from GY (exile on death)")
    return True


def reset_turn_flag(gs) -> None:
    """Reset per-turn recursion flag at start of turn."""
    gs._serra_used_this_turn = False
