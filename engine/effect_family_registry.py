"""
Effect-family registry for batching and validation.

Keep guesses conservative. Only slot cards you are reasonably confident about.
Unknowns should remain absent rather than be force-classified.
"""

from __future__ import annotations

from typing import Dict, List

FAMILIES: List[str] = [
    "single_target_removal",
    "sweeper_removal",
    "burn_and_drain",
    "card_draw",
    "loot_rummage_discard",
    "token_creation",
    "etb_targeted_effects",
    "counterspells",
    "graveyard_recursion",
    "search_and_tutor",
    "additional_cost_modal_spells",
    "counters_and_stat_modification",
]

CARD_TO_FAMILY: Dict[str, str] = {
    # burn / targeted damage
    "Lightning Strike": "burn_and_drain",
    "Torch the Tower": "burn_and_drain",
    "Shock": "burn_and_drain",
    "Play with Fire": "burn_and_drain",

    # single-target removal
    "Cut Down": "single_target_removal",
    "Go for the Throat": "single_target_removal",
    "Sheoldred's Edict": "single_target_removal",
    "Get Lost": "single_target_removal",
    "Ossification": "single_target_removal",
    "Bitter Triumph": "single_target_removal",
    "Destroy Evil": "single_target_removal",
    "Fateful Absence": "single_target_removal",
    "Anoint with Affliction": "single_target_removal",
    "Tear Asunder": "single_target_removal",

    # sweepers
    "Sunfall": "sweeper_removal",
    "Temporary Lockdown": "sweeper_removal",
    "Depopulate": "sweeper_removal",
    "Path of Peril": "sweeper_removal",

    # draw / selection
    "Memory Deluge": "card_draw",
    "Deduce": "card_draw",
    "Quick Study": "card_draw",
    "Silver Scrutiny": "card_draw",

    # loot / rummage / discard
    "Big Score": "loot_rummage_discard",
    "Unexpected Windfall": "loot_rummage_discard",
    "Faithless Looting": "loot_rummage_discard",
    "Thrill of Possibility": "loot_rummage_discard",

    # counters and stat mods
    "Monstrous Rage": "counters_and_stat_modification",
    "Audacity": "counters_and_stat_modification",
    "Battlefield Improvisation": "counters_and_stat_modification",

    # token creation
    "Wedding Announcement": "token_creation",
    "Resolute Reinforcements": "token_creation",
    "Fable of the Mirror-Breaker": "token_creation",

    # counterspells
    "Make Disappear": "counterspells",
    "Negate": "counterspells",
    "Disdainful Stroke": "counterspells",
    "Three Steps Ahead": "counterspells",

    # graveyard recursion
    "Helping Hand": "graveyard_recursion",
    "Return Triumphant": "graveyard_recursion",
    "Cruelclaw's Heist": "graveyard_recursion",

    # search / tutor
    "Analyze the Pollen": "search_and_tutor",

    # modal / additional cost
    "Insatiable Avarice": "additional_cost_modal_spells",

    # ETB targeted effects
    "Skyclave Apparition": "etb_targeted_effects",
    "Brutal Cathar": "etb_targeted_effects",
    "Werefox Bodyguard": "etb_targeted_effects",
    "Loran of the Third Path": "etb_targeted_effects",
}

FAMILY_TO_SCENARIOS: Dict[str, List[int]] = {
    "single_target_removal": [1, 2, 4],
    "sweeper_removal": [5],
    "burn_and_drain": [1, 15, 16],
    "card_draw": [10, 11],
    "loot_rummage_discard": [12],
    "token_creation": [6, 7],
    "etb_targeted_effects": [8, 9],
    "counterspells": [13, 14],
    "graveyard_recursion": [17],
    "search_and_tutor": [18],
    "additional_cost_modal_spells": [19, 10, 11],
    "counters_and_stat_modification": [3, 20],
}

FAMILY_TO_HELPERS: Dict[str, List[str]] = {
    "single_target_removal": [
        "destroy_target_permanent",
        "exile_target_permanent",
        "deal_damage_to_creature",
        "validate_target_is_creature_or_permanent",
    ],
    "sweeper_removal": [
        "destroy_all_matching",
        "deal_mass_damage",
        "exile_all_matching",
    ],
    "burn_and_drain": [
        "deal_damage_to_player",
        "deal_damage_to_any_target",
        "drain_life",
        "gain_life",
    ],
    "card_draw": [
        "draw_cards",
        "lose_if_library_empty",
    ],
    "loot_rummage_discard": [
        "draw_then_discard",
        "discard_then_draw",
        "discard_cards",
    ],
    "token_creation": [
        "create_token",
        "create_multiple_tokens",
        "enter_token_tapped",
        "enter_token_with_counters",
    ],
    "etb_targeted_effects": [
        "register_etb_trigger",
        "resolve_etb_with_target",
        "resolve_etb_without_target",
    ],
    "counterspells": [
        "counter_target_spell",
        "validate_stack_target",
        "move_countered_spell_to_zone",
    ],
    "graveyard_recursion": [
        "return_from_graveyard_to_hand",
        "return_from_graveyard_to_battlefield",
        "validate_graveyard_target",
    ],
    "search_and_tutor": [
        "search_library_for_match",
        "reveal_found_card",
        "shuffle_library",
    ],
    "additional_cost_modal_spells": [
        "require_additional_cost",
        "resolve_selected_mode",
        "spree_mode_selection",
        "bargain_check",
        "kicker_check",
    ],
    "counters_and_stat_modification": [
        "add_counters",
        "remove_counters",
        "modify_power_toughness_until_eot",
        "recompute_derived_stats",
    ],
}
