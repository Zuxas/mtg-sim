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

from typing import Iterable

# Only the network fallback needs `requests`. A machine with the bulk oracle
# file and no `requests` (the self-hosted CI runner) must still be able to
# import this module, and with it sim.py.
try:
    import requests
except ModuleNotFoundError:
    requests = None

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


def _front(name: str) -> str:
    """Front-face name of 'A // B' (decklists also write 'A / B')."""
    return name.replace(" // ", " / ").split(" / ")[0].strip()


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
    found = {}   # lowercased canonical and face names -> entry
    headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}

    for batch in _chunks(names, _BATCH):
        # The collection endpoint matches a front-face name, not "Front // Back"
        body = {"identifiers": [{"name": _front(n)} for n in batch]}
        try:
            if requests is None:
                raise RuntimeError("the 'requests' package is not installed")
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
            # Double-faced cards keep mana_cost / type_line / P/T on the faces;
            # the game object is the front face (#27).
            faces = c.get("card_faces") or []
            front = faces[0] if faces else {}

            def _field(key, default=""):
                value = c.get(key)
                return value if value not in (None, "") else front.get(key, default)

            entry = {
                "name":           name,
                "mana_cost":      _field("mana_cost"),
                "cmc":            float(c.get("cmc", 0)),
                "type_line":      (c.get("type_line") or "").split(" // ")[0] if faces
                                  else c.get("type_line", ""),
                "oracle_text":    _field("oracle_text"),
                "power":          _field("power", None),
                "toughness":      _field("toughness", None),
                "colors":         _field("colors", []),
                "color_identity": c.get("color_identity", []),
                "scryfall_id":    c.get("id", ""),
                "card_faces":     faces,
                "loyalty":        _field("loyalty", None),
            }
            result[name] = entry
            found[name.lower()] = entry
            # The entry is the FRONT face, so only the front-face name maps to
            # it. A back-face name stays unresolved and fails loudly instead of
            # quietly getting the front face's cost and stats.
            if front.get("name"):
                found.setdefault(front["name"].lower(), entry)

    # Scryfall answers under its canonical name ("Front // Back", canonical
    # capitals). Callers look up the spelling they asked for, so answer under
    # that too.
    for n in names:
        entry = found.get(n.lower()) or found.get(_front(n).lower())
        if n not in result and entry:
            result[n] = entry

    return result
