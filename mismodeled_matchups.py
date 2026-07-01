"""
mismodeled_matchups.py -- registry of matchups the sim is KNOWN to model wrong.

Why this exists: the gauntlet (engine/match_runner.py::run_match) plays combo /
fast-interactive opponents out with hand-coded APLs that under-assemble their kill,
and the engine does not model OUR interaction (removal / graveyard hate) against
them. The pure-race ComboKillSampler alternative was prototyped + measured 2026-06-29
and REJECTED (it floors those cells the other way). So several gauntlet cells are
quantitatively wrong in a KNOWN direction. Consumers (deck-selection EV, sideboard
planning, the DECK ANALYSIS PROTOCOL context block) MUST down-weight these cells.

This is the cheap-and-honest mitigation: do NOT trust the listed cells as calibrated
win rates; trust the DIRECTION/severity noted here. See harness IMPERFECTIONS.md:
  - combo-decks-not-sampled-in-gauntlet-run_match
  - grixis-reanimator-match-apl-crashes-every-turn
  - locked-modern-boros-affinity-baseline-stale-63.5
and harness/knowledge/tech/boros-energy-postban-validation-2026-06-29.md.

NOTE: these are documentation of a known limitation, NOT calibration targets. Do
NOT reverse-fit any model to the 'truth' figures (they are real-world primer data,
the sim divergence is structural).
"""

# Keyed by normalized opponent name/archetype (lowercase, hyphens->spaces).
# direction: how the SIM errs relative to real-world truth.
MISMODELED_MATCHUPS = {
    "grixis reanimator": {
        "direction": "INVERTED (improved, still flagged, assembly ~32% production / ~35% keep-mode)",
        "sim": "~57% favored (56.6% production keep-slice; was ~55% crude-both)",
        "truth": "~38% (we are the DOG)",
        "why": "handoff #2 grixis cell (2026-06-30) built the intrinsic-fragility threat model + "
               "turned the interaction layer ON. The reanimated Archon's RECURRING attack trigger "
               "(sacrifice + discard + 3 life drain) now fires in main_phase_match; when the Archon "
               "comes online grixis wins ~82% (the named mechanisms work). Our interaction is honest "
               "but NON-LOAD-BEARING (answer_combo fires ~1-3/500 G1: Boros's cheap burn can't kill a "
               "6-toughness body, no maindeck GY-hate). STILL FLAGGED per Stop condition 2. "
               "MULLIGAN KEEP-ROUTING RE-MEASURE (2026-07-01, PYTHONHASHSEED=0, seed=42, n=500): the "
               "'crude mulligan starves match assembly' premise is LARGELY DISPROVEN. Paired isolation "
               "(boros held keep, grixis crude->keep) moves grixis Archon-online only 32.4%->35.4% "
               "(+3.0pp, ~1 SE) and our WR 55.0%->55.0% (flat); routing grixis through its OWN combo-aware "
               "keep() does NOT lift assembly to Gate-2's 42% nor near the goldfish ~56%. The 32%-match-vs-"
               "56%-goldfish gap was a MISATTRIBUTION: goldfish-vs-match conflates the mulligan with the "
               "entire opponent-pressure effect; the isolated mulligan contribution is only ~+3pp, so the "
               "residual gap is dominated by (c) LEGITIMATE boros pressure (racing/removing before assembly, "
               "part of the matchup) + (b) the 66-card audit:stub decklist -- NOT the crude mulligan. In "
               "SHIPPED PRODUCTION grixis is seat B and NOT in _KEEP_ROUTED_APLS, so it stays crude: "
               "assembly 32.4%, our WR 56.6% (the +1.6pp over crude-both 55.0% is boros's OWN seat-A keep, "
               "not any grixis-assembly change). Cell stays INVERTED + flagged; NOT tuned into band "
               "(forbidden). Trust the DIRECTION (improving toward dog), not the ~55-57%.",
    },
    "goryos vengeance": {
        "direction": "INFLATED",
        "sim": "~84-92%",
        "truth": "~73% (still favored)",
        "why": "combo under-fires; sign is correct but optimistic. Real edge comes from removal on the "
               "single fragile threat, which the gauntlet only partly captures.",
    },
    "living end": {
        "direction": "INFLATED",
        "sim": "~96%",
        "truth": "no primer cell (unknown)",
        "why": "cascade under-fires in the played-out APL; almost certainly not 96%.",
    },
    "gruul broodscale": {
        "direction": "INFLATED / STUB",
        "sim": "~89%",
        "truth": "~55%",
        "why": "the Broodscale APL is a SYNTHETIC creature-deck stub that does not model the infinite "
               "combo at all -- the cell only fills the field row.",
    },
    "izzet affinity": {
        "direction": "INFLATED",
        "sim": "~81% (boros_energy_lowcurve seat A vs izzet_affinity seat B; run_match n=100, "
               "PYTHONHASHSEED=0, seed=42+i, seat-alternating on_play)",
        "truth": "~44% (direction only -- no empirical anchor; no post-ban Modern DB data)",
        "why": "Affinity's APL never DEVELOPS A BOARD: the Urza's Saga chapter/Construct engine is "
               "entirely unimplemented (0 Constructs / 100 games; peak attacking power median ~1.0, "
               "~46% of games have zero attacking power ever), so we beat it far more often in sim "
               "than in reality. Trust the INFLATED direction, not the number. Arc #3 "
               "(harness/specs/2026-07-01-affinity-offense-rebaseline.md) was attempted 2026-07-01 but "
               "landed NO fix (implementer null; apl/affinity_match.py byte-identical to pre-spec HEAD), "
               "so the mechanism did not move and this cell stays flagged at its pre-fix ~81% baseline.",
    },
    "yawgmoth": {
        "direction": "DEFLATED (combat over-credited; mulligan does NOT unstarve assembly)",
        "sim": "~50% production (combo assembles ~9.4%/game); was 49% crude-both",
        "truth": "spec band [55,80] -- we should be favored",
        "why": "The Agatha's-Cauldron/Walking-Ballista combo was REPAIRED 2026-06-30 (handoff #2): the "
               "old DRAINS/UNDYING constants named cards not in decks/yawgmoth_modern.txt, so the combo "
               "fired 0/50. It now assembles (Yawgmoth + 2 undying + Cauldron + Ballista) at ~9.4%/game "
               "and its damage is rerouted through gs.damage_dealt + WANTS_BURN to the match life total. "
               "The cell FAILS LOW: the APL plays as an over-strong generic creature deck (yawgmoth wins "
               "~46%/game on combat with NO combo), so the now-correct combo only DROPS our WR, it cannot "
               "raise it into [55,80]. MULLIGAN KEEP-ROUTING RE-MEASURE (2026-07-01, PYTHONHASHSEED=0, "
               "seed=42, n=500): keep-routing does NOT raise yawgmoth assembly toward its goldfish rate -- "
               "it LOWERS it. Routing yawgmoth through its own keep() (crude-both->keep-both) moves combo "
               "assembly 9.8%->6.8% (DOWN) because the keep mulls away resources for its 5-piece combo. "
               "Our keep-mode WR does rise 49.0%->54.6%, but ONLY because yawgmoth mulligans into weaker "
               "boards (less combat pressure) -- confirming the binding constraint is the OVER-CREDITED "
               "COMBAT MODEL, not assembly (spec Gate 2 stop-trigger 'P_assemble does not rise' fired). "
               "In SHIPPED PRODUCTION yawgmoth is seat B and NOT in _KEEP_ROUTED_APLS, so it stays crude: "
               "assembly 9.4%, our WR 50.0% -- effectively unchanged. Re-modeling yawgmoth's beatdown is "
               "OUT OF SCOPE; tuning assembly to hit the band is forbidden (Stop condition 2). Trust the "
               "DIRECTION (we are favored), not the ~50%.",
    },
}


def _norm(name: str) -> str:
    return (name or "").lower().replace("-", " ").strip()


def lookup(name: str):
    """Return the mismodel record for an opponent name/key, or None."""
    key = _norm(name)
    for k, v in MISMODELED_MATCHUPS.items():
        kn = k.replace(" ", "")
        if kn == key.replace(" ", "") or k in key or key in k:
            return v
    return None


def mismodel_flag(name: str) -> str:
    """Inline annotation for a gauntlet matchup row, or '' if not mismodeled.
    e.g. '  [!MISMODEL INVERTED: sim ~75% favored vs truth ~38% (we are the DOG)]'"""
    rec = lookup(name)
    if not rec:
        return ""
    return f"  [!MISMODEL {rec['direction']}: sim {rec['sim']} vs truth {rec['truth']}]"


def legend() -> str:
    """A printable legend block listing all known-mismodeled cells. Append below
    any gauntlet table (esp. the full-field matrix where inline flags don't fit)."""
    lines = ["", "KNOWN MISMODELED MATCHUPS (do NOT trust these cells as calibrated WR -- trust the direction):"]
    for k, v in MISMODELED_MATCHUPS.items():
        lines.append(f"  - {k}: {v['direction']} (sim {v['sim']} vs truth {v['truth']}) -- {v['why']}")
    lines.append("  See harness IMPERFECTIONS.md (combo-decks-not-sampled-in-gauntlet-run_match) for the full analysis.")
    return "\n".join(lines)
