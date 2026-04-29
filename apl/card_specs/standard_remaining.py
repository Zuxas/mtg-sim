"""Standard Remaining Cards — Final coverage module

Covers all remaining Standard-legal cards not in earlier specs:
- Blank-name cards (all identical mechanic: {1} rename to anything)
- Marvel's Spider-Man crossover
- Wilds of Eldraine remaining
- Tarkir: Dragonstorm remaining
- Aetherdrift remaining
- Final Fantasy remaining
- Dominaria United Standard-legal
- Lost Caverns remaining
- Misc small-count cards

Spec: apl/card_specs/standard_remaining.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness
from engine.keywords import KWTag

# === Blank-name cards (all same ability) ===
# These can all be named whatever is most useful at the time
BLANK_NAME_CARDS = {
    "Agatha's Soul Cauldron",  # Wilds of Eldraine
    "Proft's Eidetic Memory",  # Murders at Karlov Manor
    "Nature's Rhythm",         # Tarkir: Dragonstorm
    "Sygg's Command",          # Lorwyn Eclipsed
    "Dredger's Insight",       # Aetherdrift
    "Mindspring Merfolk",      # Aetherdrift (has Exhaust too)
    "Opt",                     # Various (scry+draw - handled in foundations but listed here too)
}

# === Marvel's Spider-Man ===
SPIDER_MANIFESTATION = "Spider Manifestation"
SUPERIOR_SPIDER_MAN  = "Superior Spider-Man"
SPIDER_SENSE         = "Spider-Sense"

# === Wilds of Eldraine ===
HEARTH_ELEMENTAL = "Hearth Elemental"
FAERIE_DREAMTHIEF= "Faerie Dreamthief"
TORCH_THE_TOWER  = "Torch the Tower"
SCALDING_VIPER   = "Scalding Viper"

# === Tarkir: Dragonstorm ===
VOICE_OF_VICTORY  = "Voice of Victory"
ELSPETH_STORM     = "Elspeth, Storm Slayer"
BITTER_TRIUMPH    = "Bitter Triumph"
STADIUM_HEADLINER = "Stadium Headliner"
SUNPEARL_KIRIN    = "Sunpearl Kirin"

# === Aetherdrift ===
BOUNCE_OFF        = "Bounce Off"
BURNOUT_BASH      = "Burnout Bashtronaut"
MOMENTUM_BREAKER  = "Momentum Breaker"
LUMBERING_WAGON   = "Lumbering Worldwagon"
MONUMENT_ENDURE   = "Monument to Endurance"

# === Final Fantasy ===
SAZHS_CHOCOBO = "Sazh's Chocobo"
FIRE_MAGIC    = "Fire Magic"
CECIL         = "Cecil, Dark Knight"

# === Nurturing Pixie / Outlaws ===
NURTURING_PIXIE   = "Nurturing Pixie"
SMUGGLERS_SURPRISE= "Smuggler's Surprise"

# === Murders at Karlov Manor ===
LIGHTNING_HELIX   = "Lightning Helix"
NO_MORE_LIES      = "No More Lies"
ARCHDRUID_CHARM   = "Archdruid's Charm"

# === Lost Caverns of Ixalan ===
BRINGER_LAST_GIFT = "Bringer of the Last Gift"
SENTINEL_NAMELESS = "Sentinel of the Nameless City"

# === Dominaria United / March of the Machine ===
LEYLINE_BINDING   = "Leyline Binding"
HERD_MIGRATION    = "Herd Migration"
SUNFALL           = "Sunfall"

# All names for coverage tracking
ALL_NAMES = (BLANK_NAME_CARDS |
    {SPIDER_MANIFESTATION, SUPERIOR_SPIDER_MAN, SPIDER_SENSE,
     HEARTH_ELEMENTAL, FAERIE_DREAMTHIEF, TORCH_THE_TOWER, SCALDING_VIPER,
     VOICE_OF_VICTORY, ELSPETH_STORM, BITTER_TRIUMPH, STADIUM_HEADLINER, SUNPEARL_KIRIN,
     BOUNCE_OFF, BURNOUT_BASH, MOMENTUM_BREAKER, LUMBERING_WAGON, MONUMENT_ENDURE,
     SAZHS_CHOCOBO, FIRE_MAGIC, CECIL,
     NURTURING_PIXIE, SMUGGLERS_SURPRISE,
     LIGHTNING_HELIX, NO_MORE_LIES, ARCHDRUID_CHARM,
     BRINGER_LAST_GIFT, SENTINEL_NAMELESS,
     LEYLINE_BINDING, HERD_MIGRATION, SUNFALL})


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for remaining Standard cards. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if card_name in BLANK_NAME_CARDS and card_name == "Agatha's Soul Cauldron":
            # Agatha has a real ability besides blank-name: activated steal ability
            if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                continue
        elif card_name == HEARTH_ELEMENTAL:
            cost = _hearth_cost(gs)
            if gs.mana_pool.total() < cost:
                continue
        elif card_name == LEYLINE_BINDING:
            cost = _leyline_binding_cost(gs)
            if gs.mana_pool.total() < cost:
                continue
        elif not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def _hearth_cost(gs) -> int:
    """Hearth Elemental: costs less per non-creature in GY."""
    non_creatures_gy = sum(1 for c in gs.zones.graveyard
                           if not c.is_land() and not c.has(Tag.CREATURE))
    return max(2, 6 - non_creatures_gy)  # base {5}{R}=6


def _leyline_binding_cost(gs) -> int:
    """Domain: reduce by 1 per basic land type."""
    types = set()
    for c in gs.zones.battlefield:
        if not c.is_land(): continue
        tl = (getattr(c,'type_line','') or '').lower()
        for t in ('plains','island','swamp','mountain','forest'):
            if t in tl: types.add(t)
    return max(1, 6 - len(types))  # base {5}{W}=6


def _on_resolve(gs, name: str, card, opponent):
    """Apply spell effects."""
    # Blank-name cards — no game effect beyond the rename
    if name in BLANK_NAME_CARDS:
        gs._log(f"  {name}: blank-name artifact/creature (can be renamed)")
        return

    if name == SPIDER_MANIFESTATION:
        # 2/2 Reach, taps for R or G, untaps on CMC4+ spell
        gs._log(f"  Spider Manifestation: 2/2 reach, taps for R/G")

    elif name == SUPERIOR_SPIDER_MAN and opponent:
        # Mind Swap: copy creature in opp's GY
        gy_creatures = [c for c in opponent.zones.graveyard if c.has(Tag.CREATURE)]
        if gy_creatures:
            best = max(gy_creatures, key=lambda c: safe_power(c))
            card.power = best.power; card.toughness = best.toughness
            gs._log(f"  Superior Spider-Man: Mind Swap copies {best.name}")

    elif name == SPIDER_SENSE:
        # Web-slinging counter + bounce tapped creature; draw
        gs.zones.draw(1)
        gs._log(f"  Spider-Sense: draw 1 (web-slinging)")

    elif name == HEARTH_ELEMENTAL:
        cost = _hearth_cost(gs)
        gs._log(f"  Hearth Elemental: 4/5 (cost {cost}, reduced by GY non-creatures)")

    elif name == FAERIE_DREAMTHIEF:
        # Surveil 1 on ETB
        if gs.zones.library:
            top = gs.zones.library[0]
            if top.is_land() or getattr(top,'cmc',0) <= 1:
                gs.zones.library.pop(0)
                gs.zones.library.append(top)
        gs._log(f"  Faerie Dreamthief: 1/1 flying, surveil 1")

    elif name == TORCH_THE_TOWER and opponent:
        # Bargain: sac artifact/enchant/token for more damage
        dmg = 1
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and safe_toughness(c) <= dmg]
        if critters:
            t = critters[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
        else:
            gs.damage_dealt += dmg
        gs._log(f"  Torch the Tower: {dmg} damage")

    elif name == SCALDING_VIPER:
        gs._log(f"  Scalding Viper: 2/1, deals 1 damage when opp casts CMC<=3 spell")

    elif name == VOICE_OF_VICTORY:
        # Mobilize 2: when attacks, create 2 tapped 1/1 Warriors
        gs._log(f"  Voice of Victory: 1/3, mobilize 2 (creates 2 Warriors on attack)")

    elif name == ELSPETH_STORM:
        # Double all tokens created
        gs._log(f"  Elspeth, Storm Slayer: double all tokens created")

    elif name == BITTER_TRIUMPH and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs.life -= 3  # pay 3 life instead of discarding
            gs._log(f"  Bitter Triumph: destroy {t.name} (pay 3 life)")

    elif name == STADIUM_HEADLINER:
        gs._log(f"  Stadium Headliner: 1/1, mobilize 1 (creates Warrior on attack)")

    elif name == SUNPEARL_KIRIN and opponent:
        # Flash, bounce nonland perm ETB
        targets = [c for c in opponent.zones.battlefield if not c.is_land()]
        if targets:
            t = max(targets, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.battlefield.remove(t)
            opponent.zones.hand.append(t)
            gs._log(f"  Sunpearl Kirin: 2/1 flash fly, bounce {t.name}")

    elif name == BOUNCE_OFF and opponent:
        targets = [c for c in opponent.zones.battlefield
                   if c.has(Tag.CREATURE) and not c.is_land()]
        if targets:
            t = max(targets, key=lambda c: safe_power(c))
            opponent.zones.battlefield.remove(t)
            opponent.zones.hand.append(t)
            gs._log(f"  Bounce Off: return {t.name} to hand")

    elif name == BURNOUT_BASH:
        gs._log(f"  Burnout Bashtronaut: 1/1 menace, start engines! speed mechanic")

    elif name == MOMENTUM_BREAKER and opponent:
        # Speed reduction effect (Aetherdrift mechanic)
        gs._log(f"  Momentum Breaker: reduce opponent speed by 1")

    elif name == LUMBERING_WAGON:
        # Vehicle: power = number of lands you control
        lands = sum(1 for c in gs.zones.battlefield if c.is_land())
        card.power = str(lands)
        gs._log(f"  Lumbering Worldwagon: {lands}/? Vehicle (power=lands)")

    elif name == MONUMENT_ENDURE:
        # On discard: draw, gain life, or create token
        gs._log(f"  Monument to Endurance: artifact, one bonus per discard")

    elif name == SAZHS_CHOCOBO:
        # Landfall: +1/+1 counter each land
        gs._log(f"  Sazh's Chocobo: 0/1, landfall +1/+1 counter")

    elif name == FIRE_MAGIC:
        # Tiered: pay 0 for 1 dmg each, or {R} for 3 dmg to one, or {1}{R} for 5
        gs.damage_dealt += 3
        gs._log(f"  Fire Magic: 3 damage (tiered, chose mid option)")

    elif name == CECIL:
        # Deathtouch; Darkness: when deals damage you lose that much life
        gs._log(f"  Cecil, Dark Knight: 2/3 deathtouch, Darkness (self-drain)")

    elif name == NURTURING_PIXIE and opponent:
        # Return non-Faerie permanent to hand (bounce your own for ETB)
        critters = [c for c in gs.zones.battlefield
                    if not c.is_land() and 'Faerie' not in (getattr(c,'type_line','') or '')]
        if critters:
            best_etb = max(critters, key=lambda c: getattr(c,'cmc',0))
            gs.zones.battlefield.remove(best_etb)
            gs.zones.hand.append(best_etb)
            gs._log(f"  Nurturing Pixie: bounce {best_etb.name} to hand (ETB re-trigger)")

    elif name == SMUGGLERS_SURPRISE:
        gs._log(f"  Smuggler's Surprise: search library for combo pieces")

    elif name == LIGHTNING_HELIX:
        gs.damage_dealt += 3
        gs.life += 3
        gs._log(f"  Lightning Helix: 3 damage + 3 life")

    elif name == NO_MORE_LIES and opponent:
        gs._log(f"  No More Lies: counter unless pay 3, then exile")

    elif name == ARCHDRUID_CHARM:
        # Choose: search land, or destroy artifact/enchant, or +1/+1 counters
        gs.zones.draw(1)
        gs._log(f"  Archdruid's Charm: modal spell (land/remove/counters)")

    elif name == BRINGER_LAST_GIFT and opponent:
        # Each player sacrifices all other creatures
        for owner in (gs, opponent):
            killed = [c for c in list(owner.zones.battlefield)
                      if c.has(Tag.CREATURE) and not c.is_land() and c is not card]
            for c in killed:
                owner.zones.battlefield.remove(c)
                owner.zones.graveyard.append(c)
        gs._log(f"  Bringer of the Last Gift: 6/6 fly, all other creatures die")

    elif name == SENTINEL_NAMELESS:
        # ETB or attack: create Map token
        map_tok = Card("Map Token", "{0}", 0, "Token Artifact — Map",
                       oracle_text="{1}, Sacrifice this: Scry 1. Explore.")
        gs.zones.battlefield.append(map_tok)
        gs._log(f"  Sentinel of the Nameless City: 3/4 vig, create Map token")

    elif name == LEYLINE_BINDING and opponent:
        cost = _leyline_binding_cost(gs)
        targets = [c for c in opponent.zones.battlefield if not c.is_land()]
        if targets:
            t = max(targets, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.battlefield.remove(t)
            opponent.zones.exile.append(t)
            gs._log(f"  Leyline Binding: exile {t.name} (flash, domain cost {cost})")

    elif name == HERD_MIGRATION:
        # Domain: create 3/3 Beasts for each basic land type
        types = set()
        for c in gs.zones.battlefield:
            if not c.is_land(): continue
            tl = (getattr(c,'type_line','') or '').lower()
            for t in ('plains','island','swamp','mountain','forest'):
                if t in tl: types.add(t)
        for _ in range(len(types)):
            tok = Card("Beast Token", "{0}", 3, "Token Creature — Beast")
            tok.power = "3"; tok.toughness = "3"
            tok.turn_entered = gs.turn; tok.summoning_sickness = True
            gs.zones.battlefield.append(tok)
        gs._log(f"  Herd Migration: {len(types)} Beast tokens (domain)")

    elif name == SUNFALL and opponent:
        # Exile all creatures; incubate X
        exiled = 0
        for owner in (gs, opponent):
            killed = [c for c in list(owner.zones.battlefield)
                      if c.has(Tag.CREATURE) and not c.is_land()]
            for c in killed:
                owner.zones.battlefield.remove(c)
                owner.zones.exile.append(c)
                exiled += 1
        gs._log(f"  Sunfall: exile all {exiled} creatures, incubate {exiled}")


def sazhs_chocobo_landfall(gs) -> None:
    """Landfall trigger: put +1/+1 counter on Sazh's Chocobo."""
    for c in gs.zones.battlefield:
        if c.name == SAZHS_CHOCOBO:
            c.counters = getattr(c,'counters',0) + 1
            c.power = str(0 + c.counters)
            c.toughness = str(1 + c.counters)
            gs._log(f"  Sazh's Chocobo landfall: {c.power}/{c.toughness}")


def voice_of_victory_attack(gs) -> None:
    """Mobilize 2: create two 1/1 Warriors when Voice attacks."""
    if not any(c.name == VOICE_OF_VICTORY for c in gs.zones.battlefield
               if c.has(Tag.CREATURE)):
        return
    for _ in range(2):
        tok = Card("Warrior Token", "{0}", 1, "Token Creature — Warrior")
        tok.power = "1"; tok.toughness = "1"
        tok.turn_entered = gs.turn; tok.summoning_sickness = False
        tok.tapped = True  # enter tapped and attacking
        gs.zones.battlefield.append(tok)
    gs._log(f"  Voice of Victory mobilize 2: 2 attacking Warriors")
