"""Strixhaven Lessons — Paradigm mechanic cards

Three Lesson spells with Paradigm (cast once, then free copy each turn
from exile):

Echocasting Symposium {4}{U}{U} Sorcery — Lesson
  Create a token copy of target creature you control.
  Paradigm: exile after cast, then free copy each upkeep.

Improvisation Capstone {5}{R}{R} Sorcery — Lesson
  Exile top cards until MV total >= 4; cast any for free.
  Paradigm: exile after cast, then free copy each upkeep.

Restoration Seminar {5}{W}{W} Sorcery — Lesson
  Return target nonland permanent from GY to battlefield.
  Paradigm: exile after cast, then free copy each upkeep.

Decks: Izzet Cauldron (Capstone), Jeskai Control (Seminar), any spells deck.

Key decisions:
- Cast once at full cost to activate Paradigm.
- After that, free copy at the beginning of each main phase.
- Priority: Capstone is most relevant for Izzet (free spells = storm fuel).
- Restoration Seminar: use to recur Prismari/Silverquill from GY.
- Echocasting Symposium: duplicate your biggest threat.

Spec: apl/card_specs/strixhaven_lessons.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

ECHOCASTING = "Echocasting Symposium"
CAPSTONE    = "Improvisation Capstone"
SEMINAR     = "Restoration Seminar"
ALL_LESSONS = {ECHOCASTING, CAPSTONE, SEMINAR}


def cast_lesson(gs, lesson_name: str, opponent=None) -> bool:
    """Cast a Lesson spell from hand (first-time cast to activate Paradigm).

    Returns True if cast.
    """
    for c in list(gs.zones.hand):
        if c.name == lesson_name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            gs.cast_spell(c)
            gs._log(f"  Lesson: {lesson_name} cast (Paradigm activated)")
            _apply_lesson_effect(gs, lesson_name, opponent, is_paradigm_copy=False)
            return True
    return False


def fire_paradigm_copy(gs, lesson_name: str, opponent=None) -> bool:
    """Fire the free Paradigm copy at the beginning of main phase.

    Should be called each turn if the lesson has been previously cast.
    Returns True if the copy was fired.
    """
    # Check if lesson is in exile (Paradigm activated)
    lesson_in_exile = any(c.name == lesson_name for c in gs.zones.exile)
    if not lesson_in_exile:
        return False
    gs._log(f"  Paradigm copy: {lesson_name} (free)")
    _apply_lesson_effect(gs, lesson_name, opponent, is_paradigm_copy=True)
    return True


def _apply_lesson_effect(gs, lesson_name: str, opponent, is_paradigm_copy: bool):
    """Apply the spell effect of a lesson."""
    if lesson_name == CAPSTONE:
        # Exile top cards until MV total >= 4, cast for free
        total_mv = 0
        to_cast = []
        for c in list(gs.zones.library[:6]):  # check top 6
            cmc = getattr(c, 'cmc', 0)
            total_mv += cmc
            if not c.is_land():
                to_cast.append(c)
                gs.zones.library.remove(c)
                gs.zones.graveyard.append(c)
            if total_mv >= 4:
                break
        gs._log(f"  Capstone: exiled {len(to_cast)} cards (MV {total_mv}), "
                f"may cast for free")
        # Rough approximation: gain damage equal to total MV of cast spells
        if to_cast and opponent:
            gs.damage_dealt += sum(getattr(c, 'cmc', 0) for c in to_cast
                                   if not c.has(Tag.CREATURE))

    elif lesson_name == SEMINAR:
        # Return best nonland permanent from GY
        gy_permanents = [c for c in gs.zones.graveyard
                         if not c.is_land() and
                         (c.has(Tag.CREATURE) or c.has(Tag.ENCHANTMENT)
                          or c.has(Tag.ARTIFACT))]
        if gy_permanents:
            target = max(gy_permanents, key=lambda c: getattr(c, 'cmc', 0))
            gs.zones.graveyard.remove(target)
            gs.zones.battlefield.append(target)
            target.turn_entered = gs.turn
            target.summoning_sickness = True
            gs._log(f"  Seminar: return {target.name} from GY to battlefield")

    elif lesson_name == ECHOCASTING:
        # Create token copy of best creature we control
        creatures = [c for c in gs.zones.battlefield
                     if c.has(Tag.CREATURE) and not c.is_land()]
        if creatures:
            best = max(creatures, key=lambda c: safe_power(c))
            # Create a token copy
            from data.card import Card
            token = Card(best.name + " Token", best.mana_cost,
                         safe_power(best), best.type_line,
                         oracle_text=getattr(best, 'oracle_text', ''))
            token.power = str(safe_power(best))
            token.toughness = str(best.toughness)
            token.turn_entered = gs.turn
            token.summoning_sickness = True
            gs.zones.battlefield.append(token)
            gs._log(f"  Echocasting: token copy of {best.name}")


def has_paradigm_active(gs, lesson_name: str) -> bool:
    """Check if a lesson's Paradigm is active (lesson is in exile)."""
    return any(c.name == lesson_name for c in gs.zones.exile)
