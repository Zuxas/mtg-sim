"""
stoneforge.py — APL for Legacy Stoneforge Midrange (UW)

Win condition: Stoneforge Mystic → Batterskull / Kaldra Compleat
then beat down behind Force of Will + Swords to Plowshares

Turn sequence:
  T1: Brainstorm / Ponder to set up
  T2: Stoneforge Mystic → fetch Batterskull or Kaldra
  T3: SFM ability: put equipment into play for {1}{W}
  T4+: Attack with 4/4 lifelink vigilance Germ, protect with counters
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from apl.mulligan import generic_bottom
from engine.keywords import KWTag


EQUIPMENT  = {"Batterskull", "Kaldra Compleat", "Umezawa's Jitte"}
COUNTERS   = {"Force of Will", "Counterspell", "Flusterstorm", "Spell Pierce"}
REMOVAL    = {"Swords to Plowshares", "Council's Judgment", "Path to Exile"}
CANTRIPS   = {"Brainstorm", "Ponder", "Preordain"}
THREATS    = {"Stoneforge Mystic", "Snapcaster Mage", "Batterskull"}


class StoneforgeAPL(BaseAPL):

    name = "Stoneforge Midrange"
    win_condition_damage = 20
    max_turns = 12

    def keep(self, hand, mulligans, on_play):
        lands   = [c for c in hand if c.is_land()]
        sfm     = [c for c in hand if c.name == "Stoneforge Mystic"]
        equip   = [c for c in hand if c.name in EQUIPMENT]
        cantrip = [c for c in hand if c.name in CANTRIPS]
        size = len(hand)

        if size <= 4: return True
        lc = len(lands)
        if lc == 0 and not cantrip: return False
        if lc >= 5: return size <= 5

        has_action = bool(sfm or cantrip or equip)
        if lc >= 2 and has_action: return True
        if lc >= 1 and bool(sfm): return True  # SFM is so strong
        if mulligans >= 3: return lc >= 1
        return lc >= 2

    def bottom(self, hand, n):
        return generic_bottom(hand, n)

    def main_phase(self, gs: GameState):
        """
        Stoneforge priority:
          1. Land (needs 3+ for SFM ability)
          2. Cantrips (set up hand)
          3. Stoneforge Mystic (fetch best equipment)
          4. Use SFM ability to cheat equipment into play
          5. Snapcaster Mage (flash back removal/cantrip)
          6. Removal on opponent threats (no targets in goldfish, skip)
        """
        self._play_land_if_able(gs)

        # Cantrips first
        self._resolve_cantrips(gs)

        # Stoneforge Mystic
        for c in list(gs.hand()):
            if c.name == "Stoneforge Mystic" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Fetch best equipment from library
                target = next((l for l in gs.zones.library
                               if l.name == "Batterskull"), None) or \
                         next((l for l in gs.zones.library
                               if l.name in EQUIPMENT), None)
                if target:
                    gs.cast_spell(c)
                    gs.zones.library.remove(target)
                    gs.zones.hand.append(target)
                    gs._log(f"  Stoneforge Mystic → {target.name} to hand")
                break

        # SFM ability: {1}{W}, tap → put equipment into play
        sfm_in_play = any(c.name == "Stoneforge Mystic" for c in gs.zones.battlefield)
        if sfm_in_play and gs.mana_pool.can_pay("{1}{W}", 2):
            equip_in_hand = [c for c in gs.hand() if c.name in EQUIPMENT]
            if equip_in_hand:
                equip = equip_in_hand[0]
                gs.mana_pool.pay("{1}{W}", 2)
                gs.zones.hand.remove(equip)
                # Create equipped Germ token with Batterskull stats
                if equip.name == "Batterskull":
                    germ = Card(
                        name="Germ + Batterskull",
                        mana_cost="",
                        cmc=0,
                        type_line="Creature — Germ",
                        oracle_text="Lifelink, vigilance",
                        power="4", toughness="4",
                        colors=[],
                    )
                    germ.tags.add(Tag.CREATURE)
                    germ.tags.add(KWTag.LIFELINK)
                    germ.tags.add(KWTag.VIGILANCE)
                    germ.summoning_sickness = True
                    gs.zones.battlefield.append(germ)
                    gs._log("  SFM ability → Batterskull: 4/4 lifelink vigilance Germ")
                elif equip.name == "Kaldra Compleat":
                    kaldra = Card(
                        name="Germ + Kaldra Compleat",
                        mana_cost="",
                        cmc=0,
                        type_line="Creature — Germ",
                        oracle_text="First strike, trample, lifelink, haste, indestructible",
                        power="5", toughness="5",
                        colors=[],
                    )
                    kaldra.tags.add(Tag.CREATURE)
                    kaldra.tags.add(KWTag.FIRST_STRIKE)
                    kaldra.tags.add(KWTag.TRAMPLE)
                    kaldra.tags.add(KWTag.LIFELINK)
                    kaldra.tags.add(KWTag.HASTE)
                    kaldra.tags.add(KWTag.INDESTRUCTIBLE)
                    kaldra.summoning_sickness = False  # has haste
                    gs.zones.battlefield.append(kaldra)
                    gs._log("  SFM ability → Kaldra: 5/5 haste first strike trample indestructible")

        # Snapcaster Mage — flash back a cantrip/removal from graveyard
        for c in list(gs.hand()):
            if c.name == "Snapcaster Mage" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                targets = [g for g in gs.zones.graveyard
                           if g.name in CANTRIPS]
                if targets:
                    gs.cast_spell(c)
                    # Flash back a cantrip
                    target = targets[0]
                    gs.zones.graveyard.remove(target)
                    gs.zones.draw(1)
                    gs.zones.graveyard.append(target)
                break

    def main_phase2(self, gs: GameState):
        """Post-combat: flash spells, remaining cantrips."""
        self._resolve_cantrips(gs)
