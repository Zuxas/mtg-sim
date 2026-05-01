"""
analyze_pt_matchups.py — PT event matchup data builder.

Usage:
    python scripts/analyze_pt_matchups.py [--event data/pt_sos_2026.json] [--rounds 4,5,6,7,8]

Reads the PT event JSON, resolves archetypes for known players, and outputs:
  1. Per-archetype Constructed W/L record (rounds 4+ only)
  2. Head-to-head MU table for archetype pairs with known data
  3. Coverage report (how many matches have both players identified)

Add results as rounds complete by editing the JSON file:
    rounds -> "5" -> [ {p1, p2, winner, score}, ... ]

Add player->archetype mappings as they become known:
    player_archetypes -> { "Lastname, Firstname": "Archetype Name" }
"""
import sys, json, argparse
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def load(path):
    with open(path) as f:
        return json.load(f)


def normalize(name):
    return name.strip().lower()


def resolve_archetype(player, arch_map):
    n = normalize(player)
    for k, v in arch_map.items():
        if normalize(k) == n:
            return v
    return None


def analyze(data, constructed_rounds):
    arch_map = data["player_archetypes"]
    rounds = data["rounds"]

    # Per-archetype overall record across all constructed rounds
    arch_record = defaultdict(lambda: {"w": 0, "l": 0, "d": 0, "matches": []})

    # Head-to-head: arch_a vs arch_b -> {w: wins for arch_a, l: losses for arch_a}
    h2h = defaultdict(lambda: {"w": 0, "l": 0, "d": 0})

    total_matches = 0
    both_known = 0
    one_known = 0
    neither_known = 0

    for rnd in constructed_rounds:
        rnd_str = str(rnd)
        if rnd_str not in rounds:
            continue
        for m in rounds[rnd_str]:
            p1, p2, winner = m["p1"], m["p2"], m["winner"]
            a1 = resolve_archetype(p1, arch_map)
            a2 = resolve_archetype(p2, arch_map)
            total_matches += 1

            if a1 and a2:
                both_known += 1
                key = tuple(sorted([a1, a2]))
                if winner == "draw":
                    arch_record[a1]["d"] += 1
                    arch_record[a2]["d"] += 1
                    h2h[key]["d"] += 1
                elif winner == "p1":
                    arch_record[a1]["w"] += 1
                    arch_record[a2]["l"] += 1
                    if a1 <= a2:
                        h2h[(a1, a2)]["w"] += 1
                    else:
                        h2h[(a2, a1)]["l"] += 1
                else:  # p2
                    arch_record[a1]["l"] += 1
                    arch_record[a2]["w"] += 1
                    if a1 <= a2:
                        h2h[(a1, a2)]["l"] += 1
                    else:
                        h2h[(a2, a1)]["w"] += 1
                arch_record[a1]["matches"].append((rnd, p2, a2, winner == "p1"))
                arch_record[a2]["matches"].append((rnd, p1, a1, winner == "p2"))

            elif a1:
                one_known += 1
                if winner == "draw":
                    arch_record[a1]["d"] += 1
                elif winner == "p1":
                    arch_record[a1]["w"] += 1
                else:
                    arch_record[a1]["l"] += 1
                arch_record[a1]["matches"].append((rnd, p2, "?", winner == "p1"))

            elif a2:
                one_known += 1
                if winner == "draw":
                    arch_record[a2]["d"] += 1
                elif winner == "p2":
                    arch_record[a2]["w"] += 1
                else:
                    arch_record[a2]["l"] += 1
                arch_record[a2]["matches"].append((rnd, p1, "?", winner == "p2"))

            else:
                neither_known += 1

    return arch_record, h2h, {
        "total": total_matches,
        "both_known": both_known,
        "one_known": one_known,
        "neither_known": neither_known,
    }


def wr(rec):
    total = rec["w"] + rec["l"] + rec["d"]
    if total == 0:
        return 0.0
    return rec["w"] / total * 100


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="data/pt_sos_2026.json")
    parser.add_argument("--rounds", default="4,5,6,7,8")
    args = parser.parse_args()

    path = ROOT / args.event
    data = load(path)
    constructed_rounds = [int(r) for r in args.rounds.split(",")]
    rounds_available = sorted(int(k) for k in data["rounds"])
    constructed_available = [r for r in rounds_available if r in constructed_rounds]

    arch_record, h2h, coverage = analyze(data, constructed_rounds)

    print(f"\n{'='*60}")
    print(f"  {data['event']} — Matchup Analysis")
    print(f"  Constructed rounds analyzed: {constructed_available}")
    print(f"  Total players: {data['total_players']}")
    print(f"  Known archetypes tagged: {len(data['player_archetypes'])}")
    print(f"{'='*60}")

    print(f"\nCoverage:")
    print(f"  Total matches:       {coverage['total']}")
    print(f"  Both players known:  {coverage['both_known']}  ({coverage['both_known']/coverage['total']*100:.1f}%)")
    print(f"  One player known:    {coverage['one_known']}")
    print(f"  Neither known:       {coverage['neither_known']}")

    print(f"\n--- Per-Archetype Constructed Record ---")
    print(f"{'Archetype':<26} {'W':>3} {'L':>3} {'D':>3} {'WR%':>6}  {'PT field%':>9}")
    field = data.get("field", {})
    total_players = data["total_players"]
    sorted_archs = sorted(arch_record.keys(),
                          key=lambda a: -(arch_record[a]["w"] / max(1, arch_record[a]["w"] + arch_record[a]["l"])))
    for arch in sorted_archs:
        rec = arch_record[arch]
        fp = field.get(arch, 0)
        fp_pct = fp / total_players * 100 if fp else 0
        print(f"  {arch:<24} {rec['w']:>3} {rec['l']:>3} {rec['d']:>3}  {wr(rec):>5.1f}%  {fp_pct:>7.1f}%")

    if h2h:
        print(f"\n--- Head-to-Head (both players known) ---")
        for (a1, a2), rec in sorted(h2h.items()):
            total = rec["w"] + rec["l"] + rec["d"]
            if total == 0:
                continue
            a1_wr = rec["w"] / total * 100
            print(f"  {a1:<26} vs {a2:<26}  {rec['w']}-{rec['l']}-{rec['d']}  ({a1_wr:.0f}% for {a1.split()[0]})")

    print(f"\n--- Match Log (known players) ---")
    for arch in sorted_archs:
        rec = arch_record[arch]
        print(f"  {arch}  ({rec['w']}-{rec['l']}-{rec['d']}):")
        for (rnd, opp, opp_arch, won) in rec["matches"]:
            result = "W" if won else ("D" if not won and rec["d"] > 0 else "L")
            print(f"    R{rnd}: {'W' if won else 'L'} vs {opp} [{opp_arch}]")

    print()


if __name__ == "__main__":
    main()
