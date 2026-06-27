"""test_r4_warp_recast_unit.py -- R4 warp cast-from-exile unit check.

Tiny standalone test for the Develop-phase R4 increment (NOT the full
match-path lifecycle deliverable). Exercises the three GameState methods
directly on a bare goldfish GameState:

  1. cast_spell_warp        -- warp-cast Quantum Riddler from hand (cheap)
  2. _tick_warp             -- end-step exile + per-card recast markers
  3. cast_spell_from_warp_exile -- recast from exile for FULL cost on a
                              LATER turn (illegal on the exile turn itself)

ASCII-only output. Exit 0 on pass, 1 on failure.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState


def _quantum_riddler() -> Card:
    # _WARP_CARDS: warp {1}{U} = 2 mana; full {3}{U}{U} CMC 5.
    return Card(
        name="Quantum Riddler",
        mana_cost="{3}{U}{U}",
        cmc=5,
        type_line="Creature - Alien",
        oracle_text="",
        power="3", toughness="3",
        colors=["U"],
    )


def _dummy_lib_card(n: int) -> Card:
    return Card(name=f"Island {n}", mana_cost="", cmc=0,
                type_line="Basic Land - Island", oracle_text="")


def run():
    riddler = _quantum_riddler()
    gs = GameState(mainboard=[])
    gs.turn = 3
    # A couple of library cards so Quantum Riddler's ETB draw never no-ops.
    gs.zones.library = [_dummy_lib_card(1), _dummy_lib_card(2),
                        _dummy_lib_card(3), _dummy_lib_card(4)]
    gs.zones.hand = [riddler]

    # --- 1. Warp-cast from hand (cheap cost) -------------------------------
    gs.mana_pool.U = 1
    gs.mana_pool.C = 1                       # 2 mana for the {1}{U} warp cost
    assert gs.cast_spell_warp(riddler), "warp-cast should succeed"
    assert riddler in gs.zones.battlefield, "warp creature must be on battlefield"
    assert getattr(riddler, "_warp_cast", False) is True, "_warp_cast must be set"
    assert riddler not in gs.zones.hand, "warp creature left hand"

    # --- 2. End-step tick: exile + set recast markers ---------------------
    gs._tick_warp()
    assert riddler not in gs.zones.battlefield, "must leave battlefield at end step"
    assert riddler in gs.zones.exile, "must be in exile after end step"
    assert getattr(riddler, "_warp_cast", True) is False, "_warp_cast cleared at exile"
    assert getattr(riddler, "_warp_recastable", False) is True, \
        "_warp_recastable marker must be set"
    assert riddler._warp_exiled_turn == 3, \
        f"_warp_exiled_turn must record the exile turn (got {riddler._warp_exiled_turn})"

    # --- 3a. Recast ILLEGAL on the exile turn itself ----------------------
    gs.spells_cast_this_turn = 0             # avoid Cosmogrand 2nd-spell path
    gs.mana_pool.empty()
    gs.mana_pool.U = 2
    gs.mana_pool.C = 3                        # 5 mana, enough for full cost
    assert gs.cast_spell_from_warp_exile(riddler) is False, \
        "recast must be ILLEGAL on the exile turn (turn == exiled_turn)"
    # Failed legality check must leave the card untouched in exile.
    assert riddler in gs.zones.exile, "card must stay in exile after illegal recast"
    assert getattr(riddler, "_warp_recastable", False) is True, \
        "_warp_recastable must remain set after illegal recast"

    # --- 3b. Recast LEGAL on a later turn, FULL cost ----------------------
    gs.turn = 4
    gs.spells_cast_this_turn = 0
    gs.mana_pool.empty()
    gs.mana_pool.U = 2
    gs.mana_pool.C = 3                        # exactly 5 = {3}{U}{U}
    pool_before = gs.mana_pool.total()
    assert pool_before == 5, f"expected 5 mana staged, got {pool_before}"
    assert gs.cast_spell_from_warp_exile(riddler) is True, \
        "recast must SUCCEED on a later turn"
    # Full cost was paid (not the 2-mana warp cost): pool drained by 5.
    assert gs.mana_pool.total() == 0, \
        f"full {{3}}{{U}}{{U}} cost must drain the pool (got {gs.mana_pool.total()})"
    # Card resolved onto battlefield, removed from exile, no double-presence.
    assert riddler in gs.zones.battlefield, "recast creature must be on battlefield"
    assert riddler not in gs.zones.exile, "recast creature must leave exile"
    assert riddler not in gs.zones.hand, "no leftover hand copy (no double-presence)"
    # Markers cleared so it cannot loop / be recast again.
    assert getattr(riddler, "_warp_recastable", True) is False, \
        "_warp_recastable must be cleared after recast"
    assert getattr(riddler, "_warp_cast", True) is False, \
        "_warp_cast must stay clear (recast body must not re-exile)"
    # And a second recast attempt is now a no-op.
    assert gs.cast_spell_from_warp_exile(riddler) is False, \
        "card cannot be recast a second time"

    print("ALL R4 WARP RECAST UNIT TESTS PASS")


if __name__ == "__main__":
    try:
        run()
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    sys.exit(0)
