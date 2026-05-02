"""scripts/calibrate_matrix.py — 11x11 match matrix for current Standard.

Runs every match APL pair for N games each, prints a table of
per-pair win rates plus per-deck aggregate WR across the field.

Usage:
    python scripts/calibrate_matrix.py [games_per_pair]
"""
import sys
import os
import importlib
from pathlib import Path

# Hop to repo root
ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from engine.match_engine import run_match
from engine.bo3_match import run_bo3
from data.deck import load_deck_from_file

# Auto-register oracle-derived handlers for every card across all
# matrix decks. Hand-written handlers take precedence.
from engine.auto_handlers import auto_register_all_standard_matrix
_auto_stats = auto_register_all_standard_matrix()
print(f"[auto-handlers] registered {_auto_stats['registered']}, "
      f"skipped {_auto_stats['skipped_handwritten']} hand-written, "
      f"{_auto_stats['no_effect']} cards had no parseable effect "
      f"(per-trigger: {_auto_stats['per_trigger']})")


DECKS = [
    ("Boros",     "apl.boros_aggro_standard_match",         "BorosAggroStandardMatchAPL",         "decks/boros_aggro_standard.txt"),
    ("Gruul",     "apl.gruul_aggro_standard_match",         "GruulAggroStandardMatchAPL",         "decks/gruul_aggro_standard.txt"),
    ("MonoR",     "apl.mono_red_aggro_standard_match",      "MonoRedAggroStandardMatchAPL",       "decks/mono_red_aggro_standard.txt"),
    ("Azorius",   "apl.azorius_control_standard_match",     "AzoriusControlStandardMatchAPL",     "decks/azorius_control_standard.txt"),
    ("Prowess",   "apl.izzet_prowess_standard_match",       "IzzetProwessStandardMatchAPL",       "decks/izzet_prowess_standard.txt"),
    ("Dimir",     "apl.dimir_midrange_standard_match",      "DimirMidrangeStandardMatchAPL",      "decks/dimir_midrange_standard.txt"),
    ("MonoG",     "apl.mono_green_landfall_standard_match", "MonoGreenLandfallStandardMatchAPL",  "decks/mono_green_landfall_standard.txt"),
    ("Lesson",    "apl.izzet_lesson_standard_match",        "IzzetLessonStandardMatchAPL",        "decks/izzet_lesson_standard.txt"),
    ("Spell",     "apl.izzet_spellementals_standard_match", "IzzetSpellementalsStandardMatchAPL", "decks/izzet_spellementals_standard.txt"),
    ("Doomsday",  "apl.superior_doomsday_standard_match",   "SuperiorDoomsdayStandardMatchAPL",   "decks/superior_doomsday_standard.txt"),
    ("Sultai",    "apl.sultai_reanimator_standard_match",   "SultaiReanimatorStandardMatchAPL",   "decks/domain_ramp_standard.txt"),
    ("Jeskai",    "apl.jeskai_control_standard_match",      "JeskaiControlStandardMatchAPL",      "decks/jeskai_control_standard.txt"),
    ("SimCub",    "apl.simic_cub_standard_match",           "SimicCubStandardMatchAPL",           "decks/simic_cub_standard.txt"),
]


def main():
    pairs = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    mode = sys.argv[2] if len(sys.argv) > 2 else "game"   # 'game' or 'bo3'

    loaded = []
    for short, mod_name, cls_name, deck_path in DECKS:
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            deck, side = load_deck_from_file(deck_path)
            # Build sideboard dict (name -> Card) for bo3 plan application
            sb_dict = {c.name: c for c in side} if side else {}
            loaded.append((short, cls, deck, sb_dict))
        except Exception as exc:
            print(f"  FAIL loading {short}: {exc}")

    print(f"Mode: {mode} × {pairs} pairs per matchup")
    hdr = " " * 10 + " ".join(f"{l[0]:>7s}" for l in loaded)
    print(hdr)
    totals = {}
    for short_a, cls_a, deck_a, sb_a in loaded:
        line = f"{short_a:10s}"
        wins_total = 0
        games_total = 0
        crashes = 0
        for short_b, cls_b, deck_b, sb_b in loaded:
            if short_a == short_b:
                line += f"  {'--':>5s}"
                continue
            wins = 0
            for g in range(pairs):
                try:
                    if mode == "bo3":
                        # Ask each APL instance for its SB plan vs the
                        # other's ARCHETYPE category. None = no swap.
                        inst_a = cls_a()
                        inst_b = cls_b()
                        opp_b_arch = getattr(inst_b, "ARCHETYPE", "midrange")
                        opp_a_arch = getattr(inst_a, "ARCHETYPE", "midrange")
                        sb_plan_a = (inst_a.sb_plan_for(opp_b_arch)
                                     if hasattr(inst_a, "sb_plan_for") else None)
                        sb_plan_b = (inst_b.sb_plan_for(opp_a_arch)
                                     if hasattr(inst_b, "sb_plan_for") else None)
                        r = run_bo3(inst_a, deck_a, sb_a,
                                     inst_b, deck_b, sb_b,
                                     sb_plan_a=sb_plan_a, sb_plan_b=sb_plan_b,
                                     a_on_play_g1=(g % 2 == 0), seed=g)
                    else:
                        r = run_match(cls_a(), deck_a, cls_b(), deck_b, seed=g)
                    if r.winner == "a":
                        wins += 1
                except Exception:
                    crashes += 1
            line += f"  {wins:>2d}/{pairs}"
            wins_total += wins
            games_total += pairs
        pct = 100.0 * wins_total / games_total if games_total else 0
        totals[short_a] = pct
        crash_tag = f" x{crashes}" if crashes else ""
        line += f"   |  {pct:4.1f}%{crash_tag}"
        print(line)

    print()
    print("Aggregate WR across the field:")
    for k, v in sorted(totals.items(), key=lambda x: -x[1]):
        print(f"  {k:10s}  {v:4.1f}%")


if __name__ == "__main__":
    main()
