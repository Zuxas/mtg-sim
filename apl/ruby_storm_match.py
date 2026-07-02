"""
apl/ruby_storm_match.py — Ruby Storm APL (Modern) — HAND-AUDITED 2026-07-02

Was: auto-generated stub flagged 'needs manual audit; INFLATED — storm wins
0/50, Grapeshot wish-gated so kill unreachable' (mismodeled_matchups
'ruby storm'). Audit findings + fixes:
  1. KILL REACHABILITY (engine side): decks/ruby_storm_modern.txt mains
     1 Grapeshot + 3 Wish; every June-2026 mtg_meta.db list keeps the second
     Grapeshot in the SB behind Wish. engine _wish_spell required
     gs._sideboard, which NO runner populates -> Wish was a silent no-op in
     every sim. Fixed in card_handlers_verified._wish_spell (wishboard fetch:
     one Grapeshot/game at wish-cost + card-cost).
  2. SEQUENCING (this file): cost reducer (Ruby Medallion) FIRST, then Ral,
     then rituals -> cantrips -> Wish; storm payoff STRICTLY LAST, held until
     lethal (copies >= opp life) or storm-count is large. The old loop cast
     in raw hand order and pre-checked can_cast with RAW cmc, bypassing the
     Medallion discount (engine _COST_REDUCTIONS now covers the shell).
  3. RAL: the old loop skipped ALL creatures, so Ral, Monsoon Mage (a core
     engine piece) was never cast. Now cast early; flips after 3 spells in a
     turn, then pings 1 per I/S cast — same model as goldfish RubyStormAPL.
  4. STORM ARITHMETIC (audited): gs.cast_spell increments
     spells_cast_this_turn BEFORE the handler resolves, so _grapeshot_spell's
     copies = 1 + max(0, spells_cast_this_turn - 1) = spells cast before it
     + 1. Correct per oracle; copies_if_cast at decision time = count + 1.
  5. Past in Flames: the engine handler is log-only, so the flashback rebuy
     is modeled HERE, mirroring goldfish RubyStormAPL._chain(from_gy=True):
     after PiF resolves, rituals/Manamorphose in the GY are recast at their
     own (Medallion-discounted) cost, exiled after use, and counted for
     storm (flashback casts are casts). PiF is held until an active storm
     turn (3+ spells already cast) so the rebuy lands on the combo turn.
"""
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

RUBY_MEDALLION = "Ruby Medallion"
DESPERATE_RITUAL = "Desperate Ritual"
MANAMORPHOSE = "Manamorphose"
PYRETIC_RITUAL = "Pyretic Ritual"
RECKLESS_IMPULSE = "Reckless Impulse"
WRENNS_RESOLVE = "Wrenn's Resolve"
GLIMPSE_THE_IMPOSSIB = "Glimpse the Impossible"
VALAKUT_AWAKENING = "Valakut Awakening"
PAST_IN_FLAMES = "Past in Flames"
WISH = "Wish"
GRAPESHOT = "Grapeshot"
RAL = "Ral, Monsoon Mage"
URABRASK = "Urabrask"

RITUALS = {PYRETIC_RITUAL, DESPERATE_RITUAL}
DRAW_CANTRIPS = {RECKLESS_IMPULSE, WRENNS_RESOLVE, GLIMPSE_THE_IMPOSSIB,
                 VALAKUT_AWAKENING}
PAYOFFS = {GRAPESHOT, "Empty the Warrens", "Galvanic Relay"}
ENGINE_PIECES = RITUALS | {MANAMORPHOSE} | DRAW_CANTRIPS | {RUBY_MEDALLION, RAL}


class RubyStormMatchAPL(MatchAPL):
    # R3 (2026-06-28): casts every spell via gs.cast_spell so
    # spells_cast_this_turn accrues + the storm handlers fire. WANTS_STORM
    # opts into the gated match-path main1 spell-damage sync.
    WANTS_STORM = True
    name = "Ruby Storm"
    win_condition_damage = 20
    max_turns = 12

    # ── Mulligan (storm-aware; the old keep counted CREATURES as threats
    #    in a 5-creature deck) ─────────────────────────────────────────
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = [c for c in hand if c.is_land()]
        if not lands:
            return False
        if len(lands) > 4:
            return False
        business = [c for c in hand if c.name in ENGINE_PIECES]
        has_engine = any(c.name in (RAL, RUBY_MEDALLION) for c in hand)
        if len(lands) >= 2 and len(business) >= 2:
            return True
        if has_engine and len(business) >= 2:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        to_bottom = []
        lands = [c for c in hand if c.is_land()]
        if len(lands) > 2:
            to_bottom.extend(lands[2:])
        keep_names = RITUALS | {MANAMORPHOSE, RAL, RUBY_MEDALLION, GRAPESHOT}
        rest = sorted([c for c in hand
                       if not c.is_land() and c.name not in keep_names],
                      key=lambda c: -getattr(c, 'cmc', 0))
        for c in rest:
            if len(to_bottom) >= n:
                break
            if c not in to_bottom:
                to_bottom.append(c)
        # Pad (guarantee n) from whatever remains
        if len(to_bottom) < n:
            for c in hand:
                if c not in to_bottom:
                    to_bottom.append(c)
                    if len(to_bottom) >= n:
                        break
        return to_bottom[:n]

    # ── Turn drivers (goldfish + match, main1 + main2 share _storm_turn) ──
    def main_phase(self, gs):
        self._storm_turn(gs, None)

    def main_phase_match(self, gs, opponent):
        self._storm_turn(gs, opponent)

    def main_phase2(self, gs):
        self._storm_turn(gs, None)

    def main_phase2_match(self, gs, opponent):
        self._storm_turn(gs, opponent)

    def _storm_turn(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        if self._should_go_off(gs):
            self._chain(gs)
            self._try_payoff(gs, opponent)
        else:
            self._setup(gs)

    def _should_go_off(self, gs):
        """Storm decks SCULPT, then go off — the pre-audit loop dumped 1-2
        spells every turn ('chip mode'), so spells_cast_this_turn never got
        big and the payoff gate never opened (goldfish RubyStormAPL had the
        same hold-rituals/go-off split; this ports it). Go off when payoff
        access (Grapeshot in hand, or Wish to fetch it) meets enough fuel
        for a real storm count, or as a late-game dump."""
        if gs.turn >= 7:
            return True  # desperation dump
        if gs.mana_pool.total() < 3:
            return False
        hand_names = [c.name for c in gs.zones.hand]
        core = sum(1 for n in hand_names
                   if n in RITUALS or n == MANAMORPHOSE)
        draw = sum(1 for n in hand_names if n in DRAW_CANTRIPS)
        has_pif = PAST_IN_FLAMES in hand_names
        fuel = core + draw + (2 if (has_pif and core) else 0)
        payoff_access = (GRAPESHOT in hand_names) or (WISH in hand_names)
        if payoff_access and fuel >= 3:
            return True
        if fuel >= 6:
            return True  # Ral-ping storm turn even without payoff access
        return False

    def _setup(self, gs):
        """Sculpt turns: develop the engine (Medallion, Ral), bank the
        wishboard payoff, and cast card-advantage cantrips on curve — but
        HOLD rituals / Manamorphose / Past in Flames / payoffs for the
        go-off turn."""
        hold = RITUALS | PAYOFFS | {MANAMORPHOSE, PAST_IN_FLAMES}
        progressed = True
        while progressed:
            progressed = False
            for c in sorted([x for x in gs.zones.hand if not x.is_land()],
                            key=self._prio):
                if c.name in hold:
                    continue
                if c.name == RAL and any(x.name == RAL
                                         for x in gs.zones.battlefield):
                    continue
                if self._cast(gs, c):
                    progressed = True
                    break
        # Out of rituals to hold -> dig with Manamorphose
        if not any(c.name in RITUALS for c in gs.zones.hand):
            for c in list(gs.zones.hand):
                if c.name == MANAMORPHOSE:
                    self._cast(gs, c)

    # ── Casting core ─────────────────────────────────────────────────
    def _cast(self, gs, card):
        """Cast via gs.cast_spell with NO raw-cmc pre-check — cast_spell
        applies the Ruby Medallion _COST_REDUCTIONS discount internally
        (the old pre-check used full cmc and skipped discounted casts).
        On success, run Ral flip/ping bookkeeping."""
        if not gs.cast_spell(card):
            return False
        self._ral_tick(gs, card)
        if card.name == PAST_IN_FLAMES:
            self._flashback_chain(gs)
        return True

    def _flashback_chain(self, gs):
        """Past in Flames rebuy (audit #5): I/S in the GY regain castability
        this turn at their own mana cost ('flashback equal to its mana
        cost'), exiling after use. The engine PiF handler is log-only, so
        the rebuy is modeled here exactly like goldfish
        RubyStormAPL._chain(from_gy=True): rituals + Manamorphose only
        (conservative — no GY Grapeshot rebuy), Medallion-discounted cost
        paid from the live pool, storm counter incremented (flashback casts
        are casts), Ral pings apply."""
        meds = sum(1 for c in gs.zones.battlefield
                   if c.name == RUBY_MEDALLION)
        cost = max(1, 2 - meds)
        progressed = True
        while progressed:
            progressed = False
            for c in list(gs.zones.graveyard):
                if c.name not in RITUALS and c.name != MANAMORPHOSE:
                    continue
                if gs.mana_pool.total() < cost:
                    continue
                gs.mana_pool.pay("{R}" if cost == 1 else "{1}{R}", cost)
                gs.zones.graveyard.remove(c)
                gs.zones.exile.append(c)
                gs.spells_cast_this_turn += 1
                gs.noncreature_spells_this_turn += 1
                if c.name in RITUALS:
                    gs.mana_pool.add("R", 3)
                else:
                    gs.mana_pool.flex += 2
                    gs.zones.draw(1)
                gs._log(f"  Flashback {c.name} (Past in Flames)")
                self._ral_tick(gs, c)
                progressed = True
                break

    def _ral_tick(self, gs, card):
        """Ral, Monsoon Mage: flips after 3 spells in a turn; once flipped,
        pings 1 per instant/sorcery cast. Mirrors goldfish RubyStormAPL.
        Flip state lives ON the battlefield card (aliased list) so it
        survives the match runner's per-turn view rebuilds."""
        ral = next((c for c in gs.zones.battlefield if c.name == RAL), None)
        if ral is None:
            return
        if (not getattr(ral, '_flipped', False)
                and gs.spells_cast_this_turn >= 3):
            ral._flipped = True
            gs._log(f"  RAL FLIPS! ({gs.spells_cast_this_turn} spells)")
        if (getattr(ral, '_flipped', False)
                and (card.has(Tag.INSTANT) or card.has(Tag.SORCERY))):
            gs.damage_dealt += 1

    def _prio(self, c):
        """Storm-turn cast order: reducer -> Ral -> rituals -> free cantrip
        -> draw -> Wish (fetches the wishboard payoff) -> bodies -> PiF."""
        n = c.name
        if n == RUBY_MEDALLION:
            return 0
        if n == RAL:
            return 1
        if n in RITUALS:
            return 2
        if n == MANAMORPHOSE:
            return 3
        if n in DRAW_CANTRIPS:
            return 4
        if n == WISH:
            return 5
        if n == URABRASK:
            return 6
        if n == PAST_IN_FLAMES:
            return 7
        return 8

    def _chain(self, gs):
        progressed = True
        while progressed:
            progressed = False
            hand = sorted([c for c in gs.zones.hand if not c.is_land()],
                          key=self._prio)
            for c in hand:
                if c.name in PAYOFFS:
                    continue  # payoff strictly last (max storm count)
                if c.name == RAL and any(x.name == RAL
                                         for x in gs.zones.battlefield):
                    continue  # legend rule
                if (c.name == PAST_IN_FLAMES
                        and gs.spells_cast_this_turn < 3):
                    continue  # flashback unmodeled; only storm-padding value
                if self._cast(gs, c):
                    progressed = True
                    break  # re-sort; a ritual may have unlocked a cast

    def _try_payoff(self, gs, opponent):
        """Grapeshot LAST. copies_if_cast = spells_cast_this_turn + 1
        (storm audit, module docstring #4). Fire when lethal vs the
        opponent's actual life (goldfish: 20 - damage so far), when the
        storm count is big anyway, or as a desperation line late."""
        for c in sorted([x for x in gs.zones.hand if x.name in PAYOFFS],
                        key=lambda x: 0 if x.name == GRAPESHOT else 1):
            if c.name == GRAPESHOT:
                copies_if_cast = gs.spells_cast_this_turn + 1
                if opponent is not None:
                    opp_life = opponent.life
                else:
                    opp_life = max(1, 20 - gs.damage_dealt)
                if not (copies_if_cast >= opp_life
                        or copies_if_cast >= 5
                        or (gs.turn >= 7 and copies_if_cast >= 3)):
                    continue  # hold: a small non-lethal shot wastes the
                    # payoff. No unconditional turn-based free-fire — that
                    # fired storm-0 1-copy Grapeshots on desperation turns;
                    # late chips need >= 3 copies to be worth the card.
            self._cast(gs, c)

    # ── Combat (unchanged from the audited stub) ─────────────────────
    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers:
            return assignments
        blockers = [c for c in gs.zones.battlefield if c.has(Tag.CREATURE)
                    and not c.is_land() and safe_power(c) >= 3
                    and not getattr(c, 'tapped', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def respond_to_spell(self, gs, opponent, spell):
        return None

    def end_step_actions(self, gs, opponent):
        pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = (c.name or '').lower()
            if ('mesa' in n or 'strand' in n or 'delta' in n or 'tarn' in n
                    or 'foothills' in n or 'flats' in n or 'rainforest' in n
                    or 'catacombs' in n or 'heath' in n or 'mire' in n):
                return 0
            if ('foundry' in n or 'vents' in n or 'garden' in n
                    or 'grave' in n or 'shrine' in n or 'fountain' in n
                    or 'crypt' in n):
                return 1
            return 3
        gs.play_land(min(lands, key=score))
