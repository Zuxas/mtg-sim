"""
apl/sultai_midrange_match.py -- Sultai (BUG) Midrange match APL

Archetype: interactive midrange/value-tempo. Trade one-for-one with cheap
removal, grind card advantage off value creatures, and protect the board with
free/off-turn counters. Closes IMPERFECTIONS no-apl-sultai_midrange.

Deck (decks/sultai_midrange_modern.txt -- kawasaki hirotaka, 2nd place Modern,
derived from mtg_meta.db deck_id=127635 "Sultai Midrange"):

  Value creatures / card advantage:
    - Psychic Frog ({U}{B}, 1/3): connects -> draw; discard for +1/+1; the
      premier BUG card-advantage two-drop.
    - Quantum Riddler ({3}{U}{U}, flyer): ETB draw, empty-hand draw doubler.
    - Abhorrent Oculus ({2}{U}, flyer): exile 6 from GY as additional cost,
      manifests dread each opp upkeep -- recurring card advantage.
    - Satoru, the Infiltrator / Aven Heartstabber / Bloodghast: cheap,
      evasive, recursive value bodies.

  Removal:
    - Fatal Push ({B}): destroy mv<=2 (mv<=4 with revolt; deck runs 10 fetches
      so revolt is near-always on).
    - Flare of Malice ({2}{B}{B} or free): edict-style, opponent sacrifices its
      greatest-mv creature -- modeled here as kill-the-biggest.
    - Culling Ritual ({2}{B}{G}): symmetric sweeper of nonland mv<=2 permanents
      -- only fired when the opponent is wide and we are not.

  Interaction (free / off-turn counters):
    - Force of Negation, Flare of Denial, Subtlety: protect threats and answer
      key spells. Free/off-turn nature means we do NOT hold extra mana for them;
      the AwareMatchAPL R1 priority machinery fires them from untapped lands on
      the opponent's turn (Force of Negation + Subtlety are in COUNTER_VALIDITY).

Engine seams used: gs.cast_spell, gs.mana_pool.can_cast, gs.tap_lands,
self._play_land_if_able, self._kill_with_removal (MATCH_REMOVAL), c.has(Tag.X),
c.is_land(), all getattr-defensive. declare_attackers / declare_blockers are
inherited from AwareMatchAPL (field-aware trade + lethal logic).
"""
from __future__ import annotations
from data.card import Tag
from engine.game_state import GameState
from engine.match_state import safe_power, safe_toughness
from apl.aware_match_apl import AwareMatchAPL

# Value creatures / threats
PSYCHIC_FROG = "Psychic Frog"
QUANTUM      = "Quantum Riddler"
OCULUS       = "Abhorrent Oculus"
SATORU       = "Satoru, the Infiltrator"
AVEN         = "Aven Heartstabber"
BLOODGHAST   = "Bloodghast"
BOGGART      = "Boggart Trawler"
SUBTLETY     = "Subtlety"

# Spells
FATAL_PUSH   = "Fatal Push"
FLARE_MALICE = "Flare of Malice"
CULLING      = "Culling Ritual"
FORCE_NEG    = "Force of Negation"
FLARE_DENIAL = "Flare of Denial"
PICK_POISON  = "Pick Your Poison"
UNEARTH      = "Unearth"
BIRTHING     = "Birthing Ritual"


class SultaiMidrangeMatchAPL(AwareMatchAPL):
    name = "Sultai Midrange"
    ARCHETYPE = "midrange"

    # Free / off-turn counters -- COUNTER_COST kept at 1 so we barely tax our
    # own development; the R1 machinery fires them from untapped lands on the
    # opponent's turn regardless of this reserve.
    COUNTER_COST  = 1
    COUNTER_CARDS = {FORCE_NEG, FLARE_DENIAL, SUBTLETY}

    # spec = (cost_doc, max_toughness). _kill_with_removal uses the toughness
    # gate; the cost string is documentation only (it pays card.mana_cost).
    MATCH_REMOVAL = {
        FATAL_PUSH:   ("B",    4),    # mv<=2 base, mv<=4 revolt (10 fetches); toughness-gated proxy
        FLARE_MALICE: ("2BB",  None), # edict: opponent sacrifices greatest-mv creature
    }
    MATCH_BOUNCE = set()
    MATCH_EXILE  = set()

    # Subtlety flashes in as a 3/2 flyer when we have nothing better to do with
    # end-of-turn mana (its counter mode is driven by the R1 machinery).
    FLASH_THREATS = {SUBTLETY}

    # Deploy order: cheap evasive value first, big card-advantage flyers last.
    _DEPLOY_CURVE = [BOGGART, PSYCHIC_FROG, SATORU, AVEN, BLOODGHAST,
                     BIRTHING, QUANTUM]

    # ------------------------------------------------------------------ keep
    def keep(self, hand, mulligans, on_play):
        """Midrange mulligan: 2-5 lands, at least one early interactive/curve
        play. Snap-keep at the London floor."""
        if len(hand) <= 4:
            return True
        lands = [c for c in hand if c.is_land()]
        n_lands = len(lands)
        if n_lands < 2 or n_lands > 5:
            return False
        nonlands = [c for c in hand if not c.is_land()]
        if not nonlands:
            return False
        has_early = any((getattr(c, 'cmc', 99) or 99) <= 3 for c in nonlands)
        has_action = any(c.has(Tag.CREATURE)
                         or c.name in self.MATCH_REMOVAL
                         or c.name in self.COUNTER_CARDS
                         for c in nonlands)
        return (has_early and has_action) or mulligans >= 2

    def bottom(self, hand, n):
        lands  = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -(getattr(c, 'cmc', 0) or 0))
        return (lands[4:] + spells)[:n]

    # ----------------------------------------------------------- mana reserve
    def reserve_mana(self, gs: GameState, opponent: GameState):
        """Light hold: leave 1 land up only when a hardcastable counter is in
        hand AND we have spare lands -- otherwise develop the board fully."""
        counters_in_hand = any(c.name in self.COUNTER_CARDS for c in gs.zones.hand)
        n_untapped = sum(1 for c in gs.zones.battlefield
                         if c.is_land() and not getattr(c, 'tapped', False))
        gs.mana_reserve = 1 if (counters_in_hand and n_untapped >= 4) else 0

    # ---------------------------------------------------------------- helpers
    def _opp_creatures(self, opponent: GameState, untapped_only: bool = False):
        if opponent is None:
            return []
        out = [c for c in opponent.zones.battlefield
               if c.has(Tag.CREATURE) and not c.is_land()]
        if untapped_only:
            out = [c for c in out if not getattr(c, 'tapped', False)]
        return out

    def _try_culling_ritual(self, gs: GameState, opponent: GameState) -> bool:
        """Culling Ritual is symmetric (destroys our own mv<=2 nonland perms
        too). Only fire when the opponent is wide with small permanents and we
        are not committed to the board."""
        if opponent is None:
            return False
        opp_small = [c for c in opponent.zones.battlefield
                     if not c.is_land() and (getattr(c, 'cmc', 9) or 9) <= 2]
        my_small = [c for c in gs.zones.battlefield
                    if not c.is_land() and (getattr(c, 'cmc', 9) or 9) <= 2]
        if len(opp_small) < 3 or len(my_small) > 1:
            return False
        for card in list(gs.zones.hand):
            if card.name == CULLING and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                return bool(gs.cast_spell(card))
        return False

    def _try_unearth(self, gs: GameState) -> bool:
        """Unearth a mv<=3 creature from our graveyard for {B}."""
        targets = [c for c in gs.zones.graveyard
                   if c.has(Tag.CREATURE) and (getattr(c, 'cmc', 9) or 9) <= 3]
        if not targets:
            return False
        for card in list(gs.zones.hand):
            if card.name == UNEARTH and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                return bool(gs.cast_spell(card))
        return False

    def _deploy_curve(self, gs: GameState):
        for name in self._DEPLOY_CURVE:
            for card in list(gs.zones.hand):
                if card.name == name and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                    gs.cast_spell(card)
                    break

    def _deploy_oculus(self, gs: GameState):
        """Abhorrent Oculus costs 6 GY cards as an additional cost -- only cast
        when the graveyard can actually pay."""
        if len(gs.zones.graveyard) < 6:
            return
        for card in list(gs.zones.hand):
            if card.name == OCULUS and gs.mana_pool.can_cast(card.mana_cost, card.cmc):
                gs.cast_spell(card)
                return

    def _dump_remaining_creatures(self, gs: GameState):
        """Spend leftover mana on the cheapest castable value creature.
        Oculus is excluded (handled by _deploy_oculus with its GY gate)."""
        changed, attempts = True, 0
        while changed and attempts < 8:
            changed = False
            attempts += 1
            castable = [c for c in gs.zones.hand
                        if c.has(Tag.CREATURE) and c.name != OCULUS
                        and gs.mana_pool.can_cast(c.mana_cost, c.cmc)]
            if castable:
                spell = min(castable, key=lambda c: getattr(c, 'cmc', 0) or 0)
                if gs.cast_spell(spell):
                    changed = True

    # ------------------------------------------------------------ main phase
    def main_phase(self, gs: GameState):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs: GameState, opponent: GameState):
        if opponent is not None:
            gs._match_opp = opponent
        self._my_gs = gs
        self._opp_gs = opponent

        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Symmetric sweeper only when clearly ahead on the math.
        self._try_culling_ritual(gs, opponent)

        # 2. Single-target removal on the opponent's biggest live threat.
        if opponent is not None:
            threats = sorted(self._opp_creatures(opponent, untapped_only=True),
                             key=lambda c: -safe_power(c))
            for t in threats:
                if safe_power(t) >= 2:
                    if self._kill_with_removal(gs, opponent, t):
                        break

        # 3. Recur a cheap creature with Unearth.
        self._try_unearth(gs)

        # 4. Deploy value creatures / engine on curve, then the big flyers.
        self._deploy_curve(gs)
        self._deploy_oculus(gs)

        # 5. Spend any leftover mana on remaining bodies.
        self._dump_remaining_creatures(gs)

    # declare_attackers / declare_blockers inherited from AwareMatchAPL.
