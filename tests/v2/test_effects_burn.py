"""Effect-library slice 1: Lava Spike and Lightning Helix (damage to a target player, damage
plus life gain). Both cards are fully supported -- no rules text ignored."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.v2 import actions as A
from engine.v2.cards import SUPPORTED, definitions
from engine.v2.game import Game
from engine.v2.ops import op
from engine.v2.policies import BasicScriptedPolicy, RandomLegalPolicy
from engine.v2.record import make_record, replay
from tests.v2.decks import BURN_TEST, WU
from tests.v2.helpers import act, advance, arrange, at, cast, events, find, new_game, put


def _resolve(g):
    advance(g, lambda g: not g.s.stack)


def _main(g):
    g2 = g
    advance(g2, at("main1", active=0, turn=3))
    for land in ("Mountain", "Mountain", "Plains"):
        put(g2, 0, land, "battlefield")
    return g2


def test_lava_spike_is_an_arcane_sorcery_targeting_only_players():
    d = definitions()["Lava Spike"]
    assert d.types == ("Sorcery",) and d.subtypes == ("Arcane",)                 # CR 205.3k
    g = _main(new_game(BURN_TEST, WU))
    put(g, 1, "Youthful Knight", "battlefield")
    spike = put(g, 0, "Lava Spike", "hand")
    act(g, A.ProposeCast, player=0, oid=spike)
    opts = {a.targets for a in g.legal_actions() if isinstance(a, A.ChooseTargets)}
    assert opts == {(("player", 0),), (("player", 1),)}                          # CR 115.1


def test_lava_spike_deals_3_to_target_player():
    g = _main(new_game(BURN_TEST, WU))
    spike = put(g, 0, "Lava Spike", "hand")
    cast(g, 0, "Lava Spike", target=("player", 1), lands=("Mountain",), oid=spike)
    _resolve(g)
    assert g.s.life == [20, 17]                                                    # CR 120.3a


def test_lava_spike_has_sorcery_timing():
    g = _main(new_game(BURN_TEST, WU))
    put(g, 0, "Lava Spike", "hand")
    advance(g, at("main1", active=1))                                              # opponent's turn
    assert not any(isinstance(a, A.ProposeCast) and a.player == 0 for a in g.legal_actions())   # CR 307.1


def test_lightning_helix_damages_creature_and_controller_gains_3():
    g = _main(new_game(BURN_TEST, WU))
    knight = put(g, 1, "Youthful Knight", "battlefield")
    cast(g, 0, "Lightning Helix", target=("obj", knight), lands=("Mountain", "Plains"))
    _resolve(g)
    assert g.s.life == [23, 20]                                                    # CR 119.3
    assert knight not in g.s.objects                                               # destroyed (CR 704.5g)
    assert any(dict(e.data).get("delta") == 3 for e in events(g, "LifeChanged"))


def test_lightning_helix_at_a_player():
    g = _main(new_game(BURN_TEST, WU))
    cast(g, 0, "Lightning Helix", target=("player", 1), lands=("Mountain", "Plains"))
    _resolve(g)
    assert g.s.life == [23, 17]


def test_lightning_helix_with_illegal_target_does_not_resolve_and_gains_no_life():
    g = _main(new_game(BURN_TEST, WU))
    knight = put(g, 1, "Youthful Knight", "battlefield")
    cast(g, 0, "Lightning Helix", target=("obj", knight), lands=("Mountain", "Plains"))
    arrange(g, [op("move", knight, "graveyard", "end")])                          # target leaves before resolution
    _resolve(g)
    assert g.s.life == [20, 20]                                                    # CR 608.2b
    assert events(g, "SpellFizzled")


def test_no_supported_card_is_a_planeswalker():
    """Lava Spike reads 'target player or planeswalker'; with no planeswalker supported its legal
    targets are exactly the players. Adding a planeswalker must revisit lava_spike's target spec."""
    assert not any("Planeswalker" in d.types for d in definitions().values())
    assert "Lava Spike" in SUPPORTED and "Lightning Helix" in SUPPORTED


def test_randomized_burn_games_hold_invariants_and_replay_exactly():
    for seed in range(40):
        g = Game.new(BURN_TEST, BURN_TEST if seed % 2 else WU, 4000 + seed, starting_player=seed % 2,
                     check_invariants=True)
        pols = [RandomLegalPolicy(seed), RandomLegalPolicy(seed + 9)] if seed % 3 else \
            [BasicScriptedPolicy(), BasicScriptedPolicy()]
        g.run(pols)
        assert g.result is not None
        replay(make_record(g))


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print(f"[ok] {name}")
            except Exception as e:                                                  # noqa: BLE001
                failures += 1
                print(f"[FAIL] {name}: {type(e).__name__}: {str(e)[:200]}")
    print(f"BURN EFFECT FAILURES: {failures}")
