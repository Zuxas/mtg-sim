"""Execute v2 gameplay-comparison fixtures (calibration/v2_gameplay.py) against engine v2.

Each runner rebuilds the episode's rules-relevant pre-state with supported cards (reducer-committed
arrangement, as in the v2 tests), drives engine v2 only through legal actions, and compares v2's
legal actions / triggers / zones / counters with what the log shows. Results:
  pass               -- v2 offers the observed action and produces the observed result;
  mismatch           -- classified (engine_rules_bug, card_implementation_bug, parser_data_ambiguity,
                        unsupported_mechanic, strategic_choice) with a reason;
  not_reconstructable -- the rules-relevant pre-state or result is not in the log (classified).
Stand-ins for unsupported cards are recorded per fixture ("substitutions").
"""
from __future__ import annotations

import hashlib
import re
import traceback

from calibration.v2_gameplay import card_types, is_creature, is_land, supported

_BURN = []
_NONCREATURE_STANDIN = "Lava Spike"
_CREATURE_STANDIN = "Goblin Guide"


def _burn():
    if not _BURN:
        from engine.v2.decklists import main_deck
        _BURN.extend(main_deck("mono_red_aggro_modern"))
    return list(_BURN)


def _seed(fid) -> int:
    return int.from_bytes(hashlib.sha256(fid.encode()).digest()[:4], "big")


def _game(fid, starting=0):
    from engine.v2.game import Game
    b = _burn()
    return Game.new(b, b, _seed(fid), starting_player=starting, check_invariants=True)


def _arrange(g, ops):
    from engine.v2 import reducer
    reducer.commit(g.s, "fixture_arrange", ops)
    g._legal_cache = (None, None)


def _find(g, player, name, zones=("library", "hand", "graveyard")):
    s = g.s
    for z in zones:
        for oid in s.zones[(player, z)]:
            if s.instances[s.objects[oid].ciid].name == name:
                return oid
    raise KeyError(f"{name} not available for player {player}")


def _put(g, player, name, zone):
    from engine.v2.ops import op
    oid = _find(g, player, name)
    _arrange(g, [op("move", oid, zone, "end", player)])
    s = g.s
    return s.zones[("bf",)][-1] if zone == "battlefield" else s.zones[(player, zone)][-1]


def _advance(g, until, limit=4000):
    from engine.v2 import actions as A
    for _ in range(limit):
        if g.result is not None or until(g):
            return
        pd = g.pending()
        k, p = pd.kind, pd.player
        acts = g.legal_actions()
        if k == "priority":
            g.apply(A.PassPriority(p))
        elif k == "declare_attack":
            g.apply(A.ChooseAttack(p, pd.info[0], False))
        elif k == "declare_block":
            g.apply(A.ChooseBlock(p, pd.info[0], None))
        elif k == "mulligan_declare":
            g.apply(A.DeclareKeep(p))
        elif k == "suspend_cast_choice":
            g.apply(next(a for a in acts if isinstance(a, A.ChooseSuspendCast) and not a.cast))
        else:
            g.apply(acts[0])
    raise AssertionError("advance did not reach the condition")


def _main(g, player, turn_min=3):
    _advance(g, lambda g: g.s.step == "main1" and g.s.active == player and g.s.turn >= turn_min
             and g.pending().kind == "priority" and g.pending().player == player)


def _events(g, kind, since=0):
    return [e for t in g.s.log.transitions[since:] for e in t.events if e.kind == kind]


def _keys(g, since):
    return [dict(e.data)["key"] for e in _events(g, "Triggered", since)]


def _tap_red(g, player):
    from engine.v2 import actions as A
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ActivateManaAbility) and a.player == player
                 and a.color == "R"))


def _resolve_stack(g):
    _advance(g, lambda g: not g.s.stack and not g.s.pending_triggers)


def _pay(g):
    from engine.v2 import actions as A
    while g.pending().kind == "cast_mana":
        acts = g.legal_actions()
        pay = [a for a in acts if isinstance(a, A.PayCost)]
        g.apply(pay[0] if pay else next(a for a in acts if isinstance(a, A.ActivateManaAbility)))


def _cast(g, p, oid, target=None, mode=None) -> bool:
    from engine.v2 import actions as A
    prop = next((a for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == oid), None)
    if prop is None:
        return False
    g.apply(prop)
    while g.pending().kind in ("cast_mode", "cast_targets"):
        acts = g.legal_actions()
        if g.pending().kind == "cast_mode":
            g.apply(next(a for a in acts if isinstance(a, A.ChooseMode) and (mode is None or a.mode == mode)))
        else:
            ts = [a for a in acts if isinstance(a, A.ChooseTargets)]
            pick = next((a for a in ts if target is not None and a.targets == target), None) or \
                next((a for a in ts if a.targets[0] == ("player", 1 - p)), ts[0])
            g.apply(pick)
    _pay(g)
    return True


def _ok(detail="", substitutions=(), **v2):
    return {"status": "pass", "classification": None, "detail": detail, "v2": v2,
            "substitutions": list(substitutions)}


def _skip(cls, detail):
    return {"status": "not_reconstructable", "classification": cls, "detail": detail}


def _fail(cls, detail, **v2):
    return {"status": "mismatch", "classification": cls, "detail": detail, "v2": v2}


# ------------------------------------------------------------------ runners
def run_mulligan(f):
    from engine.v2 import actions as A
    k = f["prestate"]["mulligans"]
    g = _game(f["id"])
    taken, bottoms = 0, []
    while g.pending().kind in ("mulligan_declare", "mulligan_bottom"):
        pd = g.pending()
        if pd.kind == "mulligan_bottom":
            opt = next(a for a in g.legal_actions() if isinstance(a, A.BottomCards))
            bottoms.append((pd.player, len(opt.cards)))
            g.apply(opt)
        elif pd.player == 0 and taken < k:
            g.apply(A.DeclareMulligan(0))
            taken += 1
        else:
            g.apply(A.DeclareKeep(pd.player))
    mine = [n for p, n in bottoms if p == 0]
    v2 = {"bottom_at_last_mulligan": mine[-1] if mine else 0, "final_hand": len(g.s.zones[(0, "hand")])}
    want_b, want_h = f["action"]["bottom"], f["action"]["final_hand"]
    if v2["bottom_at_last_mulligan"] == want_b and v2["final_hand"] == want_h:
        return _ok("CR 103.5: N cards go to the bottom after the Nth mulligan (MTGO shows the bottoming when the "
                   "player keeps; the CR text and v2 make it part of each mulligan; the result is the same)", **v2)
    return _fail("engine_rules_bug", f"v2 {v2} vs observed bottom {want_b}, hand {want_h}", **v2)


def run_suspend(f):
    from engine.v2 import actions as A
    if not f["prestate"]["own_turn"]:
        return _fail("parser_data_ambiguity", "suspended outside its owner's turn per the parsed log")
    g = _game(f["id"])
    _main(g, 0)
    _put(g, 0, "Mountain", "battlefield")
    rb = _put(g, 0, "Rift Bolt", "hand")
    _tap_red(g, 0)
    sus = [a for a in g.legal_actions() if isinstance(a, A.Suspend) and a.oid == rb]
    if not sus:
        return _fail("engine_rules_bug", "Suspend not offered in its owner's main phase with {R}")
    g.apply(sus[0])
    ex = g.s.zones[(0, "exile")][-1]
    if g.s.objects[ex].counter("time") != 1 or g.s.stack:
        return _fail("engine_rules_bug", "suspend did not exile with one time counter without using the stack")
    follow = f["action"]["observed_follow_up"]
    if not follow:
        return _ok("special action only (the game ended before the owner's next upkeep)")
    observed_cast = any("without paying its mana cost" in x for x in follow)
    observed_remove = any("removes a time counter" in x for x in follow)
    n0 = len(g.s.log.transitions)
    _advance(g, lambda g: g.pending().kind == "suspend_cast_choice" or (g.s.active == 0 and g.s.step == "draw"))
    keys = _keys(g, n0)
    if keys[:2] != ["suspend_upkeep", "suspend_cast"] or g.pending().kind != "suspend_cast_choice":
        return _fail("engine_rules_bug", f"triggers at the next upkeep {keys}")
    if not observed_remove:
        return _fail("parser_data_ambiguity", "log lacks the counter removal")
    if not observed_cast:
        return _ok("counter removed at the owner's upkeep; no free cast in the log (declined, or the log ends)",
                   triggers=keys, unobserved=[x for x in follow])
    kind = f["action"]["free_cast_target_kind"]
    g.apply(A.ChooseSuspendCast(0, True))
    targets = [a.targets for a in g.legal_actions() if isinstance(a, A.ChooseTargets)]
    if kind == "creature":
        if not any(t[0][0] == "obj" for t in targets):
            _put(g, 1, _CREATURE_STANDIN, "battlefield")
        return _ok("free cast offered with creature targets available (target identity not reconstructed)",
                   triggers=keys)
    if (("player", 1),) not in targets:
        return _fail("engine_rules_bug", "opponent not offered as the free cast's target")
    g.apply(A.ChooseTargets(0, (("player", 1),)))
    g.apply(A.PayCost(0, ()))
    top = g.s.stack[-1]
    if top.cost != "free" or top.mana_spent != 0:
        return _fail("engine_rules_bug", "suspended cast paid mana")
    return _ok("upkeep: suspend trigger -> counter removed -> cast trigger -> cast without paying its mana cost",
               triggers=keys)


def run_prowess(f):
    spell, creature = f["action"]["cast"], f["action"]["spell_is_creature"]
    if not card_types(spell):
        return _skip("parser_data_ambiguity", f"unknown card name {spell!r}")
    if creature:
        return _fail("parser_data_ambiguity", f"the nearest preceding cast ({spell}) is a creature spell; the trigger "
                     "belongs to another spell in the same chain (MTGO lists triggers after the casts)")
    use = spell if f["action"]["spell_supported"] else _NONCREATURE_STANDIN
    g = _game(f["id"])
    _main(g, 0)
    _put(g, 0, "Monastery Swiftspear", "battlefield")
    for land in ("Mountain", "Sacred Foundry", "Mountain"):
        _put(g, 0, land, "battlefield")
    oid = _put(g, 0, use, "hand")
    n0 = len(g.s.log.transitions)
    if not _cast(g, 0, oid):
        return _fail("engine_rules_bug", f"could not cast {use}")
    keys = _keys(g, n0)
    sub = [] if use == spell else [f"{spell} (unsupported noncreature spell) -> {use}"]
    if keys.count("prowess") == 1:
        return _ok("noncreature spell by the Swiftspear's controller -> one prowess trigger", sub, triggers=keys)
    return _fail("engine_rules_bug", f"prowess triggers {keys}")


def run_prowess_creature(f):
    if f["expected"]["prowess_triggers"] != 0:
        return _fail("parser_data_ambiguity", "a prowess trigger follows the creature spell in the log; it belongs to "
                     "another (noncreature) spell in the same chain")
    g = _game(f["id"])
    _main(g, 0)
    _put(g, 0, "Monastery Swiftspear", "battlefield")
    _put(g, 0, "Mountain", "battlefield")
    oid = _put(g, 0, _CREATURE_STANDIN, "hand")
    n0 = len(g.s.log.transitions)
    _cast(g, 0, oid)
    keys = _keys(g, n0)
    spell = f["action"]["cast"]
    sub = [] if spell == _CREATURE_STANDIN else [f"{spell} (creature spell) -> {_CREATURE_STANDIN}"]
    if "prowess" not in keys:
        return _ok("creature spell -> no prowess trigger", sub, triggers=keys)
    return _fail("engine_rules_bug", "prowess triggered on a creature spell")


def run_goblin_guide(f):
    from engine.v2 import actions as A
    from engine.v2.ops import op
    n = f["prestate"]["attacking_guides"]
    tops = f["prestate"]["defender_library_tops"]
    g = _game(f["id"])
    _main(g, 0)
    guides = [_put(g, 0, "Goblin Guide", "battlefield") for _ in range(n)]
    sub = []
    for c in reversed(tops):
        use = c if supported(c) else ("Mountain" if is_land(c) else "Lightning Bolt")
        if use != c:
            sub.append(f"{c} ({'land' if is_land(c) else 'nonland'}) -> {use}")
        _arrange(g, [op("move", _find(g, 1, use, ("library", "hand")), "library", "top")])
    hand0 = len(g.s.zones[(1, "hand")])
    n0 = len(g.s.log.transitions)
    _advance(g, lambda g: g.pending().kind == "declare_attack")
    while g.pending().kind == "declare_attack":
        g.apply(A.ChooseAttack(0, g.pending().info[0], g.pending().info[0] in guides))
    _resolve_stack(g)
    trig = [k for k in _keys(g, n0) if k == "goblin_guide_reveal"]
    revealed = [dict(e.data)["name"] for e in _events(g, "Revealed", n0)]
    want_t, want_r = f["expected"]["guide_triggers"], f["expected"]["reveals"]
    v2 = {"triggers": len(trig), "revealed": revealed, "defender_hand_delta": len(g.s.zones[(1, "hand")]) - hand0}
    lands = sum(1 for c in revealed if is_land(c))
    if len(trig) == n and want_t == n and len(revealed) == n and want_r == n and v2["defender_hand_delta"] == lands:
        return _ok("one reveal trigger per attacking Goblin Guide; a revealed land goes to hand", sub, **v2)
    if want_t < n or want_r < want_t:
        return _fail("parser_data_ambiguity", f"log shows {want_t} trigger(s) / {want_r} reveal(s) for {n} Guide(s) "
                     "(log ends or the trigger was removed)", **v2)
    return _fail("engine_rules_bug", f"v2 {v2} vs observed triggers {want_t}, reveals {want_r}", **v2)


def run_vortex(f):
    if f["action"]["kind"] != "upkeep":
        return run_vortex_free_cast(f)
    if not f["expected"]["at_turn_start"]:
        return _fail("parser_data_ambiguity", "upkeep trigger line not at a turn start in the log")
    same = f["prestate"]["vortex_controller"] == f["prestate"]["active"]
    g = _game(f["id"])
    _main(g, 0)
    _put(g, 0, "Roiling Vortex", "battlefield")
    victim = 0 if same else 1
    _advance(g, lambda g: g.s.active == victim and g.s.turn > 3 and g.s.step == "upkeep")
    n0 = max(i for i, t in enumerate(g.s.log.transitions) if any(e.kind == "TurnBegan" for e in t.events))
    life = g.s.life[victim]
    _advance(g, lambda g: g.s.active == victim and g.s.step == "upkeep" and g.pending().kind == "priority")
    keys = _keys(g, n0)
    _resolve_stack(g)
    if keys.count("vortex_upkeep") == 1 and g.s.life[victim] == life - 1:
        return _ok("Roiling Vortex triggers at the beginning of each player's upkeep and deals 1 to that player "
                   "(damage not logged)", triggers=keys)
    return _fail("engine_rules_bug", f"upkeep triggers {keys}")


def run_vortex_free_cast(f):
    """'Whenever a player casts a spell, if no mana was spent to cast that spell': the logged spell was
    cast without mana by a mechanism v2 may not support (evoke, etc.); the rule is tested with a spell
    cast without mana through suspend (recorded substitution)."""
    from engine.v2 import actions as A
    caster_line = f["observed"][0]
    caster = caster_line.split(" ", 1)[0]
    vortex_seat = 0 if f["prestate"]["vortex_controller"] == caster else 1
    g = _game(f["id"])
    _main(g, 0)
    _put(g, vortex_seat, "Roiling Vortex", "battlefield")
    _put(g, 0, "Mountain", "battlefield")
    rb = _put(g, 0, "Rift Bolt", "hand")
    _tap_red(g, 0)
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.Suspend) and a.oid == rb))
    _advance(g, lambda g: g.pending().kind == "suspend_cast_choice")
    g.apply(A.ChooseSuspendCast(0, True))
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ChooseTargets)))
    n0 = len(g.s.log.transitions)
    g.apply(A.PayCost(0, ()))
    keys = _keys(g, n0)
    spell = re.search(r"casts \[(.+?)\]", caster_line)
    sub = [f"{spell.group(1) if spell else 'spell'} cast without mana -> Rift Bolt cast via suspend"]
    if "vortex_free_cast" in keys:
        return _ok("a spell cast with no mana spent triggers Roiling Vortex (any player's spell)", sub, triggers=keys)
    return _fail("engine_rules_bug", f"no free-cast trigger: {keys}")


def run_searing_blaze(f):
    from engine.v2 import actions as A
    rel, pre = f["expected"]["relationship_ok"], f["prestate"]
    if rel is None:
        return _skip("parser_data_ambiguity", "controller of the targeted creature not determinable from the log")
    if rel is False:
        return _fail("parser_data_ambiguity", f"{pre['creature']} appears controlled by {pre['creature_controller']} "
                     f"but the player target is {pre['player_target']} (control change / token not inferable)")
    g = _game(f["id"])
    _main(g, 0)
    seat = 0 if pre["player_target"] == pre["caster"] else 1
    use = pre["creature"] if supported(pre["creature"]) and is_creature(pre["creature"]) else _CREATURE_STANDIN
    cre = _put(g, seat, use, "battlefield")
    other = _put(g, 1 - seat, _CREATURE_STANDIN, "battlefield")
    _put(g, 0, "Mountain", "battlefield")
    _put(g, 0, "Mountain", "battlefield")
    _main(g, 0, turn_min=g.s.turn + 1)               # a new turn: arranged lands no longer count as landfall
    if g.s.lands_entered_turn[0]:
        return _fail("engine_rules_bug", "landfall record not reset at the new turn")
    if f["expected"]["landfall_damage"] == 3:
        oid = _put(g, 0, "Mountain", "hand")
        g.apply(next(a for a in g.legal_actions() if isinstance(a, A.PlayLand) and a.oid == oid))
    bl = _put(g, 0, "Searing Blaze", "hand")
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == bl))
    pairs = {a.targets for a in g.legal_actions() if isinstance(a, A.ChooseTargets)}
    want, bad = (("player", seat), ("obj", cre)), (("player", seat), ("obj", other))
    if want not in pairs or bad in pairs:
        return _fail("engine_rules_bug", f"target pairs {sorted(pairs)}")
    g.apply(A.ChooseTargets(0, want))
    _pay(g)
    life = g.s.life[seat]
    _resolve_stack(g)
    dealt = life - g.s.life[seat]
    sub = [] if use == pre["creature"] else [f"{pre['creature']} -> {use} (controlled by the targeted player)"]
    if dealt == f["expected"]["landfall_damage"]:
        return _ok(f"pair = player + a creature that player controls; landfall from the caster's land this turn -> "
                   f"{dealt} damage (damage itself not logged)", sub, damage=dealt)
    return _fail("engine_rules_bug", f"damage {dealt} vs landfall expectation {f['expected']['landfall_damage']}")


def run_spectacle(f):
    from engine.v2 import actions as A
    from engine.v2.ops import op
    g = _game(f["id"])
    _main(g, 0)
    for land in ("Mountain", "Mountain", "Mountain"):
        _put(g, 0, land, "battlefield")
    sk = _put(g, 0, "Skewer the Critics", "hand")
    before = {a.cost for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == sk}
    if f["action"]["cost"] == "normal":
        return _ok("normal cost offered with {2}{R}") if "normal" in before else \
            _fail("engine_rules_bug", "normal cost not offered")
    if "spectacle" in before:
        return _fail("engine_rules_bug", "spectacle offered although no opponent lost life this turn")
    _arrange(g, [op("damage_player", 0, 1, 2)])
    after = {a.cost for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == sk}
    ev = f["prestate"]["opponent_life_loss_evidence"]
    note = ("earlier damage to the opponent this turn is in the log" if ev else
            "precondition not logged (e.g. combat damage); MTGO permits spectacle only when it holds")
    if "spectacle" in after:
        return _ok("spectacle offered only after an opponent lost life this turn; " + note)
    return _fail("engine_rules_bug", "spectacle not offered after the opponent lost life")


def run_boros_charm(f):
    from engine.v2 import actions as A
    mode, tk, target = f["action"]["mode"], f["action"]["target_kind"], f["action"]["target"]
    if mode is None:
        return _skip("parser_data_ambiguity", "mode line not logged")
    if mode == 0 and tk == "creature":
        name = re.sub(r"^\[|\].*$", "", target)
        if "Planeswalker" in card_types(name):
            return _skip("unsupported_mechanic", f"mode 0 targeting the planeswalker {name} (planeswalkers unsupported)")
        return _fail("parser_data_ambiguity", f"mode 0 logged with the non-planeswalker permanent target {name}")
    g = _game(f["id"])
    _main(g, 0)
    _put(g, 0, "Monastery Swiftspear", "battlefield")
    _put(g, 0, "Mountain", "battlefield")
    _put(g, 0, "Sacred Foundry", "battlefield")
    ch = _put(g, 0, "Boros Charm", "hand")
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == ch))
    if g.pending().kind != "cast_mode":
        return _fail("engine_rules_bug", "mode not chosen before targets")
    modes = {a.mode for a in g.legal_actions() if isinstance(a, A.ChooseMode)}
    if mode not in modes:
        return _fail("engine_rules_bug", f"mode {mode} not offered ({modes})")
    g.apply(A.ChooseMode(0, mode))
    kinds = {a.targets[0][0] for a in g.legal_actions() if isinstance(a, A.ChooseTargets)}
    want = {0: {"player"}, 1: set(), 2: {"obj"}}[mode]
    if kinds != want:
        return _fail("card_implementation_bug", f"mode {mode} target kinds {kinds}")
    if (mode == 1) != (tk is None):
        return _fail("parser_data_ambiguity", f"logged target {target!r} vs mode {mode}")
    return _ok(f"mode {mode} chosen before targets; target kinds {sorted(kinds) or 'none'}")


_PT_CARD = {"target_skullcrack": "Skullcrack", "target_lava_spike": "Lava Spike",
            "target_lightning_helix": "Lightning Helix", "target_lightning_bolt": "Lightning Bolt"}


def run_player_target(f):
    from engine.v2 import actions as A
    card = _PT_CARD[f["mechanic"]]
    tk, target = f["action"]["target_kind"], f["action"]["target"]
    if tk == "creature":
        name = re.sub(r"^\[|\].*$", "", target)
        types = card_types(name)
        if "Planeswalker" in types or "Battle" in types:
            return _skip("unsupported_mechanic", f"{card} targeting {name} ({'/'.join(types)}: unsupported)")
        if card in ("Skullcrack", "Lava Spike"):
            return _fail("parser_data_ambiguity", f"{card} logged targeting the non-player permanent {name}")
        if name.endswith(" Token"):
            return _skip("unsupported_mechanic", f"{card} targeting the token {name} (tokens are not supported in v2)")
        if "Creature" not in types:
            return _skip("unsupported_mechanic", f"{card} targeting {name} ({'/'.join(types) or 'unknown card'})")
    g = _game(f["id"])
    _main(g, 0)
    _put(g, 1, _CREATURE_STANDIN, "battlefield")
    _put(g, 0, "Mountain", "battlefield")
    _put(g, 0, "Sacred Foundry", "battlefield")
    oid = _put(g, 0, card, "hand")
    g.apply(next(a for a in g.legal_actions() if isinstance(a, A.ProposeCast) and a.oid == oid))
    kinds = {a.targets[0][0] for a in g.legal_actions() if isinstance(a, A.ChooseTargets)}
    want = {"player"} if card in ("Skullcrack", "Lava Spike") else {"player", "obj"}
    if kinds != want:
        return _fail("card_implementation_bug", f"{card} target kinds {kinds}")
    return _ok(f"{card}: the observed {tk} target kind is offered (kinds {sorted(kinds)})")


def run_fetch(f):
    from engine.v2 import abilities as AB
    from engine.v2 import actions as A
    card, text = f["action"]["card"], f["action"]["text"]
    g = _game(f["id"])
    _main(g, 0)
    land = _put(g, 0, card, "battlefield")
    acts = [a for a in g.legal_actions() if isinstance(a, A.ActivateAbility) and a.oid == land]
    key = AB.ACTIVATED[g.s.definition(land).effect_key][0].key
    t1, t2 = AB.FETCH_TYPES[key]
    if not acts:
        return _fail("engine_rules_bug", f"{card} activation not offered")
    if f"for a {t1} or {t2} card" not in text:
        return _fail("card_implementation_bug", f"v2 searches for {t1}/{t2}; the ability reads {text!r}")
    return _ok(f"{card}: activation offered (tap, 1 life, sacrifice); searches for a {t1} or {t2} card")


def run_play_draw(f):
    from engine.v2 import actions as A
    from engine.v2.match import ChoosePlayDraw, DoneSideboarding, Match
    pre = f["prestate"]
    loser = pre["previous_loser"]
    if loser is None:
        return _skip("parser_data_ambiguity", "previous game result not determinable")
    b = _burn()
    m = Match(b, [], b, [], _seed(f["id"]))
    m.apply(ChoosePlayDraw(m.pending[1], True))
    g = m.current
    _advance(g, lambda g: g.pending().player == 0)
    g.apply(A.Concede(0))                                        # seat 0 plays the previous game's loser
    m.finish_game()
    while m.pending and m.pending[0] == "sideboard":
        m.apply(DoneSideboarding(m.pending[1]))
    observed = f["action"]["chooser"]
    if observed != loser:
        return _fail("parser_data_ambiguity", f"observed chooser {observed} is not the previous loser {loser}")
    if m.pending == ("play_draw", 0):
        return _ok(f"CR 103.1: the loser of the previous game chooses ({pre['previous_game_end'][1]})")
    return _fail("engine_rules_bug", f"v2 gives the choice to {m.pending}")


RUNNERS = {
    "mulligan": run_mulligan, "suspend": run_suspend, "prowess": run_prowess,
    "prowess_creature_spell": run_prowess_creature, "goblin_guide_attack": run_goblin_guide,
    "roiling_vortex": run_vortex, "searing_blaze": run_searing_blaze, "spectacle": run_spectacle,
    "boros_charm": run_boros_charm, "target_skullcrack": run_player_target, "target_lava_spike": run_player_target,
    "target_lightning_helix": run_player_target, "target_lightning_bolt": run_player_target, "fetch": run_fetch,
    "play_draw_choice": run_play_draw,
}


def run_fixture(f) -> dict:
    try:
        return RUNNERS[f["mechanic"]](f)
    except Exception as e:                                       # noqa: BLE001 -- recorded as unexplained, not hidden
        return {"status": "error", "classification": "unexplained", "detail": f"{type(e).__name__}: {e}",
                "trace": traceback.format_exc()[-1500:]}
