"""
gen/ban_list.py -- Authoritative format ban-list override.

The Scryfall `legalities` map (engine/card_db.CardDB.is_legal) is the PRIMARY
legality gate and already encodes the banned list for each format. This module
is a hand-maintained OVERRIDE that catches the window where a local Scryfall
bulk snapshot lags a freshly announced Banned & Restricted update -- the pool
builder intersects both (a card must be Scryfall-legal AND not listed here).

Keep one card per line with the B&R announcement date in a comment. When you
refresh data/rules_reference/scryfall_oracle_cards.json, prune any entries the
snapshot now reflects on its own.
"""

LAST_UPDATED = "2026-06-26"
SOURCE = "WotC Banned & Restricted announcements; cross-checked vs scryfall legalities map"

# Modern banned list (override layer; high-confidence recent + format-defining bans).
MODERN_BANNED = {
    # --- recent, most likely to lag a stale snapshot ---
    "Nadu, Winged Wisdom",        # banned 2024-08
    "Grief",                      # banned 2024-08
    "Fury",                       # banned 2024-08
    "The One Ring",               # banned 2024-08
    "Underworld Breach",          # banned 2025
    # --- long-standing format-defining bans ---
    "Hogaak, Arisen Necropolis",
    "Mox Opal",
    "Faithless Looting",
    "Oko, Thief of Crowns",
    "Simian Spirit Guide",
    "Lurrus of the Dream-Den",
    "Tibalt's Trickery",
    "Mycosynth Lattice",
}

# Format suffix (decks/*_<fmt>.txt) -> override ban set.
BANNED_BY_FORMAT = {
    "modern": MODERN_BANNED,
}


def banned_set(fmt: str) -> set:
    """Return the override ban set for a format suffix (empty set if none defined)."""
    return set(BANNED_BY_FORMAT.get(fmt.lower(), set()))
