#!/usr/bin/env python3
"""arl_profile.py -- Archetype Capability Profile builder for the ARL loop.

Spec: harness/specs/2026-06-26-archetype-capability-profiles.md

Builds a durable, explicit "what this deck is trying to do AND what our engine
can/can't model" brief for an archetype BEFORE an APL is generated or its
gauntlet FWR is trusted. Two artifacts per deck are written to
mtg-sim/docs/archetype_profiles/:
    <slug>.json   machine-readable profile (the schema the loop's gate consumes)
    <slug>.md     human-readable sibling

The CRITICAL, load-bearing part is the deterministic engine_fidelity block. It
is computed with NO LLM so the data-quality gate downstream is reliable even
with Ollama down. The prose fields (win_conditions / sequencing_rules) get a
best-effort, lazily-imported, fully-guarded LLM enrichment pass -- its absence
or failure NEVER changes the engine_fidelity verdict.

------------------------------------------------------------------------------
DETERMINISTIC FIDELITY DETECTION
------------------------------------------------------------------------------
Card oracle text + type_line + keywords are resolved from this repo's local
card DB (engine.card_db.CardDB -> data/rules_reference/scryfall_oracle_cards.json).
Detection runs over the MAINBOARD only (the deck's primary plan); sideboard
cards do not move the gate.

Mechanics detected (counts are by QUANTITY / number of copies, not distinct
names -- copy density reflects how central the plan is):
  * counterspell_on_stack    -- oracle text contains the contiguous substring
                                 "counter target" (matches Counterspell, Force
                                 of Negation, Spell Snare; the space prevents
                                 "+1/+1 counter on target ..." false matches).
  * planeswalker_loyalty      -- FRONT-FACE type_line contains "Planeswalker".
                                 Front-face only: a creature that transforms
                                 into a planeswalker (e.g. Ajani, Nacatl Pariah)
                                 is NOT a loyalty deck and must not trip this.
  * warp                      -- "Warp" in the card's keywords list, or the
                                 word "Warp" appears in oracle text (keyword).
  * instant_speed_combat_trick-- an Instant whose text grants +X/+X or
                                 protection (conservative; informational only).

hidden_information is NOT auto-flagged for every deck (it is universal; flagging
all decks would make everything unmodelable). It is flagged ONLY when
counterspell-style interaction is ALSO a real plan (>= 2 counters), i.e. when
holding up reactive mana / representing hidden answers is core to the deck.

------------------------------------------------------------------------------
CONFIDENCE MAPPING (MVP)
------------------------------------------------------------------------------
Each mechanic maps to a severity; the profile's confidence is the WORST
severity among the mechanics that tripped. Order: high < medium < low <
unmodelable.

  counterspell_on_stack copies:
        >= 4   -> unmodelable   (deck's PRIMARY plan is countering on the stack)
        2 - 3  -> low           (counters are a real plan, but not the whole deck)
        1      -> medium        (minor interaction; a modeled primary plan remains)
        0      -> (no trip)
  warp:
        any core warp card present -> unmodelable (warp is wholly unmodeled)
  planeswalker_loyalty copies:
        >= 3   -> low           (planeswalker-centric; loyalty not tracked)
        < 3    -> (no trip; incidental planeswalkers don't downgrade)
  hidden_information:
        flagged (severity == the counter severity) only when counters >= 2.
  instant_speed_combat_trick:
        informational only -- never downgrades confidence.

  high        = none of the above tripped (aggro / ramp / combat decks our
                engine models well).

blocking_imperfections = the mapped IMPERFECTION ids (read from
data/engine_fidelity_map.json -- single source of truth) for every mechanic
that tripped at severity medium or worse. For a 'high' deck this is [].

------------------------------------------------------------------------------
PUBLIC API
------------------------------------------------------------------------------
    build_profile(deck_file, format_name="modern") -> dict
        Computes the profile, writes <slug>.json and <slug>.md, returns the dict.

CLI:
    python arl_profile.py <deck_file> [format]
"""

import os
import re
import sys
import json

# --- Mandatory cross-repo / in-repo sys.path setup ---------------------------
SIM_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HARNESS_SCRIPTS = os.path.abspath(
    os.path.join(SIM_ROOT, "..", "harness", "agents", "scripts")
)
for _p in (SIM_ROOT, HARNESS_SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

PROFILES_DIR = os.path.join(SIM_ROOT, "docs", "archetype_profiles")
FIDELITY_MAP_PATH = os.path.join(SIM_ROOT, "data", "engine_fidelity_map.json")

# Known format suffixes for filename-based detection (mirrors arl_generate_apl).
KNOWN_FORMATS = {
    "standard", "modern", "pioneer", "legacy", "vintage", "pauper",
    "commander", "historic", "explorer", "alchemy", "timeless", "pchampions",
}

# Severity ladder (low value == more confident).
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "unmodelable": 3}


# ---------------------------------------------------------------------------
# Naming / deck-file helpers (mirror arl_generate_apl conventions)
# ---------------------------------------------------------------------------

def _safe_slug(deck_name):
    """Mirror auto_pipeline._safe_slug so output paths match the pipeline."""
    return (deck_name.lower()
            .replace(" ", "_").replace("-", "_").replace("'", ""))


def _derive_deck_meta(deck_file):
    """Return (deck_name, detected_format_or_None) from a deck file.

    Prefers a canonical name embedded in an
    '// audit:auto-generated:<name>:<date>' header; otherwise derives from the
    filename, stripping a trailing known-format token.
    """
    deck_name = None
    fmt = None
    try:
        with open(deck_file, "r", encoding="utf-8") as fh:
            for _ in range(8):
                line = fh.readline()
                if not line:
                    break
                m = re.search(r"audit:auto-generated:([^:]+):", line)
                if m:
                    deck_name = m.group(1).strip()
                    break
    except OSError:
        pass

    stem = os.path.splitext(os.path.basename(deck_file))[0]
    tokens = stem.split("_")
    if tokens and tokens[-1].lower() in KNOWN_FORMATS:
        fmt = tokens[-1].lower()
        tokens = tokens[:-1]

    if not deck_name:
        deck_name = " ".join(t.capitalize() for t in tokens) if tokens else stem
    return deck_name, fmt


def _parse_decklist(deck_file):
    """Parse a deck file into (mainboard, sideboard) lists of (qty, name).

    Comments (// or #) and blank lines are skipped. The 'Sideboard' / 'SB:'
    marker switches accumulation to the sideboard list.
    """
    main, side = [], []
    target = main
    try:
        with open(deck_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                # A sideboard delimiter may itself be a comment ("// Sideboard").
                # Strip leading comment markers, then test for the delimiter
                # BEFORE discarding comment lines.
                bare = line.lstrip("/# ").strip().lower()
                if bare in ("sideboard", "sb:", "sideboard:"):
                    target = side
                    continue
                if line.startswith("//") or line.startswith("#"):
                    continue
                m = re.match(r"^(\d+)x?\s+(.+)$", line)
                if m:
                    target.append((int(m.group(1)), m.group(2).strip()))
    except OSError:
        pass
    return main, side


# ---------------------------------------------------------------------------
# Card-data access (local DB only -- no network, no LLM)
# ---------------------------------------------------------------------------

def _open_card_db():
    """Return a CardDB instance, or None if the DB can't be loaded.

    Guarded so the deterministic gate degrades gracefully rather than crashing
    if the oracle JSON is missing.
    """
    try:
        from engine.card_db import CardDB
        return CardDB()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("[arl_profile] CardDB unavailable: %s\n" % exc)
        return None


def _front_type_line(db, name):
    """Type line of the FRONT face only.

    The DB stores transform/MDFC cards with a combined 'Front // Back'
    type_line. For planeswalker detection we only care about what you cast
    (the front), so a creature that flips into a planeswalker does not count.
    """
    tl = db.type_line(name) if db else ""
    if "//" in tl:
        return tl.split("//", 1)[0].strip()
    return tl


# ---------------------------------------------------------------------------
# Deterministic engine-fidelity assessment (THE GATE)
# ---------------------------------------------------------------------------

# Conservative combat-trick signature: an instant that grants +X/+X or
# protection. Used for the informational instant_speed_combat_trick flag.
_PLUS_X_RE = re.compile(r"\+\d+/\+\d+")
_PROTECTION_RE = re.compile(r"\bprotection\b", re.IGNORECASE)
# Keyword "Warp" as printed on cards (capital W, word boundary).
_WARP_RE = re.compile(r"\bWarp\b")
# Keyword "Storm" as printed. Detection uses the keyword LIST as the primary signal;
# this oracle regex is the fallback. Scans oracle/keywords ONLY (never the card name)
# so "Storm Slayer"-type names don't trip; residual risk is an oracle quoting "Storm"
# (validated: Grapeshot trips; Ral / Wrenn's Resolve / rituals do not).
_STORM_RE = re.compile(r"\bStorm\b")


def _load_fidelity_map():
    """Load mechanic -> imperfection id map (single source of truth)."""
    try:
        with open(FIDELITY_MAP_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError) as exc:
        sys.stderr.write("[arl_profile] fidelity map unavailable: %s\n" % exc)
    return {}


def _detect_mechanics(db, mainboard):
    """Scan the mainboard and return raw mechanic counts + supporting evidence.

    Counts are by QUANTITY (copies). Evidence lists distinct card names so the
    profile/markdown can show exactly what tripped each mechanic.
    """
    counts = {
        "counterspell_on_stack": 0,
        "planeswalker_loyalty": 0,
        "warp": 0,
        "storm": 0,
        "instant_speed_combat_trick": 0,
    }
    evidence = {k: [] for k in counts}
    unresolved = []

    for qty, name in mainboard:
        if db is None:
            unresolved.append(name)
            continue
        card = db.get(name)
        if card is None:
            unresolved.append(name)
            continue

        oracle = db.oracle_text(name) or ""
        oracle_low = oracle.lower()
        front_type = _front_type_line(db, name)
        try:
            keywords = [str(k).lower() for k in db.keywords(name)]
        except Exception:  # noqa: BLE001
            keywords = []

        # counterspell_on_stack: contiguous "counter target" substring.
        if "counter target" in oracle_low:
            counts["counterspell_on_stack"] += qty
            evidence["counterspell_on_stack"].append(name)

        # planeswalker_loyalty: FRONT-face type only.
        if "planeswalker" in front_type.lower():
            counts["planeswalker_loyalty"] += qty
            evidence["planeswalker_loyalty"].append(name)

        # warp: keyword list or printed "Warp" keyword in oracle text.
        if "warp" in keywords or _WARP_RE.search(oracle):
            counts["warp"] += qty
            evidence["warp"].append(name)

        # storm: keyword list (primary) or printed "Storm" keyword in oracle (fallback).
        if "storm" in keywords or _STORM_RE.search(oracle):
            counts["storm"] += qty
            evidence["storm"].append(name)

        # instant_speed_combat_trick: instant granting +X/+X or protection.
        if "instant" in front_type.lower() and (
                _PLUS_X_RE.search(oracle) or _PROTECTION_RE.search(oracle)):
            counts["instant_speed_combat_trick"] += qty
            evidence["instant_speed_combat_trick"].append(name)

    return counts, evidence, unresolved


def _severity_for_counts(counts, modeled=frozenset()):
    """Map raw mechanic counts to per-mechanic severities (the MVP rules).

    Returns dict mechanic -> severity in {high, medium, low, unmodelable}.
    'high' means the mechanic did not trip anything.

    `modeled` is the set of mechanics the deck's match-APL opts into AND that have
    an engine proof (see _apl_modeled_capabilities). A modeled mechanic is credited
    as 'high' (the engine handles it) instead of tripping. Default empty set ->
    byte-identical to the prior static behavior for every existing caller.
    """
    sev = {}

    c = counts["counterspell_on_stack"]
    if "counterspell_on_stack" in modeled:
        sev["counterspell_on_stack"] = "high"
    elif c >= 4:
        sev["counterspell_on_stack"] = "unmodelable"
    elif c >= 2:
        sev["counterspell_on_stack"] = "low"
    elif c == 1:
        sev["counterspell_on_stack"] = "medium"
    else:
        sev["counterspell_on_stack"] = "high"

    if "warp" in modeled:
        sev["warp"] = "high"
    else:
        sev["warp"] = "unmodelable" if counts["warp"] >= 1 else "high"

    # storm: binary-central like warp (any storm-keyword payoff => the combo turn IS the
    # plan), NOT density-tiered like counterspells. Credited high only when the deck's
    # match-APL opts into WANTS_STORM AND an r3- proof exists (_apl_modeled_capabilities).
    if "storm" in modeled:
        sev["storm"] = "high"
    else:
        sev["storm"] = "unmodelable" if counts["storm"] >= 1 else "high"

    sev["planeswalker_loyalty"] = (
        "low" if counts["planeswalker_loyalty"] >= 3 else "high")

    # hidden_information: credited high when a deck's match-APL opts into WANTS_HIDDEN_INFO
    # + an r6- proof exists (R6); else rides along with counters ONLY when counters are a
    # real plan (>= 2). Never auto-flagged universally.
    if "hidden_information" in modeled:
        sev["hidden_information"] = "high"
    elif c >= 2:
        sev["hidden_information"] = sev["counterspell_on_stack"]
    else:
        sev["hidden_information"] = "high"

    # Combat tricks are informational only -- never downgrade.
    sev["instant_speed_combat_trick"] = "high"

    return sev


def _apl_modeled_capabilities(deck_name):
    """Set of engine mechanics the deck's registered MATCH APL opts into AND for
    which a modelability proof exists.

    Ties the modelability gate to the actual pilot-code capability flags: a deck is
    credited a mechanic only when (a) its match-APL declares the WANTS_* flag and
    (b) the engine work is proven in modelability_proofs/. Best-effort + fully
    guarded -- any failure returns an empty set, so the gate falls back to the
    static (pessimistic) rules. This is what lets a deck whose pilot actually models
    warp/stack avoid being shelved by the static decklist scan.
    """
    modeled = set()
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proofs = os.path.join(root, "modelability_proofs")
        have = os.listdir(proofs) if os.path.isdir(proofs) else []

        def _proof(prefix):
            return any(f.startswith(prefix) for f in have)

        from apl import MATCH_APL_REGISTRY
        import importlib
        key = deck_name.lower().replace(" ", "").replace("'", "").replace("-", "")
        entry = MATCH_APL_REGISTRY.get(key)
        if entry is None:
            return modeled
        # Registry is lazy: values are (module_path, class_name) string tuples
        # imported on demand. Resolve to the class (also accept a direct class).
        if isinstance(entry, tuple):
            mod = importlib.import_module(entry[0])
            cls = getattr(mod, entry[1], None)
        else:
            cls = entry
        if cls is None:
            return modeled
        if getattr(cls, "WANTS_WARP", False) and _proof("r4-warp"):
            modeled.add("warp")
        if getattr(cls, "WANTS_PRIORITY_STACK", False) and _proof("r1-"):
            modeled.add("counterspell_on_stack")
        if getattr(cls, "WANTS_STORM", False) and _proof("r3-"):
            modeled.add("storm")
        if getattr(cls, "WANTS_HIDDEN_INFO", False) and _proof("r6-"):
            modeled.add("hidden_information")
    except Exception:
        return set()
    return modeled


def assess_engine_fidelity(db, mainboard, modeled_caps=None):
    """Compute the deterministic engine_fidelity block for a mainboard.

    Returns the dict that goes under profile["engine_fidelity"], with two extra
    debug-friendly keys (mechanic_counts, evidence) the caller may keep or drop.
    NO LLM is involved anywhere in this function.

    modeled_caps: optional set of mechanics the deck's match-APL models (credited
    as handled). None/empty -> static pessimistic behavior (byte-identical).
    """
    fmap = _load_fidelity_map()
    counts, evidence, unresolved = _detect_mechanics(db, mainboard)
    sev = _severity_for_counts(counts, modeled=modeled_caps or frozenset())

    # Overall confidence = worst severity among all mechanics.
    confidence = "high"
    for mech_sev in sev.values():
        if _SEVERITY_ORDER[mech_sev] > _SEVERITY_ORDER[confidence]:
            confidence = mech_sev

    # blocking_imperfections: imperfection ids for mechanics at severity
    # medium-or-worse, read from the fidelity map (single source of truth).
    blocking = []
    for mech, mech_sev in sev.items():
        if _SEVERITY_ORDER[mech_sev] >= _SEVERITY_ORDER["medium"]:
            imp = fmap.get(mech)
            if imp and imp not in blocking:
                blocking.append(imp)

    # Human-readable NOT_modeled phrases for everything that tripped (including
    # informational combat tricks, which are real engine gaps even if they
    # don't downgrade confidence).
    not_modeled = []
    if counts["counterspell_on_stack"] > 0:
        not_modeled.append(
            "counterspells on the stack (%d copies: %s)" % (
                counts["counterspell_on_stack"],
                ", ".join(evidence["counterspell_on_stack"])))
    if counts["planeswalker_loyalty"] > 0:
        not_modeled.append(
            "planeswalker loyalty (%d copies: %s)" % (
                counts["planeswalker_loyalty"],
                ", ".join(evidence["planeswalker_loyalty"])))
    if counts["warp"] > 0:
        not_modeled.append(
            "Warp mechanic (%d copies: %s)" % (
                counts["warp"], ", ".join(evidence["warp"])))
    if sev["hidden_information"] != "high":
        not_modeled.append(
            "hidden information / reactive-mana representation "
            "(interaction is core)")
    if counts["instant_speed_combat_trick"] > 0:
        not_modeled.append(
            "instant-speed combat tricks (%d copies: %s)" % (
                counts["instant_speed_combat_trick"],
                ", ".join(evidence["instant_speed_combat_trick"])))

    # Baseline modeled capabilities (what the engine does represent).
    modeled = ["land mana / ramp", "casting spells", "combat damage",
               "goldfish kill detection"]

    block = {
        "modeled": modeled,
        "NOT_modeled": not_modeled,
        "blocking_imperfections": blocking,
        "confidence": confidence,
        # Debug-friendly extras (kept in the JSON for auditability).
        "mechanic_counts": counts,
        "evidence": {k: v for k, v in evidence.items() if v},
        "unresolved_cards": unresolved,
    }
    return block


# ---------------------------------------------------------------------------
# Deterministic prose / metadata (grounded; cites real card names only)
# ---------------------------------------------------------------------------

def _nonland_main(db, mainboard):
    """Mainboard (qty, name) entries that are not lands, best-effort."""
    out = []
    for qty, name in mainboard:
        if db is not None and db.is_land(name):
            continue
        out.append((qty, name))
    return out


def _key_cards(db, mainboard, limit=6):
    """Top nonland cards by copy count (then CMC desc) with a coarse role.

    Roles are inferred from oracle text / type only (never invents abilities):
      interaction (counter/destroy/exile/damage), enabler (draw/search/ramp),
      payoff (otherwise -- creatures / planeswalkers / threats).
    """
    nonland = _nonland_main(db, mainboard)

    def _cmc(name):
        return db.cmc(name) if db is not None else 0.0

    nonland.sort(key=lambda qn: (-qn[0], -_cmc(qn[1])))
    out = []
    for qty, name in nonland[:limit]:
        role = "payoff"
        if db is not None:
            o = (db.oracle_text(name) or "").lower()
            if any(t in o for t in ("counter target", "destroy target",
                                    "exile target", "deals", "damage to")):
                role = "interaction"
            elif any(t in o for t in ("draw a card", "draw two", "search your",
                                      "add {", "create a treasure")):
                role = "enabler"
        out.append({"name": name, "role": role, "copies": qty})
    return out


def _color_string(db, mainboard):
    """WUBRG color identity string from mainboard card colors (best-effort)."""
    seen = set()
    if db is not None:
        for _, name in mainboard:
            for c in db.colors(name):
                seen.add(c)
    order = ["W", "U", "B", "R", "G"]
    s = "".join(c for c in order if c in seen)
    return s or "C"


def _mana_profile(db, mainboard, counts):
    """Coarse, factual mana profile: colors + ramp/interaction density buckets."""
    colors = _color_string(db, mainboard)
    ramp = 0
    if db is not None:
        for qty, name in mainboard:
            o = (db.oracle_text(name) or "").lower()
            tl = (db.type_line(name) or "").lower()
            if "add {" in o or "search your library for" in o and "land" in o:
                ramp += qty
            elif "mana dork" in o:
                ramp += qty
            elif "ramp" in tl:
                ramp += qty
    interaction = counts["counterspell_on_stack"]

    def _bucket(n):
        return "high" if n >= 6 else ("medium" if n >= 3 else "low")

    return {"colors": colors, "ramp": _bucket(ramp),
            "interaction": _bucket(interaction)}


def _deterministic_prose(db, mainboard, key_cards, counts, confidence):
    """Grounded, coarse defaults for win_conditions / core_engine / etc.

    These cite only real card names + counts (no invented abilities). The
    optional LLM pass may replace win_conditions / sequencing_rules later.
    """
    payoffs = [k["name"] for k in key_cards if k["role"] == "payoff"][:3]
    win_conditions = []
    if payoffs:
        win_conditions.append("Resolve and attack with: " + ", ".join(payoffs))
    if counts["counterspell_on_stack"] >= 2:
        win_conditions.append(
            "Protect the plan with countermagic, win the long game")
    if not win_conditions:
        win_conditions.append("Reduce opponent to 0 via the deck's threats")

    core_engine = []
    if counts["counterspell_on_stack"] > 0:
        core_engine.append(
            "%d counterspell copies (stack interaction)"
            % counts["counterspell_on_stack"])
    if counts["planeswalker_loyalty"] > 0:
        core_engine.append(
            "%d planeswalker copies (loyalty engine)"
            % counts["planeswalker_loyalty"])
    enablers = [k["name"] for k in key_cards if k["role"] == "enabler"][:3]
    if enablers:
        core_engine.append("Card advantage / setup: " + ", ".join(enablers))
    if not core_engine:
        core_engine.append("Efficient threats backed by a clean mana curve")

    sequencing_rules = [
        "Land drops before spells; respect color requirements (deterministic default)",
    ]
    if counts["counterspell_on_stack"] >= 2:
        sequencing_rules.append(
            "Hold up reactive mana when the opponent can act "
            "(NOTE: not perfectly modeled by the engine)")

    known_weaknesses = []
    if confidence in ("low", "unmodelable"):
        known_weaknesses.append(
            "Engine cannot fully represent this deck's core; sim FWR is "
            "untrustworthy until the blocking imperfection is modeled")
    if counts["counterspell_on_stack"] == 0 and counts["warp"] == 0:
        known_weaknesses.append("Fast combo / resilient threats on the draw")
    if not known_weaknesses:
        known_weaknesses.append("Dedicated hate for this archetype's core")

    return win_conditions, core_engine, sequencing_rules, known_weaknesses


def _expected_kill_turn(db, mainboard, counts):
    """Coarse [min, max] kill-turn estimate by archetype shape (not a sim)."""
    if counts["counterspell_on_stack"] >= 2 or counts["planeswalker_loyalty"] >= 3:
        return [8, 12]   # control / grindy
    # Average nonland CMC as an aggro/midrange proxy.
    nonland = _nonland_main(db, mainboard)
    total_copies = sum(q for q, _ in nonland) or 1
    total_cmc = 0.0
    if db is not None:
        for q, n in nonland:
            total_cmc += q * db.cmc(n)
    avg = total_cmc / total_copies
    if avg <= 2.2:
        return [3, 5]
    if avg <= 3.2:
        return [4, 6]
    return [5, 8]


# ---------------------------------------------------------------------------
# Optional, fully-guarded LLM enrichment (best-effort; never moves the gate)
# ---------------------------------------------------------------------------

def _enrich_with_llm(profile, deck_name, mainboard):
    """Best-effort prose enrichment via auto_pipeline._classify_deck.

    Lazily imported and broadly guarded: ANY failure (module missing, Ollama
    down, parse error) leaves `profile` exactly as the deterministic pass built
    it. This function MUST be called only AFTER engine_fidelity is finalized.
    """
    try:
        import auto_pipeline  # stdlib-only at import time; heavy deps are lazy
        decklist = "\n".join("%d %s" % (q, n) for q, n in mainboard)
        cls = auto_pipeline._classify_deck(deck_name, decklist)
        if not isinstance(cls, dict) or not cls:
            return profile
        role = cls.get("role")
        if role and role not in ("NONE", ""):
            profile["mana_profile"]["role"] = role
        key = cls.get("key_cards")
        if key and key not in ("NONE", ""):
            # Replace win_conditions with the LLM's grounded key-card line.
            profile["win_conditions"] = [
                "Win via: " + key] + profile.get("win_conditions", [])
        profile["_llm_enriched"] = True
    except Exception as exc:  # noqa: BLE001 - enrichment is never fatal
        sys.stderr.write("[arl_profile] LLM enrichment skipped: %s\n" % exc)
    return profile


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _render_md(profile):
    """Render the profile dict as a readable markdown brief."""
    ef = profile["engine_fidelity"]
    lines = []
    lines.append("# Archetype Capability Profile: %s" % profile["archetype"])
    lines.append("")
    lines.append("- slug: `%s`" % profile["slug"])
    lines.append("- format: %s" % profile["format"])
    lines.append("- expected_kill_turn: %s" % profile["expected_kill_turn"])
    lines.append("")
    lines.append("## Engine Fidelity (deterministic gate)")
    lines.append("")
    lines.append("- **confidence: %s**" % ef["confidence"])
    lines.append("- blocking_imperfections: %s" % (
        ", ".join(ef["blocking_imperfections"]) or "(none)"))
    lines.append("- mechanic_counts: %s" % json.dumps(ef["mechanic_counts"]))
    lines.append("")
    lines.append("### Modeled")
    for m in ef["modeled"]:
        lines.append("- %s" % m)
    lines.append("")
    lines.append("### NOT modeled")
    if ef["NOT_modeled"]:
        for m in ef["NOT_modeled"]:
            lines.append("- %s" % m)
    else:
        lines.append("- (nothing in this deck's plan is unmodeled)")
    if ef.get("unresolved_cards"):
        lines.append("")
        lines.append("> WARNING: cards not resolved in card DB (counts may be "
                     "incomplete): %s" % ", ".join(ef["unresolved_cards"]))
    lines.append("")
    lines.append("## Win Conditions")
    for w in profile["win_conditions"]:
        lines.append("- %s" % w)
    lines.append("")
    lines.append("## Core Engine")
    for c in profile["core_engine"]:
        lines.append("- %s" % c)
    lines.append("")
    lines.append("## Key Cards")
    for k in profile["key_cards"]:
        lines.append("- %s (%s, x%s)" % (k["name"], k["role"], k["copies"]))
    lines.append("")
    lines.append("## Sequencing Rules")
    for s in profile["sequencing_rules"]:
        lines.append("- %s" % s)
    lines.append("")
    lines.append("## Mana Profile")
    lines.append("- %s" % json.dumps(profile["mana_profile"]))
    lines.append("")
    lines.append("## Sideboard Intent")
    lines.append("- %s" % json.dumps(profile["sideboard_intent"]))
    lines.append("")
    lines.append("## Known Weaknesses")
    for w in profile["known_weaknesses"]:
        lines.append("- %s" % w)
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_profile(deck_file, format_name="modern"):
    """Build, write, and return the capability profile for `deck_file`.

    Writes docs/archetype_profiles/<slug>.json and <slug>.md. The
    engine_fidelity block is computed deterministically (no LLM) and finalized
    BEFORE any optional LLM enrichment of the prose fields.
    """
    if not os.path.isfile(deck_file):
        raise FileNotFoundError("deck file not found: %s" % deck_file)

    deck_name, detected_fmt = _derive_deck_meta(deck_file)
    fmt = detected_fmt or format_name
    slug = _safe_slug(deck_name)

    mainboard, sideboard = _parse_decklist(deck_file)
    db = _open_card_db()

    # --- DETERMINISTIC GATE (finalized before any LLM call) ---
    # Capability-aware: credit mechanics the deck's match-APL actually opts into
    # (and that are proven in modelability_proofs/) so a deck whose pilot models
    # warp/stack is not shelved by the static decklist scan. Falls back to the
    # pessimistic static rules when no APL/proof is found.
    modeled_caps = _apl_modeled_capabilities(deck_name)
    ef = assess_engine_fidelity(db, mainboard, modeled_caps=modeled_caps)
    counts = ef["mechanic_counts"]
    confidence = ef["confidence"]

    key_cards = _key_cards(db, mainboard)
    win_conditions, core_engine, sequencing_rules, known_weaknesses = \
        _deterministic_prose(db, mainboard, key_cards, counts, confidence)
    mana_profile = _mana_profile(db, mainboard, counts)
    expected_kill = _expected_kill_turn(db, mainboard, counts)

    # Light deterministic sideboard intent from the sideboard size only.
    sideboard_intent = {
        "cards": sum(q for q, _ in sideboard),
        "note": "deterministic placeholder; refine with matchup data",
    }

    profile = {
        "slug": slug,
        "archetype": deck_name,
        "format": fmt,
        "win_conditions": win_conditions,
        "core_engine": core_engine,
        "key_cards": key_cards,
        "sequencing_rules": sequencing_rules,
        "mana_profile": mana_profile,
        "sideboard_intent": sideboard_intent,
        "expected_kill_turn": expected_kill,
        "known_weaknesses": known_weaknesses,
        "engine_fidelity": {
            "modeled": ef["modeled"],
            "NOT_modeled": ef["NOT_modeled"],
            "blocking_imperfections": ef["blocking_imperfections"],
            "confidence": ef["confidence"],
            "mechanic_counts": ef["mechanic_counts"],
            "evidence": ef["evidence"],
            "unresolved_cards": ef["unresolved_cards"],
        },
        "source_deck_file": os.path.abspath(deck_file),
    }

    # --- OPTIONAL enrichment (guarded; cannot move the gate above) ---
    # _enrich_with_llm already guards Ollama-down internally; this OUTER guard
    # is defense-in-depth so NO enrichment bug can ever crash the gate.
    try:
        profile = _enrich_with_llm(profile, deck_name, mainboard)
    except Exception as exc:  # noqa: BLE001 - enrichment is never fatal
        sys.stderr.write("[arl_profile] enrichment hard-failed (ignored): %s\n"
                         % exc)

    # --- Persist both artifacts ---
    os.makedirs(PROFILES_DIR, exist_ok=True)
    json_path = os.path.join(PROFILES_DIR, slug + ".json")
    md_path = os.path.join(PROFILES_DIR, slug + ".md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(profile, fh, indent=2)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(_render_md(profile))

    return profile


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        sys.stderr.write(
            "usage: python arl_profile.py <deck_file> [format]\n")
        return 0 if (argv and argv[0] in ("-h", "--help")) else 1

    deck_file = argv[0]
    fmt = argv[1] if len(argv) > 1 else "modern"

    try:
        profile = build_profile(deck_file, format_name=fmt)
    except Exception as exc:  # noqa: BLE001 - surface a one-line reason
        sys.stderr.write("ERROR: %s\n" % exc)
        return 1

    ef = profile["engine_fidelity"]
    print("PROFILE: %s" % os.path.join(PROFILES_DIR, profile["slug"] + ".json"))
    print("ARCHETYPE: %s" % profile["archetype"])
    print("CONFIDENCE: %s" % ef["confidence"])
    print("MECHANIC_COUNTS: %s" % json.dumps(ef["mechanic_counts"]))
    print("BLOCKING_IMPERFECTIONS: %s" % (
        ", ".join(ef["blocking_imperfections"]) or "(none)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
