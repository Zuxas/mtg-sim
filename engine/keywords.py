"""
keywords.py — Oracle text keyword parser

Parses MTG oracle text to auto-tag cards with keyword abilities.
Ported and expanded from heyhaigh/mtg-ai-match (MIT) oracle parser,
adapted for Python and extended for competitive format relevance.

Usage:
    from engine.keywords import tag_keywords
    tag_keywords(card)   # mutates card.tags in place
"""

import re
from data.card import Card, Tag


# ---------------------------------------------------------------------------
# Keyword tag constants (extend Tag class)
# ---------------------------------------------------------------------------

# Add these to Tag in card.py or use directly as strings here
class KWTag:
    # Evasion
    FLYING          = "flying"
    REACH           = "reach"
    MENACE          = "menace"
    TRAMPLE         = "trample"
    SHADOW          = "shadow"
    HORSEMANSHIP    = "horsemanship"
    FEAR            = "fear"
    INTIMIDATE      = "intimidate"
    UNBLOCKABLE     = "unblockable"

    # Combat modifiers
    FIRST_STRIKE    = "first_strike"
    DOUBLE_STRIKE   = "double_strike"
    DEATHTOUCH      = "deathtouch"
    LIFELINK        = "lifelink"
    VIGILANCE       = "vigilance"
    HASTE           = "haste"
    DEFENDER        = "defender"
    INDESTRUCTIBLE  = "indestructible"
    PROWESS         = "prowess"

    # Protection / Hexproof
    HEXPROOF        = "hexproof"
    WARD            = "ward"
    PROTECTION      = "protection"
    SHROUD          = "shroud"

    # Spell timing
    FLASH           = "flash"

    # Graveyard / recursion
    UNDYING         = "undying"
    PERSIST         = "persist"
    DREDGE          = "dredge"

    # Triggered effects (from oracle text patterns)
    ETB_DRAW        = "etb_draw"       # draws on ETB
    ETB_REMOVAL     = "etb_removal"    # destroys/exiles on ETB
    ETB_BOUNCE      = "etb_bounce"     # bounces on ETB
    ETB_TOKEN       = "etb_token"      # creates token on ETB
    ETB_LIFE        = "etb_life"       # gains life on ETB
    ATTACK_TRIGGER  = "attack_trigger" # has "when ~ attacks" effect

    # Role tags (for APL decision making)
    HATE_BEAR       = "hate_bear"      # taxes / restricts opponent
    DISRUPTOR       = "disruptor"      # hand disruption
    PUMP_LORD       = "pump_lord"      # buffs other creatures
    MANA_DORK       = "mana_dork"      # produces mana


# ---------------------------------------------------------------------------
# Keyword detection rules
# Each rule: (tag_string, [regex_patterns])
# Patterns are matched against oracle_text.lower()
# ---------------------------------------------------------------------------

_KEYWORD_RULES: list[tuple[str, list[str]]] = [
    # Evasion
    (KWTag.FLYING,        [r"\bflying\b"]),
    (KWTag.REACH,         [r"\breach\b"]),
    (KWTag.MENACE,        [r"\bmenace\b"]),
    (KWTag.TRAMPLE,       [r"\btrample\b"]),
    (KWTag.SHADOW,        [r"\bshadow\b"]),
    (KWTag.FEAR,          [r"\bfear\b"]),
    (KWTag.INTIMIDATE,    [r"\bintimidate\b"]),
    (KWTag.UNBLOCKABLE,   [r"can't be blocked"]),

    # Combat
    (KWTag.FIRST_STRIKE,  [r"\bfirst strike\b"]),
    (KWTag.DOUBLE_STRIKE, [r"\bdouble strike\b"]),
    (KWTag.DEATHTOUCH,    [r"\bdeathtouch\b"]),
    (KWTag.LIFELINK,      [r"\blifelink\b"]),
    (KWTag.VIGILANCE,     [r"\bvigilance\b"]),
    (KWTag.HASTE,         [r"\bhaste\b"]),
    (KWTag.DEFENDER,      [r"\bdefender\b"]),
    (KWTag.INDESTRUCTIBLE,[r"\bindestructible\b"]),

    # Protection
    (KWTag.HEXPROOF,      [r"\bhexproof\b"]),
    (KWTag.WARD,          [r"\bward\b"]),
    (KWTag.PROTECTION,    [r"\bprotection from\b"]),
    (KWTag.SHROUD,        [r"\bshroud\b"]),

    # Timing
    (KWTag.FLASH,         [r"\bflash\b"]),

    # Prowess
    (KWTag.PROWESS,       [r"\bprowess\b"]),

    # Graveyard
    (KWTag.UNDYING,       [r"\bundying\b"]),
    (KWTag.PERSIST,       [r"\bpersist\b"]),
    (KWTag.DREDGE,        [r"\bdredge\b"]),

    # ETB triggers
    (KWTag.ETB_DRAW,      [
        r"when .{0,40} enters.{0,20}draw",
        r"enters the battlefield.{0,60}draw a card",
    ]),
    (KWTag.ETB_REMOVAL,   [
        r"when .{0,40} enters.{0,20}destroy",
        r"when .{0,40} enters.{0,20}exile",
        r"enters the battlefield.{0,60}destroy target",
        r"enters the battlefield.{0,60}exile target",
    ]),
    (KWTag.ETB_BOUNCE,    [
        r"when .{0,40} enters.{0,20}return target",
        r"enters the battlefield.{0,60}return target",
    ]),
    (KWTag.ETB_TOKEN,     [
        r"when .{0,40} enters.{0,20}create",
        r"enters the battlefield.{0,60}create a",
    ]),
    (KWTag.ETB_LIFE,      [
        r"when .{0,40} enters.{0,20}you gain",
        r"enters the battlefield.{0,60}you gain \d+ life",
    ]),
    (KWTag.ATTACK_TRIGGER,[
        r"when(ever)? .{0,40} attacks",
    ]),

    # Role tags
    (KWTag.HATE_BEAR,     [
        r"spells cost \{1\} more",
        r"noncreature spells cost",
        r"can't cast spells",
        r"players can't .{0,30} unless",
        r"opponents can't",
        r"your opponents can't",
    ]),
    (KWTag.DISRUPTOR,     [
        r"target player discards",
        r"each player discards",
        r"look at .{0,20} hand",
        r"choose a card in .{0,20} hand",
    ]),
    (KWTag.PUMP_LORD,     [
        r"other .{0,40} creatures you control get \+",
        r"creatures you control get \+",
        r"other .{0,30} get \+\d+/\+\d+",
    ]),
    (KWTag.MANA_DORK,     [
        r"\{t\}: add \{",
        r"tap: add ",
        r"adds? one mana",
    ]),
]

# Compile all patterns once at import time
_COMPILED_RULES: list[tuple[str, list[re.Pattern]]] = [
    (tag, [re.compile(p, re.IGNORECASE) for p in patterns])
    for tag, patterns in _KEYWORD_RULES
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tag_keywords(card: Card) -> set[str]:
    """
    Parse card.oracle_text and add matching keyword tags to card.tags.
    Returns the set of newly added tags.
    """
    if not card.oracle_text:
        return set()

    text = card.oracle_text.lower()
    added: set[str] = set()

    for tag, patterns in _COMPILED_RULES:
        if tag in card.tags:
            continue
        for pattern in patterns:
            if pattern.search(text):
                card.tags.add(tag)
                added.add(tag)
                break

    return added


def get_keywords(card: Card) -> set[str]:
    """Return keyword tags without modifying the card (read-only)."""
    if not card.oracle_text:
        return set()

    text = card.oracle_text.lower()
    found: set[str] = set()

    for tag, patterns in _COMPILED_RULES:
        for pattern in patterns:
            if pattern.search(text):
                found.add(tag)
                break

    return found


def describe_keywords(card: Card) -> str:
    """Return a human-readable list of keyword abilities detected."""
    kw = {t for t in card.tags if t in {
        KWTag.FLYING, KWTag.REACH, KWTag.MENACE, KWTag.TRAMPLE,
        KWTag.FIRST_STRIKE, KWTag.DOUBLE_STRIKE, KWTag.DEATHTOUCH,
        KWTag.LIFELINK, KWTag.VIGILANCE, KWTag.HASTE, KWTag.HEXPROOF,
        KWTag.INDESTRUCTIBLE, KWTag.FLASH, KWTag.WARD, KWTag.DEFENDER,
        KWTag.HATE_BEAR, KWTag.PUMP_LORD, KWTag.MANA_DORK,
    }}
    return ", ".join(sorted(kw)) if kw else "none"


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from data.card import Card, Tag

    test_cards = [
        Card(
            name="Mantis Rider",
            mana_cost="{R}{W}{U}",
            cmc=3,
            type_line="Creature — Human Monk",
            oracle_text="Flying, vigilance, haste",
            power="3", toughness="3",
            colors=["R", "W", "U"],
        ),
        Card(
            name="Thalia, Guardian of Thraben",
            mana_cost="{1}{W}",
            cmc=2,
            type_line="Legendary Creature — Human Soldier",
            oracle_text="First strike\nNoncreature spells cost {1} more to cast.",
            power="2", toughness="1",
            colors=["W"],
        ),
        Card(
            name="Reflector Mage",
            mana_cost="{1}{W}{U}",
            cmc=3,
            type_line="Creature — Human Wizard",
            oracle_text="When Reflector Mage enters the battlefield, return target creature an opponent controls to its owner's hand. That creature's owner can't cast spells with that name until your next turn.",
            power="2", toughness="3",
            colors=["W", "U"],
        ),
        Card(
            name="Noble Hierarch",
            mana_cost="{G}",
            cmc=1,
            type_line="Creature — Human Druid",
            oracle_text="Exalted (Whenever a creature you control attacks alone, that creature gets +1/+1 until end of turn.)\n{T}: Add {G}, {W}, or {U}.",
            power="0", toughness="1",
            colors=["G"],
        ),
    ]

    for card in test_cards:
        new_tags = tag_keywords(card)
        print(f"\n{card.name}")
        print(f"  Keywords detected: {describe_keywords(card)}")
        print(f"  All tags: {sorted(card.tags)}")
