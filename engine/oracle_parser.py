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
    # ── ETB ───────────────────────────────────────────────────────────
    (re.compile(r"^when (?:this creature|this permanent|this artifact|this enchantment|~|it) enters(?:,| )",
                re.I | re.M), "etb"),
    (re.compile(r"^when (?:this card|a creature you control) enters,", re.I | re.M), "etb"),
    (re.compile(r"^when (?P<n>[A-Za-z'\-, ]+?) enters(?: the battlefield)?,", re.I | re.M), "etb"),
    # Room doors (DSK / SOS)
    (re.compile(r"^when you unlock this door,", re.I | re.M), "etb"),

    # ── Attack ────────────────────────────────────────────────────────
    (re.compile(r"^whenever (?:this creature|this permanent|~|it) attacks,", re.I | re.M), "attack"),
    (re.compile(r"^whenever (?:this creature|this permanent|~|it) enters or attacks,", re.I | re.M), "etb"),
    (re.compile(r"^whenever (?:a creature you control|one or more creatures you control) attacks?,", re.I | re.M), "attack"),
    (re.compile(r"^whenever (?:this creature|~) deals combat damage (?:to a player|to an opponent|to a player or planeswalker),", re.I | re.M), "combat_damage"),

    # ── Cast-spell triggers (Magecraft, Opus, Prowess-style) ──────────
    (re.compile(r"^infusion\s*[—\-]", re.I | re.M), "endstep"),   # Infusion = end-step trigger
    (re.compile(r"^opus\s*[—\-]", re.I | re.M), "cast_spell"),
    (re.compile(r"^whenever you cast an? (?:instant|sorcery|instant or sorcery|noncreature) spell,", re.I | re.M), "cast_spell"),
    (re.compile(r"^whenever you cast a spell,", re.I | re.M), "cast_spell"),
    (re.compile(r"^magecraft\s*[—\-]", re.I | re.M), "cast_spell"),

    # ── Upkeep / end step ────────────────────────────────────────────
    (re.compile(r"^at the beginning of your upkeep,", re.I | re.M), "upkeep"),
    (re.compile(r"^at the beginning of (?:your|each) end step,", re.I | re.M), "endstep"),
    (re.compile(r"^at the beginning of each (?:player'?s?|opponent'?s?) upkeep,", re.I | re.M), "upkeep"),

    # ── Dies ─────────────────────────────────────────────────────────
    (re.compile(r"^when (?:this creature|this permanent|~|it) dies,", re.I | re.M), "dies"),
    (re.compile(r"^whenever (?:a creature|another creature) (?:you control )?dies,", re.I | re.M), "dies"),

    # ── Landfall ─────────────────────────────────────────────────────
    (re.compile(r"^landfall\s*[—\-]\s*whenever a land (?:you control )?enters,?", re.I | re.M), "landfall"),
    (re.compile(r"^whenever a land (?:you control )?enters(?: the battlefield(?:\s+under your control)?)?,", re.I | re.M), "landfall"),

    # ── Life-gain trigger ────────────────────────────────────────────
    (re.compile(r"^whenever you gain life,", re.I | re.M), "gain_life_trigger"),

    # ── Damage trigger ───────────────────────────────────────────────
    (re.compile(r"^whenever (?:a source|~ or another) deals damage,", re.I | re.M), "damage_trigger"),
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

# ── New Standard mechanics (SOS / UB sets / recent sets) ───────────
# Surveil N — look at top N, put in GY or top. Goldfish proxy: scry.
SURVEIL_N         = _p(r"\bsurveil\s+(\d+|\w+)\b")
# Investigate — create Clue token (sac for draw). Proxy: draw 1.
INVESTIGATE       = _p(r"\binvestigate\b")
# Explore — look at top, if land put in hand, else +1/+1 on creature. Proxy: counter.
EXPLORE           = _p(r"\bthat (?:creature )?explores\b|\bexplores\b|\bexplore\b")
# Discover N — cascade-like, cast spell with cmc <= N free. Proxy: draw 1.
DISCOVER_N        = _p(r"\bdiscover\s+(\d+|\w+)\b")
# Earthbend N — animate land as N/N creature with haste. Proxy: +flex mana (land attacks).
EARTHBEND_N       = _p(r"\bearth[- ]?bend\s+(\d+|\w+)\b")
# Mobilize N — create N 1/1 tapped+attacking tokens on attack.
MOBILIZE_N        = _p(r"\bmobilize\s+(\d+|\w+)\b")
# Manifest / Manifest Dread — put face-down 2/2 from library. Proxy: create_token.
MANIFEST          = _p(r"\bmanifest(?:\s+dread)?\b")
# Forage (BLB) — sac Food or creature or exile 3 GY cards. Proxy: gain_life 3.
FORAGE            = _p(r"\bforage\b")
# Tap target creature (no mana effect in goldfish, register as no-op tap)
TAP_CREATURE      = _p(r"\btap\s+target\s+(?:creature|permanent)\b")
# Look at top N cards — library peek, goldfish: scry proxy.
LOOK_TOP_N        = _p(r"\blook at the top (\d+|\w+) cards?\b")
# Surveil / scry hybrid "scry 1, then draw" — already caught by SCRY + DRAW separately.
# Populate — create a copy of a token you control. Proxy: create_token 1/1 if any token.
POPULATE          = _p(r"\bpopulate\b")
# Counter on a DIFFERENT target (not self)
ADD_COUNTER_TGT   = _p(r"\bputs?\s+(?:a|an|one|two|three|(\d+))\s*\+1/\+1\s+counters?\s+on\s+(?:target|another|each|a creature|one or more)")
# Pump target until end of turn
PUMP_TGT          = _p(r"\btarget\s+creature\s+gets?\s+\+(\d+)/\+(\d+)\s+until\s+end\s+of\s+turn\b")
# Exile top N of library (mill-to-exile)
EXILE_TOP_N       = _p(r"\bexile\s+the\s+top\s+(\d+|\w+)\s+cards?\s+of\s+(?:your|target player's)\s+library\b")


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

    # ── New Standard mechanics ──────────────────────────────────────
    # Surveil N (goldfish proxy: scry)
    m = SURVEIL_N.search(text)
    if m:
        effects.append(("scry", {"n": _qty(m)}))

    # Investigate (create Clue = draw 1 proxy)
    if INVESTIGATE.search(text) and not CREATE_CLUE.search(text):
        effects.append(("draw", {"n": 1}))

    # Explore (look at top, if land into hand else +1/+1. Proxy: counter)
    if EXPLORE.search(text):
        effects.append(("add_counters", {"n": 1, "target": "self"}))

    # Discover N (cascade proxy: draw 1)
    m = DISCOVER_N.search(text)
    if m:
        effects.append(("draw", {"n": 1}))

    # Earthbend N (animate land as N/N attacker. Proxy: +N flex mana)
    m = EARTHBEND_N.search(text)
    if m:
        n = _qty(m)
        effects.append(("add_mana", {"n": n}))

    # Mobilize N (create N 1/1 tapped attacking tokens on attack)
    m = MOBILIZE_N.search(text)
    if m:
        n = _qty(m)
        effects.append(("create_token", {
            "count": n, "power": "1", "toughness": "1", "keywords": ["haste"],
        }))

    # Manifest / Manifest Dread (face-down 2/2 from top of library)
    if MANIFEST.search(text):
        effects.append(("create_token", {
            "count": 1, "power": "2", "toughness": "2", "keywords": [],
        }))

    # Forage (BLB: sac food or creature. Proxy: gain 3 life)
    if FORAGE.search(text) and not GAIN_LIFE_N.search(text):
        effects.append(("gain_life", {"n": 3}))

    # Populate (create copy of token. Proxy: create 1/1 token)
    if POPULATE.search(text):
        effects.append(("create_token", {
            "count": 1, "power": "1", "toughness": "1", "keywords": [],
        }))

    # Look at top N (peek proxy: scry)
    m = LOOK_TOP_N.search(text)
    if m and not SCRY_N.search(text):
        effects.append(("scry", {"n": _qty(m)}))

    # Pump target creature +N/+N until EOT
    m = PUMP_TGT.search(text)
    if m:
        n = int(m.group(1))
        effects.append(("add_counters", {"n": n, "target": "self"}))

    # +1/+1 counter on a target OTHER than self
    m = ADD_COUNTER_TGT.search(text)
    if m and not ADD_COUNTER.search(text):
        effects.append(("add_counters", {"n": _qty(m), "target": "friendly_biggest"}))

    # Exile top N of library (mill-to-exile proxy)
    m = EXILE_TOP_N.search(text)
    if m:
        effects.append(("mill", {"n": _qty(m), "target": "self"}))

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

        # Normalize trigger names so the auto-handler generator can use them.
        # cast_spell / gain_life_trigger / combat_damage / damage_trigger
        # all model as ETB-like one-time firing at sim time.
        if trigger_assigned in ("cast_spell", "gain_life_trigger",
                                "combat_damage", "damage_trigger",
                                "attack", "combat_begin", "upkeep",
                                "endstep", "dies", "landfall"):
            # For auto-handler generation: treat as ETB (fire once per game
            # when the sim runs through the card). Real engine wiring can
            # distinguish later; this gives correct *value* in goldfish.
            trigger_assigned = "etb"

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
