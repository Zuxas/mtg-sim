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

from data.scryfall_client import get_cards_data
from data.card import Card, Tag
from engine.keywords import tag_keywords

# Through the Omenpaths (OM1) is the Arena/MTGO reskin of Marvel's Spider-Man:
# same cards, different printed names. The oracle file only has the paper
# names, and the APLs and handlers use those too, so decklists exported from
# Arena are read as the paper card. Add a pair here when a list uses a new one.
ARENA_NAMES = {
    "Kavaero, Mind-Bitten":        "Superior Spider-Man",
    "Detect Intrusion":            "Spider-Sense",
    "Belion, the Parched":         "Hydro-Man, Fluid Felon",
    "Ademi of the Silkchutes":     "Spectacular Spider-Man",
    "Leyline Weaver":              "Spider Manifestation",
    "Makdee and Itla, Skysnarers": "Spider-Woman, Stunning Savior",
}

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
        name = ARENA_NAMES.get(name, name)
        if in_sideboard:
            sideboard.append((qty, name))
        else:
            mainboard.append((qty, name))
            main_count += qty

    return mainboard, sideboard


def _get_cards_local(names: list[str]) -> dict:
    """
    Card data from the local oracle file (scripts/fetch_scryfall_bulk.sh).

    No network by default: a sim that quietly asks the Scryfall API for every
    deck it loads is slow, gets rate-limited, and gives different cards on
    different days. A missing file is an error; a name that is not in the
    file is left out and reported by _build_cards as unresolved. Set
    MTG_SIM_ALLOW_NETWORK=1 to let missing names fall back to the API.
    """
    import os
    from engine.card_db import CardDB
    allow_network = bool(os.environ.get("MTG_SIM_ALLOW_NETWORK"))
    db = CardDB()
    if not db._loaded and not allow_network:
        raise FileNotFoundError(
            "local Scryfall data not found (data/rules_reference/scryfall_oracle_cards.json). "
            "Run scripts/fetch_scryfall_bulk.sh once, or set MTG_SIM_ALLOW_NETWORK=1 "
            "to look cards up on the Scryfall API instead.")
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
                # Stage 1 of T1.3+T1.4 transform arc: pass through
                # card_faces and loyalty so _build_cards can populate
                # Card.front_face / back_face / loyalty for DFC cards.
                "card_faces":   card.get("card_faces", []),
                "loyalty":      card.get("loyalty"),
            }
        else:
            missing.append(name)

    if missing and allow_network:
        print(f"  [{len(missing)} cards not in local DB, fetching from Scryfall: {missing[:3]}...]")
        result.update(get_cards_data(missing))
    elif not missing:
        print(f"  [{len(names)} cards loaded from local DB - no network calls]")
    return result


class UnresolvedCardError(ValueError):
    """A decklist name has no card data (typo, new card, or lookup offline)."""


def _build_cards(entries, scryfall_data: dict) -> list:
    # A name with no data used to become a blank Card (no type, cmc 0, no P/T)
    # and the sim ran on it without a word (#27). DFC_CORRECTIONS entries carry
    # their own data, so they count as resolved.
    unresolved = sorted({name for _, name in entries
                         if not scryfall_data.get(name) and name not in DFC_CORRECTIONS})
    if unresolved:
        msg = (f"{len(unresolved)} card name(s) could not be resolved: "
               + ", ".join(repr(n) for n in unresolved[:10])
               + (" ..." if len(unresolved) > 10 else "")
               + ". Check the spelling, refresh the local data with "
                 "scripts/fetch_scryfall_bulk.sh, or add an Arena name to ARENA_NAMES in "
                 "data/deck.py. Set MTG_SIM_ALLOW_UNRESOLVED=1 to load them as blank cards.")
        import os
        if not os.environ.get("MTG_SIM_ALLOW_UNRESOLVED"):
            raise UnresolvedCardError(msg)
        print(f"  [!UNRESOLVED] {msg}")
    cards = []
    for qty, name in entries:
        data = scryfall_data.get(name, {})
        corrections = DFC_CORRECTIONS.get(name, {})
        # DFC face plumbing (Stage 1 of T1.3+T1.4 transform arc):
        # If card has 2 card_faces, populate front_face/back_face for
        # later use by gs.transform(). For non-DFC cards both stay None.
        card_faces = data.get("card_faces") or []
        front_face = card_faces[0] if len(card_faces) >= 2 else None
        back_face = card_faces[1] if len(card_faces) >= 2 else None
        # Planeswalker loyalty: initialize from card_db. Some PWs are
        # transform back-faces (Ajani Avenger) so loyalty starts at 0
        # on the front-face card; gs.transform() reads from back_face
        # at flip time. Single-face PWs get loyalty here directly.
        try:
            loyalty = int(data.get("loyalty") or 0)
        except (TypeError, ValueError):
            loyalty = 0
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
            loyalty=loyalty,
            front_face=front_face,
            back_face=back_face,
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
    # A list with a card nobody could identify still loads, but it is not the
    # registered 75, so say so every time it is used.
    marked = [l for l in text.splitlines() if l.strip().startswith("// UNRESOLVED")]
    if marked:
        print(f"  [!INCOMPLETE DECK] {len(marked)} line(s) marked UNRESOLVED: "
              f"this is not the full registered list; do not treat its results as validated")
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

