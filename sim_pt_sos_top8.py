"""
sim_pt_sos_top8.py -- PT Secrets of Strixhaven 2026 Top 8 bracket simulation

Rules:
  - Single elimination, seeded bracket (1v8, 2v7, 3v6, 4v5)
  - Best-of-5, first to 3 wins
  - Games 1-2: pre-sideboard (main deck only)
  - Games 3+: post-sideboard
  - Higher seed takes play in G1
  - Loser of each game takes play next game (standard MTG rule)
  - On-draw penalty: effective kill turn shifted +1 (opponent acts first)
"""

import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))

from engine.runner import run_simulation
from sim_bridge import race_win_pct, avg_kill_turn
from apl import get_apl
from data.deck import load_deck_from_file

DECK_DIR = "decks/pt_sos_top8"
N_SIM    = 500    # games per kill-dist measurement
N_RACE   = 20000  # trials per matchup win%

TOP8 = [
    (1, "s1_steuer.txt",     "Nathan Steuer",       "Selesnya Landfall",   "selesnyalandfall"),
    (2, "s2_larsen.txt",     "Christoffer Larsen",  "Selesnya Landfall",   "selesnyalandfall"),
    (3, "s3_zhang.txt",      "Rui Zhang",           "Izzet Lessons",       "izzetlessons"),
    (4, "s4_nass.txt",       "Matt Nass",           "Selesnya Ouroboroid", "selesnyaouroboroid"),
    (5, "s5_kominowski.txt", "Maxx Kominowski",     "Izzet Spellementals", "izzetspellementals"),
    (6, "s6_schutz.txt",     "Stefan Schutz",       "Mono Green Landfall", "monogreenlandfall"),
    (7, "s7_stefansson.txt", "Matthew Stefansson",  "Mono Green Landfall", "monogreenlandfall"),
    (8, "s8_faust.txt",      "Zevin Faust",         "Azorius Tempo",       "azoriustempo"),
]


def load_player(seed, filename, name, archetype, apl_key):
    apl = get_apl(apl_key)
    if apl is None:
        raise RuntimeError(f"No APL for {archetype} ({apl_key})")
    path = os.path.join(DECK_DIR, filename)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    from data.deck import load_deck_from_text
    main, side = load_deck_from_text(text)
    return {
        "seed": seed, "name": name, "archetype": archetype,
        "apl": apl, "main": main, "side": side,
    }


def measure_dist(player, on_play=True):
    """Goldfish kill distribution from this player's main deck."""
    result = run_simulation(player["apl"], player["main"],
                            n=N_SIM, on_play=on_play, seed=42)
    return result.kill_turn_distribution()


def shift_dist(dist, turns=1):
    """Shift kill distribution by +turns (on-draw penalty)."""
    return {t + turns: pct for t, pct in dist.items()}


def sim_game(dist_a, dist_b):
    """Return True if player A wins the race. A acts first (on play)."""
    return race_win_pct(dist_a, dist_b, n=N_RACE) / 100.0


def build_post_board(player):
    """
    Merge main + sideboard into post-board deck.
    For now: naive -- just append SB cards. Real APL-driven SB plans
    are not modelled here (goldfish race only).
    """
    return player["main"] + player["side"]


def simulate_bo5(p_hi, p_lo, label=""):
    """
    Best-of-5 between higher seed (p_hi) and lower seed (p_lo).
    Returns (winner, score_hi, score_lo, log).
    """
    log = []

    # Measure kill dists once (main deck, both on-play and on-draw)
    dist_hi_play = measure_dist(p_hi, on_play=True)
    dist_hi_draw = shift_dist(dist_hi_play, turns=1)
    dist_lo_play = measure_dist(p_lo, on_play=True)
    dist_lo_draw = shift_dist(dist_lo_play, turns=1)

    avg_hi = avg_kill_turn(dist_hi_play)
    avg_lo = avg_kill_turn(dist_lo_play)
    log.append(f"  Kill avg: {p_hi['name']} T{avg_hi:.2f}  |  {p_lo['name']} T{avg_lo:.2f}")

    # Post-board kill dists (main + SB merged)
    p_hi_pb = {**p_hi, "main": build_post_board(p_hi)}
    p_lo_pb = {**p_lo, "main": build_post_board(p_lo)}
    dist_hi_play_pb = measure_dist(p_hi_pb, on_play=True)
    dist_hi_draw_pb = shift_dist(dist_hi_play_pb, turns=1)
    dist_lo_play_pb = measure_dist(p_lo_pb, on_play=True)
    dist_lo_draw_pb = shift_dist(dist_lo_play_pb, turns=1)

    wins_hi = 0
    wins_lo = 0
    # G1: higher seed is on play
    hi_on_play = True

    for game_num in range(1, 6):
        if wins_hi == 3 or wins_lo == 3:
            break

        pre_board = game_num <= 2

        if hi_on_play:
            d_a = dist_hi_play    if pre_board else dist_hi_play_pb
            d_b = dist_lo_draw    if pre_board else dist_lo_draw_pb
            a_wins_pct = race_win_pct(d_a, d_b, n=N_RACE)
            hi_wins = random.random() * 100 < a_wins_pct
        else:
            d_a = dist_lo_play    if pre_board else dist_lo_play_pb
            d_b = dist_hi_draw    if pre_board else dist_hi_draw_pb
            a_wins_pct = race_win_pct(d_a, d_b, n=N_RACE)
            hi_wins = not (random.random() * 100 < a_wins_pct)

        board_tag = "pre" if pre_board else "post"
        play_tag  = p_hi["name"].split()[-1] if hi_on_play else p_lo["name"].split()[-1]
        if hi_wins:
            wins_hi += 1
            log.append(f"  G{game_num} [{board_tag}] {play_tag} plays: "
                        f"{p_hi['name'].split()[-1]} wins  ({wins_hi}-{wins_lo})")
            hi_on_play = False   # loser (lo) takes play next game
        else:
            wins_lo += 1
            log.append(f"  G{game_num} [{board_tag}] {play_tag} plays: "
                        f"{p_lo['name'].split()[-1]} wins  ({wins_hi}-{wins_lo})")
            hi_on_play = True    # loser (hi) takes play next game

    winner = p_hi if wins_hi == 3 else p_lo
    loser  = p_lo if wins_hi == 3 else p_hi
    return winner, loser, wins_hi, wins_lo, log


def run_n_bo5(p_hi, p_lo, n=200, label=""):
    """Run N Bo5 matches and return win probability for higher seed."""
    random.seed(7)
    hi_wins = 0
    for _ in range(n):
        winner, _, _, _, _ = simulate_bo5(p_hi, p_lo)
        if winner["seed"] == p_hi["seed"]:
            hi_wins += 1
    return hi_wins / n


def main():
    print("=" * 62)
    print("PT Secrets of Strixhaven 2026 -- Top 8 Bracket Simulation")
    print("Best-of-5 | G1-2 pre-board | Higher seed plays G1")
    print("=" * 62)

    print("\nLoading players and measuring kill clocks...")
    players = {}
    for entry in TOP8:
        p = load_player(*entry)
        players[entry[0]] = p
        dist = measure_dist(p, on_play=True)
        print(f"  Seed {entry[0]}: {p['name']:<24} ({p['archetype']:<22}) T{avg_kill_turn(dist):.2f}")

    # Standard bracket seeding
    bracket = [
        (1, 8, "QF1"),
        (4, 5, "QF2"),
        (2, 7, "QF3"),
        (3, 6, "QF4"),
    ]
    # SF: winner of (1v8) vs winner of (4v5) ; winner of (2v7) vs winner of (3v6)
    N_MATCHES = 100

    print(f"\nSimulating bracket ({N_MATCHES} matches per pairing)...\n")

    sf_slots = {}  # "SF_A" and "SF_B"

    for s_hi, s_lo, label in bracket:
        p_hi = players[s_hi]
        p_lo = players[s_lo]
        win_pct = run_n_bo5(p_hi, p_lo, n=N_MATCHES)
        winner_name = p_hi["name"] if win_pct >= 0.5 else p_lo["name"]
        winner_p    = p_hi if win_pct >= 0.5 else p_lo
        loser_p     = p_lo if win_pct >= 0.5 else p_hi

        bar = "#" * int(win_pct * 20) + "-" * (20 - int(win_pct * 20))
        print(f"  {label}: Seed {s_hi} {p_hi['name']:<22} vs Seed {s_lo} {p_lo['name']:<22}")
        print(f"        {bar}  {p_hi['name'].split()[-1]} {win_pct*100:.0f}% | {p_lo['name'].split()[-1]} {(1-win_pct)*100:.0f}%")
        print(f"        --> {winner_name} advances\n")

        if label in ("QF1", "QF2"):
            sf_slots[label] = winner_p
        else:
            sf_slots[label] = winner_p

    # Semifinals
    sf_pairs = [
        (sf_slots["QF1"], sf_slots["QF2"], "SF1"),
        (sf_slots["QF3"], sf_slots["QF4"], "SF2"),
    ]
    finalists = []
    print("-" * 62)
    for p_a, p_b, label in sf_pairs:
        p_hi = p_a if p_a["seed"] < p_b["seed"] else p_b
        p_lo = p_b if p_a["seed"] < p_b["seed"] else p_a
        win_pct = run_n_bo5(p_hi, p_lo, n=N_MATCHES)
        winner_p = p_hi if win_pct >= 0.5 else p_lo

        print(f"  {label}: Seed {p_hi['seed']} {p_hi['name']:<22} vs Seed {p_lo['seed']} {p_lo['name']:<22}")
        bar = "#" * int(win_pct * 20) + "-" * (20 - int(win_pct * 20))
        print(f"        {bar}  {p_hi['name'].split()[-1]} {win_pct*100:.0f}% | {p_lo['name'].split()[-1]} {(1-win_pct)*100:.0f}%")
        print(f"        --> {winner_p['name']} advances\n")
        finalists.append(winner_p)

    # Final
    print("-" * 62)
    f1, f2 = finalists
    p_hi = f1 if f1["seed"] < f2["seed"] else f2
    p_lo = f2 if f1["seed"] < f2["seed"] else f1
    win_pct = run_n_bo5(p_hi, p_lo, n=N_MATCHES)
    champion = p_hi if win_pct >= 0.5 else p_lo
    runner   = p_lo if win_pct >= 0.5 else p_hi

    print(f"  FINAL: Seed {p_hi['seed']} {p_hi['name']:<22} vs Seed {p_lo['seed']} {p_lo['name']:<22}")
    bar = "█" * int(win_pct * 20) + "░" * (20 - int(win_pct * 20))
    print(f"         {bar}  {p_hi['name'].split()[-1]} {win_pct*100:.0f}% | {p_lo['name'].split()[-1]} {(1-win_pct)*100:.0f}%")
    print()
    print("=" * 62)
    print(f"  CHAMPION: {champion['name']} ({champion['archetype']})")
    print(f"  Runner-up: {runner['name']} ({runner['archetype']})")
    print("=" * 62)


if __name__ == "__main__":
    main()
