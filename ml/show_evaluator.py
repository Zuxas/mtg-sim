import sys; sys.path.insert(0, '.')
from data.deck import load_deck_from_file
from apl.humans import HumansAPL
from engine.action_evaluator import ActionEvaluator
from ml.win_prob_model import load_model
from engine.game_state import GameState
from engine.runner import run_simulation
from sim_bridge import avg_kill_turn

main, _ = load_deck_from_file('decks/humans_legacy.txt')

# Show what the evaluator ranks for a realistic T2 situation
model = load_model()
if model:
    from engine.action_evaluator import ActionEvaluator, _quick_snap
    arch = 'dimir tempo'
    ev = ActionEvaluator(model, arch)

    print(f"ActionEvaluator — T2 candidate ranking vs {arch}")
    print("=" * 60)
    print("Simulating hand with: Champion, Thalia, Guide of Souls, Esper Sentinel")
    print()

    # Mock board state at T2
    class MockGS:
        turn = 2
        damage_dealt = 2
        life = 20
        energy = 0
        class zones:
            battlefield = []
            hand = []
    gs = MockGS()

    class MockCard:
        def __init__(self, name, power=2, cmc=2):
            self.name = name
            self.power = power
            self.cmc = cmc
            self.mana_cost = f"{'W'*cmc}"
        def effective_power(self): return self.power

    candidates = [
        MockCard("Champion of the Parish", 1, 1),
        MockCard("Thalia, Guardian of Thraben", 2, 2),
        MockCard("Guide of Souls", 1, 1),
        MockCard("Esper Sentinel", 1, 1),
        MockCard("Thalia's Lieutenant", 2, 2),
    ]

    ranked = ev.rank_candidates(gs, candidates)
    for card, p in ranked:
        bar = chr(9608) * int(p / 5)
        print(f"  {card.name:<35} P(win)={p:.1f}%  {bar}")

    print()
    best = ev.pick_best(gs, candidates)
    print(f"Best play: {best.name}")
    print()
    print("Same T2 board vs dimir reanimator:")
    ev2 = ActionEvaluator(model, 'dimir reanimator')
    ranked2 = ev2.rank_candidates(gs, candidates)
    for card, p in ranked2:
        bar = chr(9608) * int(p / 5)
        print(f"  {card.name:<35} P(win)={p:.1f}%  {bar}")
    best2 = ev2.pick_best(gs, candidates)
    print(f"Best play: {best2.name}")
else:
    print("No model found. Run: python ml/train.py")
