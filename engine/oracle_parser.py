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

    # ── Draw trigger ─────────────────────────────────────────────────
    (re.compile(r"^whenever you draw a card,", re.I | re.M), "draw_trigger"),
    (re.compile(r"^whenever (?:a player|you) (?:draws?|draw) (?:a|one or more) cards?,", re.I | re.M), "draw_trigger"),

    # ── Cast triggers (cast spells, ETB-on-cast) ─────────────────────
    (re.compile(r"^when you cast this spell,", re.I | re.M), "cast_trigger"),
    (re.compile(r"^when you cast ~,", re.I | re.M), "cast_trigger"),
    (re.compile(r"^whenever an opponent casts (?:a|their first|an? instant|an? sorcery|a noncreature)? ?spell,", re.I | re.M), "cast_spell"),
    (re.compile(r"^whenever a player casts a spell,", re.I | re.M), "cast_spell"),

    # ── More ETB variants ─────────────────────────────────────────────
    (re.compile(r"^whenever (?:another|a) (?:creature|permanent|nonland permanent) (?:you control )?enters(?: the battlefield)?,", re.I | re.M), "etb"),
    (re.compile(r"^whenever a (?:creature|permanent) enters the battlefield under (?:your|an opponent's) control,", re.I | re.M), "etb"),
    (re.compile(r"^when this permanent (?:enters|transforms),", re.I | re.M), "etb"),

    # ── Face-up / disguise / morph ───────────────────────────────────
    (re.compile(r"^when (?:this creature|~) is turned face up,", re.I | re.M), "etb"),
    (re.compile(r"^when ~ is turned face up or (?:this creature|~) enters,", re.I | re.M), "etb"),

    # ── More attack / combat variants ────────────────────────────────
    (re.compile(r"^whenever you attack,", re.I | re.M), "attack"),
    (re.compile(r"^whenever (?:this creature|~) attacks? alone,", re.I | re.M), "attack"),
    (re.compile(r"^whenever (?:this creature|~) blocks? or becomes? blocked,", re.I | re.M), "attack"),
    (re.compile(r"^whenever (?:this creature|~) (?:deals|dealt) (?:combat )?damage,", re.I | re.M), "combat_damage"),

    # ── More death / graveyard triggers ──────────────────────────────
    (re.compile(r"^whenever (?:a nontoken|another nontoken|a|an) (?:creature|permanent) (?:you control |an opponent controls )?(?:is put into a graveyard|dies),", re.I | re.M), "dies"),
    (re.compile(r"^when ~ (?:is put into|enters) (?:a|the) graveyard(?: from anywhere)?,", re.I | re.M), "dies"),

    # ── Sacrifice / pay triggers ─────────────────────────────────────
    (re.compile(r"^whenever you sacrifice a (?:permanent|creature|artifact|Food),", re.I | re.M), "dies"),

    # ── Counter / modified triggers ───────────────────────────────────
    (re.compile(r"^whenever (?:a|one or more) \+1/\+1 (?:counter|counters) (?:is|are) (?:put on|removed from) (?:a creature|~|this creature),", re.I | re.M), "etb"),

    # ── Landfall variant ─────────────────────────────────────────────
    (re.compile(r"^whenever you (?:play|put) a land,", re.I | re.M), "landfall"),

    # ── Starting turns / combat ──────────────────────────────────────
    (re.compile(r"^at the beginning of (?:each|your) combat(?: on your turn)?,", re.I | re.M), "combat_begin"),
    (re.compile(r"^at the beginning of each (?:other player's|opponent's) (?:upkeep|end step),", re.I | re.M), "upkeep"),
    (re.compile(r"^at the beginning of your first main phase,", re.I | re.M), "upkeep"),
    (re.compile(r"^the first time (?:you|a source) (?:draws?|deals?) (?:a card|damage) (?:each turn|this turn),", re.I | re.M), "draw_trigger"),

    # ── Named mechanic keywords (DSK / BLB / LCI / DFT / FIN / TLA / SOS) ──
    # Eerie (DSK): whenever an enchantment you control enters or Room unlocked
    (re.compile(r"^eerie\s*[—\-]", re.I | re.M), "etb"),
    # Alliance (LCI): whenever another creature you control enters
    (re.compile(r"^alliance\s*[—\-]", re.I | re.M), "etb"),
    # Flurry (DSK): whenever you cast your second spell each turn
    (re.compile(r"^flurry\s*[—\-]", re.I | re.M), "cast_spell"),
    # Vivid (various): when this creature enters
    (re.compile(r"^vivid\s*[—\-]", re.I | re.M), "etb"),
    # Survival (FIN): at the beginning of your end step, if you gained life
    (re.compile(r"^survival\s*[—\-]", re.I | re.M), "endstep"),
    # Firebending N (TLA Avatar): whenever this creature attacks, deal N damage
    (re.compile(r"^firebending \d+\s*[—\-\(]", re.I | re.M), "attack"),
    (re.compile(r"^firebending \d+\s*[—\-]", re.I | re.M), "attack"),
    # Saddle attacks
    (re.compile(r"^whenever (?:this creature|~) attacks while saddled,", re.I | re.M), "attack"),
    # Leaves battlefield
    (re.compile(r"^when (?:this creature|this permanent|~|it) (?:leaves|is removed from) the battlefield,", re.I | re.M), "dies"),
    # Second draw trigger
    (re.compile(r"^whenever you draw your second card (?:each turn|this turn),", re.I | re.M), "draw_trigger"),
    # Expend (DFT racing mechanic)
    (re.compile(r"^whenever you expend \d+,", re.I | re.M), "cast_spell"),
    # Whenever an artifact enters under your control
    (re.compile(r"^whenever an? (?:artifact|equipment) (?:you control )?enters,", re.I | re.M), "etb"),
    # When enchanted creature is dealt damage / target is dealt damage
    (re.compile(r"^when(?:ever)? (?:enchanted|equipped) (?:creature|permanent) (?:is|deals|takes),", re.I | re.M), "damage_trigger"),
    # Whenever you cast a spell with [quality]
    (re.compile(r"^whenever you cast a spell with (?:mana value|converted mana cost),", re.I | re.M), "cast_spell"),
    # Another creature you control with [condition]
    (re.compile(r"^whenever another creature you control (?:with|that has),", re.I | re.M), "etb"),
    # Prowess reminder text as paragraph starter (strip via keyword_only in pipeline)
    # Start your engines! (DFT) — mechanical trigger from race
    (re.compile(r"^start your engines!", re.I | re.M), "etb"),
    # Limit (FIN) — once per game activation reminder, skip trigger here but register
    # At the beginning of your next turn
    (re.compile(r"^at the beginning of your next (?:main phase|upkeep|turn),", re.I | re.M), "upkeep"),
    # "at the beginning of combat on your turn" (common variant missed by earlier pattern)
    (re.compile(r"^at the beginning of combat on your turn,", re.I | re.M), "combat_begin"),
    # Bargain (WOE) — sacrifice a token/artifact/enchantment for a bonus. Treat as ETB.
    (re.compile(r"^bargain\s*[—\-]", re.I | re.M), "etb"),
    # Impending N (DSK/SOS) — countdown, enters with N time counters, becomes creature
    (re.compile(r"^impending\s+\d+\s*[—\-]", re.I | re.M), "etb"),
    # Increment (SOS) — cast trigger that scales counter
    (re.compile(r"^increment\s*[—\-]?", re.I | re.M), "cast_spell"),
    # Whenever this creature or another creature you control [condition]
    (re.compile(r"^whenever (?:this creature or another|this or another) creature (?:you control )?(?:enters|attacks|dies),", re.I | re.M), "etb"),
    # Whenever a creature you control with [quality] attacks
    (re.compile(r"^whenever a creature you control with (?:the greatest|power|toughness|a \+1/\+1) (?:counter|power|among)?,?", re.I | re.M), "attack"),
    # Whenever you cast a spell with mana value N or greater
    (re.compile(r"^whenever you cast a spell with (?:mana value|converted mana cost) \d+\s*(?:or (?:greater|more))?,", re.I | re.M), "cast_spell"),
    # Whenever this creature attacks while you control [condition]
    (re.compile(r"^whenever (?:this creature|~) attacks while you control (?:at least )?\d+", re.I | re.M), "attack"),
    # Bolster N (TDM) — put N counters on weakest creature you control
    (re.compile(r"^bolster\s+\d+\b", re.I | re.M), "etb"),
    # Renown N (TDM) — when this deals combat damage to player, put N counters
    (re.compile(r"^renown\s+\d+\b", re.I | re.M), "combat_damage"),
    # Whenever this creature becomes blocked
    (re.compile(r"^whenever (?:this creature|~) becomes blocked,", re.I | re.M), "combat_damage"),
    # When you discard this card / from hand
    (re.compile(r"^when(?:ever)? you discard (?:this card|a card),", re.I | re.M), "dies"),
    # Suspect mechanic (MKM) — "when ~ becomes suspected"
    (re.compile(r"^when(?:ever)? (?:this creature|~) (?:becomes suspected|is suspected),", re.I | re.M), "etb"),
    # Collect evidence N (MKM) — pay N worth of cards from GY
    (re.compile(r"^collect evidence\s+\d+", re.I | re.M), "spell"),
    # Whenever a player discards a card
    (re.compile(r"^whenever (?:a player|an opponent) discards? (?:a|one or more) cards?,", re.I | re.M), "dies"),
    # Whenever a creature you control attacks alone
    (re.compile(r"^whenever (?:a creature|one or more creatures) you control attacks? alone,", re.I | re.M), "attack"),
    # Whenever you cast a spell from [exile / anywhere / a zone]
    (re.compile(r"^whenever you cast (?:a|an) (?:\w+\s+)*spell from (?:exile|anywhere|your graveyard),", re.I | re.M), "cast_spell"),
    # At the beginning of each player's draw step
    (re.compile(r"^at the beginning of each player'?s? (?:draw step|upkeep|turn),", re.I | re.M), "draw_trigger"),
    # When enchanted creature is dealt damage / destroyed
    (re.compile(r"^when(?:ever)? enchanted (?:creature|permanent) (?:is dealt|would be dealt) (?:combat )?damage,", re.I | re.M), "damage_trigger"),
    # Whenever this creature blocks or becomes blocked
    (re.compile(r"^whenever (?:this creature|~) blocks? or becomes? blocked,?", re.I | re.M), "attack"),
    # Whenever you discard one or more cards
    (re.compile(r"^whenever you discard (?:one or more|a) cards?,", re.I | re.M), "dies"),
    # Whenever a creature is dealt damage (global damage trigger)
    (re.compile(r"^whenever (?:a|any) creature is dealt damage,", re.I | re.M), "damage_trigger"),
    # Whenever one or more creatures leave the battlefield
    (re.compile(r"^whenever one or more creatures? (?:leave|leaves) the battlefield,", re.I | re.M), "dies"),
    # Whenever you untap one or more permanents
    (re.compile(r"^whenever you untap (?:one or more|a|an) permanents?,", re.I | re.M), "etb"),
    # At the beginning of each player's end step
    (re.compile(r"^at the beginning of (?:each|every) (?:player'?s?\s+)?end step,", re.I | re.M), "endstep"),
    # Whenever this creature or another [type] you control [action]
    (re.compile(r"^whenever (?:this creature|~) or another (?:\w+\s+)*(?:you\s+control\s+)?(?:enters?|attacks?|dies?),", re.I | re.M), "etb"),
    # Whenever a nontoken [type] creature you control
    (re.compile(r"^whenever a nontoken(?:,\s*non-\w+)?\s+creature you control (?:enters?|attacks?|dies?),", re.I | re.M), "etb"),
    # Whenever you cast your first spell with {X} in its mana cost (Zimone)
    (re.compile(r"^whenever you cast (?:your\s+first\s+)?(?:an?\s+)?spell with \{[Xx]\}\b", re.I | re.M), "cast_spell"),
    # Whenever one or more creatures you control deal combat damage to a player
    (re.compile(r"^whenever one or more creatures you control deal combat damage to (?:a player|an opponent),", re.I | re.M), "combat_damage"),
    # Whenever an enchantment you control enters (eerie variant without keyword)
    (re.compile(r"^whenever an? enchantment (?:you control )?enters(?: the battlefield)?,", re.I | re.M), "etb"),
    # Whenever you tap a land for mana (land tap trigger)
    (re.compile(r"^whenever you tap (?:a|an) (?:land|basic land) for mana,", re.I | re.M), "cast_spell"),
    # Whenever this Vehicle attacks
    (re.compile(r"^whenever (?:this vehicle|~) attacks,", re.I | re.M), "attack"),
    # Whenever a token you control enters/attacks/dies/is created
    (re.compile(r"^whenever (?:a|one or more) tokens? you control (?:enters?|attacks?|dies?|is created),", re.I | re.M), "etb"),
    # Whenever you put one or more counters on a permanent (proliferate-like)
    (re.compile(r"^whenever you put (?:a|one or more) (?:\+1/\+1\s+)?counters? on (?:a|~|this|target),", re.I | re.M), "etb"),
    # At the beginning of your draw step / first main phase
    (re.compile(r"^at the beginning of your (?:draw step|first main phase),", re.I | re.M), "upkeep"),
    # Whenever a player casts their [Nth] spell each turn
    (re.compile(r"^whenever (?:a player|you) cast(?:s)? (?:their|your)\s+(?:first|second|third) spell (?:each turn|this turn),", re.I | re.M), "cast_spell"),
    # Whenever this creature becomes tapped
    (re.compile(r"^whenever (?:this creature|~) becomes? tapped,", re.I | re.M), "etb"),
    # Whenever this creature deals damage (broader)
    (re.compile(r"^whenever (?:this creature|~) deals damage to (?:a player|an opponent|a creature),", re.I | re.M), "combat_damage"),
    # Whenever this creature is dealt damage
    (re.compile(r"^whenever (?:this creature|~) is dealt (?:combat )?damage,", re.I | re.M), "combat_damage"),
    # Whenever you activate an ability
    (re.compile(r"^whenever you activate an? (?:ability|loyalty ability),", re.I | re.M), "cast_spell"),
    # Whenever a Villain/Hero/[type] you control does X
    (re.compile(r"^whenever (?:a|another)\s+\w+\s+you\s+control\s+(?:attacks?|enters?|dies?),", re.I | re.M), "attack"),
    # Whenever you attack with one or more [type]
    (re.compile(r"^whenever you attack with (?:one or more|\d+\+?|at least \d+)\s+\w+s?,", re.I | re.M), "attack"),
    # Whenever this creature or a [type] you control does X
    (re.compile(r"^whenever (?:this creature or|~or)?\s*(?:another)?\s*\w+\s+you\s+control\s+attacks?,", re.I | re.M), "attack"),
    # When this creature deals combat damage (variant without "to player")
    (re.compile(r"^when (?:this creature|~) deals combat damage(?:\s+to a\s+\w+)?,", re.I | re.M), "combat_damage"),
    # Whenever you commit a crime (OTJ)
    (re.compile(r"^whenever you commit a crime,", re.I | re.M), "cast_spell"),
    # Case cards (MKM) — "To solve, [condition]" style
    (re.compile(r"^when (?:you|this enchantment) (?:solve|is solved),?", re.I | re.M), "etb"),
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
BOUNCE_TGT        = _p(r"\breturn\s+(?:up\s+to\s+\w+\s+(?:other\s+)?)?(?:target|a)\s+(?:\w+\s+){0,3}(?:creature|nonland\s+permanent|permanent)\s+to\s+(?:its|their|your)\s+owner'?s?\s+hand\b")

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
COUNTER_SPELL     = _p(r"\bcounter\s+target\s+(?:spell|noncreature spell|creature spell|spell unless)")

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

# ── More effect patterns ────────────────────────────────────────────
# Pump all friendly creatures until EOT
PUMP_ALL_CTRL     = _p(r"\bcreatures\s+you\s+control\s+(?:each\s+)?gets?\s+\+(\d+)/\+(\d+)")
PUMP_EACH_CTRL    = _p(r"\beach\s+(?:creature|nonland permanent)\s+you\s+control\s+gets?\s+\+(\d+)/\+(\d+)")
# Exile from a graveyard (GY hate / flash proxy)
EXILE_FROM_GY     = _p(r"\bexile\s+target\s+(?:card|creature|instant|sorcery|artifact|enchantment)\s+(?:card\s+)?from\s+(?:a|your|their|an opponent's)\s+graveyard\b")
# Untap target — tap/untap effects (no real goldfish value, register to avoid hand-write)
UNTAP_TARGET      = _p(r"\buntap\s+(?:target|up to (?:\d+|\w+))\s+(?:creature|permanent)s?\b")
TAP_UP_TO         = _p(r"\btap\s+up\s+to\s+(\d+|\w+)\s+(?:target\s+)?(?:creature|permanent)s?\b")
# Attach to creature (equipment / aura — no-op in goldfish)
ATTACH_TO         = _p(r"\battach\s+(?:~|it|this)\s+to\s+(?:target|a)\s+(?:creature|permanent)\b")
# Put a [non +1/+1] counter on target (loyalty, -1/-1, charge, etc.)
COUNTER_ON_TGT    = _p(r"\bputs?\s+(?:a|an|one|\d+)\s+(\w+)\s+counter\s+on\s+(?:target|each|it|~)\b")
# Return [card type] from GY to hand (broader than RETURN_GY_HAND)
RETURN_GY_HAND2   = _p(r"\breturn\s+target\s+(?:\w+\s+)?(?:card|permanent|spell)\s+from\s+(?:your|a)\s+graveyard\s+to\s+(?:your|their)\s+hand\b")
# "Return ~ to its owner's hand" (self-bounce)
SELF_BOUNCE       = _p(r"\breturn\s+(?:~|it|this\s+(?:creature|permanent|card))\s+to\s+(?:its|your|their)\s+owner'?s?\s+hand\b")
# Draw then discard (looting)
DRAW_DISCARD      = _p(r"\bdraws?\s+(?:a|\d+|\w+)\s+cards?\s*,?\s*then\s+discards?\s+(?:a|\d+|\w+)\s+cards?\b")
DISCARD_DRAW      = _p(r"\bdiscards?\s+(?:a|\d+|\w+)\s+cards?\s*,?\s*(?:then|if (?:you|they) do)\s+draws?\s+(?:that many|a|\d+|\w+)\s+cards?\b")
# Amass N (zombie army token)
AMASS_N           = _p(r"\bamass\s+(?:\w+\s+)?(\d+|\w+)\b")
# Proliferate (add counter to each — goldfish proxy: +1 to biggest)
PROLIFERATE       = _p(r"\bproliferate\b")
# Connive N (draw N, discard N, +1/+1 for nonland)
CONNIVE_N         = _p(r"\bconnive(?:\s+(\d+|\w+))?\b")
# Exert (tap, doesn't untap next turn, gain bonus — goldfish: just use the bonus)
# Saga chapter — "I," "II," etc. starters (already handled by SAGA_EFFECTS, skip)
# "You may cast target card" / free cast proxy → draw 1
FREE_CAST_PROXY   = _p(r"\byou may cast (?:it|that card|target \w+ card)\s+(?:from exile\s+)?without paying its mana cost\b")
# "Exile target spell" → counter proxy
EXILE_TGT_SPELL   = _p(r"\bexile\s+target\s+spell\b")
# Ninjutsu / similar return+replace (complex, proxy: draw)
NINJUTSU          = _p(r"\bninjutsu\b")
# Adapt N (if no +1/+1 counters, put N on it)
ADAPT_N           = _p(r"\badapt\s+(\d+|\w+)\b")
# Broader pump: "target creature [you control] gets +N/+M [and gains X] until EOT"
PUMP_TGT_BROAD    = _p(r"\btarget\s+(?:creature|permanent)(?:\s+you\s+control)?\s+gets?\s+\+(\d+)/\+(\d+)")
# Self-pump by card name: "[Any Name] gets +N/+N until end of turn" (magecraft etc.)
SELF_NAMED_PUMP   = _p(r"\b[A-Z][a-zA-Z',]+\s+gets?\s+\+(\d+)/\+(\d+)\s+until\s+end\s+of\s+turn\b")
# Whenever you cast [your first / a] spell with {X} in its mana cost
CAST_X_SPELL      = _p(r"\bwhenever you cast (?:your\s+first\s+)?(?:an?\s+)?spell with \{[Xx]\}\b")
# Negative pump: "target creature gets -N/-M until EOT"
SHRINK_TGT        = _p(r"\btarget\s+(?:creature|permanent)\s+gets?\s+-(\d+)/-(\d+)\b")
# Copy token: "create a token that's a copy of [target creature]"
CREATE_COPY_TOKEN = _p(r"\bcreates?\s+(?:a|one|two|three|\d+)\s+tokens?\s+that'?s?\s+(?:a\s+)?(?:copies?|copy)\s+of")
# You gain control of target creature (steal effect — proxy: draw 1)
GAIN_CONTROL      = _p(r"\byou\s+gain\s+control\s+of\s+target\b")
# Target player gains control (opponent steal — proxy: no-op register)
TGT_PLAYER_DRAWS  = _p(r"\btarget\s+player\s+draws?\s+(\d+|\w+)\s+cards?\b")
# Return up to N targets to hand (mass bounce)
RETURN_UP_TO      = _p(r"\breturn\s+(?:up\s+to\s+)?(?:\d+|\w+)\s+target\s+(?:creature|permanent)s?\s+to\s+(?:their|its)\s+owner'?s?\s+hands?\b")
# Broader bounce: "return target [creature or Vehicle / artifact or creature] to hand"
BOUNCE_BROAD      = _p(r"\breturn\s+target\s+(?:creature\s+or\s+\w+|\w+\s+or\s+creature|nonland\s+permanent|permanent)\s+(?:(?:you|an\s+opponent|a\s+player|defending\s+player)\s+controls?\s+)?to\s+(?:its|their)\s+owner'?s?\s+hand\b")
# Self life loss: "you lose N life"
SELF_LOSE_LIFE    = _p(r"\byou\s+lose\s+(\d+|\w+)\s+life\b")
# Exile-until-nonland (cascade/discover variant): "exile cards from top until you exile a nonland card"
EXILE_UNTIL       = _p(r"\bexile\s+cards?\s+from\s+the\s+top\s+of\s+your\s+library\s+until\b")
# Named token: "create [Name], a legendary N/N ... creature token"
CREATE_NAMED_TOKEN = _p(r"\bcreates?\s+[A-Z][a-zA-Z',\s]+,\s+a\s+(?:legendary\s+)?(?:\d+)/(?:\d+)\s+.*?creature\s+tokens?\b")
# +1/+1 counter on a named target (TMNT: "put a +1/+1 counter on Donatello")
ADD_COUNTER_NAMED  = _p(r"\bputs?\s+(?:a|an|one|\d+)\s+\+1/\+1\s+counters?\s+on\s+[A-Z][a-z]+\b")
# Discard all / hand and redraw (Wheel of Fortune effect)
WHEEL_EFFECT       = _p(r"\bdiscard\s+(?:your\s+hand|all\s+cards\s+in\s+your\s+hand),\s+then\s+draws?\b")
# Gains [keyword] until your next turn (extended grant duration)
GRANT_KW_NEXT_TURN = _p(r"\bgains?\s+(?:flying|trample|first strike|double strike|deathtouch|lifelink|haste|hexproof|reach|indestructible|menace|vigilance)\s+until\s+your\s+next\s+turn\b")
# Broader power/toughness debuff: "[creature] gets -N/-0 or -N/-N" (flexible wording)
DEBUFF_BROAD       = _p(r"\bgets?\s+-(\d+)/-\d+\s+(?:and\s+loses?\s+\w+\s+)?until\s+(?:end\s+of\s+turn|your\s+next\s+turn)\b")
# Plays an additional land each turn (land bonus)
EXTRA_LAND         = _p(r"\bplay\s+(?:an?\s+)?additional\s+land\b")
# "each player draws" / "each player discards"
EACH_PLAYER_DRAWS  = _p(r"\beach\s+player\s+draws?\s+(\d+|\w+)\s+cards?\b")
EACH_PLAYER_DISC   = _p(r"\beach\s+player\s+discards?\s+(?:their\s+hand|\d+|\w+\s+cards?)\b")
# "Tap all creatures [an opponent controls / you don't control]" (board tap/stasis)
TAP_ALL_CREATURES  = _p(r"\btap\s+all\s+(?:creatures|creatures\s+(?:an\s+opponent\s+controls|you\s+don'?t\s+control))\b")
# "You get N poison counters" or "target player gets N poison counters"
POISON_COUNTER     = _p(r"\b(?:you|target\s+player|target\s+opponent)\s+gets?\s+(?:\d+|\w+)\s+poison\s+counters?\b")
# Return target [enchantment/artifact/permanent] to [hand/library/play]
RETURN_TGT_BROAD   = _p(r"\breturn\s+target\s+(?:enchantment|artifact|noncreature|instant or sorcery)\s+(?:card\s+)?(?:from\s+(?:your|a)\s+graveyard\s+)?to\s+(?:your|its\s+owner'?s?)\s+hand\b")
# "Create N [type] tokens" where N >= 2 (multi-token creation not caught)
CREATE_MULTI_TOKEN = _p(r"\bcreates?\s+(?:two|three|four|five|\d+)\s+(?:\d+/\d+\s+)?(?:\w+\s+){1,4}creature\s+tokens?\b")
# Investigate multiple times / specific triggers
INVESTIGATE_N      = _p(r"\binvestigate\s+(?:twice|three\s+times?|\d+\s+times?)\b")
# You may put [card type] from hand onto battlefield (free play)
FREE_PLAY          = _p(r"\byou\s+may\s+put\s+(?:a|an|target|\w+)\s+(?:land|creature|artifact|enchantment|permanent)\s+card\s+from\s+(?:your\s+)?hand\s+onto\s+the\s+battlefield\b")
# "Destroy all [type]" (mass removal variants)
DESTROY_ALL_TYPE   = _p(r"\bdestroy\s+all\s+(?:artifacts?|enchantments?|nonlands?|noncreature|tokens?)\b")
# "Exile all cards from all graveyards" (GY wipe)
EXILE_ALL_GY       = _p(r"\bexile\s+all\s+(?:cards?\s+from|permanents?\s+from)\s+(?:all\s+)?graveyards?\b")
# "[Creature] can't be the target of spells..." (hexproof-like reminder)
HEXPROOF_REMINDER  = _p(r"\bcan'?t\s+be\s+the\s+target\s+of\s+spells\b")
# Return target [non-creature type] to hand (auras, equipment, etc.)
RETURN_TGT_TYPE   = _p(r"\breturn\s+target\s+(?:land|enchantment|artifact|spell|instant|sorcery|aura)\s+(?:card\s+)?to\s+(?:its|your|their|a player'?s?)\s+(?:hand|owner'?s?\s+hand)\b")
# "tap target creature you control" (self-tap, not opponent's)
TAP_CTRL_CREATURE  = _p(r"\btap\s+target\s+(?:creature|permanent)\s+you\s+control\b")
# Exile target permanent until [event] (Oblivion Ring style)
EXILE_UNTIL_EVENT  = _p(r"\bexile\s+target\s+(?:nonland\s+)?(?:creature|artifact|enchantment|permanent)\s+(?:you\s+don'?t\s+control\s+)?until\s+(?:end\s+of\s+turn|this leaves|~ leaves|it leaves)\b")
# "You may have [creature] assign its combat damage as though it wasn't blocked"
TRAMPLE_TEXT       = _p(r"\bassign(?:s)?\s+(?:its\s+)?(?:combat\s+)?damage\s+as\s+though\b")
# "Sacrifice [permanent]" as cost/effect — various forms
SACRIFICE_PERM     = _p(r"\bsacrifice\s+(?:a|an|target|this|~|all)\s+(?:creature|artifact|enchantment|permanent|land|token|Treasure|Clue|Food)\b")
# "Put target permanent on top of its owner's library" (broader tuck)
TUCK_TOP_LIB       = _p(r"\bput\s+(?:it|target\s+\w+)\s+on\s+top\s+of\s+(?:its\s+owner'?s?|your|their)\s+library\b")
# [Number] target creatures get +N/+M (buff multiple targets)
MULTI_PUMP         = _p(r"\bup\s+to\s+(?:two|three|\d+)\s+target\s+creatures\s+(?:you\s+control\s+)?gets?\s+\+(\d+)/\+(\d+)\b")
# Role token (WOE): "create a [Wicked/Cursed/Monster/Royal/Sorcerer/Young Hero] Role token"
ROLE_TOKEN        = _p(r"\bcreates?\s+a\s+(?:wicked|cursed|monster|royal|sorcerer|young hero|instrument of the machine)\s+role\s+token\b")
# Increment (SOS): "Whenever you cast a spell, if mana spent > N, [effect]"
# Model as a conditional pump trigger -- proxy as scry (card selection value)
INCREMENT         = _p(r"\bincrement\b")
# Prepared (SOS): "this creature enters prepared" -- copy-spell trigger
# Model as a free-cast echo: treat as getting a second copy (big ETB value)
PREPARED          = _p(r"\bthis (?:creature|card|permanent) enters prepared\b")
# You get an emblem (planeswalker ultimate — register as big effect proxy)
EMBLEM            = _p(r"\byou\s+get\s+an\s+emblem\b")
# You take an extra turn / additional combat phase
EXTRA_TURN        = _p(r"\byou\s+(?:take\s+an?\s+extra\s+turn|get\s+an?\s+additional\s+(?:combat|main)\s+phase)\b")
# It / this becomes a [type] creature until EOT (animating artifacts/lands)
BECOMES_CREATURE  = _p(r"\b(?:it|~|this (?:permanent|card|artifact|land))\s+becomes?\s+a\s+(?:\d+/\d+\s+)?(?:\w+\s+)*creature\b")
# "For each [X], [effect]" — scaling effect (gets +N/+M, deals N damage, etc.)
FOR_EACH_SCALE    = _p(r"\bfor\s+each\s+(?:\w+\s+){1,5}(?:you\s+control|in\s+your|under\s+your|you\s+own|among\s+cards)\b")
# Exile target permanent/creature from battlefield (removal)
EXILE_TGT_PERM    = _p(r"\bexile\s+target\s+(?:creature|artifact|enchantment|permanent|nonland permanent|planeswalker)\b")
# Put on top of library (minor — proxy as scry)
PUT_TOP_LIB       = _p(r"\bput(?:s)?\s+(?:it|~|target \w+|that \w+)\s+on\s+top\s+of\s+(?:its owner's|your|their)\s+library\b")
# Put cards into hand from library (tutor proxy)
TUTOR_TO_HAND     = _p(r"\bsearch\s+your\s+library\s+for\s+(?:a|an|up to \w+)?\s*(?:\w+\s+)*card\s*(?:,|and)")
# Create a token copy of target creature (clone variant)
COPY_SPELL_TOKEN  = _p(r"\bcopy\s+(?:of\s+)?(?:that\s+spell|target\s+(?:instant|sorcery|spell))\b")
# "Put N +1/+1 counters on each" / on target — additional counter variant
PUT_COUNTERS_EACH = _p(r"\bput\s+(?:a|\d+|\w+)\s+\+1/\+1\s+counters?\s+on\s+each\b")
# Gain life equal to the number of [X] you control / in play
GAIN_LIFE_COUNT   = _p(r"\byou\s+gain\s+(?:\d+|\w+)\s+life\s+for\s+each\b")
# "Search your library for a land card and put it into your hand"
TUTOR_LAND_HAND   = _p(r"\bsearch\s+your\s+library\s+for\s+(?:a|up to \w+)?\s*(?:basic\s+)?land\s+card\s*(?:and\s+)?put\s+(?:it|(?:that|those) cards?)\s+into\s+your\s+hand\b")
# Target creature fights target creature (fight effect)
FIGHT             = _p(r"\btarget\s+creature\s+(?:you\s+control\s+)?fights?\s+(?:target|another)")
# Bolster N — put N counters on weakest friendly creature
BOLSTER_N         = _p(r"\bbolster\s+(\d+|\w+)\b")
# Renown N — put N counters when deals combat damage to player
RENOWN_N          = _p(r"\brenown\s+(\d+|\w+)\b")
# Cycling — activated ability, no ETB effect
CYCLING           = _p(r"\bcycling\s*\{")
# Level up — activated, no ETB
LEVEL_UP          = _p(r"\blevel\s+up\s*\{")
# Keyword grant: "gains [keyword] until end of turn" — register as no-op
GRANT_KEYWORD     = _p(r"\bgains?\s+(?:flying|trample|first strike|double strike|deathtouch|lifelink|haste|hexproof|reach|indestructible|menace|vigilance|ward \{[^}]+\})\s+until\s+(?:end\s+of\s+turn|your\s+next\s+turn)\b")
# Power debuff: "gets -N/-0 until end of turn" (no toughness change)
DEBUFF_POWER      = _p(r"\bgets?\s+-(\d+)/-0\s+until\s+(?:end\s+of\s+turn|your\s+next\s+turn)\b")
# All other creatures get -N/-M (sweeper/debuff)
DEBUFF_ALL        = _p(r"\b(?:all|each)\s+(?:other\s+)?creatures?\s+(?:get|gets?)\s+-(\d+)/-(\d+)\s+until\s+end\s+of\s+turn\b")
# Destroy up to one target artifact/enchantment
DESTROY_TGT_ARTENC = _p(r"\bdestroy\s+(?:up\s+to\s+one\s+)?target\s+(?:artifact|enchantment|noncreature artifact|artifact or enchantment)\b")
# Return creature CARDS from graveyard (broader than REANIMATE)
RETURN_CR_CARDS_GY = _p(r"\breturn\s+(?:up\s+to\s+(?:\d+|\w+)\s+)?target\s+creature\s+cards?\s+from\s+(?:your|a|target player's)\s+graveyard\s+to\s+(?:the\s+battlefield|your\s+hand)\b")
# Loses all abilities until end of turn
LOSES_ABILITIES   = _p(r"\bloses\s+all\s+abilities\s+until\s+end\s+of\s+turn\b")
# "Other [type] you control get +N/+M" — lord effect
OTHER_CREATURES_GET = _p(r"\bother\s+(?:\w+\s+)*creatures?\s+you\s+control\s+gets?\s+\+(\d+)/\+(\d+)\b")
# Enchanted / equipped creature static bonuses
ENCHANTED_GETS    = _p(r"\benchanted\s+(?:creature|permanent)\s+gets?\s+\+(\d+)/\+(\d+)")
EQUIPPED_GETS     = _p(r"\bequipped\s+creature\s+gets?\s+\+(\d+)/\+(\d+)")
# Firebending N damage (TLA Avatar)
FIREBENDING_DMG   = _p(r"\bfirebending\s+(\d+)\b")
# "deals damage equal to its power" / "deals X damage to target" variants
DEALS_POWER_DMG   = _p(r"\bdeals?\s+damage\s+equal\s+to\s+(?:its|their|~'?s?)\s+power\b")
# "each opponent loses N life" (symmetric drain variant)
EACH_OPP_LOSES    = _p(r"\beach\s+opponent\s+loses?\s+(\d+|\w+)\s+life\b")
# "you gain life equal to / you gain N life" broader
GAIN_LIFE_BROAD   = _p(r"\byou\s+gain\s+(?:life\s+equal\s+to|(\d+|\w+)\s+life)\b")


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

    # ── Additional effect patterns ────────────────────────────────────
    # Pump all friendly creatures +N/+M until EOT
    m = PUMP_ALL_CTRL.search(text) or PUMP_EACH_CTRL.search(text)
    if m:
        n = int(m.group(1))
        effects.append(("add_counters", {"n": n, "target": "all_friendly"}))

    # Return self to hand (self-bounce — register as no-op placeholder)
    if SELF_BOUNCE.search(text) and not effects:
        effects.append(("scry", {"n": 0}))

    # Return broader card type from GY to hand
    if RETURN_GY_HAND2.search(text) and not RETURN_GY_HAND.search(text):
        effects.append(("return_gy_to_hand", {"filter_type": "any"}))

    # Exile from graveyard (GY hate — no goldfish value, register to avoid hand-write)
    if EXILE_FROM_GY.search(text) and not effects:
        effects.append(("scry", {"n": 0}))

    # Untap target / tap up to N (register, no goldfish combat value)
    if (UNTAP_TARGET.search(text) or TAP_UP_TO.search(text)) and not effects:
        effects.append(("scry", {"n": 0}))

    # Draw then discard (looting) — net 0 cards but filters hand
    m = DRAW_DISCARD.search(text)
    if m and not DRAW_N.search(text) and not DRAW_ONE_ALT.search(text):
        effects.append(("draw", {"n": 1}))
        effects.append(("discard", {"n": 1, "target": "self"}))

    # Discard then draw (rummaging)
    m = DISCARD_DRAW.search(text)
    if m and not DRAW_N.search(text) and not DRAW_ONE_ALT.search(text) and not DRAW_DISCARD.search(text):
        effects.append(("draw", {"n": 1}))

    # Amass N (put +1/+1 on Zombie Army token, create if needed — proxy: counter)
    m = AMASS_N.search(text)
    if m and not ADD_COUNTER.search(text):
        effects.append(("add_counters", {"n": _qty(m), "target": "self"}))

    # Proliferate (put counter on each — proxy: +1 counter on self)
    if PROLIFERATE.search(text) and not ADD_COUNTER.search(text):
        effects.append(("add_counters", {"n": 1, "target": "self"}))

    # Connive N (draw N, discard N nonland → +1/+1 per discarded)
    m = CONNIVE_N.search(text)
    if m and not DRAW_N.search(text):
        n = _qty(m, default=1)
        effects.append(("draw", {"n": n}))
        effects.append(("add_counters", {"n": 1, "target": "self"}))

    # Adapt N (put N +1/+1 counters if creature has none)
    m = ADAPT_N.search(text)
    if m and not ADD_COUNTER.search(text) and not SURVEIL_N.search(text):
        effects.append(("add_counters", {"n": _qty(m), "target": "self"}))

    # Free cast proxy (cast without paying mana — draw proxy)
    if FREE_CAST_PROXY.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Exile target permanent from battlefield (removal — register)
    if EXILE_TGT_PERM.search(text) and not EXILE_TGT_CR.search(text):
        effects.append(("exile", {"target": "opp_biggest_creature"}))

    # Put on top of library (tempo effect — proxy as scry 1)
    if PUT_TOP_LIB.search(text) and not effects:
        effects.append(("scry", {"n": 1}))

    # Tutor to hand (search library for specific card)
    if TUTOR_TO_HAND.search(text) and not SEARCH_BASIC.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Search library for land to hand (ramp variant)
    if TUTOR_LAND_HAND.search(text) and not SEARCH_BASIC.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Copy a spell (storm/fork effects — proxy: fire the spell again, model as draw)
    if COPY_SPELL_TOKEN.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Put +1/+1 counters on each creature you control (mass pump)
    if PUT_COUNTERS_EACH.search(text) and not ADD_COUNTER.search(text):
        effects.append(("add_counters", {"n": 1, "target": "all_friendly"}))

    # Tap all creatures (board stasis / tap-all effect)
    if TAP_ALL_CREATURES.search(text) and not effects:
        effects.append(("scry", {"n": 0}))  # stasis: no goldfish value (no blockers anyway)

    # Poison counters (Phyrexian mechanic — register as damage proxy)
    m = POISON_COUNTER.search(text)
    if m and not effects:
        effects.append(("damage_player", {"n": 2, "target": "opp"}))

    # Return target enchantment/artifact/etc from GY to hand (broader GY recursion)
    if RETURN_TGT_BROAD.search(text) and not RETURN_GY_HAND.search(text) and not RETURN_GY_HAND2.search(text):
        effects.append(("return_gy_to_hand", {"filter_type": "any"}))

    # Create N tokens (multi-token creation)
    m = CREATE_MULTI_TOKEN.search(text)
    if m and not CREATE_CR_TOKEN.search(text) and not CREATE_COPY_TOKEN.search(text):
        effects.append(("create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}))

    # Investigate N times
    if INVESTIGATE_N.search(text) and not INVESTIGATE.search(text):
        effects.append(("draw", {"n": 2}))

    # Free play from hand (put creature/land onto battlefield without paying)
    if FREE_PLAY.search(text) and not effects:
        effects.append(("draw", {"n": 1}))  # proxy: playing for free = card advantage

    # Destroy all [type] (mass removal)
    if DESTROY_ALL_TYPE.search(text) and not DESTROY_ALL_CR.search(text):
        effects.append(("destroy_all_creatures", {}))

    # Exile all cards from graveyards (GY wipe)
    if EXILE_ALL_GY.search(text) and not effects:
        effects.append(("scry", {"n": 0}))  # GY wipe: no direct goldfish value

    # Return non-creature type to hand
    if RETURN_TGT_TYPE.search(text) and not BOUNCE_TGT.search(text) and not RETURN_GY_HAND.search(text):
        effects.append(("bounce_to_hand", {}))

    # Tap target creature you control (self-tap cost/effect)
    if TAP_CTRL_CREATURE.search(text) and not effects:
        effects.append(("scry", {"n": 0}))  # self-tap: no goldfish value

    # Exile target permanent until [event] (O-Ring style tempo)
    if EXILE_UNTIL_EVENT.search(text) and not EXILE_TGT_CR.search(text) and not EXILE_TGT_PERM.search(text):
        effects.append(("exile", {"target": "opp_biggest_creature"}))

    # Sacrifice a permanent as cost (register as no-op — cost not modeled in goldfish)
    if SACRIFICE_PERM.search(text) and not effects:
        effects.append(("scry", {"n": 0}))

    # Tuck to top of library (put on top — tempo play)
    if TUCK_TOP_LIB.search(text) and not PUT_TOP_LIB.search(text) and not effects:
        effects.append(("scry", {"n": 1}))

    # Multiple targets get +N/+M (buff up to N creatures)
    m = MULTI_PUMP.search(text)
    if m and not PUMP_TGT_BROAD.search(text):
        n = int(m.group(1))
        effects.append(("add_counters", {"n": n, "target": "all_friendly"}))

    # Increment (SOS): conditional pump on cast -- proxy as scry (card selection)
    if INCREMENT.search(text) and not effects:
        effects.append(("scry", {"n": 1}))

    # Prepared (SOS): creature enters prepared = may cast free copy on ETB
    # Model as a significant ETB value: proxy as draw 1 (copy = card advantage)
    if PREPARED.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Role token (WOE aura tokens)
    if ROLE_TOKEN.search(text) and not effects:
        effects.append(("create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}))

    # You get an emblem (planeswalker ultimate — proxy: big damage)
    if EMBLEM.search(text) and not effects:
        effects.append(("damage_player", {"n": 5, "target": "opp"}))

    # Extra turn / combat phase (register as big advantage — proxy: draw)
    if EXTRA_TURN.search(text) and not effects:
        effects.append(("draw", {"n": 2}))

    # "It/this becomes a creature" (animate permanent — register as counter)
    if BECOMES_CREATURE.search(text) and not effects:
        effects.append(("add_counters", {"n": 1, "target": "self"}))

    # For each [X] you control: scaling effect (proxy: +2 to whatever primary effect is)
    if FOR_EACH_SCALE.search(text) and not effects:
        effects.append(("add_counters", {"n": 2, "target": "self"}))

    # Named token creation (e.g. "create Voja Fenstalker, a legendary 5/5...")
    if CREATE_NAMED_TOKEN.search(text) and not CREATE_CR_TOKEN.search(text):
        effects.append(("create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}))

    # +1/+1 counter on a named target (TMNT/IP cards)
    if ADD_COUNTER_NAMED.search(text) and not ADD_COUNTER.search(text) and not ADD_COUNTER_TGT.search(text):
        effects.append(("add_counters", {"n": 1, "target": "self"}))

    # Self life loss ("you lose N life")
    m = SELF_LOSE_LIFE.search(text)
    if m and not LOSE_LIFE_N.search(text):
        effects.append(("lose_life", {"n": _qty(m), "target": "self"}))

    # Exile-until-nonland (cascade proxy)
    if EXILE_UNTIL.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Broader bounce (creature or Vehicle, defender controls, etc.)
    if BOUNCE_BROAD.search(text) and not BOUNCE_TGT.search(text):
        effects.append(("bounce_to_hand", {}))

    # Wheel effect (discard hand, draw N)
    if WHEEL_EFFECT.search(text) and not DRAW_DISCARD.search(text):
        effects.append(("draw", {"n": 4}))  # proxy: net card advantage

    # Extended keyword grant (until your next turn)
    if GRANT_KW_NEXT_TURN.search(text) and not GRANT_KEYWORD.search(text) and not effects:
        effects.append(("scry", {"n": 0}))

    # Broader debuff (gets -N/-M and loses [keyword])
    m = DEBUFF_BROAD.search(text)
    if m and not SHRINK_TGT.search(text) and not DEBUFF_POWER.search(text):
        n = int(m.group(1))
        effects.append(("damage_creature", {"n": n, "target": "opp_biggest"}))

    # Extra land drop each turn
    if EXTRA_LAND.search(text) and not effects:
        effects.append(("add_mana", {"n": 1}))  # proxy: extra land = extra mana

    # Each player draws N
    m = EACH_PLAYER_DRAWS.search(text)
    if m and not DRAW_N.search(text) and not DRAW_ONE_ALT.search(text):
        effects.append(("draw", {"n": _qty(m)}))

    # Each player discards (Wheel-style mass discard)
    if EACH_PLAYER_DISC.search(text) and not OPP_DISCARDS.search(text):
        effects.append(("discard", {"n": 1, "target": "opp"}))

    # Keyword grant: "[creature] gains [keyword] until EOT" — register as no-op
    if GRANT_KEYWORD.search(text) and not effects:
        effects.append(("scry", {"n": 0}))  # keyword grant: no goldfish damage value

    # Power debuff: target creature gets -N/-0 until EOT
    m = DEBUFF_POWER.search(text)
    if m and not SHRINK_TGT.search(text) and not effects:
        n = int(m.group(1))
        effects.append(("damage_creature", {"n": n, "target": "opp_biggest"}))

    # All other creatures get -N/-M (sweeper)
    m = DEBUFF_ALL.search(text)
    if m and not DESTROY_ALL_CR.search(text):
        n = int(m.group(1))
        effects.append(("damage_creature", {"n": n, "target": "each_opp"}))

    # Destroy target artifact or enchantment
    if DESTROY_TGT_ARTENC.search(text) and not DESTROY_TGT_CR.search(text):
        effects.append(("destroy", {"target": "opp_biggest_creature"}))

    # Return creature cards from graveyard to hand or battlefield
    if RETURN_CR_CARDS_GY.search(text) and not REANIMATE.search(text) and not RETURN_GY_HAND.search(text):
        effects.append(("return_gy_to_hand", {"filter_type": "creature"}))

    # Other [type] you control get +N/+M (lord effect)
    m = OTHER_CREATURES_GET.search(text)
    if m and not PUMP_ALL_CTRL.search(text):
        n = int(m.group(1))
        effects.append(("add_counters", {"n": n, "target": "all_friendly"}))

    # Loses all abilities until EOT (control effect — register as no-op)
    if LOSES_ABILITIES.search(text) and not effects:
        effects.append(("scry", {"n": 0}))

    # Gain life for each [X] you control
    m = GAIN_LIFE_COUNT.search(text)
    if m and not GAIN_LIFE_N.search(text):
        effects.append(("gain_life", {"n": 2}))  # proxy: 2 life average

    # Exile target spell (counter-like effect — register as no-op)
    if EXILE_TGT_SPELL.search(text) and not COUNTER_SPELL.search(text) and not effects:
        effects.append(("scry", {"n": 0}))

    # Self-pump by name: "Veyran gets +1/+1 until EOT" (magecraft self-pump)
    m = SELF_NAMED_PUMP.search(text)
    if m and not PUMP_TGT.search(text) and not PUMP_TGT_BROAD.search(text):
        effects.append(("add_counters", {"n": int(m.group(1)), "target": "self"}))

    # Broader pump: target creature gets +N/+M (catches "and gains X" variants)
    m = PUMP_TGT_BROAD.search(text)
    if m and not PUMP_TGT.search(text):
        effects.append(("add_counters", {"n": int(m.group(1)), "target": "self"}))

    # Negative pump: target creature gets -N/-M (removal/debuff)
    m = SHRINK_TGT.search(text)
    if m and not effects:
        effects.append(("damage_creature", {"n": int(m.group(1)), "target": "opp_biggest"}))

    # Copy token creation
    if CREATE_COPY_TOKEN.search(text) and not CREATE_CR_TOKEN.search(text):
        effects.append(("create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}))

    # Gain control of target creature (steal — goldfish proxy: draw 1)
    if GAIN_CONTROL.search(text) and not effects:
        effects.append(("draw", {"n": 1}))

    # Target player draws N cards
    m = TGT_PLAYER_DRAWS.search(text)
    if m and not DRAW_N.search(text) and not DRAW_ONE_ALT.search(text):
        effects.append(("draw", {"n": _qty(m)}))

    # Counter target spell (register as no-op — prevents hand-write classification)
    if COUNTER_SPELL.search(text) and not effects:
        effects.append(("scry", {"n": 0}))  # counterspell: no goldfish gain

    # Return up to N creatures to hand (mass bounce)
    if RETURN_UP_TO.search(text) and not BOUNCE_TGT.search(text):
        effects.append(("bounce_to_hand", {}))

    # Fight: both creatures deal damage to each other
    if FIGHT.search(text) and not effects:
        effects.append(("damage_creature", {"n": 2, "target": "opp_biggest"}))

    # Bolster N (put N counters on weakest friendly creature you control)
    m = BOLSTER_N.search(text)
    if m and not ADD_COUNTER.search(text) and not ADD_COUNTER_TGT.search(text):
        effects.append(("add_counters", {"n": _qty(m), "target": "self"}))

    # Renown N (put N +1/+1 counters when deals combat damage to player)
    m = RENOWN_N.search(text)
    if m and not ADD_COUNTER.search(text):
        effects.append(("add_counters", {"n": _qty(m), "target": "self"}))

    # Enchanted / equipped creature gets +N/+M (aura/equipment bonus)
    m = ENCHANTED_GETS.search(text) or EQUIPPED_GETS.search(text)
    if m and not effects:
        n = int(m.group(1))
        effects.append(("add_counters", {"n": n, "target": "all_friendly"}))

    # Firebending N (TLA): deal N damage to target creature or player on attack
    m = FIREBENDING_DMG.search(text)
    if m and not DAMAGE_ANY.search(text) and not DAMAGE_PLAYER.search(text):
        n = _qty(m)
        effects.append(("damage_any", {"n": n}))

    # "deals damage equal to its power" (power-based damage)
    if DEALS_POWER_DMG.search(text) and not effects:
        effects.append(("damage_any", {"n": 2}))  # proxy: typical power

    # Each opponent loses N life (drain)
    m = EACH_OPP_LOSES.search(text)
    if m and not LOSE_LIFE_N.search(text):
        effects.append(("lose_life", {"n": _qty(m), "target": "opp"}))

    # Broader gain life (catches "equal to" variants)
    m = GAIN_LIFE_BROAD.search(text)
    if m and not GAIN_LIFE_N.search(text):
        n = _qty(m, default=2)
        effects.append(("gain_life", {"n": n}))

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
        text = text.replace(card_name, "~")

    # ── Pre-processing ──────────────────────────────────────────────
    # Modal cards: "Choose one —\n• [mode1]\n• [mode2]"
    # Strip "Choose one/two/three —" header and treat each bullet as a paragraph.
    text = re.sub(r"^choose (?:one|two|three|a mode)\s*[—\-]", "", text,
                  flags=re.I | re.M)
    # Spree cards: "+ {cost} — [mode]" — strip the cost prefix, keep the effect.
    text = re.sub(r"^\+\s*\{[^}]+\}\s*[—\-]\s*", "", text, flags=re.M)
    # Normalize bullet points (•) and em-dashes starting a line to nothing.
    text = re.sub(r"^[•\-]\s+", "", text, flags=re.M)

    # Adventure / split cards: oracle text contains both halves separated by
    # a line beginning with the adventure-spell name (no mana cost on that line
    # in our DB format). Heuristic: if the text contains a paragraph that is ALL
    # caps-like word(s) followed only by a card type word ("Instant","Sorcery"),
    # truncate everything from that separator onward so we parse the creature
    # half only. Also handle the "\n//\n" literal separator Scryfall uses.
    if " // " in text or "\n// " in text or text.startswith("// "):
        # Keep only the part before the "//" split marker
        text = re.split(r"\s*//\s*", text)[0]

    # Strip "As an additional cost to cast this spell, [cost]." — this is a
    # casting requirement line; the real effect is on subsequent lines.
    text = re.sub(r"^as an additional cost to cast (?:this spell|~),[^\n]+\n?",
                  "", text, flags=re.I | re.M)

    # SOS mechanics: replace keyword stubs with concrete effect proxies BEFORE
    # stripping parens, so the reminder text is used to confirm the pattern.
    # Increment: conditional +1/+1 on cast -- replace with a pump proxy line.
    text = re.sub(r"\bIncrement\s*\([^)]*\)", "When this creature enters, put a +1/+1 counter on it.", text, flags=re.I)
    # Prepared: entering prepared = free copy -- replace with draw proxy.
    text = re.sub(r"This (?:creature|card|permanent) enters prepared\.", "When this creature enters, draw a card.", text, flags=re.I)
    # Converge: "Converge — [effect]" strip the keyword header (em-dash or en-dash)
    text = re.sub(r"^Converge\s*[—–-]\s*", "", text, flags=re.I | re.M)

    # Strip reminder text in parentheses (e.g. "(You may pay...")  so
    # mechanic keywords like "Prowess" and "Firebending 1" become bare.
    text = re.sub(r"\s*\([^)]*\)", "", text)

    # Split into lines / logical paragraphs
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    for para in paragraphs:
        # Strip common conditional prefixes so the body can be parsed.
        # "You may [effect]." → "[effect]."
        para = re.sub(r"^you may\s+", "", para, flags=re.I)
        # "If you do, [effect]." → "[effect]."
        para = re.sub(r"^if you do,\s+", "", para, flags=re.I)
        # "If [condition], [effect]." — strip only simple "if X," clause.
        para = re.sub(r"^if [^,]{1,60},\s+", "", para, flags=re.I)
        # "Until end of turn, [effect]." → "[effect]."
        para = re.sub(r"^until end of turn,\s+", "", para, flags=re.I)
        # "It gets +N/+N" → "target creature gets +N/+N"
        para = re.sub(r"^it\s+(gets?|gains?|has|becomes?)\s+", r"target creature \1 ", para, flags=re.I)
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
