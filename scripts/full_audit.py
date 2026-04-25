"""
scripts/full_audit.py -- Full coverage audit (Track A: L1 card handlers,
Track B: APL/MatchAPL coverage).

Track A: Per-format L1 audit
  For each requested format:
    parse non-land cards from decks/*_<format>.txt
    cross-ref ETB_EFFECTS / SPELL_EFFECTS / CARD_TO_FAMILY
    classify misses as VANILLA vs HAS_EFFECTS
    output data/<format>_l1_handler_audit_<DATE>.csv

Track B: APL coverage
  For each deck file:
    derive normalized key from filename
    look up in APL_REGISTRY + MATCH_APL_REGISTRY
    classify APL quality (HAND_TUNED / STUB / UNKNOWN)
    verify deck loads (mainboard 60, sideboard 0/15)
      -- honors `audit:intentional` and `audit:custom_variant` header
         markers per the 2026-04-25 deck-triage convention
    output data/apl_coverage_audit_<DATE>.csv

Combined:
  data/full_audit_<DATE>.md

Usage:
  python scripts/full_audit.py
  python scripts/full_audit.py --formats modern,standard
  python scripts/full_audit.py --date 2026-04-25
  python scripts/full_audit.py --formats pioneer --date 2026-05-01
"""
import sys, os, csv, re, glob, ast, argparse
from collections import defaultdict, Counter
from datetime import date as _date

# Repo-relative paths -- script lives at scripts/full_audit.py
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO); os.chdir(REPO)

# CLI
parser = argparse.ArgumentParser(description="Full coverage audit (L1 + APL)")
parser.add_argument("--formats", default="modern,standard,pioneer,legacy",
                    help="Comma-separated list of format suffixes to audit")
parser.add_argument("--date", default=None,
                    help="Date stamp for output filenames (default: today YYYY-MM-DD)")
args = parser.parse_args()
DATE = args.date or _date.today().strftime("%Y-%m-%d")
FORMATS = tuple(f.strip() for f in args.formats.split(",") if f.strip())

DATA = os.path.join(REPO, "data")
os.makedirs(DATA, exist_ok=True)

# Imports from mtg-sim
from engine.card_effects import ETB_EFFECTS, SPELL_EFFECTS
from engine.effect_family_registry import CARD_TO_FAMILY
from engine.card_db import CardDB
from apl import APL_REGISTRY, MATCH_APL_REGISTRY

DB = CardDB()

# ─── Shared deck parsing ────────────────────────────────────────────
DECK_LINE = re.compile(r"^\s*(?:SB:\s*)?(\d+)\s+(.+?)\s*$")

def parse_deck_lines(path):
    in_sb = False
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("//"):
                continue
            if s.lower().startswith("sideboard"):
                in_sb = True
                continue
            m = DECK_LINE.match(s)
            if m:
                yield int(m.group(1)), m.group(2).strip(), in_sb

def parse_format_from_filename(filename):
    base = os.path.basename(filename).replace(".txt", "")
    for fmt in ("modern", "standard", "pioneer", "legacy"):
        if base.endswith("_" + fmt):
            return fmt
    return "unknown"

# ─── Track A: L1 handler audit ──────────────────────────────────────
TRIGGER_RE = re.compile(
    r"\b(when|whenever|at the beginning|sacrifice this|"
    r"choose one|may search|reveal|create a|enters\b|dies\b|attacks\b|"
    r"deals damage|equipped creature|enchanted creature)\b",
    re.IGNORECASE,
)
ACTIVATED_RE = re.compile(r"\{[^}]+\}\s*[:,]")
STATIC_KW = {
    "flying", "trample", "vigilance", "lifelink", "first strike",
    "double strike", "deathtouch", "haste", "hexproof", "reach",
    "menace", "defender", "indestructible", "flash", "shadow",
    "skulk", "horsemanship", "banding", "phasing", "fear", "intimidate",
}

def is_vanilla(text):
    if not text.strip():
        return True
    tokens = re.split(r"[,\n;]| and ", text.lower())
    for tok in tokens:
        t = tok.strip().rstrip(".")
        if not t: continue
        if t in STATIC_KW: continue
        if t.startswith("protection from "): continue
        if re.match(r"ward\s+\{?\d+\}?$", t): continue
        return False
    return True

def classify_miss(name):
    card = DB.get(name)
    if not card:
        return ("UNKNOWN_CARD", "?", "(card not in oracle DB)")
    oracle = (card.get("oracle_text") or "").strip()
    type_line = (card.get("type_line") or "").lower()
    if is_vanilla(oracle):
        return ("VANILLA", "n/a", oracle.replace("\n", " | ")[:80] or "(no oracle text)")
    if "instant" in type_line or "sorcery" in type_line:
        suggest = "SPELL_EFFECTS"
    elif TRIGGER_RE.search(oracle) or "enters" in oracle.lower():
        suggest = "ETB_EFFECTS"
    elif ACTIVATED_RE.search(oracle):
        suggest = "REVIEW (activated)"
    else:
        suggest = "REVIEW"
    summary = oracle.replace("\n", " | ")
    if len(summary) > 100:
        summary = summary[:97] + "..."
    return ("HAS_EFFECTS", suggest, summary)

def run_l1_for_format(format_name):
    paths = sorted(glob.glob(os.path.join(REPO, "decks", f"*_{format_name}.txt")))
    if not paths:
        return [], {"format": format_name, "decks": 0, "unique_cards": 0,
                    "registered": 0, "vanilla": 0, "gaps": 0, "unknown": 0,
                    "family_only": 0}

    agg = defaultdict(lambda: {"decks": set(), "copies": 0})
    for path in paths:
        deck_name = os.path.basename(path).replace(f"_{format_name}.txt", "")
        for count, name, _ in parse_deck_lines(path):
            if DB.is_land(name):
                continue
            agg[name]["decks"].add(deck_name)
            agg[name]["copies"] += count

    rows, counts = [], Counter()
    for name, info in agg.items():
        decks, copies = len(info["decks"]), info["copies"]
        in_etb = name in ETB_EFFECTS
        in_spell = name in SPELL_EFFECTS
        in_family = name in CARD_TO_FAMILY
        if in_etb or in_spell:
            bucket = "REGISTERED"
            suggest = ("ETB" if in_etb else "") + ("+" if in_etb and in_spell else "") + ("SPELL" if in_spell else "")
            if in_family: suggest += "+FAMILY"
            oracle_summary = ""
        elif in_family:
            bucket = "FAMILY_ONLY"
            suggest = f"FAMILY: {CARD_TO_FAMILY[name]}"
            oracle_summary = ""
        else:
            bucket, suggest, oracle_summary = classify_miss(name)
        counts[bucket] += 1
        rows.append({"card": name, "format": format_name,
                     "decks_present_in": decks, "total_copies": copies,
                     "bucket": bucket, "suggested_registry": suggest,
                     "oracle_summary": oracle_summary})

    csv_path = os.path.join(DATA, f"{format_name}_l1_handler_audit_{DATE}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["card", "format", "decks_present_in",
                                           "total_copies", "bucket",
                                           "suggested_registry", "oracle_summary"])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (-r["decks_present_in"], -r["total_copies"], r["card"])):
            w.writerow(r)

    return rows, {"format": format_name, "decks": len(paths), "unique_cards": len(rows),
                  "registered": counts["REGISTERED"], "family_only": counts["FAMILY_ONLY"],
                  "vanilla": counts["VANILLA"], "gaps": counts["HAS_EFFECTS"],
                  "unknown": counts["UNKNOWN_CARD"], "csv_path": csv_path}

# ─── Track B: APL coverage audit ────────────────────────────────────
def derive_key_from_filename(filename):
    base = os.path.basename(filename).replace(".txt", "")
    for fmt in ("modern", "standard", "pioneer", "legacy"):
        if base.endswith("_" + fmt):
            base = base[:-len("_" + fmt)]
            break
    return base.replace("_", "").replace("-", "").replace("'", "").lower()

def classify_apl_quality(module_path):
    parts = module_path.split(".")
    src_path = os.path.join(REPO, *parts) + ".py"
    if not os.path.exists(src_path):
        return ("MISSING_FILE", "", 0)
    try:
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        return ("READ_ERROR", str(e)[:30], 0)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return ("SYNTAX_ERROR", "", 0)

    base_class = ""
    def_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for b in node.bases:
                if isinstance(b, ast.Name):
                    if b.id in ("BaseAPL", "GenericAPL", "MatchAPL", "GoldfishAdapter"):
                        base_class = b.id
                        break
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    def_count += 1
    if base_class == "GenericAPL":
        return ("STUB", base_class, def_count)
    if base_class == "BaseAPL":
        return ("HAND_TUNED" if def_count >= 3 else "STUB", base_class, def_count)
    if base_class == "MatchAPL":
        return ("HAND_TUNED" if def_count >= 3 else "STUB", base_class, def_count)
    if base_class == "GoldfishAdapter":
        return ("ADAPTER", base_class, def_count)
    return ("UNKNOWN_BASE", base_class or "?", def_count)

def verify_deck_load(path):
    """Honors `audit:intentional` and `audit:custom_variant` markers
    in the file's first 10 lines (per 2026-04-25 triage convention)."""
    try:
        with open(path, encoding="utf-8") as f:
            head = "".join(f.readline() for _ in range(10))
        intentional = "audit:intentional" in head
        custom = "audit:custom_variant" in head

        mb, sb = 0, 0
        for count, _, is_sb in parse_deck_lines(path):
            if is_sb: sb += count
            else: mb += count

        if intentional:
            return (mb, sb, f"ok (intentional, mb={mb} sb={sb})")
        if custom:
            return (mb, sb, f"ok (custom_variant triaged, mb={mb} sb={sb})")
        if mb < 40:
            return (mb, sb, f"mainboard too small ({mb})")
        if mb != 60:
            return (mb, sb, f"non-standard mainboard ({mb})")
        if sb not in (0, 15):
            return (mb, sb, f"non-standard sideboard ({sb})")
        return (mb, sb, "ok")
    except Exception as e:
        return (0, 0, f"parse error: {str(e)[:40]}")

def run_apl_audit():
    paths = sorted(glob.glob(os.path.join(REPO, "decks", "*.txt")))
    rows = []
    for path in paths:
        deck_file = os.path.basename(path)
        fmt = parse_format_from_filename(path)
        key = derive_key_from_filename(path)
        apl_entry = APL_REGISTRY.get(key)
        if apl_entry:
            mod_path, cls_name, _stub = apl_entry
            quality, base_class, def_count = classify_apl_quality(mod_path)
            apl_class = cls_name
        else:
            mod_path, cls_name, _stub = ("", "", "")
            quality, base_class, def_count = ("NOT_REGISTERED", "", 0)
            apl_class = ""
        mapl_entry = MATCH_APL_REGISTRY.get(key)
        if mapl_entry:
            mapl_mod, mapl_cls = mapl_entry
            mapl_q, _, _ = classify_apl_quality(mapl_mod)
        else:
            mapl_cls, mapl_q = "", "NOT_REGISTERED"
        mb, sb, load_status = verify_deck_load(path)
        notes = []
        if not apl_entry:
            notes.append("no APL_REGISTRY entry")
        if not mapl_entry and apl_entry:
            notes.append("falls back to GoldfishAdapter")
        if quality == "STUB":
            notes.append("GenericAPL stub")
        rows.append({
            "deck_file": deck_file, "format": fmt, "expected_key": key,
            "apl_found": "yes" if apl_entry else "no",
            "apl_class": apl_class, "apl_module": mod_path,
            "apl_quality": quality, "apl_base_class": base_class,
            "apl_def_count": def_count,
            "match_apl_found": "yes" if mapl_entry else "no",
            "match_apl_class": mapl_cls, "match_apl_quality": mapl_q,
            "mainboard_count": mb, "sideboard_count": sb,
            "load_status": load_status, "notes": "; ".join(notes),
        })
    csv_path = os.path.join(DATA, f"apl_coverage_audit_{DATE}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["format"], r["deck_file"])):
            w.writerow(r)
    return rows, csv_path

# ─── Run both tracks ────────────────────────────────────────────────
print(f"=== Audit run (formats={','.join(FORMATS)}, date={DATE}) ===", file=sys.stderr)
print("=== Track A: L1 handler audit ===", file=sys.stderr)
fmt_results = {}
all_l1_rows = []
for fmt in FORMATS:
    rows, summary = run_l1_for_format(fmt)
    fmt_results[fmt] = summary
    all_l1_rows.extend(rows)
    print(f"  {fmt:10s}: {summary['decks']:>2} decks, {summary['unique_cards']:>4} unique, "
          f"reg={summary['registered']:>4}, fam={summary['family_only']}, "
          f"vanilla={summary['vanilla']}, GAPS={summary['gaps']}, unk={summary['unknown']}",
          file=sys.stderr)

print("\n=== Track B: APL coverage audit ===", file=sys.stderr)
apl_rows, apl_csv = run_apl_audit()
print(f"  {len(apl_rows)} deck files audited -> {apl_csv}", file=sys.stderr)

# ─── Combined markdown ──────────────────────────────────────────────
md_path = os.path.join(DATA, f"full_audit_{DATE}.md")
out = []
def w(line=""): out.append(line)

w(f"# Full Coverage Audit -- {DATE}")
w()
w(f"Generated by `scripts/full_audit.py`. Track A: card-handler L1 coverage "
  f"across decks/*_<format>.txt for formats: {', '.join(FORMATS)}. "
  f"Track B: APL/MatchAPL registry coverage across all decks/*.txt.")
w()
w("## Top-line summary")
w()
w("| Format | Decks | Unique non-land cards | Registered | Family-only | Vanilla | L1 GAPS | Unknown to DB |")
w("|--------|-------|------------------------|------------|-------------|---------|---------|----------------|")
for fmt in FORMATS:
    s = fmt_results[fmt]
    w(f"| {fmt.title()} | {s['decks']} | {s['unique_cards']} | {s['registered']} | "
      f"{s['family_only']} | {s['vanilla']} | **{s['gaps']}** | {s['unknown']} |")
w()

# APL coverage by format
w("## APL coverage by format")
w()
fmt_apl = defaultdict(lambda: {"total": 0, "apl_yes": 0, "mapl_yes": 0,
                                "hand_tuned": 0, "stubs": 0, "load_issues": 0})
for r in apl_rows:
    f = fmt_apl[r["format"]]
    f["total"] += 1
    if r["apl_found"] == "yes": f["apl_yes"] += 1
    if r["match_apl_found"] == "yes": f["mapl_yes"] += 1
    if r["apl_quality"] == "HAND_TUNED": f["hand_tuned"] += 1
    elif r["apl_quality"] == "STUB": f["stubs"] += 1
    if not r["load_status"].startswith("ok"): f["load_issues"] += 1

w("| Format | Decks | APL | MatchAPL | Hand-tuned | Stubs | Load issues |")
w("|--------|-------|-----|----------|------------|-------|-------------|")
for fmt in list(FORMATS) + ["unknown"]:
    if fmt not in fmt_apl: continue
    f = fmt_apl[fmt]
    w(f"| {fmt.title()} | {f['total']} | {f['apl_yes']}/{f['total']} | "
      f"{f['mapl_yes']}/{f['total']} | {f['hand_tuned']} | {f['stubs']} | {f['load_issues']} |")
w()

apl_gaps = [r for r in apl_rows if r["apl_found"] == "no"]
w(f"## APL gaps (decks with no APL_REGISTRY entry) -- {len(apl_gaps)} decks")
w()
if apl_gaps:
    w("| Deck file | Format | Expected key | Notes |")
    w("|-----------|--------|--------------|-------|")
    for r in sorted(apl_gaps, key=lambda r: (r["format"], r["deck_file"])):
        w(f"| `{r['deck_file']}` | {r['format']} | `{r['expected_key']}` | {r['notes']} |")
    w()
else:
    w("_All decks have an APL_REGISTRY entry._")
    w()

mapl_gaps = [r for r in apl_rows if r["apl_found"] == "yes" and r["match_apl_found"] == "no"]
w(f"## MatchAPL gaps (deck has APL but no MatchAPL -- uses GoldfishAdapter) -- {len(mapl_gaps)} decks")
w()
if mapl_gaps:
    w("| Deck file | Format | Goldfish APL | Quality |")
    w("|-----------|--------|--------------|---------|")
    for r in sorted(mapl_gaps, key=lambda r: (r["format"], r["deck_file"])):
        w(f"| `{r['deck_file']}` | {r['format']} | `{r['apl_class']}` | {r['apl_quality']} |")
    w()
else:
    w("_All registered APLs have a MatchAPL._")
    w()

stubs = [r for r in apl_rows if r["apl_quality"] == "STUB"]
w(f"## Stub-only APLs (GenericAPL or thin BaseAPL shims, not hand-tuned) -- {len(stubs)} decks")
w()
if stubs:
    w("| Deck file | Format | APL class | Base | def count |")
    w("|-----------|--------|-----------|------|-----------|")
    for r in sorted(stubs, key=lambda r: (r["format"], r["deck_file"])):
        w(f"| `{r['deck_file']}` | {r['format']} | `{r['apl_class']}` | "
          f"{r['apl_base_class']} | {r['apl_def_count']} |")
    w()
else:
    w("_No stub-only APLs._")
    w()

# Decklist load issues -- now ONLY rows where load_status doesn't start with "ok"
load_issues = [r for r in apl_rows if not r["load_status"].startswith("ok")]
w(f"## Decklist load issues -- {len(load_issues)} decks")
w()
if load_issues:
    w("| Deck file | Format | Mainboard | Sideboard | Status |")
    w("|-----------|--------|-----------|-----------|--------|")
    for r in sorted(load_issues, key=lambda r: (r["format"], r["deck_file"])):
        w(f"| `{r['deck_file']}` | {r['format']} | {r['mainboard_count']} | "
          f"{r['sideboard_count']} | {r['load_status']} |")
    w()
else:
    w("_All decks load with mainboard=60 and sideboard in (0, 15), or are documented "
      "as `audit:intentional` / `audit:custom_variant` per the triage convention._")
    w()

# Per-format L1 gap details
w("## Per-format L1 card-handler gap details")
w()
any_gaps = False
for fmt in FORMATS:
    s = fmt_results[fmt]
    if s["gaps"] == 0 and s["unknown"] == 0:
        continue
    any_gaps = True
    fmt_rows = [r for r in all_l1_rows if r["format"] == fmt]
    gaps = sorted([r for r in fmt_rows if r["bucket"] == "HAS_EFFECTS"],
                   key=lambda r: (-r["decks_present_in"], -r["total_copies"], r["card"]))
    unks = sorted([r for r in fmt_rows if r["bucket"] == "UNKNOWN_CARD"],
                   key=lambda r: (-r["decks_present_in"], -r["total_copies"], r["card"]))
    w(f"### {fmt.title()} -- {len(gaps)} gaps, {len(unks)} unknown-to-DB")
    w()
    if gaps:
        w("| Card | Decks | Copies | Oracle summary | Suggested registry |")
        w("|------|-------|--------|----------------|---------------------|")
        for r in gaps:
            c = r["card"].replace("|", "\\|")
            o = r["oracle_summary"].replace("|", "\\|")
            sug = r["suggested_registry"].replace("|", "\\|")
            w(f"| {c} | {r['decks_present_in']} | {r['total_copies']} | {o} | {sug} |")
        w()
    if unks:
        w(f"#### {fmt.title()} -- unknown to oracle DB (likely typos)")
        w()
        w("| Card | Decks | Copies |")
        w("|------|-------|--------|")
        for r in unks:
            c = r["card"].replace("|", "\\|")
            w(f"| {c} | {r['decks_present_in']} | {r['total_copies']} |")
        w()
if not any_gaps:
    w("_No gaps in any audited format._")
    w()

# Cross-format card overlap
w("## Cross-format card overlap")
w()
cross = defaultdict(lambda: {"formats": set(), "total_copies": 0, "decks_total": 0})
for r in all_l1_rows:
    cross[r["card"]]["formats"].add(r["format"])
    cross[r["card"]]["total_copies"] += r["total_copies"]
    cross[r["card"]]["decks_total"] += r["decks_present_in"]
multi = [(name, info) for name, info in cross.items() if len(info["formats"]) >= 2]
multi.sort(key=lambda x: (-x[1]["total_copies"], -len(x[1]["formats"]), x[0]))
w(f"Cards present in 2+ format pools: **{len(multi)}**. Top 20 by total copies summed across formats:")
w()
w("| Card | Formats | Decks (total) | Copies (total) |")
w("|------|---------|---------------|----------------|")
for name, info in multi[:20]:
    fmts = ", ".join(sorted(info["formats"]))
    c = name.replace("|", "\\|")
    w(f"| {c} | {fmts} | {info['decks_total']} | {info['total_copies']} |")
w()
w(f"_Signal: handler tuning on these cards compounds across formats._")
w()

w("## CSV inventory")
w()
for fmt in FORMATS:
    if fmt_results[fmt]["decks"]:
        w(f"- `data/{fmt}_l1_handler_audit_{DATE}.csv`")
w(f"- `data/apl_coverage_audit_{DATE}.csv`")

with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"\n[saved] {md_path} ({len(out)} lines)", file=sys.stderr)
