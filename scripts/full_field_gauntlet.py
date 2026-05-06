"""
scripts/full_field_gauntlet.py -- Full Standard field WR matrix.

Runs every Standard deck vs every other deck using registered Match APLs.
Reports G1 field-weighted win rate per archetype to surface
over/underperformers relative to their metagame share.

Usage:
    python scripts/full_field_gauntlet.py [--games N] [--cores N]
"""
import sys, os, argparse
from concurrent.futures import ProcessPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from format_config import get_field


# Display name -> registry key (must match APL_REGISTRY / MATCH_APL_REGISTRY)
STANDARD_DECKS = {
    "Simic Rhythm":         "simicrhythm",
    "Bant Rhythm":          "bantrhythm",
    "Sultai Reanimator":    "sultaireanimator",
    "Izzet Prowess":        "izzetprowessstandard",
    "Bant Airbending":      "bantairbending",
    "Izzet Spellementals":  "izzetspellementals",
    "Selesnya Landfall":    "selesnyalandfall",
    "Mono Green Landfall":  "monogreenlandfall",
    "Izzet Lessons":        "izzetlesson",
    "Five-Color Rhythm":    "fivecolorrhythm",
    "Grixis Elementals":    "grixiselementals",
    "Jeskai Control":       "jeskaicontrol",
    "Dimir Excruciator":    "dimirexcruciator",
    "Selesnya Ouroboroid":  "selesnyaouroboroid",
    "Azorius Momo":         "azoriusmomo",
}


def _get_deck_file(key):
    """Return deck file path for a registry key, or None if not found."""
    from apl import APL_REGISTRY
    entry = APL_REGISTRY.get(key)
    if entry and isinstance(entry, tuple) and len(entry) >= 3:
        path = entry[2]
        if path and path.endswith('.txt') and os.path.exists(path):
            return path
    return None


def _run_matchup_job(args):
    """Worker: run N G1 games of key_a vs key_b. Returns (key_a, key_b, wins, total)."""
    key_a, key_b, n_games, seed_base = args

    from apl import get_match_apl, APL_REGISTRY
    from data.deck import load_deck_from_file
    from engine.match_runner import run_match

    def load_pair(key):
        deck_file = _get_deck_file(key)
        if not deck_file:
            return None, None
        try:
            main_deck, _ = load_deck_from_file(deck_file)
            apl = get_match_apl(key)
            return main_deck, apl
        except Exception:
            return None, None

    deck_a, apl_a = load_pair(key_a)
    deck_b, apl_b = load_pair(key_b)
    if deck_a is None or deck_b is None:
        return key_a, key_b, 0, 0

    wins = 0
    total = 0
    for i in range(n_games):
        seed = seed_base + i
        on_play = (i % 2 == 0)
        try:
            r = run_match(apl_a, deck_a, apl_b, deck_b, seed=seed, on_play=on_play)
            wins += 1 if r.won else 0
            total += 1
        except Exception:
            pass

    return key_a, key_b, wins, total


def main():
    ap = argparse.ArgumentParser(description="Full Standard field WR matrix")
    ap.add_argument("--games", type=int, default=200, help="G1 games per matchup")
    ap.add_argument("--cores", type=int, default=8)
    args = ap.parse_args()

    field = get_field("standard")
    decks = STANDARD_DECKS

    # Validate which decks can load
    valid = {}
    skipped = []
    for name, key in decks.items():
        deck_file = _get_deck_file(key)
        if deck_file is None:
            skipped.append(f"{name} ({key}): no deck file")
        else:
            valid[name] = key

    if skipped:
        print("[SKIP]")
        for s in skipped:
            print(f"  {s}")

    names = sorted(valid.keys(), key=lambda n: -field.get(n, 0))
    keys  = [valid[n] for n in names]
    n_decks = len(names)
    n_jobs = n_decks * (n_decks - 1)
    print(f"\nRunning {n_decks} archetypes x {n_decks-1} opponents x {args.games} G1 games")
    print(f"Cores: {args.cores}  Total sims: ~{n_jobs * args.games:,}\n")

    # Build all jobs: a vs b and b vs a are symmetric (both track on_play variance)
    jobs = []
    for i, ka in enumerate(keys):
        for j, kb in enumerate(keys):
            if i == j:
                continue
            seed_base = (i * 997 + j * 101 + 42) % 99991
            jobs.append((ka, kb, args.games, seed_base))

    results = {}
    completed = 0
    report_every = max(1, n_jobs // 20)

    with ProcessPoolExecutor(max_workers=args.cores) as pool:
        futures = {pool.submit(_run_matchup_job, j): j for j in jobs}
        for fut in as_completed(futures):
            ka, kb, wins, total = fut.result()
            results[(ka, kb)] = (wins, total)
            completed += 1
            if completed % report_every == 0:
                pct = completed / n_jobs * 100
                print(f"  {pct:5.1f}%  ({completed}/{n_jobs})", flush=True)

    print()

    # Compute field-weighted G1 WR per deck
    rows = []
    for name in names:
        key_a = valid[name]
        share = field.get(name, 0)
        total_w = 0
        total_g = 0
        fw_wins = 0.0
        fw_tot  = 0.0

        for name_b, key_b in valid.items():
            if name_b == name:
                continue
            w, t = results.get((key_a, key_b), (0, 0))
            if t == 0:
                continue
            wr = w / t
            sb = field.get(name_b, 0)
            total_w += w
            total_g += t
            fw_wins += wr * sb
            fw_tot  += sb

        avg_wr = total_w / total_g if total_g > 0 else 0.0
        fw_wr  = fw_wins / fw_tot  if fw_tot  > 0 else 0.0
        delta  = fw_wr - 0.50

        rows.append((name, share, avg_wr, fw_wr, delta))

    rows.sort(key=lambda r: -r[3])

    print("=" * 72)
    print(f"  {'Archetype':<26}  {'Field%':>6}  {'Avg G1':>7}  {'FW G1':>7}  {'vs 50%':>7}")
    print("-" * 72)
    for name, share, avg_wr, fw_wr, delta in rows:
        sign = "+" if delta >= 0 else ""
        tag = "  <-- HERO" if delta > 0.12 and share < 5.0 else ""
        tag = "  <-- DOMINANT" if delta > 0.20 and share >= 5.0 else tag
        print(f"  {name:<26}  {share:5.1f}%  {avg_wr*100:6.1f}%  {fw_wr*100:6.1f}%  {sign}{delta*100:.1f}%{tag}")
    print("=" * 72)

    # Full matchup matrix
    print("\n--- G1 WR matrix (row=our deck, col=opponent) ---\n")
    col_w = 8
    hdr = " " * 28
    for n in names:
        hdr += f" {n[:col_w]:>{col_w}}"
    print(hdr)

    for name_a in names:
        key_a = valid[name_a]
        row = f"  {name_a:<26}"
        for name_b in names:
            if name_a == name_b:
                row += f" {'---':>{col_w}}"
                continue
            key_b = valid[name_b]
            w, t = results.get((key_a, key_b), (0, 0))
            wr = w / t * 100 if t > 0 else 0.0
            row += f" {wr:>{col_w}.1f}%"
        print(row)

    print()


if __name__ == "__main__":
    main()
