"""engine/oracle_parser.py — regex-based oracle text parser.

Reads a card's oracle text and emits a dict of trigger → effect-list:

  {
    "etb":     [("draw", {"n": 1}), ...],
    "attack":  [...],
    "upkeep":  [...],
    "endstep": [...],
    "dies":    [...],
    "landfall":[...],
    "spell":   [...],   # instant/sorcery resolve
  }

Where each effect-list is a list of `(primitive_name, kwargs)` tuples
that `engine.effect_primitives.run_effects` can execute.

This parser is rule-based, not ML. Patterns are ordered from most
specific to most general. Unknown phrases emit no effects — the card
still casts but its oracle ability is a no-op (logged).

Number words are converted: 'one' → 1, 'two' → 2, ... up to 'ten'.

Limitations (first-pass scope):
  - Triggered abilities with conditional clauses ('if ~') drop the
    condition — we always fire.
  - Choice/modal ('choose one') picks the first listed mode.
  - Targeting is heuristic: 'target creature' = opp's biggest.
  - Alternative costs (flashback, kicker, evoke, impending, warp)
    are flagged on the card but not fully modeled yet.
  - Replacement effects ('enters tapped', 'if ~ would be dealt damage
    instead') are tagged but require engine wiring.
"""

from __future__ import annotations
import re
from typing import Optional

# Convert spelled-out numbers
NUM_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}


def _to_int(s: str) -> int:
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    return NUM_WORDS.get(s, 1)


# ─── Segment splitters ─────────────────────────────────────────────

TRIGGER_PATTERNS = [
    # (regex to match, trigger name)
    (re.compile(r"^when (?:this creature|this permanent|this artifact|this enchantment|~|it) enters(?:,| )",
                re.I | re.M), "etb"),
    (re.compile(r"^when (?P<n>[A-Za-z'\-, ]+?) enters,", re.I | re.M), "etb"),
    (re.compile(r"^whenever (?:this creature|this permanent|~|it) attacks,", re.I | re.M), "attack"),
    (re.compile(r"^whenever (?:this creature|this permanent|~|it) enters or attacks,", re.I | re.M), "etb_or_attack"),
    (re.compile(r"^at the beginning of your upkeep,", re.I | re.M), "upkeep"),
    (re.compile(r"^at the beginning of (?:your|each) end step,", re.I | re.M), "endstep"),
    (re.compile(r"^when (?:this creature|this permanent|~|it) dies,", re.I | re.M), "dies"),
    (re.compile(r"^landfall\s*[—\-]\s*whenever a land (?:you control )?enters,?", re.I | re.M), "landfall"),
    (re.compile(r"^whenever a land (?:you control )?enters(?: the battlefield under your control)?,", re.I | re.M), "landfall"),
]


# ─── Effect-phrase patterns (applied to each trigger segment) ──────
# Ordered: most specific first.

def _p(pattern, flags=re.I):
    return re.compile(pattern, flags)


# "deal N damage to any target" / "to target creature" / "to each opp creature" / face
DAMAGE_ANY  = _p(r"\bdeals?\s+(\d+|\w+)\s+damage\s+to\s+any\s+target\b")
DAMAGE_PLAYER = _p(r"\bdeals?\s+(\d+|\w+)\s+damage\s+to\s+(?:target\s+player|target\s+opponent|each\s+opponent|that\s+player)\b")
DAMAGE_CREATURE = _p(r"\bdeals?\s+(\d+|\w+)\s+damage\s+to\s+target\s+(?:creature|creature or planeswalker|creature, planeswalker)")
DAMAGE_EACH_OPP_CR = _p(r"\bdeals?\s+(\d+|\w+)\s+damage\s+to\s+each\s+(?:creature|opponent's creature|creature your opponents control)")
DAMAGE_EACH_CR = _p(r"\bdeals?\s+(\d+|\w+)\s+damage\s+to\s+each\s+creature\b")

# "destroy target creature" / permanent / exile variants
DESTROY_TGT_CR    = _p(r"\bdestroy\s+target\s+(?:creature|creature or planeswalker|creature, planeswalker|nonland\s+permanent)")
EXILE_TGT_CR      = _p(r"\bexile\s+target\s+(?:creature|creature or planeswalker|nonland\s+permanent|permanent)")
DESTROY_ALL_CR    = _p(r"\bdestroy\s+all\s+creatures\b")
EXILE_ALL_CR      = _p(r"\bexile\s+all\s+creatures\b")

# "put a +1/+1 counter" / "N +1/+1 counters on ~"
ADD_COUNTER       = _p(r"\bputs?\s+(?:a|an|one|two|three|(\d+))\s*\+1/\+1\s+counter(?:s)?\s+on\s+(?:this|it|~|target|itself|each creature)")

# Bounce
BOUNCE_TGT        = _p(r"\breturn\s+target\s+(?:creature|nonland\s+permanent|permanent)\s+to\s+(?:its|their)\s+owner'?s?\s+hand\b")

# Card draw
DRAW_N            = _p(r"\bdraws?\s+(\d+|\w+)\s+cards?\b")
DRAW_ONE_ALT      = _p(r"\bdraw\s+a\s+card\b")

# Mill
MILL_N            = _p(r"\bmills?\s+(\d+|\w+)\s+cards?\b")
MILL_EACH_PLAYER  = _p(r"\beach player mills\s+(\d+|\w+)")

# Life
GAIN_LIFE_N       = _p(r"\byou\s+gain\s+(\d+|\w+)\s+life\b")
LOSE_LIFE_N       = _p(r"\b(?:target\s+opponent|each\s+opponent|target\s+player)\s+loses?\s+(\d+|\w+)\s+life\b")

# Discard
OPP_DISCARDS      = _p(r"\b(?:target\s+opponent|each\s+opponent)\s+discards?\s+(?:a card|(\d+|\w+)\s+cards?)")

# Treasure / Clue / generic tokens
CREATE_TREASURE   = _p(r"\bcreates?\s+(?:a|an|one|two|three|(\d+))\s*Treasure\s+tokens?")
CREATE_CLUE       = _p(r"\bcreates?\s+(?:a|an|one|two|three|(\d+))\s*Clue\s+tokens?")
CREATE_FOOD       = _p(r"\bcreates?\s+(?:a|an|one|two|three|(\d+))\s*Food\s+tokens?")
# Creature token: "create N P/T color type creature token[s] [with ...]"
CREATE_CR_TOKEN   = _p(
    r"\bcreates?\s+(?:(\d+|\w+)\s+)?(\d+)/(\d+)\s+"
    r"(?:[a-zA-Z]+(?:\s+and\s+[a-zA-Z]+)?\s+)?"  # colors
    r"(?:[A-Za-z]+(?:\s+[A-Za-z]+)?)\s+creature tokens?"
    r"(?:\s+with\s+([^.]+))?"
)

# Ramp: search library for basic land / dual / etc.
SEARCH_BASIC      = _p(r"\bsearch\s+your\s+library\s+for\s+(?:a|an|up to (\d+|\w+))\s+basic land")

# Reanimate
REANIMATE         = _p(r"\breturn\s+target\s+creature\s+card\s+from\s+(?:your|a)?\s*graveyard\s+to\s+the\s+battlefield")
RETURN_GY_HAND    = _p(r"\breturn\s+target\s+(?:creature|instant|sorcery|permanent)\s+card\s+from\s+(?:your|a)?\s*graveyard\s+to\s+(?:your|their)\s+hand")

# Scry
SCRY_N            = _p(r"\bscry\s+(\d+|\w+)")

# Counter
COUNTER_SPELL     = _p(r"\bcounter\s+target\s+(?:spell|noncreature spell|creature spell)")


def _qty(m, group=1, default=1):
    """Extract quantity from regex match group."""
    if m is None:
        return default
    g = m.group(group)
    if g is None:
        return default
    return _to_int(g)


def parse_segment(text: str) -> list:
    """Parse one trigger's body text into an effect list."""
    if not text:
        return []
    text = text.strip()
    effects: list = []

    # Damage to any target (check first, most specific)
    m = DAMAGE_ANY.search(text)
    if m:
        effects.append(("damage_any", {"n": _qty(m)}))

    m = DAMAGE_PLAYER.search(text)
    if m:
        effects.append(("damage_player", {"n": _qty(m), "target": "opp"}))

    m = DAMAGE_CREATURE.search(text)
    if m:
        effects.append(("damage_creature", {"n": _qty(m), "target": "opp_biggest"}))

    m = DAMAGE_EACH_OPP_CR.search(text) or DAMAGE_EACH_CR.search(text)
    if m:
        effects.append(("damage_creature", {"n": _qty(m), "target": "each_opp"}))

    # Destroy / exile creatures
    if DESTROY_TGT_CR.search(text):
        effects.append(("destroy", {"target": "opp_biggest_creature"}))

    if EXILE_TGT_CR.search(text):
        effects.append(("exile", {"target": "opp_biggest_creature"}))

    if DESTROY_ALL_CR.search(text):
        effects.append(("destroy_all_creatures", {}))

    if EXILE_ALL_CR.search(text):
        # model as destroy (we don't separately track exile-vs-GY for wipes)
        effects.append(("destroy_all_creatures", {}))

    # +1/+1 counters
    m = ADD_COUNTER.search(text)
    if m:
        n = _qty(m, default=1)
        effects.append(("add_counters", {"n": n, "target": "self"}))

    # Bounce
    if BOUNCE_TGT.search(text):
        effects.append(("bounce_to_hand", {}))

    # Draw
    m = DRAW_N.search(text)
    if m:
        effects.append(("draw", {"n": _qty(m)}))
    elif DRAW_ONE_ALT.search(text):
        effects.append(("draw", {"n": 1}))

    # Mill
    m = MILL_N.search(text)
    if m:
        effects.append(("mill", {"n": _qty(m), "target": "self"}))

    # Life
    m = GAIN_LIFE_N.search(text)
    if m:
        effects.append(("gain_life", {"n": _qty(m)}))

    m = LOSE_LIFE_N.search(text)
    if m:
        effects.append(("lose_life", {"n": _qty(m), "target": "opp"}))

    # Discard
    m = OPP_DISCARDS.search(text)
    if m:
        effects.append(("discard", {"n": _qty(m), "target": "opp"}))

    # Tokens
    m = CREATE_TREASURE.search(text)
    if m:
        effects.append(("create_treasure", {"n": _qty(m)}))

    m = CREATE_CLUE.search(text)
    if m:
        # Clue = {2}, sac: draw a card. Goldfish proxy: +1 card now.
        effects.append(("draw", {"n": _qty(m)}))

    m = CREATE_FOOD.search(text)
    if m:
        # Food = {2}, sac: gain 3 life. Goldfish proxy.
        effects.append(("gain_life", {"n": 3 * _qty(m)}))

    m = CREATE_CR_TOKEN.search(text)
    if m:
        count = _qty(m, 1, default=1)
        p, t = m.group(2), m.group(3)
        kw_text = m.group(4) or ""
        kws = [k.strip() for k in re.split(r",| and ", kw_text) if k.strip()]
        effects.append(("create_token", {
            "count": count, "power": p, "toughness": t,
            "keywords": kws,
        }))

    # Ramp
    m = SEARCH_BASIC.search(text)
    if m:
        effects.append(("search_basic_land", {"n": _qty(m, default=1)}))

    # Reanimate
    if REANIMATE.search(text):
        effects.append(("return_gy_to_bf", {"filter_type": "creature"}))

    if RETURN_GY_HAND.search(text):
        effects.append(("return_gy_to_hand", {"filter_type": "creature"}))

    # Scry
    m = SCRY_N.search(text)
    if m:
        effects.append(("scry", {"n": _qty(m)}))

    return effects


# ─── Trigger extractor: splits oracle text by trigger and parses body ──

def parse_oracle(oracle_text: str, card_name: Optional[str] = None) -> dict:
    """Return {trigger_name: effect_list} for all recognized triggers."""
    result: dict = {}
    if not oracle_text:
        return result

    # Replace pronoun references for easier regex
    text = oracle_text.replace("\r\n", "\n")
    if card_name:
        # Some cards use their own name; swap in a generic token.
        text = text.replace(card_name, "~")

    # Split into lines / logical paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    for para in paragraphs:
        para_lower = para.lower()
        trigger_assigned = None
        body = para
        for pattern, trig_name in TRIGGER_PATTERNS:
            m = pattern.search(para)
            if m:
                trigger_assigned = trig_name
                # Body is everything after the matched prefix
                body = para[m.end():].strip()
                break

        effects = parse_segment(body)
        if not effects:
            continue

        if trigger_assigned is None:
            # No trigger prefix — treat as instant/sorcery effect
            trigger_assigned = "spell"

        result.setdefault(trigger_assigned, []).extend(effects)

    return result


# ─── Stats helper ─────────────────────────────────────────────────

def coverage_report(oracle_text: str, card_name: Optional[str] = None):
    """Return (parsed_effects, unparsed_paragraphs) for debugging."""
    parsed = parse_oracle(oracle_text, card_name)
    paragraphs = [p.strip() for p in (oracle_text or "").split("\n") if p.strip()]
    unparsed = []
    for p in paragraphs:
        if not parse_segment(p):
            # Check if it's at least TRIGGER-matched
            got_trigger = any(pat.search(p) for pat, _ in TRIGGER_PATTERNS)
            if not got_trigger:
                unparsed.append(p)
    return parsed, unparsed
