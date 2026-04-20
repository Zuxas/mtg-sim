"""Pull top decklists for all Modern meta archetypes and test APLs."""
import sqlite3, json, os, sys, importlib, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB = os.path.join(os.path.dirname(__file__), "..", "mtg-meta-analyzer", "data", "mtg_meta.db")
conn = sqlite3.connect(DB)
c = conn.cursor()

from format_config import FORMATS
from data.deck import load_deck_from_text
from apl.base_apl import BaseAPL

MODERN_FIELD = FORMATS["modern"]["field"]

# Map archetype names to APL classes
APL_MAP = {
    "Boros Energy": ("apl.boros_energy", "BorosEnergyAPL"),
    "Izzet Prowess": ("apl.izzet_prowess", "IzzetProwessAPL"),
    "Izzet Affinity": ("apl.generic_apl", "GenericAPL"),
    "Amulet Titan": ("apl.amulet_titan", "AmuletTitanAPL"),
    "Eldrazi Ramp": ("apl.generic_apl", "GenericAPL"),
    "Grinding Breach": ("apl.generic_apl", "GenericAPL"),
    "Jeskai Blink": ("apl.generic_apl", "GenericAPL"),
    "Orzhov Blink": ("apl.generic_apl", "GenericAPL"),
    "Goryo's Vengeance": ("apl.goryo_vengeance", "GoryoVengeanceAPL"),
    "Domain Zoo": ("apl.domain_zoo", "DomainZooAPL"),
    "Eldrazi Tron": ("apl.eldrazi_tron", "EldraziTronAPL"),
    "Mono Red Aggro": ("apl.mono_red_aggro", "MonoRedAggroAPL"),
    "Temur Breach": ("apl.generic_apl", "GenericAPL"),
    "Dimir Murktide": ("apl.generic_apl", "GenericAPL"),
    "Esper Blink": ("apl.esper_blink", "EsperBlinkAPL"),
}

results = []
for arch, pct in sorted(MODERN_FIELD.items(), key=lambda x: -x[1]):
    # Pull a decklist
    c.execute("""
        SELECT d.id, d.player, e.date FROM decks d JOIN events e ON d.event_id=e.id
        WHERE d.archetype LIKE ? AND e.format='modern'
        ORDER BY e.date DESC LIMIT 1
    """, (f"%{arch}%",))
    row = c.fetchone()
    
    if not row:
        results.append((arch, pct, "NO DECK", "", 0, 0))
        continue
    
    deck_id = row[0]
    c.execute("""
        SELECT c.name, dc.quantity, dc.is_sideboard
        FROM deck_cards dc JOIN cards c ON dc.card_id=c.id
        WHERE dc.deck_id=? ORDER BY dc.is_sideboard, c.name
    """, (deck_id,))
    
    cards = c.fetchall()
    lines = []
    for name, qty, is_sb in cards:
        if is_sb and not any("Sideboard" in l for l in lines):
            lines.append("Sideboard")
        lines.append(f"{qty} {name}")
    deck_text = "\n".join(lines)
    
    # Save deck file
    safe_name = arch.lower().replace(" ", "_").replace("'", "")
    deck_path = f"decks/{safe_name}_modern.txt"
    with open(deck_path, 'w', encoding='utf-8') as f:
        f.write(f"// {arch} - {row[1]} ({row[2]})\n" + deck_text)
    
    # Try to load and goldfish
    try:
        main, sb = load_deck_from_text(deck_text)
        mod_name, cls_name = APL_MAP.get(arch, ("apl.generic_apl", "GenericAPL"))
        mod = importlib.import_module(mod_name)
        apl_cls = getattr(mod, cls_name)
        apl = apl_cls()
        
        import random, copy
        random.seed(42)
        res = apl.run_game(mainboard=main, on_play=True)
        
        status = f"T{res.kill_turn}" if res.won else "FAIL"
        results.append((arch, pct, status, cls_name, len(main), len(sb)))
    except Exception as e:
        results.append((arch, pct, f"ERR: {str(e)[:40]}", "", 0, 0))

print(f"\n{'Archetype':<25} {'Meta%':>5} {'Result':>8} {'APL':<20} {'Cards':>5}")
print("-" * 75)
for arch, pct, status, apl, mc, sc in results:
    print(f"  {arch:<23} {pct:>5.1f}% {status:>8} {apl:<20} {mc:>3}+{sc}")
