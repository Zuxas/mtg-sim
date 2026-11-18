"""test_keyword_tagging.py -- issue #17.

Keyword tags were a regex search over the whole oracle text, so a card was
tagged with any keyword it granted to something else or merely mentioned.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.keywords import tag_keywords, get_keywords, keyword_text, KWTag, KEYWORD_ABILITY_TAGS
from engine.match_state import has_keyword


def _card(name, text, type_line="Creature - Test"):
    return Card(name=name, mana_cost="{1}", cmc=1, type_line=type_line, oracle_text=text,
                power="2", toughness="2", colors=[])


def _kw(name, text):
    return get_keywords(_card(name, text)) & KEYWORD_ABILITY_TAGS


# ---- the three cases from the issue ----

def test_until_end_of_turn_grant_is_not_the_cards_own_keyword():
    inti = ("Whenever you attack, you may discard a card. When you do, put a +1/+1 counter "
            "on target attacking creature. It gains trample until end of turn.")
    assert _kw("Inti, Seneschal of the Sun", inti) == set()


def test_granting_to_another_creature_does_not_tag():
    assert _kw("Giver", "{T}: Target creature you control gains lifelink until end of turn.") == set()
    assert _kw("Regal Caracal", "Other Cats you control get +1/+1 and have lifelink.") == set()


def test_mentioning_a_keyword_does_not_tag():
    assert _kw("Plummet Guy", "When this creature enters, destroy target creature with flying.") == set()
    assert _kw("Token Maker", "Create two 1/1 Insect creature tokens with flying.") == set()


# ---- real keyword holders keep their tags ----

def test_keyword_lines():
    assert _kw("Serra Angel", "Flying, vigilance") == {KWTag.FLYING, KWTag.VIGILANCE}
    assert _kw("Questing Beast", "Vigilance, deathtouch, haste\nQuesting Beast can't be blocked "
               "by creatures with power 2 or less.") == {KWTag.VIGILANCE, KWTag.DEATHTOUCH, KWTag.HASTE}
    assert _kw("Akroma", "Flying, first strike, vigilance, trample, haste, protection from black "
               "and from red") >= {KWTag.FLYING, KWTag.FIRST_STRIKE, KWTag.TRAMPLE, KWTag.PROTECTION}
    assert _kw("Warded", "Ward {2}\nFlash\nHexproof from black") == {KWTag.WARD, KWTag.FLASH, KWTag.HEXPROOF}
    assert _kw("Fencer", "Double strike") == {KWTag.DOUBLE_STRIKE}


def test_reminder_text_is_ignored():
    assert _kw("Lifelinker", "Lifelink (Damage dealt by this creature also causes you to gain "
               "that much life.)") == {KWTag.LIFELINK}
    assert _kw("Reminder Only", "Plot {1}{R} (You may cast it later. It has haste and flying "
               "in this example.)") == set()


def test_own_static_and_conditional_abilities_count():
    assert _kw("Wickerfolk", "Haste\nDelirium - This creature gets +1/+1 and has trample as long "
               "as there are four or more card types among cards in your graveyard.") == {KWTag.HASTE, KWTag.TRAMPLE}
    assert _kw("Dragon's Rage Channeler", "Delirium - As long as there are four or more card types "
               "among cards in your graveyard, this creature gets +2/+2, has flying, and attacks "
               "each combat if able.") == {KWTag.FLYING}
    assert _kw("Warden", "As long as this creature has three or more counters on it, it has flying "
               "and vigilance.") == {KWTag.FLYING, KWTag.VIGILANCE}
    assert _kw("Named One", "Named One has lifelink as long as you control an artifact.") == {KWTag.LIFELINK}


def test_conditional_self_grants_can_be_switched_off():
    from engine import keywords
    drc = ("Delirium - As long as there are four or more card types among cards in your "
           "graveyard, this creature gets +2/+2, has flying, and attacks each combat if able.")
    keywords.TAG_CONDITIONAL_SELF_GRANTS = False
    try:
        assert _kw("Dragon's Rage Channeler", drc) == set()
        assert _kw("Plain", "This creature has lifelink.") == {KWTag.LIFELINK}, "unconditional stays"
    finally:
        keywords.TAG_CONDITIONAL_SELF_GRANTS = True
    assert _kw("Dragon's Rage Channeler", drc) == {KWTag.FLYING}


def test_equipment_and_lords_do_not_tag_themselves():
    assert _kw("Wings", "Equipped creature has flying.\nEquip {1}") == set()
    assert _kw("Lord", "Other creatures you control have haste.") == set()
    assert _kw("Aura", "Enchanted creature gets +2/+2 and has trample.") == set()


def test_mixed_card_keeps_only_its_own():
    c = _card("Hardened Academic", "Flying, haste\nDiscard a card: This creature gains lifelink "
              "until end of turn.")
    assert tag_keywords(c) & KEYWORD_ABILITY_TAGS == {KWTag.FLYING, KWTag.HASTE}
    assert KWTag.LIFELINK not in c.tags


def test_other_tags_still_use_the_whole_text():
    c = _card("ETB Guy", "When ETB Guy enters, draw a card.\nWhenever ETB Guy attacks, you gain 1 life.")
    tags = get_keywords(c)
    assert KWTag.ETB_DRAW in tags and KWTag.ATTACK_TRIGGER in tags


def test_has_keyword_fallback_uses_the_same_rule():
    untagged = _card("Fallback", "First strike\nDestroy target creature with flying.")
    untagged.tags = set()
    assert has_keyword(untagged, "first strike")
    assert not has_keyword(untagged, "flying")
    blank = _card("Blank", "")
    assert not has_keyword(blank, "flying")


def test_sentence_starting_with_a_keyword_is_not_a_keyword_line():
    assert _kw("Lord", "Flying creatures you control get +1/+1.") == set()
    assert _kw("Hater", "Reach creatures can't block this turn") == set()
    assert _kw("Paywall", "Ward\u2014Pay 2 life.\nDredge 3") == {KWTag.WARD, KWTag.DREDGE}


def test_temporary_self_grant_is_not_intrinsic():
    assert _kw("Pumper", "{R}: This creature has flying until end of turn.") == set()
    assert _kw("Crasher", "Whenever you cast a spell, this creature has trample this turn.") == set()
    # "this turn" inside the condition is not a duration
    assert _kw("Stoic Sphinx", "Flash\nFlying\nThis creature has hexproof as long as you "
               "haven't cast a spell this turn.") == {KWTag.FLASH, KWTag.FLYING, KWTag.HEXPROOF}


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
    print("test_keyword_tagging: OK")
