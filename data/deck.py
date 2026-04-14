"""
deck.py — Deck loader

Converts a plain text decklist into a list of Card objects.
Uses the Scryfall scraper from mtg-meta-analyzer to enrich card data.

Decklist format (MTGA/MTGO export, also Moxfield/Goldfish copy-paste):
    // Comment lines are skipped
    4 Lightning Bolt
    4 Goblin Guide
    (blank lines within mainboard are OK — common in creature/land split)
    4 Mountain

    (blank line after 60 cards = sideboard separator)
    2 Path to Exile
"""

import sys
import os

_META_ANALYZER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "mtg-meta-analyzer"
)
if _META_ANALYZER_PATH not in sys.path:
    sys.path.insert(0, os.path.abspath(_META_ANALYZER_PATH))

from scrapers.scryfall import get_cards_data
from data.card import Card, Tag
from engine.keywords import tag_keywords

# DFC / transform cards that Scryfall returns with wrong front-face data.
DFC_CORRECTIONS = {
    "Valley of Gorgoroth": {
        "mana_cost": "", "cmc": 0.0,
        "type_line": "Land",
        "power": None, "toughness": None,
        "oracle_text": "Valley of Gorgoroth enters tapped. T: Add W. T: Add R.",
    },
    "Delver of Secrets": {
        "mana_cost": "{U}", "cmc": 1.0,
        "type_line": "Creature — Human Wizard",
        "power": "1", "toughness": "1",
        "oracle_text": "At the beginning of your upkeep, look at the top card of your library. "
                       "You may reveal it. If it's an instant or sorcery, transform Delver of Secrets.",
    },
    "Mishra's Bauble": {
        "mana_cost": "{0}", "cmc": 0.0,
        "type_line": "Artifact",
        "power": None, "toughness": None,
    },
    "Ornithopter": {
        "mana_cost": "{0}", "cmc": 0.0,
        "type_line": "Artifact Creature — Thopter",
        "power": "0", "toughness": "2",
    },
}


def _parse_decklist(text: str):
    """
    Parse a plain text decklist.
    Rules:
    - // and # lines are comments — skip
    - Blank lines within the first 60 cards are section breaks (creature/land split) — ignore
    - Blank line after 60+ cards = sideboard separator
    - Line "Sideboard" / "sideboard" = explicit sideboard marker
    Returns (mainboard, sideboard) as lists of (qty, name) tuples.
    """
    mainboard, sideboard = [], []
    in_sideboard = False
    main_count = 0

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            # Blank line: only flip to sideboard after 50+ mainboard cards
            if not line and not in_sideboard and main_count >= 50:
                in_sideboard = True
            continue
        if line.lower() in ("sideboard", "maindeck", "companion"):
            if line.lower() == "sideboard":
                in_sideboard = True
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            qty = int(parts[0])
        except ValueError:
            continue
        name = parts[1].strip()
        if in_sideboard:
            sideboard.append((qty, name))
        else:
            mainboard.append((qty, name))
            main_count += qty

    return mainboard, sideboard


def _get_cards_local(names: list[str]) -> dict:
    """
    Load card data from local CardDB (no network calls).
    Falls back to Scryfall API for any cards not found locally.
    """
    try:
        from engine.card_db import CardDB
        db = CardDB()
        result = {}
        missing = []
        for name in names:
            card = db.get(name)
            if card:
                result[name] = {
                    "name":         card.get("name", name),
                    "mana_cost":    card.get("mana_cost", ""),
                    "cmc":          float(card.get("cmc", 0)),
                    "type_line":    card.get("type_line", ""),
                    "oracle_text":  card.get("oracle_text", ""),
                    "power":        card.get("power"),
                    "toughness":    card.get("toughness"),
                    "colors":       card.get("colors", []),
                    "color_identity": card.get("color_identity", []),
                    "scryfall_id":  card.get("id", ""),
                }
            else:
                missing.append(name)

        if missing:
            print(f"  [{len(missing)} cards not in local DB, fetching from Scryfall: {missing[:3]}...]")
            from scrapers.scryfall import get_cards_data
            api_data = get_cards_data(missing)
            result.update(api_data)
        else:
            print(f"  [{len(names)} cards loaded from local DB — no network calls]")

        return result

    except Exception as e:
        # Full fallback to Scryfall API
        print(f"  [CardDB unavailable ({e}), using Scryfall API]")
        from scrapers.scryfall import get_cards_data
        return get_cards_data(names)


def _build_cards(entries, scryfall_data: dict) -> list:
    cards = []
    for qty, name in entries:
        data = scryfall_data.get(name, {})
        corrections = DFC_CORRECTIONS.get(name, {})
        card = Card(
            name=name,
            mana_cost=corrections.get("mana_cost", data.get("mana_cost", "")),
            cmc=float(corrections.get("cmc", data.get("cmc", 0))),
            type_line=corrections.get("type_line", data.get("type_line", "")),
            oracle_text=corrections.get("oracle_text", data.get("oracle_text", "")),
            power=corrections.get("power", data.get("power")),
            toughness=corrections.get("toughness", data.get("toughness")),
            colors=data.get("colors") or [],
            color_identity=data.get("color_identity") or [],
            scryfall_id=data.get("scryfall_id", ""),
        )
        tag_keywords(card)
        # CRITICAL: Each copy must be a SEPARATE object with independent state!
        # [card] * qty creates references to the SAME object — tapping one
        # taps ALL copies across ALL zones (hand, library, battlefield, GY).
        # deepcopy ensures tags (set), counters, etc are also independent.
        import copy
        for _ in range(qty):
            cards.append(copy.deepcopy(card))
    return cards


def load_deck_from_text(text: str):
    main_entries, side_entries = _parse_decklist(text)
    all_names = list({name for _, name in main_entries + side_entries})
    card_data = _get_cards_local(all_names)
    mainboard = _build_cards(main_entries, card_data)
    sideboard = _build_cards(side_entries, card_data)
    print(f"  Loaded: {len(mainboard)} main | {len(sideboard)} sideboard")
    return mainboard, sideboard


def load_deck_from_file(path: str):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    return load_deck_from_text(text)

