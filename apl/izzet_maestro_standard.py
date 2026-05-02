"""
apl/izzet_maestro_standard.py -- Izzet Maestro goldfish APL (Standard)

Game plan:
  T1: Expressive Firedancer or Gran-Gran
  T2: Molten-Core Maestro (2/2 menace, Opus: +1/+1 counter on each instant/sorcery)
  T3+: Chain cheap instants/sorceries to grow Maestro; if 5+ mana spent on a spell,
       Maestro generates R equal to its power — mana engine for bigger turns

PT SOS performance: 30.6% FWR (worst in field). Included for gauntlet completeness —
the deck is underpowered, which the sim should reflect.

Priority: Maestro first, then chain spells to grow it. Gran-Gran makes
noncreature spells cost {1} less at 3+ Lessons in GY.
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

MAESTRO    = "Molten-Core Maestro"
GRAN       = "Gran-Gran"
STALLION   = "Colorstorm Stallion"
DANCER     = "Expressive Firedancer"
SANAR      = "Sanar, Unfinished Genius"
VIBRANT    = "Vibrant Outburst"
CHOREO     = "Choreographed Sparks"
COMBUSTION = "Combustion Technique"
FLASHBACK  = "Flashback"
FIREBEND   = "Firebending Lesson"
STORM      = "Stormchaser's Talent"
CHASE      = "Chase Inspiration"
DUEL       = "Duel Tactics"

CREATURES  = (GRAN, DANCER, MAESTRO, STALLION, SANAR)
CHEAP_INSTANTS = {VIBRANT, CHOREO, COMBUSTION, FLASHBACK, DUEL, CHASE}


class IzzetMaestroAPL(BaseAPL):
    name = "Izzet Maestro"
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
        threats = [c for c in hand if c.name in {MAESTRO, GRAN, DANCER}]
        spells  = [c for c in hand if c.name in CHEAP_INSTANTS]
        return (len(threats) >= 1 or len(spells) >= 2) or mulligans >= 2

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

        # Gran-Gran cost reduction if 3+ Lesson cards in GY
        gran_on_board = any(c.name == GRAN for c in gs.zones.battlefield
                            if not c.is_land())
        lessons_in_gy = sum(1 for c in gs.zones.graveyard
                            if 'Lesson' in (getattr(c, 'type_line', '') or ''))
        if gran_on_board and lessons_in_gy >= 3:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, 1)

        # Deploy creatures first (Maestro wants to land early to grow)
        changed = True
        while changed:
            changed = False
            hand_names = {c.name: c for c in gs.zones.hand if not c.is_land()}
            for name in CREATURES:
                card = hand_names.get(name)
                if card and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    if gs.cast_spell(card):
                        changed = True
                        break

        # Chain instants/sorceries to trigger Maestro's Opus ability
        # Cast cheapest first to trigger as many times as possible
        maestro_on_board = any(c.name == MAESTRO for c in gs.zones.battlefield
                               if not c.is_land())
        for card in sorted(list(gs.zones.hand),
                           key=lambda c: getattr(c, 'cmc', 0)):
            if not card.is_land() and card.name not in CREATURES:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    if gs.cast_spell(card) and maestro_on_board:
                        # Maestro grows — counters tracked by ETB/spell handlers
                        pass

    def main_phase2(self, gs):
        gs.tap_lands()
        for card in list(gs.zones.hand):
            if not card.is_land() and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
