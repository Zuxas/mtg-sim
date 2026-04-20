"""Check which Modern field APLs exist and their status."""
import os

modern_field = {
    'Boros Energy': 22.1, 'Amulet Titan': 8.5, 'Eldrazi Ramp': 7.4,
    'Izzet Prowess': 7.2, 'Izzet Affinity': 6.8, 'Grinding Breach': 6.4,
    'Jeskai Blink': 6.4, 'Orzhov Blink': 6.1, "Goryo's Vengeance": 5.6,
    'Domain Zoo': 5.0, 'Eldrazi Tron': 4.3, 'Mono Red Aggro': 4.1,
    'Temur Breach': 3.8, 'Dimir Murktide': 3.5, 'Esper Blink': 2.8,
}

apl_files = [f for f in os.listdir('apl') if f.endswith('.py') and f != '__init__.py']

print(f"{'%':>5}  {'Deck':<22} {'APL File':<26} {'Lines':>5}  Status")
print("-" * 80)

for name, pct in sorted(modern_field.items(), key=lambda x: -x[1]):
    slug = name.lower().replace("'", "").replace(" ", "_")
    # Find matching file
    found = None
    for f in apl_files:
        fname = f.replace('.py', '')
        # Check various matching strategies
        if fname == slug or slug.startswith(fname) or fname.startswith(slug[:8]):
            found = f
            break
    # Try word-by-word
    if not found:
        words = name.lower().replace("'", "").split()
        for f in apl_files:
            if all(w in f for w in words[:2]):
                found = f
                break
    # Try first word only
    if not found:
        first = name.lower().split()[0]
        for f in apl_files:
            if first in f and f != 'generic_apl.py':
                found = f
                break

    if found:
        path = os.path.join('apl', found)
        with open(path, encoding='utf-8') as fh:
            content = fh.read()
        lines = len(content.splitlines())
        has_main = 'def main_phase' in content
        has_keep = 'def keep' in content
        if has_main and has_keep and lines > 50:
            status = "REAL"
        elif has_main or has_keep:
            status = "PARTIAL"
        else:
            status = "STUB"
        print(f"{pct:>5.1f}  {name:<22} {found:<26} {lines:>5}  {status}")
    else:
        print(f"{pct:>5.1f}  {name:<22} {'--- MISSING ---':<26}         NEED")
