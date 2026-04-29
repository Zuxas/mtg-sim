"""Lorwyn Eclipsed — 21 cards

Key mechanics: Blight (-1/-1 counters), Behold (reveal creature type),
Hybrid mana (two-color spells with color bonuses), Merfolk tribal,
Elemental tribal, Convoke.

Cards included:
Requiting Hex {B} - instant, blight 1 optional, target creature gets -1/-1
Deceit {4}{U/B}{U/B} 5/5 - ETB if {UU} spent: bounce nonland perm
Sear {1}{R} - 4 damage to creature/planeswalker
Wistfulness {3}{G/U}{G/U} 6/5 - ETB if {GG} spent: exile artifact/enchantment
Sunderflock {7}{U}{U} 5/5 - cost reduction by highest Elemental CMC you control
Vibrance {3}{R/G}{R/G} 4/4 - ETB if {RR} spent: 3 damage to any target
Deepchannel Duelist {W}{U} 2/2 - end step untap Merfolk, other Merfolk +0/+1
Deepway Navigator {W}{U} 2/2 Flash - ETB untap all Merfolk
Disruptor of Currents {3}{U}{U} 3/3 Flash Convoke - counter target spell CMC<=2
Silvergill Mentor {1}{U} 2/1 - behold Merfolk or pay 2; ETB draw
Sygg Command {1}{U} 1/1 - {1}: change its name
Wanderbrine Trapper {W} 2/1 - tap ability to tap opponent creature
Ashling, Rekindled {1}{R} 1/3 - ETB discard→draw, transforms on discard
Flamebraider {1}{R} 2/2 - tap for 2-color mana (Elemental/activated only)
Formidable Speaker {2}{G} 2/4 - ETB discard to tutor creature to hand
Spell Snare {U} - counter target spell CMC=2
Sapling Nursery {6}{G}{G} - affinity for Forests, landfall creates Sapling
Bitterbloom Bearer {B}{B} 1/1 Flash Flying - upkeep lose 1 life, create Faerie
Shimmerwilds Growth {1}{G} - aura: enchanted land produces extra mana
Champion of the Weird {3}{B} 5/5 - behold+exile Goblin to cast
Oko, Lorwyn Liege {2}{U} PW - transform into elk, +2 bounce, -1 copy animal

Spec: apl/card_specs/lorwyn_eclipsed.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness

# Constants
REQUITING_HEX        = "Requiting Hex"
DECEIT               = "Deceit"
SEAR                 = "Sear"
WISTFULNESS          = "Wistfulness"
SUNDERFLOCK          = "Sunderflock"
VIBRANCE             = "Vibrance"
DEEPCHANNEL_DUELIST  = "Deepchannel Duelist"
DEEPWAY_NAVIGATOR    = "Deepway Navigator"
DISRUPTOR            = "Disruptor of Currents"
SILVERGILL_MENTOR    = "Silvergill Mentor"
SYGG_COMMAND         = "Sygg Command"
WANDERBRINE_TRAPPER  = "Wanderbrine Trapper"
ASHLING              = "Ashling, Rekindled"
FLAMEBRAIDER         = "Flamebraider"
FORMIDABLE_SPEAKER   = "Formidable Speaker"
SPELL_SNARE          = "Spell Snare"
SAPLING_NURSERY      = "Sapling Nursery"
BITTERBLOOM_BEARER   = "Bitterbloom Bearer"
SHIMMERWILDS_GROWTH  = "Shimmerwilds Growth"
CHAMPION_WEIRD       = "Champion of the Weird"
OKO_LIEGE            = "Oko, Lorwyn Liege"


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Lorwyn Eclipsed cards. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        # Special cost handling
        if card_name == SUNDERFLOCK:
            cost = _sunderflock_cost(gs)
            if gs.mana_pool.total() < cost:
                continue
        elif card_name == SAPLING_NURSERY:
            cost = _sapling_cost(gs)
            if gs.mana_pool.total() < cost:
                continue
        elif not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue

        gs.cast_spell(c)
        _on_resolve(gs, card_name, opponent)
        return True
    return False


def _sunderflock_cost(gs) -> int:
    """Cost reduction by highest Elemental CMC you control."""
    elementals = [x for x in gs.zones.battlefield
                  if x.has(Tag.CREATURE) and 'Elemental' in (getattr(x,'type_line','') or '')]
    reduction = max((getattr(e,'cmc',0) for e in elementals), default=0)
    return max(0, 9 - int(reduction))  # base {7}{U}{U} = 9


def _sapling_cost(gs) -> int:
    """Affinity for Forests."""
    forests = sum(1 for c in gs.zones.battlefield if c.is_land()
                  and 'Forest' in (getattr(c,'type_line','') or ''))
    return max(2, 8 - forests)  # base {6}{G}{G} = 8


def _on_resolve(gs, name: str, opponent):
    """Apply resolution effects."""
    if name == REQUITING_HEX and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = min(critters, key=lambda c: safe_toughness(c))
            t.counters = getattr(t,'counters',0) - 1
            if safe_toughness(t) + getattr(t,'counters',0) <= 0:
                opponent.zones.battlefield.remove(t)
                opponent.zones.graveyard.append(t)
            gs._log(f"  Requiting Hex: -1/-1 on {t.name}")

    elif name == SEAR and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and safe_toughness(c) <= 4]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs._log(f"  Sear: 4 damage kills {t.name}")
        else:
            gs.damage_dealt += 4
            gs._log(f"  Sear: 4 damage face")

    elif name == DECEIT and opponent:
        targets = [c for c in opponent.zones.battlefield if not c.is_land()]
        if targets:
            t = max(targets, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.battlefield.remove(t)
            opponent.zones.hand.append(t)
            gs._log(f"  Deceit ETB: bounce {t.name}")

    elif name == WISTFULNESS and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if not c.is_land() and (c.has(Tag.ARTIFACT) or c.has(Tag.ENCHANTMENT))]
        if targets:
            t = targets[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.exile.append(t)
            gs._log(f"  Wistfulness ETB: exile {t.name}")

    elif name == VIBRANCE and opponent:
        gs.damage_dealt += 3
        gs._log(f"  Vibrance ETB: 3 damage")

    elif name in (DEEPWAY_NAVIGATOR, DEEPCHANNEL_DUELIST):
        # Untap Merfolk
        merfolk = [c for c in gs.zones.battlefield
                   if c.has(Tag.CREATURE) and 'Merfolk' in (getattr(c,'type_line','') or '')]
        for m in merfolk:
            m.tapped = False
        gs._log(f"  Merfolk: untap {len(merfolk)} creatures")

    elif name == SILVERGILL_MENTOR:
        gs.zones.draw(1)
        gs._log(f"  Silvergill Mentor: draw 1")

    elif name == FORMIDABLE_SPEAKER:
        # Discard to tutor creature
        if gs.zones.hand:
            worst = min(gs.zones.hand, key=lambda c: getattr(c,'cmc',0))
            gs.zones.hand.remove(worst)
            gs.zones.graveyard.append(worst)
            # Find best creature in library
            lib_creatures = [c for c in gs.zones.library if c.has(Tag.CREATURE)]
            if lib_creatures:
                tutor = max(lib_creatures, key=lambda c: getattr(c,'cmc',0))
                gs.zones.library.remove(tutor)
                gs.zones.hand.append(tutor)
                gs._log(f"  Formidable Speaker: tutor {tutor.name} to hand")

    elif name == BITTERBLOOM_BEARER:
        # ETB on upkeep -- Bitterbloom creates Faerie each upkeep
        pass  # handled in upkeep

    elif name == DISRUPTOR and opponent:
        gs._log(f"  Disruptor of Currents: counter target spell CMC<=2 via convoke")


def bitterbloom_upkeep(gs) -> None:
    """Bitterbloom Bearer upkeep: lose 1 life, create 1/1 Faerie."""
    if not any(c.name == BITTERBLOOM_BEARER for c in gs.zones.battlefield):
        return
    gs.life -= 1
    tok = Card("Faerie Token", "{0}", 1, "Token Creature — Faerie")
    tok.power = "1"; tok.toughness = "1"
    tok.turn_entered = gs.turn; tok.summoning_sickness = True
    gs.zones.battlefield.append(tok)
    gs._log(f"  Bitterbloom Bearer upkeep: -1 life, create 1/1 Faerie")


def cast_spell_snare(gs, opponent=None, target_spell=None) -> bool:
    """Counter target spell with CMC 2."""
    if not opponent or not target_spell:
        return False
    if getattr(target_spell, 'cmc', 0) != 2:
        return False
    for c in list(gs.zones.hand):
        if c.name == SPELL_SNARE and gs.mana_pool.total() >= 1:
            try:
                gs.mana_pool.pay("{U}", 1)
            except Exception:
                continue
            gs.zones.hand.remove(c)
            gs.zones.graveyard.append(c)
            gs._log(f"  Spell Snare: counter {target_spell.name} (CMC 2)")
            return True
    return False
