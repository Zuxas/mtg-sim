# Amulet Titan APL — Full Bible Audit & Rewrite Spec
## Source: Dom Harvey's "All About Amulet Titan" (2651 lines, updated Nov 2025)

---

## EXECUTIVE SUMMARY

The current APL (3304 lines) models Amulet Titan as a "ramp to Titan, attack 4 times" deck.
The REAL deck is a **deterministic combo deck** with multiple kill lines that win the turn
Titan enters (or even without Titan via Scapeshift→Analyst loop). The APL needs a
fundamental architectural rewrite from "beatdown" to "combo with toolbox finish."

Current sim: avg T7.31 kill, 81.5% win rate
Target: avg T4.5-5.5 kill, 90%+ win rate
Gap: combo lines not modeled, mana engine underperforms on burst turns

---

## CRITICAL MISSING MECHANICS (Priority Order)

### 1. BOUNCE LAND SELF-RETURN WITH MULTIPLE LAND DROPS
**Bible quote:** "you should use bouncelands' triggers on themselves after you tap them 
for mana, so that you can play them again. A single bounceland can generate 6 mana all 
by itself this way"

**What the deck does:** With Amulet + extra land drops (Grazer/Spelunking/Explore), you:
1. Play bounce land → Amulet untaps → tap for 2 → bounce trigger returns ITSELF to hand
2. Play same bounce land again (using extra land drop) → Amulet untaps → tap for 2 → bounce itself
3. Repeat for each extra land drop available
4. On the LAST play, bounce something ELSE (keep the bounce land on BF for future turns)

**Net mana per replay:** +2 per Amulet per replay (with 2 Amulets = +4 per replay)
**With Grazer:** T1 Amulet, T2 bounce (2 mana) → Grazer ({G}) → Grazer puts bounce back → 
  bounce again (2 more) = 4 mana from 1 bounce + 1 Grazer. Then bounce stays, returning Forest.

**APL status:** PARTIALLY FIXED (self-return implemented) but the greedy loop doesn't 
properly chain multiple replays per turn. Need: after self-return, immediately check 
"do I have another land drop?" → if yes, play it again from hand.

**Net mana chart (from Bible):**
- Grazer + 1 Amulet + bounce = +1 mana net (costs G, gains 2)
- Grazer + 2 Amulets + bounce = +3 mana net (costs G, gains 4)
- Spelunking + 1 Amulet + bounce = ~+1 (costs 2G, gains 2 + the land from ETB)
- Explore + 1 Amulet + bounce = +0 net (costs 1G, gains 2, but drew a card)

### 2. SCAPESHIFT DETERMINISTIC KILL LINE
**Bible quote:** "the Scapeshift OHKO is the single most powerful angle in the deck 
and is worth leaning into as hard as possible"

**The standard kill (1 Amulet + 4 lands):**
1. Cast Scapeshift ({2}{G}{G}), sacrifice all 4 lands
2. Fetch: 2x Lotus Field + 1 bounce land + 1 Tolaria West
3. Stack triggers: Amulet untaps each → tap Lotus (3G each × 2 = 6G), 
   tap bounce (2 mana), Tolaria West enters tapped → Amulet untaps → tap (U)
4. Bounce trigger: return Tolaria West to hand
5. Lotus sac triggers: sacrifice bounce + both Lotus to each other
6. Total mana floating: ~9+ mana (enough for everything below)
7. Transmute Tolaria West ({1}{U}{U}) → find Summoner's Pact
8. Cast Pact ({0}) → find Aftermath Analyst
9. Cast Analyst ({1}{G}) → ETB mills 3
10. Sacrifice Analyst ({3}{G}) → return ALL sacrificed lands (2 Lotus + bounce + TWest + original 4)
11. Massive mana burst → cast Titan → Titan ETB finds Woodland + X → Analyst loop assembled

**APL status:** NOT MODELED. The APL's `_try_scapeshift` just fetches lands generically.
It doesn't know about the Lotus+bounce+TWest package or the transmute→Pact→Analyst chain.

### 3. THE ANALYST DETERMINISTIC LOOP (WIN CONDITION)
**Bible requirements:** Amulet + Lotus Field + (2nd Lotus OR Echoing Deeps) + 
Shifting Woodland + delirium (4 card types in GY)

**The loop:**
1. Sacrifice Analyst → return Lotus + Deeps/Lotus + Woodland + bounce + other lands
2. All lands enter tapped → Amulet chains fire → massive mana
3. Lotus sac triggers → sacrifice some returned lands (but you net mana)
4. Activate Shifting Woodland ({2}{G}{G}) → becomes copy of Analyst in GY
5. Sacrifice Woodland-as-Analyst ({3}{G}) → return everything again
6. Loop infinitely, each cycle netting mana

**Each loop costs:** {5}{G}{G}{G} (2GG for Woodland + 3G for Analyst sac)
**Each loop generates:** 6+ mana from Lotus (with 1 Amulet) or 12+ (with 2 Amulets)
**Net positive:** YES with 2 Amulets or 2 Lotus Fields

**Win condition from loop:**
- Bounce land + Boseiju → channel Boseiju each loop → destroy all opponent permanents
- Bounce land + Otawara → channel Otawara each loop → bounce everything
- Mirrorpool → copy Analyst before sac → make infinite creature tokens → Hanweir haste all
- Urza's Cave → find any land needed for the loop

**APL status:** NOT MODELED. Analyst is used as "ramp" only, not as a loop win condition.

### 4. THE MYCOSYNTH GARDENS (MISSING FROM DECKLIST)
**Bible quote:** "TMG turns a single Amulet hand into a double Amulet hand"

**Oracle:** {T}: Add {C}. {1}, {T}: This land becomes a copy of target artifact you 
control with mana value 1 or less. (It's no longer a land.)

**What it does:** Copy Amulet of Vigor for {1} + tap. Now you have 2 Amulets = 
every bounce land generates 4 mana instead of 2. This is the bridge from "fast" to "T2 kill."

**APL status:** NOT IN THE STUB DECK. Our 60-card list doesn't have Mycosynth Gardens.
The aljce tournament list may not run it, but most stock lists do.
At minimum: check the actual tournament list, and if Gardens is there, add it.

### 5. TITAN FETCHES AS A TOOLBOX (NOT JUST HASTE)
**Bible decision trees show Titan ETB has 20+ possible fetch combinations:**

**No Amulet:**
- Boseiju + bounce (interact with opponent's board)
- 2x Urza's Saga (build Constructs for board presence)
- Tolaria West + bounce (chain to next Titan via transmute)
- Shifting Woodland + X (set up delirium threat)
- Crumbling Vestige + X (immediate mana for follow-up spell)

**One Amulet (no spare mana):**
- Battlements + Vestige → haste Titan → attack → Otawara + bounce → channel Otawara
- Battlements + Lotus → attack → Woodland + Lotus (sets up Analyst loop)

**One Amulet (spare mana):**
- Battlements + Vestige → attack → Lotus + Mirrorpool → copy Titan
- This creates a SECOND Titan (ETB fires before legendary rule kills token)

**Two Amulets:**
- Mirrorpool + Lotus → copy Titan (net +2 mana) → copy again with Deeps-as-Mirrorpool
- Chain 3-4 Titan ETBs → fetch every land you need → Analyst loop assembled

**APL status:** RUDIMENTARY. Only fetches Hanweir+bounce or 2x bounce. Doesn't model 
the 20+ decision tree branches, the Mirrorpool copy chains, or the Analyst loop setup.

### 6. EXPLORE (MISSING FROM DECK/APL)
**Bible:** "Explore keeps your card count the same and offers a redraw toward any missing piece"
Some lists run Explore over Rumble. Our stub deck has Rumble instead.
Not critical but worth noting — Explore + Amulet + bounce = +0 mana net but draws a card.

---

## MISSING/BROKEN CARD INTERACTIONS

### 7. Crumbling Vestige Replay Trick
**Bible:** "Vestige -> bounceland returning Vestige -> replay Vestige gets you the same 
amount of mana as playing the bounceland repeatedly while letting you keep this additional 
land in play"
This is a mana-neutral way to establish an extra permanent land on BF.
**APL status:** Not modeled as a specific play pattern.

### 8. Spelunking + Cave = 4 Life (already in APL but verify)
When Spelunking ETB puts a Cave (Urza's Cave, Echoing Deeps) onto BF, gain 4 life.
**APL status:** Partially modeled but verify the Cave check is correct.

### 9. Shifting Woodland as a Slow Saga
**Bible:** "You can slowly build a permanent Urza's Saga (activating in your draw step 
each turn you want to gain a counter)"
Woodland copying Saga starts at 0 lore counters and gains them normally.
**APL status:** Not modeled (edge case, low priority).

### 10. Vesuva CANNOT Copy Simultaneously-Entering Lands
**Bible/Oracle:** If Titan fetches Vesuva + Gruul Turf simultaneously, Vesuva cannot 
copy the Gruul Turf (they enter at the same time). Vesuva can only copy lands ALREADY on BF.
**APL status:** The oracle audit mentions this (EC-09) but verify the fetch logic enforces it.

### 11. Echoing Deeps CAN Copy Simultaneously-Returning Lands
**Bible:** "Echoing Deeps can copy a land returning alongside it via Analyst etc; this is 
the opposite of the Titan -> Vesuva + X interaction"
When Analyst returns Deeps + Lotus from GY simultaneously, Deeps CAN see the Lotus.
**APL status:** IMPORTANT for the Analyst loop. Verify this is modeled.

### 12. Lotus Field Hexproof
**Oracle:** Lotus Field has hexproof. Can't be targeted by Boseiju, Ghost Quarter, etc.
**APL status:** Not relevant in goldfish but important for match APL.

### 13. Summoner's Pact Safety Rules
**Bible:** "you usually want to use it when you're winning that same turn"
The APL should only cast Pact when:
a) You will win this turn, OR
b) You can definitely pay {2}{G}{G} next upkeep (have 4+ mana from lands on BF)
**APL status:** Partially modeled but the upkeep payment logic was broken (fixed this session).

### 14. Urza's Saga Chapter II Construct Sizing
Constructs get +1/+1 per artifact you control. This includes:
- Amulet of Vigor (artifact)
- The Construct token itself (artifact creature)
- Any other Constructs from other Sagas
- Vexing Bauble (if in play)
With 2 Amulets + 1 Construct: Construct is 3/3
**APL status:** Fixed this session but verify the artifact counting logic.

### 15. Tolaria West Transmute Timing
Transmute is sorcery-speed only. You cannot transmute during combat or at instant speed.
If Titan fetches SGC + Tolaria West, you can't transmute until postcombat main phase.
But if Titan ETB finds TWest (you need to bounce it with a bounceland trigger first), 
you can transmute in main phase 1 before combat.
**APL status:** The transmute check requires `gs.mana_pool.U >= 2` but doesn't verify timing.

---

## STUB DECK DISCREPANCIES

### Cards in Bible's stock list NOT in our stub:
- **The Mycosynth Gardens** — critical for single→double Amulet
- **Explore** — some lists run this over/alongside Rumble
- **Dryad Arbor** — GSZ-0 target for ramp + Forest type
- **Valakut, the Molten Pinnacle** — alternate win condition (some builds)
- **Springheart Nantuko** — infinite combo with Titan + fetchland

### Cards in our stub NOT in Bible's stock list:
- **Ghost Quarter** — situational, not in most stock lists
- **Icetill Explorer** — newer card, not in the Bible's main examples

### Verify: Get the actual aljce tournament list from the meta-analyzer DB
and compare card-for-card against our stub deck.

---

## MULLIGAN IMPROVEMENTS (from Bible)

### Bible's mulligan philosophy:
"A hand that just makes a fast Titan isn't enough — without immediate kills via 
Dryad or a follow-up Analyst loop you can easily die anyway"

### Key principles not yet modeled:
1. **Speed matters most in Game 1** — mulligan aggressively for T3-4 Titan hands
2. **Saga hands are keepable** — T1 Saga → T3 Amulet → T4+ Titan is a real plan
3. **Double Amulet hands are premium** — even without a threat, 2 Amulets + lands = keep
4. **Pact hands need safety** — only keep Pact hands if you can win or pay the upkeep
5. **Bounceland is the key card** — "Drawing the first bounceland is often the key to 
   your draw being functional"

### Current APL keeps at 77.6% (21.5% mull rate) — this seems about right for the deck.

---

## ARCHITECTURAL CHANGES NEEDED

### Current architecture:
```
main_phase():
    greedy_loop:
        play_land()
        try_deploy_titan()  # hardcast or GSZ
        cast_amulet()
        cast_grazer()
        cast_spelunking()
        ...
    
main_phase2():
    titan_attacks()  # just deals damage
```

### Needed architecture:
```
main_phase():
    greedy_loop:
        # Phase A: Establish engine (Amulet/Spelunking)
        # Phase B: Generate mana (bounce chains with self-return)
        # Phase C: Deploy win condition (in priority order):
        #   1. Scapeshift deterministic kill (if 4+ lands + Amulet)
        #   2. Titan + haste + Mirrorpool chain
        #   3. Analyst loop setup (if all pieces available)
        #   4. Raw Titan cast → toolbox finish
        
titan_etb():
    # Full 20+ branch decision tree based on:
    # - Amulet count (0, 1, 2+)
    # - Spare mana available
    # - Cards in hand (Pact? Analyst? Zenith?)
    # - Lands already in play (Hanweir? Mirrorpool?)
    # - Win condition: immediate kill vs setup next turn
    
analyst_loop():
    # Deterministic infinite loop:
    # Sac Analyst → return lands → Woodland becomes Analyst → sac again
    # Track: is loop net-positive on mana? If yes, win.
    
scapeshift_kill():
    # Deterministic combo:
    # Shift for Lotus+Lotus+bounce+TWest → transmute → Pact → Analyst → loop
```

---

## NEXT SESSION CHECKLIST

1. [ ] Verify stub deck against actual tournament list (check for Mycosynth Gardens)
2. [ ] Implement Scapeshift deterministic kill line
3. [ ] Implement Analyst loop as a win condition (not just ramp)
4. [ ] Rewrite Titan fetch priority as a 20+ branch decision tree
5. [ ] Fix bounce self-return to chain multiple replays per turn
6. [ ] Add Mirrorpool → copy Titan → copy again with Deeps chain
7. [ ] Verify Echoing Deeps can copy simultaneously-returning lands
8. [ ] Add Shifting Woodland delirium activation as attack threat
9. [ ] Test: run 5000 games, target avg T5-6 kill
10. [ ] Update CLAUDE.md with final numbers

---

## ADDITIONAL IMPROVEMENTS IDENTIFIED

### From the Bible's matchup section:
- **Titan → double Vestige → channel Boseiju** line for instant interaction
- **Titan → Otawara + bounce → channel Otawara in declare attackers** for removal
- **Saga Constructs as serious threats** with multiple Amulets (3/3 or 4/4 bodies)
- **Urza's Cave as instant-speed Bojuka Bog** in the match APL
- **Woodland as recurring threat** against counter-heavy decks

### From mana engine section:
- **Vestige → bounce → replay Vestige** to establish permanent mana without losing tempo
- **Lotus Field chaining:** Lotus → bounce → replay Lotus (net +2 with 1 Amulet)
- **Grazer paying for itself** with Vestige: Grazer → Vestige (G) → Grazer costs {G} → net zero

### From game theory section:
- **Titan haste vs safety tradeoff:** Sometimes DON'T give haste if Titan will die 
  to removal — fetch utility lands instead and survive to next turn
- **Multiple Titans are the endgame:** The first Titan chains into the second via 
  Tolaria West, which chains into the third via Woodland or another TWest
- **Postboard games are slower:** The APL should have match-APL-specific logic for 
  grindier games where Saga Constructs and Woodland copies matter more
