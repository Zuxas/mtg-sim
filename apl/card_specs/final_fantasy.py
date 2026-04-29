"""Final Fantasy (Universal Beyond) — 10 cards

Cards from Magic × Final Fantasy crossover set.
Key cards: Vivi Ornitier (mana engine), Aerith (lifegain/counters),
Snow Villiers (scales with creatures), Esper Origins (GY recursion).

Spec: apl/card_specs/final_fantasy.py
"""
from __future__ import annotations
from data.card import Tag
from engine.match_state import safe_power

ESPER_ORIGINS = "Esper Origins"
VIVI_ORNITIER = "Vivi Ornitier"
AERITH        = "Aerith Gainsborough"
SNOW_VILLIERS = "Snow Villiers"

ALL_NAMES = {ESPER_ORIGINS, VIVI_ORNITIER, AERITH, SNOW_VILLIERS}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Cast Final Fantasy card. Returns True if cast."""
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
    if name == ESPER_ORIGINS:
        # Surveil 2, gain 2 life; if cast from GY: exile it, create token
        gs.life += 2
        # Surveil 2
        for _ in range(min(2, len(gs.zones.library))):
            top = gs.zones.library[0]
            if top.is_land() or getattr(top,'cmc',0) <= 1:
                gs.zones.library.pop(0)
                gs.zones.library.append(top)
        gs._log(f"  Esper Origins: surveil 2 + gain 2 life")

    elif name == VIVI_ORNITIER:
        # 0/3 creature that taps for blue/red mana equal to its counters
        gs._log(f"  Vivi Ornitier: 0/3, {T}: add X mana where X=counters")

    elif name == AERITH:
        # 2/2 lifelink, gains +1/+1 on lifegain
        gs._log(f"  Aerith: 2/2 lifelink, +1/+1 counter whenever you gain life")

    elif name == SNOW_VILLIERS:
        # */3 vigilance where * = creatures you control
        creatures = sum(1 for c in gs.zones.battlefield
                       if c.has(Tag.CREATURE) and not c.is_land())
        card.power = str(creatures)
        gs._log(f"  Snow Villiers: {creatures}/3 vigilance")


def vivi_tap_for_mana(gs) -> int:
    """Vivi Ornitier: tap for X mana where X = counter count."""
    vivi = next((c for c in gs.zones.battlefield if c.name == VIVI_ORNITIER), None)
    if not vivi or getattr(vivi,'tapped',False):
        return 0
    x = getattr(vivi,'counters',0)
    vivi.tapped = True
    gs._log(f"  Vivi tap: add {x} mana")
    return x


def aerith_lifegain_trigger(gs) -> None:
    """Whenever you gain life, put +1/+1 counter on Aerith."""
    aerith = next((c for c in gs.zones.battlefield if c.name == AERITH), None)
    if aerith:
        aerith.counters = getattr(aerith,'counters',0) + 1
