"""
gen/notation.py -- Strong card-combination memory.

A Notation records that a specific set of cards co-occurred in decks that scored
well, with an exponentially-weighted strength so repeated observation reinforces
it and stale ones decay. This is the "notations for card combinations that are
particularly strong" store: the optimizer feeds observed fitness deltas in, and
the discovery stage reads the strongest combinations back out to seed novel
archetypes.

Persisted to data/auto_pipeline/notations.json.

Usage:
    store = NotationStore.load()
    store.record(("Amulet of Vigor", "Primeval Titan"), fitness_delta=6.2, deck_id="run3_d12")
    for n in store.top(10):
        print(n.cards, n.strength)
    store.save()
"""

import os
import json
from dataclasses import dataclass, field, asdict

from gen import PIPELINE_DATA

NOTATIONS_PATH = os.path.join(PIPELINE_DATA, "notations.json")

# EWMA smoothing for strength updates: new = (1-a)*old + a*observed.
_ALPHA = 0.35


def canonical(cards) -> tuple:
    """Order-independent canonical key for a card combination."""
    return tuple(sorted(set(cards)))


@dataclass
class Notation:
    cards: tuple
    strength: float = 0.0
    observations: int = 0
    sample_decks: list = field(default_factory=list)
    discovered: str = ""
    note: str = ""

    def key(self) -> tuple:
        return canonical(self.cards)


class NotationStore:
    def __init__(self, notations=None):
        self._by_key: dict = {}     # canonical tuple -> Notation
        for n in (notations or []):
            self._by_key[n.key()] = n

    def __len__(self):
        return len(self._by_key)

    def record(self, cards, fitness_delta: float, deck_id: str = "",
               discovered: str = "", note: str = ""):
        """Update (or create) the notation for `cards` with an observed delta."""
        key = canonical(cards)
        if len(key) < 2:
            return None     # a notation needs at least a pair
        n = self._by_key.get(key)
        if n is None:
            n = Notation(cards=key, strength=fitness_delta, observations=1,
                         discovered=discovered, note=note)
            self._by_key[key] = n
        else:
            n.strength = (1 - _ALPHA) * n.strength + _ALPHA * fitness_delta
            n.observations += 1
            if note and not n.note:
                n.note = note
        if deck_id and deck_id not in n.sample_decks:
            n.sample_decks.append(deck_id)
            n.sample_decks = n.sample_decks[-10:]   # keep most recent 10
        return n

    def get(self, cards):
        return self._by_key.get(canonical(cards))

    def top(self, n: int = 20, color_id=None, min_observations: int = 1):
        """Strongest notations, optionally filtered by min observation count."""
        items = [x for x in self._by_key.values() if x.observations >= min_observations]
        items.sort(key=lambda x: -x.strength)
        return items[:n]

    def conjoin_candidates(self, pkg, limit: int = 10):
        """
        Notations whose cards overlap a package's cards/tags -- i.e. combinations
        the package could extend. Used by discovery to propose new package pairings.
        """
        pkg_cards = set(pkg.cards.keys())
        hits = []
        for nt in self._by_key.values():
            if pkg_cards & set(nt.cards):
                hits.append(nt)
        hits.sort(key=lambda x: -x.strength)
        return hits[:limit]

    # --- persistence -----------------------------------------------------
    def save(self, path: str = None):
        path = path or NOTATIONS_PATH
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {"notations": [
            {**asdict(n), "cards": list(n.cards)} for n in self._by_key.values()
        ]}
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, path)
        return path

    @classmethod
    def load(cls, path: str = None) -> "NotationStore":
        path = path or NOTATIONS_PATH
        if not os.path.exists(path):
            return cls()
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
        notations = []
        for d in payload.get("notations", []):
            d = dict(d)
            d["cards"] = tuple(d.get("cards", []))
            notations.append(Notation(**{k: v for k, v in d.items()
                                         if k in Notation.__dataclass_fields__}))
        return cls(notations)
