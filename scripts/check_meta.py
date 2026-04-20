import sqlite3
conn = sqlite3.connect('data/mtg_meta.db')
c = conn.cursor()

# Get the most recent Boros Ocelot deck
c.execute("""
    SELECT d.id, d.player, e.date, e.name
    FROM decks d JOIN events e ON d.event_id = e.id
    WHERE d.archetype = 'Boros Ocelot' AND e.format = 'modern'
    ORDER BY e.date DESC LIMIT 1
""")
deck = c.fetchone()
print(f'Deck: {deck}')

# Get full decklist
c.execute("""
    SELECT c.name, dc.quantity, dc.is_sideboard
    FROM deck_cards dc
    JOIN cards c ON dc.card_id = c.id
    WHERE dc.deck_id = ?
    ORDER BY dc.is_sideboard, c.name
""", (deck[0],))

print(f'\n// Boros Ocelot - {deck[1]} ({deck[2]})')
print(f'// Event: {deck[3]}')
main = []
sb = []
for row in c.fetchall():
    line = f'{row[1]} {row[0]}'
    if row[2]:
        sb.append(line)
    else:
        main.append(line)

for line in main:
    print(line)
print('\nSideboard')
for line in sb:
    print(line)

# Also get Modern meta field with percentages
c.execute("""
    SELECT d.archetype, COUNT(*) as cnt
    FROM decks d JOIN events e ON d.event_id = e.id
    WHERE e.format = 'modern'
    GROUP BY d.archetype ORDER BY cnt DESC LIMIT 15
""")
rows = c.fetchall()
total_all = sum(r[1] for r in c.execute("""
    SELECT d.archetype, COUNT(*) FROM decks d JOIN events e ON d.event_id = e.id
    WHERE e.format = 'modern' GROUP BY d.archetype
""").fetchall())
print(f'\n// Modern field ({total_all} total decks):')
for name, cnt in rows:
    pct = round(100.0 * cnt / total_all, 1)
    print(f'//   {name}: {pct}%')
