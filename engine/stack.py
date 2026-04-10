"""
engine/stack.py — Simplified spell stack for Phase 3B interaction

Models the core of MTG's stack: cast → opponent responds? → resolve LIFO.
Not a full rules engine — handles the 90% of competitive interaction:
removal, counterspells, discard, burn, bounce, wrath.

The stack resolves Last-In-First-Out. If player A casts a creature and
player B responds with a counterspell, the counter resolves first and
the creature never enters the battlefield.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

from data.card import Card, Tag


class InteractionType(str, Enum):
    """What an instant/sorcery does to the opponent."""
    REMOVAL   = "removal"      # destroy/exile target creature
    COUNTER   = "counter"      # counter target spell
    DISCARD   = "discard"      # opponent discards from hand
    BURN      = "burn"         # deal damage to player
    BOUNCE    = "bounce"       # return permanent to hand
    WRATH     = "wrath"        # destroy all creatures
    PUMP      = "pump"         # +N/+N to own creature (combat trick)
    NONE      = "none"         # cantrip, card draw, etc.


@dataclass
class StackItem:
    """A spell or ability on the stack."""
    card:       Card
    caster:     str                          # 'a' or 'b'
    targets:    list = field(default_factory=list)  # target cards/players
    countered:  bool = False
    interaction_type: InteractionType = InteractionType.NONE
    damage:     int = 0                      # for burn spells


@dataclass
class Resolution:
    """Result of resolving one stack item."""
    item:    StackItem
    outcome: str = ''       # 'resolved', 'countered', 'fizzled'
    effects: list = field(default_factory=list)  # what happened


class Stack:
    """
    Simplified MTG spell stack.
    
    Flow: cast spell → opponent gets priority to respond → resolve LIFO.
    Each "priority pass" is one chance to cast an instant or activate an ability.
    If both players pass, the top item resolves.
    """
    
    def __init__(self):
        self.items: list[StackItem] = []
    
    def is_empty(self) -> bool:
        return len(self.items) == 0
    
    def cast(self, card: Card, caster: str, targets: list = None,
             interaction_type: InteractionType = None, damage: int = 0):
        """Put a spell on the stack."""
        if interaction_type is None:
            interaction_type = classify_card(card)
        item = StackItem(
            card=card, caster=caster,
            targets=targets or [],
            interaction_type=interaction_type,
            damage=damage,
        )
        self.items.append(item)
        return item
    
    def respond(self, card: Card, caster: str, targets: list = None,
                interaction_type: InteractionType = None, damage: int = 0):
        """Respond to the top item (counter, kill in response, etc.)."""
        return self.cast(card, caster, targets, interaction_type, damage)
    
    def counter_top(self):
        """Mark the item below the top as countered (the counter spell is on top)."""
        if len(self.items) >= 2:
            self.items[-2].countered = True
    
    def resolve_one(self) -> Optional[Resolution]:
        """Resolve the top item on the stack."""
        if not self.items:
            return None
        item = self.items.pop()
        if item.countered:
            return Resolution(item, 'countered')
        return Resolution(item, 'resolved')
    
    def resolve_all(self) -> list[Resolution]:
        """Resolve entire stack LIFO."""
        results = []
        while self.items:
            results.append(self.resolve_one())
        return results


# ---------------------------------------------------------------------------
# Card Classification — what does this spell DO?
# ---------------------------------------------------------------------------

# Known removal spells (name → InteractionType + damage if burn)
SPELL_DB = {
    # Modern removal
    "lightning bolt":        (InteractionType.BURN, 3),
    "fatal push":            (InteractionType.REMOVAL, 0),
    "unholy heat":           (InteractionType.REMOVAL, 0),
    "galvanic discharge":    (InteractionType.REMOVAL, 0),
    "solitude":              (InteractionType.REMOVAL, 0),
    "fury":                  (InteractionType.REMOVAL, 0),
    "swords to plowshares":  (InteractionType.REMOVAL, 0),
    "path to exile":         (InteractionType.REMOVAL, 0),
    "prismatic ending":      (InteractionType.REMOVAL, 0),
    "march of otherworldly light": (InteractionType.REMOVAL, 0),
    "dismember":             (InteractionType.REMOVAL, 0),
    "terminate":             (InteractionType.REMOVAL, 0),
    "drown in the loch":     (InteractionType.REMOVAL, 0),
    "static prison":         (InteractionType.REMOVAL, 0),
    "thraben charm":         (InteractionType.REMOVAL, 0),
    "lava spike":            (InteractionType.BURN, 3),
    "rift bolt":             (InteractionType.BURN, 3),
    "searing blaze":         (InteractionType.BURN, 3),
    "goblin guide":          (InteractionType.BURN, 0),
    "fiery impulse":         (InteractionType.BURN, 2),
    "cut down":              (InteractionType.REMOVAL, 0),
    "go for the throat":     (InteractionType.REMOVAL, 0),
    "heartfire hero":        (InteractionType.BURN, 0),
    
    # Counterspells
    "counterspell":          (InteractionType.COUNTER, 0),
    "force of negation":     (InteractionType.COUNTER, 0),
    "force of will":         (InteractionType.COUNTER, 0),
    "spell pierce":          (InteractionType.COUNTER, 0),
    "mystical dispute":      (InteractionType.COUNTER, 0),
    "negate":                (InteractionType.COUNTER, 0),
    "dovin's veto":          (InteractionType.COUNTER, 0),
    "daze":                  (InteractionType.COUNTER, 0),
    "flusterstorm":          (InteractionType.COUNTER, 0),
    "subtlety":              (InteractionType.COUNTER, 0),
    "consign to memory":     (InteractionType.COUNTER, 0),
    
    # Discard
    "thoughtseize":          (InteractionType.DISCARD, 0),
    "inquisition of kozilek": (InteractionType.DISCARD, 0),
    "grief":                 (InteractionType.DISCARD, 0),
    "duress":                (InteractionType.DISCARD, 0),
    "cabal therapy":         (InteractionType.DISCARD, 0),
    
    # Bounce
    "teferi, time raveler":  (InteractionType.BOUNCE, 0),
    "brazen borrower":       (InteractionType.BOUNCE, 0),
    "ephemerate":            (InteractionType.BOUNCE, 0),
    
    # Wrath
    "supreme verdict":       (InteractionType.WRATH, 0),
    "terminus":              (InteractionType.WRATH, 0),
    "wrath of god":          (InteractionType.WRATH, 0),
    "day of judgment":        (InteractionType.WRATH, 0),
    "sunfall":               (InteractionType.WRATH, 0),
    "temporary lockdown":    (InteractionType.WRATH, 0),
    "brotherhood's end":     (InteractionType.WRATH, 0),
    
    # Pump / combat tricks
    "mutagenic growth":      (InteractionType.PUMP, 0),
    "giant growth":          (InteractionType.PUMP, 0),
    "violent urge":          (InteractionType.PUMP, 0),
    "might of old krosa":    (InteractionType.PUMP, 0),
}


def classify_card(card: Card) -> InteractionType:
    """Classify what a card does based on name or oracle text."""
    name = card.name.lower()
    
    # Check known spell DB
    if name in SPELL_DB:
        return SPELL_DB[name][0]
    
    # Heuristic: check oracle text for keywords
    oracle = (getattr(card, 'oracle_text', '') or '').lower()
    
    if 'counter target' in oracle:
        return InteractionType.COUNTER
    if 'destroy target' in oracle or 'exile target' in oracle:
        return InteractionType.REMOVAL
    if 'discard' in oracle and ('target' in oracle or 'opponent' in oracle):
        return InteractionType.DISCARD
    if 'damage to any target' in oracle or 'damage to target' in oracle:
        return InteractionType.BURN
    if 'destroy all' in oracle or 'exile all' in oracle:
        return InteractionType.WRATH
    if 'return target' in oracle and 'to its owner' in oracle:
        return InteractionType.BOUNCE
    if '+' in oracle and '/' in oracle and ('until end of turn' in oracle or 'target creature' in oracle):
        return InteractionType.PUMP
    
    return InteractionType.NONE


def get_burn_damage(card: Card) -> int:
    """Get the damage a burn spell deals."""
    name = card.name.lower()
    if name in SPELL_DB:
        return SPELL_DB[name][1]
    # Heuristic from oracle text
    oracle = (getattr(card, 'oracle_text', '') or '').lower()
    for n in [3, 2, 4, 5, 1]:
        if f'deals {n} damage' in oracle:
            return n
    return 2  # default guess


# ---------------------------------------------------------------------------
# Interaction Resolution — apply effects to the game state
# ---------------------------------------------------------------------------

def resolve_interaction(resolution: Resolution, caster_gs, target_gs):
    """
    Apply the resolved spell's effect to the game state.
    
    caster_gs: the GameState of the player who cast the spell
    target_gs: the GameState of the opponent
    """
    if resolution.outcome == 'countered':
        return  # spell was countered, no effect
    
    item = resolution.item
    itype = item.interaction_type
    
    if itype == InteractionType.REMOVAL:
        # Destroy/exile the best target creature
        targets = item.targets
        if targets:
            target = targets[0]
            if target in target_gs.zones.battlefield:
                target_gs.zones.battlefield.remove(target)
                target_gs.zones.graveyard.append(target)
        else:
            # No explicit target — kill the biggest creature
            creatures = [c for c in target_gs.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
            if creatures:
                from engine.match_state import safe_power
                best = max(creatures, key=lambda c: safe_power(c))
                target_gs.zones.battlefield.remove(best)
                target_gs.zones.graveyard.append(best)
    
    elif itype == InteractionType.BURN:
        damage = item.damage or get_burn_damage(item.card)
        if item.targets:
            target = item.targets[0]
            if isinstance(target, Card) and target in target_gs.zones.battlefield:
                # Burn a creature — check if it dies
                from engine.match_state import safe_toughness
                if damage >= safe_toughness(target):
                    target_gs.zones.battlefield.remove(target)
                    target_gs.zones.graveyard.append(target)
            else:
                # Burn the player
                target_gs.life -= damage
                caster_gs.damage_dealt += damage
        else:
            # Default: burn the player
            target_gs.life -= damage
            caster_gs.damage_dealt += damage
    
    elif itype == InteractionType.COUNTER:
        # Counter effect is already handled by stack.counter_top()
        pass
    
    elif itype == InteractionType.DISCARD:
        # Opponent discards their best card
        hand = target_gs.zones.hand
        nonlands = [c for c in hand if not c.is_land()]
        if nonlands:
            # Discard highest CMC (most impactful) card
            worst = max(nonlands, key=lambda c: getattr(c, 'cmc', 0))
            hand.remove(worst)
            target_gs.zones.graveyard.append(worst)
    
    elif itype == InteractionType.BOUNCE:
        # Return best creature to owner's hand
        targets = item.targets
        if targets and targets[0] in target_gs.zones.battlefield:
            target = targets[0]
            target_gs.zones.battlefield.remove(target)
            target_gs.zones.hand.append(target)
        else:
            creatures = [c for c in target_gs.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
            if creatures:
                from engine.match_state import safe_power
                best = max(creatures, key=lambda c: safe_power(c))
                target_gs.zones.battlefield.remove(best)
                target_gs.zones.hand.append(best)
    
    elif itype == InteractionType.WRATH:
        # Destroy all creatures on BOTH boards
        for c in list(target_gs.zones.battlefield):
            if not c.is_land() and c.has(Tag.CREATURE):
                target_gs.zones.battlefield.remove(c)
                target_gs.zones.graveyard.append(c)
        for c in list(caster_gs.zones.battlefield):
            if not c.is_land() and c.has(Tag.CREATURE):
                caster_gs.zones.battlefield.remove(c)
                caster_gs.zones.graveyard.append(c)
    
    elif itype == InteractionType.PUMP:
        # +N/+N to own creature — handled as temporary counters
        targets = item.targets
        if targets and targets[0] in caster_gs.zones.battlefield:
            targets[0].counters += 2  # approximate +2/+2
