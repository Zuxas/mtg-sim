"""
trace_game.py — Full turn-by-turn game trace with decision annotations

Runs a single game and prints every decision made by the APL,
including opponent hand model updates and CFR decision reasoning.

Usage:
    python trace_game.py --opponent "dimir reanimator" --seed 42
    python trace_game.py --opponent "dimir tempo" --turns 6
    python trace_game.py --opponent "mono red painter" --verbose
"""

import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponent", default="dimir reanimator")
    ap.add_argument("--deck-file", default="decks/humans_legacy.txt")
    ap.add_argument("--seed",      type=int, default=42)
    ap.add_argument("--turns",     type=int, default=8)
    ap.add_argument("--on-play",   action="store_true", default=True)
    ap.add_argument("--games",     type=int, default=1)
    args = ap.parse_args()

    from data.deck import load_deck_from_file
    from apl.humans import HumansAPL
    from sim_bridge import _infer_archetype_key
    from engine.opponent_model import OpponentHandModel
    from engine.decision import meddling_mage_name, turn_decision_summary

    main_deck, _ = load_deck_from_file(args.deck_file)
    opp_key = _infer_archetype_key(args.opponent)

    print(f"\n{'='*65}")
    print(f"GAME TRACE: Legacy Humans vs {args.opponent}")
    print(f"Opponent key: {opp_key}  |  On play: {args.on_play}")
    print(f"{'='*65}\n")

    for game_num in range(args.games):
        import random
        random.seed(args.seed + game_num)

        # Build APL with opponent model
        apl = HumansAPL()
        apl.set_opponent(opp_key, on_play=args.on_play)

        # Run verbose game
        result = apl.run_game(
            mainboard=main_deck,
            on_play=args.on_play,
            verbose=True,
        )

        print(f"\n{'─'*65}")
        print(f"Game {game_num+1} result: {'WON' if result.won else 'LOST'} "
              f"on turn {result.kill_turn}")

        # Show opponent hand model state at key turns
        model = OpponentHandModel(archetype_key=opp_key, on_play=args.on_play)
        print(f"\nOpponent hand model progression (vs {args.opponent}):")
        for turn in range(1, min(args.turns + 1, result.kill_turn + 1)):
            model.advance_turn()
            top = model.top_threats(3)
            p_int = model.p_has_interaction()
            print(f"\n  Turn {turn}:")
            print(f"    P(interaction) = {p_int:.0%}")
            for card, prob in top:
                bar = "█" * int(prob * 20)
                print(f"    {card:<35} {prob:.0%}  {bar}")

            # Show Meddling Mage naming recommendation
            best, ev, ranked = meddling_mage_name(model, turn=turn)
            print(f"    → Meddling Mage names: {best}  (EV={ev:.2f})")

        if args.games > 1:
            print()

    # Show multi-game summary
    if args.games > 1:
        print(f"\n{'='*65}")
        print(f"Summary: {args.games} games vs {args.opponent}")
        print(f"{'='*65}")


if __name__ == "__main__":
    main()
