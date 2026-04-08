"""
apl/tempo.py — Dimir Tempo APL (Force of Will + Murktide)

Models the tempo play pattern:
  T1: Ragavan / DRC / Thoughtseize
  T2: Daze anything they play, continue developing
  T3: Murktide Regent (cheap from filled GY)
  T4+: Attack with Murktide, hold up Force of Will

The key mechanic: holds interaction mana open while developing threats.
"""

from apl.base_apl import BaseAPL
from data.card import Card, Tag
from engine.game_state import GameState


RAGAVAN    = "Ragavan, Nimble Pilferer"
DRC        = "Dragon's Rage Channeler"
MURKTIDE   = "Murktide Regent"
DELVER     = "Delver of Secrets"
FOW        = "Force of Will"
DAZE       = "Daze"
BOLT       = "Lightning Bolt"
BRAINSTORM = "Brainstorm"
PONDER     = "Ponder"
THOUGHTSEIZE = "Thoughtseize"
WASTELAND  = "Wasteland"
SNAP       = "Snapcaster Mage"

ONE_DROPS  = {RAGAVAN, DRC, DELVER}
TWO_DROPS  = {SNAP, DAZE}
BIG_THREATS = {MURKTIDE}


class DimirTempoAPL(BaseAPL):
    """
    Dimir Tempo — tempo threats backed by Force of Will and Daze.
    Plays proactively on its own turn, holds up interaction.
    """

    name = "Dimir Tempo"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        if len(hand) <= 4:
            return True
        lands   = sum(1 for c in hand if c.is_land())
        threats = sum(1 for c in hand if c.name in ONE_DROPS | BIG_THREATS)
        has_fow = any(c.name == FOW for c in hand)

        if lands == 0:
            return False
        if lands >= 2 and (threats >= 1 or has_fow):
            return True
        if len(hand) <= 5 or mulligans >= 2:
            return True
        return False

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        lands  = [c for c in hand if c.is_land()]
        excess = lands[2:] + [c for c in hand
                               if c.name in {THOUGHTSEIZE} and len(lands) < 2]
        return excess[:n]

    def main_phase(self, gs: GameState):
        # 1. Land
        self._play_land_if_able(gs)
        mana = gs.mana_pool.available()

        # 2. Thoughtseize T1 (strip their best card)
        if gs.turn == 1:
            for card in list(gs.hand()):
                if card.name == THOUGHTSEIZE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    gs._log("  Thoughtseize → stripped their best card")
                    break

        # 3. One-drops: Ragavan > DRC > Delver
        for name in (RAGAVAN, DRC, DELVER):
            for card in list(gs.hand()):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # 4. Hold up 1 mana for Daze if early turns
        mana_after_threats = gs.mana_pool.available()
        hold_for_daze = gs.turn <= 3 and mana_after_threats >= 1

        # 5. Murktide — play once we have enough spells in GY (T3+)
        spells_in_gy = len([c for c in gs.zones.graveyard
                             if not c.is_land()])
        murktide_cmc = max(1, 7 - spells_in_gy * 2)   # reduces by 2 per spell

        if not hold_for_daze or mana_after_threats >= murktide_cmc + 1:
            for card in list(gs.hand()):
                if card.name == MURKTIDE and mana_after_threats >= murktide_cmc:
                    gs.cast_spell(card)
                    break

        # 6. Cantrips to fill GY and find threats
        for card in list(gs.hand()):
            if card.name in {BRAINSTORM, PONDER} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                if not hold_for_daze or gs.mana_pool.available() >= 2:
                    gs.cast_spell(card)
                    break

        # 7. Lightning Bolt if mana available
        for card in list(gs.hand()):
            if card.name == BOLT and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.damage_dealt += 3   # bolting their face
                gs.hand().remove(card)
                gs.zones.graveyard.append(card)
                gs._log("  Lightning Bolt → face (3 dmg)")
                break
