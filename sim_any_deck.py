"""
sim_any_deck.py — Simulate any deck from playbook data

Uses GenericAPL (CMC-order play) for decks without hand-tuned APLs.
Automatically loads the correct playbook, builds a deck, runs simulation.

Usage:
    python sim_any_deck.py "Boros Energy"
    python sim_any_deck.py "Amulet Titan" --format modern --games 2000
    python sim_any_deck.py --list
    python sim_any_deck.py --gauntlet --format modern --top-n 10
"""

import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def load_deck_from_playbook(pb):
    """Build a Card list from a PlaybookData mainboard dict."""
    from data.deck import load_deck_from_text
    if not pb.mainboard:
        return None, None
    lines = []
    for card_name, qty in pb.mainboard.items():
        lines.append(f"{qty} {card_name}")
    for card_name, qty in (pb.sideboard or {}).items():
        lines.append(f"SB: {qty} {card_name}")
    text = "\n".join(lines)
    try:
        main, side = load_deck_from_text(text)
        if len(main) < 40:
            return None, None
        return main, side
    except Exception as e:
        print(f"  [deck load failed: {e}]")
        return None, None


def simulate_deck(deck_name: str, format_name: str = "modern",
                  n_games: int = 2000, verbose: bool = False):
    """Simulate a single deck and return kill distribution."""
    from apl.playbook_parser import load_all_playbooks, find_playbook, load_all_tac_guides
    from apl.generic_apl import generic_from_playbook, GenericAPL
    from engine.runner import run_simulation
    from sim_bridge import avg_kill_turn

    pbs = {**load_all_playbooks(), **load_all_tac_guides()}
    pb = find_playbook(deck_name, pbs)

    if not pb:
        print(f"Playbook not found: {deck_name}")
        return None

    main, side = load_deck_from_playbook(pb)
    if not main:
        print(f"Could not build deck for: {deck_name}")
        return None

    apl = generic_from_playbook(pb)
    sim = run_simulation(apl, main, n=n_games, on_play=True, seed=42,
                        verbose_first=1 if verbose else 0)
    dist = sim.kill_turn_distribution()
    wr = sim.won_games / sim.n_games * 100
    print(f"{deck_name:<35} T{avg_kill_turn(dist):.2f}  "
          f"win={sim.won_games}/{sim.n_games}  "
          f"avg_mull={sum(sim.mulligans)/max(1,len(sim.mulligans)):.1f}")
    return dist


def run_gauntlet(format_name: str = "modern", n_games: int = 1000, top_n: int = 10):
    """Simulate all valid playbook decks and rank by kill speed."""
    from apl.playbook_parser import load_all_playbooks
    from sim_bridge import avg_kill_turn

    pbs = load_all_playbooks()
    valid = {name: pb for name, pb in pbs.items()
             if pb.mainboard and sum(pb.mainboard.values()) >= 55}

    print(f"\nRunning gauntlet: {len(valid)} decks ({format_name.upper()})\n")
    print(f"  {'Deck':<35} {'AvgKill':>8} {'WinRate':>8}")
    print("  " + "-"*55)

    results = []
    for name, pb in sorted(valid.items()):
        try:
            from apl.playbook_parser import load_all_playbooks, load_all_tac_guides
            from apl.generic_apl import generic_from_playbook
            from engine.runner import run_simulation

            main, side = load_deck_from_playbook(pb)
            if not main:
                continue
            apl = generic_from_playbook(pb)
            sim = run_simulation(apl, main, n=n_games, on_play=True, seed=42)
            dist = sim.kill_turn_distribution()
            avg = avg_kill_turn(dist)
            wr  = sim.won_games / sim.n_games * 100
            results.append((name, avg, wr, dist))
            print(f"  {name:<35} T{avg:>5.2f}   {wr:>6.1f}%")
        except Exception as e:
            print(f"  {name:<35} [ERROR: {e}]")

    results.sort(key=lambda x: x[1])
    print("\n" + "="*55)
    print("Rankings by kill speed:")
    for i, (name, avg, wr, _) in enumerate(results, 1):
        print(f"  {i:2}. {name:<35} T{avg:.2f}")

    return results


def list_decks():
    """List all available playbooks with their status."""
    from apl.playbook_parser import load_all_playbooks
    pbs = load_all_playbooks()
    print(f"\nAvailable playbooks ({len(pbs)} total):\n")
    print(f"  {'Deck':<35} {'Main':>5}  {'Matchups':>8}  {'Status'}")
    print("  " + "-"*65)
    for name in sorted(pbs.keys()):
        pb = pbs[name]
        mb = sum(pb.mainboard.values()) if pb.mainboard else 0
        mu = len(pb.matchups)
        status = "ready" if mb >= 55 else ("partial" if mb > 0 else "no list")
        print(f"  {name:<35} {mb:>5}  {mu:>8}  {status}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck", nargs="?", default="")
    ap.add_argument("--format",  default="modern")
    ap.add_argument("--games",   type=int, default=2000)
    ap.add_argument("--list",    action="store_true")
    ap.add_argument("--gauntlet",action="store_true")
    ap.add_argument("--top-n",   type=int, default=10)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.list:
        list_decks()
    elif args.gauntlet:
        run_gauntlet(args.format, args.games, args.top_n)
    elif args.deck:
        simulate_deck(args.deck, args.format, args.games, args.verbose)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
