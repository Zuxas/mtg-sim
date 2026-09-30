"""GameState -- mutated ONLY by engine.v2.reducer.

Two canonical hashes (spec section 4):
  rules_state_hash -- the rules-visible state (zones with ObjectIds + status, stack, life,
                      pools, turn/step/active/priority, land drops, mulligan counts and
                      keeps, pending decision kind + owner, result, draw-failed flags);
  full_state_hash  -- rules state + engine internals (id allocators, RNG state, open
                      casting transaction, staged decision buffers).
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field

from engine.v2.events import EventLog

PLAYER_ZONES = ("library", "hand", "graveyard", "exile")


@dataclass
class Pending:
    kind: str                       # mulligan_declare | mulligan_bottom | priority | cast_targets | cast_mana |
    player: int                     # declare_attack | declare_block | assign_damage | discard | none
    info: tuple = ()                # kind-specific, hashable

    def view(self) -> tuple:
        return (self.kind, self.player, self.info)


@dataclass
class GameState:
    config: dict
    rng: random.Random
    instances: dict = field(default_factory=dict)          # ciid -> CardInstance
    objects: dict = field(default_factory=dict)            # oid -> GameObject (live or suspended)
    retired: set = field(default_factory=set)              # retired ObjectIds (never reappear)
    zones: dict = field(default_factory=dict)              # (player, zone) -> [oid]; ("bf",) -> [oid]
    stack: list = field(default_factory=list)              # StackEntry, bottom -> top
    life: list = field(default_factory=lambda: [20, 20])   # CR 103.4
    pools: list = field(default_factory=lambda: [dict.fromkeys("WUBRGC", 0), dict.fromkeys("WUBRGC", 0)])
    land_played: list = field(default_factory=lambda: [0, 0])
    draw_failed: list = field(default_factory=lambda: [False, False])
    mull_count: list = field(default_factory=lambda: [0, 0])
    kept: list = field(default_factory=lambda: [False, False])
    mull_declared: dict = field(default_factory=dict)      # player -> "keep" | "mulligan" (current round)
    mull_bottoms: dict = field(default_factory=dict)       # player -> ordered tuple (hidden until commit)
    mull_stage: str = "declare"                            # declare | bottom | done
    mull_round: tuple = ()                                 # players who mulliganed this round
    starting_player: int = 0
    turn: int = 0
    active: int = 0
    step: str = "pregame"
    priority: object = None
    passes: int = 0
    pending: object = None
    attackers: tuple = ()                                  # declared attackers (oids)
    attack_choices: dict = field(default_factory=dict)     # staged ChooseAttack decisions
    blocks: dict = field(default_factory=dict)             # blocker oid -> attacker oid (committed)
    block_choices: dict = field(default_factory=dict)      # staged ChooseBlock decisions
    blocked: tuple = ()                                    # attackers that became blocked (stay blocked)
    divisions: dict = field(default_factory=dict)          # attacker oid -> ((blocker, dmg), ...) staged
    first_strike_done: bool = False
    open_cast: object = None                               # dict while a casting transaction is open
    lost: list = field(default_factory=lambda: [None, None])
    result: object = None                                  # ("win", p, reason) | ("draw", reason)
    next_ciid: int = 1
    next_oid: int = 1
    next_prov: int = 1
    log: EventLog = field(default_factory=EventLog)
    def_by_ciid: dict = field(default_factory=dict)       # derived cache: ciid -> CardDefinition (not hashed)

    # ------------------------------------------------------------ zone helpers (read-only)
    def zone(self, player, name) -> list:
        return self.zones[("bf",)] if name == "battlefield" else self.zones[(player, name)]

    def battlefield(self) -> list:
        return self.zones[("bf",)]

    def definition(self, oid_or_ciid, is_ciid=False):
        return self.def_by_ciid[oid_or_ciid if is_ciid else self.objects[oid_or_ciid].ciid]

    def power(self, oid) -> int:
        o = self.objects[oid]
        return (self.definition(oid).power or 0) + o.eot_power

    def toughness(self, oid) -> int:
        o = self.objects[oid]
        return (self.definition(oid).toughness or 0) + o.eot_toughness

    def entry(self, sid):
        return next((e for e in self.stack if e.sid == sid), None)

    # ------------------------------------------------------------ hashing
    def rules_view(self) -> dict:
        zones = {f"{k[0]}:{k[1]}" if len(k) == 2 else "bf": [self.objects[o].rules_view() for o in v]
                 for k, v in sorted(self.zones.items(), key=lambda kv: str(kv[0]))}
        return {
            "zones": zones,
            "stack": [e.rules_view() for e in self.stack],
            "life": list(self.life), "pools": [sorted(p.items()) for p in self.pools],
            "turn": self.turn, "active": self.active, "step": self.step,
            "priority": self.priority, "passes": self.passes,
            "land_played": list(self.land_played), "mull_count": list(self.mull_count),
            "kept": list(self.kept), "mull_declared": sorted(self.mull_declared.items()),
            "mull_stage": self.mull_stage, "mull_round": list(self.mull_round),
            "pending": self.pending.view() if self.pending else None,
            "attackers": list(self.attackers), "blocks": sorted(self.blocks.items()),
            "blocked": list(self.blocked), "first_strike_done": self.first_strike_done,
            "draw_failed": list(self.draw_failed), "lost": list(self.lost), "result": self.result,
            "starting_player": self.starting_player,
        }

    def full_view(self) -> dict:
        v = self.rules_view()
        v["internals"] = {
            "next_ciid": self.next_ciid, "next_oid": self.next_oid, "next_prov": self.next_prov,
            "rng": hashlib.sha256(repr(self.rng.getstate()).encode()).hexdigest(),
            "open_cast": _canon(self.open_cast), "mull_bottoms": sorted(self.mull_bottoms.items()),
            "attack_choices": sorted(self.attack_choices.items()),
            "block_choices": sorted(self.block_choices.items()),
            "divisions": sorted(self.divisions.items()),
            "suspended": sorted(o.oid for o in self.objects.values() if o.zone == "suspended"),
            "retired_count": len(self.retired),
        }
        return v

    def rules_state_hash(self) -> str:
        return _hash(self.rules_view())

    def full_state_hash(self) -> str:
        return _hash(self.full_view())


def _canon(x):
    if isinstance(x, dict):
        return sorted((str(k), _canon(v)) for k, v in x.items())
    if isinstance(x, (list, tuple)):
        return [_canon(i) for i in x]
    return x


def _hash(obj) -> str:
    return hashlib.sha256(json.dumps(_canon(obj), sort_keys=True, separators=(",", ":"), default=str)
                          .encode("utf-8")).hexdigest()
