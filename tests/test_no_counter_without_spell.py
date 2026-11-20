"""
test_no_counter_without_spell.py -- the core engine never casts a counterspell
when there is no spell to counter.

After the active player's main phase the core asks the other player's APL for
an instant-speed response with spell=None. An APL that answered with a
counterspell had it paid for and put in the graveyard with no target and no
effect (Izzet Lessons: 1.4 counters per game). Counterspells belong to the
cast path, GameState.cast_spell -> counter_resolver.try_counter_spell, which
this test also checks still fires.
"""
from __future__ import annotations
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import counter_resolver, match_engine
from engine.match_runner import _run_single_match
from engine.stack import InteractionType
from scripts.compare_engines import _load

GAMES = 30


def main():
    wasted, real = [], [0]
    resolve = match_engine.resolve_interaction

    def spy_resolve(resolution, reactive_gs, active_gs):
        item = resolution.item
        if item.interaction_type == InteractionType.COUNTER and not item.targets:
            wasted.append(item.card.name)
        return resolve(resolution, reactive_gs, active_gs)

    try_counter = counter_resolver.try_counter_spell

    def spy_counter(*a, **k):
        hit = try_counter(*a, **k)
        real[0] += bool(hit)
        return hit

    match_engine.resolve_interaction = spy_resolve
    counter_resolver.try_counter_spell = spy_counter

    lessons, momo = _load("izzetlesson"), _load("azoriusmomo")
    rng = random.Random(42)
    for i in range(GAMES):
        _run_single_match((rng.randint(0, 999999), lessons[0], momo[0],
                           lessons[1], momo[1], i % 2 == 0, False, "core"))

    assert not wasted, f"counterspells cast with nothing to counter: {wasted[:5]}"
    print(f"PASS: no counterspell cast without a target in {GAMES} core games")
    assert real[0] > 0, "the cast-path counter never fired; test would prove nothing"
    print(f"PASS: spells are still countered on the cast path ({real[0]} times)")


def table_checks():
    """Which spells each counter may target, and what it costs, from the
    local card data."""
    from data.card import Card, Tag
    from engine.card_db import CardDB
    from engine.counter_resolver import (COUNTER_COST, COUNTER_TAX,
                                         COUNTER_VALIDITY, _spare_mana)
    db = CardDB()

    def spell(cmc, colors=(), creature=False):
        c = Card(name="X", mana_cost="", cmc=cmc, type_line="", colors=list(colors))
        c.tags = {Tag.CREATURE} if creature else set()
        return c

    ok = lambda name, s: COUNTER_VALIDITY[name][0](s)
    assert [ok("Spell Snare", spell(n)) for n in (1, 2, 3)] == [False, True, False]
    assert ok("Negate", spell(3)) and not ok("Negate", spell(3, creature=True))
    assert "red or green" in db.get("Flashfreeze")["oracle_text"]
    assert ok("Flashfreeze", spell(2, "G")) and ok("Flashfreeze", spell(2, "R"))
    assert not ok("Flashfreeze", spell(2, "U")) and not ok("Flashfreeze", spell(2))
    # Three Steps Ahead: {U} plus the spree mode {1}{U} = three mana.
    assert "+ {1}{U} \u2014 Counter target spell." in db.get("Three Steps Ahead")["oracle_text"]
    assert COUNTER_COST["Three Steps Ahead"] == ("{1}{U}{U}", 3)
    assert "unless its controller pays {2}" in db.get("It'll Quench Ya!")["oracle_text"]
    assert COUNTER_TAX["It'll Quench Ya!"] == 2

    class Land:
        def __init__(self, tapped):
            self.tapped = tapped

    gs = type("GS", (), {
        "mana_pool": type("P", (), {"total": lambda self: 1})(),
        "zones": type("Z", (), {"lands_on_battlefield":
                                lambda self: [Land(False), Land(True)]})()})()
    assert _spare_mana(gs) == 2      # one floating + one untapped land
    print("PASS: counter restrictions, the spree cost and the tax amount match "
          "the card text")


if __name__ == "__main__":
    table_checks()
    main()
