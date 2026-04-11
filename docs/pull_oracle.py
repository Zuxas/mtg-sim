"""Pull oracle text for all cards in a deck. Usage: python docs/pull_oracle.py {deck_name}
Example: python docs/pull_oracle.py eldrazi_tron"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data.deck import load_deck_from_file

deck_name = sys.argv[1] if len(sys.argv) > 1 else 'boros_energy'
deck_file = f'decks/{deck_name}_modern.txt'
out_file = f'docs/{deck_name}_oracle.txt'

deck, sb = load_deck_from_file(deck_file)
seen = set()
lines = [f'# {deck_name.upper().replace("_"," ")} — ORACLE TEXT ({len(set(c.name for c in deck+sb))} unique cards)\n']

for section, cards in [('NONLAND', [c for c in deck+sb if not c.is_land()]),
                        ('LANDS', [c for c in deck+sb if c.is_land()])]:
    lines.append(f'\n{"="*60}\n  {section}\n{"="*60}')
    for c in sorted(cards, key=lambda c: (getattr(c,'cmc',0), c.name)):
        if c.name in seen: continue
        seen.add(c.name)
        mc = getattr(c, 'mana_cost', '') or ''
        pt = f'{c.power}/{c.toughness}' if getattr(c, 'power', '') else ''
        oracle = getattr(c, 'oracle_text', '') or ''
        main_ct = sum(1 for x in deck if x.name == c.name)
        sb_ct = sum(1 for x in sb if x.name == c.name)
        loc = []
        if main_ct: loc.append(f'Main x{main_ct}')
        if sb_ct: loc.append(f'SB x{sb_ct}')
        lines.append(f'\n--- {c.name} ({mc}) {pt} [{", ".join(loc)}] ---')
        for line in oracle.split('\n'):
            lines.append(f'  {line}')

with open(out_file, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f'Written {len(lines)} lines to {out_file}')
