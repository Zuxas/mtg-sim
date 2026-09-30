"""GameRecord + exact replay (spec section 8)."""
from __future__ import annotations

from engine.v2 import actions as A
from engine.v2.cards import CardDataMismatch, definitions_hash


class ReplayMismatch(AssertionError):
    pass


def make_record(game, policy_seeds=None) -> dict:
    s = game.s
    return {
        "config": {k: v for k, v in s.config.items()},
        "policy_seeds": policy_seeds,
        "actions": [A.to_record(a) for a in game.actions],
        "transition_hashes": [t.hash for t in s.log.transitions],
        "log_head": s.log.head,
        "full_state_hash": s.full_state_hash(),
        "rules_state_hash": s.rules_state_hash(),
        "result": s.result,
    }


def replay(record: dict):
    """Re-run the game from its record WITHOUT consulting policies; must reproduce every
    transition hash and the final full state hash."""
    from engine.v2.game import Game, rules_meta
    cfg = record["config"]
    if cfg["definitions_hash"] != definitions_hash():
        raise CardDataMismatch(f"record definitions_hash {cfg['definitions_hash']} != current {definitions_hash()}")
    if cfg["rules_sha256"] != rules_meta()["sha256"]:
        raise ReplayMismatch("record was produced under a different rules baseline")
    g = Game.new(cfg["decks"][0], cfg["decks"][1], cfg["seed"], starting_mode=cfg["starting_mode"],
                 starting_player=cfg["starting_player"], turn_limit=cfg["turn_limit"],
                 check_invariants=cfg.get("check_invariants", False))
    for rec in record["actions"]:
        g.apply(A.from_record(rec))
    got = [t.hash for t in g.s.log.transitions]
    want = record["transition_hashes"]
    if got != want:
        i = next((k for k, (x, y) in enumerate(zip(got, want)) if x != y), min(len(got), len(want)))
        raise ReplayMismatch(f"first differing transition {i}")
    if g.s.full_state_hash() != record["full_state_hash"]:
        raise ReplayMismatch("final full_state_hash differs")
    return g
