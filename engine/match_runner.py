"""
engine/match_runner.py — Both-sides simulation framework

Runs two APLs against each other in a real game, not a goldfish race.
Both players draw cards, play lands, cast creatures, attack and block.

This is what enables real matchup data — both decks executing their
actual game plan simultaneously, with real combat and interaction.

Architecture:
  - Player A (us): runs our APL as normal
  - Player B (opponent): runs their APL (GenericAPL, AutoAPL, or hand-tuned)
  - Each turn: both players take actions in phase order
  - Combat: Player A attacks → Player B blocks (or vice versa)
  - Win condition: deal 20 damage to opponent, or opponent has 0 life

The result feeds into the meta-analyzer DB as real matchup data.

Usage:
    from engine.match_runner import run_match, run_match_set
    result = run_match(our_apl, our_deck, their_apl, their_deck, on_play=True)
    results = run_match_set(our_apl, our_deck, their_apl, their_deck, n=1000)
"""

from __future__ import annotations
import random
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional
from copy import deepcopy

from engine.game_state import GameState, Phase
from engine.zones import Zones
from engine.mana import ManaPool
from data.card import Card, Tag
from engine.match_state import MatchSetResults


@dataclass
class MatchResult:
    won:           bool  = False
    kill_turn:     int   = 0
    loser_life:    int   = 20
    winner_damage: int   = 0
    mulligans_a:   int   = 0
    mulligans_b:   int   = 0
    turn_count:    int   = 0
    snapshots_a:   list  = field(default_factory=list)


class TwoPlayerGameState:
    """
    Minimal game state for both-sides simulation.
    Each player has their own hand, battlefield, graveyard, mana.
    """
    def __init__(self, deck_a: list, deck_b: list,
                 on_play: bool = True, seed: int = None):
        self.rng = random.Random(seed)
        self.turn     = 0
        self.on_play  = on_play   # True = player A is on the play

        # Player A state
        self.hand_a   = []
        self.bf_a     = []   # battlefield
        self.gy_a     = []   # graveyard
        self.life_a   = 20
        self.mana_a   = 0
        self.land_played_a = False
        self.damage_to_b = 0   # damage A has dealt to B
        self.noncreature_spells_a = 0  # noncreature spells cast this turn by A
        self.spells_cast_a = 0  # total spells cast this turn by A (High Noon lock)

        # Player B state
        self.hand_b   = []
        self.bf_b     = []
        self.gy_b     = []
        self.life_b   = 20
        self.mana_b   = 0
        self.land_played_b = False
        self.damage_to_a = 0   # damage B has dealt to A
        self.noncreature_spells_b = 0  # noncreature spells cast this turn by B
        self.spells_cast_b = 0  # total spells cast this turn by B (High Noon lock)

        # R4: persistent per-player exile lists. The match path otherwise has
        # NO durable exile (each _build_view creates a fresh GameState whose
        # zones.exile is a throwaway list), so a warp creature exiled at end
        # step would vanish and could never be recast. These lists hold the
        # warp-exiled (and, when the gate is on, any view-exiled) cards across
        # turns so cast_spell_from_warp_exile can find them. They are ONLY
        # touched behind _warp_match_gate -> when the gate is OFF they stay
        # empty and unused, and the match path is byte-identical.
        self.exile_a = []
        self.exile_b = []

        # Deep-copy decks to isolate per-game Card state.
        # Pre-fix: shallow `list(deck)` shared Card refs across games,
        # so mutations (summoning_sickness, lore_counters, is_transformed,
        # +1/+1 counters, tap state) leaked between games and inflated
        # win rates by ~3-5pp on aggressive matchups (BE vs Domain Zoo
        # measured 98.5% pre-fix vs ~94% post-fix at n=200 seed=42).
        # Partial fix: APL instance state ALSO leaks; full determinism
        # requires Stage 1.6 fresh-session work. Surfaced 2026-04-26 by
        # Stage 1 perf validation; see
        # harness/knowledge/tech/perf-within-matchup-parallelism-2026-04-26.md
        self.lib_a = [deepcopy(c) for c in deck_a]
        self.lib_b = [deepcopy(c) for c in deck_b]
        self.rng.shuffle(self.lib_a)
        self.rng.shuffle(self.lib_b)

    def draw_a(self, n=1) -> list:
        drawn = []
        for _ in range(n):
            if self.lib_a:
                drawn.append(self.lib_a.pop(0))
        self.hand_a.extend(drawn)
        return drawn

    def draw_b(self, n=1) -> list:
        drawn = []
        for _ in range(n):
            if self.lib_b:
                drawn.append(self.lib_b.pop(0))
        self.hand_b.extend(drawn)
        return drawn

    def lands_in_play_a(self) -> int:
        return sum(1 for c in self.bf_a if c.is_land())

    def lands_in_play_b(self) -> int:
        return sum(1 for c in self.bf_b if c.is_land())

    def power_a(self) -> int:
        return sum(_safe_power(c) for c in self.bf_a
                   if not c.is_land() and not getattr(c,'summoning_sickness',True))

    def power_b(self) -> int:
        return sum(_safe_power(c) for c in self.bf_b
                   if not c.is_land() and not getattr(c,'summoning_sickness',True))

    def _tick_warp_player(self, player: str) -> None:
        """R4 match-path end-step warp tick for ONE player (the active player
        whose end step it is). Mirrors GameState._tick_warp (game_state.py
        L757) but operates on this player's flat battlefield (bf_a/bf_b) and
        persistent exile list (exile_a/exile_b) instead of a single-player
        view's zones, because the match has two states.

        Scans the active player's battlefield for creatures cast via Warp
        (card._warp_cast), moves each to that player's exile, clears
        _warp_cast so it does not re-fire, and sets the cast-from-exile
        markers (_warp_recastable + _warp_exiled_turn = current turn) read by
        cast_spell_from_warp_exile on a LATER turn.

        Called ONLY behind _warp_match_gate -> never runs when the gate is OFF,
        so the match end-step path is byte-identical for non-opted-in decks."""
        if player == "a":
            bf, ex = self.bf_a, self.exile_a
        else:
            bf, ex = self.bf_b, self.exile_b
        for c in list(bf):
            if getattr(c, "_warp_cast", False):
                bf.remove(c)
                ex.append(c)
                c._warp_cast = False
                c._warp_recastable = True
                c._warp_exiled_turn = self.turn


def _simple_play_turn(gs: TwoPlayerGameState, player: str, apl=None):
    """
    Turn simulator for a player.

    If `apl` is provided, build a single-player `GameState` view over
    TwoPlayerGameState's per-player fields and delegate the precombat
    turn to `apl.main_phase(view)` + `apl.main_phase2(view)` if it
    exists. Zone lists are aliased between view and TwoPlayerGameState,
    so mutations (casts, plays, triggers) propagate.

    If `apl` is None (or the APL path raises an unhandled exception
    without SIM_DEBUG set), fall through to the legacy heuristic:
    play one land + cheapest-CMC nonland spells from hand. The legacy
    heuristic ignores APL entirely and is only here as a safety net;
    it was the sole code path from this file's creation until the
    APL wiring landed 2026-04-24 (see
    harness/knowledge/tech/match-runner-bug-2026-04-23.md).
    """
    if apl is not None:
        import os, sys
        from engine.game_state import GameState
        from apl.match_apl import MatchAPL, RemovalAwareGoldfishAdapter

        def _build_view(for_player):
            """Construct a single-player GameState aliasing the
            appropriate per-player fields of the shared TwoPlayerGameState."""
            if for_player == "a":
                on_play = gs.on_play
                hand, bf, gy, lib = gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a
                life, land_played = gs.life_a, gs.land_played_a
            else:
                on_play = not gs.on_play
                hand, bf, gy, lib = gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b
                life, land_played = gs.life_b, gs.land_played_b
            v = GameState(mainboard=[], on_play=on_play)
            v.turn              = gs.turn
            v.zones.hand        = hand   # list aliased — mutations propagate
            v.zones.battlefield = bf
            v.zones.graveyard   = gy
            v.zones.library     = lib
            v.life              = life
            v.land_played       = land_played
            # R4 (gated): alias this player's PERSISTENT exile so warp-exiled
            # cards survive across turns/views and cast_spell_from_warp_exile
            # can find them (it requires `card in self.zones.exile`). Gate OFF
            # -> exile stays the fresh throwaway list and this view is
            # byte-identical to the trilogy baseline.
            if _warp_match_gate(gs):
                v.zones.exile = gs.exile_a if for_player == "a" else gs.exile_b
            # Sync spell counters from TwoPlayerGameState (High Noon needs this
            # to persist across main_phase / main_phase2 / end_step view recreations)
            if for_player == "a":
                v.spells_cast_this_turn        = gs.spells_cast_a
                v.noncreature_spells_this_turn = gs.noncreature_spells_a
            else:
                v.spells_cast_this_turn        = gs.spells_cast_b
                v.noncreature_spells_this_turn = gs.noncreature_spells_b
            # Color-aware mana via ManaPool.add_land — handles basics,
            # duals, fetchlands (flex), Wasteland (colorless), etc.
            for c in v.zones.battlefield:
                if c.is_land():
                    try:
                        v.mana_pool.add_land(c.type_line or "", c.name or "")
                    except Exception:
                        v.mana_pool.add("C", 1)
            return v

        view     = _build_view(player)
        opp      = "b" if player == "a" else "a"
        opp_view = _build_view(opp)
        # Wire opponent reference so cast_spell can check High Noon on opp's bf
        view._match_opp = opp_view
        # Wire opp's APL ref so cast_spell can ask them about counterspells
        view._match_opp_apl = gs.apl_b if player == "a" else gs.apl_a
        opp_view._match_opp_apl = gs.apl_a if player == "a" else gs.apl_b
        opp_view._match_opp = view

        # Auto-upgrade goldfish APLs to opp-aware removal play.
        # Hand-tuned MatchAPLs (BorosEnergyMatchAPL etc.) keep their own logic.
        match_apl = apl if isinstance(apl, MatchAPL) else RemovalAwareGoldfishAdapter(apl)

        try:
            match_apl.main_phase_match(view, opp_view)
        except Exception as e:
            if os.environ.get("SIM_DEBUG"):
                raise
            print(
                f"  [WARN _simple_play_turn APL exec failed for "
                f"{type(apl).__name__} player={player} turn={gs.turn}: {e}]",
                file=sys.stderr,
            )

        # Sync back — APL may have played a land this turn; also sync spell counts
        if player == "a":
            gs.land_played_a = view.land_played
            gs.noncreature_spells_a = getattr(view, 'noncreature_spells_this_turn', 0)
            gs.spells_cast_a = getattr(view, 'spells_cast_this_turn', 0)
        else:
            gs.land_played_b = view.land_played
            gs.noncreature_spells_b = getattr(view, 'noncreature_spells_this_turn', 0)
            gs.spells_cast_b = getattr(view, 'spells_cast_this_turn', 0)
        # R3 storm (gated): propagate the ACTIVE player's main-phase-1 spell damage
        # back to the match state. Mirrors _run_post_combat_phase's damage sync. The
        # view is fresh (_build_view makes a new GameState, never seeds damage_dealt),
        # so view.damage_dealt holds ONLY this main1's damage and += onto the cumulative
        # total is correct (no double-count). Gated on the ACTIVE apl's WANTS_STORM (not
        # _storm_match_gate) so the opponent's own main1 burn stays dropped, exactly as
        # pre-R3. Gate OFF -> pure no-op -> byte-identical to the trilogy+R4 baseline.
        if getattr(apl, "WANTS_STORM", False):
            _dmg = getattr(view, "damage_dealt", 0)
            if player == "a":
                gs.damage_to_b += _dmg
                gs.life_b -= _dmg
            else:
                gs.damage_to_a += _dmg
                gs.life_a -= _dmg
        return

    # -------- Legacy heuristic fallback (apl is None) --------
    if player == "a":
        hand    = gs.hand_a
        bf      = gs.bf_a
        gy      = gs.gy_a
        mana    = gs.lands_in_play_a()
        land_ok = not gs.land_played_a
    else:
        hand    = gs.hand_b
        bf      = gs.bf_b
        gy      = gs.gy_b
        mana    = gs.lands_in_play_b()
        land_ok = not gs.land_played_b

    # Play a land if possible
    lands_in_hand = [c for c in hand if c.is_land()]
    if land_ok and lands_in_hand:
        land = lands_in_hand[0]
        hand.remove(land)
        bf.append(land)
        mana += 1
        if player == "a":
            gs.land_played_a = True
        else:
            gs.land_played_b = True

    # Play creatures by CMC order
    mana_left = mana
    changed   = True
    while changed:
        changed = False
        playable = [c for c in hand
                    if not c.is_land()
                    and hasattr(c, 'cmc')
                    and c.cmc <= mana_left
                    and c.cmc > 0]
        if not playable:
            break
        # Prefer lowest CMC first (aggressive sequencing)
        card = min(playable, key=lambda c: c.cmc)
        hand.remove(card)
        card.summoning_sickness = True
        bf.append(card)
        mana_left -= card.cmc
        changed = True

    # Update mana available
    if player == "a":
        gs.mana_a = mana_left
    else:
        gs.mana_b = mana_left


def _run_player_turn(gs: TwoPlayerGameState, player: str, apl,
                     skip_draw: bool, result: MatchResult, turn_num: int) -> bool:
    """Run one player's turn: draw, main, combat, main2, win check.

    Phase 4 of match-runner combat-gap fix (2026-04-26 evening / 2026-04-27).
    Extracted from run_match's inline turn handling so the loop can respect
    on_play: first-player goes first per turn (with T1 draw skip), second-
    player goes second (always draws).

    Pre-Phase-4: A always acted first per loop iteration, AND B always drew
    on T1, regardless of on_play. Both bugs compounded into a structural
    ~6pp player-A advantage in mirror matches (BE mirror n=1000: 57.4% A
    wins; Murktide mirror: 55.6%). Phase 4 makes turn order honor on_play.

    Returns True if the game ended this turn (caller should return result).
    """
    # Phase 3.5 Stage B: clear tapped_from_attack at start of player's
    # turn (creature untap step). Vigilance creatures don't tap to
    # attack, so this only clears non-vigilance creatures.
    own_bf = gs.bf_a if player == "a" else gs.bf_b
    for c in own_bf:
        c.tapped_from_attack = False

    # Azure Beastbinder strip wears off "until your next turn".
    # On the attacker's next untap, restore stashed tags + P/T on
    # any opp permanents we previously stripped.
    opp_bf = gs.bf_b if player == "a" else gs.bf_a
    for c in opp_bf:
        if getattr(c, '_abilities_stripped', False):
            stashed = getattr(c, '_beastbind_stashed_tags', None)
            if stashed is not None:
                c.tags = set(stashed)
                c._beastbind_stashed_tags = None
            orig_p = getattr(c, '_beastbind_orig_power', None)
            orig_t = getattr(c, '_beastbind_orig_toughness', None)
            if orig_p is not None:
                c.power = orig_p
                c.toughness = orig_t
                c._beastbind_orig_power = None
                c._beastbind_orig_toughness = None
            c._abilities_stripped = False

    # Reset spell counts for this player's new turn (High Noon + Slickshot tracking)
    if player == "a":
        gs.noncreature_spells_a = 0
        gs.spells_cast_a = 0
    else:
        gs.noncreature_spells_b = 0
        gs.spells_cast_b = 0

    # Draw step
    if not skip_draw:
        if player == "a":
            gs.draw_a(1)
        else:
            gs.draw_b(1)

    # Main phase 1
    _simple_play_turn(gs, player, apl)

    # R5: planeswalker loyalty activation (gated; once per player-turn so the
    # CR 606.3 budget holds by construction). Gate OFF -> no-op, byte-identical.
    _run_pw_activations(gs, player, apl)

    # Combat (Phase 3: keyword-aware -- first strike, deathtouch,
    # lifelink, trample, flying-vs-blocker, indestructible.
    # Phase 3.5 Stage B: 5-tuple return adds defender_lifelink_gain.)
    dmg, attacker_lost, defender_lost, lifelink_gain, defender_lifelink_gain, creatures_hit = _resolve_combat(gs, player)
    if player == "a":
        gs.damage_to_b += dmg
        gs.life_b      -= dmg
        gs.life_a      += lifelink_gain
        gs.life_b      += defender_lifelink_gain
        for c in attacker_lost: gs.bf_a.remove(c); gs.gy_a.append(c)
        for c in defender_lost:
            _safe_remove(gs.bf_b, c, "bf_b"); gs.gy_b.append(c)
    else:
        gs.damage_to_a += dmg
        gs.life_a      -= dmg
        gs.life_b      += lifelink_gain
        gs.life_a      += defender_lifelink_gain
        for c in attacker_lost:
            _safe_remove(gs.bf_b, c, "bf_b"); gs.gy_b.append(c)
        for c in defender_lost:
            _safe_remove(gs.bf_a, c, "bf_a"); gs.gy_a.append(c)

    # Cecil Darkness drawback (2026-05-08 audit fix):
    # "Whenever Cecil deals damage, you lose that much life."
    # Approximation: if Cecil attacked AND survived (not in attacker_lost),
    # he likely dealt damage. Lose life equal to Cecil's power (default 2).
    # This makes Cecil a real tempo trade vs free deathtouch.
    attacker_bf = gs.bf_a if player == "a" else gs.bf_b
    cecil_in_attacker = any(c.name == "Cecil, Dark Knight" for c in attacker_bf)
    cecil_died = any(c.name == "Cecil, Dark Knight" for c in attacker_lost)
    if cecil_in_attacker and not cecil_died and creatures_hit > 0:
        cecils_alive = sum(1 for c in attacker_bf if c.name == "Cecil, Dark Knight")
        cecil_dmg = 2 * cecils_alive  # Cecil's base power = 2
        if player == "a":
            gs.life_a -= cecil_dmg
        else:
            gs.life_b -= cecil_dmg

    # Enduring Curiosity: draw 1 per creature that dealt combat damage to a player
    _EC_NAMES = {"Enduring Curiosity"}
    if creatures_hit > 0:
        atk_bf = gs.bf_a if player == "a" else gs.bf_b
        if any(c.name in _EC_NAMES for c in atk_bf):
            if player == "a":
                gs.draw_a(creatures_hit)
            else:
                gs.draw_b(creatures_hit)

    # Main phase 2 (Phase 1 wiring, commit a31f360)
    _run_post_combat_phase(gs, player, apl)

    # Win check
    if player == "a":
        if gs.life_b <= 0 or gs.damage_to_b >= 20:
            result.won           = True
            result.kill_turn     = turn_num
            result.loser_life    = gs.life_b
            result.winner_damage = gs.damage_to_b
            result.turn_count    = turn_num
            return True
    else:
        if gs.life_a <= 0 or gs.damage_to_a >= 20:
            result.won           = False
            result.kill_turn     = turn_num
            result.loser_life    = gs.life_a
            result.winner_damage = gs.damage_to_a
            result.turn_count    = turn_num
            return True
    return False


def _run_post_combat_phase(gs: TwoPlayerGameState, player: str, apl):
    """Phase 1 of match-runner combat-gap fix (2026-04-26 morning).

    Calls apl.main_phase2(view) after _resolve_combat resolves, so
    BE's main_phase2 work fires in match mode (Phlage hardcast/escape,
    Pyromancer ETB+GY, Lightning Bolt face burn, Ocelot end-step Cat
    tokens, Bombardment lethal sac, Ajani transform check, saga casts,
    face_burn role iteration).

    Pre-fix: match-runner only called main_phase_match; main_phase2
    was never invoked. Diagnostic B 2026-04-26 surfaced this gap.
    See harness/knowledge/tech/match-runner-combat-gap-2026-04-26.md.

    Caveats (Phase 2 fixes):
    - view.mana_pool resets fresh from lands-in-play (not synced from
      main_phase remainder). main_phase2 effectively has full mana
      again. BE may over-cast Phlage hardcast.
    - view.energy resets to 0 each phase call. Pre-existing energy
      from main_phase is lost. APL flags persist on apl instance.
    - APLs without main_phase2 method no-op via getattr fallback.
    """
    if apl is None:
        return
    import os, sys
    from engine.game_state import GameState
    from apl.match_apl import MatchAPL, RemovalAwareGoldfishAdapter

    if player == "a":
        on_play = gs.on_play
        hand, bf, gy, lib = gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a
        life, land_played = gs.life_a, gs.land_played_a
        prev_damage = gs.damage_to_b
    else:
        on_play = not gs.on_play
        hand, bf, gy, lib = gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b
        life, land_played = gs.life_b, gs.land_played_b
        prev_damage = gs.damage_to_a

    view = GameState(mainboard=[], on_play=on_play)
    view.turn              = gs.turn
    view.zones.hand        = hand
    view.zones.battlefield = bf
    view.zones.graveyard   = gy
    view.zones.library     = lib
    view.life              = life
    view.land_played       = land_played
    view.damage_dealt      = prev_damage
    # Sync spell counters (High Noon needs persistence across views)
    if player == "a":
        view.spells_cast_this_turn        = gs.spells_cast_a
        view.noncreature_spells_this_turn = gs.noncreature_spells_a
    else:
        view.spells_cast_this_turn        = gs.spells_cast_b
        view.noncreature_spells_this_turn = gs.noncreature_spells_b

    for c in view.zones.battlefield:
        if c.is_land():
            try:
                view.mana_pool.add_land(c.type_line or "", c.name or "")
            except Exception:
                view.mana_pool.add("C", 1)

    if player == "a":
        opp_hand, opp_bf, opp_gy = gs.hand_b, gs.bf_b, gs.gy_b
        opp_life = gs.life_b
    else:
        opp_hand, opp_bf, opp_gy = gs.hand_a, gs.bf_a, gs.gy_a
        opp_life = gs.life_a
    opp_view = GameState(mainboard=[], on_play=not on_play)
    opp_view.turn = gs.turn
    opp_view.zones.hand = opp_hand
    opp_view.zones.battlefield = opp_bf
    opp_view.zones.graveyard = opp_gy
    opp_view.life = opp_life
    view._match_opp = opp_view  # for High Noon check (looks at opp's battlefield)
    view._match_opp_apl = gs.apl_b if player == "a" else gs.apl_a
    opp_view._match_opp_apl = gs.apl_a if player == "a" else gs.apl_b
    opp_view._match_opp = view

    match_apl = apl if isinstance(apl, MatchAPL) else RemovalAwareGoldfishAdapter(apl)

    try:
        if hasattr(match_apl, 'main_phase2_match'):
            match_apl.main_phase2_match(view, opp_view)
        elif hasattr(match_apl, 'main_phase2'):
            match_apl.main_phase2(view)
    except Exception as e:
        if os.environ.get("SIM_DEBUG"):
            raise
        print(
            f"  [WARN _run_post_combat_phase APL exec failed for "
            f"{type(apl).__name__} player={player} turn={gs.turn}: {e}]",
            file=sys.stderr,
        )

    delta_damage = view.damage_dealt - prev_damage
    if player == "a":
        gs.damage_to_b = view.damage_dealt
        gs.life_b -= delta_damage
        gs.life_a = view.life
        gs.spells_cast_a = getattr(view, 'spells_cast_this_turn', gs.spells_cast_a)
        gs.noncreature_spells_a = getattr(view, 'noncreature_spells_this_turn', gs.noncreature_spells_a)
    else:
        gs.damage_to_a = view.damage_dealt
        gs.life_a -= delta_damage
        gs.life_b = view.life
        gs.spells_cast_b = getattr(view, 'spells_cast_this_turn', gs.spells_cast_b)
        gs.noncreature_spells_b = getattr(view, 'noncreature_spells_this_turn', gs.noncreature_spells_b)


def _safe_power(card) -> int:
    """Safely get a card's power as int, handling '*' and None."""
    try:
        ep = getattr(card, 'effective_power', None)
        if callable(ep):
            return ep()
        p = card.power
        if p is None or p == '*':
            return 2   # default for dynamic power cards
        return int(p)
    except Exception:
        return 0


def _safe_toughness(card) -> int:
    try:
        et = getattr(card, 'effective_toughness', None)
        if callable(et):
            return et()
        t = card.toughness
        if t is None or t == '*':
            return 2
        return int(t)
    except Exception:
        return 1


def _legal_blockers(atk, blockers):
    """Filter blockers list to those legally able to block `atk` per
    evasion keywords. Returns a new list (does not mutate input).

    Phase 3.5 Stage A (2026-04-27): full block-eligibility coverage.
    Pre-Stage-A: only FLYING + REACH handled inline in _resolve_combat.

    Covers: UNBLOCKABLE, FLYING (vs reach), SHADOW (mutual restriction),
    HORSEMANSHIP, FEAR (artifact/black only), INTIMIDATE (artifact or
    shares-color). MENACE is handled at the assignment-count level in
    _resolve_combat, not here.
    """
    from engine.keywords import KWTag

    if KWTag.UNBLOCKABLE in atk.tags:
        return []

    legal = list(blockers)

    if KWTag.FLYING in atk.tags:
        legal = [b for b in legal
                 if KWTag.FLYING in b.tags or KWTag.REACH in b.tags]

    if KWTag.SHADOW in atk.tags:
        legal = [b for b in legal if KWTag.SHADOW in b.tags]
    else:
        legal = [b for b in legal if KWTag.SHADOW not in b.tags]

    if KWTag.HORSEMANSHIP in atk.tags:
        legal = [b for b in legal if KWTag.HORSEMANSHIP in b.tags]

    if KWTag.FEAR in atk.tags:
        legal = [b for b in legal
                 if 'Artifact' in (b.type_line or '')
                 or 'B' in (b.colors or [])]

    if KWTag.INTIMIDATE in atk.tags:
        atk_colors = set(atk.colors or [])
        legal = [b for b in legal
                 if 'Artifact' in (b.type_line or '')
                 or set(b.colors or []) & atk_colors]

    return legal


def _safe_remove(lst, card, label="list"):
    """list.remove that uses identity fallback when __eq__ crashes (missing attribute)."""
    try:
        lst.remove(card)
    except AttributeError:
        # Card.__eq__ failed — a card in the list is missing an attribute (e.g. colors).
        # Fall back to identity removal so the match can continue.
        bad = [c for c in lst if not hasattr(c, 'colors')]
        if bad:
            import sys
            print(f"  [WARN] _safe_remove({label}): {len(bad)} card(s) missing .colors: "
                  f"{[c.name for c in bad]}", file=sys.stderr)
        for i, c in enumerate(lst):
            if c is card:
                lst.pop(i)
                return
        # not found by identity either — skip silently
    except ValueError:
        pass  # already removed


# ── R5 planeswalker-loyalty gate + activation (all gated; gate-OFF byte-identical) ──

def _pw_match_gate(gs) -> bool:
    """R5 capability gate for the match path. Fires iff EITHER seat's APL opts
    in via WANTS_PW_LOYALTY. Reads the APLs stashed on the TwoPlayerGameState by
    run_match (gs.apl_a / gs.apl_b). The combo-sampler path never sets these, so
    getattr defaults keep it OFF there. Gate OFF -> every R5 branch below is
    skipped and the legacy combat/turn path is byte-identical."""
    return bool(getattr(getattr(gs, "apl_a", None), "WANTS_PW_LOYALTY", False)
                or getattr(getattr(gs, "apl_b", None), "WANTS_PW_LOYALTY", False))


def _warp_match_gate(gs) -> bool:
    """R4 capability gate for the match path. Fires iff EITHER seat's APL opts
    in via WANTS_WARP. Reads the APLs stashed on the TwoPlayerGameState by
    run_match (gs.apl_a / gs.apl_b), mirroring _pw_match_gate. The combo-sampler
    path never sets these, so getattr defaults keep it OFF there. Gate OFF ->
    the end-step warp tick is skipped and _build_view does NOT alias the
    persistent exile, so the match path is byte-identical to the trilogy
    baseline (the buggy-but-stable persist-forever path)."""
    return bool(getattr(getattr(gs, "apl_a", None), "WANTS_WARP", False)
                or getattr(getattr(gs, "apl_b", None), "WANTS_WARP", False))


def _storm_match_gate(gs) -> bool:
    """R3 capability gate (either-seat), for fidelity-wiring symmetry with
    _warp_match_gate. The actual main-phase-1 spell-damage sync in
    _simple_play_turn gates on the ACTIVE player's own WANTS_STORM (deliberate
    active-only choice -- so an opponent's main1 burn is NOT newly propagated
    inside a storm matchup; see spec 1.2). getattr-based, defaults False -> OFF
    for goldfish / combo-sampler paths that never set apl_a/apl_b."""
    return bool(getattr(getattr(gs, "apl_a", None), "WANTS_STORM", False)
                or getattr(getattr(gs, "apl_b", None), "WANTS_STORM", False))


def _run_pw_activations(gs: TwoPlayerGameState, player: str, apl) -> int:
    """R5: gated planeswalker loyalty activation for the active player, called
    EXACTLY ONCE per player-turn (so CR 606.3 one-ability-per-PW-per-turn holds
    by construction -- no TwoPlayerGameState budget aliasing needed). Gate OFF ->
    returns 0 immediately, legacy turn path byte-identical.

    Builds a single-player GameState view aliasing the active player's zones
    (the same aliasing pattern _build_view uses), wires _self_apl so the chooser
    is reachable, sets each PW's starting loyalty at ETB when unset, and delegates
    the tick/budget/0-loyalty-SBA to planeswalkers.activate_pws_for_turn. Zero-RNG."""
    if not _pw_match_gate(gs):
        return 0
    from engine import planeswalkers as _pw
    from engine.game_state import GameState

    if player == "a":
        on_play = gs.on_play
        hand, bf, gy, lib, life = gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a, gs.life_a
        opp_hand, opp_bf, opp_gy, opp_lib, opp_life = (
            gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b, gs.life_b)
    else:
        on_play = not gs.on_play
        hand, bf, gy, lib, life = gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b, gs.life_b
        opp_hand, opp_bf, opp_gy, opp_lib, opp_life = (
            gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a, gs.life_a)

    pws = [c for c in bf
           if "planeswalker" in (getattr(c, "type_line", "") or "").lower()]
    if not pws:
        return 0

    # ETB-set-loyalty (gated): a freshly-deployed PW Card defaults to loyalty 0
    # (data.card) so the first +ability would trigger the 0-loyalty SBA on arrival.
    # Set the printed starting value when unset; never overwrite a live total.
    for c in pws:
        if not getattr(c, "loyalty", 0):
            start = _pw.PLANESWALKER_START_LOYALTY.get(c.name)
            if start:
                c.loyalty = start

    view = GameState(mainboard=[], on_play=on_play)
    view.turn            = gs.turn
    view.zones.hand      = hand   # aliased lists -> mutations propagate
    view.zones.battlefield = bf
    view.zones.graveyard = gy
    view.zones.library   = lib
    view.life            = life
    view._self_apl       = apl

    opp_view = GameState(mainboard=[], on_play=not on_play)
    opp_view.turn            = gs.turn
    opp_view.zones.hand      = opp_hand
    opp_view.zones.battlefield = opp_bf
    opp_view.zones.graveyard = opp_gy
    opp_view.zones.library   = opp_lib
    opp_view.life            = opp_life

    fired = _pw.activate_pws_for_turn(view, opp_view, apl)

    # Sync life back: + abilities can gain life (view.life) and ults can ping /
    # the opponent loses permanents (opp_view zones alias gs.bf, propagate free).
    if player == "a":
        gs.life_a, gs.life_b = view.life, opp_view.life
    else:
        gs.life_b, gs.life_a = view.life, opp_view.life
    return fired


# ---------------------------------------------------------------------------
# R2 instant-speed combat windows -- SECONDARY mirror (design 1.3).
#
# This is the sim-fallback path (Path B in design section 0); Murktide runs the
# bo3/match_engine path, NOT this one. The mirror exists for PATH PARITY so the
# gate behaves identically regardless of which runner a matchup takes. The whole
# block is reached ONLY when _instant_combat_enabled_runner is True, so the
# gate-OFF path is byte-identical to today's _resolve_combat.
# ---------------------------------------------------------------------------

def _instant_combat_enabled_runner(gs: "TwoPlayerGameState") -> bool:
    """R2 gate for the sim-fallback runner: True iff either seat opts in.

    Reads the APLs stashed on TwoPlayerGameState (gs.apl_a / gs.apl_b). Both
    lookups default to None/False, so the goldfish path -- which constructs
    TwoPlayerGameState WITHOUT apl_a/apl_b (run_goldfish at L1009) -- returns
    False and the gate-OFF combat path is untouched on every caller.
    """
    apl_a = getattr(gs, 'apl_a', None)
    apl_b = getattr(gs, 'apl_b', None)
    return bool(getattr(apl_a, 'WANTS_INSTANT_COMBAT', False)
                or getattr(apl_b, 'WANTS_INSTANT_COMBAT', False))


def _build_combat_view(gs: "TwoPlayerGameState", player: str):
    """Build a single-player GameState view aliasing this seat's zone lists.

    Mirrors _simple_play_turn._build_view so mutations (removal moving a card
    bf -> gy, PUMP adding counters) propagate to the shared TwoPlayerGameState
    lists. Mana is filled color-aware from lands in play (same approximation the
    main-phase view uses)."""
    if player == "a":
        on_play = gs.on_play
        hand, bf, gy, lib = gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a
        life = gs.life_a
    else:
        on_play = not gs.on_play
        hand, bf, gy, lib = gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b
        life = gs.life_b
    v = GameState(mainboard=[], on_play=on_play)
    v.turn = gs.turn
    v.zones.hand        = hand
    v.zones.battlefield = bf
    v.zones.graveyard   = gy
    v.zones.library     = lib
    v.life = life
    for c in v.zones.battlefield:
        if c.is_land():
            try:
                v.mana_pool.add_land(c.type_line or "", c.name or "")
            except Exception:
                v.mana_pool.add("C", 1)
    return v


def _run_combat_window_runner(gs: "TwoPlayerGameState", attacker: str, window: int):
    """Run one gated combat window on the sim-fallback runner via the SHARED
    helper (engine.match_engine._run_combat_window). Returns nothing; mutations
    land on the aliased zone lists. ZERO random()."""
    from engine.match_engine import _run_combat_window
    defender = "b" if attacker == "a" else "a"
    active_view = _build_combat_view(gs, attacker)
    opp_view    = _build_combat_view(gs, defender)
    active_apl  = gs.apl_a if attacker == "a" else gs.apl_b
    opp_apl     = gs.apl_b if attacker == "a" else gs.apl_a
    active_view._self_apl = active_apl
    active_view._match_opp_apl = opp_apl
    active_view._match_opp = opp_view
    opp_view._self_apl = opp_apl
    opp_view._match_opp_apl = active_apl
    opp_view._match_opp = active_view
    _run_combat_window(active_view, active_apl, opp_view, opp_apl, window=window)


def _resolve_combat(gs: TwoPlayerGameState, attacker: str):
    """
    Combat with keyword awareness (Phase 3, 2026-04-27).

    Attacker sends all non-summoning-sick creatures. Defender blocks
    optimally (biggest blocker blocks biggest attacker, subject to
    flying/reach restrictions). Damage resolves in two steps for
    first strike / double strike. Lifelink, deathtouch, trample,
    indestructible all honored.

    Vigilance is no-op (match-runner doesn't model tap state).
    Menace not modeled (not BE-relevant, deferred).

    Returns a 6-tuple: (damage_dealt, attacker_losses, defender_losses,
    lifelink_gain, defender_lifelink_gain, creatures_hit). Lifelink gains
    are applied to each player's life by the caller.
    """
    from engine.keywords import KWTag

    # R5: when the loyalty gate is ON, a planeswalker must NOT be admitted to the
    # blocker pool (planeswalkers can't block) so the attack-the-walker branch can
    # target it. Gate OFF -> _pw_blockable is always True -> blocker list is
    # byte-identical to the legacy filter (which only excluded lands).
    pw_gate = _pw_match_gate(gs)

    def _pw_blockable(c):
        return (not pw_gate
                or "planeswalker" not in (getattr(c, "type_line", "") or "").lower())

    # Phase 3.5 Stage B: attacker filter ORs with KWTag.HASTE (so Ragavan
    # cast T1 can attack T1) and excludes KWTag.DEFENDER (defender
    # creatures can't attack). Blockers filter excludes
    # tapped_from_attack creatures (vigilance no-ops the tap).
    if attacker == "a":
        attackers = [c for c in gs.bf_a
                     if not c.is_land()
                     and KWTag.DEFENDER not in c.tags
                     and _pw_blockable(c)
                     and (not getattr(c, 'summoning_sickness', False)
                          or KWTag.HASTE in c.tags)]
        blockers  = [c for c in gs.bf_b
                     if not c.is_land()
                     and not getattr(c, 'tapped_from_attack', False)
                     and _pw_blockable(c)]
    else:
        attackers = [c for c in gs.bf_b
                     if not c.is_land()
                     and KWTag.DEFENDER not in c.tags
                     and _pw_blockable(c)
                     and (not getattr(c, 'summoning_sickness', False)
                          or KWTag.HASTE in c.tags)]
        blockers  = [c for c in gs.bf_a
                     if not c.is_land()
                     and not getattr(c, 'tapped_from_attack', False)
                     and _pw_blockable(c)]

    if not attackers:
        return 0, [], [], 0, 0, 0

    # --- R2 gate: WINDOW 1 (post-attackers, pre-blockers) ---
    # gate_on is False for every non-tempo deck and for the goldfish path
    # (no apl_a/apl_b), so the block below is unreached and combat stays
    # byte-identical (design 1.3).
    gate_on = _instant_combat_enabled_runner(gs)
    if gate_on:
        _run_combat_window_runner(gs, attacker, window=1)
        # A removal response may have moved a creature bf -> gy on the shared
        # lists; drop it from the local attacker/blocker working lists.
        atk_bf = gs.bf_a if attacker == "a" else gs.bf_b
        def_bf = gs.bf_b if attacker == "a" else gs.bf_a
        attackers = [a for a in attackers if a in atk_bf]
        blockers  = [b for b in blockers  if b in def_bf]
        if not attackers:
            return 0, [], [], 0, 0, 0

    # Phase 3.5 Stage B: mark non-vigilance attackers as tapped from attack.
    # Vigilance creatures don't tap to attack, so they remain available
    # to block on opponent's next turn.
    for atk in attackers:
        if KWTag.VIGILANCE not in atk.tags:
            atk.tapped_from_attack = True

    # Sunset Saboteur attack trigger -- "Whenever this creature attacks, put
    # a +1/+1 counter on target creature an opponent controls." The target
    # is opp's CHOICE; we model as their largest power creature (best pick).
    # If opp has no creatures, the trigger does nothing (no legal target).
    # Note: APL attacks SS unconditionally, so this drawback fires more often
    # in sim than a smart human pilot would let it. Real-play impact is
    # smaller -- pilot would skip attack when no legal-but-useless target.
    sunset_count = sum(1 for a in attackers if a.name == "Sunset Saboteur")
    if sunset_count > 0:
        # Defending player's battlefield = side that's NOT attacking.
        # Real card text targets ANY creature an opponent controls --
        # including Defender creatures.
        defender_bf = gs.bf_b if attacker == "a" else gs.bf_a
        defender_creatures = [c for c in defender_bf
                              if not c.is_land()
                              and getattr(c, 'power', None) is not None]
        for _ in range(sunset_count):
            if not defender_creatures:
                break  # No legal target -- trigger fizzles
            target = max(defender_creatures, key=_safe_power)
            try:
                target.power = str(int(target.power) + 1)
                target.toughness = str(int(target.toughness) + 1)
                gs._log(f"  Sunset Saboteur attack trigger: +1/+1 to {target.name} "
                        f"(now {target.power}/{target.toughness})")
            except (ValueError, TypeError):
                pass

    # Azure Beastbinder attack trigger -- "Whenever this creature attacks,
    # up to one target ARTIFACT, CREATURE, or PLANESWALKER an opponent
    # controls loses all abilities until your next turn. If creature,
    # base P/T 2/2 too." (Cannot target enchantments.)
    #
    # Priority ranking for target choice (best first):
    #   T1: Opp planeswalkers (Kaito, Aang, Ral, etc.) -- removing
    #       loyalty abilities is huge tempo
    #   T2: High-value artifacts with activated/triggered abilities
    #       (Monument to Endurance, Resonating Lute, Cryogen Relic,
    #       Cauldron of Essence, Springleaf Drum, Ghost Vacuum)
    #   T3: Combat-engine creatures (Slickshot, Sunderflock, Mightform,
    #       Lumbering Worldwagon, Sage of the Skies)
    #   T4: Largest-power opp creature
    #
    # NOTE: Stormchaser's Talent / Earthbender Ascension / Sapling
    # Nursery are ENCHANTMENTS -- Beastbinder cannot target them.
    abb_count = sum(1 for a in attackers if a.name == "Azure Beastbinder")
    if abb_count > 0:
        defender_bf = gs.bf_b if attacker == "a" else gs.bf_a
        priority_artifacts = {"Monument to Endurance", "Resonating Lute",
                              "Cryogen Relic", "Cauldron of Essence",
                              "Springleaf Drum", "Ghost Vacuum",
                              "Aether Vial", "Soul-Guide Lantern"}
        priority_creatures = {"Slickshot Show-Off", "Sunderflock",
                              "Mightform Harmonizer", "Lumbering Worldwagon",
                              "Sage of the Skies", "Stormchaser",
                              "Eddymurk Crab", "Hearth Elemental",
                              "Quantum Riddler"}
        # T1: planeswalkers (any opp PW)
        pw_targets = [c for c in defender_bf
                      if 'Planeswalker' in (c.type_line or '')]
        # T2: priority artifacts
        artifact_targets = [c for c in defender_bf
                            if c.name in priority_artifacts
                            and 'Artifact' in (c.type_line or '')]
        # T3: priority creatures
        priority_creature_targets = [c for c in defender_bf
                                     if c.name in priority_creatures
                                     and c.has(Tag.CREATURE)]
        # T4: any other creature (largest-power fallback)
        non_priority_creatures = [c for c in defender_bf
                                  if c.has(Tag.CREATURE) and not c.is_land()
                                  and c not in priority_creature_targets
                                  and getattr(c, 'power', None) is not None]
        for _ in range(abb_count):
            target = None
            if pw_targets:
                target = pw_targets.pop(0)
            elif artifact_targets:
                target = artifact_targets.pop(0)
            elif priority_creature_targets:
                target = priority_creature_targets.pop(0)
            elif non_priority_creatures:
                target = max(non_priority_creatures, key=_safe_power)
                non_priority_creatures.remove(target)
            if target is None:
                continue
            target._abilities_stripped = True
            # Stash original keyword tags so we can restore later
            target._beastbind_stashed_tags = set(target.tags)
            try:
                # Strip keyword abilities (flying, deathtouch, lifelink, etc.)
                # so the target loses combat-relevant keywords
                for kw in (KWTag.FLYING, KWTag.DEATHTOUCH, KWTag.LIFELINK,
                           KWTag.TRAMPLE, KWTag.HASTE, KWTag.MENACE,
                           KWTag.VIGILANCE, KWTag.REACH, KWTag.INDESTRUCTIBLE):
                    target.tags.discard(kw)
                # Override base P/T to 2/2 if creature
                if target.has(Tag.CREATURE):
                    target._beastbind_orig_power = target.power
                    target._beastbind_orig_toughness = target.toughness
                    target.power = "2"
                    target.toughness = "2"
            except (ValueError, TypeError):
                pass

    # Preacher of the Schism attack triggers -- two life-total-conditional
    # triggers fire on attack:
    #   - If opp has most life (or tied): create 1/1 lifelink Vampire token
    #   - If you have most life (or tied): draw a card + lose 1 life
    preacher_count = sum(1 for a in attackers if a.name == "Preacher of the Schism")
    if preacher_count > 0:
        attacker_life = gs.life_a if attacker == "a" else gs.life_b
        defender_life = gs.life_b if attacker == "a" else gs.life_a
        for _ in range(preacher_count):
            if defender_life >= attacker_life:
                # Opp has most life -- token trigger
                # Add a 1/1 lifelink Vampire token to attacker's board
                attacker_bf = gs.bf_a if attacker == "a" else gs.bf_b
                from data.card import Card, Tag as _Tag
                token = Card(name="Vampire Token", mana_cost="", cmc=0,
                             type_line="Token Creature - Vampire",
                             power="1", toughness="1", colors=["W"])
                token.tags = {_Tag.CREATURE, KWTag.LIFELINK}
                token.summoning_sickness = True
                attacker_bf.append(token)
            if attacker_life >= defender_life:
                # You have most life -- draw + lose 1
                if attacker == "a":
                    gs.life_a -= 1
                    if gs.lib_a:
                        gs.hand_a.append(gs.lib_a.pop(0))
                else:
                    gs.life_b -= 1
                    if gs.lib_b:
                        gs.hand_b.append(gs.lib_b.pop(0))

    # Slickshot Show-Off: +2/+0 per noncreature spell cast this turn (power only)
    _SLICKSHOT_NAMES = {"Slickshot Show-Off"}
    n_spells = gs.noncreature_spells_a if attacker == "a" else gs.noncreature_spells_b
    slickshot_boosted = []
    if n_spells > 0:
        for atk in attackers:
            if atk.name in _SLICKSHOT_NAMES:
                try:
                    orig_pwr = atk.power
                    atk.power = str(int(atk.power) + n_spells * 2)
                    slickshot_boosted.append((atk, orig_pwr))
                except (ValueError, TypeError):
                    pass

    atk_sorted = sorted(attackers, key=lambda c: -_safe_power(c))
    blk_sorted = sorted(blockers,  key=lambda c: -_safe_power(c))

    # Blocker assignment (Phase 3.5 Stage A): full evasion coverage via
    # _legal_blockers helper. Each attacker gets a LIST of blockers
    # (menace requires 2+; unblockable / unsatisfiable -> empty list).
    # Defender prioritizes biggest attackers first; uses biggest legal
    # blockers; for menace attackers, assigns 2 if available else 0.
    available_blockers = list(blk_sorted)
    assignments = {}  # id(attacker) -> list[blocker]
    for atk in atk_sorted:
        legal = _legal_blockers(atk, available_blockers)
        if not legal:
            assignments[id(atk)] = []
            continue
        needed = 2 if KWTag.MENACE in atk.tags else 1
        if len(legal) < needed:
            # Can't satisfy menace -- attacker goes unblocked
            assignments[id(atk)] = []
            continue
        chosen = legal[:needed]
        assignments[id(atk)] = chosen
        for b in chosen:
            available_blockers.remove(b)

    # --- R2 gate: WINDOW 2 (post-blockers, pre-combat-damage) ---
    # Canonical combat-trick window. Pump mutates a creature's counters on the
    # shared lists; effective_power/_toughness (read by _safe_power/_safe_toughness
    # at the strike step below) reflect it for free -- no damage-routine change.
    # gate_on was computed at WINDOW 1; the whole block is unreached when OFF.
    #
    # Trilogy-integration ordering: WINDOW 2 runs BEFORE R5's pw-assignment so a
    # window-2 removal/pump that kills an attacker prunes atk_sorted FIRST; R5's
    # pw-assignment below then reads the post-window-2 atk_sorted/assignments.
    # The two gates stay independent -- R2-only leaves pw_assignment empty, R5-only
    # skips this block, both-off reaches neither (pw_assignment defaults to {}).
    if gate_on:
        _run_combat_window_runner(gs, attacker, window=2)
        # A removal response could have killed a creature mid-window: drop dead
        # attackers from assignments and dead blockers from each assignment list.
        atk_bf = gs.bf_a if attacker == "a" else gs.bf_b
        def_bf = gs.bf_b if attacker == "a" else gs.bf_a
        atk_sorted = [a for a in atk_sorted if a in atk_bf]
        for k in list(assignments.keys()):
            assignments[k] = [b for b in assignments[k] if b in def_bf]

    # R5: gated attackable-planeswalker assignment. An UNBLOCKED attacker may be
    # routed at an opposing planeswalker instead of the player's face (CR 508.1 /
    # 306.5b: combat damage to a PW is removed as loyalty). Gate OFF -> the dict
    # stays empty, the strike-step PW branch is never entered, combat is
    # byte-identical. Heuristic (two-sided, zero-RNG): if the unblocked attack is
    # NOT lethal to the face, divert ONE attacker per walker (largest attacker ->
    # the walker nearest its ultimate, i.e. highest loyalty); the rest still hit
    # the face. If the attack IS lethal, take the kill and divert nothing.
    pw_assignment = {}  # id(attacker) -> planeswalker card
    if pw_gate:
        defender_bf = gs.bf_b if attacker == "a" else gs.bf_a
        defender_life = gs.life_b if attacker == "a" else gs.life_a
        opp_pws = [c for c in defender_bf
                   if "planeswalker" in (getattr(c, "type_line", "") or "").lower()
                   and (getattr(c, "loyalty", 0) or 0) > 0]
        if opp_pws:
            unblocked = [a for a in atk_sorted if not assignments.get(id(a))]
            total_unblocked = sum(_safe_power(a) for a in unblocked)
            if total_unblocked < defender_life:
                walkers = sorted(opp_pws,
                                 key=lambda p: -(getattr(p, "loyalty", 0) or 0))
                pool = sorted(unblocked, key=lambda a: -_safe_power(a))
                for pw_card in walkers:
                    if not pool:
                        break
                    chosen_atk = pool.pop(0)   # one attacker per walker
                    pw_assignment[id(chosen_atk)] = pw_card

    atk_dead = set()  # id() of dead attackers
    blk_dead = set()  # id() of dead blockers
    blk_lookup = {id(b): b for b in blockers}
    atk_lookup = {id(a): a for a in attackers}
    total_dmg = 0
    lifelink_gain = 0           # attacker-side lifelink (gains attacking player)
    defender_lifelink_gain = 0  # blocker-side lifelink (gains defending player)
    creatures_hit_player = 0    # count of attackers that dealt damage to defending player

    def _is_indestructible(c):
        return KWTag.INDESTRUCTIBLE in c.tags

    def _resolve_strike_step(strike_attackers):
        """Resolve damage for one strike step (first-strike or regular).
        Updates atk_dead, blk_dead, total_dmg, lifelink_gain in enclosing
        scope. Skips attackers/blockers already dead from prior step.

        Phase 3.5 Stage A: handles multi-blocker assignment (menace).
        Attacker assigns damage among blockers in list order (biggest-
        first); deathtouch makes 1 damage lethal to each blocker.
        """
        nonlocal total_dmg, lifelink_gain, defender_lifelink_gain, creatures_hit_player
        for atk in strike_attackers:
            if id(atk) in atk_dead:
                continue
            atk_pwr = _safe_power(atk)
            atk_tou = _safe_toughness(atk)
            atk_dt  = KWTag.DEATHTOUCH in atk.tags
            atk_ll  = KWTag.LIFELINK in atk.tags
            atk_tr  = KWTag.TRAMPLE in atk.tags

            blocker_list = assignments.get(id(atk), [])
            # Filter out blockers already dead from prior step
            live_blockers = [b for b in blocker_list if id(b) not in blk_dead]

            if not live_blockers:
                # R5: unblocked attacker routed at an opposing planeswalker.
                # Combat damage removes loyalty (does NOT reduce the player's
                # life); the attacker is committed to the walker, so it deals no
                # face damage even if the walker is already dead (no trample-over-
                # PW in v1). Lifelink still gains. 0-loyalty -> shared SBA.
                if id(atk) in pw_assignment:
                    pw_target = pw_assignment[id(atk)]
                    if (getattr(pw_target, "loyalty", 0) or 0) > 0 and atk_pwr > 0:
                        pw_target.loyalty -= atk_pwr
                        if atk_ll:
                            lifelink_gain += atk_pwr
                        if pw_target.loyalty <= 0:
                            from engine import planeswalkers as _pw
                            dbf = gs.bf_b if attacker == "a" else gs.bf_a
                            dgy = gs.gy_b if attacker == "a" else gs.gy_a
                            if pw_target in dbf:
                                dbf.remove(pw_target)
                                dgy.append(pw_target)
                                _pw.note_pw_combat_death()
                    continue
                # Unblocked (or all blockers died in first-strike step):
                # full damage to defending player
                if atk_pwr > 0:
                    total_dmg += atk_pwr
                    creatures_hit_player += 1   # for Enduring Curiosity trigger
                if atk_ll:
                    lifelink_gain += atk_pwr
                continue

            # Blocked combat -- two sequential passes over live_blockers.
            # Pass 1: accumulate total damage TO attacker before lethality
            # check (CR: blocker damage sums on the attacker; total >=
            # toughness is lethal). Pre-fix bug: per-blocker check meant
            # 2x 2/2 vs 3/4 menace attacker didn't kill it (neither blocker
            # had 2 >= 4 individually). Hidden in BE/Murktide mirrors (no
            # menace) but breaks Rakdos Bloodtithe Harvester etc.
            total_damage_to_atk = 0
            any_blocker_deathtouch = False
            for blk in live_blockers:
                blk_pwr = _safe_power(blk)
                if blk_pwr > 0:
                    total_damage_to_atk += blk_pwr
                    if KWTag.DEATHTOUCH in blk.tags:
                        any_blocker_deathtouch = True
                    # Phase 3.5 Stage B: blocker-side lifelink (defender
                    # gains life equal to blocker's damage to attacker).
                    if KWTag.LIFELINK in blk.tags:
                        defender_lifelink_gain += blk_pwr

            # Apply combined damage to attacker
            if total_damage_to_atk > 0 and not _is_indestructible(atk):
                if total_damage_to_atk >= atk_tou or any_blocker_deathtouch:
                    atk_dead.add(id(atk))

            # Pass 2: attacker assigns damage among blockers in list order
            # (biggest-first per assignment, CR 509.4 attacker chooses order)
            damage_remaining = atk_pwr
            for blk in live_blockers:
                blk_tou = _safe_toughness(blk)
                if damage_remaining > 0:
                    # Deathtouch: 1 damage is lethal regardless of toughness
                    damage_to_assign = 1 if atk_dt else min(damage_remaining, blk_tou)
                    if not _is_indestructible(blk):
                        if damage_to_assign >= blk_tou or atk_dt:
                            blk_dead.add(id(blk))
                    if atk_ll:
                        lifelink_gain += damage_to_assign
                    damage_remaining -= damage_to_assign

            # Trample: excess damage after all blockers go to defending player
            if atk_tr and damage_remaining > 0:
                total_dmg += damage_remaining
                if atk_ll:
                    lifelink_gain += damage_remaining

    # First-strike step: FIRST_STRIKE or DOUBLE_STRIKE attackers
    first_strikers = [c for c in atk_sorted
                      if KWTag.FIRST_STRIKE in c.tags
                      or KWTag.DOUBLE_STRIKE in c.tags]
    _resolve_strike_step(first_strikers)

    # Regular step: any attacker without FIRST_STRIKE deals damage
    # (DOUBLE_STRIKE deals damage in BOTH steps)
    regular_strikers = [c for c in atk_sorted
                        if KWTag.FIRST_STRIKE not in c.tags
                        or KWTag.DOUBLE_STRIKE in c.tags]
    _resolve_strike_step(regular_strikers)

    atk_losses = [atk_lookup[i] for i in atk_dead]
    blk_losses = [blk_lookup[i] for i in blk_dead]

    # Restore Slickshot power after damage is resolved
    for card, orig_pwr in slickshot_boosted:
        card.power = orig_pwr

    return total_dmg, atk_losses, blk_losses, lifelink_gain, defender_lifelink_gain, creatures_hit_player


class ComboKillSampler:
    """
    For combo decks that can't be modeled with simple creature deployment.
    Samples a kill turn from a pre-measured distribution and deals lethal
    damage on that turn, bypassing combat entirely.

    This gives realistic win/loss timing even without a full combo APL.
    """
    KILL_DISTS = {
        "dimir reanimator": {1: 5, 2: 40, 3: 35, 4: 15, 5: 5},
        "lotus combo":      {2: 5, 3: 30, 4: 40, 5: 20, 6: 5},
        "cephalid breakfast":{1: 2, 2: 30, 3: 45, 4: 18, 5: 5},
        "sneak and show":   {2: 10, 3: 40, 4: 35, 5: 10, 6: 5},
        "mono red painter": {3: 20, 4: 40, 5: 30, 6: 10},
        "doomsday":         {2: 10, 3: 35, 4: 35, 5: 15, 6: 5},
        "bant nadu":        {3: 15, 4: 40, 5: 35, 6: 10},
    }

    def __init__(self, archetype: str, rng: random.Random):
        key = archetype.lower().replace(" ", "").replace("-", "")
        dist = None
        for k, v in self.KILL_DISTS.items():
            if k.replace(" ", "") == key:
                dist = v
                break
        self.dist    = dist or {4: 50, 5: 30, 6: 20}
        self.rng     = rng
        self._kill_t = self._sample_kill()
        self.name    = archetype

    def _sample_kill(self) -> int:
        turns   = sorted(self.dist.keys())
        weights = [self.dist[t] for t in turns]
        total   = sum(weights)
        r       = self.rng.random() * total
        cumul   = 0
        for t, w in zip(turns, weights):
            cumul += w
            if r <= cumul:
                return t
        return turns[-1]

    def kills_on_turn(self, turn: int) -> bool:
        return turn == self._kill_t


def _run_match_with_combo(
    apl_a, deck_a, combo_b: ComboKillSampler,
    on_play: bool, max_turns: int, rng: random.Random
) -> MatchResult:
    """
    Run a match where player B is a combo deck modeled by kill-turn sampling.
    Player A plays normally via _simple_play_turn; player B deals lethal on its kill turn.
    """
    result = MatchResult()
    gs = TwoPlayerGameState(deck_a, [], on_play=on_play, seed=rng.randint(0, 999999))

    # Opening hand for A only
    gs.draw_a(7)
    for _ in range(3):
        if sum(1 for c in gs.hand_a if c.is_land()) < 2:
            gs.lib_a = gs.hand_a + gs.lib_a
            gs.hand_a = []
            gs.rng.shuffle(gs.lib_a)
            gs.draw_a(max(4, 7 - result.mulligans_a - 1))
            result.mulligans_a += 1
        else:
            break

    for turn_num in range(1, max_turns + 1):
        gs.turn = turn_num
        gs.land_played_a = False

        if turn_num > 1:
            for c in gs.bf_a:
                c.summoning_sickness = False

        if not (turn_num == 1 and on_play):
            gs.draw_a(1)

        _simple_play_turn(gs, "a")

        # Player A attacks (Phase 3: keyword-aware; _resolve_combat returns a 6-tuple)
        dmg, a_lost, b_lost, lifelink_gain, defender_lifelink_gain, creatures_hit = _resolve_combat(gs, "a")
        gs.damage_to_b += dmg
        # Note: combo path doesn't track gs.life_a directly; lifelink no-op here
        for c in a_lost: gs.bf_a.remove(c); gs.gy_a.append(c)

        if gs.damage_to_b >= 20:
            result.won = True; result.kill_turn = turn_num
            result.winner_damage = gs.damage_to_b; result.turn_count = turn_num
            return result

        # Player B combo kill check
        if combo_b.kills_on_turn(turn_num):
            result.won = False; result.kill_turn = turn_num
            result.winner_damage = 20; result.turn_count = turn_num
            return result

    result.won = gs.damage_to_b > 0
    result.kill_turn = max_turns; result.turn_count = max_turns
    return result


def _run_end_step(gs: TwoPlayerGameState, active_player: str,
                  reactive_player: str, reactive_apl) -> None:
    """
    End-step window: reactive player's APL may flash instants/creatures
    at the end of the active player's turn (e.g. Floodpits Drowner during
    opponent's upkeep timing, Eddymurk Crab EOT bounce, etc.).

    Builds a GameState view for the reactive player and calls end_step_actions.
    """
    import os, sys
    # R4 (gated): the active player's beginning-of-end-step warp trigger. This
    # is the active player's own trigger and must fire regardless of whether
    # the reactive player has flash actions, so it runs BEFORE the reactive
    # early-returns below. Gate OFF -> pure no-op, end-step path byte-identical.
    if _warp_match_gate(gs):
        gs._tick_warp_player(active_player)
    if reactive_apl is None:
        return
    from engine.game_state import GameState
    from apl.match_apl import MatchAPL, RemovalAwareGoldfishAdapter

    match_apl = (reactive_apl if isinstance(reactive_apl, MatchAPL)
                 else RemovalAwareGoldfishAdapter(reactive_apl))
    if not hasattr(match_apl, 'end_step_actions'):
        return

    # ── Voice of Victory lock ─────────────────────────────────────────────
    # 'Your opponents can't cast spells during your turn.'
    # If active player controls Voice, the reactive player cannot cast
    # spells in this end-step window. Skip the call entirely.
    active_bf = gs.bf_a if active_player == "a" else gs.bf_b
    if any(c.name == "Voice of Victory" for c in active_bf):
        return

    if reactive_player == "a":
        on_play = gs.on_play
        hand, bf, gy, lib = gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a
        life, land_played = gs.life_a, gs.land_played_a
        opp_hand, opp_bf, opp_gy, opp_lib = gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b
        opp_life = gs.life_b
    else:
        on_play = not gs.on_play
        hand, bf, gy, lib = gs.hand_b, gs.bf_b, gs.gy_b, gs.lib_b
        life, land_played = gs.life_b, gs.land_played_b
        opp_hand, opp_bf, opp_gy, opp_lib = gs.hand_a, gs.bf_a, gs.gy_a, gs.lib_a
        opp_life = gs.life_a

    view = GameState(mainboard=[], on_play=on_play)
    view.turn              = gs.turn
    view.zones.hand        = hand
    view.zones.battlefield = bf
    view.zones.graveyard   = gy
    view.zones.library     = lib
    view.life              = life
    view.land_played       = land_played
    for c in bf:
        if c.is_land():
            try:
                view.mana_pool.add_land(c.type_line or "", c.name or "")
            except Exception:
                view.mana_pool.add("C", 1)

    opp_view = GameState(mainboard=[], on_play=not on_play)
    opp_view.turn              = gs.turn
    opp_view.zones.hand        = opp_hand
    opp_view.zones.battlefield = opp_bf
    opp_view.zones.graveyard   = opp_gy
    opp_view.zones.library     = opp_lib
    opp_view.life              = opp_life
    view._match_opp = opp_view
    # In end_step, view is the REACTIVE player; opp's APL is the active player's APL
    view._match_opp_apl = gs.apl_b if active_player == "a" else gs.apl_a
    opp_view._match_opp_apl = gs.apl_a if active_player == "a" else gs.apl_b
    opp_view._match_opp = view
    # Reactive cast flag: cast_spell will check opp's Voice of Victory and
    # also enforce the High Noon symmetric lock against this player's
    # already-cast spells this turn.
    view._is_reactive_cast = True
    if reactive_player == "a":
        view.spells_cast_this_turn        = gs.spells_cast_a
        view.noncreature_spells_this_turn = gs.noncreature_spells_a
    else:
        view.spells_cast_this_turn        = gs.spells_cast_b
        view.noncreature_spells_this_turn = gs.noncreature_spells_b

    try:
        match_apl.end_step_actions(view, opp_view)
    except Exception as e:
        if os.environ.get("SIM_DEBUG"):
            raise
        print(f"  [WARN end_step {type(reactive_apl).__name__}: {e}]",
              file=sys.stderr)

    # Sync hand/bf/gy back (APL may have moved cards)
    if reactive_player == "a":
        gs.land_played_a = view.land_played
        gs.spells_cast_a = getattr(view, 'spells_cast_this_turn', gs.spells_cast_a)
        gs.noncreature_spells_a = getattr(view, 'noncreature_spells_this_turn', gs.noncreature_spells_a)
    else:
        gs.land_played_b = view.land_played
        gs.spells_cast_b = getattr(view, 'spells_cast_this_turn', gs.spells_cast_b)
        gs.noncreature_spells_b = getattr(view, 'noncreature_spells_this_turn', gs.noncreature_spells_b)


def run_match(
    apl_a,
    deck_a:   list,
    apl_b,
    deck_b:   list,
    on_play:  bool = True,
    max_turns: int = 15,
    seed:     int  = None,
) -> MatchResult:
    """
    Run a single match between two APLs.
    Returns MatchResult with winner, kill turn, and game data.
    """
    result = MatchResult()
    gs = TwoPlayerGameState(deck_a, deck_b, on_play=on_play, seed=seed)
    # Stash APLs on TwoPlayerGameState so view-builders can wire
    # _match_opp_apl onto per-player GameStates (cast_spell needs this
    # to ask the opponent whether to counter).
    gs.apl_a = apl_a
    gs.apl_b = apl_b

    # Opening hands
    gs.draw_a(7)
    gs.draw_b(7)

    # Simple mulligan: mull if 0 or 1 land
    for _ in range(3):
        lands = sum(1 for c in gs.hand_a if c.is_land())
        if lands < 2:
            gs.lib_a = gs.hand_a + gs.lib_a
            gs.hand_a = []
            gs.rng.shuffle(gs.lib_a)
            gs.draw_a(max(4, 7 - result.mulligans_a - 1))
            result.mulligans_a += 1
        else:
            break

    for _ in range(3):
        lands = sum(1 for c in gs.hand_b if c.is_land())
        if lands < 2:
            gs.lib_b = gs.hand_b + gs.lib_b
            gs.hand_b = []
            gs.rng.shuffle(gs.lib_b)
            gs.draw_b(max(4, 7 - result.mulligans_b - 1))
            result.mulligans_b += 1
        else:
            break

    for turn_num in range(1, max_turns + 1):
        gs.turn = turn_num
        gs.land_played_a = False
        gs.land_played_b = False

        # Untap all creatures (remove summoning sickness for T2+)
        if turn_num > 1:
            for c in gs.bf_a + gs.bf_b:
                c.summoning_sickness = False

        # Phase 4 fix (2026-04-27): turn order respects on_play. The player
        # on the play goes first each turn (and skips draw on T1). Pre-fix,
        # A always acted first per loop iteration AND B always drew on T1
        # regardless of on_play, producing a structural ~6pp player-A
        # advantage in mirror matches.
        if on_play:
            first, first_apl   = "a", apl_a
            second, second_apl = "b", apl_b
        else:
            first, first_apl   = "b", apl_b
            second, second_apl = "a", apl_a

        # First player's turn (skips draw on T1 per Magic rules)
        if _run_player_turn(gs, first, first_apl,
                            skip_draw=(turn_num == 1),
                            result=result, turn_num=turn_num):
            return result
        # End-step: second player's APL may flash instants at end of first's turn
        _run_end_step(gs, first, second, second_apl)

        # Second player's turn (always draws)
        if _run_player_turn(gs, second, second_apl,
                            skip_draw=False,
                            result=result, turn_num=turn_num):
            return result
        # End-step: first player's APL may flash instants at end of second's turn
        _run_end_step(gs, second, first, first_apl)

    # Time out — call it based on life totals
    result.won       = gs.life_b < gs.life_a
    result.kill_turn = max_turns
    result.turn_count = max_turns
    return result


def _run_single_match(args):
    """Module-level worker for ProcessPoolExecutor — must be picklable."""
    game_seed, apl_a_class, apl_b_class, deck_a, deck_b, on_play, use_combo_sampler = args
    random.seed(game_seed)
    fresh_apl_a = apl_a_class()
    fresh_apl_b = apl_b_class()
    if use_combo_sampler:
        rng = random.Random(game_seed)
        combo_b = ComboKillSampler(getattr(fresh_apl_b, 'name', 'unknown'), rng)
        return _run_match_with_combo(
            fresh_apl_a, deck_a, combo_b,
            on_play=on_play, max_turns=15, rng=rng,
        )
    return run_match(fresh_apl_a, deck_a, fresh_apl_b, deck_b,
                     on_play=on_play, seed=game_seed)


def run_match_set(
    apl_a,
    deck_a:    list,
    apl_b,
    deck_b:    list,
    n:         int  = 1000,
    on_play:   bool = True,
    seed:      int  = 42,
    mix_play_draw: bool = True,
    n_workers: int  = 1,
) -> MatchSetResults:
    """
    Run N matches between two APLs. Returns aggregated results.
    If apl_b is a known combo archetype, uses ComboKillSampler for accuracy.
    mix_play_draw=True alternates who is on the play.
    """
    results = MatchSetResults(n_games=n)
    rng = random.Random(seed)

    combo_keys = set(ComboKillSampler.KILL_DISTS.keys())
    b_name = getattr(apl_b, 'name', '').lower().replace(' ', '').replace('-','')
    use_combo_sampler = any(k.replace(' ','') == b_name for k in combo_keys)

    apl_a_class = type(apl_a)
    apl_b_class = type(apl_b)

    # Pre-generate per-game seeds and play/draw flags from the seeded rng.
    # Using per-game seeds (rather than chaining global random across games)
    # ensures bit-identical results across any n_workers value, because each
    # game always receives the same (game_seed, on_play) regardless of how
    # many workers are running. Determinism contract: same (n, seed, n_workers)
    # => identical aggregate for all n_workers >= 1.
    game_seeds   = [rng.randint(0, 999999) for _ in range(n)]
    game_on_plays = [(i % 2 == 0) if mix_play_draw else on_play for i in range(n)]

    saved_global_random_state = random.getstate()
    try:
        if n_workers <= 1:
            for i in range(n):
                # Per-game global seed: makes naked random.foo() consumers in
                # engine code (zones.shuffle, opponent.py, ~10 handler sites)
                # deterministic for this game independently of other games.
                random.seed(game_seeds[i])
                fresh_apl_a = apl_a_class()
                fresh_apl_b = apl_b_class()
                if use_combo_sampler:
                    combo_rng = random.Random(game_seeds[i])
                    combo_b = ComboKillSampler(
                        getattr(fresh_apl_b, 'name', 'unknown'), combo_rng)
                    match = _run_match_with_combo(
                        fresh_apl_a, deck_a, combo_b,
                        on_play=game_on_plays[i], max_turns=15, rng=combo_rng,
                    )
                else:
                    match = run_match(fresh_apl_a, deck_a, fresh_apl_b, deck_b,
                                      on_play=game_on_plays[i],
                                      seed=game_seeds[i])
                if match.won:
                    results.a_wins += 1
                else:
                    results.b_wins += 1
                results.kill_turns.append(match.kill_turn)
        else:
            game_args = [
                (game_seeds[i], apl_a_class, apl_b_class,
                 deck_a, deck_b, game_on_plays[i], use_combo_sampler)
                for i in range(n)
            ]
            with concurrent.futures.ProcessPoolExecutor(max_workers=n_workers) as pool:
                matches = list(pool.map(_run_single_match, game_args))
            for match in matches:
                if match.won:
                    results.a_wins += 1
                else:
                    results.b_wins += 1
                results.kill_turns.append(match.kill_turn)
    finally:
        random.setstate(saved_global_random_state)

    results.avg_turns = sum(results.kill_turns) / n if n else 0
    return results
