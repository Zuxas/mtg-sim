"""
api/sim_api.py — Clean API for the MTG Sim engine

Usage:
    from api.sim_api import MTGSim
    sim = MTGSim()
    
    # Quick matchup
    wr = sim.matchup("Boros Energy", "Izzet Prowess", n=500)
    
    # Bo3 with sideboarding  
    bo3 = sim.bo3("Boros Energy", "Izzet Prowess", n=200)
    
    # Full meta solve (G1 or Bo3)
    meta = sim.meta_solve(n_per=500, bo3=False)
    
    # Tournament simulation
    rc = sim.simulate_rc(n_events=1000)
    
    # Variant testing
    delta = sim.test_swap("Boros Energy", "Phlage", "Lightning Bolt")
"""
from __future__ import annotations
import sys, os, random, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from data.deck import load_deck_from_file
from data.sb_plans_tr import get_tr_sb_plan

# APL registry
from apl.boros_energy_match import BorosEnergyMatchAPL
from apl.izzet_prowess_match import IzzetProwessMatchAPL
from apl.domain_zoo_match import DomainZooMatchAPL
from apl.mono_red_match import MonoRedMatchAPL
from apl.murktide_match import MurktideMatchAPL
from apl.jeskai_blink_match import JeskaiBlinkMatchAPL
from apl.affinity_match import AffinityMatchAPL
from apl.esper_blink_match import EsperBlinkMatchAPL
from apl.eldrazi_tron_match import EldraziTronMatchAPL
from apl.eldrazi_ramp_match import EldraziRampMatchAPL
from apl.goryos_match import GoryosMatchAPL
from apl.amulet_titan_match import AmuletTitanMatchAPL

APL_REGISTRY = {
    "Boros Energy": BorosEnergyMatchAPL,
    "Izzet Prowess": IzzetProwessMatchAPL,
    "Domain Zoo": DomainZooMatchAPL,
    "Mono Red Aggro": MonoRedMatchAPL,
    "Dimir Murktide": MurktideMatchAPL,
    "Jeskai Blink": JeskaiBlinkMatchAPL,
    "Izzet Affinity": AffinityMatchAPL,
    "Esper Blink": EsperBlinkMatchAPL,
    "Orzhov Blink": EsperBlinkMatchAPL,
    "Eldrazi Tron": EldraziTronMatchAPL,
    "Eldrazi Ramp": EldraziRampMatchAPL,
    "Goryos Vengeance": GoryosMatchAPL,
    "Amulet Titan": AmuletTitanMatchAPL,
}

DEFAULT_FIELD = {
    "Boros Energy": 0.173, "Izzet Affinity": 0.057, "Eldrazi Tron": 0.056,
    "Jeskai Blink": 0.054, "Domain Zoo": 0.048, "Eldrazi Ramp": 0.038,
    "Amulet Titan": 0.034, "Dimir Murktide": 0.034, "Grinding Breach": 0.032,
    "Izzet Prowess": 0.029, "Goryos Vengeance": 0.025, "Mono Red Aggro": 0.020,
    "Esper Blink": 0.018, "Orzhov Blink": 0.015, "Temur Breach": 0.015,
}


class MTGSim:
    """Clean API for the MTG Sim engine."""
    
    def __init__(self, deck_dir: str = 'decks', workers: int = 16):
        self.workers = workers
        self.deck_dir = Path(deck_dir)
        self._decks = {}
        self._sbs = {}
        self._loaded = False
    
    def _ensure_loaded(self):
        if self._loaded: return
        for f in sorted(self.deck_dir.glob('*_modern.txt')):
            name = f.stem.replace('_modern','').replace('_',' ').title()
            try:
                d, sb = load_deck_from_file(str(f))
                self._decks[name] = d
                sd = {}
                for c in sb: sd[c.name] = sd.get(c.name, 0) + 1
                self._sbs[name] = sd
            except: pass
        self._loaded = True
    
    def list_decks(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._decks.keys())
    
    def get_apl(self, deck_name: str):
        return APL_REGISTRY.get(deck_name)
    
    def matchup(self, deck_a: str, deck_b: str, n: int = 500, seed: int = 42) -> dict:
        """Quick G1 matchup. Returns {a_wr, b_wr, n_games}."""
        self._ensure_loaded()
        from engine.match_engine import run_match_set
        apl_a = (self.get_apl(deck_a) or GenericMatchAPL)()
        apl_b = (self.get_apl(deck_b) or GenericMatchAPL)()
        r = run_match_set(apl_a, self._decks[deck_a], apl_b, self._decks[deck_b], n=n, seed=seed)
        return {"a_wr": round(r.a_wins / r.n_games * 100, 1),
                "b_wr": round(r.b_wins / r.n_games * 100, 1),
                "n_games": r.n_games, "deck_a": deck_a, "deck_b": deck_b}

    def bo3(self, deck_a: str, deck_b: str, n: int = 200, seed: int = 42) -> dict:
        """Bo3 matchup with SB plans. Returns {match_wr, g1_wr, g2_wr, to_g3_pct}."""
        self._ensure_loaded()
        from engine.bo3_match import run_bo3_set
        apl_a = (self.get_apl(deck_a) or GenericMatchAPL)()
        apl_b = (self.get_apl(deck_b) or GenericMatchAPL)()
        sb_a = get_tr_sb_plan(deck_a, deck_b)
        sb_b = get_tr_sb_plan(deck_b, deck_a)
        sb_a = sb_a if (sb_a[0] or sb_a[1]) else None
        sb_b = sb_b if (sb_b[0] or sb_b[1]) else None
        r = run_bo3_set(apl_a, self._decks[deck_a], self._sbs.get(deck_a, {}),
                        apl_b, self._decks[deck_b], self._sbs.get(deck_b, {}),
                        sb_plan_a=sb_a, sb_plan_b=sb_b, n=n, seed=seed)
        return {"match_wr": r.match_wr_a(),
                "g1_wr": round(r.g1_wr_a, 1),
                "g2_wr": round(r.g2_wr_a, 1),
                "to_g3_pct": round(r.g3_rate, 1),
                "n_matches": r.n_matches, "deck_a": deck_a, "deck_b": deck_b}
    
    def meta_solve(self, n_per: int = 500, seed: int = 42) -> dict:
        """Full G1 meta solve. Returns {rankings, matrix}."""
        self._ensure_loaded()
        from engine.meta_solver import solve_meta
        solution = solve_meta(self._decks, DEFAULT_FIELD, n_per_pair=n_per,
                              workers=self.workers, seed=seed, apls=APL_REGISTRY)
        rankings = []
        for i, ds in enumerate(solution.deck_scores):
            rankings.append({"rank": i+1, "deck": ds.name, "field_wr": round(ds.field_wr, 1)})
        return {"rankings": rankings, "matrix": solution.matchup_matrix,
                "total_games": solution.total_games, "elapsed": solution.elapsed}
    
    def simulate_rc(self, matrix: dict = None, n_events: int = 1000,
                    n_players: int = 200, n_rounds: int = 8, seed: int = 42) -> list[dict]:
        """Swiss tournament sim. If no matrix, runs Bo3 solve first."""
        from engine.tournament import simulate_rc as _sim_rc
        if matrix is None:
            # Run Bo3 meta solve to get matrix
            bo3_matrix = self._run_bo3_matrix()
            matrix = bo3_matrix
        results = _sim_rc(DEFAULT_FIELD, matrix, n_events=n_events,
                          n_players=n_players, n_rounds=n_rounds, seed=seed)
        return [{"deck": r.deck, "avg_wins": r.avg_wins, "avg_losses": r.avg_losses,
                 "top8_pct": r.top8_pct, "day2_pct": r.x2_pct} for r in results]

    def test_swap(self, deck_name: str, card_out: str, card_in: str,
                  opponent: str = None, n: int = 300, seed: int = 42) -> dict:
        """Test swapping one card. Returns {base_wr, var_wr, delta}.
        If opponent is None, tests against full field."""
        self._ensure_loaded()
        from copy import deepcopy
        
        deck = self._decks[deck_name]
        # Swap one copy
        var_deck = list(deck)
        for i, c in enumerate(var_deck):
            if c.name.lower() == card_out.lower():
                r = deepcopy(c); r.name = card_in; var_deck[i] = r; break
        
        if opponent:
            base = self.matchup(deck_name, opponent, n=n, seed=seed)
            # Run with swapped deck
            from engine.match_engine import run_match_set
            apl_a = (self.get_apl(deck_name) or GenericMatchAPL)()
            apl_b = (self.get_apl(opponent) or GenericMatchAPL)()
            r = run_match_set(apl_a, var_deck, apl_b, self._decks[opponent], n=n, seed=seed+1)
            var_wr = round(r.a_wins / r.n_games * 100, 1)
            return {"base_wr": base["a_wr"], "var_wr": var_wr,
                    "delta": round(var_wr - base["a_wr"], 1),
                    "card_out": card_out, "card_in": card_in, "vs": opponent}
        else:
            return {"card_out": card_out, "card_in": card_in,
                    "note": "Use field-wide variant testing for full field analysis"}
    
    def _run_bo3_matrix(self, n_per: int = 200, seed: int = 42) -> dict:
        """Run Bo3 meta solve and return matchup matrix."""
        self._ensure_loaded()
        from multiprocessing import Pool
        import random as rng_mod
        rng = rng_mod.Random(seed)
        
        names = list(self._decks.keys())
        pairs = []
        for i, na in enumerate(names):
            for j, nb in enumerate(names):
                if i >= j: continue
                sa = get_tr_sb_plan(na, nb); sb = get_tr_sb_plan(nb, na)
                sa = sa if (sa[0] or sa[1]) else None
                sb = sb if (sb[0] or sb[1]) else None
                pairs.append((self._decks[na], self._decks[nb],
                              self._sbs.get(na, {}), self._sbs.get(nb, {}),
                              na, nb, n_per, rng.randint(0, 999_999),
                              self.get_apl(na), self.get_apl(nb), sa, sb))
        
        with Pool(self.workers) as pool:
            results = pool.map(_bo3_worker, pairs)
        
        matrix = {}
        for (na, nb, aw, bw) in results:
            t = aw + bw
            matrix[(na, nb)] = round(aw / t * 100, 1) if t else 50
            matrix[(nb, na)] = round(bw / t * 100, 1) if t else 50
        return matrix


def _bo3_worker(args):
    """Multiprocessing worker for Bo3 matrix."""
    deck_a, deck_b, sb_a, sb_b, na, nb, n, seed, apl_a, apl_b, sp_a, sp_b = args
    import random, sys
    sys.path.insert(0, '.')
    from apl.match_apl import GenericMatchAPL
    from engine.bo3_match import run_bo3
    rng = random.Random(seed)
    a = apl_a() if apl_a else GenericMatchAPL()
    b = apl_b() if apl_b else GenericMatchAPL()
    aw = bw = 0
    for i in range(n):
        bo3 = run_bo3(a, deck_a, sb_a, b, deck_b, sb_b,
                      sb_plan_a=sp_a, sb_plan_b=sp_b,
                      a_on_play_g1=(i % 2 == 0), seed=rng.randint(0, 999_999))
        if bo3.winner == 'a': aw += 1
        else: bw += 1
    return (na, nb, aw, bw)


# Import for GenericMatchAPL
from apl.match_apl import GenericMatchAPL
