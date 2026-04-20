"""Pull consensus 75 for an archetype from tournament data."""
import sqlite3, json

conn = sqlite3.connect('../mtg-meta-analyzer/data/mtg_meta.db')
c = conn.cursor()

# Get all Boros Ocelot deck IDs
c.execute("""
    SELECT d.id FROM decks d JOIN events e ON d.event_id = e.id
    WHERE d.archetype = 'Boros Ocelot' AND e.format = 'modern'
""")
deck_ids = [r[0] for r in c.fetchall()]
total_decks = len(deck_ids)
print(f"Boros Ocelot: {total_decks} decks in DB\n")

# Count card frequency across all decks
c.execute("""
    SELECT c.name, dc.is_sideboard,
           COUNT(*) as decks_with,
           ROUND(AVG(dc.quantity), 1) as avg_qty,
           MAX(dc.quantity) as max_qty,
           MIN(dc.quantity) as min_qty
    FROM deck_cards dc
    JOIN cards c ON dc.card_id = c.id
    JOIN decks d ON dc.deck_id = d.id
    JOIN events e ON d.event_id = e.id
    WHERE d.archetype = 'Boros Ocelot' AND e.format = 'modern'
    GROUP BY c.name, dc.is_sideboard
    ORDER BY dc.is_sideboard, decks_with DESC
""")

print("MAINBOARD (cards in 50%+ of decks):")
print(f"{'Card':<35} {'In%':>5} {'Avg':>4} {'Range':>7}")
print("-" * 55)
main_cards = []
sb_cards = []
for name, is_sb, decks_with, avg_qty, max_qty, min_qty in c.fetchall():
    pct = round(100 * decks_with / total_decks, 1)
    if is_sb == 0:
        if pct >= 30:
            print(f"  {name:<33} {pct:>5.1f}% {avg_qty:>4} {min_qty}-{max_qty}")
            if pct >= 50:
                main_cards.append((name, round(avg_qty)))
    else:
        if pct >= 20:
            sb_cards.append((name, pct, avg_qty, min_qty, max_qty))

print(f"\nSIDEBOARD (cards in 20%+ of decks):")
print(f"{'Card':<35} {'In%':>5} {'Avg':>4} {'Range':>7}")
print("-" * 55)
for name, pct, avg_qty, min_qty, max_qty in sb_cards:
    print(f"  {name:<33} {pct:>5.1f}% {avg_qty:>4} {min_qty}-{max_qty}")

# Build consensus 75
print(f"\n// Stock Boros Ocelot — Consensus from {total_decks} tournament decks")
total_main = 0
for name, qty in main_cards:
    print(f"{qty} {name}")
    total_main += qty
print(f"// Total mainboard: {total_main}")
