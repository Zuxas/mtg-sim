"""tests/test_api.py — Integration tests for the MTG Sim API.
Run: python tests/test_api.py
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_list_decks():
    from api.sim_api import MTGSim
    sim = MTGSim(workers=1)
    decks = sim.list_decks()
    assert len(decks) == 15, f"Expected 15 decks, got {len(decks)}"
    assert "Boros Energy" in decks

def test_matchup():
    from api.sim_api import MTGSim
    sim = MTGSim(workers=4)
    r = sim.matchup("Boros Energy", "Izzet Prowess", n=100)
    assert 25 <= r['a_wr'] <= 75, f"Expected 25-75%, got {r['a_wr']}"
    assert r['n_games'] == 100

def test_bo3():
    from api.sim_api import MTGSim
    sim = MTGSim(workers=4)
    b = sim.bo3("Boros Energy", "Izzet Prowess", n=50)
    assert 20 <= b['match_wr'] <= 80
    assert b['n_matches'] == 50

def test_swap():
    from api.sim_api import MTGSim
    sim = MTGSim(workers=4)
    s = sim.test_swap("Boros Energy", "Phlage, Titan of Fire's Fury",
                      "Lightning Bolt", opponent="Izzet Prowess", n=100)
    assert 'delta' in s
    assert -30 <= s['delta'] <= 30

def test_meta_solve():
    from api.sim_api import MTGSim
    sim = MTGSim(workers=4)
    meta = sim.meta_solve(n_per=50)
    assert len(meta['rankings']) == 15
    assert meta['rankings'][0]['deck'] == "Boros Energy"
    assert meta['total_games'] > 0

if __name__ == '__main__':
    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            try:
                fn()
                print(f"  PASS {name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL {name}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
