"""
apl/goryos_reanimator_match.py — Goryo's Reanimator (Modern, June-2026
"Instant Reanimator" shell). Consolidates and supersedes BOTH flawed cells:

  * apl/goryos_match.py (GoryosMatchAPL)  — flagged INFLATED (sim 84-92 vs ~73):
    the reanimated body was NEVER exiled (Goryo's delayed trigger unmodeled) and
    Atraxa's ETB was a flat draw-4 fired twice per blink. Both fixed here.
  * apl/grixis_reanimator_match.py (GrixisReanimatorMatchAPL) — flagged INVERTED,
    fed by a 66-card audit:stub list. The June-2026 DB has only 2 Grixis decks
    vs 41 Instant Reanimator; the real archetype is this Esper shell.

Deck: decks/goryos_reanimator_modern.txt (real modal 60+15, 5 first-place
June-2026 finishes; see deck header for attribution).

PROACTIVE combo-beatdown deck. Plan A: bin Atraxa/Griselbrand (Fallaji mill /
Otherworldly Gaze / Faithful Mending / Psychic Frog discard), Goryo's Vengeance
it back with haste, keep it permanently with a post-combat Ephemerate. Plan B:
Psychic Frog + Fallaji + Solitude beatdown with Frog growing off excess cards.

ENGINE BOUNDARIES (honest, documented — not tuned):
  * Casting window: Goryo's Vengeance is an instant, but this APL keeps to the
    sanctioned sorcery-speed main-phase-1 window the old GoryosMatchAPL used
    (run_match has no own-turn instant window for the active player).
  * The engine handler _goryos_vengeance_spell (fires inside gs.cast_spell)
    reanimates the max-cmc legendary with haste + on_etb, but does NOT schedule
    the "exile at the beginning of the next end step" delayed trigger, and
    _run_end_step only calls the REACTIVE player's end_step_actions. This APL
    therefore owns the trigger itself: the body attacks via _resolve_combat,
    then is exiled at the end of main_phase2_match (post-combat) unless saved
    by Ephemerate. On the goldfish path (engine/runner.py never calls
    main_phase2) the save-or-exile resolves at the start of the NEXT main
    phase, before the body could ever attack twice.
  * _run_post_combat_phase re-grants a FULL mana pool in main phase 2; this APL
    carries its own MP1-leftover budget (self._mp2_budget) so the post-combat
    Ephemerate is only cast off mana that was genuinely left untapped.
  * NO FAKE REACTIVITY: Force of Negation / Consign to Memory / Mystical
    Dispute / March of Otherworldly Light are modeled INERT (respond_to_spell
    returns None). Psychic Frog's combat-damage draw is unmodeled (engine has
    no on-damage hook); its discard outlet IS modeled (+1/+1 via card.counters,
    the same convention the Fallaji engine handler uses).
  * Opponent interaction with the reanimated body goes through the shared
    combo_interaction layer (double-gated offer, same pattern as the grixis
    cell) — a no-op unless the opponent sets WANTS_COMBO_INTERACTION.
"""
from data.card import Tag
from apl.match_apl import MatchAPL
from engine.match_state import safe_power

ATRAXA      = "Atraxa, Grand Unifier"
GRISELBRAND = "Griselbrand"
GORYOS      = "Goryo's Vengeance"
EPHEMERATE  = "Ephemerate"
FROG        = "Psychic Frog"
FALLAJI     = "Fallaji Archaeologist"
MENDING     = "Faithful Mending"
GAZE        = "Otherworldly Gaze"
SOLITUDE    = "Solitude"
THOUGHTSEIZE = "Thoughtseize"
PRISMATIC   = "Prismatic Ending"

FATTIES  = {ATRAXA, GRISELBRAND}          # legendary Goryo's targets
OUTLETS  = {FROG, MENDING}                # discard a hand fatty into the GY
ENABLERS = {FALLAJI, GAZE, MENDING}       # dig fatties from library into the GY
INERT    = {"Force of Negation", "Consign to Memory", "Mystical Dispute",
            "March of Otherworldly Light"}  # proactive deck: no fake reactivity


def _fatty_in_gy(gs):
    return any(c.name in FATTIES for c in gs.zones.graveyard)


class GoryosReanimatorMatchAPL(MatchAPL):
    name = "Goryos Reanimator"
    win_condition_damage = 20
    max_turns = 12

    def __init__(self):
        # (body, turn) for Goryo's-reanimated creatures whose delayed exile
        # trigger this APL owns (engine handler does not schedule it).
        self._pending_exile = []
        self._eph_rebound_turn = None   # Ephemerate rebound: free flicker next turn
        self._mp2_budget = 0            # honest post-combat mana (MP1 leftover)

    # ── Mulligan keep tiers (enabler + payoff + lands) ───────────────────
    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4:
            return True
        lands = sum(1 for c in hand if c.is_land())
        if lands == 0 or lands >= 6:
            return mulligans >= 2
        has_goryos = any(c.name == GORYOS for c in hand)
        has_fatty  = any(c.name in FATTIES for c in hand)
        outlets    = sum(1 for c in hand if c.name in OUTLETS)
        enablers   = sum(1 for c in hand if c.name in (ENABLERS | OUTLETS))
        bodies     = sum(1 for c in hand if c.name in (FROG, FALLAJI, SOLITUDE))
        # T1 snap: full combo — Goryo's + fatty + a discard outlet + 2 lands
        if has_goryos and has_fatty and outlets and lands >= 2:
            return True
        # T2: Goryo's + GY enabler + 2-5 lands (Fallaji/Gaze/Mending finds a fatty)
        if has_goryos and enablers and 2 <= lands <= 5:
            return True
        # T3: fatty + outlet + 2+ lands (bin it now, 4 Goryo's + dig to find one)
        if has_fatty and outlets and lands >= 2:
            return True
        # T4 fair keep: 2+ bodies/enablers + 2-4 lands (Frog beatdown fallback)
        if bodies + enablers >= 2 and 2 <= lands <= 4:
            return True
        return mulligans >= 2

    def bottom(self, hand, n):
        """Bottom excess lands, then highest-cmc spells; protect ONE fatty when
        the kept hand has a plan for it (Goryo's or a discard outlet)."""
        lands  = [c for c in hand if c.is_land()]
        spells = [c for c in hand if not c.is_land()]
        protected = []
        if any(c.name == GORYOS or c.name in OUTLETS for c in spells):
            f = next((c for c in spells if c.name in FATTIES), None)
            if f is not None:
                protected.append(f)
        rest = sorted([c for c in spells if c not in protected],
                      key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + rest + protected + lands[:3])[:n]

    # ── Main phases ──────────────────────────────────────────────────────
    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        # Stash the opponent view like the base class does: engine spell/ETB
        # handlers (Thoughtseize / Prismatic Ending / Solitude) read
        # gs._match_opp and silently NO-OP without it, and the base-class
        # honest combat hooks consult self._opp_gs.
        self._opp_gs = opponent
        if opponent is not None:
            gs._match_opp = opponent
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 0. Own the Goryo's delayed exile from LAST turn (goldfish path only:
        #    engine/runner.py never calls main_phase2, so save-or-exile lands
        #    here — the body attacked once with haste and never attacks twice).
        self._settle_stale_pending(gs)

        # 0b. Ephemerate rebound: recast from exile for free (oracle: rebound).
        if self._eph_rebound_turn == gs.turn:
            self._eph_rebound_turn = None
            self._rebound_flicker(gs)

        # 1. Free Psychic Frog discard outlet: pitch a hand fatty for Goryo's
        #    (oracle: "Discard a card: put a +1/+1 counter on this creature.")
        frog = next((c for c in gs.zones.battlefield if c.name == FROG), None)
        if frog is not None:
            hand_fatties = [c for c in gs.zones.hand if c.name in FATTIES]
            # Pitch a fatty when none is reachable in the GY yet.
            if hand_fatties and not _fatty_in_gy(gs):
                t = hand_fatties[0]
                gs.zones.hand.remove(t)
                gs.zones.graveyard.append(t)
                frog.counters = (frog.counters or 0) + 1
                gs._log(f"  Psychic Frog: discard {t.name} (+1/+1) — Goryo's setup")
            else:
                # Grow the Frog off genuinely excess lands (4th+).
                lands_in_hand = [c for c in gs.zones.hand if c.is_land()]
                if len(lands_in_hand) > 3:
                    t = lands_in_hand[-1]
                    gs.zones.hand.remove(t)
                    gs.zones.graveyard.append(t)
                    frog.counters = (frog.counters or 0) + 1
                    gs._log("  Psychic Frog: discard excess land (+1/+1)")

        # 2. Faithful Mending ({W}{U}) — APL-driven cast: the engine handler
        #    discards lands-first (generic), which never pitches the fatty. Same
        #    sanctioned pattern as the grixis cell's Faithless Looting: manual
        #    zone moves + oracle-faithful choices ("gain 2, draw 2, discard 2").
        if not _fatty_in_gy(gs):
            for c in list(gs.zones.hand):
                if c.name == MENDING and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.mana_pool.pay(c.mana_cost, c.cmc)
                    gs.zones.hand.remove(c)
                    gs.zones.graveyard.append(c)
                    gs.life += 2
                    gs.zones.draw(2)
                    for _ in range(2):
                        if not gs.zones.hand:
                            break
                        fat = [x for x in gs.zones.hand if x.name in FATTIES]
                        lands = [x for x in gs.zones.hand if x.is_land()]
                        if fat:
                            d = fat[0]              # pitch the fatty -> Goryo's it
                        elif len(lands) > 3:
                            d = lands[-1]           # excess land
                        else:
                            d = max(gs.zones.hand, key=lambda x: getattr(x, 'cmc', 0))
                        gs.zones.hand.remove(d)
                        gs.zones.graveyard.append(d)
                    gs._log("  Faithful Mending: +2 life, draw 2, discard 2 (pitch fatty)")
                    break

        # 3. THE COMBO — Goryo's Vengeance ({1}{B}). Engine SPELL_EFFECTS
        #    handler reanimates the max-cmc legendary in our GY with haste and
        #    fires on_etb (Atraxa: reveal-10-grab-by-type; Griselbrand: pay 7
        #    draw 7 when life > 10). We snapshot the battlefield by identity to
        #    find the body the engine ACTUALLY landed (grixis-cell lesson: never
        #    guess + never re-move the card), offer the honest interaction
        #    window, then take ownership of the delayed exile trigger.
        #    Chaining is a real line (Griselbrand draw-7 into a 2nd Goryo's on
        #    Atraxa), so this loops while targets + mana + copies allow.
        for c in list(gs.zones.hand):
            if not _fatty_in_gy(gs):
                break
            if c.name == GORYOS and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                before = {id(x) for x in gs.zones.battlefield}
                gs.cast_spell(c)
                new_bodies = [x for x in gs.zones.battlefield
                              if id(x) not in before and x.has(Tag.CREATURE)]
                for body in new_bodies:
                    gs._log(f"  GORYO'S VENGEANCE: reanimate {body.name} "
                            f"(haste; exile EOT unless Ephemerate)")
                    if self._offer_threat(gs, opponent, body):
                        continue    # answered — zone move already applied
                    if not any(x is body for x in gs.zones.battlefield):
                        continue
                    # MATCH mode: run_match_set never calls main_phase2, so the
                    # post-combat save window does not exist on the production
                    # gauntlet path. The real alternative line — Ephemerate the
                    # body IMMEDIATELY (permanence, giving up this turn's haste
                    # hit; it re-enters summoning-sick) — is taken here inside
                    # the sanctioned MP1 window. Goldfish keeps the haste hit
                    # and saves via _settle_stale_pending instead.
                    if opponent is not None:
                        eph = next((x for x in gs.zones.hand
                                    if x.name == EPHEMERATE), None)
                        if eph is not None and gs.mana_pool.can_cast(eph.mana_cost, 1):
                            gs.cast_spell(eph)   # engine flickers max-cmc = body
                            self._eph_rebound_turn = gs.turn + 1
                            gs._log("  Ephemerate (MP1): body kept permanently "
                                    "(no haste hit this turn)")
                            continue             # kept — no delayed exile
                    self._pending_exile.append((body, gs.turn))

        # 4. Fallaji Archaeologist ({1}{U}) — engine ETB mills 3 and may
        #    recover a noncreature/nonland (Goryo's/Ephemerate) from the mill.
        for c in list(gs.zones.hand):
            if c.name == FALLAJI and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 5. Psychic Frog ({U}{B}) — clock + discard outlet for later turns.
        for c in list(gs.zones.hand):
            if c.name == FROG and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 6. Otherworldly Gaze ({U}) — engine proxy: surveil 3 as mill 2 draw 1.
        #    Cast while a fatty is still missing from the GY (dig), or T1 filter.
        if not _fatty_in_gy(gs) or gs.turn <= 2:
            for c in list(gs.zones.hand):
                if c.name == GAZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    break

        # 7. Thoughtseize ({B}) — engine handler strips the opponent's max-cmc
        #    nonland + we lose 2 life. Early turns only (proactive discard).
        if opponent is not None and gs.turn <= 3:
            for c in list(gs.zones.hand):
                if c.name == THOUGHTSEIZE and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    if getattr(opponent.zones, 'hand', None):
                        gs.cast_spell(c)
                    break

        # 8. Solitude EVOKE — free exile on a real threat (oracle: pitch a
        #    white card; ETB exile, controller gains life = power; evoke body
        #    dies at end of turn — modeled as straight to GY like the old cell).
        if opponent is not None:
            opp_threats = [x for x in opponent.zones.battlefield
                           if not x.is_land() and x.has(Tag.CREATURE)
                           and safe_power(x) >= 3]
            if opp_threats:
                sol = next((c for c in gs.zones.hand if c.name == SOLITUDE), None)
                if sol is not None:
                    # Pitch priority: never Ephemerate/Atraxa; prefer the
                    # cheap white spells or a 2nd Solitude.
                    pitchable = [x for x in gs.zones.hand
                                 if x is not sol and not x.is_land()
                                 and 'W' in (getattr(x, 'colors', []) or [])
                                 and x.name not in (EPHEMERATE, ATRAXA)]
                    if pitchable:
                        pitch = min(pitchable, key=lambda x: getattr(x, 'cmc', 0))
                        gs.zones.hand.remove(pitch)
                        gs.zones.exile.append(pitch)
                        gs.zones.hand.remove(sol)
                        t = max(opp_threats, key=lambda x: safe_power(x))
                        if t in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(t)
                            opponent.zones.exile.append(t)
                            opponent.life += safe_power(t)  # oracle lifegain
                        gs.zones.graveyard.append(sol)      # evoke sac (EOT)
                        gs._log(f"  Solitude EVOKE: exile {t.name} "
                                f"(pitch {pitch.name}; body dies EOT)")

        # 9. Prismatic Ending — engine handler exiles opp's best cmc<=3 nonland.
        if opponent is not None:
            opp_small = [x for x in opponent.zones.battlefield
                         if not x.is_land() and getattr(x, 'cmc', 99) <= 3]
            if opp_small:
                for c in list(gs.zones.hand):
                    if c.name == PRISMATIC and gs.mana_pool.can_cast(c.mana_cost, 2):
                        gs.cast_spell(c)
                        break

        # 10. Hard-cast a fatty late (Atraxa 7 / Griselbrand 8) — real line,
        #     body STAYS (no Goryo's exile); engine fires the ETB.
        for c in list(gs.zones.hand):
            if c.name in FATTIES and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                break

        # 11. Fill curve: leftover cheap bodies (2nd Fallaji/Frog this turn).
        for c in list(gs.zones.hand):
            if (c.name in (FALLAJI, FROG)
                    and gs.mana_pool.can_cast(c.mana_cost, c.cmc)):
                gs.cast_spell(c)

        # Honest MP2 budget = mana genuinely left untapped after MP1
        # (_run_post_combat_phase re-grants a full pool; we do not use it).
        self._mp2_budget = gs.mana_pool.total()

    # ── Post-combat main (match path): Ephemerate save, then honest exile ──
    def main_phase2(self, gs):
        self.main_phase2_match(gs, None)

    def main_phase2_match(self, gs, opponent):
        """The real pilot's line: reanimate in MP1, attack with haste, then
        Ephemerate AFTER combat so the body is kept permanently (it re-enters
        as a new object; Goryo's delayed exile no longer applies). The engine
        _ephemerate_spell flickers our max-cmc creature and re-fires its ETB
        (oracle-faithful re-trigger). Any body not saved is exiled HERE — this
        is the delayed trigger the old cell dropped (its INFLATED root)."""
        budget = min(self._mp2_budget, gs.mana_pool.total())
        fatty_on_bf = any(x.name in FATTIES for x in gs.zones.battlefield)
        if fatty_on_bf and budget >= 1:
            eph = next((c for c in gs.zones.hand if c.name == EPHEMERATE), None)
            if eph is not None and gs.mana_pool.can_cast(eph.mana_cost, 1):
                saved = self._flicker_target(gs)   # mirror engine's choice
                gs.cast_spell(eph)   # engine: flicker max-cmc creature + re-ETB
                self._eph_rebound_turn = gs.turn + 1
                self._mp2_budget = budget - 1
                # The flickered body re-enters as a NEW game object: Goryo's
                # delayed exile no longer applies to it.
                self._pending_exile = [(b, t) for (b, t) in self._pending_exile
                                       if b is not saved]
                gs._log("  Ephemerate (post-combat): fatty kept permanently "
                        "(rebound next upkeep)")
        # Delayed trigger: exile this turn's unsaved Goryo's bodies.
        self._exile_pending(gs, upto_turn=gs.turn)

    def _settle_stale_pending(self, gs):
        """Goldfish-path fallback (no main_phase2 hook): before anything else
        on the NEXT turn, try the Ephemerate save, then exile leftovers. The
        body attacked once with haste last turn and never attacks again."""
        stale = [(b, t) for (b, t) in self._pending_exile if t < gs.turn]
        if not stale:
            return
        eph = next((c for c in gs.zones.hand if c.name == EPHEMERATE), None)
        if eph is not None and gs.mana_pool.can_cast(eph.mana_cost, 1):
            saved = self._flicker_target(gs)       # mirror engine's choice
            gs.cast_spell(eph)   # flickers the fatty -> new object, stays
            self._eph_rebound_turn = gs.turn + 1
            self._pending_exile = [(b, t) for (b, t) in self._pending_exile
                                   if b is not saved]
            gs._log("  Ephemerate (end-step save, goldfish path): fatty kept")
        self._exile_pending(gs, upto_turn=gs.turn - 1)

    def _exile_pending(self, gs, upto_turn):
        remaining = []
        for body, turn in self._pending_exile:
            if turn > upto_turn:
                remaining.append((body, turn))
                continue
            for i, x in enumerate(gs.zones.battlefield):
                if x is body:
                    gs.zones.exile.append(gs.zones.battlefield.pop(i))
                    gs._log(f"  Goryo's delayed trigger: exile {body.name}")
                    break
        self._pending_exile = remaining

    # ── Helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _flicker_target(gs):
        """Mirror engine _ephemerate_spell target choice (max-cmc creature) so
        we know which object was saved — never re-move it (grixis lesson)."""
        my_cr = [c for c in gs.zones.battlefield
                 if not c.is_land() and c.has(Tag.CREATURE)]
        return max(my_cr, key=lambda c: getattr(c, 'cmc', 0)) if my_cr else None

    def _rebound_flicker(self, gs):
        """Ephemerate rebound (oracle): recast from exile for free at upkeep.
        Manual flicker mirroring engine semantics + on_etb re-fire."""
        target = self._flicker_target(gs)
        if target is None:
            return
        for i, x in enumerate(gs.zones.battlefield):
            if x is target:
                gs.zones.battlefield.pop(i)
                break
        gs.zones.battlefield.append(target)
        target.turn_entered = gs.turn
        target.summoning_sickness = True
        try:
            from engine.card_effects import on_etb
            on_etb(gs, target)
        except Exception:
            pass
        gs._log(f"  Ephemerate rebound: flicker {target.name} (free, re-ETB)")

    def _offer_threat(self, gs, opponent, body):
        """Honest interaction window on the reanimated body via the shared
        combo_interaction layer (double-gated; no-op unless the opponent set
        WANTS_COMBO_INTERACTION). Same pattern as the grixis cell."""
        if opponent is None:
            return False
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

    # ── Combat / reactivity ──────────────────────────────────────────────
    # declare_attackers / declare_blockers intentionally NOT overridden: the
    # base MatchAPL race-aware attacks + optimal_blocking are the honest model
    # here (Atraxa blocking with deathtouch/lifelink/vigilance is a real part
    # of this deck's fair games — the old GoryosMatchAPL returned {} blockers
    # and never blocked, an inherited flaw this cell fixes).

    def respond_to_spell(self, gs, opponent, spell):
        return None   # proactive deck: FoN/Consign/Dispute modeled INERT

    def end_step_actions(self, gs, opponent):
        pass          # reactive-player hook; our exile discipline is in MP2

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played:
            return
        def score(c):
            n = (c.name or '').lower()
            if 'delta' in n or 'strand' in n or 'flats' in n:
                return 0   # fetches first (thin + fix)
            if ('grave' in n or 'shrine' in n or 'fountain' in n
                    or 'pool' in n):
                return 1   # untapped duals
            if 'archive' in n or 'backstreet' in n or 'sewers' in n:
                return 2   # tapped surveil duals
            return 3
        gs.play_land(min(lands, key=score))
