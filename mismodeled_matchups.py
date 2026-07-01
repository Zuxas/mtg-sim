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
    "belcher": {
        "direction": "INFLATED / STUB (silent until 2026-07-01 -- worse than flagged cells)",
        "sim": "~100% Boros (belcher effectively never wins the played-out cell)",
        "truth": "no primer cell (unknown; certainly not ~0% for belcher)",
        "why": "BATCH I0 honesty flag (combo spec Amendment 2026-07-01). The belcher decklist is a "
               "64-card audit:stub and the played-out APL under-assembles the Charbelcher kill, so "
               "the row fed false ~100%-Boros wins across ~3.5% of the modeled field with NO "
               "down-weight warning. Fix type = author a real 60 (decklist-stub cluster). "
               "Direction-only cell; do not trust the number.",
    },
    "neobrand": {
        "direction": "INFLATED / STUB (silent until 2026-07-01 -- worse than flagged cells)",
        "sim": "~100% Boros (neobrand effectively never wins the played-out cell)",
        "truth": "no primer cell (unknown; certainly not ~0% for neobrand)",
        "why": "BATCH I0 honesty flag (combo spec Amendment 2026-07-01). Griselbrand kill channel "
               "is unmodeled (Griselbrand draws score no clock -- see GRIS-SPIKE batch), so the "
               "row fed false ~100%-Boros wins across ~2.0% of the modeled field with NO warning. "
               "Fix type = APL kill-line (APL-stub cluster) + GRIS-SPIKE. Direction-only cell.",
    },
    "temur crashcade": {
        "direction": "INFLATED",
        "sim": "~96% Boros",
        "truth": "no primer cell (unknown; flag-forever split B = direction-only)",
        "why": "BATCH I0 honesty flag (combo spec Amendment 2026-07-01). Cascade fires at sorcery "
               "speed in the played-out APL; the instant-speed end_step seam (BATCH A, shared with "
               "living_end) is unbuilt, so the cascade payload under-fires. ~3.4% of the modeled "
               "field. Direction-only cell.",
    },
    "ruby storm": {
        "direction": "INFLATED (payoff-reachability, NOT the damage channel)",
        "sim": "~100% Boros (ruby_storm wins 0/50)",
        "truth": "no primer cell (unknown; certainly not 0% for storm)",
        "why": "BATCH I0 honesty flag (combo spec Amendment 2026-07-01). The old IMPERFECTION "
               "(ruby-storm-fires-but-never-closes -> WANTS_STORM/damage_dealt path) is "
               "SUPERSEDED/WRONG: WANTS_STORM is already True and mp1 damage IS synced "
               "(Component 2 Site 1 is a no-op for it, baseline 496 byte-identical). Real cause = "
               "payoff REACHABILITY: Grapeshot is Wish/SB-gated so the engine never reaches the "
               "kill (Step-2.0 Stop-condition-4 re-scope). ~4.1% of the modeled field. "
               "Direction-only cell.",
    },
    "izzet affinity": {
        "direction": "INFLATED (mechanism moved arc #3, cell still OUT OF BAND -- trust direction)",
        "sim": "~76% Boros / ~24% Affinity POST-FIX (boros_energy_lowcurve seat A vs izzet_affinity "
               "seat B; run_match, seat-alternating on_play, seed=42+i, PYTHONHASHSEED=0, global RNG "
               "pinned, n=300). Down from ~85.7% Boros PRE-FIX under the SAME pin (-9.7pp). NOTE: the "
               "legacy ~81% was an n=100 non-global-pinned figure -- use the pinned 85.7->76.0 for the "
               "apples-to-apples move; do not compare 81 vs 76.",
        "truth": "~44% (direction only -- no empirical anchor; no post-ban Modern DB data)",
        "why": "Affinity's APL historically never DEVELOPED A BOARD (Urza's Saga chapter/Construct "
               "engine unimplemented; 0 Constructs / 100 games). Arc #3 "
               "(harness/specs/2026-07-01-affinity-offense-rebaseline.md, mtg-sim commit ae9cb12) "
               "IMPLEMENTED the Urza's Saga chapter/Construct engine, oracle-faithful (0/0 Construct, "
               "P/T = live artifact count recomputed each main phase, summoning-sick, {2},{T} paid from "
               "an honest pool with the Saga's own {C} forgone, Saga sacrificed at chapter III) + a "
               "Thoughtcast card-advantage branch + Munitions WANTS_BURN fidelity + honest Mox-metalcraft "
               "{C} mana routing. MECHANISM MOVED, NOT TUNED: Constructs 0->~24% present, peak attacking "
               "board power median 0->1 / mean 2.94->4.53, %games-zero-attacking-power-ever 53->43, "
               "kill-turn-when-Aff-wins median 6->5; all THREE Boros builds fall comparably (standard "
               "-13.5, lowcurve -9.5, variant_jermey -10.0 = a genuine clock, not a per-cell constant). "
               "But the cell did NOT reach the ~44-56 band and STAYS INFLATED (overall verdict PARTIAL): "
               "the faithful clock is present in only ~24% of games (early-Saga/tight-mana -- the honest "
               "{2},{T} gate that forgoes the Saga's own {C} was deliberately NOT relaxed to inflate "
               "presence), so the board-development thresholds (median>=3, %zero<20%) are only partially "
               "met. The residual above the band is EXPECTED and is attributed to the mana model / "
               "opponent overmodel, NOT tuned away (Aff 24% << 56%, no overshoot; no cell hand-edited). "
               "The broader field lift is substantially the honest Mox-mana routing (present every game), "
               "not the construct (present ~24%). Trust the INFLATED DIRECTION, not the number; no "
               "reverse-fit.",
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
    # strip apostrophes (straight + curly) so "Goryo's Vengeance" matches the
    # apostrophe-less stored key "goryos vengeance" (else the flag is silently missed);
    # underscores -> spaces so deck keys like "temur_crashcade" match "temur crashcade"
    # (same silent-miss class, found during BATCH I0 verification 2026-07-01)
    return (name or "").lower().replace("-", " ").replace("_", " ").replace("'", "").replace("’", "").strip()


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
