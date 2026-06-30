"""
apl/yawgmoth_match.py — Yawgmoth, Thran Physician APL (Modern)

Combo engine:
  Yawgmoth + 2 undying creatures + Blood Artist/Zulaport = infinite drain kill.
  Loop: sac undying creature A → dies → Blood Artist drains → undying returns with +1/+1
        → Yawgmoth puts -1/-1 on creature B (cancels B's +1/+1) → sac B → repeat.
  Each Yawgmoth activation: pay 1 life + gain 1 (Blood Artist) = net 0.
  Opponent loses 1 per death × infinite = game over.

Oracle-verified (Scryfall 2026-04-30):
  Yawgmoth: "Pay 1 life, Sacrifice another creature: Put a -1/-1 counter on up to one
             target creature and draw a card. Activate only as a sorcery."
  Blood Artist: "Whenever this creature or another creature dies, target player loses 1
                 life and you gain 1 life."
  Zulaport Cutthroat: "Whenever this creature or another creature you control dies, each
                        opponent loses 1 life and you gain 1 life."
  Geralf's Messenger ETB: "When this creature enters, target opponent loses 2 life."
  Collected Company: "Look at top 6. Put up to 2 creatures with MV ≤ 3 onto battlefield."
  Eldritch Evolution: "Sac a creature. Tutor creature with MV ≤ sacced MV + 2."
"""
from apl.match_apl import MatchAPL
from data.card import Tag
from engine.match_state import safe_power, safe_toughness

YAWGMOTH = "Yawgmoth, Thran Physician"
MELIRA = "Melira, Sylvok Outcast"
BLOOD_ARTIST = "Blood Artist"
ZULAPORT = "Zulaport Cutthroat"
YOUNG_WOLF = "Young Wolf"
STRANGLEROOT = "Strangleroot Geist"
GERALFS_MESSENGER = "Geralf's Messenger"
RENATA = "Renata, Called to the Hunt"
CoCo = "Collected Company"
CHORD = "Chord of Calling"
GSZ = "Green Sun's Zenith"
ELDRITCH = "Eldritch Evolution"
# Cauldron-variant additions (2026 canonical build)
CAULDRON = "Agatha's Soul Cauldron"
BALLISTA = "Walking Ballista"
BADGERMOLE = "Badgermole Cub"
HALFLING = "Delighted Halfling"
MALEVOLENT = "Malevolent Rumble"
GRIST = "Grist, the Hunger Tide"
FORMIDABLE = "Formidable Speaker"
ENDURANCE = "Endurance"

# ---------------------------------------------------------------------------
# DECK-VARIANT ALIGNMENT (2026-06-30, combo-interaction handoff #2).
# decks/yawgmoth_modern.txt is the Golgari "Agatha's Soul Cauldron / Walking
# Ballista" build (xerk, MTGO Modern Challenge 2026-04-29). It runs ZERO
# Blood Artist / Zulaport Cutthroat / Geralf's Messenger -- the old DRAINS /
# UNDYING constants pointed at cards the list does not contain, so the combo
# checker's `drain_on_board` was ALWAYS False and the combo fired 0/50.
#   * UNDYING bodies in THIS list: Young Wolf (4) + Strangleroot Geist (1).
#   * DRAIN payoff in THIS list: NONE. The kill is Agatha's Soul Cauldron
#     exiling Walking Ballista from the graveyard, granting the "remove a
#     +1/+1 counter: deal 1 damage" ability to the undying creatures (which
#     carry +1/+1 counters from undying returns). The Yawgmoth sac-loop feeds
#     unbounded +1/+1 counters -> unbounded face pings = lethal.
# ---------------------------------------------------------------------------
UNDYING = {YOUNG_WOLF, STRANGLEROOT}
DRAINS = set()  # this build runs no Blood Artist / Zulaport (drain payoff absent)
TUTORS = {CoCo, CHORD, GSZ, ELDRITCH}


class YawgmothMatchAPL(MatchAPL):
    # combo-interaction handoff #2 (Component 2 + Component 3 yawgmoth cell):
    # the Cauldron/Ballista kill is DIRECT DAMAGE (the granted Ballista pings hit
    # the face). A scalar `opponent.life -= X` write is a no-op on the match life
    # total (spec spine #3 -- opp_view.life is a throwaway that is never synced back
    # for the non-active seat). So the combo damage is routed through the ACTIVE
    # player's `gs.damage_dealt`, which `_simple_play_turn` propagates to the match
    # life total ONLY when the active APL sets WANTS_STORM or WANTS_BURN. We opt in
    # via WANTS_BURN, mirroring MonoRedMatchAPL.
    WANTS_BURN = True
    name = "Yawgmoth"
    win_condition_damage = 20
    max_turns = 12

    # Class-level instrumentation: counts combo assemblies across a run_match_set
    # (run_match_set builds a FRESH instance per game, so an instance counter would
    # not aggregate). Reset by the measurement harness before a sweep.
    _combo_fires = 0

    def __init__(self):
        self._combo_fired = False

    def keep(self, hand, mulligans, on_play):
        if len(hand) <= 4: return True
        lands = sum(1 for c in hand if c.is_land())
        has_yawg = any(c.name == YAWGMOTH for c in hand)
        has_undying = sum(1 for c in hand if c.name in UNDYING)
        has_drain = any(c.name in DRAINS for c in hand)
        has_tutor = any(c.name in TUTORS for c in hand)
        if lands == 0: return False
        if lands > 5: return False
        if has_yawg and has_undying >= 1 and lands >= 2: return True
        if has_drain and has_undying >= 1 and lands >= 2: return True
        if has_tutor and lands >= 2: return True
        return mulligans >= 2

    def bottom(self, hand, n):
        lands = sorted([c for c in hand if c.is_land()], key=lambda c: c.name)
        spells = sorted([c for c in hand if not c.is_land()],
                        key=lambda c: -getattr(c, 'cmc', 0))
        return (lands[4:] + spells)[:n]

    def main_phase(self, gs): self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        self._play_land_if_able(gs)
        gs.tap_lands()

        # 1. Collected Company ({3}{G}) — put 2 creatures with MV ≤ 3 onto battlefield
        # Oracle: "Look at top 6. Put up to 2 creatures with mana value 3 or less onto
        #          the battlefield."
        for c in list(gs.zones.hand):
            if c.name == CoCo and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                deployed = 0
                for lib_card in list(gs.zones.library[:6]):
                    if lib_card.has(Tag.CREATURE) and getattr(lib_card, 'cmc', 0) <= 3:
                        gs.zones.library.remove(lib_card)
                        gs.zones.battlefield.append(lib_card)
                        lib_card.turn_entered = gs.turn
                        lib_card.summoning_sickness = True
                        self._trigger_etb(gs, opponent, lib_card)
                        deployed += 1
                        if deployed >= 2: break
                gs._log(f"  CoCo: {deployed} creatures onto battlefield")
                break

        # 2. Eldritch Evolution ({1}{G}{G}) — sac creature, tutor higher CMC creature
        # Oracle: "As an additional cost, sacrifice a creature. Search for creature
        #          with MV ≤ sacced MV + 2, put onto battlefield."
        for c in list(gs.zones.hand):
            if c.name == ELDRITCH and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                sac_pool = [x for x in gs.zones.battlefield
                            if x.has(Tag.CREATURE) and not x.is_land()
                            and x.name not in {YAWGMOTH, BLOOD_ARTIST, ZULAPORT}]
                if sac_pool:
                    sac_target = min(sac_pool, key=lambda x: getattr(x, 'cmc', 0))
                    sac_mv = getattr(sac_target, 'cmc', 0)
                    search_mv = sac_mv + 2
                    # Find best candidate: prioritize Yawgmoth > drain > high cmc
                    def priority(x):
                        if x.name == YAWGMOTH: return 100
                        if x.name in DRAINS: return 50
                        return getattr(x, 'cmc', 0)
                    candidates = [x for x in gs.zones.library
                                  if x.has(Tag.CREATURE)
                                  and getattr(x, 'cmc', 0) <= search_mv]
                    if candidates:
                        gs.cast_spell(c)
                        gs.zones.battlefield.remove(sac_target)
                        gs.zones.graveyard.append(sac_target)
                        tutor_target = max(candidates, key=priority)
                        gs.zones.library.remove(tutor_target)
                        gs.zones.battlefield.append(tutor_target)
                        tutor_target.turn_entered = gs.turn
                        tutor_target.summoning_sickness = True
                        self._trigger_etb(gs, opponent, tutor_target)
                        gs._log(f"  Eldritch Evolution: sac {sac_target.name}, "
                                f"tutor {tutor_target.name}")
                break

        # 2b. Malevolent Rumble ({1}{G}) — reveal top 4, put permanent into hand
        # Oracle: "Reveal top 4, put a permanent card into hand, rest to GY."
        for c in list(gs.zones.hand):
            if c.name == MALEVOLENT and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                gs.cast_spell(c)
                top4 = gs.zones.library[:4]
                permanents = [x for x in top4 if x.has(Tag.CREATURE) or x.has(Tag.ARTIFACT)]
                if permanents:
                    best = max(permanents, key=lambda x: getattr(x, 'cmc', 0))
                    gs.zones.library.remove(best)
                    gs.zones.hand.append(best)
                    for card in top4:
                        if card in gs.zones.library and card != best:
                            gs.zones.library.remove(card)
                            gs.zones.graveyard.append(card)
                gs._log(f"  Malevolent Rumble: tutor from top 4")
                break

        # 3. Deploy threats. Order = mana dork -> undying bodies -> engine pieces
        # -> payoff. Only cards ACTUALLY in decks/yawgmoth_modern.txt (the
        # Cauldron/Ballista build); the old list named Blood Artist / Zulaport /
        # Geralf's Messenger / Melira / Renata, none of which this variant runs.
        deploy_order = [HALFLING, YOUNG_WOLF, STRANGLEROOT, BADGERMOLE,
                        FORMIDABLE, ENDURANCE, YAWGMOTH, CAULDRON, BALLISTA]
        for name in deploy_order:
            for c in list(gs.zones.hand):
                if c.name == name and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                    gs.cast_spell(c)
                    self._trigger_etb(gs, opponent, c)
                    break

        # 4. Removal on opponent creatures
        if opponent:
            opp_cr = [c for c in opponent.zones.battlefield
                      if not c.is_land() and c.has(Tag.CREATURE) and safe_power(c) >= 3]
            if opp_cr:
                target = max(opp_cr, key=lambda x: safe_power(x))
                for c in list(gs.zones.hand):
                    if not c.is_land() and not c.has(Tag.CREATURE):
                        if gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                            if safe_toughness(target) <= 3:
                                gs.mana_pool.pay(c.mana_cost, c.cmc)
                                gs.zones.hand.remove(c)
                                gs.zones.graveyard.append(c)
                                if target in opponent.zones.battlefield:
                                    opponent.zones.battlefield.remove(target)
                                    opponent.zones.graveyard.append(target)
                                gs._log(f"  Remove: {target.name}")
                                break

        # 5. Walking Ballista direct damage
        # Oracle: "Remove a +1/+1 counter: Deal 1 damage to any target."
        if opponent:
            for c in list(gs.zones.battlefield):
                if c.name == BALLISTA:
                    try:
                        counters = int(c.power)
                    except (ValueError, TypeError):
                        counters = 0
                    if counters >= 2:
                        dmg = min(counters, max(0, opponent.life))
                        # Direct damage -> route via gs.damage_dealt so WANTS_BURN
                        # propagates it to the match life total (a scalar
                        # opponent.life write is dropped; spec spine #3).
                        gs.damage_dealt += dmg
                        c.power = str(counters - dmg)
                        c.toughness = str(counters - dmg)
                        gs._log(f"  Walking Ballista: {dmg} direct damage")
                        if counters - dmg <= 0:
                            gs.zones.battlefield.remove(c)
                            gs.zones.graveyard.append(c)

        # 6. Check for combo kill
        if not self._combo_fired and opponent:
            self._check_combo_kill(gs, opponent)

        # 7. Non-combo Yawgmoth activation: sac weakest creature → draw + remove counter
        if not self._combo_fired and opponent:
            self._activate_yawgmoth(gs, opponent)

        # 7. Fill curve
        for c in list(gs.zones.hand):
            if c.has(Tag.CREATURE) and gs.mana_pool.can_cast(c.mana_cost, c.cmc):
                if gs.cast_spell(c):
                    self._trigger_etb(gs, opponent, c)

    def _trigger_etb(self, gs, opponent, card):
        """Fire ETB triggers for key Yawgmoth deck cards."""
        if card.name == GERALFS_MESSENGER:
            # Oracle: "This creature enters tapped. When enters, target opponent loses 2 life."
            card.summoning_sickness = True
            card.tapped = True
            if opponent:
                opponent.life -= 2
                gs._log(f"  Geralf's Messenger ETB: opponent -2 life")

    def _check_combo_kill(self, gs, opponent):
        """Detect and fire the Agatha's Soul Cauldron / Walking Ballista infinite.

        ASSEMBLY (the actual decks/yawgmoth_modern.txt kill -- NO Blood Artist):
          Yawgmoth on board
          + >= 2 undying bodies on board (Young Wolf / Strangleroot Geist; their
            undying returns carry +1/+1 counters)
          + Agatha's Soul Cauldron on board
          + Walking Ballista reachable (on the battlefield OR in the graveyard for
            Cauldron to exile).
        Mechanism: Cauldron exiling Ballista grants every +1/+1-countered creature
        Ballista's "remove a +1/+1 counter: deal 1 damage". The Yawgmoth sac-loop
        (sac undying A -> returns with +1/+1; -1/-1 on B to reset) produces UNBOUNDED
        +1/+1 counters, hence unbounded face pings -> lethal.

        DAMAGE CHANNEL: the pings are direct damage. They are routed through
        gs.damage_dealt (NOT a scalar opponent.life write, which is dropped --
        spec spine #3); WANTS_BURN propagates gs.damage_dealt to the match life
        total. Dealing >= 20 (or opp's current life) models the unbounded loop and
        is lethal via the `gs.damage_to_a >= 20` / `gs.life_a <= 0` match check.
        """
        yawg = any(c.name == YAWGMOTH for c in gs.zones.battlefield)
        if not yawg:
            return
        undying_on_board = [c for c in gs.zones.battlefield if c.name in UNDYING]
        if len(undying_on_board) < 2:
            return
        cauldron = any(c.name == CAULDRON for c in gs.zones.battlefield)
        if not cauldron:
            return
        # Ballista must be exilable by Cauldron: in a graveyard, or on the
        # battlefield (sacrificable into the yard via the Yawgmoth engine).
        ballista_reachable = any(
            c.name == BALLISTA
            for c in list(gs.zones.battlefield) + list(gs.zones.graveyard))
        if not ballista_reachable:
            return

        opp_life = opponent.life if opponent else 20
        dmg = max(20, opp_life)          # unbounded loop -> lethal
        gs.damage_dealt += dmg
        self._combo_fired = True
        type(self)._combo_fires += 1
        gs._log(f"  YAWGMOTH CAULDRON/BALLISTA COMBO: "
                f"{undying_on_board[0].name} + {undying_on_board[1].name} + Cauldron "
                f"+ Ballista = {dmg} face (routed via damage_dealt)")

    def _activate_yawgmoth(self, gs, opponent):
        """Yawgmoth non-combo: pay 1 life, sac creature → draw + remove counter.
        Only activate if we have a real sac target (not our engines) and something useful
        to do with the -1/-1 counter.
        """
        yawg = any(c.name == YAWGMOTH for c in gs.zones.battlefield)
        if not yawg: return
        # Only activate if opponent has a threatening creature we can weaken
        opp_cr = [c for c in (opponent.zones.battlefield if opponent else [])
                  if not c.is_land() and c.has(Tag.CREATURE)]
        if not opp_cr: return
        sac_fodder = [c for c in gs.zones.battlefield
                      if c.has(Tag.CREATURE) and not c.is_land()
                      and c.name not in {YAWGMOTH, BLOOD_ARTIST, ZULAPORT, MELIRA}
                      and not c.name in UNDYING]  # save undying creatures for combo
        if not sac_fodder: return
        sac = min(sac_fodder, key=lambda c: safe_power(c))
        target = max(opp_cr, key=lambda c: safe_power(c))
        if gs.life > 3:  # don't activate when at low life
            gs.life -= 1
            gs.zones.battlefield.remove(sac)
            gs.zones.graveyard.append(sac)
            # Death trigger (Blood Artist if on board)
            if any(c.name in DRAINS for c in gs.zones.battlefield) and opponent:
                opponent.life -= 1; gs.life += 1
            # Put -1/-1 counter on opponent's creature (weakens it)
            try:
                target.power = str(max(0, int(target.power) - 1))
                target.toughness = str(max(0, int(target.toughness) - 1))
                if int(target.toughness) <= 0 and target in opponent.zones.battlefield:
                    opponent.zones.battlefield.remove(target)
                    opponent.zones.graveyard.append(target)
            except (ValueError, TypeError):
                pass
            gs.zones.draw(1)  # Yawgmoth draws a card
            gs._log(f"  Yawgmoth activation: sac {sac.name}, -1/-1 on {target.name}, draw")

    def declare_attackers(self, gs, opponent):
        return [c for c in gs.zones.battlefield
                if not c.is_land() and c.has(Tag.CREATURE)
                and not getattr(c, 'summoning_sickness', False)
                and not getattr(c, 'tapped', False)]

    def declare_blockers(self, gs, opp, attackers):
        assignments = {}
        if not attackers: return assignments
        blockers = [c for c in gs.zones.battlefield
                    if c.has(Tag.CREATURE) and not c.is_land()
                    and safe_toughness(c) >= 3
                    and not getattr(c, 'tapped', False)]
        if blockers:
            biggest = max(attackers, key=lambda c: safe_power(c))
            if safe_power(biggest) >= 3:
                assignments[id(biggest)] = [blockers[0]]
        return assignments

    def end_step_actions(self, gs, opponent):
        """Undying: return Young Wolf and Geralf's Messenger from GY."""
        for card in list(gs.zones.graveyard):
            if card.name in UNDYING and not getattr(card, '_had_plus1_counter', False):
                gs.zones.graveyard.remove(card)
                gs.zones.battlefield.append(card)
                card.turn_entered = gs.turn
                card.summoning_sickness = True
                card._had_plus1_counter = True
                try:
                    card.power = str(int(card.power) + 1)
                    card.toughness = str(int(card.toughness) + 1)
                except (ValueError, TypeError):
                    pass
                # Blood Artist drain on death triggered before return
                if any(c.name in DRAINS for c in gs.zones.battlefield) and opponent:
                    opponent.life -= 1; gs.life += 1
                gs._log(f"  Undying: {card.name} returns to battlefield (+1/+1)")

    def respond_to_spell(self, gs, opponent, spell): return None

    def _play_land_if_able(self, gs):
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands or gs.land_played: return
        def score(c):
            n = (c.name or '').lower()
            if any(x in n for x in ('mesa', 'strand', 'delta', 'tarn', 'foothills',
                                     'flats', 'rainforest', 'catacombs', 'heath', 'mire')):
                return 0
            if any(x in n for x in ('foundry', 'vents', 'garden', 'grave', 'shrine',
                                     'fountain', 'crypt')):
                return 1
            return 3
        gs.play_land(min(lands, key=score))
