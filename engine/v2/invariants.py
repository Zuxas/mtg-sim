"""Invariants (spec section 11), checked after every atomic transition when
config["check_invariants"] is set. A violation raises InvariantViolation."""
from __future__ import annotations

from collections import Counter


class InvariantViolation(AssertionError):
    pass


def _fail(msg):
    raise InvariantViolation(msg)


def check(s, kind: str) -> None:
    # I2 identity + zones
    seen = Counter()
    for key, lst in s.zones.items():
        for oid in lst:
            seen[oid] += 1
            o = s.objects.get(oid)
            if o is None:
                _fail(f"I2 zone {key} holds dead object {oid}")
            want = "battlefield" if key == ("bf",) else key[1]
            if o.zone != want:
                _fail(f"I2 object {oid} zone {o.zone} listed in {want}")
            if key != ("bf",) and o.owner != key[0]:
                _fail(f"I2 object {oid} in another player's {want}")
    if any(n > 1 for n in seen.values()):
        _fail("I2 object listed twice")
    stack_oids = {e.oid for e in s.stack if e.state == "cast"}
    for oid, o in s.objects.items():
        if oid in s.retired:
            _fail(f"I2 retired id {oid} is live")
        if o.zone == "stack" and oid not in stack_oids:
            _fail(f"I2 stack object {oid} without a cast entry")
        if o.zone not in ("stack", "suspended") and seen[oid] != 1:
            _fail(f"I2 live object {oid} not in exactly one zone")
    suspended = [o for o in s.objects.values() if o.zone == "suspended"]
    proposed = [e for e in s.stack if e.state == "proposed"]
    if s.open_cast is None and (suspended or proposed):
        _fail("I2/I5 suspended object or proposed entry without an open casting transaction")
    if s.open_cast is not None and (len(suspended) != 1 or len(proposed) != 1 or s.stack[-1].state != "proposed"):
        _fail("I2 open casting transaction malformed")
    for e in s.stack:
        if e.state == "proposed" and not str(e.sid).startswith("P"):
            _fail("I2 provisional id is not a ProvisionalStackId")
    per_ciid = Counter(o.ciid for o in s.objects.values())
    if any(n != 1 for n in per_ciid.values()):
        _fail("I2 card instance with more than one live/suspended object")
    # I1 conservation: exact CardInstanceId set per player, definitions and owners unchanged
    for p in (0, 1):
        present = sorted(o.ciid for o in s.objects.values() if o.owner == p)
        deck = sorted(c for c, inst in s.instances.items() if inst.owner == p)
        if present != deck:
            _fail(f"I1 card conservation broken for player {p}")
    for i, name in enumerate(n for deck in s.config["decks"] for n in deck):
        inst = s.instances.get(i + 1)
        if inst is None or inst.name != name:
            _fail("I1 card instance definition changed")
    # I3 pools empty as a step begins
    if kind == "step" and any(any(v for v in pool.values()) for pool in s.pools):
        _fail("I3 mana pool not empty at a step boundary")
    if any(v < 0 for pool in s.pools for v in pool.values()):
        _fail("I3 negative mana")
    # I5 land drops
    if any(n > 1 for n in s.land_played):
        _fail("I5 more than one land this turn")
    # I6 attackers tapped unless vigilance
    if kind == "declare_attackers":
        for a in s.attackers:
            if not s.objects[a].tapped and not s.definition(a).has("Vigilance"):
                _fail("I6 attacker not tapped")
    # I7 hand size after cleanup
    if kind == "cleanup" and len(s.zones[(s.active, "hand")]) > 7:
        _fail("I7 hand larger than 7 after cleanup")
    # I7 result only from SBA / concession / turn limit
    if s.result is not None and kind not in ("sba", "concede", "game_end"):
        _fail(f"I7 game ended in a {kind} transition")
