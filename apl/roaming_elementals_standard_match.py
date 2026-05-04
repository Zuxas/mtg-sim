"""
apl/roaming_elementals_standard_match.py -- Izzet Spellementals match APL (Standard)

RCQ-winning control/tempo build (RIW Hobbies March 2026).
Win conditions: large elemental creatures (Sunderflock, Hearth Elemental)
backed by heavy counter suite. Sunderflock bounces all non-elementals = game reset.

Matchup roles (from guides):
  vs Landfall:       tempo-control; sweep dorks, counter payoffs
  vs Izzet Prowess:  control; Annul Stormchaser's Talent on the stack
  vs Izzet Lessons:  control; Annul Monument to Endurance and Artist's Talent
  vs Aggro:          interaction race; Pyroclasm + sweepers over bounce
  vs Control:        tempo; one threat + protect for 4 turns wins
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.roaming_elementals_standard import RoamingElementalsAPL

ANNUL          = "Annul"
SPELL_PIERCE   = "Spell Pierce"
SPELL_SNARE    = "Spell Snare"
DISDAINFUL     = "Disdainful Stroke"
FLASHFREEZE    = "Flashfreeze"
BOUNCE_OFF     = "Bounce Off"
INTO_FLOOD     = "Into the Flood Maw"
PYROCLASM      = "Pyroclasm"
BURST_LIGHTNING = "Burst Lightning"
SEAR           = "Sear"
BROADSIDE      = "Broadside Barrage"
SUNDERFLOCK    = "Sunderflock"

# Permanent-based engines that Annul must counter on the stack
ANNUL_TARGETS = {
    "Stormchaser's Talent",    # Izzet Prowess engine — letting it resolve is often game-ending
    "Monument to Endurance",   # Izzet Lessons win condition
    "Artist's Talent",         # Izzet Lessons card-draw engine
    "Earthbender Ascension",   # Selesnya ramp/trample enabler
    "Sapling Nursery",         # token engine
    "Felidar Retreat",         # Selesnya post-board pivot
}

# Creatures killed on sight (before they fire their engine)
KILL_PRIORITY = {
    "Badgermole Cub",        # double-mana ramp — Pyroclasm kills it
    "Mossborn Hydra",        # exponentially growing finisher
    "Llanowar Elves",        # mana dork, Pyroclasm sweeps
    "Gran-Gran",             # loot = Monument trigger; kill immediately
    "Icetill Explorer",      # 4 landfall triggers per fetch land cycle
}


class RoamingElementalsStandardMatchAPL(AwareMatchAPL, RoamingElementalsAPL):
    ARCHETYPE = "tempo"

    # Hold UU for Annul / Spell Pierce at all times when in hand
    COUNTER_COST  = 2
    COUNTER_CARDS = {ANNUL, SPELL_PIERCE, SPELL_SNARE, DISDAINFUL, FLASHFREEZE, BOUNCE_OFF}

    MATCH_REMOVAL = {
        PYROCLASM:       ("1R",  2),   # sweeps all 2-toughness or less
        BURST_LIGHTNING: ("R",   2),   # 2 damage instant
        SEAR:            ("1R",  4),   # 4 damage sorcery
        BROADSIDE:       ("2R",  3),   # 3 damage
    }
    MATCH_EXILE = {INTO_FLOOD}  # Into the Flood Maw bounces to exile

    # Sideboard plans derived from RIW Hobbies guide + TheBoulderMTG Substack
    SB_PLANS = {
        "aggro": (
            # vs Izzet Prowess: Pyroclasm for early creatures, Annul for enchantments
            [PYROCLASM, PYROCLASM, ANNUL, ANNUL, "Sear"],
            [SPELL_PIERCE, SPELL_PIERCE, "Spider Sense", "Stock Up", "Bounce Off"],
        ),
        "control": (
            # vs Control: land one threat and protect it; Disdainful Stroke for expensive stuff
            [DISDAINFUL, DISDAINFUL, "Negate", "Soul-Guide Lantern"],
            [PYROCLASM, PYROCLASM, "Bounce Off", "Spider Sense"],
        ),
        "combo": (
            # vs Izzet Lessons: Annul Monument/Artist's Talent; Soul-Guide Lantern for GY
            [ANNUL, ANNUL, "Soul-Guide Lantern", "Soul-Guide Lantern", DISDAINFUL, "Negate"],
            [SUNDERFLOCK, SUNDERFLOCK, "Bounce Off", INTO_FLOOD, SEAR, BURST_LIGHTNING],
        ),
        "ramp": (
            # vs Landfall (Mono-Green / Selesnya): Pyroclasm for dorks, Disdainful/Flashfreeze for payoffs
            [PYROCLASM, PYROCLASM, FLASHFREEZE, FLASHFREEZE, DISDAINFUL, BROADSIDE],
            [SPELL_SNARE, SPELL_SNARE, "Spider Sense", "Stock Up", "Winternights", BOUNCE_OFF],
        ),
        "midrange": (
            # vs Dimir Midrange: Hydro-Man Fluid Felon for value, Broadside for interaction
            ["Hydro-Man Fluid Felon", "Hydro-Man Fluid Felon", BROADSIDE],
            ["Spider Sense", BOUNCE_OFF, "Spell Pierce"],
        ),
    }

    # ---------------------------------------------------------------------------
    # Spellementals-specific: Sunderflock board reset
    # Sunderflock enters and immediately bounces all non-elemental permanents.
    # Model: when Sunderflock resolves, opponent's non-elemental creatures go away.
    # We represent this by treating Sunderflock as a very high-priority cast target.
    # ---------------------------------------------------------------------------

    def _sunderflock_in_hand(self, gs: GameState) -> bool:
        return any(c.name == SUNDERFLOCK for c in gs.zones.hand)

    def _opp_has_non_elementals(self, opponent: GameState) -> bool:
        for c in opponent.zones.battlefield:
            if c.has(Tag.CREATURE) and not c.is_land():
                subtype = getattr(c, 'subtypes', [])
                if 'Elemental' not in (subtype or []):
                    return True
        return False

    # ---------------------------------------------------------------------------
    # Reserve mana: always hold counter mana; hold more for Sunderflock opportunity
    # ---------------------------------------------------------------------------

    def reserve_mana(self, gs: GameState, opponent: GameState):
        has_counter = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        # Hold 4 mana if Sunderflock in hand and opponent has non-elementals to bounce
        if self._sunderflock_in_hand(gs) and self._opp_has_non_elementals(opponent):
            gs.mana_reserve = 4
        elif has_counter:
            gs.mana_reserve = self.COUNTER_COST
        else:
            gs.mana_reserve = 0

    # ---------------------------------------------------------------------------
    # Pre-combat: counter engine pieces and kill priority creatures
    # ---------------------------------------------------------------------------

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        # Kill priority creatures before combat (Pyroclasm sweeps dorks)
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]

        # Gran-Gran first — loot triggers Monument; kill it before it can attack
        for c in opp_creatures:
            if c.name == "Gran-Gran":
                if self._kill_with_removal(gs, opponent, c):
                    return

        # Pyroclasm sweep: use when >=3 creatures with toughness <=2 on board
        small = [c for c in opp_creatures if safe_toughness(c) <= 2]
        if len(small) >= 3:
            for card in gs.zones.hand:
                if card.name == PYROCLASM and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.mana_pool.pay(card.mana_cost, card.cmc)
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    for victim in list(small):
                        if victim in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(victim)
                            opponent.zones.graveyard.append(victim)
                    gs._log(f"  [pre-combat] Pyroclasm swept {len(small)} small creatures")
                    return

        # Kill other priority targets individually
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c):
                        gs._log(f"  [pre-combat] killed priority target {c.name}")
                        return

        # Fall through to base ninjutsu / blink-bait logic
        super().pre_combat_instant(gs, opponent)
