"""
sim_any_deck.py — Simulate any deck by name using playbook data + GenericAPL

Usage:
    python sim_any_deck.py "Boros Energy"
    python sim_any_deck.py "Living End"
    python sim_any_deck.py --list
    python sim_any_deck.py "Boros Energy" --gauntlet
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mtg-meta-analyzer'))

from apl.playbook_parser import load_all_playbooks, load_all_tac_guides, find_playbook
from apl.generic_apl import generic_from_playbook
from engine.runner import run_simulation
from data.deck import load_deck_from_text


def sim_deck_from_playbook(deck_name: str, n: int = 3000) -> dict:
    """Simulate a deck using its playbook. Returns result summary dict."""
    pbs = {**load_all_playbooks(), **load_all_tac_guides()}
    pb  = find_playbook(deck_name, pbs)

    if not pb:
        print(f"No playbook found for '{deck_name}'")
        return {}

    if not pb.mainboard:
        print(f"Playbook found ({pb.deck_name}) but has no decklist")
        return {}

    print(f"Deck:      {pb.deck_name} [{pb.format_name}]")
    print(f"Role:      {pb.role}")
    print(f"Kill Turn: {pb.kill_turn} (expected avg T{pb.avg_kill_turn():.1f})")
    print(f"Cards:     {sum(pb.mainboard.values())} main / {sum(pb.sideboard.values())} side")
    print()

    # Build deck from playbook
    decklist_txt = "\n".join(f"{qty} {name}" for name, qty in pb.mainboard.items())
    try:
        main, _ = load_deck_from_text(decklist_txt)
    except Exception as e:
        print(f"Deck load error: {e}")
        return {}

    if len(main) < 40:
        print(f"Warning: only {len(main)} cards loaded — some cards may be missing from Scryfall cache")

    # Create APL
    apl = generic_from_playbook(pb)

    # Run sim
    print(f"Simulating {n} games…")
    r = run_simulation(apl, main, n=n, on_play=True, seed=42)

    avg   = r.avg_kill_turn()
    med   = r.median_kill_turn()
    win   = r.win_rate() * 100
    mull  = r.mull_rate()
    dist  = r.kill_turn_distribution()

    print(f"\nResults ({n} games):")
    print(f"  Avg kill:  T{avg:.2f}")
    print(f"  Median:    T{med:.0f}")
    print(f"  Win rate:  {win:.1f}%")
    print(f"  Mull rate: {mull:.0f}%")
    print(f"  Expected:  T{pb.avg_kill_turn():.1f} (from playbook)")
    print()
    print("Kill distribution:")
    for t, p in sorted(dist.items()):
        bar = "█" * int(p / 2.5)
        print(f"  T{t:2d}: {p:5.1f}%  {bar}")

    return {
        "deck_name":  pb.deck_name,
        "format":     pb.format_name,
        "avg_kill":   avg,
        "median":     med,
        "win_rate":   win,
        "mull_rate":  mull,
        "expected":   pb.avg_kill_turn(),
        "dist":       dist,
    }


def list_available():
    pbs  = load_all_playbooks()
    tacs = load_all_tac_guides()
    all_pbs = {**pbs, **tacs}
    print(f"\n{len(all_pbs)} decks available:\n")
    by_format = {}
    for name, pb in all_pbs.items():
        fmt = pb.format_name or "Unknown"
        by_format.setdefault(fmt, []).append((name, pb))
    for fmt in sorted(by_format):
        print(f"  {fmt}:")
        for name, pb in sorted(by_format[fmt], key=lambda x: x[0]):
            cards = sum(pb.mainboard.values())
            print(f"    {name:<40} T{pb.kill_turn:<8} {cards}main")
        print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "--list" in args:
        list_available()
    else:
        deck_name = " ".join(a for a in args if not a.startswith("--"))
        n = 3000
        for a in args:
            if a.startswith("--n="):
                n = int(a.split("=")[1])
        sim_deck_from_playbook(deck_name, n=n)
