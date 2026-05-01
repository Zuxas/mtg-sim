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
    attacker_deaths:     list = field(default_factory=list)
    defender_deaths:     list = field(default_factory=list)


def resolve_combat(attackers: list[Card],
                   blocker_assignments: dict,
                   attacking_player: str,
                   mgs: MatchGameState) -> CombatResult:
    """
    Resolve combat with keyword support.
    
    blocker_assignments: {id(attacker_card): [list of blocker cards]}
    Cards not in the dict are unblocked.
    """
    result = CombatResult()
    damage_taken = {}  # id(card) -> damage received

    def deal_strike(strike_attackers, is_first_strike=False):
        for atk in strike_attackers:
            atk_pwr = safe_power(atk)
            atk_deathtouch = has_keyword(atk, 'deathtouch')
            atk_trample = has_keyword(atk, 'trample')
            atk_lifelink = has_keyword(atk, 'lifelink')

            blockers = blocker_assignments.get(id(atk), [])

            if not blockers:
                # Unblocked — all damage to defending player
                result.damage_to_defender += atk_pwr
                if atk_lifelink:
                    result.life_gained_attacker += atk_pwr
            else:
                # Blocked — distribute damage among blockers
                remaining_power = atk_pwr
                for blk in blockers:
                    blk_tou = safe_toughness(blk) - damage_taken.get(id(blk), 0)
                    if blk_tou <= 0:
                        continue
                    if atk_deathtouch:
                        # Deathtouch: 1 damage is lethal
                        dmg_to_blk = 1
                    else:
                        dmg_to_blk = min(remaining_power, blk_tou)
                    damage_taken[id(blk)] = damage_taken.get(id(blk), 0) + dmg_to_blk
                    remaining_power -= dmg_to_blk
                    if remaining_power <= 0:
                        break

                # Trample: excess damage goes to player
                if atk_trample and remaining_power > 0:
                    result.damage_to_defender += remaining_power
                    if atk_lifelink:
                        result.life_gained_attacker += remaining_power
                elif atk_lifelink and remaining_power <= 0:
                    # Lifelink from damage dealt to blockers
                    result.life_gained_attacker += (atk_pwr - remaining_power)

                # Blocker damages attacker
                for blk in blockers:
                    blk_pwr = safe_power(blk)
                    blk_deathtouch = has_keyword(blk, 'deathtouch')
                    if blk_deathtouch:
                        damage_taken[id(atk)] = 9999  # lethal
                    else:
                        damage_taken[id(atk)] = damage_taken.get(id(atk), 0) + blk_pwr

    # --- First strike damage step ---
    first_strikers = [a for a in attackers
                      if has_keyword(a, 'first strike') or has_keyword(a, 'double strike')]
    if first_strikers:
        deal_strike(first_strikers, is_first_strike=True)
        # Remove creatures that died to first strike before regular damage
        for card_id, dmg in list(damage_taken.items()):
            card = _find_by_id(card_id, attackers, blocker_assignments)
            if card and dmg >= safe_toughness(card):
                if card in attackers:
                    result.attacker_deaths.append(card)
                else:
                    result.defender_deaths.append(card)

    # --- Regular damage step ---
    regular_strikers = [a for a in attackers
                        if a not in result.attacker_deaths
                        and (not has_keyword(a, 'first strike')
                             or has_keyword(a, 'double strike'))]
    deal_strike(regular_strikers)

    # --- Process deaths ---
    all_creatures = list(attackers)
    for blk_list in blocker_assignments.values():
        all_creatures.extend(blk_list)

    for card in all_creatures:
        if card in result.attacker_deaths or card in result.defender_deaths:
            continue
        dmg = damage_taken.get(id(card), 0)
        if dmg >= safe_toughness(card):
            if card in attackers:
                result.attacker_deaths.append(card)
            else:
                result.defender_deaths.append(card)

    return result


def _find_by_id(card_id, attackers, assignments):
    """Find a card by its id() across attackers and blockers."""
    for c in attackers:
        if id(c) == card_id:
            return c
    for blk_list in assignments.values():
        for c in blk_list:
            if id(c) == card_id:
                return c
    return None


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
