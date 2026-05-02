"""
apl/selesnya_landfall_standard.py -- Selesnya Landfall goldfish APL (Standard)

Game plan:
  T1: Llanowar Elves or Sazh's Chocobo (1-drop ramp / landfall body)
  T2: Tifa Lockhart or Badgermole Cub
  T3: Mossborn Hydra + land = 2/2 trample; Earthbender Ascension starts quest
  T4+: Planar Engineering (sac 2 lands, get 4 tapped basics) kicks landfall chain
  Win via trample attackers doubled by Tifa landfall and Mossborn counter doubling.

Landfall triggers handled by engine (on_landfall in card_effects):
  - Sazh's Chocobo: LANDFALL_GROW (+1/+1 counter)
  - Earthbender Ascension: LANDFALL_QUEST (quest counter, pump at 4)
  - Mossborn Hydra: named case (double own counters)
  - Tifa Lockhart: named case (double own power)
  - Bristly Bill: named case (+1/+1 on biggest friend)
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL
from engine.card_effects import on_landfall

ELVES     = "Llanowar Elves"
CHOCOBO   = "Sazh's Chocobo"
TIFA      = "Tifa Lockhart"
BADGER    = "Badgermole Cub"
HYDRA     = "Mossborn Hydra"
ASCENSION = "Earthbender Ascension"
BRISTLY   = "Bristly Bill, Spine Sower"
TRAVEL    = "Traveling Chocobo"
PLANAR    = "Planar Engineering"
ROYAL     = "Royal Treatment"
BA_SING   = "Ba Sing Se"

ONE_DROPS  = {ELVES, CHOCOBO}
TWO_DROPS  = {TIFA, BADGER}
THREE_DROPS = {HYDRA, ASCENSION, BRISTLY, TRAVEL}


class SelesnyaLandfallAPL(BaseAPL):
    name = "Selesnya Landfall"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = [c for c in hand if c.is_land()]
        ones  = [c for c in hand if c.name in ONE_DROPS]
        twos  = [c for c in hand if c.name in TWO_DROPS]
        if len(lands) == 0:
            return False
        if len(lands) > 5:
            return False
        # Need at least a 1-drop or (2 lands + a 2-drop)
        if ones:
            return len(lands) >= 1
        if twos:
            return len(lands) >= 2
        return mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        excess = lands[4:]  # keep up to 4 lands
        return (excess + spells)[:n]

    def main_phase(self, gs):
        self._play_land(gs)
        gs.tap_lands()
        # Deploy in curve order; loop until nothing new can be cast
        priority = [ONE_DROPS, TWO_DROPS, THREE_DROPS]
        changed = True
        while changed:
            changed = False
            for group in priority:
                for card in list(gs.zones.hand):
                    if card.name not in group:
                        continue
                    if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        if gs.cast_spell(card):
                            changed = True
                            break
                if changed:
                    break
        # Planar Engineering last — only when 4+ lands in play so we can
        # afford to sacrifice two and still have mana available
        lands_on_bf = sum(1 for c in gs.zones.battlefield if c.is_land())
        for card in list(gs.zones.hand):
            if card.name == PLANAR and lands_on_bf >= 4:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

    def main_phase2(self, gs):
        gs.tap_lands()
        # Cast anything left (Royal Treatment, utility) after combat
        for card in list(gs.zones.hand):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def _play_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = c.name.lower()
            # Fetchlands first — fire double landfall trigger
            if 'passage' in n or 'tunnel' in n:
                return 0
            # Ba Sing Se — enters tapped unless basic present; play early
            if 'ba sing se' in n:
                return 1
            # Basics
            return 2
        gs.play_land(min(lands, key=score))
