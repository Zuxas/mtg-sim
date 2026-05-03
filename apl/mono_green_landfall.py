"""apl/mono_green_landfall.py -- Mono Green Landfall APL (Standard)

Based on Stefan Schutz PT SOS Top 5 list (2026-05-01).
PT overall WR: 55.45% (N=514). Beats Prowess 62.7%, loses to Selesnya 34.6%.

Game plan:
  T1: Llanowar Elves (ramp into T2 3-drop)
  T2: Badgermole Cub / Sazh Chocobo / Icetill Explorer
  T3: Earthbender Ascension (quest saga) + fetchland trigger
  T4+: Mightform Harmonizer growing with each landfall
  Win: wide board pumped by landfall triggers from fetches

Match-mode: Meltstrider Resolve fights small opp creatures when we are
ahead on board. ETB fight handler is match-aware (fights opp MV<=2 creature).
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

ELVES       = "Llanowar Elves"
BADGER      = "Badgermole Cub"
SAZH        = "Sazh's Chocobo"
ICETILL     = "Icetill Explorer"
EDGE_ROVER  = "Edge Rover"
ASCENSION   = "Earthbender Ascension"
HARMONIZER  = "Mightform Harmonizer"
MELTSTRIDER = "Meltstrider's Resolve"

ONE_DROPS   = {ELVES}
TWO_DROPS   = {BADGER, SAZH, ICETILL, EDGE_ROVER}
THREE_DROPS = {ASCENSION, HARMONIZER}

FETCHLANDS  = {"Fabled Passage", "Escape Tunnel", "Ba Sing Se"}


class MonoGreenLandfallAPL(BaseAPL):
    name = "Mono Green Landfall"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands  = [c for c in hand if c.is_land()]
        ones   = [c for c in hand if c.name in ONE_DROPS]
        twos   = [c for c in hand if c.name in TWO_DROPS]
        threes = [c for c in hand if c.name in THREE_DROPS]
        n = len(lands)
        if n == 0 or n > 5:
            return False
        if ones and n >= 1:
            return True
        if twos and n >= 2:
            return True
        if threes and n >= 3:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands  = [c for c in hand if c.is_land()]
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, "cmc", 0))
        return (lands[4:] + spells)[:n]

    def _play_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            if c.name in FETCHLANDS:
                return 0
            return 1
        gs.play_land(min(lands, key=score))

    def main_phase(self, gs):
        self._play_land(gs)
        gs.tap_lands()
        self._maybe_meltstrider(gs)
        deployed = True
        while deployed:
            deployed = False
            for group in [ONE_DROPS, TWO_DROPS, THREE_DROPS]:
                for card in list(gs.zones.hand):
                    if card.name not in group:
                        continue
                    if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        deployed = True
                        break
                if deployed:
                    break

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in list(gs.zones.hand):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)

    def _maybe_meltstrider(self, gs):
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return
        if not any(c.name == MELTSTRIDER for c in gs.zones.hand):
            return
        opp_small = [c for c in opp.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)
                     and (getattr(c, "cmc", 0) or 0) <= 2]
        if not opp_small:
            return
        opp_target = max(opp_small, key=lambda c: int(c.toughness or 1))
        our_creatures = [c for c in gs.zones.battlefield
                         if not c.is_land() and c.has(Tag.CREATURE)]
        if not any(c.effective_power() > int(opp_target.toughness or 1) for c in our_creatures):
            return
        for card in list(gs.zones.hand):
            if card.name == MELTSTRIDER and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
