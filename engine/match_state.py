"""
engine/match_state.py — Two-player game state for matchup simulation

Wraps two GameState instances (one per player) + shared match state.
This is the core data structure for Phase 3: real matchup simulation.

Design principle: DON'T rebuild the engine. Each player gets a real
GameState with all existing mechanics (ETB, prowess, fetch lands,
summoning sickness). The match layer orchestrates turn alternation
and adds new concepts (opponent life tracking, combat interaction).
"""

from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Optional

from engine.game_state import GameState, Phase
from data.card import Card, Tag


@dataclass
class MatchResult:
    """Result of a single match between two decks."""
    winner:        str   = ''       # 'a' or 'b'
    kill_turn:     int   = 0
    turn_count:    int   = 0
    final_life_a:  int   = 20
    final_life_b:  int   = 20
    mulligans_a:   int   = 0
    mulligans_b:   int   = 0
    damage_by_a:   int   = 0
    damage_by_b:   int   = 0
    win_method:    str   = ''       # 'combat', 'combo', 'timeout'
    # Opening hands (card names) snapshotted after mulligans. Set by run_match.
    hand_a:        list  = field(default_factory=list)
    hand_b:        list  = field(default_factory=list)


@dataclass
class MatchSetResults:
    """Aggregated results from N matches."""
    n_games:     int   = 0
    a_wins:      int   = 0
    b_wins:      int   = 0
    avg_turns:   float = 0.0
    kill_turns:  list  = field(default_factory=list)
    results:     list  = field(default_factory=list)  # list of MatchResult

    def win_rate_a(self) -> float:
        return self.a_wins / self.n_games if self.n_games else 0.0

    def win_pct_a(self) -> float:
        return round(self.win_rate_a() * 100, 1)

    # Backwards-compatible aliases used by match_runner / goldfish callers
    def win_rate(self) -> float:
        return self.win_rate_a()

    def win_pct(self) -> float:
        return self.win_pct_a()

    def avg_kill_turn(self) -> float:
        return self.avg_turns

    def kill_turn_distribution(self) -> dict:
        dist = {}
        for t in self.kill_turns:
            dist[t] = dist.get(t, 0) + 1
        total = len(self.kill_turns)
        return {t: round(c / total * 100, 2)
                for t, c in sorted(dist.items())} if total else {}

    def play_draw_split(self) -> dict:
        """Win rate on the play vs on the draw."""
        play_w = sum(1 for r in self.results if r.winner == 'a' and r._on_play)
        play_n = sum(1 for r in self.results if r._on_play)
        draw_w = sum(1 for r in self.results if r.winner == 'a' and not r._on_play)
        draw_n = sum(1 for r in self.results if not r._on_play)
        return {
            'on_play': round(play_w / play_n * 100, 1) if play_n else 0,
            'on_draw': round(draw_w / draw_n * 100, 1) if draw_n else 0,
        }


class MatchGameState:
    """
    Two-player game state wrapping two GameState instances.
    
    Each player gets the FULL goldfish engine (ETB triggers, prowess,
    fetch/shock lands, summoning sickness, etc.). The match layer adds:
    - Turn alternation (active player / reactive player)
    - Opponent life tracking (damage_dealt on gs_a maps to life on gs_b)
    - Combat interaction (blocking, removal targeting)
    - Shared turn counter
    """

    def __init__(self, deck_a: list, deck_b: list,
                 on_play: bool = True, seed: int = None):
        self.rng = random.Random(seed)

        # Each player gets a full GameState with all mechanics
        self.gs_a = GameState(list(deck_a), on_play=True)
        self.gs_b = GameState(list(deck_b), on_play=False)

        # Copy mainboard into library (goldfish engine does this in run_game)
        from copy import deepcopy
        self.gs_a.zones.library = deepcopy(self.gs_a.mainboard)
        self.gs_b.zones.library = deepcopy(self.gs_b.mainboard)

        # Shuffle libraries
        self.rng.shuffle(self.gs_a.zones.library)
        self.rng.shuffle(self.gs_b.zones.library)

        # Match-level state
        self.turn = 0
        self.on_play = on_play          # True = player A goes first
        self.active_player = 'a'        # whose turn it is right now
        self.game_over = False
        self.winner = None
        self.win_method = ''

    # -- Convenience accessors --

    def active_gs(self) -> GameState:
        return self.gs_a if self.active_player == 'a' else self.gs_b

    def reactive_gs(self) -> GameState:
        return self.gs_b if self.active_player == 'a' else self.gs_a

    def opponent_life(self, player: str) -> int:
        """How much life does the opponent of `player` have?"""
        opp = self.gs_b if player == 'a' else self.gs_a
        return opp.life

    def deal_damage(self, source_player: str, amount: int):
        """Deal damage from source_player to their opponent."""
        if amount <= 0:
            return
        opp = self.gs_b if source_player == 'a' else self.gs_a
        opp.life -= amount
        src = self.gs_a if source_player == 'a' else self.gs_b
        src.damage_dealt += amount
        if opp.life <= 0:
            self.game_over = True
            self.winner = source_player
            self.win_method = 'combat'

    def gain_life(self, player: str, amount: int):
        """Player gains life (from lifelink, etc.)."""
        gs = self.gs_a if player == 'a' else self.gs_b
        gs.life += amount

    def creatures(self, player: str) -> list[Card]:
        """Non-land permanents on player's battlefield."""
        gs = self.gs_a if player == 'a' else self.gs_b
        return [c for c in gs.zones.battlefield if not c.is_land()]

    def attackable_creatures(self, player: str) -> list[Card]:
        """Creatures that can attack (not summoning sick, not tapped)."""
        return [c for c in self.creatures(player)
                if not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def blocking_creatures(self, player: str) -> list[Card]:
        """Creatures that can block (not tapped)."""
        return [c for c in self.creatures(player)
                if not getattr(c, 'tapped', False)]

    def total_power(self, player: str) -> int:
        """Total attacking power available."""
        return sum(safe_power(c) for c in self.attackable_creatures(player))

    def clock(self, player: str) -> int:
        """Estimated turns to lethal for this player."""
        power = self.total_power(player)
        opp_life = self.opponent_life(player)
        if power <= 0:
            return 99
        return max(1, -(-opp_life // power))  # ceiling division

    def to_match_result(self) -> MatchResult:
        return MatchResult(
            winner=self.winner or '',
            kill_turn=self.turn,
            turn_count=self.turn,
            final_life_a=self.gs_a.life,
            final_life_b=self.gs_b.life,
            mulligans_a=0,  # filled by caller
            mulligans_b=0,
            damage_by_a=self.gs_a.damage_dealt,
            damage_by_b=self.gs_b.damage_dealt,
            win_method=self.win_method,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_power(card: Card) -> int:
    """Safely get a card's power as int, handling '*' and None."""
    try:
        ep = getattr(card, 'effective_power', None)
        if callable(ep):
            return ep()
        p = card.power
        if p is None or p == '*':
            return 2
        return int(p)
    except Exception:
        return 0


def safe_toughness(card: Card) -> int:
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


def has_keyword(card: Card, keyword: str) -> bool:
    """Check if a card has a keyword ability.

    Checks card.tags first (populated by tag_keywords() at deck load; KWTag
    values use underscores so 'first strike' -> 'first_strike').  Falls back
    to oracle_text for keywords not covered by KWTag (e.g. double strike).
    """
    tags = getattr(card, 'tags', None)
    if tags:
        if keyword.lower().replace(' ', '_') in tags:
            return True
    oracle = getattr(card, 'oracle_text', '') or ''
    return keyword.lower() in oracle.lower()


# Conditional evasion registry. Key = attacker card name; value = a
# predicate (attacker, blocker) -> bool that returns True when the
# blocker is legal against this specific attacker's evasion rule.
# Checked AFTER the generic flying filter in optimal_blocking.
_CONDITIONAL_EVASION = {
    # Elusive Otter: "Creatures with power less than this creature's
    # power can't block it." — blocker must have power >= attacker.
    "Elusive Otter": lambda atk, blk: safe_power(blk) >= safe_power(atk),
}


# ---------------------------------------------------------------------------
# Combat Resolution — Phase 3A upgrade with keyword support
# ---------------------------------------------------------------------------

@dataclass
class CombatResult:
    """Result of one combat step."""
    damage_to_defender:  int  = 0
    life_gained_attacker: int = 0   # from lifelink
    life_gained_defender: int = 0   # from lifelink on blockers
    attacker_deaths:     list = field(default_factory=list)
    defender_deaths:     list = field(default_factory=list)


@dataclass
class DamageResult:
    """Outcome of combat_damage()."""
    face:              int  = 0   # combat damage to the defending player
    attacker_lifelink: int  = 0
    defender_lifelink: int  = 0
    hits_on_player:    int  = 0   # damage events on the player (double strike = 2)
    dead_attackers:    list = field(default_factory=list)
    dead_blockers:     list = field(default_factory=list)


def combat_damage(attackers, assignments, has=None, divert=None,
                  defender_life=None) -> DamageResult:
    """Combat damage for both match engines (CR 510, issue #13).

    assignments: {id(attacker): [blockers]}; missing or empty = unblocked.
    has(card, keyword): keyword test, names as printed ('first strike').
    divert(attacker, power): optional. Return the damage an UNBLOCKED attacker
        deals somewhere other than the player (a planeswalker), or None to
        hit the player as usual.
    defender_life: the defending player's life. If the first-strike step
        leaves them at 0 or less the game is over, so the regular step is
        not dealt (no late lifelink rescue, no extra damage or triggers).

    Two damage steps. In each, every creature that strikes in that step --
    attackers AND blockers -- deals damage at once, then lethal damage is
    checked. A creature killed in the first-strike step deals nothing in the
    regular step. An attacker that was blocked stays blocked when its blockers
    die: it deals no damage unless it has trample (CR 510.1c). Lifelink counts
    all damage dealt. Marked damage carries from the first step to the second.
    """
    has = has or has_keyword
    res = DamageResult()
    marked, touched, dead = {}, set(), set()   # id -> damage, deathtouched ids, dead ids
    blocked = {id(a): list(assignments.get(id(a)) or []) for a in attackers}

    def strikes(c, first):
        fs, ds = has(c, 'first strike'), has(c, 'double strike')
        return (fs or ds) if first else (ds or not fs)

    def mark(src, tgt, n):
        if n > 0:
            marked[id(tgt)] = marked.get(id(tgt), 0) + n
            if has(src, 'deathtouch'):
                touched.add(id(tgt))

    for first in (True, False):
        for atk in attackers:
            if id(atk) in dead:
                continue
            live = [b for b in blocked[id(atk)] if id(b) not in dead]
            pwr = safe_power(atk)
            if strikes(atk, first) and pwr > 0:
                left = pwr
                if not blocked[id(atk)]:
                    diverted = divert(atk, pwr) if divert else None
                    if diverted is None:
                        res.face += pwr
                        res.hits_on_player += 1
                        left = 0
                    else:
                        left = pwr - diverted
                else:
                    trample = has(atk, 'trample')
                    dt = has(atk, 'deathtouch')
                    for n_blk, blk in enumerate(live):
                        lethal = 1 if dt else max(
                            safe_toughness(blk) - marked.get(id(blk), 0), 1)
                        last = n_blk == len(live) - 1 and not trample
                        n = left if last else min(left, lethal)
                        mark(atk, blk, n)
                        left -= n
                        if left <= 0:
                            break
                    if trample and left > 0:
                        res.face += left
                        res.hits_on_player += 1
                        left = 0
                if has(atk, 'lifelink'):
                    res.attacker_lifelink += pwr - left
            for blk in live:
                if strikes(blk, first):
                    n = safe_power(blk)
                    mark(blk, atk, n)
                    if n > 0 and has(blk, 'lifelink'):
                        res.defender_lifelink += n

        # State-based actions between the two steps and after the second
        for group, out in ((attackers, res.dead_attackers),
                           ([b for bl in blocked.values() for b in bl], res.dead_blockers)):
            for c in group:
                m = marked.get(id(c), 0)
                if (id(c) not in dead and m > 0 and not has(c, 'indestructible')
                        and (m >= safe_toughness(c) or id(c) in touched)):
                    dead.add(id(c))
                    out.append(c)
        if (first and defender_life is not None
                and defender_life + res.defender_lifelink - res.face <= 0):
            break
    return res


def resolve_combat(attackers: list[Card],
                   blocker_assignments: dict,
                   attacking_player: str,
                   mgs: MatchGameState) -> CombatResult:
    """
    Resolve combat with keyword support. Thin wrapper over combat_damage().

    blocker_assignments: {id(attacker_card): [list of blocker cards]}
    Cards not in the dict are unblocked.
    """
    defender = (mgs.gs_b if attacking_player == 'a' else mgs.gs_a) if mgs else None
    r = combat_damage(attackers, blocker_assignments,
                      defender_life=defender.life if defender else None)
    return CombatResult(damage_to_defender=r.face,
                        life_gained_attacker=r.attacker_lifelink,
                        life_gained_defender=r.defender_lifelink,
                        attacker_deaths=r.dead_attackers,
                        defender_deaths=r.dead_blockers)


# ---------------------------------------------------------------------------
# Smart Blocking Algorithm
# ---------------------------------------------------------------------------

def optimal_blocking(blockers: list[Card], attackers: list[Card],
                     defender_life: int, attacker_clock: int) -> dict:
    """
    Compute optimal blocking assignments. Returns {attacker: [blockers]}.
    
    Strategy priorities:
    1. MUST-BLOCK: if taking all damage is lethal, we must block
    2. PROFITABLE TRADE: our creature kills theirs and vice versa (trade)
    3. EAT SMALL: our big creature eats their small one without dying
    4. CHUMP BLOCK: sacrifice a small creature to prevent big damage (when low life)
    5. NO BLOCK: take the damage (preserve board when ahead or not threatened)
    
    Factors:
    - defender_life: how much life we have (chump more aggressively when low)
    - attacker_clock: how many turns until we kill them (race math)
    """
    assignments = {}  # id(attacker) -> [blockers]
    available_blockers = list(blockers)

    # Calculate total incoming damage if we don't block
    total_incoming = sum(safe_power(a) for a in attackers)
    lethal_incoming = total_incoming >= defender_life

    # Sort attackers by power descending (block the biggest threats first)
    sorted_attackers = sorted(attackers, key=lambda c: -safe_power(c))

    for atk in sorted_attackers:
        if not available_blockers:
            break
        atk_pwr = safe_power(atk)
        atk_tou = safe_toughness(atk)
        atk_flying = has_keyword(atk, 'flying')

        # Filter: can this be blocked? (flying check + per-card
        # conditional evasion)
        valid_blockers = [b for b in available_blockers
                          if not atk_flying
                          or has_keyword(b, 'flying')
                          or has_keyword(b, 'reach')]
        # Conditional evasion registry: attacker-name -> predicate that
        # returns True when a given blocker CAN block the attacker.
        evasion_ok = _CONDITIONAL_EVASION.get(atk.name)
        if evasion_ok:
            valid_blockers = [b for b in valid_blockers
                              if evasion_ok(atk, b)]
        if not valid_blockers:
            continue

        # Find best blocker for this attacker
        best = None
        best_score = -999

        for blk in valid_blockers:
            blk_pwr = safe_power(blk)
            blk_tou = safe_toughness(blk)
            kills_attacker = blk_pwr >= atk_tou or has_keyword(blk, 'deathtouch')
            blk_dies = atk_pwr >= blk_tou or has_keyword(atk, 'deathtouch')

            score = 0
            if kills_attacker and not blk_dies:
                score = 10   # eat for free — always do this
            elif kills_attacker and blk_dies:
                # Trade — good if their creature is bigger/more valuable
                score = 5 + (atk_pwr - blk_pwr)
            elif not kills_attacker and blk_dies:
                # Chump block — only if we're about to die
                if lethal_incoming:
                    score = 2 + atk_pwr  # chump the biggest
                else:
                    score = -5  # bad trade, don't chump when safe
            else:
                # Neither dies — just prevents damage
                score = 1

            if score > best_score:
                best_score = score
                best = blk

        # Only assign block if the score is positive (worth blocking)
        if best and best_score > 0:
            assignments[id(atk)] = [best]
            available_blockers.remove(best)

    return assignments
