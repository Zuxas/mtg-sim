"""apl/mono_red_aggro.py — Mono Red Aggro APL (Modern + Standard + Legacy)
Goblin Guide + Eidolon + Chain Lightning + Price of Progress.
Kill clock: T3-4 via pure damage.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

GOBLIN_GUIDE  = "Goblin Guide"
SWIFTSPEAR    = "Monastery Swiftspear"
EIDOLON       = "Eidolon of the Great Revel"
CHAIN         = "Chain Lightning"
BOLT          = "Lightning Bolt"
PRICE         = "Price of Progress"
FIREBLAST     = "Fireblast"
RIFT_BOLT     = "Rift Bolt"
SEARING_BLAZE = "Searing Blaze"
SKULLCRACK    = "Skullcrack"
LIGHT_UP      = "Light Up the Stage"
# Standard red
SLICKSHOT     = "Slickshot Show-Off"
DRC           = "Dragon's Rage Channeler"
GALVANIC      = "Galvanic Discharge"
CACOPHONY     = "Cacophony Scamp"

ONE_DROPS  = {GOBLIN_GUIDE, SWIFTSPEAR, DRC, CACOPHONY}
BURN_SPELLS= {CHAIN, BOLT, RIFT_BOLT, SEARING_BLAZE, GALVANIC, PRICE, FIREBLAST}

class MonoRedAggroAPL(BaseAPL):
    name = "Mono Red Aggro"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands  = sum(1 for c in hand if c.is_land())
        ones   = sum(1 for c in hand if c.name in ONE_DROPS)
        burns  = sum(1 for c in hand if c.name in BURN_SPELLS)
        if lands == 0: return False
        if lands <= 1 and ones + burns >= 4: return True  # 1-land burn hands
        if lands >= 2 and (ones >= 1 or burns >= 2): return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[2:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        # 1-drops
        for name in (GOBLIN_GUIDE, SWIFTSPEAR, DRC, CACOPHONY, EIDOLON, SLICKSHOT):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break
        # Burn face
        for card in list(gs.hand()):
            if card.name in BURN_SPELLS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                dmg = 4 if card.name in {PRICE, FIREBLAST} else 3
                gs.damage_dealt += dmg
                gs.hand().remove(card)
                gs.zones.graveyard.append(card)
                gs._log(f"  {card.name} → face ({dmg})")
                break
        # Light Up the Stage
        for card in list(gs.hand()):
            if card.name == LIGHT_UP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
