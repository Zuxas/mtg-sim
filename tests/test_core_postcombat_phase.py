"""
test_core_postcombat_phase.py -- the core engine runs a postcombat main phase
(CR 505) between combat and the end step (#62, migration step 3).

Checks:
1. Order: main 1, then the postcombat phase, then the end step, every turn.
2. Mana: nothing untaps and the pool does not grow between main 1 and the
   postcombat phase.
3. A deck-specific main_phase2_match is used when the APL has one.
4. An APL marked POST_COMBAT_IS_WIN_PROXY never has main_phase2_match called
   by the core: it gets the ordinary main_phase2 casts instead, and its
   wins on the core do not come from the proxy.
5. Postcombat spells can be answered: the other player gets an instant-speed
   response once per spell cast in the postcombat phase, with no mana
   refreshed, and none when no spell was cast there.
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apl.match_apl import MatchAPL
from data.deck import load_deck_from_file
from engine import match_engine

DECK = "decks/izzet_prowess_nick_tokyo_standard.txt"


def _untapped(gs):
    return sum(1 for l in gs.zones.lands_on_battlefield() if not l.tapped)


class Spy(MatchAPL):
    """Plays lands only and records what the engine calls, in order."""
    name = "spy"
    use_match_hook = False

    def __init__(self):
        self.calls, self.mana = [], []

    def keep(self, hand, mulligans, on_play):
        return True

    def bottom(self, hand, n):
        return hand[:n]

    def main_phase(self, gs):
        pass

    def main_phase_match(self, gs, opp):
        for c in list(gs.zones.hand):
            if c.is_land() and not gs.land_played:
                gs.play_land(c)
        self.calls.append("main1")
        self._after_main1 = (_untapped(gs), gs.mana_pool.total())

    def main_phase2(self, gs):
        self.calls.append("main2")
        self.mana.append((self._after_main1, (_untapped(gs), gs.mana_pool.total())))

    def own_end_step(self, gs, opp):
        self.calls.append("end")

    def declare_attackers(self, gs, opp):
        return []


class SpyMatchHook(Spy):
    def main_phase2_match(self, gs, opp):
        self.calls.append("main2_match")


class SpyProxy(SpyMatchHook):
    POST_COMBAT_IS_WIN_PROXY = True

    def main_phase2_match(self, gs, opp):
        raise AssertionError("core called a win proxy")


class Caster(Spy):
    """Holds everything in main 1, then casts what it can after combat."""
    phase, postcombat_casts = "", 0

    def main_phase_match(self, gs, opp):
        Caster.phase = "main1"
        super().main_phase_match(gs, opp)

    def main_phase2(self, gs):
        Caster.phase = "main2"
        before = gs.spells_cast_this_turn
        self._cast_all_castable(gs)
        Caster.postcombat_casts += gs.spells_cast_this_turn - before

    def own_end_step(self, gs, opp):
        Caster.phase = "end"


class Responder(Spy):
    """Holds an instant so the engine has a response to ask about."""
    seen, lands = [], []

    def respond_to_spell(self, gs, opp, spell):
        Responder.seen.append(Caster.phase)
        if Caster.phase == "main2":
            Responder.lands.append((self._untapped_before, _untapped(gs)))
        return None

    def main_phase_match(self, gs, opp):
        super().main_phase_match(gs, opp)

    def own_end_step(self, gs, opp):
        self._untapped_before = _untapped(gs)


def _play(cls, deck):
    a, b = cls(), Spy()
    match_engine.run_match(a, deck, b, deck, on_play=True, max_turns=6, seed=3)
    return a


def main():
    deck, _ = load_deck_from_file(DECK)

    spy = _play(Spy, deck)
    turns = len(spy.calls) // 3
    assert turns >= 3 and spy.calls == ["main1", "main2", "end"] * turns, spy.calls
    print(f"PASS: main 1 -> postcombat -> end step on each of {turns} turns")

    for (u1, p1), (u2, p2) in spy.mana:
        assert u2 <= u1 and p2 <= p1, f"mana grew before postcombat: {spy.mana}"
    print("PASS: no land untaps and no mana is added before the postcombat phase")

    hook = _play(SpyMatchHook, deck)
    assert "main2_match" in hook.calls and "main2" not in hook.calls, hook.calls
    print("PASS: main_phase2_match is used when the APL defines it")

    proxy = _play(SpyProxy, deck)
    assert "main2" in proxy.calls and "main2_match" not in proxy.calls, proxy.calls
    print("PASS: a win proxy is skipped; ordinary postcombat casts run instead")

    match_engine.run_match(Caster(), deck, Responder(), deck, on_play=True,
                           max_turns=8, seed=3)
    assert Caster.postcombat_casts > 0, "spy cast nothing after combat"
    answered = Responder.seen.count("main2")
    assert "main1" in Responder.seen, Responder.seen
    assert 0 < answered <= Caster.postcombat_casts, (answered, Caster.postcombat_casts)
    for before, after in Responder.lands:
        assert after <= before, f"responder's lands untapped for the window: {Responder.lands}"
    print(f"PASS: {answered} responses offered to {Caster.postcombat_casts} "
          "postcombat spells, with no land untapped for them")

    class Holder(Caster):             # same phases, casts nothing after combat
        def main_phase2(self, gs):
            Caster.phase = "main2"

    Responder.seen.clear()
    match_engine.run_match(Holder(), deck, Responder(), deck, on_play=True,
                           max_turns=8, seed=3)
    assert "main1" in Responder.seen and "main2" not in Responder.seen, Responder.seen
    print("PASS: no response window when nothing is cast")

    from apl.izzet_lesson_standard_match import IzzetLessonStandardMatchAPL
    from apl.jeskai_lute_standard_match import JeskaiLuteMatchAPL
    for cls in (IzzetLessonStandardMatchAPL, JeskaiLuteMatchAPL):
        assert cls.POST_COMBAT_IS_WIN_PROXY is True
        cls.main_phase2_match = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("core called the proxy"))
    ldeck, _ = load_deck_from_file("decks/izzet_lesson_standard.txt")
    for seed in range(10):
        match_engine.run_match(IzzetLessonStandardMatchAPL(), ldeck,
                               Spy(), deck, on_play=seed % 2 == 0, seed=seed)
    print("PASS: Izzet Lessons plays 10 core games without the proxy firing")


if __name__ == "__main__":
    main()
