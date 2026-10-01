"""The reducer: the ONLY code that mutates GameState.

commit(state, kind, ops) applies a list of ops as ONE atomic transition: each op is
validated against the current state (an invalid op is an engine bug and raises
EngineInvariantError -- never skipped), emits at least one event (spec section 8: every
op applied produces an event, so the chained transition hash covers every state change),
and the transition is appended to the event log. Invariants run after the whole
transition (never mid-transition) when state.config["check_invariants"] is set.

Atomicity (spec section 15, copy-on-write of touched objects): while a transaction is
open, the first touch of any state attribute, zone list, game object, the RNG or the
object table saves a copy in `state.txn`; on any handler or invariant failure `rollback`
restores every saved copy and truncates the event log, then the error is re-raised.
Game.apply opens one transaction per action (all of its transitions); a commit made
outside an action opens its own.
"""
from __future__ import annotations

import hashlib

from engine.v2 import abilities as AB
from engine.v2.events import Event, ev
from engine.v2.objects import CardInstance, GameObject, StackEntry, TurnEffect
from engine.v2.state import Pending


class EngineInvariantError(AssertionError):
    pass


def _need(cond, msg):
    if not cond:
        raise EngineInvariantError(msg)


# ---------------------------------------------------------------- transaction journal
_LOG = ("log",)
_RNG = ("rng",)


def _same(v):                                             # immutable value (int / str / tuple / Pending*)
    return v                                             # *Pending is replaced, never mutated in place


# How each top-level attribute is saved on first touch (containers are copied so that in-place
# mutation cannot reach the saved copy; stack entries are saved as (entry, field dict)).
_COPY = {
    "pools": lambda v: [dict(p) for p in v],
    "open_cast": lambda v: None if v is None else {**v, "paid": dict(v["paid"]),
                                                   "activations": list(v["activations"])},
    "stack": lambda v: [(e, e.__dict__.copy()) for e in v],
    "objects": dict, "instances": dict, "def_by_ciid": dict, "mull_declared": dict, "mull_bottoms": dict,
    "attack_choices": dict, "block_choices": dict, "blocks": dict, "divisions": dict,
    "retired": set,
    "life": list, "land_played": list, "draw_failed": list, "mull_count": list, "kept": list, "lost": list,
    "life_lost_turn": list, "lands_entered_turn": list,
}


def _keep(s, name):
    t = s.txn
    if name not in t:
        t[name] = _COPY.get(name, _same)(getattr(s, name))


# Journal keys: str = GameState attribute, int = ObjectId (fields of that object),
# tuple = a zone key ((player, zone) or ("bf",)) or one of the markers _LOG / _RNG.
def _obj(s, oid):
    """The live object, its fields saved before their first mutation in this transaction."""
    o = s.objects[oid]
    t = s.txn
    if oid not in t:
        t[oid] = (o, o.__dict__.copy())
    return o


def _zone(s, key):
    t = s.txn
    if key not in t:
        t[key] = list(s.zones[key])
    return s.zones[key]


def _keep_rng(s):
    if _RNG not in s.txn:
        s.txn[_RNG] = s.rng.getstate()


def begin(s) -> bool:
    """Open a transaction if none is open; returns True if the caller owns it. The journal
    dict is reused (cleared) rather than reallocated, to keep allocation (GC) pressure low."""
    if s.txn_open:
        return False
    s.txn_open = True
    s.txn[_LOG] = len(s.log.transitions)
    return True


def end(s):
    s.txn.clear()
    s.txn_open = False


def rollback(s):
    """Restore every copy saved since begin() and truncate the event log."""
    t = s.txn
    for k, v in t.items():
        if k == _LOG:
            del s.log.transitions[v:]
            del s.log._hashes[v:]
        elif k == _RNG:
            s.rng.setstate(v)
        elif k == "stack":
            for e, fields in v:
                e.__dict__.update(fields)
            s.stack = [e for e, _f in v]
        elif isinstance(k, str):
            setattr(s, k, v)
        elif isinstance(k, int):                         # ObjectId: restore the fields in place
            live, fields = v
            live.__dict__.update(fields)
        else:                                            # zone key
            s.zones[k] = v
    end(s)


# ---------------------------------------------------------------- event interning
# Events are immutable values; equal small-domain events (pending / priority / step
# bookkeeping) share one object. Values and hashes are unchanged; it only keeps the
# long-lived event log from allocating ~2k duplicate tuples per game (GC pressure).
# Caveat: lookup is by tuple equality, and 1 == True in Python; only intern events whose
# fields never carry a bool in one game and an int in another (true for every caller
# below), or the repr-based transition hash would depend on process history.
_INTERN: dict = {}


def _iv(e):
    got = _INTERN.get(e)
    if got is None:
        if len(_INTERN) > 20000:
            _INTERN.clear()
        _INTERN[e] = got = e
    return got


# ---------------------------------------------------------------- helpers
def _alloc_oid(s) -> int:
    _keep(s, "next_oid")
    oid = s.next_oid
    s.next_oid += 1
    return oid


def _zone_key(obj_zone, player):
    return ("bf",) if obj_zone == "battlefield" else (player, obj_zone)


def _remove_from_zone(s, o):
    if o.zone == "stack":
        return None
    lst = _zone(s, _zone_key(o.zone, o.owner))
    idx = lst.index(o.oid)
    lst.pop(idx)
    return idx


def _move(s, oid, dest, position, controller, evs, tapped=False):
    """Zone change (CR 400.7): retire oid, create a new object for the same card instance."""
    _need(oid in s.objects and oid not in s.retired, f"move of dead object {oid}")
    o = s.objects[oid]
    src = o.zone
    _need(src != "suspended", f"move of suspended object {oid}")
    _remove_from_zone(s, o)
    _keep(s, "objects")
    _keep(s, "retired")
    del s.objects[oid]
    s.retired.add(oid)
    new = _alloc_oid(s)
    ctrl = o.owner if controller is None else controller
    no = GameObject(oid=new, ciid=o.ciid, owner=o.owner, controller=ctrl if dest == "battlefield" else o.owner,
                    zone=dest, controlled_since=s.turn, tapped=bool(tapped and dest == "battlefield"))
    s.objects[new] = no
    if dest != "stack":
        lst = _zone(s, _zone_key(dest, o.owner))
        if position == "top":
            lst.insert(0, new)
        elif position == "bottom" or position == "end":
            lst.append(new)
        else:
            lst.insert(int(position), new)
    evs.append(ev("ZoneChanged", old=oid, new=new, ciid=o.ciid, frm=src, to=dest))
    if no.tapped:
        evs.append(ev("EntersTapped", oid=new))
    if dest == "battlefield":
        is_land = s.def_by_ciid[o.ciid].is_land
        if is_land:
            _keep(s, "lands_entered_turn")
            s.lands_entered_turn[no.controller] += 1                       # landfall record (this turn)
        s.occ.append(AB.EnterOcc(new, no.controller, is_land))
    return new


# ---------------------------------------------------------------- op handlers
# TOUCHES[name] lists the top-level GameState attributes an op may mutate; commit saves
# them before the handler runs. Objects, zone lists and the RNG are saved inside the
# handlers on first touch (_obj / _zone / _keep_rng).
TOUCHES = {
    "create_card": ("next_ciid", "instances", "def_by_ciid", "objects"),
    "starting_player": ("starting_player",),
    "draw": ("draw_failed",),
    "mull_declare": ("mull_declared",),
    "mull_round_reset": ("mull_declared",),
    "mull_count_inc": ("mull_count",),
    "keep": ("kept",),
    "store_bottom": ("mull_bottoms",),
    "clear_bottoms": ("mull_bottoms",),
    "begin_turn": ("turn", "active", "land_played", "life_lost_turn", "lands_entered_turn"),
    "empty_pools": ("pools",),
    "priority": ("priority", "passes"),
    "pending": ("pending",),
    "land_played": ("land_played",),
    "add_mana": ("pools",),
    "spend_mana": ("pools", "open_cast"),
    "open_cast": ("next_prov", "stack", "open_cast"),
    "set_targets": ("stack",),
    "set_mode": ("stack",),
    "record_activation": ("open_cast",),
    "commit_cast": ("objects", "retired", "stack", "open_cast"),
    "revert_cast": ("stack", "pools", "priority", "passes", "pending", "open_cast", "life"),
    "remove_entry": ("stack",),
    "attack_choice": ("attack_choices",),
    "block_choice": ("block_choices",),
    "declare_attackers": ("attackers", "attack_choices"),
    "declare_blockers": ("blocks", "blocked", "block_choices"),
    "division": ("divisions",),
    "clear_combat": ("attackers", "blocks", "blocked", "divisions", "attack_choices", "block_choices",
                     "first_strike_done", "first_step_strikers"),
    "clear_divisions": ("divisions",),
    "add_turn_effect": ("turn_effects",),
    "cleanup_wear_off": ("turn_effects",),
    "damage_player": ("life", "life_lost_turn"),
    "pay_life": ("life", "life_lost_turn"),
    "push_ability": ("next_ability", "stack"),
    "sacrifice": (),
    "gain_life": ("life",),
    "clear_draw_failed": ("draw_failed",),
    "lose": ("lost",),
    "end_game": ("result", "pending"),
    "stack_trigger": ("pending_triggers", "next_ability", "stack"),
    "drop_trigger": ("pending_triggers",),
    "priority_resume": ("priority_resume",),
    "pending_entry": ("pending_entry",),
    "set_continuation": ("continuation",),
}


def _h_create_card(s, evs, owner, name):
    ciid = s.next_ciid
    s.next_ciid += 1
    s.instances[ciid] = CardInstance(ciid, name, owner)
    from engine.v2.cards import definitions
    s.def_by_ciid[ciid] = definitions()[name]
    oid = _alloc_oid(s)
    s.objects[oid] = GameObject(oid=oid, ciid=ciid, owner=owner, controller=owner, zone="library")
    _zone(s, (owner, "library")).append(oid)
    evs.append(ev("CardCreated", ciid=ciid, oid=oid, owner=owner, name=name))


def _h_starting_player(s, evs, mode, player):
    if mode == "random":
        _keep_rng(s)
        player = s.rng.randrange(2)
        evs.append(ev("RngDraw", purpose="starting_player", value=player))
    _need(player in (0, 1), "bad starting player")
    s.starting_player = player
    evs.append(ev("StartingPlayer", player=player, mode=mode))


def _h_shuffle(s, evs, player):
    _keep_rng(s)
    lib = _zone(s, (player, "library"))
    s.rng.shuffle(lib)
    # The new order is hidden information: the event carries a digest keyed by the (secret) game
    # RNG state, so the transition hash still commits to the order without revealing it.
    commitment = hashlib.sha256((repr(tuple(lib)) + repr(s.rng.getstate())).encode()).hexdigest()[:24]
    evs.append(ev("Shuffled", player=player, commitment=commitment))


def _h_draw(s, evs, player):
    lib = s.zones[(player, "library")]
    if not lib:
        s.draw_failed[player] = True                       # CR 704.5b
        evs.append(ev("DrawFailed", player=player))
        return
    new = _move(s, lib[0], "hand", "end", None, evs)
    evs.append(ev("Drew", player=player, oid=new))


def _h_move(s, evs, oid, dest, position="end", controller=None, tapped=False):
    _move(s, oid, dest, position, controller, evs, tapped)


def _h_set_continuation(s, evs, value):
    s.continuation = value
    evs.append(ev("Continuation", value=tuple(value) if value else None))


def _h_exile_with_counters(s, evs, oid, kind, n):
    """Suspend's special action (CR 702.62a): exile the card with N counters, one zone change."""
    new = _move(s, oid, "exile", "end", None, evs)
    o = _obj(s, new)
    o.counters = tuple(sorted({**dict(o.counters), kind: n}.items()))
    evs.append(ev("CounterAdded", oid=new, counter=kind, n=n))


def _h_remove_counter(s, evs, oid, kind, n):
    o = _obj(s, oid)
    c = dict(o.counters)
    _need(c.get(kind, 0) >= n, "remove of counters that are not there")
    c[kind] -= n
    if not c[kind]:
        del c[kind]
    o.counters = tuple(sorted(c.items()))
    evs.append(ev("CounterRemoved", oid=oid, counter=kind, n=n))
    if kind == "time" and o.zone == "exile" and not c.get("time"):
        s.occ.append(AB.LastCounterOcc(oid, o.owner))                    # CR 702.62a third ability


def _h_pending_entry(s, evs, value):
    s.pending_entry = value
    evs.append(ev("PendingEntry", value=value))


def _h_set(s, evs, attr, value):
    """Bookkeeping fields only (whitelisted); rules fields have dedicated ops."""
    _need(attr in _SETTABLE, f"set of non-bookkeeping field {attr}")
    _keep(s, attr)
    setattr(s, attr, value)
    evs.append(_iv(ev("Set", attr=attr, value=value)))
    if attr == "step":
        s.occ.append(AB.StepOcc(value, s.active))


_SETTABLE = {"mull_stage", "mull_round", "step", "first_strike_done", "attackers", "blocked", "first_step_strikers"}


def _h_mull_declare(s, evs, player, choice):
    _need(player not in s.mull_declared and not s.kept[player], "double declaration")
    s.mull_declared[player] = choice
    evs.append(ev("MulliganDeclared", player=player, choice=choice))


def _h_mull_round_reset(s, evs):
    s.mull_declared = {}
    evs.append(_iv(ev("MulliganRoundReset")))


def _h_mull_count_inc(s, evs, player):
    s.mull_count[player] += 1
    _need(s.mull_count[player] <= 7, "mulligan below zero cards")
    evs.append(ev("MulliganTaken", player=player, count=s.mull_count[player]))


def _h_keep(s, evs, player):
    s.kept[player] = True
    evs.append(ev("Kept", player=player))


def _h_store_bottom(s, evs, player, cards):
    # The event log is not part of any Observation, so the ordered choice is recorded here
    # (hashed) without being revealed to the opponent.
    s.mull_bottoms[player] = tuple(cards)
    evs.append(ev("BottomChosen", player=player, cards=tuple(cards)))


def _h_clear_bottoms(s, evs):
    s.mull_bottoms = {}
    evs.append(_iv(ev("BottomsCleared")))


def _h_begin_turn(s, evs, turn, active):
    s.turn, s.active = turn, active
    s.land_played = [0, 0]
    s.life_lost_turn = [False, False]
    s.lands_entered_turn = [0, 0]
    evs.append(ev("TurnBegan", turn=turn, active=active))


def _h_untap_all(s, evs, player=None):
    """CR 502.3: the ACTIVE player untaps their permanents (resolved when the op applies,
    after any begin_turn earlier in the same transition)."""
    player = s.active if player is None else player
    evs.append(_iv(ev("UntapStep", player=player)))
    for oid in s.zones[("bf",)]:
        o = s.objects[oid]
        if o.controller == player and o.tapped:
            _obj(s, oid).tapped = False
            evs.append(ev("Untapped", oid=oid))


def _h_empty_pools(s, evs):
    lost_any = False
    for p in (0, 1):
        pool = s.pools[p]
        if not any(pool.values()):                      # usually already empty: nothing to do
            continue
        lost = tuple(sorted((c, n) for c, n in pool.items() if n))
        evs.append(ev("ManaEmptied", player=p, mana=lost))
        s.pools[p] = dict.fromkeys("WUBRGC", 0)
        lost_any = True
    if not lost_any:
        evs.append(_NO_MANA_EMPTIED)


_NO_MANA_EMPTIED = ev("ManaEmptied", player=None, mana=())


_PRIORITY_EV: dict = {}
_PENDING: dict = {}                    # (kind, player, info) -> (Pending, Event); Pending is never mutated


def _h_priority(s, evs, player, passes):
    s.priority, s.passes = player, passes
    e = _PRIORITY_EV.get((player, passes))
    if e is None:
        e = _PRIORITY_EV[(player, passes)] = _iv(Event("Priority", (("passes", passes), ("player", player))))
    evs.append(e)


def _h_pending(s, evs, kind, player, info=()):
    k = (kind, player, info)
    got = _PENDING.get(k)
    if got is None:
        info = tuple(info)
        if len(_PENDING) > 20000:
            _PENDING.clear()
        got = _PENDING[k] = (Pending(kind, player, info) if kind else None,
                             _iv(Event("PendingSet", (("info", info), ("pkind", kind), ("player", player)))))
    s.pending = got[0]
    evs.append(got[1])


def _h_land_played(s, evs, player):
    s.land_played[player] += 1
    _need(s.land_played[player] <= 1, "second land this turn")
    evs.append(_iv(ev("LandDropUsed", player=player, count=s.land_played[player])))


def _h_tap(s, evs, oid):
    o = s.objects[oid]
    _need(o.zone == "battlefield" and not o.tapped, f"tap of untapped-invalid {oid}")
    _obj(s, oid).tapped = True
    evs.append(ev("Tapped", oid=oid))


def _h_untap(s, evs, oid):
    o = s.objects[oid]
    _need(o.zone == "battlefield" and o.tapped, f"untap of {oid}")
    _obj(s, oid).tapped = False
    evs.append(ev("Untapped", oid=oid))


def _h_add_mana(s, evs, player, color, n):
    s.pools[player][color] += n
    evs.append(ev("ManaAdded", player=player, color=color, n=n))


def _h_spend_mana(s, evs, player, color, n):
    _need(s.pools[player][color] >= n, "spend of mana not in pool")
    s.pools[player][color] -= n
    if s.open_cast is not None:
        s.open_cast["paid"][color] = s.open_cast["paid"].get(color, 0) + n
    evs.append(ev("ManaSpent", player=player, color=color, n=n))


def _h_open_cast(s, evs, source_oid, controller, cost_name="normal", cost_symbols=None):
    """CR 601.2a-b: the card moves to the stack as a proposed spell; the announced cost (its mana
    cost, an alternative cost, or "free") is fixed for the whole casting transaction."""
    _need(s.open_cast is None, "nested casting transaction")
    o = s.objects[source_oid]
    _need(o.zone in ("hand", "exile") and o.owner == controller, "cast from outside the caster's hand/exile")
    if cost_symbols is None:
        cost_symbols = s.def_by_ciid[o.ciid].cost_symbols
    frm = o.zone
    idx = _remove_from_zone(s, o)
    _obj(s, source_oid).zone = "suspended"
    prov = f"P{s.next_prov}"
    s.next_prov += 1
    s.stack.append(StackEntry(sid=prov, ciid=o.ciid, controller=controller, state="proposed", cost=cost_name))
    s.open_cast = {"prov": prov, "source": source_oid, "from": frm, "index": idx, "controller": controller,
                   "activations": [], "paid": {}, "priority": s.priority, "passes": s.passes,
                   "pending": s.pending.view() if s.pending else None, "cost": tuple(cost_symbols)}
    evs.append(ev("CastProposed", prov=prov, source=source_oid, ciid=o.ciid, controller=controller, frm=frm,
                  cost=cost_name))


def _h_set_mode(s, evs, sid, mode):
    e = s.entry(sid)
    _need(e is not None and e.state == "proposed" and e.mode is None, "mode for a non-proposed entry")
    e.mode = mode
    evs.append(ev("ModeChosen", sid=sid, mode=mode))


def _h_set_targets(s, evs, sid, targets):
    e = s.entry(sid)
    _need(e is not None and e.state == "proposed", "targets for a non-proposed entry")
    e.targets = tuple(targets)
    evs.append(ev("TargetsChosen", sid=sid, targets=tuple(targets)))


def _h_record_activation(s, evs, land_oid, color, life=0):
    _need(s.open_cast is not None, "activation record without a cast")
    s.open_cast["activations"].append((land_oid, color, life))
    evs.append(ev("ActivationRecorded", land=land_oid, color=color, life=life))


def _h_commit_cast(s, evs):
    oc = s.open_cast
    _need(oc is not None, "commit without an open cast")
    cost_symbols = oc["cost"]                                             # the announced cost (CR 601.2f)
    _need(_covers(cost_symbols, oc["paid"]), f"payment {oc['paid']} does not match cost {cost_symbols}")  # CR 601.2h
    src = s.objects[oc["source"]]
    del s.objects[oc["source"]]
    s.retired.add(oc["source"])
    new = _alloc_oid(s)
    s.objects[new] = GameObject(oid=new, ciid=src.ciid, owner=src.owner, controller=oc["controller"],
                                zone="stack", controlled_since=s.turn)
    e = s.entry(oc["prov"])
    e.sid, e.state, e.oid = f"O{new}", "cast", new
    e.mana_spent = sum(oc["paid"].values())                               # recorded for "no mana spent" checks
    s.open_cast = None
    evs.append(ev("SpellCast", sid=e.sid, oid=new, retired=oc["source"], ciid=src.ciid, controller=e.controller,
                  mana_spent=e.mana_spent))
    s.occ.append(AB.CastOcc(e.controller, e.sid, src.ciid, s.def_by_ciid[src.ciid].is_creature, e.mana_spent))


def _covers(symbols, paid) -> bool:
    need = {}
    generic = 0
    for sym in symbols:
        if sym.isdigit():
            generic += int(sym)
        else:
            need[sym] = need.get(sym, 0) + 1
    total_paid = sum(paid.values())
    if total_paid != generic + sum(need.values()):
        return False
    return all(paid.get(c, 0) >= n for c, n in need.items())


def _h_revert_cast(s, evs, reverse_mana):
    """CR 733.1 rollback of an open casting transaction: restore the suspended ObjectId."""
    oc = s.open_cast
    _need(oc is not None, "revert without an open cast")
    _need(not oc["paid"], "revert after payment")
    src = _obj(s, oc["source"])
    src.zone = oc["from"]
    _zone(s, (src.owner, oc["from"])).insert(oc["index"], src.oid)
    s.stack = [e for e in s.stack if e.sid != oc["prov"]]
    if reverse_mana:
        for land, color, life in reversed(oc["activations"]):
            _need(s.pools[oc["controller"]][color] >= 1, "reversed mana already spent")
            s.pools[oc["controller"]][color] -= 1
            _obj(s, land).tapped = False
            if life:                                                        # the whole activation is reversed
                s.life[oc["controller"]] += life
    s.priority, s.passes = oc["priority"], oc["passes"]
    s.pending = Pending(*oc["pending"]) if oc["pending"] else None
    s.open_cast = None
    evs.append(ev("ProposalReverted", prov=oc["prov"], source=src.oid, reversed_mana=bool(reverse_mana)))


def _h_remove_entry(s, evs, sid):
    e = s.entry(sid)
    _need(e is not None, f"remove of missing stack entry {sid}")
    s.stack.remove(e)
    evs.append(ev("StackEntryRemoved", sid=sid))


def _h_attack_choice(s, evs, oid, attacks):
    s.attack_choices[oid] = bool(attacks)
    evs.append(ev("AttackChosen", oid=oid, attacks=bool(attacks)))


def _h_block_choice(s, evs, blocker, attacker):
    s.block_choices[blocker] = attacker
    evs.append(ev("BlockChosen", blocker=blocker, attacker=attacker))


def _h_declare_attackers(s, evs, attackers):
    for a in attackers:
        o = s.objects[a]
        _need(o.zone == "battlefield" and o.controller == s.active and not o.tapped, "illegal attacker")
        if not s.definition(a).has("Vigilance"):          # CR 508.1f, 702.20b
            _obj(s, a).tapped = True
            evs.append(ev("Tapped", oid=a))
    s.attackers = tuple(attackers)
    s.attack_choices = {}
    evs.append(ev("AttackersDeclared", attackers=tuple(attackers)))
    for a in attackers:
        s.occ.append(AB.AttackOcc(a, s.active, 1 - s.active))


def _h_declare_blockers(s, evs, blocks):
    for b, a in blocks:
        o = s.objects[b]
        _need(o.zone == "battlefield" and not o.tapped and o.controller != s.active, "illegal blocker")
        _need(a in s.attackers, "block of a non-attacker")
        if s.definition(a).has("Flying"):                 # CR 702.9b
            _need(s.definition(b).has("Flying"), "non-flyer blocks a flyer")
    s.blocks = dict(blocks)
    s.blocked = tuple(sorted({a for _b, a in blocks}))
    s.block_choices = {}
    evs.append(ev("BlockersDeclared", blocks=tuple(sorted(blocks))))


def _h_division(s, evs, attacker, division):
    s.divisions[attacker] = tuple(division)
    evs.append(ev("DamageDivisionChosen", attacker=attacker, division=tuple(division)))


def _h_clear_combat(s, evs):
    s.attackers, s.blocks, s.blocked, s.divisions = (), {}, (), {}
    s.attack_choices, s.block_choices, s.first_strike_done = {}, {}, False
    s.first_step_strikers = ()
    evs.append(_iv(ev("CombatCleared")))


def _h_damage_creature(s, evs, source, oid, n):
    o = s.objects.get(oid)
    _need(o is not None and o.zone == "battlefield", "damage to a creature not on the battlefield")
    _obj(s, oid).damage += n
    evs.append(ev("DamageDealt", source=source, target=("obj", oid), n=n))


def _h_damage_player(s, evs, source, player, n):
    s.life[player] -= n
    if n > 0:
        s.life_lost_turn[player] = True                                   # CR 120.3a: damage -> life loss
    evs.append(ev("DamageDealt", source=source, target=("player", player), n=n))
    evs.append(ev("LifeChanged", player=player, life=s.life[player], delta=-n))


def _h_pay_life(s, evs, player, n):
    """CR 119.4: payable only with at least that much life; paying life is losing it."""
    _need(n > 0 and s.life[player] >= n, "life payment not possible")
    s.life[player] -= n
    s.life_lost_turn[player] = True
    evs.append(ev("LifePaid", player=player, n=n))
    evs.append(ev("LifeChanged", player=player, life=s.life[player], delta=-n))


def _h_push_ability(s, evs, controller, ciid, source, key, info, targets):
    """An activated ability on the stack (CR 602.2a): an object that is not a card."""
    sid = f"A{s.next_ability}"
    s.next_ability += 1
    s.stack.append(StackEntry(sid=sid, ciid=ciid, controller=controller, state="ability",
                              targets=tuple(targets), ability=key, source=source, info=tuple(info)))
    evs.append(ev("AbilityActivated", sid=sid, key=key, controller=controller, source=source,
                  targets=tuple(targets)))


def _h_sacrifice(s, evs, oid):
    o = s.objects.get(oid)
    _need(o is not None and o.zone == "battlefield", f"sacrifice of a non-permanent {oid}")
    evs.append(ev("Sacrificed", oid=oid, controller=o.controller))
    _move(s, oid, "graveyard", "end", None, evs)


def _h_gain_life(s, evs, player, n):
    _need(n > 0, "life gain of a non-positive amount")
    if s.has_effect("no_lifegain", player):                               # CR 119.7: the gain doesn't happen
        evs.append(ev("LifeGainPrevented", player=player, n=n))
        return
    s.life[player] += n                                                    # CR 119.3
    evs.append(ev("LifeChanged", player=player, life=s.life[player], delta=n))


def _h_add_turn_effect(s, evs, kind, a=None):
    _need(kind in ("no_lifegain", "no_prevention", "indestructible", "double_strike"), f"turn effect {kind}")
    eff = TurnEffect(kind, a)
    if eff not in s.turn_effects:
        s.turn_effects = s.turn_effects + (eff,)
    evs.append(ev("TurnEffectAdded", effect=kind, a=a))


def _h_clear_divisions(s, evs):
    s.divisions = {}
    evs.append(ev("DivisionsCleared"))


def _h_eot_mod(s, evs, oid, p, t):
    o = s.objects[oid]
    _need(o.zone == "battlefield", "EOT modification of a non-permanent")
    o = _obj(s, oid)
    o.eot_power += p
    o.eot_toughness += t
    evs.append(ev("PTModified", oid=oid, p=p, t=t))


def _h_cleanup_wear_off(s, evs):                          # CR 514.2 (simultaneous)
    for oid in s.zones[("bf",)]:
        o = s.objects[oid]
        if o.damage or o.eot_power or o.eot_toughness:
            o = _obj(s, oid)
            o.damage = o.eot_power = o.eot_toughness = 0
    s.turn_effects = ()                                                    # "until end of turn" / "this turn" end
    evs.append(_iv(ev("CleanupWearOff")))


def _h_clear_draw_failed(s, evs, player):
    s.draw_failed[player] = False
    evs.append(_iv(ev("DrawFailedCleared", player=player)))


def _h_lose(s, evs, player, reason):
    s.lost[player] = reason
    evs.append(ev("PlayerLost", player=player, reason=reason))


def _h_end_game(s, evs, result):
    _need(s.result is None, "game already over")
    s.result = tuple(result)
    s.pending = None
    evs.append(ev("GameEnded", result=tuple(result)))


def _h_stack_trigger(s, evs, tid, targets=()):
    """Put a pending triggered ability on the stack (CR 603.3): an object that is not a card."""
    t = next((x for x in s.pending_triggers if x.tid == tid), None)
    _need(t is not None, f"stack of unknown trigger {tid}")
    s.pending_triggers = tuple(x for x in s.pending_triggers if x.tid != tid)
    sid = f"A{s.next_ability}"
    s.next_ability += 1
    s.stack.append(StackEntry(sid=sid, ciid=t.ciid, controller=t.controller, state="ability",
                              targets=tuple(targets), ability=t.key, source=t.source, info=t.info))
    evs.append(ev("TriggerStacked", tid=tid, sid=sid, key=t.key, controller=t.controller, source=t.source,
                  targets=tuple(targets)))


def _h_drop_trigger(s, evs, tid, reason):
    """CR 603.3d: a trigger with no legal choice is removed instead of being put on the stack."""
    _need(any(x.tid == tid for x in s.pending_triggers), f"drop of unknown trigger {tid}")
    s.pending_triggers = tuple(x for x in s.pending_triggers if x.tid != tid)
    evs.append(ev("TriggerRemoved", tid=tid, reason=reason))


def _h_priority_resume(s, evs, value):
    s.priority_resume = value
    evs.append(_iv(ev("PriorityResume", value=value)))


def _h_reveal(s, evs, player, oid):
    """CR 701.20a/b: show a card to all players; it stays in its zone."""
    o = s.objects[oid]
    evs.append(ev("Revealed", player=player, oid=oid, name=s.instances[o.ciid].name))


def _add_triggers(s, evs, found):
    _keep(s, "pending_triggers")
    _keep(s, "next_tid")
    new = []
    for ctrl, src, ciid, key, info in found:
        tid = s.next_tid
        s.next_tid += 1
        new.append(AB.TriggerInstance(tid, ctrl, src, ciid, key, info))
        evs.append(ev("Triggered", tid=tid, key=key, controller=ctrl, source=src, info=info))
    s.pending_triggers = s.pending_triggers + tuple(new)


def _h_note(s, evs, kind, *data):
    evs.append(ev(kind, data=tuple(data)))


HANDLERS = {n[3:]: f for n, f in globals().items() if n.startswith("_h_")}
# op name -> (handler, ((attr, copier), ...)): one lookup per op on the hot path
_DISPATCH = {n: (h, tuple((a, _COPY.get(a, _same)) for a in TOUCHES.get(n, ()))) for n, h in HANDLERS.items()}
assert set(TOUCHES) <= set(HANDLERS), set(TOUCHES) - set(HANDLERS)


def commit(s, kind: str, ops) -> None:
    t = s.txn
    own = not s.txn_open
    if own:
        s.txn_open = True
        t[_LOG] = len(s.log.transitions)
    try:
        evs: list = []
        for name, args in ops:
            d = _DISPATCH.get(name)
            if d is None:
                raise EngineInvariantError(f"unknown op {name}")
            for attr, cp in d[1]:
                if attr not in t:
                    t[attr] = cp(getattr(s, attr))
            n = len(evs)
            d[0](s, evs, *args)
            if len(evs) == n:
                raise EngineInvariantError(f"op {name} produced no event")          # spec section 8
        if s.occ:                                                     # CR 603.2: triggers of this batch
            found = AB.detect(s, s.occ)
            s.occ.clear()
            if found:
                _add_triggers(s, evs, found)
        s.log.append(kind, evs)
        if s.config["check_invariants"]:
            from engine.v2.invariants import check
            check(s, kind)
    except BaseException:
        s.occ.clear()
        if own:
            rollback(s)
        raise
    if own:
        t.clear()
        s.txn_open = False
