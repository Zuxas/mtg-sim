import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('..', 'mtg-meta-analyzer'))
from data.deck import load_deck_from_file
from apl.humans import HumansAPL
from engine.game_state import GameState
from engine.runner import run_simulation
import copy, random

main, _ = load_deck_from_file('decks/humans_new.txt')

# Find a seed with Adeline + Champion or Lieutenant in opening hand
good_seed = 42
for seed in range(500):
    random.seed(seed)
    deck = copy.deepcopy(main)
    random.shuffle(deck)
    hand = [c.name for c in deck[:7]]
    has_adeline = 'Adeline, Resplendent Cathar' in hand
    has_lord = 'Champion of the Parish' in hand or "Thalia's Lieutenant" in hand
    has_land = any('Land' in c or 'Plains' in c or 'Cavern' in c or 'Valley' in c for c in hand)
    if has_adeline and has_lord and has_land:
        good_seed = seed
        print('Seed %d: %s' % (seed, hand))
        break

r = run_simulation(HumansAPL(), main, n=200, seed=good_seed, verbose_first=1)
avg = r.avg_kill_turn()
print('Avg kill: T%.2f' % avg if avg else 'Avg: None')
