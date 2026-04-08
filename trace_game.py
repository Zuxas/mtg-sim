import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, os.path.join('..', 'mtg-meta-analyzer'))
from data.deck import load_deck_from_file
from apl.humans import HumansAPL
from engine.game_state import GameState
from engine.zones import Zones
import copy, random

main, _ = load_deck_from_file('decks/humans_new.txt')

# Manually run one game with verbose logging
random.seed(8)
deck = copy.deepcopy(main)
random.shuffle(deck)

from apl.mulligan import take_opening_hand
hand, library, mulls = take_opening_hand(deck, HumansAPL().keep, HumansAPL().bottom, on_play=True, verbose=True)

gs = GameState(mainboard=main, on_play=True)
gs.new_game()
gs._verbose = True
gs.zones.hand = hand
gs.zones.library = library

apl = HumansAPL()
for turn in range(6):
    gs.run_turn()
    gs.tap_lands()
    apl.main_phase(gs)
    gs.mana_pool.empty()
    gs.tap_lands()
    apl.main_phase2(gs)
    
    bf_names = [c.name for c in gs.zones.battlefield if not c.is_land()]
    bf_detail = [(c.name, c.effective_power(), c.effective_toughness(), c.counters) 
                 for c in gs.zones.battlefield if not c.is_land()]
    
    print('T%d end — %d dmg | energy=%d | life=%d' % (gs.turn, gs.damage_dealt, gs.energy, gs.life))
    for name, pw, tg, ctr in bf_detail:
        print('  %s: %d/%d (counters=%d)' % (name, pw, tg, ctr))
    print()
    
    if gs.has_won():
        print('WON on T%d' % gs.turn)
        break
