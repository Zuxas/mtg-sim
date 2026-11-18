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
      "1 Clarion Conqueror" — single entry (most common in MATCHUP_SB_PLANS)
      "1 Slickshot Show-Off" — names with hyphens
      "2 Ral, Crackling Wit" — names with commas
      "1 Roaring Furnace // Steaming Sauna" — double-faced names
      "1 Clarion Conqueror +1 Damping Sphere +3 Charmaw" — multi-entry
      "-2 Blood Moon -3 Ragavan" — minus-prefix multi-entry
      "+2 Wear//Tear +1 Wrath of the Skies" — plus-prefix multi-entry

    Returns [(qty, name), ...] in order. Returns empty list if nothing parsed.
    """
    raw = raw.strip().strip('"').lstrip('+- ').rstrip()
    if not raw:
        return []

    # Detect multi-entry form: a "+" or " -" appears followed by qty digits.
    # We split on those separators only — commas/hyphens inside names stay intact.
    has_multi = bool(re.search(r'(?:\s\+|\s-)\s*\d+\s+', raw))

    if has_multi:
        # Split before each "+N name" or "-N name" boundary
        parts = re.split(r'\s+(?=[+\-]\d)', raw)
        # First part has no leading sign; subsequent parts start with +/-
        results = []
        for p in parts:
            p = p.strip().lstrip('+-').strip()
            m = re.match(r'(\d+)\s+(.+)', p)
            if m:
                qty = int(m.group(1))
                name = m.group(2).strip()
                if qty > 0 and len(name) >= 2:
                    results.append((qty, name))
        return results

    # Single-entry form: leading digit + rest is the card name
    m = re.match(r'(\d+)\s+(.+)', raw)
    if m:
        qty = int(m.group(1))
        name = m.group(2).strip()
        if qty > 0 and len(name) >= 2:
            return [(qty, name)]
    return []


_WARNED = set()   # messages already printed by _warn


def _warn(msg: str):
    """Report a sideboarding problem: once per distinct message (a gauntlet
    applies the same plan thousands of times), and raise under SIM_DEBUG."""
    import os
    if os.environ.get("SIM_DEBUG"):
        raise ValueError(msg)
    if msg not in _WARNED:
        _WARNED.add(msg)
        print(f"  [!SIDEBOARD] {msg}")


def _debug() -> bool:
    import os
    return bool(os.environ.get("SIM_DEBUG"))


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _fuzzy_match(card_name: str, deck_names: list[str]) -> Optional[str]:
    """Match a plan's card name against real names (#18).

    Exact match first, ignoring case and punctuation. Otherwise a fuzzy match
    is accepted only if exactly ONE distinct card starts with or contains the
    name. The old 8-character-prefix rule turned "Kozilek's Return" into
    Kozilek's Command. Ambiguous or unknown names return None; the caller
    reports them.
    """
    want = _norm(card_name)
    if not want:
        return None
    distinct = {}
    for n in deck_names:
        distinct.setdefault(_norm(n), n)
    if want in distinct:
        return distinct[want]
    if len(want) < 4:
        return None
    hits = [n for key, n in distinct.items() if want in key]
    return hits[0] if len(hits) == 1 else None


# ---------------------------------------------------------------------------
# Apply sideboard swaps to a deck
# ---------------------------------------------------------------------------

def apply_sideboard_plan(
    mainboard:  list,         # list[Card] — will be copied
    sideboard,                # dict {name: qty} OR list[Card] — auto-normalized
    sb_in_raw:  list[str],    # raw sb_in strings from matchup
    sb_out_raw: list[str],    # raw sb_out strings from matchup
) -> list:
    """
    Apply a sideboard plan to a deck and return the modified 60-card list.

    Parses the raw strings, matches card names fuzzily, removes sb_out
    cards from mainboard and adds sb_in cards from sideboard.
    Returns a new list without modifying the originals.

    sideboard accepts either {name: qty} dict OR a list[Card] (e.g. what
    load_deck_from_file returns) — list form is auto-converted to a dict.
    """
    from copy import deepcopy
    from collections import Counter

    deck = deepcopy(mainboard)
    # Keep a name -> list[Card] index from the original sideboard so we can
    # copy real Card objects (with full mana_cost / oracle / etc.) instead of
    # going to the Scryfall cache. dict-form sideboard has no Card objects so
    # falls back to _make_sb_card.
    sb_card_pool: dict = {}
    if isinstance(sideboard, dict):
        sb = deepcopy(sideboard)
    else:
        sb = dict(Counter(c.name for c in sideboard))
        for c in sideboard:
            sb_card_pool.setdefault(c.name, []).append(c)

    # Parse all in/out strings
    cards_in:  list[tuple[int, str]] = []
    cards_out: list[tuple[int, str]] = []

    for raw in sb_in_raw:
        cards_in.extend(parse_sb_string(raw))
    for raw in sb_out_raw:
        cards_out.extend(parse_sb_string(raw))

    deck_names = [c.name for c in deck]
    sb_names   = list(sb.keys())

    size_before = len(deck)
    what = f"plan in={cards_in} out={cards_out}"

    def match(name, names, where):
        hit = _fuzzy_match(name, names)
        if not hit:
            close = sorted({n for n in names if _norm(name)[:4] and _norm(name)[:4] in _norm(n)})[:4]
            _warn(f"{name!r} not found in the {where}"
                  + (f" (did you mean one of {close}?)" if close else "") + f"; {what}")
        return hit

    # Remove sb_out cards from deck
    removed = []
    for qty, name in cards_out:
        matched = match(name, deck_names, "mainboard")
        if not matched:
            continue
        to_remove = qty
        new_deck  = []
        for card in deck:
            if card.name == matched and to_remove > 0:
                to_remove -= 1
                removed.append(card)
            else:
                new_deck.append(card)
        deck = new_deck
        if to_remove:
            _warn(f"asked to take out {qty} x {matched!r} but the mainboard has "
                  f"{qty - to_remove}; {what}")

    # Add sb_in cards to deck
    added = []
    for qty, name in cards_in:
        matched = match(name, sb_names, "sideboard")
        if not matched:
            continue
        available = sb.get(matched, 0)
        to_add    = min(qty, available)
        if to_add < qty:
            _warn(f"asked to bring in {qty} x {matched!r} but the sideboard has "
                  f"{available}; {what}")
        if to_add <= 0:
            continue

        # Prefer copies of the real Card objects from the supplied sideboard;
        # fall back to Scryfall-cache placeholder if only a dict was provided.
        pool = sb_card_pool.get(matched, [])
        for _ in range(to_add):
            card = deepcopy(pool.pop()) if pool else _make_sb_card(matched)
            if card:
                deck.append(card)
                added.append(card)

        sb[matched] = available - to_add

    # Keep the deck the size it started at. A plan that does not balance is
    # applied as far as it balances: extra cards brought in are left out, and
    # cards taken out with nothing to replace them go back.
    if len(removed) != len(added):
        _warn(f"plan does not balance: {len(added)} in, {len(removed)} out; "
              f"keeping the deck at {size_before} cards; {what}")
    while len(deck) > size_before and added:
        deck.remove(added.pop())
    while len(deck) < size_before and removed:
        deck.append(removed.pop())

    over = sorted(n for n, c in Counter(c.name for c in deck).items()
                  if c > 4 and not any(c2.name == n and "Basic" in (c2.type_line or "") for c2 in deck))
    if over:
        _warn(f"more than 4 copies after sideboarding: {over}; {what}")

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
    Look up sb_in / sb_out for a matchup from playbook HTML data.
    Returns (sb_in_raw_list, sb_out_raw_list).
    
    Uses extract_sb_plans_from_html for real card-level SB plans,
    falling back to cached playbook matchup data.
    """
    import re
    from pathlib import Path
    
    # Try extracting real SB plans directly from HTML first
    try:
        from apl.playbook_parser import extract_sb_plans_from_html, find_playbook
        
        # Find the HTML file for this deck
        # Playbook root: MTG_SIM_PLAYBOOK_DIR, else the sibling My-Website repo
        import os
        root = Path(os.environ.get("MTG_SIM_PLAYBOOK_DIR")
                    or Path(__file__).parent.parent.parent / "My-Website")
        pb_dirs = [root / fmt for fmt in ("modern", "standard", "pioneer")]
        if not any(d.exists() for d in pb_dirs):
            _warn(f"no playbook folders under {root}: no card-level sideboard plans "
                  f"will be found there (set MTG_SIM_PLAYBOOK_DIR)")
        
        deck_slug = re.sub(r"[^a-z0-9]+", "-", our_deck.lower()).strip("-")
        
        for d in pb_dirs:
            if not d.exists():
                continue
            for f in d.glob("*playbook*.html"):
                if deck_slug in f.stem or f.stem.replace("-playbook", "") in deck_slug:
                    plans = extract_sb_plans_from_html(str(f))
                    if plans:
                        # Fuzzy-match opponent name
                        opp_clean = re.sub(r"[^a-z0-9]", "", opponent.lower())
                        for plan in plans:
                            plan_clean = re.sub(r"[^a-z0-9]", "", plan.opponent.lower())
                            if opp_clean in plan_clean or plan_clean in opp_clean:
                                return plan.sb_in, plan.sb_out
                        # Try partial word matching
                        opp_words = [w for w in re.split(r"[^a-z]+", opponent.lower()) if len(w) > 2]
                        for plan in plans:
                            plan_lower = plan.opponent.lower()
                            if any(w in plan_lower for w in opp_words):
                                return plan.sb_in, plan.sb_out
    except Exception as e:
        if _debug():
            raise
        _warn(f"reading playbook HTML for {our_deck!r} failed: {type(e).__name__}: {e}")
    
    # Fallback to cached playbook matchup data
    if playbooks is None:
        try:
            from apl.playbook_parser import load_all_playbooks, load_all_tac_guides
            playbooks = {**load_all_playbooks(), **load_all_tac_guides()}
        except Exception as e:
            if _debug():
                raise
            _warn(f"loading playbooks failed: {type(e).__name__}: {e}")
            return [], []

    try:
        from apl.playbook_parser import find_playbook
        pb = find_playbook(our_deck, playbooks)
        if not pb or not pb.matchups:
            return [], []

        opp_clean = re.sub(r"[^a-z0-9]", "", opponent.lower())
        for matchup in pb.matchups:
            mu_clean = re.sub(r"[^a-z0-9]", "", matchup.opponent.lower())
            if opp_clean in mu_clean or mu_clean in opp_clean:
                return matchup.sb_in, matchup.sb_out
    except Exception as e:
        if _debug():
            raise
        _warn(f"looking up the {our_deck!r} vs {opponent!r} plan failed: {type(e).__name__}: {e}")

    return [], []
