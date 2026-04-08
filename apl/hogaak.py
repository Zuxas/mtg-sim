"""
hogaak.py — APL for Golgari Hogaak (Legacy)

Win condition: Fill graveyard T1 → convoke + delve cast Hogaak T2
Attack for 8+ with Hogaak + Vengevines returning

Turn sequence:
  T1: Stitcher's Supplier (mill 3) + Putrid Imp / Carrion Feeder
  T2: Cast Hogaak (convoke 2 creatures + delve 7 cards in GY)
      Vengevines return (if 2 creatures cast this turn)
  T3: Attack for lethal (8 Hogaak + 4+4 Vengevines = 16+)

Keep criteria:
  - At least 1 black/green land
  - Stitcher's Supplier OR a discard outlet (Putrid Imp, Faithless Looting)
  - Either Hogaak in hand or Vengevines to return
"""

from data.card import Card, Tag
from engine.game_state import GameState
from apl.base_apl import BaseAPL
from apl.mulligan import generic_bottom


HOGAAK_NAMES    = {"Hogaak, Arisen Necropolis", "Hogaak Arisen Necropolis"}
DISCARD_OUTLETS = {"Putrid Imp", "Faithless Looting", "Cabal Therapy"}
SUPPLIER_NAMES  = {"Stitcher's Supplier", "Stitcher Supplier"}
GRAVEYARD_FILL  = SUPPLIER_NAMES | {"Altar of Dementia", "Darkblast"}
RECURSIVE       = {"Vengevine", "Gravecrawler"}
PAYOFFS         = HOGAAK_NAMES


class HogaakAPL(BaseAPL):

    name = "Golgari Hogaak"
    win_condition_damage = 20
    max_turns = 8

    def keep(self, hand, mulligans, on_play):
        lands    = [c for c in hand if c.is_land()]
        supplier = [c for c in hand if c.name in SUPPLIER_NAMES]
        outlet   = [c for c in hand if c.name in DISCARD_OUTLETS]
        hogaak   = [c for c in hand if c.name == "Hogaak, Arisen Necropolis"]
        vine     = [c for c in hand if c.name == "Vengevine"]
        feeder   = [c for c in hand if c.name == "Carrion Feeder"]
        size = len(hand)

        if size <= 4: return True

        has_mana = len(lands) >= 1
        has_engine = bool(supplier or outlet)
        has_payload = bool(hogaak or vine or feeder)

        if not has_mana: return False
        if has_mana and has_engine: return True
        if has_mana and has_payload and bool(outlet): return True
        if mulligans >= 3: return has_mana
        return len(lands) >= 1 and has_engine

    def bottom(self, hand, n):
        # Keep: Supplier, discard outlets, Hogaak, Vengevine
        # Bottom: excess lands, high-CMC cards we don't need
        to_bottom = []
        spells = sorted([c for c in hand if not c.is_land()], key=lambda c: -c.cmc)
        lands = [c for c in hand if c.is_land()]

        # Bottom excess lands
        if len(lands) > 2:
            excess = lands[2:]
            to_bottom.extend(excess[:n])

        # Bottom high-CMC spells that aren't payoffs
        for c in spells:
            if len(to_bottom) >= n: break
            if c.name not in {"Hogaak, Arisen Necropolis", "Vengevine",
                               "Stitcher's Supplier", "Carrion Feeder"}:
                if c not in to_bottom:
                    to_bottom.append(c)

        return to_bottom[:n]

    def main_phase(self, gs: GameState):
        """
        Hogaak priority:
          1. Land
          2. Stitcher's Supplier (mills 3 on ETB — do this first, multiple times if possible)
          3. Carrion Feeder (free sac outlet)
          4. Altar of Dementia (free sac engine for more milling)
          5. Putrid Imp / discard outlets (put Hogaak/Vengevines in GY)
          6. Faithless Looting (draw + fill GY)
          7. Gravecrawler
          8. Cast Hogaak once conditions met
          9. Check Vengevine returns
        """
        self._play_land_if_able(gs)

        # Cast ALL Suppliers immediately — each mills 3
        for c in list(gs.hand()):
            if c.name in SUPPLIER_NAMES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                milled = gs.zones.library[:3]
                gs.zones.library = gs.zones.library[3:]
                gs.zones.graveyard.extend(milled)
                gs._log(f"  Supplier mills: {[m.name for m in milled]}")

        # Carrion Feeder (0 mana, grows as creatures die)
        for c in list(gs.hand()):
            if c.name == "Carrion Feeder" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # Altar of Dementia — free artifact
        for c in list(gs.hand()):
            if c.name == "Altar of Dementia" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # Sac via Altar: use non-Hogaak, non-Vengevine creatures to mill
        altar = next((c for c in gs.zones.battlefield
                      if c.name == "Altar of Dementia"), None)
        if altar:
            sac_targets = sorted(
                [c for c in gs.zones.battlefield
                 if c.has(Tag.CREATURE)
                 and c.name not in {"Hogaak, Arisen Necropolis", "Vengevine", "Carrion Feeder"}],
                key=lambda c: c.effective_power()
            )
            for sac in sac_targets:
                power = sac.effective_power()
                if power > 0:
                    gs.zones.destroy(sac)
                    milled = gs.zones.library[:power]
                    gs.zones.library = gs.zones.library[power:]
                    gs.zones.graveyard.extend(milled)
                    gs._log(f"  Altar: sac {sac.name} → mill {power}")

        # Putrid Imp — discard Hogaak/Vengevines
        for c in list(gs.hand()):
            if c.name == "Putrid Imp" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                discard_targets = [h for h in gs.hand()
                                   if h.name in {"Hogaak, Arisen Necropolis", "Vengevine"}]
                for target in discard_targets[:2]:
                    gs.zones.hand.remove(target)
                    gs.zones.graveyard.append(target)
                    gs._log(f"  Putrid Imp: discard {target.name}")

        # Faithless Looting
        for c in list(gs.hand()):
            if c.name == "Faithless Looting" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                gs.zones.draw(2)
                discard_from = sorted(gs.zones.hand,
                    key=lambda c: 0 if c.name in {"Hogaak, Arisen Necropolis", "Vengevine"} else 1)
                for dc in discard_from[:2]:
                    gs.zones.hand.remove(dc)
                    gs.zones.graveyard.append(dc)

        # Gravecrawler
        for c in list(gs.hand()):
            if c.name == "Gravecrawler" and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # Try Hogaak
        self._try_cast_hogaak(gs)

        # Check Vengevine returns
        self._check_vengevine_return(gs)

    def _try_cast_hogaak(self, gs):
        """
        Hogaak costs: convoke 2 creatures + delve 7 cards.
        Relaxed: 2 creatures + 5+ cards in GY (we model delve cost as flexible).
        """
        hogaak_in_hand = [c for c in gs.hand()
                          if c.name == "Hogaak, Arisen Necropolis"]
        if not hogaak_in_hand:
            # Try to find Hogaak in graveyard (if it was discarded)
            hogaak_in_gy = [c for c in gs.zones.graveyard
                            if c.name == "Hogaak, Arisen Necropolis"]
            if not hogaak_in_gy:
                return
            # Cast from GY (Hogaak has "you may cast this from your graveyard")
            hogaak_in_hand = hogaak_in_gy
            from_gy = True
        else:
            from_gy = False

        creatures = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)]
        gy_cards  = len(gs.zones.graveyard)

        if len(creatures) >= 2 and gy_cards >= 5:
            hogaak = hogaak_in_hand[0]
            # Delve up to 7
            delve_count = min(7, gy_cards)
            for card in gs.zones.graveyard[:delve_count]:
                gs.zones.graveyard.remove(card)
                gs.zones.exile.append(card)
            if from_gy:
                gs.zones.graveyard.remove(hogaak)
            else:
                gs.zones.hand.remove(hogaak)
            hogaak.summoning_sickness = True
            gs.zones.battlefield.append(hogaak)
            gs._fire_etb_triggers(hogaak)
            gs._log(f"  Convoke + Delve: Hogaak enters (8/8 trample) from {'GY' if from_gy else 'hand'}")

    def _check_vengevine_return(self, gs):
        """
        Vengevine returns from GY when you cast 2+ creatures in a turn.
        Count creature spells cast this turn (simplified: check GY for recently cast).
        """
        creatures_entered_this_turn = sum(
            1 for c in gs.zones.battlefield
            if c.has(Tag.CREATURE) and getattr(c, "summoning_sickness", False)
        )
        if creatures_entered_this_turn >= 2:
            vines_in_gy = [c for c in gs.zones.graveyard if c.name == "Vengevine"]
            for vine in vines_in_gy:
                gs.zones.graveyard.remove(vine)
                vine.summoning_sickness = False  # Vengevine has haste
                gs.zones.battlefield.append(vine)
                gs._log(f"  Vengevine returns from GY (4/3 haste)")

    def main_phase2(self, gs: GameState):
        """Post-combat: try Hogaak again with any new creatures."""
        self._try_cast_hogaak(gs)
        self._check_vengevine_return(gs)
