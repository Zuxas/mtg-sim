"""
mine_lethal_puzzles.py -- Puzzle Trainer v0 Track T2 (goldfish slice).

Mines "you have lethal THIS turn -- find the line" positions out of goldfish
games. Honest by construction:

  * Environment is goldfish (real deck vs an open board at `win_damage`), so a
    power-sum lethal is not blocker-blind -- there is no blocker. The lethality
    ORACLE is the engine's own combat step run on a throwaway fork
    (`fork.run_combat()` then `has_won`), NOT the miner re-summing power. That
    keeps the T2-G1 replay gate independent of the search's own arithmetic.
  * A position is a PUZZLE only if the lethal DEPENDS ON a specific main-phase
    play (a cast / land / sequence) -- not "swing the board you already have."
    Positions that are already lethal with zero plays are skipped as trivial
    (that is an attack-step question, not a sequencing puzzle). This filter is
    the user's "the winning line isn't the obvious one."

Boundaries (v0): single-turn KILL only ("how do I win from here"); NOT the
"slow them down / grind" stabilize third. Goldfish, not gauntlet -- the same
pipeline (search -> Scene export -> JSONL bridge -> replay gate) drops onto the
gauntlet next by swapping the driver + adding a no-blocker filter.

Usage:
    python scripts/mine_lethal_puzzles.py --deck decks/boros_energy_modern.txt \\
        --games 500 --seed 42 --out data/lethal_candidates.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.deck import load_deck_from_file
from apl import get_apl
from engine.runner import run_simulation
from engine.decision_api import legal_main_actions, apply_action, fork

# node budget for the per-position bounded search (documented cap)
_SEARCH_NODE_BUDGET = 500
# cap main-phase plays considered in one line (depth guard)
_MAX_LINE_DEPTH = 8


# ── independent lethality oracle ────────────────────────────────────────

def _lethal_after_combat(gs, win_damage: int) -> bool:
    """Run the engine's REAL combat on a throwaway fork and read the win
    condition. Independent of the search's own power math (T2-G1)."""
    g2, _ = fork(gs, None)
    try:
        g2.run_combat()
    except Exception:
        return False
    return bool(g2.has_won(win_damage))


def _tapped_fork(gs):
    """Fork and make mana available (tap_lands) so legal_main_actions sees a
    full pool -- mirrors what an APL does at the top of its main phase."""
    g2, _ = fork(gs, None)
    try:
        g2.tap_lands()
    except Exception:
        pass
    return g2


def _ordered_actions(gs) -> list:
    """Deterministic action order: lands first (enable mana), then casts by
    (cmc, name). Determinism is a T2-G3 precondition, so no set-iteration."""
    acts = [a for a in legal_main_actions(gs) if a.kind != "PASS"]
    def _key(a):
        cmc = getattr(a.card_ref, "cmc", 0) or 0
        return (0 if a.kind == "PLAY_LAND" else 1, float(cmc), a.card_name)
    return sorted(acts, key=_key)


def _search_lethal_line(gs_tapped, win_damage: int, budget: list) -> list | None:
    """Bounded DFS for a main-phase line that turns this turn lethal. Returns
    the list of action labels (>=1 play) or None. The empty line (already
    lethal) is handled by the caller's trivial check, so the root requires a
    play before it will accept lethality."""

    def _dfs(gs, depth) -> list | None:
        if _lethal_after_combat(gs, win_damage):
            return []                      # lethal reached at this node
        if depth >= _MAX_LINE_DEPTH:
            return None
        for a in _ordered_actions(gs):
            if budget[0] <= 0:
                return None
            budget[0] -= 1
            g2, _ = fork(gs, None)
            if not apply_action(g2, a):
                continue
            sub = _dfs(g2, depth + 1)
            if sub is not None:
                label = a.card_name or a.kind
                return [f"{a.kind}:{label}" if a.kind == "PLAY_LAND"
                        else label] + sub
        return None

    # root: every accepted line must include >=1 real play
    for a in _ordered_actions(gs_tapped):
        if budget[0] <= 0:
            return None
        budget[0] -= 1
        g2, _ = fork(gs_tapped, None)
        if not apply_action(g2, a):
            continue
        sub = _dfs(g2, 1)
        if sub is not None:
            label = a.card_name or a.kind
            head = f"{a.kind}:{label}" if a.kind == "PLAY_LAND" else label
            return [head] + sub
    return None


# ── Scene serialization (one-way: GameState -> analyzer Scene dict) ──────

def _card_dict(c) -> dict:
    def _num(x):
        try:
            return int(float(str(x)))
        except (TypeError, ValueError):
            return None
    return {
        "name": getattr(c, "name", "?"),
        "power": _num(getattr(c, "power", None)),
        "toughness": _num(getattr(c, "toughness", None)),
        "tapped": bool(getattr(c, "tapped", False)),
    }


def _serialize_scene(gs, deck_name: str, turn_num: int,
                     win_damage: int) -> dict:
    """Emit a dict matching the analyzer's Scene.to_dict() shape (no analyzer
    import -- mtg-sim stays standalone)."""
    bf = list(getattr(gs.zones, "battlefield", []) or [])
    lands = [c for c in bf if c.is_land()]
    creatures = [c for c in bf if not c.is_land()]
    hand = list(getattr(gs.zones, "hand", []) or [])
    remaining = max(0, win_damage - int(getattr(gs, "damage_dealt", 0) or 0))
    you = {
        "name": "You", "archetype": deck_name,
        "life": int(getattr(gs, "life", 20) or 20),
        "hand": [_card_dict(c) for c in hand],
        "battlefield_lands": [_card_dict(c) for c in lands],
        "battlefield_creatures": [_card_dict(c) for c in creatures],
        "battlefield_other": [],
        "graveyard_count": len(getattr(gs.zones, "graveyard", []) or []),
        "library_count": len(getattr(gs.zones, "library", []) or []),
        "mana_available": {},
    }
    opp = {
        "name": "Goldfish", "archetype": "open board",
        "life": remaining, "hand": [], "battlefield_lands": [],
        "battlefield_creatures": [], "battlefield_other": [],
        "graveyard_count": 0, "library_count": 0, "mana_available": {},
    }
    return {
        "arena_match_id": "", "game_num": 0, "turn_num": turn_num,
        "play_or_draw": "play", "you": you, "opp": opp,
        "notes": (f"Goldfish position, turn {turn_num}. Opponent is an open "
                  f"board at {remaining} (lethal accounts for no blockers)."),
    }


# ── the miner ───────────────────────────────────────────────────────────

class _Miner:
    def __init__(self, deck_name: str, win_damage: int):
        self.deck_name = deck_name
        self.win_damage = win_damage
        self.candidates: list[dict] = []
        self._game_idx = 0
        self._found_this_game = False

    def new_game(self):
        self._game_idx += 1
        self._found_this_game = False

    def analyze(self, gs):
        """Called at main-phase entry, BEFORE the real APL plays. Records the
        first play-dependent lethal position per game."""
        if self._found_this_game:
            return
        turn_num = int(getattr(gs, "turn", 0) or 0)
        probe = _tapped_fork(gs)
        # trivial: already lethal with zero main-phase plays -> not a puzzle
        if _lethal_after_combat(probe, self.win_damage):
            return
        budget = [_SEARCH_NODE_BUDGET]
        line = _search_lethal_line(probe, self.win_damage, budget)
        if not line:
            return
        # T2-G1 self-verify: replay the line on a fresh fork -> must reach lethal
        if not self._replays_to_lethal(gs, line):
            return
        greedy_misses = not self._greedy_finds_lethal(gs)
        scene = _serialize_scene(gs, self.deck_name, turn_num, self.win_damage)
        self.candidates.append({
            "arena_match_id": f"goldfish:{self.deck_name}:{self._game_idx}",
            "game_num": self._game_idx,
            "turn_num": turn_num,
            "category": "find_lethal",
            "heuristic_score": round(2.0 + (1.0 if greedy_misses else 0.0)
                                     + 0.1 * len(line), 3),
            "solution_line": line,
            "scene": scene,
            "greedy_misses": greedy_misses,
            "caveats": ["goldfish: opponent is an open board (no blockers, no "
                        "instant-speed interaction modeled)"],
        })
        self._found_this_game = True

    def _replays_to_lethal(self, gs, line: list) -> bool:
        """Independent replay: apply the recorded labels on a fresh tapped fork
        and confirm run_combat wins. Labels are 'KIND:name' for lands or the
        card name for casts."""
        g = _tapped_fork(gs)
        for step in line:
            kind, _, name = step.partition(":")
            if kind == "PLAY_LAND":
                target = name
            else:
                kind, target = "CAST", step
            acts = {(a.kind, a.card_name): a for a in legal_main_actions(g)}
            act = acts.get((kind, target))
            if act is None or not apply_action(g, act):
                return False
        return _lethal_after_combat(g, self.win_damage)

    def _greedy_finds_lethal(self, gs) -> bool:
        """Cheapest-first completion (the 'obvious' line). If THIS finds lethal
        too, the puzzle is less interesting (ranked lower)."""
        g = _tapped_fork(gs)
        for _ in range(_MAX_LINE_DEPTH):
            if _lethal_after_combat(g, self.win_damage):
                return True
            acts = _ordered_actions(g)
            if not acts:
                break
            if not apply_action(g, acts[0]):
                break
        return _lethal_after_combat(g, self.win_damage)


def _install_hook(apl, miner: _Miner):
    """Wrap the instance's main_phase so the miner sees each position before
    the real play line runs. Also reset per-game state via run_game wrapper."""
    orig_main = apl.main_phase
    orig_run_game = apl.run_game

    def hooked_main(gs):
        try:
            miner.analyze(gs)
        except Exception:
            pass  # mining must never perturb the real game
        return orig_main(gs)

    def hooked_run_game(*a, **k):
        miner.new_game()
        return orig_run_game(*a, **k)

    apl.main_phase = hooked_main
    apl.run_game = hooked_run_game


def mine(deck_path: str, games: int, seed: int, win_damage: int) -> list[dict]:
    mainboard, _sideboard = load_deck_from_file(deck_path)
    base = os.path.basename(deck_path)
    key = base
    for ext in (".txt", ".dec", ".dek"):
        if key.lower().endswith(ext):
            key = key[: -len(ext)]
    for suf in ("_modern", "_legacy", "_pioneer", "_standard", "_vintage",
                "_pauper"):
        if key.endswith(suf):
            key = key[: -len(suf)]
    apl = get_apl(key) or get_apl("humans")
    deck_name = key
    miner = _Miner(deck_name, win_damage)
    _install_hook(apl, miner)
    run_simulation(apl, mainboard, n=games, on_play=True, seed=seed)
    return miner.candidates


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mine goldfish lethal puzzles.")
    ap.add_argument("--deck", required=True)
    ap.add_argument("--games", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--win-damage", type=int, default=20)
    ap.add_argument("--out", default="data/lethal_candidates.jsonl")
    args = ap.parse_args(argv)

    cands = mine(args.deck, args.games, args.seed, args.win_damage)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for c in cands:
            f.write(json.dumps(c) + "\n")

    misses = sum(1 for c in cands if c.get("greedy_misses"))
    print(f"Mined {len(cands)} candidates from {args.games} games "
          f"(seed {args.seed}, win_damage {args.win_damage}).")
    print(f"  {misses} require non-obvious sequencing (greedy line misses "
          f"lethal); {len(cands) - misses} findable by cheapest-first.")
    print(f"  Written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
