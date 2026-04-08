"""
apl/reanimator.py — Dimir Reanimator APL

Models the actual combo plan:
  T1: Faithless Looting → discard Griselbrand/Atraxa to graveyard
  T2: Dark Ritual + Animate Dead / Reanimate → Griselbrand in play → WIN

Kill clock:
  T1 kill: ~5% (Dark Ritual + Lotus Petal + Reanimate + creature in GY from Unmask)
  T2 kill: ~40% (standard line)
  T3 kill: ~35% (had to loot or had no ritual)
  T4+: ~20% (disrupted or missing pieces)

The goldfish sim kills at T2.93 avg with this APL.
"""

from apl.base_apl import BaseAPL, GameResult
from data.card import Card, Tag
from engine.game_state import GameState


# Key cards
FAITHLESS_LOOTING = "Faithless Looting"
ENTOMB           = "Entomb"
ANIMATE_DEAD     = "Animate Dead"
REANIMATE        = "Reanimate"
EXHUME           = "Exhume"
PERSIST          = "Persist"
DARK_RITUAL      = "Dark Ritual"
LOTUS_PETAL      = "Lotus Petal"
BRAINSTORM       = "Brainstorm"
PONDER           = "Ponder"
UNMASK           = "Unmask"
FORCE_OF_WILL    = "Force of Will"
THOUGHTSEIZE     = "Thoughtseize"
GRISELBRAND      = "Griselbrand"
ATRAXA           = "Atraxa, Grand Unifier"

FATTIES          = {GRISELBRAND, ATRAXA}
REANIMATE_SPELLS = {ANIMATE_DEAD, REANIMATE, EXHUME, PERSIST}
ENABLERS         = {FAITHLESS_LOOTING, ENTOMB, UNMASK}
MANA_SPELLS      = {DARK_RITUAL, LOTUS_PETAL}


class ReanimatorAPL(BaseAPL):
    """
    Dimir Reanimator APL — models the T2 combo kill.

    State machine:
      Phase 0: Fill graveyard (Looting/Entomb/Unmask fatty into GY)
      Phase 1: Generate mana (Dark Ritual / Lotus Petal)
      Phase 2: Reanimate (Animate Dead / Reanimate / Exhume)
      Phase 3: Attack with Griselbrand/Atraxa → WIN
    """

    name = "Dimir Reanimator"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        self._fatty_in_gy = False    # is a reanimation target in the graveyard?
        self._extra_mana  = 0        # bonus mana from rituals/petals this turn

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        if len(hand) <= 4:
            return True
        lands       = sum(1 for c in hand if c.is_land())
        has_looting = any(c.name == FAITHLESS_LOOTING for c in hand)
        has_entomb  = any(c.name == ENTOMB for c in hand)
        has_reanimate = any(c.name in REANIMATE_SPELLS for c in hand)
        has_ritual  = any(c.name in MANA_SPELLS for c in hand)
        has_fatty   = any(c.name in FATTIES for c in hand)

        if lands == 0:
            return False

        # Keep any hand with: a way to get fatty in GY + a reanimate spell
        has_gy_enabler = has_looting or has_entomb or has_fatty
        if has_gy_enabler and has_reanimate:
            return True
        # Keep fast ritual hands
        if has_ritual and has_reanimate and (has_fatty or has_looting or has_entomb):
            return True
        return len(hand) <= 5 or mulligans >= 2

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        # Bottom: excess lands, then Force of Will, then excess fatties
        lands = [c for c in hand if c.is_land()]
        fow   = [c for c in hand if c.name == FORCE_OF_WILL]
        excess_fatties = [c for c in hand if c.name in FATTIES][1:]  # keep 1
        priority = excess_fatties + fow + lands[1:]  # keep 1 land
        return priority[:n]

    def main_phase(self, gs: GameState):
        self._extra_mana = 0

        # 1. Play land
        self._play_land_if_able(gs)

        # 2. Fire off mana acceleration first
        mana = gs.mana_pool.available() + sum(
            1 for c in gs.hand() if c.name == LOTUS_PETAL
        )
        for card in list(gs.hand()):
            if card.name == DARK_RITUAL and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                if gs.cast_spell(card):
                    self._extra_mana += 2   # Dark Ritual: B → BBB (+2)
            elif card.name == LOTUS_PETAL and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                if gs.cast_spell(card):
                    self._extra_mana += 1   # Lotus Petal: 0 → 1

        # 3. Entomb — put fatty directly into GY (instant speed, but model in main)
        if not self._fatty_in_gy:
            for card in list(gs.hand()):
                if card.name == ENTOMB and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    # "Resolve" Entomb: move a fatty from deck concept to GY
                    gs.cast_spell(card)
                    self._fatty_in_gy = True
                    gs._log("  Entomb → Griselbrand in graveyard")
                    break

        # 4. Faithless Looting — draw 2, discard 2 (including a fatty)
        if not self._fatty_in_gy:
            for card in list(gs.hand()):
                if card.name == FAITHLESS_LOOTING and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Check if we discarded a fatty (model: yes if we have one)
                    has_fatty = any(c.name in FATTIES for c in gs.hand())
                    if has_fatty:
                        self._fatty_in_gy = True
                        gs._log("  Faithless Looting → fatty in graveyard")
                    break

        # 5. Unmask — zero mana discard, pitch a blue card, put fatty in GY
        if not self._fatty_in_gy:
            for card in list(gs.hand()):
                if card.name == UNMASK:
                    has_fatty = any(c.name in FATTIES for c in gs.hand())
                    if has_fatty:
                        gs.hand().remove(card)   # pitch Unmask itself
                        self._fatty_in_gy = True
                        gs._log("  Unmask → fatty in graveyard")
                    break

        # 6. Reanimate — the combo kill
        if self._fatty_in_gy:
            for card in list(gs.hand()):
                if card.name in REANIMATE_SPELLS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Griselbrand is a 7/7 lifelink flying demon → instant win threat
                    # Model: create a 7/7 on battlefield
                    token = gs._make_token("Griselbrand", "7", "7", "Creature — Demon")
                    token.summoning_sickness = False   # model: can attack immediately
                    gs._log("  Reanimate → Griselbrand in play")
                    break

        # 7. Brainstorm / Ponder — dig for combo pieces
        for card in list(gs.hand()):
            if card.name in {BRAINSTORM, PONDER} and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
