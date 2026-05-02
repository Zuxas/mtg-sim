"""
apl/golgari_midrange_standard.py -- Golgari Midrange goldfish APL (Standard)

Game plan:
  T1: Llanowar Elves (ramp) or Duress / Requiting Hex (goldfish no-op)
  T2: Badgermole Cub (2/2 earthbend)
  T3: Emeritus of Abundance (3/4 vigilance) / Unholy Annex (draw engine)
  T4: Maelstrom Pulse (goldfish no-op) / Keen-Eyed Curator
  T5: Tragedy Feaster (7/6 trample)

Removal/discard spells (Requiting Hex, Duress, Intimidation Tactics,
Shoot the Sheriff, Witherbloom Charm) have no targets in goldfish —
cast last to clear hand, then attack for wins.
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

ELVES     = "Llanowar Elves"
BADGER    = "Badgermole Cub"
EMERITUS  = "Emeritus of Abundance"
ANNEX     = "Unholy Annex"
CURATOR   = "Keen-Eyed Curator"
FEASTER   = "Tragedy Feaster"
FIRDOCH   = "Firdoch Core"

# Threats in priority order (cheapest first)
THREATS = (ELVES, BADGER, CURATOR, EMERITUS, ANNEX, FEASTER)

# Spells that do nothing in goldfish — cast last to drain hand/mana
GOLDFISH_NOOP = {
    "Duress", "Requiting Hex", "Intimidation Tactics",
    "Shoot the Sheriff", "Witherbloom Charm", "Maelstrom Pulse",
    "Decorum Dissertation", "Strategic Betrayal",
}


class GolgariMidrangeAPL(BaseAPL):
    name = "Golgari Midrange"
    win_condition_damage = 20
    max_turns = 14

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = [c for c in hand if c.is_land()]
        if len(lands) == 0:
            return False
        if len(lands) > 5:
            return False
        threats = [c for c in hand if c.name in THREATS]
        return len(threats) >= 1 or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        # Bottom noops first, then excess lands, then high-cmc spells
        noops  = [c for c in hand if c.name in GOLDFISH_NOOP]
        spells = sorted([c for c in hand if not c.is_land()
                         and c.name not in GOLDFISH_NOOP],
                        key=lambda c: -getattr(c, 'cmc', 0))
        excess = lands[4:]
        return (noops + excess + spells)[:n]

    def main_phase(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if lands and not gs.land_played:
            gs.play_land(lands[0])
        gs.tap_lands()

        # Cast threats in priority order
        changed = True
        while changed:
            changed = False
            hand_names = {c.name: c for c in gs.zones.hand if not c.is_land()}
            for name in THREATS:
                card = hand_names.get(name)
                if card and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    if gs.cast_spell(card):
                        changed = True
                        break

        # Dump remaining castable spells (curve out mana)
        for card in sorted(list(gs.zones.hand),
                           key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in list(gs.zones.hand):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
