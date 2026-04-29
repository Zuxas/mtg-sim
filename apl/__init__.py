"""
apl/ — Action Priority List registry

Unified registry mapping deck name keys to (module, class, stub_key) tuples.
This is the SINGLE SOURCE OF TRUTH for APL lookups.

Usage:
    from apl import get_apl, get_match_apl, APL_REGISTRY
    apl = get_apl("Boros Energy")         # returns BorosEnergyAPL()
    mapl = get_match_apl("Boros Energy")  # returns BorosEnergyMatchAPL()
"""

from apl.base_apl import BaseAPL
from apl.mulligan import take_opening_hand, generic_keep, generic_bottom


# ── Unified APL Registry ───────────────────────────────────────────────
# Key: lowercased, stripped of spaces/hyphens/apostrophes
# Value: (module_path, class_name, stub_key_or_deck_file)
#   stub_key: string ending in .txt = deck file path
#             other string = key for get_stub_deck_list()
#             None = load from playbook

APL_REGISTRY = {
    # ── Legacy ──
    "legacyhumans":    ("apl.humans",          "HumansAPL",         "decks/humans_legacy.txt"),
    "humans":          ("apl.humans",           "HumansAPL",         "decks/humans_legacy.txt"),
    "5chumans":        ("apl.humans",           "HumansAPL",         "decks/humans_modern.txt"),
    "modernhumans":    ("apl.humans",           "HumansAPL",         "decks/humans_modern.txt"),
    "elves":           ("apl.elves",            "ElvesAPL",          None),
    "delver":          ("apl.delver",           "DelverAPL",         None),
    "urdelver":        ("apl.delver",           "DelverAPL",         None),
    "lands":           ("apl.lands",            "LandsAPL",          None),
    "painter":         ("apl.painter",          "PainterAPL",        None),
    "stoneforge":      ("apl.stoneforge",       "StoneforgeAPL",     None),
    "hogaak":          ("apl.hogaak",           "HogaakAPL",         None),
    "golarihogaak":    ("apl.hogaak",           "HogaakAPL",         None),
    "reanimator":      ("apl.reanimator",       "ReanimatorAPL",     None),
    "dimirtempolegacy":("apl.tempo",            "DimirTempoAPL",     None),

    # ── Modern (goldfish) ──
    "borosenergy":     ("apl.boros_energy",     "BorosEnergyAPL",    "decks/boros_energy_modern.txt"),
    "borosenergyvariantjermey": ("apl.boros_energy", "BorosEnergyAPL",
        "decks/boros_energy_variant_jermey_2026-04-26.txt"),
    "izzetprowess":    ("apl.izzet_prowess",    "IzzetProwessAPL",   "prowess"),
    "prowess":         ("apl.izzet_prowess",    "IzzetProwessAPL",   "prowess"),
    "domainzoo":       ("apl.domain_zoo",       "DomainZooAPL",      "domain"),
    "domain":          ("apl.domain_zoo",       "DomainZooAPL",      "domain"),
    "moderndomainzoo": ("apl.modern_domain_zoo","ModernDomainZooAPL","domain"),
    "amulettitan":     ("apl.amulet_titan",     "AmuletTitanAPL",    "decks/amulet_titan_modern.txt"),
    "amulet":          ("apl.amulet_titan",     "AmuletTitanAPL",    "titan"),
    "titan":           ("apl.amulet_titan",     "AmuletTitanAPL",    "titan"),
    "eldrazitron":     ("apl.eldrazi_tron",     "EldraziTronAPL",    "decks/eldrazi_tron_modern.txt"),
    "etron":           ("apl.eldrazi_tron",     "EldraziTronAPL",    "decks/eldrazi_tron_modern.txt"),
    "eldraziramp":     ("apl.eldrazi_ramp",     "EldraziRampAPL",    "decks/eldrazi_ramp_modern.txt"),
    "neoform":         ("apl.neoform_combo",    "NeoformComboAPL",   "decks/neoform_modern.txt"),
    "neoformcombo":    ("apl.neoform_combo",    "NeoformComboAPL",   "decks/neoform_modern.txt"),
    "grindingbreach":  ("apl.grinding_breach",  "GrindingBreachAPL", "decks/grinding_breach_modern.txt"),
    "breach":          ("apl.grinding_breach",  "GrindingBreachAPL", "decks/grinding_breach_modern.txt"),
    "rubystorm":       ("apl.ruby_storm",       "RubyStormAPL",      "decks/ruby_storm_modern.txt"),
    "burn":            ("apl.burn",             "BurnAPL",           None),
    "monored":         ("apl.mono_red_aggro",   "MonoRedAggroAPL",   "decks/mono_red_aggro_modern.txt"),
    "monoredaggro":    ("apl.mono_red_aggro",   "MonoRedAggroAPL",   "decks/mono_red_aggro_modern.txt"),
    "izzetaffinity":   ("apl.izzet_affinity",   "IzzetAffinityAPL",  "decks/izzet_affinity_modern.txt"),
    "affinity":        ("apl.izzet_affinity",   "IzzetAffinityAPL",  "decks/izzet_affinity_modern.txt"),
    "izzetphoenix":    ("apl.izzet_phoenix",    "IzzetPhoenixAPL",   None),
    "phoenix":         ("apl.izzet_phoenix",    "IzzetPhoenixAPL",   None),
    "murktide":        ("apl.dimir_murktide",   "MurktideAPL",       "decks/dimir_oculus_modern.txt"),
    "dimirmurktide":   ("apl.dimir_murktide",   "MurktideAPL",       "decks/dimir_oculus_modern.txt"),
    # 2026-04-26 Stage A BUCKET 1: dimir_oculus is a Murktide variant.
    "dimiroculus":     ("apl.dimir_murktide",   "MurktideAPL",       "decks/dimir_oculus_modern.txt"),

    # ── Modern goldfish stubs (2026-04-26 Stage A: GenericAPL shims for
    #    Modern decks that have MatchAPL files but no goldfish APL. Each
    #    stub registers with deck-specific name/role passed to GenericAPL.
    #    Treat numbers from these as "registered, not validated" -- they
    #    let gauntlets RUN but don't model deck-specific synergies.) ──
    "glockulous":      ("apl.glockulous",       "GlockulousAPL",     "decks/glockulous_modern.txt"),
    "jeskaiblink":     ("apl.jeskai_blink",     "JeskaiBlinkAPL",    "decks/jeskai_blink_modern.txt"),
    "livingend":       ("apl.living_end",       "LivingEndAPL",      "decks/living_end_modern.txt"),
    "temurbreach":     ("apl.temur_breach",     "TemurBreachAPL",    "decks/temur_breach_modern.txt"),
    "uwcontrol":       ("apl.uw_control",       "UWControlAPL",      "decks/uw_control_modern.txt"),
    "yawgmoth":        ("apl.yawgmoth",         "YawgmothAPL",       "decks/yawgmoth_modern.txt"),

    # ── Modern (match-aware) ──
    "uwblink":         ("apl.uw_blink",         "UWBlinkAPL",        "uw_blink"),
    "espermidrange":   ("apl.esper_midrange",   "EsperMidrangeAPL",  "esper_mid"),
    "esperblink":      ("apl.esper_blink",      "EsperBlinkAPL",     "esper_blink"),
    # 2026-04-26 Stage A BUCKET 1: orzhov_blink_modern.txt is misnamed
    # -- header reads "Esper Blink - botje_". Alias to EsperBlinkAPL.
    "orzhovblink":     ("apl.esper_blink",      "EsperBlinkAPL",     "decks/orzhov_blink_modern.txt"),
    "goryosvengeance": ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "goryovengeance":  ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "espervengance":   ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "goryos":          ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "jeskaicontrol":   ("apl.jeskai_control",   "JeskaiControlAPL",  "control"),
    "control":         ("apl.jeskai_control",   "JeskaiControlAPL",  "control"),

    # ── Standard / Pioneer ──
    "dimirmidrange":   ("apl.dimir_midrange",   "DimirMidrangeAPL",  "decks/dimir_midrange_standard.txt"),
    "dimir":           ("apl.dimir_midrange",   "DimirMidrangeAPL",  "decks/dimir_midrange_standard.txt"),
    "monogreenlandfall": ("apl.mono_green_landfall", "MonoGreenLandfallAPL", "decks/mono_green_landfall_standard.txt"),
    "standardaggro":   ("apl.standard_aggro",   "StandardAggroAPL",  None),
    "rakdosmidrange":  ("apl.rakdos_midrange",  "RakdosMidrangeAPL", None),
    "rakdos":          ("apl.rakdos_midrange",  "RakdosMidrangeAPL", None),

    # ── Standard Strixhaven brews (GenericAPL shims, 2026-04-23) ──
    "izzetcontrol":       ("apl.izzet_control_standard",      "IzzetControlAPL",      "decks/izzet_control_standard.txt"),
    "roamingelementals":  ("apl.roaming_elementals_standard", "RoamingElementalsAPL", "decks/roaming_elementals_standard.txt"),
    "monogreenaggro":     ("apl.mono_green_aggro_standard",   "MonoGreenAggroAPL",    "decks/mono_green_aggro_standard.txt"),

    # ── Standard existing APLs not previously registered (2026-04-23) ──
    # APL files and decklists have existed in the repo but were never wired
    # into APL_REGISTRY, which meant any gauntlet against them silently
    # failed with "Could not load deck." Surfaced during narrow-gauntlet run.
    "izzetlesson":        ("apl.izzet_lesson",                "IzzetLessonAPL",       "decks/izzet_lesson_standard.txt"),
    "izzetlessons":       ("apl.izzet_lesson",                "IzzetLessonAPL",       "decks/izzet_lesson_standard.txt"),
    "superiordoomsday":   ("apl.superior_doomsday_standard",  "SuperiorDoomsdayAPL",  "decks/superior_doomsday_standard.txt"),
    "doomsday":           ("apl.superior_doomsday_standard",  "SuperiorDoomsdayAPL",  "decks/superior_doomsday_standard.txt"),
    "azoriusaggro":       ("apl.azorius_aggro_standard",      "AzoriusAggroAPL",      "decks/azorius_aggro_standard.txt"),
}


# ── Match APL Registry ─────────────────────────────────────────────────
# Maps deck keys to MatchAPL subclasses (opponent-aware, two-player games)
MATCH_APL_REGISTRY = {
    "borosenergy":     ("apl.boros_energy_match",   "BorosEnergyMatchAPL"),
    "izzetprowess":    ("apl.izzet_prowess_match",  "IzzetProwessMatchAPL"),
    "prowess":         ("apl.izzet_prowess_match",  "IzzetProwessMatchAPL"),
    "domainzoo":       ("apl.domain_zoo_match",     "DomainZooMatchAPL"),
    "domain":          ("apl.domain_zoo_match",     "DomainZooMatchAPL"),
    "amulettitan":     ("apl.amulet_titan_match",   "AmuletTitanMatchAPL"),
    "amulet":          ("apl.amulet_titan_match",   "AmuletTitanMatchAPL"),
    "titan":           ("apl.amulet_titan_match",   "AmuletTitanMatchAPL"),
    "eldrazitron":     ("apl.eldrazi_tron_match",   "EldraziTronMatchAPL"),
    "etron":           ("apl.eldrazi_tron_match",   "EldraziTronMatchAPL"),
    "eldraziramp":     ("apl.eldrazi_ramp_match",   "EldraziRampMatchAPL"),
    "rubystorm":       ("apl.ruby_storm_match",     "RubyStormMatchAPL"),
    "uwblink":         ("apl.uw_blink_match",       "UWBlinkMatchAPL"),
    "esperblink":      ("apl.esper_blink_match",    "EsperBlinkMatchAPL"),
    "goryosvengeance": ("apl.goryos_match",         "GoryosMatchAPL"),
    "goryos":          ("apl.goryos_match",         "GoryosMatchAPL"),
    "humans":          ("apl.humans_match",          "HumansMatchAPL"),
    "legacyhumans":    ("apl.humans_match",          "HumansMatchAPL"),
    "monored":         ("apl.mono_red_match",        "MonoRedMatchAPL"),
    "monoredaggro":    ("apl.mono_red_match",        "MonoRedMatchAPL"),
    "murktide":        ("apl.murktide_match",        "MurktideMatchAPL"),
    "dimirmurktide":   ("apl.murktide_match",        "MurktideMatchAPL"),
    "neoform":         ("apl.neoform_match",         "NeoformMatchAPL"),
    "neoformcombo":    ("apl.neoform_match",         "NeoformMatchAPL"),
    "jeskaiblink":     ("apl.jeskai_blink_match",    "JeskaiBlinkMatchAPL"),
    # "jeskaicontrol" removed -- was wrongly routed to JeskaiBlinkMatchAPL.
    # Falls back to GoldfishAdapter(JeskaiControlAPL) until a real match APL exists.
    "izzetaffinity":   ("apl.affinity_match",        "IzzetAffinityMatchAPL"),
    "affinity":        ("apl.affinity_match",        "IzzetAffinityMatchAPL"),
    "glockulous":      ("apl.glockulous_match",      "GlockulousMatchAPL"),
    "livingend":       ("apl.living_end_match",      "LivingEndMatchAPL"),
    "yawgmoth":        ("apl.yawgmoth_match",        "YawgmothMatchAPL"),
    "golariyawgmoth":  ("apl.yawgmoth_match",        "YawgmothMatchAPL"),
    "uwcontrol":       ("apl.uw_control_match",      "UWControlMatchAPL"),
    "dimirmidrange":   ("apl.dimir_oculus_match",    "DimirOculusMatchAPL"),
    "dimir":           ("apl.dimir_oculus_match",    "DimirOculusMatchAPL"),
}


def _normalize_key(name: str) -> str:
    """Normalize a deck name to a registry key.

    Two-phase (fixed 2026-04-24 — caught when 'Dimir Midrange'
    was being normalized to 'midrange' by prefix-strip, missing
    the 'dimirmidrange' registry entry):
      1. Strict: lowercase + strip separators, no prefix rewrite.
         If that key exists in APL_REGISTRY or MATCH_APL_REGISTRY,
         return it directly.
      2. Fallback: strip known color/format prefixes ('dimir ',
         'ur ', 'legacy ', etc.) for short-form aliases like
         'UR Prowess' → 'prowess' and 'Dimir Murktide' → 'murktide'.
    """
    strict = name.lower().strip().replace(" ", "").replace("-", "").replace("'", "")
    if strict in APL_REGISTRY or strict in MATCH_APL_REGISTRY:
        return strict
    # Fall back to prefix-strip for short-form aliases
    key = name.lower().strip()
    for prefix in ("legacy ", "modern ", "pioneer ", "standard ",
                   "ur ", "uw ", "golgari ", "dimir "):
        if key.startswith(prefix):
            key = key[len(prefix):]
    return key.replace(" ", "").replace("-", "").replace("'", "")


def _load_class(module_path: str, class_name: str):
    """Lazy import an APL class."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


# Stage S4 / 2026-04-28: auto-registry sidecar for APLs generated by
# auto_pipeline.py. Loaded lazily on first lookup miss. Canonical
# APL_REGISTRY (above) is never mutated; auto entries are a fallback
# layer only. Registry file: data/auto_apl_registry.json
# Per parallel-entry-points-need-mirror-fix v1.5 lesson, the fallback
# is applied in get_apl_entry (which is consumed by get_apl + get_match_apl
# transitively, so a single fallback site here covers all 3 entry points).
_AUTO_REG_CACHE = None


def _load_auto_registry():
    global _AUTO_REG_CACHE
    if _AUTO_REG_CACHE is not None:
        return _AUTO_REG_CACHE
    from pathlib import Path
    reg_path = Path(__file__).parent.parent / "data" / "auto_apl_registry.json"
    if not reg_path.exists():
        _AUTO_REG_CACHE = {}
        return _AUTO_REG_CACHE
    try:
        import json
        _AUTO_REG_CACHE = json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception:
        _AUTO_REG_CACHE = {}
    return _AUTO_REG_CACHE


def get_apl(deck_name: str) -> BaseAPL | None:
    """
    Return a goldfish APL instance for a deck name.
    Returns None if no APL is registered (canonical or auto).
    """
    entry = get_apl_entry(deck_name)
    if not entry:
        return None
    mod_path, cls_name, _ = entry
    try:
        cls = _load_class(mod_path, cls_name)
        return cls()
    except Exception as e:
        print(f"  [APL load failed for {deck_name}: {e}]")
        return None


def get_match_apl(deck_name: str):
    """
    Return a MatchAPL instance for two-player games.
    Falls back to GoldfishAdapter wrapping the goldfish APL.
    Returns None if no APL exists at all (canonical or auto).
    """
    key = _normalize_key(deck_name)

    # Try match-specific APL first (canonical only; no auto MatchAPL path yet)
    entry = MATCH_APL_REGISTRY.get(key)
    if entry:
        mod_path, cls_name = entry
        try:
            cls = _load_class(mod_path, cls_name)
            return cls()
        except Exception as e:
            print(f"  [MatchAPL load failed for {deck_name}: {e}]")

    # Fall back to GoldfishAdapter (now picks up auto-registered goldfish APLs
    # via get_apl -> get_apl_entry -> auto registry fallback)
    goldfish = get_apl(deck_name)
    if goldfish:
        from apl.match_apl import GoldfishAdapter
        return GoldfishAdapter(goldfish)

    return None


def get_apl_entry(deck_name: str) -> tuple | None:
    """Return the raw registry entry (module, class, stub_key) or None.

    Canonical APL_REGISTRY checked first; auto-registry sidecar
    (data/auto_apl_registry.json) consulted on miss. Auto entries are
    populated by auto_pipeline.py after passing the smoke gate (50-game
    goldfish without crash). Failed APLs stay on disk but never enter
    the auto registry, so they're never returned from this function.
    """
    key = _normalize_key(deck_name)
    entry = APL_REGISTRY.get(key)
    if entry:
        return entry
    # Auto-registry fallback (Stage S4)
    auto = _load_auto_registry().get(key)
    if auto:
        return (auto["module"], auto["class"], auto["deck_file"])
    return None
