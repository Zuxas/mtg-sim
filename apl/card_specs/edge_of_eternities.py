"""Edge of Eternities — 19 cards (new Standard set)

Key mechanics: Landfall, Void (exile if kills creature), counters-matters,
Kicker, name-change artifacts (Meltstrider Resolve etc).

Spec: apl/card_specs/edge_of_eternities.py
"""
from __future__ import annotations
from data.card import Card, Tag
from engine.match_state import safe_power, safe_toughness

ANNUL                 = "Annul"
OUROBOROID            = "Ouroboroid"
COSMOGRAND_ZENITH     = "Cosmogrand Zenith"
SEAM_RIP              = "Seam Rip"
CONSULT_STAR_CHARTS   = "Consult the Star Charts"
ICETILL_EXPLORER      = "Icetill Explorer"
MELTSTRIDER_RESOLVE   = "Meltstrider's Resolve"
MIGHTFORM_HARMONIZER  = "Mightform Harmonizer"
GENE_POLLINATOR       = "Gene Pollinator"
TRAGIC_TRAJECTORY     = "Tragic Trajectory"
FULL_BORE             = "Full Bore"
HONOR                 = "Honor"
GENEMORPH_IMAGO       = "Genemorph Imago"
STARFIELD_SHEPHERD    = "Starfield Shepherd"
NOVA_HELLKITE         = "Nova Hellkite"
CRYOGEN_RELIC         = "Cryogen Relic"
EUMIDIAN              = "Eumidian Terrabotanist"
DAUNTLESS_SCRAPBOT    = "Dauntless Scrapbot"
ARCHENEMY_CHARM       = "Archenemy's Charm"

ALL_NAMES = {ANNUL, OUROBOROID, COSMOGRAND_ZENITH, SEAM_RIP,
             CONSULT_STAR_CHARTS, ICETILL_EXPLORER, MELTSTRIDER_RESOLVE,
             MIGHTFORM_HARMONIZER, GENE_POLLINATOR, TRAGIC_TRAJECTORY,
             FULL_BORE, HONOR, GENEMORPH_IMAGO, STARFIELD_SHEPHERD,
             NOVA_HELLKITE, CRYOGEN_RELIC, EUMIDIAN, DAUNTLESS_SCRAPBOT,
             ARCHENEMY_CHARM}


def cast(gs, card_name: str, opponent=None) -> bool:
    """Generic cast for Edge of Eternities cards. Returns True if cast."""
    for c in list(gs.zones.hand):
        if c.name != card_name:
            continue
        if not gs.mana_pool.can_cast(c.mana_cost, c.cmc):
            continue
        gs.cast_spell(c)
        _on_resolve(gs, card_name, c, opponent)
        return True
    return False


def _on_resolve(gs, name: str, card, opponent):
    if name == ANNUL and opponent:
        gs._log(f"  Annul: counter target artifact/enchantment spell")

    elif name == OUROBOROID:
        # Beginning of combat: put X +1/+1 counters on each creature
        # X = number of +1/+1 counters already on Ouroboroid
        ouro = next((c for c in gs.zones.battlefield if c.name == OUROBOROID), None)
        if ouro:
            x = getattr(ouro, 'counters', 0)
            ouro.counters += 1  # itself gets one too
            for cr in gs.zones.battlefield:
                if cr.has(Tag.CREATURE) and not cr.is_land() and cr is not ouro:
                    cr.counters = getattr(cr, 'counters', 0) + x
            gs._log(f"  Ouroboroid: put {x} +1/+1 counters on each creature")

    elif name == COSMOGRAND_ZENITH:
        # 2nd spell each turn: create two 1/1 tokens or draw
        gs._log(f"  Cosmogrand Zenith: ETB (2nd spell trigger: tokens or draw)")

    elif name == SEAM_RIP and opponent:
        targets = [c for c in opponent.zones.battlefield if not c.is_land()]
        if targets:
            t = max(targets, key=lambda c: getattr(c,'cmc',0))
            opponent.zones.battlefield.remove(t)
            opponent.zones.exile.append(t)
            gs._log(f"  Seam Rip: exile {t.name}")

    elif name == CONSULT_STAR_CHARTS:
        # Look at top 3, put 1 in hand; kicker = look at top 5, put 2
        drawn = min(2, len(gs.zones.library))
        for _ in range(drawn):
            if gs.zones.library:
                gs.zones.hand.append(gs.zones.library.pop(0))
        gs._log(f"  Consult the Star Charts: draw {drawn}")

    elif name == ICETILL_EXPLORER:
        # Can play additional land each turn; play lands from library
        gs._log(f"  Icetill Explorer: +1 land drop per turn")

    elif name == MIGHTFORM_HARMONIZER and opponent:
        # Landfall: double power of target creature
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            old = safe_power(t)
            t.power = str(old * 2)
            gs._log(f"  Mightform Harmonizer landfall: double {t.name} power {old}->{old*2}")

    elif name == GENE_POLLINATOR:
        gs._log(f"  Gene Pollinator: {T} tap permanent for any mana")

    elif name == TRAGIC_TRAJECTORY and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            t.counters = getattr(t,'counters',0) - 2
            if safe_toughness(t) + getattr(t,'counters',0) <= 0:
                opponent.zones.battlefield.remove(t)
                opponent.zones.exile.append(t)  # Void: exile if kills
                gs._log(f"  Tragic Trajectory: -2/-2 kills+exiles {t.name}")
            else:
                gs._log(f"  Tragic Trajectory: -2/-2 on {t.name}")

    elif name == FULL_BORE:
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            t.counters = getattr(t,'counters',0) + 3
            gs._log(f"  Full Bore: +3/+2 on {t.name}")

    elif name == HONOR:
        critters = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()]
        if critters:
            t = max(critters, key=lambda c: safe_power(c))
            t.counters = getattr(t,'counters',0) + 1
        gs.zones.draw(1)
        gs._log(f"  Honor: +1/+1 counter + draw 1")

    elif name == STARFIELD_SHEPHERD:
        # Search library for Plains
        plains = [c for c in gs.zones.library if c.is_land()
                  and 'Plains' in (getattr(c,'type_line','') or '')]
        if plains:
            gs.zones.library.remove(plains[0])
            gs.zones.battlefield.append(plains[0])
            gs._log(f"  Starfield Shepherd: fetch Plains")

    elif name == NOVA_HELLKITE and opponent:
        critters = [c for c in opponent.zones.battlefield
                    if c.has(Tag.CREATURE) and safe_toughness(c) <= 1]
        if critters:
            t = critters[0]
            opponent.zones.battlefield.remove(t)
            opponent.zones.graveyard.append(t)
            gs._log(f"  Nova Hellkite: 1 damage pings {t.name}")

    elif name == CRYOGEN_RELIC:
        gs.zones.draw(1)
        gs._log(f"  Cryogen Relic: draw 1 on ETB")

    elif name == EUMIDIAN:
        gs._log(f"  Eumidian Terrabotanist: landfall gain 1 life")

    elif name == DAUNTLESS_SCRAPBOT and opponent:
        # Exile each opponent's GY
        exiled = len(opponent.zones.graveyard)
        opponent.zones.exile.extend(opponent.zones.graveyard)
        opponent.zones.graveyard.clear()
        gs._log(f"  Dauntless Scrapbot: exile {exiled} cards from opp GY")


def ouroboroid_combat_trigger(gs) -> None:
    """Beginning of combat: each creature gets X +1/+1 counters where X = Ouroboroid's counters."""
    ouro = next((c for c in gs.zones.battlefield if c.name == OUROBOROID), None)
    if not ouro:
        return
    x = getattr(ouro, 'counters', 0)
    if x == 0:
        return
    for cr in gs.zones.battlefield:
        if cr.has(Tag.CREATURE) and not cr.is_land():
            cr.counters = getattr(cr,'counters',0) + x
    ouro.counters += 1  # Ouroboroid gains a counter too (self-reference)
    gs._log(f"  Ouroboroid combat: +{x} counters on all creatures, Ouroboroid now {ouro.counters}")
