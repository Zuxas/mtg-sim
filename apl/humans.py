"""
humans.py — APL for Legacy Humans

Field context: Lands, Delver, Elves, Painter, Stoneforge, Golgari Hogaak

Humans is a tribal aggro deck. Priority order:
  1. Play a land (always)
  2. Play Aether Vial if in opening hand or T1
  3. Play Champion of the Parish / Thalia's Lieutenant (lord payoffs)
  4. Fill mana curve with cheapest creature first
  5. Don't over-extend — stop at 4 creatures if mana is gone

Keep criteria:
  - Must have 2-3 lands
  - Must have at least 1 one-drop or Aether Vial
  - On the draw: slightly more lenient (can keep 2-land hand with curve)

Bottoming priority:
  - Bottom excess lands over 3
  - Bottom Reflector Mage / Mantis Rider over 1-drops on fewer mulligans
"""

from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL


# Card name constants — avoids magic strings scattered through logic
AETHER_VIAL         = "Aether Vial"
CHAMPION            = "Champion of the Parish"
LIEUTENANT          = "Thalia's Lieutenant"
THALIA              = "Thalia, Guardian of Thraben"
ADELINE             = "Adeline, Resplendent Cathar"
KYTHEON             = "Kytheon, Hero of Akros"
URDNAN              = "Urdnan, Dromoka Warrior"
VOICE_OF_VICTORY    = "Voice of Victory"
COPPERCOAT          = "Coppercoat Vanguard"
MANTIS_RIDER        = "Mantis Rider"
REFLECTOR_MAGE      = "Reflector Mage"
MILITIA_BUGLER      = "Militia Bugler"
IMPERIAL_RECRUITER  = "Imperial Recruiter"
MEDDLING_MAGE       = "Meddling Mage"
PHANTASMAL_IMAGE    = "Phantasmal Image"
KITESAIL_FREEBOOTER = "Kitesail Freebooter"
CAVERN_OF_SOULS     = "Cavern of Souls"
ANCIENT_ZIGGURAT    = "Ancient Ziggurat"


class HumansAPL(BaseAPL):

    name = "Legacy Humans"
    win_condition_damage = 20
    max_turns = 12

    # -----------------------------------------------------------------------
    # Mulligan
    # -----------------------------------------------------------------------

    def keep(self, hand: list[Card], mulligans: int, on_play: bool) -> bool:
        lands  = [c for c in hand if c.is_land()]
        ones   = [c for c in hand if c.has(Tag.ONE_DROP) and not c.is_land()]
        twos   = [c for c in hand if c.has(Tag.TWO_DROP) and not c.is_land()]
        vialed = [c for c in hand if c.name == AETHER_VIAL]
        land_count = len(lands)
        size = len(hand)

        # Always keep tiny hands
        if size <= 4:
            return True

        # Never keep 0-land hands of 5+
        if land_count == 0:
            return False

        # Never keep 1-land hands unless desperate (size 5 or lots of mulligans)
        if land_count == 1:
            return size <= 5 or mulligans >= 3

        # Never keep flood (5+ lands in 7, 4+ in 6, 3+ in 5)
        max_lands = {7: 4, 6: 3, 5: 3}.get(size, 3)
        if land_count > max_lands:
            return False

        # 2-land hand: need early action (1-drop, Vial, or Champion/Lieutenant)
        if land_count == 2:
            lords = [c for c in hand if c.name in (CHAMPION, LIEUTENANT)]
            has_action = bool(ones or vialed or lords)
            # On the play: need a 1-drop or Vial
            if on_play:
                return bool(ones or vialed)
            # On the draw: 2-drop is enough
            return has_action or bool(twos)

        # 3-land hand: almost always keep — just need at least one non-land
        if land_count == 3:
            return (size - land_count) >= 1

        # 4-land hand in a 7: mull (already caught above)
        return True

    def bottom(self, hand: list[Card], n: int) -> list[Card]:
        """
        Bottom priority: excess lands → reactive/high-CMC spells → flex slots.
        Keep: 2-3 lands, 1-drops, Vial.
        """
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)

        to_bottom: list[Card] = []

        # Bottom lands beyond 3
        if len(lands) > 3:
            to_bottom.extend(lands[3:])

        # Bottom high-CMC spells (Mantis Rider, Reflector Mage) before 1-drops
        for card in spells:
            if len(to_bottom) >= n:
                break
            if card.cmc >= 3 and card.name not in (CHAMPION, LIEUTENANT):
                to_bottom.append(card)

        # Fill remainder with any remaining spell (highest CMC first)
        for card in spells:
            if len(to_bottom) >= n:
                break
            if card not in to_bottom:
                to_bottom.append(card)

        return to_bottom[:n]

    # -----------------------------------------------------------------------
    # Main phase APL
    # -----------------------------------------------------------------------

    def main_phase(self, gs: GameState):
        """
        Humans APL priority:
          1. Play land
          2. Cast Aether Vial (T1, if not in play)
          3. Deploy via Vial (end of opponent's turn is ideal, but goldfish = main phase)
          4. Lords first (Champion, Lieutenant, Thalia)
          5. Fill curve — cheapest non-Image creature first
          6. Phantasmal Image (only with a good copy target)
          7. Non-creature spells
        """
        # 1. Land drop
        self._play_land_if_able(gs)

        # 2. Aether Vial — cast on T1 if none in play
        vials_in_play = sum(1 for c in gs.battlefield() if c.name == AETHER_VIAL)
        if vials_in_play == 0:
            for card in gs.hand():
                if card.name == AETHER_VIAL and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # 3. Deploy via Vial (treat as main phase deploy for goldfish purposes)
        vial = gs.vial_in_play()
        if vial and vial.counters > 0:
            viallable = gs.castable_via_vial()
            if viallable:
                # Prioritize: lords first, then by CMC
                def vial_priority(c):
                    if c.name == CHAMPION:           return 0
                    if c.name == LIEUTENANT:         return 1
                    if c.name == THALIA:             return 2
                    if c.name == KITESAIL_FREEBOOTER: return 3
                    if c.name == MEDDLING_MAGE:      return 4
                    return 5
                target = min(viallable, key=vial_priority)
                gs.put_via_vial(target, vial)

        # 4. Lords + key threats in priority order:
        # Kytheon (1-drop that flips to 4/4) → Champion → Lieutenant → Thalia
        # Coppercoat Vanguard (anthem for all Humans) → Urdnan (ETB pump) → Adeline
        for priority_name in (CHAMPION, LIEUTENANT, KYTHEON, THALIA,
                              COPPERCOAT, URDNAN, ADELINE, VOICE_OF_VICTORY):
            for card in list(gs.hand()):
                if card.name == priority_name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # 5. Fill curve — cheapest non-Image creature first
        while True:
            creatures = [
                c for c in gs.hand()
                if c.has(Tag.CREATURE)
                and c.name != PHANTASMAL_IMAGE
                and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            ]
            if not creatures:
                break
            card = min(creatures, key=lambda c: (c.cmc, c.name))
            if not gs.cast_spell(card):
                break

        # 6. Phantasmal Image — only with a worthwhile copy target
        best_target = max(
            [c for c in gs.battlefield() if c.has(Tag.CREATURE)],
            key=lambda c: c.effective_power(),
            default=None
        )
        if best_target and best_target.effective_power() >= 2:
            for card in list(gs.hand()):
                if card.name == PHANTASMAL_IMAGE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

        # 7. Non-creature spells
        while True:
            others = [
                c for c in gs.hand()
                if not c.is_land()
                and not c.has(Tag.CREATURE)
                and c.name != AETHER_VIAL
                and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            ]
            if not others:
                break
            card = min(others, key=lambda c: c.cmc)
            if not gs.cast_spell(card):
                break

        # 5. Non-creature spells (discard, disruption) if mana left
        while True:
            others = [
                c for c in gs.hand()
                if not c.is_land()
                and not c.has(Tag.CREATURE)
                and c.name != AETHER_VIAL
                and gs.mana_pool.can_cast(c.mana_cost, c.cmc)
            ]
            if not others:
                break
            card = min(others, key=lambda c: c.cmc)
            if not gs.cast_spell(card):
                break
