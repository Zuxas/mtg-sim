"""
tests/test_keywords_printed_text.py -- spec harness/specs/2026-09-29-keywords-from-printed-text.md

Run: python tests/test_keywords_printed_text.py   (or via pytest)

K1: plain keywords are tagged only when printed as one of the card's own
keywords. Oracle text below is verbatim Scryfall (local CardDB, 2026-09-29).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.keywords import KWTag, tag_keywords, get_keywords

ORACLE = {
    "Ocelot Pride": "First strike, lifelink\nAscend (If you control ten or more permanents, you get the city's blessing for the rest of the game.)\nAt the beginning of your end step, if you gained life this turn, create a 1/1 white Cat creature token. Then if you have the city's blessing, for each token you control that entered this turn, create a token that's a copy of it.",
    "Guide of Souls": "Whenever another creature you control enters, you gain 1 life and get {E} (an energy counter).\nWhenever you attack, you may pay {E}{E}{E}. When you do, put two +1/+1 counters and a flying counter on target attacking creature. It becomes an Angel in addition to its other types.",
    "Dragon's Rage Channeler": "Whenever you cast a noncreature spell, surveil 1. (Look at the top card of your library. You may put that card into your graveyard.)\nDelirium — As long as there are four or more card types among cards in your graveyard, this creature gets +2/+2, has flying, and attacks each combat if able.",
    "Scion of Draco": "Domain — This spell costs {2} less to cast for each basic land type among lands you control.\nFlying\nEach creature you control has vigilance if it's white, hexproof if it's blue, lifelink if it's black, first strike if it's red, and trample if it's green.",
    "Kellan, Planar Trailblazer": "{1}{R}: If Kellan is a Scout, it becomes a Human Faerie Detective and gains \"Whenever Kellan deals combat damage to a player, exile the top card of your library. You may play that card this turn.\"\n{2}{R}: If Kellan is a Detective, it becomes a 3/2 Human Faerie Rogue and gains double strike.",
    "Craterhoof Behemoth": "Haste\nWhen this creature enters, creatures you control gain trample and get +X/+X until end of turn, where X is the number of creatures you control.",
    "Slickshot Show-Off": "Flying, haste\nWhenever you cast a noncreature spell, this creature gets +2/+0 until end of turn.\nPlot {1}{R} (You may pay {1}{R} and exile this card from your hand. Cast it as a sorcery on a later turn without paying its mana cost. Plot only as a sorcery.)",
    "Psychic Frog": "Whenever this creature deals combat damage to a player or planeswalker, draw a card.\nDiscard a card: Put a +1/+1 counter on this creature.\nExile three cards from your graveyard: This creature gains flying until end of turn.",
    "Leyline of Sanctity": "If this card is in your opening hand, you may begin the game with it on the battlefield.\nYou have hexproof. (You can't be the target of spells or abilities your opponents control.)",
    "Thalia, Guardian of Thraben": "First strike\nNoncreature spells cost {1} more to cast.",
}

KW = [KWTag.FLYING, KWTag.TRAMPLE, KWTag.LIFELINK, KWTag.FIRST_STRIKE, KWTag.DOUBLE_STRIKE,
      KWTag.VIGILANCE, KWTag.HEXPROOF, KWTag.HASTE, KWTag.DEATHTOUCH, KWTag.MENACE]

EXPECTED = {
    "Ocelot Pride": {KWTag.FIRST_STRIKE, KWTag.LIFELINK},
    "Guide of Souls": set(),                # the flying counter goes on ANOTHER creature
    "Dragon's Rage Channeler": set(),       # flying only with delirium (conditional)
    "Scion of Draco": {KWTag.FLYING},       # grants the rest to OTHER creatures by colour
    "Kellan, Planar Trailblazer": set(),    # double strike only after two activations
    "Craterhoof Behemoth": {KWTag.HASTE},   # team trample comes from its ETB handler
    "Slickshot Show-Off": {KWTag.FLYING, KWTag.HASTE},
    "Psychic Frog": set(),                  # flying only when activated
    "Leyline of Sanctity": set(),           # the PLAYER has hexproof, not the enchantment
    "Thalia, Guardian of Thraben": {KWTag.FIRST_STRIKE},
}


def _card(name):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line="Creature", oracle_text=ORACLE[name])
    tag_keywords(c)
    return c


def test_k1_printed_keywords_only():
    for name, want in EXPECTED.items():
        c = _card(name)
        got = {k for k in KW if k in c.tags}
        assert got == want, (name, got, want)
        assert {k for k in KW if k in get_keywords(c)} == want, name
    print("[ok] K1 plain keywords only from printed text")


def test_k1_hexproof_from_still_counts():
    c = Card(name="Shalai-ish", mana_cost="{1}", cmc=1, type_line="Creature",
             oracle_text="Flying\nHexproof from blue")
    tag_keywords(c)
    assert KWTag.HEXPROOF in c.tags and KWTag.FLYING in c.tags
    print("[ok] K1 'hexproof from X' still tagged hexproof")


def main() -> int:
    test_k1_printed_keywords_only()
    test_k1_hexproof_from_still_counts()
    print("ALL K1 GATES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
