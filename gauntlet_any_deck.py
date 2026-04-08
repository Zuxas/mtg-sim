"""Quick wrapper to run any playbook deck through the Bo3 gauntlet."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mtg-meta-analyzer'))

import argparse
from apl.playbook_parser import load_all_playbooks, load_all_tac_guides, find_playbook
from apl.generic_apl import generic_from_playbook, GenericAPL
from sim_any_deck import load_deck_from_playbook
from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, race_win_pct, avg_kill_turn
from engine.runner import run_simulation
from engine.bo3 import compute_match_win_pct

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("--format",  default="modern")
    ap.add_argument("--top-n",   type=int, default=12)
    ap.add_argument("--n-games", type=int, default=1000)
    ap.add_argument("--sims",    type=int, default=1000)
    args = ap.parse_args()

    pbs = {**load_all_playbooks(), **load_all_tac_guides()}
    pb  = find_playbook(args.deck, pbs)
    if not pb:
        print(f"Playbook not found: {args.deck}")
        return

    main_deck, side_deck = load_deck_from_playbook(pb)
    if not main_deck:
        print(f"Could not build deck for: {args.deck}")
        return

    side_dict = {}
    for card in (side_deck or []):
        side_dict[card.name] = side_dict.get(card.name, 0) + 1

    apl = generic_from_playbook(pb)
    print(f"\nSimulating {args.deck} ({len(main_deck)} cards)...")
    sim = run_simulation(apl, main_deck, n=args.n_games, on_play=True, seed=42)
    our_dist = sim.kill_turn_distribution()
    print(f"Kill dist: T{avg_kill_turn(our_dist):.2f} avg")

    # Build field
    try:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=args.format, min_matches=10)
        field  = bridge.field_shares(top_n=args.top_n)
        real_matrix = bridge.real_matchup_matrix()
        print(f"Field: top {args.top_n} {args.format.upper()} archetypes")
    except Exception as e:
        print(f"MetaBridge error: {e}")
        return

    # Compute G1 and match win% per opponent
    print(f"\n{'='*65}")
    print(f"Bo3 Gauntlet: {args.deck} vs {args.format.upper()} top-{args.top_n}")
    print(f"{'='*65}")
    print(f"\n  {'Opponent':<30} {'G1':>6}  {'Match':>7}  {'Diff':>6}")
    print(f"  {'-'*55}")

    matchup_table = {}
    total_weight = 0

    for opp_arch, share in field.items():
        if opp_arch.lower() == args.deck.lower():
            continue

        opp_key  = _infer_archetype_key(opp_arch)
        opp_dist = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"])

        # G1: real data > goldfish race
        real_g1 = None
        if real_matrix:
            our_c = args.deck.lower().replace(" ","").replace("-","")
            opp_c = opp_arch.lower().replace(" ","").replace("-","")
            for (a, b), wp in real_matrix.items():
                a_c = a.lower().replace(" ","").replace("-","")
                b_c = b.lower().replace(" ","").replace("-","")
                if our_c in a_c and opp_c in b_c:
                    real_g1 = wp; break
                elif opp_c in a_c and our_c in b_c:
                    real_g1 = 100 - wp; break

        g1 = real_g1 if real_g1 is not None else race_win_pct(our_dist, opp_dist, n=20000)

        # Sb premium by opponent speed
        opp_avg = avg_kill_turn(opp_dist)
        if opp_avg <= 3.0:   sb = 2.0
        elif opp_avg <= 4.5: sb = 5.0
        elif opp_avg <= 6.0: sb = 7.0
        else:                sb = 9.0

        match = min(99.0, g1 + sb)
        diff  = match - g1
        matchup_table[opp_arch] = match
        total_weight += share

        src = "(real)" if real_g1 is not None else "(sim) "
        print(f"  {opp_arch:<30} {g1:>5.1f}%  {match:>6.1f}%  {diff:>+5.1f}%  {src}")

    field_avg = sum(matchup_table[o] * field.get(o, 0)
                    for o in matchup_table) / max(total_weight, 0.001)
    print(f"  {'-'*55}")
    print(f"  {'FIELD-WEIGHTED':<30} {'':>6}  {field_avg:>6.1f}%")

    # Event projections
    print(f"\n{'='*65}")
    print(f"Event projections:")
    from event_simulator import simulate_event
    for event_name, n_players, n_rounds in [
        ("Local (50p)",   50,  6),
        ("RPTQ (100p)",  100,  7),
        ("RC (300p)",    300,  9),
        ("PT (400p)",    400, 15),
    ]:
        r = simulate_event(
            our_deck=args.deck,
            matchup_table=matchup_table,
            field=field,
            rounds=n_rounds,
            players=n_players,
            simulations=args.sims,
        )
        print(f"  {event_name:<20} {n_rounds:>2}r  Day2: {r['day2_rate']:>5.1f}%  "
              f"Top8: {r['top8_rate']:>5.1f}%  Exp: {r['expected_record']}")


if __name__ == "__main__":
    main()
