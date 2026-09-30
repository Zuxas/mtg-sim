"""Identity model (CR 400.7).

CardInstance  -- one per physical deck card; persists all game (unit of conservation).
GameObject    -- the card's current incarnation in one zone; status lives here and is
                 discarded on every zone change (new ObjectId, same CardInstanceId).
StackEntry    -- a spell on the stack. While its casting transaction is open it has a
                 ProvisionalStackId ("P<n>", never an ObjectId) and its source ObjectId
                 is suspended; when it becomes cast it gets a real ObjectId.
Only engine.v2.reducer mutates these.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardInstance:
    ciid: int
    name: str
    owner: int


@dataclass
class GameObject:
    oid: int
    ciid: int
    owner: int
    controller: int
    zone: str                       # library | hand | battlefield | graveyard | exile | stack | suspended
    tapped: bool = False
    damage: int = 0
    eot_power: int = 0              # "until end of turn" modifications (Giant Growth)
    eot_toughness: int = 0
    controlled_since: int = 0       # turn number when it came under its controller's control

    def rules_view(self) -> tuple:
        return (self.oid, self.ciid, self.owner, self.controller, self.zone, self.tapped,
                self.damage, self.eot_power, self.eot_toughness, self.controlled_since)


@dataclass
class StackEntry:
    sid: str                        # "P<n>" while proposed, "O<oid>" once cast
    ciid: int
    controller: int
    state: str                      # proposed | cast
    oid: object = None              # ObjectId once cast
    targets: tuple = ()             # (("obj", oid) | ("player", p) | ("stack", sid), ...)

    def rules_view(self) -> tuple:
        return (self.sid, self.ciid, self.controller, self.state, self.oid, self.targets)
