"""engine/response_capability.py -- oracle-driven response CAPABILITY classifier.

Stage 1 of harness/specs/2026-07-02-oracle-driven-responses.md (extends
2026-07-01-oracle-driven-responses.md, whose classifier grammar and golden-test
discipline apply BY REFERENCE). Derives, from the already-loaded CardDB oracle
data (engine/card_db.py singleton), whether a card can counter / spot-remove
at instant speed, at what timing, and at what printed cost.

CAPABILITY vs POLICY (the load-bearing seam, spec design 4):
  This module answers "what CAN this card legally do in a response window" as
  a pure function of the card -- oracle-derived, cached, deterministic,
  APL-independent, ZERO game-state access. Whether firing is smart (value
  gates, _PRIORITY_COUNTER_TARGETS eagerness, reserve_mana hold-up) is POLICY
  and stays in counter_resolver / the APL layer, untouched by this module.

FEATURE GATE: WANTS_ORACLE_RESPONSES (R-ladder convention, default OFF).
  Stages 0-2 wire NOTHING into the live engine: no live-path module imports
  this file (tests/test_response_capability.py asserts that structurally), so
  gate-OFF byte-identity holds by construction. Stage 3 adds the consultation
  swaps behind the gate (legacy counter window, R1/R2 priority, instant-speed
  removal lookups); consultation is either/or per gate -- never both paths.

DETERMINISM: classification is pure string work done once per unique card.
  No random draws, no id()-ordering, no game-state reads. Results are cached
  for the process lifetime keyed by oracle_id (normalized-name fallback),
  mirroring CardDB's own `_db_instance` singleton pattern (spec design 2).
  Parallel workers each warm their own copy; read-only afterward.

NOT DERIVED in v1 (these cards keep their whitelist entries; the golden test
pins each one so nothing silently drifts):
  - alt/pitch costs ("rather than pay this spell's mana cost"): Force of
    Will, Force of Negation, Daze, Disrupting Shoal
  - {X} in the printed mana cost (Disrupting Shoal)
  - cost-reduction statics ("costs {N} less to cast"): Mystical Dispute,
    Witchstalker Frenzy
  - Spree / Tiered additional-mana-cost modes: Phantom Interference, Fire Magic
  - unknown target riders (non-outlaw, "toughness 4 or greater", ...):
    Shoot the Sheriff, Destroy Evil
  - variable damage ("deals damage equal to ..."): Combustion Technique
  - modal spells beyond their FIRST mode (07-01 scope; Get Out's counter mode
    is mode 1 and IS derived; its self-bounce mode 2 is not)
  - counter-abilities on permanents / ETB pseudo-counters (Subtlety)
Sorcery-speed removal and board wipes are out of scope v1 (stay
MATCH_REMOVAL-table-driven; "each"/"all" scopes never classify).

Normalization REUSES engine/oracle_parser.py idioms verbatim (face splits on
"//", reminder-text stripping, "As an additional cost" line removal, number
words via oracle_parser._to_int) -- per 07-01 pre-flight #4, this is not a
second parser dialect.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from engine.card_db import CardDB
from engine.oracle_parser import _to_int  # REUSE, do not re-implement
from data.card import Tag

# ---------------------------------------------------------------------------
# Feature gate (R-ladder convention). Stage 3 consultation sites will call
# oracle_responses_enabled(); with the gate OFF this module is never consulted
# by the engine at all.
# ---------------------------------------------------------------------------

GATE_ATTR = "WANTS_ORACLE_RESPONSES"


def oracle_responses_enabled(self_apl, opp_apl) -> bool:
    """True iff either APL opts in to oracle-driven response capability.

    Mirrors game_state._priority_stack_enabled / match_engine's
    WANTS_INSTANT_COMBAT gate shape. Default OFF.
    """
    return bool(getattr(self_apl, GATE_ATTR, False)
                or getattr(opp_apl, GATE_ATTR, False))


# ---------------------------------------------------------------------------
# Capability kinds (map 1:1 onto RESPOND_COUNTER / RESPOND_REMOVAL in
# docs/action-vocabulary.md #9/#10 -- the 13-kind B1 vocabulary does NOT grow).
# ---------------------------------------------------------------------------

COUNTER_ANY          = "COUNTER_ANY"
COUNTER_NONCREATURE  = "COUNTER_NONCREATURE"
COUNTER_CREATURE     = "COUNTER_CREATURE"
COUNTER_CMC_COND     = "COUNTER_CMC_COND"
COUNTER_UNLESS_PAY_N = "COUNTER_UNLESS_PAY_N"
REMOVAL_DMG_N        = "REMOVAL_DMG_N"
REMOVAL_DESTROY      = "REMOVAL_DESTROY"
REMOVAL_EXILE        = "REMOVAL_EXILE"
BOUNCE               = "BOUNCE"

COUNTER_KINDS = frozenset({COUNTER_ANY, COUNTER_NONCREATURE, COUNTER_CREATURE,
                           COUNTER_CMC_COND, COUNTER_UNLESS_PAY_N})
REMOVAL_KINDS = frozenset({REMOVAL_DMG_N, REMOVAL_DESTROY, REMOVAL_EXILE,
                           BOUNCE})

TIMING_INSTANT = "instant"
TIMING_FLASH   = "flash"


@dataclass(frozen=True)
class ResponseCapability:
    """(kind, timing, cost, condition) per spec design 1.

    cost is the PRINTED cmc (honest-mana path); mana_cost carries the printed
    pip string for Stage 3 affordability checks via mana_pool.can_cast.
    condition is a tuple of normalized condition tokens (hashable,
    deterministic); see counter_matches / removal_spec_from for consumption.
    """
    kind: str
    timing: str
    cost: int
    mana_cost: str
    condition: tuple = ()


@dataclass(frozen=True)
class Classification:
    """Full classification result for one card (cached unit).

    caps      -- derived capabilities (may be empty)
    guarded   -- v1 out-of-scope reasons that FORCED whitelist fallback
                 (alt-cost, {X}, cost-reduction, spree/tiered)
    unhandled -- response-looking text the grammar saw but could not derive
                 (unknown filter/rider/variable amount). Coverage sweep
                 surfaces these; they must never classify silently wrong.
    timing    -- 'instant' | 'flash' | '' (not castable at instant speed)
    """
    name: str
    caps: tuple = ()
    guarded: tuple = ()
    unhandled: tuple = ()
    timing: str = ""


# ---------------------------------------------------------------------------
# Classification cache (spec design 2): module-level dict, process lifetime,
# keyed by oracle_id with normalized-name fallback. Zero per-cast parsing.
# ---------------------------------------------------------------------------

_CACHE: dict = {}
_CACHE_HITS = 0
_CACHE_MISSES = 0


def cache_stats() -> dict:
    return {"hits": _CACHE_HITS, "misses": _CACHE_MISSES, "size": len(_CACHE)}


def _reset_cache():
    """Test hook only -- never called by engine code."""
    global _CACHE_HITS, _CACHE_MISSES
    _CACHE.clear()
    _CACHE_HITS = 0
    _CACHE_MISSES = 0


# ---------------------------------------------------------------------------
# v1 derivation guards -- when any of these fire, the card is NOT derived and
# keeps its whitelist entry (spec: "Alt/pitch costs ... are NOT derived in v1").
# ---------------------------------------------------------------------------

_ALT_COST_RE   = re.compile(r"rather than pay (?:this spell's|~'s) mana cost",
                            re.I)
_COST_LESS_RE  = re.compile(r"costs? \{[^}]+\} less", re.I)
_GUARD_KEYWORDS = ("Spree", "Tiered")   # additional-MANA-cost modal frames


# ---------------------------------------------------------------------------
# Grammar (spec design 1). Closed vocabularies; anything outside them lands in
# `unhandled`, never in a capability (Risk 4: no silent false positives).
# ---------------------------------------------------------------------------

# NOTE greedy filter group: multi-"spell" phrasings like Spider-Sense's
# "counter target instant spell, sorcery spell, or triggered ability" must
# capture up to the LAST "spell" so the mixed filter fails the closed
# vocabulary below (UNHANDLED) instead of silently narrowing to "instant".
_COUNTER_RE = re.compile(
    r"\bcounter target ((?:[a-z',\- ]+) )?spell\b"
    r"(?P<youctrl> you control)?"
    r"(?: with mana value (?P<mv>\d+)(?P<mvdir> or greater| or less)?)?"
    r"(?P<unless>[^.]*unless its controller pays \{(?P<pay>\d+)\})?",
    re.I)

# pure card-type words accepted in counter filter lists ("artifact or
# enchantment", "enchantment, instant, or sorcery", ...). Colors, subtypes
# ("red or green", "Vehicle") and ability words stay UNHANDLED.
_SPELL_TYPE_WORDS = frozenset({"creature", "artifact", "enchantment",
                               "instant", "sorcery", "planeswalker"})


def _parse_counter_filter(filt: str):
    """Return (kind, condition_tokens) for a counter target filter, or None
    if the filter is outside the closed vocabulary (-> UNHANDLED)."""
    filt = filt.strip().lower()
    if filt == "":
        return COUNTER_ANY, ()
    if filt == "noncreature":
        return COUNTER_NONCREATURE, (("target", "noncreature"),)
    if filt == "creature":
        return COUNTER_CREATURE, (("target", "creature"),)
    tokens = [t.strip() for t in
              re.split(r",\s*or\s+|,\s*|\s+or\s+", filt) if t.strip()]
    if tokens and all(t in _SPELL_TYPE_WORDS for t in tokens):
        kind = (COUNTER_CREATURE if "creature" in tokens
                else COUNTER_NONCREATURE)
        return kind, (("target_type_any", tuple(tokens)),)
    return None

_DMG_RE = re.compile(
    r"deals (\d+|[a-z]+) damage to (any target|target [a-z',\- ]+?)"
    r"(?:\.|,| and\b| where\b|$)",
    re.I)

_DESTROY_RE = re.compile(
    r"\b(destroy|exile) target ([a-z',\- ]+?)"
    r"(?: with mana value (\d+) or less)?\s*\.",
    re.I)

_SHRINK_RE = re.compile(
    r"\btarget creature gets [+-]\d+/-(\d+) until end of turn", re.I)

_BOUNCE_RE = re.compile(
    r"\breturn target ([a-z',\- ]+?) to its owner's hand", re.I)

# destroy/exile/bounce target-phrase token vocabulary
_TARGET_PREFIXES = frozenset({"nonartifact", "nonlegendary", "non-legendary",
                              "tapped", "attacking", "blocking",
                              "attacking or blocking"})
_TARGET_BASES    = frozenset({"creature", "planeswalker", "artifact",
                              "enchantment", "permanent", "nonland permanent"})


def _parse_target_phrase(phrase: str):
    """Parse a destroy/exile/bounce target phrase against the closed
    vocabulary. Returns (bases, conditions) or None if any token is unknown
    (unknown rider -> UNHANDLED, e.g. 'non-outlaw creature',
    'creature with toughness 4 or greater')."""
    phrase = phrase.strip().rstrip(",")
    conditions = []
    bases = set()
    # controller suffixes: legality nicety, capability-neutral
    for suffix in (" an opponent controls", " you don't control"):
        if phrase.endswith(suffix):
            phrase = phrase[: -len(suffix)]
            conditions.append(("opponent_controls",))
    # split on list separators: ", " / " or " / ", or " / "and/or"
    tokens = re.split(r",\s*or\s+|,\s*|\s+and/or\s+|\s+or\s+", phrase)
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if tok == "nonland permanent":
            bases.add("permanent")
            conditions.append(("nonland",))
            continue
        if tok in _TARGET_BASES:
            bases.add(tok)
            continue
        prefix, _, base = tok.rpartition(" ")
        if base in _TARGET_BASES and prefix in _TARGET_PREFIXES:
            bases.add(base)
            conditions.append((prefix.replace("non-", "non"),))
            continue
        return None   # unknown rider -> UNHANDLED, never silently wrong
    return frozenset(bases), tuple(conditions)


# ---------------------------------------------------------------------------
# Normalization -- oracle_parser.py idioms, verbatim (pre-flight #4)
# ---------------------------------------------------------------------------

_MODAL_HEADER_RE = re.compile(
    r"^choose (?:one|two|three|one or more|a mode)\s*[—\-]", re.I)


def _normalize_and_segment(oracle_text: str, card_name: str):
    """Return the list of text segments to classify.

    - front face only ("//" split, oracle_parser verbatim)
    - reminder text stripped
    - "As an additional cost ..." casting-requirement lines stripped
      (non-mana additional costs like Bitter Triumph's discard/life are
      policy-neutral for capability; Spree/Tiered mana modes are guarded
      out BEFORE this function is reached)
    - modal cards ("Choose one --"): FIRST mode only (07-01 scope)
    """
    text = (oracle_text or "").replace("\r\n", "\n")
    if card_name:
        text = text.replace(card_name, "~")
    # Adventure / split / DFC: keep only the front face (oracle_parser idiom)
    if " // " in text or "\n// " in text or text.startswith("// "):
        text = re.split(r"\s*//\s*", text)[0]
    # Strip "As an additional cost to cast this spell, [cost]." lines
    text = re.sub(r"^as an additional cost to cast (?:this spell|~),[^\n]+\n?",
                  "", text, flags=re.I | re.M)
    # Strip reminder text in parentheses
    text = re.sub(r"\s*\([^)]*\)", "", text)

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    # Modal: keep header-adjacent FIRST bullet only
    for i, ln in enumerate(lines):
        if _MODAL_HEADER_RE.match(ln):
            bullets = [b for b in lines[i + 1:]
                       if b.startswith("•") or b.startswith("- ")]
            first_mode = []
            if bullets:
                first_mode = [bullets[0].lstrip("•- ").strip()]
            # keep any non-modal lines BEFORE the header (e.g. "This spell
            # can't be countered.") plus the first mode only
            return lines[:i] + first_mode
    # Non-modal: strip stray bullet markers (oracle_parser idiom)
    return [re.sub(r"^[•\-]\s+", "", ln) for ln in lines]


# ---------------------------------------------------------------------------
# Core classifier (pure function of card fields; no CardDB access here so
# tests can feed synthetic fixtures)
# ---------------------------------------------------------------------------

def classify_fields(name: str, oracle_text: str, type_line: str,
                    cmc: float, mana_cost: str, keywords=()) -> Classification:
    """Classify from raw card fields. Pure, deterministic, state-free."""
    front_type = (type_line or "").split(" // ")[0].lower()
    kw = set(keywords or ())

    if "instant" in front_type:
        timing = TIMING_INSTANT
    elif "Flash" in kw or re.match(r"^flash\b", (oracle_text or ""), re.I):
        timing = TIMING_FLASH
    else:
        return Classification(name=name)   # not castable at instant speed (v1)

    # ---- v1 guards: whitelist fallback, never a wrong derivation ----------
    guarded = []
    if "{X}" in (mana_cost or ""):
        guarded.append("x-cost")
    if _ALT_COST_RE.search(oracle_text or ""):
        guarded.append("alt-pitch-cost")
    if _COST_LESS_RE.search(oracle_text or ""):
        guarded.append("cost-reduction-static")
    for g in _GUARD_KEYWORDS:
        if g in kw:
            guarded.append(f"additional-cost-modes:{g.lower()}")
    if guarded:
        return Classification(name=name, guarded=tuple(guarded), timing=timing)

    cost = int(cmc or 0)
    segments = _normalize_and_segment(oracle_text or "", name)
    caps: list = []
    unhandled: list = []

    for seg in segments:
        _classify_segment(seg, timing, cost, mana_cost or "", caps, unhandled)

    return Classification(name=name, caps=tuple(caps),
                          unhandled=tuple(unhandled), timing=timing)


def _classify_segment(seg: str, timing: str, cost: int, mana_cost: str,
                      caps: list, unhandled: list):
    """Run the pattern grammar over one text segment, appending results."""
    low = seg.lower()

    # ---- counters ----------------------------------------------------------
    m = _COUNTER_RE.search(seg)
    if m:
        if m.group("youctrl"):
            unhandled.append(f"counter-own-spell:{seg[:60]}")
        else:
            filt = (m.group(1) or "").strip()
            parsed = _parse_counter_filter(filt)
            if parsed is None:
                kind = None
                unhandled.append(f"counter-filter:{filt}")
            else:
                kind, filter_cond = parsed
                cond = list(filter_cond)
            if kind is not None:
                if m.group("mv"):
                    n = int(m.group("mv"))
                    op = {"": "==", " or greater": ">=",
                          " or less": "<="}[(m.group("mvdir") or "")]
                    cond.append(("cmc", op, n))
                    kind = COUNTER_CMC_COND
                if m.group("pay"):
                    cond.append(("unless_pay", int(m.group("pay"))))
                    if kind == COUNTER_ANY:
                        kind = COUNTER_UNLESS_PAY_N
                caps.append(ResponseCapability(kind, timing, cost, mana_cost,
                                               tuple(cond)))
    elif re.search(r"\bcounter target\b", low):
        # counter text outside the closed grammar (abilities, colorless, ...)
        unhandled.append(f"counter-unparsed:{seg[:60]}")

    # ---- damage-based spot removal ----------------------------------------
    m = _DMG_RE.search(seg)
    if m:
        amount, scope = m.group(1), m.group(2).lower()
        n = _to_int(amount)
        creature_scope = (scope == "any target" or "creature" in scope)
        if creature_scope and amount.strip().lower() != "x":
            caps.append(ResponseCapability(REMOVAL_DMG_N, timing, cost,
                                           mana_cost, (("dmg", n),)))
        # player/PW-only burn is inert for creature removal -- no capability,
        # and NOT unhandled (correctly classified as not-an-answer)
    elif re.search(r"deals\b[^.]*\bdamage\b[^.]*\bto (?:any target|target)",
                   low):
        # variable amounts ("equal to ..."), X damage, or unparsed shapes
        unhandled.append(f"damage-unparsed:{seg[:60]}")

    # ---- destroy / exile ---------------------------------------------------
    m = _DESTROY_RE.search(seg)
    if m:
        verb, phrase, mv = m.group(1).lower(), m.group(2), m.group(3)
        parsed = _parse_target_phrase(phrase)
        if parsed is None:
            unhandled.append(f"{verb}-rider:{phrase.strip()[:60]}")
        else:
            bases, conds = parsed
            if "creature" in bases or "permanent" in bases:
                cond = list(conds)
                if mv:
                    cond.append(("mv_le", int(mv)))
                kind = REMOVAL_DESTROY if verb == "destroy" else REMOVAL_EXILE
                caps.append(ResponseCapability(kind, timing, cost, mana_cost,
                                               tuple(cond)))
            # artifact/enchantment-only removal: real capability, but not a
            # creature answer -- out of v1 consultation scope, stay silent
    elif re.search(r"\b(?:destroy|exile) target\b", low):
        # destroy/exile text outside the closed grammar (e.g. Fatal Push's
        # "if it has mana value 2 or less" phrasing) -- surfaced, never silent
        unhandled.append(f"destroy-unparsed:{seg[:60]}")

    # ---- -X/-Y shrink (kills toughness <= Y; same projection as DMG_N) ----
    m = _SHRINK_RE.search(seg)
    if m:
        n = int(m.group(1))
        caps.append(ResponseCapability(REMOVAL_DMG_N, timing, cost, mana_cost,
                                       (("dmg", n), ("minus_toughness",))))

    # ---- bounce ------------------------------------------------------------
    m = _BOUNCE_RE.search(seg)
    if m:
        phrase = m.group(1)
        if not re.search(r"\byou (own|control)\b", phrase):
            parsed = _parse_target_phrase(phrase)
            if parsed is None:
                unhandled.append(f"bounce-rider:{phrase.strip()[:60]}")
            else:
                bases, conds = parsed
                if "creature" in bases or "permanent" in bases:
                    caps.append(ResponseCapability(
                        BOUNCE, timing, cost, mana_cost,
                        tuple(conds) + (("temporary",),)))
    elif (re.search(r"\breturn target\b[^.]*\bhand\b", low)
          and not re.search(r"\byou (?:own|control)\b", low)):
        unhandled.append(f"bounce-unparsed:{seg[:60]}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(card_or_name) -> Classification:
    """Classify a card (engine Card object or name string), cached.

    Cache key is Scryfall oracle_id when the card resolves in CardDB,
    normalized-name fallback otherwise (spec design 2).
    """
    global _CACHE_HITS, _CACHE_MISSES
    name = getattr(card_or_name, "name", None) or str(card_or_name)

    db = CardDB()
    entry = db.get(name)
    if entry is not None and entry.get("oracle_id"):
        key = entry["oracle_id"]
    else:
        key = "name::" + re.sub(r"[^a-z0-9]", "", name.lower())

    hit = _CACHE.get(key)
    if hit is not None:
        _CACHE_HITS += 1
        return hit
    _CACHE_MISSES += 1

    if entry is None:
        result = Classification(name=name)   # unknown card: no capability
    else:
        result = classify_fields(
            name=entry.get("name", name),
            oracle_text=db.oracle_text(name),
            type_line=entry.get("type_line", "") or "",
            cmc=entry.get("cmc", 0) or 0,
            mana_cost=entry.get("mana_cost", "") or "",
            keywords=entry.get("keywords", ()) or (),
        )
    _CACHE[key] = result
    return result


def capabilities(card_or_name) -> tuple:
    """capabilities(card) -> tuple[ResponseCapability, ...] (spec design 1)."""
    return classify(card_or_name).caps


# ---------------------------------------------------------------------------
# Consumption helpers (Stage 3 consultation sites + golden test)
# ---------------------------------------------------------------------------

def counter_matches(cap: ResponseCapability, spell) -> bool:
    """Can this COUNTER_* capability legally target `spell`?

    Mirrors counter_resolver.COUNTER_VALIDITY predicate semantics: consumes
    only spell.has(Tag.*) and spell.cmc. `unless_pay` never gates legality
    (whether the opponent CAN pay is a resolution/policy concern).
    Unknown condition tokens conservatively return False -- the classifier
    must never make something legal that it does not understand.
    """
    if cap.kind not in COUNTER_KINDS:
        return False
    for cond in cap.condition:
        tag = cond[0]
        if tag == "target":
            if cond[1] == "noncreature" and spell.has(Tag.CREATURE):
                return False
            if cond[1] == "creature" and not spell.has(Tag.CREATURE):
                return False
        elif tag == "target_type_any":
            type_tags = {"creature": Tag.CREATURE, "artifact": Tag.ARTIFACT,
                         "enchantment": Tag.ENCHANTMENT, "instant": Tag.INSTANT,
                         "sorcery": Tag.SORCERY,
                         "planeswalker": Tag.PLANESWALKER}
            wanted = [type_tags.get(t) for t in cond[1]]
            if None in wanted:
                return False
            if not any(spell.has(t) for t in wanted):
                return False
        elif tag == "cmc":
            op, n = cond[1], cond[2]
            v = getattr(spell, "cmc", 0) or 0
            if op == "==" and v != n:
                return False
            if op == ">=" and v < n:
                return False
            if op == "<=" and v > n:
                return False
        elif tag == "unless_pay":
            pass
        else:
            return False
    return True


def removal_spec_from(caps) -> Optional[tuple]:
    """Project removal capabilities onto MATCH_REMOVAL's (cmc, max_tgh)
    semantics (spec design 3): REMOVAL_DMG_N -> (cmc, N);
    DESTROY / EXILE / BOUNCE -> (cmc, None) + conditions.

    Returns (cost, max_tgh, conditions) for the first removal capability,
    or None if the card derives no removal.
    """
    for cap in caps:
        if cap.kind == REMOVAL_DMG_N:
            n = next((c[1] for c in cap.condition if c[0] == "dmg"), None)
            return (cap.cost, n, cap.condition)
        if cap.kind in (REMOVAL_DESTROY, REMOVAL_EXILE, BOUNCE):
            return (cap.cost, None, cap.condition)
    return None
