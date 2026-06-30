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
        "direction": "INVERTED",
        "sim": "~75% favored",
        "truth": "~38% (we are the DOG)",
        "why": "combo under-assembles via the played-out APL; sim cannot model our (limited) "
               "graveyard interaction. Sampler alternative lands ~24.5% (too pessimistic). Truth is between.",
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
        "sim": "~85-88%",
        "truth": "~44%",
        "why": "Affinity's artifact clock / Galvanic Blast reach / Thoughtcast card-advantage are "
               "undermodeled, so we beat it far more often in sim than in reality. (Same gap behind the "
               "stale 63.5% 'Modern lock'.)",
    },
    "yawgmoth": {
        "direction": "DEFLATED (combat over-credited)",
        "sim": "~49% (combo NOW assembles 9.8%/game and kills)",
        "truth": "spec band [55,80] -- we should be favored",
        "why": "The Agatha's-Cauldron/Walking-Ballista combo was REPAIRED 2026-06-30 (handoff #2): the "
               "old DRAINS/UNDYING constants named Blood Artist/Zulaport/Geralf's Messenger -- none in "
               "decks/yawgmoth_modern.txt -- so the combo fired 0/50. It now assembles (Yawgmoth + 2 "
               "undying + Cauldron + Ballista) at ~9.8%/game and its damage is rerouted through "
               "gs.damage_dealt + WANTS_BURN so it reaches the match life total. BUT the cell FAILS LOW: "
               "our no-combo race_baseline is only ~53.8% because the APL plays as an over-strong generic "
               "creature deck (yawgmoth wins ~46%/game on combat with NO combo), so the now-correct combo "
               "only DROPS our WR (53.8% -> 49.0%), it cannot raise it into [55,80]. The binding "
               "constraint is the combat model, not assembly -- re-modeling yawgmoth's beatdown is OUT OF "
               "SCOPE here, and tuning assembly frequency to hit the band is forbidden (Stop condition 2). "
               "Trust the DIRECTION (we are favored), not the 49%.",
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
