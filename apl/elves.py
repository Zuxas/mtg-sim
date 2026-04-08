"""
elves.py — APL for Legacy Elves

Win condition: Heritage Druid mana engine → Natural Order → Craterhoof Behemoth
or go-wide with enough elves.

Turn sequence:
  T1: Mana dork (Llanowar Elves / Elvish Mystic)
  T2: Heritage Druid + more elves → tap 3 for GGG → chain
  T3+: Natural Order or enough elves for lethal swing

Keep criteria:
  - At least 1 forest/mana source
  - At least 1 elf
  - Natural Order hands are keepable even with 1 land + elves
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from apl.mulligan import generic_bottom


ONE_DROPS = {"Llanowar Elves", "Elvish Mystic", "Fyndhorn Elves", "Deathrite Shaman"}
LORDS     = {"Elvish Archdruid", "Ezuri, Renegade Leader", "Joraga Warcaller"}
ENGINE    = {"Heritage Druid", "Nettle Sentinel", "Wirewood Symbiote"}
PAYOFFS   = {"Natural Order", "Glimpse of Nature", "Progenitus", "Craterhoof Behemoth"}
TUTORS    = {"Green Sun's Zenith", "Chord of Calling"}


class ElvesAPL(BaseAPL):

    name = "Elves"
    win_condition_damage = 20
    max_turns = 10

    def keep(self, hand, mulligans, on_play):
        lands   = [c for c in hand if c.is_land()]
        elves   = [c for c in hand if c.has(Tag.CREATURE)]
        orders  = [c for c in hand if c.name == "Natural Order"]
        size    = len(hand)

        if size <= 4:
            return True
        if not lands and not any(c.name in ONE_DROPS for c in hand):
            return False
        if len(lands) == 0 and len(elves) >= 3:
            return True   # sometimes keepable with GSZ / Chord
        if len(lands) >= 4:
            return size <= 5
        # Good: land + mana dork + something
        has_one = any(c.name in ONE_DROPS for c in hand)
        has_engine = any(c.name in ENGINE for c in hand)
        if len(lands) >= 1 and (has_one or has_engine):
            return True
        if mulligans >= 3:
            return True
        return len(lands) >= 1 and len(elves) >= 2

    def bottom(self, hand, n):
        return generic_bottom(hand, n)

    def main_phase(self, gs: GameState):
        """
        Elves priority:
          1. Land
          2. Mana dorks (Llanowar/Mystic) first
          3. Heritage Druid (enables the mana engine)
          4. More elves to enable Heritage Druid tap
          5. Natural Order (tutors Craterhoof/Progenitus)
          6. Lords and payoffs
        """
        self._play_land_if_able(gs)

        # 2. One-drop mana dorks
        for c in sorted(gs.hand(), key=lambda c: c.cmc):
            if c.name in ONE_DROPS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # 3. Heritage Druid (key engine piece)
        for c in list(gs.hand()):
            if c.name == "Heritage Druid" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # 4. Elves in play → Heritage Druid mana generation
        # If we have Heritage Druid + 2 other elves, tap for GGG
        self._activate_heritage_druid(gs)

        # 5. Cast more elves with generated mana
        while True:
            creatures = [c for c in gs.hand()
                         if c.has(Tag.CREATURE) and not c.is_land()
                         and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if not creatures:
                break
            card = min(creatures, key=lambda c: c.cmc)
            if not gs.cast_spell(card):
                break
            # Re-activate Heritage Druid after each elf
            self._activate_heritage_druid(gs)

        # 6. Natural Order — sacrifice any green creature, get Craterhoof/Progenitus
        for c in list(gs.hand()):
            if c.name == "Natural Order" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                green_creatures = [p for p in gs.zones.battlefield
                                   if p.has(Tag.CREATURE) and "G" in p.colors]
                if green_creatures:
                    # Sacrifice cheapest, get best creature
                    sac = min(green_creatures, key=lambda c: c.cmc)
                    gs.zones.destroy(sac)
                    # "Find" Craterhoof/Progenitus
                    target = next((l for l in gs.zones.library
                                   if l.name in ("Craterhoof Behemoth", "Progenitus")), None)
                    if target:
                        gs.zones.library.remove(target)
                        gs.zones.battlefield.append(target)
                        gs.cast_spell(c) if c in gs.zones.hand else None
                        gs._log(f"  Natural Order → {target.name}")

        # 7. Lords
        for c in list(gs.hand()):
            if c.name in LORDS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

    def _activate_heritage_druid(self, gs: GameState):
        """
        Heritage Druid: tap 3 elves → GGG.
        Fires in a loop — each activation enables more elf casts.
        """
        druid = next((c for c in gs.zones.battlefield
                      if c.name == "Heritage Druid"), None)
        if not druid:
            return

        # Count untapped elves (all elves since we simplified tap tracking)
        elves = [c for c in gs.zones.battlefield
                 if c.has(Tag.CREATURE) and (
                     "elf" in c.type_line.lower() or
                     c.name in ONE_DROPS or
                     c.name in ENGINE
                 )]

        # Each group of 3 elves generates GGG
        activations = len(elves) // 3
        if activations > 0:
            for _ in range(activations):
                gs.mana_pool.add("G")
                gs.mana_pool.add("G")
                gs.mana_pool.add("G")
            gs._log(f"  Heritage Druid: {activations}x activation = {activations*3}G "
                    f"({len(elves)} elves in play)")

    def main_phase2(self, gs: GameState):
        """Post-combat: cast any remaining spells."""
        self._cast_all_castable(gs)
