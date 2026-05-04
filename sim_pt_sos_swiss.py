"""
sim_pt_sos_swiss.py — PT Secrets of Strixhaven 2026: 10-round Standard Swiss simulation

Uses the 325 actual players from the PT (event_id=11881 in mtg_meta.db),
their submitted archetypes, and goldfish kill distributions per archetype to
simulate all 10 Standard rounds. Limited rounds excluded.

Limitations: goldfish race model — no interaction modeled. Fast combo/aggro
decks are overvalued; disruption-based strategies (Izzet Lessons, Spellementals)
will underperform vs their real finish.
"""

import sys, os, random, sqlite3
sys.path.insert(0, os.path.dirname(__file__))

from engine.runner import run_simulation
from sim_bridge import race_win_pct, avg_kill_turn, ARCHETYPE_CLOCKS
from apl import get_apl

N_SIM   = 400   # games per kill-dist per archetype
N_RACE  = 8000  # race trials per match

DB_PATH = r"E:\vscode ai project\mtg-meta-analyzer\data\mtg_meta.db"

# Map DB archetype names → APL registry keys
ARCH_MAP = {
    "Izzet Prowess":          "izzetprowessstandard",
    "Mono Green Landfall":    "monogreenlandfall",
    "Izzet Spellementals":    "izzetspellementals",
    "Izzet Lessons":          "izzetlessons",
    "Selesnya Lessons":       "izzetlessons",      # no deck file; lessons engine shared
    "Temur Lessons":          "izzetlessons",      # no deck file; lessons engine shared
    "Azorius Momo":           "azoriusmomo",
    "Jeskai Control":         "jeskaicontrol",
    "Selesnya Landfall":      "selesnyalandfall",
    "Izzet Maestro":          "izzetmaestro",
    "Golgari Midrange":       "golgarimidrange",
    "Golgari Kona":           "golgarikona",
    "Golgari Control":        "golgaricontrol",
    "Azorius Control":        "azoriuscontrol",
    "Dimir Excruciator":      "dimirexcruciator",
    "Dimir Midrange":         "dimirmidrangestd",
    "Sultai Control":         "sultaicontrol",
    "Four-Color Control":     "fourcolorcontrol",
    "Simic Omniscience":      "simicomniscience",
    "Bant Omniscience":       "bantomniscience",
    "Temur Omniscience":      "temuromniscience",
    "Four-Color Elemental...":"fourcolorelemental",
    "Selesnya Rhythm":        "selesnyarhythm",
    "Simic Rhythm":           "simicrhythm",
    "Bant Rhythm":            "bantrhythm",
    "Selesnya Ouroboroid":    "selesnyaouroboroid",
    "Mono Red Aggro":         "monoredaggrostandard",
    "Boros Dragons":          "borosdragons",
    "Mardu Discard":          "mardudiscard",
    "Rakdos Discard":         "rakdosdiscard",
    "Boros Discard":          "borosdiscard",
    "Temur Lute":             "temurlutestd",
    "Bant Airbending":        "bantairbending",
}

DECK_FILES = {
    "izzetprowessstandard": "decks/izzet_prowess_standard.txt",
    "monogreenlandfall":    "decks/mono_green_landfall_standard.txt",
    "izzetspellementals":   "decks/izzet_spellementals_standard.txt",
    "izzetlessons":         "decks/izzet_lesson_standard.txt",
    "azoriusmomo":          "decks/azorius_momo_standard.txt",
    "jeskaicontrol":        "decks/jeskai_control_standard.txt",
    "selesnyalandfall":     "decks/selesnya_landfall_standard.txt",
    "izzetmaestro":         "decks/izzet_maestro_standard.txt",
    "golgarimidrange":      "decks/golgari_midrange_standard.txt",
    "azoriuscontrol":       "decks/azorius_control_standard.txt",
    "dimirexcruciator":     "decks/dimir_excruciator_standard.txt",
    "azoriusomniscience":   "decks/azorius_omniscience_standard.txt",
    "selesnyaouroboroid":   "decks/selesnya_ouroboroid_standard.txt",
    "roamingelementals":    "decks/roaming_elementals_standard.txt",
    "simicrhythm":          "decks/simic_rhythm_standard.txt",
    "monoredaggrostandard": "decks/mono_red_aggro_standard.txt",
    "borosaggrostandard":   "decks/boros_aggro_standard.txt",
    "mardudiscard":         "decks/mardu_discard_standard.txt",
    "rakdosdiscard":        "decks/rakdos_discard_standard.txt",
    "borosdiscard":         "decks/boros_discard_standard.txt",
    "sultaicontrol":        "decks/sultai_control_standard.txt",
    "golgarikona":          "decks/golgari_kona_standard.txt",
    "golgaricontrol":       "decks/golgari_control_standard.txt",
    "dimirmidrangestd":     "decks/dimir_midrange_std_standard.txt",
    "fourcolorcontrol":     "decks/four_color_control_standard.txt",
    "simicomniscience":     "decks/simic_omniscience_standard.txt",
    "bantomniscience":      "decks/bant_omniscience_standard.txt",
    "temuromniscience":     "decks/temur_omniscience_standard.txt",
    "fourcolorelemental":   "decks/four_color_elemental_standard.txt",
    "selesnyarhythm":       "decks/selesnya_rhythm_standard.txt",
    "bantrhythm":           "decks/bant_rhythm_standard.txt",
    "bantairbending":       "decks/bant_airbending_standard.txt",
    "borosdragons":         "decks/boros_dragons_standard.txt",
    "temurlutestd":         "decks/temur_lute_standard.txt",
}


def load_players():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT player, archetype FROM decks
        WHERE event_id = 11881
        ORDER BY id
    """)
    players = []
    for i, (name, arch) in enumerate(cur.fetchall()):
        name = name.encode('ascii', 'replace').decode('ascii')
        key = ARCH_MAP.get(arch, "golgarimidrange")
        players.append({
            "id": i, "name": name, "arch": arch, "key": key,
            "wins": 0, "losses": 0, "draws": 0,
            "opp_wins": 0, "opp_total": 0, "played": set(),
        })
    con.close()
    return players


def measure_dists(players):
    from data.deck import load_deck_from_file
    keys = set(p["key"] for p in players)
    dists = {}
    print(f"  Measuring kill distributions for {len(keys)} archetypes...")
    for key in sorted(keys):
        apl = get_apl(key)
        deck_file = DECK_FILES.get(key)
        if apl and deck_file and os.path.exists(deck_file):
            try:
                main, _ = load_deck_from_file(deck_file)
                result = run_simulation(apl, main, n=N_SIM, on_play=True, seed=42)
                dist = result.kill_turn_distribution()
                dists[key] = dist
                print(f"    {key:<30} T{avg_kill_turn(dist):.2f}")
                continue
            except Exception as e:
                pass
        # Fallback to ARCHETYPE_CLOCKS
        dist = ARCHETYPE_CLOCKS.get(key + "standard",
               ARCHETYPE_CLOCKS.get(key,
               ARCHETYPE_CLOCKS["unknown"]))
        dists[key] = dist
        print(f"    {key:<30} T{avg_kill_turn(dist):.2f}  (clock fallback)")
    return dists


def shift_dist(dist):
    return {t + 1: pct for t, pct in dist.items()}


def match_win_pct(dist_a, dist_b):
    return race_win_pct(dist_a, dist_b, n=N_RACE) / 100.0


def swiss_round(players, dists, rnd, rng):
    # Sort: wins desc, then opponent win% desc
    def sort_key(p):
        opp_wr = p["opp_wins"] / p["opp_total"] if p["opp_total"] > 0 else 0.5
        return (-p["wins"], -opp_wr)

    ordered = sorted(players, key=sort_key)
    paired = [False] * len(ordered)
    pairs = []

    for i in range(len(ordered)):
        if paired[i]:
            continue
        p1 = ordered[i]
        # Find closest unpaired opponent not already played
        for j in range(i + 1, len(ordered)):
            if paired[j]:
                continue
            p2 = ordered[j]
            if p2["id"] not in p1["played"]:
                pairs.append((p1, p2))
                paired[i] = paired[j] = True
                break
        else:
            # All remaining opponents already played — take nearest unpaired
            for j in range(i + 1, len(ordered)):
                if not paired[j]:
                    pairs.append((p1, ordered[j]))
                    paired[i] = paired[j] = True
                    break

    # Handle odd player (bye)
    bye_player = None
    for i, p in enumerate(ordered):
        if not paired[i]:
            bye_player = p
            p["wins"] += 1
            break

    wins_this_round = {p["id"]: 0 for p in players}
    results = []

    for p1, p2 in pairs:
        d1 = dists[p1["key"]]
        d2 = dists[p2["key"]]
        # Coin flip for play/draw
        if rng.random() < 0.5:
            wp = match_win_pct(d1, shift_dist(d2))
        else:
            wp = match_win_pct(d2, shift_dist(d1))
            wp = 1.0 - wp

        p1_wins = rng.random() < wp
        winner, loser = (p1, p2) if p1_wins else (p2, p1)
        winner["wins"] += 1
        loser["losses"] += 1
        winner["played"].add(loser["id"])
        loser["played"].add(winner["id"])
        wins_this_round[winner["id"]] = 1
        results.append((winner, loser))

    # Update opponent win tracking
    for p1, p2 in pairs:
        p1["opp_wins"]  += p2["wins"]
        p1["opp_total"] += p2["wins"] + p2["losses"]
        p2["opp_wins"]  += p1["wins"]
        p2["opp_total"] += p1["wins"] + p1["losses"]

    return results, bye_player


def main():
    print("=" * 60)
    print("PT SOS 2026 — 10-Round Standard Swiss Simulation")
    print("325 actual players | Limited excluded")
    print("=" * 60)

    print("\nLoading players from DB...")
    players = load_players()
    print(f"  {len(players)} players loaded")

    print("\nMeasuring archetype kill distributions...")
    dists = measure_dists(players)

    rng = random.Random(2026)

    print(f"\nRunning 10 rounds of Swiss...\n")
    for rnd in range(1, 11):
        results, bye = swiss_round(players, dists, rnd, rng)
        # standings snapshot
        top = sorted(players, key=lambda p: (-p["wins"], -p["opp_wins"]))[:8]
        leader = top[0]
        print(f"  Round {rnd:>2} done | Leader: {leader['wins']}-{leader['losses']} "
              f"{leader['name'][:20]:<20} ({leader['arch'][:24]})")

    # Final standings
    def standing_key(p):
        opp_wr = p["opp_wins"] / p["opp_total"] if p["opp_total"] > 0 else 0
        return (-p["wins"], -opp_wr)

    standings = sorted(players, key=standing_key)

    print("\n" + "=" * 60)
    print("FINAL STANDINGS — Top 16")
    print(f"{'Rank':<5} {'Record':<8} {'OppWR':>6}  {'Player':<26} {'Archetype'}")
    print("-" * 60)
    for rank, p in enumerate(standings[:16], 1):
        opp_wr = p["opp_wins"] / p["opp_total"] * 100 if p["opp_total"] else 0
        marker = " <-- Top 8" if rank <= 8 else ""
        print(f"  {rank:<3} {p['wins']}-{p['losses']:<5} {opp_wr:5.1f}%  "
              f"{p['name'][:24]:<26} {p['arch'][:24]}{marker}")

    print()
    print("SIMULATED TOP 8:")
    top8_archs = {}
    for p in standings[:8]:
        top8_archs[p["arch"]] = top8_archs.get(p["arch"], 0) + 1
    for arch, cnt in sorted(top8_archs.items(), key=lambda x: -x[1]):
        print(f"  {cnt}x {arch}")

    print()
    print("ARCHETYPE PERFORMANCE (by avg record):")
    arch_records = {}
    for p in players:
        a = p["arch"]
        if a not in arch_records:
            arch_records[a] = {"wins": 0, "losses": 0, "count": 0}
        arch_records[a]["wins"]   += p["wins"]
        arch_records[a]["losses"] += p["losses"]
        arch_records[a]["count"]  += 1
    for arch, rec in sorted(arch_records.items(),
                             key=lambda x: -x[1]["wins"] / (x[1]["wins"] + x[1]["losses"])):
        if rec["count"] < 2:
            continue
        wr = rec["wins"] / (rec["wins"] + rec["losses"]) * 100
        avg_w = rec["wins"] / rec["count"]
        print(f"  {wr:5.1f}%  avg {avg_w:.1f}W  ({rec['count']:>3}p)  {arch}")


if __name__ == "__main__":
    main()
