"""
apl/azorius_blink_standard.py -- Azorius Blink goldfish APL (Standard / PT SOS 2026)

Game plan:
  T1: Novice Inspector (1W, 1/2): ETB creates a Treasure token
  T2: Nurturing Pixie (W, 1/1 flying): ETB/attack blinks a nonland you control
      OR Enduring Innocence (WW, 2/3 enchantment): draw whenever a creature ETBs
  T3: Voice of Victory (2W, 1/3 flash): Mobilize 2 on attack; 3 life gain
      OR Starfield Shepherd (3W, 3/3 flying): ETB tutors Plains or creature MV<=life
  T4+: Cosmogrand Zenith (7W), Shardmage's Rescue (instant blink for re-triggers)

Engine: Enduring Innocence in play → cast/blink Novice Inspector or any creature
        → draw a card per ETB. Nurturing Pixie blinks the Inspector or the Innocence
        itself for repeated value.
"""
from apl.base_apl import BaseAPL

INSPECTOR  = "Novice Inspector"
PIXIE      = "Nurturing Pixie"
INNOCENCE  = "Enduring Innocence"
VOICE      = "Voice of Victory"
SHEPHERD   = "Starfield Shepherd"
MOMO       = "Momo, Friendly Flier"
HALIYA     = "Haliya, Guided by Light"
RESCUE     = "Shardmage's Rescue"
ZENITH     = "Cosmogrand Zenith"

CURVE_ORDER = (INSPECTOR, PIXIE, INNOCENCE, VOICE, SHEPHERD, HALIYA, MOMO, ZENITH)
THREATS     = frozenset(CURVE_ORDER)


class AzoriusBlinkAPL(BaseAPL):
    name = "Azorius Blink"
    win_condition_damage = 20
    max_turns = 13

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        threats = sum(1 for c in hand if c.name in {INSPECTOR, PIXIE, INNOCENCE, VOICE})
        return threats >= 1 or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        excess = lands[4:]
        return (excess + spells)[:n]

    def main_phase(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if lands and not gs.land_played:
            gs.play_land(lands[0])
        gs.tap_lands()

        # Play engine pieces in curve order; Innocence early enables draw triggers
        changed = True
        while changed:
            changed = False
            hand_by_name = {c.name: c for c in gs.zones.hand if not c.is_land()}
            for name in CURVE_ORDER:
                card = hand_by_name.get(name)
                if card and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    if gs.cast_spell(card):
                        changed = True
                        break

        # Dump remaining castable spells (removal, cantrips, etc.)
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in sorted(list(gs.zones.hand), key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
