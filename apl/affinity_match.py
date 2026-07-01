"""
apl/affinity_match.py — Oracle-audited Izzet Affinity APL (Modern)

Playbook engines:
A. Pinnacle Emissary Token Flood — creates artifact creature tokens
B. Weapons Manufacturing + Engineered Explosives — sac artifacts for burst damage
C. Urza's Saga + Emry Recursion — Saga constructs + Emry recasts from GY

Key cards: Kappa Cannoneer (ward, grows on artifact ETB), Mox Opal (free mana),
Pinnacle Emissary (token flood), Arcbound Ravager (sac for +1/+1 counters),
Metallic Rebuke (affinity counter), Urza's Saga (constructs + tutor)
"""
import os
from typing import Optional
from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from apl.aware_match_apl import AwareMatchAPL
from engine.match_state import safe_power, safe_toughness

KAPPA      = "Kappa Cannoneer"
PINNACLE   = "Pinnacle Emissary"
WEAPONS    = "Weapons Manufacturing"
EE         = "Engineered Explosives"
MOX_OPAL   = "Mox Opal"
BAUBLE     = "Mishra's Bauble"
EMRY       = "Emry, Lurker of the Loch"
RAVAGER    = "Arcbound Ravager"
REBUKE     = "Metallic Rebuke"
SAGA       = "Urza's Saga"
SHADOWSPEAR= "Shadowspear"
SKATEBOARD = "Skateboard"
THOUGHTCAST= "Thoughtcast"
CONSTRUCT  = "Construct Token"

ARTIFACTS = {MOX_OPAL, BAUBLE, EE, SHADOWSPEAR, SKATEBOARD, WEAPONS,
             "Tormod's Crypt", "Claws of Gix", "Welding Jar", "Aether Spellbomb", "Pithing Needle"}


class IzzetAffinityMatchAPL(AwareMatchAPL):
    name = "Izzet Affinity"
    win_condition_damage = 20
    max_turns = 10

    # R4 opt-in: Pinnacle Emissary has Warp {U/R}. Setting this activates the
    # match_runner end-step warp tick + cast-from-exile aliasing (gate fires if
    # either seat opts in; non-warp matchups stay byte-identical). The cast loop
    # warp-casts Pinnacle cheaply for an early Drone-engine turn, the tick exiles
    # it, and the recast block below replays it for full value on a later turn.
    WANTS_WARP = True

    # arc #3 (2026-07-01): opt into the match_runner:279 mp1-damage propagation so the
    # section-6b Munitions leave-trigger (Weapons Manufacturing) is no longer discarded.
    # Only section-6b writes gs.damage_dealt in this APL, so the gate propagates ONLY
    # faithful Munitions damage; Boros never sets WANTS_BURN so its cells stay byte-identical.
    WANTS_BURN = True

    # R1 opt-in (Stage B 2026-06-27): now extends AwareMatchAPL, so the inherited
    # priority_action / _r1_choose_counter route the 3 Metallic Rebukes through the
    # shipped stack-priority machinery (+ COUNTER_VALIDITY["Metallic Rebuke"]). Flips
    # the fidelity gate counterspell_on_stack low -> high (PROMOTABLE). MRO note: this
    # class's own keep/bottom/main_phase*/declare_attackers/declare_blockers shadow
    # AwareMatchAPL's, so combat + mulligan are UNCHANGED by the re-base.
    WANTS_PRIORITY_STACK = True
    COUNTER_CARDS = {REBUKE}
    COUNTER_COST = int(os.environ.get("AFFINITY_COUNTER_COST", "2"))  # Phase-2 sweep winner (n=300:
                      # 0->42.0 1->42.0 2->42.3 3->41.9; all within noise, no regression vs 41% baseline).
                      # full Rebuke cost is {2}{U}=3 but reserve fires only conditionally (reserve_mana).

    def __init__(self):
        self._artifact_count = 0
        self._kappa_counters = 0
        self._artifacts_cast_this_turn = 0   # for Pinnacle Emissary Drone creation
        self._munitions_pending = 0          # Weapons Manufacturing Munitions tokens

    def _count_artifacts(self, gs):
        """Count artifacts on battlefield for affinity/metalcraft."""
        return sum(1 for c in gs.zones.battlefield
                  if not c.is_land() and 'artifact' in (getattr(c, 'type_line', '') or '').lower())

    # ---------------------------------------------------------------------
    # Urza's Saga chapter/Construct engine (arc #3). APL-LOCAL: all chapter
    # state is attached to the Saga Card object itself (persists across turns
    # because the match view aliases the persistent battlefield list). Keyed off
    # the Saga's turn_entered exactly the way boros_energy_match self-generates
    # its tokens off turn state. Oracle (scryfall_oracle_cards.json):
    #   "(As this Saga enters and after your draw step, add a lore counter.
    #     Sacrifice after III.)"
    #   I   -- "{T}: Add {C}."
    #   II  -- "{2}, {T}: Create a 0/0 colorless Construct artifact creature token
    #           with 'This token gets +1/+1 for each artifact you control.'"
    #   III -- "Search your library for an artifact card with mana cost {0} or {1},
    #           put it onto the battlefield, then shuffle."  (then sac after III)
    # ---------------------------------------------------------------------
    def _advance_saga_chapters(self, gs, on_artifact_enter):
        """Add one lore counter per Saga per MY main phase (turn-guarded so a
        second main-phase call in the same turn does not double-advance). Fire
        chapter III (tutor + sacrifice) the turn a Saga reaches lore 3."""
        for c in list(gs.zones.battlefield):
            if c.name != SAGA:
                continue
            if getattr(c, '_saga_turn_seen', None) == gs.turn:
                continue
            c._saga_turn_seen = gs.turn
            ch = getattr(c, '_saga_chapter', 0) + 1
            c._saga_chapter = ch
            if ch >= 3:
                self._saga_chapter_three(gs, c, on_artifact_enter)

    def _saga_chapter_three(self, gs, saga, on_artifact_enter):
        """III: search library for an MV 0-1 artifact -> battlefield, then sac Saga."""
        def _mv(card):
            return getattr(card, 'cmc', 0) or 0
        # Prefer Mox Opal (mana), then any other MV0-1 artifact.
        candidates = [x for x in gs.zones.library
                      if _mv(x) <= 1
                      and 'artifact' in (getattr(x, 'type_line', '') or '').lower()
                      and not x.is_land()]
        if candidates:
            candidates.sort(key=lambda x: (x.name != MOX_OPAL, _mv(x)))
            tgt = candidates[0]
            gs.zones.library.remove(tgt)
            gs.zones.battlefield.append(tgt)
            tgt.turn_entered = gs.turn
            tgt.tapped = True  # entered this main; no fresh mana this turn
            on_artifact_enter(is_nontoken=True)
            gs._log(f"  Urza's Saga III: tutor {tgt.name} (MV{_mv(tgt)}) -> battlefield")
        # Sacrifice after III.
        if saga in gs.zones.battlefield:
            gs.zones.battlefield.remove(saga)
            gs.zones.graveyard.append(saga)
        gs._log("  Urza's Saga III: sacrificed Saga")

    def _activate_saga_constructs(self, gs, on_artifact_enter):
        """II: for each untapped chapter-II+ Saga, pay {2} and tap it to make a
        0/0 Construct (P/T set from live artifact count; summoning-sick). Honest
        mana only: {2} is an activated-ability cost (NOT affinity/improvise), paid
        from the real pool via ManaPool.pay, and the Saga's own {T} is consumed."""
        made = 0
        for c in list(gs.zones.battlefield):
            if c.name != SAGA:
                continue
            if getattr(c, '_saga_chapter', 0) < 2:
                continue
            # One activation per Saga per turn (needs {T}). Note tap_lands() has
            # already tapped the Saga for mana; the {T} for THIS ability competes
            # with that, which is why the honest >=3 gate below forgoes the Saga's
            # own {C}. Guard on a per-turn-use flag, not the tapped-for-mana state.
            if getattr(c, '_saga_used_turn', None) == gs.turn:
                continue
            # {2},{T}: the Saga is being tapped for the ability (not for mana), so
            # require >=3 in pool -- 1 stands in for the Saga's own {C} we forgo --
            # then pay the {2} generic with no cost_reduction.
            if gs.mana_pool.total() < 3:
                continue
            gs.mana_pool.cost_reduction = 0
            if not gs.mana_pool.pay("{2}", 2):
                continue
            c._saga_used_turn = gs.turn
            c.tapped = True  # {T}
            tok = gs._make_token(CONSTRUCT, "0", "0",
                                 "Artifact Creature - Construct")
            on_artifact_enter(is_nontoken=False)  # a token; no Munitions trigger
            self._recompute_constructs(gs)
            made += 1
            gs._log(f"  Urza's Saga II: {{2}},{{T}} -> 0/0 Construct "
                    f"(now {safe_power(tok)}/{safe_toughness(tok)}, artifacts={self._count_artifacts(gs)})")
        return made

    def _recompute_constructs(self, gs):
        """Construct 'gets +1/+1 for each artifact you control': set P/T to the live
        artifact count (which includes the Construct itself, an artifact creature).
        A Construct reduced to 0/0 (no artifacts) dies as a state-based action."""
        n = self._count_artifacts(gs)
        dead = []
        for c in list(gs.zones.battlefield):
            if c.name == CONSTRUCT:
                c.power = str(n)
                c.toughness = str(n)
                if n <= 0:
                    dead.append(c)
        for c in dead:
            gs.zones.battlefield.remove(c)
            gs.zones.graveyard.append(c)

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        artifacts = sum(1 for c in hand if c.name in ARTIFACTS or c.name == MOX_OPAL)
        threats = sum(1 for c in hand if c.name in (KAPPA, PINNACLE, EMRY, RAVAGER))
        has_opal = any(c.name == MOX_OPAL for c in hand)
        
        if lands == 0 and not has_opal: return False
        if artifacts >= 2 and threats >= 1: return True
        if has_opal and threats >= 1 and lands >= 1: return True
        if threats >= 2 and lands >= 1: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[3:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()
        self._artifact_count = self._count_artifacts(gs)
        self._artifacts_cast_this_turn = 0
        avail = gs.mana_pool.total()

        # R4: recast a warp-exiled Pinnacle from exile for FULL value on a LATER
        # turn (permanent Drone engine). WANTS_WARP gates this; match_runner aliases
        # gs.zones.exile to this player's persistent exile list. cast_spell_from_warp_exile
        # pays the full {1}{U}{R} through cast_spell and clears the markers so it can't loop.
        if getattr(self, "WANTS_WARP", False):
            for c in list(getattr(gs.zones, "exile", [])):
                if (getattr(c, "_warp_recastable", False)
                        and gs.turn > getattr(c, "_warp_exiled_turn", gs.turn)
                        and gs.mana_pool.can_cast(c.mana_cost, c.cmc)):
                    if gs.cast_spell_from_warp_exile(c):
                        gs._log(f"  R4 recast {c.name} from warp exile (full value)")
            avail = gs.mana_pool.total()

        pinnacle_on_board = any(c.name == PINNACLE for c in gs.zones.battlefield)
        weapons_on_board = any(c.name == WEAPONS for c in gs.zones.battlefield)

        def _on_artifact_enter(is_nontoken=True):
            """Fire ETB triggers when an artifact enters the battlefield."""
            self._artifact_count += 1
            self._kappa_counters += 1  # Kappa gets +1/+1 per artifact ETB
            if weapons_on_board and is_nontoken:
                self._munitions_pending += 1  # Munitions token created

        def _on_artifact_cast():
            """Fire cast triggers when an artifact spell is cast."""
            self._artifacts_cast_this_turn += 1

        # Urza's Saga lore: add a counter per main phase; chapter III (tutor + sac)
        # is a free triggered ability that fires at the start of the main phase.
        self._advance_saga_chapters(gs, _on_artifact_enter)

        # 0. Mox Opal — deploy; its metalcraft {C} is tapped AFTER cheap artifacts
        # land (section 1) so metalcraft can actually be online. Real Mox mana now
        # goes into gs.mana_pool (not just the local `avail`) so the gs.mana_pool-gated
        # spells (Emry/Kappa) and the {2},{T} Saga construct can honestly use it.
        for c in list(gs.zones.hand):
            if c.name == MOX_OPAL:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                _on_artifact_enter(is_nontoken=True)
                gs._log(f"  Mox Opal deployed (artifacts: {self._artifact_count})")
                break

        # 1. Deploy cheap artifacts (free, ETB triggers Kappa + Weapons Manufacturing)
        for c in list(gs.zones.hand):
            if c.name in ARTIFACTS and getattr(c, 'cmc', 0) == 0:
                gs.zones.hand.remove(c); gs.zones.battlefield.append(c)
                c.turn_entered = gs.turn
                _on_artifact_enter(is_nontoken=True)
                _on_artifact_cast()
                gs._log(f"  Deploy {c.name} (artifact #{self._artifact_count})")

        # 1b. Tap Mox Opal for {C} (metalcraft: 3+ artifacts) — evaluated here, after
        # the cheap artifacts have entered, since metalcraft is usually only online
        # once they're down. Honest real mana into gs.mana_pool, one {C} per Mox, once.
        if self._count_artifacts(gs) >= 3:
            for c in gs.zones.battlefield:
                if c.name == MOX_OPAL and getattr(c, '_mox_mana_turn', None) != gs.turn:
                    gs.mana_pool.add("C", 1)
                    c._mox_mana_turn = gs.turn
            avail = gs.mana_pool.total()

        # 2. Weapons Manufacturing ({2}) — creates Munitions tokens on each artifact entering
        # Oracle: "Whenever a nontoken artifact you control enters, create a Munitions token
        # (an artifact token with 'When this token leaves the battlefield, it deals 2 damage')."
        for c in list(gs.zones.hand):
            if c.name == WEAPONS and avail >= 2:
                gs.cast_spell(c); _on_artifact_enter(); _on_artifact_cast()
                avail = gs.mana_pool.total()
                gs._log(f"  Weapons Manufacturing: each artifact entering now creates Munitions (+2 dmg on sac)")
                break

        # 2b. Urza's Saga II — {2},{T} makes a Construct (sized to live artifact count,
        # recomputed each main phase). Activated here, after the free/cheap artifacts and
        # BEFORE the {2}{U}+ mana sinks (Emry/Kappa/Pinnacle), because the {2} board-builder
        # otherwise never gets mana on the tight chapter-II turn. P/T is re-set at end of main.
        self._activate_saga_constructs(gs, _on_artifact_enter)
        avail = gs.mana_pool.total()

        # 3. Emry ({2}{U} with affinity for artifacts) — cast artifacts from GY
        # Oracle (ETB): "When Emry enters, mill four cards." — puts 4 cards from library to GY
        for c in list(gs.zones.hand):
            if c.name == EMRY:
                gs.mana_pool.cost_reduction = self._artifact_count
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    _on_artifact_enter()
                    # Oracle ETB: mill 4 cards (library -> GY, fills GY for delirium)
                    for _ in range(min(4, len(gs.zones.library))):
                        card = gs.zones.library.pop(0)
                        gs.zones.graveyard.append(card)
                    gs._log(f"  Emry ETB: affinity, mill 4 -> GY ({len(gs.zones.graveyard)} in GY)")
                gs.mana_pool.cost_reduction = 0
                avail = gs.mana_pool.total()
                break

        # 4. Kappa Cannoneer ({5}{U}, ward {4}) — grows on artifact ETB, improvise
        for c in list(gs.zones.hand):
            if c.name == KAPPA:
                gs.mana_pool.cost_reduction = self._artifact_count
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    _on_artifact_enter()
                    c.power = str(4 + self._kappa_counters)
                    c.toughness = str(4 + self._kappa_counters)
                    gs._log(f"  Kappa: {safe_power(c)}/{safe_toughness(c)} (affinity -{self._artifact_count}, ward 4)")
                gs.mana_pool.cost_reduction = 0
                avail = gs.mana_pool.total()
                break

        # 5. Pinnacle Emissary ({3}{U}{R}) — creates 1/1 Drone flying tokens on each artifact cast.
        # Oracle: "Whenever you cast an artifact spell, create a 1/1 colorless Drone artifact
        # creature token with flying." Drone tokens ALSO trigger Kappa + Weapons Manufacturing.
        for c in list(gs.zones.hand):
            if c.name == PINNACLE:
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    avail = gs.mana_pool.total()
                    break
                # R4 warp fallback: can't afford full {1}{U}{R} but can afford {U/R}.
                # Deploy Pinnacle for one turn of the Drone engine; the end-step tick
                # exiles it; the recast block above replays it full-value next turn.
                if getattr(self, "WANTS_WARP", False) and gs.mana_pool.can_cast("{U/R}", 1):
                    if gs.cast_spell_warp(c):
                        gs._log(f"  R4 warp-cast Pinnacle Emissary ({{U/R}}, exiles next end step)")
                        avail = gs.mana_pool.total()
                        break
        # Create Drones for all artifact casts so far this turn (if Pinnacle now on board
        # or was already on board). Post-cast is conservative; ideally fires per-cast.
        pinnacle_on_board = any(c.name == PINNACLE for c in gs.zones.battlefield)
        if pinnacle_on_board and self._artifacts_cast_this_turn > 0:
            for _ in range(self._artifacts_cast_this_turn):
                gs._make_token("Drone Token", "1", "1",
                               "Artifact Creature — Drone")
                _on_artifact_enter(is_nontoken=False)  # tokens don't trigger Weapons Mfg
            gs._log(f"  Pinnacle: {self._artifacts_cast_this_turn} Drone token(s) (flying, artifact)")

        # 6. Arcbound Ravager ({2}) — sacrifice artifacts for counters
        # Oracle: "Sacrifice an artifact: Put a +1/+1 counter on this creature.
        #          Modular 1 (enters with 1 +1/+1 counter)."
        for c in list(gs.zones.hand):
            if c.name == RAVAGER and avail >= 2:
                gs.cast_spell(c); _on_artifact_enter(); _on_artifact_cast()
                c.power = '1'; c.toughness = '1'
                # Modular 1: enters with 1 +1/+1 counter
                counters = 1
                # Activate sac ability: sacrifice expendable artifacts (tokens, Baubles, etc.)
                sac_fodder = [x for x in gs.zones.battlefield
                              if x.has(Tag.ARTIFACT) and x != c
                              and x.name not in (KAPPA, PINNACLE, EMRY, RAVAGER)
                              and not x.has(Tag.CREATURE)]
                for sac in sac_fodder[:4]:  # sac up to 4 artifacts
                    gs.zones.battlefield.remove(sac)
                    gs.zones.graveyard.append(sac)
                    counters += 1
                c.power = str(counters); c.toughness = str(counters)
                avail = gs.mana_pool.total()
                gs._log(f"  Ravager: {counters} counters (modular 1 + {counters-1} sac)")
                break

        # 6b. Weapons Manufacturing Munitions — a Munitions token deals 2 damage WHEN
        # IT LEAVES the battlefield (oracle). Faithful crack-for-reach: only sacrifice
        # the pending Munitions when we are the beatdown (a real closing decision), not
        # a free blanket dump every turn. WANTS_BURN=True lets match_runner:279 sync it.
        if self._munitions_pending > 0 and self._affinity_is_beatdown(gs):
            dmg = self._munitions_pending * 2
            gs.damage_dealt += dmg
            gs._log(f"  Weapons Mfg Munitions: sac {self._munitions_pending} tokens (leave) -> {dmg} face")
            self._munitions_pending = 0

        # 7. Removal with Metallic Rebuke (handled in respond_to_spell)

        # 7b. Thoughtcast — Affinity for artifacts; "Draw two cards." Placed BEFORE the
        # section-8 Tag.CREATURE fill-curve gate (an instant can never satisfy it, so it
        # would otherwise strand). Affinity reduces the {3} generic by artifact count.
        for c in list(gs.zones.hand):
            if c.name == THOUGHTCAST:
                gs.mana_pool.cost_reduction = self._count_artifacts(gs)
                if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    drawn = 0
                    for _ in range(2):
                        if gs.zones.library:
                            gs.zones.hand.append(gs.zones.library.pop(0))
                            drawn += 1
                    gs._log(f"  Thoughtcast: affinity -{self._count_artifacts(gs)}, draw {drawn}")
                gs.mana_pool.cost_reduction = 0
                avail = gs.mana_pool.total()
                break

        # 8. Fill curve
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)

        # Final: recompute every Construct's P/T from the live artifact count so combat
        # (and next turn) sees the current size. Dynamic, not frozen at creation.
        self._recompute_constructs(gs)

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        """Block with largest creatures. Kappa (ward 4) and Ravager soak hits."""
        if not attackers:
            return {}
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and not getattr(c, 'tapped', False)
                    and not getattr(c, 'summoning_sickness', False)]
        if not blockers:
            return {}
        assignments = {}
        blockers_sorted = sorted(blockers, key=lambda c: -safe_toughness(c))
        attackers_sorted = sorted(attackers, key=lambda c: -safe_power(c))
        for atk, blk in zip(attackers_sorted, blockers_sorted):
            assignments[id(atk)] = [blk]
        return assignments

    # ---- Stage B: keep the AwareMatchAPL re-base blast radius minimal ----------
    # The inherited combat-instant hooks would newly fire on defense (tapping our
    # lands for a scan that finds nothing castable -- affinity has no MATCH_REMOVAL).
    # No-op them so only the intended R1 counters + reserve_mana change behavior.
    def pre_combat_instant(self, gs, opponent):
        pass

    def post_attackers_instant(self, gs, opponent, attackers):
        pass

    def _affinity_is_beatdown(self, gs):
        """Local beatdown check. Do NOT reuse AwareMatchAPL._i_am_beatdown -- it reads
        match-dmg attrs this APL's overridden main path may not populate."""
        attackers = sum(1 for c in gs.zones.battlefield
                        if c.has(Tag.CREATURE) and not c.is_land()
                        and not getattr(c, "summoning_sickness", False))
        return attackers >= 2 or getattr(gs, "damage_dealt", 0) >= 10

    def reserve_mana(self, gs, opponent):
        """Hold up Metallic Rebuke ONLY when we have one AND aren't the beatdown, so the
        tempo tax doesn't tank the aggro clock. COUNTER_COST swept in Phase 2."""
        has_rebuke = any(c.name == REBUKE for c in gs.zones.hand)
        if has_rebuke and self.COUNTER_COST > 0 and not self._affinity_is_beatdown(gs):
            gs.mana_reserve = self.COUNTER_COST
        else:
            gs.mana_reserve = 0

    def respond_to_spell(self, gs, opponent, spell):
        """Metallic Rebuke — affinity counter ({2}{U} - artifacts)."""
        if not spell: return None
        rebuke_cost = max(1, 3 - self._count_artifacts(gs))
        for c in list(gs.zones.hand):
            if c.name == REBUKE and gs.mana_pool.total() >= rebuke_cost:
                gs.zones.hand.remove(c); gs.zones.graveyard.append(c)
                gs._log(f"  Metallic Rebuke: counter {spell.name} (cost {rebuke_cost})")
                return c
        return None

    def end_step_actions(self, gs, opponent): pass

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if 'saga' in n: return 0  # Urza's Saga is priority
            if 'islet' in n or 'canal' in n: return 1
            return 3
        gs.play_land(min(lands, key=score))
