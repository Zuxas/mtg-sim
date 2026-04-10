"""
engine/variant.py — Phase 3D variant testing + sideboard optimizer

Swap cards in a deck, re-sim, compare win rates.
Answers: "is 4 Phlage better than 3 Phlage + 1 Bolt against this field?"

Usage:
    from engine.variant import compare_variants, optimize_sideboard
    
    # Single swap comparison
    result = compare_variants(
        deck, opponent_deck,
        swaps=[("Phlage, Titan of Fire's Fury", "Lightning Bolt")],
        n=2000
    )
    
    # Field-wide optimization
    best = optimize_sideboard(
        mainboard, sideboard,
        field={"Boros Energy": 0.20, "Izzet Prowess": 0.10},
        n_per_matchup=1000
    )
"""

from __future__ import annotations
import time
from copy import deepcopy
from dataclasses import dataclass, field

from engine.match_engine import run_match_set, print_match_report
from apl.match_apl import GenericMatchAPL


@dataclass
class VariantResult:
    """Result of comparing a variant against the base deck."""
    card_out:     str
    card_in:      str
    base_wr:      float    # base deck win rate
    variant_wr:   float    # variant win rate
    delta:        float    # variant - base (positive = improvement)
    n_games:      int
    base_avg_t:   float
    variant_avg_t: float


def _swap_card(deck: list, card_out_name: str, card_in) -> list:
    """Create a copy of deck with one card swapped. card_in can be a Card or name string."""
    new_deck = list(deck)
    for i, c in enumerate(new_deck):
        if c.name.lower() == card_out_name.lower():
            if isinstance(card_in, str):
                # Create a copy of the card being removed and rename it
                replacement = deepcopy(c)
                replacement.name = card_in
            else:
                replacement = deepcopy(card_in)
            new_deck[i] = replacement
            return new_deck
    return new_deck  # card not found, return unchanged


def compare_variants(base_deck: list, opponent_deck: list,
                     swaps: list[tuple[str, str]],
                     n: int = 2000, seed: int = 42) -> list[VariantResult]:
    """
    Swap cards and compare win rates against an opponent deck.
    
    swaps: list of (card_out_name, card_in_name) tuples
    Returns: list of VariantResult showing delta for each swap
    """
    apl_a = GenericMatchAPL()
    apl_b = GenericMatchAPL()
    
    # Run baseline
    base_results = run_match_set(apl_a, base_deck, apl_b, opponent_deck,
                                 n=n, seed=seed)
    base_wr = base_results.win_rate_a()
    base_avg = base_results.avg_turns
    
    variant_results = []
    for card_out, card_in in swaps:
        variant_deck = _swap_card(base_deck, card_out, card_in)
        var_results = run_match_set(apl_a, variant_deck, apl_b, opponent_deck,
                                    n=n, seed=seed)
        var_wr = var_results.win_rate_a()
        delta = var_wr - base_wr
        
        variant_results.append(VariantResult(
            card_out=card_out, card_in=card_in,
            base_wr=round(base_wr * 100, 1),
            variant_wr=round(var_wr * 100, 1),
            delta=round(delta * 100, 1),
            n_games=n,
            base_avg_t=round(base_avg, 1),
            variant_avg_t=round(var_results.avg_turns, 1),
        ))
    
    return variant_results


def print_variant_report(results: list[VariantResult], deck_name: str = "Deck"):
    """Print formatted variant comparison."""
    print(f"\n{'='*55}")
    print(f"  VARIANT ANALYSIS: {deck_name}")
    print(f"{'='*55}")
    for r in results:
        direction = "+" if r.delta > 0 else ""
        emoji = ">>>" if abs(r.delta) >= 2 else " > " if abs(r.delta) >= 0.5 else " = "
        print(f"  {emoji} {r.card_out} -> {r.card_in}")
        print(f"      Base: {r.base_wr}% | Variant: {r.variant_wr}% | Delta: {direction}{r.delta}%")
        print(f"      Avg turns: {r.base_avg_t} -> {r.variant_avg_t}")
    print()


@dataclass
class FieldResult:
    """Win rate against each deck in a field."""
    matchup_wrs: dict = field(default_factory=dict)  # {opp_name: win_rate}
    field_wr:    float = 0.0  # weighted average
    
    def compute_field_wr(self, field_shares: dict):
        total = 0.0
        weight_sum = 0.0
        for name, share in field_shares.items():
            if name in self.matchup_wrs:
                total += self.matchup_wrs[name] * share
                weight_sum += share
        self.field_wr = round(total / max(0.01, weight_sum) * 100, 1)


def run_field_analysis(deck: list, field_decks: dict[str, list],
                       field_shares: dict[str, float],
                       n_per_matchup: int = 1000,
                       seed: int = 42) -> FieldResult:
    """
    Run a deck against every opponent in a field.
    
    field_decks: {name: deck_list}
    field_shares: {name: meta_share_fraction}
    Returns FieldResult with per-matchup and weighted WRs.
    """
    apl_a = GenericMatchAPL()
    result = FieldResult()
    
    for name, opp_deck in field_decks.items():
        apl_b = GenericMatchAPL()
        match_results = run_match_set(apl_a, deck, apl_b, opp_deck,
                                      n=n_per_matchup, seed=seed)
        result.matchup_wrs[name] = match_results.win_rate_a()
    
    result.compute_field_wr(field_shares)
    return result


def compare_field_variants(base_deck: list, field_decks: dict[str, list],
                           field_shares: dict[str, float],
                           swaps: list[tuple[str, str]],
                           n_per_matchup: int = 1000,
                           seed: int = 42) -> dict:
    """
    Compare variants across a full field.
    Returns {variant_label: FieldResult} including 'base'.
    """
    results = {}
    
    # Base
    results['base'] = run_field_analysis(
        base_deck, field_decks, field_shares, n_per_matchup, seed)
    
    # Variants
    for card_out, card_in in swaps:
        label = f"-{card_out} +{card_in}"
        variant_deck = _swap_card(base_deck, card_out, card_in)
        results[label] = run_field_analysis(
            variant_deck, field_decks, field_shares, n_per_matchup, seed)
    
    return results


def print_field_report(results: dict, field_shares: dict, deck_name: str = "Deck"):
    """Print field analysis with variant comparison."""
    print(f"\n{'='*65}")
    print(f"  FIELD ANALYSIS: {deck_name}")
    print(f"{'='*65}")
    
    base = results.get('base')
    if not base:
        print("  No base result")
        return
    
    print(f"\n  {'Matchup':<25} {'Share':>6}  {'Base':>6}", end="")
    variants = [k for k in results if k != 'base']
    for v in variants:
        print(f"  {v[:15]:>15}", end="")
    print()
    print(f"  {'-'*25} {'-'*6}  {'-'*6}", end="")
    for _ in variants:
        print(f"  {'-'*15}", end="")
    print()
    
    for name in sorted(base.matchup_wrs.keys()):
        share = field_shares.get(name, 0)
        base_wr = round(base.matchup_wrs[name] * 100, 1)
        print(f"  {name:<25} {share*100:5.1f}%  {base_wr:5.1f}%", end="")
        for v in variants:
            vr = results[v]
            var_wr = round(vr.matchup_wrs.get(name, 0) * 100, 1)
            delta = var_wr - base_wr
            d = f"{'+' if delta > 0 else ''}{delta:.1f}"
            print(f"  {var_wr:5.1f}% ({d})", end="")
        print()
    
    print(f"\n  {'FIELD-WEIGHTED':<25} {'':>6}  {base.field_wr:5.1f}%", end="")
    for v in variants:
        vr = results[v]
        delta = vr.field_wr - base.field_wr
        d = f"{'+' if delta > 0 else ''}{delta:.1f}"
        print(f"  {vr.field_wr:5.1f}% ({d})", end="")
    print("\n")
