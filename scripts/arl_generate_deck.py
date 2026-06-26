"""
arl_generate_deck.py -- standalone Modern (or any-format) deck-file generator
for the Autonomous Research Loop (ARL).

Pulls the most-recent top-finish decklist for an archetype from the
meta-analyzer DB and writes it to decks/auto/<slug>_<format>.txt in the
mtg-sim deck format.

CLI:
    python arl_generate_deck.py "<Archetype Name>" [format]

    format defaults to "modern".

Importable:
    from arl_generate_deck import generate_deck
    path = generate_deck("Amulet Titan", "modern")  # -> str path, or None

Slug rule: lowercased archetype, every run of non-alphanumeric characters
collapsed to a single underscore, leading/trailing underscores stripped.

On success: prints the written path to stdout, exit 0.
On failure (DB missing / 0 tournament samples): prints a one-line reason to
stderr, exit 1 -- so the loop can convert it into a blocker.
"""

import sys
import os
import re
import sqlite3

# ---------------------------------------------------------------------------
# Cross-repo sys.path setup
# ---------------------------------------------------------------------------
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts"))
for p in (SIM_ROOT, HARNESS_SCRIPTS):
    if p not in sys.path:
        sys.path.insert(0, p)

# Meta-analyzer DB lives alongside the sibling mtg-meta-analyzer repo.
DB_PATH = os.path.abspath(os.path.join(
    SIM_ROOT, "..", "mtg-meta-analyzer", "data", "mtg_meta.db"
))

# SQL expression to normalise mixed date formats in events.date to YYYYMMDD.
# Mirrors auto_pipeline._DB_DATE_KEY: MTGTop8 stores DD/MM/YY, MTGDecks stores
# YYYY-MM-DD, so a raw lexicographic ORDER BY e.date DESC is wrong.
_DB_DATE_KEY = (
    "CASE WHEN instr(e.date,'/')>0 "
    "THEN '20'||substr(e.date,7,2)||substr(e.date,4,2)||substr(e.date,1,2) "
    "ELSE replace(e.date,'-','') END"
)


def slugify(archetype):
    """Lowercase, collapse non-alphanumeric runs to a single underscore."""
    s = re.sub(r"[^a-z0-9]+", "_", archetype.lower())
    return s.strip("_")


def _find_deck_row(conn, archetype, format_name):
    """Return the (id,) row of the most-recent top-finish deck for archetype.

    Tries an exact archetype match first (the DB stores canonical names);
    falls back to a LIKE match so loose loop-supplied names still resolve.
    Returns the sqlite3.Row or None.
    """
    fmt = format_name.lower()
    # Most recent first, then best placement. NULL placements sort last.
    order = (
        f"ORDER BY ({_DB_DATE_KEY}) DESC, "
        "CASE WHEN d.placement IS NULL THEN 1 ELSE 0 END ASC, "
        "d.placement ASC"
    )
    exact = conn.execute(
        f"""
        SELECT d.id FROM decks d
        JOIN events e ON e.id = d.event_id
        WHERE d.archetype = ? AND e.format = ?
        {order}
        LIMIT 1
        """,
        (archetype, fmt),
    ).fetchone()
    if exact:
        return exact
    return conn.execute(
        f"""
        SELECT d.id FROM decks d
        JOIN events e ON e.id = d.event_id
        WHERE d.archetype LIKE ? AND e.format = ?
        {order}
        LIMIT 1
        """,
        (f"%{archetype}%", fmt),
    ).fetchone()


class DeckGenError(Exception):
    """Raised with a one-line, stderr-ready reason."""


def generate_deck(archetype, format_name="modern"):
    """Generate a deck file for archetype from the meta DB.

    Returns the absolute path (str) of the written file on success.
    Returns None on a soft failure (DB missing, 0 samples, empty deck).
    """
    if not archetype or not archetype.strip():
        return None

    if not os.path.exists(DB_PATH):
        sys.stderr.write(f"meta DB not found at {DB_PATH}\n")
        return None

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        deck_row = _find_deck_row(conn, archetype, format_name)
        if not deck_row:
            sys.stderr.write(
                f"0 tournament samples for '{archetype}' ({format_name}) in meta DB\n"
            )
            return None

        deck_id = deck_row["id"]
        cards = conn.execute(
            """
            SELECT c.name AS card_name, dc.quantity AS quantity,
                   dc.is_sideboard AS sideboard
            FROM deck_cards dc
            JOIN cards c ON c.id = dc.card_id
            WHERE dc.deck_id = ?
            ORDER BY dc.is_sideboard, c.name
            """,
            (deck_id,),
        ).fetchall()

        meta = conn.execute(
            """
            SELECT d.player AS player, d.placement AS placement,
                   e.name AS event_name, e.date AS date
            FROM decks d JOIN events e ON e.id = d.event_id
            WHERE d.id = ?
            """,
            (deck_id,),
        ).fetchone()
    finally:
        conn.close()

    if not cards:
        sys.stderr.write(
            f"deck_id={deck_id} for '{archetype}' has no cards in meta DB\n"
        )
        return None

    main = [c for c in cards if not c["sideboard"]]
    side = [c for c in cards if c["sideboard"]]
    if not main:
        sys.stderr.write(
            f"deck_id={deck_id} for '{archetype}' has an empty mainboard\n"
        )
        return None

    slug = slugify(archetype)
    fmt = format_name.lower()
    deck_dir = os.path.join(SIM_ROOT, "decks", "auto")

    # GUARD: only ever write under decks/auto/. Refuse anything that resolves
    # outside it (defends against a slug/format with traversal characters).
    deck_path = os.path.abspath(os.path.join(deck_dir, f"{slug}_{fmt}.txt"))
    auto_real = os.path.abspath(deck_dir)
    if os.path.commonpath([auto_real, deck_path]) != auto_real:
        sys.stderr.write(
            f"refusing to write outside decks/auto/: {deck_path}\n"
        )
        return None

    os.makedirs(deck_dir, exist_ok=True)

    player = meta["player"] if meta and meta["player"] else "unknown"
    placement = meta["placement"] if meta and meta["placement"] is not None else "NA"
    event_name = meta["event_name"] if meta and meta["event_name"] else "unknown event"
    date = meta["date"] if meta and meta["date"] else "unknown"

    lines = [
        f"// {archetype} - {player} ({date})",
        f"// Event: {event_name}, Place: {placement}",
        f"// Source: mtg_meta.db deck_id={deck_id} (audit:auto-generated)",
        "",
    ]
    for c in main:
        lines.append(f"{c['quantity']} {c['card_name']}")
    if side:
        lines.append("")
        lines.append("Sideboard")
        for c in side:
            lines.append(f"{c['quantity']} {c['card_name']}")

    with open(deck_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return deck_path


def main(argv):
    args = argv[1:]
    if not args or args[0] in ("-h", "--help"):
        sys.stderr.write(
            'usage: python arl_generate_deck.py "<Archetype Name>" [format]\n'
        )
        # --help is a clean exit; a bare missing-arg call is an error.
        return 0 if (args and args[0] in ("-h", "--help")) else 1

    archetype = args[0]
    format_name = args[1] if len(args) > 1 else "modern"

    try:
        path = generate_deck(archetype, format_name)
    except Exception as exc:  # noqa: BLE001 - surface a one-line reason
        sys.stderr.write(f"deck generation failed: {exc}\n")
        return 1

    if not path:
        # generate_deck already wrote a one-line reason to stderr.
        return 1

    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
