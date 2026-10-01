"""GameRecord + exact replay (spec section 8)."""
from __future__ import annotations

import re

from engine.v2 import ENGINE_VERSION
from engine.v2 import actions as A
from engine.v2.cards import CardDataMismatch, definitions_hash

# Exact replay needs the engine that produced the record: v2-m1.1 changed every transition
# hash (every op emits an event), so records from earlier engines cannot replay.
REPLAY_VERSION = ENGINE_VERSION
LEGACY_CUTOFF = "v2-m1.1"


class ReplayMismatch(AssertionError):
    """A record that claims a compatible engine version but does not reproduce."""


class ReplayVersionError(ValueError):
    """The record was produced by an incompatible engine version (not corrupted data)."""


def _vkey(v):
    m = re.fullmatch(r"v(\d+)-m(\d+)\.(\d+)", str(v))
    return tuple(int(x) for x in m.groups()) if m else None


def check_version(record: dict) -> None:
    """Refuse an incompatible record before any rules / card-data / log / state check.
    A record without a record-level engine_version is legacy (pre-v2-m1.1). Never upgrades."""
    found = record.get("engine_version")
    if found == REPLAY_VERSION:
        return
    if found is None:
        cfg = (record.get("config") or {}).get("engine_version")
        shown = "none (no record-level engine_version field" + (f"; config says {cfg!r})" if cfg else ")")
        legacy = True
    else:
        shown = repr(found)
        k, cut = _vkey(found), _vkey(LEGACY_CUTOFF)
        legacy = k is not None and k < cut
    why = (f"the record predates {LEGACY_CUTOFF}, whose transition hashes differ from earlier engines"
           if legacy else "the record was produced by a different engine version")
    raise ReplayVersionError(
        f"replay version incompatible: found {shown}, required {REPLAY_VERSION!r}; {why}. "
        f"This is a compatibility problem, not corrupted game data; the record was not modified.")


def make_record(game, policy_seeds=None) -> dict:
    s = game.s
    return {
        "engine_version": s.config["engine_version"],              # replay format (checked first)
        "config": {k: v for k, v in s.config.items()},
        "policy_seeds": policy_seeds,
        "starting_player": s.starting_player,                      # resolved (mode is in config)
        "actions": [A.to_record(a) for a in game.actions],
        "action_transition_index": list(game.action_transition_index),
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
    check_version(record)
    cfg = record["config"]
    if cfg["definitions_hash"] != definitions_hash():
        raise CardDataMismatch(f"record definitions_hash {cfg['definitions_hash']} != current {definitions_hash()}")
    if cfg["rules_sha256"] != rules_meta()["sha256"]:
        raise ReplayMismatch("record was produced under a different rules baseline")
    g = Game.new(cfg["decks"][0], cfg["decks"][1], cfg["seed"], starting_mode=cfg["starting_mode"],
                 starting_player=cfg["starting_player"], turn_limit=cfg["turn_limit"],
                 check_invariants=cfg.get("check_invariants", False), deck_rules=cfg["deck_rules"])
    if g.s.starting_player != record.get("starting_player", g.s.starting_player):
        raise ReplayMismatch("starting player differs")
    idx = record.get("action_transition_index")
    for i, rec in enumerate(record["actions"]):
        if idx is not None and len(g.s.log.transitions) != idx[i]:
            raise ReplayMismatch(f"action {i} applied at transition {len(g.s.log.transitions)}, recorded {idx[i]}")
        g.apply(A.from_record(rec))
    got = [t.hash for t in g.s.log.transitions]
    want = record["transition_hashes"]
    if got != want:
        i = next((k for k, (x, y) in enumerate(zip(got, want)) if x != y), min(len(got), len(want)))
        raise ReplayMismatch(f"first differing transition {i}")
    if g.s.full_state_hash() != record["full_state_hash"]:
        raise ReplayMismatch("final full_state_hash differs")
    return g
