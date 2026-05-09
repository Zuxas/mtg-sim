"""A/B test: does the SB guide actually improve Bo3 WR?

Compares:
  Arm A: Bo3 with my SB plan applied G2/G3 for Hybrid
  Arm B: Bo3 with NO SB plan (Hybrid uses G1 deck all 3 games)
  Delta = the SB guide's actual contribution

Uses engine.match_runner.run_match (production runner) for G1/G2/G3 to
keep WRs comparable to the 74.6% FW WR baseline. Opp uses no SB in
either arm (controls for opp adjustment confound).
"""
import sys, os, time, random
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from copy import deepcopy
from apl import get_match_apl
from data.deck import load_deck_from_file
from engine.match_runner import run_match
from engine.sideboard import parse_sb_string, _fuzzy_match


def apply_sb_local(mainboard, sideboard_cards, sb_in_strs, sb_out_strs):
    """Apply SB plan using actual Card objects from the sideboard list.

    Avoids engine.sideboard._make_sb_card failures (Scryfall fetch fails
    for several common Standard cards). Mutates a deep-copied mainboard.
    """
    deck = [deepcopy(c) for c in mainboard]
    sb_pool = [deepcopy(c) for c in sideboard_cards]  # mutable pool
    deck_names = [c.name for c in deck]
    sb_names = [c.name for c in sb_pool]

    # Parse all in/out strings
    cards_in = []
    cards_out = []
    for raw in sb_in_strs:
        cards_in.extend(parse_sb_string(raw))
    for raw in sb_out_strs:
        cards_out.extend(parse_sb_string(raw))

    # Remove OUT cards
    for qty, name in cards_out:
        matched = _fuzzy_match(name, deck_names)
        if not matched:
            continue
        to_remove = qty
        new_deck = []
        for c in deck:
            if c.name == matched and to_remove > 0:
                to_remove -= 1
            else:
                new_deck.append(c)
        deck = new_deck
        deck_names = [c.name for c in deck]

    # Add IN cards (pull from sb_pool by name)
    for qty, name in cards_in:
        matched = _fuzzy_match(name, sb_names)
        if not matched:
            continue
        to_add = qty
        i = 0
        while i < len(sb_pool) and to_add > 0:
            if sb_pool[i].name == matched:
                deck.append(sb_pool.pop(i))
                to_add -= 1
            else:
                i += 1
        sb_names = [c.name for c in sb_pool]

    return deck


# SB plans from harness/knowledge/mtg/hybrid-jermey-sb-guide-rc-dc.md
# Format: (name, opp_apl_key, opp_deck, sb_in_strs, sb_out_strs)
PLANS = {
    "Izzet Prowess": (
        "izzetprowessstandard", "decks/izzet_prowess_standard.txt",
        ["2 Day of Black Sun", "1 Spider-Sense", "1 Negate"],
        ["2 Tinybones Joins Up", "1 Long Goodbye", "1 Bitter Triumph"],
    ),
    "Selesnya Landfall": (
        "selesnyalandfall", "decks/selesnya_landfall_standard.txt",
        ["2 Disdainful Stroke", "1 Tishana's Tidebinder", "1 Annul"],
        ["2 Tinybones Joins Up", "1 Spell Snare", "1 Long Goodbye"],
    ),
    "Izzet Lessons": (
        "izzetlesson", "decks/izzet_lesson_standard.txt",
        ["2 Duress", "1 Soul-Guide Lantern", "1 Spider-Sense", "1 Annul"],
        ["2 Tinybones Joins Up", "1 Floodpits Drowner", "1 Long Goodbye", "1 Bitter Triumph"],
    ),
    "Jeskai Control": (
        "jeskaicontrol", "decks/jeskai_control_standard.txt",
        ["2 Duress", "2 Disdainful Stroke", "1 Negate", "1 Spider-Sense", "1 The Unagi of Kyoshi Island"],
        ["2 Tinybones Joins Up", "2 Cecil, Dark Knight", "1 Floodpits Drowner",
         "1 Long Goodbye", "1 Bitter Triumph"],
    ),
    "HN (UW Flash)": (
        "azoriushighnoon", "decks/azorius_high_noon_standard.txt",
        ["2 Annul", "1 Negate", "1 Spider-Sense"],
        ["2 Tinybones Joins Up", "1 Long Goodbye", "1 Cecil, Dark Knight"],
    ),
    "Gruul Aggro": (
        "gruulaggro", "decks/gruul_aggro_standard.txt",
        ["2 Day of Black Sun", "1 Tishana's Tidebinder", "1 Strategic Betrayal"],
        ["2 Tinybones Joins Up", "1 Long Goodbye", "1 Floodpits Drowner"],
    ),
}

DECK = "decks/dimir_bounce_jermey_hybrid_standard.txt"
APL_KEY = "dimirmidrangejermey"
N_BO3 = 200  # 200 Bo3 = 400-600 actual games per matchup


def run_bo3_match(apl_a, deck_a_g1, deck_a_post, apl_b, deck_b, seed, a_on_play_g1):
    """Run a Bo3 match. Returns (a_wins, b_wins) tuple."""
    rng = random.Random(seed)
    a_wins = b_wins = 0

    # G1: pre-board both sides
    g1 = run_match(apl_a, deck_a_g1, apl_b, deck_b,
                   on_play=a_on_play_g1, seed=rng.randint(0, 999_999))
    if g1.won:
        a_wins += 1
    else:
        b_wins += 1
    if a_wins == 2 or b_wins == 2:
        return a_wins, b_wins

    # G2: post-board for A, loser of G1 on play
    a_on_play_g2 = (a_wins == 0)
    g2 = run_match(apl_a, deck_a_post, apl_b, deck_b,
                   on_play=a_on_play_g2, seed=rng.randint(0, 999_999))
    if g2.won:
        a_wins += 1
    else:
        b_wins += 1
    if a_wins == 2 or b_wins == 2:
        return a_wins, b_wins

    # G3: same post-board, loser of G2 on play
    a_on_play_g3 = (a_wins == b_wins) or (b_wins > a_wins)
    g3 = run_match(apl_a, deck_a_post, apl_b, deck_b,
                   on_play=a_on_play_g3, seed=rng.randint(0, 999_999))
    if g3.won:
        a_wins += 1
    else:
        b_wins += 1

    return a_wins, b_wins


def main():
    apl_a = get_match_apl(APL_KEY)
    deck_a_main, deck_a_sb_list = load_deck_from_file(DECK)

    print(f"\n=== Hybrid Bo3 SB-guide validation, N={N_BO3} per matchup ===")
    print(f"Deck: {DECK}\n")
    print(f"{'Matchup':<22}  {'No SB':>8}  {'With SB':>8}  {'Delta':>7}  {'G1-only':>8}")
    print("-" * 70)

    for name, (opp_key, opp_path, sb_in, sb_out) in PLANS.items():
        try:
            apl_b = get_match_apl(opp_key)
        except Exception as e:
            print(f"{name:<22}  SKIP ({e})")
            continue
        deck_b, _ = load_deck_from_file(opp_path)

        # Build post-board deck (use local apply that bypasses Scryfall fetch)
        try:
            deck_a_post = apply_sb_local(
                deck_a_main, deck_a_sb_list, sb_in, sb_out
            )
        except Exception as e:
            print(f"{name:<22}  SB-APPLY FAIL: {e}")
            continue

        # Sanity check
        post_size = len(deck_a_post)
        if post_size != 60:
            print(f"  WARN: {name} post-board has {post_size} cards (expected 60)")

        # Arm A: Bo3 with SB
        wins_with = 0
        for s in range(N_BO3):
            a, b = run_bo3_match(apl_a, deck_a_main, deck_a_post, apl_b, deck_b,
                                 seed=s, a_on_play_g1=(s % 2 == 0))
            if a > b:
                wins_with += 1

        # Arm B: Bo3 with NO SB (use main in G2/G3)
        wins_without = 0
        for s in range(N_BO3):
            a, b = run_bo3_match(apl_a, deck_a_main, deck_a_main, apl_b, deck_b,
                                 seed=s, a_on_play_g1=(s % 2 == 0))
            if a > b:
                wins_without += 1

        # G1-only baseline (single game, both on-play balanced)
        g1_wins = 0
        for s in range(N_BO3):
            r = run_match(apl_a, deck_a_main, apl_b, deck_b,
                          seed=s + 100_000, on_play=(s % 2 == 0))
            if r.won:
                g1_wins += 1

        wr_no_sb = wins_without / N_BO3 * 100
        wr_with  = wins_with / N_BO3 * 100
        wr_g1    = g1_wins / N_BO3 * 100
        delta    = wr_with - wr_no_sb

        sign = "+" if delta >= 0 else ""
        print(f"{name:<22}  {wr_no_sb:>7.1f}%  {wr_with:>7.1f}%  {sign}{delta:>5.1f}pp  {wr_g1:>7.1f}%")


if __name__ == "__main__":
    main()
