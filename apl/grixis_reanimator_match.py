"""
apl/grixis_reanimator_match.py — Grixis Reanimator (Modern)

Combo: Unmarked Grave (nonlegendary to GY) + Persist (reanimate) → Abhorrent Oculus.
       Hard-cast Archon of Cruelty if mana allows.
Key:
- Unmarked Grave: Oracle "Search library for nonlegendary card, put in GY, shuffle."
- Persist: Oracle "Return target nonlegendary creature card from GY to battlefield
           with a -1/-1 counter." Bypasses Oculus's cast-cost exile requirement.
- Archon ETB/attack: opponent sacs permanent + discards + loses 3 life; we draw + gain 3.
- Abhorrent Oculus: 2/2 flying. At each opponent's upkeep: manifest dread.

Kill distribution (from format_config.py): T2 15%, T3 45%, T4 30%, T5 10%.
As opponent: routed to ComboKillSampler via format_config 'combo' set.
"""
from apl.match_apl import MatchAPL
from data.card import Tag
from engine.match_state import safe_power

ARCHON = "Archon of Cruelty"
OCULUS = "Abhorrent Oculus"
GRAVE = "Unmarked Grave"
PERSIST = "Persist"
THOUGHTSEIZE = "Thoughtseize"
INQUISITION = "Inquisition of Kozilek"

REANIMATE_TARGETS = {OCULUS}

# The (few) maindeck answers our Boros opponent actually has to the reanimated
# Archon. Modeled as the cards our hand-disruption (Thoughtseize / Inquisition /
# the Archon ETB discard) preferentially STRIPS -- an engine-scored effect, not
# card-draw and not a tuned probability. Galvanic Discharge + Thraben Charm are
# the only ones that can answer a 6-toughness body; Lightning Bolt only reaches
# the smaller bodies. Stripping them is what makes us the DOG (spec Component 3
# grixis: "Thoughtseize removing our answer from hand").
OUR_ANSWERS = {
    "Galvanic Discharge": 4,   # energy burn -- can kill the Archon (highest value to strip)
    "Thraben Charm":      4,   # 2x creatures dmg / GY exile -- can kill the Archon
    "Static Prison":      3,   # exile (not in lowcurve main, but answers the Archon if present)
    "Lightning Bolt":     2,   # only reaches the small bodies, still worth taking
}


def _is_legendary(card):
    return 'Legendary' in (getattr(card, 'type_line', '') or '')


class GrixisReanimatorMatchAPL(MatchAPL):
    name = "Grixis Reanimator"
    win_condition_damage = 20
    max_turns = 8

    # combo-spine #2 Site 1: the Archon's brutal ETB/attack trigger drains the
    # opponent for 3 each time it fires. A scalar opponent.life write on the per-
    # turn view does NOT propagate to the match life total (spec spine #3), so the
    # drain is routed through gs.damage_dealt in main phase 1 and made visible by
    # WANTS_BURN (same channel + flag the yawgmoth cell uses). The body's COMBAT
    # damage already counts via _resolve_combat; this only adds the trigger's
    # direct-damage rider. WANTS_BURN affects ONLY cells where grixis is the
    # active seat -- in the single-hero sweep grixis is seat B only, so the only
    # cell it can move is boros-vs-grixis (the cell we are calibrating).
    WANTS_BURN = True

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        has_tutor = any(c.name == GRAVE for c in hand)
        has_reanimate = any(c.name == PERSIST for c in hand)
        has_target = any(c.name in REANIMATE_TARGETS for c in hand)
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0: return False
        if (has_tutor or has_reanimate) and lands >= 1: return True
        if has_target and lands >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        high_cmc = sorted([c for c in hand if not c.is_land()],
                          key=lambda c: -getattr(c, 'cmc', 0))
        lands = [c for c in hand if c.is_land()]
        return (lands[3:] + high_cmc)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Hand disruption — Thoughtseize ({B}) / Inquisition of Kozilek ({B}).
        # Oracle (Thoughtseize): "Target player reveals hand. You choose a nonland
        #   card, they discard it. You lose 2 life."
        # Oracle (Inquisition): "...choose a nonland card with mana value 3 or less..."
        # The deck runs 4 Thoughtseize + 4 Inquisition (+ Grief). They preferentially
        # STRIP OUR ANSWER to the Archon (Galvanic Discharge / Thraben Charm / Bolt),
        # which is the engine-scored mechanism that makes us the dog -- with our
        # removal in the bin, the reanimated body resolves unanswered. NOT card-draw,
        # NOT a tuned probability (it fires off the actual copy-counts in hand).
        if opponent and gs.turn <= 3:
            for c in list(gs.zones.hand):
                disc_name = c.name
                if disc_name == THOUGHTSEIZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    gs.life -= 2  # oracle: you lose 2 life
                    self._strip_hand(gs, opponent, max_cmc=None)
                elif disc_name == INQUISITION and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    self._strip_hand(gs, opponent, max_cmc=3)
                else:
                    continue
                break

        # 1b. Faithless Looting ({R}) — draw 2, discard 2; PITCH the Archon into the
        # graveyard. Oracle: "Draw two cards, then discard two cards. Flashback {2}{R}."
        # This is the canonical reanimator enabler: a hand Archon (uncastable at 8 mana)
        # is pitched to the bin so Persist/Reanimate can return it the same turn. The
        # engine handler discards generically (lands first), so the APL drives the
        # discard. Faithful card-selection, not a tuned assembly probability.
        FAITHLESS = "Faithless Looting"
        for c in list(gs.zones.hand):
            if c.name == FAITHLESS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.mana_pool.pay(c.mana_cost, c.cmc)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.zones.draw(2)
                for _ in range(2):
                    if not gs.zones.hand:
                        break
                    archons = [x for x in gs.zones.hand if x.name == ARCHON]
                    lands = [x for x in gs.zones.hand if x.is_land()]
                    if archons:
                        d = archons[0]                    # pitch Archon -> reanimate it
                    elif len(lands) > 3:
                        d = lands[-1]                     # excess land
                    else:
                        d = max(gs.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.hand.remove(d)
                    gs.zones.graveyard.append(d)
                gs._log("  Faithless Looting: draw 2, discard 2 (pitch Archon)")
                break

        # 2. Unmarked Grave ({1}{B}) — tutor the ARCHON into the graveyard.
        # Oracle: "Search your library for a nonlegendary card, put it in your
        #          graveyard, then shuffle."
        # A real Grixis pilot fetches Archon of Cruelty -- the recurring brutal
        # payoff -- not "any creature." Pre-fix this grabbed max-cmc of WHATEVER
        # was in the library and was gated off the moment any small evoke body
        # (Grief / Bowmasters) hit the GY, so Persist kept reanimating chaff and
        # the Archon almost never came online. Now it seeds the Archon whenever one
        # is not already reachable (in GY or on our battlefield).
        archon_reachable = any(
            x.name == ARCHON for x in gs.zones.graveyard + gs.zones.battlefield)
        if not archon_reachable:
            for c in list(gs.zones.hand):
                if c.name == GRAVE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    lib_archons = [x for x in gs.zones.library if x.name == ARCHON]
                    fetch = lib_archons[0] if lib_archons else max(
                        [x for x in gs.zones.library
                         if x.has(Tag.CREATURE) and not _is_legendary(x)],
                        key=lambda x: getattr(x, 'cmc', 0), default=None)
                    if fetch is not None:
                        gs.zones.library.remove(fetch)
                        gs.zones.graveyard.append(fetch)
                        gs._log(f"  Unmarked Grave: put {fetch.name} in GY")
                    break

        # 2b. Reanimate ({B}) — return the Archon from GY as a full 6/6 (no -1/-1).
        # Oracle: "Put target creature card from a graveyard onto the battlefield
        #          under your control. You lose life equal to its mana value."
        # A second reanimation path (4 copies) + the recursion engine: after our
        # removal kills the Archon it returns to GY, and Reanimate/Persist bring it
        # straight back. Identity-safe manual move (engine has no Reanimate handler).
        REANIMATE = "Reanimate"
        gy_archon = next((x for x in gs.zones.graveyard if x.name == ARCHON), None)
        on_bf_archon = any(x.name == ARCHON for x in gs.zones.battlefield)
        if gy_archon is not None and not on_bf_archon:
            for c in list(gs.zones.hand):
                if c.name == REANIMATE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    # identity-safe GY -> battlefield
                    moved = False
                    for i, x in enumerate(gs.zones.graveyard):
                        if x is gy_archon:
                            gs.zones.battlefield.append(gs.zones.graveyard.pop(i))
                            moved = True
                            break
                    if moved:
                        gy_archon.turn_entered = gs.turn
                        gy_archon.summoning_sickness = True
                        gs.life -= 8  # Archon mana value (grixis view; not a scored clock)
                        gs._log(f"  Reanimate: return {ARCHON} (full 6/6)")
                        self._resolve_reanimated_threat(gs, opponent, gy_archon)
                    break

        # 3. Persist ({1}{B}) — reanimate nonlegendary creature from GY
        # Oracle: "Return target nonlegendary creature card from your graveyard to the
        #          battlefield with a -1/-1 counter on it."
        # Key: bypasses Abhorrent Oculus's additional cast cost (exile 6 from GY).
        # NOTE: the ENGINE owns the reanimation. SPELL_EFFECTS['Persist'] ->
        # _persist_spell (engine/card_handlers_verified.py) fires inside
        # gs.cast_spell(): it picks the SAME max-cmc nonlegendary creature, moves
        # it GY -> battlefield, marks it summoning-sick, and applies the -1/-1.
        # The pre-fix code re-did that move (gs.zones.graveyard.remove(tgt)) AFTER
        # the engine had already pulled the card -> 'list.remove(x): x not in list'
        # on nearly every Persist, which aborted Grixis's whole turn via
        # _simple_play_turn's except-and-fallback. We must NOT move the card again
        # (a value/identity re-remove crashes-or-no-ops, and re-appending would put
        # a DUPLICATE creature on the battlefield). We only mirror the engine's
        # target choice so we can fire the reanimated creature's ETB (the engine
        # handler moves the card but does not trigger its ETB).
        gy_targets = [c for c in gs.zones.graveyard
                      if c.has(Tag.CREATURE) and not _is_legendary(c)]
        if gy_targets:
            for c in list(gs.zones.hand):
                if c.name == PERSIST and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    # Snapshot the battlefield by identity BEFORE the engine moves
                    # the card, so we can find the body the engine ACTUALLY landed
                    # (the engine's _persist_spell picks its own max-cmc target;
                    # the pre-fix code guessed and missed, so the brutal ETB fired
                    # on only ~9%% of reanimations). No value-based .remove().
                    before = {id(x) for x in gs.zones.battlefield}
                    gs.cast_spell(c)  # engine _persist_spell reanimates a body
                    new_bodies = [x for x in gs.zones.battlefield
                                  if id(x) not in before and x.has(Tag.CREATURE)]
                    for body in new_bodies:
                        gs._log(f"  Persist: reanimate {body.name} (with -1/-1 counter)")
                        self._resolve_reanimated_threat(gs, opponent, body)
                    break

        # 4. Hard-cast Archon of Cruelty ({6}{B}{B}) — 8 mana, late game threat
        for c in list(gs.zones.hand):
            if c.name == ARCHON and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                if any(x is c for x in gs.zones.battlefield):
                    self._resolve_reanimated_threat(gs, opponent, c)
                break

        # 4b. Archon recurring ATTACK trigger. declare_attackers is NEVER called on
        # the run_match gauntlet path (combat is resolved by _resolve_combat reading
        # bodies -- spec spine #1), so the Archon's on-attack trigger was dropped
        # entirely and the body acted as a vanilla beater. Fire it here in main phase
        # 1 for each Archon that WILL attack this turn (untapped, not summoning-sick).
        # The body's combat damage still resolves in _resolve_combat; this adds only
        # the trigger rider (sac + discard + 3 drain). Once-per-turn guard prevents a
        # double fire if any path also calls declare_attackers.
        if opponent:
            for c in list(gs.zones.battlefield):
                if (c.name == ARCHON
                        and not getattr(c, 'summoning_sickness', False)
                        and not getattr(c, 'tapped', False)
                        and getattr(c, '_archon_atk_turn', None) != gs.turn):
                    c._archon_atk_turn = gs.turn
                    self._trigger_etb(gs, opponent, c)
                    gs._log(f"  Archon attacks: brutal trigger fires")

        # 5. Abhorrent Oculus ({2}{U}) direct cast — requires exiling 6 from GY
        for c in list(gs.zones.hand):
            if c.name == OCULUS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                # Never exile our Archon (recursion fuel) to pay Oculus's cost.
                exile_pool = [x for x in gs.zones.graveyard if x.name != ARCHON][:6]
                if len(exile_pool) >= 6:
                    for ex in exile_pool:
                        gs.zones.graveyard.remove(ex)
                        gs.zones.exile.append(ex)
                    gs.cast_spell(c)
                    gs._log(f"  Oculus: direct cast (exile 6 from GY)")
                break

        # 6. Fill curve
        self._cast_all_castable(gs)

    def _trigger_etb(self, gs, opponent, card):
        """Archon of Cruelty ETB / attack trigger: opponent sacs + discards + loses 3;
        we draw + gain 3.
        Oracle: 'Whenever this creature enters or attacks, target opponent sacrifices a
        creature or planeswalker of their choice, discards a card, and loses 3 life.
        You draw a card and gain 3 life.'
        Note: opponent 'chooses' — we model as they keep best, sac weakest.

        Damage-channel discipline (spec spine #3): the sac and discard are ZONE MOVES
        that propagate to the shared TwoPlayerGameState. The 3-life loss is direct
        damage -- a scalar `opponent.life -= 3` on the per-turn view is DROPPED, so it
        is routed through gs.damage_dealt (active main-phase-1 channel) and made visible
        by WANTS_BURN. Our draw/lifegain stay on the grixis view (faithful, not a scored
        clock; card-draw is explicitly NOT a lever here).
        """
        if card.name != ARCHON or not opponent:
            return
        opp_perms = [c for c in opponent.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)]
        if opp_perms:
            sac = min(opp_perms, key=lambda x: safe_power(x))
            opponent.zones.battlefield.remove(sac)
            opponent.zones.graveyard.append(sac)
        if opponent.zones.hand:
            discard = self._pick_discard(opponent.zones.hand, max_cmc=None)
            opponent.zones.hand.remove(discard)
            opponent.zones.graveyard.append(discard)
        gs.damage_dealt += 3          # routed via Site 1 (WANTS_BURN) -> match life
        gs.zones.draw(1)
        gs.life += 3
        gs._log(f"  Archon ETB/attack: opp sac+discard, 3 drain (->damage_dealt), we draw+3")

    def _pick_discard(self, hand, max_cmc=None):
        """Choose the card to strip from the opponent's hand. Prefer the highest-value
        ANSWER to our threat (our removal), then the highest-mana-value nonland, then
        anything. `max_cmc` bounds the choice (Inquisition mode)."""
        pool = [c for c in hand
                if (max_cmc is None or getattr(c, 'cmc', 0) <= max_cmc)]
        if not pool:
            pool = list(hand)
        answers = [c for c in pool if c.name in OUR_ANSWERS]
        if answers:
            return max(answers, key=lambda c: OUR_ANSWERS.get(c.name, 0))
        nonlands = [c for c in pool if not c.is_land()]
        if nonlands:
            return max(nonlands, key=lambda c: getattr(c, 'cmc', 0))
        return pool[0]

    def _strip_hand(self, gs, opponent, max_cmc=None):
        """Resolve a Thoughtseize / Inquisition: strip our best answer from the
        opponent's hand (zone move -> propagates)."""
        if not opponent.zones.hand:
            return
        d = self._pick_discard(opponent.zones.hand, max_cmc=max_cmc)
        opponent.zones.hand.remove(d)
        opponent.zones.graveyard.append(d)
        gs._log(f"  Disruption: strip {d.name} from opp hand")

    def _resolve_reanimated_threat(self, gs, opponent, body):
        """A threat (Archon, Oculus, ...) just hit our battlefield. Offer the opponent
        the honest interaction window (Component 1: removal / GY-hate on the lone body),
        then -- if it survives -- fire the Archon ETB. The interaction is double-gated
        and a no-op unless the opponent set WANTS_COMBO_INTERACTION (Boros G1 maindeck
        has ~no reliable answer to a 6-toughness body, so it RARELY fires)."""
        if opponent is None:
            return
        if self._offer_threat(gs, opponent, body):
            return  # answered -> body removed (zone move already applied)
        if body.name == ARCHON and any(x is body for x in gs.zones.battlefield):
            self._trigger_etb(gs, opponent, body)

    def _offer_threat(self, gs, opponent, body):
        """Call the shared interaction layer at the decisive step. Returns True iff the
        opponent answered (and the body was removed). No-op (False) unless the opponent
        opted in via WANTS_COMBO_INTERACTION -- the structural initiation gate is THIS
        call (only a combo APL reaches it), the capability gate is the opp flag."""
        opp_apl = getattr(gs, '_match_opp_apl', None)
        if opp_apl is None:
            return False
        try:
            from engine.combo_interaction import (offer_interaction, ComboEvent,
                                                   RESOLVE_THREAT)
            ev = ComboEvent(kind=RESOLVE_THREAT, targets=[body])
            res = offer_interaction(gs, self, opponent, opp_apl, ev)
            return bool(res.disrupted)
        except Exception:
            return False

    def declare_attackers(self, gs, opponent):
        attackers = [c for c in gs.zones.battlefield
                     if not c.is_land() and c.has(Tag.CREATURE)
                     and not getattr(c, 'summoning_sickness', False)
                     and not getattr(c, 'tapped', False)]
        # Archon attack trigger fires same as ETB. NOTE: declare_attackers is NOT
        # called on the run_match gauntlet path (the trigger is fired in
        # main_phase_match step 4b instead); this branch only runs on paths that do
        # call it. Once-per-turn guard shared with 4b prevents a double fire.
        if opponent:
            for c in attackers:
                if (c.name == ARCHON
                        and getattr(c, '_archon_atk_turn', None) != gs.turn):
                    c._archon_atk_turn = gs.turn
                    self._trigger_etb(gs, opponent, c)
        return attackers

    def declare_blockers(self, gs, opp, attackers):
        return {}

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'delta' in n or 'strand' in n or 'flats' in n: return 0
            if 'grave' in n or 'shrine' in n or 'fountain' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
