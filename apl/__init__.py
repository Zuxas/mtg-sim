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
    "borosenergy":     ("apl.boros_energy",     "BorosEnergyAPL",    "boros_energy"),
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

    # ── Modern (match-aware) ──
    "uwblink":         ("apl.uw_blink",         "UWBlinkAPL",        "uw_blink"),
    "espermidrange":   ("apl.esper_midrange",   "EsperMidrangeAPL",  "esper_mid"),
    "esperblink":      ("apl.esper_blink",      "EsperBlinkAPL",     "esper_blink"),
    "goryosvengeance": ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "goryovengeance":  ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "espervengance":   ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "goryos":          ("apl.goryo_vengeance",  "GoryoVengeanceAPL", "decks/goryos_vengeance_modern.txt"),
    "jeskaicontrol":   ("apl.jeskai_control",   "JeskaiControlAPL",  "control"),
    "control":         ("apl.jeskai_control",   "JeskaiControlAPL",  "control"),

    # ── Standard / Pioneer ──
    "dimirmidrange":   ("apl.dimir_midrange",   "DimirMidrangeAPL",  None),
    "dimir":           ("apl.dimir_midrange",   "DimirMidrangeAPL",  None),
    "standardaggro":   ("apl.standard_aggro",   "StandardAggroAPL",  None),
    "rakdosmidrange":  ("apl.rakdos_midrange",  "RakdosMidrangeAPL", None),
    "rakdos":          ("apl.rakdos_midrange",  "RakdosMidrangeAPL", None),
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
    "jeskaicontrol":   ("apl.jeskai_blink_match",    "JeskaiBlinkMatchAPL"),
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
    """Normalize a deck name to a registry key."""
    key = name.lower().strip()
    # Strip format prefixes
    for prefix in ("legacy ", "modern ", "pioneer ", "standard ",
                   "ur ", "uw ", "golgari ", "dimir "):
        if key.startswith(prefix):
            key = key[len(prefix):]
    # Remove separators
    return key.replace(" ", "").replace("-", "").replace("'", "")


def _load_class(module_path: str, class_name: str):
    """Lazy import an APL class."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def get_apl(deck_name: str) -> BaseAPL | None:
    """
    Return a goldfish APL instance for a deck name.
    Returns None if no APL is registered.
    """
    key = _normalize_key(deck_name)
    entry = APL_REGISTRY.get(key)
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
    Returns None if no APL exists at all.
    """
    key = _normalize_key(deck_name)

    # Try match-specific APL first
    entry = MATCH_APL_REGISTRY.get(key)
    if entry:
        mod_path, cls_name = entry
        try:
            cls = _load_class(mod_path, cls_name)
            return cls()
        except Exception as e:
            print(f"  [MatchAPL load failed for {deck_name}: {e}]")

    # Fall back to GoldfishAdapter
    goldfish = get_apl(deck_name)
    if goldfish:
        from apl.match_apl import GoldfishAdapter
        return GoldfishAdapter(goldfish)

    return None


def get_apl_entry(deck_name: str) -> tuple | None:
    """Return the raw registry entry (module, class, stub_key) or None."""
    key = _normalize_key(deck_name)
    return APL_REGISTRY.get(key)
