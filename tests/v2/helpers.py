"""Test helpers for engine v2. Scenario setup goes through the reducer's own ops in an
explicit "test_arrange" transition -- tests never mutate GameState directly."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2 import reducer
from engine.v2.game import Game
from engine.v2.ops import op
from tests.v2.decks import RG, WU


def new_game(a=RG, b=WU, seed=0, starting=0, keep=True, **kw):
    g = Game.new(a, b, seed, starting_player=starting, check_invariants=True, **kw)
    if keep:
        while g.pending().kind == "mulligan_declare":
            g.apply(A.DeclareKeep(g.pending().player))
    return g


def arrange(g, ops):
    reducer.commit(g.s, "test_arrange", ops)
    g._legal_cache = (None, None)


def find(g, player, name, zone="library"):
    s = g.s
    lst = s.zones[("bf",)] if zone == "battlefield" else s.zones[(player, zone)]
    for oid in lst:
        o = s.objects[oid]
        if s.instances[o.ciid].name == name and o.owner == player and (zone != "battlefield" or o.controller == player):
            return oid
    raise KeyError(f"{name} not in player {player}'s {zone}")


def put(g, player, name, zone):
    """Move a copy of `name` from the player's library (else hand) into `zone`."""
    try:
        oid = find(g, player, name, "library")
    except KeyError:
        oid = find(g, player, name, "hand")
    arrange(g, [op("move", oid, zone, "end", player)])
    return g.s.zones[("bf",)][-1] if zone == "battlefield" else g.s.zones[(player, zone)][-1]


def act(g, cls, **kw):
    """Apply the unique legal action of class `cls` matching the keyword fields."""
    for a in g.legal_actions():
        if isinstance(a, cls) and all(getattr(a, k) == v for k, v in kw.items()):
            g.apply(a)
            return a
    raise AssertionError(f"no legal {cls.__name__} {kw}; legal: {g.legal_actions()[:12]}")


def advance(g, until, max_steps=5000):
    """Answer every decision with the passive choice until until(g) is true."""
    for _ in range(max_steps):
        if until(g) or g.result is not None:
            return
        pd = g.pending()
        k, p = pd.kind, pd.player
        if k == "priority":
            g.apply(A.PassPriority(p))
        elif k == "declare_attack":
            g.apply(A.ChooseAttack(p, pd.info[0], False))
        elif k == "declare_block":
            g.apply(A.ChooseBlock(p, pd.info[0], None))
        elif k == "mulligan_declare":
            g.apply(A.DeclareKeep(p))
        else:
            g.apply(g.legal_actions()[0])
    raise AssertionError("advance did not reach the condition")


def at(step, active=None, turn=None, player=None):
    def cond(g):
        s = g.s
        return (s.step == step and s.pending is not None and s.pending.kind == "priority"
                and (active is None or s.active == active) and (turn is None or s.turn == turn)
                and (player is None or s.pending.player == player))
    return cond


def tap_for(g, player, *names):
    for n in names:
        act(g, A.ActivateManaAbility, player=player, oid=_untapped(g, player, n))


def _untapped(g, player, name):
    s = g.s
    for oid in s.zones[("bf",)]:
        o = s.objects[oid]
        if s.instances[o.ciid].name == name and o.controller == player and not o.tapped:
            return oid
    raise KeyError(f"no untapped {name}")


def cast(g, player, name, target=None, lands=(), oid=None):
    """ProposeCast `name` (or the exact object `oid`) from hand, choose `target`, tap `lands`,
    pay the first assignment."""
    act(g, A.ProposeCast, player=player, oid=oid if oid is not None else find(g, player, name, "hand"))
    if g.pending().kind == "cast_targets":
        act(g, A.ChooseTargets, player=player, targets=(target,))
    for land in lands:
        act(g, A.ActivateManaAbility, player=player, oid=_untapped(g, player, land))
    pays = [a for a in g.legal_actions() if isinstance(a, A.PayCost)]
    assert pays, f"cannot pay for {name}"
    g.apply(pays[0])


def name_of(g, oid):
    return g.s.instances[g.s.objects[oid].ciid].name


def events(g, kind):
    return [e for t in g.s.log.transitions for e in t.events if e.kind == kind]
