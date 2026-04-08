"""
engine/combat.py — Realistic combat resolver with blocking

Simulates combat between our attackers and opponent's blockers.
Used to convert goldfish kill distributions into realistic racing distributions.

Blocking strategy (opponent plays optimally):
  - Biggest opponent creature blocks our biggest attacker (minimize damage)
  - Remaining attackers deal unblocked damage
  - Creatures with lethal damage die
  - Tracks both boards turn by turn
"""

import random
from collections import defaultdict
from engine.opponent import OPPONENT_PROFILES


def get_opp_profile(archetype_key: str) -> dict:
    """Get opponent profile, falling back to unknown."""
    key = archetype_key.lower()
    if key in OPPONENT_PROFILES:
        return OPPONENT_PROFILES[key]
    # Partial match
    for k in OPPONENT_PROFILES:
        if k in key or key in k:
            return OPPONENT_PROFILES[k]
    return OPPONENT_PROFILES["unknown"]


def resolve_combat_turn(our_attackers, opp_blockers):
    """
    Resolve one combat step.

    our_attackers: list of [power, toughness] (mutable)
    opp_blockers:  list of [power, toughness] (mutable)

    Returns:
        damage_dealt: int  (unblocked damage + trample etc.)
        our_losses:   list of indices in our_attackers that die
        opp_losses:   list of indices in opp_blockers that die
    """
    # Sort both: opponent blocks biggest with biggest
    atk_sorted = sorted(enumerate(our_attackers), key=lambda x: -x[1][0])
    blk_sorted = sorted(enumerate(opp_blockers),  key=lambda x: -x[1][0])

    our_losses = []
    opp_losses = []
    damage_dealt = 0

    assigned_blocks = {}  # attacker_idx → blocker_idx

    # Assign blocks greedily: biggest blocker → biggest attacker
    blk_iter = iter(blk_sorted)
    for atk_idx, atk in atk_sorted:
        try:
            blk_idx, blk = next(blk_iter)
            assigned_blocks[atk_idx] = blk_idx
        except StopIteration:
            break

    # Resolve damage
    for atk_idx, atk in our_attackers:
        if atk_idx in assigned_blocks:
            blk_idx = assigned_blocks[atk_idx]
            blk = opp_blockers[blk_idx]

            # Mutual damage
            atk_pwr, atk_tou = atk
            blk_pwr, blk_tou = blk

            # Does blocker die?
            if atk_pwr >= blk_tou:
                opp_losses.append(blk_idx)
            # Does attacker die?
            if blk_pwr >= atk_tou:
                our_losses.append(atk_idx)
        else:
            # Unblocked — deal damage
            damage_dealt += our_attackers[atk_idx][0] if isinstance(our_attackers[atk_idx], list) else our_attackers[atk_idx]

    return damage_dealt, set(our_losses), set(opp_losses)


class CombatSimulator:
    """
    Simulates a full game with blocking.

    Each turn:
    1. Opponent plays creatures from their curve
    2. Opponent may remove one of our creatures (removal_per_turn probability)
    3. We attack with all non-summoning-sick creatures
    4. Opponent assigns optimal blocks
    5. Combat resolves, dead creatures removed from both sides
    6. Track cumulative damage

    Returns kill turn distribution across N simulations.
    """

    def __init__(self, archetype_key: str, seed: int = None):
        self.profile = get_opp_profile(archetype_key)
        self.rng     = random.Random(seed)

    def simulate_game(
        self,
        our_kill_dist:  dict,    # {turn: pct} — our goldfish kill distribution
        max_turns:      int = 15,
        on_play:        bool = True,
    ) -> int:
        """
        Simulate one game. Returns the actual kill turn (or max_turns if we lost).
        Samples our action from the kill distribution, then applies blocking losses.
        """
        # Sample our "ideal" kill turn from goldfish distribution
        turns = sorted(our_kill_dist.keys())
        weights = [our_kill_dist[t] for t in turns]
        total = sum(weights)
        r = self.rng.random() * total
        cumulative = 0
        ideal_kill_turn = turns[-1]
        for t, w in zip(turns, weights):
            cumulative += w
            if r <= cumulative:
                ideal_kill_turn = t
                break

        # Check if it's a combo matchup — they kill before we can
        combo_turns = self.profile.get("combo_kill_turns")
        if combo_turns:
            opp_turns = sorted(combo_turns.keys())
            opp_weights = [combo_turns[t] for t in opp_turns]
            opp_total = sum(opp_weights)
            r2 = self.rng.random() * opp_total
            cumulative2 = 0
            opp_kill_turn = opp_turns[-1]
            for t, w in zip(opp_turns, opp_weights):
                cumulative2 += w
                if r2 <= cumulative2:
                    opp_kill_turn = t
                    break

            # If they kill before us, we lose
            draw_adj = 0 if on_play else 1
            if opp_kill_turn + draw_adj <= ideal_kill_turn:
                return max_turns + 1  # loss

        # Simulate blocking — how many extra turns does blocking add?
        our_board  = []   # [[power, toughness], ...]
        opp_board  = []
        damage     = 0
        removal_pct = self.profile.get("removal_per_turn", 0.0)
        curve = self.profile.get("curve", {})

        extra_turns = 0

        for turn in range(1, max_turns + 1):
            # Opponent plays creatures
            opp_plays = curve.get(turn, [])
            for p, t in opp_plays:
                opp_board.append([p, t])

            # Opponent removes one of our creatures (simplified: random removal)
            if our_board and self.rng.random() < removal_pct:
                victim_idx = self.rng.randint(0, len(our_board) - 1)
                our_board.pop(victim_idx)

            # We attack with all creatures (simplified: all attack)
            if not our_board:
                # Add a generic attacker based on our kill dist
                our_power = max(1, 20 // max(1, ideal_kill_turn))
                our_board.append([our_power, our_power])

            # Simple combat resolve
            opp_alive = list(opp_board)
            our_alive  = list(our_board)

            unblocked_dmg = 0
            our_died  = []
            opp_died  = []

            # Sort: biggest blocker blocks biggest attacker
            atk = sorted(range(len(our_alive)), key=lambda i: -our_alive[i][0])
            blk = sorted(range(len(opp_alive)), key=lambda i: -opp_alive[i][0])
            blk_iter = iter(blk)

            for atk_i in atk:
                a_pwr, a_tou = our_alive[atk_i]
                try:
                    blk_i = next(blk_iter)
                    b_pwr, b_tou = opp_alive[blk_i]
                    if a_pwr >= b_tou:
                        opp_died.append(blk_i)
                    if b_pwr >= a_tou:
                        our_died.append(atk_i)
                except StopIteration:
                    unblocked_dmg += a_pwr

            damage += unblocked_dmg

            # Remove dead creatures
            opp_board = [c for i, c in enumerate(opp_alive) if i not in opp_died]
            our_board = [c for i, c in enumerate(our_alive) if i not in our_died]

            if damage >= 20:
                return turn

        return max_turns + 1   # loss

    def simulate_n(
        self,
        our_kill_dist: dict,
        n:             int = 5000,
        on_play:       bool = True,
    ) -> dict:
        """Run N games and return kill turn distribution."""
        dist = defaultdict(int)
        for _ in range(n):
            kill_turn = self.simulate_game(our_kill_dist, on_play=on_play)
            dist[kill_turn] += 1

        total = sum(dist.values())
        return {t: round(count / total * 100, 2)
                for t, count in sorted(dist.items())
                if t <= 15}  # cap at 15 — beyond is a loss


def realistic_win_pct(
    our_kill_dist:  dict,
    opp_archetype:  str,
    n:              int  = 5000,
    on_play:        bool = True,
    seed:           int  = 42,
) -> float:
    """
    One-shot: get realistic win% for our deck vs an opponent archetype.
    Accounts for blocking and removal — more accurate than pure goldfish race.
    """
    from sim_bridge import _infer_archetype_key
    arch_key = _infer_archetype_key(opp_archetype)
    sim = CombatSimulator(arch_key, seed=seed)
    dist = sim.simulate_n(our_kill_dist, n=n, on_play=on_play)

    # Win = kill on turn 1-15
    win_pcts = sum(v for t, v in dist.items() if t <= 15)
    return round(win_pcts, 1)
