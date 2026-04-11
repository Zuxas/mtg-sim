# ELDRAZI RAMP — CARD-BY-CARD APL AUDIT
# Full 7-step audit following Boros Energy gold standard

## CRITICAL INTERACTIONS

### 1. Kozilek's Return GY Trigger — FREE Sweeper (P0)
**Oracle:** "Whenever you cast an Eldrazi creature MV≥7, exile from GY → 5 dmg all creatures"
When you cast Emrakul/World Breaker/Sire/Devourer, K-Return fires from GY.
This is a FREE board wipe that doesn't cost mana or a card (already in GY).
**Pilot:** Mill/discard K-Return early. Cast big Eldrazi = wipe opponent's board.
**Opponent:** Exile K-Return from GY before they cast big Eldrazi (Surgical, Thraben Charm Mode 3).

### 2. Emrakul Cost Reduction + Mindslaver (P0)
**Oracle:** "Costs {1} less per card type in GY. When CAST: control opponent's next turn."
Card types: instant, sorcery, creature, artifact, enchantment, land, PW = 7 max.
Realistic: 4-5 types = costs {8}-{9}. With Temple + Labyrinth = castable T4-T5.
The Mindslaver effect: use opponent's removal on their own creatures, waste their mana.
**Pilot:** Fill GY with diverse types. Malevolent Rumble + Formidable Speaker help.
**Opponent:** Exile their GY to deny cost reduction.

### 3. Ugin's Labyrinth Imprint — Sol Land (P0)
**Oracle:** "ETB: exile 7+ MV colorless card from hand. Tap: {C} or {C}{C} if imprinted."
T1 Labyrinth + imprint Emrakul = {C}{C} every turn. Can retrieve imprinted card later.
This is the deck's primary acceleration — a Sol land on T1.
**Pilot:** Always imprint if you have a 7+ card. Retrieve when ready to cast.

### 4. Sowing Mycospawn — CAST Trigger Ramp + Land Exile (P1)
**Oracle:** "When you CAST: search library for land → battlefield. Kicker {1}{C}: exile target land."
Cast trigger fires from any zone. Puts land ONTO BATTLEFIELD (not hand).
Kicker = mana denial. Ramps you AND denies opponent.
**Pilot:** Kick when ahead on mana to lock opponent out. Tutor Ghost Quarter/Cavern.

### 5. Icetill Explorer + Ghost Quarter Lock (P1)
**Oracle (Icetill):** "Play additional land each turn. Play lands from GY."
**Oracle (Ghost Quarter):** "Sacrifice: Destroy target land. They get a basic."
**Combo:** Ghost Quarter → destroy their land → opponent may get basic (if they have one).
Icetill replays Ghost Quarter from GY next turn → repeat. = Strip Mine every turn.
Most Modern decks run 1-3 basics. After those are gone, Ghost Quarter = Strip Mine.

### 6. Formidable Speaker Lines (P1)
**Oracle:** "ETB: discard a card → tutor a creature. {1},{T}: Untap another permanent."
**Line A:** Discard K-Return → tutor Emrakul → cast Emrakul → K-Return fires from GY
**Line B:** Discard a land → tutor Icetill → play Icetill → play land from GY (Icetill ability)
**Line C:** Untap Ugin's Labyrinth for double mana in one turn

### 7. Sanctum of Ugin — Chain Eldrazi (P1)
**Oracle:** "When you cast 7+ MV colorless, sacrifice: tutor colorless creature."
Cast Devourer → sacrifice Sanctum → tutor Emrakul → cast Emrakul next turn.
Chain threats so opponent can never stabilize.

### 8. World Breaker — Recurring + Cast Trigger (P1)
**Oracle:** "CAST: exile artifact/enchantment/land. Reach. {2}{C}, sac land: return from GY."
World Breaker can return from GY repeatedly for {2}{C} + sacrifice a land.
Each time you cast it = exile another permanent + K-Return triggers if in GY.

### 9. Eldrazi Temple — Double Mana for Eldrazi (P1)
**Oracle:** "{T}: {C}{C} for Eldrazi spells or abilities only."
Combined with Ugin's Labyrinth, this provides massive acceleration.
T1 Labyrinth ({C}{C}) → T2 Temple ({C}{C}) + other land = 5 mana on T2.

### 10. Cavern of Souls — Uncounterable Eldrazi (P2)
**Oracle:** "Choose creature type. Mana from Cavern makes that type uncounterable."
Name "Eldrazi" → Emrakul, World Breaker, etc. can't be countered.
Critical vs Murktide/Jeskai counterspell decks.

### 11. Ugin PW — Cast Trigger + Static Ability (P1)
**Oracle:** "CAST: exile colored permanent. Whenever cast colorless spell: exile colored."
Ugin's static ability means every Eldrazi/artifact you cast ALSO exiles a permanent.
Cast Ugin → exile something → next turn cast Sowing Mycospawn → exile another.
+2: gain 3 life + draw. 0: add {C}{C}{C} (mana on a PW!).

### 12. Malevolent Rumble — GY Filler + Token (P2)
**Oracle:** "Reveal top 4, get a permanent, rest to GY. Create 0/1 Spawn."
The cards going to GY increase card type diversity → cheaper Emrakul.
Spawn token = sacrifice for {C} (emergency mana).

### 13. Emrakul Protection from Instants (P2)
**Oracle:** "Flying, trample, protection from instants"
Can't be targeted by Bolt, Path, Solitude pitch, Fatal Push, etc.
Only dies to: sorcery-speed removal, board wipes, sacrifice effects.


## APL CODE ISSUES (Cross-referenced with source)

### Issue A: Emrakul summoning_sickness = False — WRONG
Emrakul does NOT have haste. Has flying, trample, protection from instants. No haste.
**Fix:** `summoning_sickness = True`

### Issue B: Emrakul Mindslaver — NOT MODELED (Game-winning)
The CAST trigger "control target opponent's next turn" is THE reason you cast Emrakul.
You use opponent's removal on their own creatures, waste their mana, attack into yours.
**Model as:** Opponent effectively skips their next turn + takes ~5-10 self-damage.

### Issue C: Kozilek's Return GY Trigger — NOT MODELED (FREE Sweeper)
When casting MV≥7 Eldrazi: exile K-Return from GY → 5 damage all creatures.
This fires EVERY time you cast a big Eldrazi. Free board wipe.
**Fix:** Check GY for K-Return when casting Emrakul/World Breaker/Sire/Devourer.

### Issue D: Ugin's Labyrinth + Eldrazi Temple — Double Mana NOT TRACKED
Both produce {C}{C}, not {C}. The `gs.tap_lands()` gives 1 per land.
With 2 Temples + 1 Labyrinth + 1 Forest = 7 mana (not 4).
**Fix:** Count Temples and Labyrinth, add extra mana via _ramp_bonus.

### Issue E: Sowing Mycospawn CAST Trigger — NOT MODELED
Cast trigger puts a land from library ONTO BATTLEFIELD. This is T4 ramp.
**Fix:** When casting Mycospawn, add +1 to land count (simulate land from library).

### Issue F: Malevolent Rumble — NOT CAST AT ALL
Should: reveal top 4, get a permanent, rest to GY, create Spawn token.
Fills GY for Emrakul cost reduction. Creates Spawn = sacrifice for {C}.
**Fix:** Cast Rumble for card selection + GY fill + token.

### Issue G: Formidable Speaker Tutor — NOT MODELED
ETB: discard → tutor a creature. Untap a permanent.
Key line: discard K-Return → tutor Emrakul.
**Fix:** When casting Speaker, discard worst card, "tutor" by drawing.

### Issue H: World Breaker Cast Trigger — Targets Wrong Things
Oracle: exile artifact/enchantment/LAND. Current: only targets non-land permanents.
**Fix:** Can exile opponent's lands too (mana denial).
