"""
engine/sideboard.py — Parse and apply sideboard plans

Handles:
  - Parsing messy sb_in/sb_out strings from tac team guides
    "1 Clarion Conqueror +1 Damping Sphere +3 Charmaw" → [(1, "Clarion Conqueror"), ...]
  - Applying swaps to a mainboard deck list
  - Fuzzy card name matching against actual sideboard
"""

import re
from copy import deepcopy
from typing import Optional


# ---------------------------------------------------------------------------
# Parser — messy string → [(qty, card_name)]
# ---------------------------------------------------------------------------

def parse_sb_string(raw: str) -> list[tuple[int, str]]:
    """
    Parse sideboard strings from tac team guides.

    Handles formats like:
      "1 Clarion Conqueror +1 Damping Sphere +3 Charmaw"
      "-2 Blood Moon -3 Ragavan"
      "2 Spell Pierce, 3 Ral, 1 Crab"
      "+2 Wear//Tear +1 Wrath of the Skies"
    """
    raw = raw.strip().lstrip('+-"')
    # Normalize separators
    raw = re.sub(r'\s*[,;]\s*', ' +', raw)
    raw = re.sub(r'\s+', ' ', raw)

    results = []
    # Pattern: optional +/- then qty then card name until next +/- qty
    pattern = re.compile(r'[+\-]?\s*(\d+)\s+([A-Za-z][^+\-\d][^+\-]*?)(?=\s*[+\-]?\s*\d+\s+[A-Za-z]|\Z)')

    for m in pattern.finditer(raw):
        qty  = int(m.group(1))
        name = m.group(2).strip().strip('"-')
        # Clean trailing punctuation
        name = re.sub(r'\s+$', '', name)
        if qty > 0 and len(name) > 2:
            results.append((qty, name))

    return results


def _fuzzy_match(card_name: str, deck_names: list[str]) -> Optional[str]:
    """Case-insensitive fuzzy match of card name against a list."""
    name_clean = re.sub(r"[^a-z0-9]", "", card_name.lower())

    # Exact match
    for n in deck_names:
        if re.sub(r"[^a-z0-9]", "", n.lower()) == name_clean:
            return n

    # Prefix match (first word)
    first_word = name_clean[:8]
    for n in deck_names:
        if re.sub(r"[^a-z0-9]", "", n.lower()).startswith(first_word):
            return n

    # Substring match
    for n in deck_names:
        if name_clean in re.sub(r"[^a-z0-9]", "", n.lower()):
            return n

    return None


# ---------------------------------------------------------------------------
# Apply sideboard swaps to a deck
# ---------------------------------------------------------------------------

def apply_sideboard_plan(
    mainboard:  list,     # list[Card] — will be copied
    sideboard:  dict,     # {card_name: qty} — available sb cards
    sb_in_raw:  list[str],  # raw sb_in strings from matchup
    sb_out_raw: list[str],  # raw sb_out strings from matchup
) -> list:
    """
    Apply a sideboard plan to a deck and return the modified 60-card list.

    Parses the raw strings, matches card names fuzzily, removes sb_out
    cards from mainboard and adds sb_in cards from sideboard.
    Returns a new list without modifying the originals.
    """
    from copy import deepcopy

    deck = deepcopy(mainboard)
    sb   = deepcopy(sideboard)  # {name: qty}

    # Parse all in/out strings
    cards_in:  list[tuple[int, str]] = []
    cards_out: list[tuple[int, str]] = []

    for raw in sb_in_raw:
        cards_in.extend(parse_sb_string(raw))
    for raw in sb_out_raw:
        cards_out.extend(parse_sb_string(raw))

    deck_names = [c.name for c in deck]
    sb_names   = list(sb.keys())

    # Remove sb_out cards from deck
    removed = 0
    for qty, name in cards_out:
        matched = _fuzzy_match(name, deck_names)
        if not matched:
            continue
        to_remove = qty
        new_deck  = []
        for card in deck:
            if card.name == matched and to_remove > 0:
                to_remove -= 1
                removed   += 1
            else:
                new_deck.append(card)
        deck = new_deck

    # Add sb_in cards to deck
    added = 0
    for qty, name in cards_in:
        matched = _fuzzy_match(name, sb_names)
        if not matched:
            continue
        available = sb.get(matched, 0)
        to_add    = min(qty, available)
        if to_add <= 0:
            continue

        # Find a template card from sideboard
        from data.card import Card
        template = None
        # We'll create placeholder cards — Scryfall data loaded lazily
        for _ in range(to_add):
            card = _make_sb_card(matched)
            if card:
                deck.append(card)
                added += 1

        sb[matched] = available - to_add

    return deck


def _make_sb_card(card_name: str):
    """Create a Card object for a sideboard card, fetching from Scryfall cache."""
    try:
        from data.deck import _fetch_card_data
        data = _fetch_card_data(card_name)
        if data:
            from data.card import Card
            return Card(
                name=data.get("name", card_name),
                mana_cost=data.get("mana_cost", ""),
                cmc=float(data.get("cmc", 2)),
                type_line=data.get("type_line", "Unknown"),
                oracle_text=data.get("oracle_text", ""),
                power=data.get("power"),
                toughness=data.get("toughness"),
                colors=data.get("colors", []),
            )
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Lookup sideboard plan from playbook data
# ---------------------------------------------------------------------------

def get_sb_plan(
    our_deck:  str,    # e.g. "Boros Energy"
    opponent:  str,    # e.g. "Elves"
    playbooks: dict = None,
) -> tuple[list[str], list[str]]:
    """
    Look up sb_in / sb_out for a matchup from playbook data.
    Returns (sb_in_raw_list, sb_out_raw_list).
    """
    if playbooks is None:
        from apl.playbook_parser import load_all_playbooks, load_all_tac_guides
        playbooks = {**load_all_playbooks(), **load_all_tac_guides()}

    from apl.playbook_parser import find_playbook
    pb = find_playbook(our_deck, playbooks)
    if not pb or not pb.matchups:
        return [], []

    opp_clean = re.sub(r"[^a-z0-9]", "", opponent.lower())
    for matchup in pb.matchups:
        mu_clean = re.sub(r"[^a-z0-9]", "", matchup.opponent.lower())
        if opp_clean in mu_clean or mu_clean in opp_clean:
            return matchup.sb_in, matchup.sb_out

    return [], []
