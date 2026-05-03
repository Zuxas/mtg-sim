"""
Build auto-handlers for ALL Standard-legal card sets.
Reads local scryfall_oracle_cards.json (freshly fetched).
Outputs engine/standard_auto_handlers.py.
"""
import sys, json, re
from pathlib import Path
from collections import defaultdict

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
OUT = REPO / "engine" / "standard_auto_handlers.py"

STANDARD_SETS = {
    "woe": "Wilds of Eldraine",
    "lci": "Lost Caverns of Ixalan",
    "mkm": "Murders at Karlov Manor",
    "otj": "Outlaws of Thunder Junction",
    "big": "The Big Score",
    "blb": "Bloomburrow",
    "dsk": "Duskmourn: House of Horror",
    "fdn": "Foundations",
    "dft": "Aetherdrift",
    "tdm": "Tarkir: Dragonstorm",
    "fin": "Final Fantasy",
    "eoe": "Edge of Eternities",
    "spm": "Marvel's Spider-Man",
    "tla": "Avatar: The Last Airbender",
    "ecl": "Lorwyn Eclipsed",
    "tmt": "Teenage Mutant Ninja Turtles",
    "sos": "Secrets of Strixhaven",
}

# ── Load oracle DB ────────────────────────────────────────────────────────────
raw = json.loads((REPO / "data/rules_reference/scryfall_oracle_cards.json")
                 .read_text(encoding="utf-8"))
cards_list = raw if isinstance(raw, list) else raw.get("data", [])

# Index by name AND by set — include DFC face names
BY_NAME = {}
SET_CARDS = defaultdict(list)  # set_code -> [card_dict]

for c in cards_list:
    set_code = c.get("set", "")
    name = c.get("name", "")
    BY_NAME[name] = c
    # DFC: also index each face
    for face in c.get("card_faces", []):
        fn = face.get("name", "")
        if fn and fn not in BY_NAME:
            BY_NAME[fn] = {**c, **face}
    if set_code in STANDARD_SETS:
        SET_CARDS[set_code].append(c)

print(f"Oracle DB: {len(BY_NAME)} unique names")
print(f"Standard-legal oracle cards by set:")
total_std = 0
for code, name in STANDARD_SETS.items():
    n = len(SET_CARDS[code])
    total_std += n
    print(f"  {code:4} {name:<40} {n:>4}")
print(f"  {'':4} {'TOTAL':<40} {total_std:>4}")

# ── Load ONLY hand-verified registry (not auto-generated files) ────────────────
# We DON'T import auto-handlers here because we're regenerating them.
# ALREADY only tracks cards with hand-written oracle-verified handlers — those
# don't need auto-generation. Auto-handlers use setdefault so no conflict.
from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
from engine.card_effects import LANDFALL_GROW, LANDFALL_MILL, LANDFALL_DOUBLE, LANDFALL_QUEST
from engine.sagas import SAGA_EFFECTS
from engine.game_state import GameState
from engine.oracle_parser import parse_oracle

# Only skip cards that have hand-written verified handlers or engine handling.
# Do NOT skip cards that are only in auto-generated files — those we regenerate.
import engine.card_handlers_verified  # noqa — loads verified into ETB/SPELL_EFFECTS
from engine.card_effects import ETB_EFFECTS as _ETB_AFTER_VERIFIED
from engine.card_effects import SPELL_EFFECTS as _SPELL_AFTER_VERIFIED

ALREADY = (
    set(_ETB_AFTER_VERIFIED) | set(_SPELL_AFTER_VERIFIED) | set(SAGA_EFFECTS)
    | LANDFALL_GROW | LANDFALL_MILL | LANDFALL_DOUBLE | LANDFALL_QUEST
    | {n.lower() for n in GameState.FAST_LANDS}
    | {n.lower() for n in GameState.TAPLANDS}
    | {n.lower() for n in GameState.SHOCK_LANDS}
)
# Remove anything only added by sos_auto_handlers (not hand-verified)
# The simplest approach: after importing verified, also import sos to get its
# additions into ALREADY so we don't duplicate them in standard.
# Actually: just always generate everything the parser can handle.
# setdefault at runtime means duplicates are harmless.
ALREADY = set()  # regenerate ALL auto-parseable cards unconditionally

# Still skip cards with HAND-WRITTEN handlers (they take precedence anyway,
# but no need to generate auto versions for them).
import ast as _ast
from pathlib import Path as _Path
_verified_src = (_Path(__file__).resolve().parent.parent / "engine" / "card_handlers_verified.py").read_text(encoding="utf-8")
_HAND_WRITTEN = set()
try:
    _tree = _ast.parse(_verified_src)
    for node in _ast.walk(_tree):
        if isinstance(node, _ast.Dict):
            for k in node.keys:
                if isinstance(k, _ast.Constant) and isinstance(k.value, str):
                    _HAND_WRITTEN.add(k.value)
except Exception:
    pass
# Also add landfall sets and engine-handled lands
ALREADY = (
    _HAND_WRITTEN
    | set(SAGA_EFFECTS)
    | LANDFALL_GROW | LANDFALL_MILL | LANDFALL_DOUBLE | LANDFALL_QUEST
    | {n.lower() for n in GameState.FAST_LANDS}
    | {n.lower() for n in GameState.TAPLANDS}
    | {n.lower() for n in GameState.SHOCK_LANDS}
)
print(f"Hand-written/engine cards (skip auto-gen): {len(ALREADY)}")

BASIC_LANDS = {"Plains","Island","Swamp","Mountain","Forest",
               "Snow-Covered Plains","Snow-Covered Island","Snow-Covered Swamp",
               "Snow-Covered Mountain","Snow-Covered Forest"}
SKIP_TYPES = {"Basic Land"}

def ascii_safe(s):
    return s.replace("\n"," | ").encode("ascii", errors="replace").decode("ascii")

# Regex that matches a trigger word in oracle text.
# Cards with NO trigger word are pure static abilities — no handler needed.
HAS_TRIGGER = re.compile(r'\bwhen(?:ever)?\b|\bat the beginning\b|\bat end\b', re.I)

def keyword_only(oracle):
    """True if oracle text contains only keywords, static abilities, and reminder text."""
    # Quick win: if there's no trigger word at all, this card has no ETB/spell effect.
    if not HAS_TRIGGER.search(oracle):
        return True
    # Otherwise strip known keywords + reminder text and check if anything's left.
    stripped = re.sub(
        r'\b(flying|haste|vigilance|trample|menace|deathtouch|lifelink|'
        r'first strike|double strike|flash|ward|hexproof|indestructible|'
        r'reach|protection|changeling|convoke|prowess|cascade|cycling|'
        r'kicker|undying|persist|riot|adapt|boast|foretell|learn|'
        r'magecraft|ward \d+|skulk|annihilator \d+|devoid|phasing|'
        r'defender|banding|shroud|regenerate|fear|landwalk|rampage|'
        r'equip \{[^}]+\}|equip \d+|crew \d+|saddle \d+|disguise \{[^}]+\}|'
        r'plot \{[^}]+\}|bargain|ninjutsu \{[^}]+\}|evoke \{[^}]+\}|'
        r'affinity for \w+|fading \d+|vanishing \d+|plainscycling \{[^}]+\}|'
        r'cycling \{[^}]+\}|cycling \d+|landcycling \{[^}]+\}|'
        r'convoke|renown \d+|bolster \d+|riot|adapt \d+|'
        r'exploit|myriad|rampage \d+|wither|persist|undying|'
        r'this spell costs \{[^}]+\} (?:less|more)|'
        r'as an additional cost to cast this spell,[^.]+\.|'
        r'enchant (?:creature|permanent|land|artifact|player|enchantment)|'
        r'this creature can\'?t (?:block|attack)|'
        r'this creature attacks (?:each|every) (?:turn|combat)|'
        r'this (?:creature|permanent) doesn\'?t untap|'
        r'enchanted creature doesn\'?t untap|'
        r'enchanted creature (?:attacks?|blocks?) (?:each|every) (?:turn|combat)|'
        r'target creature\'?s? owner puts it on top|'
        r'this spell costs \{[^}]+\} (?:less|more) to cast|'
        r'spree \(|bargain \(|limit \(|impending|'
        r'gain control of target creature until end of turn|'
        r'job select\b|'                          # FIN Final Fantasy class selection
        r'max speed\s*[—\-]|'                     # DFT Aetherdrift racing
        r'islandcycling \{[^}]+\}|'               # cycling variant keywords
        r'swampcycling \{[^}]+\}|mountaincycling \{[^}]+\}|'
        r'forestcycling \{[^}]+\}|plainscycling \{[^}]+\}|'
        r'instant and sorcery spells you cast|'   # cost-reduction static
        r'tap enchanted creature|'                 # aura tap-lock
        r'a deck can have any number|'              # rule override text
        r'toxic \d+|'                              # Phyrexian toxic keyword
        r'oil counter|'                            # Phyrexian oil counter mechanic
        r'poison counter|'                         # poison counter reminder
        r'proliferate\b|'                          # keyword in paragraph form
        r'protection from (?:everything|all|each)|'
        r'this creature can\'?t (?:be blocked|block)|'
        r'spells you cast cost \{[^}]+\} (?:less|more)|'
        r'you may cast (?:this card|~) from your graveyard|'
        r'this permanent (?:enters|is) the battlefield (?:tapped|with)|'
        r'if you control (?:no|a|an|two or more)|'
        r'living weapon|'
        r'partner(?: with \w+)?|'
        r'commander ninjutsu|'
        r'offering|'
        r'dredge \d+|'
        r'morph \{|'
        r'megamorph \{|'
        r'bestow \{)'
        r'|\([^)]+\)'  # strip all reminder text in parentheses
        r'|^[A-Z][a-z]+ \d+$',
        '', oracle, flags=re.IGNORECASE | re.MULTILINE
    ).strip(' \n|—•(),./0123456789{} ')
    return not stripped

# ── Process all cards ─────────────────────────────────────────────────────────
auto_etb   = []   # (name, effects, snip, set_code)
auto_spell = []
no_effect  = []
hand_write = []   # (name, type_line, oracle, set_code)
already    = []
skipped    = []

seen = set()

for set_code in STANDARD_SETS:
    for c in SET_CARDS[set_code]:
        name = c.get("name","")
        if not name or name in seen:
            continue
        seen.add(name)

        type_line = c.get("type_line","")
        oracle = (c.get("oracle_text") or "").strip()

        # Skip basics and token-only cards
        if name in BASIC_LANDS or "Basic Land" in type_line:
            skipped.append(name); continue
        if "Token" in type_line and "Creature" in type_line and not oracle:
            skipped.append(name); continue

        # Already handled
        if name in ALREADY or name.lower() in ALREADY:
            already.append((name, set_code)); continue

        # Lands (engine handles mana production)
        if "Land" in type_line and "Creature" not in type_line:
            skipped.append(name); continue

        is_spell_type = any(t in type_line for t in ("Instant", "Sorcery"))

        # No oracle / keyword only.
        # Instants and sorceries always have an effect (they resolve as spells),
        # so only apply keyword_only filtering to permanents.
        if not oracle:
            no_effect.append(name); continue
        if not is_spell_type and keyword_only(oracle):
            no_effect.append(name); continue

        # Oracle parser
        try:
            parsed = parse_oracle(oracle)
        except Exception:
            parsed = {}

        etb_efx   = parsed.get("etb", [])
        spell_efx = parsed.get("spell", [])

        is_creature = "Creature" in type_line
        is_spell    = any(t in type_line for t in ("Instant","Sorcery"))
        is_enchant  = "Enchantment" in type_line and "Creature" not in type_line
        is_artifact = "Artifact" in type_line and "Creature" not in type_line

        if etb_efx and (is_creature or is_enchant or is_artifact):
            auto_etb.append((name, etb_efx, oracle[:80], set_code))
        elif spell_efx and is_spell:
            auto_spell.append((name, spell_efx, oracle[:80], set_code))
        else:
            hand_write.append((name, type_line[:35], oracle[:90], set_code))

# ── Write output file ─────────────────────────────────────────────────────────
lines = ['''\
"""engine/standard_auto_handlers.py -- Auto-generated Standard card handlers.
Generated: 2026-05-03. Source: Scryfall oracle bulk (all Standard-legal sets).
Hand-written entries in card_handlers_verified.py take precedence (setdefault).
"""
from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
from engine.effect_primitives import run_effects as _re

def _etb(fx):
    def h(gs, card):
        _re(gs, {"source_card":card,"trigger_event":"etb","chosen_target":None}, fx)
    return h

def _spell(fx):
    def h(gs, card):
        _re(gs, {"source_card":card,"trigger_event":"spell","chosen_target":None}, fx)
    return h

''']

etb_names, spell_names = [], []
for name, efx, snip, sc in auto_etb:
    safe = re.sub(r"[^a-z0-9]","_",name.lower())
    lines.append(f"# [{sc}] {ascii_safe(snip)}")
    lines.append(f'_h_{safe} = _etb({json.dumps(efx)})')
    etb_names.append(name)

lines.append("")
for name, efx, snip, sc in auto_spell:
    safe = re.sub(r"[^a-z0-9]","_",name.lower())
    lines.append(f"# [{sc}] {ascii_safe(snip)}")
    lines.append(f'_h_{safe} = _spell({json.dumps(efx)})')
    spell_names.append(name)

lines.append("\nfor _n,_f in {")
for name in etb_names:
    safe = re.sub(r"[^a-z0-9]","_",name.lower())
    lines.append(f'    {json.dumps(name)}: _h_{safe},')
lines.append("}.items(): ETB_EFFECTS.setdefault(_n,_f)")

lines.append("\nfor _n,_f in {")
for name in spell_names:
    safe = re.sub(r"[^a-z0-9]","_",name.lower())
    lines.append(f'    {json.dumps(name)}: _h_{safe},')
lines.append("}.items(): SPELL_EFFECTS.setdefault(_n,_f)")

OUT.write_text("\n".join(lines), encoding="utf-8")

# ── Summary ───────────────────────────────────────────────────────────────────
total = len(auto_etb) + len(auto_spell) + len(no_effect) + len(already) + len(hand_write)
covered = len(auto_etb) + len(auto_spell) + len(no_effect) + len(already)
pct = 100*covered/total if total else 0

print(f"\n{'='*65}")
print(f"Standard Handler Coverage ({total} unique non-basic/land cards)")
print(f"{'='*65}")
print(f"  Already registered           : {len(already)}")
print(f"  Auto-generated ETB           : {len(auto_etb)}")
print(f"  Auto-generated SPELL         : {len(auto_spell)}")
print(f"  Keyword/no-effect (skip)     : {len(no_effect)}")
print(f"  Lands / tokens (skip)        : {len(skipped)}")
print(f"  Need hand-writing            : {len(hand_write)}")
print(f"  Coverage                     : {covered}/{total} = {pct:.1f}%")

print(f"\n-- By set (hand-write needed) --")
by_set = defaultdict(int)
for _,_,_,sc in hand_write: by_set[sc] += 1
for code, name in STANDARD_SETS.items():
    print(f"  {code:4} {name:<40} {by_set[code]:>4} need hand-write")

print(f"\nWrote: {OUT}")
