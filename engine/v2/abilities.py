"""Triggered abilities (milestone two, S1). Pure: nothing here mutates GameState.

The reducer records typed OCCURRENCES while it applies a transition (never parsed from the
event log). After the transition's ops, the reducer asks `detect` which triggered abilities
those occurrences trigger (CR 603.2, 603.10 -- objects as they exist after the event) and
records them as pending TriggerInstances in the same atomic transition. The game puts
pending triggers on the stack the next time a player would receive priority, after
state-based actions (CR 117.5, 603.3), active player first (APNAP, CR 603.3b).

Each ability is a typed record keyed by an ability key; its resolution is a pure function
of an AbilityContext built by a pure `facts` function. An intervening-if (CR 603.4) is
checked when the trigger event occurs (in `detect`) and again on resolution (`still_true`).
"""
from __future__ import annotations

from typing import NamedTuple

from engine.v2.ops import op


# ------------------------------------------------------------------ occurrences (typed)
class CastOcc(NamedTuple):            # a spell became cast (CR 601.2i)
    player: int
    sid: str
    ciid: int
    creature: bool
    mana_spent: int


class AttackOcc(NamedTuple):          # a creature was declared as an attacker (CR 508.1)
    oid: int
    controller: int
    defender: int


class StepOcc(NamedTuple):            # a step began (beginning-of-step triggers, CR 503.1a)
    step: str
    active: int


class EnterOcc(NamedTuple):           # a permanent entered the battlefield
    oid: int
    controller: int
    is_land: bool


class LastCounterOcc(NamedTuple):     # the last time counter was removed from an exiled card
    oid: int
    owner: int


# ------------------------------------------------------------------ pending trigger record
class TriggerInstance(NamedTuple):
    tid: int
    controller: int
    source: int                       # source ObjectId at trigger time
    ciid: int                         # source card instance
    key: str                          # ability key
    info: tuple                       # parameters fixed at trigger time


class TriggerSpec(NamedTuple):
    key: str
    zone: str                         # zone the source must be in to trigger
    match: object                     # (state, source_oid, occurrence) -> info tuple | None
    on: tuple                         # occurrence types this ability can match (cheap pre-filter)
    steps: tuple = ()                 # for StepOcc: the steps it can match
    targets: tuple = ()               # target kinds chosen when stacked (CR 603.3d); () = untargeted


# ------------------------------------------------------------------ matchers (trigger time)
def _prowess(s, src, occ):
    if isinstance(occ, CastOcc) and not occ.creature and occ.player == s.objects[src].controller:
        return (occ.sid,)                                               # CR 702.108a
    return None


def _goblin_guide(s, src, occ):
    if isinstance(occ, AttackOcc) and occ.oid == src:
        return (occ.defender,)
    return None


def _vortex_upkeep(s, src, occ):
    if isinstance(occ, StepOcc) and occ.step == "upkeep":
        return (occ.active,)                                            # "each player's upkeep ... to them"
    return None


def _vortex_free_cast(s, src, occ):
    if isinstance(occ, CastOcc) and occ.mana_spent == 0:                # intervening if (CR 603.4)
        return (occ.player, occ.sid)
    return None


TRIGGERS = {                          # effect_key -> TriggerSpecs of that card
    "monastery_swiftspear": (TriggerSpec("prowess", "battlefield", _prowess, (CastOcc,)),),
    "goblin_guide": (TriggerSpec("goblin_guide_reveal", "battlefield", _goblin_guide, (AttackOcc,)),),
    "roiling_vortex": (TriggerSpec("vortex_upkeep", "battlefield", _vortex_upkeep, (StepOcc,), ("upkeep",)),
                       TriggerSpec("vortex_free_cast", "battlefield", _vortex_free_cast, (CastOcc,))),
}
TRIGGER_KEYS = frozenset(TRIGGERS)
SPEC_BY_KEY = {t.key: t for specs in TRIGGERS.values() for t in specs}
_WANTED = frozenset(c for specs in TRIGGERS.values() for t in specs for c in t.on)
_STEPS = frozenset(st for specs in TRIGGERS.values() for t in specs for st in t.steps)


def _relevant(o) -> bool:
    return type(o) in _WANTED and (type(o) is not StepOcc or o.step in _STEPS)


def detect(state, occurrences) -> list:
    """Triggered abilities triggered by `occurrences` (in occurrence order, then by source
    ObjectId, then by the card's ability order). Returns (controller, source, ciid, key, info)."""
    occurrences = [o for o in occurrences if _relevant(o)]
    if not occurrences:
        return []
    sources = [oid for oid in state.zones[("bf",)] if state.definition(oid).effect_key in TRIGGER_KEYS]
    for p in (0, 1):
        sources += [oid for oid in state.zones[(p, "exile")] if state.definition(oid).effect_key in TRIGGER_KEYS]
    if not sources:
        return []
    sources.sort()
    out = []
    for occ in occurrences:
        for src in sources:
            o = state.objects.get(src)
            if o is None:
                continue
            for spec in TRIGGERS[state.definition(src).effect_key]:
                if o.zone != spec.zone or type(occ) not in spec.on:
                    continue
                info = spec.match(state, src, occ)
                if info is not None:
                    ctrl = o.controller if spec.zone == "battlefield" else o.owner      # CR 603.3a
                    out.append((ctrl, src, o.ciid, spec.key, tuple(info)))
    return out


# ------------------------------------------------------------------ activated abilities (S2, CR 602)
class ActivatedSpec(NamedTuple):
    key: str
    mana: tuple                       # mana cost symbols (paid from the pool)
    tap: bool                         # {T} in the cost
    life: int                         # "Pay N life" (CR 119.4)
    sacrifice: bool                   # "Sacrifice this permanent"
    targets: tuple = ()               # (none of the supported activated abilities target)
    sorcery_speed: bool = False


_CYCLE_DRAW = ActivatedSpec("land_draw", ("1",), True, 0, True)
ACTIVATED = {                         # effect_key -> activated (non-mana) abilities, in printed order
    "sunbaked_canyon": (_CYCLE_DRAW,),
    "fiery_islet": (_CYCLE_DRAW,),
}
assert all(not a.targets for specs in ACTIVATED.values() for a in specs)    # no targeted activations yet

# ability key -> (zone its source must be in, target kinds)
ABILITY_META = {t.key: (t.zone, t.targets) for specs in TRIGGERS.values() for t in specs}
ABILITY_META.update({a.key: ("battlefield", a.targets) for specs in ACTIVATED.values() for a in specs})


# ------------------------------------------------------------------ resolution
class AbilityContext(NamedTuple):
    controller: int
    source: int                       # source ObjectId when the ability was created
    source_alive: bool                # still the same object in the same zone
    info: tuple
    facts: tuple                      # ability-specific facts read at resolution
    targets: tuple = ()


def _facts_goblin_guide(s, e):
    defender = e.info[0]
    lib = s.zones[(defender, "library")]
    if not lib:
        return ()
    top = lib[0]
    return (top, s.definition(top).is_land)


FACTS = {"goblin_guide_reveal": _facts_goblin_guide}


def still_true(s, e) -> bool:
    """Intervening-if re-check on resolution (CR 603.4)."""
    if e.ability == "vortex_free_cast":
        return True                   # "no mana was spent to cast that spell" is fixed once cast
    return True


def _res_prowess(ctx):
    if not ctx.source_alive:          # the creature left: "this creature gets +1/+1" affects nothing
        return [op("note", "ProwessNoTarget", ctx.source)]
    return [op("eot_mod", ctx.source, 1, 1)]                             # CR 702.108a, until cleanup


def _res_goblin_guide(ctx):
    if not ctx.facts:                 # empty library: nothing to reveal (CR 609.3)
        return [op("note", "RevealNothing", ctx.info[0])]
    top, is_land = ctx.facts
    out = [op("reveal", ctx.info[0], top)]                               # CR 701.20a/b
    if is_land:
        out.append(op("move", top, "hand", "end"))
    return out


def _res_vortex_upkeep(ctx):
    return [op("damage_player", ctx.source, ctx.info[0], 1)]


def _res_vortex_free_cast(ctx):
    return [op("damage_player", ctx.source, ctx.info[0], 5)]


def _res_land_draw(ctx):
    return [op("draw", ctx.controller)]


RESOLVE = {
    "land_draw": _res_land_draw,
    "prowess": _res_prowess,
    "goblin_guide_reveal": _res_goblin_guide,
    "vortex_upkeep": _res_vortex_upkeep,
    "vortex_free_cast": _res_vortex_free_cast,
}

ABILITY_NAMES = {"land_draw": "Draw a card", "prowess": "Prowess", "goblin_guide_reveal": "Goblin Guide reveal",
                 "vortex_upkeep": "Roiling Vortex upkeep damage", "vortex_free_cast": "Roiling Vortex free-spell damage"}


def ability_targets(key) -> tuple:
    return SPEC_BY_KEY[key].targets if key in SPEC_BY_KEY else ABILITY_META[key][1]


def context(s, e) -> AbilityContext:
    o = s.objects.get(e.source)
    alive = o is not None and o.zone == ABILITY_META[e.ability][0]
    facts = FACTS[e.ability](s, e) if e.ability in FACTS else ()
    return AbilityContext(e.controller, e.source, alive, tuple(e.info), facts, tuple(e.targets))
