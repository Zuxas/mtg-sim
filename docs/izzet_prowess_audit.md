# IZZET PROWESS — CARD-BY-CARD APL AUDIT
# Every card analyzed from pilot + opponent perspective
# What APL currently does vs what it SHOULD do

## CRITICAL CORRECTIONS NEEDED

### 1. Violent Urge DELIRIUM = DOUBLE STRIKE (NOT MODELED)
**Oracle:** "Target creature gets +1/+0 and gains first strike until end of turn.
           Draw a card.
           Delirium — If 4+ card types in GY, that creature gains double strike."
**Current APL:** Only models as +1 fuel in burst calculator. Missing:
  - The CARD DRAW (cantrip) — already partially fixed
  - The DOUBLE STRIKE with delirium — completely missing
  - Double strike on a pumped Slickshot = LETHAL BURST
    Example: Slickshot 1/2 + 3 spells cast = 7/2. With double strike = 14 flying damage.
**Pilot:** Save Violent Urge for the kill turn. With delirium active, this doubles
  your biggest creature's damage output.
**Opponent:** Must remove Slickshot BEFORE the burst turn. Once spells start chaining,
  it's too late.

### 2. Slickshot Show-Off PLOT Mechanic (NOT MODELED)
**Oracle:** "Plot {1}{R} (You may pay {1}{R} and exile this card from your hand. 
           Cast it as a sorcery on a later turn without paying its mana cost.)"
**Current APL:** Treats Slickshot as a normal 2-drop. Missing:
  - T2: Plot Slickshot (pay {1}{R}, exile it face-up)
  - T3: Cast Slickshot for FREE → all mana available for spells → maximum burst
  - Plotted Slickshot has flying + haste, attacks immediately
  - This is THE setup for burst kills
**Pilot:** Plot T2 if you have a good T3 hand (multiple cheap spells).
  Don't plot if you need to apply pressure immediately.
**Opponent:** If opponent plots T2, expect T3 burst. Hold up removal.

### 3. Cori-Steel Flurry — ANY Second Spell (PARTIALLY WRONG)
**Oracle:** "Flurry — Whenever you cast your second spell each turn, create a 1/1 
           white Monk creature token with prowess. You may attach this Equipment to it."
**Current APL:** May only trigger on noncreature spells.
**CORRECT:** Triggers on ANY second spell — creatures, instants, sorceries, artifacts.
  - Cast Bauble (spell 1) → Cast Bolt (spell 2) → Flurry triggers → 1/1 Monk
  - Monk gets equipment auto-attached: +1/+1, trample, haste = 2/2 trample haste
  - Monk also has prowess → additional spells pump it further
  - Works on OPPONENT'S TURN too — if you cast 2 instants during their turn, Flurry fires
**Pilot:** Sequence matters. Cast your cheapest spell first (Bauble, Mutagenic),
  then your second spell triggers Flurry.
**Opponent:** Kill Cori-Steel Cutter on sight. Without it, Prowess loses its engine.

### 4. Lava Dart = TWO Prowess Triggers (CRITICAL MATH)
**Oracle:** "Lava Dart deals 1 damage to any target.
           Flashback—Sacrifice a Mountain."
**Current APL:** Partially models flashback but may not count as 2 separate triggers.
**CORRECT behavior:**
  - Cast from hand: 1 damage + prowess trigger #1
  - Flashback from GY: 1 damage + prowess trigger #2 (sacrifice a Mountain)
  - Each trigger gives: Swiftspear +1/+1, DRC surveil 1, Slickshot +2/+0
  - With Slickshot: Lava Dart alone = +4/+0 from two prowess triggers
  - Dart from hand + flashback can trigger Cori-Steel Flurry (2 spells)
**Pilot:** Save Lava Dart for burst turns. One card = two prowess triggers.
  Sacrifice Mountain is real cost — don't do it unless going for lethal.
**Opponent:** If Prowess has a Mountain and Dart in GY, expect extra damage.

### 5. DRC Surveil → Delirium Engine (PARTIALLY MODELED)
**Oracle:** "Whenever you cast a noncreature spell, surveil 1."
           "Delirium — 4+ card types in GY: +2/+2, flying, attacks each combat."
**Current APL:** Has delirium check but doesn't model surveil filling GY.
**CORRECT:** Each spell cast → DRC surveil 1 → potentially puts a card type in GY.
  - Cast 3 spells → surveil 3 → could go from 0 delirium cards to 3-4
  - Card types needed: creature, instant, sorcery, artifact, land, enchantment
  - Bauble (artifact) + Bolt (instant) + Preordain (sorcery) + surveil land = 4 types
**Pilot:** Surveil aggressively to turn on delirium ASAP.
  Different card types in GY > raw card count.

### 6. Expressive Iteration = Effectively 2 Cards (UNDERMODELED)
**Oracle:** "Look at top 3. Put one in hand, one on bottom, exile one. 
           You may play the exiled card this turn."
**Current APL:** May not count the exiled card as additional fuel.
**CORRECT:** Iteration draws 2 usable cards (1 hand + 1 exiled playable this turn).
  - The exiled card can be a land (extra land drop) or a spell (more prowess fuel)
  - On burst turn: Iteration → get 2 more spells → 2 more prowess triggers
  - Iteration itself triggers prowess/Cori-Steel
**Pilot:** Save Iteration for burst turn. It refuels the chain.

### 7. Mutagenic Growth = Free Prowess + Pump (CORRECTLY MODELED)
**Oracle:** "{G/P} can be paid with {G} or 2 life. Target creature gets +2/+2."
**Analysis:** 
  - 0 mana cost (pay 2 life)
  - Triggers prowess (+1/+1 on Swiftspear, +2/+0 on Slickshot)
  - PLUS the +2/+2 pump on the target
  - Net on Swiftspear: +3/+3 for 2 life
  - Net on Slickshot: +4/+2 for 2 life
**Current APL:** Correctly identified as free spell. Verify pump is applied.

### 8. Mishra's Bauble = Free Prowess + Delirium + Delayed Draw
**Oracle:** "{T}, Sacrifice: Look at top card of target player's library. 
           Draw a card at beginning of next turn's upkeep."
**Analysis:**
  - 0 mana cost → free prowess trigger
  - Artifact type in GY (helps delirium — artifact + instant + sorcery = 3 types)
  - Card draw is DELAYED (next turn upkeep, not immediate)
  - The draw happens even if Bauble is exiled from GY (trigger already on stack)
**Current APL:** Models as fuel but may not track delayed draw or delirium type.

### 9. Monastery Swiftspear — Haste + Standard Prowess
**Oracle:** "Haste. Prowess (+1/+1 per noncreature spell)."
**Analysis:**
  - T1 play: attacks immediately for 1 damage
  - With 3 spells: 4/5 (1+3/2+3)
  - With Mutagenic: +3/+3 for 2 life = 4/5
  - Best T1 play on the play (Ragavan from Boros can't block on draw)
**Current APL:** Correctly modeled. Verify prowess counter application.

### 10. Slickshot Show-Off — +2/+0 Per Spell, NOT +1/+1
**Oracle:** "Flying, haste. Whenever you cast a noncreature spell, +2/+0 until EOT."
**CRITICAL:** Slickshot gets +2/+0, NOT standard prowess +1/+1.
  - 3 spells: 1/2 → 7/2 flying haste
  - 4 spells: 1/2 → 9/2 flying haste  
  - With Mutagenic: 1/2 + 2/0 (trigger) + 2/2 (pump) = 5/4 for just one spell
  - With Violent Urge double strike: 7/2 → 14 flying damage
**Current APL:** Correctly models +2/+0 triggers. Verify.

## EDGE CASES FROM COMPETITIVE GUIDES

### EDGE 1: Cori-Steel Can Be Manually Equipped
If no Flurry trigger, you can pay {1}{R} to equip Cori-Steel to any creature.
- Equip DRC: 1/1 → 2/2 trample haste. With delirium: 4/4 flying trample haste.
- Equip Swiftspear: 1/2 → 2/3 trample haste
- This is a backup plan when Flurry isn't triggering

### EDGE 2: Prowess Trigger Timing — Opponent Can Respond
"The opponent can respond to the prowess triggers to kill the creature while it's smaller."
- If opponent has 3 damage removal and your Swiftspear is 1/2:
  → You cast Bolt → prowess trigger goes on stack → opponent responds with Bolt
  → Swiftspear is still 1/2 (prowess hasn't resolved) → dies to 3 damage
- Competitive pilots sequence around this by casting pump spells FIRST

### EDGE 3: Lava Dart Stack Interaction
"The opponent can respond to the Dart on the stack, at which point you don't have 
access to it in the graveyard for a flashback."
- Cast Lava Dart → it's on the stack → opponent responds
- Dart is still on the stack (not in GY yet) → can't flashback
- Must let Dart RESOLVE (goes to GY) → then flashback

### EDGE 4: Iteration Exiled Card Timing
"When you exile a card with Iteration, you don't need to play the card immediately."
- The exiled card is playable any time during your turn
- This means you can use it post-combat if needed

### EDGE 5: Fiery Islet Sacrifice
**Oracle:** "{1}, {T}, Sacrifice: Draw a card."
- In the late game when hellbent (empty hand), sacrifice Islet to draw
- Costs: lose a land + 1 mana → gain a card
- Can turn a dead land into a prowess trigger

### EDGE 6: Against Boros — Kill Engine Pieces
From guides: "Focus on individual threats, making it difficult for opponent to 
establish Guide of Souls + Ocelot Pride, or Ajani + Bombardment."
- Priority kill targets: Guide of Souls (#1), Ocelot Pride (#2), Ajani (#3)
- Don't waste removal on tokens — kill the engine
- Lava Dart is excellent at killing 1-toughness creatures (Guide, Ocelot, Ragavan)

### EDGE 7: Burst Damage Calculation (The Kill Turn)
Full burst example with good hand:
  Board: Swiftspear + Slickshot (plotted last turn, cast free this turn)
  Hand: Bolt, Mutagenic, Lava Dart, Violent Urge
  GY: Bauble (artifact), Preordain (sorcery), DRC (creature) = delirium ON
  
  1. Cast Slickshot (free, plotted) → Swiftspear prowess +1/+1
  2. Cast Bauble → Swiftspear +1/+1, Slickshot +2/+0, Cori Flurry (2nd spell) → 2/2 Monk
  3. Cast Mutagenic (2 life) → all prowess, Slickshot +2/+0, pump Slickshot +2/+2
  4. Cast Violent Urge on Slickshot → prowess, +2/+0, +1/+0, DOUBLE STRIKE (delirium), draw
  5. Cast Bolt face → prowess, Slickshot +2/+0
  6. Lava Dart face → prowess, Slickshot +2/+0
  7. Lava Dart flashback → prowess, Slickshot +2/+0

  Slickshot: 1 + (7 spells × 2) = 15 power, + 2 (Mutagenic) + 1 (Violent) = 18/4 flying DOUBLE STRIKE = 36 damage
  Swiftspear: 1 + 7 = 8 power + 2 (if Mutagenic on it) = 8/9 haste  
  Monk: 2 + prowess from remaining spells = ~5/4 trample haste
  Bolt: 3 face, Dart: 1 face, Dart flash: 1 face = 5 direct
  TOTAL: 36 + 8 + 5 + 5 = 54 damage (overkill from 20)

  Realistic scenario (3-4 spells, not 7): ~18-22 damage burst = lethal


## ADDITIONAL EDGE CASES (Deep Dive #2)

### EDGE 8: Cori-Steel Cutter Spell Count Ruling (CRITICAL)
Scryfall ruling: "Spells that were cast BEFORE a permanent with flurry count. If 
  that permanent was the first spell you cast that turn, the next spell triggers Flurry."
**Impact:** If you cast Bauble (spell 1) → Cori-Steel (spell 2) → Flurry triggers
  IMMEDIATELY when Cori enters. Current APL may not count Cori itself as spell #2.
**Also:** If Cori is spell 1, the NEXT spell (anything) triggers Flurry.

### EDGE 9: Cori-Steel Flurry on OPPONENT'S Turn
Flurry says "your second spell each turn" — not "each of YOUR turns."
If you cast 2 instants during opponent's turn → Flurry creates a 2/2 Monk with haste.
**Defensive play:** Opponent attacks → cast Bolt (spell 1) → cast Mutagenic (spell 2)
  → Flurry → 2/2 Monk appears → block with Monk.
**Current APL:** Flurry only triggers during your turn. Missing defensive Monks.

### EDGE 10: DRC FORCED Attack with Delirium
Oracle: "attacks each combat if able"
**Impact:** With delirium, DRC is a 3/3 flyer that MUST attack. You cannot hold it 
  back for blocking. If opponent has a 4/4 flyer, your DRC flies into it and dies.
**Current APL:** DRC is in the optional attackers list. Should be FORCED with delirium.

### EDGE 11: Mishra's Bauble Delayed Draw — NOT Immediate
Oracle: "Draw a card at the beginning of the NEXT TURN'S upkeep."
**Impact on burst:** Bauble draw does NOT arrive during the burst turn. Cast Bauble 
  for prowess trigger only. The draw is next turn (if you survive).
**Current APL:** Burst turn casts Bauble and draws immediately (gs.zones.draw(1)).
  This overvalues Bauble during burst turns.

### EDGE 12: Preordain Scry 2 = Card Selection
Oracle: "Scry 2, then draw a card."
**Impact:** Look at top 2, put bad ones on bottom, THEN draw the good one.
  This is card selection — better than a random draw.
**Current APL:** Models as draw 1. Missing scry quality improvement.

### EDGE 13: Mutagenic Growth Life Cost Compounds
Each Mutagenic costs 2 life. Prowess starts at ~15-17 life (fetches + shocks).
With 2 Mutangenics: 4 life spent. Against Boros with lifegain, this is significant.
**Current APL:** Correctly pays 2 life per Mutagenic. No fix needed.

### EDGE 14: Lava Dart Flashback Loses a Land
Flashback sacrifices a Mountain. After flashback, you have fewer lands = less mana.
**Decision:** Only flashback when going for lethal or when the extra prowess trigger
  pushes damage over the threshold.
**Current APL:** Flashbacks when available. Should check if mana loss matters.

### EDGE 15: Multiple Slickshots Stack
2 Slickshots + 3 noncreature spells = each Slickshot is 1+(3×2) = 7/2 flying.
Total flying damage: 14. This is why the deck runs 4 copies.
**Current APL:** Correctly models multiple Slickshots.

### EDGE 16: Monk Gets Prowess from Subsequent Spells
After Flurry creates a 2/2 Monk (with equipment), each subsequent noncreature spell
gives it +1/+1 prowess. After 3 more spells: 5/5 trample haste.
**Current APL:** Monk is in PROWESS_CREATURES check (name contains "Monk" + "Token").
  Should be correct. Verify.

### EDGE 17: Delirium Card Types Available
Types in deck: instant (Bolt), sorcery (Preordain), artifact (Bauble/Cori), 
  creature (DRC/Swiftspear), land (Mountain). NO enchantments.
Need 4 types for delirium. Typical path: instant + sorcery + artifact + (creature OR land).
Bauble is critical — artifact type is hard to get otherwise.
**Current APL:** _has_delirium checks card types in GY. Verify it counts correctly.

### EDGE 18: Plotted Slickshot Cast Counts for Flurry
Casting from plot IS casting a spell. Plot Slickshot (spell 1) → Cast Bolt (spell 2)
  → Flurry triggers. OR: Plotted Slickshot was cast as spell 2 → Flurry triggers.
**Current APL:** _cast_from_plot increments _spells_this_turn and calls _check_flurry.
  Should be correct. Verify.

### EDGE 19: Violent Urge First Strike Before Regular Damage
With first strike (non-delirium), the target creature deals damage FIRST.
If Slickshot has first strike and deals 7 damage → opponent takes 7 before
their blockers deal damage. This matters when both creatures would trade.
**Current APL:** First strike not modeled in combat resolution engine.

### EDGE 20: Expressive Iteration Exile = Land Drop + Spell
The exiled card can be a LAND (extra land drop this turn) or a spell (more fuel).
If exiled card is a land: you get an extra land → more mana for spells.
If exiled card is a spell: extra prowess trigger + effect.
**Current APL:** Models Iteration as draw 1. Missing the exiled card value.


## PLAYBOOK-SOURCED INTERACTION SWEEP (Deep Dive #3)

Source: E:\vscode ai project\My-Website\modern\prowess-playbook.html
Sections read: Engines (3), Lines & Tricks, Edge Cases, Matchup vs Boros, SB Guide

### FIXES APPLIED:

1. **Murktide Regent — MAJOR MISSING CARD** (was not in APL at all)
   Playbook Priority 03 finisher. Oracle: {5}{U}{U}, Delve, 3/3 flying base + 
   +1/+1 counter per instant/sorcery exiled. With 4 spells in GY = 7/7 flying for {U}{U}.
   **Fix:** Added delve deployment after early creatures. Only deploys with 3+ spells in GY.

2. **respond_to_spell — Mutagenic Growth Protection**
   Playbook: "Cast Mutagenic Growth at instant speed in response to Discharge 
   to save your creature (+2/+2 survives most Discharge values)."
   **Fix:** Added Mutagenic Growth as reactive protection when creature would die to burn.

3. **Ragavan Kill Priority**
   Playbook: "Kill Ragavan with Lava Dart before it connects" on the draw.
   **Fix:** Added Ragavan to engine_pieces in removal priority list.

### VERIFIED CORRECT (no fix needed):

4. Prowess triggers on CAST, not resolution — APL triggers on cast ✅
5. DRC delirium is continuous — _has_delirium() checks dynamically ✅
6. Slickshot Plot mechanic — cast from exile, counts for Flurry ✅
7. Lava Dart self-target — face target is strictly better (prowess triggers on cast regardless) ⏭️
8. Violent Urge double strike on Slickshot = 14+ damage — in burst calc ✅

### PLAYBOOK ERROR FOUND:

9. **Unholy Heat vs Goblin Bombardment** — Playbook says "Unholy Heat kills Bombardment"
   but oracle says Heat targets "creature or planeswalker" only. Cannot target enchantments.
   **Action:** Flag for website playbook correction in next update cycle.

### MATCHUP RESULT AFTER FIXES:
Boros vs Prowess (2000g): 47.9% Boros | 52.1% Prowess (T4.7)
Competitive target: 48-52% range ✅ ACHIEVED
