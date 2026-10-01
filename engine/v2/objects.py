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
    counters: tuple = ()            # ((kind, n), ...) sorted, e.g. (("time", 1),) on a suspended card

    def rules_view(self) -> tuple:
        return (self.oid, self.ciid, self.owner, self.controller, self.zone, self.tapped,
                self.damage, self.eot_power, self.eot_toughness, self.controlled_since, self.counters)

    def counter(self, kind: str) -> int:
        return dict(self.counters).get(kind, 0)


@dataclass
class StackEntry:
    """A spell ("P<n>" while proposed, "O<oid>" once cast) or an ability ("A<n>", state
    "ability"): an object that is not a card, never in a card zone (CR 602.2a, 603.3)."""
    sid: str
    ciid: int                       # the card (spell) or the ability's source card
    controller: int
    state: str                      # proposed | cast | ability
    oid: object = None              # ObjectId once cast (spells only)
    targets: tuple = ()             # (("obj", oid) | ("player", p) | ("stack", sid), ...)
    ability: object = None          # ability key (abilities only)
    source: object = None           # source ObjectId when the ability was created (may be gone)
    info: tuple = ()                # ability parameters fixed when it was created
    mode: object = None             # chosen mode (modal spells, CR 700.2a)
    cost: object = None             # "normal" | alternative-cost name | "free" (CR 601.2b, 118.9)
    mana_spent: int = 0             # mana actually spent to cast it (CR 601.2h)

    def rules_view(self) -> tuple:
        return (self.sid, self.ciid, self.controller, self.state, self.oid, self.targets, self.ability,
                self.source, self.info, self.mode, self.cost, self.mana_spent)
