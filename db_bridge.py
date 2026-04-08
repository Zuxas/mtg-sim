"""
db_bridge.py — Bridge between mtg-meta-analyzer DB and mtg-sim engine

Pulls saved decklists, tournament decklists, and meta field data
directly from the mtg_meta.db database.

Usage:
    from db_bridge import load_saved_deck, load_tournament_deck, get_meta_field

    # Load your curated 75
    main, sb = load_saved_deck("Boros Energy")

    # Load a top-8 tournament list
    main, sb = load_tournament_deck("Boros Ocelot", format="modern", top=8)

    # Get meta field with shares
    field = get_meta_field("modern", days=30, top_n=15)
"""

import os
import sys
import json
import sqlite3
from typing import Optional

# Path to the meta-analyzer database
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "mtg-meta-analyzer", "data", "mtg_meta.db"
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data.deck import load_deck_from_text
from engine.card_db import CardDB


def _get_conn():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Meta-analyzer DB not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def load_saved_deck(name: str, format_name: str = None):
    """
    Load a saved deck from the meta-analyzer DB.
    Returns (mainboard_text, sideboard_text) as strings ready for load_deck_from_text.
    """
    conn = _get_conn()
    c = conn.cursor()
    
    if format_name:
        c.execute("SELECT mainboard, sideboard, name, format FROM saved_decks WHERE name LIKE ? AND format = ?",
                  (f"%{name}%", format_name))
    else:
        c.execute("SELECT mainboard, sideboard, name, format FROM saved_decks WHERE name LIKE ?",
                  (f"%{name}%",))
    
    row = c.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"No saved deck matching '{name}' found")
    
    mb_json = json.loads(row[0])
    sb_json = json.loads(row[1]) if row[1] else {}
    
    # Convert JSON {card_name: quantity} to deck text
    lines = [f"// {row[2]} ({row[3]})"]
    for card, qty in mb_json.items():
        lines.append(f"{qty} {card}")
    if sb_json:
        lines.append("\nSideboard")
        for card, qty in sb_json.items():
            lines.append(f"{qty} {card}")
    
    deck_text = "\n".join(lines)
    return deck_text


def load_tournament_deck(archetype: str, format_name: str = "modern",
                          top: int = 8, most_recent: bool = True):
    """
    Load a tournament decklist from the DB.
    Finds a top-placing deck of the given archetype.
    Returns deck text string.
    """
    conn = _get_conn()
    c = conn.cursor()
    
    query = """
        SELECT d.id, d.player, d.placement, e.name, e.date
        FROM decks d JOIN events e ON d.event_id = e.id
        WHERE d.archetype LIKE ? AND e.format = ?
        AND (d.placement <= ? OR d.placement IS NULL)
        ORDER BY e.date DESC
        LIMIT 1
    """
    c.execute(query, (f"%{archetype}%", format_name, top))
    deck_row = c.fetchone()
    
    if not deck_row:
        raise ValueError(f"No {archetype} deck found in {format_name} (top {top})")
    
    deck_id = deck_row[0]
    
    # Get card list
    c.execute("""
        SELECT c.name, dc.quantity, dc.is_sideboard
        FROM deck_cards dc JOIN cards c ON dc.card_id = c.id
        WHERE dc.deck_id = ?
        ORDER BY dc.is_sideboard, c.name
    """, (deck_id,))
    
    rows = c.fetchall()
    conn.close()
    
    lines = [f"// {archetype} - {deck_row[1]} ({deck_row[4]})"]
    lines.append(f"// Event: {deck_row[3]}, Place: {deck_row[2]}")
    
    for name, qty, is_sb in rows:
        if is_sb and not any("Sideboard" in l for l in lines):
            lines.append("\nSideboard")
        lines.append(f"{qty} {name}")
    
    return "\n".join(lines)


def get_meta_field(format_name: str = "modern", days: int = 60,
                    top_n: int = 15) -> dict:
    """
    Get meta field with archetype shares from tournament data.
    Returns dict of {archetype_name: meta_share_pct}.
    """
    conn = _get_conn()
    c = conn.cursor()
    
    c.execute("""
        SELECT d.archetype, COUNT(*) as cnt
        FROM decks d JOIN events e ON d.event_id = e.id
        WHERE e.format = ?
        GROUP BY d.archetype ORDER BY cnt DESC
        LIMIT ?
    """, (format_name, top_n))
    
    rows = c.fetchall()
    conn.close()
    
    total = sum(r[1] for r in rows)
    field = {}
    for name, cnt in rows:
        if name:  # skip empty archetype names
            field[name] = round(100.0 * cnt / total, 1)
    
    return field


def list_saved_decks(format_name: str = None):
    """List all saved decks, optionally filtered by format."""
    conn = _get_conn()
    c = conn.cursor()
    
    if format_name:
        c.execute("SELECT name, format, archetype, notes FROM saved_decks WHERE format = ? ORDER BY name",
                  (format_name,))
    else:
        c.execute("SELECT name, format, archetype, notes FROM saved_decks ORDER BY format, name")
    
    rows = c.fetchall()
    conn.close()
    return rows


def list_meta_archetypes(format_name: str = "modern", top_n: int = 20):
    """List top archetypes with deck counts for a format."""
    conn = _get_conn()
    c = conn.cursor()
    
    c.execute("""
        SELECT d.archetype, COUNT(*) as cnt
        FROM decks d JOIN events e ON d.event_id = e.id
        WHERE e.format = ?
        GROUP BY d.archetype ORDER BY cnt DESC
        LIMIT ?
    """, (format_name, top_n))
    
    rows = c.fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# CLI — test the bridge
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser(description="MTG Meta DB Bridge")
    ap.add_argument("--format", default="modern", help="Format to query")
    ap.add_argument("--list-saved", action="store_true", help="List saved decks")
    ap.add_argument("--list-meta", action="store_true", help="List meta archetypes")
    ap.add_argument("--load-saved", type=str, help="Load a saved deck by name")
    ap.add_argument("--load-tournament", type=str, help="Load a tournament deck by archetype")
    ap.add_argument("--meta-field", action="store_true", help="Print meta field dict")
    args = ap.parse_args()
    
    if args.list_saved:
        print(f"\nSaved decks ({args.format}):")
        for name, fmt, arch, notes in list_saved_decks(args.format):
            print(f"  {name:<40} [{fmt}] {arch} - {notes}")
    
    elif args.list_meta:
        print(f"\n{args.format.title()} meta ({args.format}):")
        for arch, cnt in list_meta_archetypes(args.format):
            print(f"  {arch:<35} {cnt:>5} decks")
    
    elif args.load_saved:
        text = load_saved_deck(args.load_saved, args.format)
        print(text)
    
    elif args.load_tournament:
        text = load_tournament_deck(args.load_tournament, args.format)
        print(text)
    
    elif args.meta_field:
        field = get_meta_field(args.format)
        print(f"\n{args.format.title()} meta field:")
        for arch, pct in sorted(field.items(), key=lambda x: -x[1]):
            print(f"  {arch:<35} {pct:>5.1f}%")
    
    else:
        # Default: show everything
        print(f"\n=== Saved {args.format} decks ===")
        for name, fmt, arch, notes in list_saved_decks(args.format):
            print(f"  {name:<40} {notes}")
        
        field = get_meta_field(args.format)
        print(f"\n=== {args.format.title()} meta field ===")
        for arch, pct in sorted(field.items(), key=lambda x: -x[1]):
            print(f"  {arch:<35} {pct:>5.1f}%")
