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


# [woe] When Greta enters, create a Food token. (It's an artifact with "{2}, {T}, Sacrif
_h_greta__sweettooth_scourge = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] When this artifact enters, draw a card. | {1}, {T}: Add one mana of any color.
_h_prophetic_prism = _etb([["draw", {"n": 1}]])
# [woe] When this creature enters, you may return another target nonland permanent you c
_h_stockpiling_celebrant = _etb([["scry", {"n": 2}]])
# [woe] When this creature enters, you may pay {2}. If you do, create a Sorcerer Role to
_h_unassuming_sage = _etb([["scry", {"n": 1}]])
# [woe] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_provisions_merchant = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] When this enchantment enters, create a 2/2 white Knight creature token with vigi
_h_hopeful_vigil = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["vigilance"]}]])
# [woe] When this enchantment enters, create a Food token. (It's an artifact with "{2}, 
_h_night_of_the_sweets__revenge = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_sweettooth_witch = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] When this creature enters, you may pay {1}. When you do, create a Young Hero Rol
_h_merry_bards = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [woe] Flash | Flying | When this creature enters, destroy target creature an opponent cont
_h_stingblade_assassin = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [woe] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_experimental_confectioner = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] When this creature enters, create a 1/1 black Rat creature token with "This toke
_h_voracious_vermin = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_high_fae_negotiator = _etb([["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [woe] When this creature enters, create a 1/1 black Rat creature token with "This crea
_h_twisted_sewer_witch = _etb([["lose_life", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This creature can't block"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_hamlet_glutton = _etb([["gain_life", {"n": 3}]])
# [woe] When this enchantment enters, exile target creature an opponent controls until t
_h_food_coma = _etb([["exile", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] Flying | Ward {2} (Whenever this creature becomes the target of a spell or ability
_h_archive_dragon = _etb([["scry", {"n": 2}]])
# [woe] When this enchantment enters, create a Wicked Role token attached to target crea
_h_lord_skitter_s_blessing = _etb([["lose_life", {"n": 1, "target": "opp"}]])
# [woe] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_redcap_thief = _etb([["create_treasure", {"n": 1}]])
# [woe] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_edgewall_pack = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [lci] When this creature enters, it explores. (Reveal the top card of your library. Pu
_h_river_herald_scout = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this artifact enters or is put into a graveyard from the battlefield, you d
_h_mephitic_draught = _etb([["draw", {"n": 1}]])
# [lci] When this creature enters, surveil 2. Then for each card you put on top of your 
_h_starving_revenant = _etb([["draw", {"n": 1}]])
# [lci] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_plundering_pirate = _etb([["create_treasure", {"n": 1}]])
# [lci] Trample | When this creature enters, draw a card for each other Dinosaur you contr
_h_earthshaker_dreadmaw = _etb([["draw", {"n": 1}]])
# [lci] When this creature enters, it explores. (Reveal the top card of your library. Pu
_h_pathfinding_axejaw = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Flash | When this artifact enters, it deals 6 damage to target creature an opponen
_h_runaway_boulder = _etb([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [lci] When this Vehicle enters, it deals 5 damage to target creature an opponent contr
_h_magmatic_galleon = _etb([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [lci] Flying | When this creature enters, you gain 3 life. | Plainscycling {2} ({2}, Disca
_h_soaring_sandwing = _etb([["gain_life", {"n": 3}]])
# [lci] When this creature enters, search your library for a basic land card or Cave car
_h_scampering_surveyor = _etb([["search_basic_land", {"n": 1}]])
# [lci] When this creature enters, you may reveal a Dinosaur card from your hand. If you
_h_armored_kincaller = _etb([["gain_life", {"n": 3}]])
# [lci] Deathtouch | When this creature enters, you may mill two cards. (You may put the t
_h_deathcap_marionette = _etb([["mill", {"n": 2, "target": "self"}]])
# [lci] When this creature enters, draw a card. | Descend 4 ? This creature has flying as 
_h_didact_echo = _etb([["draw", {"n": 1}]])
# [lci] Enchant creature or Vehicle | When this Aura enters, you may mill two cards. (You 
_h_song_of_stupefaction = _etb([["mill", {"n": 2, "target": "self"}]])
# [lci] Flying | When this creature enters, create a 1/1 colorless Gnome artifact creature
_h_oltec_cloud_guard = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [lci] When this creature enters, scry 2. (Look at the top two cards of your library, t
_h_cavern_stomper = _etb([["scry", {"n": 2}]])
# [lci] When this creature enters, you may search your library for a basic land card or 
_h_compass_gnome = _etb([["search_basic_land", {"n": 1}]])
# [lci] Double strike | When this creature enters, it explores. (Reveal the top card of yo
_h_kinjalli_s_dawnrunner = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Vigilance | When this creature enters, it explores. (Reveal the top card of your l
_h_river_herald_guide = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this enchantment enters, create a 1/1 black Bat creature token with flying 
_h_bat_colony = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying for each mana from a Cave spent to cast it"]}]])
# [lci] When this artifact enters, create two 1/1 colorless Gnome artifact creature toke
_h_tinker_s_tote = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [lci] Other Dinosaurs you control have haste. | When this creature enters, create two 0/
_h_palani_s_hatcher = _etb([["create_token", {"count": 2, "power": "0", "toughness": "1", "keywords": []}]])
# [lci] When this creature enters, create a 3/3 green Dinosaur creature token. | Forestcyc
_h_nurturing_bristleback = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [lci] Reach | When this creature enters, you may mill two cards. (You may put the top tw
_h_mineshaft_spider = _etb([["mill", {"n": 2, "target": "self"}]])
# [lci] When this creature enters, put a +1/+1 counter on target creature.
_h_ironpaw_aspirant = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] When this creature enters, create a 2/2 white and blue Detective creature token.
_h_inside_source = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] When this creature enters, investigate. (Create a Clue token. It's an artifact w
_h_loxodon_eavesdropper = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] As an additional cost to cast this spell, you may collect evidence 6. (Exile car
_h_vitu_ghazi_inspector = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 2}]])
# [mkm] When this creature enters, return up to one other target creature to its owner's
_h_hotshot_investigators = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] When this creature enters, suspect it. Create a 2/2 white and blue Detective cre
_h_person_of_interest = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] When this creature enters, you may sacrifice an artifact. When you do, this crea
_h_cornered_crook = _etb([["damage_any", {"n": 3}]])
# [mkm] When this Case enters, create a 2/1 black Skeleton creature token and suspect it
_h_case_of_the_stashed_skeleton = _etb([["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": []}]])
# [mkm] When this enchantment enters, create a 1/1 white Human creature token, a 1/1 blu
_h_a_killer_among_us = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [mkm] When this Case enters, it deals 3 damage to target creature an opponent controls
_h_case_of_the_burning_masks = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [mkm] When this creature enters, you may sacrifice an artifact or creature. When you d
_h_undercity_eliminator = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [mkm] When this enchantment enters, exile target creature an opponent controls until t
_h_makeshift_binding = _etb([["exile", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 2}]])
# [mkm] When this enchantment enters, it deals 3 damage to target creature an opponent c
_h_blood_spatter_analysis = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [mkm] Flying | When this creature enters, investigate. (Create a Clue token. It's an art
_h_gleaming_geardrake = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] When this creature enters, investigate. (Create a Clue token. It's an artifact w
_h_persuasive_interrogators = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Menace | When this creature enters, target opponent creates two 1/1 white Dog crea
_h_hunted_bonebrute = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [mkm] When this Case enters, search your library for a basic land card, reveal it, put
_h_case_of_the_shattered_pact = _etb([["search_basic_land", {"n": 1}]])
# [mkm] When this creature enters or is turned face up, create a 1/1 colorless Thopter a
_h_gadget_technician = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [mkm] Vigilance | When Alquist Proft enters, investigate. (Create a Clue token. It's an 
_h_alquist_proft__master_sleuth = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] When this artifact enters, investigate twice. (To investigate, create a Clue tok
_h_detective_s_satchel = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Enchant land | When this Aura enters, exile target nonland permanent you don't con
_h_buried_in_the_garden = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [otj] When this creature enters, you may sacrifice a creature. When you do, target pla
_h_unscrupulous_contractor = _etb([["draw", {"n": 2}]])
# [otj] When this creature enters, create a 1/1 red Mercenary creature token with "{T}: 
_h_prosperity_tycoon = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] When Ertha Jo enters, create a 1/1 red Mercenary creature token with "{T}: Targe
_h_ertha_jo__frontier_mentor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] When this creature enters, if you've cast two or more spells this turn, draw a c
_h_loan_shark = _etb([["draw", {"n": 1}]])
# [otj] Other outlaws you control have haste. (Assassins, Mercenaries, Pirates, Rogues, 
_h_hellspur_posse_boss = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] When this creature enters, if you control a creature with power 4 or greater, dr
_h_beastbond_outcaster = _etb([["draw", {"n": 1}]])
# [otj] When this creature enters, you gain 2 life. | {T}: Add one mana of any color.
_h_oasis_gardener = _etb([["gain_life", {"n": 2}]])
# [otj] When this creature enters, create a 1/1 red Mercenary creature token with "{T}: 
_h_prickly_pair = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] Trample | When this creature enters, if you control another outlaw, create a Treas
_h_mine_raider = _etb([["create_treasure", {"n": 1}]])
# [otj] When Rakdos Joins Up enters, return target creature card from your graveyard to 
_h_rakdos_joins_up = _etb([["return_gy_to_bf", {"filter_type": "creature"}]])
# [otj] Flash | Flying | When this creature enters, you gain 2 life and scry 1. (Look at the
_h_holy_cow = _etb([["gain_life", {"n": 2}], ["scry", {"n": 1}]])
# [otj] When this creature enters, you may search your library for a basic land card or 
_h_silver_deputy = _etb([["search_basic_land", {"n": 1}]])
# [otj] When this creature enters, target player draws a card and loses 1 life.
_h_vault_plunderer = _etb([["draw", {"n": 1}]])
# [otj] When this creature enters, search your library for a basic land card or a Desert
_h_outcaster_greenblade = _etb([["search_basic_land", {"n": 1}]])
# [otj] When this Equipment enters, create a Treasure token. (It's an artifact with "{T}
_h_gold_pan = _etb([["create_treasure", {"n": 1}]])
# [otj] When this creature enters, if a creature died this turn, create a 2/2 blue and b
_h_rictus_robber = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [otj] When this enchantment enters, exile target nonland permanent an opponent control
_h_lassoed_by_the_law = _etb([["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] When this creature enters, create a 2/2 blue and black Zombie Rogue creature tok
_h_outlaw_stitcher = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [otj] When this creature enters, you may discard a card. If you do, draw a card.
_h_discerning_peddler = _etb([["draw", {"n": 1}]])
# [otj] When this creature enters, mill three cards. Put a land card from among the mill
_h_patient_naturalist = _etb([["mill", {"n": 3, "target": "self"}], ["create_treasure", {"n": 1}]])
# [otj] Trample | When this creature enters, you gain 3 life. | Plot {3}{G} (You may pay {3}
_h_spinewoods_paladin = _etb([["gain_life", {"n": 3}]])
# [otj] When Fortune enters, scry 2. | Whenever Fortune attacks while saddled, at end of c
_h_fortune__loyal_steed = _etb([["scry", {"n": 2}]])
# [otj] When this enchantment enters, create a 1/1 red Mercenary creature token with "{T
_h_rakish_crew = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] Lifelink | When this creature enters, target player mills two cards. (They put the
_h_desperate_bloodseeker = _etb([["mill", {"n": 2, "target": "self"}]])
# [otj] Flash | Flying, lifelink | When this creature enters, destroy target creature an opp
_h_rooftop_assassin = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [big] When this enchantment enters, you draw three cards, gain 6 life, and create thre
_h_greed_s_gambit = _etb([["draw", {"n": 3}], ["create_token", {"count": 3, "power": "2", "toughness": "1", "keywords": ["flying"]}]])
# [big] Trample | When this creature enters, create two Food tokens. (They're artifacts wi
_h_bristlebud_farmer = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [blb] Flying | When this creature enters, put a +1/+1 counter on target creature you con
_h_pileated_provisioner = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] When this creature enters, mill three cards. When you do, target creature an opp
_h_wick_s_patrol = _etb([["mill", {"n": 3, "target": "self"}]])
# [blb] Offspring {3} (You may pay an additional {3} as you cast this spell. If you do, 
_h_thornplate_intimidator = _etb([["lose_life", {"n": 3, "target": "opp"}]])
# [blb] Flying | When this creature enters, each opponent loses 2 life and you gain 2 life
_h_glidedive_duo = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [blb] Deathtouch | When this creature enters, you may mill two cards. (You may put the t
_h_daggerfang_duo = _etb([["mill", {"n": 2, "target": "self"}]])
# [blb] Trample | When this creature enters, put a +1/+1 counter on it for each other Squi
_h_honored_dreyleader = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] When this creature enters, create two 1/1 white Rabbit creature tokens.
_h_head_of_the_homestead = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [blb] Offspring {2} (You may pay an additional {2} as you cast this spell. If you do, 
_h_bushy_bodyguard = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Reach | When this creature enters, you may forage. If you do, draw a card. (To for
_h_treetop_sentries = _etb([["draw", {"n": 1}]])
# [blb] When this artifact enters, create a Food token. (It's an artifact with "{2}, {T}
_h_bumbleflower_s_sharepot = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [blb] When this creature enters, put a +1/+1 counter on target creature and you gain 1
_h_sunshower_druid = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 1}]])
# [blb] Flash | Enchant creature | When this Aura enters, draw a card. | Enchanted creature ge
_h_feather_of_flight = _etb([["draw", {"n": 1}]])
# [blb] When this creature enters or dies, create a Food token. (It's an artifact with "
_h_vinereap_mentor = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [blb] When this artifact enters, you may search your library for a basic land card, re
_h_fountainport_bell = _etb([["search_basic_land", {"n": 1}]])
# [blb] When this creature enters, create a Food token. | Whenever you expend 4, this crea
_h_bakersbane_duo = _etb([["gain_life", {"n": 3}]])
# [blb] When this creature enters, draw a card, then discard a card.
_h_bellowing_crier = _etb([["draw", {"n": 1}]])
# [blb] When this creature enters, exile target creature an opponent controls until this
_h_driftgloom_coyote = _etb([["exile", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [dsk] When Marina Vendrell's Grimoire enters, if you cast it, draw five cards. | You hav
_h_marina_vendrell_s_grimoire = _etb([["draw", {"n": 5}]])
# [dsk] When this creature enters, it deals 4 damage to each opponent. | Delirium ? Whenev
_h_fear_of_burning_alive = _etb([["damage_player", {"n": 4, "target": "opp"}]])
# [dsk] When this creature enters, you may sacrifice another creature or enchantment. Wh
_h_boilerbilges_ripper = _etb([["damage_any", {"n": 2}]])
# [dsk] When this enchantment enters, you may sacrifice another enchantment or creature.
_h_disturbing_mirth = _etb([["draw", {"n": 2}]])
# [dsk] When this creature enters, create a 1/1 white Glimmer enchantment creature token
_h_tunnel_surveyor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] When this creature enters, each player discards a card. If you discarded a card 
_h_fanatic_of_the_harrowing = _etb([["draw", {"n": 1}]])
# [dsk] As an additional cost to cast this spell, exile a creature you control. | Flying | W
_h_fear_of_abduction = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [dsk] When this Equipment enters, create a 1/1 white Glimmer enchantment creature toke
_h_glimmerlight = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] When this creature enters, search your library for a basic land card, reveal it,
_h_spineseeker_centipede = _etb([["search_basic_land", {"n": 1}]])
# [fdn] When this creature enters, each opponent discards a card.
_h_burglar_rat = _etb([["discard", {"n": 1, "target": "opp"}]])
# [fdn] When this creature enters, create a 4/4 red Dragon creature token with flying.
_h_dragon_trainer = _etb([["create_token", {"count": 1, "power": "4", "toughness": "4", "keywords": ["flying"]}]])
# [fdn] When this creature enters, it deals 1 damage to any target.
_h_skeleton_archer = _etb([["damage_any", {"n": 1}]])
# [fdn] When this creature enters, if you control another Elf, create a 1/1 green Elf Wa
_h_dwynen_s_elite = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] Flash | When this enchantment enters, exile up to one target nonland permanent an 
_h_prayer_of_binding = _etb([["gain_life", {"n": 2}]])
# [fdn] Flying | When this creature enters, draw a card, then discard a card.
_h_icewind_elemental = _etb([["draw", {"n": 1}]])
# [fdn] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_cat_collector = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [fdn] As an additional cost to cast this spell, sacrifice a creature. | Flying | When this
_h_arbiter_of_woe = _etb([["draw", {"n": 1}], ["discard", {"n": 1, "target": "opp"}]])
# [fdn] When this creature enters, you may search your library for a basic land card, re
_h_campus_guide = _etb([["search_basic_land", {"n": 1}]])
# [fdn] Lifelink (Damage dealt by this creature also causes you to gain that much life.)
_h_guarded_heir = _etb([["create_token", {"count": 2, "power": "3", "toughness": "3", "keywords": []}]])
# [fdn] Flash (You may cast this spell any time you could cast an instant.) | When this en
_h_stasis_snare = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [fdn] When this creature enters, you may sacrifice a land. If you do, search your libr
_h_springbloom_druid = _etb([["search_basic_land", {"n": 2}]])
# [fdn] Enchant land | When this Aura enters, put a +1/+1 counter on target creature you c
_h_new_horizons = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Flying | When this creature enters, if an opponent lost life this turn, each oppon
_h_bloodtithe_collector = _etb([["discard", {"n": 1, "target": "opp"}]])
# [fdn] Flying | When this creature enters or dies, mill two cards. (Put the top two cards
_h_crow_of_dark_tidings = _etb([["mill", {"n": 2, "target": "self"}]])
# [fdn] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_corsair_captain = _etb([["create_treasure", {"n": 1}]])
# [fdn] Menace | When this creature enters, create two 1/1 black Rat creature tokens with 
_h_redcap_gutter_dweller = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [fdn] When this creature enters, return target permanent card from your graveyard to y
_h_elvish_regrower = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Flying | This creature can't block. | When this creature enters, return target creat
_h_vampire_soulcaller = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Kicker {3}{B} (You may pay an additional {3}{B} as you cast this spell.) | Lifelin
_h_nullpriest_of_oblivion = _etb([["return_gy_to_bf", {"filter_type": "creature"}]])
# [fdn] Flying | When this creature enters, mill three cards. (Put the top three cards of 
_h_billowing_shriekmass = _etb([["mill", {"n": 3, "target": "self"}]])
# [fdn] Trample (This creature can deal excess combat damage to the player or planeswalk
_h_pelakka_wurm = _etb([["gain_life", {"n": 7}]])
# [fdn] Flying | When this creature enters, you gain 1 life and draw a card.
_h_inspiring_overseer = _etb([["draw", {"n": 1}], ["gain_life", {"n": 1}]])
# [fdn] When this creature enters, destroy target nonland permanent an opponent controls
_h_meteor_golem = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Flying | When this creature enters, you gain 2 life for each Gate you control.
_h_archway_angel = _etb([["gain_life", {"n": 2}]])
# [fdn] When this creature enters, exile up to two target cards from a single graveyard.
_h_soul_shackled_zombie = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [fdn] Flying | When this creature enters, you gain 2 life and draw two cards.
_h_cloudblazer = _etb([["draw", {"n": 2}], ["gain_life", {"n": 2}]])
# [dft] When this creature enters, create a 1/1 colorless Thopter artifact creature toke
_h_nimble_thopterist = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [dft] When this Vehicle enters, scry 2. (Look at the top two cards of your library, th
_h_spotcycle_scouter = _etb([["scry", {"n": 2}]])
# [dft] When this Vehicle enters, create a 1/1 colorless Thopter artifact creature token
_h_broadcast_rambler = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [dft] Start your engines! (If you have no speed, it starts at 1. It increases once on 
_h_embalmed_ascendant = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dft] When Aatchik enters, create a 1/1 green Insect creature token for each artifact 
_h_aatchik__emerald_radian = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dft] Start your engines! (If you have no speed, it starts at 1. It increases once on 
_h_racers__scoreboard = _etb([["draw", {"n": 2}]])
# [dft] Reach | When this creature enters, you gain 4 life. | Cycling {2} ({2}, Discard this
_h_migrating_ketradon = _etb([["gain_life", {"n": 4}]])
# [dft] When this Vehicle enters, search your library for a basic land card, reveal it, 
_h_marshals__pathcruiser = _etb([["search_basic_land", {"n": 1}]])
# [dft] When this creature enters, scry 2. | {T}: Create X 1/1 colorless Pilot creature to
_h_cloudspire_coordinator = _etb([["scry", {"n": 2}]])
# [dft] When this Vehicle enters, each opponent discards a card. | Crew 2 (Tap any number 
_h_ripclaw_wrangler = _etb([["discard", {"n": 1, "target": "opp"}]])
# [dft] Enchant creature or Vehicle | When this Aura enters, create a 1/1 colorless Pilot 
_h_roadside_assistance = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token saddles Mounts", "crews Vehicles as though its power were 2 greater"]}]])
# [dft] Menace, reach | When this Vehicle enters, destroy target nonland permanent an oppo
_h_thundering_broodwagon = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [dft] Affinity for artifacts (This spell costs {1} less to cast for each artifact you 
_h_demonic_junker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dft] When this creature enters, mill three cards, then you may return a land card fro
_h_pothole_mole = _etb([["mill", {"n": 3, "target": "self"}]])
# [dft] When this Vehicle enters, scry 1. | Tap three other untapped creatures you control
_h_voyager_glidecar = _etb([["scry", {"n": 1}]])
# [dft] Defender | When this creature enters, if an opponent controls more lands than you,
_h_ticket_tortoise = _etb([["create_treasure", {"n": 1}]])
# [dft] When this artifact enters, draw a card. | {2}, {T}: Target Mount you control becom
_h_guidelight_matrix = _etb([["draw", {"n": 1}]])
# [dft] When this Vehicle enters, mill two cards. Then return a creature or Vehicle card
_h_carrion_cruiser = _etb([["mill", {"n": 2, "target": "self"}]])
# [dft] Flying | When this Vehicle enters, draw two cards. | Crew 3 (Tap any number of creat
_h_hulldrifter = _etb([["draw", {"n": 2}]])
# [dft] When this creature enters, mill two cards, then put a +1/+1 counter on this crea
_h_ooze_patrol = _etb([["add_counters", {"n": 1, "target": "self"}], ["mill", {"n": 2, "target": "self"}]])
# [dft] Start your engines! | When this enchantment enters, create a 2/2 black Zombie crea
_h_hour_of_victory = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dft] When this creature enters and whenever it attacks while saddled, create a 3/3 gr
_h_autarch_mammoth = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [dft] When this Vehicle enters, you gain 2 life. | {T}: Add one mana of any color. | Crew 
_h_veloheart_bike = _etb([["gain_life", {"n": 2}]])
# [tdm] When this creature enters, it deals 5 damage to target creature an opponent cont
_h_unsparing_boltcaster = _etb([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [tdm] When this creature enters, if you cast it, mill four cards. When you do, return 
_h_yathan_roadwatcher = _etb([["mill", {"n": 4, "target": "self"}]])
# [tdm] When this enchantment enters, search your library for up to two basic land cards
_h_encroaching_dragonstorm = _etb([["search_basic_land", {"n": 2}]])
# [tdm] When this enchantment enters, create two 2/2 white Soldier creature tokens. | When
_h_teeming_dragonstorm = _etb([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": []}]])
# [tdm] When this creature enters, scry 2. (Look at the top two cards of your library, t
_h_mardu_devotee = _etb([["scry", {"n": 2}]])
# [tdm] Prowess (Whenever you cast a noncreature spell, this creature gets +1/+1 until e
_h_meticulous_artisan = _etb([["create_treasure", {"n": 1}]])
# [tdm] When this creature enters, create a 1/1 red Goblin creature token. | {1}, {T}: Tar
_h_underfoot_underdogs = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tdm] Reach | When this creature enters, it endures 3. (Put three +1/+1 counters on it o
_h_dusyut_earthcarver = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [tdm] Trample | When this creature enters, each opponent loses 2 life and you gain 2 lif
_h_skirmish_rhino = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [tdm] When this enchantment enters, exile target nonland permanent an opponent control
_h_stormplain_detainment = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [tdm] When this enchantment enters, each opponent loses 2 life and you gain 2 life. Su
_h_corroding_dragonstorm = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [tdm] Affinity for creatures (This spell costs {1} less to cast for each creature you 
_h_salt_road_packbeast = _etb([["draw", {"n": 1}]])
# [tdm] When this creature enters or dies, put a +1/+1 counter on target creature you co
_h_reputable_merchant = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] When this creature enters, you may mill three cards. (You may put the top three 
_h_rainveil_rejuvenator = _etb([["mill", {"n": 3, "target": "self"}]])
# [tdm] When this creature enters, mill three cards. You may put a land card from among 
_h_ainok_wayfarer = _etb([["add_counters", {"n": 1, "target": "self"}], ["mill", {"n": 3, "target": "self"}]])
# [tdm] When this creature enters, draw a card, then discard a card.
_h_temur_tawnyback = _etb([["draw", {"n": 1}]])
# [tdm] When this creature enters, draw a card if you control a creature with a counter 
_h_trade_route_envoy = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [tdm] Lifelink | When this creature enters, it endures 1. (Put a +1/+1 counter on it or 
_h_kin_tree_nurturer = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tdm] When this creature enters, you may search your library for a basic land card, re
_h_embermouth_sentinel = _etb([["search_basic_land", {"n": 1}]])
# [tdm] Flying | When this creature enters, it deals 2 damage to any target and you gain 2
_h_sonic_shrieker = _etb([["damage_any", {"n": 2}], ["gain_life", {"n": 2}]])
# [tdm] When this creature enters, put a +1/+1 counter on target creature. | Renew ? {3}{G
_h_sage_of_the_fang = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_sandskitter_outrider = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tdm] When this creature enters, it endures 1. (Put a +1/+1 counter on it or create a 
_h_fortress_kin_guard = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] When this Vehicle enters, create a 1/1 colorless Hero creature token. | Crew 1 (Ta
_h_magitek_armor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] When this creature enters, create a 0/1 black Wizard creature token with "Whenev
_h_mysidian_elder = _etb([["damage_player", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": ["\"Whenever you cast a noncreature spell", "this token deals 1 damage to each opponent"]}]])
# [fin] Flash | When this artifact enters, draw a card. | {2}, {T}, Sacrifice this artifact:
_h_instant_ramen = _etb([["draw", {"n": 1}]])
# [fin] When Edgar enters, draw a card for each artifact you control. | Two-Headed Coin ? 
_h_edgar__king_of_figaro = _etb([["draw", {"n": 1}]])
# [fin] When this creature enters, you lose 1 life and create a Treasure token. | Whenever
_h_namazu_trader = _etb([["create_treasure", {"n": 1}]])
# [fin] Trample | When this creature enters, you gain 3 life. | Forestcycling {2} ({2}, Disc
_h_balamb_t_rexaur = _etb([["gain_life", {"n": 3}]])
# [fin] When this creature enters, mill three cards and you gain 3 life. (To mill three 
_h_shinra_reinforcements = _etb([["mill", {"n": 3, "target": "self"}], ["gain_life", {"n": 3}]])
# [fin] When this creature enters, each opponent discards a card.
_h_hecteyes = _etb([["discard", {"n": 1, "target": "opp"}]])
# [fin] When this creature enters, draw a card. | At the beginning of combat on your turn,
_h_weapons_vendor = _etb([["draw", {"n": 1}]])
# [fin] When this Equipment enters, it deals 2 damage to any target. | Equipped creature g
_h_lion_heart = _etb([["damage_any", {"n": 2}]])
# [fin] Flying | When this creature enters, create a 1/1 colorless Hero creature token.
_h_dragoon_s_wyvern = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Flying | When this creature enters, put a +1/+1 counter on target creature. | Plains
_h_cloudbound_moogle = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this Spacecraft enters, create a 2/2 colorless Robot artifact creature toke
_h_wedgelight_rammer = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [eoe] When this enchantment enters, if you cast it, shuffle your hand and graveyard in
_h_weftwalking = _etb([["draw", {"n": 7}]])
# [eoe] When this creature enters, create a 1/1 white Human Soldier creature token. | Warp
_h_knight_luminary = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [eoe] When this Spacecraft enters, mill three cards, then return a creature or Spacecr
_h_fell_gravship = _etb([["mill", {"n": 3, "target": "self"}]])
# [eoe] When this creature enters, you may sacrifice an artifact. When you do, put a +1/
_h_selfcraft_mechan = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [eoe] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_kav_landseeker = _etb([["search_basic_land", {"n": 1}]])
# [eoe] When this Spacecraft enters, put a +1/+1 counter on each creature you control. | S
_h_atmospheric_greenhouse = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this creature enters, put a +1/+1 counter on target creature. | Each creature
_h_drix_fatemaker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this creature enters, create a 1/1 white Human Soldier creature token. | {4}{
_h_honored_knight_captain = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [eoe] When this enchantment enters, create a Lander token. (It's an artifact with "{2}
_h_bioengineered_future = _etb([["search_basic_land", {"n": 1}]])
# [eoe] Flying | When this creature enters, it deals 3 damage to any target.
_h_nebula_dragon = _etb([["damage_any", {"n": 3}]])
# [eoe] When this creature enters, put a +1/+1 counter on target creature you control. | W
_h_rayblade_trooper = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this Spacecraft enters, draw two cards, then discard a card. | Station (Tap a
_h_uthros_scanship = _etb([["draw", {"n": 2}]])
# [eoe] When this creature enters, look at the top five cards of your library. You may r
_h_pulsar_squadron_ace = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this creature enters, create a Lander token. (It's an artifact with "{2}, {
_h_galactic_wayfarer = _etb([["search_basic_land", {"n": 1}]])
# [eoe] When this creature enters, you gain 2 life. | Warp {1}{G} (You may cast this card 
_h_germinating_wurm = _etb([["gain_life", {"n": 2}]])
# [eoe] When this creature enters, if an opponent controls more lands than you, create a
_h_sunstar_expansionist = _etb([["search_basic_land", {"n": 1}]])
# [eoe] When this creature enters, create a Lander token. (It's an artifact with "{2}, {
_h_biomechan_engineer = _etb([["search_basic_land", {"n": 1}]])
# [eoe] When this Spacecraft enters, you may sacrifice a land or Lander. If you do, sear
_h_larval_scoutlander = _etb([["search_basic_land", {"n": 2}]])
# [eoe] When this Spacecraft enters, it deals 3 damage to any target. | Station (Tap anoth
_h_debris_field_crusher = _etb([["damage_any", {"n": 3}]])
# [eoe] When this creature enters, destroy up to one other target creature. If that crea
_h_faller_s_faithful = _etb([["draw", {"n": 2}]])
# [eoe] When this creature enters, each opponent discards a card.
_h_virus_beetle = _etb([["discard", {"n": 1, "target": "opp"}]])
# [eoe] When Alpharael enters, draw two cards. Then discard two cards unless you discard
_h_alpharael__dreaming_acolyte = _etb([["draw", {"n": 2}]])
# [eoe] When this Equipment enters, create a 2/2 colorless Robot artifact creature token
_h_auxiliary_boosters = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [spm] When Spider-Ham enters, create a Food token. (It's an artifact with "{2}, {T}, S
_h_spider_ham__peter_porker = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [spm] Enchant land | When this Aura enters, create three 1/1 green and white Human Citiz
_h_friendly_neighborhood = _etb([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [spm] Flying | When this creature enters, create a 1/1 green and white Human Citizen cre
_h_news_helicopter = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [spm] Web-slinging {2}{G} (You may cast this spell for {2}{G} if you also return a tap
_h_spider_man__brooklyn_visionary = _etb([["search_basic_land", {"n": 1}]])
# [spm] When this creature enters, draw a card.
_h_gallant_citizen = _etb([["draw", {"n": 1}]])
# [spm] When this artifact enters, it deals 5 damage to target creature. | {1}{R}, Discard
_h_steel_wrecking_ball = _etb([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [spm] When Anti-Venom enters, if he was cast, return target creature card from your gr
_h_anti_venom__horrifying_healer = _etb([["return_gy_to_bf", {"filter_type": "creature"}]])
# [spm] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_professional_wrestler = _etb([["create_treasure", {"n": 1}]])
# [spm] When Mysterio enters, create a 3/3 blue Illusion Villain creature token for each
_h_mysterio__master_of_illusion = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [spm] When this creature enters, target creature you control connives. (Draw a card, t
_h_mob_lookout = _etb([["draw", {"n": 1}]])
# [spm] When this enchantment enters, create a 2/1 green Spider creature token with reac
_h_wall_crawl = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": ["reach", "then you gain 1 life for each Spider you control"]}]])
# [spm] When this Vehicle enters, you may pay {G}. If you do, search your library for a 
_h_subway_train = _etb([["search_basic_land", {"n": 1}]])
# [spm] Flash | Enchant creature | When this Aura enters, create two 1/1 colorless Robot art
_h_robotics_mastery = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [spm] When this enchantment enters, exile target nonland permanent an opponent control
_h_web_up = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [spm] When this creature enters, exile up to one target card from a graveyard. Target 
_h_mechanical_mobster = _etb([["draw", {"n": 1}]])
# [spm] When this artifact enters, draw a card. | {1}{B}, Sacrifice this artifact: Mill fo
_h_eerie_gravestone = _etb([["draw", {"n": 1}]])
# [spm] When this artifact enters, create a Food token. (It's an artifact with "{2}, {T}
_h_hot_dog_cart = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [spm] Web-slinging {4}{G}{G} (You may cast this spell for {4}{G}{G} if you also return
_h_spiders_man__heroic_horde = _etb([["gain_life", {"n": 3}], ["create_token", {"count": 2, "power": "2", "toughness": "1", "keywords": ["reach"]}]])
# [spm] Reach | When this creature enters, you may search your library for a basic land ca
_h_spider_bot = _etb([["search_basic_land", {"n": 1}]])
# [spm] Deathtouch | When this creature enters, mill two cards. (Put the top two cards of 
_h_venomized_cat = _etb([["mill", {"n": 2, "target": "self"}]])
# [tla] As an additional cost to cast this spell, waterbend {5}. (While paying a waterbe
_h_benevolent_river_spirit = _etb([["scry", {"n": 2}]])
# [tla] When this creature enters, earthbend 2. (Target land you control becomes a 0/0 c
_h_badgermole = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Vigilance | When Katara enters, create a 1/1 white Ally creature token. | Waterbend 
_h_katara__water_tribe_s_hope = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] When Crescent Island Temple enters, for each Shrine you control, create a 1/1 re
_h_crescent_island_temple = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["prowess"]}]])
# [tla] When Northern Air Temple enters, each opponent loses X life and you gain X life,
_h_northern_air_temple = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [tla] Flying | When this creature enters, you may sacrifice an artifact or creature. If 
_h_buzzard_wasp_colony = _etb([["draw", {"n": 1}]])
# [tla] When this creature enters, mill three cards. You may put a land card from among 
_h_ostrich_horse = _etb([["add_counters", {"n": 1, "target": "self"}], ["mill", {"n": 3, "target": "self"}]])
# [tla] When Toph enters, earthbend 2. (Target land you control becomes a 0/0 creature w
_h_toph__the_blind_bandit = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Trample | When The Fire Nation Drill enters, you may tap it. When you do, destroy 
_h_the_fire_nation_drill = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [tla] Flying | When this creature enters, create a Clue token. (It's an artifact with "{
_h_messenger_hawk = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] When this enchantment enters, create a Clue token. (It's an artifact with "{2}, 
_h_tolls_of_war = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] Reach | When this creature enters, you may discard a card. If you do, draw a card.
_h_yuyan_archers = _etb([["draw", {"n": 1}]])
# [tla] When this creature enters, put a +1/+1 counter on target creature.
_h_jeong_jeong_s_deserters = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] When this Equipment enters, create a 1/1 white Ally creature token, then attach 
_h_kyoshi_battle_fan = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] When Iroh enters, create a Food token. | At the beginning of combat on your turn, 
_h_iroh__tea_master = _etb([["gain_life", {"n": 3}]])
# [tla] When this creature enters, earthbend 1, then earthbend 1. (To earthbend 1, targe
_h_dai_li_agents = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Haste | When this creature enters, create a 1/1 white Ally creature token.
_h_treetop_freedom_fighters = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Defender | When this creature enters, mill two cards. (Put the top two cards of yo
_h_platypus_bear = _etb([["mill", {"n": 2, "target": "self"}]])
# [tla] When this enchantment enters, create a Clue token. (It's an artifact with "{2}, 
_h_air_nomad_legacy = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] When this creature enters, create a Clue token. (It's an artifact with "{2}, Sac
_h_forecasting_fortune_teller = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] When Flopsie enters, put a +1/+1 counter on each creature you control. | Each crea
_h_flopsie__bumi_s_buddy = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_mongoose_lizard = _etb([["damage_any", {"n": 1}]])
# [tla] When this creature enters, create a 1/1 white Ally creature token.
_h_kyoshi_warriors = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] When The Spirit Oasis enters, draw a card for each Shrine you control. | Whenever 
_h_the_spirit_oasis = _etb([["draw", {"n": 1}]])
# [tla] Deathtouch | When this creature enters, create a Food token. (It's an artifact wit
_h_canyon_crawler = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [tla] When Kyoshi Island Plaza enters, search your library for up to X basic land card
_h_kyoshi_island_plaza = _etb([["search_basic_land", {"n": 1}]])
# [tla] When The Earth King enters, create a 4/4 green Bear creature token. | Whenever one
_h_the_earth_king = _etb([["create_token", {"count": 1, "power": "4", "toughness": "4", "keywords": []}]])
# [tla] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_unlucky_cabbage_merchant = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [tla] When this creature enters, earthbend 2. (Target land you control becomes a 0/0 c
_h_earth_kingdom_general = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] When this creature enters, target opponent discards a card.
_h_corrupt_court_official = _etb([["discard", {"n": 1, "target": "opp"}]])
# [tla] When Hama enters, target opponent mills three cards. Exile up to one noncreature
_h_hama__the_bloodbender = _etb([["mill", {"n": 3, "target": "self"}]])
# [tla] Flying | When this creature enters, scry 1. (Look at the top card of your library.
_h_glider_kids = _etb([["scry", {"n": 1}]])
# [tla] Vigilance, reach | When The Lion-Turtle enters, you gain 3 life. | The Lion-Turtle c
_h_the_lion_turtle = _etb([["gain_life", {"n": 3}]])
# [ecl] When this creature enters, create a 1/1 black and red Goblin creature token.
_h_elder_auntie = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] When this enchantment enters, exile up to one target nonland permanent an oppone
_h_liminal_hold = _etb([["gain_life", {"n": 2}]])
# [ecl] Changeling (This card is every creature type.) | When this creature enters, you ma
_h_graveshifter = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [ecl] When this creature enters, if you control three or more creatures, return target
_h_dundoolin_weaver = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [ecl] Changeling (This card is every creature type.) | Flying | When this creature enters,
_h_rooftop_percher = _etb([["gain_life", {"n": 3}]])
# [ecl] When this artifact enters, draw a card, then choose a color. This artifact becom
_h_puca_s_eye = _etb([["draw", {"n": 1}]])
# [ecl] When this enchantment enters, create two 1/1 green and white Kithkin creature to
_h_clachan_festival = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_dawnhand_eulogist = _etb([["mill", {"n": 3, "target": "self"}], ["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [ecl] When this creature enters, you may blight 2. If you do, create two 1/1 black and
_h_sourbread_auntie = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] When Lluwen enters, mill four cards, then you may put a creature or land card fr
_h_lluwen__imperfect_naturalist = _etb([["mill", {"n": 4, "target": "self"}]])
# [ecl] Changeling (This card is every creature type.) | When this creature enters, you ma
_h_changeling_wayfinder = _etb([["search_basic_land", {"n": 1}]])
# [ecl] This spell costs {1} less to cast if you control a Kithkin. | When this creature e
_h_mistmeadow_council = _etb([["draw", {"n": 1}]])
# [ecl] When this creature enters or dies, create a Treasure token. (It's an artifact wi
_h_noggle_robber = _etb([["create_treasure", {"n": 1}]])
# [ecl] When this enchantment enters, you may blight 1. If you do, create two 1/1 black 
_h_boggart_mischief = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Trample | When this creature enters, create a Treasure token. (It's an artifact wi
_h_flamekin_gildweaver = _etb([["create_treasure", {"n": 1}]])
# [ecl] Flying | When this creature enters, you may blight 1. If you do, each opponent dis
_h_dream_seizer = _etb([["discard", {"n": 1, "target": "opp"}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_merrow_skyswimmer = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Lifelink | When this creature enters, mill two cards. (Put the top two cards of yo
_h_scarblade_scout = _etb([["mill", {"n": 2, "target": "self"}]])
# [ecl] When this creature enters and whenever you cast a spell with mana value 4 or gre
_h_flaring_cinder = _etb([["draw", {"n": 1}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_lofty_dreams = _etb([["draw", {"n": 1}]])
# [ecl] Vigilance, reach | Ward {2} (Whenever this creature becomes the target of a spell 
_h_pummeler_for_hire = _etb([["gain_life", {"n": 1}]])
# [tmt] When this creature enters, you may search your library for a Food card, reveal i
_h_courier_of_comestibles = _etb([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [tmt] When this creature enters, create a 1/1 colorless Robot artifact creature token.
_h_mechanized_ninja_cavalry = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] Sneak {3}{W/B} (You may cast this spell for {3}{W/B} if you also return an unblo
_h_foot_ninjas = _etb([["gain_life", {"n": 3}]])
# [tmt] When April O'Neil enters, scry 2. (Look at the top two cards of your library, th
_h_april_o_neil__kunoichi_trainee = _etb([["scry", {"n": 2}]])
# [tmt] When this artifact enters or leaves the battlefield, create a 1/1 colorless Robo
_h_mouser_foundry = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] Flying | Whenever this creature attacks, Dinosaurs you control other than this cre
_h_triceraton_commander = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] Reach, trample | When this creature enters, you gain 2 life.
_h_primordial_pachyderm = _etb([["gain_life", {"n": 2}]])
# [tmt] When this artifact enters, destroy target creature. | {2}, {T}, Sacrifice this art
_h_anchovy___banana_pizza = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] Flying | When Ray Fillet enters, create a Mutagen token. (It's an artifact with "{
_h_ray_fillet__man_ray = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When this artifact enters, draw a card. | {1}, {T}, Sacrifice this artifact: Add o
_h_omni_cheese_pizza = _etb([["draw", {"n": 1}]])
# [tmt] (Gain the next level as a sorcery to add its ability.) | When this Class enters, e
_h_party_dude = _etb([["gain_life", {"n": 3}]])
# [tmt] Enchant basic land you control | When this Aura enters, exile target creature an o
_h_dimensional_exile = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [tmt] When this creature enters, mill three cards. (Put the top three cards of your li
_h_paramecia_coloniex = _etb([["mill", {"n": 3, "target": "self"}]])
# [tmt] When this artifact enters, it deals 4 damage to any target and 3 damage to you. | 
_h_spicy_oatmeal_pizza = _etb([["damage_any", {"n": 4}]])
# [tmt] When this artifact enters, search your library for a basic land card, reveal it,
_h_everything_pizza = _etb([["search_basic_land", {"n": 1}]])
# [tmt] Trample | When General Traag enters, you may sacrifice another artifact. When you 
_h_general_traag__heart_of_stone = _etb([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [tmt] When this creature enters, create a Mutagen token. (It's an artifact with "{1}, 
_h_crustacean_commando = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When Sally Pride enters, create X 2/2 red Mutant creature tokens, where X is the
_h_sally_pride__lioness_leader = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] When Jennika enters, create a 2/2 red Mutant creature token. | Plainscycling {2} (
_h_jennika__bad_apple_big_sister = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] Flying | When Stockman enters, draw a card, then discard a card. | Islandcycling {2}
_h_stockman__mad_fly_entist = _etb([["draw", {"n": 1}]])
# [tmt] Flying | When this Vehicle enters, create a 2/2 red Mutant creature token. | Crew 2 
_h_turtle_blimp = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] When Baxter Stockman enters, create a 1/1 colorless Robot artifact creature toke
_h_baxter_stockman = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] When Pizza Face enters, create a Food token. | Disappear ? At the beginning of you
_h_pizza_face__gastromancer = _etb([["gain_life", {"n": 3}]])
# [tmt] When this creature enters, return up to one other target artifact you control to
_h_nobody = _etb([["scry", {"n": 1}]])
# [tmt] When this creature enters, create a Mutagen token. (It's an artifact with "{1}, 
_h_slithering_cryptid = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When Donatello enters, if you control an artifact, draw a card.
_h_donatello__turtle_techie = _etb([["draw", {"n": 1}]])
# [tmt] When this creature enters, create a 2/2 red Mutant creature token. | Alliance ? Wh
_h_mighty_mutanimals = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] When this creature enters, you gain 1 life. | {2}{G}: This creature gets +2/+2 unt
_h_mindful_biomancer = _etb([["gain_life", {"n": 1}]])
# [sos] When this creature enters, create a 1/1 white and black Inkling creature token w
_h_eager_glyphmage = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [sos] Flying | When this creature enters, each opponent loses 2 life and you gain 2 life
_h_sneering_shadewriter = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [sos] When this enchantment enters, create a 2/2 red and white Spirit creature token. | 
_h_living_history = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] Flying | When Moseo enters, create a 1/1 black and green Pest creature token with 
_h_moseo__vein_s_new_dean = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}]])
# [sos] When this enchantment enters, create a 0/0 green and blue Fractal creature token
_h_additive_evolution = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] When this creature enters, create a 1/1 black and green Pest creature token with
_h_essenceknit_scholar = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}]])
# [sos] Flying | When this Vehicle enters, you may search your library for a basic land ca
_h_strixhaven_skycoach = _etb([["search_basic_land", {"n": 1}]])
# [sos] When this creature enters, you may discard a card. If you do, draw a card. | {T}, 
_h_rubble_rouser = _etb([["draw", {"n": 1}]])

# [woe] You may discard a card. If you do, draw two cards. | Create a Wicked Role token at
_h_witch_s_mark = _spell([["draw", {"n": 2}], ["lose_life", {"n": 1, "target": "opp"}]])
# [woe] Creatures you control get +2/+0 until end of turn. Whenever a nontoken creature 
_h_gnawing_crescendo = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_stonesplitter_bolt = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [woe] This spell costs {1} less to cast for each creature that attacked this turn. | Dra
_h_rowdy_research = _spell([["draw", {"n": 3}]])
# [woe] Destroy target creature with mana value 3 or less. If it's your turn, create a F
_h_feed_the_cauldron = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] Target opponent discards two cards. Create a Wicked Role token attached to up to
_h_eriette_s_whisper = _spell([["lose_life", {"n": 1, "target": "opp"}], ["discard", {"n": 2, "target": "opp"}]])
# [woe] Up to one target creature gets -1/-1 until end of turn. You create a 1/1 black R
_h_rat_out = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [woe] Destroy up to one target artifact, enchantment, or creature with flying. Create 
_h_spider_food = _spell([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] Return all creatures to their owners' hands. For each opponent who controlled a 
_h_faerie_slumber_party = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["flying", "\"This token can block only creatures with flying"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_brave_the_wilds = _spell([["search_basic_land", {"n": 1}]])
# [woe] Choose two ? | ? Search your library for a basic land card, put it onto the battle
_h_return_from_the_wilds = _spell([["search_basic_land", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [woe] Target creature gets +3/+0 until end of turn. | Draw a card.
_h_sugar_rush = _spell([["draw", {"n": 1}]])
# [woe] Tap target creature an opponent controls and put three stun counters on it. Scry
_h_freeze_in_place = _spell([["scry", {"n": 2}]])
# [woe] Draw three cards. Create a 1/1 blue Faerie creature token with flying and "This 
_h_into_the_fae_court = _spell([["draw", {"n": 3}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying", "\"This token can block only creatures with flying"]}]])
# [woe] Flick a Coin deals 1 damage to any target. You create a Treasure token. (It's an
_h_flick_a_coin = _spell([["damage_any", {"n": 1}], ["create_treasure", {"n": 1}], ["draw", {"n": 1}]])
# [woe] Cut In deals 4 damage to target creature. | Create a Young Hero Role token attache
_h_cut_in = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["add_counters", {"n": 1, "target": "self"}]])
# [woe] Tap up to one target creature. Scry 1, then draw a card.
_h_plunge_into_winter = _spell([["draw", {"n": 1}], ["scry", {"n": 1}]])
# [woe] Return target creature card with mana value 3 or less from your graveyard to the
_h_return_triumphant = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [woe] Destroy target enchantment. If a permanent you controlled or a token was destroy
_h_break_the_spell = _spell([["draw", {"n": 1}]])
# [woe] Choose one ? | ? Untap target creature. It gets +1/+0 and gains indestructible unt
_h_moment_of_valor = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [woe] Target creature gets +1/+0 and gains first strike until end of turn. Scry 1.
_h_kindled_heroism = _spell([["scry", {"n": 1}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_johann_s_stopgap = _spell([["bounce_to_hand", {}], ["draw", {"n": 1}]])
# [woe] Exile target creature. If you control an enchantment, scry 2.
_h_taken_by_nightmares = _spell([["exile", {"target": "opp_biggest_creature"}], ["scry", {"n": 2}]])
# [woe] Frantic Firebolt deals X damage to target creature, where X is 2 plus the number
_h_frantic_firebolt = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [woe] Destroy target creature or enchantment. Create a Wicked Role token attached to u
_h_shatter_the_oath = _spell([["destroy", {"target": "opp_biggest_creature"}], ["lose_life", {"n": 1, "target": "opp"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_rowan_s_grim_search = _spell([["draw", {"n": 2}]])
# [lci] This spell costs {3} less to cast if it targets a tapped creature. | Exile target 
_h_quicksand_whirlpool = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [lci] Choose target creature you control and target creature you don't control. If the
_h_malamet_battle_glyph = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Return target creature to its owner's hand. If it was tapped, create a Map token
_h_brackish_blunder = _spell([["bounce_to_hand", {}]])
# [lci] Calamitous Cave-In deals X damage to each creature and each planeswalker, where 
_h_calamitous_cave_in = _spell([["damage_creature", {"n": 1, "target": "each_opp"}]])
# [lci] Target creature gets +2/+0 and gains first strike until end of turn. | Create a Tr
_h_ancestors__aid = _spell([["create_treasure", {"n": 1}]])
# [lci] Return target creature card from your graveyard to the battlefield. That creatur
_h_defossilize = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [lci] Draw three cards, then discard a card.
_h_ancestral_reminiscence = _spell([["draw", {"n": 3}]])
# [lci] You may mill two cards. Then return up to two creature cards from your graveyard
_h_another_chance = _spell([["mill", {"n": 2, "target": "self"}]])
# [lci] Exile target creature, Vehicle, or nonbasic land. Scry 1. (Look at the top card 
_h_ray_of_ruin = _spell([["exile", {"target": "opp_biggest_creature"}], ["scry", {"n": 1}]])
# [mkm] Each player who controls the most creatures investigates. Then destroy all creat
_h_no_witnesses = _spell([["destroy_all_creatures", {}], ["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Create a 2/2 white and blue Detective creature token. If a creature died this tu
_h_drag_the_canal = _spell([["draw", {"n": 1}], ["gain_life", {"n": 2}], ["draw", {"n": 1}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] Target creature gains deathtouch and lifelink until end of turn. Investigate. (C
_h_toxin_analysis = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Search your library for a basic land card, put it onto the battlefield tapped, t
_h_they_went_this_way = _spell([["draw", {"n": 1}], ["draw", {"n": 1}], ["search_basic_land", {"n": 1}]])
# [mkm] As an additional cost to cast this spell, sacrifice a creature that dealt damage
_h_treacherous_greed = _spell([["draw", {"n": 3}], ["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [mkm] Target opponent reveals their hand. You choose a nonland card from it. Exile tha
_h_soul_search = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [mkm] Target creature gets +3/+0 and gains first strike until end of turn. Investigate
_h_the_chase_is_on = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] This spell costs {3} less to cast if you've sacrificed an artifact this turn. | Th
_h_suspicious_detonation = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [mkm] Galvanize deals 3 damage to target creature. If you've drawn two or more cards t
_h_galvanize = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [mkm] Target creature gets +2/+2 until end of turn. Investigate. (Create a Clue token.
_h_auspicious_arrival = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Create a 0/0 green Ooze creature token with trample. Put X +1/+1 counters on it,
_h_slime_against_humanity = _spell([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": ["trample"]}]])
# [mkm] Choose one or both ? | ? Destroy target creature. | ? Put a +1/+1 counter on target 
_h_deadly_complication = _spell([["destroy", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [mkm] Investigate. Creatures your opponents control get -2/-0 until end of turn. If an
_h_eliminate_the_impossible = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Create a 0/1 green Plant creature token, then draw cards equal to the number of 
_h_audience_with_trostani = _spell([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [mkm] Return target creature card from your graveyard to the battlefield. Suspect it. 
_h_it_doesn_t_add_up = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [mkm] Creatures you control get +2/+1 until end of turn. Investigate. (Create a Clue t
_h_on_the_job = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] Reveal the top five cards of your library and separate them into two piles. An o
_h_intrude_on_the_mind = _spell([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": ["flying", "then put a +1/+1 counter on it for each card put into your graveyard this way"]}]])
# [otj] Spree (Choose one or more additional costs.) | + {2}{B} ? Destroy target creature.
_h_unfortunate_accident = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] Search your library for up to two basic land cards and/or Desert cards, put them
_h_map_the_frontier = _spell([["search_basic_land", {"n": 2}]])
# [otj] Target creature gets -1/-0 until end of turn. It gets -4/-0 until end of turn in
_h_take_the_fall = _spell([["draw", {"n": 1}]])
# [otj] Create a Treasure token. Until end of turn, up to one target creature gets +2/+2
_h_gold_rush = _spell([["create_treasure", {"n": 1}]])
# [otj] Each player may shuffle their hand and graveyard into their library. Each player
_h_step_between_worlds = _spell([["draw", {"n": 7}]])
# [otj] Spree (Choose one or more additional costs.) | + {2} ? Return target creature card
_h_one_last_job = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [otj] Return up to one target creature card from your graveyard to your hand. Create a
_h_mourner_s_surprise = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Until end of turn, target c
_h_metamorphic_blast = _spell([["draw", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Search your library for a b
_h_dance_of_the_tumbleweeds = _spell([["search_basic_land", {"n": 1}]])
# [otj] Hell to Pay deals X damage to target creature. Create a number of tapped Treasur
_h_hell_to_pay = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [otj] Trick Shot deals 6 damage to target creature and 2 damage to up to one other tar
_h_trick_shot = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [otj] Create X 1/1 red Mercenary creature tokens with "{T}: Target creature you contro
_h_form_a_posse = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Exile target nontoken creat
_h_getaway_glamer = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [otj] Exile target creature. If it had mana value 3 or less, surveil 2. (Look at the t
_h_consuming_ashes = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [otj] Surveil 3 if you have no cards in hand. Then draw three cards. (To surveil 3, lo
_h_plan_the_heist = _spell([["draw", {"n": 3}]])
# [otj] Spree (Choose one or more additional costs.) | + {2}{R} ? Untap all creatures you 
_h_great_train_heist = _spell([["damage_player", {"n": 1, "target": "opp"}]])
# [otj] Destroy target tapped creature. You gain 2 life.
_h_eriette_s_lullaby = _spell([["gain_life", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {2} ? Explosive Derailment deals 
_h_explosive_derailment = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [otj] As an additional cost to cast this spell, sacrifice a creature. | Draw two cards.
_h_corrupted_conviction = _spell([["draw", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {2} ? Put two +1/+1 counters on t
_h_trash_the_town = _spell([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {3} ? Put a +1/+1 counter on targ
_h_jailbreak_scheme = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Thunder Salvo deals X damage to target creature, where X is 2 plus the number of
_h_thunder_salvo = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [otj] Target creature you control gets +1/+1 until end of turn. Put a +1/+1 counter on
_h_throw_from_the_saddle = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Create X 2/1 green Varmint creature tokens, where X is the number of creature ca
_h_rise_of_the_varmints = _spell([["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": []}]])
# [otj] This spell costs {1} less to cast if you've committed a crime this turn. (Target
_h_seize_the_secrets = _spell([["draw", {"n": 2}]])
# [otj] You may discard a card or sacrifice a land. If you do, draw two cards. | Plot {1}{
_h_highway_robbery = _spell([["draw", {"n": 2}]])
# [otj] Put a +1/+1 counter on target creature. It gains lifelink and indestructible unt
_h_take_up_the_shield = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Return target nonland permanent to its owner's hand. If you control a Desert, su
_h_failed_fording = _spell([["bounce_to_hand", {}]])
# [blb] Conduct Electricity deals 6 damage to target creature and 2 damage to up to one 
_h_conduct_electricity = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [blb] Gift a tapped Fish (You may promise an opponent a gift as you cast this spell. I
_h_mind_spiral = _spell([["draw", {"n": 3}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_wildfire_howl = _spell([["draw", {"n": 1}], ["damage_any", {"n": 1}], ["damage_creature", {"n": 2, "target": "each_opp"}]])
# [blb] Playful Shove deals 1 damage to any target. | Draw a card.
_h_playful_shove = _spell([["damage_any", {"n": 1}], ["draw", {"n": 1}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_coiling_rebirth = _spell([["draw", {"n": 1}], ["return_gy_to_bf", {"filter_type": "creature"}]])
# [blb] Return up to two target creature cards from your graveyard to your hand. Each op
_h_hazel_s_nocturne = _spell([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [blb] Draw X cards.
_h_mind_spring = _spell([["draw", {"n": 1}]])
# [blb] Target opponent discards two cards. Then if you control a Rat, surveil 2. (Look 
_h_psychic_whorl = _spell([["discard", {"n": 2, "target": "opp"}]])
# [blb] Create a 1/1 blue and red Otter creature token with prowess. If this spell was c
_h_otterball_antics = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["prowess"]}]])
# [blb] Gift a Food (You may promise an opponent a gift as you cast this spell. If you d
_h_valley_rally = _spell([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_starfall_invocation = _spell([["draw", {"n": 1}], ["destroy_all_creatures", {}]])
# [blb] Choose one ? | ? Agate Assault deals 4 damage to target creature. If that creature
_h_agate_assault = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [blb] Choose one ? | ? Counter target spell. | ? Surveil 2, then draw two cards. (To surve
_h_spellgyre = _spell([["draw", {"n": 2}]])
# [blb] This spell costs {1} less to cast if you control an Otter. | Draw two cards.
_h_pearl_of_wisdom = _spell([["draw", {"n": 2}]])
# [blb] Gift a Food (You may promise an opponent a gift as you cast this spell. If you d
_h_crumb_and_get_it = _spell([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_peerless_recycling = _spell([["draw", {"n": 1}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [blb] Creatures you control get +2/+1 until end of turn. If you control a Rabbit, scry
_h_rabbit_response = _spell([["scry", {"n": 2}]])
# [blb] Surveil 2, then draw two cards. You lose 2 life. (To surveil 2, look at the top 
_h_diresight = _spell([["draw", {"n": 2}]])
# [blb] Target opponent exiles a card from their hand. If this spell was cast from a gra
_h_ruthless_negotiation = _spell([["draw", {"n": 1}]])
# [blb] Gift a tapped Fish (You may promise an opponent a gift as you cast this spell. I
_h_sazacap_s_brew = _spell([["draw", {"n": 2}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_consumed_by_greed = _spell([["draw", {"n": 1}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [blb] Destroy target creature with power or toughness 4 or greater.
_h_repel_calamity = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [blb] Flame Lash deals 4 damage to any target.
_h_flame_lash = _spell([["damage_any", {"n": 4}]])
# [blb] Return up to two target creatures to their owners' hands. Draw two cards, then d
_h_calamitous_tide = _spell([["draw", {"n": 2}]])
# [blb] Sonar Strike deals 4 damage to target attacking, blocking, or tapped creature. Y
_h_sonar_strike = _spell([["gain_life", {"n": 3}]])
# [blb] Create X tokens that are copies of target token you control. Then tokens you con
_h_for_the_common_good = _spell([["gain_life", {"n": 1}]])
# [blb] Target creature gets -2/-2 until end of turn. Create a Food token. (It's an arti
_h_savor = _spell([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [blb] Take Out the Trash deals 3 damage to target creature or planeswalker. If you con
_h_take_out_the_trash = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [blb] Create three 1/1 white Rabbit creature tokens.
_h_hop_to_it = _spell([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [blb] Gift a Food (You may promise an opponent a gift as you cast this spell. If you d
_h_nocturnal_hunger = _spell([["gain_life", {"n": 3}], ["gain_life", {"n": 3}], ["destroy", {"target": "opp_biggest_creature"}]])
# [blb] Choose one ? | ? Exile target creature. | ? Target opponent exiles an enchantment th
_h_early_winter = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [dsk] Look at the top four cards of your library. Put one of them into your hand and t
_h_commune_with_evil = _spell([["gain_life", {"n": 3}]])
# [dsk] Destroy target creature. If a creature card is put into a graveyard this way, re
_h_come_back_wrong = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Create three 1/1 red Gremlin creature tokens. Gremlins you control gain menace, 
_h_midnight_mayhem = _spell([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Target creature can't be blocked this turn. | Draw a card.
_h_enter_the_enigma = _spell([["draw", {"n": 1}]])
# [dsk] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_seized_from_slumber = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Discard your hand. Then draw X cards, where X is the number of card types among 
_h_peer_past_the_veil = _spell([["draw", {"n": 1}]])
# [dsk] Destroy target creature. Its controller manifests dread. (That player looks at t
_h_unwanted_remake = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Winter's Intervention deals 2 damage to target creature. You gain 2 life.
_h_winter_s_intervention = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}], ["gain_life", {"n": 2}]])
# [dsk] Destroy target creature.
_h_murder = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Draw two cards. Create a 1/1 white Glimmer enchantment creature token.
_h_glimmerburst = _spell([["draw", {"n": 2}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Return target creature card from your graveyard to the battlefield with a finali
_h_rite_of_the_moth = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [dsk] Choose one ? | ? Return target creature card from your graveyard to the battlefiel
_h_live_or_die = _spell([["return_gy_to_bf", {"filter_type": "creature"}], ["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Delirium ? Choose one. If there are four or more card types among cards in your 
_h_let_s_play_a_game = _spell([["discard", {"n": 2, "target": "opp"}], ["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [dsk] Delirium ? This spell costs {2} less to cast as long as there are four or more c
_h_drag_to_the_roots = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Impossible Inferno deals 6 damage to target creature. | Delirium ? If there are fo
_h_impossible_inferno = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [dsk] Return target creature card from your graveyard to the battlefield. You gain 3 l
_h_emerge_from_the_cocoon = _spell([["gain_life", {"n": 3}], ["return_gy_to_bf", {"filter_type": "creature"}]])
# [fdn] Destroy target creature or planeswalker.
_h_hero_s_downfall = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Return target creature card from your graveyard to your hand. If it's a Zombie c
_h_cemetery_recruitment = _spell([["draw", {"n": 1}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Destroy target creature. Create a Food token. (It's an artifact with "{2}, {T}, 
_h_bake_into_a_pie = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [fdn] As an additional cost to cast this spell, discard a card. | Draw two cards.
_h_thrill_of_possibility = _spell([["draw", {"n": 2}]])
# [fdn] Counter target noncreature spell. Its controller creates two Treasure tokens. (T
_h_an_offer_you_can_t_refuse = _spell([["create_treasure", {"n": 1}]])
# [fdn] Search your library for up to two basic land cards and/or Gate cards, put them o
_h_circuitous_route = _spell([["search_basic_land", {"n": 2}]])
# [fdn] Seismic Rupture deals 2 damage to each creature without flying.
_h_seismic_rupture = _spell([["damage_creature", {"n": 2, "target": "each_opp"}]])
# [fdn] Incinerating Blast deals 6 damage to target creature. | You may discard a card. If
_h_incinerating_blast = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [fdn] Draw a card for each different mana value among nonland permanents you control.
_h_lunar_insight = _spell([["draw", {"n": 1}]])
# [fdn] Choose one ? | ? Destroy target creature or planeswalker. | ? Return target Zombie c
_h_deadly_plot = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Put a +1/+1 counter on target creature. It gains flying until end of turn. Preve
_h_fleeting_flight = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] For each land you control, create a Treasure token. (It's an artifact with "{T},
_h_brass_s_bounty = _spell([["create_treasure", {"n": 1}]])
# [fdn] Each player mills X cards. For each creature card put into a graveyard this way,
_h_dread_summons = _spell([["mill", {"n": 1, "target": "self"}]])
# [fdn] Kicker {2} (You may pay an additional {2} as you cast this spell.) | Search your l
_h_grow_from_the_ashes = _spell([["search_basic_land", {"n": 1}]])
# [fdn] Draw X cards. If X is 10 or more, instead shuffle your graveyard into your libra
_h_finale_of_revelation = _spell([["draw", {"n": 1}]])
# [fdn] Goblin Negotiation deals X damage to target creature. Create a number of 1/1 red
_h_goblin_negotiation = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [fdn] Choose one ? | ? Creatures you control get +2/+0 until end of turn. | ? Create two 1
_h_goblin_surprise = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] Gain control of target creature until end of turn. Untap that creature. It gains
_h_involuntary_employment = _spell([["create_treasure", {"n": 1}]])
# [fdn] Each opponent loses X life. You gain life equal to the life lost this way.
_h_exsanguinate = _spell([["lose_life", {"n": 1, "target": "opp"}]])
# [fdn] Draw a card for each creature you control with a +1/+1 counter on it. Those crea
_h_inspiring_call = _spell([["draw", {"n": 1}]])
# [fdn] Until end of turn, target creature gets +2/+0 and gains "When this creature dies
_h_fake_your_own_death = _spell([["create_treasure", {"n": 1}]])
# [fdn] Target creature gets -1/-0 until end of turn. | Draw a card.
_h_fleeting_distraction = _spell([["draw", {"n": 1}]])
# [fdn] Mill three cards, then return an instant or sorcery card from your graveyard to 
_h_inspiration_from_beyond = _spell([["mill", {"n": 3, "target": "self"}]])
# [fdn] Create two 1/1 white Soldier creature tokens. Until end of turn, creatures you c
_h_heroic_reinforcements = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] Create two 1/1 red Goblin creature tokens.
_h_dragon_fodder = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_luminous_rebuke = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Deadly Riposte deals 3 damage to target tapped creature and you gain 2 life.
_h_deadly_riposte = _spell([["gain_life", {"n": 2}]])
# [fdn] Destroy target creature or enchantment.
_h_mortify = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Put a +1/+1 counter on target creature you control. Then that creature deals dam
_h_felling_blow = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] This spell costs {1} less to cast if you control a Wizard. | Draw three cards.
_h_arcane_epiphany = _spell([["draw", {"n": 3}]])
# [dft] Destroy target creature with toughness 4 or greater. | Cycling {2} ({2}, Discard t
_h_gallant_strike = _spell([["destroy", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}]])
# [dft] Choose one ? | ? Destroy target Vehicle. | ? Crash and Burn deals 6 damage to target
_h_crash_and_burn = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [dft] Affinity for artifacts (This spell costs {1} less to cast for each artifact you 
_h_voyage_home = _spell([["draw", {"n": 3}]])
# [dft] Choose target opponent. Create two 1/1 colorless Thopter artifact creature token
_h_haunt_the_network = _spell([["gain_life", {"n": 1}], ["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [dft] Target creature gets -6/-6 until end of turn. You gain 2 life.
_h_syphon_fuel = _spell([["gain_life", {"n": 2}]])
# [dft] All creatures and Vehicles lose indestructible until end of turn, then destroy a
_h_spectacular_pileup = _spell([["destroy_all_creatures", {}], ["draw", {"n": 1}]])
# [dft] Draw two cards. Each player loses 2 life.
_h_risky_shortcut = _spell([["draw", {"n": 2}]])
# [dft] Return target creature or Vehicle card from your graveyard to the battlefield. C
_h_back_on_track = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token saddles Mounts", "crews Vehicles as though its power were 2 greater"]}]])
# [dft] Target nonland permanent's owner puts it on their choice of the top or bottom of
_h_trip_up = _spell([["draw", {"n": 1}]])
# [dft] Destroy target creature or Vehicle.
_h_spin_out = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dft] Exchange control of target artifact or creature you control and target artifact 
_h_trade_the_helm = _spell([["draw", {"n": 1}]])
# [dft] Exile up to one target artifact or creature. Return it to the battlefield under 
_h_explosive_getaway = _spell([["damage_creature", {"n": 4, "target": "each_opp"}]])
# [dft] Tap target creature or Vehicle, then put three stun counters on it. (If a perman
_h_stall_out = _spell([["draw", {"n": 1}]])
# [dft] As an additional cost to cast this spell, sacrifice an artifact or creature. | Des
_h_hellish_sideswipe = _spell([["destroy", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}]])
# [dft] Road Rage deals X damage to target creature or planeswalker, where X is 2 plus t
_h_road_rage = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [dft] Target creature gets +2/+2 until end of turn. | Cycling {2} ({2}, Discard this car
_h_lightshield_parry = _spell([["draw", {"n": 1}]])
# [dft] Put a +1/+1 counter on target creature. It gains deathtouch and indestructible u
_h_maximum_overdrive = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [dft] Target creature gets -1/-1 until end of turn. | Cycling {B} ({B}, Discard this car
_h_locust_spray = _spell([["draw", {"n": 1}]])
# [tdm] As an additional cost to cast this spell, sacrifice a creature. | Exile target cre
_h_worthy_cost = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [tdm] Exile target permanent with mana value 3 or greater.
_h_kin_tree_severance = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [tdm] Narset's Rebuke deals 5 damage to target creature. Add {U}{R}{W}. If that creatu
_h_narset_s_rebuke = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [tdm] Surveil 2, then draw two cards. You lose 2 life. (To surveil 2, look at the top 
_h_cruel_truths = _spell([["draw", {"n": 2}]])
# [tdm] This spell costs {2} less to cast if you've cast another spell this turn. | Choose
_h_rally_the_monastery = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["prowess"]}], ["destroy", {"target": "opp_biggest_creature"}]])
# [tdm] Return target creature card from your graveyard to your hand. Lie in Wait deals 
_h_lie_in_wait = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [tdm] Target creature gets +3/+0 until end of turn. | Draw a card.
_h_rebellious_strike = _spell([["draw", {"n": 1}]])
# [tdm] Destroy all creatures and enchantments. Draw a card for each permanent destroyed
_h_death_begets_life = _spell([["destroy_all_creatures", {}], ["draw", {"n": 1}]])
# [tdm] Defibrillating Current deals 4 damage to target creature or planeswalker and you
_h_defibrillating_current = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["gain_life", {"n": 2}]])
# [tdm] Put a +1/+1 counter on target creature. It gains flying and indestructible until
_h_lightfoot_technique = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] As an additional cost to cast this spell, sacrifice a creature. | Creatures you co
_h_duty_beyond_death = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] This spell costs {2} less to cast if you've cast another spell this turn. | Draw t
_h_focus_the_mind = _spell([["draw", {"n": 3}]])
# [tdm] Create a 5/5 green Elephant creature token. | Harmonize {5}{G}{U}{R} (You may cast
_h_mammoth_bellow = _spell([["create_token", {"count": 1, "power": "5", "toughness": "5", "keywords": []}]])
# [tdm] Put a +1/+1 counter on target creature you control, then it deals damage equal t
_h_knockout_maneuver = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Draw three cards. Creatures your opponents control get -3/-0 until end of turn.
_h_bewildering_blizzard = _spell([["draw", {"n": 3}]])
# [tdm] This spell costs {2} more to cast if it targets a Dragon. | Destroy target creatur
_h_dragon_s_prey = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [tdm] Return target creature to its owner's hand. | Harmonize {5}{U} (You may cast this 
_h_ureni_s_rebuff = _spell([["bounce_to_hand", {}]])
# [tdm] Draw a card. | Harmonize {5}{U} (You may cast this card from your graveyard for it
_h_unending_whisper = _spell([["draw", {"n": 1}]])
# [tdm] Search your library for a basic land card, put it onto the battlefield tapped, t
_h_roamer_s_routine = _spell([["search_basic_land", {"n": 1}]])
# [tdm] Destroy target creature. Create two 1/1 red Warrior creature tokens. They gain h
_h_salt_road_skirmish = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] This spell costs {2} less to cast if it targets a tapped creature. | Destroy targe
_h_fate_of_the_sun_cryst = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fin] Search your library for up to two basic land cards and/or Town cards with differ
_h_reach_the_horizon = _spell([["search_basic_land", {"n": 2}]])
# [fin] Choose one ? | ? Take the Elevator ? Create three 1/1 colorless Hero creature toke
_h_aerith_rescue_mission = _spell([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Return target creature card from your graveyard to the battlefield with two addi
_h_evil_reawakened = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [fin] Target player draws two cards. Put a +1/+1 counter on up to one target creature 
_h_combat_tutorial = _spell([["draw", {"n": 2}]])
# [fin] You draw two cards and you lose 2 life. Create a 0/1 black Wizard creature token
_h_circle_of_power = _spell([["damage_player", {"n": 1, "target": "opp"}], ["draw", {"n": 2}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": ["\"Whenever you cast a noncreature spell", "this token deals 1 damage to each opponent"]}]])
# [fin] Destroy target creature an opponent controls. Then draw a card for each creature
_h_deadly_embrace = _spell([["destroy", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}]])
# [fin] As an additional cost to cast this spell, discard a card. | Draw two cards. | Flashb
_h_laughing_mad = _spell([["draw", {"n": 2}]])
# [fin] Affinity for Towns (This spell costs {1} less to cast for each Town you control.
_h_travel_the_overworld = _spell([["draw", {"n": 4}]])
# [fin] Target opponent sacrifices a creature of their choice. | Create a 0/1 black Wizard
_h_cornered_by_black_mages = _spell([["damage_player", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": ["\"Whenever you cast a noncreature spell", "this token deals 1 damage to each opponent"]}]])
# [fin] Tiered (Choose one additional cost.) | ? Blizzard ? {0} ? Return target creature t
_h_ice_magic = _spell([["bounce_to_hand", {}]])
# [fin] Light of Judgment deals 6 damage to target creature. Destroy up to one Equipment
_h_light_of_judgment = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [fin] Destroy target creature. You gain 2 life.
_h_sephiroth_s_intervention = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 2}]])
# [fin] For each creature you control, create a 1/2 white Moogle creature token with lif
_h_moogles__valor = _spell([["create_token", {"count": 1, "power": "1", "toughness": "2", "keywords": ["lifelink"]}]])
# [fin] This spell can't be countered. | Return target nonland permanent to its owner's ha
_h_eject = _spell([["bounce_to_hand", {}], ["draw", {"n": 1}]])
# [fin] Search your library for a Mountain card, reveal it, put it into your hand, then 
_h_call_the_mountain_chocobo = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["\"Whenever a land you control enters", "this token gets +1/+0 until end of turn"]}]])
# [fin] Judgment Bolt deals 5 damage to target creature and X damage to that creature's 
_h_judgment_bolt = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [fin] Search your library for a basic land card or Town card, put it onto the battlefi
_h_prishe_s_wanderings = _spell([["add_counters", {"n": 1, "target": "self"}], ["search_basic_land", {"n": 1}]])
# [fin] Create four 1/1 colorless Hero creature tokens. Then put a +1/+1 counter on each
_h_the_crystal_s_chosen = _spell([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 4, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Create a 2/2 green Bird creature token with "Whenever a land you control enters,
_h_gysahl_greens = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["\"Whenever a land you control enters", "this token gets +1/+0 until end of turn"]}]])
# [eoe] As an additional cost to cast this spell, sacrifice an artifact or creature. | Des
_h_embrace_oblivion = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Create a Lander token. Then you may sacrifice an artifact. When you do, Lithobra
_h_lithobraking = _spell([["damage_creature", {"n": 2, "target": "each_opp"}], ["search_basic_land", {"n": 1}]])
# [eoe] Exile target creature or Spacecraft.
_h_gravkill = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [eoe] Destroy target artifact or tapped creature. You gain 3 life.
_h_radiant_strike = _spell([["gain_life", {"n": 3}]])
# [eoe] Put a +1/+1 counter on target creature you control. It gains reach, trample, and
_h_biosynthic_burst = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] You draw two cards and lose 2 life. | Void ? If a nonland permanent left the battl
_h_decode_transmissions = _spell([["draw", {"n": 2}], ["draw", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [eoe] This spell costs {1} less to cast during your turn. | Tap target artifact or creat
_h_mental_modulation = _spell([["draw", {"n": 1}]])
# [eoe] Invasive Maneuvers deals 3 damage to target creature. It deals 5 damage instead 
_h_invasive_maneuvers = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [eoe] Orbital Plunge deals 6 damage to target creature. If excess damage was dealt thi
_h_orbital_plunge = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}], ["search_basic_land", {"n": 1}]])
# [eoe] You gain 2 life. Create a Lander token. (It's an artifact with "{2}, {T}, Sacrif
_h_sami_s_curiosity = _spell([["gain_life", {"n": 2}], ["search_basic_land", {"n": 1}]])
# [eoe] As an additional cost to cast this spell, sacrifice an artifact or creature. | Ret
_h_scrounge_for_eternity = _spell([["search_basic_land", {"n": 1}]])
# [eoe] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_vote_out = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Target creature you control gains double strike until end of turn. If it has a +
_h_dual_sun_technique = _spell([["draw", {"n": 1}]])
# [eoe] Surveil 1, then you draw a card and lose 1 life. (To surveil 1, look at the top 
_h_hymn_of_the_faller = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [eoe] Bombard deals 4 damage to target creature.
_h_bombard = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [eoe] Surveil X, where X is the number of artifacts you control. Then draw three cards
_h_cerebral_download = _spell([["draw", {"n": 3}]])
# [spm] Surveil 2, then draw two cards. You lose 2 life. (To surveil 2, look at the top 
_h_risky_research = _spell([["draw", {"n": 2}]])
# [spm] This spell costs {2} less to cast if you control a Villain. | Destroy target creat
_h_venom_s_hunger = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 2}]])
# [spm] Kicker {1}{U} (You may pay an additional {1}{U} as you cast this spell.) | Return 
_h_whoosh_ = _spell([["bounce_to_hand", {}], ["draw", {"n": 1}]])
# [spm] Return target creature card from your graveyard to the battlefield with an addit
_h_prison_break = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [spm] Choose one ? | ? Do Homework ? Draw three cards. | ? Fight Crime ? Counter target sp
_h_school_daze = _spell([["draw", {"n": 3}], ["draw", {"n": 1}]])
# [spm] Put a +1/+1 counter on target creature you control. It fights target creature an
_h_kapow_ = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [spm] Choose one ? | ? Look Around ? Mill three cards. You may put a permanent card from
_h_scout_the_city = _spell([["mill", {"n": 3, "target": "self"}], ["gain_life", {"n": 3}], ["destroy", {"target": "opp_biggest_creature"}]])
# [spm] Target creature gets +2/+2 and gains flying until end of turn. If it's a Spider,
_h_thwip_ = _spell([["gain_life", {"n": 2}]])
# [tla] Create two 2/2 red Soldier creature tokens with firebending 1. (Whenever a creat
_h_fire_nation_attacks = _spell([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": ["firebending 1"]}]])
# [tla] The owner of target creature or enchantment puts it into their library second fr
_h_lost_days = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] Draw three cards. Then discard a card unless you waterbend {2}. (While paying a 
_h_waterbending_lesson = _spell([["draw", {"n": 3}]])
# [tla] Choose one ? | ? Target opponent reveals their hand. You choose a nonland permanen
_h_dai_li_indoctrination = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Kicker {3} (You may pay an additional {3} as you cast this spell.) | Target creatu
_h_jet_s_brainwashing = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] Exile target artifact, creature, or enchantment. Its controller creates a Clue t
_h_zuko_s_exile = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] As an additional cost to cast this spell, you may waterbend {6}. (While paying a
_h_spirit_water_revival = _spell([["draw", {"n": 2}]])
# [tla] Exile target creature. If it was dealt damage this turn, create a Clue token. (I
_h_sold_out = _spell([["exile", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] Sacrifice a land. Search your library for up to two basic land cards, put them o
_h_cycle_of_renewal = _spell([["search_basic_land", {"n": 2}]])
# [tla] As an additional cost to cast this spell, you may waterbend {4}. (While paying a
_h_ruinous_waterbending = _spell([["gain_life", {"n": 1}]])
# [tla] Counter target spell. | Draw a card, then mill three cards. | Untap target land.
_h_sokka_s_haiku = _spell([["draw", {"n": 1}], ["mill", {"n": 3, "target": "self"}]])
# [tla] Target creature gets +3/+1 until end of turn. | Create a Clue token. (It's an arti
_h_cunning_maneuver = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] Ozai's Cruelty deals 2 damage to target player. That player discards two cards.
_h_ozai_s_cruelty = _spell([["damage_player", {"n": 2, "target": "opp"}]])
# [tla] Create X 1/1 white Ally creature tokens, then put a +1/+1 counter on each creatu
_h_united_front = _spell([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Lands you control gain all basic land types until end of turn. | Draw a card.
_h_energybending = _spell([["draw", {"n": 1}]])
# [tla] As an additional cost to cast this spell, pay {4} or sacrifice an artifact or cr
_h_deadly_precision = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [tla] Create a 1/1 white Ally creature token for each Plains you control. Scry 2. (Loo
_h_gather_the_white_lotus = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["scry", {"n": 2}]])
# [tla] Kicker {2} (You may pay an additional {2} as you cast this spell.) | Search your l
_h_aang_s_journey = _spell([["search_basic_land", {"n": 1}], ["gain_life", {"n": 2}]])
# [tla] Choose one ? | ? Destroy target creature with power 4 or greater. | ? Earthbend 3. (
_h_sandbenders__storm = _spell([["destroy", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [tla] Airbend target nonland permanent. (Exile it. While it's exiled, its owner may ca
_h_airbending_lesson = _spell([["draw", {"n": 1}]])
# [tla] Exile target creature with mana value 3 or greater.
_h_epic_downfall = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [tla] Kicker {4} (You may pay an additional {4} as you cast this spell.) | Return target
_h_zuko_s_conviction = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [tla] Earthbend 2. When you do, up to one target creature you control fights target cr
_h_earth_rumble = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Choose one or both ? | ? Target creature gets -1/-1 until end of turn. | ? Put a +1/
_h_azula_always_lies = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [ecl] End-Blaze Epiphany deals X damage to target creature. When that creature dies th
_h_end_blaze_epiphany = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [ecl] Draw three cards. Then discard two cards unless you discard a creature card.
_h_thirst_for_identity = _spell([["draw", {"n": 3}]])
# [ecl] Choose exactly two creatures you control. You draw X cards and the chosen creatu
_h_spry_and_mighty = _spell([["draw", {"n": 1}]])
# [ecl] As an additional cost to cast this spell, blight 1 or pay {3}. (To blight 1, put
_h_bogslither_s_embrace = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [ecl] Changeling (This card is every creature type.) | Exile target creature. Its contro
_h_crib_swap = _spell([["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["changeling"]}]])
# [ecl] As an additional cost to cast this spell, blight X. X can't be greater than the 
_h_soul_immolation = _spell([["damage_player", {"n": 1, "target": "opp"}]])
# [ecl] As an additional cost to cast this spell, you may blight 1. (You may put a -1/-1
_h_cinder_strike = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [ecl] Choose two ? | ? Create a token that's a copy of target Kithkin you control. | ? Tar
_h_brigid_s_command = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Target creature you control gains deathtouch and lifelink until end of turn. Whe
_h_scarblade_s_malice = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [ecl] Mill four cards, then you may return a permanent card from among them to your ha
_h_midnight_tilling = _spell([["mill", {"n": 4, "target": "self"}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_wanderwine_farewell = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Choose two ? | ? Create a token that's a copy of target Goblin you control. | ? Crea
_h_grub_s_command = _spell([["mill", {"n": 5, "target": "self"}]])
# [ecl] Search your library for a basic land card, put it onto the battlefield tapped, t
_h_tend_the_sprigs = _spell([["create_token", {"count": 1, "power": "3", "toughness": "4", "keywords": ["reach"]}], ["search_basic_land", {"n": 1}]])
# [ecl] Tweeze deals 3 damage to any target. You may discard a card. If you do, draw a c
_h_tweeze = _spell([["damage_any", {"n": 3}], ["draw", {"n": 1}]])
# [ecl] Target creature gets +3/+3 until end of turn. If a creature entered the battlefi
_h_thoughtweft_charge = _spell([["draw", {"n": 1}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_harmonized_crescendo = _spell([["draw", {"n": 1}]])
# [ecl] Vivid ? This spell costs {1} less to cast for each color among permanents you co
_h_rime_chill = _spell([["draw", {"n": 1}]])
# [ecl] Choose one ? | ? Destroy target creature with flying. | ? Destroy target enchantment
_h_unforgiving_aim = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_unexpected_assistance = _spell([["draw", {"n": 3}]])
# [ecl] Exile target creature you control, then return that card to the battlefield unde
_h_personify = _spell([["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["changeling"]}]])
# [ecl] Choose one ? | ? Return target creature card from your graveyard to your hand. | ? R
_h_unbury = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [ecl] Target creature gets +3/+2 until end of turn. Create a Treasure token. (It's an 
_h_reckless_ransacking = _spell([["create_treasure", {"n": 1}]])
# [ecl] Choose two ? | ? Create a token that's a copy of target Elf you control. | ? Return 
_h_trystan_s_command = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [ecl] Feed the Flames deals 5 damage to target creature. If that creature would die th
_h_feed_the_flames = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [ecl] Return target creature card from your graveyard to the battlefield. Then if it i
_h_dose_of_dawnglow = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [tmt] Until end of turn, target artifact or creature becomes an artifact creature with
_h_mind_transfer_protocol = _spell([["draw", {"n": 1}]])
# [tmt] Bot Bashing Time deals 6 damage to target creature. If that creature would die t
_h_bot_bashing_time = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [tmt] Choose one ? | ? Target player discards two cards. | ? Target player draws two cards
_h_shredder_s_revenge = _spell([["draw", {"n": 2}]])
# [tmt] Destroy target artifact or creature. If its mana value was 4 or less, create a F
_h_tainted_treats = _spell([["gain_life", {"n": 3}], ["gain_life", {"n": 3}]])
# [tmt] Return all creatures to their owners' hands. Each player may shuffle their hand 
_h_turtles_in_time = _spell([["draw", {"n": 7}]])
# [tmt] Sneak {R} (You may cast this spell for {R} if you also return an unblocked attac
_h_jennika_s_technique = _spell([["damage_creature", {"n": 2, "target": "each_opp"}]])
# [tmt] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_grounded_for_life = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] Target creature's owner puts it on their choice of the top or bottom of their li
_h_return_to_the_sewers = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Choose one or both ? | ? Brilliance Unleashed deals 5 damage to target creature. | ?
_h_brilliance_unleashed = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [tmt] Choose one ? | ? Create a 1/1 colorless Robot artifact creature token. | ? Target cr
_h_mouser_attack_ = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] Counter target spell. Create a Mutagen token. (It's an artifact with "{1}, {T}, 
_h_ooze_spill = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Manhole Missile deals 3 damage to target creature. You may put a card from your 
_h_manhole_missile = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [tmt] Target creature gets +1/+3 and gains flying until end of turn. Scry 1. (Look at 
_h_hamato_guardian_stance = _spell([["scry", {"n": 1}]])
# [tmt] Sneak {2}{G} (You may cast this spell for {2}{G} if you also return an unblocked
_h_new_generation_s_technique = _spell([["search_basic_land", {"n": 2}]])
# [tmt] Destroy up to one target artifact, enchantment, or creature with flying. Create 
_h_mutant_chain_reaction = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Sneak {2}{R} (You may cast this spell for {2}{R} if you also return an unblocked
_h_raphael_s_technique = _spell([["draw", {"n": 7}]])
# [tmt] Exile target creature with mana value 3 or less.
_h_death_in_the_family = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] Exile target creature you control, then return that card to the battlefield unde
_h_daydream = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] Destroy target creature. Its controller creates a 1/1 white and black Inkling cr
_h_harsh_annotation = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [sos] Put two +1/+1 counters on target creature. | Infusion ? If you gained life this tu
_h_efflorescence = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Create a 0/0 green and blue Fractal creature token. Put X +1/+1 counters on it. | 
_h_wild_hypothesis = _spell([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] Converge ? Create two 0/0 green and blue Fractal creature tokens. Put X +1/+1 co
_h_snarl_song = _spell([["gain_life", {"n": 1}], ["create_token", {"count": 2, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] This spell costs {2} less to cast if one or more cards left your graveyard this 
_h_wilt_in_the_heat = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [sos] You gain 2 life. You may discard a card. If you do, draw two cards. | Flashback {2
_h_pursue_the_past = _spell([["draw", {"n": 2}], ["gain_life", {"n": 2}]])
# [sos] Until end of turn, any number of target creatures you control each get +1/+0 and
_h_rabid_attack = _spell([["draw", {"n": 1}]])
# [sos] Create a 0/0 green and blue Fractal creature token and put X +1/+1 counters on i
_h_fractal_anomaly = _spell([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] Target opponent loses 1 life and you gain 1 life. | Up to one target creature gets
_h_dissection_practice = _spell([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [sos] Choose up to four. You may choose the same mode more than once. | ? Destroy target
_h_moment_of_reckoning = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Each opponent discards a card. You create a 1/1 black and green Pest creature to
_h_send_in_the_pest = _spell([["gain_life", {"n": 1}], ["discard", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}]])
# [sos] Put a +1/+1 counter on target creature you control. It gains vigilance until end
_h_dig_site_inventory = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Create two 2/2 red and white Spirit creature tokens. Then if this spell was cast
_h_antiquities_on_the_loose = _spell([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] Destroy target creature. | Infusion ? If you gained life this turn, that creature'
_h_foolish_fate = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Unsubtle Mockery deals 4 damage to target creature. Surveil 1. (Look at the top 
_h_unsubtle_mockery = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [sos] Return up to one target nonland permanent to its owner's hand. Search your libra
_h_proctor_s_gaze = _spell([["search_basic_land", {"n": 1}]])
# [sos] Choose one ? | ? Destroy target artifact. | ? Glorious Decay deals 4 damage to targe
_h_glorious_decay = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [sos] Exile target creature.
_h_wander_off = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] Target player draws two cards and loses 2 life. Put a +1/+1 counter on up to one
_h_cost_of_brilliance = _spell([["draw", {"n": 2}]])
# [sos] Draw three cards. You may put a land card from your hand onto the battlefield ta
_h_embrace_the_paradox = _spell([["draw", {"n": 3}]])
# [sos] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_ajani_s_response = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Target creature gets +1/+1 until end of turn. Draw a card. | Whenever one or more 
_h_killian_s_confidence = _spell([["draw", {"n": 1}]])
# [sos] Put two +1/+1 counters on each creature you control. | Paradigm (Then exile this s
_h_germination_practicum = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Create two 3/3 blue and red Elemental creature tokens with flying. | {2}, Discard 
_h_visionary_s_dance = _spell([["create_token", {"count": 2, "power": "3", "toughness": "3", "keywords": ["flying"]}]])
# [sos] Tap target creature. If it's your turn, put a stun counter on it. (If a permanen
_h_rapier_wit = _spell([["draw", {"n": 1}]])
# [sos] Until end of turn, creatures you control get +2/+2 and gain menace and "Whenever
_h_root_manipulation = _spell([["gain_life", {"n": 1}]])
# [sos] Create a 2/2 red and white Spirit creature token. | Flashback?Tap three untapped c
_h_group_project = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] Target player draws two cards. Tap up to two target creatures. Put a stun counte
_h_homesickness = _spell([["draw", {"n": 2}]])
# [sos] Tome Blast deals 2 damage to any target. | Flashback {4}{R} (You may cast this car
_h_tome_blast = _spell([["damage_any", {"n": 2}]])

for _n,_f in {
    "Greta, Sweettooth Scourge": _h_greta__sweettooth_scourge,
    "Prophetic Prism": _h_prophetic_prism,
    "Stockpiling Celebrant": _h_stockpiling_celebrant,
    "Unassuming Sage": _h_unassuming_sage,
    "Provisions Merchant": _h_provisions_merchant,
    "Hopeful Vigil": _h_hopeful_vigil,
    "Night of the Sweets' Revenge": _h_night_of_the_sweets__revenge,
    "Sweettooth Witch": _h_sweettooth_witch,
    "Merry Bards": _h_merry_bards,
    "Stingblade Assassin": _h_stingblade_assassin,
    "Experimental Confectioner": _h_experimental_confectioner,
    "Voracious Vermin": _h_voracious_vermin,
    "High Fae Negotiator": _h_high_fae_negotiator,
    "Twisted Sewer-Witch": _h_twisted_sewer_witch,
    "Hamlet Glutton": _h_hamlet_glutton,
    "Food Coma": _h_food_coma,
    "Archive Dragon": _h_archive_dragon,
    "Lord Skitter's Blessing": _h_lord_skitter_s_blessing,
    "Redcap Thief": _h_redcap_thief,
    "Edgewall Pack": _h_edgewall_pack,
    "River Herald Scout": _h_river_herald_scout,
    "Mephitic Draught": _h_mephitic_draught,
    "Starving Revenant": _h_starving_revenant,
    "Plundering Pirate": _h_plundering_pirate,
    "Earthshaker Dreadmaw": _h_earthshaker_dreadmaw,
    "Pathfinding Axejaw": _h_pathfinding_axejaw,
    "Runaway Boulder": _h_runaway_boulder,
    "Magmatic Galleon": _h_magmatic_galleon,
    "Soaring Sandwing": _h_soaring_sandwing,
    "Scampering Surveyor": _h_scampering_surveyor,
    "Armored Kincaller": _h_armored_kincaller,
    "Deathcap Marionette": _h_deathcap_marionette,
    "Didact Echo": _h_didact_echo,
    "Song of Stupefaction": _h_song_of_stupefaction,
    "Oltec Cloud Guard": _h_oltec_cloud_guard,
    "Cavern Stomper": _h_cavern_stomper,
    "Compass Gnome": _h_compass_gnome,
    "Kinjalli's Dawnrunner": _h_kinjalli_s_dawnrunner,
    "River Herald Guide": _h_river_herald_guide,
    "Bat Colony": _h_bat_colony,
    "Tinker's Tote": _h_tinker_s_tote,
    "Palani's Hatcher": _h_palani_s_hatcher,
    "Nurturing Bristleback": _h_nurturing_bristleback,
    "Mineshaft Spider": _h_mineshaft_spider,
    "Ironpaw Aspirant": _h_ironpaw_aspirant,
    "Inside Source": _h_inside_source,
    "Loxodon Eavesdropper": _h_loxodon_eavesdropper,
    "Vitu-Ghazi Inspector": _h_vitu_ghazi_inspector,
    "Hotshot Investigators": _h_hotshot_investigators,
    "Person of Interest": _h_person_of_interest,
    "Cornered Crook": _h_cornered_crook,
    "Case of the Stashed Skeleton": _h_case_of_the_stashed_skeleton,
    "A Killer Among Us": _h_a_killer_among_us,
    "Case of the Burning Masks": _h_case_of_the_burning_masks,
    "Undercity Eliminator": _h_undercity_eliminator,
    "Makeshift Binding": _h_makeshift_binding,
    "Blood Spatter Analysis": _h_blood_spatter_analysis,
    "Gleaming Geardrake": _h_gleaming_geardrake,
    "Persuasive Interrogators": _h_persuasive_interrogators,
    "Hunted Bonebrute": _h_hunted_bonebrute,
    "Case of the Shattered Pact": _h_case_of_the_shattered_pact,
    "Gadget Technician": _h_gadget_technician,
    "Alquist Proft, Master Sleuth": _h_alquist_proft__master_sleuth,
    "Detective's Satchel": _h_detective_s_satchel,
    "Buried in the Garden": _h_buried_in_the_garden,
    "Unscrupulous Contractor": _h_unscrupulous_contractor,
    "Prosperity Tycoon": _h_prosperity_tycoon,
    "Ertha Jo, Frontier Mentor": _h_ertha_jo__frontier_mentor,
    "Loan Shark": _h_loan_shark,
    "Hellspur Posse Boss": _h_hellspur_posse_boss,
    "Beastbond Outcaster": _h_beastbond_outcaster,
    "Oasis Gardener": _h_oasis_gardener,
    "Prickly Pair": _h_prickly_pair,
    "Mine Raider": _h_mine_raider,
    "Rakdos Joins Up": _h_rakdos_joins_up,
    "Holy Cow": _h_holy_cow,
    "Silver Deputy": _h_silver_deputy,
    "Vault Plunderer": _h_vault_plunderer,
    "Outcaster Greenblade": _h_outcaster_greenblade,
    "Gold Pan": _h_gold_pan,
    "Rictus Robber": _h_rictus_robber,
    "Lassoed by the Law": _h_lassoed_by_the_law,
    "Outlaw Stitcher": _h_outlaw_stitcher,
    "Discerning Peddler": _h_discerning_peddler,
    "Patient Naturalist": _h_patient_naturalist,
    "Spinewoods Paladin": _h_spinewoods_paladin,
    "Fortune, Loyal Steed": _h_fortune__loyal_steed,
    "Rakish Crew": _h_rakish_crew,
    "Desperate Bloodseeker": _h_desperate_bloodseeker,
    "Rooftop Assassin": _h_rooftop_assassin,
    "Greed's Gambit": _h_greed_s_gambit,
    "Bristlebud Farmer": _h_bristlebud_farmer,
    "Pileated Provisioner": _h_pileated_provisioner,
    "Wick's Patrol": _h_wick_s_patrol,
    "Thornplate Intimidator": _h_thornplate_intimidator,
    "Glidedive Duo": _h_glidedive_duo,
    "Daggerfang Duo": _h_daggerfang_duo,
    "Honored Dreyleader": _h_honored_dreyleader,
    "Head of the Homestead": _h_head_of_the_homestead,
    "Bushy Bodyguard": _h_bushy_bodyguard,
    "Treetop Sentries": _h_treetop_sentries,
    "Bumbleflower's Sharepot": _h_bumbleflower_s_sharepot,
    "Sunshower Druid": _h_sunshower_druid,
    "Feather of Flight": _h_feather_of_flight,
    "Vinereap Mentor": _h_vinereap_mentor,
    "Fountainport Bell": _h_fountainport_bell,
    "Bakersbane Duo": _h_bakersbane_duo,
    "Bellowing Crier": _h_bellowing_crier,
    "Driftgloom Coyote": _h_driftgloom_coyote,
    "Marina Vendrell's Grimoire": _h_marina_vendrell_s_grimoire,
    "Fear of Burning Alive": _h_fear_of_burning_alive,
    "Boilerbilges Ripper": _h_boilerbilges_ripper,
    "Disturbing Mirth": _h_disturbing_mirth,
    "Tunnel Surveyor": _h_tunnel_surveyor,
    "Fanatic of the Harrowing": _h_fanatic_of_the_harrowing,
    "Fear of Abduction": _h_fear_of_abduction,
    "Glimmerlight": _h_glimmerlight,
    "Spineseeker Centipede": _h_spineseeker_centipede,
    "Burglar Rat": _h_burglar_rat,
    "Dragon Trainer": _h_dragon_trainer,
    "Skeleton Archer": _h_skeleton_archer,
    "Dwynen's Elite": _h_dwynen_s_elite,
    "Prayer of Binding": _h_prayer_of_binding,
    "Icewind Elemental": _h_icewind_elemental,
    "Cat Collector": _h_cat_collector,
    "Arbiter of Woe": _h_arbiter_of_woe,
    "Campus Guide": _h_campus_guide,
    "Guarded Heir": _h_guarded_heir,
    "Stasis Snare": _h_stasis_snare,
    "Springbloom Druid": _h_springbloom_druid,
    "New Horizons": _h_new_horizons,
    "Bloodtithe Collector": _h_bloodtithe_collector,
    "Crow of Dark Tidings": _h_crow_of_dark_tidings,
    "Corsair Captain": _h_corsair_captain,
    "Redcap Gutter-Dweller": _h_redcap_gutter_dweller,
    "Elvish Regrower": _h_elvish_regrower,
    "Vampire Soulcaller": _h_vampire_soulcaller,
    "Nullpriest of Oblivion": _h_nullpriest_of_oblivion,
    "Billowing Shriekmass": _h_billowing_shriekmass,
    "Pelakka Wurm": _h_pelakka_wurm,
    "Inspiring Overseer": _h_inspiring_overseer,
    "Meteor Golem": _h_meteor_golem,
    "Archway Angel": _h_archway_angel,
    "Soul-Shackled Zombie": _h_soul_shackled_zombie,
    "Cloudblazer": _h_cloudblazer,
    "Nimble Thopterist": _h_nimble_thopterist,
    "Spotcycle Scouter": _h_spotcycle_scouter,
    "Broadcast Rambler": _h_broadcast_rambler,
    "Embalmed Ascendant": _h_embalmed_ascendant,
    "Aatchik, Emerald Radian": _h_aatchik__emerald_radian,
    "Racers' Scoreboard": _h_racers__scoreboard,
    "Migrating Ketradon": _h_migrating_ketradon,
    "Marshals' Pathcruiser": _h_marshals__pathcruiser,
    "Cloudspire Coordinator": _h_cloudspire_coordinator,
    "Ripclaw Wrangler": _h_ripclaw_wrangler,
    "Roadside Assistance": _h_roadside_assistance,
    "Thundering Broodwagon": _h_thundering_broodwagon,
    "Demonic Junker": _h_demonic_junker,
    "Pothole Mole": _h_pothole_mole,
    "Voyager Glidecar": _h_voyager_glidecar,
    "Ticket Tortoise": _h_ticket_tortoise,
    "Guidelight Matrix": _h_guidelight_matrix,
    "Carrion Cruiser": _h_carrion_cruiser,
    "Hulldrifter": _h_hulldrifter,
    "Ooze Patrol": _h_ooze_patrol,
    "Hour of Victory": _h_hour_of_victory,
    "Autarch Mammoth": _h_autarch_mammoth,
    "Veloheart Bike": _h_veloheart_bike,
    "Unsparing Boltcaster": _h_unsparing_boltcaster,
    "Yathan Roadwatcher": _h_yathan_roadwatcher,
    "Encroaching Dragonstorm": _h_encroaching_dragonstorm,
    "Teeming Dragonstorm": _h_teeming_dragonstorm,
    "Mardu Devotee": _h_mardu_devotee,
    "Meticulous Artisan": _h_meticulous_artisan,
    "Underfoot Underdogs": _h_underfoot_underdogs,
    "Dusyut Earthcarver": _h_dusyut_earthcarver,
    "Skirmish Rhino": _h_skirmish_rhino,
    "Stormplain Detainment": _h_stormplain_detainment,
    "Corroding Dragonstorm": _h_corroding_dragonstorm,
    "Salt Road Packbeast": _h_salt_road_packbeast,
    "Reputable Merchant": _h_reputable_merchant,
    "Rainveil Rejuvenator": _h_rainveil_rejuvenator,
    "Ainok Wayfarer": _h_ainok_wayfarer,
    "Temur Tawnyback": _h_temur_tawnyback,
    "Trade Route Envoy": _h_trade_route_envoy,
    "Kin-Tree Nurturer": _h_kin_tree_nurturer,
    "Embermouth Sentinel": _h_embermouth_sentinel,
    "Sonic Shrieker": _h_sonic_shrieker,
    "Sage of the Fang": _h_sage_of_the_fang,
    "Sandskitter Outrider": _h_sandskitter_outrider,
    "Fortress Kin-Guard": _h_fortress_kin_guard,
    "Magitek Armor": _h_magitek_armor,
    "Mysidian Elder": _h_mysidian_elder,
    "Instant Ramen": _h_instant_ramen,
    "Edgar, King of Figaro": _h_edgar__king_of_figaro,
    "Namazu Trader": _h_namazu_trader,
    "Balamb T-Rexaur": _h_balamb_t_rexaur,
    "Shinra Reinforcements": _h_shinra_reinforcements,
    "Hecteyes": _h_hecteyes,
    "Weapons Vendor": _h_weapons_vendor,
    "Lion Heart": _h_lion_heart,
    "Dragoon's Wyvern": _h_dragoon_s_wyvern,
    "Cloudbound Moogle": _h_cloudbound_moogle,
    "Wedgelight Rammer": _h_wedgelight_rammer,
    "Weftwalking": _h_weftwalking,
    "Knight Luminary": _h_knight_luminary,
    "Fell Gravship": _h_fell_gravship,
    "Selfcraft Mechan": _h_selfcraft_mechan,
    "Kav Landseeker": _h_kav_landseeker,
    "Atmospheric Greenhouse": _h_atmospheric_greenhouse,
    "Drix Fatemaker": _h_drix_fatemaker,
    "Honored Knight-Captain": _h_honored_knight_captain,
    "Bioengineered Future": _h_bioengineered_future,
    "Nebula Dragon": _h_nebula_dragon,
    "Rayblade Trooper": _h_rayblade_trooper,
    "Uthros Scanship": _h_uthros_scanship,
    "Pulsar Squadron Ace": _h_pulsar_squadron_ace,
    "Galactic Wayfarer": _h_galactic_wayfarer,
    "Germinating Wurm": _h_germinating_wurm,
    "Sunstar Expansionist": _h_sunstar_expansionist,
    "Biomechan Engineer": _h_biomechan_engineer,
    "Larval Scoutlander": _h_larval_scoutlander,
    "Debris Field Crusher": _h_debris_field_crusher,
    "Faller's Faithful": _h_faller_s_faithful,
    "Virus Beetle": _h_virus_beetle,
    "Alpharael, Dreaming Acolyte": _h_alpharael__dreaming_acolyte,
    "Auxiliary Boosters": _h_auxiliary_boosters,
    "Spider-Ham, Peter Porker": _h_spider_ham__peter_porker,
    "Friendly Neighborhood": _h_friendly_neighborhood,
    "News Helicopter": _h_news_helicopter,
    "Spider-Man, Brooklyn Visionary": _h_spider_man__brooklyn_visionary,
    "Gallant Citizen": _h_gallant_citizen,
    "Steel Wrecking Ball": _h_steel_wrecking_ball,
    "Anti-Venom, Horrifying Healer": _h_anti_venom__horrifying_healer,
    "Professional Wrestler": _h_professional_wrestler,
    "Mysterio, Master of Illusion": _h_mysterio__master_of_illusion,
    "Mob Lookout": _h_mob_lookout,
    "Wall Crawl": _h_wall_crawl,
    "Subway Train": _h_subway_train,
    "Robotics Mastery": _h_robotics_mastery,
    "Web Up": _h_web_up,
    "Mechanical Mobster": _h_mechanical_mobster,
    "Eerie Gravestone": _h_eerie_gravestone,
    "Hot Dog Cart": _h_hot_dog_cart,
    "Spiders-Man, Heroic Horde": _h_spiders_man__heroic_horde,
    "Spider-Bot": _h_spider_bot,
    "Venomized Cat": _h_venomized_cat,
    "Benevolent River Spirit": _h_benevolent_river_spirit,
    "Badgermole": _h_badgermole,
    "Katara, Water Tribe's Hope": _h_katara__water_tribe_s_hope,
    "Crescent Island Temple": _h_crescent_island_temple,
    "Northern Air Temple": _h_northern_air_temple,
    "Buzzard-Wasp Colony": _h_buzzard_wasp_colony,
    "Ostrich-Horse": _h_ostrich_horse,
    "Toph, the Blind Bandit": _h_toph__the_blind_bandit,
    "The Fire Nation Drill": _h_the_fire_nation_drill,
    "Messenger Hawk": _h_messenger_hawk,
    "Tolls of War": _h_tolls_of_war,
    "Yuyan Archers": _h_yuyan_archers,
    "Jeong Jeong's Deserters": _h_jeong_jeong_s_deserters,
    "Kyoshi Battle Fan": _h_kyoshi_battle_fan,
    "Iroh, Tea Master": _h_iroh__tea_master,
    "Dai Li Agents": _h_dai_li_agents,
    "Treetop Freedom Fighters": _h_treetop_freedom_fighters,
    "Platypus-Bear": _h_platypus_bear,
    "Air Nomad Legacy": _h_air_nomad_legacy,
    "Forecasting Fortune Teller": _h_forecasting_fortune_teller,
    "Flopsie, Bumi's Buddy": _h_flopsie__bumi_s_buddy,
    "Mongoose Lizard": _h_mongoose_lizard,
    "Kyoshi Warriors": _h_kyoshi_warriors,
    "The Spirit Oasis": _h_the_spirit_oasis,
    "Canyon Crawler": _h_canyon_crawler,
    "Kyoshi Island Plaza": _h_kyoshi_island_plaza,
    "The Earth King": _h_the_earth_king,
    "Unlucky Cabbage Merchant": _h_unlucky_cabbage_merchant,
    "Earth Kingdom General": _h_earth_kingdom_general,
    "Corrupt Court Official": _h_corrupt_court_official,
    "Hama, the Bloodbender": _h_hama__the_bloodbender,
    "Glider Kids": _h_glider_kids,
    "The Lion-Turtle": _h_the_lion_turtle,
    "Elder Auntie": _h_elder_auntie,
    "Liminal Hold": _h_liminal_hold,
    "Graveshifter": _h_graveshifter,
    "Dundoolin Weaver": _h_dundoolin_weaver,
    "Rooftop Percher": _h_rooftop_percher,
    "Puca's Eye": _h_puca_s_eye,
    "Clachan Festival": _h_clachan_festival,
    "Dawnhand Eulogist": _h_dawnhand_eulogist,
    "Sourbread Auntie": _h_sourbread_auntie,
    "Lluwen, Imperfect Naturalist": _h_lluwen__imperfect_naturalist,
    "Changeling Wayfinder": _h_changeling_wayfinder,
    "Mistmeadow Council": _h_mistmeadow_council,
    "Noggle Robber": _h_noggle_robber,
    "Boggart Mischief": _h_boggart_mischief,
    "Flamekin Gildweaver": _h_flamekin_gildweaver,
    "Dream Seizer": _h_dream_seizer,
    "Merrow Skyswimmer": _h_merrow_skyswimmer,
    "Scarblade Scout": _h_scarblade_scout,
    "Flaring Cinder": _h_flaring_cinder,
    "Lofty Dreams": _h_lofty_dreams,
    "Pummeler for Hire": _h_pummeler_for_hire,
    "Courier of Comestibles": _h_courier_of_comestibles,
    "Mechanized Ninja Cavalry": _h_mechanized_ninja_cavalry,
    "Foot Ninjas": _h_foot_ninjas,
    "April O'Neil, Kunoichi Trainee": _h_april_o_neil__kunoichi_trainee,
    "Mouser Foundry": _h_mouser_foundry,
    "Triceraton Commander": _h_triceraton_commander,
    "Primordial Pachyderm": _h_primordial_pachyderm,
    "Anchovy & Banana Pizza": _h_anchovy___banana_pizza,
    "Ray Fillet, Man Ray": _h_ray_fillet__man_ray,
    "Omni-Cheese Pizza": _h_omni_cheese_pizza,
    "Party Dude": _h_party_dude,
    "Dimensional Exile": _h_dimensional_exile,
    "Paramecia Coloniex": _h_paramecia_coloniex,
    "Spicy Oatmeal Pizza": _h_spicy_oatmeal_pizza,
    "Everything Pizza": _h_everything_pizza,
    "General Traag, Heart of Stone": _h_general_traag__heart_of_stone,
    "Crustacean Commando": _h_crustacean_commando,
    "Sally Pride, Lioness Leader": _h_sally_pride__lioness_leader,
    "Jennika, Bad Apple Big Sister": _h_jennika__bad_apple_big_sister,
    "Stockman, Mad Fly-entist": _h_stockman__mad_fly_entist,
    "Turtle Blimp": _h_turtle_blimp,
    "Baxter Stockman": _h_baxter_stockman,
    "Pizza Face, Gastromancer": _h_pizza_face__gastromancer,
    "Nobody": _h_nobody,
    "Slithering Cryptid": _h_slithering_cryptid,
    "Donatello, Turtle Techie": _h_donatello__turtle_techie,
    "Mighty Mutanimals": _h_mighty_mutanimals,
    "Mindful Biomancer": _h_mindful_biomancer,
    "Eager Glyphmage": _h_eager_glyphmage,
    "Sneering Shadewriter": _h_sneering_shadewriter,
    "Living History": _h_living_history,
    "Moseo, Vein's New Dean": _h_moseo__vein_s_new_dean,
    "Additive Evolution": _h_additive_evolution,
    "Essenceknit Scholar": _h_essenceknit_scholar,
    "Strixhaven Skycoach": _h_strixhaven_skycoach,
    "Rubble Rouser": _h_rubble_rouser,
}.items(): ETB_EFFECTS.setdefault(_n,_f)

for _n,_f in {
    "Witch's Mark": _h_witch_s_mark,
    "Gnawing Crescendo": _h_gnawing_crescendo,
    "Stonesplitter Bolt": _h_stonesplitter_bolt,
    "Rowdy Research": _h_rowdy_research,
    "Feed the Cauldron": _h_feed_the_cauldron,
    "Eriette's Whisper": _h_eriette_s_whisper,
    "Rat Out": _h_rat_out,
    "Spider Food": _h_spider_food,
    "Faerie Slumber Party": _h_faerie_slumber_party,
    "Brave the Wilds": _h_brave_the_wilds,
    "Return from the Wilds": _h_return_from_the_wilds,
    "Sugar Rush": _h_sugar_rush,
    "Freeze in Place": _h_freeze_in_place,
    "Into the Fae Court": _h_into_the_fae_court,
    "Flick a Coin": _h_flick_a_coin,
    "Cut In": _h_cut_in,
    "Plunge into Winter": _h_plunge_into_winter,
    "Return Triumphant": _h_return_triumphant,
    "Break the Spell": _h_break_the_spell,
    "Moment of Valor": _h_moment_of_valor,
    "Kindled Heroism": _h_kindled_heroism,
    "Johann's Stopgap": _h_johann_s_stopgap,
    "Taken by Nightmares": _h_taken_by_nightmares,
    "Frantic Firebolt": _h_frantic_firebolt,
    "Shatter the Oath": _h_shatter_the_oath,
    "Rowan's Grim Search": _h_rowan_s_grim_search,
    "Quicksand Whirlpool": _h_quicksand_whirlpool,
    "Malamet Battle Glyph": _h_malamet_battle_glyph,
    "Brackish Blunder": _h_brackish_blunder,
    "Calamitous Cave-In": _h_calamitous_cave_in,
    "Ancestors' Aid": _h_ancestors__aid,
    "Defossilize": _h_defossilize,
    "Ancestral Reminiscence": _h_ancestral_reminiscence,
    "Another Chance": _h_another_chance,
    "Ray of Ruin": _h_ray_of_ruin,
    "No Witnesses": _h_no_witnesses,
    "Drag the Canal": _h_drag_the_canal,
    "Toxin Analysis": _h_toxin_analysis,
    "They Went This Way": _h_they_went_this_way,
    "Treacherous Greed": _h_treacherous_greed,
    "Soul Search": _h_soul_search,
    "The Chase Is On": _h_the_chase_is_on,
    "Suspicious Detonation": _h_suspicious_detonation,
    "Galvanize": _h_galvanize,
    "Auspicious Arrival": _h_auspicious_arrival,
    "Slime Against Humanity": _h_slime_against_humanity,
    "Deadly Complication": _h_deadly_complication,
    "Eliminate the Impossible": _h_eliminate_the_impossible,
    "Audience with Trostani": _h_audience_with_trostani,
    "It Doesn't Add Up": _h_it_doesn_t_add_up,
    "On the Job": _h_on_the_job,
    "Intrude on the Mind": _h_intrude_on_the_mind,
    "Unfortunate Accident": _h_unfortunate_accident,
    "Map the Frontier": _h_map_the_frontier,
    "Take the Fall": _h_take_the_fall,
    "Gold Rush": _h_gold_rush,
    "Step Between Worlds": _h_step_between_worlds,
    "One Last Job": _h_one_last_job,
    "Mourner's Surprise": _h_mourner_s_surprise,
    "Metamorphic Blast": _h_metamorphic_blast,
    "Dance of the Tumbleweeds": _h_dance_of_the_tumbleweeds,
    "Hell to Pay": _h_hell_to_pay,
    "Trick Shot": _h_trick_shot,
    "Form a Posse": _h_form_a_posse,
    "Getaway Glamer": _h_getaway_glamer,
    "Consuming Ashes": _h_consuming_ashes,
    "Plan the Heist": _h_plan_the_heist,
    "Great Train Heist": _h_great_train_heist,
    "Eriette's Lullaby": _h_eriette_s_lullaby,
    "Explosive Derailment": _h_explosive_derailment,
    "Corrupted Conviction": _h_corrupted_conviction,
    "Trash the Town": _h_trash_the_town,
    "Jailbreak Scheme": _h_jailbreak_scheme,
    "Thunder Salvo": _h_thunder_salvo,
    "Throw from the Saddle": _h_throw_from_the_saddle,
    "Rise of the Varmints": _h_rise_of_the_varmints,
    "Seize the Secrets": _h_seize_the_secrets,
    "Highway Robbery": _h_highway_robbery,
    "Take Up the Shield": _h_take_up_the_shield,
    "Failed Fording": _h_failed_fording,
    "Conduct Electricity": _h_conduct_electricity,
    "Mind Spiral": _h_mind_spiral,
    "Wildfire Howl": _h_wildfire_howl,
    "Playful Shove": _h_playful_shove,
    "Coiling Rebirth": _h_coiling_rebirth,
    "Hazel's Nocturne": _h_hazel_s_nocturne,
    "Mind Spring": _h_mind_spring,
    "Psychic Whorl": _h_psychic_whorl,
    "Otterball Antics": _h_otterball_antics,
    "Valley Rally": _h_valley_rally,
    "Starfall Invocation": _h_starfall_invocation,
    "Agate Assault": _h_agate_assault,
    "Spellgyre": _h_spellgyre,
    "Pearl of Wisdom": _h_pearl_of_wisdom,
    "Crumb and Get It": _h_crumb_and_get_it,
    "Peerless Recycling": _h_peerless_recycling,
    "Rabbit Response": _h_rabbit_response,
    "Diresight": _h_diresight,
    "Ruthless Negotiation": _h_ruthless_negotiation,
    "Sazacap's Brew": _h_sazacap_s_brew,
    "Consumed by Greed": _h_consumed_by_greed,
    "Repel Calamity": _h_repel_calamity,
    "Flame Lash": _h_flame_lash,
    "Calamitous Tide": _h_calamitous_tide,
    "Sonar Strike": _h_sonar_strike,
    "For the Common Good": _h_for_the_common_good,
    "Savor": _h_savor,
    "Take Out the Trash": _h_take_out_the_trash,
    "Hop to It": _h_hop_to_it,
    "Nocturnal Hunger": _h_nocturnal_hunger,
    "Early Winter": _h_early_winter,
    "Commune with Evil": _h_commune_with_evil,
    "Come Back Wrong": _h_come_back_wrong,
    "Midnight Mayhem": _h_midnight_mayhem,
    "Enter the Enigma": _h_enter_the_enigma,
    "Seized from Slumber": _h_seized_from_slumber,
    "Peer Past the Veil": _h_peer_past_the_veil,
    "Unwanted Remake": _h_unwanted_remake,
    "Winter's Intervention": _h_winter_s_intervention,
    "Murder": _h_murder,
    "Glimmerburst": _h_glimmerburst,
    "Rite of the Moth": _h_rite_of_the_moth,
    "Live or Die": _h_live_or_die,
    "Let's Play a Game": _h_let_s_play_a_game,
    "Drag to the Roots": _h_drag_to_the_roots,
    "Impossible Inferno": _h_impossible_inferno,
    "Emerge from the Cocoon": _h_emerge_from_the_cocoon,
    "Hero's Downfall": _h_hero_s_downfall,
    "Cemetery Recruitment": _h_cemetery_recruitment,
    "Bake into a Pie": _h_bake_into_a_pie,
    "Thrill of Possibility": _h_thrill_of_possibility,
    "An Offer You Can't Refuse": _h_an_offer_you_can_t_refuse,
    "Circuitous Route": _h_circuitous_route,
    "Seismic Rupture": _h_seismic_rupture,
    "Incinerating Blast": _h_incinerating_blast,
    "Lunar Insight": _h_lunar_insight,
    "Deadly Plot": _h_deadly_plot,
    "Fleeting Flight": _h_fleeting_flight,
    "Brass's Bounty": _h_brass_s_bounty,
    "Dread Summons": _h_dread_summons,
    "Grow from the Ashes": _h_grow_from_the_ashes,
    "Finale of Revelation": _h_finale_of_revelation,
    "Goblin Negotiation": _h_goblin_negotiation,
    "Goblin Surprise": _h_goblin_surprise,
    "Involuntary Employment": _h_involuntary_employment,
    "Exsanguinate": _h_exsanguinate,
    "Inspiring Call": _h_inspiring_call,
    "Fake Your Own Death": _h_fake_your_own_death,
    "Fleeting Distraction": _h_fleeting_distraction,
    "Inspiration from Beyond": _h_inspiration_from_beyond,
    "Heroic Reinforcements": _h_heroic_reinforcements,
    "Dragon Fodder": _h_dragon_fodder,
    "Luminous Rebuke": _h_luminous_rebuke,
    "Deadly Riposte": _h_deadly_riposte,
    "Mortify": _h_mortify,
    "Felling Blow": _h_felling_blow,
    "Arcane Epiphany": _h_arcane_epiphany,
    "Gallant Strike": _h_gallant_strike,
    "Crash and Burn": _h_crash_and_burn,
    "Voyage Home": _h_voyage_home,
    "Haunt the Network": _h_haunt_the_network,
    "Syphon Fuel": _h_syphon_fuel,
    "Spectacular Pileup": _h_spectacular_pileup,
    "Risky Shortcut": _h_risky_shortcut,
    "Back on Track": _h_back_on_track,
    "Trip Up": _h_trip_up,
    "Spin Out": _h_spin_out,
    "Trade the Helm": _h_trade_the_helm,
    "Explosive Getaway": _h_explosive_getaway,
    "Stall Out": _h_stall_out,
    "Hellish Sideswipe": _h_hellish_sideswipe,
    "Road Rage": _h_road_rage,
    "Lightshield Parry": _h_lightshield_parry,
    "Maximum Overdrive": _h_maximum_overdrive,
    "Locust Spray": _h_locust_spray,
    "Worthy Cost": _h_worthy_cost,
    "Kin-Tree Severance": _h_kin_tree_severance,
    "Narset's Rebuke": _h_narset_s_rebuke,
    "Cruel Truths": _h_cruel_truths,
    "Rally the Monastery": _h_rally_the_monastery,
    "Lie in Wait": _h_lie_in_wait,
    "Rebellious Strike": _h_rebellious_strike,
    "Death Begets Life": _h_death_begets_life,
    "Defibrillating Current": _h_defibrillating_current,
    "Lightfoot Technique": _h_lightfoot_technique,
    "Duty Beyond Death": _h_duty_beyond_death,
    "Focus the Mind": _h_focus_the_mind,
    "Mammoth Bellow": _h_mammoth_bellow,
    "Knockout Maneuver": _h_knockout_maneuver,
    "Bewildering Blizzard": _h_bewildering_blizzard,
    "Dragon's Prey": _h_dragon_s_prey,
    "Ureni's Rebuff": _h_ureni_s_rebuff,
    "Unending Whisper": _h_unending_whisper,
    "Roamer's Routine": _h_roamer_s_routine,
    "Salt Road Skirmish": _h_salt_road_skirmish,
    "Fate of the Sun-Cryst": _h_fate_of_the_sun_cryst,
    "Reach the Horizon": _h_reach_the_horizon,
    "Aerith Rescue Mission": _h_aerith_rescue_mission,
    "Evil Reawakened": _h_evil_reawakened,
    "Combat Tutorial": _h_combat_tutorial,
    "Circle of Power": _h_circle_of_power,
    "Deadly Embrace": _h_deadly_embrace,
    "Laughing Mad": _h_laughing_mad,
    "Travel the Overworld": _h_travel_the_overworld,
    "Cornered by Black Mages": _h_cornered_by_black_mages,
    "Ice Magic": _h_ice_magic,
    "Light of Judgment": _h_light_of_judgment,
    "Sephiroth's Intervention": _h_sephiroth_s_intervention,
    "Moogles' Valor": _h_moogles__valor,
    "Eject": _h_eject,
    "Call the Mountain Chocobo": _h_call_the_mountain_chocobo,
    "Judgment Bolt": _h_judgment_bolt,
    "Prishe's Wanderings": _h_prishe_s_wanderings,
    "The Crystal's Chosen": _h_the_crystal_s_chosen,
    "Gysahl Greens": _h_gysahl_greens,
    "Embrace Oblivion": _h_embrace_oblivion,
    "Lithobraking": _h_lithobraking,
    "Gravkill": _h_gravkill,
    "Radiant Strike": _h_radiant_strike,
    "Biosynthic Burst": _h_biosynthic_burst,
    "Decode Transmissions": _h_decode_transmissions,
    "Mental Modulation": _h_mental_modulation,
    "Invasive Maneuvers": _h_invasive_maneuvers,
    "Orbital Plunge": _h_orbital_plunge,
    "Sami's Curiosity": _h_sami_s_curiosity,
    "Scrounge for Eternity": _h_scrounge_for_eternity,
    "Vote Out": _h_vote_out,
    "Dual-Sun Technique": _h_dual_sun_technique,
    "Hymn of the Faller": _h_hymn_of_the_faller,
    "Bombard": _h_bombard,
    "Cerebral Download": _h_cerebral_download,
    "Risky Research": _h_risky_research,
    "Venom's Hunger": _h_venom_s_hunger,
    "Whoosh!": _h_whoosh_,
    "Prison Break": _h_prison_break,
    "School Daze": _h_school_daze,
    "Kapow!": _h_kapow_,
    "Scout the City": _h_scout_the_city,
    "Thwip!": _h_thwip_,
    "Fire Nation Attacks": _h_fire_nation_attacks,
    "Lost Days": _h_lost_days,
    "Waterbending Lesson": _h_waterbending_lesson,
    "Dai Li Indoctrination": _h_dai_li_indoctrination,
    "Jet's Brainwashing": _h_jet_s_brainwashing,
    "Zuko's Exile": _h_zuko_s_exile,
    "Spirit Water Revival": _h_spirit_water_revival,
    "Sold Out": _h_sold_out,
    "Cycle of Renewal": _h_cycle_of_renewal,
    "Ruinous Waterbending": _h_ruinous_waterbending,
    "Sokka's Haiku": _h_sokka_s_haiku,
    "Cunning Maneuver": _h_cunning_maneuver,
    "Ozai's Cruelty": _h_ozai_s_cruelty,
    "United Front": _h_united_front,
    "Energybending": _h_energybending,
    "Deadly Precision": _h_deadly_precision,
    "Gather the White Lotus": _h_gather_the_white_lotus,
    "Aang's Journey": _h_aang_s_journey,
    "Sandbenders' Storm": _h_sandbenders__storm,
    "Airbending Lesson": _h_airbending_lesson,
    "Epic Downfall": _h_epic_downfall,
    "Zuko's Conviction": _h_zuko_s_conviction,
    "Earth Rumble": _h_earth_rumble,
    "Azula Always Lies": _h_azula_always_lies,
    "End-Blaze Epiphany": _h_end_blaze_epiphany,
    "Thirst for Identity": _h_thirst_for_identity,
    "Spry and Mighty": _h_spry_and_mighty,
    "Bogslither's Embrace": _h_bogslither_s_embrace,
    "Crib Swap": _h_crib_swap,
    "Soul Immolation": _h_soul_immolation,
    "Cinder Strike": _h_cinder_strike,
    "Brigid's Command": _h_brigid_s_command,
    "Scarblade's Malice": _h_scarblade_s_malice,
    "Midnight Tilling": _h_midnight_tilling,
    "Wanderwine Farewell": _h_wanderwine_farewell,
    "Grub's Command": _h_grub_s_command,
    "Tend the Sprigs": _h_tend_the_sprigs,
    "Tweeze": _h_tweeze,
    "Thoughtweft Charge": _h_thoughtweft_charge,
    "Harmonized Crescendo": _h_harmonized_crescendo,
    "Rime Chill": _h_rime_chill,
    "Unforgiving Aim": _h_unforgiving_aim,
    "Unexpected Assistance": _h_unexpected_assistance,
    "Personify": _h_personify,
    "Unbury": _h_unbury,
    "Reckless Ransacking": _h_reckless_ransacking,
    "Trystan's Command": _h_trystan_s_command,
    "Feed the Flames": _h_feed_the_flames,
    "Dose of Dawnglow": _h_dose_of_dawnglow,
    "Mind Transfer Protocol": _h_mind_transfer_protocol,
    "Bot Bashing Time": _h_bot_bashing_time,
    "Shredder's Revenge": _h_shredder_s_revenge,
    "Tainted Treats": _h_tainted_treats,
    "Turtles in Time": _h_turtles_in_time,
    "Jennika's Technique": _h_jennika_s_technique,
    "Grounded for Life": _h_grounded_for_life,
    "Return to the Sewers": _h_return_to_the_sewers,
    "Brilliance Unleashed": _h_brilliance_unleashed,
    "Mouser Attack!": _h_mouser_attack_,
    "Ooze Spill": _h_ooze_spill,
    "Manhole Missile": _h_manhole_missile,
    "Hamato Guardian Stance": _h_hamato_guardian_stance,
    "New Generation's Technique": _h_new_generation_s_technique,
    "Mutant Chain Reaction": _h_mutant_chain_reaction,
    "Raphael's Technique": _h_raphael_s_technique,
    "Death in the Family": _h_death_in_the_family,
    "Daydream": _h_daydream,
    "Harsh Annotation": _h_harsh_annotation,
    "Efflorescence": _h_efflorescence,
    "Wild Hypothesis": _h_wild_hypothesis,
    "Snarl Song": _h_snarl_song,
    "Wilt in the Heat": _h_wilt_in_the_heat,
    "Pursue the Past": _h_pursue_the_past,
    "Rabid Attack": _h_rabid_attack,
    "Fractal Anomaly": _h_fractal_anomaly,
    "Dissection Practice": _h_dissection_practice,
    "Moment of Reckoning": _h_moment_of_reckoning,
    "Send in the Pest": _h_send_in_the_pest,
    "Dig Site Inventory": _h_dig_site_inventory,
    "Antiquities on the Loose": _h_antiquities_on_the_loose,
    "Foolish Fate": _h_foolish_fate,
    "Unsubtle Mockery": _h_unsubtle_mockery,
    "Proctor's Gaze": _h_proctor_s_gaze,
    "Glorious Decay": _h_glorious_decay,
    "Wander Off": _h_wander_off,
    "Cost of Brilliance": _h_cost_of_brilliance,
    "Embrace the Paradox": _h_embrace_the_paradox,
    "Ajani's Response": _h_ajani_s_response,
    "Killian's Confidence": _h_killian_s_confidence,
    "Germination Practicum": _h_germination_practicum,
    "Visionary's Dance": _h_visionary_s_dance,
    "Rapier Wit": _h_rapier_wit,
    "Root Manipulation": _h_root_manipulation,
    "Group Project": _h_group_project,
    "Homesickness": _h_homesickness,
    "Tome Blast": _h_tome_blast,
}.items(): SPELL_EFFECTS.setdefault(_n,_f)