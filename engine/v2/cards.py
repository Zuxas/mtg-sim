"""Card definitions and the milestone-one SUPPORTED registry.

Printed characteristics come from engine.card_db.CardDB (exact lookup) over the
installed Scryfall snapshot; behaviour comes ONLY from SUPPORTED (effect key +
implementation version). A deck with any other card is refused before a game
starts (UnsupportedCardError). definitions_hash pins exactly what was loaded.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from functools import lru_cache

# name -> (effect_key, implementation version)
SUPPORTED = {
    "Plains": ("basic_land", "1"),
    "Island": ("basic_land", "1"),
    "Mountain": ("basic_land", "1"),
    "Forest": ("basic_land", "1"),
    "Grizzly Bears": ("vanilla_creature", "1"),
    "Hill Giant": ("vanilla_creature", "1"),
    "Raging Goblin": ("vanilla_creature", "1"),
    "Youthful Knight": ("vanilla_creature", "1"),
    "Wind Drake": ("vanilla_creature", "1"),
    "Serra Angel": ("vanilla_creature", "1"),
    "Lightning Bolt": ("lightning_bolt", "1"),
    "Giant Growth": ("giant_growth", "1"),
    "Counterspell": ("counterspell", "1"),
    "Divination": ("divination", "1"),
    "Lava Spike": ("lava_spike", "1"),
    "Lightning Helix": ("lightning_helix", "1"),
    "Monastery Swiftspear": ("monastery_swiftspear", "1"),
    "Goblin Guide": ("goblin_guide", "1"),
}
SUPPORTED_KEYWORDS = frozenset({"Flying", "Haste", "First strike", "Vigilance"})
# Keywords implemented only by specific cards' behaviour (never accepted on any other card).
CARD_KEYWORDS = {
    "monastery_swiftspear": frozenset({"Prowess"}),                 # engine.v2.abilities prowess trigger
}
# effect keys of permanents whose behaviour lives outside engine.v2.effects (no spell effect)
PERMANENT_KEYS = frozenset({"basic_land", "vanilla_creature", "monastery_swiftspear", "goblin_guide"})
BASIC_LAND_COLOR = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
COLORS = ("W", "U", "B", "R", "G", "C")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RR = os.path.join(ROOT, "data", "rules_reference")


class UnsupportedCardError(ValueError):
    def __init__(self, names):
        self.names = sorted(set(names))
        super().__init__(f"cards not supported by engine v2 milestone one: {self.names}")


class CardDataMismatch(RuntimeError):
    pass


@dataclass(frozen=True)
class CardDefinition:
    name: str
    mana_cost: str
    cost_symbols: tuple          # e.g. ("1", "G") -- generic amounts as digit strings
    mana_value: int
    colors: tuple
    supertypes: tuple
    types: tuple
    subtypes: tuple
    power: object                # int or None
    toughness: object
    keywords: tuple
    effect_key: str
    impl_version: str

    def is_type(self, t: str) -> bool:
        return t in self.types

    @property
    def is_land(self) -> bool:
        return "Land" in self.types

    @property
    def is_creature(self) -> bool:
        return "Creature" in self.types

    @property
    def is_permanent_spell(self) -> bool:
        return any(t in self.types for t in ("Creature", "Artifact", "Enchantment", "Planeswalker", "Battle"))

    @property
    def is_instant(self) -> bool:
        return "Instant" in self.types

    def has(self, keyword: str) -> bool:
        return keyword in self.keywords


def parse_cost(mana_cost: str) -> tuple:
    return tuple(re.findall(r"\{([^}]+)\}", mana_cost or ""))


def _split_type_line(type_line: str):
    left, _, right = (type_line or "").partition(" — ")
    words = left.split()
    supers = tuple(w for w in words if w in ("Basic", "Legendary", "Snow", "World"))
    types = tuple(w for w in words if w not in supers)
    return supers, types, tuple(right.split())


def _int_or_none(v):
    return None if v is None else int(v)


@lru_cache(maxsize=1)
def _carddb():
    from engine.card_db import CardDB
    return CardDB()


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@lru_cache(maxsize=1)
def oracle_file_sha256() -> str:
    """sha256 of the installed converted oracle file, checked against SNAPSHOT.json."""
    snap = json.load(open(os.path.join(RR, "SNAPSHOT.json"), encoding="utf-8"))
    expected = snap["files"]["scryfall_oracle_cards.json"].get("installed_sha256")
    actual = _sha256_file(os.path.join(RR, "scryfall_oracle_cards.json"))
    if expected is None or actual != expected:
        raise CardDataMismatch(f"installed oracle file sha256 {actual} != SNAPSHOT.json installed_sha256 {expected}")
    return actual


def build_definition(name: str) -> CardDefinition:
    if name not in SUPPORTED:
        raise UnsupportedCardError([name])
    data = _carddb().get(name)
    if data is None:
        from engine.card_db import UnknownCardError
        raise UnknownCardError([name], {name: _carddb().suggest(name)})
    supers, types, subs = _split_type_line(data.get("type_line", ""))
    kws = tuple(sorted(data.get("keywords") or ()))
    effect_key, version = SUPPORTED[name]
    if not set(kws) <= SUPPORTED_KEYWORDS | CARD_KEYWORDS.get(effect_key, frozenset()):
        raise UnsupportedCardError([name])
    return CardDefinition(
        name=data["name"], mana_cost=data.get("mana_cost", "") or "", cost_symbols=parse_cost(data.get("mana_cost", "")),
        mana_value=int(float(data.get("cmc", 0) or 0)), colors=tuple(data.get("colors") or ()),
        supertypes=supers, types=types, subtypes=subs,
        power=_int_or_none(data.get("power")), toughness=_int_or_none(data.get("toughness")),
        keywords=kws, effect_key=effect_key, impl_version=version)


@lru_cache(maxsize=1)
def definitions() -> dict:
    oracle_file_sha256()                      # refuse to build from an unexpected installed file
    return {n: build_definition(n) for n in sorted(SUPPORTED)}


def definitions_hash(defs: dict | None = None) -> str:
    defs = definitions() if defs is None else defs
    payload = [asdict(defs[n]) for n in sorted(defs)]
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def validate_deck(names) -> None:
    """Every name must resolve exactly and be SUPPORTED; else raise (no game starts)."""
    unknown, unsupported = [], []
    for n in names:
        if _carddb().get(n) is None:
            unknown.append(n)
        elif n not in SUPPORTED:
            unsupported.append(n)
    if unknown:
        from engine.card_db import UnknownCardError
        raise UnknownCardError(sorted(set(unknown)), {u: _carddb().suggest(u) for u in set(unknown)})
    if unsupported:
        raise UnsupportedCardError(unsupported)
