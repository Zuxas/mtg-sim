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
    # ── Blitz 2026-06-28: field-gap archetypes (deck resolution for the gauntlet) ──
    "temurprowess":    ("apl.temur_prowess_match",   "TemurProwessMatchAPL",   "decks/temur_prowess_standard.txt"),
    "sultaimidrange":  ("apl.sultai_midrange_match",  "SultaiMidrangeMatchAPL",  "decks/sultai_midrange_modern.txt"),
    "grixismidrange":  ("apl.grixis_midrange_match",  "GrixisMidrangeMatchAPL",  "decks/dimir_murktide_modern.txt"),
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
    # "grindingbreach" + "breach" alias both formerly pointed at
    # apl.grinding_breach + decks/grinding_breach_modern.txt -- but the deck
    # file was a bit-identical copy of decks/temur_breach_modern.txt (Teg
    # storm-ritual list, NOT an Underworld Breach + Grinding Station combo).
    # Removed 2026-05-14 alongside apl/grinding_breach.py. "breach" now
    # redirects to TemurBreach since that's the actual breach deck we model.
    "breach":          ("apl.temur_breach",     "TemurBreachAPL",    "decks/temur_breach_modern.txt"),
    "rubystorm":       ("apl.ruby_storm",       "RubyStormAPL",      "decks/ruby_storm_modern.txt"),
    "belcher":         ("apl.belcher_match",     "BelcherMatchAPL",   "decks/belcher_modern.txt"),
    "goblincharbelcher":("apl.belcher_match",    "BelcherMatchAPL",   "decks/belcher_modern.txt"),
    "neobrand":        ("apl.neobrand_match",    "NeobrandMatchAPL",  "decks/neobrand_modern.txt"),
    "grixisreanimator":("apl.grixis_reanimator_match","GrixisReanimatorMatchAPL","decks/grixis_reanimator_modern.txt"),
    "burn":            ("apl.burn",             "BurnAPL",           None),
    "izzetcauldron":   ("apl.izzet_cauldron_standard_match", "IzzetCauldronMatchAPL", "decks/izzet_cauldron_standard.txt"),
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
    "jeskaicontrol":   ("apl.jeskai_control_standard", "JeskaiControlAPL",  "decks/jeskai_control_standard.txt"),
    "jeskailute":      ("apl.jeskai_control_standard", "JeskaiControlAPL",  "decks/jeskai_lute_standard.txt"),
    "control":         ("apl.jeskai_control",   "JeskaiControlAPL",  "control"),

    # ── Standard / Pioneer ──
    "dimirmidrange":   ("apl.dimir_midrange",   "DimirMidrangeAPL",  "decks/dimir_midrange_modern.txt"),
    "dimir":           ("apl.dimir_midrange",   "DimirMidrangeAPL",  "decks/dimir_midrange_modern.txt"),
    "dimirmidrangestd": ("apl.dimir_midrange",  "DimirMidrangeAPL",  "decks/dimir_midrange_standard.txt"),
    "monogreenlandfall": ("apl.mono_green_landfall", "MonoGreenLandfallAPL", "decks/mono_green_landfall_standard.txt"),
    "standardaggro":   ("apl.standard_aggro",   "StandardAggroAPL",  None),
    "rakdosmidrange":  ("apl.rakdos_midrange",  "RakdosMidrangeAPL", None),
    "rakdos":          ("apl.rakdos_midrange",  "RakdosMidrangeAPL", None),

    # ── Standard match APLs (2026-04-29) — class doubles as goldfish APL ──
    "gruulaggro":      ("apl.gruul_aggro_standard_match",    "GruulAggroStandardMatchAPL", "decks/gruul_aggro_standard.txt"),
    "borosaggrostandard": ("apl.boros_aggro_standard_match","BorosAggroMatchAPL",          "decks/boros_aggro_standard.txt"),
    "borosaggro":      ("apl.boros_aggro_standard_match","BorosAggroMatchAPL",            "decks/boros_aggro_standard.txt"),
    "azoriuscontrol":  ("apl.azorius_control_standard_match","AzoriusControlMatchAPL",     "decks/azorius_control_standard.txt"),
    "esperpixie":      ("apl.esper_pixie_standard_match",    "EsperPixieMatchAPL",         "decks/esper_pixie_standard.txt"),
    "jeskaioculus":    ("apl.jeskai_oculus_standard_match",  "JeskaiOculusMatchAPL",       "decks/jeskai_oculus_standard.txt"),
    "simicouroboroid": ("apl.simic_ouroboroid_standard_match","SimicOuroboroidMatchAPL",   "decks/simic_ouroboroid_standard.txt"),
    "sultaireanimator":("apl.sultai_reanimator_standard_match","SultaiReanimatorStandardMatchAPL","decks/sultai_reanimator_standard.txt"),
    "selesnyalandfall": ("apl.selesnya_landfall_standard_match","SelesnyaLandfallStandardMatchAPL","decks/selesnya_landfall_standard.txt"),
    "izzetspellementals":("apl.izzet_spellementals_standard_match","IzzetSpellementalsStandardMatchAPL","decks/izzet_spellementals_standard.txt"),
    "azoriusmomo":       ("apl.azorius_momo_standard_match",     "AzoriusMomoStandardMatchAPL",    "decks/azorius_momo_standard.txt"),
    "golgari":          ("apl.golgari_midrange_standard_match", "GolgariMidrangeStandardMatchAPL", "decks/golgari_midrange_standard.txt"),
    "golgarimidrange":  ("apl.golgari_midrange_standard_match", "GolgariMidrangeStandardMatchAPL", "decks/golgari_midrange_standard.txt"),
    "domainramp":      ("apl.sultai_reanimator_standard_match","SultaiReanimatorStandardMatchAPL","decks/domain_ramp_standard.txt"),
    "grixisdiscard":   ("apl.izzet_cauldron_standard_match",  "IzzetCauldronMatchAPL",           "decks/grixis_discard_standard.txt"),
    "esperraffine":    ("apl.esper_raffine_standard_match",   "EsperRaffineMatchAPL",            "decks/esper_raffine_standard.txt"),
    "dimiragggrostandard":("apl.esper_raffine_standard_match", "EsperRaffineMatchAPL",            "decks/dimir_aggro_standard.txt"),
    "dimiraggro":       ("apl.esper_raffine_standard_match",   "EsperRaffineMatchAPL",            "decks/dimir_aggro_standard.txt"),
    "azoriusomniscience":("apl.azorius_omniscience_standard_match","AzoriusOmniscienceMatchAPL","decks/azorius_omniscience_standard.txt"),

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
    # ── PT SOS 2026 Standard APLs (2026-05-03) ──────────────────────────
    "selesnyalandfall":   ("apl.selesnya_landfall_standard",  "SelesnyaLandfallAPL",  "decks/selesnya_landfall_standard.txt"),
    "golgarimidrange":    ("apl.golgari_midrange_standard",   "GolgariMidrangeAPL",   "decks/golgari_midrange_standard.txt"),
    "golgari":            ("apl.golgari_midrange_standard",   "GolgariMidrangeAPL",   "decks/golgari_midrange_standard.txt"),
    "azoriusmomo":        ("apl.azorius_momo_standard",       "AzoriusMomoAPL",       "decks/azorius_momo_standard.txt"),
    "momo":               ("apl.azorius_momo_standard",       "AzoriusMomoAPL",       "decks/azorius_momo_standard.txt"),
    "azoriustempo":       ("apl.azorius_tempo_standard",      "AzoriusTempoAPL",      "decks/azorius_tempo_standard.txt"),
    "tempo":              ("apl.azorius_tempo_standard",      "AzoriusTempoAPL",      "decks/azorius_tempo_standard.txt"),
    "izzetmaestro":       ("apl.izzet_maestro_standard",      "IzzetMaestroAPL",      "decks/izzet_maestro_standard.txt"),
    "maestro":            ("apl.izzet_maestro_standard",      "IzzetMaestroAPL",      "decks/izzet_maestro_standard.txt"),
    # ── PT SOS 2026 new archetypes ───────────────────────────────────────
    # Dimir Excruciator: 3.1% of PT field (Victor Santos Esquici list)
    "dimirexcruciator":   ("apl.generic_apl",                 "GenericAPL",           "decks/dimir_excruciator_standard.txt"),
    "excruciator":        ("apl.generic_apl",                 "GenericAPL",           "decks/dimir_excruciator_standard.txt"),
    # Selesnya Ouroboroid: Matt Nass #2 seed PT SOS (Ouroboroid engine)
    "selesnyaouroboroid": ("apl.selesnya_ouroboroid_standard", "SelesnyaOuroboroidAPL", "decks/selesnya_ouroboroid_standard.txt"),
    "ouroboroid":         ("apl.selesnya_ouroboroid_standard", "SelesnyaOuroboroidAPL", "decks/selesnya_ouroboroid_standard.txt"),
    # ── PT SOS 2026 named archetypes (each gets its own APL) ────────────
    "temurlute":           ("apl.lute_control_standard",       "TemurLuteAPL",           "decks/temur_lute_standard.txt"),
    "temurlutestd":        ("apl.lute_control_standard",       "TemurLuteAPL",           "decks/temur_lute_standard.txt"),
    "fourcolorcontrol":    ("apl.lute_control_standard",       "FourColorControlAPL",    "decks/four_color_control_standard.txt"),
    "borordragons":        ("apl.boros_dragons_standard",      "BorsDragonsAPL",         "decks/boros_dragons_standard.txt"),  # kept for compat
    "borosdragons":        ("apl.boros_dragons_standard",      "BorsDragonsAPL",         "decks/boros_dragons_standard.txt"),
    "golgarikona":         ("apl.golgari_kona_standard",       "GolgariKonaAPL",         "decks/golgari_kona_standard.txt"),
    "golgaricontrol":      ("apl.golgari_control_standard",    "GolgariControlAPL",      "decks/golgari_control_standard.txt"),
    "dimirmidrangestdstd": ("apl.dimir_midrange_std_standard", "DimirMidrangeStdAPL",    "decks/dimir_midrange_std_standard.txt"),
    "dimirmidrangestd":    ("apl.dimir_midrange_std_standard", "DimirMidrangeStdAPL",    "decks/dimir_midrange_std_standard.txt"),
    "simicomniscience":    ("apl.omniscience_standard",        "SimicOmniscienceAPL",    "decks/simic_omniscience_standard.txt"),
    "bantomniscience":     ("apl.omniscience_standard",        "BantOmniscienceAPL",     "decks/bant_omniscience_standard.txt"),
    "temuromniscience":    ("apl.omniscience_standard",        "TemurOmniscienceAPL",    "decks/temur_omniscience_standard.txt"),
    "temuomniscience":     ("apl.omniscience_standard",        "TemurOmniscienceAPL",    "decks/temur_omniscience_standard.txt"),
    "fourcolorelemental":  ("apl.four_color_elemental_standard","FourColorElementalAPL", "decks/four_color_elemental_standard.txt"),
    "selesnyarhythm":      ("apl.selesnya_rhythm_standard",    "SelesnyaRhythmAPL",      "decks/selesnya_rhythm_standard.txt"),
    "bantrhythm":          ("apl.bant_rhythm_standard",        "BantRhythmAPL",          "decks/bant_rhythm_standard.txt"),
    "bantairbending":      ("apl.bant_airbending_standard",    "BantAirbendingAPL",      "decks/bant_airbending_standard.txt"),
    # ── Discard-aggro archetypes (PT SOS 2026) ───────────────────────────
    "mardudiscard":    ("apl.discard_aggro_standard", "MarduDiscardAPL",  "decks/mardu_discard_standard.txt"),
    "rakdosdiscard":   ("apl.discard_aggro_standard", "RakdosDiscardAPL", "decks/rakdos_discard_standard.txt"),
    "borosdiscard":    ("apl.discard_aggro_standard", "BorosDiscardAPL",  "decks/boros_discard_standard.txt"),
    "sultaicontrol":   ("apl.sultai_control_standard","SultaiControlAPL", "decks/sultai_control_standard.txt"),
    # Azorius Blink: 2.5% of PT SOS field (12/481 players)
    "azoriusblink":       ("apl.azorius_blink_standard",       "AzoriusBlinkAPL",       "decks/azorius_blink_standard.txt"),
    "blink":              ("apl.azorius_blink_standard",       "AzoriusBlinkAPL",       "decks/azorius_blink_standard.txt"),
    # Izzet Prowess Standard goldfish APL (separate from Modern "izzetprowess")
    "izzetprowessstandard": ("apl.izzet_prowess_standard",    "IzzetProwessAPL",        "decks/izzet_prowess_standard.txt"),
    # Nick Odenheimer / Worldly Counsel RC Tokyo build (post-PT SOS, 2026-05-10)
    "izzetprowessstandardtokyo": ("apl.izzet_prowess_nick_tokyo_standard", "IzzetProwessNickTokyoAPL", "decks/izzet_prowess_nick_tokyo_standard.txt"),
    "prowessnicktokyo":          ("apl.izzet_prowess_nick_tokyo_standard", "IzzetProwessNickTokyoAPL", "decks/izzet_prowess_nick_tokyo_standard.txt"),
    # Izzet Looting (Jermey Store Champ May 2026 -- locked) + Portland Feb 2026 + McNamara Spotlight
    "izzetlootingstorechamp": ("apl.izzet_looting_standard", "IzzetLootingAPL", "decks/izzet_looting_store_champ_may2026_standard.txt"),
    "izzetlootingportland":   ("apl.izzet_looting_standard", "IzzetLootingAPL", "decks/izzet_looting_portland_feb2026_standard.txt"),
    "izzetlootingmcnamara":   ("apl.izzet_looting_standard", "IzzetLootingAPL", "decks/izzet_looting_mcnamara_spotlight_standard.txt"),
    "izzetlooting":           ("apl.izzet_looting_standard", "IzzetLootingAPL", "decks/izzet_looting_store_champ_may2026_standard.txt"),
    "looting":                ("apl.izzet_looting_standard", "IzzetLootingAPL", "decks/izzet_looting_store_champ_may2026_standard.txt"),
    # ── Standard match APLs promoted from GoldfishAdapter (2026-05-04) ──────
    "azoriusaggro":         ("apl.azorius_aggro_standard",       "AzoriusAggroAPL",                   "decks/azorius_aggro_standard.txt"),
    "azoriustempo":         ("apl.azorius_tempo_standard",       "AzoriusTempoAPL",                   "decks/azorius_tempo_standard.txt"),
    "dimirexcruciator":     ("apl.generic_apl",                  "GenericAPL",                        "decks/dimir_excruciator_standard.txt"),
    "excruciator":          ("apl.generic_apl",                  "GenericAPL",                        "decks/dimir_excruciator_standard.txt"),
    "fourcoveroverlords":   ("apl.auto_apls.four_color_overlords","FourColorOverlordsAPL",             "decks/four_color_overlords_standard.txt"),
    "fourcoloroverlords":   ("apl.auto_apls.four_color_overlords","FourColorOverlordsAPL",             "decks/four_color_overlords_standard.txt"),
    "izzetcontrol":         ("apl.izzet_control_standard",       "IzzetControlAPL",                   "decks/izzet_control_standard.txt"),
    "izzetmaestro":         ("apl.izzet_maestro_standard",       "IzzetMaestroAPL",                   "decks/izzet_maestro_standard.txt"),
    "maestro":              ("apl.izzet_maestro_standard",       "IzzetMaestroAPL",                   "decks/izzet_maestro_standard.txt"),
    "monogreenaggro":       ("apl.mono_green_aggro_standard",    "MonoGreenAggroAPL",                 "decks/mono_green_aggro_standard.txt"),
    "roamingelementals":    ("apl.roaming_elementals_standard",  "RoamingElementalsAPL",              "decks/roaming_elementals_standard.txt"),
    "selesnyaouroboroid":   ("apl.selesnya_ouroboroid_standard", "SelesnyaOuroboroidAPL",             "decks/selesnya_ouroboroid_standard.txt"),
    "ouroboroid":           ("apl.selesnya_ouroboroid_standard", "SelesnyaOuroboroidAPL",             "decks/selesnya_ouroboroid_standard.txt"),
    "simicjackal":          ("apl.auto_apls.simic_jackal",       "SimicJackalAPL",                    "decks/simic_jackal_standard.txt"),
    "simicrhythm":          ("apl.auto_apls.simic_rhythm",       "SimicRhythmAPL",                    "decks/simic_rhythm_standard.txt"),
    "superiordoomsday":     ("apl.superior_doomsday_standard",   "SuperiorDoomsdayAPL",               "decks/superior_doomsday_standard.txt"),
    "doomsday":             ("apl.superior_doomsday_standard",   "SuperiorDoomsdayAPL",               "decks/superior_doomsday_standard.txt"),
    "simiccub":             ("apl.simic_cub_standard_match",     "SimicCubStandardMatchAPL",          "decks/simic_cub_standard.txt"),
    # PT Lorwyn Eclipsed: archetypes with match APLs but missing deck-file entries
    # Grixis Elementals (Filipe Sousa EMT list): proxy to roaming elementals (same Elemental core)
    "grixiselementals":     ("apl.roaming_elementals_standard",  "RoamingElementalsAPL",              "decks/roaming_elementals_standard.txt"),
    "grixiselements":       ("apl.roaming_elementals_standard",  "RoamingElementalsAPL",              "decks/roaming_elementals_standard.txt"),
    # Five-Color Rhythm: proxy to Simic Rhythm (same Nature's Rhythm engine, wider color splash)
    "fivecolorrhythm":      ("apl.auto_apls.simic_rhythm",       "SimicRhythmAPL",                    "decks/simic_rhythm_standard.txt"),
    # Izzet Blink: proxy to Izzet Spellementals (both U/R tempo with Elemental synergies)
    "izzetblink":           ("apl.izzet_spellementals_standard", "IzzetSpellementalsAPL",             "decks/izzet_spellementals_standard.txt"),
    "izzetblinkstandard":   ("apl.izzet_spellementals_standard", "IzzetSpellementalsAPL",             "decks/izzet_spellementals_standard.txt"),
    # Azorius High Noon (Zevin Faust UW Prison-Tempo) -- distinct from Bant Airbending
    "azoriushighnoon":      ("apl.azorius_high_noon_standard_match", "AzoriusHighNoonMatchAPL",       "decks/azorius_high_noon_standard.txt"),
    "highnoon":             ("apl.azorius_high_noon_standard_match", "AzoriusHighNoonMatchAPL",       "decks/azorius_high_noon_standard.txt"),
    "azoriusprison":        ("apl.azorius_high_noon_standard_match", "AzoriusHighNoonMatchAPL",       "decks/azorius_high_noon_standard.txt"),
}


# ── Match APL Registry ─────────────────────────────────────────────────
# Maps deck keys to MatchAPL subclasses (opponent-aware, two-player games)
MATCH_APL_REGISTRY = {
    # Blitz 2026-06-28: 3 field-gap match APLs (WF-1, smoke-passed, confidence medium).
    "temurprowess":    ("apl.temur_prowess_match",   "TemurProwessMatchAPL"),
    "sultaimidrange":  ("apl.sultai_midrange_match",  "SultaiMidrangeMatchAPL"),
    "grixismidrange":  ("apl.grixis_midrange_match",  "GrixisMidrangeMatchAPL"),
    "borosenergy":     ("apl.boros_energy_match",   "BorosEnergyMatchAPL"),
    "izzetprowess":    ("apl.izzet_prowess_match",  "IzzetProwessMatchAPL"),       # Modern
    "prowess":         ("apl.izzet_prowess_match",  "IzzetProwessMatchAPL"),       # Modern alias
    "izzetprowessstandard": ("apl.izzet_prowess_standard_match", "IzzetProwessStandardMatchAPL"),
    "izzetprowessstandardtokyo": ("apl.izzet_prowess_nick_tokyo_standard_match", "IzzetProwessNickTokyoMatchAPL"),
    "prowessnicktokyo":          ("apl.izzet_prowess_nick_tokyo_standard_match", "IzzetProwessNickTokyoMatchAPL"),
    # Izzet Looting (single match APL backs all 3 deck variants via different deck files)
    "izzetlootingstorechamp": ("apl.izzet_looting_standard_match", "IzzetLootingStandardMatchAPL"),
    "izzetlootingportland":   ("apl.izzet_looting_standard_match", "IzzetLootingStandardMatchAPL"),
    "izzetlootingmcnamara":   ("apl.izzet_looting_standard_match", "IzzetLootingStandardMatchAPL"),
    "izzetlooting":           ("apl.izzet_looting_standard_match", "IzzetLootingStandardMatchAPL"),
    "looting":                ("apl.izzet_looting_standard_match", "IzzetLootingStandardMatchAPL"),
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
    "5chumans":        ("apl.humans_match",          "HumansMatchAPL"),
    "modernhumans":    ("apl.humans_match",          "HumansMatchAPL"),
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
    "uwcontrol":       ("apl.uw_control_modern_match","UWControlModernMatchAPL"),  # R1 priority-stack opt-in (real control APL)
    "dimirmidrange":   ("apl.murktide_match",         "MurktideMatchAPL"),   # proxy: both Dimir tempo/control
    "dimir":           ("apl.murktide_match",         "MurktideMatchAPL"),
    # New 2026-04-29: real-meta gap decks
    "belcher":         ("apl.belcher_match",         "BelcherMatchAPL"),
    "goblincharbelcher":("apl.belcher_match",        "BelcherMatchAPL"),
    "neobrand":        ("apl.neobrand_match",        "NeobrandMatchAPL"),
    "grixisreanimator":("apl.grixis_reanimator_match","GrixisReanimatorMatchAPL"),
    "jeskaicontrol":   ("apl.jeskai_control_standard_match", "JeskaiControlStandardMatchAPL"),
    "jeskailute":      ("apl.jeskai_lute_standard_match", "JeskaiLuteMatchAPL"),
    "jeskaienergycontrol": ("apl.jeskai_control_standard_match", "JeskaiControlStandardMatchAPL"),
    "jeskaimodern":    ("apl.jeskai_control_match",  "JeskaiControlMatchAPL"),  # Modern variant (Teferi/Narset)
    # Standard APLs (2026-04-29)
    "izzetcauldron":   ("apl.izzet_cauldron_standard_match", "IzzetCauldronMatchAPL"),
    "gruulaggro":      ("apl.gruul_aggro_standard_match",    "GruulAggroStandardMatchAPL"),
    "borosaggrostandard": ("apl.boros_aggro_standard_match", "BorosAggroMatchAPL"),
    "borosaggro":         ("apl.boros_aggro_standard_match", "BorosAggroMatchAPL"),
    "azoriuscontrol":  ("apl.azorius_control_standard_match","AzoriusControlMatchAPL"),
    "esperpixie":      ("apl.esper_pixie_standard_match",    "EsperPixieMatchAPL"),
    "jeskaioculus":    ("apl.jeskai_oculus_standard_match",  "JeskaiOculusMatchAPL"),
    "simicouroboroid": ("apl.simic_ouroboroid_standard_match","SimicOuroboroidMatchAPL"),
    "sultaireanimator":  ("apl.sultai_reanimator_standard_match","SultaiReanimatorStandardMatchAPL"),
    "selesnyalandfall":  ("apl.selesnya_landfall_standard_match","SelesnyaLandfallStandardMatchAPL"),
    "golgarimidrange":   ("apl.golgari_midrange_standard_match", "GolgariMidrangeStandardMatchAPL"),
    "golgari":           ("apl.golgari_midrange_standard_match", "GolgariMidrangeStandardMatchAPL"),
    "domainramp":        ("apl.sultai_reanimator_standard_match","SultaiReanimatorStandardMatchAPL"),
    "grixisdiscard":     ("apl.izzet_cauldron_standard_match",  "IzzetCauldronMatchAPL"),
    "azoriusomniscience":("apl.azorius_omniscience_standard_match","AzoriusOmniscienceMatchAPL"),
    "esperraffine":      ("apl.esper_raffine_standard_match",   "EsperRaffineMatchAPL"),
    "dimiraggro":         ("apl.esper_raffine_standard_match",   "EsperRaffineMatchAPL"),
    # PT SOS additions (2026-05-01)
    "monogreenlandfall": ("apl.mono_green_landfall_standard_match","MonoGreenLandfallStandardMatchAPL"),
    "monogreen":         ("apl.mono_green_landfall_standard_match","MonoGreenLandfallStandardMatchAPL"),
    "izzetlessons":      ("apl.izzet_lesson_standard_match",    "IzzetLessonStandardMatchAPL"),
    "izzetlesson":       ("apl.izzet_lesson_standard_match",    "IzzetLessonStandardMatchAPL"),
    "izzetspellementals":("apl.izzet_spellementals_standard_match","IzzetSpellementalsStandardMatchAPL"),
    "azoriusmomo":       ("apl.azorius_momo_standard_match",    "AzoriusMomoStandardMatchAPL"),
    "momo":              ("apl.azorius_momo_standard_match",    "AzoriusMomoStandardMatchAPL"),
    # Azorius Blink (2026-05-04)
    "azoriusblink":        ("apl.azorius_blink_standard_match",            "AzoriusBlinkStandardMatchAPL"),
    "blink":               ("apl.azorius_blink_standard_match",            "AzoriusBlinkStandardMatchAPL"),
    # ── Standard match APLs promoted from GoldfishAdapter (2026-05-04) ──────
    "azoriusaggro":        ("apl.azorius_aggro_standard_match",            "AzoriusAggroStandardMatchAPL"),
    "azoriustempo":        ("apl.azorius_tempo_standard_match",            "AzoriusTempoStandardMatchAPL"),
    "dimirexcruciator":    ("apl.dimir_excruciator_standard_match",        "DimirExcruciatorStandardMatchAPL"),
    "excruciator":         ("apl.dimir_excruciator_standard_match",        "DimirExcruciatorStandardMatchAPL"),
    "fourcoloroverlords":  ("apl.experimental.four_color_overlords_standard_match", "FourColorOverlordsMatchAPL"),
    "fourcoveroverlords":  ("apl.experimental.four_color_overlords_standard_match", "FourColorOverlordsMatchAPL"),
    "izzetcontrol":        ("apl.izzet_control_standard_match",            "IzzetControlStandardMatchAPL"),
    "izzetmaestro":        ("apl.izzet_maestro_standard_match",            "IzzetMaestroStandardMatchAPL"),
    "maestro":             ("apl.izzet_maestro_standard_match",            "IzzetMaestroStandardMatchAPL"),
    "monogreenaggro":      ("apl.mono_green_aggro_standard_match",         "MonoGreenAggroStandardMatchAPL"),
    "roamingelementals":   ("apl.roaming_elementals_standard_match",       "RoamingElementalsStandardMatchAPL"),
    "selesnyaouroboroid":  ("apl.selesnya_ouroboroid_standard_match",      "SelesnyaOuroboroidStandardMatchAPL"),
    "ouroboroid":          ("apl.selesnya_ouroboroid_standard_match",      "SelesnyaOuroboroidStandardMatchAPL"),
    "simicjackal":         ("apl.experimental.simic_jackal_standard_match","SimicJackalStandardMatchAPL"),
    "simicrhythm":         ("apl.experimental.simic_rhythm_standard_match","SimicRhythmStandardMatchAPL"),
    "superiordoomsday":    ("apl.superior_doomsday_standard_match",        "SuperiorDoomsdayStandardMatchAPL"),
    "doomsday":            ("apl.superior_doomsday_standard_match",        "SuperiorDoomsdayStandardMatchAPL"),
    "simiccub":            ("apl.simic_cub_standard_match",                "SimicCubStandardMatchAPL"),
    # ── PT Lorwyn Eclipsed dominant archetypes (2026-05-04) ─────────────────
    # Rhythm variants: 34.6% of PT Lorwyn Eclipsed field combined
    "simicrhythm":         ("apl.simic_rhythm_standard_match",             "SimicRhythmStandardMatchAPL"),
    "bantrhythm":          ("apl.bant_rhythm_standard_match",              "BantRhythmStandardMatchAPL"),
    "fivecolorrhythm":     ("apl.simic_rhythm_standard_match",             "SimicRhythmStandardMatchAPL"),   # proxy
    # Sultai Reanimator: 10.1% of field; Bringer + Superior Spider-Man combo
    "sultaireanimator":    ("apl.sultai_reanimator_standard_match",        "SultaiReanimatorStandardMatchAPL"),
    "grixiselementals":    ("apl.grixis_elementals_standard_match",        "GrixisElementalsStandardMatchAPL"),
    "izzetblink":          ("apl.izzet_blink_standard_match",              "IzzetBlinkStandardMatchAPL"),
    "izzetblinkstandard":  ("apl.izzet_blink_standard_match",              "IzzetBlinkStandardMatchAPL"),
    "grixiselements":      ("apl.grixis_elementals_standard_match",        "GrixisElementalsStandardMatchAPL"),
    "izzetelementsstandard": ("apl.izzet_spellementals_standard_match",    "IzzetSpellementalsStandardMatchAPL"),  # Izzet Elementals proxy
    # ── New match APLs from guide-informed pass (2026-05-04) ─────────────────
    "bantairbending":      ("apl.bant_airbending_standard_match",          "BantAirbendingStandardMatchAPL"),
    "temurlute":           ("apl.temur_lute_standard_match",               "TemurLuteStandardMatchAPL"),
    "temurlutestd":        ("apl.temur_lute_standard_match",               "TemurLuteStandardMatchAPL"),
    "mardudiscard":        ("apl.discard_aggro_standard_match",            "MarduDiscardStandardMatchAPL"),
    "rakdosdiscard":       ("apl.discard_aggro_standard_match",            "RakdosDiscardStandardMatchAPL"),
    "borosdiscard":        ("apl.discard_aggro_standard_match",            "BorosDiscardStandardMatchAPL"),
    "sultaicontrol":       ("apl.sultai_control_standard_match",           "SultaiControlStandardMatchAPL"),
    # Proxy mappings: route to nearest strategic equivalent
    "dimirmidrangestd":    ("apl.dimir_excruciator_standard_match",        "DimirExcruciatorStandardMatchAPL"),
    "dimirmidrangestdstd": ("apl.dimir_excruciator_standard_match",        "DimirExcruciatorStandardMatchAPL"),
    "dimirmidrangejermey": ("apl.dimir_midrange_jermey_match",             "JermeyDimirMatchAPL"),
    "fourcolorcontrol":    ("apl.jeskai_control_standard_match",           "JeskaiControlStandardMatchAPL"),
    "fourcolorelemental":  ("apl.izzet_spellementals_standard_match",      "IzzetSpellementalsStandardMatchAPL"),
    "golgaricontrol":      ("apl.golgari_midrange_standard_match",         "GolgariMidrangeStandardMatchAPL"),
    "golgarikona":         ("apl.golgari_midrange_standard_match",         "GolgariMidrangeStandardMatchAPL"),
    "selesnyarhythm":      ("apl.selesnya_landfall_standard_match",        "SelesnyaLandfallStandardMatchAPL"),
    # bantrhythm: now has dedicated APL (see PT Lorwyn Eclipsed section above)
    "simicomniscience":    ("apl.azorius_omniscience_standard_match",      "AzoriusOmniscienceMatchAPL"),
    "bantomniscience":     ("apl.azorius_omniscience_standard_match",      "AzoriusOmniscienceMatchAPL"),
    "temuromniscience":    ("apl.azorius_omniscience_standard_match",      "AzoriusOmniscienceMatchAPL"),
    # ── Typo aliases + remaining proxy mappings ───────────────────────────────
    "borordragons":        ("apl.azorius_momo_standard_match",             "AzoriusMomoStandardMatchAPL"),   # typo; Boros Dragons ~ Azorius Momo (flying aggro)
    "borosdragons":        ("apl.azorius_momo_standard_match",             "AzoriusMomoStandardMatchAPL"),   # proxy; dragon tribal flying aggro
    "borosenergyvariantjermey": ("apl.boros_energy_match",                 "BorosEnergyMatchAPL"),           # custom variant
    "dimiragggrostandard": ("apl.esper_raffine_standard_match",            "EsperRaffineMatchAPL"),           # typo of dimiraggro
    "dimiroculus":         ("apl.dimir_excruciator_standard_match",        "DimirExcruciatorStandardMatchAPL"), # Dimir Oculus ~ Dimir Midrange
    "espermidrange":       ("apl.esper_raffine_standard_match",            "EsperRaffineMatchAPL"),           # Esper midrange
    "espervengance":       ("apl.goryos_match",                            "GoryosMatchAPL"),                 # typo of Esper Goryo's
    "goryovengeance":      ("apl.goryos_match",                            "GoryosMatchAPL"),                 # Goryo's Vengeance
    "orzhovblink":         ("apl.uw_blink_match",                          "UWBlinkMatchAPL"),                # Orzhov Blink ~ UW Blink
    "rakdos":              ("apl.golgari_midrange_standard_match",         "GolgariMidrangeStandardMatchAPL"), # generic Rakdos -> midrange proxy
    "rakdosmidrange":      ("apl.golgari_midrange_standard_match",         "GolgariMidrangeStandardMatchAPL"), # Rakdos Midrange
    "standardaggro":       ("apl.mono_red_match",                          "MonoRedMatchAPL"),                 # generic aggro -> MonoRed proxy
    "temuomniscience":     ("apl.azorius_omniscience_standard_match",      "AzoriusOmniscienceMatchAPL"),     # typo of temuromniscience
    # Azorius High Noon -- Zevin Faust's UW Prison-Tempo (NOT Bant Airbending)
    "azoriushighnoon":     ("apl.azorius_high_noon_standard_match",        "AzoriusHighNoonMatchAPL"),
    "highnoon":            ("apl.azorius_high_noon_standard_match",        "AzoriusHighNoonMatchAPL"),
    "azoriusprison":       ("apl.azorius_high_noon_standard_match",        "AzoriusHighNoonMatchAPL"),
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
