"""test_handler_sweep.py -- issue #26.

Calls every registered ETB and spell handler on a small fixture board and
fails if any of them raises. card_effects.on_etb / on_spell_resolve catch
handler exceptions, so before this test a handler that crashed on every call
simply made its card do nothing.

Run: python tests/test_handler_sweep.py          (exit 1 on any failure)
     python tests/test_handler_sweep.py -v       (list every failing handler)
"""
import sys, os, random, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.card import Card, Tag
from engine.game_state import GameState
from engine import card_effects


def _card(name, type_line, cmc=2, p=None, t=None, cost="{1}{R}"):
    c = Card(name=name, mana_cost=cost, cmc=cmc, type_line=type_line, oracle_text="",
             power=p, toughness=t, colors=["R"])
    if "Creature" in type_line:
        c.tags = set(getattr(c, "tags", None) or set()) | {Tag.CREATURE}
        c.summoning_sickness = False
    return c


def _side():
    gs = GameState(mainboard=[], on_play=True)
    gs.turn = 4
    z = gs.zones
    z.battlefield = [_card("Mountain", "Basic Land - Mountain", 0, cost="") for _ in range(4)]
    z.battlefield.append(_card("Grizzly Bears", "Creature - Bear", 2, "2", "2"))
    z.hand = [_card("Mountain", "Basic Land - Mountain", 0, cost=""),
              _card("Hill Giant", "Creature - Giant", 4, "3", "3"),
              _card("Shock", "Instant", 1, cost="{R}")]
    z.graveyard = [_card("Gray Ogre", "Creature - Ogre", 3, "2", "2"),
                   _card("Opt", "Instant", 1, cost="{U}")]
    z.library = [_card(f"Filler {i}", "Creature - Bear" if i % 2 else "Basic Land - Mountain",
                       2, "2", "2") for i in range(20)]
    for c in z.battlefield:
        if c.is_land():
            gs.mana_pool.add_land(c.type_line, c.name)
    return gs


def _fixture():
    gs, opp = _side(), _side()
    gs._match_opp, opp._match_opp = opp, gs
    return gs


def sweep():
    """Returns [(kind, card name, 'ExcType: message'), ...] for handlers that raise."""
    failures = []
    for kind, registry in (("etb", card_effects.ETB_EFFECTS),
                           ("spell", card_effects.SPELL_EFFECTS)):
        for name, fn in sorted(registry.items()):
            random.seed(0)
            gs = _fixture()
            is_spell = kind == "spell"
            card = _card(name, "Instant" if is_spell else "Creature - Test", 3, "2", "2")
            (gs.zones.graveyard if is_spell else gs.zones.battlefield).append(card)
            try:
                fn(gs, card)
            except Exception as e:
                failures.append((kind, name, f"{type(e).__name__}: {e}"))
    return failures


def test_no_handler_raises():
    failures = sweep()
    by_error = collections.Counter(msg for _, _, msg in failures)
    summary = "\n".join(f"  {n:4d} x {msg[:110]}" for msg, n in by_error.most_common(12))
    assert not failures, f"{len(failures)} handlers raise on the fixture board:\n{summary}"


def test_failures_are_counted_and_reported():
    """A handler that raises is counted and shows up in the exit summary;
    with SIM_DEBUG set it raises instead."""
    def boom(gs, card):
        raise ValueError("boom")
    card_effects.ETB_EFFECTS["__sweep_probe__"] = boom
    saved, saved_env = dict(card_effects.HANDLER_ERRORS), os.environ.pop("SIM_DEBUG", None)
    try:
        card_effects.HANDLER_ERRORS.clear()
        gs = _fixture()
        probe = _card("__sweep_probe__", "Creature - Test", 3, "2", "2")
        card_effects.on_etb(gs, probe)
        card_effects.on_etb(gs, probe)
        assert card_effects.HANDLER_ERRORS == {("ETB", "__sweep_probe__", "ValueError"): 2}
        summary = "\n".join(card_effects.handler_error_summary())
        assert "2 failed calls" in summary and "__sweep_probe__" in summary, summary
        assert summary.isascii()
        os.environ["SIM_DEBUG"] = "1"
        try:
            card_effects.on_etb(gs, probe)
            raise AssertionError("SIM_DEBUG should re-raise")
        except ValueError:
            pass
    finally:
        del card_effects.ETB_EFFECTS["__sweep_probe__"]
        os.environ.pop("SIM_DEBUG", None)
        if saved_env is not None:
            os.environ["SIM_DEBUG"] = saved_env
        card_effects.HANDLER_ERRORS.clear()
        card_effects.HANDLER_ERRORS.update(saved)


if __name__ == "__main__":
    test_failures_are_counted_and_reported()
    fails = sweep()
    total = len(card_effects.ETB_EFFECTS) + len(card_effects.SPELL_EFFECTS)
    if "-v" in sys.argv:
        for kind, name, msg in fails:
            print(f"  {kind:5s} {name}: {msg}")
    for msg, n in collections.Counter(m for _, _, m in fails).most_common(15):
        print(f"  {n:4d} x {msg[:120]}")
    print(f"handler sweep: {total - len(fails)}/{total} clean, {len(fails)} raise")
    sys.exit(1 if fails else 0)
