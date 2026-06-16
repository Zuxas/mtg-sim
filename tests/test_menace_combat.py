"""test_menace_combat.py -- synthetic tests for Phase 3.5 Stage A menace.

Validates the multi-blocker damage accumulation fix from Stage A
Amendment 1 (CR 510.1) and the menace 2-blocker assignment requirement.
The 14-deck Modern gauntlet has no menace creatures, so this logic
ships untested in production. This file closes the gap.

Spec: harness/specs/2026-04-27-phase-3.5-stage-a-block-eligibility.md
Amendment 1: per-blocker damage check meant 2x 2/2 vs 3/4 menace
attacker didn't kill it (neither had 2 >= 4 individually). Fix sums
blocker damage before the lethality check.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card
from engine.keywords import KWTag
from engine.match_runner import TwoPlayerGameState, _resolve_combat


def _mk_creature(name, power, toughness, colors=None, tags=None, type_line="Creature"):
    c = Card(name=name, mana_cost="{1}", cmc=1, type_line=type_line,
             oracle_text="", power=str(power), toughness=str(toughness),
             colors=colors or [])
    if tags:
        c.tags.update(tags)
    c.summoning_sickness = False
    return c


def _fresh_gs():
    return TwoPlayerGameState([], [], on_play=True, seed=42)


def test_menace_damage_accumulates_kills_attacker():
    """3/4 menace attacker vs 2x 2/2 blockers: blocker damage sums to 4,
    attacker dies. Pre-Amendment-1 bug: per-blocker check kept attacker
    alive (neither blocker had power 2 >= toughness 4).
    """
    gs = _fresh_gs()
    atk = _mk_creature("Menace Beast", 3, 4, colors=["R"], tags={KWTag.MENACE})
    blk1 = _mk_creature("Bear A", 2, 2, colors=["G"])
    blk2 = _mk_creature("Bear B", 2, 2, colors=["G"])
    gs.bf_a = [atk]
    gs.bf_b = [blk1, blk2]

    dmg, atk_losses, blk_losses, ll, dll, creatures_hit = _resolve_combat(gs, "a")

    assert atk in atk_losses, "menace attacker should die from accumulated 2+2=4 damage"
    assert dmg == 0, "blocked menace attacker (no trample) deals no damage to defender"
    # 3 power assigned in list order: blk1 takes 2 (dies), blk2 takes 1 (survives)
    assert len(blk_losses) == 1, f"expected 1 blocker dead, got {len(blk_losses)}"


def test_menace_forces_two_blocker_requirement():
    """Menace attacker with only 1 legal blocker available goes
    unblocked (defender can't satisfy the 2-blocker requirement).
    """
    gs = _fresh_gs()
    atk = _mk_creature("Menace Beast", 3, 4, colors=["R"], tags={KWTag.MENACE})
    blk = _mk_creature("Lone Bear", 2, 2, colors=["G"])
    gs.bf_a = [atk]
    gs.bf_b = [blk]

    dmg, atk_losses, blk_losses, ll, dll, creatures_hit = _resolve_combat(gs, "a")

    assert atk_losses == [], "unblocked menace attacker survives"
    assert blk_losses == [], "lone blocker can't legally block menace -- doesn't engage"
    assert dmg == 3, f"unblocked attacker deals full power to defender, got {dmg}"


def test_non_menace_only_takes_one_blocker():
    """Sanity check: a non-menace 3/4 attacker takes only 1 of 2
    available 2/2 blockers (vs menace which takes 2). Confirms the
    `needed = 2 if MENACE else 1` branch is the menace-specific path.
    """
    gs = _fresh_gs()
    atk = _mk_creature("Plain Beast", 3, 4, colors=["R"])  # no MENACE tag
    blk1 = _mk_creature("Bear A", 2, 2, colors=["G"])
    blk2 = _mk_creature("Bear B", 2, 2, colors=["G"])
    gs.bf_a = [atk]
    gs.bf_b = [blk1, blk2]

    dmg, atk_losses, blk_losses, ll, dll, creatures_hit = _resolve_combat(gs, "a")

    # Only 1 blocker assigned -> attacker takes 2 dmg < 4 toughness -> survives
    assert atk_losses == [], "non-menace 3/4 with 1 blocker assigned survives 2 damage"
    assert dmg == 0, "blocked attacker deals no damage to defender"
    assert len(blk_losses) == 1, "the single assigned blocker dies to 3 damage"


if __name__ == "__main__":
    test_menace_damage_accumulates_kills_attacker()
    test_menace_forces_two_blocker_requirement()
    test_non_menace_only_takes_one_blocker()
    print("ALL 3 TESTS PASS")
