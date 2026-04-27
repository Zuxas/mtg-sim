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
from dataclasses import dataclass, field
from typing import Optional
from copy import deepcopy

from engine.game_state import GameState, Phase
from engine.zones import Zones
from engine.mana import ManaPool
from data.card import Card, Tag


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


@dataclass 
class MatchSetResults:
    n_games:    int = 0
    a_wins:     int = 0
    b_wins:     int = 0
    avg_turns:  float = 0.0
    kill_turns: list = field(default_factory=list)

    def win_rate(self) -> float:
        return self.a_wins / self.n_games if self.n_games else 0.0

    def win_pct(self) -> float:
        return round(self.win_rate() * 100, 1)

    def kill_turn_distribution(self) -> dict:
        dist = {}
        for t in self.kill_turns:
            dist[t] = dist.get(t, 0) + 1
        total = len(self.kill_turns)
        return {t: round(c/total*100, 2) for t,c in sorted(dist.items())} if total else {}


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

        # Player B state
        self.hand_b   = []
        self.bf_b     = []
        self.gy_b     = []
        self.life_b   = 20
        self.mana_b   = 0
        self.land_played_b = False
        self.damage_to_a = 0   # damage B has dealt to A

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

        # Sync back — APL may have played a land this turn
        if player == "a":
            gs.land_played_a = view.land_played
        else:
            gs.land_played_b = view.land_played
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

    # Draw step
    if not skip_draw:
        if player == "a":
            gs.draw_a(1)
        else:
            gs.draw_b(1)

    # Main phase 1
    _simple_play_turn(gs, player, apl)

    # Combat (Phase 3: keyword-aware -- first strike, deathtouch,
    # lifelink, trample, flying-vs-blocker, indestructible.
    # Phase 3.5 Stage B: 5-tuple return adds defender_lifelink_gain.)
    dmg, attacker_lost, defender_lost, lifelink_gain, defender_lifelink_gain = _resolve_combat(gs, player)
    if player == "a":
        gs.damage_to_b += dmg
        gs.life_b      -= dmg
        gs.life_a      += lifelink_gain
        gs.life_b      += defender_lifelink_gain
        for c in attacker_lost: gs.bf_a.remove(c); gs.gy_a.append(c)
        for c in defender_lost: gs.bf_b.remove(c); gs.gy_b.append(c)
    else:
        gs.damage_to_a += dmg
        gs.life_a      -= dmg
        gs.life_b      += lifelink_gain
        gs.life_a      += defender_lifelink_gain
        for c in attacker_lost: gs.bf_b.remove(c); gs.gy_b.append(c)
        for c in defender_lost: gs.bf_a.remove(c); gs.gy_a.append(c)

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
    else:
        gs.damage_to_a = view.damage_dealt
        gs.life_a -= delta_damage
        gs.life_b = view.life


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

    Returns (damage_dealt, attacker_losses, defender_losses,
    lifelink_gain). Lifelink applied to attacking-player's life by
    caller.
    """
    from engine.keywords import KWTag

    # Phase 3.5 Stage B: attacker filter ORs with KWTag.HASTE (so Ragavan
    # cast T1 can attack T1) and excludes KWTag.DEFENDER (defender
    # creatures can't attack). Blockers filter excludes
    # tapped_from_attack creatures (vigilance no-ops the tap).
    if attacker == "a":
        attackers = [c for c in gs.bf_a
                     if not c.is_land()
                     and KWTag.DEFENDER not in c.tags
                     and (not getattr(c, 'summoning_sickness', False)
                          or KWTag.HASTE in c.tags)]
        blockers  = [c for c in gs.bf_b
                     if not c.is_land()
                     and not getattr(c, 'tapped_from_attack', False)]
    else:
        attackers = [c for c in gs.bf_b
                     if not c.is_land()
                     and KWTag.DEFENDER not in c.tags
                     and (not getattr(c, 'summoning_sickness', False)
                          or KWTag.HASTE in c.tags)]
        blockers  = [c for c in gs.bf_a
                     if not c.is_land()
                     and not getattr(c, 'tapped_from_attack', False)]

    if not attackers:
        return 0, [], [], 0, 0

    # Phase 3.5 Stage B: mark non-vigilance attackers as tapped from attack.
    # Vigilance creatures don't tap to attack, so they remain available
    # to block on opponent's next turn.
    for atk in attackers:
        if KWTag.VIGILANCE not in atk.tags:
            atk.tapped_from_attack = True

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

    atk_dead = set()  # id() of dead attackers
    blk_dead = set()  # id() of dead blockers
    blk_lookup = {id(b): b for b in blockers}
    atk_lookup = {id(a): a for a in attackers}
    total_dmg = 0
    lifelink_gain = 0           # attacker-side lifelink (gains attacking player)
    defender_lifelink_gain = 0  # blocker-side lifelink (gains defending player)

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
        nonlocal total_dmg, lifelink_gain, defender_lifelink_gain
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
                # Unblocked (or all blockers died in first-strike step):
                # full damage to defending player
                total_dmg += atk_pwr
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

    return total_dmg, atk_losses, blk_losses, lifelink_gain, defender_lifelink_gain


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

        # Player A attacks (Phase 3: keyword-aware; Phase 3.5 Stage B 5-tuple)
        dmg, a_lost, b_lost, lifelink_gain, defender_lifelink_gain = _resolve_combat(gs, "a")
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

        # Second player's turn (always draws)
        if _run_player_turn(gs, second, second_apl,
                            skip_draw=False,
                            result=result, turn_num=turn_num):
            return result

    # Time out — call it based on life totals
    result.won       = gs.life_b < gs.life_a
    result.kill_turn = max_turns
    result.turn_count = max_turns
    return result


def run_match_set(
    apl_a,
    deck_a:    list,
    apl_b,
    deck_b:    list,
    n:         int  = 1000,
    on_play:   bool = True,
    seed:      int  = 42,
    mix_play_draw: bool = True,
) -> MatchSetResults:
    """
    Run N matches between two APLs. Returns aggregated results.
    If apl_b is a known combo archetype, uses ComboKillSampler for accuracy.
    mix_play_draw=True alternates who is on the play.
    """
    results = MatchSetResults(n_games=n)
    rng = random.Random(seed)

    # Check if B is a combo deck — use sampler for accuracy
    combo_keys = set(ComboKillSampler.KILL_DISTS.keys())
    b_name = getattr(apl_b, 'name', '').lower().replace(' ', '').replace('-','')
    use_combo_sampler = any(k.replace(' ','') == b_name for k in combo_keys)

    # Stage 1.6: instantiate a fresh APL per game to eliminate APL
    # state leakage. Pre-fix, per-game-mutable APL fields
    # (BorosEnergy: _cat_died_this_turn, _treasures, _gained_life_this_turn,
    # _tokens_entered_this_turn, _roles_computed cache; similar in others)
    # leaked between games even after Stage 1.5's Card deepcopy.
    # Combined with Stage 1.5, this completes the determinism fix.
    apl_a_class = type(apl_a)
    apl_b_class = type(apl_b)

    for i in range(n):
        game_on_play = (i % 2 == 0) if mix_play_draw else on_play

        fresh_apl_a = apl_a_class()
        fresh_apl_b = apl_b_class()

        if use_combo_sampler:
            combo_b = ComboKillSampler(getattr(fresh_apl_b, 'name', 'unknown'), rng)
            match = _run_match_with_combo(
                fresh_apl_a, deck_a, combo_b,
                on_play=game_on_play, max_turns=15, rng=rng
            )
        else:
            match = run_match(fresh_apl_a, deck_a, fresh_apl_b, deck_b,
                              on_play=game_on_play,
                              seed=rng.randint(0, 999999))

        if match.won:
            results.a_wins += 1
        else:
            results.b_wins += 1
        results.kill_turns.append(match.kill_turn)

    results.avg_turns = sum(results.kill_turns) / n if n else 0
    return results
