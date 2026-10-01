"""Milestone four, step 1 (survey only -- no engine code): rank asymmetric same-format pairings by
what engine v2 would need to play them.

Each non-basic main-deck card is classified from its oracle text (public Scryfall data) into:
  supported        -- already in engine.v2.cards.SUPPORTED;
  definition       -- playable with EXISTING v2 machinery, needs only a card definition (basic lands,
                      shock / fast / fetch / pain lands of the supported shapes, vanilla creatures with
                      supported keywords, plain damage / draw / pump / counter spells);
  primitive        -- needs a small new effect primitive inside existing subsystems (destroy, exile,
                      bounce, a new combat keyword, life loss, tap / untap, scry, ...);
  subsystem        -- needs a genuinely new subsystem (graveyard casting, discard, tokens, planeswalkers,
                      layers / static continuous effects, copy, transform / MDFC, +1/+1 counters, X costs,
                      equipment / auras, flash, other alternative costs, energy, ...).
Score (lower = cheaper): 25 per distinct new subsystem + 6 per distinct new primitive + 1 per new card
definition, with an extra penalty for the explicitly disfavoured subsystems (graveyard casting, discard,
tokens, planeswalkers, layers, copy, transform). Heuristic -- the top candidates are then read by hand.

  python scripts/v2_matchup_survey.py   -> data/v2_matchup_survey.json (+ printed top pairs)
"""
from __future__ import annotations

import collections
import glob
import itertools
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "data", "v2_matchup_survey.json")
SUPPORTED_KW = {"Flying", "Haste", "First strike", "Vigilance", "Prowess", "Landfall", "Suspend", "Spectacle"}
SMALL_KW = {"Trample", "Reach", "Menace", "Deathtouch", "Lifelink", "Defender", "Double strike", "Indestructible",
            "Hexproof"}
DISFAVOURED = {"graveyard_casting", "discard", "tokens", "planeswalkers", "layers", "copy", "transform_mdfc"}

SUBSYSTEM_RX = [
    ("planeswalkers", r"planeswalker|loyalty"),
    ("transform_mdfc", None),                      # from layout
    ("copy", r"\bcopy\b"),
    ("tokens", r"\bcreate\b|\btoken\b"),
    ("graveyard_casting", r"from (your|a|their) graveyard|flashback|escape|unearth|delve|retrace|disturb|jump-start|"
                          r"return .* from .*graveyard"),
    ("discard", r"\bdiscard"),
    ("plus_counters", r"\+1/\+1 counter|-1/-1 counter|counters? on"),
    ("layers", r"(creatures|permanents|lands) you control (get|have|are)|becomes? (a|an) |gain control|"
               r"\bget \+\d+/\+\d+ (for each|as long)|loses all abilities|base power"),
    ("x_costs", r"\{x\}"),
    ("equipment_auras", r"\bequip\b|\benchant\b|equipped|enchanted"),
    ("flash", r"\bflash\b"),
    ("alt_costs", r"evoke|convoke|kicker|affinity|emerge|plot|warp|offspring|bargain|cycling|channel|mutate|ninjutsu|"
                  r"dash|foretell|madness|overload|without paying"),
    ("energy", r"\{e\}|energy"),
    ("hidden_zone_peek", r"look at the top|reveal (the top|your hand|their hand)|surveil|scry|explore|mill"),
    ("sacrifice_effects", r"sacrifice (a|another|an)"),
    ("library_search_other", r"search your library for (a|an|up to)(?! (basic )?(mountain|plains|island|swamp|forest)\b)"),
    ("replacement_other", r"\binstead\b|prevent|as .* enters, choose|enters with"),
    ("cost_changes", r"costs? \{\d\} (less|more)|cost \{\d\} more"),
    ("hand_or_library_manipulation", r"put .* (on top|on the bottom) of|shuffle .* into"),
    ("triggers_other", r"\bwhen(ever)?\b|\bat the beginning\b"),
    ("activated_other", r"^[^:\"]*\{t\}[^:\"]*:(?! add)|^[^:\"]*\{\d?[wubrgc]?\}[^:\"]*:(?! add)"),
]
PRIMITIVE_RX = [
    ("destroy", r"\bdestroy target"),
    ("exile_removal", r"\bexile target"),
    ("bounce", r"return target .* to (its|their) owner'?s? hand"),
    ("life_loss", r"loses? \d+ life|lose life"),
    ("tap_untap", r"\b(tap|untap) target|doesn't untap"),
    ("cant_block_attack", r"can't (block|attack|be blocked)"),
    ("minus_pt", r"gets? -\d+/-\d+"),
    ("fight", r"\bfights?\b"),
]


def _db():
    from engine.card_db import CardDB
    return CardDB()


def classify(db, name):
    from engine.v2.cards import BASIC_LAND_COLOR, SUPPORTED
    if name in SUPPORTED:
        return "supported", ()
    d = db.get(name)
    if d is None:
        return "unknown", ("unknown_card",)
    tl = d.get("type_line", "")
    if name in BASIC_LAND_COLOR:
        return "definition", ("basic_land",)
    layout = d.get("layout")
    text = (d.get("oracle_text") or " // ".join(f.get("oracle_text", "") for f in d.get("card_faces") or [])).lower()
    body = re.sub(r"\([^)]*\)", "", text)
    kws = set(d.get("keywords") or ())
    if layout not in ("normal",):
        return "subsystem", ("transform_mdfc" if layout in ("transform", "modal_dfc") else f"layout_{layout}",)
    if "Planeswalker" in tl or "Battle" in tl or "Saga" in tl:
        return "subsystem", ("planeswalkers" if "Planeswalker" in tl else f"type_{tl.split()[-1].lower()}",)
    if tl.startswith("Land") or " Land" in tl.split("—")[0]:
        sub = tl.split("—")[1].split() if "—" in tl else []
        basics = [s for s in sub if s in BASIC_LAND_COLOR]
        lines = [l.strip() for l in body.split("\n") if l.strip()]
        shapes = []
        for l in lines:
            if re.fullmatch(r"as this land enters, you may pay 2 life\. if you don't, it enters tapped\.", l):
                shapes.append("shock")
            elif re.fullmatch(r"this land enters tapped unless you control two or fewer other lands\.", l):
                shapes.append("fast")
            elif re.fullmatch(r"\{t\}, pay 1 life, sacrifice this land: search your library for an? \w+ or \w+ card, "
                              r"put it onto the battlefield, then shuffle\.", l):
                shapes.append("fetch")
            elif re.fullmatch(r"\{t\}(, pay 1 life)?: add \{[wubrgc]\}( or \{[wubrgc]\})?\.", l):
                shapes.append("mana")
            elif re.fullmatch(r"\{1\}, \{t\}, sacrifice this land: draw a card\.", l):
                shapes.append("cycle_draw")
            elif l == "":
                continue
            else:
                shapes.append("other:" + l[:60])
        if all(not s.startswith("other:") for s in shapes):
            return "definition", tuple(sorted(set(shapes)) or ("basic_types",))
        return "subsystem", ("land_other",)
    tags_sub = []
    if not kws <= SUPPORTED_KW | SMALL_KW:
        tags_sub.append("keyword:" + "/".join(sorted(kws - SUPPORTED_KW - SMALL_KW)))
    for tag, rx in SUBSYSTEM_RX:
        if rx and re.search(rx, body, re.M):
            tags_sub.append(tag)
    if "Creature" in tl:
        # a creature whose text is only supported keywords is a pure definition
        rest = body
        for kw in kws:
            rest = re.sub(re.escape(kw.lower()), "", rest)
        if not re.sub(r"[\s,.]", "", rest) and kws <= SUPPORTED_KW:
            return "definition", ("vanilla_creature",)
    simple_spell = re.fullmatch(
        r"[^\n]*? deals \d+ damage to (any target|target creature|target player( or planeswalker)?)\.|"
        r"draw (a card|two cards|three cards)\.|target creature gets \+\d+/\+\d+ until end of turn\.|"
        r"counter target spell\.", body.strip())
    if simple_spell and not tags_sub and ("Instant" in tl or "Sorcery" in tl):
        return "definition", ("simple_spell",)
    if tags_sub:
        return "subsystem", tuple(t for t in tags_sub if t not in ("triggers_other", "activated_other")) or \
            tuple(tags_sub)
    tags_prim = [t for t, rx in PRIMITIVE_RX if re.search(rx, body)]
    tags_prim += ["keyword:" + k for k in sorted(kws & SMALL_KW)]
    if tags_prim:
        return "primitive", tuple(tags_prim)
    return "subsystem", ("unclassified",)


def deck_cards(path):
    from data.deck import _parse_decklist
    main, _side = _parse_decklist(open(path, encoding="utf-8").read())
    return main


def main():
    db = _db()
    decks = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "decks", "*.txt")) + glob.glob(os.path.join(ROOT, "decks", "auto", "*.txt"))):
        stem = os.path.relpath(f, os.path.join(ROOT, "decks"))[:-4].replace("\\", "/")
        fmt = stem.rsplit("_", 1)[-1]
        if fmt not in ("modern", "standard", "pioneer"):
            continue
        try:
            main_ = deck_cards(f)
        except Exception:                                            # noqa: BLE001 -- unparseable lists are skipped
            continue
        if sum(q for q, _ in main_) < 60:
            continue
        names = sorted({n for _, n in main_})
        cls = {n: classify(db, n) for n in names}
        if any(b == "unknown" for b, _ in cls.values()):
            continue
        decks[stem] = {"format": fmt, "cards": cls}

    def cost(cards):
        defs = sorted(n for n, (b, _t) in cards.items() if b == "definition")
        prims = sorted({t for b, ts in cards.values() if b == "primitive" for t in ts})
        subs = sorted({t for b, ts in cards.values() if b == "subsystem" for t in ts})
        sub_cards = sorted(n for n, (b, _t) in cards.items() if b == "subsystem")
        score = 25 * len(subs) + 6 * len(prims) + len(defs) + 15 * len(set(subs) & DISFAVOURED)
        return {"score": score, "new_definitions": defs, "new_primitives": prims, "new_subsystems": subs,
                "subsystem_cards": sub_cards,
                "primitive_cards": sorted(n for n, (b, _t) in cards.items() if b == "primitive")}

    rows = []
    for a, b in itertools.combinations(sorted(decks), 2):
        if decks[a]["format"] != decks[b]["format"]:
            continue
        cards = {**decks[a]["cards"], **decks[b]["cards"]}
        c = cost(cards)
        rows.append({"a": a, "b": b, "format": decks[a]["format"], **c})
    rows.sort(key=lambda r: (r["score"], len(r["subsystem_cards"])))
    per_deck = sorted(({"deck": d, "format": v["format"], **cost(v["cards"])} for d, v in decks.items()),
                      key=lambda r: r["score"])
    out = {"decks_surveyed": len(decks), "pairs": len(rows), "top_pairs": rows[:40], "per_deck": per_deck[:40],
           "card_classes": {d: {n: [b, list(t)] for n, (b, t) in v["cards"].items()} for d, v in decks.items()}}
    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
    print(f"decks {len(decks)}  pairs {len(rows)}")
    for r in rows[:15]:
        print(f"{r['score']:4d}  {r['a']}  vs  {r['b']}  defs={len(r['new_definitions'])} "
              f"prims={r['new_primitives']} subs={r['new_subsystems']}")
    print("cheapest single decks:")
    for r in per_deck[:10]:
        print(f"{r['score']:4d}  {r['deck']}  defs={len(r['new_definitions'])} prims={r['new_primitives']} "
              f"subs={r['new_subsystems']}")


if __name__ == "__main__":
    main()
