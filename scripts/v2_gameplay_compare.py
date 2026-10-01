"""Milestone three, phase 1: compare engine v2 with real MTGO gameplay.

  python scripts/v2_gameplay_compare.py                 # parse logs, run every fixture, write the outputs
  python scripts/v2_gameplay_compare.py --from-fixtures # re-run the committed fixtures only (no raw logs needed)

Outputs: data/v2_gameplay_fixtures.json (self-contained fixtures + results; MTGO account names and
raw match ids replaced with deterministic aliases / hashes) and
data/v2_gameplay_comparison.json (coverage + every divergence with its classification).
Raw logs: mtg-meta-analyzer/data/raw/mtgo/<snapshot>/Match_GameLog_*.dat (gitignored, local only).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from calibration.v2_gameplay import DEFAULT_LOG_DIR, FIXTURES, extract_all      # noqa: E402
from calibration.v2_gameplay_exec import run_fixture                            # noqa: E402

SUMMARY = os.path.join(ROOT, "data", "v2_gameplay_comparison.json")
BURN_CARDS = ("Lava Spike", "Rift Bolt", "Goblin Guide", "Searing Blaze", "Roiling Vortex", "Skewer the Critics")

LEGAL = {   # the legal action(s) v2 must offer in the reconstructed pre-state
    "mulligan": "DeclareMulligan x N, then BottomCards with exactly N cards; DeclareKeep",
    "suspend": "Suspend(Rift Bolt) in its owner's main phase with {R}; at the next upkeep ChooseSuspendCast(True) "
               "and targets for the free cast",
    "prowess": "ProposeCast of the noncreature spell (Swiftspear on the battlefield)",
    "prowess_creature_spell": "ProposeCast of a creature spell (Swiftspear on the battlefield)",
    "goblin_guide_attack": "ChooseAttack(Goblin Guide, True)",
    "roiling_vortex": "none (triggered ability); PassPriority to reach the upkeep / a spell cast with no mana",
    "searing_blaze": "ChooseTargets((player P), (creature controlled by P)); pairs with another controller absent",
    "spectacle": "ProposeCast(Skewer, 'spectacle') only after an opponent lost life this turn; 'normal' with {2}{R}",
    "boros_charm": "ChooseMode(m) before targets; targets of the chosen mode only",
    "target_skullcrack": "ChooseTargets with players only", "target_lava_spike": "ChooseTargets with players only",
    "target_lightning_helix": "ChooseTargets with creatures and players",
    "target_lightning_bolt": "ChooseTargets with creatures and players",
    "fetch": "ActivateAbility(fetch land) with tap + 1 life + sacrifice",
    "play_draw_choice": "ChoosePlayDraw offered to the loser of the previous game (CR 103.1)",
}
RESULT = {   # the observable result v2 must reproduce
    "mulligan": "after N mulligans N cards go to the bottom; opening hand 7 - N",
    "suspend": "card exiled with one time counter, no stack; owner's next upkeep: suspend trigger -> counter "
               "removed -> cast trigger -> cast without paying its mana cost",
    "prowess": "exactly one prowess trigger per Swiftspear, above the spell",
    "prowess_creature_spell": "no prowess trigger",
    "goblin_guide_attack": "one reveal trigger per attacking Guide; reveals the defender's top card; a land goes to hand",
    "roiling_vortex": "one trigger at each player's upkeep dealing 1 to that player / a trigger on a spell cast with "
                      "no mana",
    "searing_blaze": "1 damage to each target, 3 with landfall (a land entered under the caster's control this turn)",
    "spectacle": "spectacle cost {R} accepted only under its condition",
    "boros_charm": "mode 0: 4 to a player; mode 1: indestructible for permanents you control; mode 2: double strike",
    "target_skullcrack": "players only", "target_lava_spike": "players only",
    "target_lightning_helix": "any target", "target_lightning_bolt": "any target",
    "fetch": "search for the named land types, put onto the battlefield, shuffle",
    "play_draw_choice": "the previous loser chooses",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", default=DEFAULT_LOG_DIR)
    ap.add_argument("--from-fixtures", action="store_true")
    args = ap.parse_args()
    if args.from_fixtures:
        fx = json.load(open(FIXTURES, encoding="utf-8"))
    else:
        fx = extract_all(args.logs)
    by_match = collections.defaultdict(set)
    for f in fx:
        for line in f["observed"]:
            for c in BURN_CARDS:
                if f"[{c}]" in line:
                    by_match[f["source"]["match"]].add(c)
    for f in fx:
        r = run_fixture(f)
        f["legal_actions_expected"] = LEGAL[f["mechanic"]]
        f["selected_action"] = f.get("action")
        f["expected_result"] = RESULT[f["mechanic"]]
        f["result"] = {k: v for k, v in r.items() if k != "trace"}
        f["substitutions"] = r.get("substitutions", f.get("substitutions", []))
        f["passed"] = r["status"] == "pass"
    json.dump(fx, open(FIXTURES, "w", encoding="utf-8"), indent=1)
    burn_matches = {f["source"]["match"] for f in fx if f["mechanic"] in
                    ("suspend", "goblin_guide_attack", "roiling_vortex", "searing_blaze", "spectacle",
                     "target_lava_spike")} | set(by_match)
    cov = collections.defaultdict(collections.Counter)
    burn_cov = collections.defaultdict(collections.Counter)
    for f in fx:
        st = f["result"]["status"]
        cov[f["mechanic"]][st] += 1
        if f["source"]["match"] in burn_matches:
            burn_cov[f["mechanic"]][st] += 1
    div = [{"id": f["id"], "mechanic": f["mechanic"], "status": f["result"]["status"],
            "classification": f["result"]["classification"], "detail": f["result"]["detail"],
            "observed": f["observed"]} for f in fx if not f["passed"]]
    unexplained = [d for d in div if d["classification"] in ("unexplained", "engine_rules_bug", "card_implementation_bug")]
    summary = {
        "fixtures": len(fx),
        "matches": len({f["source"]["match"] for f in fx}),
        "matches_with_burn_specific_events": len(burn_matches),
        "passed": sum(1 for f in fx if f["passed"]),
        "with_substitutions": sum(1 for f in fx if f["substitutions"]),
        "coverage_by_mechanic": {m: dict(c) for m, c in sorted(cov.items())},
        "burn_coverage_by_mechanic": {m: dict(c) for m, c in sorted(burn_cov.items())},
        "divergences": div,
        "divergence_classes": dict(collections.Counter(d["classification"] for d in div)),
        "unexplained_rules_divergences": len(unexplained),
        "gate": "PASS" if not unexplained else "FAIL",
    }
    json.dump(summary, open(SUMMARY, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "divergences"}, indent=1))


if __name__ == "__main__":
    main()
