"""
apl/selesnya_ouroboroid_standard.py -- Selesnya Ouroboroid APL (Standard)

Based on Matt Nass's PT SOS #2 seed list (2026-05-01).
New archetype -- not in prior field configs.

Game plan:
  T1: Llanowar Elves (ramp) or Pawpatch Recruit (aggressive 2/1)
  T2: Gene Pollinator (mana) or Badgermole Cub (landfall 2/2)
  T3: Ouroboroid (4x, core engine) -- pumps ALL creatures by X at combat start
      where X = Ouroboroid's power (starts 1/3, snowballs quickly)
  T3+: Sage of the Skies -- cast ANOTHER spell first to get a free 2/3 flyer copy
  T4+: Brightglass Gearhulk -- ETB searches 2 more threats from library
       Keen-Eyed Curator -- grows to 7/7 trample when exiling enough card types

Win by going wide (Pawpatch offspring, Sage copies, Badgermole cubs) then
pumping the whole board with Ouroboroid at the start of each combat.
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

ELVES        = "Llanowar Elves"
PAWPATCH     = "Pawpatch Recruit"
BADGER       = "Badgermole Cub"
OUROBOROID   = "Ouroboroid"            # The engine -- highest deploy priority
SAGE         = "Sage of the Skies"     # Best after casting another spell first
CURATOR      = "Keen-Eyed Curator"
GEARHULK     = "Brightglass Gearhulk"
PIXIE        = "Nurturing Pixie"
MELTSTRIDER  = "Meltstrider's Resolve"
SEAM_RIP     = "Seam Rip"
ERODE        = "Erode"

ONE_DROPS    = {ELVES, PAWPATCH}
TWO_DROPS    = {BADGER}
# Sage listed separately -- needs setup (cast another spell first)
THREE_DROPS  = {OUROBOROID, SAGE, CURATOR}
FOUR_DROPS   = {GEARHULK}
UTILITY      = {MELTSTRIDER, SEAM_RIP, PIXIE}

# Fetchlands -- play early for double landfall
FETCHLANDS   = {"Hushwood Verge", "Fabled Passage"}


class SelesnyaOuroboroidAPL(BaseAPL):
    name = "Selesnya Ouroboroid"
    win_condition_damage = 20
    max_turns = 10

    # ── Mulligan ───────────────────────────────────────────────────────

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands  = [c for c in hand if c.is_land()]
        ones   = [c for c in hand if c.name in ONE_DROPS]
        twos   = [c for c in hand if c.name in TWO_DROPS]
        engines = [c for c in hand if c.name == OUROBOROID]
        n = len(lands)
        if n == 0 or n > 5:
            return False
        # Ouroboroid + 2 lands + any other threat is a snap keep
        if engines and n >= 2 and (ones or twos):
            return True
        # 1-drop + 2 lands is a keep
        if ones and n >= 2:
            return True
        # 2-drop + 3 lands
        if twos and n >= 3:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands  = [c for c in hand if c.is_land()]
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, "cmc", 0))
        excess = lands[4:]
        return (excess + spells)[:n]

    # ── Land selection ─────────────────────────────────────────────────

    def _play_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            if c.name in FETCHLANDS:
                return 0   # fetch first for landfall triggers
            if "tapped" in (c.oracle_text or "").lower():
                return 2   # tap-lands last
            return 1
        gs.play_land(min(lands, key=score))

    # ── Main phase 1 (pre-combat) ──────────────────────────────────────

    def main_phase(self, gs):
        self._play_land(gs)
        gs.tap_lands()

        # Erode: remove opp threat pre-combat when they have power >= 3
        self._maybe_erode(gs)

        # Cast Seam Rip / Meltstrider as setup BEFORE Sage (enables copy trigger)
        spells_cast_this_turn = getattr(gs, "_spells_cast_this_turn", 0)
        sage_in_hand = any(c.name == SAGE for c in gs.zones.hand)
        if sage_in_hand and spells_cast_this_turn == 0:
            # Cast a cheap utility spell first to trigger Sage copy
            for name in [SEAM_RIP, MELTSTRIDER, BADGER]:
                for card in list(gs.zones.hand):
                    if card.name != name:
                        continue
                    if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        break

        # Deploy in curve order: Ouroboroid is T3 priority #1
        deployed = True
        while deployed:
            deployed = False
            for group in [ONE_DROPS, TWO_DROPS, THREE_DROPS, FOUR_DROPS]:
                for card in list(gs.zones.hand):
                    if card.name not in group:
                        continue
                    if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)
                        deployed = True
                        break
                if deployed:
                    break

    def main_phase2(self, gs):
        gs.tap_lands()
        # Cast remaining utility + Erode post-combat
        self._maybe_erode(gs)
        for card in list(gs.zones.hand):
            if not card.is_land():
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)

    # ── Ouroboroid combat pump ─────────────────────────────────────────

    def _do_combat(self, gs):
        """Apply Ouroboroid pump before declaring attackers.

        Oracle: 'At the beginning of combat on your turn, put X +1/+1 counters
        on each creature you control, where X is this creature's power.'
        """
        from data.card import Tag
        ouros = [c for c in gs.zones.battlefield
                 if c.name == OUROBOROID and not c.is_land() and c.has(Tag.CREATURE)]
        for ouro in ouros:
            x = max(1, int(ouro.power or 1)) + (ouro.counters or 0)
            friends = [c for c in gs.zones.battlefield
                       if not c.is_land() and c.has(Tag.CREATURE)]
            for friend in friends:
                friend.counters = (friend.counters or 0) + x
            gs._log(f"  Ouroboroid combat trigger: +{x}/+{x} to all {len(friends)} creatures")
        super()._do_combat(gs)

    # ── Erode targeting ────────────────────────────────────────────────

    def _maybe_erode(self, gs):
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return
        opp_power = sum(
            int(getattr(c, "power", 0) or 0)
            for c in opp.zones.battlefield
            if not c.is_land() and c.has(Tag.CREATURE)
        )
        if opp_power < 2:
            return
        for card in list(gs.zones.hand):
            if card.name == ERODE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
