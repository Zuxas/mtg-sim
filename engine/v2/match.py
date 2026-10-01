"""Best-of-three matches (milestone two, phase 5). The match is its own small state machine
around engine-v2 games; every match-level choice is a typed, recorded decision:

- Play/draw (CR 103.1): game 1 -- a match-RNG coin flip picks the player who chooses; later
  games -- the loser of the previous game chooses; after a drawn game, the player who made
  the previous choice chooses again. `ChoosePlayDraw(player, play)`.
- Sideboarding (CR 100.4, 100.4a, 100.2a) between games, one staged swap at a time:
  `SideboardSwap(player, out_name, in_name)` exchanges one main-deck card with one sideboard
  card; `DoneSideboarding(player)` ends that player's changes. Only explicitly supported cards
  can be brought in; the main deck stays >= 60, the sideboard <= 15, the 4-of rule holds for
  deck + sideboard combined. Each player sideboards against their own previous configuration;
  choices are hidden from the opponent until the next game begins.
- Match end: the first player with 2 game wins wins the match; a drawn game counts for
  neither. Conservative cap (recorded): at most `max_games` games (default 5); if nobody has
  2 wins by then the match is a draw.

Every game is a normal engine-v2 Game with its own seed derived from the match seed, so the
complete match replays exactly from its MatchRecord.
"""
from __future__ import annotations

import collections
import hashlib
import json
import random
from dataclasses import dataclass, fields

from engine.v2.cards import BASIC_LAND_COLOR, MAX_COPIES, MIN_DECK, SUPPORTED, validate_deck

MAX_SIDEBOARD = 15
BASIC = set(BASIC_LAND_COLOR)


@dataclass(frozen=True)
class MatchObservation:
    """What a seat knows between games: public match state plus ONLY its own 75."""
    seat: int
    wins: tuple
    games_played: int
    game_results: tuple             # result of each finished game
    starting: tuple                 # starting player of each game so far
    pending: tuple                  # (kind, player)
    my_main: tuple                  # this seat's current main deck (names)
    my_side: tuple                  # this seat's current sideboard (names)


@dataclass(frozen=True)
class ChoosePlayDraw:
    player: int
    play: bool


@dataclass(frozen=True)
class SideboardSwap:
    player: int
    out_name: str
    in_name: str


@dataclass(frozen=True)
class DoneSideboarding:
    player: int


MATCH_ACTIONS = {c.__name__: c for c in (ChoosePlayDraw, SideboardSwap, DoneSideboarding)}


def _rec(a) -> list:
    return [type(a).__name__] + [getattr(a, f.name) for f in fields(a)]


def _unrec(r):
    return MATCH_ACTIONS[r[0]](*r[1:])


class MatchError(ValueError):
    pass


def validate_75(main, side) -> None:
    """Constructed deck rules for a match (CR 100.2a, 100.4a) and engine support for all 75."""
    if len(main) < MIN_DECK:
        raise MatchError(f"main deck has {len(main)} cards (< {MIN_DECK})")
    if len(side) > MAX_SIDEBOARD:
        raise MatchError(f"sideboard has {len(side)} cards (> {MAX_SIDEBOARD})")
    counts = collections.Counter(list(main) + list(side))
    over = [n for n, k in counts.items() if n not in BASIC and k > MAX_COPIES]
    if over:
        raise MatchError(f"more than {MAX_COPIES} copies across deck and sideboard: {over}")
    validate_deck(list(main) + list(side))            # unknown / unsupported -> refused, nothing starts


class Match:
    def __init__(self, deck_a, side_a, deck_b, side_b, seed: int, turn_limit: int = 50, max_games: int = 5,
                 check_invariants: bool = False):
        validate_75(deck_a, side_a)
        validate_75(deck_b, side_b)
        self.config = {"decks": [list(deck_a), list(deck_b)], "sides": [list(side_a), list(side_b)],
                       "seed": seed, "turn_limit": turn_limit, "max_games": max_games,
                       "check_invariants": check_invariants}
        self.rng = random.Random(seed)                # match RNG: only the game-1 chooser coin flip
        self.main = [list(deck_a), list(deck_b)]
        self.side = [list(side_a), list(side_b)]
        self.games = []                               # finished Game objects
        self.wins = [0, 0]
        self.actions = []                             # match-level decisions, in order
        self.action_game_index = []                   # number of finished games when each was made
        self.chooser = self.rng.randrange(2)          # CR 103.1: "any mutually agreeable method"
        self.pending = ("play_draw", self.chooser)
        self.sb_done = [False, False]
        self.result = None
        self.current = None                           # the Game in progress
        self.starting = []                            # starting player of each game

    # ------------------------------------------------------------------ decisions
    def observe(self, seat) -> MatchObservation:
        return MatchObservation(seat, tuple(self.wins), len(self.games), tuple(g.result for g in self.games),
                                tuple(self.starting), tuple(self.pending) if self.pending else (),
                                tuple(self.main[seat]), tuple(self.side[seat]))

    def legal_actions(self) -> tuple:
        return tuple(self._legal())

    def _legal(self) -> list:
        if self.result is not None or self.pending is None:
            return []
        kind, p = self.pending
        if kind == "play_draw":
            return [ChoosePlayDraw(p, True), ChoosePlayDraw(p, False)]
        if kind == "sideboard":
            out = [DoneSideboarding(p)]
            seen = set()
            for o in sorted(set(self.main[p])):
                for i in sorted(set(self.side[p])):
                    if o == i or (o, i) in seen or i not in SUPPORTED:
                        continue
                    seen.add((o, i))
                    out.append(SideboardSwap(p, o, i))
            return out
        return []

    def apply(self, a) -> None:
        if a not in self.legal_actions():
            raise MatchError(f"{a!r} is not a legal match action now ({self.pending})")
        self.actions.append(a)
        self.action_game_index.append(len(self.games))
        if isinstance(a, ChoosePlayDraw):
            start = a.player if a.play else 1 - a.player
            self._start_game(start)
        elif isinstance(a, SideboardSwap):
            m, s = self.main[a.player], self.side[a.player]
            m.remove(a.out_name)
            s.remove(a.in_name)
            m.append(a.in_name)
            s.append(a.out_name)
            validate_75(m, s)                             # stays a legal 75 (counts are unchanged)
        elif isinstance(a, DoneSideboarding):
            self.sb_done[a.player] = True
            nxt = next((p for p in (0, 1) if not self.sb_done[p]), None)
            self.pending = ("sideboard", nxt) if nxt is not None else ("play_draw", self.chooser)

    def _start_game(self, start):
        from engine.v2.game import Game
        gi = len(self.games)
        seed = int.from_bytes(hashlib.sha256(f"{self.config['seed']}:{gi}".encode()).digest()[:6], "big")
        self.starting.append(start)
        self.current = Game.new(self.main[0], self.main[1], seed, starting_player=start,
                                turn_limit=self.config["turn_limit"],
                                check_invariants=self.config["check_invariants"])
        self.pending = None

    def finish_game(self) -> None:
        """Record the finished current game and set up the next decision (or end the match)."""
        g = self.current
        assert g is not None and g.result is not None
        self.games.append(g)
        self.current = None
        if g.result[0] == "win":
            w = g.result[1]
            self.wins[w] += 1
            self.chooser = 1 - w                          # CR 103.1: the loser chooses
        # a draw: the player who made the previous choice chooses again (chooser unchanged)
        if max(self.wins) >= 2:
            self.result = ("win", self.wins.index(max(self.wins)), tuple(self.wins))
            return
        if len(self.games) >= self.config["max_games"]:
            self.result = ("draw", "game_cap", tuple(self.wins))
            return
        self.sb_done = [False, False]
        self.pending = ("sideboard", 0)

    def run(self, game_policies, match_policies=None) -> tuple:
        """Play the whole match. game_policies: [p0, p1] for in-game decisions; match_policies
        (default: the same objects) may offer `choose_match(observation, actions)` -- they get a
        frozen MatchObservation (never the Match); if absent, the first legal match action is
        taken (play first; no sideboard changes)."""
        mp = match_policies or game_policies
        while self.result is None:
            if self.current is not None:
                self.current.run(game_policies)
                self.finish_game()
                continue
            kind, p = self.pending
            acts = self.legal_actions()
            pick = getattr(mp[p], "choose_match", None)
            self.apply(pick(self.observe(p), acts) if pick else acts[0])
        return self.result


# ---------------------------------------------------------------------- record + replay
def make_match_record(m: Match) -> dict:
    from engine.v2 import ENGINE_VERSION
    from engine.v2.record import make_record
    games = [make_record(g) for g in m.games]
    chain = hashlib.sha256()
    for a, gi in zip(m.actions, m.action_game_index):
        chain.update(repr((gi, _rec(a))).encode())
    for gr in games:
        chain.update(gr["log_head"].encode())
        chain.update(gr["full_state_hash"].encode())
    return {"engine_version": ENGINE_VERSION, "config": dict(m.config),
            "actions": [_rec(a) for a in m.actions], "action_game_index": list(m.action_game_index),
            "starting": list(m.starting), "games": games, "result": list(m.result), "match_hash": chain.hexdigest()}


class MatchReplayMismatch(AssertionError):
    pass


def replay_match(rec: dict) -> Match:
    """Re-run the match from its record (no policies): match decisions, then each game's
    recorded actions; every game must reproduce its transition hashes, and the match hash
    and result must match."""
    from engine.v2 import actions as A
    from engine.v2.record import check_version, replay
    for gr in rec["games"]:
        check_version(gr)
    c = rec["config"]
    m = Match(c["decks"][0], c["sides"][0], c["decks"][1], c["sides"][1], c["seed"], c["turn_limit"],
              c["max_games"], c["check_invariants"])
    actions = [_unrec(r) for r in rec["actions"]]
    i = 0
    while m.result is None:
        if m.current is not None:
            gr = rec["games"][len(m.games)]
            g = m.current
            if g.s.config["seed"] != gr["config"]["seed"] or g.s.starting_player != gr["starting_player"]:
                raise MatchReplayMismatch(f"game {len(m.games)} configuration differs")
            for ar in gr["actions"]:
                g.apply(A.from_record(ar))
            got = [t.hash for t in g.s.log.transitions]
            if got != gr["transition_hashes"] or g.s.full_state_hash() != gr["full_state_hash"]:
                raise MatchReplayMismatch(f"game {len(m.games)} diverged")
            replay(gr)                                    # the stand-alone game replay agrees too
            m.finish_game()
            continue
        if i >= len(actions):
            raise MatchReplayMismatch("record ended before the match did")
        m.apply(actions[i])
        i += 1
    again = make_match_record(m)
    norm = lambda x: json.loads(json.dumps(x))                        # noqa: E731 (tuples vs JSON lists)
    if again["match_hash"] != rec["match_hash"] or norm(again["result"]) != norm(rec["result"]):
        raise MatchReplayMismatch("match hash or result differs")
    return m
