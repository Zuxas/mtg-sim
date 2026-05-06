"""
scripts/rc_meta_shift.py -- RC Swiss with adjusted meta: more Landfall, Lessons, Ouroboroid.

Uses the real Bo3 matrix from the PT SOS gauntlet run.
Only the field composition changes -- matchup WRs are fixed by deck identity.

Usage:
    python scripts/rc_meta_shift.py [--events N]
"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.tournament import simulate_rc

# ── Bo3 match WR matrix from PT SOS gauntlet run (60 matches/pair, real engine)
# Deck order matches DECK_NAMES below
DECK_NAMES = [
    "Izzet Prowess",        # 0
    "Mono Green Landfall",  # 1
    "Izzet Spellementals",  # 2
    "Izzet Lessons",        # 3
    "Azorius Momo",         # 4
    "Jeskai Control",       # 5
    "Selesnya Landfall",    # 6
    "Izzet Maestro",        # 7
    "Azorius Control",      # 8
    "Golgari Midrange",     # 9
    "Dimir Excruciator",    # 10
    "Sultai Control",       # 11
    "Four-Color Control",   # 12
    "Selesnya Rhythm",      # 13
    "Selesnya Ouroboroid",  # 14
    "Mardu Discard",        # 15
    "Boros Dragons",        # 16
    "Bant Rhythm",          # 17
    "Rakdos Discard",       # 18
    "Simic Rhythm",         # 19
    "Bant Airbending",      # 20
    "Golgari Kona",         # 21
    "Golgari Control",      # 22
    "Boros Discard",        # 23
    "Four-Color Elemental", # 24
    "Temur Lute",           # 25
    "Simic Omniscience",    # 26
    "Esper Pixie",          # 27
    "Gruul Aggro",          # 28
]

# Row = deck wins vs col deck (%)
RAW = [
    #  0      1      2      3      4      5      6      7      8      9     10     11     12     13     14     15     16     17     18     19     20     21     22     23     24     25     26     27     28
    [  0.0, 36.7,  80.0,  15.0,  58.3,  95.0,  21.7,  41.7,  16.7,  71.7,  66.7,  60.0, 100.0,  16.7,  21.7,  43.3,  38.3,  26.7,  68.3,   8.3,  28.3,  90.0,  88.3,  41.7, 100.0,  93.3,  81.7,  31.7,  33.3],  # Izzet Prowess
    [ 63.3,  0.0,  95.0,  43.3,  81.7,  85.0,  23.3,  53.3,  41.7,  68.3,  61.7,  41.7, 100.0,  35.0,  28.3,  61.7,  70.0,  41.7,  65.0,  28.3,  30.0,  95.0,  91.7,  48.3, 100.0,  86.7,  88.3,  23.3,  28.3],  # Mono Green Landfall
    [ 10.0, 15.0,   0.0,   3.3,  16.7,  81.7,   5.0,   6.7,  20.0,  23.3,  28.3,  28.3, 100.0,   5.0,   6.7,  13.3,  23.3,  11.7,  25.0,   3.3,  16.7,  55.0,  66.7,  13.3, 100.0,  63.3,  41.7,   6.7,   8.3],  # Izzet Spellementals
    [ 78.3, 53.3,  91.7,   0.0,  81.7, 100.0,  48.3,  68.3,  75.0,  76.7,  85.0,  93.3, 100.0,  45.0,  41.7,  98.3,  76.7,  48.3,  98.3,  18.3,  68.3,  96.7,  96.7,  83.3, 100.0,  98.3,  80.0,  63.3,  61.7],  # Izzet Lessons
    [ 48.3, 13.3,  80.0,  20.0,   0.0,  71.7,   5.0,  41.7,  20.0,  53.3,  25.0,  30.0, 100.0,  10.0,  16.7,  53.3,  20.0,  11.7,  58.3,   3.3,  10.0,  80.0,  80.0,  53.3, 100.0,  86.7,  51.7,  10.0,  16.7],  # Azorius Momo
    [ 11.7, 11.7,  21.7,   3.3,  23.3,   0.0,   5.0,  18.3,   8.3,  31.7,   5.0,  11.7,  86.7,   3.3,  10.0,  26.7,  15.0,   0.0,  28.3,   3.3,  15.0,  28.3,  51.7,  21.7,  96.7,  45.0,  16.7,  13.3,   1.7],  # Jeskai Control
    [ 81.7, 88.3,  98.3,  50.0,  95.0, 100.0,   0.0,  75.0,  75.0,  88.3,  86.7,  83.3, 100.0,  63.3,  60.0,  68.3,  80.0,  60.0,  80.0,  51.7,  65.0, 100.0,  98.3,  83.3, 100.0,  98.3,  98.3,  53.3,  55.0],  # Selesnya Landfall
    [ 46.7, 55.0,  81.7,  35.0,  58.3,  78.3,  16.7,   0.0,  40.0,  58.3,  50.0,  36.7, 100.0,  23.3,  16.7,  50.0,  40.0,  38.3,  63.3,  43.3,  30.0,  88.3,  73.3,  68.3, 100.0,  80.0,  83.3,  45.0,  53.3],  # Izzet Maestro
    [ 80.0, 73.3,  80.0,  21.7,  80.0,  86.7,  25.0,  71.7,   0.0,  86.7,  71.7,  75.0, 100.0,  40.0,  33.3,  78.3,  71.7,  46.7,  81.7,  26.7,  58.3,  96.7,  90.0,  75.0, 100.0,  93.3,  80.0,  55.0,  25.0],  # Azorius Control
    [ 35.0, 33.3,  71.7,  21.7,  43.3,  70.0,  13.3,  53.3,  20.0,   0.0,  35.0,  26.7, 100.0,  18.3,  18.3,  31.7,  18.3,  11.7,  30.0,   6.7,  11.7,  66.7,  61.7,  40.0, 100.0,  68.3,  45.0,  28.3,   5.0],  # Golgari Midrange
    [ 31.7, 55.0,  73.3,  10.0,  78.3,  85.0,  13.3,  56.7,  23.3,  80.0,   0.0,  55.0,  98.3,  13.3,  28.3,  43.3,  58.3,  16.7,  63.3,   3.3,  41.7,  68.3,  86.7,  41.7, 100.0,  95.0,  50.0,  36.7,   6.7],  # Dimir Excruciator
    [ 40.0, 60.0,  61.7,   6.7,  76.7,  83.3,  13.3,  60.0,  20.0,  73.3,  41.7,   0.0, 100.0,  26.7,  46.7,  60.0,  66.7,  23.3,  63.3,  13.3,  45.0,  66.7,  81.7,  48.3, 100.0,  95.0,  46.7,  30.0,   5.0],  # Sultai Control
    [  0.0,  0.0,   0.0,   0.0,   0.0,   3.3,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   5.0,   0.0,  76.7,   1.7,   0.0,   0.0,   0.0],  # Four-Color Control
    [ 66.7, 60.0,  93.3,  56.7,  78.3,  88.3,  46.7,  75.0,  53.3,  86.7,  71.7,  63.3, 100.0,   0.0,  35.0,  73.3,  85.0,  60.0,  80.0,  26.7,  50.0,  96.7,  93.3,  78.3, 100.0,  93.3,  95.0,  51.7,  51.7],  # Selesnya Rhythm
    [ 73.3, 81.7,  96.7,  60.0,  93.3,  96.7,  41.7,  80.0,  58.3,  86.7,  83.3,  50.0, 100.0,  56.7,   0.0,  76.7,  86.7,  58.3,  88.3,  48.3,  75.0,  98.3,  91.7,  81.7, 100.0,  98.3,  93.3,  60.0,  41.7],  # Selesnya Ouroboroid
    [ 45.0, 45.0,  93.3,   5.0,  55.0,  70.0,  21.7,  48.3,  25.0,  63.3,  63.3,  41.7, 100.0,  35.0,   8.3,   0.0,  48.3,  28.3,  55.0,  23.3,  26.7,  88.3,  88.3,  55.0, 100.0,  76.7,  86.7,  11.7,  31.7],  # Mardu Discard
    [ 61.7, 31.7,  83.3,  15.0,  83.3,  83.3,   8.3,  38.3,  35.0,  88.3,  53.3,  48.3, 100.0,  25.0,  25.0,  43.3,   0.0,  16.7,  58.3,   5.0,  28.3,  98.3,  95.0,  51.7, 100.0,  88.3,  63.3,  48.3,  16.7],  # Boros Dragons
    [ 68.3, 80.0,  93.3,  50.0,  80.0,  98.3,  36.7,  56.7,  53.3,  75.0,  78.3,  80.0, 100.0,  41.7,  61.7,  85.0,  80.0,   0.0,  76.7,  28.3,  51.7,  96.7,  98.3,  65.0, 100.0,  90.0,  88.3,  51.7,  53.3],  # Bant Rhythm
    [ 41.7, 41.7,  85.0,   0.0,  43.3,  60.0,  20.0,  41.7,  21.7,  66.7,  55.0,  36.7, 100.0,  26.7,  20.0,  43.3,  36.7,  30.0,   0.0,  15.0,  11.7,  90.0,  85.0,  48.3, 100.0,  68.3,  65.0,  21.7,  28.3],  # Rakdos Discard
    [ 83.3, 66.7,  95.0,  66.7,  95.0, 100.0,  58.3,  66.7,  80.0,  86.7,  90.0,  90.0, 100.0,  51.7,  60.0,  68.3,  98.3,  71.7,  90.0,   0.0,  88.3, 100.0, 100.0,  85.0, 100.0,  98.3,  96.7,  55.0,  65.0],  # Simic Rhythm
    [ 88.3, 55.0,  83.3,  35.0,  88.3,  90.0,  28.3,  70.0,  43.3,  83.3,  50.0,  70.0, 100.0,  53.3,  40.0,  75.0,  60.0,  25.0,  80.0,  25.0,   0.0,  93.3,  91.7,  71.7, 100.0,  90.0,  81.7,  58.3,  20.0],  # Bant Airbending
    [  8.3, 11.7,  30.0,   3.3,  20.0,  85.0,   0.0,  15.0,   8.3,  28.3,  41.7,  36.7,  98.3,   5.0,   5.0,   6.7,   1.7,   5.0,  23.3,   0.0,   5.0,   0.0,  68.3,  11.7, 100.0,  45.0,  13.3,   0.0,   3.3],  # Golgari Kona
    [  6.7, 10.0,  23.3,   3.3,  25.0,  50.0,   0.0,  20.0,   6.7,  33.3,  11.7,   5.0,  98.3,   5.0,  10.0,  13.3,   6.7,   6.7,  15.0,   0.0,   6.7,  31.7,   0.0,  11.7, 100.0,  63.3,  15.0,   8.3,   0.0],  # Golgari Control
    [ 56.7, 33.3,  86.7,  21.7,  40.0,  81.7,  21.7,  41.7,  33.3,  58.3,  63.3,  58.3, 100.0,  26.7,  25.0,  46.7,  48.3,  26.7,  56.7,  16.7,  26.7,  91.7, 100.0,   0.0, 100.0,  76.7,  83.3,  30.0,  26.7],  # Boros Discard
    [  0.0,  0.0,   0.0,   0.0,   0.0,   1.7,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,  18.3,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   1.7,   0.0,   0.0,   0.0],  # Four-Color Elemental
    [ 13.3,  3.3,  45.0,   1.7,  15.0,  55.0,   1.7,  18.3,   8.3,  21.7,   6.7,  11.7,  98.3,   8.3,   1.7,  18.3,  13.3,   5.0,  16.7,   0.0,   3.3,  46.7,  25.0,  33.3,  98.3,   0.0,  20.0,   5.0,   1.7],  # Temur Lute
    [ 15.0, 15.0,  48.3,  10.0,  46.7,  98.3,   5.0,  26.7,  25.0,  70.0,  60.0,  51.7, 100.0,  10.0,   8.3,  25.0,  35.0,  16.7,  40.0,   1.7,  16.7,  83.3,  85.0,  28.3, 100.0,  85.0,   0.0,  15.0,   6.7],  # Simic Omniscience
    [ 61.7, 71.7,  91.7,  31.7,  90.0,  95.0,  38.3,  58.3,  41.7,  90.0,  61.7,  66.7, 100.0,  55.0,  40.0,  66.7,  61.7,  45.0,  73.3,  45.0,  43.3,  91.7,  95.0,  61.7, 100.0,  93.3,  85.0,   0.0,  40.0],  # Esper Pixie
    [ 65.0, 55.0,  96.7,  41.7,  95.0, 100.0,  43.3,  65.0,  58.3,  96.7,  93.3,  93.3, 100.0,  56.7,  51.7,  60.0,  85.0,  61.7,  88.3,  26.7,  75.0,  98.3, 100.0,  71.7, 100.0, 100.0,  90.0,  58.3,   0.0],  # Gruul Aggro
]

# ── Meta scenarios ──────────────────────────────────────────────────────────
# Original PT SOS field
SOS_ORIGINAL = {
    "Izzet Prowess":        25,
    "Mono Green Landfall":  25,
    "Izzet Spellementals":  25,
    "Izzet Lessons":        24,
    "Azorius Momo":         14,
    "Jeskai Control":       12,
    "Selesnya Landfall":    11,
    "Izzet Maestro":        10,
    "Azorius Control":      10,
    "Golgari Midrange":     10,
    "Dimir Excruciator":    10,
    "Sultai Control":       10,
    "Four-Color Control":   10,
    "Selesnya Rhythm":      10,
    "Selesnya Ouroboroid":  10,
    "Mardu Discard":        10,
    "Boros Dragons":        10,
    "Bant Rhythm":          10,
    "Rakdos Discard":       10,
    "Simic Rhythm":         10,
    "Bant Airbending":      10,
    "Golgari Kona":         10,
    "Golgari Control":      10,
    "Boros Discard":        10,
    "Four-Color Elemental": 10,
    "Temur Lute":           10,
    "Simic Omniscience":    10,
    "Esper Pixie":          10,
    "Gruul Aggro":          10,
}

# Adjusted: more Landfall, Lessons, Ouroboroid — as meta adapts to known results
# Izzet Prowess still large but losing share; green/value decks spiking
META_SHIFT = {
    "Izzet Prowess":        18,   # still large but shedding players (-7)
    "Mono Green Landfall":  25,   # cap stays
    "Izzet Spellementals":  14,   # losing players to Lessons (-11)
    "Izzet Lessons":        25,   # spiking, people copying the winner (+1 to cap)
    "Azorius Momo":         12,   # slight drop
    "Jeskai Control":       10,   # floor
    "Selesnya Landfall":    25,   # HUGE spike — was 11, now cap (+14)
    "Izzet Maestro":        10,
    "Azorius Control":      10,
    "Golgari Midrange":     10,
    "Dimir Excruciator":    10,
    "Sultai Control":       10,
    "Four-Color Control":   10,
    "Selesnya Rhythm":      18,   # gaining as meta greens up (+8)
    "Selesnya Ouroboroid":  22,   # spiking hard — was 10, now 22 (+12)
    "Mardu Discard":        10,
    "Boros Dragons":        10,
    "Bant Rhythm":          15,   # gaining (+5)
    "Rakdos Discard":       10,
    "Simic Rhythm":         18,   # spiking after strong results (+8)
    "Bant Airbending":      12,   # slight uptick
    "Golgari Kona":         10,
    "Golgari Control":      10,
    "Boros Discard":        10,
    "Four-Color Elemental": 10,
    "Temur Lute":           10,
    "Simic Omniscience":    10,
    "Esper Pixie":          12,   # slight uptick
    "Gruul Aggro":          12,   # gaining (+2)
}


def run_scenario(name, player_counts, matrix, n_events, n_rounds):
    total = sum(player_counts.values())
    field_shares = {d: c / total for d, c in player_counts.items()}

    results = simulate_rc(
        field_shares=field_shares,
        matrix=matrix,
        n_events=n_events,
        n_players=total,
        n_rounds=n_rounds,
        seed=42,
    )

    expected_top8 = 8 / total * 100

    print(f"\n{'='*95}")
    print(f"  {name}")
    print(f"  {n_events:,} Swiss events  |  {n_rounds} rounds  |  {total} players  |  Random top8: {expected_top8:.1f}%")
    print(f"{'='*95}")
    print(f"  {'Deck':<28} {'Players':>7}  {'Field%':>6}  {'Avg':>7}  "
          f"{'Top8%':>6}  {'X-1%':>6}  {'X-2%':>6}  {'EV':>7}  Notes")
    print(f"  {'-'*28} {'-'*7}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*7}")

    for r in results:
        pc   = player_counts.get(r.deck, 0)
        pct  = pc / total * 100
        ev   = r.top8_pct - expected_top8
        sign = "+" if ev >= 0 else ""
        rec  = f"{r.avg_wins:.1f}-{r.avg_losses:.1f}"

        tag = ""
        if ev > 10 and pct < 5:
            tag = "<< UNDERPLAYED HERO"
        elif ev > 10:
            tag = "<< DOMINANT"
        elif ev > 5:
            tag = "<< STRONG"
        elif ev < -1.0 and pc >= 18:
            tag = "TRAP"

        print(f"  {r.deck:<28} {pc:>7}  {pct:>5.1f}%  {rec:>7}  "
              f"{r.top8_pct:>5.1f}%  {r.x1_pct:>5.1f}%  {r.x2_pct:>5.1f}%  "
              f"{sign}{ev:>5.1f}%  {tag}")

    print(f"{'='*95}")
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=5000)
    ap.add_argument("--rounds", type=int, default=8)
    args = ap.parse_args()

    # Build matrix dict
    matrix = {}
    for i, na in enumerate(DECK_NAMES):
        for j, nb in enumerate(DECK_NAMES):
            if i != j:
                matrix[(na, nb)] = RAW[i][j]

    print("RC Gauntlet -- Meta Shift: More Landfall / Lessons / Ouroboroid")
    print("Bo3 matrix source: PT SOS 2026 real match engine (60 matches/pair)\n")

    print("Field changes vs PT SOS baseline:")
    all_decks = sorted(set(list(SOS_ORIGINAL.keys()) + list(META_SHIFT.keys())))
    for d in all_decks:
        orig = SOS_ORIGINAL.get(d, 0)
        new  = META_SHIFT.get(d, 0)
        diff = new - orig
        if diff != 0:
            arrow = f"+{diff}" if diff > 0 else str(diff)
            print(f"  {d:<28} {orig:>3} -> {new:>3}  ({arrow})")

    run_scenario(
        "SCENARIO A: PT SOS Original Field",
        SOS_ORIGINAL, matrix, args.events, args.rounds,
    )

    run_scenario(
        "SCENARIO B: Meta Shift -- More Selesnya Landfall / Lessons / Ouroboroid / Simic Rhythm",
        META_SHIFT, matrix, args.events, args.rounds,
    )


if __name__ == "__main__":
    main()
