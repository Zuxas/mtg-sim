"""Strixhaven Support Cards — 7 remaining specs

Zimone, Infinite Analyst {1}{G}{U} 0/4
  First X-spell each turn costs {1} less per +1/+1 counter on Zimone.
  Whenever you cast an X-spell, put that many +1/+1 counters on Zimone.

Zimone, All-Questioning {1}{G}{U} 1/1
  End step: if a land ETB under your control this turn and you control a
  planeswalker, draw a card then discard a card.

Nev, the Practical Dean {2}{G} 2/2
  Creatures you control with counters have trample.
  Whenever you cast your first X-spell each turn, put X +1/+1 counters
  on target creature. (Increment mechanic)

Striding Shotcaller {G}{U} 0/4
  Reach. Whenever creatures you control deal combat damage to a player,
  this becomes prepared. (While prepared, cast a copy of its spell —
  back face likely a {G}{U} counterspell or instant.)

Advanced Reconstruction {3}{R} Enchantment — Class
  Level 1: Beginning of first main phase, mill a card, then may cast it.
  Level 2: Spells cost {1} less.
  Level 3: When you cast a spell from GY, return it to hand.

Professor Dellian Fel {2}{B}{G} Planeswalker (starts at 4)
  +2: Gain 3 life.
  0: Draw a card, lose 1 life.
  -3: Destroy target creature.
  -6: Emblem "whenever you gain life, create 1/1 token for each life gained".

Mangara, the Diplomat {3}{W} 2/4
  Lifelink. Whenever opp attacks with 2+ creatures, draw a card.
  Whenever opp casts their second spell each turn, draw a card.

Decks: Simic Ouroboroid (Zimones, Ozolith, Nev), Jeskai Control (Dellian),
       various control (Mangara, Advanced Reconstruction).

Spec: apl/card_specs/strixhaven_support.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

ZIMONE_ANALYST     = "Zimone, Infinite Analyst"
ZIMONE_QUESTIONING = "Zimone, All-Questioning"
NEV                = "Nev, the Practical Dean"
STRIDING           = "Striding Shotcaller"
ADV_RECONSTRUCTION = "Advanced Reconstruction"
PROF_DELLIAN       = "Professor Dellian Fel"
MANGARA            = "Mangara, the Diplomat"

ALL_NAMES = {ZIMONE_ANALYST, ZIMONE_QUESTIONING, NEV, STRIDING,
             ADV_RECONSTRUCTION, PROF_DELLIAN, MANGARA}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def _on_resolve(gs, name: str, card, opponent):
    if name == ZIMONE_ANALYST:
        gs._log(f"  Zimone Infinite Analyst: 0/4, X-spells cheaper per counter, "
                f"X-spells add X counters")

    elif name == ZIMONE_QUESTIONING:
        gs._log(f"  Zimone All-Questioning: 1/1, end step land+PW = draw/discard")

    elif name == NEV:
        # Grant trample to all creatures with counters
        from engine.keywords import KWTag
        for cr in gs.zones.battlefield:
            if cr.has(Tag.CREATURE) and not cr.is_land() and getattr(cr,'counters',0) > 0:
                cr.tags.add(KWTag.TRAMPLE)
        gs._log(f"  Nev, the Practical Dean: 2/2, countered creatures have trample")

    elif name == STRIDING:
        gs._log(f"  Striding Shotcaller: 0/4 reach, becomes prepared on combat damage")

    elif name == ADV_RECONSTRUCTION:
        gs._log(f"  Advanced Reconstruction: Class - mill+cast, cost reduction, GY recursion")

    elif name == PROF_DELLIAN:
        card.counters = 4  # starting loyalty
        gs._log(f"  Professor Dellian Fel: PW 4 loyalty, +2 gainlife, 0 draw/lose1, "
                f"-3 destroy creature, -6 token emblem")

    elif name == MANGARA:
        gs._log(f"  Mangara, the Diplomat: 2/4 lifelink, draws when opp attacks 2+ "
                f"or casts 2nd spell")


# === Zimone, Infinite Analyst helpers ===

def zimone_analyst_x_cost_reduction(gs, base_x_cost: int) -> int:
    """Return reduced X cost for first X-spell this turn."""
    zimone = next((c for c in gs.zones.battlefield if c.name == ZIMONE_ANALYST), None)
    if not zimone:
        return base_x_cost
    if getattr(gs, '_zimone_x_used', False):
        return base_x_cost  # only once per turn
    counters = getattr(zimone, 'counters', 0)
    return max(0, base_x_cost - counters)


def zimone_analyst_x_trigger(gs, x_value: int) -> None:
    """When you cast an X-spell, put X +1/+1 counters on Zimone."""
    zimone = next((c for c in gs.zones.battlefield if c.name == ZIMONE_ANALYST), None)
    if not zimone:
        return
    zimone.counters = getattr(zimone, 'counters', 0) + x_value
    zimone.toughness = str(4 + zimone.counters)
    gs._zimone_x_used = True
    gs._log(f"  Zimone Analyst: +{x_value} counters, now 0/{zimone.toughness}")


def zimone_reset_turn(gs) -> None:
    gs._zimone_x_used = False


# === Nev, the Practical Dean helpers ===

def nev_apply_trample(gs) -> None:
    """Apply trample to all creatures with counters (passive)."""
    from engine.keywords import KWTag
    for cr in gs.zones.battlefield:
        if cr.has(Tag.CREATURE) and not cr.is_land():
            if getattr(cr, 'counters', 0) > 0:
                cr.tags.add(KWTag.TRAMPLE)
            else:
                cr.tags.discard(KWTag.TRAMPLE)


def nev_increment_trigger(gs, x_value: int, target=None) -> None:
    """Whenever you cast first X-spell each turn, put X counters on target."""
    if target is None:
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if not critters:
            return
        target = max(critters, key=lambda c: safe_power(c))
    target.counters = getattr(target, 'counters', 0) + x_value
    nev_apply_trample(gs)
    gs._log(f"  Nev Increment: +{x_value} counters on {target.name} -> trample")


# === Professor Dellian Fel helpers ===

def prof_dellian_plus2(gs) -> None:
    """Dellian +2: Gain 3 life."""
    dellian = next((c for c in gs.zones.battlefield if c.name == PROF_DELLIAN), None)
    if not dellian: return
    dellian.counters = getattr(dellian, 'counters', 4) + 2
    gs.life += 3
    gs._log(f"  Dellian +2: gain 3 life (loyalty {dellian.counters})")


def prof_dellian_zero(gs) -> None:
    """Dellian 0: Draw a card, lose 1 life."""
    dellian = next((c for c in gs.zones.battlefield if c.name == PROF_DELLIAN), None)
    if not dellian: return
    gs.zones.draw(1)
    gs.life -= 1
    gs._log(f"  Dellian 0: draw 1, lose 1 life (loyalty {dellian.counters})")


def prof_dellian_minus3(gs, opponent=None) -> bool:
    """Dellian -3: Destroy target creature."""
    dellian = next((c for c in gs.zones.battlefield if c.name == PROF_DELLIAN), None)
    if not dellian or getattr(dellian, 'counters', 0) < 3:
        return False
    if not opponent:
        return False
    targets = [c for c in opponent.zones.battlefield
               if c.has(Tag.CREATURE) and not c.is_land()]
    if not targets:
        return False
    t = max(targets, key=lambda c: safe_power(c))
    opponent.zones.battlefield.remove(t)
    opponent.zones.graveyard.append(t)
    dellian.counters -= 3
    gs._log(f"  Dellian -3: destroy {t.name} (loyalty {dellian.counters})")
    return True


# === Mangara helpers ===

def mangara_attack_trigger(gs, num_attackers: int) -> None:
    """If opp attacks with 2+ creatures, draw a card."""
    if any(c.name == MANGARA for c in gs.zones.battlefield) and num_attackers >= 2:
        gs.zones.draw(1)
        gs._log(f"  Mangara: draw 1 (opp attacked with {num_attackers} creatures)")


def mangara_spell_trigger(gs) -> None:
    """When opp casts their 2nd spell, draw a card."""
    if any(c.name == MANGARA for c in gs.zones.battlefield):
        gs.zones.draw(1)
        gs._log(f"  Mangara: draw 1 (opp's 2nd spell this turn)")
