"""apl/izzet_phoenix.py — Izzet Phoenix APL (Pioneer)
Arclight Phoenix self-mill + cheap spells to bring back from GY.
Kill clock: T3-4 via Phoenix recursion + Sprite Dragon.
"""
from apl.base_apl import BaseAPL
from engine.game_state import GameState

PHOENIX   = "Arclight Phoenix"
DRAGON    = "Sprite Dragon"
DRC       = "Dragon's Rage Channeler"
CONSIDER  = "Consider"
PREORDAIN = "Preordain"
IMPULSE   = "Impulse"
FIERY     = "Fiery Impulse"
BOLT      = "Lightning Bolt"
LAVA_COIL = "Lava Coil"
LEDGER    = "Ledger Shredder"

SPELLS_0_1 = {CONSIDER, PREORDAIN, FIERY, BOLT, IMPULSE}

class IzzetPhoenixAPL(BaseAPL):
    name = "Izzet Phoenix"
    win_condition_damage = 20
    max_turns = 10

    def __init__(self):
        self._phoenix_in_gy = False
        self._spells_this_turn = 0

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands   = sum(1 for c in hand if c.is_land())
        has_phoenix = any(c.name == PHOENIX for c in hand)
        has_enabler = sum(1 for c in hand if c.name in SPELLS_0_1)
        has_threat  = any(c.name in {DRAGON, DRC, LEDGER} for c in hand)
        if lands == 0: return False
        if lands >= 2 and (has_phoenix or has_threat) and has_enabler >= 1: return True
        if lands >= 2 and has_enabler >= 3: return True  # cantrip pile
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        return lands[3:][:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        self._spells_this_turn = 0
        # Deploy threats
        for name in (DRC, LEDGER, DRAGON):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    self._spells_this_turn += 1
                    break
        # Cast cheap spells to trigger Phoenix recursion
        for card in list(gs.hand()):
            if card.name in SPELLS_0_1 and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                self._spells_this_turn += 1
                if card.name in {FIERY, BOLT}:
                    gs.damage_dealt += 2
                    gs._log(f"  {card.name} → face")
                # 3 spells → bring back Phoenix
                if self._spells_this_turn >= 3 and not self._phoenix_in_gy:
                    self._phoenix_in_gy = True
                if self._spells_this_turn >= 3 and self._phoenix_in_gy:
                    token = gs._make_token("Arclight Phoenix", "3", "2", "Creature")
                    token.summoning_sickness = False
                    gs._log("  Arclight Phoenix returns from GY (3 spells)")
                    self._phoenix_in_gy = False
                break
        # Phoenix itself (discard to GY via looting)
        for card in list(gs.hand()):
            if card.name == PHOENIX and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
