"""
bo3_gauntlet.py — Run a full Bo3 gauntlet for any deck

Usage:
    python bo3_gauntlet.py --deck "Legacy Humans" --format legacy
    python bo3_gauntlet.py --deck "Boros Energy" --format modern --top-n 10
    python bo3_gauntlet.py --deck "Legacy Humans" --format legacy --field "Elves,Painter,Hogaak,Lands,UR Delver,Stoneforge Midrange"
"""

import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sim_bridge import ARCHETYPE_CLOCKS, avg_kill_turn, _infer_archetype_key
from mismodeled_matchups import mismodel_flag, legend


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",    default="Legacy Humans")
    ap.add_argument("--format",  default="legacy")
    ap.add_argument("--top-n",   type=int, default=8)
    ap.add_argument("--field",   default="")
    ap.add_argument("--n-games", type=int, default=1000)
    ap.add_argument("--deck-file", default="decks/humans_legacy.txt")
    args = ap.parse_args()

    # ── Load our deck ─────────────────────────────────────────────────────
    from data.deck import load_deck_from_file, load_deck_from_text
    from apl.humans import HumansAPL
    from apl.generic_apl import GenericAPL
    from apl.playbook_parser import load_all_playbooks, find_playbook

    deck_file = args.deck_file or "decks/humans_legacy.txt"
    main_deck, side_deck = load_deck_from_file(deck_file)
    side_dict = {}
    for card in side_deck:
        side_dict[card.name] = side_dict.get(card.name, 0) + 1

    print(f"Loaded: {len(main_deck)} main / {len(side_deck)} side")

    # Choose APL
    arch_key = _infer_archetype_key(args.deck)
    if arch_key == "humans":
        our_apl = HumansAPL()
    else:
        pbs = load_all_playbooks()
        pb  = find_playbook(args.deck, pbs)
        from apl.generic_apl import generic_from_playbook
        our_apl = generic_from_playbook(pb) if pb else GenericAPL(args.deck)

    print(f"APL: {our_apl.name}")

    # ── Build field ───────────────────────────────────────────────────────
    if args.field:
        names  = [n.strip() for n in args.field.split(",")]
        field  = {n: 1/len(names) for n in names}
    else:
        try:
            from meta_bridge import MetaBridge
            bridge = MetaBridge(format_name=args.format, min_matches=10)
            field  = bridge.field_shares(top_n=args.top_n)
            print(f"\nReal {args.format.upper()} field (top {args.top_n}):")
            for arch, share in list(field.items())[:args.top_n]:
                print(f"  {arch:<35} {share*100:.1f}%")
        except Exception as e:
            print(f"MetaBridge unavailable ({e}), using format_config field")
            try:
                from format_config import get_field
                field_raw = get_field(args.format or "modern", top_n=args.top_n)
                total = sum(field_raw.values())
                field = {k: v/total for k, v in field_raw.items()}
                print(f"  Loaded {len(field)} archetypes from format_config ({args.format})")
            except Exception as e2:
                print(f"format_config also failed ({e2}), using stub field")
                field = {k: 1/6 for k in ["elves","painter","hogaak","lands","delver","stoneforge"]}

    # Build opponent kill distributions
    opp_clocks = {}
    _fmt = (args.format or "").lower().replace(" ", "")
    for arch in field:
        key = _infer_archetype_key(arch)
        # Try format-qualified key first (e.g. "izzetprowessstandard") so Standard
        # and Modern clocks don't collide on shared archetype names.
        fmt_key = key + _fmt if _fmt and _fmt != "legacy" else key
        opp_clocks[arch] = ARCHETYPE_CLOCKS.get(fmt_key,
                           ARCHETYPE_CLOCKS.get(key, ARCHETYPE_CLOCKS["unknown"]))

    # ── Load real matchup data ────────────────────────────────────────────
    real_matrix = {}
    try:
        from meta_bridge import MetaBridge
        bridge      = MetaBridge(format_name=args.format, min_matches=10)
        real_matrix = bridge.real_matchup_matrix()
        print(f"\nReal matchup data: {len(real_matrix)} pairs loaded")
    except Exception:
        pass

    # ── Load playbooks for sideboard plans ───────────────────────────────
    from apl.playbook_parser import load_all_tac_guides
    playbooks = {**load_all_playbooks(), **load_all_tac_guides()}

    # ── Run Bo3 gauntlet ──────────────────────────────────────────────────
    from engine.bo3 import simulate_bo3_gauntlet
    from sim_bridge import race_win_pct, avg_kill_turn
    from engine.runner import run_simulation as _rs
    from data.deck import load_deck_from_file as _ldf

    print(f"\n{'='*60}")
    print(f"Bo3 Gauntlet: {args.deck} vs {len(field)}-deck field")
    print(f"{'='*60}\n")

    # Simulate our kill distribution
    _main, _side = _ldf(args.deck_file)
    _sim = _rs(our_apl, _main, n=3000, on_play=True, seed=42)
    our_dist = _sim.kill_turn_distribution()
    print(f"Our kill dist: T{avg_kill_turn(our_dist):.2f} avg\n")

    # Build G1 win rates: real data > goldfish race
    print("G1 win rates:")
    for opp_arch in field:
        opp_key  = _infer_archetype_key(opp_arch)
        opp_dist = opp_clocks.get(opp_arch, ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"]))

        # Check real match data
        real_g1 = None
        if real_matrix:
            our_clean = args.deck.lower().replace(" ","").replace("-","")
            opp_clean = opp_arch.lower().replace(" ","").replace("-","")
            for (a, b), wp in real_matrix.items():
                a_c = a.lower().replace(" ","").replace("-","")
                b_c = b.lower().replace(" ","").replace("-","")
                if our_clean in a_c and opp_clean in b_c:
                    real_g1 = wp
                    break
                elif opp_clean in a_c and our_clean in b_c:
                    real_g1 = 100 - wp
                    break

        if real_g1 is not None:
            g1 = real_g1
            src = "real"
        else:
            g1 = race_win_pct(our_dist, opp_dist, n=30000)
            src = "sim"

        opp_clocks[opp_arch] = {"_g1": g1, "_dist": opp_dist}
        print(f"  {opp_arch:<35} G1: {g1:.1f}% ({src})")

    gauntlet = simulate_bo3_gauntlet(
        our_deck_name=args.deck,
        our_apl=our_apl,
        our_mainboard=main_deck,
        our_sideboard=side_dict,
        field=field,
        opp_clocks=opp_clocks,
        n_games=args.n_games,
        format_name=args.format,
        playbooks=playbooks,
        real_matchup_matrix=real_matrix,
    )

    print()
    print(gauntlet.summary_table())
    print(f"\nField-weighted match win rate: {gauntlet.avg_match_win:.1f}%")

    # Compare G1 vs Match
    print(f"\n{'='*60}")
    print("G1 vs Match win rate comparison:")
    print(f"  {'Opponent':<28} {'G1':>6}  {'Match':>7}  {'Diff':>7}")
    print("  " + "-"*52)
    for r in sorted(gauntlet.matchups, key=lambda x: -x.match_win_pct):
        diff = r.match_win_pct - r.g1_win_pct
        arrow = "^" if diff > 1 else ("v" if diff < -1 else "~")
        print(f"  {r.opponent:<28} {r.g1_win_pct:>5.1f}%  {r.match_win_pct:>6.1f}%  "
              f"{diff:>+6.1f}% {arrow}{mismodel_flag(r.opponent)}")

    print(legend())


if __name__ == "__main__":
    main()
