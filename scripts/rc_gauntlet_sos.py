"""
scripts/rc_gauntlet_sos.py -- RC Swiss gauntlet using PT SOS 2026 meta.

Real Bo3 matches via run_match (APL vs APL both sides, full interaction).
10-25 players per deck. Swiss pairings. Multiple events for stable EV.

Usage:
    python scripts/rc_gauntlet_sos.py [--matches N] [--events N] [--cores N] [--rounds N]
"""
import sys, os, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── PT SOS 2026 field (325 players, constructed rounds) ───────────────────
# Archetype name -> (registry_key, player_count_at_PT_SOS)
# Player counts clipped to [10, 25] for RC field simulation.
# Decks with 0 or 1 player at PT SOS get floor of 10 (fringe representation).
SOS_FIELD = {
    "Izzet Prowess":        ("izzetprowessstandard", 25),   # 99 at SOS, capped
    "Mono Green Landfall":  ("monogreenlandfall",    25),   # 62 at SOS, capped
    "Izzet Spellementals":  ("izzetspellementals",   25),   # 26 at SOS, capped
    "Izzet Lessons":        ("izzetlesson",           24),
    "Azorius Momo":         ("azoriusmomo",           14),
    "Jeskai Control":       ("jeskaicontrol",          12),
    "Selesnya Landfall":    ("selesnyalandfall",       11),
    "Izzet Maestro":        ("izzetmaestro",           10),
    "Azorius Control":      ("azoriuscontrol",         10),
    "Golgari Midrange":     ("golgarimidrange",        10),
    "Dimir Excruciator":    ("dimirexcruciator",       10),
    "Sultai Control":       ("sultaicontrol",          10),
    "Four-Color Control":   ("fourcolorcontrol",       10),
    "Selesnya Rhythm":      ("selesnyarhythm",         10),
    "Selesnya Ouroboroid":  ("selesnyaouroboroid",     10),
    "Mardu Discard":        ("mardudiscard",           10),
    "Boros Dragons":        ("borosdragons",           10),
    "Bant Rhythm":          ("bantrhythm",             10),
    "Rakdos Discard":       ("rakdosdiscard",          10),
    "Simic Rhythm":         ("simicrhythm",            10),
    "Bant Airbending":      ("bantairbending",         10),
    "Golgari Kona":         ("golgarikona",            10),
    "Golgari Control":      ("golgaricontrol",         10),
    "Boros Discard":        ("borosdiscard",           10),
    "Four-Color Elemental": ("fourcolorelemental",     10),
    "Temur Lute":           ("temurlutestd",           10),
    "Simic Omniscience":    ("simicomniscience",       10),
    "Esper Pixie":          ("esperpixie",             10),
    "Gruul Aggro":          ("gruulaggro",             10),
}


def _get_deck_file(key):
    from apl import APL_REGISTRY
    entry = APL_REGISTRY.get(key)
    if entry and isinstance(entry, tuple) and len(entry) >= 3:
        path = entry[2]
        if path and path.endswith('.txt') and os.path.exists(path):
            return path
    return None


def _run_bo3_job(args):
    """
    Worker: run N real Bo3 matches (deck_a vs deck_b).
    Each Bo3: play G1, G2 (swap on_play), G3 if split.
    Returns (name_a, name_b, match_wins, total_matches).
    """
    name_a, key_a, name_b, key_b, n_matches, seed_base = args

    from apl import get_match_apl
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    def load(key):
        path = _get_deck_file(key)
        if not path:
            return None, None
        try:
            deck, _ = load_deck_from_file(path)
            apl = get_match_apl(key)
            return deck, apl
        except Exception:
            return None, None

    deck_a, apl_a = load(key_a)
    deck_b, apl_b = load(key_b)
    if deck_a is None or deck_b is None:
        return name_a, name_b, 0, 0

    match_wins = 0
    total = 0

    for i in range(n_matches):
        s = seed_base + i * 13
        wins_a = 0
        wins_b = 0

        # G1: a on the play
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s, on_play=True)
            if r.won: wins_a += 1
            else:     wins_b += 1
        except Exception:
            wins_b += 1

        # G2: b on the play (sideboard game — same decks, role reversed)
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s+1, on_play=False)
            if r.won: wins_a += 1
            else:     wins_b += 1
        except Exception:
            wins_b += 1

        # G3 only if split (1-1)
        if wins_a == 1 and wins_b == 1:
            on_play_g3 = (i % 2 == 0)   # alternate G3 on_play across matches
            try:
                r = run_match(apl_a, deck_a, apl_b, deck_b, seed=s+2, on_play=on_play_g3)
                if r.won: wins_a += 1
                else:     wins_b += 1
            except Exception:
                wins_b += 1

        if wins_a >= 2:
            match_wins += 1
        total += 1

    return name_a, name_b, match_wins, total


def main():
    ap = argparse.ArgumentParser(description="PT SOS 2026 RC Swiss gauntlet (real Bo3)")
    ap.add_argument("--matches", type=int, default=60,  help="Bo3 matches per pairing")
    ap.add_argument("--events",  type=int, default=3000, help="Swiss events to simulate")
    ap.add_argument("--cores",   type=int, default=12)
    ap.add_argument("--rounds",  type=int, default=8)
    args = ap.parse_args()

    # Validate deck files
    valid = {}
    skipped = []
    seen_files = set()
    for name, (key, players) in SOS_FIELD.items():
        path = _get_deck_file(key)
        if path is None:
            skipped.append(f"{name} ({key}): no deck file")
            continue
        if path in seen_files:
            skipped.append(f"{name}: duplicate file {path}, skipped")
            continue
        seen_files.add(path)
        valid[name] = (key, players)

    if skipped:
        print("[SKIP]")
        for s in skipped:
            print(f"  {s}")

    names    = list(valid.keys())
    keys     = [valid[n][0] for n in names]
    pcounts  = {n: valid[n][1] for n in names}
    total_p  = sum(pcounts.values())
    n_decks  = len(names)
    n_pairs  = n_decks * (n_decks - 1)

    print(f"\nPT SOS 2026 Standard RC Gauntlet")
    print(f"Decks: {n_decks}  |  Players: {total_p}  |  Rounds: {args.rounds}")
    print(f"Bo3 matches per pairing: {args.matches}  |  Swiss events: {args.events:,}  |  Cores: {args.cores}")
    print(f"Total Bo3 matches: {n_pairs * args.matches:,}  (real match engine, both sides)\n")

    print(f"{'Deck':<28} {'Players':>7}  {'Field%':>6}")
    print("-" * 45)
    for n in names:
        pct = pcounts[n] / total_p * 100
        print(f"  {n:<26} {pcounts[n]:>7}  {pct:>5.1f}%")
    print()

    # Build jobs
    jobs = []
    for i, (na, ka) in enumerate(zip(names, keys)):
        for j, (nb, kb) in enumerate(zip(names, keys)):
            if i == j:
                continue
            seed = (i * 997 + j * 103 + 7) % 99991
            jobs.append((na, ka, nb, kb, args.matches, seed))

    # Run Bo3 matrix
    print(f"Building Bo3 match matrix ({n_pairs} pairings)...")
    matrix = {}
    done = 0
    report_every = max(1, n_pairs // 20)

    with ProcessPoolExecutor(max_workers=args.cores) as pool:
        futures = {pool.submit(_run_bo3_job, j): j for j in jobs}
        for fut in as_completed(futures):
            na, nb, w, t = fut.result()
            matrix[(na, nb)] = (w / t * 100) if t > 0 else 50.0
            done += 1
            if done % report_every == 0:
                print(f"  {done/n_pairs*100:5.1f}%  ({done}/{n_pairs})", flush=True)

    print(f"\nMatrix done. Running {args.events:,} Swiss events...\n")

    # Swiss simulation
    from engine.tournament import simulate_rc
    field_shares = {n: pcounts[n] / total_p for n in names}   # fractions 0-1
    results = simulate_rc(
        field_shares=field_shares,
        matrix=matrix,
        n_events=args.events,
        n_players=total_p,
        n_rounds=args.rounds,
        seed=42,
    )

    expected_top8 = 8 / total_p * 100

    # Print ALL results
    print(f"\n{'='*90}")
    print(f"  PT SOS 2026 STANDARD RC SWISS -- {args.events:,} events, {args.rounds} rounds, {total_p} players")
    print(f"  Real Bo3 match engine (APL vs APL, {args.matches} matches/pairing)")
    print(f"{'='*90}")
    print(f"  {'Deck':<28} {'Players':>7}  {'Field%':>6}  {'Avg':>7}  "
          f"{'Top8%':>6}  {'X-1%':>6}  {'X-2%':>6}  {'EV':>7}  Notes")
    print(f"  {'-'*28} {'-'*7}  {'-'*6}  {'-'*7}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*7}")

    for r in results:
        pc  = pcounts.get(r.deck, 0)
        pct = pc / total_p * 100
        ev  = r.top8_pct - expected_top8
        sign = "+" if ev >= 0 else ""
        rec  = f"{r.avg_wins:.1f}-{r.avg_losses:.1f}"

        tag = ""
        if ev > 10 and pct < 5:
            tag = "<< UNDERPLAYED HERO"
        elif ev > 10:
            tag = "<< DOMINANT"
        elif ev > 5:
            tag = "<< STRONG"
        elif ev < -1.0 and pc >= 20:
            tag = "TRAP"

        print(f"  {r.deck:<28} {pc:>7}  {pct:>5.1f}%  {rec:>7}  "
              f"{r.top8_pct:>5.1f}%  {r.x1_pct:>5.1f}%  {r.x2_pct:>5.1f}%  "
              f"{sign}{ev:>5.1f}%  {tag}")

    print(f"{'='*90}")
    print(f"\n  Random top8 rate: {expected_top8:.1f}%  (8/{total_p} players)")
    print(f"  Field avg record: {sum(r.avg_wins for r in results)/len(results):.2f} wins\n")

    # Full Bo3 match WR matrix
    print(f"\n{'='*90}")
    print("  Bo3 MATCH WR MATRIX  (row = our deck, value = match win % vs column)")
    print(f"{'='*90}")
    col_w = 6
    hdr = f"  {'Deck':<28}"
    for n in names:
        hdr += f"  {n[:col_w]:>{col_w}}"
    print(hdr)

    for na in names:
        row = f"  {na:<28}"
        for nb in names:
            if na == nb:
                row += f"  {'---':>{col_w}}"
            else:
                wr = matrix.get((na, nb), 0.0)
                row += f"  {wr:>{col_w}.1f}%"
        print(row)
    print()


if __name__ == "__main__":
    main()
