import sys, os, random, copy, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from generate_matchup_data import load_deck_and_apl

# Test 1: keep_vs fires correctly for Humans vs Reanimator
main, _, apl = load_deck_and_apl('Legacy Humans', 'legacy')
sig = inspect.signature(apl.keep_vs)
print(f'Humans keep_vs params: {list(sig.parameters.keys())}')

random.seed(99)
print('\nHumans vs Reanimator - 10 opening hands:')
for i in range(10):
    deck = copy.deepcopy(main)
    random.shuffle(deck)
    hand = deck[:7]
    decision = apl.keep_vs(hand, 0, True, 'Dimir Reanimator')
    gy_hate = sum(1 for c in hand if c.name in {
        "Grafdigger's Cage","Faerie Macabre","Containment Priest","Deafening Silence"})
    lands = sum(1 for c in hand if c.is_land())
    result = "KEEP" if decision else "MULL"
    print(f'  Hand {i+1}: {result:4s} | {gy_hate} GY hate | {lands} lands')

print('\nHumans vs Tempo - 5 hands (should be less selective):')
for i in range(5):
    deck = copy.deepcopy(main)
    random.shuffle(deck)
    hand = deck[:7]
    d_rean = apl.keep_vs(hand, 0, True, 'Dimir Reanimator')
    d_tempo = apl.keep_vs(hand, 0, True, 'Dimir Tempo')
    lands = sum(1 for c in hand if c.is_land())
    print(f'  Hand {i+1}: vs Rean={("K" if d_rean else "M")} vs Tempo={("K" if d_tempo else "M")} | {lands} lands')

print('\nSB premiums:')
tests = [
    ('Legacy Humans','Dimir Reanimator','legacy'),
    ('Legacy Humans','Dimir Tempo','legacy'),
    ('Boros Energy','Amulet Titan','modern'),
    ('Boros Energy','Eldrazi Ramp','modern'),
    ('Boros Energy','Izzet Prowess','modern'),
    ('Boros Energy','Mono Red Aggro','modern'),
    ('Izzet Phoenix','Azorius Control','pioneer'),
    ('Amulet Titan','Boros Energy','modern'),
]
for deck, opp, fmt in tests:
    _, _, a = load_deck_and_apl(deck, fmt)
    sb = a.sideboard_premium(opp, fmt)
    print(f'  {deck:<20} vs {opp:<25} +{sb:.0f}%')
