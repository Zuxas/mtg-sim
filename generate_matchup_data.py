"""
generate_matchup_data.py — Run both-sides sims for all archetype pairs

For each matchup in the Legacy top-15:
  1. Load both decks from playbooks / hand-tuned lists
  2. Run N games with both APLs playing their real game plan
  3. Record win rates, kill turns, game logs
  4. Write results to meta-analyzer DB format
  5. Update real_matchup_matrix for the event simulator

Usage:
    python generate_matchup_data.py --our-deck "Legacy Humans" --format legacy --n 1000
    python generate_matchup_data.py --all-pairs --format legacy --n 500
    python generate_matchup_data.py --matchup "Legacy Humans" "Dimir Tempo" --n 2000
"""

import sys, os, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mtg-meta-analyzer'))

from engine.match_runner import run_match_set, MatchSetResults
from sim_bridge import _infer_archetype_key, avg_kill_turn


def load_deck_and_apl(deck_name: str, format_name: str = "legacy"):
    """
    Load a deck and APL by name.
    Priority: hand-tuned APL → real stub from DB → legacy stub → GenericAPL
    """
    from apl.generic_apl import GenericAPL
    from data.card import Card
    from engine.card_db import CardDB

    _db = CardDB()

    def build_deck_from_dict(card_dict):
        """Convert {card_name: qty} dict to list of Card objects."""
        deck = []
        for card_name, qty in card_dict.items():
            for _ in range(qty):
                data = _db.get(card_name)
                if data:
                    deck.append(Card(
                        name=data.get("name", card_name),
                        mana_cost=data.get("mana_cost", ""),
                        cmc=float(data.get("cmc", 2)),
                        type_line=data.get("type_line", ""),
                        oracle_text=data.get("oracle_text", ""),
                        power=data.get("power"),
                        toughness=data.get("toughness"),
                        colors=data.get("colors", []),
                    ))
                else:
                    # Minimal placeholder card
                    deck.append(Card(
                        name=card_name, mana_cost="{1}", cmc=1,
                        type_line="Creature", oracle_text="",
                        power="1", toughness="1", colors=[],
                    ))
        return deck

    # 1. Hand-tuned APLs
    deck_key = deck_name.lower().replace(" ", "").replace("-", "").replace("'", "")
    if deck_key in ("legacyhumans", "humans"):
        from apl.humans import HumansAPL
        from data.deck import load_deck_from_file
        main, side = load_deck_from_file("decks/humans_legacy.txt")
        return main, side, HumansAPL()

    if deck_key == "borosenergy":
        from apl.boros_energy import BorosEnergyAPL
        try:
            from data.stub_decks import get_stub_deck_list
            mb = get_stub_deck_list("boros_energy")
            if mb:
                main = build_deck_from_dict(mb)
                return main, [], BorosEnergyAPL()
        except Exception:
            pass

    if deck_key in ("izzetprowess", "prowess"):
        from apl.izzet_prowess import IzzetProwessAPL
        try:
            from data.stub_decks import get_stub_deck_list
            mb = get_stub_deck_list("izzet_prowess")
            if mb:
                main = build_deck_from_dict(mb)
                return main, [], IzzetProwessAPL()
        except Exception:
            pass

    # 2. Real stub from DB
    try:
        from data.stub_decks import get_stub_deck_list
        mb = get_stub_deck_list(deck_name)
        if mb and sum(mb.values()) >= 40:
            main = build_deck_from_dict(mb)
            apl  = GenericAPL(deck_name)
            return main, [], apl
    except Exception:
        pass

    # 3. Legacy hardcoded stubs
    try:
        from data.stub_decks import get_stub_deck
        stub = get_stub_deck(deck_name)
        if stub and len(stub) >= 40:
            return stub, [], GenericAPL(deck_name)
    except Exception:
        pass

    # 4. Playbook
    try:
        from apl.playbook_parser import load_all_playbooks, load_all_tac_guides, find_playbook
        pbs = {**load_all_playbooks(), **load_all_tac_guides()}
        pb  = find_playbook(deck_name, pbs)
        if pb and pb.mainboard and sum(pb.mainboard.values()) >= 40:
            lines = [f"{q} {n}" for n, q in pb.mainboard.items()]
            from data.deck import load_deck_from_text
            main, side = load_deck_from_text("\n".join(lines))
            if len(main) >= 40:
                from apl.generic_apl import generic_from_playbook
                return main, side, generic_from_playbook(pb)
    except Exception:
        pass

    print(f"  [No deck found for {deck_name}]")
    return None, None, None
    """
    Load a deck and its APL by name.
    Priority: hand-tuned APL → AutoAPL → GenericAPL
    """
    from apl.playbook_parser import (load_all_playbooks, load_all_tac_guides,
                                      find_playbook)
    from apl.generic_apl import generic_from_playbook, GenericAPL
    from data.deck import load_deck_from_file

    # Special case: our own decks
    deck_files = {
        "legacy humans": "decks/humans_legacy.txt",
        "humans":        "decks/humans_legacy.txt",
    }
    deck_key = deck_name.lower().replace(" ", "").replace("-","")
    for k, path in deck_files.items():
        if deck_key == k.replace(" ",""):
            from apl.humans import HumansAPL
            main, side = load_deck_from_file(path)
            apl = HumansAPL()
            return main, side, apl

    # Load from playbooks
    pbs = {**load_all_playbooks(), **load_all_tac_guides()}
    pb  = find_playbook(deck_name, pbs)

    if pb and pb.mainboard and sum(pb.mainboard.values()) >= 40:
        # Build deck from playbook
        lines = []
        for card, qty in pb.mainboard.items():
            lines.append(f"{qty} {card}")
        for card, qty in (pb.sideboard or {}).items():
            lines.append(f"SB: {qty} {card}")

        try:
            from data.deck import load_deck_from_text
            main, side = load_deck_from_text("\n".join(lines))
            if len(main) >= 40:
                apl = generic_from_playbook(pb)
                return main, side, apl
        except Exception as e:
            print(f"  [Deck load failed for {deck_name}: {e}]")

    print(f"  [No playbook for {deck_name} — trying stub deck]")
    from data.stub_decks import get_stub_deck
    from engine.match_runner import ComboKillSampler
    from apl.generic_apl import GenericAPL

    # Check if this is a known combo archetype — use named APL for sampler detection
    combo_keys = set(ComboKillSampler.KILL_DISTS.keys())
    d_key = deck_name.lower().replace(" ","").replace("-","")
    is_combo = any(k.replace(" ","") == d_key for k in combo_keys)

    stub = get_stub_deck(deck_name)
    if stub and len(stub) >= 40:
        apl = GenericAPL(deck_name)   # name matters — sampler matches on it
        return stub, [], apl

    print(f"  [No deck found for {deck_name} — skipping]")
    return None, None, None


def run_matchup(
    deck_a_name:  str,
    deck_b_name:  str,
    format_name:  str = "legacy",
    n:            int = 1000,
    seed:         int = 42,
) -> dict:
    """Run a single matchup between two named decks. Returns result dict."""
    print(f"\n{deck_a_name} vs {deck_b_name} ({n} games)...")

    deck_a, side_a, apl_a = load_deck_and_apl(deck_a_name, format_name)
    deck_b, side_b, apl_b = load_deck_and_apl(deck_b_name, format_name)

    if not deck_a or not deck_b:
        print(f"  Skipping — could not load both decks")
        return {}

    print(f"  A: {deck_a_name} ({len(deck_a)} cards, APL: {apl_a.name})")
    print(f"  B: {deck_b_name} ({len(deck_b)} cards, APL: {apl_b.name})")

    results = run_match_set(apl_a, deck_a, apl_b, deck_b,
                             n=n, seed=seed, mix_play_draw=True)

    wp_a = results.win_pct()
    print(f"  Result: {deck_a_name} wins {wp_a:.1f}%  "
          f"({results.a_wins}/{n})  avg T{results.avg_turns:.1f}")

    return {
        "deck_a":     deck_a_name,
        "deck_b":     deck_b_name,
        "format":     format_name,
        "n_games":    n,
        "a_win_pct":  wp_a,
        "b_win_pct":  round(100 - wp_a, 1),
        "avg_turns":  round(results.avg_turns, 2),
        "kill_dist":  results.kill_turn_distribution(),
        "source":     "sim_v1",
    }


def run_our_matchups(
    our_deck:    str = "Legacy Humans",
    format_name: str = "legacy",
    top_n:       int = 15,
    n:           int = 1000,
    output_path: str = "data/sim_matchup_data.json",
):
    """Run our deck vs the entire field. Saves results to JSON."""
    try:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=format_name, min_matches=10)
        field  = bridge.field_shares(top_n=top_n)
        print(f"Field: top {top_n} {format_name.upper()} archetypes")
    except Exception as e:
        print(f"MetaBridge unavailable ({e}) — using default field")
        field = {
            "Dimir Reanimator": 0.22, "Lotus Combo": 0.105,
            "Dimir Tempo": 0.105, "Cephalid Breakfast": 0.075,
            "Eldrazi Stompy": 0.064, "Sneak And Show": 0.054,
            "Mono Red Painter": 0.05, "Doomsday": 0.049,
            "Izzet Delver": 0.047, "Death And Taxes": 0.046,
            "Bant Nadu": 0.043, "Four-Color": 0.037,
            "Jeskai Control": 0.036, "Mono Red Aggro": 0.034,
            "Mono Red Prison": 0.032,
        }

    results = []
    for opp_name in field:
        if opp_name.lower() == our_deck.lower():
            continue
        r = run_matchup(our_deck, opp_name, format_name, n)
        if r:
            results.append(r)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} matchup results to {output_path}")

    # Summary table
    print(f"\n{'='*60}")
    print(f"Both-sides sim results: {our_deck} vs {format_name.upper()} field")
    print(f"{'='*60}")
    print(f"  {'Opponent':<30} {'Win%':>6}  {'AvgT':>5}")
    print(f"  {'-'*45}")
    for r in sorted(results, key=lambda x: -x['a_win_pct']):
        print(f"  {r['deck_b']:<30} {r['a_win_pct']:>5.1f}%  T{r['avg_turns']:.1f}")

    field_avg = sum(r['a_win_pct'] * field.get(r['deck_b'], 1/len(results))
                    for r in results) / sum(field.get(r['deck_b'], 1/len(results))
                                            for r in results)
    print(f"\n  Field-weighted win%: {field_avg:.1f}%")
    return results


def update_real_matrix(sim_results: list, output_path: str = "data/sim_matchup_matrix.json"):
    """
    Convert sim results to real_matchup_matrix format for event_simulator.
    Format: {(deck_a, deck_b): win_pct_a}
    """
    matrix = {}
    for r in sim_results:
        matrix[r['deck_a']] = matrix.get(r['deck_a'], {})
        matrix[r['deck_a']][r['deck_b']] = r['a_win_pct']
        matrix[r['deck_b']] = matrix.get(r['deck_b'], {})
        matrix[r['deck_b']][r['deck_a']] = r['b_win_pct']

    with open(output_path, 'w') as f:
        json.dump(matrix, f, indent=2)
    print(f"Matrix saved: {output_path}")
    return matrix


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--our-deck",   default="Legacy Humans")
    ap.add_argument("--format",     default="legacy")
    ap.add_argument("--top-n",      type=int, default=15)
    ap.add_argument("--n",          type=int, default=500)
    ap.add_argument("--matchup",    nargs=2, metavar=("DECK_A", "DECK_B"))
    ap.add_argument("--all-pairs",  action="store_true")
    ap.add_argument("--output",     default="data/sim_matchup_data.json")
    args = ap.parse_args()

    if args.matchup:
        r = run_matchup(args.matchup[0], args.matchup[1], args.format, args.n)
        if r:
            print(f"\n{args.matchup[0]} vs {args.matchup[1]}: {r['a_win_pct']:.1f}%")
    else:
        results = run_our_matchups(
            args.our_deck, args.format, args.top_n, args.n, args.output
        )
        if results:
            update_real_matrix(results)


if __name__ == "__main__":
    main()
