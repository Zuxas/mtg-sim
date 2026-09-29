"""
mine_gauntlet_puzzles.py -- "you have lethal THIS turn, find the line" puzzles
mined from real two-player games (our deck vs the modeled field), so every
puzzle carries a REAL opponent board: blockers, permanents, and a hand.

Spec: harness/specs/2026-09-29-gauntlet-lethal-puzzles.md (the T2 real-opponent
follow-on to scripts/mine_lethal_puzzles.py, the goldfish slice).

How it works (no engine edits):
  * `match_runner._run_player_turn` is wrapped IN THIS PROCESS ONLY. At the
    start of each of our turns the whole TwoPlayerGameState is forked
    (deepcopy) and main-phase-1 lines are searched with a scripted pilot.
  * The lethality ORACLE is the engine's own full turn on the fork: draw, main
    1 = the line, combat with the defender's real blocks and response windows,
    main 2 = nothing, win check. Not a power sum.
  * One fork + one engine turn per search node yields both "does this line
    kill" and the legal next actions (decision_api) after it.
  * A position counts only if the kill DEPENDS on a play: the empty line (just
    attack) must not kill.
  * Every recorded line is re-run from a fresh fork before it is kept (G1).

The opponent's hand is exported face-up: the kill is verified against exactly
that hand and the sim opponent's responses, so the puzzle states it.

Usage:
    python scripts/mine_gauntlet_puzzles.py --games-per-opp 50 --seed 42 \\
        --out data/gauntlet_candidates.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from copy import deepcopy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.match_apl import MatchAPL
from data.card import Tag
from engine import match_runner as mr
from engine.decision_api import legal_main_actions, apply_action

_ORIG_TURN = mr._run_player_turn

# documented caps (spec "Search")
OPP_LIFE_CAP = 12          # analyze only when the opponent is at or below this
NODE_BUDGET = 120          # engine turns simulated per position
MAX_DEPTH = 6              # plays in one line

CAVEATS = [
    "engine truth: sim card fidelity and the match-runner combat model (every "
    "eligible creature attacks; defender uses the engine's best-block heuristic; "
    "menace not modeled)",
    "verified against the opponent's revealed hand and the sim opponent's responses",
    "line vocabulary: land drop + spells cast in main phase 1, then combat",
]


def _label(action) -> str:
    return (f"PLAY_LAND:{action.card_name}" if action.kind == "PLAY_LAND"
            else action.card_name)


def _printed_keyword(card, word: str) -> bool:
    """`word` is one of the card's own keyword abilities ("Haste", "Flying,
    haste"); reminder text in parentheses is ignored."""
    import re
    for line in (getattr(card, "oracle_text", "") or "").split("\n"):
        line = re.sub(r"\([^)]*\)", "", line)
        if word in {t.strip().lower() for t in line.split(",")}:
            return True
    return False


def printed_haste(card) -> bool:
    """True only when Haste is one of the card's own keyword abilities. The
    engine's keyword regex also tags cards whose text merely MENTIONS haste --
    Ragavan (dash reminder), Bloodghast (conditional), Emperor of Bones,
    Badgermole Cub -- so a cast of one of those attacking this turn is not a
    trustworthy puzzle answer."""
    return _printed_keyword(card, "haste")


def hand_threats(opp_hand, opp_bf, our_bf) -> list[str]:
    """Cards a REAL opponent could use on our turn that the sim opponent did
    not: instants, flash cards, evoke (a free Solitude/Subtlety), channel.
    Voice of Victory ("your opponents can't cast spells during your turn")
    shuts off every spell; Aether Vial with a creature in hand is an ability
    and still counts."""
    voice = any(c.name == "Voice of Victory" for c in our_bf)
    out = []
    for c in opp_hand:
        text = (getattr(c, "oracle_text", "") or "").lower()
        spell = ("instant" in (getattr(c, "type_line", "") or "").lower()
                 or _printed_keyword(c, "flash") or "evoke" in text)
        if (spell and not voice) or "channel" in text:
            out.append(c.name)
    if any(c.name == "Aether Vial" for c in opp_bf) and \
            any(_is_creature(c) for c in opp_hand):
        out.append("Aether Vial (+ creature in hand)")
    return out


def survives_best_blocks(gs, opponent) -> bool:
    """Conservative check after the line: the opponent's k untapped creatures
    each block one of our k BIGGEST attackers, and the rest must still be
    lethal. Ignores trample and evasion, so it can only under-count us. Voice
    of Victory adds its two mobilize 1/1s. The engine's defender blocks by a
    heuristic, so this keeps only puzzles that don't rely on a weak block."""
    from engine.keywords import KWTag
    powers = []
    for c in gs.zones.battlefield:
        if c.is_land() or not _is_creature(c) or KWTag.DEFENDER in c.tags:
            continue
        if getattr(c, "summoning_sickness", False) and not printed_haste(c):
            continue
        powers.append(max(0, mr._safe_power(c)))
        if c.name == "Voice of Victory":
            powers += [1, 1]
    k = sum(1 for c in opponent.zones.battlefield
            if not c.is_land() and _is_creature(c)
            and not getattr(c, "tapped_from_attack", False)
            and "planeswalker" not in (getattr(c, "type_line", "") or "").lower())
    powers.sort(reverse=True)
    return sum(powers[k:]) >= int(opponent.life)


def _haste_suspect(card) -> bool:
    from engine.keywords import KWTag
    return (_is_creature(card) and KWTag.HASTE in getattr(card, "tags", set())
            and not printed_haste(card))


def _ordered(view) -> list:
    """Deterministic child order: land first (enables mana), casts by (cmc, name)."""
    acts = [a for a in legal_main_actions(view) if a.kind != "PASS"]
    return sorted(acts, key=lambda a: (0 if a.kind == "PLAY_LAND" else 1,
                                       float(getattr(a.card_ref, "cmc", 0) or 0),
                                       a.card_name))


# ---------------------------------------------------------------- scene export

def _is_creature(c) -> bool:
    return Tag.CREATURE in getattr(c, "tags", set()) or \
        "creature" in (getattr(c, "type_line", "") or "").lower()


def _card(c, *, tapped=False, sick=False) -> dict:
    d = {"name": c.name, "tapped": bool(tapped), "summoning_sick": bool(sick)}
    if _is_creature(c):
        d["power"] = mr._safe_power(c)
        d["toughness"] = mr._safe_toughness(c)
    return d


def _side(name, archetype, life, hand, bf, gy, lib, *, hand_known, ours) -> dict:
    lands = [c for c in bf if c.is_land()]
    creatures = [c for c in bf if not c.is_land() and _is_creature(c)]
    other = [c for c in bf if not c.is_land() and not _is_creature(c)]
    return {
        "name": name, "archetype": archetype, "life": int(life),
        "hand": [_card(c) for c in hand] if hand_known else [],
        "hand_count": len(hand),
        # match mode never untaps lands (mana comes from the view), so land
        # tap flags are meaningless -- it is the start of our turn: untapped.
        "battlefield_lands": [_card(c) for c in lands],
        # ours: sickness matters; theirs: attacked last turn -> still tapped
        "battlefield_creatures": [
            _card(c, tapped=(not ours and getattr(c, "tapped_from_attack", False)),
                  sick=(ours and getattr(c, "summoning_sickness", False)))
            for c in creatures],
        "battlefield_other": [_card(c) for c in other],
        "graveyard_count": len(gy), "library_count": len(lib),
        "mana_available": {},
    }


def _scene(view, opp_view, our_name, opp_name, turn_num, on_play) -> dict:
    z, oz = view.zones, opp_view.zones
    you = _side("You", our_name, view.life, z.hand, z.battlefield, z.graveyard,
                z.library, hand_known=True, ours=True)
    opp = _side(opp_name, opp_name, opp_view.life, oz.hand, oz.battlefield,
                oz.graveyard, oz.library, hand_known=True, ours=False)
    blockers = sum(1 for c in opp["battlefield_creatures"] if not c["tapped"])
    return {
        "arena_match_id": "", "game_num": 0, "turn_num": turn_num,
        "play_or_draw": "play" if on_play else "draw", "you": you, "opp": opp,
        "notes": (f"Sim position vs {opp_name}, turn {turn_num}. Opponent at "
                  f"{opp['life']} with {blockers} untapped creature(s); their "
                  f"hand is revealed. You have lethal this turn."),
    }


# ---------------------------------------------------------------- scripted pilot

class LinePilot(MatchAPL):
    """Plays exactly `line` in main phase 1, then nothing. Records the legal
    children after the line and (optionally) the pre-action scene."""
    name = "Line Pilot"

    def __init__(self, line, *, capture=None):
        try:
            super().__init__()
        except TypeError:
            pass
        self.line = list(line)
        self.capture = capture      # (our_name, opp_name, turn_num, on_play) or None
        self.ok = False
        self.children: list = []
        self.scene = None
        self.haste_suspect = False   # line casts a creature with engine-only haste
        self.robust = False          # survives the opponent's best blocks (after the line)
        self.threats: list = []      # revealed-hand cards a real opponent could use

    def keep(self, *a, **k):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass

    def main_phase2(self, gs):
        pass

    def main_phase_match(self, gs, opponent):
        if opponent is not None:
            gs._match_opp = opponent
        self._opp_gs = opponent
        if self.capture is not None:
            self.scene = _scene(gs, opponent, *self.capture)
        gs.tap_lands()
        for step in self.line:
            kind, _, name = step.partition(":")
            want = ("PLAY_LAND", name) if kind == "PLAY_LAND" else ("CAST", step)
            act = next((a for a in legal_main_actions(gs)
                        if (a.kind, a.card_name) == want), None)
            if act is None or not apply_action(gs, act):
                return                  # self.ok stays False
            if act.kind == "CAST" and _haste_suspect(act.card_ref):
                self.haste_suspect = True
        self.ok = True
        self.children = [_label(a) for a in _ordered(gs)]
        if opponent is not None:
            self.robust = survives_best_blocks(gs, opponent)
            self.threats = hand_threats(opponent.zones.hand, opponent.zones.battlefield,
                                        gs.zones.battlefield)


# ---------------------------------------------------------------- the miner

class GauntletMiner:
    def __init__(self, our_name: str):
        self.our_name = our_name
        self.opp_name = ""
        self.game_id = ""
        self.on_play = True
        self.candidates: list[dict] = []
        self.position_secs: list[float] = []
        self.positions = 0
        self.haste_rejects = 0
        self._found = False
        self._pending = None

    def new_game(self, opp_name, game_id, on_play):
        self.opp_name, self.game_id, self.on_play = opp_name, game_id, on_play
        self._found, self._pending = False, None

    def _turn(self, root, line, skip_draw, turn_num, capture=False):
        fork = deepcopy(root)
        cap = (self.our_name, self.opp_name, turn_num, self.on_play) if capture else None
        pilot = LinePilot(line, capture=cap)
        res = mr.MatchResult()
        ended = _ORIG_TURN(fork, "a", pilot, skip_draw, res, turn_num)
        return (bool(ended and res.won), pilot)

    def analyze(self, root, skip_draw, turn_num):
        if self._found or root.life_b > OPP_LIFE_CAP or root.life_b <= 0:
            return
        t0 = time.perf_counter()
        self.positions += 1
        try:
            self._search(root, skip_draw, turn_num)
        finally:
            self.position_secs.append(time.perf_counter() - t0)

    def _search(self, root, skip_draw, turn_num):
        won, base = self._turn(root, [], skip_draw, turn_num, capture=True)
        if won or not base.ok:
            return                          # trivial (just attack) or broken
        budget = [NODE_BUDGET]
        first_win: list = []    # fallback when no line survives best blocks

        def dfs(prefix, children, depth):
            for child in children:
                if budget[0] <= 0:
                    return None
                budget[0] -= 1
                line = prefix + [child]
                w, p = self._turn(root, line, skip_draw, turn_num)
                if not p.ok or p.haste_suspect:
                    if p.haste_suspect:
                        self.haste_rejects += 1
                    continue
                if w:
                    if p.robust:
                        return line     # kills even through the best blocks
                    if not first_win:
                        first_win.append(line)
                    continue
                if depth + 1 < MAX_DEPTH:
                    got = dfs(line, p.children, depth + 1)
                    if got:
                        return got
            return None

        line = dfs([], base.children, 0) or (first_win[0] if first_win else None)
        if not line:
            return
        # G1: independent re-run from a fresh fork, every step must apply
        w, p = self._turn(root, line, skip_draw, turn_num)
        if not (w and p.ok) or p.haste_suspect:
            return
        scene = base.scene
        blockers = sum(1 for c in scene["opp"]["battlefield_creatures"] if not c["tapped"])
        opp_perms = (len(scene["opp"]["battlefield_creatures"])
                     + len(scene["opp"]["battlefield_other"]))
        self._pending = {
            "arena_match_id": f"gauntlet:{self.game_id}",
            "game_num": 1, "turn_num": turn_num, "category": "find_lethal",
            "heuristic_score": 0.0,     # set after the real turn (apl_found)
            "solution_line": line, "scene": scene, "source": "gauntlet-miner",
            "our_deck": self.our_name, "opp_deck": self.opp_name,
            "live_blockers": blockers, "opp_permanents": opp_perms,
            "robust_vs_best_blocks": p.robust, "hand_threats": p.threats,
            "clean": p.robust and not p.threats,
            "caveats": CAVEATS,
        }
        self._found = True

    def settle(self, real_won: bool):
        """Called after the REAL turn ran: record whether the APL found it too."""
        c = self._pending
        if c is None:
            return
        c["apl_found"] = bool(real_won)
        c["heuristic_score"] = round(2.0 + (0.0 if real_won else 1.0)
                                     + (0.5 if c["live_blockers"] else 0.0)
                                     + 0.1 * len(c["solution_line"]), 3)
        self.candidates.append(c)
        self._pending = None


def _install(miner: GauntletMiner):
    def hooked(gs, player, apl, skip_draw, result, turn_num):
        if player == "a":
            try:
                miner.analyze(gs, skip_draw, turn_num)
            except Exception:
                if os.environ.get("SIM_DEBUG"):
                    raise
                miner._pending = None   # mining must never perturb the real game
        ended = _ORIG_TURN(gs, player, apl, skip_draw, result, turn_num)
        if player == "a":
            miner.settle(bool(ended and result.won))
        return ended
    mr._run_player_turn = hooked


def _uninstall():
    mr._run_player_turn = _ORIG_TURN


def field_opponents(fmt: str) -> list[str]:
    from format_config import FORMATS
    cfg = FORMATS[fmt]
    combo = {c.lower() for c in cfg.get("combo", set())}
    return [n for n in cfg["field"] if n.lower() not in combo]


def mine(our_deck: str, fmt: str, games_per_opp: int, seed: int,
         opps: list[str] | None = None, hook: bool = True):
    """Returns (candidates, results, miner). `hook=False` plays the same games
    with no mining (G4 no-perturbation baseline)."""
    from generate_matchup_data import load_deck_and_apl
    from apl import get_match_apl

    ours, _, _ = load_deck_and_apl(our_deck, fmt)
    miner = GauntletMiner(our_deck)
    results = []
    if hook:
        _install(miner)
    try:
        for opp in (opps or field_opponents(fmt)):
            theirs, _, _ = load_deck_and_apl(opp, fmt)
            if not theirs:
                continue
            for i in range(games_per_opp):
                on_play = (i % 2 == 0)
                gseed = seed + i
                miner.new_game(opp, f"{our_deck}|{opp}|{gseed}", on_play)
                r = mr.run_match(get_match_apl(our_deck), ours,
                                 get_match_apl(opp), theirs,
                                 on_play=on_play, seed=gseed)
                results.append((opp, gseed, r.won, r.kill_turn, r.loser_life))
    finally:
        _uninstall()
    return miner.candidates, results, miner


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Mine gauntlet lethal puzzles.")
    ap.add_argument("--deck", default="Boros Energy")
    ap.add_argument("--format", default="modern")
    ap.add_argument("--games-per-opp", type=int, default=50)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--opps", default="", help="comma list; default = non-combo field")
    ap.add_argument("--out", default="data/gauntlet_candidates.jsonl")
    args = ap.parse_args(argv)

    opps = [o.strip() for o in args.opps.split(",") if o.strip()] or None
    t0 = time.time()
    cands, results, miner = mine(args.deck, args.format, args.games_per_opp,
                                 args.seed, opps)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    clean = [c for c in cands if c["clean"]]
    flagged = [c for c in cands if not c["clean"]]
    flagged_path = args.out.replace(".jsonl", "_flagged.jsonl")
    for path, rows in ((args.out, clean), (flagged_path, flagged)):
        with open(path, "w", encoding="utf-8") as f:
            for c in rows:
                f.write(json.dumps(c, sort_keys=True) + "\n")

    games = len(results)
    missed = sum(1 for c in cands if not c["apl_found"])
    live = sum(1 for c in cands if c["live_blockers"])
    med = statistics.median(miner.position_secs) if miner.position_secs else 0.0
    print(f"Mined {len(cands)} candidates from {games} games "
          f"({100.0 * len(cands) / max(games, 1):.1f}%), {time.time() - t0:.0f}s.")
    print(f"  positions searched {miner.positions}, median {med:.2f}s, "
          f"max {max(miner.position_secs or [0]):.2f}s")
    print(f"  {missed} the deck's own pilot missed; {live} with a live blocker.")
    print(f"  {miner.haste_rejects} search lines dropped: they cast a creature whose "
          f"haste is an engine tag, not printed (e.g. Ragavan without dash).")
    by_opp: dict = {}
    for c in cands:
        by_opp[c["opp_deck"]] = by_opp.get(c["opp_deck"], 0) + 1
    for o, n in sorted(by_opp.items(), key=lambda x: -x[1]):
        print(f"    {o}: {n}")
    weak = sum(1 for c in flagged if not c["robust_vs_best_blocks"])
    answer = sum(1 for c in flagged if c["hand_threats"])
    print(f"  CLEAN {len(clean)} -> {args.out}")
    print(f"  FLAGGED {len(flagged)} -> {flagged_path} ({weak} need a weak block, "
          f"{answer} have a real-opponent answer in the revealed hand)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
