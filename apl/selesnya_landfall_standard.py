"""
apl/selesnya_landfall_standard.py -- Selesnya Landfall match APL (Standard)

Based on Christoffer Larsen's PT SOS Top 4 list (2026-05-01).
PT overall WR: 63.81%. Beats Prowess 62.9%, Mono-Green 65.4%.
Loses to Izzet Lessons 25% (only reliable counter).

Game plan:
  T1: Llanowar Elves (ramp into T2 3-drop)
  T2: Badgermole Cub or Sazh's Chocobo (landfall body)
  T3: Earthbender Ascension or Mightform Harmonizer + fetch for double landfall
  T4+: Surrak, Lumbering Worldwagon, Bushwhack for hasty threats
  Remove: Erode (destroy opp's biggest creature; has full match-aware handler)

Landfall triggers handled by engine (on_landfall in card_effects).
Erode is match-aware -- destroys opponent's biggest creature in match mode,
no-op in goldfish mode.
"""
from data.card import Card, Tag
from apl.base_apl import BaseAPL

ELVES      = "Llanowar Elves"
CHOCOBO    = "Sazh's Chocobo"
BADGER     = "Badgermole Cub"
ICETILL    = "Icetill Explorer"
CURATOR    = "Keen-Eyed Curator"
ASCENSION  = "Earthbender Ascension"
HARMONIZER = "Mightform Harmonizer"
SURRAK     = "Surrak, Elusive Hunter"
WORLDWAGON = "Lumbering Worldwagon"
BUSHWHACK  = "Bushwhack"
ERODE      = "Erode"

ONE_DROPS   = {ELVES, CHOCOBO}
TWO_DROPS   = {BADGER, ICETILL, CURATOR}
THREE_DROPS = {ASCENSION, HARMONIZER}
FOUR_DROPS  = {SURRAK, WORLDWAGON}

# Fetchlands — play first to trigger landfall twice (ETB + fetch)
FETCHLANDS  = {"Fabled Passage", "Escape Tunnel", "Hushwood Verge"}
# Slow lands — enter tapped or conditional
SLOW_LANDS  = {"Ba Sing Se", "Temple Garden"}


class SelesnyaLandfallAPL(BaseAPL):
    name = "Selesnya Landfall"
    win_condition_damage = 20
    max_turns = 12

    # ── Mulligan ───────────────────────────────────────────────────────

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands  = [c for c in hand if c.is_land()]
        ones   = [c for c in hand if c.name in ONE_DROPS]
        twos   = [c for c in hand if c.name in TWO_DROPS]
        threes = [c for c in hand if c.name in THREE_DROPS]
        n = len(lands)
        if n == 0 or n > 5:
            return False
        # Elves + 1 land is a keep — can accelerate into T2 3-drop
        if ones and n >= 1:
            return True
        # 2 lands + any 2-drop or 3-drop
        if n >= 2 and (twos or threes):
            return True
        # 3 lands + any threat
        if n >= 3 and (ones or twos or threes):
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands  = [c for c in hand if c.is_land()]
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, "cmc", 0))
        excess = lands[4:]  # keep at most 4 lands
        return (excess + spells)[:n]

    # ── Main phase 1 (pre-combat) ──────────────────────────────────────

    def main_phase(self, gs):
        self._play_land(gs)
        gs.tap_lands()

        # Cast Erode pre-combat if opponent has a big creature threatening
        # us AND we have enough mana to cast it AND still deploy a threat.
        self._maybe_erode(gs)

        # Deploy creatures in curve order
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

        # Bushwhack — hasty boost; cast last so all creatures are out
        for card in list(gs.zones.hand):
            if card.name == BUSHWHACK and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break

    def main_phase2(self, gs):
        gs.tap_lands()
        # Cast remaining Erode after combat if opponent still has creatures
        self._maybe_erode(gs)
        # Cast anything else left (post-combat extras)
        for card in list(gs.zones.hand):
            if not card.is_land() and card.name != ERODE:
                if gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)

    # ── Land selection ─────────────────────────────────────────────────

    def _play_land(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return

        def score(c):
            n = c.name
            if n in FETCHLANDS:
                return 0   # fetchlands first — double landfall trigger
            if n in SLOW_LANDS:
                return 2   # enters tapped, lower priority
            return 1       # basics and dual lands

        gs.play_land(min(lands, key=score))

    # ── Erode targeting ────────────────────────────────────────────────

    def _maybe_erode(self, gs):
        """Cast Erode if opponent has a creature with power >= 3.

        Erode's handler (card_handlers_verified.py) is match-aware:
        it destroys opp's highest-CMC creature. We fire it here when
        their board threatens to outrace us.
        """
        opp = getattr(self, "_opp_gs", None)
        if opp is None:
            return  # goldfish: Erode is a no-op, don't waste mana
        opp_power = sum(
            int(getattr(c, "power", 0) or 0)
            for c in opp.zones.battlefield
            if not c.is_land() and c.has(Tag.CREATURE)
        )
        if opp_power < 3:
            return  # no threat yet
        for card in list(gs.zones.hand):
            if card.name == ERODE and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                break
