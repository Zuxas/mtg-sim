"""Characteristics after continuous effects (CR 611.3a, 613.1). Pure; read on demand, never stored.

The supported continuous effects are all additive power/toughness changes (layer 7c) and ability
grants (layer 6), so their order does not matter:
- printed values (CR 613.1: start with the card's printed characteristics, or the token's);
- "until end of turn" modifications recorded on the object (Giant Growth, prowess, Mutagenic Growth);
- Equipment: Cori-Steel Cutter -- "Equipped creature gets +1/+1 and has trample and haste.";
- delirium: Dragon's Rage Channeler -- "As long as there are four or more card types among cards in
  your graveyard, this creature gets +2/+2, has flying, and attacks each combat if able." (CR 207.2c:
  delirium is an ability word -- the condition is the whole rule; CR 611.3a: not locked in);
- typed turn effects: first strike / double strike gained until end of turn.
Fast path: an object that is not equipped, has no static ability and no granting turn effect
reads its printed values directly.
"""
from __future__ import annotations

# CR 205.2a card types that can be among cards in a graveyard (the DRC ruling lists exactly these)
CARD_TYPES = frozenset({"Artifact", "Battle", "Creature", "Enchantment", "Instant", "Kindred", "Land",
                        "Planeswalker", "Sorcery"})
# Equipment effect key -> (power, toughness, granted keywords) for the equipped creature
EQUIPMENT = {"cori_steel_cutter": (1, 1, frozenset({"Trample", "Haste"}))}
# effect key -> (power, toughness, granted keywords) while its delirium condition holds
DELIRIUM = {"dragons_rage_channeler": (2, 2, frozenset({"Flying"}))}
MUST_ATTACK_WITH_DELIRIUM = frozenset({"dragons_rage_channeler"})
_KW_EFFECTS = {"First strike": "first_strike", "Double strike": "double_strike"}


def card_types_in_graveyard(s, player) -> int:
    """Distinct card types among CARDS in the player's graveyard (a multi-type card adds each of its
    types; a token is not a card and never counts)."""
    types = set()
    defs, objs, inst = s.def_by_ciid, s.objects, s.instances
    for oid in s.zones[(player, "graveyard")]:
        ciid = objs[oid].ciid
        if inst[ciid].token:
            continue
        types.update(t for t in defs[ciid].types if t in CARD_TYPES)
    return len(types)


def delirium(s, player) -> bool:
    return card_types_in_graveyard(s, player) >= 4


def _bonus(s, oid, o, d):
    """(power, toughness, keywords) added by continuous effects other than end-of-turn P/T mods."""
    p = t = 0
    kws = frozenset()
    if s.attachments:
        for eq, c in s.attachments.items():
            if c == oid:
                bp, bt, bk = EQUIPMENT[s.def_by_ciid[s.objects[eq].ciid].effect_key]
                p, t, kws = p + bp, t + bt, kws | bk
    grant = DELIRIUM.get(d.effect_key)
    if grant is not None and o.zone == "battlefield" and delirium(s, o.controller):
        p, t, kws = p + grant[0], t + grant[1], kws | grant[2]
    return p, t, kws


def power(s, oid) -> int:
    o = s.objects[oid]
    d = s.def_by_ciid[o.ciid]
    base = (d.power or 0) + o.eot_power
    if not s.attachments and d.effect_key not in DELIRIUM:
        return base
    return base + _bonus(s, oid, o, d)[0]


def toughness(s, oid) -> int:
    o = s.objects[oid]
    d = s.def_by_ciid[o.ciid]
    base = (d.toughness or 0) + o.eot_toughness
    if not s.attachments and d.effect_key not in DELIRIUM:
        return base
    return base + _bonus(s, oid, o, d)[1]


def has_kw(s, oid, keyword) -> bool:
    o = s.objects[oid]
    d = s.def_by_ciid[o.ciid]
    if keyword in d.keywords:
        return True
    kind = _KW_EFFECTS.get(keyword)
    if kind is not None and s.turn_effects and s.has_effect(kind, oid):
        return True
    if not s.attachments and d.effect_key not in DELIRIUM:
        return False
    return keyword in _bonus(s, oid, o, d)[2]


def must_attack(s, oid) -> bool:
    """CR 508.1d: an attack requirement ("attacks each combat if able")."""
    o = s.objects[oid]
    d = s.def_by_ciid[o.ciid]
    return d.effect_key in MUST_ATTACK_WITH_DELIRIUM and delirium(s, o.controller)
