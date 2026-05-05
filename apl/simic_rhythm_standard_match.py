"""
apl/simic_rhythm_standard_match.py -- Simic Rhythm match APL (Standard 2026)

PT Lorwyn Eclipsed dominant archetype: 15.7% field share (48/306 players).
Source: Andrea Fortunati RC Turin winning list + magic.gg meta breakdown.

Game plan: ramp on T1-T3, Nature's Rhythm tutors finisher directly onto battlefield,
           Craterhoof Behemoth ETB gives all creatures +N/+N trample (N = # creatures).

KEY CARD ORACLE TEXT (confirmed from Scryfall):
  Nature's Rhythm {X}{G}{G}: Sorcery -- search your library for creature with MV <= X,
    put it directly onto the battlefield. X=3 -> Quantum Riddler; X=5 -> Brightglass;
    X=8 -> Craterhoof Behemoth. ALSO has Harmonize {X}{G}{G}{G}{G} (cast from GY).
    This is NOT an enchantment -- it resolves immediately as a tutor.

  Spider Manifestation {1}{R/G}: Creature (Spider Avatar) -- reach, {T}: add R or G.
    Untaps whenever you cast a spell with MV 4+. Mana dork that generates extra mana
    when you cast big spells. Arena name = "Leyline Weaver".

  Gene Pollinator {G}: Artifact Creature (Robot Insect) -- {T} + tap another untapped
    permanent = add one mana of any color. Also {1}{T}: untap another permanent.
    Essentially taps twice the permanents for mana.

  Mockingbird {X}{U}: Bird Bard, Flying -- enters as copy of any creature on battlefield
    with MV <= X. Most efficient copies: Quantum Riddler (X=3), Brightglass Gearhulk (X=5).

  Craterhoof Behemoth {5}{G}{G}{G}: Haste, ETB: all creatures you control gain trample
    and +X/+X where X = # creatures you control.

Sideboard: Seam Rip (destroy enchantment/artifact), Rest in Peace, Soul-Guide Lantern,
           Sage of the Skies, Leatherhead + Surrak (hexproof finishers vs control)
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

LLANOWAR       = "Llanowar Elves"
GENE_POLL      = "Gene Pollinator"
BADGERMOLE     = "Badgermole Cub"
SPIDER_MAN     = "Spider Manifestation"
NATURES_RHYTHM = "Nature's Rhythm"
MOCKINGBIRD    = "Mockingbird"
QUANTUM_RIDDLER = "Quantum Riddler"
OUROBOROID     = "Ouroboroid"
BRIGHTGLASS    = "Brightglass Gearhulk"
CRATERHOOF     = "Craterhoof Behemoth"
BOUNCE_OFF     = "Bounce Off"

SEAM_RIP       = "Seam Rip"
REST_IN_PEACE  = "Rest in Peace"
SOUL_GUIDE     = "Soul-Guide Lantern"
SAGE_SKIES     = "Sage of the Skies"
LEATHERHEAD    = "Leatherhead, Swamp Stalker"
SURRAK         = "Surrak, Elusive Hunter"
BEZA           = "Beza, the Bounding Spring"
INSIDIOUS      = "Insidious Fungus"

# Deploy priority: ramp first, then ETB value, then finisher
CURVE = (
    LLANOWAR,        # T1: mana dork
    GENE_POLL,       # T2: ramp/ETB value
    BADGERMOLE,      # T2: landfall growth
    SPIDER_MAN,      # T2-3: tokens / mana
    NATURES_RHYTHM,  # T3: enchantment pump all creatures
    MOCKINGBIRD,     # T3-4: copies a creature for double ETB
    QUANTUM_RIDDLER, # T4: draw engine
    OUROBOROID,      # T4: mill + GY setup
    BRIGHTGLASS,     # T4-5: tutor silver bullet
    CRATERHOOF,      # Finisher: pump whole team for lethal
)

# Opponent creatures worth blocking (high power threats)
KILL_PRIORITY = (
    "Gran-Gran",            # Monument enabler
    "Mightform Harmonizer", # Combo kill piece
    "Icetill Explorer",     # Landfall engine
)


class SimicRhythmStandardMatchAPL(AwareMatchAPL):
    name = "Simic Rhythm"
    ARCHETYPE = "aggro"

    # Tap out every turn; 1 Bounce Off SB only -- no main interaction
    COUNTER_COST  = 0
    COUNTER_CARDS = {BOUNCE_OFF}
    MATCH_REMOVAL = {}
    MATCH_EXILE   = set()

    SB_PLANS = {
        "combo": (
            # vs Izzet Lessons: Rest in Peace GY hate; Seam Rip answer Monument
            [REST_IN_PEACE, REST_IN_PEACE, SEAM_RIP, SEAM_RIP, SEAM_RIP,
             SOUL_GUIDE, INSIDIOUS],
            [QUANTUM_RIDDLER, QUANTUM_RIDDLER, QUANTUM_RIDDLER,
             OUROBOROID, OUROBOROID, MOCKINGBIRD, SPIDER_MAN],
        ),
        "control": (
            # vs Control: Leatherhead + Surrak (hexproof beats removal/counters)
            [LEATHERHEAD, SURRAK, SURRAK, BEZA, SOUL_GUIDE],
            [OUROBOROID, OUROBOROID, MOCKINGBIRD, BRIGHTGLASS, SPIDER_MAN],
        ),
        "ramp": (
            # vs Mirror: Seam Rip destroys Nature's Rhythm; race with Craterhoof
            [SEAM_RIP, SEAM_RIP, SEAM_RIP, SEAM_RIP, SAGE_SKIES, SAGE_SKIES],
            [QUANTUM_RIDDLER, QUANTUM_RIDDLER, QUANTUM_RIDDLER,
             OUROBOROID, OUROBOROID, MOCKINGBIRD],
        ),
        "aggro": (
            # vs Red Aggro: Seam Rip, Beza (lifegain), Sage of the Skies (flying blocker)
            [BEZA, SAGE_SKIES, SAGE_SKIES, SEAM_RIP, SOUL_GUIDE],
            [OUROBOROID, OUROBOROID, BRIGHTGLASS, MOCKINGBIRD, SPIDER_MAN],
        ),
        "tempo": (
            # vs Izzet Prowess/Spellementals: Seam Rip for enchantments; Leatherhead hexproof
            [SEAM_RIP, SEAM_RIP, LEATHERHEAD, SURRAK, SOUL_GUIDE],
            [QUANTUM_RIDDLER, QUANTUM_RIDDLER, OUROBOROID, MOCKINGBIRD, BRIGHTGLASS],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        has_ramp = any(c.name in {LLANOWAR, GENE_POLL, BADGERMOLE, SPIDER_MAN} for c in hand)
        return has_ramp or mulligans >= 2

    def bottom(self, hand, n):
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess_lands[3:]
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom
                         and c.name not in {LLANOWAR, GENE_POLL, BADGERMOLE}],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (to_bottom + filler)[:n]

    def reserve_mana(self, gs: GameState, opponent: GameState):
        gs.mana_reserve = 0   # tap out every turn

    def main_phase_match(self, gs: GameState, opponent: GameState):
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._opp_gs = opponent

        # Check for Craterhoof lethal: if 5+ creatures, cast Craterhoof and attack
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()]
        if len(my_creatures) >= 5:
            for card in list(gs.zones.hand):
                if card.name == CRATERHOOF and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    # Craterhoof ETB: all creatures get +N/+N trample where N = # creatures
                    n = len(my_creatures)
                    for c in my_creatures:
                        c.counters = (c.counters or 0) + n
                    gs._log(f"  Craterhoof Behemoth ETB: {len(my_creatures)} creatures each +{n}/+{n}")
                    break

        # Nature's Rhythm ({X}{G}{G}): tutor a creature with MV <= X onto battlefield
        # X is determined by available mana minus 2G (=2 for green costs)
        # Priority: X=8 -> Craterhoof, X=5 -> Brightglass, X=3 -> Quantum Riddler, X=2 -> Ouroboroid
        available_for_x = max(0, gs.mana_pool.total() - 2)  # subtract {G}{G} cost
        NATURES_TARGETS = [
            (8, CRATERHOOF),       # find Craterhoof with 10+ mana (X=8)
            (5, BRIGHTGLASS),      # find Brightglass with 7+ mana (X=5)
            (3, QUANTUM_RIDDLER),  # find Quantum Riddler with 5+ mana (X=3)
            (2, OUROBOROID),       # find Ouroboroid with 4+ mana (X=2)
        ]
        for card in list(gs.zones.hand):
            if card.name == NATURES_RHYTHM:
                for x_needed, target_name in NATURES_TARGETS:
                    if available_for_x >= x_needed:
                        # Check if target is in library
                        target_in_lib = next(
                            (c for c in gs.zones.library if c.name == target_name), None)
                        if target_in_lib:
                            total_cost = x_needed + 2
                            if gs.mana_pool.total() >= total_cost:
                                gs.mana_pool.pay(card.mana_cost or "XGG", total_cost)
                                gs.zones.hand.remove(card)
                                gs.zones.graveyard.append(card)
                                gs.zones.library.remove(target_in_lib)
                                gs.zones.battlefield.append(target_in_lib)
                                target_in_lib.summoning_sickness = True
                                # Craterhoof ETB pump
                                if target_in_lib.name == CRATERHOOF:
                                    n = len(my_creatures) + 1
                                    for c in gs.zones.battlefield:
                                        if c.has(Tag.CREATURE) and not c.is_land():
                                            c.counters = (c.counters or 0) + n
                                gs._log(f"  Nature's Rhythm X={x_needed}: found {target_name}")
                                break
                        if target_in_lib and gs.mana_pool.total() >= x_needed + 2:
                            break
                break

        # Mockingbird ({X}{U}): copy highest-CMC creature on board with MV <= X
        for card in list(gs.zones.hand):
            if card.name == MOCKINGBIRD:
                available_x = max(0, gs.mana_pool.total() - 1)  # subtract {U}
                copy_targets = [c for c in gs.zones.battlefield
                                if c.has(Tag.CREATURE) and not c.is_land()
                                and getattr(c, 'cmc', 0) <= available_x]
                if copy_targets:
                    template = max(copy_targets, key=lambda c: getattr(c, 'cmc', 0))
                    total_x = getattr(template, 'cmc', 0) + 1
                    if gs.mana_pool.total() >= total_x:
                        gs.mana_pool.pay(card.mana_cost or "XU", total_x)
                        gs.zones.hand.remove(card)
                        from copy import copy as _copy
                        token = _copy(template)
                        token.summoning_sickness = True
                        gs.zones.battlefield.append(token)
                        gs._log(f"  Mockingbird X={getattr(template,'cmc',0)}: copied {template.name}")
                break

        # Deploy remaining curve pieces
        for name in (LLANOWAR, GENE_POLL, BADGERMOLE, SPIDER_MAN,
                     QUANTUM_RIDDLER, OUROBOROID, BRIGHTGLASS, CRATERHOOF):
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    if card.name == CRATERHOOF:
                        n = len(my_creatures)
                        for c in gs.zones.battlefield:
                            if c.has(Tag.CREATURE) and not c.is_land():
                                c.counters = (c.counters or 0) + n
                    break

        self._cast_all_castable(gs)

    def declare_attackers(self, gs, opponent):
        # Attack with everything except keep 1 blocker if opponent has fliers
        opp_fliers = [c for c in opponent.zones.battlefield
                      if c.has(Tag.CREATURE) and not c.is_land()
                      and 'flying' in (getattr(c, 'oracle_text', '') or '').lower()]
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)]
        if opp_fliers and len(my_creatures) > 1:
            # Hold back highest-toughness creature as blocker
            keeper = max(my_creatures, key=lambda c: safe_toughness(c))
            return [c for c in my_creatures if c is not keeper]
        return my_creatures

    def declare_blockers(self, gs, opponent, attackers):
        if not attackers:
            return {}
        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, 'tapped', False)
                        and not getattr(c, 'summoning_sickness', False)]
        assignments = {}
        for atk, blk in zip(
            sorted(attackers, key=lambda c: -safe_power(c)),
            sorted(my_creatures, key=lambda c: -safe_toughness(c))
        ):
            assignments[id(atk)] = [blk]
        return assignments

    def _play_land_if_able(self, gs: GameState):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        gs.play_land(lands[0])
