"""Casting legality (CR 601.2, 307.1, 115.5) and targets (CR 601.2c, 608.2b). Pure."""
from __future__ import annotations

from engine.v2.rules.mana import mana_variants, payable_with_sources

MAIN_STEPS = ("main1", "main2")
TARGET_SPEC = {                     # effect_key -> what it may target
    "mutagenic_growth": ("creature",),
    "violent_urge": ("creature",),
    "lava_dart": ("creature", "player"),               # "any target" (no planeswalkers / battles supported)
    "lightning_bolt": ("creature", "player"),
    "giant_growth": ("creature",),
    "counterspell": ("spell",),
    "lava_spike": ("player",),
    "lightning_helix": ("creature", "player"),
    "skullcrack": ("player",),
    "rift_bolt": ("creature", "player"),
    "skewer_the_critics": ("creature", "player"),
}
MODAL = {"boros_charm": 3}                                  # effect_key -> number of modes (choose one)
MODE_TARGETS = {                                            # (key, mode) -> target slots (kinds per slot)
    ("boros_charm", 0): (("player",),),                     # 4 damage to target player (no planeswalkers)
    ("boros_charm", 1): (),                                 # permanents you control gain indestructible
    ("boros_charm", 2): (("creature",),),                   # target creature gains double strike
}
# Searing Blaze: "target player or planeswalker and target creature that player ... controls"
DEPENDENT = {"searing_blaze"}


def target_slots(key, mode=None) -> tuple:
    if (key, mode) in MODE_TARGETS:
        return MODE_TARGETS[(key, mode)]
    if key in DEPENDENT:
        return (("player",), ("creature",))
    spec = TARGET_SPEC.get(key)
    return (spec,) if spec else ()


def target_choices(state, key, mode=None, exclude_sid=None) -> list:
    """Every complete legal target assignment (CR 601.2c, 115.1); [()] when untargeted."""
    slots = target_slots(key, mode)
    if not slots:
        return [()]
    if key in DEPENDENT:
        return [(("player", p), ("obj", c)) for p in (0, 1) if state.lost[p] is None
                for c in creatures_on_battlefield(state) if state.objects[c].controller == p]
    return [(t,) for t in options_for_kinds(state, slots[0], exclude_sid)]


def castable_modes(state, key, exclude_sid=None) -> list:
    """CR 700.2a: a mode that would be illegal (no legal targets) can't be chosen."""
    return [m for m in range(MODAL[key]) if has_legal_targets(state, key, m, exclude_sid)]


def has_legal_targets(state, key, mode=None, exclude_sid=None) -> bool:
    """Existence-only form of target_choices (same answer, without building the list)."""
    slots = target_slots(key, mode)
    if not slots:
        return True
    if key in DEPENDENT:
        return any(state.objects[c].controller in (0, 1) and state.lost[state.objects[c].controller] is None
                   for c in creatures_on_battlefield(state))
    kinds = slots[0]
    if "player" in kinds and (state.lost[0] is None or state.lost[1] is None):
        return True
    if "creature" in kinds and creatures_on_battlefield(state):
        return True
    if "spell" in kinds and any(e.state == "cast" and e.sid != exclude_sid for e in state.stack):
        return True
    return False


def slot_still_legal(state, key, i, target, targets) -> bool:
    """CR 608.2b per target; Searing Blaze's creature must still be controlled by the targeted player."""
    if not target_still_legal(state, target, key):
        return False
    if key in DEPENDENT and i == 1:
        return state.objects[target[1]].controller == targets[0][1]
    return True


def creatures_on_battlefield(state) -> list:
    return [oid for oid in state.battlefield() if state.definition(oid).is_creature]


def target_options(state, effect_key, exclude_sid=None) -> list:
    """Legal target choices for a spell with `effect_key` (single-target spells only)."""
    return options_for_kinds(state, TARGET_SPEC.get(effect_key), exclude_sid)


def options_for_kinds(state, spec, exclude_sid=None) -> list:
    """Legal single targets of the given kinds (creature / player / spell)."""
    if not spec:
        return []
    out = []
    if "creature" in spec:
        out += [("obj", oid) for oid in creatures_on_battlefield(state)]
    if "player" in spec:
        out += [("player", 0), ("player", 1)]
    if "spell" in spec:                                   # CR 115.5: not itself
        out += [("stack", e.sid) for e in state.stack if e.state == "cast" and e.sid != exclude_sid]
    return out


def target_still_legal(state, target, effect_key) -> bool:
    """CR 608.2b: a target no longer in the zone it was in when targeted is illegal."""
    kind = target[0]
    if kind == "obj":
        o = state.objects.get(target[1])
        return o is not None and o.zone == "battlefield" and state.definition(o.oid).is_creature
    if kind == "player":
        return state.lost[target[1]] is None
    if kind == "stack":
        e = state.entry(target[1])
        return e is not None and e.state == "cast"
    return False


def activation_target_options(state, player, kinds) -> list:
    """Targets of an activated ability: "own_creature" = target creature you control (equip,
    CR 702.6a); "player" = target player."""
    out = []
    if "own_creature" in kinds:
        out += [("obj", c) for c in creatures_on_battlefield(state) if state.objects[c].controller == player]
    if "player" in kinds:
        out += [("player", p) for p in (0, 1) if state.lost[p] is None]
    return out


def ability_target_still_legal(state, controller, target, kinds) -> bool:
    """CR 608.2b for an activated or triggered ability's target."""
    if target[0] == "obj" and "own_creature" in kinds:
        o = state.objects.get(target[1])
        return (o is not None and o.zone == "battlefield" and state.definition(o.oid).is_creature
                and o.controller == controller)
    return target_still_legal_kinds(state, target, kinds)


def target_still_legal_kinds(state, target, kinds) -> bool:
    """CR 608.2b for an ability whose targets are of the given kinds."""
    if target[0] == "obj" and "creature" not in kinds:
        return False
    if target[0] == "player" and "player" not in kinds:
        return False
    return target_still_legal(state, target, None)


def sorcery_timing_ok(state, player) -> bool:
    """CR 307.1 / 305.2 timing: own main phase, empty stack, has priority."""
    return player == state.active and state.step in MAIN_STEPS and not state.stack


# Flashback with a non-mana cost (CR 702.34a): effect key -> the land subtype of the permanent to sacrifice
FLASHBACK = {"lava_dart": "Mountain"}                     # "Flashback--Sacrifice a Mountain."
PLOT = {"slickshot_show_off": ("1", "R")}                 # "Plot {1}{R}" (CR 702.170a)


class CostVariant(tuple):
    """(name, mana symbols, life, sacrifice subtype or None): one way to announce a spell's total
    cost (CR 601.2b, 601.2f). Plain tuple subclass: hashable, cheap."""
    __slots__ = ()

    def __new__(cls, name, mana, life=0, sacrifice=None):
        return tuple.__new__(cls, (name, tuple(mana), life, sacrifice))

    name = property(lambda self: self[0])
    mana = property(lambda self: self[1])
    life = property(lambda self: self[2])
    sacrifice = property(lambda self: self[3])


def may_play(state, player, oid) -> bool:
    """Expressive Iteration's "You may play the exiled card this turn" for this object."""
    return any(e.kind == "may_play" and e.a == (player, oid) for e in state.turn_effects)


def plotted_turn(state, oid):
    return next((t for o, t in state.plotted if o == oid), None)


def cost_variants(state, player, oid, timing=None) -> list:
    """Every way this player may begin to cast this object now (CR 601.3), with its announced cost:
    from hand (mana cost incl. Phyrexian choices, spectacle), from exile with a play permission
    (mana cost), from exile as a plotted card on a later turn (free, CR 702.170d), from the
    graveyard with flashback (CR 702.34a). Timing per card type (CR 307.1); a plotted card only
    during its owner's main phase with an empty stack."""
    o = state.objects.get(oid)
    if o is None or o.owner != player:
        return []
    d = state.def_by_ciid[o.ciid]
    if d.is_land:
        return []
    if timing is None:
        timing = sorcery_timing_ok(state, player)
    normal_timing = d.is_instant or timing
    zone, key = o.zone, d.effect_key
    out = []
    if zone == "hand" or (zone == "exile" and state.turn_effects and may_play(state, player, oid)):
        if normal_timing:
            out += [CostVariant(n, m, l) for n, m, l in mana_variants(d.cost_symbols)]
            if zone == "hand" and key in _spectacle() and spectacle_ok(state, player):
                out.append(CostVariant("spectacle", _spectacle()[key]))
    if zone == "exile" and state.plotted and timing:
        t = plotted_turn(state, oid)
        if t is not None and t < state.turn:                              # "on a later turn"
            out.append(CostVariant("plot", ()))
    if zone == "graveyard" and key in FLASHBACK and normal_timing:
        out.append(CostVariant("flashback", (), 0, FLASHBACK[key]))
    return out


def variant(state, player, oid, name):
    return next((v for v in cost_variants(state, player, oid) if v.name == name), None)


def sacrifice_options(state, player, subtype) -> list:
    """Permanents the player could sacrifice for a "Sacrifice a <subtype>" cost (tapped or not)."""
    return [x for x in state.zones[("bf",)] if state.objects[x].controller == player
            and subtype in state.definition(x).subtypes]


def can_propose(state, player, oid, v, avail=None, targets_ok=None) -> bool:
    """ProposeCast with this cost variant is legal only when a legal completion exists (spec 7.4):
    legal targets / modes, the mana payable together with any life, a permanent to sacrifice."""
    d = state.def_by_ciid[state.objects[oid].ciid]
    if targets_ok is None:
        targets_ok = {}
    memo = ("castable", d.name, v)                          # per decision: same card + cost -> same answer
    if memo in targets_ok:
        return targets_ok[memo]
    ok = _castable(state, player, d, avail, targets_ok, v)
    targets_ok[memo] = ok
    return ok


def can_propose_cast(state, player, oid, avail=None, timing=None, targets_ok=None, cost=None) -> bool:
    """Compatibility form: the normal mana cost (or `cost` symbols) from hand."""
    o = state.objects.get(oid)
    if o is None or o.zone != "hand" or o.owner != player:
        return False
    if cost is not None:
        d = state.def_by_ciid[o.ciid]
        if d.is_land or not (d.is_instant or (sorcery_timing_ok(state, player) if timing is None else timing)):
            return False
        return can_propose(state, player, oid, CostVariant("alt", cost), avail, targets_ok)
    return any(can_propose(state, player, oid, v, avail, targets_ok)
               for v in cost_variants(state, player, oid, timing) if v.name == "normal")


def cast_proposals(state, player, avail, timing, targets_ok) -> list:
    """(oid, cost name) of every legal ProposeCast: hand, exile (permission / plotted), graveyard
    (flashback)."""
    out = []
    zones = state.zones
    for oid in zones[(player, "hand")]:
        out += [(oid, v.name) for v in cost_variants(state, player, oid, timing)
                if can_propose(state, player, oid, v, avail, targets_ok)]
    if state.plotted or state.turn_effects:
        for oid in zones[(player, "exile")]:
            out += [(oid, v.name) for v in cost_variants(state, player, oid, timing)
                    if can_propose(state, player, oid, v, avail, targets_ok)]
    defs, objs = state.def_by_ciid, state.objects
    for oid in zones[(player, "graveyard")]:
        if defs[objs[oid].ciid].effect_key in FLASHBACK:
            out += [(oid, v.name) for v in cost_variants(state, player, oid, timing)
                    if can_propose(state, player, oid, v, avail, targets_ok)]
    return out


def _castable(state, player, d, avail, targets_ok, v) -> bool:
    key = d.effect_key
    if key in TARGET_SPEC or key in MODAL or key in DEPENDENT:
        if key not in targets_ok:                           # per-decision cache (same answer per key)
            targets_ok[key] = bool(castable_modes(state, key)) if key in MODAL else \
                has_legal_targets(state, key)
        if not targets_ok[key]:
            return False
    if v.sacrifice is not None and not sacrifice_options(state, player, v.sacrifice):
        return False
    return payable_with_sources(state, player, v.mana, avail, v.life)


def can_plot(state, player, oid, timing=None) -> bool:
    """CR 702.170a / 116.2k: from hand, during the player's main phase with an empty stack."""
    o = state.objects.get(oid)
    if o is None or o.zone != "hand" or o.owner != player:
        return False
    if state.def_by_ciid[o.ciid].effect_key not in PLOT:
        return False
    return sorcery_timing_ok(state, player) if timing is None else timing


def _spectacle():
    from engine.v2.abilities import SPECTACLE
    return SPECTACLE


def spectacle_ok(state, player) -> bool:
    """CR 702.137a: an opponent lost life this turn."""
    return state.life_lost_turn[1 - player]


def can_suspend(state, player, oid, timing=None) -> bool:
    """CR 116.2f / 702.62a,c: from hand, only when the player could begin to cast the card."""
    o = state.objects.get(oid)
    if o is None or o.zone != "hand" or o.owner != player:
        return False
    d = state.definition(oid)
    if d.effect_key not in _suspend_keys():
        return False
    return d.is_instant or (sorcery_timing_ok(state, player) if timing is None else timing)


def _suspend_keys():
    from engine.v2.abilities import SUSPEND
    return SUSPEND


def can_play_land(state, player, oid) -> bool:
    """CR 305.1 / 116.2a: a land from hand -- or from exile with a play permission (Expressive
    Iteration) -- during the player's main phase with an empty stack, one land per turn (CR 305.2)."""
    o = state.objects.get(oid)
    if o is None or o.owner != player or not state.definition(oid).is_land:
        return False
    if o.zone != "hand" and not (o.zone == "exile" and may_play(state, player, oid)):
        return False
    return sorcery_timing_ok(state, player) and state.land_played[player] == 0
