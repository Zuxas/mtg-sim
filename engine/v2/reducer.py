"""The reducer: the ONLY code that mutates GameState.

commit(state, kind, ops) applies a list of ops as ONE atomic transition: each op is
validated against the current state (an invalid op is an engine bug and raises
EngineInvariantError -- never skipped), emits events, and the transition is appended to
the event log. Invariants run after the whole transition (never mid-transition) when
state.config["check_invariants"] is set.
"""
from __future__ import annotations

from engine.v2.events import ev
from engine.v2.objects import CardInstance, GameObject, StackEntry


class EngineInvariantError(AssertionError):
    pass


def _need(cond, msg):
    if not cond:
        raise EngineInvariantError(msg)


# ---------------------------------------------------------------- helpers
def _alloc_oid(s) -> int:
    oid = s.next_oid
    s.next_oid += 1
    return oid


def _zone_list(s, obj_zone, player):
    return s.zones[("bf",)] if obj_zone == "battlefield" else s.zones[(player, obj_zone)]


def _remove_from_zone(s, o):
    if o.zone == "stack":
        return None
    lst = _zone_list(s, o.zone, o.owner)
    idx = lst.index(o.oid)
    lst.pop(idx)
    return idx


def _move(s, oid, dest, position, controller, evs):
    """Zone change (CR 400.7): retire oid, create a new object for the same card instance."""
    _need(oid in s.objects and oid not in s.retired, f"move of dead object {oid}")
    o = s.objects[oid]
    src = o.zone
    _need(src != "suspended", f"move of suspended object {oid}")
    _remove_from_zone(s, o)
    del s.objects[oid]
    s.retired.add(oid)
    new = _alloc_oid(s)
    ctrl = o.owner if controller is None else controller
    no = GameObject(oid=new, ciid=o.ciid, owner=o.owner, controller=ctrl if dest == "battlefield" else o.owner,
                    zone=dest, controlled_since=s.turn)
    s.objects[new] = no
    if dest != "stack":
        lst = _zone_list(s, dest, o.owner)
        if position == "top":
            lst.insert(0, new)
        elif position == "bottom" or position == "end":
            lst.append(new)
        else:
            lst.insert(int(position), new)
    evs.append(ev("ZoneChanged", old=oid, new=new, ciid=o.ciid, frm=src, to=dest))
    return new


# ---------------------------------------------------------------- op handlers
def _h_create_card(s, evs, owner, name):
    ciid = s.next_ciid
    s.next_ciid += 1
    s.instances[ciid] = CardInstance(ciid, name, owner)
    oid = _alloc_oid(s)
    s.objects[oid] = GameObject(oid=oid, ciid=ciid, owner=owner, controller=owner, zone="library")
    s.zones[(owner, "library")].append(oid)
    evs.append(ev("CardCreated", ciid=ciid, oid=oid, owner=owner, name=name))


def _h_starting_player(s, evs, mode, player):
    if mode == "random":
        player = s.rng.randrange(2)
        evs.append(ev("RngDraw", purpose="starting_player", value=player))
    _need(player in (0, 1), "bad starting player")
    s.starting_player = player
    evs.append(ev("StartingPlayer", player=player, mode=mode))


def _h_shuffle(s, evs, player):
    lib = s.zones[(player, "library")]
    s.rng.shuffle(lib)
    evs.append(ev("Shuffled", player=player, order=tuple(lib)))


def _h_draw(s, evs, player):
    lib = s.zones[(player, "library")]
    if not lib:
        s.draw_failed[player] = True                       # CR 704.5b
        evs.append(ev("DrawFailed", player=player))
        return
    new = _move(s, lib[0], "hand", "end", None, evs)
    evs.append(ev("Drew", player=player, oid=new))


def _h_move(s, evs, oid, dest, position="end", controller=None):
    _move(s, oid, dest, position, controller, evs)


def _h_set(s, evs, attr, value):
    """Bookkeeping fields only (whitelisted); rules fields have dedicated ops."""
    _need(attr in _SETTABLE, f"set of non-bookkeeping field {attr}")
    setattr(s, attr, value)
    evs.append(ev("Set", attr=attr, value=value))


_SETTABLE = {"mull_stage", "mull_round", "step", "first_strike_done", "attackers", "blocked"}


def _h_mull_declare(s, evs, player, choice):
    _need(player not in s.mull_declared and not s.kept[player], "double declaration")
    s.mull_declared[player] = choice
    evs.append(ev("MulliganDeclared", player=player, choice=choice))


def _h_mull_round_reset(s, evs):
    s.mull_declared = {}


def _h_mull_count_inc(s, evs, player):
    s.mull_count[player] += 1
    _need(s.mull_count[player] <= 7, "mulligan below zero cards")
    evs.append(ev("MulliganTaken", player=player, count=s.mull_count[player]))


def _h_keep(s, evs, player):
    s.kept[player] = True
    evs.append(ev("Kept", player=player))


def _h_store_bottom(s, evs, player, cards):
    s.mull_bottoms[player] = tuple(cards)
    evs.append(ev("BottomChosen", player=player))          # hidden: contents not in the event


def _h_clear_bottoms(s, evs):
    s.mull_bottoms = {}


def _h_begin_turn(s, evs, turn, active):
    s.turn, s.active = turn, active
    s.land_played = [0, 0]
    evs.append(ev("TurnBegan", turn=turn, active=active))


def _h_untap_all(s, evs, player):
    for oid in s.zones[("bf",)]:
        o = s.objects[oid]
        if o.controller == player and o.tapped:
            o.tapped = False
            evs.append(ev("Untapped", oid=oid))


def _h_empty_pools(s, evs):
    for p in (0, 1):
        lost = {c: n for c, n in s.pools[p].items() if n}
        if lost:
            evs.append(ev("ManaEmptied", player=p, mana=tuple(sorted(lost.items()))))
        s.pools[p] = dict.fromkeys("WUBRGC", 0)


def _h_priority(s, evs, player, passes):
    s.priority, s.passes = player, passes
    evs.append(ev("Priority", player=player, passes=passes))


def _h_pending(s, evs, kind, player, info=()):
    from engine.v2.state import Pending
    s.pending = Pending(kind, player, tuple(info)) if kind else None


def _h_land_played(s, evs, player):
    s.land_played[player] += 1
    _need(s.land_played[player] <= 1, "second land this turn")


def _h_tap(s, evs, oid):
    o = s.objects[oid]
    _need(o.zone == "battlefield" and not o.tapped, f"tap of untapped-invalid {oid}")
    o.tapped = True
    evs.append(ev("Tapped", oid=oid))


def _h_untap(s, evs, oid):
    o = s.objects[oid]
    _need(o.zone == "battlefield" and o.tapped, f"untap of {oid}")
    o.tapped = False
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


def _h_open_cast(s, evs, source_oid, controller):
    _need(s.open_cast is None, "nested casting transaction")
    o = s.objects[source_oid]
    _need(o.zone == "hand" and o.owner == controller, "cast from outside the caster's hand")
    idx = _remove_from_zone(s, o)
    o.zone = "suspended"
    prov = f"P{s.next_prov}"
    s.next_prov += 1
    s.stack.append(StackEntry(sid=prov, ciid=o.ciid, controller=controller, state="proposed"))
    s.open_cast = {"prov": prov, "source": source_oid, "from": "hand", "index": idx, "controller": controller,
                   "activations": [], "paid": {}, "priority": s.priority, "passes": s.passes,
                   "pending": s.pending.view() if s.pending else None}
    evs.append(ev("CastProposed", prov=prov, source=source_oid, ciid=o.ciid, controller=controller))


def _h_set_targets(s, evs, sid, targets):
    e = s.entry(sid)
    _need(e is not None and e.state == "proposed", "targets for a non-proposed entry")
    e.targets = tuple(targets)
    evs.append(ev("TargetsChosen", sid=sid, targets=tuple(targets)))


def _h_record_activation(s, evs, land_oid, color):
    _need(s.open_cast is not None, "activation record without a cast")
    s.open_cast["activations"].append((land_oid, color))


def _h_commit_cast(s, evs, cost_symbols):
    oc = s.open_cast
    _need(oc is not None, "commit without an open cast")
    _need(_covers(cost_symbols, oc["paid"]), f"payment {oc['paid']} does not match cost {cost_symbols}")  # CR 601.2h
    src = s.objects[oc["source"]]
    del s.objects[oc["source"]]
    s.retired.add(oc["source"])
    new = _alloc_oid(s)
    s.objects[new] = GameObject(oid=new, ciid=src.ciid, owner=src.owner, controller=oc["controller"],
                                zone="stack", controlled_since=s.turn)
    e = s.entry(oc["prov"])
    e.sid, e.state, e.oid = f"O{new}", "cast", new
    s.open_cast = None
    evs.append(ev("SpellCast", sid=e.sid, oid=new, retired=oc["source"], ciid=src.ciid, controller=e.controller))


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
    src = s.objects[oc["source"]]
    src.zone = oc["from"]
    s.zones[(src.owner, oc["from"])].insert(oc["index"], src.oid)
    s.stack = [e for e in s.stack if e.sid != oc["prov"]]
    if reverse_mana:
        for land, color in reversed(oc["activations"]):
            _need(s.pools[oc["controller"]][color] >= 1, "reversed mana already spent")
            s.pools[oc["controller"]][color] -= 1
            s.objects[land].tapped = False
    s.priority, s.passes = oc["priority"], oc["passes"]
    from engine.v2.state import Pending
    s.pending = Pending(*oc["pending"]) if oc["pending"] else None
    s.open_cast = None
    evs.append(ev("ProposalReverted", prov=oc["prov"], source=src.oid, reversed_mana=bool(reverse_mana)))


def _h_remove_entry(s, evs, sid):
    e = s.entry(sid)
    _need(e is not None, f"remove of missing stack entry {sid}")
    s.stack.remove(e)


def _h_attack_choice(s, evs, oid, attacks):
    s.attack_choices[oid] = bool(attacks)


def _h_block_choice(s, evs, blocker, attacker):
    s.block_choices[blocker] = attacker


def _h_declare_attackers(s, evs, attackers):
    for a in attackers:
        o = s.objects[a]
        _need(o.zone == "battlefield" and o.controller == s.active and not o.tapped, "illegal attacker")
        if not s.definition(a).has("Vigilance"):          # CR 508.1f, 702.20b
            o.tapped = True
            evs.append(ev("Tapped", oid=a))
    s.attackers = tuple(attackers)
    s.attack_choices = {}
    evs.append(ev("AttackersDeclared", attackers=tuple(attackers)))


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


def _h_clear_combat(s, evs):
    s.attackers, s.blocks, s.blocked, s.divisions = (), {}, (), {}
    s.attack_choices, s.block_choices, s.first_strike_done = {}, {}, False


def _h_damage_creature(s, evs, source, oid, n):
    o = s.objects.get(oid)
    _need(o is not None and o.zone == "battlefield", "damage to a creature not on the battlefield")
    o.damage += n
    evs.append(ev("DamageDealt", source=source, target=("obj", oid), n=n))


def _h_damage_player(s, evs, source, player, n):
    s.life[player] -= n
    evs.append(ev("DamageDealt", source=source, target=("player", player), n=n))
    evs.append(ev("LifeChanged", player=player, life=s.life[player], delta=-n))


def _h_eot_mod(s, evs, oid, p, t):
    o = s.objects[oid]
    _need(o.zone == "battlefield", "EOT modification of a non-permanent")
    o.eot_power += p
    o.eot_toughness += t
    evs.append(ev("PTModified", oid=oid, p=p, t=t))


def _h_cleanup_wear_off(s, evs):                          # CR 514.2 (simultaneous)
    for oid in s.zones[("bf",)]:
        o = s.objects[oid]
        if o.damage or o.eot_power or o.eot_toughness:
            o.damage = o.eot_power = o.eot_toughness = 0
    evs.append(ev("CleanupWearOff"))


def _h_clear_draw_failed(s, evs, player):
    s.draw_failed[player] = False


def _h_lose(s, evs, player, reason):
    s.lost[player] = reason
    evs.append(ev("PlayerLost", player=player, reason=reason))


def _h_end_game(s, evs, result):
    _need(s.result is None, "game already over")
    s.result = tuple(result)
    s.pending = None
    evs.append(ev("GameEnded", result=tuple(result)))


def _h_note(s, evs, kind, *data):
    evs.append(ev(kind, data=tuple(data)))


HANDLERS = {n[3:]: f for n, f in globals().items() if n.startswith("_h_")}


def commit(s, kind: str, ops) -> None:
    evs: list = []
    for o in ops:
        h = HANDLERS.get(o.name)
        _need(h is not None, f"unknown op {o.name}")
        h(s, evs, *o.args)
    s.log.append(kind, evs)
    if s.config.get("check_invariants"):
        from engine.v2.invariants import check
        check(s, kind)
