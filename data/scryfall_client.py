"""
data/scryfall_client.py - minimal Scryfall API fallback.

Used by data/deck.py when a card name isn't found in the local CardDB
bulk (e.g., a very recent release not yet in the bundled oracle_cards.json).
Returns {name: {9 fields}} matching the shape deck.py expects.

Scryfall's /cards/collection endpoint takes up to 75 identifiers per call.
This module batches accordingly and falls back silently for any card that
Scryfall doesn't recognize.

Network dependency: requires internet at call time. If offline, results are
empty and deck.py skips the affected cards with empty field defaults.

Attribution: Card data from Scryfall (https://scryfall.com).
Magic: The Gathering is (c) Wizards of the Coast.
"""

import requests
from typing import Iterable

_ENDPOINT = "https://api.scryfall.com/cards/collection"
_BATCH = 75
_USER_AGENT = "mtg-sim/1.0"
_FIELDS = (
    "name", "mana_cost", "cmc", "type_line", "oracle_text",
    "power", "toughness", "colors", "color_identity",
)


def _chunks(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def get_cards_data(names: Iterable[str]) -> dict:
    """Resolve card names to a small dict of gameplay-relevant fields.

    Returns a dict keyed by the input name. Cards Scryfall doesn't find
    are absent from the output (same contract as the old scrapers.scryfall
    get_cards_data that this replaces).
    """
    names = list({n for n in names if n})
    if not names:
        return {}

    result = {}
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}

    for batch in _chunks(names, _BATCH):
        body = {"identifiers": [{"name": n} for n in batch]}
        try:
            r = requests.post(_ENDPOINT, json=body, headers=headers, timeout=10)
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            print(f"  [scryfall_client] request failed: {e}")
            continue

        for c in payload.get("data", []):
            name = c.get("name")
            if not name:
                continue
            result[name] = {
                "name":           c.get("name", name),
                "mana_cost":      c.get("mana_cost", ""),
                "cmc":            float(c.get("cmc", 0)),
                "type_line":      c.get("type_line", ""),
                "oracle_text":    c.get("oracle_text", ""),
                "power":          c.get("power"),
                "toughness":      c.get("toughness"),
                "colors":         c.get("colors", []),
                "color_identity": c.get("color_identity", []),
                "scryfall_id":    c.get("id", ""),
            }

    return result
