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
_h_greta__sweettooth_scourge = _etb([["gain_life", {"n": 3}]])
# [woe] {1}: This creature gets +1/-1 until end of turn. | When this creature dies, scry 2
_h_merfolk_coralsmith = _etb([["scry", {"n": 2}]])
# [woe] At the beginning of combat on your turn, if you control a creature with power 4 
_h_boundary_lands_ranger = _etb([["draw", {"n": 1}]])
# [woe] When this artifact enters, draw a card. | {1}, {T}: Add one mana of any color.
_h_prophetic_prism = _etb([["draw", {"n": 1}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_troublemaker_ouphe = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [woe] When this creature enters, you may return another target nonland permanent you c
_h_stockpiling_celebrant = _etb([["scry", {"n": 2}]])
# [woe] Lifelink | When this creature enters, create a Cursed Role token attached to it. (
_h_cursed_courtier = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] When this creature enters, you may pay {2}. If you do, create a Sorcerer Role to
_h_unassuming_sage = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Whenever you cast an instant or sorcery spell, create a Sorcerer Role token atta
_h_splashy_spellcaster = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Reach | Whenever you cast a spell with mana value 5 or greater, create a Food toke
_h_skybeast_tracker = _etb([["gain_life", {"n": 3}]])
# [woe] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_provisions_merchant = _etb([["gain_life", {"n": 3}], ["scry", {"n": 0}]])
# [woe] When this enchantment enters, create a 2/2 white Knight creature token with vigi
_h_hopeful_vigil = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["vigilance"]}]])
# [woe] This creature can't block. | When this creature dies, create X 1/1 black Rat creat
_h_tangled_colony = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block", "\" where X is the amount of damage dealt to it this turn"]}]])
# [woe] Flash | Flying | Whenever another Faerie you control enters, each opponent loses 1 l
_h_obyra__dreaming_duelist = _etb([["lose_life", {"n": 1, "target": "opp"}]])
# [woe] When this enchantment enters, create a Food token. (It's an artifact with "{2}, 
_h_night_of_the_sweets__revenge = _etb([["gain_life", {"n": 3}]])
# [woe] Menace | Whenever this creature enters or attacks, create two 1/1 black Rat creatu
_h_ogre_chitterlord = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}], ["add_counters", {"n": 2, "target": "self"}]])
# [woe] When Syr Armont enters, create a Monster Role token attached to another target c
_h_syr_armont__the_redeemer = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_sweettooth_witch = _etb([["gain_life", {"n": 3}]])
# [woe] When this creature enters, you may pay {1}. When you do, create a Young Hero Rol
_h_merry_bards = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] At the beginning of your upkeep, if an opponent controls more lands than you, cr
_h_discerning_financier = _etb([["create_treasure", {"n": 1}]])
# [woe] Flash | Flying | When this creature enters, destroy target creature an opponent cont
_h_stingblade_assassin = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [woe] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_experimental_confectioner = _etb([["gain_life", {"n": 3}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [woe] Whenever an enchantment you control enters, scry 1. | {2}{W}: This creature gets +
_h_slumbering_keepguard = _etb([["scry", {"n": 1}]])
# [woe] When this creature enters, create a 1/1 black Rat creature token with "This toke
_h_voracious_vermin = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_high_fae_negotiator = _etb([["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [woe] Defender | At the beginning of combat on your turn, if you control a creature with
_h_territorial_witchstalker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [woe] When this creature enters, create a 1/1 black Rat creature token with "This crea
_h_twisted_sewer_witch = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This creature can't block"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_hamlet_glutton = _etb([["gain_life", {"n": 3}]])
# [woe] When this enchantment enters, exile target creature an opponent controls until t
_h_food_coma = _etb([["exile", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}]])
# [woe] Flying | When this creature enters, create a Royal Role token attached to another 
_h_charmed_clothier = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_tenacious_tomeseeker = _etb([["return_gy_to_hand", {"filter_type": "any"}]])
# [woe] When Eriette's Tempting Apple enters, gain control of target creature until end 
_h_eriette_s_tempting_apple = _etb([["scry", {"n": 0}]])
# [woe] Deathtouch | Whenever this creature deals combat damage to a player, create a Food
_h_scream_puff = _etb([["gain_life", {"n": 3}]])
# [woe] When this creature enters, create a Monster Role token attached to it. (Enchante
_h_faunsbane_troll = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_diminisher_witch = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Whenever this creature attacks, it gets +1/+0 until end of turn for each attacki
_h_charging_hooligan = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [woe] When this creature dies, create a Food token. (It's an artifact with "{2}, {T}, 
_h_mintstrosity = _etb([["gain_life", {"n": 3}]])
# [woe] Flying | Ward {2} (Whenever this creature becomes the target of a spell or ability
_h_archive_dragon = _etb([["scry", {"n": 2}]])
# [woe] When this enchantment enters, create a Wicked Role token attached to target crea
_h_lord_skitter_s_blessing = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}], ["lose_life", {"n": 1, "target": "self"}]])
# [woe] When this creature dies, create a Young Hero Role token attached to up to one ta
_h_protective_parents = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Whenever you cast a spell with mana value 5 or greater, put two +1/+1 counters o
_h_stormkeld_prowler = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [woe] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_redcap_thief = _etb([["create_treasure", {"n": 1}]])
# [woe] Menace | Whenever this creature deals combat damage to a player, put a skewer coun
_h_rotisserie_elemental = _etb([["mill", {"n": 1, "target": "self"}]])
# [woe] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_edgewall_pack = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [woe] Whenever a token you control enters, put a +1/+1 counter on this creature. | Whene
_h_wildwood_mentor = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [woe] When this creature enters, create a Royal Role token attached to another target 
_h_redtooth_genealogist = _etb([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Flying | At the beginning of each end step, if a creature died this turn, create a
_h_old_flitterfang = _etb([["gain_life", {"n": 3}]])
# [lci] When this creature enters, it explores. (Reveal the top card of your library. Pu
_h_river_herald_scout = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this artifact enters or is put into a graveyard from the battlefield, you d
_h_mephitic_draught = _etb([["draw", {"n": 1}], ["lose_life", {"n": 1, "target": "self"}]])
# [lci] Whenever this creature attacks, target attacking creature gains trample until en
_h_malamet_brawler = _etb([["scry", {"n": 0}]])
# [lci] When this creature enters, you may sacrifice another creature or artifact. When 
_h_glorifier_of_suffering = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [lci] When this creature enters, it explores X times. (To have it explore, reveal the 
_h_jadelight_spelunker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] At the beginning of combat on your turn, this creature explores. Then you may ha
_h_deepfathom_echo = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Whenever this creature becomes tapped, scry 1. (Look at the top card of your lib
_h_attentive_sunscribe = _etb([["scry", {"n": 1}]])
# [lci] Flying | At the beginning of each end step, if you gained 5 or more life this turn
_h_resplendent_angel = _etb([["create_token", {"count": 1, "power": "4", "toughness": "4", "keywords": ["flying", "vigilance"]}]])
# [lci] When this creature enters, surveil 2. Then for each card you put on top of your 
_h_starving_revenant = _etb([["draw", {"n": 1}], ["scry", {"n": 2}], ["lose_life", {"n": 3, "target": "self"}]])
# [lci] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_plundering_pirate = _etb([["create_treasure", {"n": 1}]])
# [lci] When this creature enters, target creature you control gets +2/+0 and gains inde
_h_rampaging_spiketail = _etb([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [lci] Whenever an artifact you control enters, put a +1/+1 counter on target Pirate yo
_h_captain_storm__cosmium_raider = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_dinotomaton = _etb([["scry", {"n": 0}]])
# [lci] Trample | When this creature enters, draw a card for each other Dinosaur you contr
_h_earthshaker_dreadmaw = _etb([["draw", {"n": 1}]])
# [lci] At the beginning of each player's end step, if an artifact entered the battlefie
_h_akal_pakal__first_among_equals = _etb([["scry", {"n": 2}]])
# [lci] When this creature enters, it explores. (Reveal the top card of your library. Pu
_h_pathfinding_axejaw = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Flash | When this artifact enters, it deals 6 damage to target creature an opponen
_h_runaway_boulder = _etb([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [lci] When this Vehicle enters, it deals 5 damage to target creature an opponent contr
_h_magmatic_galleon = _etb([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [lci] Flying | When this creature enters, you gain 3 life. | Plainscycling {2} ({2}, Disca
_h_soaring_sandwing = _etb([["gain_life", {"n": 3}]])
# [lci] At the beginning of combat on your turn, target creature you control gets +2/+0 
_h_might_of_the_ancestors = _etb([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [lci] When this creature enters, search your library for a basic land card or Cave car
_h_scampering_surveyor = _etb([["search_basic_land", {"n": 1}]])
# [lci] When this creature enters, look at the top three cards of your library. You may 
_h_sage_of_days = _etb([["scry", {"n": 3}]])
# [lci] When this creature enters, you may reveal a Dinosaur card from your hand. If you
_h_armored_kincaller = _etb([["gain_life", {"n": 3}]])
# [lci] Deathtouch | When this creature enters, you may mill two cards. (You may put the t
_h_deathcap_marionette = _etb([["mill", {"n": 2, "target": "self"}]])
# [lci] Trample | At the beginning of your end step, if you descended this turn, put a +1/
_h_child_of_the_volcano = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this creature dies, discover 3. (Exile cards from the top of your library u
_h_primordial_gnawer = _etb([["draw", {"n": 1}]])
# [lci] When this creature enters, draw a card. | Descend 4 ? This creature has flying as 
_h_didact_echo = _etb([["draw", {"n": 1}]])
# [lci] Whenever this creature attacks, exile target card from an opponent's graveyard.
_h_disruptor_wanderglyph = _etb([["scry", {"n": 0}]])
# [lci] Enchant creature or Vehicle | When this Aura enters, you may mill two cards. (You 
_h_song_of_stupefaction = _etb([["mill", {"n": 2, "target": "self"}]])
# [lci] When this creature enters, creatures you control get +2/+1 until end of turn.
_h_malamet_war_scribe = _etb([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [lci] When this creature enters, look at the top four cards of your library. You may r
_h_staunch_crewmate = _etb([["scry", {"n": 4}]])
# [lci] Flying | When this creature enters, create a 1/1 colorless Gnome artifact creature
_h_oltec_cloud_guard = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [lci] When this creature enters, scry 2. (Look at the top two cards of your library, t
_h_cavern_stomper = _etb([["scry", {"n": 2}]])
# [lci] At the beginning of your end step, if you descended this turn, create a Treasure
_h_enterprising_scallywag = _etb([["create_treasure", {"n": 1}]])
# [lci] This artifact enters with two +1/+1 counters on it. | Whenever a creature you cont
_h_explorer_s_cache = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this creature enters, you may search your library for a basic land card or 
_h_compass_gnome = _etb([["search_basic_land", {"n": 1}]])
# [lci] Double strike | When this creature enters, it explores. (Reveal the top card of yo
_h_kinjalli_s_dawnrunner = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Trample | The Mycotyrant's power and toughness are each equal to the number of cre
_h_the_mycotyrant = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block", "\" where X is the number of times you descended this turn"]}]])
# [lci] Menace | At the beginning of your end step, if you descended this turn, put a +1/+
_h_deep_goblin_skulltaker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Vigilance | When this creature enters, it explores. (Reveal the top card of your l
_h_river_herald_guide = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this enchantment enters, create a 1/1 black Bat creature token with flying 
_h_bat_colony = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying for each mana from a Cave spent to cast it"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [lci] Whenever this Vehicle attacks, create a Treasure token. (It's an artifact with "
_h_careening_mine_cart = _etb([["create_treasure", {"n": 1}]])
# [lci] Menace | At the beginning of your end step, if you descended this turn, put a +1/+
_h_stalactite_stalker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this artifact enters, create two 1/1 colorless Gnome artifact creature toke
_h_tinker_s_tote = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [lci] Other Dinosaurs you control have haste. | When this creature enters, create two 0/
_h_palani_s_hatcher = _etb([["create_token", {"count": 2, "power": "0", "toughness": "1", "keywords": []}], ["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [lci] Sacrifice this creature: Exile up to four target cards from a single graveyard. 
_h_digsite_conservator = _etb([["draw", {"n": 1}]])
# [lci] Flying | Whenever this creature attacks, mill a card. (Put the top card of your li
_h_screaming_phantom = _etb([["mill", {"n": 1, "target": "self"}]])
# [lci] When this creature enters, create a 3/3 green Dinosaur creature token. | Forestcyc
_h_nurturing_bristleback = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [lci] When this creature enters, look at the top X cards of your library, where X is t
_h_sinuous_benthisaur = _etb([["scry", {"n": 1}]])
# [lci] At the beginning of your end step, if you descended this turn, put a +1/+1 count
_h_canonized_in_blood = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] When this creature dies, scry 1 and create a Treasure token. (To scry 1, look at
_h_greedy_freebooter = _etb([["create_treasure", {"n": 1}], ["scry", {"n": 1}]])
# [lci] Flash | When this creature enters, target creature an opponent controls gets -2/-0
_h_cogwork_wrestler = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [lci] When Geological Appraiser enters, if you cast it, discover 3. (Exile cards from 
_h_a_geological_appraiser = _etb([["draw", {"n": 1}]])
# [lci] Reach | When this creature enters, you may mill two cards. (You may put the top tw
_h_mineshaft_spider = _etb([["mill", {"n": 2, "target": "self"}]])
# [lci] Flying, lifelink | At the beginning of your end step, if you descended this turn, 
_h_ruin_lurker_bat = _etb([["scry", {"n": 1}]])
# [lci] Deathtouch | At the beginning of your end step, if you descended this turn, each o
_h_zoyowa_lava_tongue = _etb([["damage_player", {"n": 3, "target": "opp"}]])
# [lci] Flying, vigilance | When this creature dies, target creature you control explores.
_h_miner_s_guidewing = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Whenever this creature becomes tapped, you may discard a card. If you do, draw a
_h_volatile_wanderglyph = _etb([["draw", {"n": 1}]])
# [lci] At the beginning of your end step, if you descended this turn, create a 1/1 blac
_h_broodrage_mycoid = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [lci] When this creature dies, create two 1/1 black Fungus creature tokens with "This 
_h_synapse_necromage = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [lci] When this creature enters, put a +1/+1 counter on target creature.
_h_ironpaw_aspirant = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] Flying | When this creature enters, you lose 3 life. | Disguise {B}{B} (You may cast
_h_nightdrinker_moroii = _etb([["lose_life", {"n": 3, "target": "self"}]])
# [mkm] Lifelink | When Tolsimir enters, create Voja Fenstalker, a legendary 5/5 green and
_h_tolsimir__midnight_s_light = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [mkm] When this creature enters, create a 2/2 white and blue Detective creature token.
_h_inside_source = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] When this creature enters, investigate. (Create a Clue token. It's an artifact w
_h_loxodon_eavesdropper = _etb([["draw", {"n": 1}]])
# [mkm] As an additional cost to cast this spell, you may collect evidence 6. (Exile car
_h_vitu_ghazi_inspector = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 2}]])
# [mkm] Disguise {2}{W} (You may cast this card face down for {3} as a 2/2 creature with
_h_essence_of_antiquity = _etb([["scry", {"n": 0}]])
# [mkm] When this creature enters, return up to one other target creature to its owner's
_h_hotshot_investigators = _etb([["draw", {"n": 1}]])
# [mkm] Flying | When this creature dies, investigate. (Create a Clue token. It's an artif
_h_cold_case_cracker = _etb([["draw", {"n": 1}]])
# [mkm] Flying, vigilance | Disguise {W/U}{W/U} (You may cast this card face down for {3} 
_h_granite_witness = _etb([["scry", {"n": 0}]])
# [mkm] When this creature dies, create a 2/2 white and blue Detective creature token. | D
_h_museum_nightwatch = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] Whenever this creature deals combat damage to a player, investigate. (Create a C
_h_undercover_crocodelf = _etb([["draw", {"n": 1}]])
# [mkm] Disguise {1}{W} (You may cast this card face down for {3} as a 2/2 creature with
_h_unyielding_gatekeeper = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] When this creature enters, suspect it. Create a 2/2 white and blue Detective cre
_h_person_of_interest = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [mkm] When this creature enters, you may sacrifice an artifact. When you do, this crea
_h_cornered_crook = _etb([["damage_any", {"n": 3}]])
# [mkm] Whenever this creature enters or attacks, put a +1/+1 counter on target creature
_h_haazda_vigilante = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] Flying | Whenever this creature attacks, gain control of target permanent you own 
_h_coveted_falcon = _etb([["draw", {"n": 1}]])
# [mkm] Whenever this creature attacks, you may sacrifice an artifact or discard a card.
_h_reckless_detective = _etb([["draw", {"n": 1}], ["add_counters", {"n": 2, "target": "self"}]])
# [mkm] Whenever this creature enters or attacks, you may sacrifice an artifact. If you 
_h_benthic_criminologists = _etb([["draw", {"n": 1}]])
# [mkm] Whenever this creature attacks, you may collect evidence 3. When you do, put a +
_h_sample_collector = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] This creature enters tapped. | Disguise {4}{B}{B} (You may cast this card face dow
_h_alley_assailant = _etb([["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [mkm] Flash | When this enchantment enters, target creature gets -4/-4 until end of turn
_h_soul_enervation = _etb([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [mkm] When this creature dies, it deals 2 damage to any target. | Disguise {2}{B/R}{B/R}
_h_shady_informant = _etb([["damage_any", {"n": 2}]])
# [mkm] When this Case enters, create a 2/1 black Skeleton creature token and suspect it
_h_case_of_the_stashed_skeleton = _etb([["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": []}]])
# [mkm] This creature can't be blocked by creatures with power 3 or greater. | Disguise {1
_h_exit_specialist = _etb([["bounce_to_hand", {}]])
# [mkm] When this enchantment enters, create a 1/1 white Human creature token, a 1/1 blu
_h_a_killer_among_us = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [mkm] When this Case enters, it deals 3 damage to target creature an opponent controls
_h_case_of_the_burning_masks = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [mkm] Disguise {1}{W} (You may cast this card face down for {3} as a 2/2 creature with
_h_forum_familiar = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] Flying | Disguise {1}{U} (You may cast this card face down for {3} as a 2/2 creatu
_h_mistway_spy = _etb([["draw", {"n": 1}]])
# [mkm] When this creature enters and whenever you solve a Case, look at the top six car
_h_case_file_auditor = _etb([["scry", {"n": 6}]])
# [mkm] At the beginning of your end step, if a face-down creature entered the battlefie
_h_tunnel_tipster = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] This creature can't be blocked as long as you've sacrificed an artifact this tur
_h_furtive_courier = _etb([["draw", {"n": 1}]])
# [mkm] When this creature enters, you may sacrifice an artifact or creature. When you d
_h_undercity_eliminator = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [mkm] When this enchantment enters, exile target creature an opponent controls until t
_h_makeshift_binding = _etb([["exile", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 2}]])
# [mkm] Flying, trample | Whenever this creature deals combat damage to a player, you may 
_h_incinerator_of_the_guilty = _etb([["damage_creature", {"n": 1, "target": "each_opp"}]])
# [mkm] At the beginning of combat on your turn, create a 1/1 colorless Thopter artifact
_h_harried_dronesmith = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [mkm] When this enchantment enters, it deals 3 damage to target creature an opponent c
_h_blood_spatter_analysis = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [mkm] Flying, vigilance | At the beginning of your upkeep, investigate once for each opp
_h_wojek_investigator = _etb([["draw", {"n": 1}]])
# [mkm] Flying | When this creature enters, investigate. (Create a Clue token. It's an art
_h_gleaming_geardrake = _etb([["draw", {"n": 1}]])
# [mkm] Prowess, haste | Disguise {5}{R}. This cost is reduced by {1} for each instant and
_h_fugitive_codebreaker = _etb([["draw", {"n": 3}], ["draw", {"n": 4}]])
# [mkm] When this creature enters, investigate. (Create a Clue token. It's an artifact w
_h_persuasive_interrogators = _etb([["draw", {"n": 1}]])
# [mkm] Flying | Disguise {1}{U/B}{U/B} (You may cast this card face down for {3} as a 2/2
_h_faerie_snoop = _etb([["scry", {"n": 2}]])
# [mkm] When this artifact enters, look at the top four cards of your library. Put two o
_h_polygraph_orb = _etb([["scry", {"n": 4}], ["lose_life", {"n": 2, "target": "self"}]])
# [mkm] When this creature enters, surveil 1. (Look at the top card of your library. You
_h_sanitation_automaton = _etb([["scry", {"n": 1}]])
# [mkm] Menace | When this creature enters, target opponent creates two 1/1 white Dog crea
_h_hunted_bonebrute = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}], ["lose_life", {"n": 3, "target": "opp"}]])
# [mkm] Disguise {4}{R} (You may cast this card face down for {3} as a 2/2 creature with
_h_offender_at_large = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [mkm] Flash | Enchant creature | When this Aura enters, untap enchanted creature. It gains
_h_airtight_alibi = _etb([["scry", {"n": 0}]])
# [mkm] Flying, lifelink | Disguise {W/B}{W/B} (You may cast this card face down for {3} a
_h_sanguine_savior = _etb([["scry", {"n": 0}]])
# [mkm] At the beginning of combat on your turn, target creature you control with power 
_h_slimy_dualleech = _etb([["scry", {"n": 0}]])
# [mkm] When this Case enters, search your library for a basic land card, reveal it, put
_h_case_of_the_shattered_pact = _etb([["search_basic_land", {"n": 1}]])
# [mkm] Flying, trample | At the beginning of your end step, target opponent may sacrifice
_h_rakdos__patron_of_chaos = _etb([["draw", {"n": 2}]])
# [mkm] Disguise {5}{G}{G} (You may cast this card face down for {3} as a 2/2 creature w
_h_greenbelt_radical = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [mkm] Whenever this creature deals combat damage to a player, you mill two cards. | {1}{
_h_festerleech = _etb([["mill", {"n": 2, "target": "self"}]])
# [mkm] Flash | Enchant creature | When this Aura enters, enchanted creature gains hexproof 
_h_fae_flight = _etb([["scry", {"n": 0}]])
# [mkm] Enchant creature | When this Aura enters, target creature you control other than e
_h_due_diligence = _etb([["scry", {"n": 0}]])
# [mkm] Deathtouch | At the beginning of your end step, investigate for each opponent who 
_h_teysa__opulent_oligarch = _etb([["draw", {"n": 1}]])
# [mkm] Disguise {5}{G} (You may cast this card face down for {3} as a 2/2 creature with
_h_vengeful_creeper = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [mkm] Deathtouch | When this creature enters or is turned face up, target creature gains
_h_rakish_scoundrel = _etb([["scry", {"n": 0}]])
# [mkm] When this creature enters or is turned face up, create a 1/1 colorless Thopter a
_h_gadget_technician = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [mkm] Flying | When this creature enters, all suspected creatures are no longer suspecte
_h_absolving_lammasu = _etb([["gain_life", {"n": 3}]])
# [mkm] Vigilance | When Alquist Proft enters, investigate. (Create a Clue token. It's an 
_h_alquist_proft__master_sleuth = _etb([["draw", {"n": 1}]])
# [mkm] Flying | Whenever this creature deals combat damage to a player, you gain 1 life a
_h_basilica_stalker = _etb([["gain_life", {"n": 1}], ["scry", {"n": 1}]])
# [mkm] Indestructible | When this creature enters, suspect it. (It has menace and can't b
_h_barbed_servitor = _etb([["draw", {"n": 1}], ["lose_life", {"n": 1, "target": "self"}]])
# [mkm] When this artifact enters, investigate twice. (To investigate, create a Clue tok
_h_detective_s_satchel = _etb([["draw", {"n": 1}]])
# [mkm] Reach | When this creature enters, distribute three +1/+1 counters among one, two,
_h_glint_weaver = _etb([["gain_life", {"n": 2}]])
# [mkm] Enchant land | When this Aura enters, exile target nonland permanent you don't con
_h_buried_in_the_garden = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [otj] When this creature enters, you may sacrifice a creature. When you do, target pla
_h_unscrupulous_contractor = _etb([["draw", {"n": 2}]])
# [otj] When this creature enters, create a 1/1 red Mercenary creature token with "{T}: 
_h_prosperity_tycoon = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] When Ertha Jo enters, create a 1/1 red Mercenary creature token with "{T}: Targe
_h_ertha_jo__frontier_mentor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Deathtouch | Whenever this creature deals combat damage to a player, if you've com
_h_servant_of_the_stinger = _etb([["draw", {"n": 1}]])
# [otj] Flash | At the beginning of your end step, if you haven't cast a spell from your h
_h_wrangler_of_the_damned = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["flying"]}]])
# [otj] When this creature enters, if you've cast two or more spells this turn, draw a c
_h_loan_shark = _etb([["draw", {"n": 1}]])
# [otj] Other outlaws you control have haste. (Assassins, Mercenaries, Pirates, Rogues, 
_h_hellspur_posse_boss = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] When this creature enters, if you control a creature with power 4 or greater, dr
_h_beastbond_outcaster = _etb([["draw", {"n": 1}]])
# [otj] Flying | Whenever you cast your second spell each turn, put a +1/+1 counter on Kra
_h_kraum__violent_cacophony = _etb([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] When this creature enters, you gain 2 life. | {T}: Add one mana of any color.
_h_oasis_gardener = _etb([["gain_life", {"n": 2}]])
# [otj] Whenever this creature attacks while saddled, creatures you control gain trample
_h_drover_grizzly = _etb([["scry", {"n": 0}]])
# [otj] Vigilance | Whenever this creature attacks while saddled, put a +1/+1 counter on t
_h_giant_beaver = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] When this creature enters, surveil 2. (Look at the top two cards of your library
_h_sterling_hound = _etb([["scry", {"n": 2}]])
# [otj] Whenever you commit a crime, you may pay {1}. If you do, look at the top two car
_h_marchesa__dealer_of_death = _etb([["scry", {"n": 2}]])
# [otj] When this creature enters, look at the top five cards of your library. You may r
_h_frontier_seeker = _etb([["scry", {"n": 5}]])
# [otj] Whenever this creature attacks while saddled, it gets +1/+2 until end of turn. T
_h_rambling_possum = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] When this creature enters, creatures you control get +1/+1 and gain vigilance un
_h_stagecoach_security = _etb([["add_counters", {"n": 1, "target": "all_friendly"}]])
# [otj] When this creature enters, create a 1/1 red Mercenary creature token with "{T}: 
_h_prickly_pair = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Flash | When this creature enters, target creature an opponent controls gets -2/-2
_h_ambush_gigapede = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [otj] First strike, lifelink | Whenever this creature attacks while saddled, create a 3/
_h_seraphic_steed = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": ["flying"]}]])
# [otj] Whenever this creature attacks, create a 3/1 red Dinosaur creature token if you 
_h_scalestorm_summoner = _etb([["create_token", {"count": 1, "power": "3", "toughness": "1", "keywords": []}]])
# [otj] Flying, vigilance | At the beginning of your end step, if you haven't cast a spell
_h_jem_lightfoote__sky_explorer = _etb([["draw", {"n": 1}]])
# [otj] When this creature dies, create a 1/1 red Mercenary creature token with "{T}: Ta
_h_nezumi_linkbreaker = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Trample | When this creature enters, if you control another outlaw, create a Treas
_h_mine_raider = _etb([["create_treasure", {"n": 1}]])
# [otj] Whenever one or more tokens your opponents control enter, for each of them, crea
_h_kambal__profiteering_mayor = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [otj] Lifelink | When this creature dies, draw a card.
_h_outlaw_medic = _etb([["draw", {"n": 1}]])
# [otj] Whenever this creature attacks while saddled, it gets +1/+2 and gains menace unt
_h_quilled_charger = _etb([["scry", {"n": 0}]])
# [otj] Vigilance | Whenever this creature attacks while saddled, create a 1/1 white Sheep
_h_bridled_bighorn = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [otj] When Rakdos Joins Up enters, return target creature card from your graveyard to 
_h_rakdos_joins_up = _etb([["return_gy_to_bf", {"filter_type": "creature"}]])
# [otj] Lifelink | At the beginning of your end step, if you haven't cast a spell from you
_h_prairie_dog = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Flying, vigilance, ward {2} | Whenever you commit a crime, surveil 2. This ability
_h_marauding_sphinx = _etb([["scry", {"n": 2}]])
# [otj] Flash | Flying | When this creature enters, you gain 2 life and scry 1. (Look at the
_h_holy_cow = _etb([["gain_life", {"n": 2}], ["scry", {"n": 1}]])
# [otj] Flying, haste | Whenever you cast your second spell each turn, investigate. (Creat
_h_malcolm__the_eyes = _etb([["draw", {"n": 1}]])
# [otj] When this creature enters, you may search your library for a basic land card or 
_h_silver_deputy = _etb([["search_basic_land", {"n": 1}]])
# [otj] When this creature enters, target player draws a card and loses 1 life.
_h_vault_plunderer = _etb([["draw", {"n": 1}]])
# [otj] Menace | Whenever you cast your second spell each turn, you may sacrifice an artif
_h_breeches__the_blastmaker = _etb([["draw", {"n": 1}]])
# [otj] When this creature enters, search your library for a basic land card or a Desert
_h_outcaster_greenblade = _etb([["search_basic_land", {"n": 1}]])
# [otj] This creature can't be blocked if you've committed a crime this turn. (Targeting
_h_nimble_brigand = _etb([["draw", {"n": 1}]])
# [otj] When this Equipment enters, create a Treasure token. (It's an artifact with "{T}
_h_gold_pan = _etb([["create_treasure", {"n": 1}]])
# [otj] When this creature enters, if a creature died this turn, create a 2/2 blue and b
_h_rictus_robber = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [otj] When this enchantment enters, exile target nonland permanent an opponent control
_h_lassoed_by_the_law = _etb([["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] At the beginning of your end step, if you haven't cast a spell from your hand th
_h_emergent_haunting = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] When this creature enters, create a 2/2 blue and black Zombie Rogue creature tok
_h_outlaw_stitcher = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [otj] Whenever you cast your second spell each turn, put a +1/+1 counter on this creat
_h_razzle_dazzler = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] When this creature enters, you may discard a card. If you do, draw a card.
_h_discerning_peddler = _etb([["draw", {"n": 1}]])
# [otj] Whenever another outlaw you control enters, Vial Smasher deals 1 damage to targe
_h_vial_smasher__gleeful_grenadier = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [otj] Flying | When this creature enters, put a +1/+1 counter on another target creature
_h_sterling_supplier = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}]])
# [otj] Whenever you commit a crime, put a +1/+1 counter on Vadmir. This ability trigger
_h_vadmir__new_blood = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Whenever this creature attacks while saddled, put a +1/+1 counter on each other 
_h_bounding_felidar = _etb([["gain_life", {"n": 1}], ["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [otj] Whenever you commit a crime, each opponent mills three cards. This ability trigg
_h_deepmuck_desperado = _etb([["mill", {"n": 3, "target": "self"}]])
# [otj] Reach | Whenever you commit a crime, look at the top five cards of your library. Y
_h_freestrider_lookout = _etb([["scry", {"n": 5}]])
# [otj] When this creature enters, mill three cards. Put a land card from among the mill
_h_patient_naturalist = _etb([["mill", {"n": 3, "target": "self"}], ["create_treasure", {"n": 1}]])
# [otj] Whenever you commit a crime, put a +1/+1 counter on this creature. This ability 
_h_blood_hustler = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Whenever this creature attacks while saddled, it gains first strike until end of
_h_trained_arynx = _etb([["scry", {"n": 1}]])
# [otj] During your turn, outlaws you control have first strike. (Assassins, Mercenaries
_h_at_knifepoint = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Flying | When this creature dies, create a 1/1 red Mercenary creature token with "
_h_wanted_griffin = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Whenever this Vehicle attacks, create a Treasure token for each creature that cr
_h_luxurious_locomotive = _etb([["create_treasure", {"n": 1}]])
# [otj] Whenever you commit a crime, put a +1/+1 counter on Lazav. Then you may exile a 
_h_lazav__familiar_stranger = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Trample | When this creature enters, you gain 3 life. | Plot {3}{G} (You may pay {3}
_h_spinewoods_paladin = _etb([["gain_life", {"n": 3}]])
# [otj] When Fortune enters, scry 2. | Whenever Fortune attacks while saddled, at end of c
_h_fortune__loyal_steed = _etb([["scry", {"n": 2}]])
# [otj] When this enchantment enters, create a 1/1 red Mercenary creature token with "{T
_h_rakish_crew = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Lifelink | When this creature enters, target player mills two cards. (They put the
_h_desperate_bloodseeker = _etb([["mill", {"n": 2, "target": "self"}]])
# [otj] Whenever one or more tokens you control enter, create a 1/1 black Vampire Rogue 
_h_baron_bertram_graywater = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["lifelink"]}]])
# [otj] Reach | Whenever you cast your second spell each turn, this creature deals 2 damag
_h_iron_fist_pulverizer = _etb([["damage_player", {"n": 2, "target": "opp"}], ["scry", {"n": 1}]])
# [otj] Whenever you cast your second spell each turn, create a 1/1 red Mercenary creatu
_h_brimstone_roundup = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Deathtouch | Whenever a nontoken creature an opponent controls dies, you may pay {
_h_vraska__the_silencer = _etb([["scry", {"n": 0}]])
# [otj] Flying | Whenever you commit a crime, each opponent loses 1 life and you gain 1 li
_h_raven_of_fell_omens = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [otj] Whenever this creature attacks, target creature defending player controls gets -
_h_spring_splasher = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [otj] Flash | Flying, lifelink | When this creature enters, destroy target creature an opp
_h_rooftop_assassin = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [otj] At the beginning of combat on your turn, put a +1/+1 counter on target creature.
_h_ornery_tumblewagg = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Whenever you commit a crime, exile up to one target black card from your graveya
_h_kaervek__the_punisher = _etb([["lose_life", {"n": 2, "target": "self"}]])
# [otj] You may cast this spell as though it had flash if you pay {2} more to cast it. | W
_h_mystical_tether = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [big] At the beginning of combat on your turn, draw a card. Then you may exile an arti
_h_nexus_of_becoming = _etb([["draw", {"n": 1}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [big] When this enchantment enters, you draw three cards, gain 6 life, and create thre
_h_greed_s_gambit = _etb([["draw", {"n": 3}], ["create_token", {"count": 3, "power": "2", "toughness": "1", "keywords": ["flying"]}], ["scry", {"n": 0}]])
# [big] Trample | When this creature enters, create two Food tokens. (They're artifacts wi
_h_bristlebud_farmer = _etb([["gain_life", {"n": 3}], ["mill", {"n": 3, "target": "self"}]])
# [big] Ward {1} | At the beginning of your upkeep, exile the top X cards of your library,
_h_loot__the_key_to_everything = _etb([["mill", {"n": 1, "target": "self"}]])
# [big] Menace | At the beginning of your upkeep, you may create a Treasure token. When yo
_h_generous_plunderer = _etb([["create_treasure", {"n": 1}]])
# [big] When this artifact enters, if you cast it, exile target artifact or land. | This a
_h_territory_forge = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [blb] Flying | When this creature enters, put a +1/+1 counter on target creature you con
_h_pileated_provisioner = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Whenever you expend 4, this creature gains indestructible until end of turn. (Yo
_h_bark_knuckle_boxer = _etb([["scry", {"n": 0}]])
# [blb] Trample | Whenever you expend 4, this creature gets +2/+1 until end of turn. (You 
_h_junkblade_bruiser = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [blb] Flying | At the beginning of your end step, if you gained or lost life this turn, 
_h_starlit_soothsayer = _etb([["scry", {"n": 1}]])
# [blb] Trample | Whenever you expend 4, target creature you control gets +1/+1 and gains 
_h_roughshod_duo = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] Offspring {1}{U} (You may pay an additional {1}{U} as you cast this spell. If yo
_h_splash_lasher = _etb([["scry", {"n": 0}]])
# [blb] Flying | Whenever this creature or another creature you control with flying enters
_h_plumecreed_mentor = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Flying, vigilance | At the beginning of your end step, if you gained or lost life 
_h_starseer_mentor = _etb([["lose_life", {"n": 3, "target": "opp"}]])
# [blb] When this creature enters, mill three cards. When you do, target creature an opp
_h_wick_s_patrol = _etb([["mill", {"n": 3, "target": "self"}]])
# [blb] As an additional cost to cast this spell, you may sacrifice any number of nonlan
_h_rottenmouth_viper = _etb([["lose_life", {"n": 4, "target": "opp"}]])
# [blb] Offspring {3} (You may pay an additional {3} as you cast this spell. If you do, 
_h_thornplate_intimidator = _etb([["lose_life", {"n": 3, "target": "opp"}]])
# [blb] Flying | When this creature enters, each opponent loses 2 life and you gain 2 life
_h_glidedive_duo = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [blb] Whenever this creature attacks, defending player loses 1 life and you gain 1 lif
_h_agate_blade_assassin = _etb([["gain_life", {"n": 1}]])
# [blb] Trample | When Hugs enters, exile the top X cards of your library. Until the end o
_h_hugs__grisly_guardian = _etb([["mill", {"n": 1, "target": "self"}]])
# [blb] Deathtouch | When this creature enters, you may mill two cards. (You may put the t
_h_daggerfang_duo = _etb([["mill", {"n": 2, "target": "self"}]])
# [blb] Trample | When this creature enters, put a +1/+1 counter on it for each other Squi
_h_honored_dreyleader = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] When this creature enters, create two 1/1 white Rabbit creature tokens.
_h_head_of_the_homestead = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [blb] Valiant ? Whenever this creature becomes the target of a spell or ability you co
_h_heartfire_hero = _etb([["damage_any", {"n": 2}]])
# [blb] Offspring {2} (You may pay an additional {2} as you cast this spell. If you do, 
_h_bushy_bodyguard = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 3}]])
# [blb] Whenever this creature or another Rabbit you control enters, target creature you
_h_harvestrite_host = _etb([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] Flying | At the beginning of your end step, if you gained or lost life this turn, 
_h_star_charter = _etb([["scry", {"n": 4}]])
# [blb] Menace | Whenever you expend 4, this creature deals 2 damage to each opponent. (Yo
_h_teapot_slinger = _etb([["damage_player", {"n": 2, "target": "opp"}]])
# [blb] Reach | When this creature enters, you may forage. If you do, draw a card. (To for
_h_treetop_sentries = _etb([["draw", {"n": 1}], ["gain_life", {"n": 3}]])
# [blb] At the beginning of combat on your turn, you may forage. (Exile three cards from
_h_corpseberry_cultivator = _etb([["gain_life", {"n": 3}]])
# [blb] Whenever this creature deals damage to an opponent, draw a card.
_h_thieving_otter = _etb([["draw", {"n": 1}]])
# [blb] Whenever this creature attacks, if another creature entered the battlefield unde
_h_waterspout_warden = _etb([["scry", {"n": 0}]])
# [blb] Whenever you cast a noncreature spell, put a +1/+1 counter on this creature.
_h_tempest_angler = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Whenever you cast a spell, if it's the first instant spell, the first sorcery sp
_h_alania__divergent_storm = _etb([["draw", {"n": 1}]])
# [blb] When this artifact enters, create a Food token. (It's an artifact with "{2}, {T}
_h_bumbleflower_s_sharepot = _etb([["gain_life", {"n": 3}]])
# [blb] Offspring {2} (You may pay an additional {2} as you cast this spell. If you do, 
_h_steampath_charger = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [blb] Offspring {3} (You may pay an additional {3} as you cast this spell. If you do, 
_h_finch_formation = _etb([["scry", {"n": 0}]])
# [blb] When this creature enters, put a +1/+1 counter on target creature and you gain 1
_h_sunshower_druid = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 1}]])
# [blb] Offspring {1} (You may pay an additional {1} as you cast this spell. If you do, 
_h_intrepid_rabbit = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] (Gain the next level as a sorcery to add its ability.) | Whenever a creature you c
_h_gossip_s_talent = _etb([["scry", {"n": 1}]])
# [blb] Whenever you expend 4, put a +1/+1 counter on this creature. (You expend 4 as yo
_h_wandertale_mentor = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] (Gain the next level as a sorcery to add its ability.) | When this Class enters, c
_h_blacksmith_s_talent = _etb([["add_counters", {"n": 1, "target": "all_friendly"}]])
# [blb] Trample | When this creature enters, choose target creature. If that creature's po
_h_reptilian_recruiter = _etb([["scry", {"n": 0}]])
# [blb] At the beginning of combat on your turn, each opponent loses 1 life and you gain
_h_sinister_monolith = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [blb] (Gain the next level as a sorcery to add its ability.) | Whenever one or more crea
_h_scavenger_s_talent = _etb([["mill", {"n": 2, "target": "self"}]])
# [blb] Whenever you expend 4, Raccoons you control get +1/+1 and gain vigilance until e
_h_brambleguard_veteran = _etb([["scry", {"n": 0}]])
# [blb] At the beginning of your upkeep, return another creature you control to its owne
_h_mistbreath_elder = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Flash | Enchant creature | When this Aura enters, draw a card. | Enchanted creature ge
_h_feather_of_flight = _etb([["draw", {"n": 1}]])
# [blb] Flying | Whenever this creature attacks, you gain 1 life.
_h_moonrise_cleric = _etb([["gain_life", {"n": 1}]])
# [blb] When this creature enters or dies, create a Food token. (It's an artifact with "
_h_vinereap_mentor = _etb([["gain_life", {"n": 3}]])
# [blb] Flying | Whenever this creature attacks, target creature you control without flyin
_h_seedpod_squire = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Vigilance | When Byrke enters, put a +1/+1 counter on each of up to two target cre
_h_byrke__long_ear_of_the_law = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [blb] When this artifact enters, you may search your library for a basic land card, re
_h_fountainport_bell = _etb([["search_basic_land", {"n": 1}]])
# [blb] When this creature enters, create a Food token. | Whenever you expend 4, this crea
_h_bakersbane_duo = _etb([["gain_life", {"n": 3}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] When this creature enters, draw a card, then discard a card.
_h_bellowing_crier = _etb([["draw", {"n": 1}]])
# [blb] Whenever you attack, target creature you control gets +1/+0 until end of turn. I
_h_hazardroot_herbalist = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] When this creature enters, exile target creature an opponent controls until this
_h_driftgloom_coyote = _etb([["exile", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] At the beginning of your upkeep, surveil 1. (Look at the top card of your librar
_h_mindwhisker = _etb([["scry", {"n": 1}]])
# [dsk] Flying | Whenever this creature attacks, target creature defending player controls
_h_fear_of_falling = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [dsk] When this creature dies, each player draws a card.
_h_friendly_teddy = _etb([["draw", {"n": 1}]])
# [dsk] Deathtouch | Whenever this creature attacks, another target creature you control g
_h_flesh_burrower = _etb([["scry", {"n": 0}]])
# [dsk] When Marina Vendrell's Grimoire enters, if you cast it, draw five cards. | You hav
_h_marina_vendrell_s_grimoire = _etb([["draw", {"n": 5}]])
# [dsk] When this creature enters, it deals 4 damage to each opponent. | Delirium ? Whenev
_h_fear_of_burning_alive = _etb([["damage_player", {"n": 4, "target": "opp"}]])
# [dsk] When this creature enters, you may sacrifice another creature or enchantment. Wh
_h_boilerbilges_ripper = _etb([["damage_any", {"n": 2}]])
# [dsk] When this creature dies, manifest dread. (Look at the top two cards of your libr
_h_innocuous_rat = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_scrabbling_skullcrab = _etb([["mill", {"n": 2, "target": "self"}]])
# [dsk] Ward {2} (Whenever this enchantment becomes the target of a spell or ability an 
_h_trapped_in_the_screen = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_dashing_bloodsucker = _etb([["scry", {"n": 0}]])
# [dsk] Flying, vigilance | Eerie ? Whenever an enchantment you control enters and wheneve
_h_erratic_apparition = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dsk] Survival ? At the beginning of your second main phase, if this creature is tappe
_h_cautious_survivor = _etb([["gain_life", {"n": 2}]])
# [dsk] Whenever this creature attacks, another target creature you control gets +1/+0 a
_h_hardened_escort = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [dsk] Deathtouch | Whenever this creature enters or attacks, each opponent loses 2 life.
_h_shroudstomper = _etb([["draw", {"n": 1}], ["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [dsk] When this creature dies, it deals 1 damage to any target and you gain 1 life.
_h_fear_of_lost_teeth = _etb([["damage_any", {"n": 1}], ["gain_life", {"n": 1}]])
# [dsk] Haste | Whenever you attack, create a 1/1 red Gremlin creature token.
_h_razorkin_hordecaller = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] When this Equipment enters, manifest dread, then attach this Equipment to that c
_h_conductive_machete = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Vigilance | Whenever this creature attacks, surveil 1. (Look at the top card of yo
_h_fear_of_surveillance = _etb([["scry", {"n": 1}]])
# [dsk] Survival ? At the beginning of your second main phase, if Kona is tapped, you ma
_h_a_kona__rescue_beastie = _etb([["draw", {"n": 1}]])
# [dsk] Ward {2} | At the beginning of your upkeep, each player draws two cards. | Delirium 
_h_winter__misanthropic_guide = _etb([["draw", {"n": 2}]])
# [dsk] When this enchantment enters, manifest dread. | Whenever a face-down permanent you
_h_threats_around_every_corner = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Flash | When this creature enters, counter target spell. Its controller manifests 
_h_fear_of_impostors = _etb([["scry", {"n": 0}]])
# [dsk] When this enchantment enters, you may sacrifice another enchantment or creature.
_h_disturbing_mirth = _etb([["draw", {"n": 2}]])
# [dsk] When this creature enters, create a 1/1 white Glimmer enchantment creature token
_h_tunnel_surveyor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Survival ? At the beginning of your second main phase, if this creature is tappe
_h_defiant_survivor = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] When this creature enters or dies, surveil 1. (Look at the top card of your libr
_h_wary_watchdog = _etb([["scry", {"n": 1}]])
# [dsk] When this creature enters, each player discards a card. If you discarded a card 
_h_fanatic_of_the_harrowing = _etb([["draw", {"n": 1}], ["discard", {"n": 1, "target": "opp"}]])
# [dsk] When this Equipment enters, manifest dread, then attach this Equipment to that c
_h_cursed_windbreaker = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] As an additional cost to cast this spell, exile a creature you control. | Flying | W
_h_fear_of_abduction = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [dsk] When this Equipment enters, create a 1/1 white Glimmer enchantment creature toke
_h_glimmerlight = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_victor__valgavoth_s_seneschal = _etb([["discard", {"n": 1, "target": "opp"}], ["scry", {"n": 2}]])
# [dsk] When this Equipment enters, manifest dread, then attach this Equipment to that c
_h_killer_s_mask = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Flying | Eerie ? Whenever an enchantment you control enters and whenever you fully
_h_skullsnap_nuisance = _etb([["scry", {"n": 1}]])
# [dsk] This creature can't be blocked by Glimmers. | Survival ? At the beginning of your 
_h_cynical_loner = _etb([["draw", {"n": 1}]])
# [dsk] Flash | Whenever this creature attacks, surveil 1. (Look at the top card of your l
_h_appendage_amalgam = _etb([["scry", {"n": 1}]])
# [dsk] When this creature dies, create a Treasure token. (It's an artifact with "{T}, S
_h_piggy_bank = _etb([["create_treasure", {"n": 1}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_gremlin_tamer = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_balemurk_leech = _etb([["lose_life", {"n": 1, "target": "opp"}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_infernal_phantom = _etb([["add_counters", {"n": 2, "target": "self"}], ["damage_any", {"n": 2}]])
# [dsk] Flash | When this enchantment enters, manifest dread. (Look at the top two cards o
_h_growing_dread = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] When this creature enters, manifest dread. (Look at the top two cards of your li
_h_unsettling_twins = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Flying | When this creature enters, you may discard any number of cards. When you 
_h_miasma_demon = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [dsk] Reach | When this creature dies, you gain 2 life.
_h_grasping_longneck = _etb([["gain_life", {"n": 2}]])
# [dsk] Ward {2} (Whenever this creature becomes the target of a spell or ability an opp
_h_lionheart_glimmer = _etb([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [dsk] Eerie ? Whenever an enchantment you control enters and whenever you fully unlock
_h_cult_healer = _etb([["scry", {"n": 0}]])
# [dsk] Flash | Eerie ? Whenever an enchantment you control enters and whenever you fully 
_h_entity_tracker = _etb([["draw", {"n": 1}]])
# [dsk] Survival ? At the beginning of your second main phase, if this creature is tappe
_h_glimmer_seeker = _etb([["draw", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] When this creature dies, look at the top five cards of your library. You may rev
_h_living_phone = _etb([["scry", {"n": 5}]])
# [dsk] When this creature enters, search your library for a basic land card, reveal it,
_h_spineseeker_centipede = _etb([["search_basic_land", {"n": 1}]])
# [dsk] Haste | Survival ? At the beginning of your second main phase, if this creature is
_h_rootwise_survivor = _etb([["scry", {"n": 0}]])
# [dsk] {1}{B}, Sacrifice another creature or enchantment: This creature gains indestruc
_h_popular_egotist = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [dsk] Flying | When this creature enters, target creature gets +2/+4 until end of turn.
_h_friendly_ghost = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [dsk] When this creature dies, manifest dread. (Look at the top two cards of your libr
_h_bashful_beastie = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Survival ? At the beginning of your second main phase, if this creature is tappe
_h_shrewd_storyteller = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dsk] Whenever this creature attacks, you may have it get +4/+0 until end of turn. If 
_h_attack_in_the_box = _etb([["add_counters", {"n": 4, "target": "self"}]])
# [dsk] Whenever this Vehicle attacks, you may mill two cards. | Whenever one or more land
_h_hedge_shredder = _etb([["mill", {"n": 2, "target": "self"}]])
# [dsk] Whenever you attack, target attacking creature gets +1/+0 and gains first strike
_h_most_valuable_slayer = _etb([["scry", {"n": 0}]])
# [dsk] Whenever this creature attacks, tap any number of untapped creatures you control
_h_orphans_of_the_wheat = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dsk] When this creature enters, tap up to one target creature. If an opponent control
_h_fear_of_immobility = _etb([["scry", {"n": 0}]])
# [fdn] Alliance ? Whenever another creature you control enters, this creature gains dea
_h_venom_connoisseur = _etb([["scry", {"n": 0}]])
# [fdn] Landfall ? Whenever a land you control enters, you gain 1 life and draw a card.
_h_tatyova__benthic_druid = _etb([["draw", {"n": 1}], ["gain_life", {"n": 1}]])
# [fdn] Flying | Whenever this creature attacks, you may sacrifice another creature. If yo
_h_high_society_hunter = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [fdn] Flying | When this creature enters, search your library for a card, put it into yo
_h_rune_scarred_demon = _etb([["draw", {"n": 1}]])
# [fdn] Whenever you cast a noncreature spell, this creature gets +3/+0 until end of tur
_h_crackling_cyclops = _etb([["add_counters", {"n": 3, "target": "self"}]])
# [fdn] Landfall ? Whenever a land you control enters, equipped creature gets +2/+2 unti
_h_adventuring_gear = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [fdn] Whenever another creature you control enters, put a +1/+1 counter on that creatu
_h_good_fortune_unicorn = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Defender | When this creature dies, create a Treasure token. (It's an artifact wit
_h_gleaming_barrier = _etb([["create_treasure", {"n": 1}]])
# [fdn] Instant and sorcery spells you cast cost {1} less to cast. | Whenever you cast an 
_h_archmage_of_runes = _etb([["draw", {"n": 1}]])
# [fdn] Lifelink (Damage dealt by this creature also causes you to gain that much life.)
_h_felidar_savior = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [fdn] When this creature enters, each opponent discards a card.
_h_burglar_rat = _etb([["discard", {"n": 1, "target": "opp"}]])
# [fdn] When this creature enters, create a 4/4 red Dragon creature token with flying.
_h_dragon_trainer = _etb([["create_token", {"count": 1, "power": "4", "toughness": "4", "keywords": ["flying"]}]])
# [fdn] Whenever this creature attacks, you may sacrifice another creature. If you do, d
_h_vampire_gourmand = _etb([["draw", {"n": 1}]])
# [fdn] When this creature enters, it deals 1 damage to any target.
_h_skeleton_archer = _etb([["damage_any", {"n": 1}]])
# [fdn] Whenever you attack, target creature you control gets +1/+0 and gains menace unt
_h_battlesong_berserker = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [fdn] At the beginning of your upkeep, create a token that's a copy of another target 
_h_extravagant_replication = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [fdn] When this creature enters, if you control another Elf, create a 1/1 green Elf Wa
_h_dwynen_s_elite = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] Flying | Whenever you cast a spell, put a +1/+1 counter on Ramos for each of that 
_h_ramos__dragon_engine = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Whenever another creature you control dies, draw a card if it was attacking. Oth
_h_garna__bloodfist_of_keld = _etb([["damage_player", {"n": 1, "target": "opp"}], ["draw", {"n": 1}]])
# [fdn] When this creature enters or dies, surveil 1. (Look at the top card of your libr
_h_wary_thespian = _etb([["scry", {"n": 1}]])
# [fdn] Flash | When this enchantment enters, exile up to one target nonland permanent an 
_h_prayer_of_binding = _etb([["gain_life", {"n": 2}]])
# [fdn] Whenever this creature or another creature you control dies, target opponent los
_h_vengeful_bloodwitch = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [fdn] Flying | When this creature enters, draw a card, then discard a card.
_h_icewind_elemental = _etb([["draw", {"n": 1}]])
# [fdn] Whenever you cast an instant or sorcery spell, create a 5/5 red Dragon creature 
_h_rite_of_the_dragoncaller = _etb([["create_token", {"count": 1, "power": "5", "toughness": "5", "keywords": ["flying"]}]])
# [fdn] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_cat_collector = _etb([["gain_life", {"n": 3}]])
# [fdn] As an additional cost to cast this spell, sacrifice a creature. | Flying | When this
_h_arbiter_of_woe = _etb([["draw", {"n": 1}], ["discard", {"n": 1, "target": "opp"}]])
# [fdn] Deathtouch (Any amount of damage this deals to a creature is enough to destroy i
_h_vile_entomber = _etb([["draw", {"n": 1}]])
# [fdn] When this creature enters, you may search your library for a basic land card, re
_h_campus_guide = _etb([["search_basic_land", {"n": 1}]])
# [fdn] Flying | Whenever one or more creatures you control attack, you gain 1 life for ea
_h_ancestor_dragon = _etb([["gain_life", {"n": 1}]])
# [fdn] Lifelink (Damage dealt by this creature also causes you to gain that much life.)
_h_guarded_heir = _etb([["create_token", {"count": 2, "power": "3", "toughness": "3", "keywords": []}]])
# [fdn] Whenever a Gate you control enters, this creature can't be blocked this turn. | Wh
_h_gateway_sneak = _etb([["draw", {"n": 1}]])
# [fdn] Flying | Double strike (This creature deals both first-strike and regular combat d
_h_drogskol_reaver = _etb([["draw", {"n": 1}]])
# [fdn] Flash (You may cast this spell any time you could cast an instant.) | When this en
_h_stasis_snare = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [fdn] Flying | Whenever another Angel you control enters, put a +1/+1 counter on this cr
_h_youthful_valkyrie = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Landfall ? Whenever a land you control enters, this creature deals 1 damage to e
_h_spitfire_lagac = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [fdn] At the beginning of combat on your turn, you may have target creature get +2/+0 
_h_battle_rattle_shaman = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [fdn] Flash (You may cast this spell any time you could cast an instant.) | When this cr
_h_burrog_befuddler = _etb([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [fdn] Whenever this creature or another Vampire you control dies, you may pay {B}. If 
_h_kalastria_highborn = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [fdn] When this creature enters, you may sacrifice a land. If you do, search your libr
_h_springbloom_druid = _etb([["search_basic_land", {"n": 2}]])
# [fdn] Flying | Whenever another creature you control enters, you gain 1 life.
_h_dazzling_angel = _etb([["gain_life", {"n": 1}]])
# [fdn] Trample (This creature can deal excess combat damage to the player or planeswalk
_h_eager_trufflesnout = _etb([["gain_life", {"n": 3}]])
# [fdn] Whenever you gain life, each opponent loses 1 life.
_h_marauding_blight_priest = _etb([["lose_life", {"n": 1, "target": "opp"}]])
# [fdn] Flying | Double strike (This creature deals both first-strike and regular combat d
_h_terror_of_mount_velus = _etb([["scry", {"n": 0}]])
# [fdn] Enchant land | When this Aura enters, put a +1/+1 counter on target creature you c
_h_new_horizons = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] When this creature enters, surveil 3. (Look at the top three cards of your libra
_h_cephalid_inkmage = _etb([["scry", {"n": 3}]])
# [fdn] Flying | When this creature enters, if an opponent lost life this turn, each oppon
_h_bloodtithe_collector = _etb([["discard", {"n": 1, "target": "opp"}]])
# [fdn] Whenever you gain life, put a +1/+1 counter on this creature.
_h_ajani_s_pridemate = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Whenever this creature attacks, creatures you control get +1/+1 until end of tur
_h_dauntless_veteran = _etb([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Flying | Whenever you gain life, put a +1/+1 counter on this creature. | Whenever yo
_h_exemplar_of_light = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] At the beginning of combat on your turn, put a +1/+1 counter on each of up to tw
_h_zimone__paradox_sculptor = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [fdn] Flying | When this creature enters or dies, mill two cards. (Put the top two cards
_h_crow_of_dark_tidings = _etb([["mill", {"n": 2, "target": "self"}]])
# [fdn] Indestructible (Damage and effects that say "destroy" don't destroy this creatur
_h_predator_ooze = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_corsair_captain = _etb([["create_treasure", {"n": 1}]])
# [fdn] At the beginning of combat on your turn, if you control another creature with po
_h_nessian_hornbeetle = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Menace | When this creature enters, create two 1/1 black Rat creature tokens with 
_h_redcap_gutter_dweller = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [fdn] When this creature enters, return target permanent card from your graveyard to y
_h_elvish_regrower = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Flying | Ward?{3}, Pay 3 life. | Whenever you cast a noncreature spell, create X 1/1
_h_ovika__enigma_goliath = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] First strike (This creature deals combat damage before creatures without first s
_h_halana_and_alena__partners = _etb([["scry", {"n": 0}]])
# [fdn] Whenever you gain life, put a +1/+1 counter on this creature. | When this creature
_h_fiendish_panda = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Whenever this creature attacks, each opponent loses 1 life and you gain 1 life.
_h_sanguine_syphoner = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [fdn] Flying | This creature can't block. | When this creature enters, return target creat
_h_vampire_soulcaller = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Kicker {3}{B} (You may pay an additional {3}{B} as you cast this spell.) | Lifelin
_h_nullpriest_of_oblivion = _etb([["return_gy_to_bf", {"filter_type": "creature"}]])
# [fdn] Flying | Whenever this creature deals combat damage to a player, you may destroy t
_h_trygon_predator = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] At the beginning of your end step, if an opponent lost life this turn, put a +1/
_h_stromkirk_bloodthief = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Flying | Whenever this creature attacks, you gain 2 life.
_h_herald_of_faith = _etb([["gain_life", {"n": 2}]])
# [fdn] Flying | When this creature enters, mill three cards. (Put the top three cards of 
_h_billowing_shriekmass = _etb([["mill", {"n": 3, "target": "self"}]])
# [fdn] Trample (This creature can deal excess combat damage to the player or planeswalk
_h_pelakka_wurm = _etb([["gain_life", {"n": 7}], ["draw", {"n": 1}]])
# [fdn] Flying | When this creature enters, you may search your library for an artifact ca
_h_hoarding_dragon = _etb([["draw", {"n": 1}]])
# [fdn] Whenever you gain life, put a +1/+1 counter on this creature. | As long as you hav
_h_twinblade_paladin = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] When this creature dies, create a 1/1 black and green Insect creature token with
_h_infestation_sage = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [fdn] Flying | When this creature enters, you gain 1 life and draw a card.
_h_inspiring_overseer = _etb([["draw", {"n": 1}], ["gain_life", {"n": 1}]])
# [fdn] When this creature enters, destroy target nonland permanent an opponent controls
_h_meteor_golem = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Trample (This creature can deal excess combat damage to the player or planeswalk
_h_beast_kin_ranger = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] When this creature dies, create two 2/2 black Zombie creature tokens.
_h_maalfeld_twins = _etb([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": []}]])
# [fdn] Whenever a nontoken creature you control dies, this creature deals 1 damage to y
_h_midnight_reaper = _etb([["draw", {"n": 1}]])
# [fdn] Flying | Whenever this creature deals combat damage to a player, each player disca
_h_dragon_mage = _etb([["draw", {"n": 7}], ["discard", {"n": 1, "target": "opp"}]])
# [fdn] At the beginning of your upkeep, you draw a card and you lose 1 life.
_h_phyrexian_arena = _etb([["draw", {"n": 1}], ["lose_life", {"n": 1, "target": "self"}]])
# [fdn] Prowess (Whenever you cast a noncreature spell, this creature gets +1/+1 until e
_h_lightshell_duo = _etb([["scry", {"n": 2}]])
# [fdn] Flying | When this creature enters, you gain 2 life for each Gate you control.
_h_archway_angel = _etb([["gain_life", {"n": 2}]])
# [fdn] Whenever you cast a creature spell, create a 3/3 green Beast creature token. | Whe
_h_primeval_bounty = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 3}]])
# [fdn] Reach (This creature can block creatures with flying.) | Landfall ? Whenever a lan
_h_elfsworn_giant = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] When this creature enters, exile up to two target cards from a single graveyard.
_h_soul_shackled_zombie = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [fdn] Flying | When this creature enters, you gain 2 life and draw two cards.
_h_cloudblazer = _etb([["draw", {"n": 2}], ["gain_life", {"n": 2}]])
# [fdn] Whenever this creature attacks, each opponent loses 1 life.
_h_pulse_tracker = _etb([["lose_life", {"n": 1, "target": "opp"}]])
# [fdn] Flying | Whenever this creature becomes tapped, exile up to one target card from a
_h_immersturm_predator = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dft] When this creature enters, create a 1/1 colorless Thopter artifact creature toke
_h_nimble_thopterist = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [dft] This creature enters with X +1/+1 counters on it. | {4}: Put a +1/+1 counter on th
_h_marketback_walker = _etb([["draw", {"n": 1}]])
# [dft] Flying | When this creature enters, all other creatures get -2/-2 until end of tur
_h_shefet_archfiend = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}], ["damage_creature", {"n": 2, "target": "each_opp"}]])
# [dft] Flash | When this Vehicle enters, target creature you control gets +2/+0 and gains
_h_burner_rocket = _etb([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [dft] When this Vehicle enters, exile target artifact or creature an opponent controls
_h_detention_chariot = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [dft] When this Vehicle enters, scry 2. (Look at the top two cards of your library, th
_h_spotcycle_scouter = _etb([["scry", {"n": 2}]])
# [dft] Whenever this creature attacks while saddled, untap it and put a +1/+1 counter o
_h_brightfield_mustang = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dft] At the beginning of your upkeep, surveil 1. | {2}{B}{G}, {T}, Sacrifice this artif
_h_broodheart_engine = _etb([["scry", {"n": 1}]])
# [dft] Flash | When this creature enters, another target creature or Vehicle you control 
_h_fang_guardian = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [dft] When this Vehicle enters, create a 1/1 colorless Thopter artifact creature token
_h_broadcast_rambler = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [dft] Whenever this Vehicle attacks, create a Treasure token. (It's an artifact with "
_h_rocketeer_boostbuggy = _etb([["create_treasure", {"n": 1}]])
# [dft] When this creature enters, return target creature or Vehicle an opponent control
_h_spikeshell_harrier = _etb([["bounce_to_hand", {}]])
# [dft] Lifelink | Whenever this creature attacks while saddled, search your library for a
_h_gloryheath_lynx = _etb([["draw", {"n": 1}]])
# [dft] Start your engines! (If you have no speed, it starts at 1. It increases once on 
_h_embalmed_ascendant = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dft] Deathtouch | Whenever this creature attacks while saddled, it gets +0/+3 until end
_h_venomsac_lagac = _etb([["add_counters", {"n": 0, "target": "self"}]])
# [dft] When this creature enters, you may sacrifice a creature or Vehicle. When you do,
_h_gastal_blockbuster = _etb([["scry", {"n": 0}], ["destroy", {"target": "opp_biggest_creature"}]])
# [dft] When Aatchik enters, create a 1/1 green Insect creature token for each artifact 
_h_aatchik__emerald_radian = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["lose_life", {"n": 1, "target": "opp"}], ["add_counters", {"n": 1, "target": "self"}]])
# [dft] Flying, haste | Whenever this creature attacks while saddled, it deals 2 damage to
_h_dracosaur_auxiliary = _etb([["damage_any", {"n": 2}]])
# [dft] Ward?{2}, Pay 2 life. | Whenever you discard one or more cards, target creature ge
_h_captain_howler__sea_scourge = _etb([["draw", {"n": 1}], ["add_counters", {"n": 2, "target": "self"}]])
# [dft] Whenever you attack, target creature you control gets +1/+0 and gains deathtouch
_h_haunted_hellride = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [dft] Start your engines! (If you have no speed, it starts at 1. It increases once on 
_h_racers__scoreboard = _etb([["draw", {"n": 2}]])
# [dft] Reach | When this creature enters, you gain 4 life. | Cycling {2} ({2}, Discard this
_h_migrating_ketradon = _etb([["gain_life", {"n": 4}]])
# [dft] Whenever this creature attacks while saddled, it gains indestructible until end 
_h_unswerving_sloth = _etb([["scry", {"n": 0}]])
# [dft] Whenever this creature attacks while saddled, create a Treasure token. (It's an 
_h_gilded_ghoda = _etb([["create_treasure", {"n": 1}]])
# [dft] This creature saddles Mounts and crews Vehicles as though its power were 2 great
_h_dynamite_diver = _etb([["damage_any", {"n": 1}]])
# [dft] When this Vehicle enters, search your library for a basic land card, reveal it, 
_h_marshals__pathcruiser = _etb([["search_basic_land", {"n": 1}]])
# [dft] When this creature enters, scry 2. | {T}: Create X 1/1 colorless Pilot creature to
_h_cloudspire_coordinator = _etb([["scry", {"n": 2}]])
# [dft] Haste | Vehicles you control have haste. | Whenever you attack, if a Pirate and a Ve
_h_fearless_swashbuckler = _etb([["draw", {"n": 3}]])
# [dft] When this Vehicle enters, each opponent discards a card. | Crew 2 (Tap any number 
_h_ripclaw_wrangler = _etb([["discard", {"n": 1, "target": "opp"}]])
# [dft] Enchant creature or Vehicle | When this Aura enters, create a 1/1 colorless Pilot 
_h_roadside_assistance = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token saddles Mounts", "crews Vehicles as though its power were 2 greater"]}]])
# [dft] Menace, reach | When this Vehicle enters, destroy target nonland permanent an oppo
_h_thundering_broodwagon = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [dft] Affinity for artifacts (This spell costs {1} less to cast for each artifact you 
_h_demonic_junker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [dft] Whenever this creature enters or attacks, exile up to one target card from a gra
_h_wreck_remover = _etb([["gain_life", {"n": 1}]])
# [dft] When this creature enters, mill three cards, then you may return a land card fro
_h_pothole_mole = _etb([["mill", {"n": 3, "target": "self"}]])
# [dft] Start your engines! (If you have no speed, it starts at 1. It increases once on 
_h_far_fortune__end_boss = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [dft] Flying | When this creature enters, surveil 2. (Look at the top two cards of your 
_h_wreckage_wickerfolk = _etb([["scry", {"n": 2}]])
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
# [dft] When Caradora enters, you may search your library for a Mount or Vehicle card, r
_h_caradora__heart_of_alacria = _etb([["draw", {"n": 1}]])
# [dft] When this creature enters, mill two cards, then put a +1/+1 counter on this crea
_h_ooze_patrol = _etb([["add_counters", {"n": 1, "target": "self"}], ["mill", {"n": 2, "target": "self"}]])
# [dft] Vigilance | Whenever this creature attacks while saddled, it gets +1/+2 and gains 
_h_brightfield_glider = _etb([["scry", {"n": 0}]])
# [dft] Whenever you attack, target attacking creature gets +1/+0 until end of turn. Whe
_h_grim_javelineer = _etb([["scry", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [dft] Vigilance, menace | When this creature enters, other creatures you control get +2/
_h_pyrewood_gearhulk = _etb([["add_counters", {"n": 2, "target": "all_friendly"}]])
# [dft] Vigilance | Whenever this creature attacks while saddled, it gets +2/+2 until end 
_h_alacrian_jaguar = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [dft] Menace | Whenever you attack, draw a card, then discard a card. | Crew 1 (Tap any nu
_h_boosted_sloop = _etb([["draw", {"n": 1}]])
# [dft] Whenever this creature or another artifact you control enters, each opponent los
_h_pactdoll_terror = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [dft] Start your engines! | When this enchantment enters, create a 2/2 black Zombie crea
_h_hour_of_victory = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dft] When this creature enters and whenever it attacks while saddled, create a 3/3 gr
_h_autarch_mammoth = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [dft] Vigilance | When this Vehicle enters, you may search your library for an artifact 
_h_guidelight_pathmaker = _etb([["draw", {"n": 1}]])
# [dft] When this Vehicle enters, you gain 2 life. | {T}: Add one mana of any color. | Crew 
_h_veloheart_bike = _etb([["gain_life", {"n": 2}]])
# [tdm] Flash | When this creature enters, target creature an opponent controls gets -2/-0
_h_humbling_elder = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [tdm] Flying | Whenever this creature attacks, another target creature you control gains
_h_starry_eyed_skyrider = _etb([["scry", {"n": 0}]])
# [tdm] When this creature enters, you may exile a creature card from your graveyard. Wh
_h_kishla_trawlers = _etb([["return_gy_to_hand", {"filter_type": "any"}]])
# [tdm] When this creature enters, it deals 5 damage to target creature an opponent cont
_h_unsparing_boltcaster = _etb([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [tdm] When this creature enters, if you cast it, mill four cards. When you do, return 
_h_yathan_roadwatcher = _etb([["mill", {"n": 4, "target": "self"}]])
# [tdm] At the beginning of your end step, put a +1/+1 counter on this creature. | Wheneve
_h_warden_of_the_grove = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Flying, vigilance | Whenever this creature attacks, surveil 1. (Look at the top ca
_h_boulderborn_dragon = _etb([["scry", {"n": 1}]])
# [tdm] When this enchantment enters, search your library for up to two basic land cards
_h_encroaching_dragonstorm = _etb([["search_basic_land", {"n": 2}]])
# [tdm] When this enchantment enters, create two 2/2 white Soldier creature tokens. | When
_h_teeming_dragonstorm = _etb([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": []}]])
# [tdm] When this creature enters, scry 2. (Look at the top two cards of your library, t
_h_mardu_devotee = _etb([["scry", {"n": 2}]])
# [tdm] Prowess (Whenever you cast a noncreature spell, this creature gets +1/+1 until e
_h_meticulous_artisan = _etb([["create_treasure", {"n": 1}]])
# [tdm] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_gurmag_rakshasa = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}], ["add_counters", {"n": 2, "target": "self"}]])
# [tdm] Flurry ? Whenever you cast your second spell each turn, this creature deals 2 da
_h_cori_mountain_stalwart = _etb([["damage_player", {"n": 2, "target": "opp"}], ["gain_life", {"n": 2}]])
# [tdm] Deathtouch | Mobilize 1 (Whenever this creature attacks, create a tapped and attac
_h_nightblade_brigade = _etb([["scry", {"n": 1}]])
# [tdm] When this creature enters, create a 1/1 red Goblin creature token. | {1}, {T}: Tar
_h_underfoot_underdogs = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tdm] Flying | Ward {2} (Whenever this creature becomes the target of a spell or ability
_h_aegis_sculptor = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Trample | When this creature enters, each opponent loses 2 life and you gain 2 lif
_h_skirmish_rhino = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [tdm] When this creature enters, exile the top card of your library. Until the end of 
_h_equilibrium_adept = _etb([["scry", {"n": 0}]])
# [tdm] When this enchantment enters, exile target nonland permanent an opponent control
_h_stormplain_detainment = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [tdm] Mobilize 1 (Whenever this creature attacks, create a tapped and attacking 1/1 re
_h_venerated_stormsinger = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [tdm] When this enchantment enters, each opponent loses 2 life and you gain 2 life. Su
_h_corroding_dragonstorm = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}], ["scry", {"n": 2}]])
# [tdm] Affinity for creatures (This spell costs {1} less to cast for each creature you 
_h_salt_road_packbeast = _etb([["draw", {"n": 1}]])
# [tdm] When this enchantment enters, exile cards from the top of your library until you
_h_breaching_dragonstorm = _etb([["draw", {"n": 1}]])
# [tdm] When this creature enters, look at the top two cards of your library. Put one of
_h_sibsig_appraiser = _etb([["scry", {"n": 2}]])
# [tdm] When this creature enters or dies, put a +1/+1 counter on target creature you co
_h_reputable_merchant = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] When this creature enters, you may mill three cards. (You may put the top three 
_h_rainveil_rejuvenator = _etb([["mill", {"n": 3, "target": "self"}]])
# [tdm] Flurry ? Whenever you cast your second spell each turn, this creature gets +1/+1
_h_jeskai_devotee = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Ward {2} | Whenever this creature attacks, put three stun counters on it and draw 
_h_ambling_stormshell = _etb([["draw", {"n": 3}]])
# [tdm] When this creature enters, mill three cards. You may put a land card from among 
_h_ainok_wayfarer = _etb([["add_counters", {"n": 1, "target": "self"}], ["mill", {"n": 3, "target": "self"}]])
# [tdm] Flying | At the beginning of your end step, if creatures you control have total to
_h_betor__kin_to_all = _etb([["draw", {"n": 1}]])
# [tdm] Lifelink | When this creature enters, search your library for a black card, a gree
_h_lotuslight_dancers = _etb([["draw", {"n": 1}]])
# [tdm] When this creature enters, draw a card, then discard a card.
_h_temur_tawnyback = _etb([["draw", {"n": 1}]])
# [tdm] Flash | Enchant creature | When this Aura enters, enchanted creature gains first str
_h_fire_rim_form = _etb([["scry", {"n": 0}]])
# [tdm] Flying | Whenever this creature attacks, if you control a creature with a counter 
_h_delta_bloodflies = _etb([["lose_life", {"n": 1, "target": "opp"}]])
# [tdm] At the beginning of combat on your turn, put a +1/+1 counter on another target c
_h_loxodon_battle_priest = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}]])
# [tdm] Equipped creature has haste. | Flurry ? Whenever you cast your second spell each t
_h_a_cori_steel_cutter = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["prowess"]}]])
# [tdm] When this creature enters, draw a card if you control a creature with a counter 
_h_trade_route_envoy = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [tdm] When this creature enters, you may search your library for a basic land card, re
_h_embermouth_sentinel = _etb([["search_basic_land", {"n": 1}]])
# [tdm] Mobilize 1 (Whenever this creature attacks, create a tapped and attacking 1/1 re
_h_reigning_victor = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Flying, haste | Whenever this creature deals combat damage to a player, you gain 1
_h_jeskai_shrinekeeper = _etb([["draw", {"n": 1}], ["gain_life", {"n": 1}]])
# [tdm] Creature spells you cast cost {2} less to cast. | Whenever a creature you control 
_h_the_sibsig_ceremony = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tdm] Flying | Flurry ? Whenever you cast your second spell each turn, create a 1/1 whit
_h_wingblade_disciple = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [tdm] Flying | When this creature enters, it deals 2 damage to any target and you gain 2
_h_sonic_shrieker = _etb([["damage_any", {"n": 2}], ["gain_life", {"n": 2}]])
# [tdm] When this creature enters, put a +1/+1 counter on target creature. | Renew ? {3}{G
_h_sage_of_the_fang = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Whenever this creature becomes tapped, you may discard a card. If you do, draw a
_h_rescue_leopard = _etb([["draw", {"n": 1}]])
# [tdm] At the beginning of your upkeep, mill three cards. Then if your library has no c
_h_stillness_in_motion = _etb([["mill", {"n": 3, "target": "self"}]])
# [tdm] Creatures you control get +1/+0. | Whenever you attack, create a 1/1 red Warrior c
_h_war_effort = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tdm] Flurry ? Whenever you cast your second spell each turn, put a +1/+1 counter on t
_h_poised_practitioner = _etb([["add_counters", {"n": 1, "target": "self"}], ["scry", {"n": 1}]])
# [tdm] At the beginning of your upkeep, surveil 1. (Look at the top card of your librar
_h_essence_anchor = _etb([["scry", {"n": 1}]])
# [tdm] When this creature enters, look at the top six cards of your library. You may re
_h_dragonologist = _etb([["scry", {"n": 6}]])
# [tdm] Haste | Flurry ? Whenever you cast your second spell each turn, this creature deal
_h_devoted_duelist = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [tdm] When this creature dies, create a 2/2 black Zombie Druid creature token. | Renew ?
_h_adorned_crocodile = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tdm] When this creature enters, look at the top three cards of your library. You may 
_h_gurmag_nightwatch = _etb([["scry", {"n": 3}]])
# [fin] Whenever you cast a noncreature spell, if at least four mana was spent to cast i
_h_blazing_bomb = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] When this Vehicle enters, create a 1/1 colorless Hero creature token. | Crew 1 (Ta
_h_magitek_armor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] When this creature enters, create a 0/1 black Wizard creature token with "Whenev
_h_mysidian_elder = _etb([["damage_player", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": ["\"Whenever you cast a noncreature spell", "this token deals 1 damage to each opponent"]}]])
# [fin] Affinity for artifacts (This spell costs {1} less to cast for each artifact you 
_h_valkyrie_aerial_unit = _etb([["scry", {"n": 2}]])
# [fin] Lifelink | At the beginning of your end step, each opponent mills X cards, where X
_h_hope_estheim = _etb([["mill", {"n": 1, "target": "self"}]])
# [fin] Whenever you cast a noncreature spell, create a 1/1 colorless Hero creature toke
_h_tellah__great_sage = _etb([["draw", {"n": 2}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Flash | When this artifact enters, draw a card. | {2}, {T}, Sacrifice this artifact:
_h_instant_ramen = _etb([["draw", {"n": 1}]])
# [fin] When Ignis Scientia enters, look at the top six cards of your library. You may p
_h_ignis_scientia = _etb([["scry", {"n": 6}]])
# [fin] Whenever you cast a noncreature spell, if at least four mana was spent to cast i
_h_sahagin = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] Whenever another creature you control enters, this creature gets +1/+1 until end
_h_loporrit_scout = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] When Edgar enters, draw a card for each artifact you control. | Two-Headed Coin ? 
_h_edgar__king_of_figaro = _etb([["draw", {"n": 1}]])
# [fin] Vigilance, lifelink | Whenever you gain life, put a +1/+1 counter on each Cleric y
_h_minwu__white_mage = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [fin] Whenever you cast a noncreature spell, Shantotto gets +X/+0 until end of turn, w
_h_shantotto__tactician_magician = _etb([["draw", {"n": 1}]])
# [fin] When this creature enters, you lose 1 life and create a Treasure token. | Whenever
_h_namazu_trader = _etb([["create_treasure", {"n": 1}], ["lose_life", {"n": 1, "target": "self"}], ["scry", {"n": 2}]])
# [fin] Trample | At the beginning of your end step, if this creature didn't enter the bat
_h_cactuar = _etb([["scry", {"n": 0}]])
# [fin] Trample | When this creature enters, you gain 3 life. | Forestcycling {2} ({2}, Disc
_h_balamb_t_rexaur = _etb([["gain_life", {"n": 3}]])
# [fin] Whenever this creature or another creature or artifact you control dies, target 
_h_al_bhed_salvagers = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [fin] Whenever an artifact you control enters, surveil 1. | At the beginning of your end
_h_golbez__crystal_collector = _etb([["scry", {"n": 1}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [fin] When Ultimecia enters, tap all creatures your opponents control. | Whenever a crea
_h_ultimecia__temporal_threat = _etb([["scry", {"n": 0}]])
# [fin] Reach | Landfall ? Whenever a land you control enters, this creature deals 1 damag
_h_sabotender = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [fin] Vigilance (Attacking doesn't cause this creature to tap.) | When Sephiroth enters,
_h_sephiroth__planet_s_heir = _etb([["damage_creature", {"n": 2, "target": "opp_biggest"}], ["add_counters", {"n": 1, "target": "self"}]])
# [fin] When this creature enters, mill three cards and you gain 3 life. (To mill three 
_h_shinra_reinforcements = _etb([["mill", {"n": 3, "target": "self"}], ["gain_life", {"n": 3}]])
# [fin] Whenever a creature you control attacks alone, it gains double strike until end 
_h_seifer_almasy = _etb([["scry", {"n": 0}]])
# [fin] At the beginning of your upkeep, you may pay 1 life. If you do, draw a card and 
_h_seymour_flux = _etb([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [fin] Landfall ? Whenever a land you control enters, create a 2/2 green Bird creature 
_h_chocobo_racetrack = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["\"Whenever a land you control enters", "this token gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [fin] Whenever you attack, target attacking equipped creature gains menace until end o
_h_item_shopkeep = _etb([["scry", {"n": 0}]])
# [fin] Whenever one or more Birds you control attack, look at that many cards from the 
_h_choco__seeker_of_paradise = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] When this creature enters, each opponent discards a card.
_h_hecteyes = _etb([["discard", {"n": 1, "target": "opp"}]])
# [fin] Landfall ? Whenever a land you control enters, put a +1/+1 counter on target cre
_h_ride_the_shoopuf = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] When Rinoa Heartilly enters, create Angelo, a legendary 1/1 green and white Dog 
_h_rinoa_heartilly = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [fin] {T}: Add X mana in any combination of {U} and/or {R}, where X is Vivi Ornitier's
_h_a_vivi_ornitier = _etb([["damage_player", {"n": 1, "target": "opp"}], ["add_counters", {"n": 1, "target": "self"}]])
# [fin] Reach (This creature can block creatures with flying.) | At the beginning of comba
_h_rosa__resolute_white_mage = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] Flying, deathtouch | Whenever you cast a noncreature spell, Black Waltz No. 3 deal
_h_black_waltz_no__3 = _etb([["damage_player", {"n": 2, "target": "opp"}]])
# [fin] At the beginning of your end step, exile target creature you control, then retur
_h_y_shtola_rhul = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [fin] When this creature dies, create a 1/1 colorless Hero creature token.
_h_dwarven_castle_guard = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] When this creature enters, draw a card. | At the beginning of combat on your turn,
_h_weapons_vendor = _etb([["draw", {"n": 1}]])
# [fin] When this Equipment enters, it deals 2 damage to any target. | Equipped creature g
_h_lion_heart = _etb([["damage_any", {"n": 2}]])
# [fin] Flying | Whenever this creature attacks, surveil 1. (Look at the top card of your 
_h_il_mheg_pixie = _etb([["scry", {"n": 1}]])
# [fin] Flying | Whenever another artifact you control enters, you may draw a card. If you
_h_rook_turret = _etb([["draw", {"n": 1}]])
# [fin] When this creature dies, create a Treasure token. (It's an artifact with "{T}, S
_h_magic_pot = _etb([["create_treasure", {"n": 1}]])
# [fin] Flash | When this Equipment enters, attach it to target creature you control. That
_h_coral_sword = _etb([["scry", {"n": 0}]])
# [fin] Lifelink | Whenever you gain life, put a +1/+1 counter on Aerith Gainsborough. | Whe
_h_aerith_gainsborough = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] Flying | Whenever this Vehicle attacks, draw a card, then discard a card. | Crew 2 (
_h_adventurer_s_airship = _etb([["draw", {"n": 1}]])
# [fin] Whenever an artifact you control enters, put a +1/+1 counter on Tidus. | Whenever 
_h_tidus__blitzball_star = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] Flying | When this creature enters, create a 1/1 colorless Hero creature token.
_h_dragoon_s_wyvern = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Flying | When this creature enters, put a +1/+1 counter on target creature. | Plains
_h_cloudbound_moogle = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [fin] When Gladiolus Amicitia enters, search your library for a land card, put it onto
_h_gladiolus_amicitia = _etb([["draw", {"n": 1}], ["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [eoe] Whenever this creature becomes tapped, create a Lander token. (It's an artifact 
_h_seedship_agrarian = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this Spacecraft enters, create a 2/2 colorless Robot artifact creature toke
_h_wedgelight_rammer = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [eoe] Reach | Landfall ? Whenever a land you control enters, exile cards from the top of
_h_territorial_bruntar = _etb([["draw", {"n": 1}]])
# [eoe] Whenever a creature you control with a +1/+1 counter on it dies, draw a card.
_h_meltstrider_eulogist = _etb([["draw", {"n": 1}]])
# [eoe] Affinity for Slivers (This spell costs {1} less to cast for each Sliver you cont
_h_thrumming_hivepool = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [eoe] Flying | When this creature enters, surveil 2. (Look at the top two cards of your 
_h_starbreach_whale = _etb([["scry", {"n": 2}]])
# [eoe] When this creature enters or dies, surveil 1. (Look at the top card of your libr
_h_thawbringer = _etb([["scry", {"n": 1}]])
# [eoe] When this enchantment enters, if you cast it, shuffle your hand and graveyard in
_h_weftwalking = _etb([["draw", {"n": 7}]])
# [eoe] Lifelink | Whenever this creature attacks, you may sacrifice another creature or a
_h_comet_crawler = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [eoe] Flash | When this Equipment enters, attach it to target creature you control. That
_h_squire_s_lightblade = _etb([["scry", {"n": 0}]])
# [eoe] When this creature enters, create a 1/1 white Human Soldier creature token. | Warp
_h_knight_luminary = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [eoe] Whenever you cast your second spell each turn, put a +1/+1 counter on this creat
_h_sunstar_lightsmith = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [eoe] When this Spacecraft enters, mill three cards, then return a creature or Spacecr
_h_fell_gravship = _etb([["mill", {"n": 3, "target": "self"}]])
# [eoe] Whenever this creature becomes tapped, you gain 1 life. | {2}, {T}: Put target car
_h_chrome_companion = _etb([["gain_life", {"n": 1}]])
# [eoe] Whenever another artifact you control enters, create a 2/2 colorless Robot artif
_h_mechan_assembler = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [eoe] Whenever you cast your second spell each turn, put a +1/+1 counter on this creat
_h_illvoi_operative = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] Landfall ? Whenever a land you control enters, create a 2/2 colorless Robot arti
_h_eusocial_engineering = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [eoe] This creature can't be blocked if you've cast two or more spells this turn. | When
_h_illvoi_infiltrator = _etb([["draw", {"n": 1}]])
# [eoe] When this Spacecraft enters, surveil 2. | Station (Tap another creature you contro
_h_wurmwall_sweeper = _etb([["scry", {"n": 2}]])
# [eoe] When this creature enters, you may sacrifice an artifact. When you do, put a +1/
_h_selfcraft_mechan = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [eoe] When this creature enters, put a +1/+1 counter on each of up to two target creat
_h_weftblade_enhancer = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [eoe] When this Spacecraft enters, put a +1/+1 counter on each creature you control. | S
_h_atmospheric_greenhouse = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] At the beginning of your end step, if you control two or more tapped creatures, 
_h_flight_deck_coordinator = _etb([["gain_life", {"n": 2}]])
# [eoe] When this creature enters, put a +1/+1 counter on target creature. | Each creature
_h_drix_fatemaker = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] At the beginning of your end step, if you control two or more tapped creatures, 
_h_frontline_war_rager = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this creature enters, create a 1/1 white Human Soldier creature token. | {4}{
_h_honored_knight_captain = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [eoe] Flash | When this artifact enters, up to one target creature gets -3/-3 until end 
_h_dubious_delicacy = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [eoe] Lifelink | At the beginning of your end step, if you control two or more tapped cr
_h_dawnstrike_vanguard = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] Reach | Landfall ? Whenever a land you control enters, this creature gets +2/+0 un
_h_remnant_elemental = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [eoe] Flying | Whenever an artifact you control enters, put a +1/+1 counter on target cr
_h_mm_menon__uthros_exile = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] Flying | When this creature enters, it deals 3 damage to any target.
_h_nebula_dragon = _etb([["damage_any", {"n": 3}]])
# [eoe] Whenever another artifact you control enters, you may pay {1}. If you do, put a 
_h_oreplate_pangolin = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] Landfall ? Whenever a land you control enters, Tannuk deals 1 damage to each opp
_h_tannuk__memorial_ensign = _etb([["damage_player", {"n": 1, "target": "opp"}], ["draw", {"n": 1}]])
# [eoe] When this creature enters, put a +1/+1 counter on target creature you control. | W
_h_rayblade_trooper = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this Spacecraft enters, draw two cards, then discard a card. | Station (Tap a
_h_uthros_scanship = _etb([["draw", {"n": 2}]])
# [eoe] When this creature enters, look at the top five cards of your library. You may r
_h_pulsar_squadron_ace = _etb([["add_counters", {"n": 1, "target": "self"}], ["scry", {"n": 5}]])
# [eoe] Flying | Ward {2} (Whenever this creature becomes the target of a spell or ability
_h_mouth_of_the_storm = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [eoe] When this creature enters, you gain 2 life. | Warp {1}{G} (You may cast this card 
_h_germinating_wurm = _etb([["gain_life", {"n": 2}]])
# [eoe] When this creature enters, if an opponent controls more lands than you, create a
_h_sunstar_expansionist = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] Flying | Whenever this creature becomes tapped, you may sacrifice another creature
_h_swarm_culler = _etb([["draw", {"n": 1}]])
# [eoe] Deathtouch | When this creature enters, another target creature you control gains 
_h_blooming_stinger = _etb([["scry", {"n": 0}]])
# [eoe] When this creature enters, look at the top two cards of your library. Put one in
_h_codecracker_hound = _etb([["scry", {"n": 2}]])
# [eoe] When this Spacecraft enters, you may sacrifice a land or Lander. If you do, sear
_h_larval_scoutlander = _etb([["search_basic_land", {"n": 2}]])
# [eoe] Trample | Landfall ? Whenever a land you control enters, this creature gets +1/+0 
_h_icecave_crasher = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this creature enters, target creature an opponent controls gets -3/-0 until
_h_sinister_cryologist = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [eoe] Flash | When this Equipment enters, attach it to target creature you control. That
_h_illvoi_light_jammer = _etb([["scry", {"n": 0}]])
# [eoe] When Infinite Guideline Station enters, create a tapped 2/2 colorless Robot arti
_h_infinite_guideline_station = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [eoe] At the beginning of combat on your turn, target creature you control gets +1/+0 
_h_molecular_modifier = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this Spacecraft enters, it deals 3 damage to any target. | Station (Tap anoth
_h_debris_field_crusher = _etb([["damage_any", {"n": 3}]])
# [eoe] At the beginning of your end step, if you control two or more tapped creatures, 
_h_sunstar_chaplain = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] When this creature enters, destroy up to one other target creature. If that crea
_h_faller_s_faithful = _etb([["draw", {"n": 2}]])
# [eoe] When this creature enters, until end of turn, another target creature you contro
_h_perigee_beckoner = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [eoe] At the beginning of your end step, if you control two or more tapped creatures, 
_h_vaultguard_trooper = _etb([["draw", {"n": 2}]])
# [eoe] When this creature enters, each opponent discards a card.
_h_virus_beetle = _etb([["discard", {"n": 1, "target": "opp"}]])
# [eoe] When Alpharael enters, draw two cards. Then discard two cards unless you discard
_h_alpharael__dreaming_acolyte = _etb([["draw", {"n": 2}]])
# [eoe] Whenever this creature becomes tapped, draw a card, then discard a card.
_h_mechan_navigator = _etb([["draw", {"n": 1}]])
# [eoe] Whenever this creature becomes tapped, surveil 1. (Look at the top card of your 
_h_starfighter_pilot = _etb([["scry", {"n": 1}]])
# [eoe] When this Equipment enters, create a 2/2 colorless Robot artifact creature token
_h_auxiliary_boosters = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [spm] When Spider-Ham enters, create a Food token. (It's an artifact with "{2}, {T}, S
_h_spider_ham__peter_porker = _etb([["gain_life", {"n": 3}]])
# [spm] Enchant land | When this Aura enters, create three 1/1 green and white Human Citiz
_h_friendly_neighborhood = _etb([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [spm] Flying | When Starling enters, another target creature you control gains flying un
_h_starling__aerial_ally = _etb([["scry", {"n": 0}]])
# [spm] Flying | When this creature enters, create a 1/1 green and white Human Citizen cre
_h_news_helicopter = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [spm] Web-slinging {2}{G} (You may cast this spell for {2}{G} if you also return a tap
_h_spider_man__brooklyn_visionary = _etb([["search_basic_land", {"n": 1}]])
# [spm] During your turn, Sun-Spider has flying. | When Sun-Spider enters, search your lib
_h_sun_spider__nimble_webber = _etb([["draw", {"n": 1}]])
# [spm] Menace | Whenever a creature you control attacks alone, put a +1/+1 counter on it.
_h_spider_man_noir = _etb([["add_counters", {"n": 1, "target": "self"}], ["scry", {"n": 1}]])
# [spm] When this creature enters, draw a card.
_h_gallant_citizen = _etb([["draw", {"n": 1}]])
# [spm] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_web_of_life_and_destiny = _etb([["scry", {"n": 5}]])
# [spm] When this artifact enters, it deals 5 damage to target creature. | {1}{R}, Discard
_h_steel_wrecking_ball = _etb([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [spm] When this creature enters, put a +1/+1 counter on each other creature you contro
_h_web_warriors = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [spm] When Anti-Venom enters, if he was cast, return target creature card from your gr
_h_anti_venom__horrifying_healer = _etb([["return_gy_to_bf", {"filter_type": "creature"}]])
# [spm] When this creature enters, create a Treasure token. (It's an artifact with "{T},
_h_professional_wrestler = _etb([["create_treasure", {"n": 1}]])
# [spm] At the beginning of your end step, you may tap two untapped creatures and/or Tre
_h_rent_is_due = _etb([["draw", {"n": 1}]])
# [spm] Reach | At the beginning of combat on your turn, target Spider you control gets +2
_h_ezekiel_sims__spider_totem = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [spm] When Silver Sable enters, put a +1/+1 counter on another target creature. | Whenev
_h_silver_sable__mercenary_leader = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}]])
# [spm] When Mysterio enters, create a 3/3 blue Illusion Villain creature token for each
_h_mysterio__master_of_illusion = _etb([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": []}]])
# [spm] When this enchantment enters, create a 2/1 green Spider creature token with reac
_h_wall_crawl = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": ["reach", "then you gain 1 life for each Spider you control"]}]])
# [spm] Menace (This creature can't be blocked except by two or more creatures.) | When Sc
_h_scarlet_spider__kaine = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [spm] When this artifact enters, look at the top five cards of your library. You may r
_h_pictures_of_spider_man = _etb([["scry", {"n": 5}]])
# [spm] Flying | Whenever another Villain you control enters, put a +1/+1 counter on this 
_h_flying_octobot = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [spm] Trample | Whenever you cast a spell with mana value 4 or greater, put a +1/+1 coun
_h_lurking_lizards = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [spm] When Tombstone enters, return target Villain card from your graveyard to your ha
_h_tombstone__career_criminal = _etb([["return_gy_to_hand", {"filter_type": "any"}]])
# [spm] When this Vehicle enters, you may pay {G}. If you do, search your library for a 
_h_subway_train = _etb([["search_basic_land", {"n": 1}]])
# [spm] Whenever a Spider you control enters, draw a card. This ability triggers only on
_h_mary_jane_watson = _etb([["draw", {"n": 1}]])
# [spm] Flash | Enchant creature | When this Aura enters, create two 1/1 colorless Robot art
_h_robotics_mastery = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [spm] Flying, vigilance | Whenever this creature attacks, mill a card. (Put the top card
_h_mysterio_s_phantasm = _etb([["mill", {"n": 1, "target": "self"}]])
# [spm] When this enchantment enters, exile target nonland permanent an opponent control
_h_web_up = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [spm] Flying | When this creature leaves the battlefield, create a Food token. (It's an 
_h_city_pigeon = _etb([["gain_life", {"n": 3}]])
# [spm] You may look at the top card of your library any time. | You may cast Spider spell
_h_madame_web__clairvoyant = _etb([["mill", {"n": 1, "target": "self"}]])
# [spm] At the beginning of your upkeep, discard a card, then create a Treasure token. | M
_h_ultimate_green_goblin = _etb([["create_treasure", {"n": 1}]])
# [spm] Whenever another creature you control enters, you gain 1 life. If it's a Spider,
_h_aunt_may = _etb([["add_counters", {"n": 1, "target": "self"}], ["gain_life", {"n": 1}]])
# [spm] When Molten Man enters, search your library for a basic Mountain card, put it on
_h_molten_man__inferno_incarnate = _etb([["draw", {"n": 1}]])
# [spm] When this artifact enters, draw a card. | {1}{B}, Sacrifice this artifact: Mill fo
_h_eerie_gravestone = _etb([["draw", {"n": 1}]])
# [spm] When this artifact enters, create a Food token. (It's an artifact with "{2}, {T}
_h_hot_dog_cart = _etb([["gain_life", {"n": 3}]])
# [spm] Trample | Whenever you cast a spell with mana value 4 or greater, this creature de
_h_angry_rabble = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [spm] Web-slinging {4}{G}{G} (You may cast this spell for {4}{G}{G} if you also return
_h_spiders_man__heroic_horde = _etb([["gain_life", {"n": 3}], ["create_token", {"count": 2, "power": "2", "toughness": "1", "keywords": ["reach"]}]])
# [spm] Reach | When this creature enters, you may search your library for a basic land ca
_h_spider_bot = _etb([["search_basic_land", {"n": 1}]])
# [spm] Deathtouch | When this creature enters, mill two cards. (Put the top two cards of 
_h_venomized_cat = _etb([["mill", {"n": 2, "target": "self"}]])
# [spm] When this creature dies, create a Treasure token. (It's an artifact with "{T}, S
_h_common_crook = _etb([["create_treasure", {"n": 1}]])
# [spm] Web-slinging {2}{W} (You may cast this spell for {2}{W} if you also return a tap
_h_spider_uk = _etb([["draw", {"n": 1}]])
# [tla] When this creature dies, earthbend 2. (Target land you control becomes a 0/0 cre
_h_earth_village_ruffians = _etb([["add_mana", {"n": 2}]])
# [tla] Flash | Prowess (Whenever you cast a noncreature spell, this creature gets +1/+1 u
_h_ty_lee__chi_blocker = _etb([["scry", {"n": 0}]])
# [tla] Whenever this creature attacks, you may sacrifice another creature or artifact. 
_h_beetle_headed_merchants = _etb([["add_counters", {"n": 1, "target": "self"}], ["draw", {"n": 1}]])
# [tla] As an additional cost to cast this spell, waterbend {5}. (While paying a waterbe
_h_benevolent_river_spirit = _etb([["scry", {"n": 2}]])
# [tla] Defender, reach | Whenever you attack, create a 2/1 colorless Construct artifact c
_h_fire_navy_trebuchet = _etb([["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": ["flying named Ballistic Boulder that's tapped", "attacking"]}]])
# [tla] Trample | When Bumi enters, earthbend 4. | Whenever Bumi deals combat damage to a pl
_h_bumi__unleashed = _etb([["add_mana", {"n": 4}]])
# [tla] When this creature enters, earthbend 2. (Target land you control becomes a 0/0 c
_h_badgermole = _etb([["add_mana", {"n": 2}]])
# [tla] Vigilance | When Katara enters, create a 1/1 white Ally creature token. | Waterbend 
_h_katara__water_tribe_s_hope = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Raid ? This creature enters with a +1/+1 counter on it if you attacked this turn
_h_cruel_administrator = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["firebending 1"]}], ["damage_any", {"n": 1}]])
# [tla] When Crescent Island Temple enters, for each Shrine you control, create a 1/1 re
_h_crescent_island_temple = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["prowess"]}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["prowess"]}]])
# [tla] When Northern Air Temple enters, each opponent loses X life and you gain X life,
_h_northern_air_temple = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}], ["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [tla] Flying | When this creature enters, you may sacrifice an artifact or creature. If 
_h_buzzard_wasp_colony = _etb([["draw", {"n": 1}]])
# [tla] When this creature enters, mill three cards. You may put a land card from among 
_h_ostrich_horse = _etb([["add_counters", {"n": 1, "target": "self"}], ["mill", {"n": 3, "target": "self"}]])
# [tla] When Toph enters, earthbend 2. (Target land you control becomes a 0/0 creature w
_h_toph__the_blind_bandit = _etb([["add_mana", {"n": 2}]])
# [tla] Firebending 1 (Whenever this creature attacks, add {R}. This mana lasts until en
_h_tundra_tank = _etb([["scry", {"n": 0}]])
# [tla] Trample | When The Fire Nation Drill enters, you may tap it. When you do, destroy 
_h_the_fire_nation_drill = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [tla] Flying | When this creature enters, create a Clue token. (It's an artifact with "{
_h_messenger_hawk = _etb([["draw", {"n": 1}]])
# [tla] Vigilance | When this creature enters, put a +1/+1 counter on each of up to two ta
_h_earth_kingdom_soldier = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [tla] Landfall ? Whenever a land you control enters, this creature gains flying until 
_h_rabaroo_troop = _etb([["gain_life", {"n": 1}]])
# [tla] When Guru Pathik enters, look at the top five cards of your library. You may rev
_h_guru_pathik = _etb([["scry", {"n": 5}]])
# [tla] Whenever you cast a noncreature spell, put a +1/+1 counter on this creature.
_h_boar_q_pine = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] At the beginning of your end step, if Katara is tapped, put a +1/+1 counter on h
_h_katara__bending_prodigy = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] When this enchantment enters, create a Clue token. (It's an artifact with "{2}, 
_h_tolls_of_war = _etb([["draw", {"n": 1}]])
# [tla] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_callous_inspector = _etb([["draw", {"n": 1}]])
# [tla] Reach | When this creature enters, you may discard a card. If you do, draw a card.
_h_yuyan_archers = _etb([["draw", {"n": 1}]])
# [tla] Haste | Whenever another Ally you control enters, put a +1/+1 counter on that crea
_h_wartime_protestors = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] When this creature enters, put a +1/+1 counter on target creature.
_h_jeong_jeong_s_deserters = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Menace, prowess (Whenever you cast a noncreature spell, this creature gets +1/+1
_h_sokka__tenacious_tactician = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Whenever this creature becomes tapped, you gain 1 life and scry 1. (Look at the 
_h_compassionate_healer = _etb([["gain_life", {"n": 1}], ["scry", {"n": 1}]])
# [tla] Whenever this creature attacks, creatures you control get +1/+0 until end of tur
_h_wandering_musicians = _etb([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [tla] Whenever another Ally you control enters, earthbend 1. (Target land you control 
_h_haru__hidden_talent = _etb([["add_mana", {"n": 1}]])
# [tla] Whenever another Ally you control enters, put a +1/+1 counter on this creature.
_h_avatar_enthusiasts = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] When this Equipment enters, create a 1/1 white Ally creature token, then attach 
_h_kyoshi_battle_fan = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] When Iroh enters, create a Food token. | At the beginning of combat on your turn, 
_h_iroh__tea_master = _etb([["gain_life", {"n": 3}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["add_counters", {"n": 1, "target": "self"}]])
# [tla] Flash | When this Equipment enters, attach it to target creature you control. That
_h_twin_blades = _etb([["scry", {"n": 0}]])
# [tla] When this creature enters, earthbend 1, then earthbend 1. (To earthbend 1, targe
_h_dai_li_agents = _etb([["add_mana", {"n": 1}], ["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [tla] When Toph enters, you may discard a card. If you do, return target instant or so
_h_toph__hardheaded_teacher = _etb([["return_gy_to_hand", {"filter_type": "any"}], ["add_mana", {"n": 1}]])
# [tla] Haste | When this creature enters, create a 1/1 white Ally creature token.
_h_treetop_freedom_fighters = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Defender | When this creature enters, mill two cards. (Put the top two cards of yo
_h_platypus_bear = _etb([["mill", {"n": 2, "target": "self"}]])
# [tla] When Southern Air Temple enters, put X +1/+1 counters on each creature you contr
_h_southern_air_temple = _etb([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [tla] When this enchantment enters, create a Clue token. (It's an artifact with "{2}, 
_h_air_nomad_legacy = _etb([["draw", {"n": 1}]])
# [tla] When this creature enters, create a Clue token. (It's an artifact with "{2}, Sac
_h_forecasting_fortune_teller = _etb([["draw", {"n": 1}]])
# [tla] When Flopsie enters, put a +1/+1 counter on each creature you control. | Each crea
_h_flopsie__bumi_s_buddy = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tla] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_mongoose_lizard = _etb([["damage_any", {"n": 1}]])
# [tla] Whenever this creature attacks, choose target creature an opponent controls. Tap
_h_vengeful_villagers = _etb([["scry", {"n": 0}]])
# [tla] When this creature enters, create a 1/1 white Ally creature token.
_h_kyoshi_warriors = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] At the beginning of your first main phase, choose one that hasn't been chosen an
_h_zuko__conflicted = _etb([["lose_life", {"n": 2, "target": "self"}]])
# [tla] When The Spirit Oasis enters, draw a card for each Shrine you control. | Whenever 
_h_the_spirit_oasis = _etb([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [tla] Deathtouch | When this creature enters, create a Food token. (It's an artifact wit
_h_canyon_crawler = _etb([["gain_life", {"n": 3}]])
# [tla] Whenever you cast a noncreature spell, create a Clue token. (It's an artifact wi
_h_the_mechanist__aerial_artisan = _etb([["draw", {"n": 1}]])
# [tla] Vigilance | Whenever you draw your second card each turn, put a +1/+1 counter on t
_h_knowledge_seeker = _etb([["draw", {"n": 1}]])
# [tla] When Kyoshi Island Plaza enters, search your library for up to X basic land card
_h_kyoshi_island_plaza = _etb([["search_basic_land", {"n": 1}], ["search_basic_land", {"n": 1}]])
# [tla] When The Earth King enters, create a 4/4 green Bear creature token. | Whenever one
_h_the_earth_king = _etb([["create_token", {"count": 1, "power": "4", "toughness": "4", "keywords": []}]])
# [tla] When this creature enters, create a Food token. (It's an artifact with "{2}, {T}
_h_unlucky_cabbage_merchant = _etb([["gain_life", {"n": 3}], ["search_basic_land", {"n": 1}]])
# [tla] At the beginning of combat on your turn, target creature you control with a +1/+
_h_hog_monkey = _etb([["scry", {"n": 0}]])
# [tla] When this creature enters, earthbend 2. (Target land you control becomes a 0/0 c
_h_earth_kingdom_general = _etb([["add_mana", {"n": 2}]])
# [tla] When this creature enters, target opponent discards a card.
_h_corrupt_court_official = _etb([["discard", {"n": 1, "target": "opp"}]])
# [tla] When this enchantment enters, creatures you control get +2/+2 until end of turn.
_h_invasion_tactics = _etb([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [tla] When Hama enters, target opponent mills three cards. Exile up to one noncreature
_h_hama__the_bloodbender = _etb([["mill", {"n": 3, "target": "self"}]])
# [tla] Reach, deathtouch | When this creature dies, if there's a Lesson card in your grav
_h_walltop_sentries = _etb([["gain_life", {"n": 2}]])
# [tla] Nontoken artifacts you control are lands in addition to their other types. (They
_h_toph__the_first_metalbender = _etb([["add_mana", {"n": 2}]])
# [tla] When this creature dies, create a 1/1 white Ally creature token.
_h_pretending_poxbearers = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Flying | When this creature enters, scry 1. (Look at the top card of your library.
_h_glider_kids = _etb([["scry", {"n": 1}]])
# [tla] Vigilance, reach | When The Lion-Turtle enters, you gain 3 life. | The Lion-Turtle c
_h_the_lion_turtle = _etb([["gain_life", {"n": 3}]])
# [ecl] When this creature enters, surveil 2. (Look at the top two cards of your library
_h_twilight_diviner = _etb([["scry", {"n": 2}]])
# [ecl] When this creature enters, create a 1/1 black and red Goblin creature token.
_h_elder_auntie = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Whenever this creature becomes tapped, draw a card, then discard a card.
_h_silvergill_peddler = _etb([["draw", {"n": 1}]])
# [ecl] When this enchantment enters, exile up to one target nonland permanent an oppone
_h_liminal_hold = _etb([["gain_life", {"n": 2}]])
# [ecl] When this creature enters, surveil 1. (Look at the top card of your library. You
_h_foraging_wickermaw = _etb([["scry", {"n": 1}]])
# [ecl] Whenever you attack, target attacking Goblin you control gets +1/+0 until end of
_h_boggart_prankster = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [ecl] Changeling (This card is every creature type.) | When this creature enters, you ma
_h_graveshifter = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [ecl] At the beginning of combat on your turn, you may blight 1. When you do, target c
_h_warren_torchmaster = _etb([["scry", {"n": 0}]])
# [ecl] Vivid ? When this enchantment enters, search your library for up to X basic land
_h_prismatic_undercurrents = _etb([["search_basic_land", {"n": 1}]])
# [ecl] When this creature enters, if you control three or more creatures, return target
_h_dundoolin_weaver = _etb([["return_gy_to_hand", {"filter_type": "creature"}]])
# [ecl] At the beginning of your first main phase, you may blight 2. If you don't, you l
_h_gutsplitter_gang = _etb([["lose_life", {"n": 3, "target": "self"}]])
# [ecl] Flying | When this creature enters, target creature gains flying until end of turn
_h_stratosoarer = _etb([["scry", {"n": 0}]])
# [ecl] Changeling (This card is every creature type.) | Flying | When this creature enters,
_h_rooftop_percher = _etb([["gain_life", {"n": 3}]])
# [ecl] Flying | When this creature enters, surveil 1. (Look at the top card of your libra
_h_shore_lurker = _etb([["scry", {"n": 1}]])
# [ecl] When this creature enters, look at the top four cards of your library. You may r
_h_eclipsed_flamekin = _etb([["scry", {"n": 4}]])
# [ecl] When this artifact enters, draw a card, then choose a color. This artifact becom
_h_puca_s_eye = _etb([["draw", {"n": 1}]])
# [ecl] Whenever this creature becomes tapped, you gain 2 life.
_h_wanderbrine_preacher = _etb([["gain_life", {"n": 2}]])
# [ecl] When this creature enters, creatures you control get +1/+0 until end of turn. Ki
_h_gallant_fowlknight = _etb([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [ecl] Whenever this creature or another Kithkin you control enters, target creature yo
_h_thoughtweft_lieutenant = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [ecl] Menace (This creature can't be blocked except by two or more creatures.) | Vivid ?
_h_shimmercreep = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [ecl] When this enchantment enters, create two 1/1 green and white Kithkin creature to
_h_clachan_festival = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Menace (This creature can't be blocked except by two or more creatures.) | When th
_h_dawnhand_eulogist = _etb([["mill", {"n": 3, "target": "self"}], ["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [ecl] {1}{W}, {T}: Another target creature you control gains flying and lifelink until
_h_bre_of_clan_stoutarm = _etb([["draw", {"n": 1}]])
# [ecl] Vivid ? When this creature enters, create X 1/1 green and white Kithkin creature
_h_kithkeeper = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Deathtouch | Whenever another Goblin you control dies, this creature deals 1 damag
_h_boggart_cursecrafter = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [ecl] This creature must be blocked if able. | Whenever this creature attacks, another t
_h_vinebred_brawler = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [ecl] At the beginning of your end step, if another creature entered the battlefield u
_h_wary_farmer = _etb([["scry", {"n": 1}]])
# [ecl] When this creature enters, you may blight 2. If you do, create two 1/1 black and
_h_sourbread_auntie = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Whenever this creature becomes tapped, target creature an opponent controls gets
_h_wanderwine_distracter = _etb([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [ecl] When this creature enters, look at the top four cards of your library. You may r
_h_eclipsed_elf = _etb([["scry", {"n": 4}]])
# [ecl] When Lluwen enters, mill four cards, then you may put a creature or land card fr
_h_lluwen__imperfect_naturalist = _etb([["mill", {"n": 4, "target": "self"}]])
# [ecl] As an additional cost to cast this spell, behold a Kithkin or pay {2}. (To behol
_h_kinsbaile_aspirant = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [ecl] Changeling (This card is every creature type.) | When this creature enters, you ma
_h_changeling_wayfinder = _etb([["search_basic_land", {"n": 1}]])
# [ecl] Whenever this creature attacks, you draw a card and lose 1 life.
_h_moonglove_extractor = _etb([["draw", {"n": 1}]])
# [ecl] Flying | Whenever this creature becomes tapped, another target Merfolk you control
_h_tributary_vaulter = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [ecl] This spell costs {1} less to cast if you control a Kithkin. | When this creature e
_h_mistmeadow_council = _etb([["draw", {"n": 1}]])
# [ecl] When this creature enters, look at the top four cards of your library. You may r
_h_eclipsed_boggart = _etb([["scry", {"n": 4}]])
# [ecl] Whenever this creature enters or attacks, you may blight 2. If you do, you draw 
_h_blighted_blackthorn = _etb([["draw", {"n": 1}]])
# [ecl] When this creature enters or dies, create a Treasure token. (It's an artifact wi
_h_noggle_robber = _etb([["create_treasure", {"n": 1}]])
# [ecl] When this creature enters, look at the top four cards of your library. You may r
_h_eclipsed_merrow = _etb([["scry", {"n": 4}]])
# [ecl] Trample | Whenever another creature you control enters, this creature gets +1/+0 u
_h_crossroads_watcher = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [ecl] When this enchantment enters, you may blight 1. If you do, create two 1/1 black 
_h_boggart_mischief = _etb([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] At the beginning of your first main phase, you may blight 1. If you do, create a
_h_scuzzback_scrounger = _etb([["create_treasure", {"n": 1}]])
# [ecl] Whenever this creature becomes tapped, create a 1/1 blue and black Faerie creatu
_h_pestered_wellguard = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [ecl] As an additional cost to cast this spell, behold an Elemental and exile it. (Exi
_h_champion_of_the_path = _etb([["damage_any", {"n": 2}]])
# [ecl] When this creature enters or dies, surveil 1. (Look at the top card of your libr
_h_lys_alana_informant = _etb([["scry", {"n": 1}]])
# [ecl] As an additional cost to cast this spell, behold a Goblin or pay {2}. (To behold
_h_mudbutton_cursetosser = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [ecl] Flash | Enchant creature you control | When this Aura enters, enchanted creature gai
_h_aquitect_s_defenses = _etb([["scry", {"n": 0}]])
# [ecl] Trample | When this creature enters, create a Treasure token. (It's an artifact wi
_h_flamekin_gildweaver = _etb([["create_treasure", {"n": 1}]])
# [ecl] Whenever you cast a spell with mana value 4 or greater, draw a card.
_h_tanufel_rimespeaker = _etb([["draw", {"n": 1}]])
# [ecl] At the beginning of your upkeep, surveil 1. (Look at the top card of your librar
_h_morcant_s_eyes = _etb([["scry", {"n": 1}]])
# [ecl] Flying | When this creature enters, you may blight 1. If you do, each opponent dis
_h_dream_seizer = _etb([["discard", {"n": 1, "target": "opp"}]])
# [ecl] Deathtouch | Vivid ? When this creature enters, you gain life equal to the number 
_h_luminollusk = _etb([["gain_life", {"n": 2}]])
# [ecl] This creature enters with two -1/-1 counters on it. | Whenever another creature yo
_h_heirloom_auntie = _etb([["scry", {"n": 1}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_merrow_skyswimmer = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] As an additional cost to cast this spell, behold a Merfolk or pay {2}. (To behol
_h_silvergill_mentor = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] Reach | Whenever you cast a spell with mana value 4 or greater, this creature deal
_h_enraged_flamecaster = _etb([["damage_player", {"n": 2, "target": "opp"}]])
# [ecl] When this creature enters, look at the top four cards of your library. You may r
_h_eclipsed_kithkin = _etb([["scry", {"n": 4}]])
# [ecl] When this creature dies, draw a card.
_h_summit_sentinel = _etb([["draw", {"n": 1}]])
# [ecl] Whenever you cast a spell with mana value 4 or greater, this creature gets +2/+0
_h_kulrath_mystic = _etb([["scry", {"n": 0}]])
# [ecl] Lifelink | When this creature enters, mill two cards. (Put the top two cards of yo
_h_scarblade_scout = _etb([["mill", {"n": 2, "target": "self"}]])
# [ecl] When this creature enters and whenever you cast a spell with mana value 4 or gre
_h_flaring_cinder = _etb([["draw", {"n": 1}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_lofty_dreams = _etb([["draw", {"n": 1}]])
# [ecl] At the beginning of each end step, if you put a counter on a creature this turn,
_h_lasting_tarfire = _etb([["damage_player", {"n": 2, "target": "opp"}]])
# [ecl] Vigilance, reach | Ward {2} (Whenever this creature becomes the target of a spell 
_h_pummeler_for_hire = _etb([["gain_life", {"n": 1}]])
# [tmt] Deathtouch | Whenever another creature you control dies, you gain life equal to it
_h_south_wind_avatar = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 1, "target": "opp"}]])
# [tmt] When this creature enters, destroy up to one target noncreature artifact.
_h_rock_soldiers = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] When this creature enters, you may search your library for a Food card, reveal i
_h_courier_of_comestibles = _etb([["gain_life", {"n": 3}]])
# [tmt] Flying | Whenever an artifact you control enters, put a +1/+1 counter on Donatello
_h_donatello__way_with_machines = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When this creature enters, create a 1/1 colorless Robot artifact creature token.
_h_mechanized_ninja_cavalry = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] Alliance ? Whenever another creature you control enters, put a +1/+1 counter on 
_h_epf_point_squad = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Sneak {3}{W/B} (You may cast this spell for {3}{W/B} if you also return an unblo
_h_foot_ninjas = _etb([["gain_life", {"n": 3}]])
# [tmt] Sneak {3}{W}{W} (You may cast this spell for {3}{W}{W} if you also return an unb
_h_leonardo__leader_in_blue = _etb([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [tmt] When April O'Neil enters, scry 2. (Look at the top two cards of your library, th
_h_april_o_neil__kunoichi_trainee = _etb([["scry", {"n": 2}]])
# [tmt] When this artifact enters or leaves the battlefield, create a 1/1 colorless Robo
_h_mouser_foundry = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] Flying, vigilance | When this creature dies, draw a card.
_h_buzz_bots = _etb([["draw", {"n": 1}]])
# [tmt] Flying | Whenever this creature attacks, Dinosaurs you control other than this cre
_h_triceraton_commander = _etb([["scry", {"n": 0}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] During your turn, this creature has first strike. | Whenever this creature attacks
_h_null_group_biological_assets = _etb([["draw", {"n": 1}]])
# [tmt] Reach, trample | When this creature enters, you gain 2 life.
_h_primordial_pachyderm = _etb([["gain_life", {"n": 2}]])
# [tmt] When this artifact enters, destroy target creature. | {2}, {T}, Sacrifice this art
_h_anchovy___banana_pizza = _etb([["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] Trample | At the beginning of combat on your turn, put a +1/+1 counter on Savanti 
_h_savanti_romero__time_s_exile = _etb([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When this artifact enters, draw a card. | {1}, {T}, Sacrifice this artifact: Add o
_h_omni_cheese_pizza = _etb([["draw", {"n": 1}]])
# [tmt] Flying | When this creature leaves the battlefield, create a Food token. (It's an 
_h_featherbrained_filcher = _etb([["gain_life", {"n": 3}]])
# [tmt] When this creature enters, tap up to one target creature and put a stun counter 
_h_utrom_scientists = _etb([["scry", {"n": 0}]])
# [tmt] (Gain the next level as a sorcery to add its ability.) | When this Class enters, e
_h_party_dude = _etb([["gain_life", {"n": 3}]])
# [tmt] Enchant basic land you control | When this Aura enters, exile target creature an o
_h_dimensional_exile = _etb([["exile", {"target": "opp_biggest_creature"}]])
# [tmt] When this creature enters, mill three cards. (Put the top three cards of your li
_h_paramecia_coloniex = _etb([["mill", {"n": 3, "target": "self"}]])
# [tmt] Trample | Whenever this creature enters or attacks, you may sacrifice a token or a
_h_west_wind_avatar = _etb([["gain_life", {"n": 3}]])
# [tmt] When this artifact enters, it deals 4 damage to any target and 3 damage to you. | 
_h_spicy_oatmeal_pizza = _etb([["damage_any", {"n": 4}]])
# [tmt] Trample | Alliance ? Whenever another creature you control enters, this creature g
_h_mutant_town_musicians = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When this artifact enters, search your library for a basic land card, reveal it,
_h_everything_pizza = _etb([["search_basic_land", {"n": 1}]])
# [tmt] Trample | When General Traag enters, you may sacrifice another artifact. When you 
_h_general_traag__heart_of_stone = _etb([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [tmt] Whenever this Vehicle attacks, put a +1/+1 counter on target creature that crewe
_h_turtle_van = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Flying | Alliance ? Whenever another creature you control enters, The Neutrinos ge
_h_the_neutrinos = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When Sally Pride enters, create X 2/2 red Mutant creature tokens, where X is the
_h_sally_pride__lioness_leader = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] When Jennika enters, create a 2/2 red Mutant creature token. | Plainscycling {2} (
_h_jennika__bad_apple_big_sister = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] Whenever this creature attacks, another target creature you control gets +1/+0 a
_h_foot_elite = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Flying | When Stockman enters, draw a card, then discard a card. | Islandcycling {2}
_h_stockman__mad_fly_entist = _etb([["draw", {"n": 1}]])
# [tmt] Flying | When this Vehicle enters, create a 2/2 red Mutant creature token. | Crew 2 
_h_turtle_blimp = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] Flash | When this artifact enters, target creature gets +2/+2 until end of turn. U
_h_guac___marshmallow_pizza = _etb([["add_counters", {"n": 2, "target": "self"}]])
# [tmt] Flying, vigilance | Alliance ? Whenever another creature you control enters, this 
_h_east_wind_avatar = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [tmt] When Baxter Stockman enters, create a 1/1 colorless Robot artifact creature toke
_h_baxter_stockman = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] When Pizza Face enters, create a Food token. | Disappear ? At the beginning of you
_h_pizza_face__gastromancer = _etb([["gain_life", {"n": 3}]])
# [tmt] At the beginning of combat on your turn, create a 2/2 red Mutant creature token.
_h_old_hob__alleycat_blues = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tmt] When this creature enters, return up to one other target artifact you control to
_h_nobody = _etb([["scry", {"n": 1}]])
# [tmt] When Donatello enters, if you control an artifact, draw a card.
_h_donatello__turtle_techie = _etb([["draw", {"n": 1}]])
# [tmt] When this creature enters, create a 2/2 red Mutant creature token. | Alliance ? Wh
_h_mighty_mutanimals = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] Whenever this creature or another creature you control enters, you gain 1 life.
_h_bogwater_lumaret = _etb([["gain_life", {"n": 1}]])
# [sos] When this creature enters, you gain 1 life. | {2}{G}: This creature gets +2/+2 unt
_h_mindful_biomancer = _etb([["gain_life", {"n": 1}]])
# [sos] When this creature enters, create a 1/1 white and black Inkling creature token w
_h_eager_glyphmage = _etb([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [sos] When this creature enters, it deals 3 damage to each opponent and you gain 3 lif
_h_colossus_of_the_blood_age = _etb([["damage_player", {"n": 3, "target": "opp"}], ["gain_life", {"n": 3}]])
# [sos] This creature can't block. | Whenever this creature attacks, each opponent loses 1
_h_postmortem_professor = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [sos] Menace (This creature can't be blocked except by two or more creatures.) | Wheneve
_h_teacher_s_pest = _etb([["gain_life", {"n": 1}]])
# [sos] Whenever this creature enters or attacks, you may draw a card. If you do, discar
_h_stadium_tidalmage = _etb([["draw", {"n": 1}]])
# [sos] Flying | When this creature enters, each opponent loses 2 life and you gain 2 life
_h_sneering_shadewriter = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [sos] Reach | When this creature enters, look at the top five cards of your library. You
_h_paradox_surveyor = _etb([["scry", {"n": 5}]])
# [sos] Flying | When this creature enters, put a +1/+1 counter on another target creature
_h_ascendant_dustspeaker = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}]])
# [sos] Reach | When this creature dies, create two 1/1 black and green Pest creature toke
_h_pestbrood_sloth = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}]])
# [sos] Vigilance, reach | Infusion ? When this creature enters, put two +1/+1 counters on
_h_old_growth_educator = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Trample | Opus ? Whenever you cast an instant or sorcery spell, put a +1/+1 counte
_h_tackle_artist = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Opus ? Whenever you cast an instant or sorcery spell, draw a card. Then discard 
_h_muse_seeker = _etb([["draw", {"n": 1}]])
# [sos] When this creature enters, look at the top X cards of your library, where X is t
_h_stirring_honormancer = _etb([["scry", {"n": 1}]])
# [sos] Deathtouch | Whenever a creature you control with power or toughness 1 or less die
_h_arnyn__deathbloom_botanist = _etb([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [sos] When this creature enters, tap target creature an opponent controls and put a st
_h_deluge_virtuoso = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Reach | Opus ? Whenever you cast an instant or sorcery spell, this creature deals 
_h_thunderdrum_soloist = _etb([["damage_player", {"n": 1, "target": "opp"}]])
# [sos] Infusion ? When this creature enters, target creature an opponent controls gets 
_h_poisoner_s_apprentice = _etb([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [sos] Increment (Whenever you cast a spell, if the amount of mana you spent is greater
_h_pensive_professor = _etb([["draw", {"n": 1}]])
# [sos] When this enchantment enters, return target nonland permanent card with mana val
_h_primary_research = _etb([["draw", {"n": 1}]])
# [sos] Flying, haste | Each instant and sorcery card in your hand has miracle {2}. (You m
_h_lorehold__the_historian = _etb([["draw", {"n": 1}]])
# [sos] Flying | Opus ? Whenever you cast an instant or sorcery spell, this creature gets 
_h_spectacular_skywhale = _etb([["add_counters", {"n": 1, "target": "self"}], ["add_counters", {"n": 3, "target": "self"}]])
# [sos] Whenever you cast an instant or sorcery spell, you may tap three untapped creatu
_h_aziza__mage_tower_captain = _etb([["draw", {"n": 1}]])
# [sos] Flying, vigilance | Opus ? Whenever you cast an instant or sorcery spell, this cre
_h_elemental_mascot = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [sos] When Ennis enters, exile up to one other target creature you control. Return tha
_h_ennis__debate_moderator = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Whenever a creature you control dies, each opponent loses 1 life and you gain 1 
_h_cauldron_of_essence = _etb([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [sos] When this enchantment enters, create a 2/2 red and white Spirit creature token. | 
_h_living_history = _etb([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["add_counters", {"n": 2, "target": "self"}]])
# [sos] Trample | Whenever you gain life, put a +1/+1 counter on this creature.
_h_pest_mascot = _etb([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Whenever you gain life, put a +1/+1 counter on each Pest, Bat, Insect, Snake, an
_h_blech__loafing_pest = _etb([["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [sos] Flying | When Moseo enters, create a 1/1 black and green Pest creature token with 
_h_moseo__vein_s_new_dean = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}]])
# [sos] Trample, reach | Converge ? This creature enters with a +1/+1 counter on it for ea
_h_magmablood_archaic = _etb([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] Ward {2} | Increment (Whenever you cast a spell, if the amount of mana you spent i
_h_fractal_tender = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] Flying | This creature enters with X +1/+1 counters on it. | When this creature ente
_h_pterafractyl = _etb([["gain_life", {"n": 2}]])
# [sos] When this enchantment enters, create a 0/0 green and blue Fractal creature token
_h_additive_evolution = _etb([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] This spell costs {3} less to cast if creatures you control have total toughness 
_h_orysa__tide_choreographer = _etb([["draw", {"n": 2}]])
# [sos] Ward {1} (Whenever this creature becomes the target of a spell or ability an opp
_h_thornfist_striker = _etb([["add_counters", {"n": 1, "target": "all_friendly"}]])
# [sos] Opus ? Whenever you cast an instant or sorcery spell, target player mills three 
_h_exhibition_tidecaller = _etb([["mill", {"n": 3, "target": "self"}]])
# [sos] When this creature enters, draw a card. Each player loses 1 life. | Repartee ? Whe
_h_conciliator_s_duelist = _etb([["draw", {"n": 1}]])
# [sos] Increment (Whenever you cast a spell, if the amount of mana you spent is greater
_h_ambitious_augmenter = _etb([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] When this creature enters, create a 1/1 black and green Pest creature token with
_h_essenceknit_scholar = _etb([["gain_life", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}], ["draw", {"n": 1}]])
# [sos] Flying | When this creature enters, surveil 1. (Look at the top card of your libra
_h_owlin_historian = _etb([["scry", {"n": 1}]])
# [sos] Flying | When this Vehicle enters, you may search your library for a basic land ca
_h_strixhaven_skycoach = _etb([["search_basic_land", {"n": 1}]])
# [sos] Trample | Whenever this creature attacks, you gain 2 life.
_h_shopkeeper_s_bane = _etb([["gain_life", {"n": 2}]])
# [sos] Increment (Whenever you cast a spell, if the amount of mana you spent is greater
_h_textbook_tabulator = _etb([["scry", {"n": 2}]])
# [sos] Repartee ? Whenever you cast an instant or sorcery spell that targets a creature
_h_snooping_page = _etb([["draw", {"n": 1}]])
# [sos] Opus ? Whenever you cast an instant or sorcery spell, this creature gets +1/+1 u
_h_expressive_firedancer = _etb([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] When this creature enters, you may search your library for a basic land card, re
_h_environmental_scientist = _etb([["search_basic_land", {"n": 1}]])
# [sos] When this creature enters, you may discard a card. If you do, draw a card. | {T}, 
_h_rubble_rouser = _etb([["draw", {"n": 1}]])
# [sos] When this creature enters, return target instant or sorcery card from your grave
_h_zealous_lorecaster = _etb([["return_gy_to_hand", {"filter_type": "any"}]])
# [sos] Ward?Pay 3 life. (Whenever this creature becomes the target of a spell or abilit
_h_mica__reader_of_ruins = _etb([["draw", {"n": 1}]])
# [sos] Vigilance | When this creature enters, surveil 2. (Look at the top two cards of yo
_h_imperious_inkmage = _etb([["scry", {"n": 2}]])

# [woe] You may discard a card. If you do, draw two cards. | Create a Wicked Role token at
_h_witch_s_mark = _spell([["draw", {"n": 2}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Creatures you control get +2/+0 until end of turn. Whenever a nontoken creature 
_h_gnawing_crescendo = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}], ["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_thunderous_debut = _spell([["scry", {"n": 1}]])
# [woe] You may cast this spell as though it had flash if you pay {2} more to cast it. | F
_h_asinine_antics = _spell([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_stonesplitter_bolt = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [woe] This spell costs {1} less to cast for each creature that attacked this turn. | Dra
_h_rowdy_research = _spell([["draw", {"n": 3}]])
# [woe] Destroy target creature with mana value 3 or less. If it's your turn, create a F
_h_feed_the_cauldron = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}]])
# [woe] Target opponent discards two cards. Create a Wicked Role token attached to up to
_h_eriette_s_whisper = _spell([["discard", {"n": 2, "target": "opp"}]])
# [woe] Up to one target creature gets -1/-1 until end of turn. You create a 1/1 black R
_h_rat_out = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token can't block"]}]])
# [woe] Destroy up to one target artifact, enchantment, or creature with flying. Create 
_h_spider_food = _spell([["gain_life", {"n": 3}], ["destroy", {"target": "opp_biggest_creature"}]])
# [woe] Return all creatures to their owners' hands. For each opponent who controlled a 
_h_faerie_slumber_party = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["flying", "\"This token can block only creatures with flying"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_brave_the_wilds = _spell([["search_basic_land", {"n": 1}]])
# [woe] Choose two ? | ? Search your library for a basic land card, put it onto the battle
_h_return_from_the_wilds = _spell([["search_basic_land", {"n": 1}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["gain_life", {"n": 3}]])
# [woe] Target creature gets +3/+0 until end of turn. | Draw a card.
_h_sugar_rush = _spell([["add_counters", {"n": 3, "target": "self"}], ["draw", {"n": 1}]])
# [woe] Look at the top five cards of your library. You may exile a creature card from a
_h_feral_encounter = _spell([["scry", {"n": 5}]])
# [woe] Target creature gets +4/+4 until end of turn.
_h_titanic_growth = _spell([["add_counters", {"n": 4, "target": "self"}]])
# [woe] Create a Monster Role token attached to target creature you control. When you do
_h_curse_of_the_werefox = _spell([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] One or two target creatures each gain haste until end of turn. For each of those
_h_become_brutes = _spell([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_farsight_ritual = _spell([["scry", {"n": 4}]])
# [woe] Tap target creature an opponent controls and put three stun counters on it. Scry
_h_freeze_in_place = _spell([["scry", {"n": 2}]])
# [woe] Draw three cards. Create a 1/1 blue Faerie creature token with flying and "This 
_h_into_the_fae_court = _spell([["draw", {"n": 3}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying", "\"This token can block only creatures with flying"]}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_candy_grapple = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [woe] Flick a Coin deals 1 damage to any target. You create a Treasure token. (It's an
_h_flick_a_coin = _spell([["damage_any", {"n": 1}], ["create_treasure", {"n": 1}], ["draw", {"n": 1}]])
# [woe] Cut In deals 4 damage to target creature. | Create a Young Hero Role token attache
_h_cut_in = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Tap up to one target creature. Scry 1, then draw a card.
_h_plunge_into_winter = _spell([["draw", {"n": 1}], ["scry", {"n": 1}]])
# [woe] Return target creature card with mana value 3 or less from your graveyard to the
_h_return_triumphant = _spell([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [woe] Any number of target enchanted creatures you control and up to one other target 
_h_graceful_takedown = _spell([["damage_any", {"n": 2}]])
# [woe] Destroy target enchantment. If a permanent you controlled or a token was destroy
_h_break_the_spell = _spell([["draw", {"n": 1}], ["destroy", {"target": "opp_biggest_creature"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_archon_s_glory = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [woe] Choose one ? | ? Untap target creature. It gets +1/+0 and gains indestructible unt
_h_moment_of_valor = _spell([["scry", {"n": 0}], ["destroy", {"target": "opp_biggest_creature"}]])
# [woe] Target creature gets +1/+0 and gains first strike until end of turn. Scry 1.
_h_kindled_heroism = _spell([["scry", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_johann_s_stopgap = _spell([["bounce_to_hand", {}], ["draw", {"n": 1}]])
# [woe] Look at the top five cards of your library. You may reveal a creature card from 
_h_commune_with_nature = _spell([["scry", {"n": 5}]])
# [woe] Exile target creature. If you control an enchantment, scry 2.
_h_taken_by_nightmares = _spell([["exile", {"target": "opp_biggest_creature"}], ["scry", {"n": 2}]])
# [woe] Target creature gets +1/+3 and gains reach until end of turn. Untap it.
_h_leaping_ambush = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_back_for_seconds = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [woe] Frantic Firebolt deals X damage to target creature, where X is 2 plus the number
_h_frantic_firebolt = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [woe] Destroy target creature or enchantment. Create a Wicked Role token attached to u
_h_shatter_the_oath = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_rowan_s_grim_search = _spell([["scry", {"n": 4}], ["draw", {"n": 2}], ["lose_life", {"n": 2, "target": "self"}]])
# [woe] Bargain (You may sacrifice an artifact, enchantment, or token as you cast this s
_h_ice_out = _spell([["scry", {"n": 0}]])
# [lci] Counter target artifact or creature spell. Discover X, where X is that spell's m
_h_hurl_into_history = _spell([["draw", {"n": 1}]])
# [lci] Target creature gets +1/+3 and gains flying until end of turn. Untap it.
_h_acrobatic_leap = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [lci] Target creature you control gets +1/+0 until end of turn. It deals damage equal 
_h_huatli_s_final_strike = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Choose one ? | ? Destroy target artifact or enchantment. | ? Target creature you con
_h_over_the_edge = _spell([["destroy", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [lci] This spell costs {3} less to cast if it targets a tapped creature. | Exile target 
_h_quicksand_whirlpool = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [lci] Choose target creature you control and target creature you don't control. If the
_h_malamet_battle_glyph = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [lci] Return target creature to its owner's hand. If it was tapped, create a Map token
_h_brackish_blunder = _spell([["bounce_to_hand", {}]])
# [lci] Calamitous Cave-In deals X damage to each creature and each planeswalker, where 
_h_calamitous_cave_in = _spell([["damage_creature", {"n": 1, "target": "each_opp"}]])
# [lci] Target creature gets +3/+3 and gains trample until end of turn.
_h_staggering_size = _spell([["scry", {"n": 0}], ["add_counters", {"n": 3, "target": "self"}]])
# [lci] Choose three. You may choose the same mode more than once. | ? Search your library
_h_cosmium_confluence = _spell([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}], ["destroy", {"target": "opp_biggest_creature"}]])
# [lci] Choose one ? | ? Creatures you control get +1/+1 until end of turn. | ? Creatures yo
_h_family_reunion = _spell([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}], ["scry", {"n": 0}]])
# [lci] Discover 10. If the discovered card's mana value is less than 10, create a numbe
_h_hit_the_mother_lode = _spell([["draw", {"n": 1}]])
# [lci] Up to three target creatures can't block this turn. | Discover 4. (Exile cards fro
_h_daring_discovery = _spell([["draw", {"n": 1}]])
# [lci] Target creature gets +2/+0 and gains first strike until end of turn. | Create a Tr
_h_ancestors__aid = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}], ["create_treasure", {"n": 1}]])
# [lci] Target creature gets -5/-5 until end of turn. | Descend 4 ? That creature gets -10
_h_join_the_dead = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}], ["damage_creature", {"n": 10, "target": "opp_biggest"}]])
# [lci] Return up to one target permanent card from your graveyard to your hand. Discove
_h_walk_with_the_ancestors = _spell([["draw", {"n": 1}]])
# [lci] Return target creature card from your graveyard to the battlefield. That creatur
_h_defossilize = _spell([["return_gy_to_bf", {"filter_type": "creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [lci] Draw three cards, then discard a card.
_h_ancestral_reminiscence = _spell([["draw", {"n": 3}]])
# [lci] You may mill two cards. Then return up to two creature cards from your graveyard
_h_another_chance = _spell([["mill", {"n": 2, "target": "self"}]])
# [lci] Exile target creature, Vehicle, or nonbasic land. Scry 1. (Look at the top card 
_h_ray_of_ruin = _spell([["exile", {"target": "opp_biggest_creature"}], ["scry", {"n": 1}]])
# [lci] This spell costs {2} less to cast if it targets a creature spell. | Counter target
_h_out_of_air = _spell([["scry", {"n": 0}]])
# [mkm] Counter target spell unless its controller pays {2}. | Suspect up to one target cr
_h_reasonable_doubt = _spell([["scry", {"n": 0}]])
# [mkm] This spell costs {2} less to cast if a creature card was put into your graveyard
_h_macabre_reconstruction = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [mkm] Each player who controls the most creatures investigates. Then destroy all creat
_h_no_witnesses = _spell([["destroy_all_creatures", {}]])
# [mkm] Create a 2/2 white and blue Detective creature token. If a creature died this tu
_h_drag_the_canal = _spell([["gain_life", {"n": 2}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["scry", {"n": 2}], ["draw", {"n": 1}]])
# [mkm] Target creature gains deathtouch and lifelink until end of turn. Investigate. (C
_h_toxin_analysis = _spell([["draw", {"n": 1}]])
# [mkm] This spell can't be countered. (This includes by the ward ability.) | Tap up to tw
_h_out_cold = _spell([["draw", {"n": 1}]])
# [mkm] Search your library for a basic land card, put it onto the battlefield tapped, t
_h_they_went_this_way = _spell([["search_basic_land", {"n": 1}], ["draw", {"n": 1}]])
# [mkm] This spell can't be countered. (This includes by the ward ability.) | Gain control
_h_caught_red_handed = _spell([["scry", {"n": 0}]])
# [mkm] As an additional cost to cast this spell, sacrifice a creature that dealt damage
_h_treacherous_greed = _spell([["draw", {"n": 3}], ["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [mkm] Target opponent reveals their hand. You choose a nonland card from it. Exile tha
_h_soul_search = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [mkm] Target creature gets +3/+0 and gains first strike until end of turn. Investigate
_h_the_chase_is_on = _spell([["draw", {"n": 1}], ["add_counters", {"n": 3, "target": "self"}]])
# [mkm] This spell costs {3} less to cast if you've sacrificed an artifact this turn. | Th
_h_suspicious_detonation = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [mkm] Look at the top five cards of your library, cloak two of them, and put the rest 
_h_hide_in_plain_sight = _spell([["scry", {"n": 5}]])
# [mkm] Galvanize deals 3 damage to target creature. If you've drawn two or more cards t
_h_galvanize = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [mkm] Until end of turn, target creature gets +2/+0 and gains "When this creature dies
_h_presumed_dead = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [mkm] Target creature gets +2/+2 until end of turn. Investigate. (Create a Clue token.
_h_auspicious_arrival = _spell([["draw", {"n": 1}], ["add_counters", {"n": 2, "target": "self"}]])
# [mkm] Create a 0/0 green Ooze creature token with trample. Put X +1/+1 counters on it,
_h_slime_against_humanity = _spell([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": ["trample"]}]])
# [mkm] Target creature gets +3/+3 and gains trample until end of turn.
_h_fanatical_strength = _spell([["scry", {"n": 0}], ["add_counters", {"n": 3, "target": "self"}]])
# [mkm] Choose one or both ? | ? Destroy target creature. | ? Put a +1/+1 counter on target 
_h_deadly_complication = _spell([["destroy", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [mkm] Investigate. Creatures your opponents control get -2/-0 until end of turn. If an
_h_eliminate_the_impossible = _spell([["draw", {"n": 1}]])
# [mkm] Create a 0/1 green Plant creature token, then draw cards equal to the number of 
_h_audience_with_trostani = _spell([["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": []}]])
# [mkm] Return target creature card from your graveyard to the battlefield. Suspect it. 
_h_it_doesn_t_add_up = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [mkm] Creatures you control get +2/+1 until end of turn. Investigate. (Create a Clue t
_h_on_the_job = _spell([["draw", {"n": 1}], ["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [mkm] This spell costs {W}{U} more to cast for each target beyond the first. | Choose an
_h_officious_interrogation = _spell([["draw", {"n": 1}]])
# [mkm] Reveal the top five cards of your library and separate them into two piles. An o
_h_intrude_on_the_mind = _spell([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": ["flying", "then put a +1/+1 counter on it for each card put into your graveyard this way"]}]])
# [mkm] As an additional cost to cast this spell, you may collect evidence 6. This spell
_h_bite_down_on_crime = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [otj] Spree (Choose one or more additional costs.) | + {2}{B} ? Destroy target creature.
_h_unfortunate_accident = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Search your library for up to two basic land cards and/or Desert cards, put them
_h_map_the_frontier = _spell([["search_basic_land", {"n": 2}]])
# [otj] Target creature gets -1/-0 until end of turn. It gets -4/-0 until end of turn in
_h_take_the_fall = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [otj] Look at the top three cards of your library. You may exile a nonland card from a
_h_make_your_own_luck = _spell([["scry", {"n": 3}]])
# [otj] Create a Treasure token. Until end of turn, up to one target creature gets +2/+2
_h_gold_rush = _spell([["create_treasure", {"n": 1}], ["add_counters", {"n": 2, "target": "self"}]])
# [otj] Each player may shuffle their hand and graveyard into their library. Each player
_h_step_between_worlds = _spell([["draw", {"n": 7}]])
# [otj] Spree (Choose one or more additional costs.) | + {2} ? Return target creature card
_h_one_last_job = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [otj] Return up to one target creature card from your graveyard to your hand. Create a
_h_mourner_s_surprise = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["return_gy_to_hand", {"filter_type": "creature"}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Creatures you control get +2/+0 until end of turn. If you control an outlaw, exi
_h_outlaws__fury = _spell([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [otj] Until end of turn, each creature you control gets +2/+2 and gains trample and "T
_h_full_steam_ahead = _spell([["add_counters", {"n": 2, "target": "all_friendly"}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Until end of turn, target c
_h_metamorphic_blast = _spell([["draw", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Search your library for a b
_h_dance_of_the_tumbleweeds = _spell([["search_basic_land", {"n": 1}]])
# [otj] Hell to Pay deals X damage to target creature. Create a number of tapped Treasur
_h_hell_to_pay = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [otj] Trick Shot deals 6 damage to target creature and 2 damage to up to one other tar
_h_trick_shot = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [otj] Create X 1/1 red Mercenary creature tokens with "{T}: Target creature you contro
_h_form_a_posse = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"{T}: Target creature you control gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Target creature gets -2/-2 until end of turn. It gets an additional -1/-1 until 
_h_desert_s_due = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [otj] Until end of turn, target creature you control gets +1/+1 and target creature an
_h_skulduggery = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Exile target nontoken creat
_h_getaway_glamer = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [otj] Exile target creature. If it had mana value 3 or less, surveil 2. (Look at the t
_h_consuming_ashes = _spell([["exile", {"target": "opp_biggest_creature"}], ["scry", {"n": 2}]])
# [otj] Return up to one target creature card from your graveyard to the battlefield. Re
_h_badlands_revival = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [otj] Surveil 3 if you have no cards in hand. Then draw three cards. (To surveil 3, lo
_h_plan_the_heist = _spell([["draw", {"n": 3}], ["scry", {"n": 3}]])
# [otj] Target creature you control gets +1/+1 and gains first strike until end of turn.
_h_quick_draw = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Spree (Choose one or more additional costs.) | + {2}{R} ? Untap all creatures you 
_h_great_train_heist = _spell([["add_counters", {"n": 1, "target": "all_friendly"}], ["damage_player", {"n": 1, "target": "opp"}]])
# [otj] Destroy target tapped creature. You gain 2 life.
_h_eriette_s_lullaby = _spell([["gain_life", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {2} ? Explosive Derailment deals 
_h_explosive_derailment = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["destroy", {"target": "opp_biggest_creature"}]])
# [otj] As an additional cost to cast this spell, sacrifice a creature. | Draw two cards.
_h_corrupted_conviction = _spell([["draw", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {2} ? Put two +1/+1 counters on t
_h_trash_the_town = _spell([["add_counters", {"n": 1, "target": "self"}], ["scry", {"n": 0}], ["draw", {"n": 2}]])
# [otj] Spree (Choose one or more additional costs.) | + {3} ? Put a +1/+1 counter on targ
_h_jailbreak_scheme = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Target creature you control gains hexproof until end of turn. Untap that creatur
_h_fleeting_reflection = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Thunder Salvo deals X damage to target creature, where X is 2 plus the number of
_h_thunder_salvo = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [otj] Target creature you control gets +1/+1 until end of turn. Put a +1/+1 counter on
_h_throw_from_the_saddle = _spell([["add_counters", {"n": 1, "target": "self"}], ["add_counters", {"n": 1, "target": "self"}]])
# [otj] Create X 2/1 green Varmint creature tokens, where X is the number of creature ca
_h_rise_of_the_varmints = _spell([["create_token", {"count": 1, "power": "2", "toughness": "1", "keywords": []}]])
# [otj] This spell costs {1} less to cast if you've committed a crime this turn. (Target
_h_seize_the_secrets = _spell([["draw", {"n": 2}]])
# [otj] You may discard a card or sacrifice a land. If you do, draw two cards. | Plot {1}{
_h_highway_robbery = _spell([["draw", {"n": 2}]])
# [otj] Put a +1/+1 counter on target creature. It gains lifelink and indestructible unt
_h_take_up_the_shield = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [otj] Spree (Choose one or more additional costs.) | + {1} ? Untap all creatures target 
_h_rustler_rampage = _spell([["scry", {"n": 0}]])
# [otj] Target creature you control deals damage equal to its power to each of two other
_h_betrayal_at_the_vault = _spell([["damage_any", {"n": 2}]])
# [otj] Return target nonland permanent to its owner's hand. If you control a Desert, su
_h_failed_fording = _spell([["bounce_to_hand", {}], ["scry", {"n": 1}]])
# [big] Create a token that's a copy of target artifact or creature you control, except 
_h_molten_duplication = _spell([["scry", {"n": 0}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [blb] Conduct Electricity deals 6 damage to target creature and 2 damage to up to one 
_h_conduct_electricity = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [blb] Gift a tapped Fish (You may promise an opponent a gift as you cast this spell. I
_h_mind_spiral = _spell([["draw", {"n": 3}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_wildfire_howl = _spell([["damage_any", {"n": 1}], ["damage_creature", {"n": 2, "target": "each_opp"}]])
# [blb] Target creature you control gets +1/+0 until end of turn. Then it deals damage e
_h_rabid_gnaw = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [blb] Playful Shove deals 1 damage to any target. | Draw a card.
_h_playful_shove = _spell([["damage_any", {"n": 1}], ["draw", {"n": 1}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_coiling_rebirth = _spell([["return_gy_to_bf", {"filter_type": "creature"}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [blb] Return up to two target creature cards from your graveyard to your hand. Each op
_h_hazel_s_nocturne = _spell([["gain_life", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [blb] Draw X cards.
_h_mind_spring = _spell([["draw", {"n": 1}]])
# [blb] Target opponent discards two cards. Then if you control a Rat, surveil 2. (Look 
_h_psychic_whorl = _spell([["discard", {"n": 2, "target": "opp"}], ["scry", {"n": 2}]])
# [blb] Create a 1/1 blue and red Otter creature token with prowess. If this spell was c
_h_otterball_antics = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["prowess"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] Gift a Food (You may promise an opponent a gift as you cast this spell. If you d
_h_valley_rally = _spell([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [blb] Choose up to five {P} worth of modes. You may choose the same mode more than onc
_h_season_of_the_bold = _spell([["mill", {"n": 2, "target": "self"}]])
# [blb] Target creature you control deals damage equal to its power to target creature y
_h_rabid_bite = _spell([["damage_any", {"n": 2}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_starfall_invocation = _spell([["destroy_all_creatures", {}]])
# [blb] Choose one ? | ? Agate Assault deals 4 damage to target creature. If that creature
_h_agate_assault = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["exile", {"target": "opp_biggest_creature"}]])
# [blb] Choose one ? | ? Counter target spell. | ? Surveil 2, then draw two cards. (To surve
_h_spellgyre = _spell([["scry", {"n": 0}], ["draw", {"n": 2}], ["scry", {"n": 2}]])
# [blb] This spell costs {1} less to cast if you control an Otter. | Draw two cards.
_h_pearl_of_wisdom = _spell([["draw", {"n": 2}]])
# [blb] Gift a Food (You may promise an opponent a gift as you cast this spell. If you d
_h_crumb_and_get_it = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_peerless_recycling = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [blb] Creatures you control get +2/+1 until end of turn. If you control a Rabbit, scry
_h_rabbit_response = _spell([["scry", {"n": 2}], ["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [blb] Surveil 2, then draw two cards. You lose 2 life. (To surveil 2, look at the top 
_h_diresight = _spell([["draw", {"n": 2}], ["scry", {"n": 2}], ["lose_life", {"n": 2, "target": "self"}]])
# [blb] Target opponent exiles a card from their hand. If this spell was cast from a gra
_h_ruthless_negotiation = _spell([["draw", {"n": 1}]])
# [blb] Target creature gets +1/+3 and gains reach until end of turn. Untap it.
_h_high_stride = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [blb] Gift a tapped Fish (You may promise an opponent a gift as you cast this spell. I
_h_sazacap_s_brew = _spell([["draw", {"n": 2}], ["add_counters", {"n": 2, "target": "self"}]])
# [blb] Gift a card (You may promise an opponent a gift as you cast this spell. If you d
_h_consumed_by_greed = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [blb] Destroy target creature with power or toughness 4 or greater.
_h_repel_calamity = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [blb] Target creature gets +2/+2 until end of turn. Up to one other target creature ge
_h_mabel_s_mettle = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [blb] Flame Lash deals 4 damage to any target.
_h_flame_lash = _spell([["damage_any", {"n": 4}]])
# [blb] Return up to two target creatures to their owners' hands. Draw two cards, then d
_h_calamitous_tide = _spell([["draw", {"n": 2}]])
# [blb] Sonar Strike deals 4 damage to target attacking, blocking, or tapped creature. Y
_h_sonar_strike = _spell([["gain_life", {"n": 3}]])
# [blb] Look at twice X cards from the top of your library. Put X cards from among them 
_h_stargaze = _spell([["lose_life", {"n": 1, "target": "self"}]])
# [blb] Create X tokens that are copies of target token you control. Then tokens you con
_h_for_the_common_good = _spell([["gain_life", {"n": 1}]])
# [blb] Target creature gets -2/-2 until end of turn. Create a Food token. (It's an arti
_h_savor = _spell([["gain_life", {"n": 3}]])
# [blb] Take Out the Trash deals 3 damage to target creature or planeswalker. If you con
_h_take_out_the_trash = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [blb] Create three 1/1 white Rabbit creature tokens.
_h_hop_to_it = _spell([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [blb] Gift a Food (You may promise an opponent a gift as you cast this spell. If you d
_h_nocturnal_hunger = _spell([["destroy", {"target": "opp_biggest_creature"}], ["lose_life", {"n": 2, "target": "self"}]])
# [blb] Choose one ? | ? Exile target creature. | ? Target opponent exiles an enchantment th
_h_early_winter = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [dsk] Look at the top four cards of your library. Put one of them into your hand and t
_h_commune_with_evil = _spell([["gain_life", {"n": 3}], ["scry", {"n": 4}]])
# [dsk] Target nonland permanent's owner puts it on their choice of the top or bottom of
_h_vanish_from_sight = _spell([["scry", {"n": 1}]])
# [dsk] Destroy target creature. If a creature card is put into a graveyard this way, re
_h_come_back_wrong = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Target creature gets +2/+2 and gains lifelink until end of turn.
_h_give_in_to_violence = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [dsk] Choose target creature you control and target creature an opponent controls. | Del
_h_beastie_beatdown = _spell([["damage_any", {"n": 2}]])
# [dsk] Create three 1/1 red Gremlin creature tokens. Gremlins you control gain menace, 
_h_midnight_mayhem = _spell([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Choose one ? | ? Counter target spell. | ? Manifest dread. (Look at the top two card
_h_twist_reality = _spell([["scry", {"n": 0}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Target creature can't be blocked this turn. | Draw a card.
_h_enter_the_enigma = _spell([["draw", {"n": 1}]])
# [dsk] Search your library for a Demon card, reveal it, put it into your hand, then shu
_h_demonic_counsel = _spell([["draw", {"n": 1}], ["draw", {"n": 1}]])
# [dsk] Until end of turn, target creature gets +2/+2, gains flying, and becomes a Horro
_h_jump_scare = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [dsk] Target creature you control deals damage equal to its power to each other creatu
_h_waltz_of_rage = _spell([["damage_any", {"n": 2}]])
# [dsk] Return up to one target nonland permanent to its owner's hand. Manifest dread. (
_h_unnerving_grasp = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_seized_from_slumber = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Manifest dread. (Look at the top two cards of your library. Put one onto the bat
_h_under_the_skin = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Discard your hand. Then draw X cards, where X is the number of card types among 
_h_peer_past_the_veil = _spell([["draw", {"n": 1}]])
# [dsk] Destroy target creature. Its controller manifests dread. (That player looks at t
_h_unwanted_remake = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Winter's Intervention deals 2 damage to target creature. You gain 2 life.
_h_winter_s_intervention = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}], ["gain_life", {"n": 2}]])
# [dsk] Destroy target creature.
_h_murder = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Choose one ? | ? Exile target artifact. | ? Exile target enchantment. | ? Manifest dre
_h_break_down_the_door = _spell([["exile", {"target": "opp_biggest_creature"}], ["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Draw two cards. Create a 1/1 white Glimmer enchantment creature token.
_h_glimmerburst = _spell([["draw", {"n": 2}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [dsk] Return target creature card from your graveyard to the battlefield with a finali
_h_rite_of_the_moth = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [dsk] Tap one or two target untapped creatures you control. They each deal damage equa
_h_coordinated_clobbering = _spell([["damage_any", {"n": 2}]])
# [dsk] Choose one ? | ? Return target creature card from your graveyard to the battlefiel
_h_live_or_die = _spell([["return_gy_to_bf", {"filter_type": "creature"}], ["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Delirium ? Choose one. If there are four or more card types among cards in your 
_h_let_s_play_a_game = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}], ["discard", {"n": 2, "target": "opp"}], ["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [dsk] Manifest dread. (Look at the top two cards of your library. Put one onto the bat
_h_manifest_dread = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [dsk] Delirium ? This spell costs {2} less to cast as long as there are four or more c
_h_drag_to_the_roots = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dsk] Impossible Inferno deals 6 damage to target creature. | Delirium ? If there are fo
_h_impossible_inferno = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [dsk] Return target creature card from your graveyard to the battlefield. You gain 3 l
_h_emerge_from_the_cocoon = _spell([["gain_life", {"n": 3}], ["return_gy_to_bf", {"filter_type": "creature"}]])
# [fdn] This spell costs {3} less to cast if you've gained 3 or more life this turn. | Ret
_h_sanguine_indulgence = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Destroy target creature or planeswalker.
_h_hero_s_downfall = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Return target creature card from your graveyard to your hand. If it's a Zombie c
_h_cemetery_recruitment = _spell([["draw", {"n": 1}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Destroy target creature. Create a Food token. (It's an artifact with "{2}, {T}, 
_h_bake_into_a_pie = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}]])
# [fdn] As an additional cost to cast this spell, discard a card. | Draw two cards.
_h_thrill_of_possibility = _spell([["draw", {"n": 2}]])
# [fdn] Target creature's owner puts it on their choice of the top or bottom of their li
_h_uncharted_voyage = _spell([["scry", {"n": 1}]])
# [fdn] Creatures you control get +10/+10 and gain vigilance until end of turn.
_h_preposterous_proportions = _spell([["add_counters", {"n": 10, "target": "all_friendly"}]])
# [fdn] Creatures you control get +3/+3 and gain trample until end of turn. (Each of tho
_h_overrun = _spell([["add_counters", {"n": 3, "target": "all_friendly"}]])
# [fdn] Each creature you control gets +3/+3 until end of turn and must be blocked this 
_h_joraga_invocation = _spell([["add_counters", {"n": 3, "target": "all_friendly"}], ["add_counters", {"n": 3, "target": "self"}]])
# [fdn] Counter target noncreature spell. Its controller creates two Treasure tokens. (T
_h_an_offer_you_can_t_refuse = _spell([["create_treasure", {"n": 1}]])
# [fdn] Create a tapped 1/1 black Rat creature token for each creature card in your grav
_h_revenge_of_the_rats = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [fdn] Target creature you control gets +0/+3 and gains hexproof until end of turn. (It
_h_dive_down = _spell([["scry", {"n": 0}], ["add_counters", {"n": 0, "target": "self"}]])
# [fdn] Search your library for up to two basic land cards and/or Gate cards, put them o
_h_circuitous_route = _spell([["search_basic_land", {"n": 2}]])
# [fdn] Seismic Rupture deals 2 damage to each creature without flying.
_h_seismic_rupture = _spell([["damage_creature", {"n": 2, "target": "each_opp"}]])
# [fdn] Target creature gets +2/+2 and gains indestructible until end of turn. (Damage a
_h_adamant_will = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [fdn] Affinity for Cats (This spell costs {1} less to cast for each Cat you control.) | 
_h_claws_out = _spell([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [fdn] Incinerating Blast deals 6 damage to target creature. | You may discard a card. If
_h_incinerating_blast = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [fdn] Kicker {2}{W} (You may pay an additional {2}{W} as you cast this spell.) | Target 
_h_divine_resilience = _spell([["scry", {"n": 0}]])
# [fdn] Creatures you control get +1/+0 and gain indestructible until end of turn. (Dama
_h_make_a_stand = _spell([["add_counters", {"n": 1, "target": "all_friendly"}]])
# [fdn] Draw a card for each different mana value among nonland permanents you control.
_h_lunar_insight = _spell([["draw", {"n": 1}]])
# [fdn] Create a token that's a copy of target creature you control. | Flashback {3}{U} (Y
_h_self_reflection = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [fdn] Choose one ? | ? Destroy target creature or planeswalker. | ? Return target Zombie c
_h_deadly_plot = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Target creature you control deals damage equal to its power to target creature o
_h_bite_down = _spell([["damage_any", {"n": 2}]])
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
_h_goblin_surprise = _spell([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}], ["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] Counter target spell.
_h_cancel = _spell([["scry", {"n": 0}]])
# [fdn] Gain control of target creature until end of turn. Untap that creature. It gains
_h_involuntary_employment = _spell([["create_treasure", {"n": 1}]])
# [fdn] Each opponent loses X life. You gain life equal to the life lost this way.
_h_exsanguinate = _spell([["lose_life", {"n": 1, "target": "opp"}], ["gain_life", {"n": 2}]])
# [fdn] Draw a card for each creature you control with a +1/+1 counter on it. Those crea
_h_inspiring_call = _spell([["draw", {"n": 1}]])
# [fdn] Until end of turn, target creature gets +2/+0 and gains "When this creature dies
_h_fake_your_own_death = _spell([["create_treasure", {"n": 1}], ["add_counters", {"n": 2, "target": "self"}]])
# [fdn] Target creature gets -1/-0 until end of turn. | Draw a card.
_h_fleeting_distraction = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [fdn] Mill three cards, then return an instant or sorcery card from your graveyard to 
_h_inspiration_from_beyond = _spell([["mill", {"n": 3, "target": "self"}]])
# [fdn] Create two 1/1 white Soldier creature tokens. Until end of turn, creatures you c
_h_heroic_reinforcements = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [fdn] Return up to two target creature cards from your graveyard to your hand, then di
_h_macabre_waltz = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fdn] Create two 1/1 red Goblin creature tokens.
_h_dragon_fodder = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fdn] ({U/R} can be paid with either {U} or {R}.) | When you next cast an instant or sor
_h_teach_by_example = _spell([["draw", {"n": 1}]])
# [fdn] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_luminous_rebuke = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Target opponent sacrifices a creature of their choice. You gain life equal to th
_h_tribute_to_hunger = _spell([["gain_life", {"n": 2}]])
# [fdn] Deadly Riposte deals 3 damage to target tapped creature and you gain 2 life.
_h_deadly_riposte = _spell([["gain_life", {"n": 2}]])
# [fdn] Target creature gets +1/+0 and gains first strike until end of turn. (It deals c
_h_kindled_fury = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [fdn] Destroy target creature or enchantment.
_h_mortify = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fdn] Target creature gets +3/+0 and gains first strike until end of turn. (It deals c
_h_sure_strike = _spell([["scry", {"n": 0}], ["add_counters", {"n": 3, "target": "self"}]])
# [fdn] Put a +1/+1 counter on target creature you control. Then that creature deals dam
_h_felling_blow = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [fdn] This spell costs {1} less to cast if you control a Wizard. | Draw three cards.
_h_arcane_epiphany = _spell([["draw", {"n": 3}]])
# [dft] Destroy target creature with toughness 4 or greater. | Cycling {2} ({2}, Discard t
_h_gallant_strike = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dft] Target creature gets +X/+0 and gains first strike until end of turn.
_h_pedal_to_the_metal = _spell([["scry", {"n": 0}]])
# [dft] This spell costs {1} less to cast if it targets a Mount or Vehicle you control. | 
_h_run_over = _spell([["damage_any", {"n": 2}]])
# [dft] Choose one ? | ? Destroy target Vehicle. | ? Crash and Burn deals 6 damage to target
_h_crash_and_burn = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [dft] Target creature gets +4/+4 and gains trample until end of turn.
_h_bestow_greatness = _spell([["scry", {"n": 0}], ["add_counters", {"n": 4, "target": "self"}]])
# [dft] Affinity for artifacts (This spell costs {1} less to cast for each artifact you 
_h_voyage_home = _spell([["draw", {"n": 3}]])
# [dft] Return all Mount and Vehicle cards from your graveyard to the battlefield. Sacri
_h_push_the_limit = _spell([["scry", {"n": 0}]])
# [dft] Choose target opponent. Create two 1/1 colorless Thopter artifact creature token
_h_haunt_the_network = _spell([["gain_life", {"n": 1}], ["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [dft] Target creature gets -6/-6 until end of turn. You gain 2 life.
_h_syphon_fuel = _spell([["gain_life", {"n": 2}]])
# [dft] All creatures and Vehicles lose indestructible until end of turn, then destroy a
_h_spectacular_pileup = _spell([["destroy_all_creatures", {}]])
# [dft] Choose one ? | ? Target creature you control fights target creature an opponent co
_h_plow_through = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [dft] Draw two cards. Each player loses 2 life.
_h_risky_shortcut = _spell([["draw", {"n": 2}]])
# [dft] Return target creature or Vehicle card from your graveyard to the battlefield. C
_h_back_on_track = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"This token saddles Mounts", "crews Vehicles as though its power were 2 greater"]}]])
# [dft] Destroy target creature or Vehicle.
_h_spin_out = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [dft] Exile up to one target artifact or creature. Return it to the battlefield under 
_h_explosive_getaway = _spell([["damage_creature", {"n": 4, "target": "each_opp"}]])
# [dft] As an additional cost to cast this spell, sacrifice an artifact or creature. | Des
_h_hellish_sideswipe = _spell([["destroy", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}]])
# [dft] Road Rage deals X damage to target creature or planeswalker, where X is 2 plus t
_h_road_rage = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [dft] Target creature gets +2/+2 until end of turn. | Cycling {2} ({2}, Discard this car
_h_lightshield_parry = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [dft] Put a +1/+1 counter on target creature. It gains deathtouch and indestructible u
_h_maximum_overdrive = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [dft] Target creature gets -1/-1 until end of turn. | Cycling {B} ({B}, Discard this car
_h_locust_spray = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [tdm] As an additional cost to cast this spell, sacrifice a creature. | Exile target cre
_h_worthy_cost = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [tdm] Exile target permanent with mana value 3 or greater.
_h_kin_tree_severance = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [tdm] Narset's Rebuke deals 5 damage to target creature. Add {U}{R}{W}. If that creatu
_h_narset_s_rebuke = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [tdm] Surveil 2, then draw two cards. You lose 2 life. (To surveil 2, look at the top 
_h_cruel_truths = _spell([["draw", {"n": 2}], ["scry", {"n": 2}], ["lose_life", {"n": 2, "target": "self"}]])
# [tdm] This spell costs {2} less to cast if you've cast another spell this turn. | Choose
_h_rally_the_monastery = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": ["prowess"]}], ["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}], ["destroy", {"target": "opp_biggest_creature"}]])
# [tdm] Return target creature card from your graveyard to your hand. Lie in Wait deals 
_h_lie_in_wait = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [tdm] Target creature gets +3/+0 until end of turn. | Draw a card.
_h_rebellious_strike = _spell([["add_counters", {"n": 3, "target": "self"}], ["draw", {"n": 1}]])
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
# [tdm] Tap target creature. Put three stun counters on it. (If a permanent with a stun 
_h_riverwheel_sweep = _spell([["mill", {"n": 2, "target": "self"}]])
# [tdm] Choose one ? | ? The owner of target nonland permanent puts it on their choice of 
_h_riverwalk_technique = _spell([["scry", {"n": 0}]])
# [tdm] Return target creature to its owner's hand. | Harmonize {5}{U} (You may cast this 
_h_ureni_s_rebuff = _spell([["bounce_to_hand", {}]])
# [tdm] Target opponent reveals their hand. You choose a nonland card from it and exile 
_h_aggressive_negotiations = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [tdm] Draw a card. | Harmonize {5}{U} (You may cast this card from your graveyard for it
_h_unending_whisper = _spell([["draw", {"n": 1}]])
# [tdm] Search your library for a basic land card, put it onto the battlefield tapped, t
_h_roamer_s_routine = _spell([["search_basic_land", {"n": 1}]])
# [tdm] Choose one ? | ? Exile the top two cards of your library. Until the end of your ne
_h_seize_opportunity = _spell([["mill", {"n": 2, "target": "self"}], ["add_counters", {"n": 2, "target": "self"}]])
# [tdm] As an additional cost to cast this spell, you may behold a Dragon. (You may choo
_h_piercing_exhale = _spell([["scry", {"n": 2}]])
# [tdm] Destroy target creature. Create two 1/1 red Warrior creature tokens. They gain h
_h_salt_road_skirmish = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Choose one ? | ? Creatures you control get +3/+3 until end of turn. | ? Return up to
_h_rydia_s_return = _spell([["add_counters", {"n": 3, "target": "all_friendly"}], ["add_counters", {"n": 3, "target": "self"}]])
# [fin] This spell costs {2} less to cast if it targets a tapped creature. | Destroy targe
_h_fate_of_the_sun_cryst = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [fin] Search your library for up to two basic land cards and/or Town cards with differ
_h_reach_the_horizon = _spell([["search_basic_land", {"n": 2}]])
# [fin] Choose one ? | ? Take the Elevator ? Create three 1/1 colorless Hero creature toke
_h_aerith_rescue_mission = _spell([["create_token", {"count": 3, "power": "1", "toughness": "1", "keywords": []}], ["scry", {"n": 0}]])
# [fin] Choose target spell. Surveil 2, then counter the chosen spell unless its control
_h_swallowed_by_leviathan = _spell([["scry", {"n": 2}]])
# [fin] Return target creature card from your graveyard to the battlefield with two addi
_h_evil_reawakened = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [fin] Target player draws two cards. Put a +1/+1 counter on up to one target creature 
_h_combat_tutorial = _spell([["draw", {"n": 2}], ["add_counters", {"n": 1, "target": "self"}]])
# [fin] You draw two cards and you lose 2 life. Create a 0/1 black Wizard creature token
_h_circle_of_power = _spell([["damage_player", {"n": 1, "target": "opp"}], ["draw", {"n": 2}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": ["\"Whenever you cast a noncreature spell", "this token deals 1 damage to each opponent"]}], ["lose_life", {"n": 2, "target": "self"}], ["scry", {"n": 0}]])
# [fin] Destroy target creature an opponent controls. Then draw a card for each creature
_h_deadly_embrace = _spell([["destroy", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}]])
# [fin] Return up to two target creature cards from your graveyard to your hand.
_h_fight_on_ = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [fin] As an additional cost to cast this spell, discard a card. | Draw two cards. | Flashb
_h_laughing_mad = _spell([["draw", {"n": 2}]])
# [fin] Attacking creatures get +2/+0 until end of turn. | Flashback {2}{W}{W} (You may ca
_h_auron_s_inspiration = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [fin] Target creature gets -0/-9999 until end of turn.
_h_overkill = _spell([["damage_creature", {"n": 0, "target": "opp_biggest"}]])
# [fin] Affinity for Towns (This spell costs {1} less to cast for each Town you control.
_h_travel_the_overworld = _spell([["draw", {"n": 4}]])
# [fin] Target opponent sacrifices a creature of their choice. | Create a 0/1 black Wizard
_h_cornered_by_black_mages = _spell([["damage_player", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "0", "toughness": "1", "keywords": ["\"Whenever you cast a noncreature spell", "this token deals 1 damage to each opponent"]}]])
# [fin] Look at the top three cards of your library. Put one of them into your hand and 
_h_resentful_revelation = _spell([["scry", {"n": 3}]])
# [fin] Search your library for a Vehicle card, reveal it, and put it into your hand. If
_h_from_father_to_son = _spell([["draw", {"n": 1}]])
# [fin] Tiered (Choose one additional cost.) | ? Blizzard ? {0} ? Return target creature t
_h_ice_magic = _spell([["bounce_to_hand", {}]])
# [fin] Until end of turn, target creature gets +1/+0 and gains "When this creature dies
_h_galuf_s_final_act = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [fin] Light of Judgment deals 6 damage to target creature. Destroy up to one Equipment
_h_light_of_judgment = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [fin] Kicker?Sacrifice an artifact or creature. (You may sacrifice an artifact or crea
_h_vayne_s_treachery = _spell([["scry", {"n": 0}], ["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [fin] Destroy target creature. You gain 2 life.
_h_sephiroth_s_intervention = _spell([["destroy", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 2}]])
# [fin] For each creature you control, create a 1/2 white Moogle creature token with lif
_h_moogles__valor = _spell([["create_token", {"count": 1, "power": "1", "toughness": "2", "keywords": ["lifelink"]}]])
# [fin] This spell can't be countered. | Return target nonland permanent to its owner's ha
_h_eject = _spell([["bounce_to_hand", {}], ["draw", {"n": 1}]])
# [fin] Target creature gets +2/+2 until end of turn. If you control three or more creat
_h_you_re_not_alone = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [fin] Search your library for a Mountain card, reveal it, put it into your hand, then 
_h_call_the_mountain_chocobo = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["\"Whenever a land you control enters", "this token gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [fin] Judgment Bolt deals 5 damage to target creature and X damage to that creature's 
_h_judgment_bolt = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [fin] Choose one or more ? | ? Target creature you control fights target creature an opp
_h_clash_of_the_eikons = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [fin] Search your library for a basic land card or Town card, put it onto the battlefi
_h_prishe_s_wanderings = _spell([["add_counters", {"n": 1, "target": "self"}], ["search_basic_land", {"n": 1}]])
# [fin] Target creature gets +3/+3 and gains trample until end of turn.
_h_blitzball_shot = _spell([["scry", {"n": 0}], ["add_counters", {"n": 3, "target": "self"}]])
# [fin] Create a token that's a copy of target artifact, creature, or land.
_h_relm_s_sketching = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [fin] Create four 1/1 colorless Hero creature tokens. Then put a +1/+1 counter on each
_h_the_crystal_s_chosen = _spell([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 4, "power": "1", "toughness": "1", "keywords": []}]])
# [fin] Create a 2/2 green Bird creature token with "Whenever a land you control enters,
_h_gysahl_greens = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": ["\"Whenever a land you control enters", "this token gets +1/+0 until end of turn"]}], ["add_counters", {"n": 1, "target": "self"}]])
# [eoe] Choose one ? | ? Put five charge counters on target Spacecraft or Planet you contr
_h_drill_too_deep = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Target creature gets +3/+0 and gains first strike and reach until end of turn.
_h_rig_for_war = _spell([["add_counters", {"n": 3, "target": "self"}]])
# [eoe] As an additional cost to cast this spell, sacrifice an artifact or creature. | Des
_h_embrace_oblivion = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Creatures you control get +2/+0 until end of turn. If it's not your turn, untap 
_h_zealous_display = _spell([["add_counters", {"n": 2, "target": "all_friendly"}], ["add_counters", {"n": 2, "target": "self"}]])
# [eoe] Create a Lander token. Then you may sacrifice an artifact. When you do, Lithobra
_h_lithobraking = _spell([["damage_creature", {"n": 2, "target": "each_opp"}]])
# [eoe] Exile target creature or Spacecraft.
_h_gravkill = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [eoe] Destroy target artifact or tapped creature. You gain 3 life.
_h_radiant_strike = _spell([["gain_life", {"n": 3}], ["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Put a +1/+1 counter on target creature you control. It gains reach, trample, and
_h_biosynthic_burst = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [eoe] You draw two cards and lose 2 life. | Void ? If a nonland permanent left the battl
_h_decode_transmissions = _spell([["draw", {"n": 2}], ["draw", {"n": 2}], ["lose_life", {"n": 2, "target": "opp"}]])
# [eoe] This spell costs {1} less to cast during your turn. | Tap target artifact or creat
_h_mental_modulation = _spell([["draw", {"n": 1}]])
# [eoe] Invasive Maneuvers deals 3 damage to target creature. It deals 5 damage instead 
_h_invasive_maneuvers = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [eoe] Orbital Plunge deals 6 damage to target creature. If excess damage was dealt thi
_h_orbital_plunge = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [eoe] Target creature you control gets +1/+0 and gains vigilance until end of turn. It
_h_diplomatic_relations = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [eoe] You gain 2 life. Create a Lander token. (It's an artifact with "{2}, {T}, Sacrif
_h_sami_s_curiosity = _spell([["gain_life", {"n": 2}]])
# [eoe] Destroy target artifact, enchantment, or creature with flying. Surveil 1. (Look 
_h_shattered_wings = _spell([["scry", {"n": 1}], ["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_vote_out = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [eoe] Target creature you control gains double strike until end of turn. If it has a +
_h_dual_sun_technique = _spell([["draw", {"n": 1}]])
# [eoe] Choose odd or even. Destroy each creature with mana value of the chosen quality.
_h_mutinous_massacre = _spell([["scry", {"n": 0}]])
# [eoe] Surveil 1, then you draw a card and lose 1 life. (To surveil 1, look at the top 
_h_hymn_of_the_faller = _spell([["draw", {"n": 1}], ["scry", {"n": 1}], ["draw", {"n": 1}]])
# [eoe] Bombard deals 4 damage to target creature.
_h_bombard = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}]])
# [eoe] You may put an artifact or creature card from your hand onto the battlefield. Th
_h_terminal_velocity = _spell([["scry", {"n": 0}]])
# [eoe] Target artifact or creature's owner puts it on their choice of the top or bottom
_h_lost_in_space = _spell([["scry", {"n": 1}]])
# [eoe] Choose one or both ? | ? Search your library for an artifact card, reveal it, put 
_h_scour_for_scrap = _spell([["draw", {"n": 1}], ["return_gy_to_hand", {"filter_type": "any"}]])
# [eoe] This spell costs {1} less to cast if it targets a blocking creature. | Target crea
_h_dark_endurance = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [eoe] Surveil X, where X is the number of artifacts you control. Then draw three cards
_h_cerebral_download = _spell([["draw", {"n": 3}], ["scry", {"n": 1}]])
# [spm] Choose one or both ? | ? Counter target spell. | ? Tap one or two target creatures.
_h_amazing_acrobatics = _spell([["scry", {"n": 0}]])
# [spm] Put target creature on the bottom of its owner's library. You lose 2 life unless
_h_the_spot_s_portal = _spell([["lose_life", {"n": 2, "target": "self"}]])
# [spm] This spell costs {2} less to cast if you control a permanent with mana value 4 o
_h_terrific_team_up = _spell([["add_counters", {"n": 1, "target": "all_friendly"}], ["add_counters", {"n": 1, "target": "self"}]])
# [spm] Surveil 2, then draw two cards. You lose 2 life. (To surveil 2, look at the top 
_h_risky_research = _spell([["draw", {"n": 2}], ["scry", {"n": 2}], ["lose_life", {"n": 2, "target": "self"}]])
# [spm] This spell costs {1} less to cast if it targets a Spider. | Target creature gets +
_h_grow_extra_arms = _spell([["add_counters", {"n": 4, "target": "self"}]])
# [spm] Target creature gets -3/-3 until end of turn.
_h_scorpion_s_sting = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
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
# [spm] Target creature deals damage equal to its power to itself. If that creature is a
_h_wisecrack = _spell([["damage_any", {"n": 2}]])
# [spm] Choose one ? | ? Look Around ? Mill three cards. You may put a permanent card from
_h_scout_the_city = _spell([["mill", {"n": 3, "target": "self"}], ["gain_life", {"n": 3}], ["destroy", {"target": "opp_biggest_creature"}]])
# [spm] Target creature gets +2/+2 and gains flying until end of turn. If it's a Spider,
_h_thwip_ = _spell([["gain_life", {"n": 2}], ["add_counters", {"n": 2, "target": "self"}]])
# [tla] Choose one ? | ? Create a token that's a copy of target creature you control, exce
_h_ember_island_production = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tla] As an additional cost to cast this spell, waterbend {X}. (While paying a waterbe
_h_foggy_swamp_visions = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [tla] Choose target creature. When that creature dies this turn, you earthbend 4. (Tar
_h_fatal_fissure = _spell([["add_mana", {"n": 4}]])
# [tla] Target creature gains menace until end of turn. (It can't be blocked except by t
_h_how_to_start_a_riot = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [tla] Exile cards from the top of your library until you exile a nonland card. You may
_h_solstice_revelations = _spell([["draw", {"n": 1}]])
# [tla] Create two 2/2 red Soldier creature tokens with firebending 1. (Whenever a creat
_h_fire_nation_attacks = _spell([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": ["firebending 1"]}], ["damage_any", {"n": 1}]])
# [tla] The owner of target creature or enchantment puts it into their library second fr
_h_lost_days = _spell([["draw", {"n": 1}]])
# [tla] Draw three cards. Then discard a card unless you waterbend {2}. (While paying a 
_h_waterbending_lesson = _spell([["draw", {"n": 3}]])
# [tla] Target creature you control gets +2/+2 until end of turn. If that creature is an
_h_yip_yip_ = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [tla] Choose one ? | ? Target opponent reveals their hand. You choose a nonland permanen
_h_dai_li_indoctrination = _spell([["add_mana", {"n": 2}]])
# [tla] Kicker {3} (You may pay an additional {3} as you cast this spell.) | Target creatu
_h_jet_s_brainwashing = _spell([["scry", {"n": 0}], ["draw", {"n": 1}]])
# [tla] Exile target artifact, creature, or enchantment. Its controller creates a Clue t
_h_zuko_s_exile = _spell([["draw", {"n": 1}], ["exile", {"target": "opp_biggest_creature"}]])
# [tla] Earthbend 4. (Target land you control becomes a 0/0 creature with haste that's s
_h_earthbending_lesson = _spell([["add_mana", {"n": 4}]])
# [tla] As an additional cost to cast this spell, you may waterbend {6}. (While paying a
_h_spirit_water_revival = _spell([["draw", {"n": 2}]])
# [tla] Exile target creature. If it was dealt damage this turn, create a Clue token. (I
_h_sold_out = _spell([["exile", {"target": "opp_biggest_creature"}], ["draw", {"n": 1}]])
# [tla] Sacrifice a land. Search your library for up to two basic land cards, put them o
_h_cycle_of_renewal = _spell([["search_basic_land", {"n": 2}]])
# [tla] As an additional cost to cast this spell, you may waterbend {4}. (While paying a
_h_ruinous_waterbending = _spell([["gain_life", {"n": 1}], ["damage_creature", {"n": 2, "target": "opp_biggest"}], ["damage_creature", {"n": 2, "target": "each_opp"}]])
# [tla] Counter target spell. | Draw a card, then mill three cards. | Untap target land.
_h_sokka_s_haiku = _spell([["scry", {"n": 0}], ["draw", {"n": 1}], ["mill", {"n": 3, "target": "self"}]])
# [tla] Target creature gets +3/+1 until end of turn. | Create a Clue token. (It's an arti
_h_cunning_maneuver = _spell([["add_counters", {"n": 3, "target": "self"}], ["draw", {"n": 1}]])
# [tla] Look at the top X cards of your library, where X is the number of lands you cont
_h_seismic_sense = _spell([["scry", {"n": 1}]])
# [tla] Target creature gets +2/+2 and gains reach until end of turn. Untap it.
_h_pillar_launch = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [tla] Ozai's Cruelty deals 2 damage to target player. That player discards two cards.
_h_ozai_s_cruelty = _spell([["damage_player", {"n": 2, "target": "opp"}]])
# [tla] Each creature you control gains firebending 5 until end of turn. (Whenever it at
_h_sozin_s_comet = _spell([["damage_any", {"n": 5}]])
# [tla] Affinity for Allies (This spell costs {1} less to cast for each Ally you control
_h_allies_at_last = _spell([["damage_any", {"n": 2}]])
# [tla] Create X 1/1 white Ally creature tokens, then put a +1/+1 counter on each creatu
_h_united_front = _spell([["add_counters", {"n": 1, "target": "self"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [tla] Lands you control gain all basic land types until end of turn. | Draw a card.
_h_energybending = _spell([["draw", {"n": 1}]])
# [tla] Untap one or two target creatures. They each get +2/+2 until end of turn.
_h_fancy_footwork = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [tla] As an additional cost to cast this spell, waterbend {X}. (While paying a waterbe
_h_crashing_wave = _spell([["scry", {"n": 0}]])
# [tla] Earthbend X, where X is the number of Forests you control. (Target land you cont
_h_rockalanche = _spell([["add_mana", {"n": 1}]])
# [tla] As an additional cost to cast this spell, pay {4} or sacrifice an artifact or cr
_h_deadly_precision = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [tla] Create a 1/1 white Ally creature token for each Plains you control. Scry 2. (Loo
_h_gather_the_white_lotus = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["scry", {"n": 2}]])
# [tla] Kicker {2} (You may pay an additional {2} as you cast this spell.) | Search your l
_h_aang_s_journey = _spell([["search_basic_land", {"n": 1}], ["gain_life", {"n": 2}]])
# [tla] Choose one ? | ? Destroy target creature with power 4 or greater. | ? Earthbend 3. (
_h_sandbenders__storm = _spell([["destroy", {"target": "opp_biggest_creature"}], ["add_mana", {"n": 3}]])
# [tla] Airbend target nonland permanent. (Exile it. While it's exiled, its owner may ca
_h_airbending_lesson = _spell([["draw", {"n": 1}]])
# [tla] Razor Rings deals 4 damage to target attacking or blocking creature. You gain li
_h_razor_rings = _spell([["gain_life", {"n": 2}]])
# [tla] Exile target creature with mana value 3 or greater.
_h_epic_downfall = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [tla] Kicker {4} (You may pay an additional {4} as you cast this spell.) | Return target
_h_zuko_s_conviction = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [tla] Earthbend 2. When you do, up to one target creature you control fights target cr
_h_earth_rumble = _spell([["add_mana", {"n": 2}]])
# [tla] Choose one or both ? | ? Target creature gets -1/-1 until end of turn. | ? Put a +1/
_h_azula_always_lies = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}], ["add_counters", {"n": 1, "target": "self"}]])
# [tla] Target creature you control fights target creature an opponent controls. If the 
_h_the_last_agni_kai = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [tla] Target creature you control deals damage equal to its power to target creature a
_h_rocky_rebuke = _spell([["damage_any", {"n": 2}]])
# [ecl] End-Blaze Epiphany deals X damage to target creature. When that creature dies th
_h_end_blaze_epiphany = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [ecl] Draw three cards. Then discard two cards unless you discard a creature card.
_h_thirst_for_identity = _spell([["draw", {"n": 3}]])
# [ecl] Choose exactly two creatures you control. You draw X cards and the chosen creatu
_h_spry_and_mighty = _spell([["draw", {"n": 1}]])
# [ecl] Gain control of target creature until end of turn. Untap that creature. It gains
_h_goatnap = _spell([["scry", {"n": 0}], ["add_counters", {"n": 3, "target": "self"}]])
# [ecl] Target creature gets +2/+2 and gains first strike until end of turn. Untap it.
_h_riverguard_s_reflexes = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [ecl] As an additional cost to cast this spell, blight 1 or pay {3}. (To blight 1, put
_h_bogslither_s_embrace = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [ecl] Changeling (This card is every creature type.) | Exile target creature. Its contro
_h_crib_swap = _spell([["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["changeling"]}]])
# [ecl] As an additional cost to cast this spell, blight X. X can't be greater than the 
_h_soul_immolation = _spell([["damage_player", {"n": 1, "target": "opp"}]])
# [ecl] Choose one ? | ? Target opponent reveals their hand. You choose a nonland permanen
_h_auntie_s_sentence = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [ecl] As an additional cost to cast this spell, you may blight 1. (You may put a -1/-1
_h_cinder_strike = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [ecl] Target creature you control gets +2/+2 and gains hexproof until end of turn. (It
_h_blossoming_defense = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [ecl] Choose two ? | ? Create a token that's a copy of target Kithkin you control. | ? Tar
_h_brigid_s_command = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["add_counters", {"n": 3, "target": "self"}], ["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [ecl] Target creature you control gains deathtouch and lifelink until end of turn. Whe
_h_scarblade_s_malice = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [ecl] Choose one ? | ? Target creature you control deals damage equal to its power to ta
_h_giantfall = _spell([["damage_any", {"n": 2}], ["destroy", {"target": "opp_biggest_creature"}]])
# [ecl] Mill four cards, then you may return a permanent card from among them to your ha
_h_midnight_tilling = _spell([["mill", {"n": 4, "target": "self"}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_wanderwine_farewell = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}]])
# [ecl] As an additional cost to cast this spell, you may blight 1. (You may put a -1/-1
_h_burning_curiosity = _spell([["mill", {"n": 2, "target": "self"}]])
# [ecl] Choose two ? | ? Create a token that's a copy of target Goblin you control. | ? Crea
_h_grub_s_command = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["scry", {"n": 0}], ["destroy", {"target": "opp_biggest_creature"}], ["mill", {"n": 5, "target": "self"}]])
# [ecl] Search your library for a basic land card, put it onto the battlefield tapped, t
_h_tend_the_sprigs = _spell([["create_token", {"count": 1, "power": "3", "toughness": "4", "keywords": ["reach"]}], ["search_basic_land", {"n": 1}]])
# [ecl] Tweeze deals 3 damage to any target. You may discard a card. If you do, draw a c
_h_tweeze = _spell([["damage_any", {"n": 3}], ["draw", {"n": 1}]])
# [ecl] Target creature gets +3/+3 until end of turn. If a creature entered the battlefi
_h_thoughtweft_charge = _spell([["draw", {"n": 1}], ["add_counters", {"n": 3, "target": "self"}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_harmonized_crescendo = _spell([["draw", {"n": 1}]])
# [ecl] Vivid ? This spell costs {1} less to cast for each color among permanents you co
_h_rime_chill = _spell([["scry", {"n": 0}], ["draw", {"n": 1}]])
# [ecl] Choose one ? | ? Destroy target creature with flying. | ? Destroy target enchantment
_h_unforgiving_aim = _spell([["destroy", {"target": "opp_biggest_creature"}], ["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_unexpected_assistance = _spell([["draw", {"n": 3}]])
# [ecl] Create a token that's a copy of target creature you control, except it has haste
_h_kindle_the_inner_flame = _spell([["scry", {"n": 0}], ["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [ecl] Convoke (Your creatures can help cast this spell. Each creature you tap while ca
_h_appeal_to_eirdu = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [ecl] As an additional cost to cast this spell, blight 2 or pay {1}. (To blight 2, put
_h_wild_unraveling = _spell([["scry", {"n": 0}]])
# [ecl] Exile target creature you control, then return that card to the battlefield unde
_h_personify = _spell([["exile", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["changeling"]}]])
# [ecl] Choose one ? | ? Return target creature card from your graveyard to your hand. | ? R
_h_unbury = _spell([["return_gy_to_hand", {"filter_type": "creature"}]])
# [ecl] Target creature gets +3/+2 until end of turn. Create a Treasure token. (It's an 
_h_reckless_ransacking = _spell([["create_treasure", {"n": 1}], ["add_counters", {"n": 3, "target": "self"}]])
# [ecl] Choose two ? | ? Create a token that's a copy of target Elf you control. | ? Return 
_h_trystan_s_command = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}], ["destroy", {"target": "opp_biggest_creature"}], ["add_counters", {"n": 3, "target": "self"}]])
# [ecl] Target creature you control gets +1/+0 until end of turn. It deals damage equal 
_h_assert_perfection = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [ecl] Feed the Flames deals 5 damage to target creature. If that creature would die th
_h_feed_the_flames = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [ecl] Return target creature card from your graveyard to the battlefield. Then if it i
_h_dose_of_dawnglow = _spell([["return_gy_to_bf", {"filter_type": "creature"}]])
# [tmt] Until end of turn, target artifact or creature becomes an artifact creature with
_h_mind_transfer_protocol = _spell([["draw", {"n": 1}]])
# [tmt] Kicker?Sacrifice an artifact or creature. (You may sacrifice an artifact or crea
_h_stomped_by_the_foot = _spell([["scry", {"n": 0}], ["damage_creature", {"n": 2, "target": "opp_biggest"}]])
# [tmt] Bot Bashing Time deals 6 damage to target creature. If that creature would die t
_h_bot_bashing_time = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [tmt] Sneak {1}{B} (You may cast this spell for {1}{B} if you also return an unblocked
_h_splinter_s_technique = _spell([["draw", {"n": 1}]])
# [tmt] Choose one ? | ? Target player discards two cards. | ? Target player draws two cards
_h_shredder_s_revenge = _spell([["draw", {"n": 2}]])
# [tmt] Destroy target artifact or creature. If its mana value was 4 or less, create a F
_h_tainted_treats = _spell([["gain_life", {"n": 3}], ["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] Sneak {1}{W} (You may cast this spell for {1}{W} if you also return an unblocked
_h_the_last_ronin_s_technique = _spell([["create_token", {"count": 2, "power": "1", "toughness": "1", "keywords": []}]])
# [tmt] Return all creatures to their owners' hands. Each player may shuffle their hand 
_h_turtles_in_time = _spell([["draw", {"n": 7}]])
# [tmt] Sneak {R} (You may cast this spell for {R} if you also return an unblocked attac
_h_jennika_s_technique = _spell([["damage_creature", {"n": 2, "target": "each_opp"}]])
# [tmt] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_grounded_for_life = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] Target creature you control deals damage equal to its power to target creature a
_h_tenderize = _spell([["damage_any", {"n": 2}]])
# [tmt] Look at the top four cards of your library. You may reveal a Mutant, Ninja, Turt
_h_cowabunga_ = _spell([["scry", {"n": 4}]])
# [tmt] Choose one or both ? | ? Brilliance Unleashed deals 5 damage to target creature. | ?
_h_brilliance_unleashed = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [tmt] Choose one ? | ? Create a 1/1 colorless Robot artifact creature token. | ? Target cr
_h_mouser_attack_ = _spell([["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": []}], ["scry", {"n": 0}], ["add_counters", {"n": 3, "target": "self"}]])
# [tmt] Counter target spell. Create a Mutagen token. (It's an artifact with "{1}, {T}, 
_h_ooze_spill = _spell([["scry", {"n": 0}]])
# [tmt] Manhole Missile deals 3 damage to target creature. You may put a card from your 
_h_manhole_missile = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [tmt] Target creature gets +1/+3 and gains flying until end of turn. Scry 1. (Look at 
_h_hamato_guardian_stance = _spell([["scry", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [tmt] Gain control of all artifacts your opponents control until end of turn. Untap th
_h_broadcast_takeover = _spell([["scry", {"n": 0}]])
# [tmt] Sneak {W}{B} (You may cast this spell for {W}{B} if you also return an unblocked
_h_karai_s_technique = _spell([["add_counters", {"n": 3, "target": "self"}], ["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [tmt] Sneak {2}{G} (You may cast this spell for {2}{G} if you also return an unblocked
_h_new_generation_s_technique = _spell([["search_basic_land", {"n": 2}]])
# [tmt] Destroy up to one target artifact, enchantment, or creature with flying. Create 
_h_mutant_chain_reaction = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [tmt] Sneak {2}{R} (You may cast this spell for {2}{R} if you also return an unblocked
_h_raphael_s_technique = _spell([["draw", {"n": 7}]])
# [tmt] Exile target creature with mana value 3 or less.
_h_death_in_the_family = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] Target creature you control gets +1/+1 until end of turn. You draw a card and ga
_h_oracle_s_restoration = _spell([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] Destroy target creature with power 3 or greater.
_h_stand_up_for_yourself = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Exile target creature you control, then return that card to the battlefield unde
_h_daydream = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] Choose one ? | ? Artistic Process deals 6 damage to target creature. | ? Artistic Pr
_h_artistic_process = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}], ["damage_creature", {"n": 2, "target": "each_opp"}], ["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": ["flying"]}]])
# [sos] Choose one ? | ? Discard your hand, then draw cards equal to the number of cards i
_h_borrowed_knowledge = _spell([["draw", {"n": 4}], ["draw", {"n": 4}]])
# [sos] Destroy target creature. Its controller creates a 1/1 white and black Inkling cr
_h_harsh_annotation = _spell([["destroy", {"target": "opp_biggest_creature"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["flying"]}]])
# [sos] Put two +1/+1 counters on target creature. | Infusion ? If you gained life this tu
_h_efflorescence = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Target creature you control gets +1/+0 and gains indestructible until end of tur
_h_masterful_flourish = _spell([["scry", {"n": 0}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] Put a +1/+1 counter on target creature you control, then double the number of +1
_h_growth_curve = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Converge ? Target player draws X cards, Together as One deals X damage to any ta
_h_together_as_one = _spell([["damage_any", {"n": 1}], ["draw", {"n": 1}], ["gain_life", {"n": 1}]])
# [sos] Choose one ? | ? Draw four cards. | ? Splatter Technique deals 4 damage to each crea
_h_splatter_technique = _spell([["draw", {"n": 4}], ["damage_creature", {"n": 4, "target": "each_opp"}]])
# [sos] Duel Tactics deals 1 damage to target creature. It can't block this turn. | Flashb
_h_duel_tactics = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [sos] Create a 0/0 green and blue Fractal creature token. Put X +1/+1 counters on it. | 
_h_wild_hypothesis = _spell([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}], ["scry", {"n": 2}]])
# [sos] Heated Argument deals 6 damage to target creature. You may exile a card from you
_h_heated_argument = _spell([["damage_creature", {"n": 6, "target": "opp_biggest"}]])
# [sos] Counter target spell. If you control a Wizard, add an amount of {C} equal to the
_h_mana_sculpt = _spell([["scry", {"n": 0}]])
# [sos] Converge ? Create two 0/0 green and blue Fractal creature tokens. Put X +1/+1 co
_h_snarl_song = _spell([["gain_life", {"n": 1}], ["create_token", {"count": 2, "power": "0", "toughness": "0", "keywords": []}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [sos] This spell costs {2} less to cast if one or more cards left your graveyard this 
_h_wilt_in_the_heat = _spell([["damage_creature", {"n": 5, "target": "opp_biggest"}]])
# [sos] You gain 2 life. You may discard a card. If you do, draw two cards. | Flashback {2
_h_pursue_the_past = _spell([["draw", {"n": 2}], ["gain_life", {"n": 2}]])
# [sos] Target creature gets +2/+2 and gains first strike until end of turn.
_h_interjection = _spell([["scry", {"n": 0}], ["add_counters", {"n": 2, "target": "self"}]])
# [sos] Until end of turn, any number of target creatures you control each get +1/+0 and
_h_rabid_attack = _spell([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [sos] Stress Dream deals 5 damage to up to one target creature. Look at the top two ca
_h_stress_dream = _spell([["scry", {"n": 2}]])
# [sos] Converge ? Archaic's Agony deals X damage to target creature, where X is the num
_h_archaic_s_agony = _spell([["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [sos] As an additional cost to cast this spell, discard a card. | Draw two cards and cre
_h_seize_the_spoils = _spell([["draw", {"n": 2}], ["create_treasure", {"n": 1}]])
# [sos] Target player draws 2? cards. (2? = 1, 2? = 2, 2? = 4, 2? = 8, 2? = 16, 2? = 32,
_h_mathemagics = _spell([["draw", {"n": 1}]])
# [sos] Look at the top five cards of your library. You may reveal up to two creature an
_h_zimone_s_experiment = _spell([["scry", {"n": 5}]])
# [sos] This spell can't be copied. | Choose one or both ? | ? Copy target instant or sorcer
_h_choreographed_sparks = _spell([["draw", {"n": 1}], ["scry", {"n": 0}]])
# [sos] Create a 3/3 blue and red Elemental creature token with flying. | Surveil 2. (Look
_h_muse_s_encouragement = _spell([["create_token", {"count": 1, "power": "3", "toughness": "3", "keywords": ["flying"]}], ["scry", {"n": 2}]])
# [sos] Create a 0/0 green and blue Fractal creature token and put X +1/+1 counters on i
_h_fractal_anomaly = _spell([["create_token", {"count": 1, "power": "0", "toughness": "0", "keywords": []}]])
# [sos] Return target nonland permanent to its owner's hand. Surveil 1. (Look at the top
_h_banishing_betrayal = _spell([["bounce_to_hand", {}], ["scry", {"n": 1}]])
# [sos] Target opponent loses 1 life and you gain 1 life. | Up to one target creature gets
_h_dissection_practice = _spell([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}], ["add_counters", {"n": 1, "target": "self"}], ["damage_creature", {"n": 1, "target": "opp_biggest"}]])
# [sos] This spell costs {1}{U} less to cast if it targets an instant or sorcery spell. | 
_h_brush_off = _spell([["scry", {"n": 0}]])
# [sos] Exile target nonland permanent and the top card of your library. For each of tho
_h_suspend_aggression = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] Create a token that's a copy of target non-Aura permanent you control, except it
_h_applied_geometry = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] Target creature you control gets +0/+10 until end of turn. Then it fights up to 
_h_chelonian_tackle = _spell([["add_counters", {"n": 0, "target": "self"}]])
# [sos] Choose up to four. You may choose the same mode more than once. | ? Destroy target
_h_moment_of_reckoning = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] As an additional cost to cast this spell, pay X life. | Destroy all artifacts and 
_h_vicious_rivalry = _spell([["destroy_all_creatures", {}]])
# [sos] Each opponent discards a card. You create a 1/1 black and green Pest creature to
_h_send_in_the_pest = _spell([["gain_life", {"n": 1}], ["discard", {"n": 1, "target": "opp"}], ["create_token", {"count": 1, "power": "1", "toughness": "1", "keywords": ["\"Whenever this token attacks", "you gain 1 life"]}]])
# [sos] Put a +1/+1 counter on target creature you control. It gains vigilance until end
_h_dig_site_inventory = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Put a +1/+1 counter on each creature target player controls. Target creature gai
_h_practiced_offense = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Target creature you control gets +0/+3 and gains hexproof until end of turn. (It
_h_chase_inspiration = _spell([["scry", {"n": 0}], ["add_counters", {"n": 0, "target": "self"}]])
# [sos] Create two 2/2 red and white Spirit creature tokens. Then if this spell was cast
_h_antiquities_on_the_loose = _spell([["create_token", {"count": 2, "power": "2", "toughness": "2", "keywords": []}], ["add_counters", {"n": 1, "target": "friendly_biggest"}], ["add_counters", {"n": 1, "target": "all_friendly"}]])
# [sos] Destroy target creature. | Infusion ? If you gained life this turn, that creature'
_h_foolish_fate = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Unsubtle Mockery deals 4 damage to target creature. Surveil 1. (Look at the top 
_h_unsubtle_mockery = _spell([["damage_creature", {"n": 4, "target": "opp_biggest"}], ["scry", {"n": 1}]])
# [sos] Choose one ? | ? Each opponent sacrifices a nontoken artifact of their choice. | ? R
_h_lorehold_charm = _spell([["add_counters", {"n": 1, "target": "all_friendly"}]])
# [sos] Return up to one target nonland permanent to its owner's hand. Search your libra
_h_proctor_s_gaze = _spell([["search_basic_land", {"n": 1}]])
# [sos] Target creature gets -3/-3 until end of turn.
_h_last_gasp = _spell([["damage_creature", {"n": 3, "target": "opp_biggest"}]])
# [sos] Search your library for a creature card, reveal it, put it into your hand or gra
_h_dina_s_guidance = _spell([["draw", {"n": 1}]])
# [sos] Choose one ? | ? Destroy target artifact. | ? Glorious Decay deals 4 damage to targe
_h_glorious_decay = _spell([["destroy", {"target": "opp_biggest_creature"}], ["damage_creature", {"n": 4, "target": "opp_biggest"}], ["draw", {"n": 1}]])
# [sos] Exile target creature.
_h_wander_off = _spell([["exile", {"target": "opp_biggest_creature"}]])
# [sos] When you cast this spell while you control a creature, you may copy this spell. | 
_h_social_snub = _spell([["gain_life", {"n": 1}], ["lose_life", {"n": 1, "target": "opp"}]])
# [sos] Target player draws two cards and loses 2 life. Put a +1/+1 counter on up to one
_h_cost_of_brilliance = _spell([["draw", {"n": 2}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] Draw three cards. You may put a land card from your hand onto the battlefield ta
_h_embrace_the_paradox = _spell([["draw", {"n": 3}]])
# [sos] This spell costs {3} less to cast if it targets a tapped creature. | Destroy targe
_h_ajani_s_response = _spell([["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Target creature gets +1/+1 until end of turn. Draw a card. | Whenever one or more 
_h_killian_s_confidence = _spell([["draw", {"n": 1}], ["add_counters", {"n": 1, "target": "self"}]])
# [sos] Target creature you control gets +1/+0 until end of turn if you've cast another 
_h_burrog_barrage = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Return up to two target creature cards from your graveyard to your hand. You gai
_h_pull_from_the_grave = _spell([["gain_life", {"n": 2}], ["return_gy_to_hand", {"filter_type": "creature"}]])
# [sos] Put two +1/+1 counters on each creature you control. | Paradigm (Then exile this s
_h_germination_practicum = _spell([["add_counters", {"n": 1, "target": "self"}]])
# [sos] Draw three cards, then discard two cards. Add {U}{U}{R}{R}{R}.
_h_rapturous_moment = _spell([["draw", {"n": 3}]])
# [sos] Create two 3/3 blue and red Elemental creature tokens with flying. | {2}, Discard 
_h_visionary_s_dance = _spell([["create_token", {"count": 2, "power": "3", "toughness": "3", "keywords": ["flying"]}], ["scry", {"n": 2}]])
# [sos] Tap target creature. If it's your turn, put a stun counter on it. (If a permanen
_h_rapier_wit = _spell([["draw", {"n": 1}]])
# [sos] Infusion ? When you cast this spell, copy it if you gained life this turn. You m
_h_lumaret_s_favor = _spell([["add_counters", {"n": 2, "target": "self"}]])
# [sos] Until end of turn, creatures you control get +2/+2 and gain menace and "Whenever
_h_root_manipulation = _spell([["gain_life", {"n": 1}], ["add_counters", {"n": 2, "target": "all_friendly"}]])
# [sos] Target player creates a token that's a copy of target creature you control. | Para
_h_echocasting_symposium = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] Choose one ? | ? Put two +1/+1 counters on target creature. | ? Exile target creatur
_h_silverquill_charm = _spell([["add_counters", {"n": 1, "target": "self"}], ["exile", {"target": "opp_biggest_creature"}], ["gain_life", {"n": 3}], ["lose_life", {"n": 3, "target": "opp"}]])
# [sos] Destroy target artifact or creature. You gain 1 life.
_h_grapple_with_death = _spell([["gain_life", {"n": 1}], ["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Target creature gains trample and gets +X/+0 until end of turn, where X is 1 plu
_h_ancestral_anger = _spell([["draw", {"n": 1}]])
# [sos] Create a 2/2 red and white Spirit creature token. | Flashback?Tap three untapped c
_h_group_project = _spell([["create_token", {"count": 1, "power": "2", "toughness": "2", "keywords": []}]])
# [sos] Target player draws two cards. Tap up to two target creatures. Put a stun counte
_h_homesickness = _spell([["draw", {"n": 2}]])
# [sos] Tome Blast deals 2 damage to any target. | Flashback {4}{R} (You may cast this car
_h_tome_blast = _spell([["damage_any", {"n": 2}]])
# [sos] Choose one ? | ? Counter target spell unless its controller pays {2}. | ? Destroy ta
_h_quandrix_charm = _spell([["scry", {"n": 0}], ["destroy", {"target": "opp_biggest_creature"}]])
# [sos] Exile cards from the top of your library until you exile cards with total mana v
_h_improvisation_capstone = _spell([["draw", {"n": 1}]])
# [sos] All creatures get -2/-2 until end of turn. | Infusion ? If you gained life this tu
_h_withering_curse = _spell([["damage_creature", {"n": 2, "target": "opp_biggest"}], ["damage_creature", {"n": 2, "target": "each_opp"}]])

for _n,_f in {
    "Greta, Sweettooth Scourge": _h_greta__sweettooth_scourge,
    "Merfolk Coralsmith": _h_merfolk_coralsmith,
    "Boundary Lands Ranger": _h_boundary_lands_ranger,
    "Prophetic Prism": _h_prophetic_prism,
    "Troublemaker Ouphe": _h_troublemaker_ouphe,
    "Stockpiling Celebrant": _h_stockpiling_celebrant,
    "Cursed Courtier": _h_cursed_courtier,
    "Unassuming Sage": _h_unassuming_sage,
    "Splashy Spellcaster": _h_splashy_spellcaster,
    "Skybeast Tracker": _h_skybeast_tracker,
    "Provisions Merchant": _h_provisions_merchant,
    "Hopeful Vigil": _h_hopeful_vigil,
    "Tangled Colony": _h_tangled_colony,
    "Obyra, Dreaming Duelist": _h_obyra__dreaming_duelist,
    "Night of the Sweets' Revenge": _h_night_of_the_sweets__revenge,
    "Ogre Chitterlord": _h_ogre_chitterlord,
    "Syr Armont, the Redeemer": _h_syr_armont__the_redeemer,
    "Sweettooth Witch": _h_sweettooth_witch,
    "Merry Bards": _h_merry_bards,
    "Discerning Financier": _h_discerning_financier,
    "Stingblade Assassin": _h_stingblade_assassin,
    "Experimental Confectioner": _h_experimental_confectioner,
    "Slumbering Keepguard": _h_slumbering_keepguard,
    "Voracious Vermin": _h_voracious_vermin,
    "High Fae Negotiator": _h_high_fae_negotiator,
    "Territorial Witchstalker": _h_territorial_witchstalker,
    "Twisted Sewer-Witch": _h_twisted_sewer_witch,
    "Hamlet Glutton": _h_hamlet_glutton,
    "Food Coma": _h_food_coma,
    "Charmed Clothier": _h_charmed_clothier,
    "Tenacious Tomeseeker": _h_tenacious_tomeseeker,
    "Eriette's Tempting Apple": _h_eriette_s_tempting_apple,
    "Scream Puff": _h_scream_puff,
    "Faunsbane Troll": _h_faunsbane_troll,
    "Diminisher Witch": _h_diminisher_witch,
    "Charging Hooligan": _h_charging_hooligan,
    "Mintstrosity": _h_mintstrosity,
    "Archive Dragon": _h_archive_dragon,
    "Lord Skitter's Blessing": _h_lord_skitter_s_blessing,
    "Protective Parents": _h_protective_parents,
    "Stormkeld Prowler": _h_stormkeld_prowler,
    "Redcap Thief": _h_redcap_thief,
    "Rotisserie Elemental": _h_rotisserie_elemental,
    "Edgewall Pack": _h_edgewall_pack,
    "Wildwood Mentor": _h_wildwood_mentor,
    "Redtooth Genealogist": _h_redtooth_genealogist,
    "Old Flitterfang": _h_old_flitterfang,
    "River Herald Scout": _h_river_herald_scout,
    "Mephitic Draught": _h_mephitic_draught,
    "Malamet Brawler": _h_malamet_brawler,
    "Glorifier of Suffering": _h_glorifier_of_suffering,
    "Jadelight Spelunker": _h_jadelight_spelunker,
    "Deepfathom Echo": _h_deepfathom_echo,
    "Attentive Sunscribe": _h_attentive_sunscribe,
    "Resplendent Angel": _h_resplendent_angel,
    "Starving Revenant": _h_starving_revenant,
    "Plundering Pirate": _h_plundering_pirate,
    "Rampaging Spiketail": _h_rampaging_spiketail,
    "Captain Storm, Cosmium Raider": _h_captain_storm__cosmium_raider,
    "Dinotomaton": _h_dinotomaton,
    "Earthshaker Dreadmaw": _h_earthshaker_dreadmaw,
    "Akal Pakal, First Among Equals": _h_akal_pakal__first_among_equals,
    "Pathfinding Axejaw": _h_pathfinding_axejaw,
    "Runaway Boulder": _h_runaway_boulder,
    "Magmatic Galleon": _h_magmatic_galleon,
    "Soaring Sandwing": _h_soaring_sandwing,
    "Might of the Ancestors": _h_might_of_the_ancestors,
    "Scampering Surveyor": _h_scampering_surveyor,
    "Sage of Days": _h_sage_of_days,
    "Armored Kincaller": _h_armored_kincaller,
    "Deathcap Marionette": _h_deathcap_marionette,
    "Child of the Volcano": _h_child_of_the_volcano,
    "Primordial Gnawer": _h_primordial_gnawer,
    "Didact Echo": _h_didact_echo,
    "Disruptor Wanderglyph": _h_disruptor_wanderglyph,
    "Song of Stupefaction": _h_song_of_stupefaction,
    "Malamet War Scribe": _h_malamet_war_scribe,
    "Staunch Crewmate": _h_staunch_crewmate,
    "Oltec Cloud Guard": _h_oltec_cloud_guard,
    "Cavern Stomper": _h_cavern_stomper,
    "Enterprising Scallywag": _h_enterprising_scallywag,
    "Explorer's Cache": _h_explorer_s_cache,
    "Compass Gnome": _h_compass_gnome,
    "Kinjalli's Dawnrunner": _h_kinjalli_s_dawnrunner,
    "The Mycotyrant": _h_the_mycotyrant,
    "Deep Goblin Skulltaker": _h_deep_goblin_skulltaker,
    "River Herald Guide": _h_river_herald_guide,
    "Bat Colony": _h_bat_colony,
    "Careening Mine Cart": _h_careening_mine_cart,
    "Stalactite Stalker": _h_stalactite_stalker,
    "Tinker's Tote": _h_tinker_s_tote,
    "Palani's Hatcher": _h_palani_s_hatcher,
    "Digsite Conservator": _h_digsite_conservator,
    "Screaming Phantom": _h_screaming_phantom,
    "Nurturing Bristleback": _h_nurturing_bristleback,
    "Sinuous Benthisaur": _h_sinuous_benthisaur,
    "Canonized in Blood": _h_canonized_in_blood,
    "Greedy Freebooter": _h_greedy_freebooter,
    "Cogwork Wrestler": _h_cogwork_wrestler,
    "A-Geological Appraiser": _h_a_geological_appraiser,
    "Mineshaft Spider": _h_mineshaft_spider,
    "Ruin-Lurker Bat": _h_ruin_lurker_bat,
    "Zoyowa Lava-Tongue": _h_zoyowa_lava_tongue,
    "Miner's Guidewing": _h_miner_s_guidewing,
    "Volatile Wanderglyph": _h_volatile_wanderglyph,
    "Broodrage Mycoid": _h_broodrage_mycoid,
    "Synapse Necromage": _h_synapse_necromage,
    "Ironpaw Aspirant": _h_ironpaw_aspirant,
    "Nightdrinker Moroii": _h_nightdrinker_moroii,
    "Tolsimir, Midnight's Light": _h_tolsimir__midnight_s_light,
    "Inside Source": _h_inside_source,
    "Loxodon Eavesdropper": _h_loxodon_eavesdropper,
    "Vitu-Ghazi Inspector": _h_vitu_ghazi_inspector,
    "Essence of Antiquity": _h_essence_of_antiquity,
    "Hotshot Investigators": _h_hotshot_investigators,
    "Cold Case Cracker": _h_cold_case_cracker,
    "Granite Witness": _h_granite_witness,
    "Museum Nightwatch": _h_museum_nightwatch,
    "Undercover Crocodelf": _h_undercover_crocodelf,
    "Unyielding Gatekeeper": _h_unyielding_gatekeeper,
    "Person of Interest": _h_person_of_interest,
    "Cornered Crook": _h_cornered_crook,
    "Haazda Vigilante": _h_haazda_vigilante,
    "Coveted Falcon": _h_coveted_falcon,
    "Reckless Detective": _h_reckless_detective,
    "Benthic Criminologists": _h_benthic_criminologists,
    "Sample Collector": _h_sample_collector,
    "Alley Assailant": _h_alley_assailant,
    "Soul Enervation": _h_soul_enervation,
    "Shady Informant": _h_shady_informant,
    "Case of the Stashed Skeleton": _h_case_of_the_stashed_skeleton,
    "Exit Specialist": _h_exit_specialist,
    "A Killer Among Us": _h_a_killer_among_us,
    "Case of the Burning Masks": _h_case_of_the_burning_masks,
    "Forum Familiar": _h_forum_familiar,
    "Mistway Spy": _h_mistway_spy,
    "Case File Auditor": _h_case_file_auditor,
    "Tunnel Tipster": _h_tunnel_tipster,
    "Furtive Courier": _h_furtive_courier,
    "Undercity Eliminator": _h_undercity_eliminator,
    "Makeshift Binding": _h_makeshift_binding,
    "Incinerator of the Guilty": _h_incinerator_of_the_guilty,
    "Harried Dronesmith": _h_harried_dronesmith,
    "Blood Spatter Analysis": _h_blood_spatter_analysis,
    "Wojek Investigator": _h_wojek_investigator,
    "Gleaming Geardrake": _h_gleaming_geardrake,
    "Fugitive Codebreaker": _h_fugitive_codebreaker,
    "Persuasive Interrogators": _h_persuasive_interrogators,
    "Faerie Snoop": _h_faerie_snoop,
    "Polygraph Orb": _h_polygraph_orb,
    "Sanitation Automaton": _h_sanitation_automaton,
    "Hunted Bonebrute": _h_hunted_bonebrute,
    "Offender at Large": _h_offender_at_large,
    "Airtight Alibi": _h_airtight_alibi,
    "Sanguine Savior": _h_sanguine_savior,
    "Slimy Dualleech": _h_slimy_dualleech,
    "Case of the Shattered Pact": _h_case_of_the_shattered_pact,
    "Rakdos, Patron of Chaos": _h_rakdos__patron_of_chaos,
    "Greenbelt Radical": _h_greenbelt_radical,
    "Festerleech": _h_festerleech,
    "Fae Flight": _h_fae_flight,
    "Due Diligence": _h_due_diligence,
    "Teysa, Opulent Oligarch": _h_teysa__opulent_oligarch,
    "Vengeful Creeper": _h_vengeful_creeper,
    "Rakish Scoundrel": _h_rakish_scoundrel,
    "Gadget Technician": _h_gadget_technician,
    "Absolving Lammasu": _h_absolving_lammasu,
    "Alquist Proft, Master Sleuth": _h_alquist_proft__master_sleuth,
    "Basilica Stalker": _h_basilica_stalker,
    "Barbed Servitor": _h_barbed_servitor,
    "Detective's Satchel": _h_detective_s_satchel,
    "Glint Weaver": _h_glint_weaver,
    "Buried in the Garden": _h_buried_in_the_garden,
    "Unscrupulous Contractor": _h_unscrupulous_contractor,
    "Prosperity Tycoon": _h_prosperity_tycoon,
    "Ertha Jo, Frontier Mentor": _h_ertha_jo__frontier_mentor,
    "Servant of the Stinger": _h_servant_of_the_stinger,
    "Wrangler of the Damned": _h_wrangler_of_the_damned,
    "Loan Shark": _h_loan_shark,
    "Hellspur Posse Boss": _h_hellspur_posse_boss,
    "Beastbond Outcaster": _h_beastbond_outcaster,
    "Kraum, Violent Cacophony": _h_kraum__violent_cacophony,
    "Oasis Gardener": _h_oasis_gardener,
    "Drover Grizzly": _h_drover_grizzly,
    "Giant Beaver": _h_giant_beaver,
    "Sterling Hound": _h_sterling_hound,
    "Marchesa, Dealer of Death": _h_marchesa__dealer_of_death,
    "Frontier Seeker": _h_frontier_seeker,
    "Rambling Possum": _h_rambling_possum,
    "Stagecoach Security": _h_stagecoach_security,
    "Prickly Pair": _h_prickly_pair,
    "Ambush Gigapede": _h_ambush_gigapede,
    "Seraphic Steed": _h_seraphic_steed,
    "Scalestorm Summoner": _h_scalestorm_summoner,
    "Jem Lightfoote, Sky Explorer": _h_jem_lightfoote__sky_explorer,
    "Nezumi Linkbreaker": _h_nezumi_linkbreaker,
    "Mine Raider": _h_mine_raider,
    "Kambal, Profiteering Mayor": _h_kambal__profiteering_mayor,
    "Outlaw Medic": _h_outlaw_medic,
    "Quilled Charger": _h_quilled_charger,
    "Bridled Bighorn": _h_bridled_bighorn,
    "Rakdos Joins Up": _h_rakdos_joins_up,
    "Prairie Dog": _h_prairie_dog,
    "Marauding Sphinx": _h_marauding_sphinx,
    "Holy Cow": _h_holy_cow,
    "Malcolm, the Eyes": _h_malcolm__the_eyes,
    "Silver Deputy": _h_silver_deputy,
    "Vault Plunderer": _h_vault_plunderer,
    "Breeches, the Blastmaker": _h_breeches__the_blastmaker,
    "Outcaster Greenblade": _h_outcaster_greenblade,
    "Nimble Brigand": _h_nimble_brigand,
    "Gold Pan": _h_gold_pan,
    "Rictus Robber": _h_rictus_robber,
    "Lassoed by the Law": _h_lassoed_by_the_law,
    "Emergent Haunting": _h_emergent_haunting,
    "Outlaw Stitcher": _h_outlaw_stitcher,
    "Razzle-Dazzler": _h_razzle_dazzler,
    "Discerning Peddler": _h_discerning_peddler,
    "Vial Smasher, Gleeful Grenadier": _h_vial_smasher__gleeful_grenadier,
    "Sterling Supplier": _h_sterling_supplier,
    "Vadmir, New Blood": _h_vadmir__new_blood,
    "Bounding Felidar": _h_bounding_felidar,
    "Deepmuck Desperado": _h_deepmuck_desperado,
    "Freestrider Lookout": _h_freestrider_lookout,
    "Patient Naturalist": _h_patient_naturalist,
    "Blood Hustler": _h_blood_hustler,
    "Trained Arynx": _h_trained_arynx,
    "At Knifepoint": _h_at_knifepoint,
    "Wanted Griffin": _h_wanted_griffin,
    "Luxurious Locomotive": _h_luxurious_locomotive,
    "Lazav, Familiar Stranger": _h_lazav__familiar_stranger,
    "Spinewoods Paladin": _h_spinewoods_paladin,
    "Fortune, Loyal Steed": _h_fortune__loyal_steed,
    "Rakish Crew": _h_rakish_crew,
    "Desperate Bloodseeker": _h_desperate_bloodseeker,
    "Baron Bertram Graywater": _h_baron_bertram_graywater,
    "Iron-Fist Pulverizer": _h_iron_fist_pulverizer,
    "Brimstone Roundup": _h_brimstone_roundup,
    "Vraska, the Silencer": _h_vraska__the_silencer,
    "Raven of Fell Omens": _h_raven_of_fell_omens,
    "Spring Splasher": _h_spring_splasher,
    "Rooftop Assassin": _h_rooftop_assassin,
    "Ornery Tumblewagg": _h_ornery_tumblewagg,
    "Kaervek, the Punisher": _h_kaervek__the_punisher,
    "Mystical Tether": _h_mystical_tether,
    "Nexus of Becoming": _h_nexus_of_becoming,
    "Greed's Gambit": _h_greed_s_gambit,
    "Bristlebud Farmer": _h_bristlebud_farmer,
    "Loot, the Key to Everything": _h_loot__the_key_to_everything,
    "Generous Plunderer": _h_generous_plunderer,
    "Territory Forge": _h_territory_forge,
    "Pileated Provisioner": _h_pileated_provisioner,
    "Bark-Knuckle Boxer": _h_bark_knuckle_boxer,
    "Junkblade Bruiser": _h_junkblade_bruiser,
    "Starlit Soothsayer": _h_starlit_soothsayer,
    "Roughshod Duo": _h_roughshod_duo,
    "Splash Lasher": _h_splash_lasher,
    "Plumecreed Mentor": _h_plumecreed_mentor,
    "Starseer Mentor": _h_starseer_mentor,
    "Wick's Patrol": _h_wick_s_patrol,
    "Rottenmouth Viper": _h_rottenmouth_viper,
    "Thornplate Intimidator": _h_thornplate_intimidator,
    "Glidedive Duo": _h_glidedive_duo,
    "Agate-Blade Assassin": _h_agate_blade_assassin,
    "Hugs, Grisly Guardian": _h_hugs__grisly_guardian,
    "Daggerfang Duo": _h_daggerfang_duo,
    "Honored Dreyleader": _h_honored_dreyleader,
    "Head of the Homestead": _h_head_of_the_homestead,
    "Heartfire Hero": _h_heartfire_hero,
    "Bushy Bodyguard": _h_bushy_bodyguard,
    "Harvestrite Host": _h_harvestrite_host,
    "Star Charter": _h_star_charter,
    "Teapot Slinger": _h_teapot_slinger,
    "Treetop Sentries": _h_treetop_sentries,
    "Corpseberry Cultivator": _h_corpseberry_cultivator,
    "Thieving Otter": _h_thieving_otter,
    "Waterspout Warden": _h_waterspout_warden,
    "Tempest Angler": _h_tempest_angler,
    "Alania, Divergent Storm": _h_alania__divergent_storm,
    "Bumbleflower's Sharepot": _h_bumbleflower_s_sharepot,
    "Steampath Charger": _h_steampath_charger,
    "Finch Formation": _h_finch_formation,
    "Sunshower Druid": _h_sunshower_druid,
    "Intrepid Rabbit": _h_intrepid_rabbit,
    "Gossip's Talent": _h_gossip_s_talent,
    "Wandertale Mentor": _h_wandertale_mentor,
    "Blacksmith's Talent": _h_blacksmith_s_talent,
    "Reptilian Recruiter": _h_reptilian_recruiter,
    "Sinister Monolith": _h_sinister_monolith,
    "Scavenger's Talent": _h_scavenger_s_talent,
    "Brambleguard Veteran": _h_brambleguard_veteran,
    "Mistbreath Elder": _h_mistbreath_elder,
    "Feather of Flight": _h_feather_of_flight,
    "Moonrise Cleric": _h_moonrise_cleric,
    "Vinereap Mentor": _h_vinereap_mentor,
    "Seedpod Squire": _h_seedpod_squire,
    "Byrke, Long Ear of the Law": _h_byrke__long_ear_of_the_law,
    "Fountainport Bell": _h_fountainport_bell,
    "Bakersbane Duo": _h_bakersbane_duo,
    "Bellowing Crier": _h_bellowing_crier,
    "Hazardroot Herbalist": _h_hazardroot_herbalist,
    "Driftgloom Coyote": _h_driftgloom_coyote,
    "Mindwhisker": _h_mindwhisker,
    "Fear of Falling": _h_fear_of_falling,
    "Friendly Teddy": _h_friendly_teddy,
    "Flesh Burrower": _h_flesh_burrower,
    "Marina Vendrell's Grimoire": _h_marina_vendrell_s_grimoire,
    "Fear of Burning Alive": _h_fear_of_burning_alive,
    "Boilerbilges Ripper": _h_boilerbilges_ripper,
    "Innocuous Rat": _h_innocuous_rat,
    "Scrabbling Skullcrab": _h_scrabbling_skullcrab,
    "Trapped in the Screen": _h_trapped_in_the_screen,
    "Dashing Bloodsucker": _h_dashing_bloodsucker,
    "Erratic Apparition": _h_erratic_apparition,
    "Cautious Survivor": _h_cautious_survivor,
    "Hardened Escort": _h_hardened_escort,
    "Shroudstomper": _h_shroudstomper,
    "Fear of Lost Teeth": _h_fear_of_lost_teeth,
    "Razorkin Hordecaller": _h_razorkin_hordecaller,
    "Conductive Machete": _h_conductive_machete,
    "Fear of Surveillance": _h_fear_of_surveillance,
    "A-Kona, Rescue Beastie": _h_a_kona__rescue_beastie,
    "Winter, Misanthropic Guide": _h_winter__misanthropic_guide,
    "Threats Around Every Corner": _h_threats_around_every_corner,
    "Fear of Impostors": _h_fear_of_impostors,
    "Disturbing Mirth": _h_disturbing_mirth,
    "Tunnel Surveyor": _h_tunnel_surveyor,
    "Defiant Survivor": _h_defiant_survivor,
    "Wary Watchdog": _h_wary_watchdog,
    "Fanatic of the Harrowing": _h_fanatic_of_the_harrowing,
    "Cursed Windbreaker": _h_cursed_windbreaker,
    "Fear of Abduction": _h_fear_of_abduction,
    "Glimmerlight": _h_glimmerlight,
    "Victor, Valgavoth's Seneschal": _h_victor__valgavoth_s_seneschal,
    "Killer's Mask": _h_killer_s_mask,
    "Skullsnap Nuisance": _h_skullsnap_nuisance,
    "Cynical Loner": _h_cynical_loner,
    "Appendage Amalgam": _h_appendage_amalgam,
    "Piggy Bank": _h_piggy_bank,
    "Gremlin Tamer": _h_gremlin_tamer,
    "Balemurk Leech": _h_balemurk_leech,
    "Infernal Phantom": _h_infernal_phantom,
    "Growing Dread": _h_growing_dread,
    "Unsettling Twins": _h_unsettling_twins,
    "Miasma Demon": _h_miasma_demon,
    "Grasping Longneck": _h_grasping_longneck,
    "Lionheart Glimmer": _h_lionheart_glimmer,
    "Cult Healer": _h_cult_healer,
    "Entity Tracker": _h_entity_tracker,
    "Glimmer Seeker": _h_glimmer_seeker,
    "Living Phone": _h_living_phone,
    "Spineseeker Centipede": _h_spineseeker_centipede,
    "Rootwise Survivor": _h_rootwise_survivor,
    "Popular Egotist": _h_popular_egotist,
    "Friendly Ghost": _h_friendly_ghost,
    "Bashful Beastie": _h_bashful_beastie,
    "Shrewd Storyteller": _h_shrewd_storyteller,
    "Attack-in-the-Box": _h_attack_in_the_box,
    "Hedge Shredder": _h_hedge_shredder,
    "Most Valuable Slayer": _h_most_valuable_slayer,
    "Orphans of the Wheat": _h_orphans_of_the_wheat,
    "Fear of Immobility": _h_fear_of_immobility,
    "Venom Connoisseur": _h_venom_connoisseur,
    "Tatyova, Benthic Druid": _h_tatyova__benthic_druid,
    "High-Society Hunter": _h_high_society_hunter,
    "Rune-Scarred Demon": _h_rune_scarred_demon,
    "Crackling Cyclops": _h_crackling_cyclops,
    "Adventuring Gear": _h_adventuring_gear,
    "Good-Fortune Unicorn": _h_good_fortune_unicorn,
    "Gleaming Barrier": _h_gleaming_barrier,
    "Archmage of Runes": _h_archmage_of_runes,
    "Felidar Savior": _h_felidar_savior,
    "Burglar Rat": _h_burglar_rat,
    "Dragon Trainer": _h_dragon_trainer,
    "Vampire Gourmand": _h_vampire_gourmand,
    "Skeleton Archer": _h_skeleton_archer,
    "Battlesong Berserker": _h_battlesong_berserker,
    "Extravagant Replication": _h_extravagant_replication,
    "Dwynen's Elite": _h_dwynen_s_elite,
    "Ramos, Dragon Engine": _h_ramos__dragon_engine,
    "Garna, Bloodfist of Keld": _h_garna__bloodfist_of_keld,
    "Wary Thespian": _h_wary_thespian,
    "Prayer of Binding": _h_prayer_of_binding,
    "Vengeful Bloodwitch": _h_vengeful_bloodwitch,
    "Icewind Elemental": _h_icewind_elemental,
    "Rite of the Dragoncaller": _h_rite_of_the_dragoncaller,
    "Cat Collector": _h_cat_collector,
    "Arbiter of Woe": _h_arbiter_of_woe,
    "Vile Entomber": _h_vile_entomber,
    "Campus Guide": _h_campus_guide,
    "Ancestor Dragon": _h_ancestor_dragon,
    "Guarded Heir": _h_guarded_heir,
    "Gateway Sneak": _h_gateway_sneak,
    "Drogskol Reaver": _h_drogskol_reaver,
    "Stasis Snare": _h_stasis_snare,
    "Youthful Valkyrie": _h_youthful_valkyrie,
    "Spitfire Lagac": _h_spitfire_lagac,
    "Battle-Rattle Shaman": _h_battle_rattle_shaman,
    "Burrog Befuddler": _h_burrog_befuddler,
    "Kalastria Highborn": _h_kalastria_highborn,
    "Springbloom Druid": _h_springbloom_druid,
    "Dazzling Angel": _h_dazzling_angel,
    "Eager Trufflesnout": _h_eager_trufflesnout,
    "Marauding Blight-Priest": _h_marauding_blight_priest,
    "Terror of Mount Velus": _h_terror_of_mount_velus,
    "New Horizons": _h_new_horizons,
    "Cephalid Inkmage": _h_cephalid_inkmage,
    "Bloodtithe Collector": _h_bloodtithe_collector,
    "Ajani's Pridemate": _h_ajani_s_pridemate,
    "Dauntless Veteran": _h_dauntless_veteran,
    "Exemplar of Light": _h_exemplar_of_light,
    "Zimone, Paradox Sculptor": _h_zimone__paradox_sculptor,
    "Crow of Dark Tidings": _h_crow_of_dark_tidings,
    "Predator Ooze": _h_predator_ooze,
    "Corsair Captain": _h_corsair_captain,
    "Nessian Hornbeetle": _h_nessian_hornbeetle,
    "Redcap Gutter-Dweller": _h_redcap_gutter_dweller,
    "Elvish Regrower": _h_elvish_regrower,
    "Ovika, Enigma Goliath": _h_ovika__enigma_goliath,
    "Halana and Alena, Partners": _h_halana_and_alena__partners,
    "Fiendish Panda": _h_fiendish_panda,
    "Sanguine Syphoner": _h_sanguine_syphoner,
    "Vampire Soulcaller": _h_vampire_soulcaller,
    "Nullpriest of Oblivion": _h_nullpriest_of_oblivion,
    "Trygon Predator": _h_trygon_predator,
    "Stromkirk Bloodthief": _h_stromkirk_bloodthief,
    "Herald of Faith": _h_herald_of_faith,
    "Billowing Shriekmass": _h_billowing_shriekmass,
    "Pelakka Wurm": _h_pelakka_wurm,
    "Hoarding Dragon": _h_hoarding_dragon,
    "Twinblade Paladin": _h_twinblade_paladin,
    "Infestation Sage": _h_infestation_sage,
    "Inspiring Overseer": _h_inspiring_overseer,
    "Meteor Golem": _h_meteor_golem,
    "Beast-Kin Ranger": _h_beast_kin_ranger,
    "Maalfeld Twins": _h_maalfeld_twins,
    "Midnight Reaper": _h_midnight_reaper,
    "Dragon Mage": _h_dragon_mage,
    "Phyrexian Arena": _h_phyrexian_arena,
    "Lightshell Duo": _h_lightshell_duo,
    "Archway Angel": _h_archway_angel,
    "Primeval Bounty": _h_primeval_bounty,
    "Elfsworn Giant": _h_elfsworn_giant,
    "Soul-Shackled Zombie": _h_soul_shackled_zombie,
    "Cloudblazer": _h_cloudblazer,
    "Pulse Tracker": _h_pulse_tracker,
    "Immersturm Predator": _h_immersturm_predator,
    "Nimble Thopterist": _h_nimble_thopterist,
    "Marketback Walker": _h_marketback_walker,
    "Shefet Archfiend": _h_shefet_archfiend,
    "Burner Rocket": _h_burner_rocket,
    "Detention Chariot": _h_detention_chariot,
    "Spotcycle Scouter": _h_spotcycle_scouter,
    "Brightfield Mustang": _h_brightfield_mustang,
    "Broodheart Engine": _h_broodheart_engine,
    "Fang Guardian": _h_fang_guardian,
    "Broadcast Rambler": _h_broadcast_rambler,
    "Rocketeer Boostbuggy": _h_rocketeer_boostbuggy,
    "Spikeshell Harrier": _h_spikeshell_harrier,
    "Gloryheath Lynx": _h_gloryheath_lynx,
    "Embalmed Ascendant": _h_embalmed_ascendant,
    "Venomsac Lagac": _h_venomsac_lagac,
    "Gastal Blockbuster": _h_gastal_blockbuster,
    "Aatchik, Emerald Radian": _h_aatchik__emerald_radian,
    "Dracosaur Auxiliary": _h_dracosaur_auxiliary,
    "Captain Howler, Sea Scourge": _h_captain_howler__sea_scourge,
    "Haunted Hellride": _h_haunted_hellride,
    "Racers' Scoreboard": _h_racers__scoreboard,
    "Migrating Ketradon": _h_migrating_ketradon,
    "Unswerving Sloth": _h_unswerving_sloth,
    "Gilded Ghoda": _h_gilded_ghoda,
    "Dynamite Diver": _h_dynamite_diver,
    "Marshals' Pathcruiser": _h_marshals__pathcruiser,
    "Cloudspire Coordinator": _h_cloudspire_coordinator,
    "Fearless Swashbuckler": _h_fearless_swashbuckler,
    "Ripclaw Wrangler": _h_ripclaw_wrangler,
    "Roadside Assistance": _h_roadside_assistance,
    "Thundering Broodwagon": _h_thundering_broodwagon,
    "Demonic Junker": _h_demonic_junker,
    "Wreck Remover": _h_wreck_remover,
    "Pothole Mole": _h_pothole_mole,
    "Far Fortune, End Boss": _h_far_fortune__end_boss,
    "Wreckage Wickerfolk": _h_wreckage_wickerfolk,
    "Voyager Glidecar": _h_voyager_glidecar,
    "Ticket Tortoise": _h_ticket_tortoise,
    "Guidelight Matrix": _h_guidelight_matrix,
    "Carrion Cruiser": _h_carrion_cruiser,
    "Hulldrifter": _h_hulldrifter,
    "Caradora, Heart of Alacria": _h_caradora__heart_of_alacria,
    "Ooze Patrol": _h_ooze_patrol,
    "Brightfield Glider": _h_brightfield_glider,
    "Grim Javelineer": _h_grim_javelineer,
    "Pyrewood Gearhulk": _h_pyrewood_gearhulk,
    "Alacrian Jaguar": _h_alacrian_jaguar,
    "Boosted Sloop": _h_boosted_sloop,
    "Pactdoll Terror": _h_pactdoll_terror,
    "Hour of Victory": _h_hour_of_victory,
    "Autarch Mammoth": _h_autarch_mammoth,
    "Guidelight Pathmaker": _h_guidelight_pathmaker,
    "Veloheart Bike": _h_veloheart_bike,
    "Humbling Elder": _h_humbling_elder,
    "Starry-Eyed Skyrider": _h_starry_eyed_skyrider,
    "Kishla Trawlers": _h_kishla_trawlers,
    "Unsparing Boltcaster": _h_unsparing_boltcaster,
    "Yathan Roadwatcher": _h_yathan_roadwatcher,
    "Warden of the Grove": _h_warden_of_the_grove,
    "Boulderborn Dragon": _h_boulderborn_dragon,
    "Encroaching Dragonstorm": _h_encroaching_dragonstorm,
    "Teeming Dragonstorm": _h_teeming_dragonstorm,
    "Mardu Devotee": _h_mardu_devotee,
    "Meticulous Artisan": _h_meticulous_artisan,
    "Gurmag Rakshasa": _h_gurmag_rakshasa,
    "Cori Mountain Stalwart": _h_cori_mountain_stalwart,
    "Nightblade Brigade": _h_nightblade_brigade,
    "Underfoot Underdogs": _h_underfoot_underdogs,
    "Aegis Sculptor": _h_aegis_sculptor,
    "Skirmish Rhino": _h_skirmish_rhino,
    "Equilibrium Adept": _h_equilibrium_adept,
    "Stormplain Detainment": _h_stormplain_detainment,
    "Venerated Stormsinger": _h_venerated_stormsinger,
    "Corroding Dragonstorm": _h_corroding_dragonstorm,
    "Salt Road Packbeast": _h_salt_road_packbeast,
    "Breaching Dragonstorm": _h_breaching_dragonstorm,
    "Sibsig Appraiser": _h_sibsig_appraiser,
    "Reputable Merchant": _h_reputable_merchant,
    "Rainveil Rejuvenator": _h_rainveil_rejuvenator,
    "Jeskai Devotee": _h_jeskai_devotee,
    "Ambling Stormshell": _h_ambling_stormshell,
    "Ainok Wayfarer": _h_ainok_wayfarer,
    "Betor, Kin to All": _h_betor__kin_to_all,
    "Lotuslight Dancers": _h_lotuslight_dancers,
    "Temur Tawnyback": _h_temur_tawnyback,
    "Fire-Rim Form": _h_fire_rim_form,
    "Delta Bloodflies": _h_delta_bloodflies,
    "Loxodon Battle Priest": _h_loxodon_battle_priest,
    "A-Cori-Steel Cutter": _h_a_cori_steel_cutter,
    "Trade Route Envoy": _h_trade_route_envoy,
    "Embermouth Sentinel": _h_embermouth_sentinel,
    "Reigning Victor": _h_reigning_victor,
    "Jeskai Shrinekeeper": _h_jeskai_shrinekeeper,
    "The Sibsig Ceremony": _h_the_sibsig_ceremony,
    "Wingblade Disciple": _h_wingblade_disciple,
    "Sonic Shrieker": _h_sonic_shrieker,
    "Sage of the Fang": _h_sage_of_the_fang,
    "Rescue Leopard": _h_rescue_leopard,
    "Stillness in Motion": _h_stillness_in_motion,
    "War Effort": _h_war_effort,
    "Poised Practitioner": _h_poised_practitioner,
    "Essence Anchor": _h_essence_anchor,
    "Dragonologist": _h_dragonologist,
    "Devoted Duelist": _h_devoted_duelist,
    "Adorned Crocodile": _h_adorned_crocodile,
    "Gurmag Nightwatch": _h_gurmag_nightwatch,
    "Blazing Bomb": _h_blazing_bomb,
    "Magitek Armor": _h_magitek_armor,
    "Mysidian Elder": _h_mysidian_elder,
    "Valkyrie Aerial Unit": _h_valkyrie_aerial_unit,
    "Hope Estheim": _h_hope_estheim,
    "Tellah, Great Sage": _h_tellah__great_sage,
    "Instant Ramen": _h_instant_ramen,
    "Ignis Scientia": _h_ignis_scientia,
    "Sahagin": _h_sahagin,
    "Loporrit Scout": _h_loporrit_scout,
    "Edgar, King of Figaro": _h_edgar__king_of_figaro,
    "Minwu, White Mage": _h_minwu__white_mage,
    "Shantotto, Tactician Magician": _h_shantotto__tactician_magician,
    "Namazu Trader": _h_namazu_trader,
    "Cactuar": _h_cactuar,
    "Balamb T-Rexaur": _h_balamb_t_rexaur,
    "Al Bhed Salvagers": _h_al_bhed_salvagers,
    "Golbez, Crystal Collector": _h_golbez__crystal_collector,
    "Ultimecia, Temporal Threat": _h_ultimecia__temporal_threat,
    "Sabotender": _h_sabotender,
    "Sephiroth, Planet's Heir": _h_sephiroth__planet_s_heir,
    "Shinra Reinforcements": _h_shinra_reinforcements,
    "Seifer Almasy": _h_seifer_almasy,
    "Seymour Flux": _h_seymour_flux,
    "Chocobo Racetrack": _h_chocobo_racetrack,
    "Item Shopkeep": _h_item_shopkeep,
    "Choco, Seeker of Paradise": _h_choco__seeker_of_paradise,
    "Hecteyes": _h_hecteyes,
    "Ride the Shoopuf": _h_ride_the_shoopuf,
    "Rinoa Heartilly": _h_rinoa_heartilly,
    "A-Vivi Ornitier": _h_a_vivi_ornitier,
    "Rosa, Resolute White Mage": _h_rosa__resolute_white_mage,
    "Black Waltz No. 3": _h_black_waltz_no__3,
    "Y'shtola Rhul": _h_y_shtola_rhul,
    "Dwarven Castle Guard": _h_dwarven_castle_guard,
    "Weapons Vendor": _h_weapons_vendor,
    "Lion Heart": _h_lion_heart,
    "Il Mheg Pixie": _h_il_mheg_pixie,
    "Rook Turret": _h_rook_turret,
    "Magic Pot": _h_magic_pot,
    "Coral Sword": _h_coral_sword,
    "Aerith Gainsborough": _h_aerith_gainsborough,
    "Adventurer's Airship": _h_adventurer_s_airship,
    "Tidus, Blitzball Star": _h_tidus__blitzball_star,
    "Dragoon's Wyvern": _h_dragoon_s_wyvern,
    "Cloudbound Moogle": _h_cloudbound_moogle,
    "Gladiolus Amicitia": _h_gladiolus_amicitia,
    "Seedship Agrarian": _h_seedship_agrarian,
    "Wedgelight Rammer": _h_wedgelight_rammer,
    "Territorial Bruntar": _h_territorial_bruntar,
    "Meltstrider Eulogist": _h_meltstrider_eulogist,
    "Thrumming Hivepool": _h_thrumming_hivepool,
    "Starbreach Whale": _h_starbreach_whale,
    "Thawbringer": _h_thawbringer,
    "Weftwalking": _h_weftwalking,
    "Comet Crawler": _h_comet_crawler,
    "Squire's Lightblade": _h_squire_s_lightblade,
    "Knight Luminary": _h_knight_luminary,
    "Sunstar Lightsmith": _h_sunstar_lightsmith,
    "Fell Gravship": _h_fell_gravship,
    "Chrome Companion": _h_chrome_companion,
    "Mechan Assembler": _h_mechan_assembler,
    "Illvoi Operative": _h_illvoi_operative,
    "Eusocial Engineering": _h_eusocial_engineering,
    "Illvoi Infiltrator": _h_illvoi_infiltrator,
    "Wurmwall Sweeper": _h_wurmwall_sweeper,
    "Selfcraft Mechan": _h_selfcraft_mechan,
    "Weftblade Enhancer": _h_weftblade_enhancer,
    "Atmospheric Greenhouse": _h_atmospheric_greenhouse,
    "Flight-Deck Coordinator": _h_flight_deck_coordinator,
    "Drix Fatemaker": _h_drix_fatemaker,
    "Frontline War-Rager": _h_frontline_war_rager,
    "Honored Knight-Captain": _h_honored_knight_captain,
    "Dubious Delicacy": _h_dubious_delicacy,
    "Dawnstrike Vanguard": _h_dawnstrike_vanguard,
    "Remnant Elemental": _h_remnant_elemental,
    "Mm'menon, Uthros Exile": _h_mm_menon__uthros_exile,
    "Nebula Dragon": _h_nebula_dragon,
    "Oreplate Pangolin": _h_oreplate_pangolin,
    "Tannuk, Memorial Ensign": _h_tannuk__memorial_ensign,
    "Rayblade Trooper": _h_rayblade_trooper,
    "Uthros Scanship": _h_uthros_scanship,
    "Pulsar Squadron Ace": _h_pulsar_squadron_ace,
    "Mouth of the Storm": _h_mouth_of_the_storm,
    "Germinating Wurm": _h_germinating_wurm,
    "Sunstar Expansionist": _h_sunstar_expansionist,
    "Swarm Culler": _h_swarm_culler,
    "Blooming Stinger": _h_blooming_stinger,
    "Codecracker Hound": _h_codecracker_hound,
    "Larval Scoutlander": _h_larval_scoutlander,
    "Icecave Crasher": _h_icecave_crasher,
    "Sinister Cryologist": _h_sinister_cryologist,
    "Illvoi Light Jammer": _h_illvoi_light_jammer,
    "Infinite Guideline Station": _h_infinite_guideline_station,
    "Molecular Modifier": _h_molecular_modifier,
    "Debris Field Crusher": _h_debris_field_crusher,
    "Sunstar Chaplain": _h_sunstar_chaplain,
    "Faller's Faithful": _h_faller_s_faithful,
    "Perigee Beckoner": _h_perigee_beckoner,
    "Vaultguard Trooper": _h_vaultguard_trooper,
    "Virus Beetle": _h_virus_beetle,
    "Alpharael, Dreaming Acolyte": _h_alpharael__dreaming_acolyte,
    "Mechan Navigator": _h_mechan_navigator,
    "Starfighter Pilot": _h_starfighter_pilot,
    "Auxiliary Boosters": _h_auxiliary_boosters,
    "Spider-Ham, Peter Porker": _h_spider_ham__peter_porker,
    "Friendly Neighborhood": _h_friendly_neighborhood,
    "Starling, Aerial Ally": _h_starling__aerial_ally,
    "News Helicopter": _h_news_helicopter,
    "Spider-Man, Brooklyn Visionary": _h_spider_man__brooklyn_visionary,
    "Sun-Spider, Nimble Webber": _h_sun_spider__nimble_webber,
    "Spider-Man Noir": _h_spider_man_noir,
    "Gallant Citizen": _h_gallant_citizen,
    "Web of Life and Destiny": _h_web_of_life_and_destiny,
    "Steel Wrecking Ball": _h_steel_wrecking_ball,
    "Web-Warriors": _h_web_warriors,
    "Anti-Venom, Horrifying Healer": _h_anti_venom__horrifying_healer,
    "Professional Wrestler": _h_professional_wrestler,
    "Rent Is Due": _h_rent_is_due,
    "Ezekiel Sims, Spider-Totem": _h_ezekiel_sims__spider_totem,
    "Silver Sable, Mercenary Leader": _h_silver_sable__mercenary_leader,
    "Mysterio, Master of Illusion": _h_mysterio__master_of_illusion,
    "Wall Crawl": _h_wall_crawl,
    "Scarlet Spider, Kaine": _h_scarlet_spider__kaine,
    "Pictures of Spider-Man": _h_pictures_of_spider_man,
    "Flying Octobot": _h_flying_octobot,
    "Lurking Lizards": _h_lurking_lizards,
    "Tombstone, Career Criminal": _h_tombstone__career_criminal,
    "Subway Train": _h_subway_train,
    "Mary Jane Watson": _h_mary_jane_watson,
    "Robotics Mastery": _h_robotics_mastery,
    "Mysterio's Phantasm": _h_mysterio_s_phantasm,
    "Web Up": _h_web_up,
    "City Pigeon": _h_city_pigeon,
    "Madame Web, Clairvoyant": _h_madame_web__clairvoyant,
    "Ultimate Green Goblin": _h_ultimate_green_goblin,
    "Aunt May": _h_aunt_may,
    "Molten Man, Inferno Incarnate": _h_molten_man__inferno_incarnate,
    "Eerie Gravestone": _h_eerie_gravestone,
    "Hot Dog Cart": _h_hot_dog_cart,
    "Angry Rabble": _h_angry_rabble,
    "Spiders-Man, Heroic Horde": _h_spiders_man__heroic_horde,
    "Spider-Bot": _h_spider_bot,
    "Venomized Cat": _h_venomized_cat,
    "Common Crook": _h_common_crook,
    "Spider-UK": _h_spider_uk,
    "Earth Village Ruffians": _h_earth_village_ruffians,
    "Ty Lee, Chi Blocker": _h_ty_lee__chi_blocker,
    "Beetle-Headed Merchants": _h_beetle_headed_merchants,
    "Benevolent River Spirit": _h_benevolent_river_spirit,
    "Fire Navy Trebuchet": _h_fire_navy_trebuchet,
    "Bumi, Unleashed": _h_bumi__unleashed,
    "Badgermole": _h_badgermole,
    "Katara, Water Tribe's Hope": _h_katara__water_tribe_s_hope,
    "Cruel Administrator": _h_cruel_administrator,
    "Crescent Island Temple": _h_crescent_island_temple,
    "Northern Air Temple": _h_northern_air_temple,
    "Buzzard-Wasp Colony": _h_buzzard_wasp_colony,
    "Ostrich-Horse": _h_ostrich_horse,
    "Toph, the Blind Bandit": _h_toph__the_blind_bandit,
    "Tundra Tank": _h_tundra_tank,
    "The Fire Nation Drill": _h_the_fire_nation_drill,
    "Messenger Hawk": _h_messenger_hawk,
    "Earth Kingdom Soldier": _h_earth_kingdom_soldier,
    "Rabaroo Troop": _h_rabaroo_troop,
    "Guru Pathik": _h_guru_pathik,
    "Boar-q-pine": _h_boar_q_pine,
    "Katara, Bending Prodigy": _h_katara__bending_prodigy,
    "Tolls of War": _h_tolls_of_war,
    "Callous Inspector": _h_callous_inspector,
    "Yuyan Archers": _h_yuyan_archers,
    "Wartime Protestors": _h_wartime_protestors,
    "Jeong Jeong's Deserters": _h_jeong_jeong_s_deserters,
    "Sokka, Tenacious Tactician": _h_sokka__tenacious_tactician,
    "Compassionate Healer": _h_compassionate_healer,
    "Wandering Musicians": _h_wandering_musicians,
    "Haru, Hidden Talent": _h_haru__hidden_talent,
    "Avatar Enthusiasts": _h_avatar_enthusiasts,
    "Kyoshi Battle Fan": _h_kyoshi_battle_fan,
    "Iroh, Tea Master": _h_iroh__tea_master,
    "Twin Blades": _h_twin_blades,
    "Dai Li Agents": _h_dai_li_agents,
    "Toph, Hardheaded Teacher": _h_toph__hardheaded_teacher,
    "Treetop Freedom Fighters": _h_treetop_freedom_fighters,
    "Platypus-Bear": _h_platypus_bear,
    "Southern Air Temple": _h_southern_air_temple,
    "Air Nomad Legacy": _h_air_nomad_legacy,
    "Forecasting Fortune Teller": _h_forecasting_fortune_teller,
    "Flopsie, Bumi's Buddy": _h_flopsie__bumi_s_buddy,
    "Mongoose Lizard": _h_mongoose_lizard,
    "Vengeful Villagers": _h_vengeful_villagers,
    "Kyoshi Warriors": _h_kyoshi_warriors,
    "Zuko, Conflicted": _h_zuko__conflicted,
    "The Spirit Oasis": _h_the_spirit_oasis,
    "Canyon Crawler": _h_canyon_crawler,
    "The Mechanist, Aerial Artisan": _h_the_mechanist__aerial_artisan,
    "Knowledge Seeker": _h_knowledge_seeker,
    "Kyoshi Island Plaza": _h_kyoshi_island_plaza,
    "The Earth King": _h_the_earth_king,
    "Unlucky Cabbage Merchant": _h_unlucky_cabbage_merchant,
    "Hog-Monkey": _h_hog_monkey,
    "Earth Kingdom General": _h_earth_kingdom_general,
    "Corrupt Court Official": _h_corrupt_court_official,
    "Invasion Tactics": _h_invasion_tactics,
    "Hama, the Bloodbender": _h_hama__the_bloodbender,
    "Walltop Sentries": _h_walltop_sentries,
    "Toph, the First Metalbender": _h_toph__the_first_metalbender,
    "Pretending Poxbearers": _h_pretending_poxbearers,
    "Glider Kids": _h_glider_kids,
    "The Lion-Turtle": _h_the_lion_turtle,
    "Twilight Diviner": _h_twilight_diviner,
    "Elder Auntie": _h_elder_auntie,
    "Silvergill Peddler": _h_silvergill_peddler,
    "Liminal Hold": _h_liminal_hold,
    "Foraging Wickermaw": _h_foraging_wickermaw,
    "Boggart Prankster": _h_boggart_prankster,
    "Graveshifter": _h_graveshifter,
    "Warren Torchmaster": _h_warren_torchmaster,
    "Prismatic Undercurrents": _h_prismatic_undercurrents,
    "Dundoolin Weaver": _h_dundoolin_weaver,
    "Gutsplitter Gang": _h_gutsplitter_gang,
    "Stratosoarer": _h_stratosoarer,
    "Rooftop Percher": _h_rooftop_percher,
    "Shore Lurker": _h_shore_lurker,
    "Eclipsed Flamekin": _h_eclipsed_flamekin,
    "Puca's Eye": _h_puca_s_eye,
    "Wanderbrine Preacher": _h_wanderbrine_preacher,
    "Gallant Fowlknight": _h_gallant_fowlknight,
    "Thoughtweft Lieutenant": _h_thoughtweft_lieutenant,
    "Shimmercreep": _h_shimmercreep,
    "Clachan Festival": _h_clachan_festival,
    "Dawnhand Eulogist": _h_dawnhand_eulogist,
    "Bre of Clan Stoutarm": _h_bre_of_clan_stoutarm,
    "Kithkeeper": _h_kithkeeper,
    "Boggart Cursecrafter": _h_boggart_cursecrafter,
    "Vinebred Brawler": _h_vinebred_brawler,
    "Wary Farmer": _h_wary_farmer,
    "Sourbread Auntie": _h_sourbread_auntie,
    "Wanderwine Distracter": _h_wanderwine_distracter,
    "Eclipsed Elf": _h_eclipsed_elf,
    "Lluwen, Imperfect Naturalist": _h_lluwen__imperfect_naturalist,
    "Kinsbaile Aspirant": _h_kinsbaile_aspirant,
    "Changeling Wayfinder": _h_changeling_wayfinder,
    "Moonglove Extractor": _h_moonglove_extractor,
    "Tributary Vaulter": _h_tributary_vaulter,
    "Mistmeadow Council": _h_mistmeadow_council,
    "Eclipsed Boggart": _h_eclipsed_boggart,
    "Blighted Blackthorn": _h_blighted_blackthorn,
    "Noggle Robber": _h_noggle_robber,
    "Eclipsed Merrow": _h_eclipsed_merrow,
    "Crossroads Watcher": _h_crossroads_watcher,
    "Boggart Mischief": _h_boggart_mischief,
    "Scuzzback Scrounger": _h_scuzzback_scrounger,
    "Pestered Wellguard": _h_pestered_wellguard,
    "Champion of the Path": _h_champion_of_the_path,
    "Lys Alana Informant": _h_lys_alana_informant,
    "Mudbutton Cursetosser": _h_mudbutton_cursetosser,
    "Aquitect's Defenses": _h_aquitect_s_defenses,
    "Flamekin Gildweaver": _h_flamekin_gildweaver,
    "Tanufel Rimespeaker": _h_tanufel_rimespeaker,
    "Morcant's Eyes": _h_morcant_s_eyes,
    "Dream Seizer": _h_dream_seizer,
    "Luminollusk": _h_luminollusk,
    "Heirloom Auntie": _h_heirloom_auntie,
    "Merrow Skyswimmer": _h_merrow_skyswimmer,
    "Silvergill Mentor": _h_silvergill_mentor,
    "Enraged Flamecaster": _h_enraged_flamecaster,
    "Eclipsed Kithkin": _h_eclipsed_kithkin,
    "Summit Sentinel": _h_summit_sentinel,
    "Kulrath Mystic": _h_kulrath_mystic,
    "Scarblade Scout": _h_scarblade_scout,
    "Flaring Cinder": _h_flaring_cinder,
    "Lofty Dreams": _h_lofty_dreams,
    "Lasting Tarfire": _h_lasting_tarfire,
    "Pummeler for Hire": _h_pummeler_for_hire,
    "South Wind Avatar": _h_south_wind_avatar,
    "Rock Soldiers": _h_rock_soldiers,
    "Courier of Comestibles": _h_courier_of_comestibles,
    "Donatello, Way with Machines": _h_donatello__way_with_machines,
    "Mechanized Ninja Cavalry": _h_mechanized_ninja_cavalry,
    "EPF Point Squad": _h_epf_point_squad,
    "Foot Ninjas": _h_foot_ninjas,
    "Leonardo, Leader in Blue": _h_leonardo__leader_in_blue,
    "April O'Neil, Kunoichi Trainee": _h_april_o_neil__kunoichi_trainee,
    "Mouser Foundry": _h_mouser_foundry,
    "Buzz Bots": _h_buzz_bots,
    "Triceraton Commander": _h_triceraton_commander,
    "Null Group Biological Assets": _h_null_group_biological_assets,
    "Primordial Pachyderm": _h_primordial_pachyderm,
    "Anchovy & Banana Pizza": _h_anchovy___banana_pizza,
    "Savanti Romero, Time's Exile": _h_savanti_romero__time_s_exile,
    "Omni-Cheese Pizza": _h_omni_cheese_pizza,
    "Featherbrained Filcher": _h_featherbrained_filcher,
    "Utrom Scientists": _h_utrom_scientists,
    "Party Dude": _h_party_dude,
    "Dimensional Exile": _h_dimensional_exile,
    "Paramecia Coloniex": _h_paramecia_coloniex,
    "West Wind Avatar": _h_west_wind_avatar,
    "Spicy Oatmeal Pizza": _h_spicy_oatmeal_pizza,
    "Mutant Town Musicians": _h_mutant_town_musicians,
    "Everything Pizza": _h_everything_pizza,
    "General Traag, Heart of Stone": _h_general_traag__heart_of_stone,
    "Turtle Van": _h_turtle_van,
    "The Neutrinos": _h_the_neutrinos,
    "Sally Pride, Lioness Leader": _h_sally_pride__lioness_leader,
    "Jennika, Bad Apple Big Sister": _h_jennika__bad_apple_big_sister,
    "Foot Elite": _h_foot_elite,
    "Stockman, Mad Fly-entist": _h_stockman__mad_fly_entist,
    "Turtle Blimp": _h_turtle_blimp,
    "Guac & Marshmallow Pizza": _h_guac___marshmallow_pizza,
    "East Wind Avatar": _h_east_wind_avatar,
    "Baxter Stockman": _h_baxter_stockman,
    "Pizza Face, Gastromancer": _h_pizza_face__gastromancer,
    "Old Hob, Alleycat Blues": _h_old_hob__alleycat_blues,
    "Nobody": _h_nobody,
    "Donatello, Turtle Techie": _h_donatello__turtle_techie,
    "Mighty Mutanimals": _h_mighty_mutanimals,
    "Bogwater Lumaret": _h_bogwater_lumaret,
    "Mindful Biomancer": _h_mindful_biomancer,
    "Eager Glyphmage": _h_eager_glyphmage,
    "Colossus of the Blood Age": _h_colossus_of_the_blood_age,
    "Postmortem Professor": _h_postmortem_professor,
    "Teacher's Pest": _h_teacher_s_pest,
    "Stadium Tidalmage": _h_stadium_tidalmage,
    "Sneering Shadewriter": _h_sneering_shadewriter,
    "Paradox Surveyor": _h_paradox_surveyor,
    "Ascendant Dustspeaker": _h_ascendant_dustspeaker,
    "Pestbrood Sloth": _h_pestbrood_sloth,
    "Old-Growth Educator": _h_old_growth_educator,
    "Tackle Artist": _h_tackle_artist,
    "Muse Seeker": _h_muse_seeker,
    "Stirring Honormancer": _h_stirring_honormancer,
    "Arnyn, Deathbloom Botanist": _h_arnyn__deathbloom_botanist,
    "Deluge Virtuoso": _h_deluge_virtuoso,
    "Thunderdrum Soloist": _h_thunderdrum_soloist,
    "Poisoner's Apprentice": _h_poisoner_s_apprentice,
    "Pensive Professor": _h_pensive_professor,
    "Primary Research": _h_primary_research,
    "Lorehold, the Historian": _h_lorehold__the_historian,
    "Spectacular Skywhale": _h_spectacular_skywhale,
    "Aziza, Mage Tower Captain": _h_aziza__mage_tower_captain,
    "Elemental Mascot": _h_elemental_mascot,
    "Ennis, Debate Moderator": _h_ennis__debate_moderator,
    "Cauldron of Essence": _h_cauldron_of_essence,
    "Living History": _h_living_history,
    "Pest Mascot": _h_pest_mascot,
    "Blech, Loafing Pest": _h_blech__loafing_pest,
    "Moseo, Vein's New Dean": _h_moseo__vein_s_new_dean,
    "Magmablood Archaic": _h_magmablood_archaic,
    "Fractal Tender": _h_fractal_tender,
    "Pterafractyl": _h_pterafractyl,
    "Additive Evolution": _h_additive_evolution,
    "Orysa, Tide Choreographer": _h_orysa__tide_choreographer,
    "Thornfist Striker": _h_thornfist_striker,
    "Exhibition Tidecaller": _h_exhibition_tidecaller,
    "Conciliator's Duelist": _h_conciliator_s_duelist,
    "Ambitious Augmenter": _h_ambitious_augmenter,
    "Essenceknit Scholar": _h_essenceknit_scholar,
    "Owlin Historian": _h_owlin_historian,
    "Strixhaven Skycoach": _h_strixhaven_skycoach,
    "Shopkeeper's Bane": _h_shopkeeper_s_bane,
    "Textbook Tabulator": _h_textbook_tabulator,
    "Snooping Page": _h_snooping_page,
    "Expressive Firedancer": _h_expressive_firedancer,
    "Environmental Scientist": _h_environmental_scientist,
    "Rubble Rouser": _h_rubble_rouser,
    "Zealous Lorecaster": _h_zealous_lorecaster,
    "Mica, Reader of Ruins": _h_mica__reader_of_ruins,
    "Imperious Inkmage": _h_imperious_inkmage,
}.items(): ETB_EFFECTS.setdefault(_n,_f)

for _n,_f in {
    "Witch's Mark": _h_witch_s_mark,
    "Gnawing Crescendo": _h_gnawing_crescendo,
    "Thunderous Debut": _h_thunderous_debut,
    "Asinine Antics": _h_asinine_antics,
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
    "Feral Encounter": _h_feral_encounter,
    "Titanic Growth": _h_titanic_growth,
    "Curse of the Werefox": _h_curse_of_the_werefox,
    "Become Brutes": _h_become_brutes,
    "Farsight Ritual": _h_farsight_ritual,
    "Freeze in Place": _h_freeze_in_place,
    "Into the Fae Court": _h_into_the_fae_court,
    "Candy Grapple": _h_candy_grapple,
    "Flick a Coin": _h_flick_a_coin,
    "Cut In": _h_cut_in,
    "Plunge into Winter": _h_plunge_into_winter,
    "Return Triumphant": _h_return_triumphant,
    "Graceful Takedown": _h_graceful_takedown,
    "Break the Spell": _h_break_the_spell,
    "Archon's Glory": _h_archon_s_glory,
    "Moment of Valor": _h_moment_of_valor,
    "Kindled Heroism": _h_kindled_heroism,
    "Johann's Stopgap": _h_johann_s_stopgap,
    "Commune with Nature": _h_commune_with_nature,
    "Taken by Nightmares": _h_taken_by_nightmares,
    "Leaping Ambush": _h_leaping_ambush,
    "Back for Seconds": _h_back_for_seconds,
    "Frantic Firebolt": _h_frantic_firebolt,
    "Shatter the Oath": _h_shatter_the_oath,
    "Rowan's Grim Search": _h_rowan_s_grim_search,
    "Ice Out": _h_ice_out,
    "Hurl into History": _h_hurl_into_history,
    "Acrobatic Leap": _h_acrobatic_leap,
    "Huatli's Final Strike": _h_huatli_s_final_strike,
    "Over the Edge": _h_over_the_edge,
    "Quicksand Whirlpool": _h_quicksand_whirlpool,
    "Malamet Battle Glyph": _h_malamet_battle_glyph,
    "Brackish Blunder": _h_brackish_blunder,
    "Calamitous Cave-In": _h_calamitous_cave_in,
    "Staggering Size": _h_staggering_size,
    "Cosmium Confluence": _h_cosmium_confluence,
    "Family Reunion": _h_family_reunion,
    "Hit the Mother Lode": _h_hit_the_mother_lode,
    "Daring Discovery": _h_daring_discovery,
    "Ancestors' Aid": _h_ancestors__aid,
    "Join the Dead": _h_join_the_dead,
    "Walk with the Ancestors": _h_walk_with_the_ancestors,
    "Defossilize": _h_defossilize,
    "Ancestral Reminiscence": _h_ancestral_reminiscence,
    "Another Chance": _h_another_chance,
    "Ray of Ruin": _h_ray_of_ruin,
    "Out of Air": _h_out_of_air,
    "Reasonable Doubt": _h_reasonable_doubt,
    "Macabre Reconstruction": _h_macabre_reconstruction,
    "No Witnesses": _h_no_witnesses,
    "Drag the Canal": _h_drag_the_canal,
    "Toxin Analysis": _h_toxin_analysis,
    "Out Cold": _h_out_cold,
    "They Went This Way": _h_they_went_this_way,
    "Caught Red-Handed": _h_caught_red_handed,
    "Treacherous Greed": _h_treacherous_greed,
    "Soul Search": _h_soul_search,
    "The Chase Is On": _h_the_chase_is_on,
    "Suspicious Detonation": _h_suspicious_detonation,
    "Hide in Plain Sight": _h_hide_in_plain_sight,
    "Galvanize": _h_galvanize,
    "Presumed Dead": _h_presumed_dead,
    "Auspicious Arrival": _h_auspicious_arrival,
    "Slime Against Humanity": _h_slime_against_humanity,
    "Fanatical Strength": _h_fanatical_strength,
    "Deadly Complication": _h_deadly_complication,
    "Eliminate the Impossible": _h_eliminate_the_impossible,
    "Audience with Trostani": _h_audience_with_trostani,
    "It Doesn't Add Up": _h_it_doesn_t_add_up,
    "On the Job": _h_on_the_job,
    "Officious Interrogation": _h_officious_interrogation,
    "Intrude on the Mind": _h_intrude_on_the_mind,
    "Bite Down on Crime": _h_bite_down_on_crime,
    "Unfortunate Accident": _h_unfortunate_accident,
    "Map the Frontier": _h_map_the_frontier,
    "Take the Fall": _h_take_the_fall,
    "Make Your Own Luck": _h_make_your_own_luck,
    "Gold Rush": _h_gold_rush,
    "Step Between Worlds": _h_step_between_worlds,
    "One Last Job": _h_one_last_job,
    "Mourner's Surprise": _h_mourner_s_surprise,
    "Outlaws' Fury": _h_outlaws__fury,
    "Full Steam Ahead": _h_full_steam_ahead,
    "Metamorphic Blast": _h_metamorphic_blast,
    "Dance of the Tumbleweeds": _h_dance_of_the_tumbleweeds,
    "Hell to Pay": _h_hell_to_pay,
    "Trick Shot": _h_trick_shot,
    "Form a Posse": _h_form_a_posse,
    "Desert's Due": _h_desert_s_due,
    "Skulduggery": _h_skulduggery,
    "Getaway Glamer": _h_getaway_glamer,
    "Consuming Ashes": _h_consuming_ashes,
    "Badlands Revival": _h_badlands_revival,
    "Plan the Heist": _h_plan_the_heist,
    "Quick Draw": _h_quick_draw,
    "Great Train Heist": _h_great_train_heist,
    "Eriette's Lullaby": _h_eriette_s_lullaby,
    "Explosive Derailment": _h_explosive_derailment,
    "Corrupted Conviction": _h_corrupted_conviction,
    "Trash the Town": _h_trash_the_town,
    "Jailbreak Scheme": _h_jailbreak_scheme,
    "Fleeting Reflection": _h_fleeting_reflection,
    "Thunder Salvo": _h_thunder_salvo,
    "Throw from the Saddle": _h_throw_from_the_saddle,
    "Rise of the Varmints": _h_rise_of_the_varmints,
    "Seize the Secrets": _h_seize_the_secrets,
    "Highway Robbery": _h_highway_robbery,
    "Take Up the Shield": _h_take_up_the_shield,
    "Rustler Rampage": _h_rustler_rampage,
    "Betrayal at the Vault": _h_betrayal_at_the_vault,
    "Failed Fording": _h_failed_fording,
    "Molten Duplication": _h_molten_duplication,
    "Conduct Electricity": _h_conduct_electricity,
    "Mind Spiral": _h_mind_spiral,
    "Wildfire Howl": _h_wildfire_howl,
    "Rabid Gnaw": _h_rabid_gnaw,
    "Playful Shove": _h_playful_shove,
    "Coiling Rebirth": _h_coiling_rebirth,
    "Hazel's Nocturne": _h_hazel_s_nocturne,
    "Mind Spring": _h_mind_spring,
    "Psychic Whorl": _h_psychic_whorl,
    "Otterball Antics": _h_otterball_antics,
    "Valley Rally": _h_valley_rally,
    "Season of the Bold": _h_season_of_the_bold,
    "Rabid Bite": _h_rabid_bite,
    "Starfall Invocation": _h_starfall_invocation,
    "Agate Assault": _h_agate_assault,
    "Spellgyre": _h_spellgyre,
    "Pearl of Wisdom": _h_pearl_of_wisdom,
    "Crumb and Get It": _h_crumb_and_get_it,
    "Peerless Recycling": _h_peerless_recycling,
    "Rabbit Response": _h_rabbit_response,
    "Diresight": _h_diresight,
    "Ruthless Negotiation": _h_ruthless_negotiation,
    "High Stride": _h_high_stride,
    "Sazacap's Brew": _h_sazacap_s_brew,
    "Consumed by Greed": _h_consumed_by_greed,
    "Repel Calamity": _h_repel_calamity,
    "Mabel's Mettle": _h_mabel_s_mettle,
    "Flame Lash": _h_flame_lash,
    "Calamitous Tide": _h_calamitous_tide,
    "Sonar Strike": _h_sonar_strike,
    "Stargaze": _h_stargaze,
    "For the Common Good": _h_for_the_common_good,
    "Savor": _h_savor,
    "Take Out the Trash": _h_take_out_the_trash,
    "Hop to It": _h_hop_to_it,
    "Nocturnal Hunger": _h_nocturnal_hunger,
    "Early Winter": _h_early_winter,
    "Commune with Evil": _h_commune_with_evil,
    "Vanish from Sight": _h_vanish_from_sight,
    "Come Back Wrong": _h_come_back_wrong,
    "Give In to Violence": _h_give_in_to_violence,
    "Beastie Beatdown": _h_beastie_beatdown,
    "Midnight Mayhem": _h_midnight_mayhem,
    "Twist Reality": _h_twist_reality,
    "Enter the Enigma": _h_enter_the_enigma,
    "Demonic Counsel": _h_demonic_counsel,
    "Jump Scare": _h_jump_scare,
    "Waltz of Rage": _h_waltz_of_rage,
    "Unnerving Grasp": _h_unnerving_grasp,
    "Seized from Slumber": _h_seized_from_slumber,
    "Under the Skin": _h_under_the_skin,
    "Peer Past the Veil": _h_peer_past_the_veil,
    "Unwanted Remake": _h_unwanted_remake,
    "Winter's Intervention": _h_winter_s_intervention,
    "Murder": _h_murder,
    "Break Down the Door": _h_break_down_the_door,
    "Glimmerburst": _h_glimmerburst,
    "Rite of the Moth": _h_rite_of_the_moth,
    "Coordinated Clobbering": _h_coordinated_clobbering,
    "Live or Die": _h_live_or_die,
    "Let's Play a Game": _h_let_s_play_a_game,
    "Manifest Dread": _h_manifest_dread,
    "Drag to the Roots": _h_drag_to_the_roots,
    "Impossible Inferno": _h_impossible_inferno,
    "Emerge from the Cocoon": _h_emerge_from_the_cocoon,
    "Sanguine Indulgence": _h_sanguine_indulgence,
    "Hero's Downfall": _h_hero_s_downfall,
    "Cemetery Recruitment": _h_cemetery_recruitment,
    "Bake into a Pie": _h_bake_into_a_pie,
    "Thrill of Possibility": _h_thrill_of_possibility,
    "Uncharted Voyage": _h_uncharted_voyage,
    "Preposterous Proportions": _h_preposterous_proportions,
    "Overrun": _h_overrun,
    "Joraga Invocation": _h_joraga_invocation,
    "An Offer You Can't Refuse": _h_an_offer_you_can_t_refuse,
    "Revenge of the Rats": _h_revenge_of_the_rats,
    "Dive Down": _h_dive_down,
    "Circuitous Route": _h_circuitous_route,
    "Seismic Rupture": _h_seismic_rupture,
    "Adamant Will": _h_adamant_will,
    "Claws Out": _h_claws_out,
    "Incinerating Blast": _h_incinerating_blast,
    "Divine Resilience": _h_divine_resilience,
    "Make a Stand": _h_make_a_stand,
    "Lunar Insight": _h_lunar_insight,
    "Self-Reflection": _h_self_reflection,
    "Deadly Plot": _h_deadly_plot,
    "Bite Down": _h_bite_down,
    "Fleeting Flight": _h_fleeting_flight,
    "Brass's Bounty": _h_brass_s_bounty,
    "Dread Summons": _h_dread_summons,
    "Grow from the Ashes": _h_grow_from_the_ashes,
    "Finale of Revelation": _h_finale_of_revelation,
    "Goblin Negotiation": _h_goblin_negotiation,
    "Goblin Surprise": _h_goblin_surprise,
    "Cancel": _h_cancel,
    "Involuntary Employment": _h_involuntary_employment,
    "Exsanguinate": _h_exsanguinate,
    "Inspiring Call": _h_inspiring_call,
    "Fake Your Own Death": _h_fake_your_own_death,
    "Fleeting Distraction": _h_fleeting_distraction,
    "Inspiration from Beyond": _h_inspiration_from_beyond,
    "Heroic Reinforcements": _h_heroic_reinforcements,
    "Macabre Waltz": _h_macabre_waltz,
    "Dragon Fodder": _h_dragon_fodder,
    "Teach by Example": _h_teach_by_example,
    "Luminous Rebuke": _h_luminous_rebuke,
    "Tribute to Hunger": _h_tribute_to_hunger,
    "Deadly Riposte": _h_deadly_riposte,
    "Kindled Fury": _h_kindled_fury,
    "Mortify": _h_mortify,
    "Sure Strike": _h_sure_strike,
    "Felling Blow": _h_felling_blow,
    "Arcane Epiphany": _h_arcane_epiphany,
    "Gallant Strike": _h_gallant_strike,
    "Pedal to the Metal": _h_pedal_to_the_metal,
    "Run Over": _h_run_over,
    "Crash and Burn": _h_crash_and_burn,
    "Bestow Greatness": _h_bestow_greatness,
    "Voyage Home": _h_voyage_home,
    "Push the Limit": _h_push_the_limit,
    "Haunt the Network": _h_haunt_the_network,
    "Syphon Fuel": _h_syphon_fuel,
    "Spectacular Pileup": _h_spectacular_pileup,
    "Plow Through": _h_plow_through,
    "Risky Shortcut": _h_risky_shortcut,
    "Back on Track": _h_back_on_track,
    "Spin Out": _h_spin_out,
    "Explosive Getaway": _h_explosive_getaway,
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
    "Riverwheel Sweep": _h_riverwheel_sweep,
    "Riverwalk Technique": _h_riverwalk_technique,
    "Ureni's Rebuff": _h_ureni_s_rebuff,
    "Aggressive Negotiations": _h_aggressive_negotiations,
    "Unending Whisper": _h_unending_whisper,
    "Roamer's Routine": _h_roamer_s_routine,
    "Seize Opportunity": _h_seize_opportunity,
    "Piercing Exhale": _h_piercing_exhale,
    "Salt Road Skirmish": _h_salt_road_skirmish,
    "Rydia's Return": _h_rydia_s_return,
    "Fate of the Sun-Cryst": _h_fate_of_the_sun_cryst,
    "Reach the Horizon": _h_reach_the_horizon,
    "Aerith Rescue Mission": _h_aerith_rescue_mission,
    "Swallowed by Leviathan": _h_swallowed_by_leviathan,
    "Evil Reawakened": _h_evil_reawakened,
    "Combat Tutorial": _h_combat_tutorial,
    "Circle of Power": _h_circle_of_power,
    "Deadly Embrace": _h_deadly_embrace,
    "Fight On!": _h_fight_on_,
    "Laughing Mad": _h_laughing_mad,
    "Auron's Inspiration": _h_auron_s_inspiration,
    "Overkill": _h_overkill,
    "Travel the Overworld": _h_travel_the_overworld,
    "Cornered by Black Mages": _h_cornered_by_black_mages,
    "Resentful Revelation": _h_resentful_revelation,
    "From Father to Son": _h_from_father_to_son,
    "Ice Magic": _h_ice_magic,
    "Galuf's Final Act": _h_galuf_s_final_act,
    "Light of Judgment": _h_light_of_judgment,
    "Vayne's Treachery": _h_vayne_s_treachery,
    "Sephiroth's Intervention": _h_sephiroth_s_intervention,
    "Moogles' Valor": _h_moogles__valor,
    "Eject": _h_eject,
    "You're Not Alone": _h_you_re_not_alone,
    "Call the Mountain Chocobo": _h_call_the_mountain_chocobo,
    "Judgment Bolt": _h_judgment_bolt,
    "Clash of the Eikons": _h_clash_of_the_eikons,
    "Prishe's Wanderings": _h_prishe_s_wanderings,
    "Blitzball Shot": _h_blitzball_shot,
    "Relm's Sketching": _h_relm_s_sketching,
    "The Crystal's Chosen": _h_the_crystal_s_chosen,
    "Gysahl Greens": _h_gysahl_greens,
    "Drill Too Deep": _h_drill_too_deep,
    "Rig for War": _h_rig_for_war,
    "Embrace Oblivion": _h_embrace_oblivion,
    "Zealous Display": _h_zealous_display,
    "Lithobraking": _h_lithobraking,
    "Gravkill": _h_gravkill,
    "Radiant Strike": _h_radiant_strike,
    "Biosynthic Burst": _h_biosynthic_burst,
    "Decode Transmissions": _h_decode_transmissions,
    "Mental Modulation": _h_mental_modulation,
    "Invasive Maneuvers": _h_invasive_maneuvers,
    "Orbital Plunge": _h_orbital_plunge,
    "Diplomatic Relations": _h_diplomatic_relations,
    "Sami's Curiosity": _h_sami_s_curiosity,
    "Shattered Wings": _h_shattered_wings,
    "Vote Out": _h_vote_out,
    "Dual-Sun Technique": _h_dual_sun_technique,
    "Mutinous Massacre": _h_mutinous_massacre,
    "Hymn of the Faller": _h_hymn_of_the_faller,
    "Bombard": _h_bombard,
    "Terminal Velocity": _h_terminal_velocity,
    "Lost in Space": _h_lost_in_space,
    "Scour for Scrap": _h_scour_for_scrap,
    "Dark Endurance": _h_dark_endurance,
    "Cerebral Download": _h_cerebral_download,
    "Amazing Acrobatics": _h_amazing_acrobatics,
    "The Spot's Portal": _h_the_spot_s_portal,
    "Terrific Team-Up": _h_terrific_team_up,
    "Risky Research": _h_risky_research,
    "Grow Extra Arms": _h_grow_extra_arms,
    "Scorpion's Sting": _h_scorpion_s_sting,
    "Venom's Hunger": _h_venom_s_hunger,
    "Whoosh!": _h_whoosh_,
    "Prison Break": _h_prison_break,
    "School Daze": _h_school_daze,
    "Kapow!": _h_kapow_,
    "Wisecrack": _h_wisecrack,
    "Scout the City": _h_scout_the_city,
    "Thwip!": _h_thwip_,
    "Ember Island Production": _h_ember_island_production,
    "Foggy Swamp Visions": _h_foggy_swamp_visions,
    "Fatal Fissure": _h_fatal_fissure,
    "How to Start a Riot": _h_how_to_start_a_riot,
    "Solstice Revelations": _h_solstice_revelations,
    "Fire Nation Attacks": _h_fire_nation_attacks,
    "Lost Days": _h_lost_days,
    "Waterbending Lesson": _h_waterbending_lesson,
    "Yip Yip!": _h_yip_yip_,
    "Dai Li Indoctrination": _h_dai_li_indoctrination,
    "Jet's Brainwashing": _h_jet_s_brainwashing,
    "Zuko's Exile": _h_zuko_s_exile,
    "Earthbending Lesson": _h_earthbending_lesson,
    "Spirit Water Revival": _h_spirit_water_revival,
    "Sold Out": _h_sold_out,
    "Cycle of Renewal": _h_cycle_of_renewal,
    "Ruinous Waterbending": _h_ruinous_waterbending,
    "Sokka's Haiku": _h_sokka_s_haiku,
    "Cunning Maneuver": _h_cunning_maneuver,
    "Seismic Sense": _h_seismic_sense,
    "Pillar Launch": _h_pillar_launch,
    "Ozai's Cruelty": _h_ozai_s_cruelty,
    "Sozin's Comet": _h_sozin_s_comet,
    "Allies at Last": _h_allies_at_last,
    "United Front": _h_united_front,
    "Energybending": _h_energybending,
    "Fancy Footwork": _h_fancy_footwork,
    "Crashing Wave": _h_crashing_wave,
    "Rockalanche": _h_rockalanche,
    "Deadly Precision": _h_deadly_precision,
    "Gather the White Lotus": _h_gather_the_white_lotus,
    "Aang's Journey": _h_aang_s_journey,
    "Sandbenders' Storm": _h_sandbenders__storm,
    "Airbending Lesson": _h_airbending_lesson,
    "Razor Rings": _h_razor_rings,
    "Epic Downfall": _h_epic_downfall,
    "Zuko's Conviction": _h_zuko_s_conviction,
    "Earth Rumble": _h_earth_rumble,
    "Azula Always Lies": _h_azula_always_lies,
    "The Last Agni Kai": _h_the_last_agni_kai,
    "Rocky Rebuke": _h_rocky_rebuke,
    "End-Blaze Epiphany": _h_end_blaze_epiphany,
    "Thirst for Identity": _h_thirst_for_identity,
    "Spry and Mighty": _h_spry_and_mighty,
    "Goatnap": _h_goatnap,
    "Riverguard's Reflexes": _h_riverguard_s_reflexes,
    "Bogslither's Embrace": _h_bogslither_s_embrace,
    "Crib Swap": _h_crib_swap,
    "Soul Immolation": _h_soul_immolation,
    "Auntie's Sentence": _h_auntie_s_sentence,
    "Cinder Strike": _h_cinder_strike,
    "Blossoming Defense": _h_blossoming_defense,
    "Brigid's Command": _h_brigid_s_command,
    "Scarblade's Malice": _h_scarblade_s_malice,
    "Giantfall": _h_giantfall,
    "Midnight Tilling": _h_midnight_tilling,
    "Wanderwine Farewell": _h_wanderwine_farewell,
    "Burning Curiosity": _h_burning_curiosity,
    "Grub's Command": _h_grub_s_command,
    "Tend the Sprigs": _h_tend_the_sprigs,
    "Tweeze": _h_tweeze,
    "Thoughtweft Charge": _h_thoughtweft_charge,
    "Harmonized Crescendo": _h_harmonized_crescendo,
    "Rime Chill": _h_rime_chill,
    "Unforgiving Aim": _h_unforgiving_aim,
    "Unexpected Assistance": _h_unexpected_assistance,
    "Kindle the Inner Flame": _h_kindle_the_inner_flame,
    "Appeal to Eirdu": _h_appeal_to_eirdu,
    "Wild Unraveling": _h_wild_unraveling,
    "Personify": _h_personify,
    "Unbury": _h_unbury,
    "Reckless Ransacking": _h_reckless_ransacking,
    "Trystan's Command": _h_trystan_s_command,
    "Assert Perfection": _h_assert_perfection,
    "Feed the Flames": _h_feed_the_flames,
    "Dose of Dawnglow": _h_dose_of_dawnglow,
    "Mind Transfer Protocol": _h_mind_transfer_protocol,
    "Stomped by the Foot": _h_stomped_by_the_foot,
    "Bot Bashing Time": _h_bot_bashing_time,
    "Splinter's Technique": _h_splinter_s_technique,
    "Shredder's Revenge": _h_shredder_s_revenge,
    "Tainted Treats": _h_tainted_treats,
    "The Last Ronin's Technique": _h_the_last_ronin_s_technique,
    "Turtles in Time": _h_turtles_in_time,
    "Jennika's Technique": _h_jennika_s_technique,
    "Grounded for Life": _h_grounded_for_life,
    "Tenderize": _h_tenderize,
    "Cowabunga!": _h_cowabunga_,
    "Brilliance Unleashed": _h_brilliance_unleashed,
    "Mouser Attack!": _h_mouser_attack_,
    "Ooze Spill": _h_ooze_spill,
    "Manhole Missile": _h_manhole_missile,
    "Hamato Guardian Stance": _h_hamato_guardian_stance,
    "Broadcast Takeover": _h_broadcast_takeover,
    "Karai's Technique": _h_karai_s_technique,
    "New Generation's Technique": _h_new_generation_s_technique,
    "Mutant Chain Reaction": _h_mutant_chain_reaction,
    "Raphael's Technique": _h_raphael_s_technique,
    "Death in the Family": _h_death_in_the_family,
    "Oracle's Restoration": _h_oracle_s_restoration,
    "Stand Up for Yourself": _h_stand_up_for_yourself,
    "Daydream": _h_daydream,
    "Artistic Process": _h_artistic_process,
    "Borrowed Knowledge": _h_borrowed_knowledge,
    "Harsh Annotation": _h_harsh_annotation,
    "Efflorescence": _h_efflorescence,
    "Masterful Flourish": _h_masterful_flourish,
    "Growth Curve": _h_growth_curve,
    "Together as One": _h_together_as_one,
    "Splatter Technique": _h_splatter_technique,
    "Duel Tactics": _h_duel_tactics,
    "Wild Hypothesis": _h_wild_hypothesis,
    "Heated Argument": _h_heated_argument,
    "Mana Sculpt": _h_mana_sculpt,
    "Snarl Song": _h_snarl_song,
    "Wilt in the Heat": _h_wilt_in_the_heat,
    "Pursue the Past": _h_pursue_the_past,
    "Interjection": _h_interjection,
    "Rabid Attack": _h_rabid_attack,
    "Stress Dream": _h_stress_dream,
    "Archaic's Agony": _h_archaic_s_agony,
    "Seize the Spoils": _h_seize_the_spoils,
    "Mathemagics": _h_mathemagics,
    "Zimone's Experiment": _h_zimone_s_experiment,
    "Choreographed Sparks": _h_choreographed_sparks,
    "Muse's Encouragement": _h_muse_s_encouragement,
    "Fractal Anomaly": _h_fractal_anomaly,
    "Banishing Betrayal": _h_banishing_betrayal,
    "Dissection Practice": _h_dissection_practice,
    "Brush Off": _h_brush_off,
    "Suspend Aggression": _h_suspend_aggression,
    "Applied Geometry": _h_applied_geometry,
    "Chelonian Tackle": _h_chelonian_tackle,
    "Moment of Reckoning": _h_moment_of_reckoning,
    "Vicious Rivalry": _h_vicious_rivalry,
    "Send in the Pest": _h_send_in_the_pest,
    "Dig Site Inventory": _h_dig_site_inventory,
    "Practiced Offense": _h_practiced_offense,
    "Chase Inspiration": _h_chase_inspiration,
    "Antiquities on the Loose": _h_antiquities_on_the_loose,
    "Foolish Fate": _h_foolish_fate,
    "Unsubtle Mockery": _h_unsubtle_mockery,
    "Lorehold Charm": _h_lorehold_charm,
    "Proctor's Gaze": _h_proctor_s_gaze,
    "Last Gasp": _h_last_gasp,
    "Dina's Guidance": _h_dina_s_guidance,
    "Glorious Decay": _h_glorious_decay,
    "Wander Off": _h_wander_off,
    "Social Snub": _h_social_snub,
    "Cost of Brilliance": _h_cost_of_brilliance,
    "Embrace the Paradox": _h_embrace_the_paradox,
    "Ajani's Response": _h_ajani_s_response,
    "Killian's Confidence": _h_killian_s_confidence,
    "Burrog Barrage": _h_burrog_barrage,
    "Pull from the Grave": _h_pull_from_the_grave,
    "Germination Practicum": _h_germination_practicum,
    "Rapturous Moment": _h_rapturous_moment,
    "Visionary's Dance": _h_visionary_s_dance,
    "Rapier Wit": _h_rapier_wit,
    "Lumaret's Favor": _h_lumaret_s_favor,
    "Root Manipulation": _h_root_manipulation,
    "Echocasting Symposium": _h_echocasting_symposium,
    "Silverquill Charm": _h_silverquill_charm,
    "Grapple with Death": _h_grapple_with_death,
    "Ancestral Anger": _h_ancestral_anger,
    "Group Project": _h_group_project,
    "Homesickness": _h_homesickness,
    "Tome Blast": _h_tome_blast,
    "Quandrix Charm": _h_quandrix_charm,
    "Improvisation Capstone": _h_improvisation_capstone,
    "Withering Curse": _h_withering_curse,
}.items(): SPELL_EFFECTS.setdefault(_n,_f)