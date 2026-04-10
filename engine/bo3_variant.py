"""
engine/bo3_variant.py — Bo3 variant testing with sideboard plans

Answers the RC prep question: "Is 4 Phlage or 3 Phlage + 1 Bolt better
against this field in Bo3 with real sideboarding?"

Combines:
- engine/variant.py (card swap logic)
- engine/bo3_match.py (real 3-game matches)  
- data/sb_plans_tr.py (Team Resolve SB plans)
"""

from __future__ import annotations
import time, os
from copy import deepcopy
from dataclasses import dataclass, field
from multiprocessing import Pool

from engine.bo3_match import run_bo3
from apl.match_apl import GenericMatchAPL
from data.sb_plans_tr import get_tr_sb_plan


@dataclass
class Bo3VariantResult:
    """Result of a Bo3 variant comparison."""
    card_out:       str
    card_in:        str
    base_match_wr:  float  # base deck Bo3 match win rate
    var_match_wr:   float  # variant Bo3 match win rate
    delta:          float  # variant - base
    base_g1_wr:     float
    var_g1_wr:      float
    base_g2_wr:     float
    var_g2_wr:      float
    n_matches:      int


def _swap_card_in_deck(deck: list, card_out: str, card_in_name: str) -> list:
    """Swap one copy of card_out for card_in_name in deck."""
    new_deck = list(deck)
    for i, c in enumerate(new_deck):
        if c.name.lower() == card_out.lower():
            replacement = deepcopy(c)
            replacement.name = card_in_name
            new_deck[i] = replacement
            return new_deck
    return new_deck


def _run_bo3_chunk(args):
    """Worker for parallel Bo3 variant comparison."""
    deck_a, deck_b, sb_a, sb_b, n, seed, apl_cls_a, apl_cls_b, sb_plan_a, sb_plan_b = args
    import random
    rng = random.Random(seed)
    
    apl_a = apl_cls_a() if apl_cls_a else GenericMatchAPL()
    apl_b = apl_cls_b() if apl_cls_b else GenericMatchAPL()
    
    match_wins = 0
    g1_wins = 0; g1_total = 0
    g2_wins = 0; g2_total = 0
    total = 0
    
    for i in range(n):
        bo3 = run_bo3(apl_a, deck_a, sb_a, apl_b, deck_b, sb_b,
                      sb_plan_a=sb_plan_a, sb_plan_b=sb_plan_b,
                      a_on_play_g1=(i % 2 == 0),
                      seed=rng.randint(0, 999_999))
        total += 1
        if bo3.winner == 'a':
            match_wins += 1
        games = bo3.game_results
        if len(games) >= 1:
            g1_total += 1
            if games[0].winner == 'a': g1_wins += 1
        if len(games) >= 2:
            g2_total += 1
            if games[1].winner == 'a': g2_wins += 1
    
    return match_wins, total, g1_wins, g1_total, g2_wins, g2_total


def compare_bo3_variants(base_deck: list, base_sb: dict,
                         opponent_deck: list, opponent_sb: dict,
                         our_name: str, opp_name: str,
                         swaps: list[tuple[str, str]],
                         n_per: int = 300,
                         apl_cls_a=None, apl_cls_b=None) -> list[Bo3VariantResult]:
    """
    Compare card swaps in Bo3 format with real SB plans.
    
    swaps: list of (card_out, card_in) tuples
    Returns: list of Bo3VariantResult
    """
    import random
    rng = random.Random(42)
    
    sb_plan_a = get_tr_sb_plan(our_name, opp_name)
    sb_plan_b = get_tr_sb_plan(opp_name, our_name)
    sb_plan_a = sb_plan_a if (sb_plan_a[0] or sb_plan_a[1]) else None
    sb_plan_b = sb_plan_b if (sb_plan_b[0] or sb_plan_b[1]) else None
    
    # Run baseline
    base_args = (base_deck, opponent_deck, base_sb, opponent_sb,
                 n_per, rng.randint(0, 999_999),
                 apl_cls_a, apl_cls_b, sb_plan_a, sb_plan_b)
    base_r = _run_bo3_chunk(base_args)
    base_wr = round(base_r[0] / max(1, base_r[1]) * 100, 1)
    base_g1 = round(base_r[2] / max(1, base_r[3]) * 100, 1)
    base_g2 = round(base_r[4] / max(1, base_r[5]) * 100, 1)
    
    results = []
    for card_out, card_in in swaps:
        var_deck = _swap_card_in_deck(base_deck, card_out, card_in)
        var_args = (var_deck, opponent_deck, base_sb, opponent_sb,
                    n_per, rng.randint(0, 999_999),
                    apl_cls_a, apl_cls_b, sb_plan_a, sb_plan_b)
        var_r = _run_bo3_chunk(var_args)
        var_wr = round(var_r[0] / max(1, var_r[1]) * 100, 1)
        var_g1 = round(var_r[2] / max(1, var_r[3]) * 100, 1)
        var_g2 = round(var_r[4] / max(1, var_r[5]) * 100, 1)
        
        results.append(Bo3VariantResult(
            card_out=card_out, card_in=card_in,
            base_match_wr=base_wr, var_match_wr=var_wr,
            delta=round(var_wr - base_wr, 1),
            base_g1_wr=base_g1, var_g1_wr=var_g1,
            base_g2_wr=base_g2, var_g2_wr=var_g2,
            n_matches=n_per,
        ))
    
    return results


def print_bo3_variant_report(results: list[Bo3VariantResult],
                              deck_name: str, opponent: str):
    """Print formatted Bo3 variant comparison."""
    print(f"\n{'='*60}")
    print(f"  Bo3 VARIANT ANALYSIS: {deck_name} vs {opponent}")
    print(f"{'='*60}")
    for r in results:
        d = f"+{r.delta}" if r.delta > 0 else str(r.delta)
        emoji = ">>>" if abs(r.delta) >= 3 else " > " if abs(r.delta) >= 1 else " = "
        print(f"  {emoji} {r.card_out} → {r.card_in}")
        print(f"      Match WR: {r.base_match_wr}% → {r.var_match_wr}% ({d}%)")
        print(f"      G1: {r.base_g1_wr}% → {r.var_g1_wr}%  |  G2: {r.base_g2_wr}% → {r.var_g2_wr}%")
    print()
