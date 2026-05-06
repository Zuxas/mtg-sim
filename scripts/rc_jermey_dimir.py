"""
scripts/rc_jermey_dimir.py -- Add Jermey's Dimir Midrange to the meta shift gauntlet.

Builds new Bo3 matchup data for the personal Dimir build vs all 29 SOS decks,
then re-runs the Swiss sim with it slotted into the adjusted meta field.
"""
import sys, os, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.tournament import simulate_rc

MY_DECK_NAME = "Jermey Dimir Midrange"
MY_DECK_FILE = "decks/dimir_midrange_jermey_standard.txt"
MY_APL_KEY   = "dimirmidrangejermey"   # JermeyDimirMatchAPL -- full strategy APL

# ── Existing 29-deck Bo3 matrix (from PT SOS gauntlet, 60 matches/pair) ────
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

RAW = [
    [  0.0, 36.7,  80.0,  15.0,  58.3,  95.0,  21.7,  41.7,  16.7,  71.7,  66.7,  60.0, 100.0,  16.7,  21.7,  43.3,  38.3,  26.7,  68.3,   8.3,  28.3,  90.0,  88.3,  41.7, 100.0,  93.3,  81.7,  31.7,  33.3],
    [ 63.3,  0.0,  95.0,  43.3,  81.7,  85.0,  23.3,  53.3,  41.7,  68.3,  61.7,  41.7, 100.0,  35.0,  28.3,  61.7,  70.0,  41.7,  65.0,  28.3,  30.0,  95.0,  91.7,  48.3, 100.0,  86.7,  88.3,  23.3,  28.3],
    [ 10.0, 15.0,   0.0,   3.3,  16.7,  81.7,   5.0,   6.7,  20.0,  23.3,  28.3,  28.3, 100.0,   5.0,   6.7,  13.3,  23.3,  11.7,  25.0,   3.3,  16.7,  55.0,  66.7,  13.3, 100.0,  63.3,  41.7,   6.7,   8.3],
    [ 78.3, 53.3,  91.7,   0.0,  81.7, 100.0,  48.3,  68.3,  75.0,  76.7,  85.0,  93.3, 100.0,  45.0,  41.7,  98.3,  76.7,  48.3,  98.3,  18.3,  68.3,  96.7,  96.7,  83.3, 100.0,  98.3,  80.0,  63.3,  61.7],
    [ 48.3, 13.3,  80.0,  20.0,   0.0,  71.7,   5.0,  41.7,  20.0,  53.3,  25.0,  30.0, 100.0,  10.0,  16.7,  53.3,  20.0,  11.7,  58.3,   3.3,  10.0,  80.0,  80.0,  53.3, 100.0,  86.7,  51.7,  10.0,  16.7],
    [ 11.7, 11.7,  21.7,   3.3,  23.3,   0.0,   5.0,  18.3,   8.3,  31.7,   5.0,  11.7,  86.7,   3.3,  10.0,  26.7,  15.0,   0.0,  28.3,   3.3,  15.0,  28.3,  51.7,  21.7,  96.7,  45.0,  16.7,  13.3,   1.7],
    [ 81.7, 88.3,  98.3,  50.0,  95.0, 100.0,   0.0,  75.0,  75.0,  88.3,  86.7,  83.3, 100.0,  63.3,  60.0,  68.3,  80.0,  60.0,  80.0,  51.7,  65.0, 100.0,  98.3,  83.3, 100.0,  98.3,  98.3,  53.3,  55.0],
    [ 46.7, 55.0,  81.7,  35.0,  58.3,  78.3,  16.7,   0.0,  40.0,  58.3,  50.0,  36.7, 100.0,  23.3,  16.7,  50.0,  40.0,  38.3,  63.3,  43.3,  30.0,  88.3,  73.3,  68.3, 100.0,  80.0,  83.3,  45.0,  53.3],
    [ 80.0, 73.3,  80.0,  21.7,  80.0,  86.7,  25.0,  71.7,   0.0,  86.7,  71.7,  75.0, 100.0,  40.0,  33.3,  78.3,  71.7,  46.7,  81.7,  26.7,  58.3,  96.7,  90.0,  75.0, 100.0,  93.3,  80.0,  55.0,  25.0],
    [ 35.0, 33.3,  71.7,  21.7,  43.3,  70.0,  13.3,  53.3,  20.0,   0.0,  35.0,  26.7, 100.0,  18.3,  18.3,  31.7,  18.3,  11.7,  30.0,   6.7,  11.7,  66.7,  61.7,  40.0, 100.0,  68.3,  45.0,  28.3,   5.0],
    [ 31.7, 55.0,  73.3,  10.0,  78.3,  85.0,  13.3,  56.7,  23.3,  80.0,   0.0,  55.0,  98.3,  13.3,  28.3,  43.3,  58.3,  16.7,  63.3,   3.3,  41.7,  68.3,  86.7,  41.7, 100.0,  95.0,  50.0,  36.7,   6.7],
    [ 40.0, 60.0,  61.7,   6.7,  76.7,  83.3,  13.3,  60.0,  20.0,  73.3,  41.7,   0.0, 100.0,  26.7,  46.7,  60.0,  66.7,  23.3,  63.3,  13.3,  45.0,  66.7,  81.7,  48.3, 100.0,  95.0,  46.7,  30.0,   5.0],
    [  0.0,  0.0,   0.0,   0.0,   0.0,   3.3,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   5.0,   0.0,  76.7,   1.7,   0.0,   0.0,   0.0],
    [ 66.7, 60.0,  93.3,  56.7,  78.3,  88.3,  46.7,  75.0,  53.3,  86.7,  71.7,  63.3, 100.0,   0.0,  35.0,  73.3,  85.0,  60.0,  80.0,  26.7,  50.0,  96.7,  93.3,  78.3, 100.0,  93.3,  95.0,  51.7,  51.7],
    [ 73.3, 81.7,  96.7,  60.0,  93.3,  96.7,  41.7,  80.0,  58.3,  86.7,  83.3,  50.0, 100.0,  56.7,   0.0,  76.7,  86.7,  58.3,  88.3,  48.3,  75.0,  98.3,  91.7,  81.7, 100.0,  98.3,  93.3,  60.0,  41.7],
    [ 45.0, 45.0,  93.3,   5.0,  55.0,  70.0,  21.7,  48.3,  25.0,  63.3,  63.3,  41.7, 100.0,  35.0,   8.3,   0.0,  48.3,  28.3,  55.0,  23.3,  26.7,  88.3,  88.3,  55.0, 100.0,  76.7,  86.7,  11.7,  31.7],
    [ 61.7, 31.7,  83.3,  15.0,  83.3,  83.3,   8.3,  38.3,  35.0,  88.3,  53.3,  48.3, 100.0,  25.0,  25.0,  43.3,   0.0,  16.7,  58.3,   5.0,  28.3,  98.3,  95.0,  51.7, 100.0,  88.3,  63.3,  48.3,  16.7],
    [ 68.3, 80.0,  93.3,  50.0,  80.0,  98.3,  36.7,  56.7,  53.3,  75.0,  78.3,  80.0, 100.0,  41.7,  61.7,  85.0,  80.0,   0.0,  76.7,  28.3,  51.7,  96.7,  98.3,  65.0, 100.0,  90.0,  88.3,  51.7,  53.3],
    [ 41.7, 41.7,  85.0,   0.0,  43.3,  60.0,  20.0,  41.7,  21.7,  66.7,  55.0,  36.7, 100.0,  26.7,  20.0,  43.3,  36.7,  30.0,   0.0,  15.0,  11.7,  90.0,  85.0,  48.3, 100.0,  68.3,  65.0,  21.7,  28.3],
    [ 83.3, 66.7,  95.0,  66.7,  95.0, 100.0,  58.3,  66.7,  80.0,  86.7,  90.0,  90.0, 100.0,  51.7,  60.0,  68.3,  98.3,  71.7,  90.0,   0.0,  88.3, 100.0, 100.0,  85.0, 100.0,  98.3,  96.7,  55.0,  65.0],
    [ 88.3, 55.0,  83.3,  35.0,  88.3,  90.0,  28.3,  70.0,  43.3,  83.3,  50.0,  70.0, 100.0,  53.3,  40.0,  75.0,  60.0,  25.0,  80.0,  25.0,   0.0,  93.3,  91.7,  71.7, 100.0,  90.0,  81.7,  58.3,  20.0],
    [  8.3, 11.7,  30.0,   3.3,  20.0,  85.0,   0.0,  15.0,   8.3,  28.3,  41.7,  36.7,  98.3,   5.0,   5.0,   6.7,   1.7,   5.0,  23.3,   0.0,   5.0,   0.0,  68.3,  11.7, 100.0,  45.0,  13.3,   0.0,   3.3],
    [  6.7, 10.0,  23.3,   3.3,  25.0,  50.0,   0.0,  20.0,   6.7,  33.3,  11.7,   5.0,  98.3,   5.0,  10.0,  13.3,   6.7,   6.7,  15.0,   0.0,   6.7,  31.7,   0.0,  11.7, 100.0,  63.3,  15.0,   8.3,   0.0],
    [ 56.7, 33.3,  86.7,  21.7,  40.0,  81.7,  21.7,  41.7,  33.3,  58.3,  63.3,  58.3, 100.0,  26.7,  25.0,  46.7,  48.3,  26.7,  56.7,  16.7,  26.7,  91.7, 100.0,   0.0, 100.0,  76.7,  83.3,  30.0,  26.7],
    [  0.0,  0.0,   0.0,   0.0,   0.0,   1.7,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,  18.3,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   0.0,   1.7,   0.0,   0.0,   0.0],
    [ 13.3,  3.3,  45.0,   1.7,  15.0,  55.0,   1.7,  18.3,   8.3,  21.7,   6.7,  11.7,  98.3,   8.3,   1.7,  18.3,  13.3,   5.0,  16.7,   0.0,   3.3,  46.7,  25.0,  33.3,  98.3,   0.0,  20.0,   5.0,   1.7],
    [ 15.0, 15.0,  48.3,  10.0,  46.7,  98.3,   5.0,  26.7,  25.0,  70.0,  60.0,  51.7, 100.0,  10.0,   8.3,  25.0,  35.0,  16.7,  40.0,   1.7,  16.7,  83.3,  85.0,  28.3, 100.0,  85.0,   0.0,  15.0,   6.7],
    [ 61.7, 71.7,  91.7,  31.7,  90.0,  95.0,  38.3,  58.3,  41.7,  90.0,  61.7,  66.7, 100.0,  55.0,  40.0,  66.7,  61.7,  45.0,  73.3,  45.0,  43.3,  91.7,  95.0,  61.7, 100.0,  93.3,  85.0,   0.0,  40.0],
    [ 65.0, 55.0,  96.7,  41.7,  95.0, 100.0,  43.3,  65.0,  58.3,  96.7,  93.3,  93.3, 100.0,  56.7,  51.7,  60.0,  85.0,  61.7,  88.3,  26.7,  75.0,  98.3, 100.0,  71.7, 100.0, 100.0,  90.0,  58.3,   0.0],
]

# 25 players on every known Standard archetype (equal representation)
FLAT_25_COUNTS = {name: 25 for name in DECK_NAMES}
FLAT_25_COUNTS[MY_DECK_NAME] = 25


def _get_deck_file(key):
    from apl import APL_REGISTRY
    entry = APL_REGISTRY.get(key)
    if entry and isinstance(entry, tuple) and len(entry) >= 3:
        path = entry[2]
        if path and path.endswith('.txt') and os.path.exists(path):
            return path
    return None


def _run_bo3_job(args):
    name_a, deck_file_a, apl_key_a, name_b, deck_file_b, apl_key_b, n_matches, seed_base = args

    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    def load(deck_file, apl_key):
        try:
            deck, _ = load_deck_from_file(deck_file)
            apl = get_match_apl(apl_key)
            return deck, apl
        except Exception:
            return None, None

    deck_a, apl_a = load(deck_file_a, apl_key_a)
    deck_b, apl_b = load(deck_file_b, apl_key_b)
    if deck_a is None or deck_b is None:
        return name_a, name_b, 0, 0

    match_wins = 0
    total = 0
    for i in range(n_matches):
        s = seed_base + i * 13
        wa, wb = 0, 0
        for g, on_play in enumerate([True, False]):
            try:
                r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s + g, on_play=on_play)
                if r.won: wa += 1
                else:     wb += 1
            except Exception:
                wb += 1
        if wa == 1 and wb == 1:
            op = (i % 2 == 0)
            try:
                r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s + 2, on_play=op)
                if r.won: wa += 1
                else:     wb += 1
            except Exception:
                wb += 1
        if wa >= 2:
            match_wins += 1
        total += 1

    return name_a, name_b, match_wins, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--matches", type=int, default=60)
    ap.add_argument("--events",  type=int, default=5000)
    ap.add_argument("--cores",   type=int, default=12)
    ap.add_argument("--rounds",  type=int, default=8)
    args = ap.parse_args()

    # ── Load APL key -> deck file map for the 29 existing decks ─────────
    from scripts.rc_gauntlet_sos import SOS_FIELD
    opp_info = {}
    for name, (key, _) in SOS_FIELD.items():
        path = _get_deck_file(key)
        if path:
            opp_info[name] = (key, path)

    print(f"Building matchups: {MY_DECK_NAME} vs {len(opp_info)} opponents")
    print(f"  Deck file: {MY_DECK_FILE}")
    print(f"  APL:       {MY_APL_KEY}")
    print(f"  Matches:   {args.matches} per pairing ({args.matches*2} total jobs)\n")

    # Jobs: my deck vs each opponent (both directions)
    jobs = []
    for i, (opp_name, (opp_key, opp_file)) in enumerate(opp_info.items()):
        seed = (i * 991 + 7) % 99991
        # my deck as player A
        jobs.append((MY_DECK_NAME, MY_DECK_FILE, MY_APL_KEY,
                      opp_name, opp_file, opp_key, args.matches, seed))
        # my deck as player B
        jobs.append((opp_name, opp_file, opp_key,
                      MY_DECK_NAME, MY_DECK_FILE, MY_APL_KEY, args.matches, seed + 500))

    new_wrs = {}
    done = 0
    with ProcessPoolExecutor(max_workers=args.cores) as pool:
        futures = {pool.submit(_run_bo3_job, j): j for j in jobs}
        for fut in as_completed(futures):
            na, nb, w, t = fut.result()
            new_wrs[(na, nb)] = (w / t * 100) if t > 0 else 50.0
            done += 1
            if done % max(1, len(jobs) // 10) == 0:
                print(f"  {done/len(jobs)*100:.0f}%  ({done}/{len(jobs)})", flush=True)

    # ── Assemble full 30-deck matrix ─────────────────────────────────────
    all_names = DECK_NAMES + [MY_DECK_NAME]
    matrix = {}
    for i, na in enumerate(DECK_NAMES):
        for j, nb in enumerate(DECK_NAMES):
            if i != j:
                matrix[(na, nb)] = RAW[i][j]
    for k, v in new_wrs.items():
        matrix[k] = v

    # ── Print my deck's matchup card ─────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"  {MY_DECK_NAME} -- Bo3 Match WRs vs field")
    print(f"{'='*65}")
    my_matchups = [(nb, matrix.get((MY_DECK_NAME, nb), 0.0))
                   for nb in DECK_NAMES if nb != MY_DECK_NAME]
    my_matchups.sort(key=lambda x: -x[1])
    for opp, wr in my_matchups:
        bar = "#" * int(wr / 5)
        print(f"  {opp:<28}  {wr:5.1f}%  {bar}")
    avg_wr = sum(w for _, w in my_matchups) / len(my_matchups)
    print(f"\n  Avg unweighted WR:  {avg_wr:.1f}%")
    print(f"{'='*65}\n")

    # ── Run Swiss: 25 players per deck, flat equal representation ────────
    pcounts = dict(FLAT_25_COUNTS)
    total_p = sum(pcounts.values())
    field_shares = {n: pcounts[n] / total_p for n in all_names if n in pcounts}

    results = simulate_rc(
        field_shares=field_shares,
        matrix=matrix,
        n_events=args.events,
        n_players=total_p,
        n_rounds=args.rounds,
        seed=42,
    )

    expected_top8 = 8 / total_p * 100

    print(f"{'='*95}")
    print(f"  FULL STANDARD RC SWISS -- 25 players per deck, {len(all_names)} archetypes")
    print(f"  {args.events:,} events | {args.rounds} rounds | {total_p} players | Random top8: {expected_top8:.1f}%")
    print(f"{'='*95}")
    print(f"  {'Deck':<28} {'Players':>7}  {'Field%':>6}  {'Avg':>7}  "
          f"{'Top8%':>6}  {'X-1%':>6}  {'X-2%':>6}  {'EV':>7}  Notes")
    print(f"  {'-'*28} {'-'*7}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*7}")

    for r in results:
        pc   = pcounts.get(r.deck, 0)
        pct  = pc / total_p * 100
        ev   = r.top8_pct - expected_top8
        sign = "+" if ev >= 0 else ""
        rec  = f"{r.avg_wins:.1f}-{r.avg_losses:.1f}"
        mine = "  <<< YOUR DECK" if r.deck == MY_DECK_NAME else ""
        tag  = ""
        if not mine:
            if ev > 15:
                tag = "<< DOMINANT"
            elif ev > 8:
                tag = "<< STRONG"
            elif ev > 3:
                tag = "<< GOOD"
            elif ev < -0.5:
                tag = "BELOW AVG"
        print(f"  {r.deck:<28} {pc:>7}  {pct:>5.1f}%  {rec:>7}  "
              f"{r.top8_pct:>5.1f}%  {r.x1_pct:>5.1f}%  {r.x2_pct:>5.1f}%  "
              f"{sign}{ev:>5.1f}%  {tag}{mine}")

    print(f"{'='*95}")
    print(f"\n  Random expected top8: {expected_top8:.1f}% | Field avg record: "
          f"{sum(r.avg_wins for r in results)/len(results):.2f} wins\n")


if __name__ == "__main__":
    main()
