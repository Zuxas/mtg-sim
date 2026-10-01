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
    nth: int = 1                      # spells that player has cast this turn, this one included (flurry)


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


def _suspend_upkeep(s, src, occ):
    o = s.objects[src]
    if isinstance(occ, StepOcc) and occ.step == "upkeep" and occ.active == o.owner and o.counter("time") > 0:
        return ()                                                        # intervening "if this card is suspended"
    return None


def _suspend_last(s, src, occ):
    if isinstance(occ, LastCounterOcc) and occ.oid == src:
        return ()
    return None


def _vortex_free_cast(s, src, occ):
    if isinstance(occ, CastOcc) and occ.mana_spent == 0:                # intervening if (CR 603.4)
        return (occ.player, occ.sid)
    return None


def _second_spell(s, src, occ):
    # Flurry -- "Whenever you cast your second spell each turn" (spells cast before this permanent
    # entered count too: card ruling)
    if isinstance(occ, CastOcc) and occ.nth == 2 and occ.player == s.objects[src].controller:
        return (occ.sid,)
    return None


def _self_enters(s, src, occ):
    if isinstance(occ, EnterOcc) and occ.oid == src:                   # "When this land enters"
        return ()
    return None


_PROWESS = TriggerSpec("prowess", "battlefield", _prowess, (CastOcc,))
TRIGGERS = {                          # effect_key -> TriggerSpecs of that card
    "monastery_swiftspear": (_PROWESS,),
    "monk_token": (_PROWESS,),                                          # "creature token with prowess"
    # "Whenever you cast a noncreature spell, surveil 1." / "...this creature gets +2/+0 until end of turn."
    "dragons_rage_channeler": (TriggerSpec("drc_surveil", "battlefield", _prowess, (CastOcc,)),),
    "slickshot_show_off": (TriggerSpec("slickshot_pump", "battlefield", _prowess, (CastOcc,)),),
    "cori_steel_cutter": (TriggerSpec("flurry", "battlefield", _second_spell, (CastOcc,)),),
    "thundering_falls": (TriggerSpec("falls_surveil", "battlefield", _self_enters, (EnterOcc,)),),
    "goblin_guide": (TriggerSpec("goblin_guide_reveal", "battlefield", _goblin_guide, (AttackOcc,)),),
    "roiling_vortex": (TriggerSpec("vortex_upkeep", "battlefield", _vortex_upkeep, (StepOcc,), ("upkeep",)),
                       TriggerSpec("vortex_free_cast", "battlefield", _vortex_free_cast, (CastOcc,))),
    "rift_bolt": (TriggerSpec("suspend_upkeep", "exile", _suspend_upkeep, (StepOcc,), ("upkeep",)),
                  TriggerSpec("suspend_cast", "exile", _suspend_last, (LastCounterOcc,))),
}
SUSPEND = {"rift_bolt": (1, ("R",))}               # effect_key -> (N time counters, suspend cost) "Suspend 1-{R}"
SPECTACLE = {"skewer_the_critics": ("R",)}         # effect_key -> spectacle cost "Spectacle {R}"
TRIGGER_KEYS = frozenset(TRIGGERS)
SPEC_BY_KEY = {t.key: t for specs in TRIGGERS.values() for t in specs}
_WANTED = frozenset(c for specs in TRIGGERS.values() for t in specs for c in t.on)
_STEPS = frozenset(st for specs in TRIGGERS.values() for t in specs for st in t.steps)


def _relevant(o) -> bool:
    return type(o) in _WANTED and (type(o) is not StepOcc or o.step in _STEPS)


# ------------------------------------------------------------------ delayed triggered abilities (CR 603.7)
class DelayedTrigger(NamedTuple):
    did: int
    controller: int                   # CR 603.7e: the controller of the ability that created it
    source: int                       # CR 603.7e: same source as the creating ability (may be gone)
    ciid: int
    key: str
    turn: int                         # "the next turn's upkeep": the turn number whose upkeep it waits for


DELAYED_STEP = {"bauble_draw": "upkeep"}                               # delayed key -> the step it waits for


def detect_delayed(state, occurrences) -> list:
    """[(did, (controller, source, ciid, key, info))] for delayed triggers whose event occurred;
    each triggers only once (CR 603.7b) -- the reducer removes it."""
    if not state.delayed:
        return []
    out = []
    for occ in occurrences:
        if type(occ) is not StepOcc:
            continue
        for d in state.delayed:
            if DELAYED_STEP[d.key] == occ.step and d.turn == state.turn and all(d.did != x for x, _t in out):
                out.append((d.did, (d.controller, d.source, d.ciid, d.key, ())))
    return out


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
    targets: tuple = ()               # target kinds: "own_creature" (equip), "player"
    sorcery_speed: bool = False       # "Activate only as a sorcery" (CR 602.5d)


_CYCLE_DRAW = ActivatedSpec("land_draw", ("1",), True, 0, True)
ACTIVATED = {                         # effect_key -> activated (non-mana) abilities, in printed order
    "sunbaked_canyon": (_CYCLE_DRAW,),
    "fiery_islet": (_CYCLE_DRAW,),
    # "{T}, Pay 1 life, Sacrifice this land: Search your library for a X or Y card, put it onto the
    # battlefield, then shuffle."
    "arid_mesa": (ActivatedSpec("fetch_mountain_plains", (), True, 1, True),),
    "bloodstained_mire": (ActivatedSpec("fetch_swamp_mountain", (), True, 1, True),),
    "roiling_vortex": (ActivatedSpec("vortex_no_lifegain", ("R",), False, 0, False),),   # {R}: ...
    "scalding_tarn": (ActivatedSpec("fetch_island_mountain", (), True, 1, True),),
    "wooded_foothills": (ActivatedSpec("fetch_mountain_forest", (), True, 1, True),),
    # "Equip {1}{R}" = "{1}{R}: Attach this permanent to target creature you control. Activate only as a
    # sorcery." (CR 702.6a)
    "cori_steel_cutter": (ActivatedSpec("equip", ("1", "R"), False, 0, False, ("own_creature",), True),),
    # "{T}, Sacrifice this artifact: Look at the top card of target player's library. Draw a card at the
    # beginning of the next turn's upkeep."
    "mishras_bauble": (ActivatedSpec("bauble_look", (), True, 0, True, ("player",)),),
}
# fetch ability key -> the land subtypes it searches for (CR 701.23a: "a Mountain or Plains card")
FETCH_TYPES = {"fetch_mountain_plains": ("Mountain", "Plains"), "fetch_swamp_mountain": ("Swamp", "Mountain"),
               "fetch_island_mountain": ("Island", "Mountain"), "fetch_mountain_forest": ("Mountain", "Forest")}


def fetch_matches(state, key, oid) -> bool:
    """Exact search predicate: a card with one of the named land subtypes."""
    return any(t in state.definition(oid).subtypes for t in FETCH_TYPES[key])


# ------------------------------------------------------------------ paused resolutions (typed, hashed)
class Continuation(NamedTuple):
    """A resolution paused for a player's choice (CR 608.2): which entry, which stage, the data
    fixed so far, and a digest checked on resume (corruption guard). Serializable plain values."""
    kind: str
    sid: str
    stage: str
    data: tuple
    digest: str


def continuation(kind, sid, stage, data) -> Continuation:
    import hashlib
    body = repr((kind, sid, stage, tuple(data)))
    return Continuation(kind, sid, stage, tuple(data), hashlib.sha256(body.encode()).hexdigest()[:16])


def check_continuation(c) -> None:
    good = continuation(c.kind, c.sid, c.stage, c.data).digest
    if c.digest != good:
        raise RuntimeError(f"corrupted continuation {c}")

# ability key -> (zone its source must be in, target kinds)
ABILITY_META = {t.key: (t.zone, t.targets) for specs in TRIGGERS.values() for t in specs}
ABILITY_META.update({a.key: ("battlefield", a.targets) for specs in ACTIVATED.values() for a in specs})
ABILITY_META.update({k: (None, ()) for k in DELAYED_STEP})              # no source zone: never "the same object"


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


def _facts_equip(s, e):
    return (s.attachments.get(e.source),)                              # what the Equipment is attached to now


def _facts_bauble(s, e):
    return (s.turn, e.ciid)


FACTS = {"goblin_guide_reveal": _facts_goblin_guide, "equip": _facts_equip, "bauble_look": _facts_bauble}


def still_true(s, e) -> bool:
    """Intervening-if re-check on resolution (CR 603.4)."""
    if e.ability == "vortex_free_cast":
        return True                   # "no mana was spent to cast that spell" is fixed once cast
    if e.ability == "suspend_upkeep":                                    # "if this card is suspended"
        o = s.objects.get(e.source)
        return o is not None and o.zone == "exile" and o.counter("time") > 0
    if e.ability == "suspend_cast":                                      # "if it's exiled"
        o = s.objects.get(e.source)
        return o is not None and o.zone == "exile"
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


def _res_suspend_upkeep(ctx):
    return [op("remove_counter", ctx.source, "time", 1)]


def _res_vortex_upkeep(ctx):
    return [op("damage_player", ctx.source, ctx.info[0], 1)]


def _res_vortex_free_cast(ctx):
    return [op("damage_player", ctx.source, ctx.info[0], 5)]


def _res_land_draw(ctx):
    return [op("draw", ctx.controller)]


def _res_vortex_no_lifegain(ctx):
    return [op("add_turn_effect", "no_lifegain", 1 - ctx.controller)]   # "Your opponents can't gain life this turn."


def _res_slickshot_pump(ctx):
    if not ctx.source_alive:
        return [op("note", "PumpNoTarget", ctx.source)]
    return [op("eot_mod", ctx.source, 2, 0)]


def _res_equip(ctx):
    """CR 702.6a / 701.3b: attach to the (still legal) target; nothing if the Equipment left the
    battlefield, and nothing if it is already attached to that creature."""
    (tgt,) = [t[1] for t in ctx.targets]
    if not ctx.source_alive:
        return [op("note", "EquipSourceGone", ctx.source)]
    if ctx.facts[0] == tgt:
        return [op("note", "AttachNoChange", ctx.source, tgt)]
    return [op("attach", ctx.source, tgt)]


def _res_bauble_look(ctx):
    """Look at the top card of target player's library (privately), then create the delayed
    trigger "Draw a card at the beginning of the next turn's upkeep." (CR 603.7a, 603.7e)."""
    turn, ciid = ctx.facts
    (p,) = [t[1] for t in ctx.targets]
    return [op("look", ctx.controller, p), op("create_delayed", "bauble_draw", ctx.controller, ctx.source, ciid, turn + 1)]


def _res_bauble_draw(ctx):
    return [op("draw", ctx.controller)]


RESOLVE = {
    "slickshot_pump": _res_slickshot_pump,
    "equip": _res_equip,
    "bauble_look": _res_bauble_look,
    "bauble_draw": _res_bauble_draw,
    "land_draw": _res_land_draw,
    "vortex_no_lifegain": _res_vortex_no_lifegain,
    "prowess": _res_prowess,
    "goblin_guide_reveal": _res_goblin_guide,
    "vortex_upkeep": _res_vortex_upkeep,
    "suspend_upkeep": _res_suspend_upkeep,
    "vortex_free_cast": _res_vortex_free_cast,
}

ABILITY_NAMES = {"fetch_island_mountain": "Search for an Island or Mountain card",
                 "fetch_mountain_forest": "Search for a Mountain or Forest card",
                 "equip": "Equip", "bauble_look": "Look at the top card of target player's library",
                 "bauble_draw": "Draw a card (delayed)", "flurry": "Flurry: create a Monk token",
                 "drc_surveil": "Surveil 1", "falls_surveil": "Surveil 1",
                 "slickshot_pump": "Slickshot Show-Off +2/+0",
                 "fetch_mountain_plains": "Search for a Mountain or Plains card",
                 "fetch_swamp_mountain": "Search for a Swamp or Mountain card",
                 "land_draw": "Draw a card", "vortex_no_lifegain": "Opponents can't gain life",
                 "prowess": "Prowess", "goblin_guide_reveal": "Goblin Guide reveal",
                 "vortex_upkeep": "Roiling Vortex upkeep damage",
                 "suspend_upkeep": "Remove a time counter", "suspend_cast": "Cast without paying its mana cost", "vortex_free_cast": "Roiling Vortex free-spell damage"}


def ability_targets(key) -> tuple:
    return SPEC_BY_KEY[key].targets if key in SPEC_BY_KEY else ABILITY_META[key][1]


def context(s, e) -> AbilityContext:
    o = s.objects.get(e.source)
    alive = o is not None and o.zone == ABILITY_META[e.ability][0]
    facts = FACTS[e.ability](s, e) if e.ability in FACTS else ()
    return AbilityContext(e.controller, e.source, alive, tuple(e.info), facts, tuple(e.targets))
