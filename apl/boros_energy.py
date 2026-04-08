"""
apl/boros_energy.py — Boros Energy APL (Modern)

Deck: Ocelot Pride + Guide of Souls energy engine with Ragavan + Phlage top end.
Kill clock: T3.8 avg (can kill T2-3 with good hands)

Priority order:
  T1: Ragavan > Guide of Souls > Ocelot Pride
  T2: Ocelot Pride > Ajani > Seasoned Pyromancer > Guide of Souls
  T3: Phlage > Seasoned Pyromancer > Ajani > pump + attack
  Combat: attack every turn, use energy for +2/+2 flying via Guide of Souls

Key mechanic: Ocelot Pride creates Cat tokens whenever we cast a noncreature spell.
Goblin Bombardment = sacrifice outlet to push through damage.
"""

from apl.base_apl import BaseAPL
from data.card import Card, Tag
from engine.game_state import GameState

RAGAVAN       = "Ragavan, Nimble Pilferer"
GUIDE         = "Guide of Souls"
OCELOT        = "Ocelot Pride"
AJANI         = "Ajani, Nacatl Pariah"
PYROMANCER    = "Seasoned Pyromancer"
PHLAGE        = "Phlage, Titan of Fire's Fury"
VOICE         = "Voice of Victory"
GALVANIC      = "Galvanic Discharge"
BOMBARDMENT   = "Goblin Bombardment"
THRABEN       = "Thraben Charm"
BLOOD_MOON    = "Blood Moon"
STATIC_PRISON = "Static Prison"


class BorosEnergyAPL(BaseAPL):
    """
    Boros Energy — energy-based Ocelot Pride aggro.
    Aggressive curve, pump creatures with Guide of Souls energy.
    """

    name = "Boros Energy"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands    = sum(1 for c in hand if c.is_land())
        threats  = sum(1 for c in hand if c.name in {RAGAVAN, GUIDE, OCELOT, AJANI})
        has_phlage = any(c.name == PHLAGE for c in hand)

        if lands == 0: return False
        if lands == 1 and len(hand) >= 6 and not (threats >= 2): return False
        if lands >= 2 and (threats >= 1 or has_phlage): return True
        if len(hand) <= 5 or mulligans >= 2: return True
        return lands >= 2 and sum(1 for c in hand if not c.is_land()) >= 2

    def bottom(self, hand, n):
        lands = [c for c in hand if c.is_land()]
        extra_lands = lands[3:] if len(lands) > 3 else []
        slow = [c for c in hand if c.name in {BLOOD_MOON, BOMBARDMENT} and len(lands) < 3]
        return (extra_lands + slow)[:n]

    def main_phase(self, gs: GameState):
        self._play_land_if_able(gs)
        mana = gs.mana_pool.available()

        # T1 priority: Ragavan > Guide > Ocelot
        for name in (RAGAVAN, GUIDE, OCELOT):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # T2+ priority: Ocelot > Ajani > Pyromancer > Guide
        for name in (OCELOT, AJANI, PYROMANCER, GUIDE):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # T3+ threats
        for name in (PHLAGE, VOICE, STATIC_PRISON):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # Removal/pump if mana left
        for card in list(gs.hand()):
            if card.name in {GALVANIC, THRABEN} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                # Use as face damage if we have creatures swinging
                if len([c for c in gs.battlefield() if not c.is_land()]) >= 2:
                    gs.damage_dealt += 2
                    gs.hand().remove(card)
                    gs.zones.graveyard.append(card)
                    gs._log(f"  {card.name} → face (2 dmg)")
                break

    def main_phase2(self, gs: GameState):
        # Post-combat: deploy Goblin Bombardment if we have tokens
        for card in list(gs.hand()):
            if card.name == BOMBARDMENT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
