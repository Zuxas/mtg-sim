"""Trace ONE game of Jermey Dimir vs Azorius High Noon to see what fires."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    apl_a = get_match_apl('dimirmidrangejermey')
    apl_b = get_match_apl('azoriushighnoon')
    deck_a, _ = load_deck_from_file('decks/dimir_midrange_jermey_standard.txt')
    deck_b, _ = load_deck_from_file('decks/azorius_high_noon_standard.txt')

    print("\n=== probe: does _vs_high_noon detection fire? ===")
    # Build a fake opponent state with HN cards in library
    from data.card import Card
    from engine.game_state import GameState
    fake_opp = GameState(mainboard=[], on_play=False)
    fake_opp.zones.library = [Card("High Noon", mana_cost="2", cmc=2, type_line="Enchantment"),
                              Card("Voice of Victory", mana_cost="1W", cmc=2, type_line="Creature"),
                              Card("Aven Interrupter", mana_cost="1WW", cmc=3, type_line="Creature")]
    print(f"  fake opp lib has {len(fake_opp.zones.library)} HN-related cards")
    print(f"  _vs_high_noon = {apl_a._vs_high_noon(fake_opp)}")
    print(f"  _vs_green     = {apl_a._vs_green(fake_opp)}")
    print(f"  _vs_lessons   = {apl_a._vs_lessons(fake_opp)}")

    print("\n=== one full game with logs ===")
    # Run one game and dump the log on game end
    # We need to capture the gs._log_lines from each turn; the game_state's log
    # is per-view rebuild. Let's use stderr by enabling SIM_DEBUG.
    os.environ['SIM_DEBUG'] = '1'
    r = run_match(apl_a, deck_a, apl_b, deck_b, seed=42, on_play=True)
    print(f"\n  result: won={r.won}  kill_turn={r.kill_turn}  turn_count={r.turn_count}")


if __name__ == "__main__":
    main()
