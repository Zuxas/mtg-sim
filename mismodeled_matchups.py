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
    # ── Goryo's Reanimator consolidation (2026-07-02) ───────────────────────────
    # Replaces BOTH the old "goryos vengeance" INFLATED flag (sim 84-92 vs ~73)
    # and the old "grixis reanimator" INVERTED flag (66-card audit:stub cell).
    # Aliased below so every archetype name variant hits this record.
    "goryos reanimator": {
        "direction": "our WR DEFLATED vs anchors (Boros cell only one >10pp out of band; "
                     "from the Boros-centric gauntlet's POV that cell reads INFLATED-for-Boros)",
        "sim": "our WR vs Boros Energy 15.4% [12.5-18.8] / vs Izzet Affinity 26.6% "
               "[22.9-30.6] / vs Urzatron 37.6% [33.5-41.9] (n=500 each, seed=42, "
               "PYTHONHASHSEED=0, run_match_set mix_play_draw, 2026-07-02)",
        "truth": "matchup_matrix 2026-04-24 (STALE pre-ban; 'Esper Reanimator' rows -- this "
                 "archetype's April DB label per meta_bridge.py; verified 2026-07-02 no "
                 "fresher Modern rows exist): vs Boros 46% (n=352), vs Affinity 36% "
                 "(n=240), vs Eldrazi Tron 47% (n=66; colorless-shell proxy row for the "
                 "urzatron cell, same convention as the urzatron flag)",
        "why": "CONSOLIDATED CELL (2026-07-02): real modal June-2026 'Instant Reanimator' "
               "list (decks/goryos_reanimator_modern.txt, 5 first-place finishes) + "
               "hand-written GoryosReanimatorMatchAPL supersede the old goryos cell "
               "(never exiled the Goryo's body -- delayed trigger unmodeled -- and "
               "double-fired a flat draw-4 Atraxa ETB: its 84-92% was inflated mechanics "
               "on an April list) and the old grixis cell (June DB: 2 Grixis decks vs 41 "
               "Instant Reanimator -- the archetype IS this Esper shell). Affinity and "
               "Urzatron cells sit ~9.4pp low with overlapping Wilson bands. The Boros "
               "cell FAILS LOW at -30.6pp: goldfish kill median T8 (12.9% reanimate by "
               "T3, 27.9% by T4) vs paper T4-5, so the modeled clock loses the race to "
               "Boros's T4.3. Attribution is structural, shared with existing flags: "
               "1-land-per-turn mana model, Psychic Frog's combat-damage draw engine "
               "unmodeled, no own-turn instant window (FoN/Consign INERT by design -- no "
               "fake reactivity), and the combo-decks-not-sampled opponent-pressure "
               "class. Honest fidelity fixes (exile discipline, engine-owned ETBs, "
               "base-class blocking) moved the cell 8.0%->15.4%; NOT tuned toward "
               "anchors (forbidden). Trust the DIRECTION (real Boros cell ~even, we are "
               "a slight dog), not the 15%.",
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
        "direction": "INFLATED (kill now REACHABLE; residual = modeled clock too slow)",
        "sim": "~99.6% Boros / ~0.4% ruby [0.1-1.4] vs boros_energy; ~1.0% ruby [0.4-2.3] vs "
               "urzatron (n=500 each, seed=42, PYTHONHASHSEED=0, run_match_set mix_play_draw, "
               "established deck seat A, 2026-07-02). Was literally 0/500 vs both pre-fix.",
        "truth": "matchup_matrix 2026-04-24 (STALE pre-ban; verified 2026-07-02 that no fresher "
                 "Modern rows exist): Boros Energy vs Ruby Storm 50% (n=215) -> ruby ~50%; "
                 "Eldrazi Tron vs Ruby Storm 48% (n=46) -> ruby ~52% (colorless-shell proxy row, "
                 "same convention as the urzatron flag). Paper goldfish medians ~T3-4.",
        "why": "PAYOFF-REACHABILITY FIXED (2026-07-02 hand-audit, was BATCH I0): engine "
               "_wish_spell required gs._sideboard which NO runner populates -> Wish (3 main) "
               "was a silent no-op and the SB Grapeshot unreachable; now models the wishboard "
               "(1 Grapeshot/game at wish-cost + card-cost). RubyStormMatchAPL rewritten + "
               "hand-audited: Medallion-first sequencing (engine _COST_REDUCTIONS now covers "
               "the red shell), Ral cast + flip pings (old loop skipped ALL creatures), PiF "
               "flashback rebuy (goldfish-parity), sculpt-then-go-off with payoff strictly "
               "last (storm arithmetic verified: copies = prior spells + 1). Goldfish moved "
               "11.5%->69.2% wins by T12, storm-majority kills 1/1000->603/1000, Grapeshot "
               "median 3 copies/shot. BUT kill-turn median is still T10 vs paper T3-4 (mana "
               "model 1-land/turn + flex-fetch, impulse-draw proxies, Pyromancer Ascension / "
               "Artist's Talent unmodeled, Ral eats match-path removal), so vs a T4.3 Boros "
               "clock the cell stays ~-49.6pp off anchor. NOT tuned toward the anchor "
               "(forbidden). Trust the DIRECTION (real cell ~even), not the ~99.6%. "
               "~4.1% of the modeled field.",
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
    "urzatron": {
        "direction": "INFLATED (all 3 calibration cells; Amulet cell INVERTED)",
        "sim": "vs Boros Energy 56.4% [52.0-60.7] / vs Affinity 58.4% [54.0-62.6] / "
               "vs Amulet Titan 85.6% [82.3-88.4] (n=500 each, seed=42, PYTHONHASHSEED=0, "
               "run_match_set mix_play_draw, 2026-07-02)",
        "truth": "matchup_matrix 2026-04-24 (STALE pre-ban; Eldrazi Tron rows -- same "
                 "colorless shell by April; matches table has no June-2026 Modern rounds): "
                 "vs Boros 42% (n=168), vs Affinity 38% (n=116), vs Amulet 19% (n=119)",
        "why": "Calibration gate for the new hand-written UrzatronMatchAPL (Mono-Green Tron "
               "meta cell, 2026-07-02). NOT tuned toward the anchors (forbidden). Attribution "
               "is structural, shared with existing flags: (a) opponent LAND HATE (Boseiju/"
               "Ghost Quarter/Demolition Field-class Tron-land destruction -- the spine of "
               "every real anti-Tron plan) is entirely unmodeled, inflating ALL Tron cells "
               "(this also means the sibling eldrazitron cells share this direction); "
               "(b) Amulet Titan under-kills in the played-out cell (combo-decks-not-sampled "
               "class; anchor says Tron is a 19% dog, sim says 86% favored -> INVERTED, do "
               "not trust this cell at all); (c) Affinity board under-development (see "
               "'izzet affinity' flag). Trust the DIRECTION (real Tron is roughly even-to-dog "
               "vs Boros/Affinity and a heavy dog vs Amulet), not the sim numbers. Anchors "
               "are themselves pre-ban/stale -- re-anchor when post-ban Modern rounds land.",
    },
    # ── audit:stub Standard decks feeding current gauntlet fields ──────────────
    # (2026-07-01 handover / mismodel-coverage lint: same silent-inflation class as
    # belcher/neobrand in BATCH I0 -- stub decklists fill field rows with NO
    # down-weight warning. Direction-only cells; do not trust the numbers.)
    "azorius omniscience": {
        "direction": "INFLATED / STUB (decklist is a guess)",
        "sim": "whatever the PT-SOS swiss row says (sim_pt_sos_swiss.py field)",
        "truth": "no primer cell (unknown)",
        "why": "mismodel-coverage flag (2026-07-01 handover). decks/azorius_omniscience_standard.txt "
               "is an audit:stub ('deck list pending; Azorius Omniscience combo' -- approximate "
               "build), so every cell it feeds is built on a guessed 75, and the combo kill is "
               "likely under-assembled like the other played-out combo cells. Fix type = author "
               "the real list (decklist-stub cluster). Direction-only cell.",
    },
    "esper raffine": {
        "direction": "INFLATED / STUB (pre-Strixhaven approximate shell)",
        "sim": "whatever the swiss-gauntlet row says (rc_swiss_gauntlet.py / rc_underdog_scout.py fields)",
        "truth": "no primer cell (unknown)",
        "why": "mismodel-coverage flag (2026-07-01 handover). decks/esper_raffine_standard.txt is an "
               "audit:stub ('pre-Strixhaven Esper Raffine baseline -- real list pending post-PT "
               "data'), so its field rows are approximate-build cells. NOTE the registry also "
               "routes dimiraggro/espermidrange through EsperRaffineMatchAPL, widening the blast "
               "radius of this stub. Fix type = refresh from post-PT data. Direction-only cell.",
    },
    "izzet lessons": {
        "direction": "MILDLY OFF / STUB (real PT list, 14-card sideboard)",
        "sim": "whatever the gauntlet rows say (rc_ptsos_gauntlet.py / rc_dimir_gauntlet.py / sim_pt_sos_swiss.py fields)",
        "truth": "PT WR 49.44% overall (real-world anchor exists; see deck file header)",
        "why": "mismodel-coverage flag (2026-07-01 handover). decks/izzet_lesson_standard.txt is the "
               "real Rui Zhang PT SOS list but carries audit:stub for a 14-card sideboard (PT DB "
               "record missing 1 SB slot), so BO3 post-board cells run a card short. Mildest stub "
               "in this batch: G1 cells are a real 60. Fix type = recover the missing SB slot. "
               "Covers both registry keys (izzetlesson + izzetlessons dup).",
    },
    "jeskai oculus": {
        "direction": "INFLATED / STUB (decklist is a guess)",
        "sim": "whatever the swiss-gauntlet row says (rc_swiss_gauntlet.py field)",
        "truth": "no primer cell (unknown)",
        "why": "mismodel-coverage flag (2026-07-01 handover). decks/jeskai_oculus_standard.txt is an "
               "audit:stub ('deck list pending; approximate Jeskai Oculus post-Strixhaven'), so its "
               "field row is an approximate-build cell. Fix type = author the real list "
               "(decklist-stub cluster). Direction-only cell.",
    },
    "sultai reanimator": {
        "direction": "INFLATED / STUB (decklist is a guess; reanimator kill likely under-assembles)",
        "sim": "whatever the gauntlet rows say (rc_dimir_gauntlet.py + hill-climb/calibrate fields)",
        "truth": "no primer cell (unknown; 10.1% of PT Lorwyn Eclipsed field, so this cell MATTERS)",
        "why": "mismodel-coverage flag (2026-07-01 handover). decks/sultai_reanimator_standard.txt is "
               "an audit:stub ('deck list pending; Sultai Reanimator'), and reanimator kill channels "
               "are exactly the class run_match under-assembles (cf. grixis reanimator above), so "
               "expect the same INFLATED-for-us direction on top of the guessed 75. Widely used "
               "(domainramp also proxies to this APL). Fix type = author the real list. "
               "Direction-only cell.",
    },
}


# Aliases: the Mono-Green Tron meta cell must hit the urzatron flag whichever
# label a gauntlet feeds lookup() ("Mono-Green Tron", "Green Tron", registry key
# "monogreentron"/"greentron") -- same silent-miss class as the BATCH I0
# apostrophe/underscore fixes below.
MISMODELED_MATCHUPS["mono green tron"] = MISMODELED_MATCHUPS["urzatron"]
MISMODELED_MATCHUPS["green tron"] = MISMODELED_MATCHUPS["urzatron"]

# Goryo's Reanimator name variants (2026-07-02 consolidation): every DB label /
# registry key for the archetype must hit the consolidated record, including the
# two RETIRED flag keys ("goryos vengeance", "grixis reanimator") so existing
# gauntlet lookups keep warning.
for _alias in ("goryos vengeance", "grixis reanimator", "instant reanimator",
               "esper reanimator", "esper goryo"):
    MISMODELED_MATCHUPS[_alias] = MISMODELED_MATCHUPS["goryos reanimator"]


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
