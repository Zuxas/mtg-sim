"""
apl/izzet_prowess.py — Izzet Prowess APL (Modern + Standard)

Sligh-style prowess deck. Swiftspear + DRC + Slickshot Show-Off.
Kill clock: T3.2 avg (fastest non-combo Modern deck)

Priority: buff creatures with spells, attack every turn for lethal.
"""

from apl.base_apl import BaseAPL
from apl.sb_mixin import SBPlanMixin
from engine.game_state import GameState

SWIFTSPEAR = "Monastery Swiftspear"
DRC        = "Dragon's Rage Channeler"
SLICKSHOT  = "Slickshot Show-Off"
CORI       = "Cori-Steel Cutter"
BOLT       = "Lightning Bolt"
LAVA_DART  = "Lava Dart"
ITERATION  = "Expressive Iteration"
PREORDAIN  = "Preordain"
BAUBLE     = "Mishra's Bauble"
MUTAGENIC  = "Mutagenic Growth"


class IzzetProwessAPL(SBPlanMixin, BaseAPL):
    name = "Izzet Prowess"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands     = sum(1 for c in hand if c.is_land())
        threats   = sum(1 for c in hand if c.name in {SWIFTSPEAR, DRC, SLICKSHOT})
        has_spells= sum(1 for c in hand if c.name in {BOLT, LAVA_DART, MUTAGENIC, BAUBLE})
        if lands == 0: return False
        if lands == 1 and threats >= 1 and has_spells >= 2: return True
        if lands >= 2 and threats >= 1: return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[2:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)

        # Deploy threats first
        for name in (SWIFTSPEAR, DRC, CORI, SLICKSHOT):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Fire off cheap spells to trigger prowess + deal damage
        # Each spell gives +1/+0 to all prowess creatures this turn
        creatures_with_prowess = len([c for c in gs.battlefield() if not c.is_land()])
        for card in list(gs.hand()):
            if card.name in {LAVA_DART, BAUBLE, MUTAGENIC} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.hand().remove(card)
                gs.zones.graveyard.append(card)
                # Prowess trigger: +1 damage per creature for each free spell
                gs.damage_dealt += max(1, creatures_with_prowess)
                gs._log(f"  {card.name} → prowess trigger ({creatures_with_prowess} creatures)")

        # Lightning Bolt face
        for card in list(gs.hand()):
            if card.name == BOLT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.damage_dealt += 3
                gs.hand().remove(card)
                gs.zones.graveyard.append(card)
                gs._log("  Lightning Bolt → face (3)")
                break

        # Cantrips to find more gas
        for card in list(gs.hand()):
            if card.name in {PREORDAIN, ITERATION} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
