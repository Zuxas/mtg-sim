"""
apl/urzatron_modern_match.py -- Hand-written Mono-Green Tron (Urzatron) MatchAPL (Modern)

DECK IDENTITY (June 2026, post-ban arc): the meta cell still called
"Mono-Green Tron" / "Urzatron" (5.2% of Modern) is the COLORLESS
Karn/Kozilek's Command build -- mtg_meta.db shows ZERO June-2026 lists with
Sylvan Scrying / Chromatic eggs / Wurmcoil. Deck file
decks/urzatron_modern.txt is the modal 60+15 from 5 top June finishes
(Argjent Kurtaj RCQ 1st 06-29, Jumba Challenge-64 3rd 06-29 + 2nd 06-25,
Samcaster-Mage Challenge-64 3rd 06-20, Derek Mccormack RCQ 4th 06-28).
Tracked SEPARATELY from the eldrazitron cell (shells converged in the data,
meta sites list both archetypes).

Playbook engines:
A. Tron Assembly -- land sequencing completes Tower+Mine+Plant; Expedition
   Map is cast early and later activated ({2}, sac) to pull the missing
   piece FROM THE LIBRARY into hand (real tutor, not a draw-1 proxy).
B. Big-mana payoff ladder -- posture-aware: against a developed board,
   All Is Dust / Ugin wipe first; against low-board (combo/control
   posture), Ugin -> Devourer -> Sire pressure first. Ulamog at 10.
C. Grind mode when Tron is disrupted/missing -- Eldrazi Temple + Mind
   Stone + Ugin's Labyrinth still produce 5-7 mana by T4-5; TKS +
   Fleshraker + Kozilek's Command play a fair big-mana midrange game.

ENGINE BOUNDARY (PROACTIVE deck -- honest limits, do NOT trust these seams):
- No reactive interaction is faked: this APL never counters, never acts on
  the opponent's turn (beyond the oracle-faithful TKS leave-trigger). The
  real deck is also ~90% proactive, so the boundary is small here.
- Karn, the Great Creator: the -2 wishboard fetch is proxied as draw-1
  (house pattern, cf. eldrazi_tron_match). The +1 artifact-hate static and
  the 15-card wishboard toolbox are UNMODELED -> we undervalue Karn vs
  artifact decks (Affinity) and in grindy sideboard games.
- Chalice of the Void / (SB) Trinisphere / Ensnaring Bridge: prison locks
  are UNMODELED. Chalice is cast only as last-priority filler; it never
  locks anyone out -> we undervalue it vs Belcher/Prowess-class decks.
- Glaring Fleshraker: approximated as 1 face damage per colorless spell
  cast while it is on the battlefield (routed through gs.damage_dealt +
  WANTS_BURN, the sanctioned mp1 channel); +1/+1 counters/Spawn tokens not
  modeled.
- Ugin's Labyrinth imprint: the exiled 7+ card is a REAL card loss from
  hand (faithful), +1 mana while imprinted.

CALIBRATION (MEASURED 2026-07-02, n=500/pairing, seed=42, PYTHONHASHSEED=0,
run_match_set mix_play_draw=True; anchors = mtg_meta.db matchup_matrix
fetched 2026-04-24 -- STALE/pre-ban, Eldrazi Tron rows used because the
April "Urzatron" cell had already converged to this shell and the matches
table has no June-2026 Modern rounds; Wilson bands via engine.stats_util):
  vs Boros Energy  sim 56.4% [52.0-60.7]  anchor 42% [34.8-49.6] (n=168) -> +14.4pp INFLATED
  vs Affinity      sim 58.4% [54.0-62.6]  anchor 38% [29.7-47.1] (n=116) -> +20.4pp INFLATED
  vs Amulet Titan  sim 85.6% [82.3-88.4]  anchor 19% [13.0-27.0] (n=119) -> +66.6pp INFLATED/INVERTED
ALL THREE cells diverge > +10pp. They were NOT tuned toward the anchors
(forbidden); flagged in mismodeled_matchups.py ("urzatron"). Attribution is
the KNOWN engine classes, not this APL's own sequencing:
  (a) opponent LAND HATE is unmodeled (Boseiju/Ghost Quarter/Demolition
      Field-class Tron-land destruction is the spine of every real anti-Tron
      plan; in-sim our Tron always survives) -- inflates all three cells;
  (b) Amulet's combo under-kills in the played-out cell (best-covered combo
      APL, still slower than a goldfish-fast big-mana deck; anchor says we
      are a 19% DOG, sim says 86% favored -> INVERTED, worst cell);
  (c) Affinity's Saga/Construct engine develops in only ~24% of games (known
      INFLATED cell class, see "izzet affinity" flag).
Goldfish (n=1000, seed=42, mixed play/draw): Tron assembled by T3 in 39.9% /
by T4 in 55.2% of games (median T3 among the 73.9% that ever assemble);
first big payoff (Karn/Ugin/7-drop) on battlefield median T4 (80.0% by T4,
Labyrinth+Temple T2 Karn in 4.0%); goldfish kill median T6 (fastest T4,
98.1% of games closed by the T12 horizon). Matches paper Tron's realistic
T3-4 assembly / T3-4 first-threat clock.
"""
from typing import Optional

from data.card import Card, Tag
from engine.game_state import GameState
from apl.match_apl import MatchAPL
from engine.match_state import safe_power, safe_toughness

TOWER      = "Urza's Tower"
MINE       = "Urza's Mine"
PLANT      = "Urza's Power Plant"
TEMPLE     = "Eldrazi Temple"
LABYRINTH  = "Ugin's Labyrinth"
EXP_MAP    = "Expedition Map"
MIND_STONE = "Mind Stone"
KOZ_CMD    = "Kozilek's Command"
KARN       = "Karn, the Great Creator"
TKS        = "Thought-Knot Seer"
UGIN       = "Ugin, Eye of the Storms"
DEVOURER   = "Devourer of Destiny"
FLESHRAKER = "Glaring Fleshraker"
SIRE       = "Sire of Seven Deaths"
CHALICE    = "Chalice of the Void"
DISMEMBER  = "Dismember"
ALL_IS_DUST= "All Is Dust"
ULAMOG     = "Ulamog, the Ceaseless Hunger"

TRON_PIECES = {TOWER, MINE, PLANT}
BIG_PAYOFFS = {UGIN, DEVOURER, SIRE, ULAMOG, ALL_IS_DUST}
PAYOFFS     = BIG_PAYOFFS | {KARN, TKS}


class UrzatronMatchAPL(MatchAPL):
    name = "Mono-Green Tron (Urzatron)"
    win_condition_damage = 20
    max_turns = 12
    ARCHETYPE = "ramp"

    # Fleshraker face pings are mp1 direct damage -> route through the
    # sanctioned gs.damage_dealt + WANTS_BURN sync (combo-spine #2 Site 1).
    WANTS_BURN = True

    # Karn + Ugin are the deck's engine walkers -- opt into R5 loyalty
    # (same gate + policy as EldraziTronMatchAPL, design 1.5).
    WANTS_PW_LOYALTY = True

    def choose_pw_ability(self, pw, gs, opp_gs) -> int:
        """Karn/Ugin loyalty policy: fire the ultimate as soon as it is
        affordable, else tick up (grindy ramp deck banks loyalty).
        Zero-RNG, deterministic. Mirrors the eldrazi_tron policy."""
        from engine.planeswalkers import (PLANESWALKER_ABILITIES,
                                          PLANESWALKER_ULTIMATES)
        abilities = PLANESWALKER_ABILITIES.get(getattr(pw, "name", ""), {})
        if not abilities:
            return 0
        loyalty = getattr(pw, "loyalty", 0) or 0
        ult = PLANESWALKER_ULTIMATES.get(getattr(pw, "name", ""))
        if ult is not None and loyalty + ult >= 0:
            return ult
        plus = [c for c in abilities if c > 0]
        if plus:
            return max(plus)
        affordable = [c for c in abilities if loyalty + c >= 0]
        return max(affordable) if affordable else 0

    def __init__(self):
        self._karn_wishes_used = 0
        self._tks_on_board_last_turn = 0

    # ── board arithmetic ────────────────────────────────────────────────

    def _tron_pieces_on_bf(self, gs) -> set:
        return {c.name for c in gs.zones.battlefield if c.name in TRON_PIECES}

    def _tron_online(self, gs) -> bool:
        return len(self._tron_pieces_on_bf(gs)) == 3

    def _big_mana_bonus(self, gs) -> int:
        """Extra mana beyond 1-per-land: Tron online +4 (3 lands -> 7),
        Eldrazi Temple +1 each (every spell we play is colorless Eldrazi-or-
        artifact; house approximation shared with eldrazi_tron_match),
        Ugin's Labyrinth +1 each while a 7+ card is imprinted,
        Mind Stone +1 each."""
        bonus = 4 if self._tron_online(gs) else 0
        imprinted = any(getattr(x, "cmc", 0) >= 7 for x in gs.zones.exile)
        for c in gs.zones.battlefield:
            n = c.name or ""
            if n == TEMPLE:
                bonus += 1
            elif n == LABYRINTH and imprinted:
                bonus += 1
            elif n == MIND_STONE:
                bonus += 1
        return bonus

    # ── mulligan ────────────────────────────────────────────────────────

    def keep(self, hand, mulligans, on_play) -> bool:
        """Tron-assembly keep rules, in priority order:
        A. natural Tron (all 3 pieces) -- snap keep;
        B. 2 distinct pieces + a route to the 3rd or something to do with
           the mana (Map / payoff / Mind Stone);
        C. Expedition Map + 2 lands + a payoff (Map assembles from 1 piece);
        D. Temple big-mana fallback (T3 TKS beats) with a payoff.
        No-land and 6-land hands ship. At 2+ mulligans keep anything sane."""
        if len(hand) <= 4:
            return True
        n_lands = sum(1 for c in hand if c.is_land())
        tron    = len({c.name for c in hand if c.name in TRON_PIECES})
        maps    = sum(1 for c in hand if c.name == EXP_MAP)
        stones  = sum(1 for c in hand if c.name == MIND_STONE)
        payoffs = sum(1 for c in hand if c.name in PAYOFFS)
        temples = sum(1 for c in hand if c.name == TEMPLE)
        if n_lands == 0 or n_lands >= 6:
            return mulligans >= 2
        if tron == 3:
            return True                                   # A
        if tron >= 2 and (maps or payoffs or stones):
            return True                                   # B
        if maps >= 1 and n_lands >= 2 and (payoffs or tron):
            return True                                   # C
        if temples >= 1 and n_lands >= 3 and payoffs:
            return True                                   # D
        return mulligans >= 2

    def bottom(self, hand, n) -> list:
        """Bottom duplicate big payoffs first (one 7-drop is plenty on a
        mull), then excess non-Tron lands, then cheap spells. Never bottom
        a Tron piece we don't already hold or an Expedition Map."""
        keep_names = set()
        pool = []
        # rank lands: distinct tron pieces / Temple / Labyrinth are precious
        lands  = [c for c in hand if c.is_land()]
        spells = [c for c in hand if not c.is_land()]
        seen_tron = set()
        precious, spare_lands = [], []
        for c in lands:
            if c.name in TRON_PIECES and c.name not in seen_tron:
                seen_tron.add(c.name); precious.append(c)
            elif c.name in (TEMPLE, LABYRINTH) and len(precious) < 4:
                precious.append(c)
            else:
                spare_lands.append(c)
        big  = sorted([c for c in spells if c.name in BIG_PAYOFFS],
                      key=lambda c: -getattr(c, "cmc", 0))
        rest = [c for c in spells if c.name not in BIG_PAYOFFS
                and c.name != EXP_MAP]
        maps = [c for c in spells if c.name == EXP_MAP]
        # bottoming order: extra big payoffs -> spare lands -> cheap rest
        pool = big[1:] + spare_lands + rest + big[:1] + maps + precious
        return pool[:n]

    # ── land + tutor sequencing ─────────────────────────────────────────

    def _play_land_if_able(self, gs) -> Optional[Card]:
        """Priority: missing Tron piece > Temple > Labyrinth (imprinting a
        7+ card from hand -- real card loss) > basics > spare Tron dupes."""
        if gs.land_played:
            return None
        lands = [c for c in gs.zones.hand if c.is_land()]
        if not lands:
            return None
        missing = TRON_PIECES - self._tron_pieces_on_bf(gs)
        big_in_hand = any(getattr(c, "cmc", 0) >= 7 and not c.is_land()
                          for c in gs.zones.hand)

        def score(c):
            if c.name in missing:
                return 0
            if c.name == TEMPLE:
                return 1
            if c.name == LABYRINTH:
                return 2 if big_in_hand else 4
            if c.name in TRON_PIECES:
                return 5     # spare dupe
            return 3         # Swamp / Wastes
        best = min(lands, key=score)
        gs.play_land(best)
        if best.name == LABYRINTH:
            big = [c for c in gs.zones.hand
                   if getattr(c, "cmc", 0) >= 7 and not c.is_land()]
            if big:
                # imprint the WORST big card (spare Ulamog/dupe first)
                big.sort(key=lambda c: getattr(c, "cmc", 0))
                pick = big[-1]
                gs.zones.hand.remove(pick)
                gs.zones.exile.append(pick)
                gs._log(f"  Labyrinth imprint: exile {pick.name}")
        return best

    def _activate_map(self, gs, avail) -> int:
        """Expedition Map on the battlefield: {2}, sac -> tutor the missing
        Tron piece (or a Temple) from the LIBRARY into hand. Fires before
        the land drop so the fetched piece can be played this turn."""
        if avail < 2 or self._tron_online(gs):
            return avail
        maps = [c for c in gs.zones.battlefield if c.name == EXP_MAP]
        if not maps:
            return avail
        missing = TRON_PIECES - self._tron_pieces_on_bf(gs)
        # don't fetch a piece we already hold in hand
        in_hand = {c.name for c in gs.zones.hand if c.name in TRON_PIECES}
        want = [n for n in (TOWER, MINE, PLANT)
                if n in missing and n not in in_hand] or [TEMPLE]
        target = None
        for name in want:
            for c in gs.zones.library:
                if c.name == name:
                    target = c
                    break
            if target:
                break
        if target is None:
            return avail
        gs.mana_pool.flex -= min(2, gs.mana_pool.flex)
        m = maps[0]
        gs.zones.battlefield.remove(m)
        gs.zones.graveyard.append(m)
        gs.zones.library.remove(target)
        gs.zones.hand.append(target)
        gs._log(f"  Expedition Map: tutor {target.name} to hand "
                f"({len(self._tron_pieces_on_bf(gs))}/3 Tron)")
        return gs.mana_pool.total()

    # ── main phase ──────────────────────────────────────────────────────

    def main_phase(self, gs):
        self.main_phase_match(gs, None)

    def main_phase_match(self, gs, opponent):
        casts_with_raker = 0

        def rakers():
            return sum(1 for c in gs.zones.battlefield
                       if c.name == FLESHRAKER)

        gs.tap_lands()
        bonus_before = self._big_mana_bonus(gs)
        gs.mana_pool.flex += bonus_before
        avail = gs.mana_pool.total()

        # 1. Map activation BEFORE the land drop (fetch -> play this turn)
        avail = self._activate_map(gs, avail)

        # 2. Land drop (may complete Tron) -- credit the new land's mana +
        #    any bonus delta (Tron completion +4, Temple +1, ...)
        played = self._play_land_if_able(gs)
        if played is not None:
            delta = self._big_mana_bonus(gs) - bonus_before
            gs.mana_pool.flex += 1 + max(0, delta)
            avail = gs.mana_pool.total()

        # 3. Expedition Map from hand ({1}) -- assembles future Tron
        if not self._tron_online(gs):
            for c in list(gs.zones.hand):
                if c.name == EXP_MAP and avail >= 1:
                    if gs.cast_spell(c):
                        casts_with_raker += rakers()
                        avail = gs.mana_pool.total()
                    break

        # 4. Mind Stone ({2}) -- grind-mode ramp toward 7 even off-Tron
        for c in list(gs.zones.hand):
            if c.name == MIND_STONE and avail >= 2 and avail < 7:
                if gs.cast_spell(c):
                    casts_with_raker += rakers()
                    avail = gs.mana_pool.total()
                break

        # 5. Dismember ({1} + 4 life) on a real threat (power >= 3, tough <= 5)
        if opponent is not None and gs.life > 8:
            threats = [x for x in opponent.zones.battlefield
                       if not x.is_land() and x.has(Tag.CREATURE)
                       and safe_power(x) >= 3 and safe_toughness(x) <= 5]
            if threats:
                target = max(threats, key=safe_power)
                for c in list(gs.zones.hand):
                    if c.name == DISMEMBER and avail >= 1:
                        gs.mana_pool.flex -= min(1, gs.mana_pool.flex)
                        gs.zones.hand.remove(c)
                        gs.zones.graveyard.append(c)
                        gs.life -= 4
                        gs.noncreature_spells_this_turn += 1
                        casts_with_raker += rakers()
                        if target in opponent.zones.battlefield:
                            opponent.zones.battlefield.remove(target)
                            opponent.zones.graveyard.append(target)
                            gs._log(f"  Dismember: kill {target.name} (paid 4 life)")
                        avail = gs.mana_pool.total()
                        break

        # 6. Glaring Fleshraker ({3}) -- the ping engine wants to land EARLY
        for c in list(gs.zones.hand):
            if c.name == FLESHRAKER and avail >= 3:
                if gs.cast_spell(c):
                    avail = gs.mana_pool.total()
                break

        # 7. Thought-Knot Seer ({3}{C}) -- ETB: exile opp's best card
        for c in list(gs.zones.hand):
            if c.name == TKS and avail >= 4:
                if gs.cast_spell(c):
                    casts_with_raker += rakers()
                    if opponent is not None and opponent.zones.hand:
                        best = max(opponent.zones.hand,
                                   key=lambda x: getattr(x, "cmc", 0))
                        opponent.zones.hand.remove(best)
                        opponent.zones.exile.append(best)
                        gs._log(f"  TKS: exile {best.name} from opp hand")
                    avail = gs.mana_pool.total()
                break

        # 8. Karn ({4}) -- wish proxied as draw-1 (house pattern; wishboard
        #    toolbox + artifact-hate static UNMODELED, see module docstring)
        for c in list(gs.zones.hand):
            if c.name == KARN and avail >= 4:
                if gs.cast_spell(c):
                    casts_with_raker += rakers()
                    gs.zones.draw(1)
                    self._karn_wishes_used += 1
                    gs._log(f"  Karn: wish -> draw 1 "
                            f"(#{self._karn_wishes_used}; toolbox unmodeled)")
                    avail = gs.mana_pool.total()
                break

        # 9. Seven-mana payoff ladder, posture-aware
        avail, casts_with_raker = self._deploy_payoffs(
            gs, opponent, avail, casts_with_raker, rakers)

        # 10. Kozilek's Command ({X}{C}{C}) with leftovers: exile a creature
        #     MV<=X + scry-draw (house-approved approximation)
        for c in list(gs.zones.hand):
            if c.name == KOZ_CMD and avail >= 3:
                x_val = avail - 2
                gs.mana_pool.flex -= min(avail, gs.mana_pool.flex)
                gs.zones.hand.remove(c)
                gs.zones.graveyard.append(c)
                gs.noncreature_spells_this_turn += 1
                casts_with_raker += rakers()
                if opponent is not None:
                    opp_cr = [x for x in opponent.zones.battlefield
                              if x.has(Tag.CREATURE) and not x.is_land()
                              and getattr(x, "cmc", 0) <= x_val]
                    if opp_cr:
                        t = max(opp_cr, key=safe_power)
                        opponent.zones.battlefield.remove(t)
                        opponent.zones.exile.append(t)
                        gs._log(f"  Koz Command X={x_val}: exile {t.name} + draw")
                gs.zones.draw(1)
                avail = gs.mana_pool.total()
                break

        # 11. Chalice as last-priority filler (prison lock UNMODELED --
        #     cast only when mana would otherwise go to waste)
        for c in list(gs.zones.hand):
            if c.name == CHALICE and avail >= 2 and not [
                    x for x in gs.zones.hand
                    if not x.is_land() and x.name != CHALICE
                    and getattr(x, "cmc", 99) <= avail]:
                if gs.cast_spell(c):
                    casts_with_raker += rakers()
                    avail = gs.mana_pool.total()
                break

        # Fleshraker pings: 1 face damage per colorless spell cast while it
        # was on the battlefield (WANTS_BURN routes this to the match life)
        if casts_with_raker > 0:
            gs.damage_dealt += casts_with_raker
            gs._log(f"  Fleshraker ping x{casts_with_raker}")

    def _deploy_payoffs(self, gs, opponent, avail, casts_with_raker, rakers):
        """Posture-aware 7-drop order.
        Board posture (2+ opp creatures or 6+ power): All Is Dust > Ugin >
        Sire > Devourer -- stabilize first.
        Race posture (empty-ish opp board): Ugin > Devourer > Sire --
        pressure + card advantage first. Ulamog whenever 10 is there."""
        if avail < 7:
            return avail, casts_with_raker
        opp_creatures = []
        if opponent is not None:
            opp_creatures = [x for x in opponent.zones.battlefield
                             if x.has(Tag.CREATURE) and not x.is_land()]
        board_power = sum(safe_power(x) for x in opp_creatures)
        threatened = len(opp_creatures) >= 2 or board_power >= 6
        order = ([ALL_IS_DUST, UGIN, SIRE, DEVOURER] if threatened
                 else [UGIN, DEVOURER, SIRE, ALL_IS_DUST])

        while avail >= 7:
            cast_something = False
            # Ulamog first if we can afford him
            if avail >= 10:
                for c in list(gs.zones.hand):
                    if c.name == ULAMOG:
                        gs.mana_pool.flex -= min(10, gs.mana_pool.flex)
                        gs.zones.hand.remove(c)
                        gs.zones.battlefield.append(c)
                        c.turn_entered = gs.turn
                        c.summoning_sickness = True
                        casts_with_raker += rakers()
                        if opponent is not None:
                            for _ in range(2):
                                tg = [x for x in opponent.zones.battlefield
                                      if not x.is_land()]
                                if tg:
                                    t = max(tg, key=safe_power)
                                    opponent.zones.battlefield.remove(t)
                                    opponent.zones.exile.append(t)
                                    gs._log(f"  Ulamog CAST: exile {t.name}")
                        avail = gs.mana_pool.total()
                        cast_something = True
                        break
            if cast_something:
                continue
            for name in order:
                card = next((c for c in gs.zones.hand if c.name == name), None)
                if card is None:
                    continue
                if name == ALL_IS_DUST:
                    if not opp_creatures:
                        continue
                    gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                    gs.zones.hand.remove(card)
                    gs.zones.graveyard.append(card)
                    gs.noncreature_spells_this_turn += 1
                    casts_with_raker += rakers()
                    killed = 0
                    if opponent is not None:
                        for x in list(opponent.zones.battlefield):
                            if x.is_land():
                                continue
                            # our permanents are colorless; theirs almost
                            # never are -- sweep opp nonland board
                            opponent.zones.battlefield.remove(x)
                            opponent.zones.graveyard.append(x)
                            killed += 1
                    gs._log(f"  All Is Dust: sweep {killed} opp permanents")
                elif name == UGIN:
                    gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                    gs.zones.hand.remove(card)
                    gs.zones.battlefield.append(card)
                    card.turn_entered = gs.turn
                    casts_with_raker += rakers()
                    if opponent is not None:
                        tg = [x for x in opponent.zones.battlefield
                              if not x.is_land()]
                        if tg:
                            t = max(tg, key=safe_power)
                            opponent.zones.battlefield.remove(t)
                            opponent.zones.exile.append(t)
                            gs._log(f"  Ugin CAST: exile {t.name}")
                else:  # DEVOURER / SIRE -- 7-mana beaters
                    gs.mana_pool.flex -= min(7, gs.mana_pool.flex)
                    gs.zones.hand.remove(card)
                    gs.zones.battlefield.append(card)
                    card.turn_entered = gs.turn
                    card.summoning_sickness = True
                    casts_with_raker += rakers()
                    if name == DEVOURER and opponent is not None:
                        tg = [x for x in opponent.zones.battlefield
                              if not x.is_land()]
                        if tg:
                            t = max(tg, key=safe_power)
                            opponent.zones.battlefield.remove(t)
                            opponent.zones.exile.append(t)
                            gs._log(f"  Devourer CAST: exile {t.name}")
                avail = gs.mana_pool.total()
                cast_something = True
                break
            if not cast_something:
                break
            if opponent is not None:
                opp_creatures = [x for x in opponent.zones.battlefield
                                 if x.has(Tag.CREATURE) and not x.is_land()]
        return avail, casts_with_raker

    # ── combat / triggers ───────────────────────────────────────────────

    def declare_attackers(self, gs, opponent):
        """Base trade-aware attack logic + the Ulamog attack trigger
        (defending player exiles top 20 -- oracle-faithful)."""
        attackers = super().declare_attackers(gs, opponent)
        for a in attackers:
            if a.name == ULAMOG and opponent is not None:
                exiled = min(20, len(opponent.zones.library))
                for _ in range(exiled):
                    if opponent.zones.library:
                        opponent.zones.exile.append(
                            opponent.zones.library.pop(0))
                if exiled:
                    gs._log(f"  Ulamog attack: exile {exiled} from opp library")
        return attackers

    def respond_to_spell(self, gs, opponent, spell):
        return None  # proactive deck -- no stack interaction (see docstring)

    def end_step_actions(self, gs, opponent):
        """TKS leave-trigger: opponent draws a card per TKS that left
        (oracle-faithful, same tracking pattern as eldrazi_tron_match)."""
        tks_now = sum(1 for c in gs.zones.battlefield if c.name == TKS)
        tks_died = max(0, self._tks_on_board_last_turn - tks_now)
        if tks_died > 0 and opponent is not None:
            for _ in range(tks_died):
                opponent.zones.draw(1)
            gs._log(f"  TKS leaves: opp draws {tks_died} (oracle trigger)")
        self._tks_on_board_last_turn = tks_now
