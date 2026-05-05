"""
apl/bant_rhythm_standard_match.py -- Bant Rhythm match APL (Standard 2026)

PT Lorwyn Eclipsed: 15.0% field share (46/306 players).
Source: univerce list.

Bant Rhythm vs Simic Rhythm key differences:
  - Leyline Weaver 4x (instead of Spider Manifestation): enchantment synergy mana
  - Brightglass Gearhulk 4x (vs Simic 1x): ETB tutors any card -- silver bullet engine
  - Ouroboroid 4x (vs Simic 2x): heavier GY mill
  - Archdruid's Charm 2x: modal green tutor (find creature/land/remove enchantment)
  - Figure of Fable 1x: powerful creature when enchantments are in play
  - Abandoned Air Temple: land that produces mana and creates flying token

Game plan: same as Simic Rhythm but more tutor-heavy (Brightglass + Archdruid's Charm).
           Brightglass Gearhulk fetches silver bullets: Surrak vs control, Leatherhead vs
           flying, Seam Rip vs enchantments, Insidious Fungus vs GY.

Sideboard: Sage of the Skies (flying blockers), Get Lost (exile), Soul-Guide Lantern,
           Beza (lifegain), Leatherhead + Surrak (hexproof finishers)
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

LLANOWAR       = "Llanowar Elves"
GENE_POLL      = "Gene Pollinator"
BADGERMOLE     = "Badgermole Cub"
NATURES_RHYTHM = "Nature's Rhythm"
LEYLINE_WEAVER = "Leyline Weaver"
OUROBOROID     = "Ouroboroid"
BRIGHTGLASS    = "Brightglass Gearhulk"
ARCHDRUID      = "Archdruid's Charm"
FIGURE_FABLE   = "Figure of Fable"
CRATERHOOF     = "Craterhoof Behemoth"
SEAM_RIP       = "Seam Rip"       # {W} Enchantment: ETB exiles opponent's nonland MV<=2 permanent

SAGE_SKIES     = "Sage of the Skies"
GET_LOST       = "Get Lost"
SOUL_GUIDE     = "Soul-Guide Lantern"
LEATHERHEAD    = "Leatherhead, Swamp Stalker"
SURRAK         = "Surrak, Elusive Hunter"
BEZA           = "Beza, the Bounding Spring"
PAWPATCH       = "Pawpatch Formation"
INSIDIOUS      = "Insidious Fungus"
MELTSTRIDER    = "Meltstrider's Resolve"

# Tutor via Brightglass Gearhulk based on board state
SILVER_BULLETS = {
    "aggro":    SAGE_SKIES,    # flying blockers vs fast fliers
    "control":  SURRAK,        # hexproof creature beats removal
    "combo":    SOUL_GUIDE,    # GY hate vs Lessons/Reanimator
    "ramp":     LEATHERHEAD,   # hexproof+trample vs other landfall
}

CURVE = (
    LLANOWAR,        # T1
    GENE_POLL,       # T2
    BADGERMOLE,      # T2
    LEYLINE_WEAVER,  # T3: mana enchantment
    NATURES_RHYTHM,  # T3: all creatures bonus
    OUROBOROID,      # T3-4: GY mill + payoff
    ARCHDRUID,       # T4: tutor/removal
    BRIGHTGLASS,     # T4-5: ETB tutor silver bullet
    FIGURE_FABLE,    # T4+: enchantment payoff
    CRATERHOOF,      # Finisher
)


class BantRhythmStandardMatchAPL(AwareMatchAPL):
    name = "Bant Rhythm"
    ARCHETYPE = "aggro"

    COUNTER_COST  = 0
    COUNTER_CARDS = set()
    # Seam Rip {W}: enchantment that exiles target nonland permanent with MV<=2
    # Banishing Light variant: cast main phase, ETB effect fires immediately
    MATCH_REMOVAL = {SEAM_RIP: ("W", 2)}   # {W} cost, max toughness proxy = MV 2
    MATCH_EXILE   = {GET_LOST, SEAM_RIP}   # both are exile effects

    SB_PLANS = {
        "combo": (
            # vs Izzet Lessons: Soul-Guide Lantern + Seam Rip vs Monument; Surrak hexproof
            [SOUL_GUIDE, SOUL_GUIDE, SEAM_RIP, SURRAK, INSIDIOUS],
            [OUROBOROID, OUROBOROID, LEYLINE_WEAVER, ARCHDRUID, FIGURE_FABLE],
        ),
        "control": (
            # vs Control: Leatherhead + Surrak (hexproof bodies); Meltstrider pump
            [LEATHERHEAD, SURRAK, SURRAK, MELTSTRIDER, PAWPATCH],
            [OUROBOROID, OUROBOROID, FIGURE_FABLE, ARCHDRUID, LEYLINE_WEAVER],
        ),
        "ramp": (
            # vs Mirror (Simic/Bant): Seam Rip destroys Nature's Rhythm; race with Craterhoof
            [SEAM_RIP, SEAM_RIP, SEAM_RIP, SEAM_RIP, SAGE_SKIES, SAGE_SKIES],
            [OUROBOROID, OUROBOROID, FIGURE_FABLE, ARCHDRUID, LEYLINE_WEAVER, LEYLINE_WEAVER],
        ),
        "aggro": (
            # vs Aggro: Beza lifegain; Sage flying blockers; Get Lost exile
            [BEZA, BEZA, SAGE_SKIES, SAGE_SKIES, GET_LOST],
            [OUROBOROID, OUROBOROID, FIGURE_FABLE, ARCHDRUID, LEYLINE_WEAVER],
        ),
        "tempo": (
            # vs Izzet Prowess: Seam Rip vs enchantments; Leatherhead hexproof vs burn
            [SEAM_RIP, SEAM_RIP, LEATHERHEAD, SURRAK, SOUL_GUIDE],
            [OUROBOROID, OUROBOROID, FIGURE_FABLE, ARCHDRUID, LEYLINE_WEAVER],
        ),
    }

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands > 5:
            return False
        has_ramp = any(c.name in {LLANOWAR, GENE_POLL, BADGERMOLE} for c in hand)
        return has_ramp or mulligans >= 2

    def bottom(self, hand, n):
        excess_lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        to_bottom = excess_lands[3:]
        filler = sorted([c for c in hand if not c.is_land() and c not in to_bottom
                         and c.name not in {LLANOWAR, GENE_POLL, BADGERMOLE}],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (to_bottom + filler)[:n]

    def reserve_mana(self, gs: GameState, opponent: GameState):
        gs.mana_reserve = 0

    def main_phase_match(self, gs: GameState, opponent: GameState):
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._opp_gs = opponent

        my_creatures = [c for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()]

        # Craterhoof lethal check -- ETB handler pumps automatically, no manual pump
        if len(my_creatures) >= 5:
            for card in list(gs.zones.hand):
                if card.name == CRATERHOOF and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)  # _craterhoof_behemoth_etb fires automatically
                    break

        # Seam Rip: exiles any nonland permanent with MV <= 2 (not just enchantments)
        if opponent:
            opp_targets = sorted(
                [c for c in opponent.zones.battlefield
                 if not c.is_land() and getattr(c, 'cmc', 99) <= 2],
                key=lambda c: -getattr(c, 'cmc', 0)
            )
            if opp_targets:
                target = opp_targets[0]
                for card in list(gs.zones.hand):
                    if card.name == SEAM_RIP and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                        gs.cast_spell(card)  # ETB handler exiles via _seam_rip_etb
                        break

        # Nature's Rhythm ({X}{G}{G}): tutor a creature with MV <= X directly onto battlefield
        available_for_x = max(0, gs.mana_pool.total() - 2)
        NATURES_TARGETS = [
            (8, CRATERHOOF),
            (5, BRIGHTGLASS),
            (4, OUROBOROID),
        ]
        for card in list(gs.zones.hand):
            if card.name == NATURES_RHYTHM:
                for x_needed, target_name in NATURES_TARGETS:
                    if available_for_x >= x_needed:
                        target = next((c for c in gs.zones.library if c.name == target_name), None)
                        if target and gs.mana_pool.total() >= x_needed + 2:
                            gs.mana_pool.pay(card.mana_cost or "XGG", x_needed + 2)
                            gs.zones.hand.remove(card)
                            gs.zones.graveyard.append(card)
                            gs.zones.library.remove(target)
                            gs.zones.battlefield.append(target)
                            target.summoning_sickness = True
                            if target.name == CRATERHOOF:
                                n = len(my_creatures) + 1
                                for c in gs.zones.battlefield:
                                    if c.has(Tag.CREATURE) and not c.is_land():
                                        c.counters = (c.counters or 0) + n
                            gs._log(f"  Nature's Rhythm X={x_needed}: found {target_name}")
                            break
                break

        for name in (LLANOWAR, GENE_POLL, BADGERMOLE, LEYLINE_WEAVER,
                     OUROBOROID, BRIGHTGLASS, ARCHDRUID, FIGURE_FABLE, CRATERHOOF):
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)  # all ETB handlers fire automatically
                    break

        # Ouroboroid per-combat trigger: +X/+X to all creatures where X = Ouroboroid power
        for ouro in gs.zones.battlefield:
            if ouro.name == OUROBOROID:
                x = getattr(ouro, 'counters', 0) + getattr(ouro, '_base_power', 4)
                for c in gs.zones.battlefield:
                    if c.has(Tag.CREATURE) and not c.is_land():
                        c.counters = (c.counters or 0) + x
                gs._log(f"  Ouroboroid combat trigger: +{x}/+{x} to all creatures")
                break

        # Lumbering Worldwagon: dynamic power = # lands
        for wagon in gs.zones.battlefield:
            if wagon.name == "Lumbering Worldwagon":
                land_count = sum(1 for c in gs.zones.battlefield if c.is_land())
                wagon.counters = max(0, land_count - getattr(wagon, '_base_power', 0))

        self._cast_all_castable(gs)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if c.has(Tag.CREATURE) and not c.is_land()
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

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
