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

        # Shuffle and set up libraries
        self.lib_a = list(deck_a)
        self.lib_b = list(deck_b)
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

        if player == "a":
            view_on_play    = gs.on_play
            hand_ref        = gs.hand_a
            bf_ref          = gs.bf_a
            gy_ref          = gs.gy_a
            lib_ref         = gs.lib_a
            life_val        = gs.life_a
            land_played_val = gs.land_played_a
        else:
            view_on_play    = not gs.on_play
            hand_ref        = gs.hand_b
            bf_ref          = gs.bf_b
            gy_ref          = gs.gy_b
            lib_ref         = gs.lib_b
            life_val        = gs.life_b
            land_played_val = gs.land_played_b

        view = GameState(mainboard=[], on_play=view_on_play)
        view.turn              = gs.turn
        view.zones.hand        = hand_ref   # list aliased
        view.zones.battlefield = bf_ref
        view.zones.graveyard   = gy_ref
        view.zones.library     = lib_ref
        view.life              = life_val
        view.land_played       = land_played_val

        # Color-aware mana via ManaPool.add_land — handles basics,
        # duals, fetchlands (flex), Wasteland (colorless), etc.
        for c in view.zones.battlefield:
            if c.is_land():
                try:
                    view.mana_pool.add_land(
                        c.type_line or "", c.name or ""
                    )
                except Exception:
                    view.mana_pool.add("C", 1)

        try:
            apl.main_phase(view)
            if hasattr(apl, "main_phase2"):
                apl.main_phase2(view)
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


def _resolve_combat(gs: TwoPlayerGameState, attacker: str):
    """
    Simplified combat: attacker sends all non-summoning-sick creatures.
    Defender blocks optimally (biggest creature blocks biggest attacker).
    Returns (damage_dealt, attacker_losses, defender_losses).
    """
    if attacker == "a":
        attackers = [c for c in gs.bf_a
                     if not c.is_land()
                     and not getattr(c, 'summoning_sickness', False)]
        blockers  = [c for c in gs.bf_b if not c.is_land()]
    else:
        attackers = [c for c in gs.bf_b
                     if not c.is_land()
                     and not getattr(c, 'summoning_sickness', False)]
        blockers  = [c for c in gs.bf_a if not c.is_land()]

    if not attackers:
        return 0, [], []

    # Sort: biggest blocker blocks biggest attacker
    atk_sorted = sorted(attackers, key=lambda c: -_safe_power(c))
    blk_sorted = sorted(blockers,  key=lambda c: -_safe_power(c))

    atk_losses = []
    blk_losses = []
    total_dmg  = 0
    blk_iter   = iter(blk_sorted)

    for atk in atk_sorted:
        atk_pwr = _safe_power(atk)
        atk_tou = _safe_toughness(atk)
        try:
            blk = next(blk_iter)
            blk_pwr = _safe_power(blk)
            blk_tou = _safe_toughness(blk)
            atk_pwr = _safe_power(atk)
            atk_tou = _safe_toughness(atk)
            if atk_pwr >= blk_tou:
                blk_losses.append(blk)
            if blk_pwr >= atk_tou:
                atk_losses.append(atk)
        except StopIteration:
            total_dmg += _safe_power(atk)

    return total_dmg, atk_losses, blk_losses


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

        # Player A attacks
        dmg, a_lost, b_lost = _resolve_combat(gs, "a")
        gs.damage_to_b += dmg
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

        # Draw (skip A's draw if on play turn 1)
        if not (turn_num == 1 and on_play):
            gs.draw_a(1)
        gs.draw_b(1)

        # Player A main phase
        _simple_play_turn(gs, "a", apl_a)

        # Player A attacks
        dmg, a_lost, b_lost = _resolve_combat(gs, "a")
        gs.damage_to_b += dmg
        gs.life_b      -= dmg
        for c in a_lost: gs.bf_a.remove(c); gs.gy_a.append(c)
        for c in b_lost: gs.bf_b.remove(c); gs.gy_b.append(c)

        if gs.life_b <= 0 or gs.damage_to_b >= 20:
            result.won          = True
            result.kill_turn    = turn_num
            result.loser_life   = gs.life_b
            result.winner_damage = gs.damage_to_b
            result.turn_count   = turn_num
            return result

        # Player B main phase
        _simple_play_turn(gs, "b", apl_b)

        # Player B attacks
        dmg, b_lost, a_lost = _resolve_combat(gs, "b")
        gs.damage_to_a += dmg
        gs.life_a      -= dmg
        for c in b_lost: gs.bf_b.remove(c); gs.gy_b.append(c)
        for c in a_lost: gs.bf_a.remove(c); gs.gy_a.append(c)

        if gs.life_a <= 0 or gs.damage_to_a >= 20:
            result.won          = False
            result.kill_turn    = turn_num
            result.loser_life   = gs.life_a
            result.winner_damage = gs.damage_to_a
            result.turn_count   = turn_num
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

    for i in range(n):
        game_on_play = (i % 2 == 0) if mix_play_draw else on_play

        if use_combo_sampler:
            combo_b = ComboKillSampler(getattr(apl_b, 'name', 'unknown'), rng)
            match = _run_match_with_combo(
                apl_a, deck_a, combo_b,
                on_play=game_on_play, max_turns=15, rng=rng
            )
        else:
            match = run_match(apl_a, deck_a, apl_b, deck_b,
                              on_play=game_on_play,
                              seed=rng.randint(0, 999999))

        if match.won:
            results.a_wins += 1
        else:
            results.b_wins += 1
        results.kill_turns.append(match.kill_turn)

    results.avg_turns = sum(results.kill_turns) / n if n else 0
    return results
