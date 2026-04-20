import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, '..', 'mtg-meta-analyzer'))
from data.deck import load_deck_from_file
from apl.humans import HumansAPL
from engine.runner import run_simulation
from sim_bridge import ARCHETYPE_CLOCKS, race_win_pct as rwp, avg_kill_turn

FIELD = [
    ('Lands',      'lands'),
    ('UR Delver',  'delver'),
    ('Elves',      'elves'),
    ('Painter',    'painter'),
    ('Stoneforge', 'stoneforge'),
    ('Hogaak',     'hogaak'),
]

main_old, _ = load_deck_from_file('decks/humans_legacy.txt')
main_new, _ = load_deck_from_file('decks/humans_new.txt')

r_old = run_simulation(HumansAPL(), main_old, n=5000, seed=42)
r_new = run_simulation(HumansAPL(), main_new, n=5000, seed=42)

dist_old = r_old.kill_turn_distribution()
dist_new = r_new.kill_turn_distribution()

print('Matchup comparison vs locals field:')
print('  Opponent             Old List  New List     Delta')
print('  ' + '-'*52)

old_total = 0
new_total = 0
for opp_name, opp_key in FIELD:
    opp_dist = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS['unknown'])
    wp_old = rwp(dist_old, opp_dist, n=30000)
    wp_new = rwp(dist_new, opp_dist, n=30000)
    delta = wp_new - wp_old
    arrow = 'UP' if delta > 0.5 else ('DN' if delta < -0.5 else '==')
    print(f'  {opp_name:<20} {wp_old:>7.1f}%   {wp_new:>7.1f}%   {delta:>+6.1f}% {arrow}')
    old_total += wp_old
    new_total += wp_new

print('  ' + '-'*52)
n = len(FIELD)
print(f'  AVERAGE              {old_total/n:>7.1f}%   {new_total/n:>7.1f}%   {(new_total-old_total)/n:>+6.1f}%')
print()
print(f'  Kill turn:  Old T{r_old.avg_kill_turn():.2f}  vs  New T{r_new.avg_kill_turn():.2f}')
