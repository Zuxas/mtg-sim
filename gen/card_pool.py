"""
gen/card_pool.py -- Legal + simulatable card pool for a format.

Builds the universe of cards the generator is allowed to use. A card is in the
pool iff:
  1. It is present in the local Scryfall oracle DB (engine/card_db.CardDB), AND
  2. legalities[<format>] == "legal" (engine quirk: is_legal returns True for
     unknown names, so we gate on DB membership ourselves -- iterating the DB
     guarantees every pool card is real), AND
  3. It is NOT in the authoritative ban-list override (gen/ban_list.py).

Each card is tagged with its simulatability bucket (gen/sim_coverage.py) so the
generator can keep non-simulatable cards out of load-bearing slots.

Cache: data/auto_pipeline/<fmt>_pool.json. Rebuilt on --rebuild or when older
than the oracle snapshot.

Usage:
    from gen.card_pool import CardPool
    pool = CardPool.load_or_build("modern")
    pc = pool.get("Lightning Bolt")
    names = pool.simulatable_names()

CLI:
    python gen/card_pool.py [--format modern] [--rebuild] [--stats]
"""

import os
import sys
import json
import time
from dataclasses import dataclass, asdict, field

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from engine.card_db import CardDB
from engine.mana import parse_cost
from gen.sim_coverage import classify_card, SIMULATABLE_BUCKETS
from gen.ban_list import banned_set
from gen import PIPELINE_DATA

ORACLE_PATH = os.path.join(REPO, "data", "rules_reference", "scryfall_oracle_cards.json")

# Scryfall set_type values that are not real, castable game cards.
_SKIP_SET_TYPES = {"memorabilia", "token", "art_series", "minigame"}


@dataclass
class PoolCard:
    name: str
    cmc: float
    mana_cost: str
    type_line: str
    color_identity: list           # e.g. ["R", "W"]
    colors: list                   # e.g. ["R"]
    pips: dict                     # parse_cost(mana_cost): {"generic":N,"W":..}
    is_land: bool
    sim_bucket: str                # one of gen.sim_coverage.ALL_BUCKETS
    simulatable: bool
    family: str = None             # CARD_TO_FAMILY[name] if FAMILY_ONLY

    @property
    def colored_pips(self) -> dict:
        return {c: n for c, n in self.pips.items() if c != "generic"}


class CardPool:
    """The legal + simulatable card universe for one format."""

    def __init__(self, fmt: str, cards: dict):
        self.fmt = fmt
        self._cards: dict = cards    # name -> PoolCard

    # --- access ----------------------------------------------------------
    def __len__(self):
        return len(self._cards)

    def __contains__(self, name):
        return name in self._cards

    def get(self, name: str):
        return self._cards.get(name)

    def legal(self, name: str) -> bool:
        return name in self._cards

    def names(self):
        return set(self._cards.keys())

    def simulatable_names(self) -> set:
        return {n for n, c in self._cards.items() if c.simulatable}

    def lands(self):
        return [c for c in self._cards.values() if c.is_land]

    def nonlands(self):
        return [c for c in self._cards.values() if not c.is_land]

    def by_color_identity(self, identity, simulatable_only=True):
        """Cards whose color identity is a subset of `identity` (set of colors)."""
        ident = set(identity)
        out = []
        for c in self._cards.values():
            if simulatable_only and not c.simulatable:
                continue
            if set(c.color_identity).issubset(ident):
                out.append(c)
        return out

    # --- build -----------------------------------------------------------
    @classmethod
    def build(cls, fmt: str = "modern", db: CardDB = None) -> "CardPool":
        """Filter + classify the oracle DB into a format pool (no cache write)."""
        db = db or CardDB()
        from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
        from engine.effect_family_registry import CARD_TO_FAMILY

        banned = banned_set(fmt)
        fmt_l = fmt.lower()
        cards: dict = {}
        seen = set()

        for card in db._cards:
            name = card.get("name", "")
            if not name or name in seen:
                continue
            if card.get("set_type", "") in _SKIP_SET_TYPES:
                continue
            legalities = card.get("legalities", {})
            if legalities.get(fmt_l, "not_legal") != "legal":
                continue
            if name in banned:
                continue
            seen.add(name)

            mana_cost = card.get("mana_cost") or ""
            type_line = card.get("type_line") or ""
            # MDFC/adventure: top-level cost can be blank -> use the front face.
            if not mana_cost or not type_line:
                faces = card.get("card_faces") or []
                if faces:
                    mana_cost = mana_cost or (faces[0].get("mana_cost") or "")
                    type_line = type_line or (faces[0].get("type_line") or "")

            bucket = classify_card(name, db, ETB_EFFECTS, SPELL_EFFECTS,
                                   CARD_TO_FAMILY, card=card)
            cards[name] = PoolCard(
                name=name,
                cmc=float(card.get("cmc", 0) or 0),
                mana_cost=mana_cost,
                type_line=type_line,
                color_identity=list(card.get("color_identity", []) or []),
                colors=list(card.get("colors", []) or []),
                pips=parse_cost(mana_cost),
                is_land="land" in type_line.lower(),
                sim_bucket=bucket,
                simulatable=bucket in SIMULATABLE_BUCKETS,
                family=CARD_TO_FAMILY.get(name),
            )
        return cls(fmt, cards)

    # --- persistence -----------------------------------------------------
    def cache_path(self) -> str:
        return os.path.join(PIPELINE_DATA, f"{self.fmt}_pool.json")

    def save(self, path: str = None):
        path = path or self.cache_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {
            "format": self.fmt,
            "built_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "count": len(self._cards),
            "cards": [asdict(c) for c in self._cards.values()],
        }
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, fmt: str = "modern", path: str = None) -> "CardPool":
        path = path or os.path.join(PIPELINE_DATA, f"{fmt}_pool.json")
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        cards = {c["name"]: PoolCard(**c) for c in payload["cards"]}
        return cls(payload.get("format", fmt), cards)

    @classmethod
    def load_or_build(cls, fmt: str = "modern", rebuild: bool = False) -> "CardPool":
        """Load the cached pool, rebuilding if missing/stale or rebuild=True."""
        path = os.path.join(PIPELINE_DATA, f"{fmt}_pool.json")
        fresh = (
            not rebuild
            and os.path.exists(path)
            and os.path.exists(ORACLE_PATH)
            and os.path.getmtime(path) >= os.path.getmtime(ORACLE_PATH)
        )
        if fresh:
            try:
                return cls.load(fmt, path)
            except Exception as e:
                print(f"[CardPool] cache load failed ({e}); rebuilding")
        pool = cls.build(fmt)
        pool.save(path)
        return pool

    # --- reporting -------------------------------------------------------
    def bucket_counts(self) -> dict:
        out = {}
        for c in self._cards.values():
            out[c.sim_bucket] = out.get(c.sim_bucket, 0) + 1
        return out


def _main(argv):
    import argparse
    p = argparse.ArgumentParser(description="Build / inspect a format card pool")
    p.add_argument("--format", default="modern")
    p.add_argument("--rebuild", action="store_true")
    p.add_argument("--stats", action="store_true")
    args = p.parse_args(argv)

    pool = CardPool.load_or_build(args.format, rebuild=args.rebuild)
    print(f"Pool [{args.format}]: {len(pool)} legal cards, "
          f"{len(pool.simulatable_names())} simulatable")
    if args.stats:
        for bucket, n in sorted(pool.bucket_counts().items(), key=lambda x: -x[1]):
            print(f"  {bucket:14s} {n}")
        print(f"  lands          {len(pool.lands())}")
    print(f"Cache: {pool.cache_path()}")


if __name__ == "__main__":
    _main(sys.argv[1:])
