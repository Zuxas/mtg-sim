"""
sb_optimizer.py — Sideboard card impact analysis for Bo3

Two measurement approaches:

1. CLOCK SHIFT MODEL (goldfish-valid):
   Each sb card has a known effect on the opponent's kill turn distribution.
   e.g. Grafdigger's Cage vs Reanimator pushes their T2 clock to T5+
   We model this as an opponent clock shift and measure match win% delta.

2. REAL DATA VALIDATION:
   Uses actual G1 vs match win% from the meta-analyzer DB to estimate
   how much the sb is helping/hurting vs real results.

Usage:
    python sb_optimizer.py --deck "Legacy Humans" --format legacy
    python sb_optimizer.py --deck "Legacy Humans" --format legacy --matchup "Dimir Reanimator"
"""

import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, race_win_pct, avg_kill_turn
from engine.bo3 import compute_match_win_pct, _adjust_opp_clock

# ---------------------------------------------------------------------------
# Sideboard card effect database
# How much each sb card shifts the opponent's avg kill turn (in turns)
# Positive = opponent kills later = better for us
# {card_name: {archetype_key: turn_shift}}
# ---------------------------------------------------------------------------
SB_CARD_EFFECTS = {
    # Graveyard hate — hard stops reanimation but costs tempo
    "Faerie Macabre": {
        "dimir reanimator": 1.5,   # T2 → T3.5, still fast but disrupted once
        "reanimator":       1.5,
        "cephalid breakfast": 1.2,
        "doomsday":         0.5,
        "hogaak":           1.0,
        "living end":       1.5,
        "default":          0.05,
    },
    "Grafdigger's Cage": {
        "dimir reanimator": 2.0,   # hard stops but they find Thoughtseize etc
        "reanimator":       2.0,
        "cephalid breakfast": 1.8,
        "doomsday":         0.3,
        "lotus combo":      0.5,
        "sneak and show":   0.2,
        "default":          0.05,
    },
    "Containment Priest": {
        "dimir reanimator": 1.8,
        "reanimator":       1.8,
        "sneak and show":   1.5,
        "cephalid breakfast": 1.5,
        "bant nadu":        0.8,
        "default":          0.05,
    },
    # Anti-combo — conditional but powerful when relevant
    "Deafening Silence": {
        "lotus combo":      2.5,   # real disruption but they can still play lands
        "doomsday":         1.0,
        "cephalid breakfast": 0.8,
        "sneak and show":   0.3,
        "mono red prison":  0.5,
        "default":          0.05,
    },
    "Clarion Conqueror": {
        "sneak and show":   1.8,   # prevents Show and Tell once
        "mono red prison":  1.0,
        "eldrazi stompy":   0.5,
        "default":          0.0,
    },
    # Artifact hate
    "Stony Silence": {
        "mono red painter": 2.5,   # prevents Grindstone but they still have creatures
        "painter":          2.5,
        "eldrazi stompy":   0.8,
        "default":          0.05,
    },
    # Removal — answers their threats but costs tempo for us
    "Path to Exile": {
        "eldrazi stompy":   0.7,
        "bant nadu":        0.9,
        "dimir tempo":      0.5,
        "izzet delver":     0.5,
        "death and taxes":  0.5,
        "default":          0.2,
    },
    "Swords to Plowshares": {
        "eldrazi stompy":   0.7,
        "dimir tempo":      0.5,
        "default":          0.2,
    },
    "Wrath of the Skies": {
        "eldrazi stompy":   1.3,
        "bant nadu":        1.5,
        "dimir tempo":      0.9,
        "death and taxes":  1.2,
        "default":          0.3,
    },
    # Protection / resilience
    "Sanctifier en-Vec": {
        "mono red painter": 1.2,
        "mono red aggro":   1.2,
        "dimir reanimator": 0.2,
        "default":          0.05,
    },
    "Sheltered by Ghosts": {
        "dimir tempo":      0.6,
        "izzet delver":     0.6,
        "default":          0.2,
    },
}

# Merge duplicate keys
_merged = {}
for card, effects in SB_CARD_EFFECTS.items():
    if card not in _merged:
        _merged[card] = {}
    for arch, shift in effects.items():
        if arch not in _merged[card] or shift > _merged[card][arch]:
            _merged[card][arch] = shift
SB_CARD_EFFECTS = _merged


def get_card_effect(card_name: str, opp_arch_key: str) -> float:
    """Return clock shift (turns) for a sb card vs an opponent archetype."""
    effects = SB_CARD_EFFECTS.get(card_name, {})
    # Try exact archetype key
    if opp_arch_key in effects:
        return effects[opp_arch_key]
    # Try partial match
    for arch_key, shift in effects.items():
        if arch_key != "default" and arch_key in opp_arch_key:
            return shift
    return effects.get("default", 0.0)


def shift_opp_clock(base_dist: dict, turn_shift: float) -> dict:
    """
    Shift an opponent's kill distribution by turn_shift turns later.
    Represents the effect of a sb card slowing their plan.
    """
    if turn_shift <= 0:
        return base_dist
    result = {}
    for t, pct in base_dist.items():
        new_t = t + int(round(turn_shift))
        result[new_t] = result.get(new_t, 0) + pct
    return result


def compute_matchup_with_sb(
    our_dist:   dict,
    opp_dist:   dict,
    sb_cards:   dict,          # {card_name: qty}
    opp_arch:   str,
    n_races:    int = 30000,
) -> tuple[float, float, float]:
    """
    Compute G1, G2, match win% for a matchup with a given sb.

    Key insight: sb cards replace creatures, which SLOWS our clock.
    Non-creature sb cards added = our clock slows by ~0.1 turns each.
    Opponent clock shifts by sum of card effects.
    """
    opp_key = _infer_archetype_key(opp_arch)

    # G1: pre-board, pure goldfish race
    g1 = race_win_pct(our_dist, opp_dist, n=n_races)

    # Count how many non-creature sb cards we're bringing in
    # (rough proxy — removal/hate costs tempo vs. creatures)
    non_creature_hate = sum(
        qty for card, qty in sb_cards.items()
        if card not in ("Sanctifier en-Vec",)  # creatures that help our clock
    )

    # Our clock slows by ~0.1 turn per non-creature sb card swapped in
    our_slowdown = non_creature_hate * 0.10
    our_dist_post = _adjust_opp_clock(our_dist, our_slowdown)  # reuse the shift fn

    # Opponent clock shifts by sum of sb card effects
    total_opp_shift = 0.0
    for card, qty in sb_cards.items():
        shift = get_card_effect(card, opp_key)
        total_opp_shift += shift * min(qty, 2)  # diminishing returns after 2 copies

    # Cap at realistic values
    total_opp_shift = min(total_opp_shift, 3.5)

    opp_dist_post = shift_opp_clock(opp_dist, total_opp_shift)

    # G2 on draw (we lost G1, opponent on play): slight disadvantage
    g2_on_draw = race_win_pct(our_dist_post, opp_dist_post, n=n_races)
    g2_on_draw = max(0, g2_on_draw - 3)  # ~3% penalty for being on draw

    # G2 on play (we won G1, we're on play)
    g2_on_play = race_win_pct(our_dist_post, opp_dist_post, n=n_races)

    g3 = (g2_on_draw + g2_on_play) / 2
    match_win = compute_match_win_pct(g1, g2_on_draw, g2_on_play, g3)

    return g1, g3, match_win


def optimize_sideboard(
    our_dist:    dict,
    sideboard:   dict,      # {card_name: qty}
    field:       dict,      # {archetype: share}
    opp_clocks:  dict,
    target_matchup: str = None,
) -> list[dict]:
    """
    For each sb card, measure its match win% contribution.
    Returns ranked list of card impact.
    """
    opponents = ([target_matchup] if target_matchup
                 else [o for o in field if field[o] > 0])

    # Baseline: full sb
    def weighted_avg(results):
        if target_matchup:
            return results.get(target_matchup, 0)
        total = sum(field.get(o, 1) for o in results)
        return sum(results[o] * field.get(o, 1) for o in results) / max(total, 0.001)

    print("\nBaseline (full sb):")
    baseline = {}
    for opp in opponents:
        opp_dist = opp_clocks.get(opp, ARCHETYPE_CLOCKS["unknown"])
        g1, g2, mw = compute_matchup_with_sb(our_dist, opp_dist, sideboard, opp)
        baseline[opp] = mw
        print(f"  vs {opp:<30} G1={g1:.0f}%  G2={g2:.0f}%  Match={mw:.1f}%")
    baseline_avg = weighted_avg(baseline)
    print(f"\nBaseline avg: {baseline_avg:.1f}%\n")

    card_results = []
    seen = set()

    for card_name in sideboard:
        if card_name in seen:
            continue
        seen.add(card_name)
        qty = sideboard[card_name]

        # Test without this card
        sb_without = {k: v for k, v in sideboard.items() if k != card_name}
        results_without = {}

        for opp in opponents:
            opp_dist = opp_clocks.get(opp, ARCHETYPE_CLOCKS["unknown"])
            _, _, mw = compute_matchup_with_sb(our_dist, opp_dist, sb_without, opp)
            results_without[opp] = mw

        avg_without = weighted_avg(results_without)
        delta = baseline_avg - avg_without

        matchup_deltas = {opp: round(baseline[opp] - results_without[opp], 1)
                         for opp in opponents}

        print(f"  {card_name:<30} {qty}x  delta: {delta:+.1f}%")
        card_results.append({
            "card":           card_name,
            "qty":            qty,
            "baseline":       baseline_avg,
            "without":        avg_without,
            "delta":          round(delta, 1),
            "matchup_deltas": matchup_deltas,
        })

    card_results.sort(key=lambda x: -x["delta"])
    return card_results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",      default="Legacy Humans")
    ap.add_argument("--format",    default="legacy")
    ap.add_argument("--top-n",     type=int, default=8)
    ap.add_argument("--n-games",   type=int, default=5000)
    ap.add_argument("--deck-file", default="decks/humans_legacy.txt")
    ap.add_argument("--matchup",   default="")
    args = ap.parse_args()

    from data.deck import load_deck_from_file
    from apl.humans import HumansAPL
    from engine.runner import run_simulation

    main_deck, side_deck = load_deck_from_file(args.deck_file)
    side_dict = {}
    for card in side_deck:
        side_dict[card.name] = side_dict.get(card.name, 0) + 1

    print(f"Sideboard ({sum(side_dict.values())} cards): {side_dict}")

    # Simulate our kill distribution
    print(f"\nSimulating kill distribution ({args.n_games} games)...")
    apl = HumansAPL()
    sim = run_simulation(apl, main_deck, n=args.n_games, on_play=True, seed=42)
    our_dist = sim.kill_turn_distribution()
    print(f"Avg kill: T{avg_kill_turn(our_dist):.2f}")

    # Field
    try:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=args.format, min_matches=10)
        field  = bridge.field_shares(top_n=args.top_n)
        print(f"\nField: top {args.top_n} {args.format.upper()} archetypes")
        for arch, share in field.items():
            print(f"  {arch:<35} {share*100:.1f}%")
    except Exception as e:
        print(f"MetaBridge unavailable ({e}), using locals field")
        field = {
            "Dimir Reanimator": 0.22, "Lotus Combo": 0.10,
            "Dimir Tempo": 0.10, "Cephalid Breakfast": 0.07,
            "Eldrazi Stompy": 0.06, "Sneak And Show": 0.05,
            "Mono Red Painter": 0.05, "Doomsday": 0.05,
        }

    opp_clocks = {}
    for arch in field:
        key = _infer_archetype_key(arch)
        opp_clocks[arch] = ARCHETYPE_CLOCKS.get(key, ARCHETYPE_CLOCKS["unknown"])

    target = args.matchup if args.matchup else None
    results = optimize_sideboard(
        our_dist=our_dist,
        sideboard=side_dict,
        field=field,
        opp_clocks=opp_clocks,
        target_matchup=target,
    )

    # Print results
    print(f"\n{'='*65}")
    print(f"Sideboard Card Rankings — {args.deck}")
    if target:
        print(f"(Optimized for: {target})")
    print(f"{'='*65}")
    print(f"  {'Card':<32} {'Qty':>3}  {'Value':>7}  {'w/o Card':>8}")
    print(f"  {'-'*58}")
    for r in results:
        arrow = "▲" if r["delta"] > 0.5 else ("▼" if r["delta"] < -0.5 else "≈")
        print(f"  {r['card']:<32} {r['qty']:>3}x  {r['delta']:>+6.1f}%  "
              f"{r['without']:>7.1f}% {arrow}")

    print(f"\n  Baseline match win% (full sb): {results[0]['baseline']:.1f}%")

    # Per-matchup breakdown
    print(f"\n{'='*65}")
    print("Per-matchup value of each sb card:")
    opps = list(results[0]["matchup_deltas"].keys()) if results else []
    hdr  = f"  {'Card':<28}"
    for o in opps[:6]:
        hdr += f"  {o[:11]:>11}"
    print(hdr)
    print("  " + "-"*90)
    for r in results:
        row = f"  {r['card']:<28}"
        for o in opps[:6]:
            d = r["matchup_deltas"].get(o, 0)
            row += f"  {d:>+10.1f}%"
        print(row)


if __name__ == "__main__":
    main()
