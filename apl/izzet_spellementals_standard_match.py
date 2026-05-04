"""
apl/izzet_spellementals_standard_match.py -- Izzet Spellementals (Standard, PT SOS 2026)

RCQ-winning control/tempo build. 8% of PT SOS field (26/325 players).
Guide sources: RIW Hobbies March 2026 (RCQ winner), TheBoulderMTG Substack

Key engine:
- Hearth Elemental (4x) -- early Elemental body
- Eddymurk Crab (4x) -- costs X less where X = spells cast; cost-reduces Sunderflock
- Colorstorm Stallion (2x) -- {1}{U}{R} 3/3 haste, +1/+1 per spell cast this turn
- Sunderflock ({7}{U}{U}, discount = greatest MV among Elementals) -- bounces ALL
  non-elemental permanents when it enters. With Eddymurk (CMC 7) on board: costs {UU}.

Matchup roles (from RIW Hobbies RCQ guide):
  vs Badgermole Cub decks: 80/20 control -- bolt ramp, snare cubs, hold Sunderflock reset
  vs Izzet Prowess:        tempo/control -- Annul Stormchaser's Talent on the stack
  vs Izzet Lessons:        50/50 control -- Annul Monument/Artist's Talent; Soul-Guide Lantern
  vs Mono Green Landfall:  45/55 underdog -- Pyroclasm dorks, Disdainful Stroke payoffs
  vs Dimir Midrange:       slightly unfavorable -- tempo; if Cecil+Kaito resolve, very hard

Kill priority:
  Stormchaser's Talent  -- letting it resolve is "often game-ending" (Annul on the stack)
  Monument to Endurance  -- Annul on the stack
  Artist's Talent        -- Annul on the stack
  Gran-Gran              -- kill before it loots; Monument trigger enabler
  Badgermole Cub         -- Pyroclasm; instant acceleration must die

Sunderflock = board reset: bounces all non-elemental permanents. Hold 4 mana when live.
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_toughness
from apl.aware_match_apl import AwareMatchAPL
from apl.izzet_prowess_standard import (
    IzzetProwessAPL, COLORSTORM, FLOW_STATE,
    TRAUMATIC, PRISMARI_CHARM, IMPRACTICAL, BURST,
)

EDDYMURK    = "Eddymurk Crab"
SUNDERFLOCK = "Sunderflock"
HEARTH      = "Hearth Elemental"
WINTERNIGHT = "Winternight Stories"   # {2}{U}: draw 3, discard 2
ELEMENTALS  = frozenset({EDDYMURK, HEARTH, COLORSTORM})

ANNUL          = "Annul"
SPELL_PIERCE   = "Spell Pierce"
SPELL_SNARE    = "Spell Snare"
DISDAINFUL     = "Disdainful Stroke"
FLASHFREEZE    = "Flashfreeze"
BOUNCE_OFF     = "Bounce Off"
PYROCLASM      = "Pyroclasm"
BROADSIDE      = "Broadside Barrage"
SOUL_GUIDE     = "Soul-Guide Lantern"

# Permanent-based engines: Annul these on the stack
ANNUL_TARGETS = {
    "Stormchaser's Talent",    # Prowess engine -- game-ending if it resolves
    "Monument to Endurance",   # Lessons win condition
    "Artist's Talent",         # Lessons card-draw engine
    "Earthbender Ascension",   # Selesnya ramp/trample enabler
    "Sapling Nursery",         # token engine
    "Felidar Retreat",         # Selesnya post-board pivot
}

# Creatures killed before they fire their engine
KILL_PRIORITY = (
    "Gran-Gran",         # loot = Monument trigger; #1 kill target vs Lessons
    "Badgermole Cub",    # double-mana ramp; Pyroclasm sweeps it
    "Icetill Explorer",  # 4 landfall triggers per fetch land
    "Mossborn Hydra",    # exponentially growing finisher
)


class IzzetSpellementalsStandardMatchAPL(AwareMatchAPL, IzzetProwessAPL):
    name = "Izzet Spellementals"
    ARCHETYPE = "tempo"

    # Hold {U}{U} for Annul / Spell Pierce; hold 4 for Sunderflock window
    COUNTER_COST  = 2
    COUNTER_CARDS = {ANNUL, SPELL_PIERCE, SPELL_SNARE, DISDAINFUL, FLASHFREEZE, BOUNCE_OFF}

    MATCH_REMOVAL = {
        PYROCLASM: ("1R", 2),   # sweeps all 2-toughness or less (main + sideboard)
        BURST:     ("R",  2),   # 2 damage instant
    }
    MATCH_EXILE = set()

    CREATURES = (HEARTH, COLORSTORM, EDDYMURK)
    CANTRIP_SPELLS = ("Opt", "Sleight of Hand", FLOW_STATE, PRISMARI_CHARM, WINTERNIGHT)
    BURN_SPELLS = {BURST: (1, 2), IMPRACTICAL: (1, 3), TRAUMATIC: (3, 3)}
    HASTE_CREATURES = frozenset({COLORSTORM})
    MULL_MIN_LANDS  = 2
    MULL_MAX_LANDS  = 4

    # Exact sideboard plans from RIW Hobbies RCQ winner guide (March 2026)
    SB_PLANS = {
        "aggro": (
            # vs Izzet Prowess: Abrade + Broadside + Pyroclasm; trim slow/bad matchup pieces
            ["Abrade", BROADSIDE, PYROCLASM],
            ["Three Steps Ahead", SPELL_PIERCE, "Stock Up"],
        ),
        "control": (
            # vs Control/Dimir Midrange: Hydro-Man Fluid Felon for card advantage; Broadside
            ["Hydro-Man Fluid Felon", "Hydro-Man Fluid Felon", BROADSIDE],
            ["Spider Sense", BOUNCE_OFF, SPELL_PIERCE],
        ),
        "combo": (
            # vs Izzet Lessons (50/50): Annul Monument/Artist's; Soul Guide Lantern GY hate
            # Sunderflock is too slow here -- bring in counters instead
            [SOUL_GUIDE, SOUL_GUIDE, ANNUL, ANNUL, "Abrade", "Negate", "Stock Up"],
            [SUNDERFLOCK, SUNDERFLOCK, "Spider Sense", BOUNCE_OFF, "Into the Flood Maw",
             "Sear", BURST],
        ),
        "ramp": (
            # vs Mono Green (45/55 underdog): Flashfreeze payoffs, Abrade/Broadside dorks
            [FLASHFREEZE, "Abrade", "Into the Flood Maw", DISDAINFUL, BROADSIDE],
            ["Three Steps Ahead", "Spider Sense", SPELL_SNARE, "Stock Up", WINTERNIGHT],
        ),
        "tempo": (
            # vs UG Badgermole Cub (80/20): bolt ramp, Pyroclasm, Flashfreeze Rhythm
            [BROADSIDE, PYROCLASM, FLASHFREEZE, "Into the Flood Maw"],
            ["Stock Up", SPELL_PIERCE, "Spider Sense", "Three Steps Ahead"],
        ),
    }

    # ---------------------------------------------------------------------------
    # Reserve mana: hold counter mana; hold 4 when Sunderflock reset is available
    # ---------------------------------------------------------------------------

    def reserve_mana(self, gs: GameState, opponent: GameState):
        # Check for Sunderflock opportunity (board reset)
        has_sunderflock = any(c.name == SUNDERFLOCK for c in gs.zones.hand)
        opp_has_nonelements = any(
            c.has(Tag.CREATURE) and not c.is_land()
            for c in opponent.zones.battlefield
        )
        if has_sunderflock and opp_has_nonelements:
            gs.mana_reserve = 4   # hold up for Sunderflock cost after discount
            return
        has_counter = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        gs.mana_reserve = self.COUNTER_COST if has_counter else 0

    # ---------------------------------------------------------------------------
    # main_phase_match: preserve Elemental cost-reduction + Sunderflock discount
    # ---------------------------------------------------------------------------

    def main_phase_match(self, gs: GameState, opponent: GameState):
        elementals = [c for c in gs.zones.battlefield
                      if not c.is_land() and c.name in ELEMENTALS]
        max_mv = max((getattr(c, 'cmc', 0) for c in elementals), default=0)
        if max_mv:
            gs.mana_pool.cost_reduction = max(gs.mana_pool.cost_reduction, int(max_mv))
        self._opp_gs = opponent
        self._match_cast_removal(gs, opponent)
        self.main_phase(gs)
        # Sunderflock with Elemental discount -- cast when discount makes it affordable
        for c in list(gs.zones.hand):
            if c.name == SUNDERFLOCK:
                effective = max(2, getattr(c, 'cmc', 9) - int(max_mv))
                gs.mana_pool.cost_reduction = int(max_mv)
                if gs.mana_pool.can_cast(c.mana_cost, effective):
                    gs.cast_spell(c)
                    # Sunderflock ETB: bounce all non-elemental permanents
                    for opp_c in list(opponent.zones.battlefield):
                        if opp_c.has(Tag.CREATURE) and not opp_c.is_land():
                            subtype = getattr(opp_c, 'subtypes', []) or []
                            if 'Elemental' not in subtype:
                                opponent.zones.battlefield.remove(opp_c)
                                opponent.zones.hand.append(opp_c)
                    gs._log(f"  Sunderflock: -{max_mv} discount -> {effective} eff cost; bounced non-elementals")
                gs.mana_pool.cost_reduction = 0
                break

    # ---------------------------------------------------------------------------
    # Pre-combat: Pyroclasm sweep + priority kill targets
    # ---------------------------------------------------------------------------

    def pre_combat_instant(self, gs: GameState, opponent: GameState):
        opp_creatures = [c for c in opponent.zones.battlefield
                         if c.has(Tag.CREATURE) and not c.is_land()]

        # Gran-Gran: kill immediately (Monument trigger enabler)
        for c in opp_creatures:
            if c.name == "Gran-Gran":
                if self._kill_with_removal(gs, opponent, c):
                    gs._log("  [pre-combat] killed Gran-Gran before loot trigger")
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

        # Kill other priority targets
        for name in KILL_PRIORITY:
            for c in opp_creatures:
                if c.name == name:
                    if self._kill_with_removal(gs, opponent, c):
                        gs._log(f"  [pre-combat] killed {c.name}")
                        return

        super().pre_combat_instant(gs, opponent)
