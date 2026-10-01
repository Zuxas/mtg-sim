"""Engine v2 vs real gameplay (milestone three, phase 1).

Parses MTGO match game logs (Match_GameLog_*.dat: MTGO's own play-by-play text, as captured by the
analyzer's MTGO import), extracts observable rules episodes that involve mechanics engine v2
supports, turns each into a self-contained comparison fixture, and executes the fixture against
engine v2.

Honesty rules:
- Only what the log shows is used. Life totals, damage amounts, mana payments, shock-land choices
  and searched cards are NOT in MTGO logs; anything depending on them is marked unobservable.
- An episode is executed only when its rules-relevant pre-state can be rebuilt with supported cards.
  When the real game used an unsupported card whose identity is irrelevant to the rule under test
  (e.g. the noncreature spell that triggered prowess), a supported card with the same relevant
  characteristic is used and the substitution is recorded in the fixture.
- Mismatches are classified: engine_rules_bug, card_implementation_bug, parser_data_ambiguity,
  unsupported_mechanic, strategic_choice. Only the first two may change the engine.

The comparison tooling lives outside engine/ and only drives engine v2 through its public API plus
reducer-committed scenario arrangement (the same mechanism the v2 tests use).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_LOG_DIR = os.path.join(os.path.dirname(ROOT), "mtg-meta-analyzer", "data", "raw", "mtgo")
FIXTURES = os.path.join(ROOT, "data", "v2_gameplay_fixtures.json")

_CARD = re.compile(r"@\[([^@]+)@:\d+,\d+:@\]")
_TRAIL = re.compile(r"(\.)[^.]{0,6}$")


# ------------------------------------------------------------------ parsing
def log_lines(path) -> list:
    """The text lines of an MTGO game log: '@P'-prefixed runs, card markup reduced to [Name]."""
    raw = open(path, "rb").read()
    out = []
    for m in re.findall(rb"@P[\x20-\x7e]{3,}", raw):
        t = _CARD.sub(lambda mm: f"[{mm.group(1)}]", m.decode("ascii"))
        t = t[2:].lstrip("@P") if t.startswith("@P@P") else t[2:]
        t = _TRAIL.sub(r"\1", t.strip())                       # drop binary noise after the final '.'
        out.append(t)
    return out


def split_games(lines) -> list:
    """Games of a match: a game starts at '... chooses to play first.' (or the first 'begins the
    game') and ends at 'wins the game' / 'has conceded' / 'loses the game'."""
    games, cur = [], None
    for i, t in enumerate(lines):
        if re.search(r" chooses to (play|draw) first\.?$", t) or (cur is None and "begins the game with" in t):
            if cur is not None and cur["lines"]:
                games.append(cur)
            cur = {"start": i, "lines": [], "chooser": None, "end": None}
            m = re.match(r"^(\S+) chooses to (play|draw) first", t)
            if m:
                cur["chooser"], cur["choice"] = m.group(1), m.group(2)
        if cur is None:
            continue
        cur["lines"].append((i, t))
        m = re.match(r"^(\S+) (wins the game|has conceded from the game|loses the game)", t)
        if m and cur["end"] is None:
            cur["end"] = (m.group(1), m.group(2))
    if cur is not None and cur["lines"]:
        games.append(cur)
    return games


TURN = re.compile(r"^Turn (\d+): (\S+)$")


def game_players(game) -> list:
    return sorted({m.group(1) for _i, t in game["lines"]
                   for m in [re.match(r"^(\S+) (?:casts|plays|begins the game|mulligans|draws|chooses|rolled) ", t)] if m})


def annotate(game) -> list:
    """[(line_no, turn, active_player, text)]; the active player's name is resolved against the
    game's players (turn lines can carry a trailing noise character)."""
    players = game_players(game)
    turn, active, out = 0, None, []
    for i, t in game["lines"]:
        m = TURN.match(t)
        if m:
            raw = m.group(2)
            cands = [p for p in players if raw == p or raw.startswith(p)]
            turn, active = int(m.group(1)), (max(cands, key=len) if cands else raw)
        out.append((i, turn, active, t))
    return out


# ------------------------------------------------------------------ card facts (public oracle data)
_DB = None


def card_types(name) -> tuple:
    global _DB
    if _DB is None:
        from engine.card_db import CardDB
        _DB = CardDB()
    d = _DB.get(name)
    if d is None:
        return ()
    tl = d.get("type_line", "").split(" // ")[0]
    return tuple(tl.split(" — ")[0].split())


def is_creature(name) -> bool:
    return "Creature" in card_types(name)


def is_land(name) -> bool:
    return "Land" in card_types(name)


def supported(name) -> bool:
    from engine.v2.cards import SUPPORTED
    return name in SUPPORTED


# ------------------------------------------------------------------ episode extraction
def extract(path) -> list:
    """Every comparison fixture (dict) of one match log."""
    match_id = re.sub(r"^Match_GameLog_|\.dat$", "", os.path.basename(path))
    lines = log_lines(path)
    games = split_games(lines)
    match_players = sorted({m.group(1) for t in lines            # both players, from the whole match
                            for m in [re.match(r"^(\S+) (?:casts|plays|chooses|begins the game|mulligans|wins|"
                                               r"has conceded|loses) ", t)] if m})
    fx = []
    prev_end = None
    prev_chooser = None
    for gi, g in enumerate(games):
        rows = annotate(g)
        src = {"file": os.path.basename(path), "match": match_id, "game": gi + 1}
        players = match_players
        fx += _mulligans(src, rows)
        fx += _suspends(src, rows)
        fx += _prowess(src, rows)
        fx += _goblin_guide(src, rows)
        fx += _vortex(src, rows)
        fx += _searing_blaze(src, rows)
        fx += _spectacle(src, rows)
        fx += _boros_charm(src, rows)
        fx += _player_target_spells(src, rows)
        fx += _fetches(src, rows)
        if gi > 0 and g.get("chooser"):
            fx.append(_play_draw(src, g, prev_end, prev_chooser, players))
        prev_end, prev_chooser = g["end"], g.get("chooser")
    return _anonymize_match(fx, match_id, match_players)


def _anonymize_match(fixtures, match_id, players):
    """Remove MTGO account names and raw match ids from committed fixtures.

    The source token is deterministic, so local raw logs remain traceable by hashing their match
    ids. Line numbers retain the precise location inside that private source.
    """
    token = hashlib.sha256(match_id.encode("utf-8")).hexdigest()[:12]
    mapping = {name: f"Player{chr(ord('A') + i)}"
               for i, name in enumerate(sorted(players, key=str.casefold))}

    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        if isinstance(value, tuple):
            return tuple(scrub(item) for item in value)
        if not isinstance(value, str):
            return value
        for name, alias in sorted(mapping.items(), key=lambda item: -len(item[0])):
            value = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])", alias, value)
        return value

    out = []
    for fixture in fixtures:
        clean = scrub(fixture)
        suffix = fixture["id"].split("-", 1)[1]
        clean["id"] = f"{token[:8]}-{suffix}"
        clean["source"]["file"] = f"match_{token}.dat"
        clean["source"]["match"] = token
        out.append(clean)
    return out


def _fx(src, mech, rows_used, **kw):
    lines = [r[3] for r in rows_used]
    ids = [r[0] for r in rows_used]
    base = {"id": f"{src['match'][:8]}-g{src['game']}-{mech}-{ids[0] if ids else 0}", "mechanic": mech,
            "source": dict(src, lines=ids), "observed": lines, "unobservable": [], "substitutions": []}
    base.update(kw)
    return base


def _mulligans(src, rows):
    out = []
    for p in sorted({m.group(1) for *_x, t in rows for m in [re.match(r"^(\S+) mulligans to", t)] if m}):
        mull = [r for r in rows if re.match(rf"^{re.escape(p)} mulligans to (\w+) cards", r[3])]
        fin = [r for r in rows if re.match(rf"^{re.escape(p)} puts (\w+) cards? on the bottom of their library and "
                                          rf"begins the game with (\w+) cards", r[3])]
        if not fin:
            continue
        m = re.match(r"^\S+ puts (\w+) cards? on the bottom of their library and begins the game with (\w+) cards",
                     fin[-1][3])
        sizes = [_num(re.match(r"^\S+ mulligans to (\w+) cards", r[3]).group(1)) for r in mull]
        # the count comes from the smallest hand reached: MTGO logs occasionally repeat a line verbatim
        out.append(_fx(src, "mulligan", mull + fin[-1:], prestate={"mulligans": 7 - min(sizes),
                                                                  "logged_mulligan_lines": len(mull)},
                       action={"bottom": _num(m.group(1)), "final_hand": _num(m.group(2))},
                       unobservable=["which cards were bottomed (hidden)"]))
    return out


_NUM = {"a": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "zero": 0}


def _num(w):
    return _NUM[w.lower()] if w.lower() in _NUM else int(w)


def _suspends(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) exiles \[Rift Bolt\] with 1 time counter", t)
        if not m:
            continue
        p = m.group(1)
        follow = []
        for r in rows[k + 1:]:
            if r[1] > turn + 2:
                break
            if r[1] > turn and r[2] == p and re.search(r"Rift Bolt", r[3]):
                follow.append(r)
        cast = [r for r in follow if "casts [Rift Bolt] without paying its mana cost" in r[3]]
        target = None
        if cast:
            tm = re.search(r"targeting (.+?)\.?$", cast[0][3])
            target = tm.group(1) if tm else None
        out.append(_fx(src, "suspend", [rows[k]] + follow,
                       prestate={"own_turn": active == p, "turn": turn},
                       action={"suspend": "Rift Bolt", "observed_follow_up": [r[3] for r in follow],
                               "free_cast_target_kind": None if target is None else
                               ("player" if not target.startswith("[") else "creature")},
                       unobservable=["mana used to pay {R}"]))
    return out


def _cast_before(rows, k, player):
    """The most recent spell cast by `player` before row k in the same turn."""
    for r in reversed(rows[:k]):
        if r[1] != rows[k][1]:
            return None
        m = re.match(rf"^{re.escape(player)} casts \[(.+?)\]", r[3])
        if m:
            return r, m.group(1)
    return None


def _prowess(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) puts (?:a )?triggered ability from \[Monastery Swiftspear\] onto the stack \(Prowess", t)
        if not m:
            continue
        p = m.group(1)
        c = _cast_before(rows, k, p)
        if c is None:
            continue
        r, spell = c
        out.append(_fx(src, "prowess", [r, rows[k]], prestate={"caster_controls_swiftspear": True},
                       action={"cast": spell, "spell_is_creature": is_creature(spell),
                               "spell_supported": supported(spell)},
                       expected={"prowess_triggers_at_least": 1},
                       unobservable=["exact number of Swiftspears on the battlefield (deaths are not logged)"]))
    # negative: a creature spell cast by a player whose Swiftspear triggered earlier that turn
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) casts \[(.+?)\]", t)
        if not m or not is_creature(m.group(2)):
            continue
        p, spell = m.group(1), m.group(2)
        earlier = [r for r in rows[:k] if r[1] == turn and re.match(
            rf"^{re.escape(p)} puts (?:a )?triggered ability from \[Monastery Swiftspear\]", r[3])]
        if not earlier:
            continue
        nxt = [r for r in rows[k + 1:k + 3] if r[1] == turn]
        triggered = any(re.match(rf"^{re.escape(p)} puts (?:a )?triggered ability from \[Monastery Swiftspear\]", r[3])
                        for r in nxt)
        out.append(_fx(src, "prowess_creature_spell", [earlier[-1], rows[k]] + nxt,
                       prestate={"caster_controls_swiftspear": True},
                       action={"cast": spell, "spell_is_creature": True, "spell_supported": supported(spell)},
                       expected={"prowess_triggers": 1 if triggered else 0},
                       unobservable=["Swiftspear assumed still on the battlefield (it triggered earlier this turn)"]))
    return out


def _goblin_guide(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) is being attacked by (.*)$", t)
        if not m or "[Goblin Guide]" not in m.group(2):
            continue
        defender = m.group(1)
        n_guides = m.group(2).count("[Goblin Guide]")
        after = [r for r in rows[k + 1:k + 8] if r[1] == turn]
        trig = [r for r in after if re.search(r"triggered ability from \[Goblin Guide\]", r[3])]
        reveals = [r for r in after if re.match(rf"^{re.escape(defender)} reveals \[(.+?)\] with \[Goblin Guide\]'s", r[3])]
        revealed = [re.match(r"^\S+ reveals \[(.+?)\]", r[3]).group(1) for r in reveals]
        out.append(_fx(src, "goblin_guide_attack", [rows[k]] + trig + reveals,
                       prestate={"attacking_guides": n_guides, "defender_library_tops": revealed},
                       action={"attack": n_guides},
                       expected={"guide_triggers": len(trig), "reveals": len(reveals),
                                 "revealed_lands": [c for c in revealed if is_land(c)]},
                       unobservable=["defender's library beyond the revealed card"]))
    return out


def _vortex(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) puts (?:a )?triggered ability from \[Roiling Vortex\] onto the stack \((.*)$", t)
        if not m:
            continue
        upkeep = "beginning of each player's upkeep" in m.group(2)
        prev = rows[k - 1][3] if k else ""
        out.append(_fx(src, "roiling_vortex", [rows[k - 1], rows[k]] if k else [rows[k]],
                       prestate={"vortex_controller": m.group(1), "active": active},
                       action={"kind": "upkeep" if upkeep else "free_cast"},
                       expected={"at_turn_start": bool(TURN.match(prev)) or "triggered ability from [Roiling Vortex]" in prev},
                       unobservable=["damage dealt (life totals are not logged)"]))
    return out


def _controller_of(rows, k, card):
    """Who put `card` (a permanent) onto the battlefield most recently before row k."""
    for r in reversed(rows[:k]):
        m = re.match(rf"^(\S+) (?:casts|plays) \[{re.escape(card)}\]", r[3])
        if m:
            return m.group(1)
        m = re.match(rf"^(\S+)'s \[.+?\] creates (?:a |an )?\[?{re.escape(card)}", r[3])
        if m:
            return m.group(1)
    return None


def _searing_blaze(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) casts \[Searing Blaze\] targeting (\S+), and \[(.+?)\]", t)
        if not m:
            continue
        caster, player_t, creature = m.groups()
        ctrl = _controller_of(rows, k, creature)
        landfall = any(r[1] == turn and r[2] == caster and re.match(
            rf"^{re.escape(caster)} (plays \[|activates an ability of \[(Arid Mesa|Bloodstained Mire|Marsh Flats|"
            rf"Wooded Foothills|Scalding Tarn|Windswept Heath|Flooded Strand|Polluted Delta|Prismatic Vista|Fabled Passage)\])",
            r[3]) for r in rows[:k])
        out.append(_fx(src, "searing_blaze", [rows[k]],
                       prestate={"caster": caster, "player_target": player_t, "creature": creature,
                                 "creature_controller": ctrl, "creature_supported": supported(creature)},
                       action={"targets": [player_t, creature]},
                       expected={"relationship_ok": ctrl == player_t if ctrl else None,
                                 "landfall_damage": 3 if landfall else 1},
                       unobservable=["damage dealt"] + ([] if ctrl else ["creature controller not determinable"])))
    return out


def _spectacle(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) casts \[Skewer the Critics\](.*)$", t)
        if not m:
            continue
        caster = m.group(1)
        spect = "spectacle cost" in m.group(2)
        opp_evidence = []
        for r in rows[:k]:
            if r[1] != turn:
                continue
            x = r[3]
            if re.match(rf"^{re.escape(caster)} casts \[(Lava Spike|Lightning Bolt|Rift Bolt|Lightning Helix|Boros Charm|"
                        rf"Skullcrack|Searing Blaze|Skewer the Critics)\].*targeting (?!{re.escape(caster)}\b)\S+", x) \
                    and not re.search(r"targeting \[", x):
                opp_evidence.append(r)
        out.append(_fx(src, "spectacle", [*opp_evidence, rows[k]],
                       prestate={"caster": caster, "opponent_life_loss_evidence": len(opp_evidence)},
                       action={"cost": "spectacle" if spect else "normal"},
                       unobservable=["whether the earlier damage resolved / was prevented; combat damage"]))
    return out


def _boros_charm(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) casts \[Boros Charm\](?: targeting (.+?))?\.?$", t)
        if not m:
            continue
        mode_row = next((r for r in rows[k + 1:k + 3] if re.match(r"^(Chosen )?[Mm]ode: ", r[3]) or " mode: " in r[3]), None)
        mode_txt = mode_row[3] if mode_row else ""
        mode = 0 if "4 damage" in mode_txt else 1 if "indestructible" in mode_txt else 2 if "double strike" in mode_txt else None
        target = m.group(2)
        out.append(_fx(src, "boros_charm", [rows[k]] + ([mode_row] if mode_row else []),
                       prestate={"caster": m.group(1)},
                       action={"mode": mode, "target": target,
                               "target_kind": None if target is None else ("creature" if target.startswith("[") else "player")},
                       unobservable=[] if mode is not None else ["mode line not logged"]))
    return out


def _player_target_spells(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) casts \[(Skullcrack|Lava Spike|Lightning Helix|Lightning Bolt)\](?: targeting (.+?))?\.?$", t)
        if not m:
            continue
        card, target = m.group(2), m.group(3)
        if target is None:
            continue
        out.append(_fx(src, "target_" + card.lower().replace(" ", "_"), [rows[k]],
                       prestate={"caster": m.group(1)},
                       action={"target_kind": "creature" if target.startswith("[") else "player", "target": target}))
    return out


def _fetches(src, rows):
    out = []
    for k, (i, turn, active, t) in enumerate(rows):
        m = re.match(r"^(\S+) activates an ability of \[(Arid Mesa|Bloodstained Mire)\] \(\s*(.*?)\)?\.?$", t)
        if not m:
            continue
        out.append(_fx(src, "fetch", [rows[k]], prestate={"player": m.group(1)},
                       action={"card": m.group(2), "text": m.group(3)},
                       unobservable=["the card found (MTGO does not log it)", "1 life paid (not logged)"]))
    return out


def _play_draw(src, g, prev_end, prev_chooser, players):
    who, how = prev_end if prev_end else (None, None)
    loser = None
    if how == "wins the game" and len(players) == 2:
        loser = next(p for p in players if p != who)
    elif how in ("has conceded from the game", "loses the game"):
        loser = who
    row = (g["start"], 0, None, f"{g['chooser']} chooses to {g['choice']} first.")
    return _fx(src, "play_draw_choice", [row],
               prestate={"previous_game_end": list(prev_end) if prev_end else None, "previous_loser": loser,
                         "previous_chooser": prev_chooser},
               action={"chooser": g["chooser"], "choice": g["choice"]},
               expected={"chooser": loser},
               unobservable=[] if loser else ["previous game result not determinable"])


def extract_all(log_dir=DEFAULT_LOG_DIR) -> list:
    paths = sorted(glob.glob(os.path.join(log_dir, "*", "Match_GameLog_*.dat")))
    seen, out = set(), []
    for p in paths:                                   # the same match may appear in two snapshot folders
        mid = os.path.basename(p)
        if mid in seen:
            continue
        seen.add(mid)
        out += extract(p)
    return out
