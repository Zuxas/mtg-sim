# Amulet Titan — Comprehensive Rules Reference for APL
# Key rules the goldfish simulator must model correctly

## TRIGGER ORDERING (CR 603.3b) — CRITICAL FOR AMULET TITAN

When multiple abilities trigger simultaneously (e.g. Scapeshift resolves,
putting 4 lands on BF), the active player puts them on the stack IN ANY
ORDER THEY CHOOSE. Stack resolves LIFO (last in, first out).

### What this means for the sim:
- Scapeshift putting 4 lands: ALL enter simultaneously, ALL triggers
  (Amulet untap × N per land, bounce returns, Lotus sacs) go on stack
- Player orders: Amulet untaps FIRST (resolve last = bottom of stack?
  NO — they resolve first because they go on LAST)
  
  Actually the correct ordering: player puts triggers on stack in the
  order they WANT them to resolve (bottom first, top last... wait)
  
  CORRECTION: Stack is LIFO. If you want Amulet untaps to resolve FIRST:
  put them on the stack LAST (top of stack). So the order on stack is:
  BOTTOM: Lotus sac triggers (resolve last = after everything)
  MIDDLE: Bounce return triggers  
  TOP: Amulet untap triggers (resolve first)
  
  Practical effect:
  1. Amulet untap triggers resolve → tap each land for mana
  2. Bounce triggers resolve → pick up TWest or cheap land
  3. Lotus sac triggers resolve → sacrifice tapped/empty lands

### Current APL modeling:
- Sequential processing via _place_land_on_bf (one land at a time)
- _skip_lotus_sac flag during Scapeshift/Analyst to prevent early sacs
- Bounce return fires immediately per land (approximation of optimal)
- Net mana is CORRECT (same total as simultaneous) because each land
  gets its own Amulet untap regardless of order
- The KEY difference: which land gets BOUNCED matters hugely
  → Fixed: Woodland/Lotus/Echoing never bounced when loop is close

## AMULET OF VIGOR — TRIGGERED ABILITY (CR 603.2)

Oracle: "Whenever a permanent enters the battlefield tapped, untap it."
- This is a TRIGGERED ability, NOT a replacement effect
- The permanent DOES enter tapped first, THEN Amulet triggers
- With N Amulets: N separate triggers, each untapping the same permanent
- Between each trigger resolution, the player has priority → can TAP
  the permanent (e.g. tap a bounce land for mana between Amulet triggers)
- Bible: "with two Amulets you can tap in response to each trigger"

### Key interaction: Amulet + Spelunking
- Spelunking: "Lands you control enter untapped" — REPLACEMENT EFFECT (CR 614.1d)
- If Spelunking is active, lands NEVER enter tapped → Amulet trigger
  condition is never met → Amulet does NOT trigger
- Result: with Spelunking + Amulet, land enters untapped (1 tap only)
- Bible EC-02 confirms this

## BOUNCE LANDS — MANDATORY TRIGGER (CR 603.2)

Oracle: "When [this] enters, return a land you control to its owner's hand."
- MANDATORY — must return a land (if you control one)
- If you control no other lands, must return ITSELF
- Enters tapped (without Amulet/Spelunking)
- With Amulet: enters tapped → Amulet untaps → can tap for mana
  BEFORE bounce trigger resolves (because Amulet trigger goes on stack
  ABOVE the bounce trigger per CR 603.3b player ordering)

### Self-return chain with Amulet:
1. Play bounce (land drop #1) → enters tapped → Amulet untaps → tap for 2
2. Bounce trigger: return itself to hand (uses NO land drop — it's a trigger)
3. Replay bounce (land drop #2, need extra from Grazer/Explore) →
   enters tapped → Amulet untaps → tap for 2 more
4. No more land drops → bounce returns a permanent land
Total: 2 land drops consumed, 2 × Amulet taps = +4 mana

### CR 305.2: Land drops per turn
- Default: 1 per turn
- Grazer ETB: "put a land onto the battlefield" — NOT a land play (special action)
  But it grants +1 land play (the APL models this as max_land_drops += 1)
  Actually re-reading Grazer: "When ~ enters, you may put a land card from
  your hand onto the battlefield." This is a PUT, not a PLAY. It doesn't
  consume a land drop. But it also doesn't GRANT an extra land drop.
  The land just enters via the ETB resolution.

## LOTUS FIELD — MANDATORY SACRIFICE (CR 603.6a)

Oracle: "Hexproof. This land enters tapped. When Lotus Field enters,
sacrifice two lands. {T}: Add three mana of any one color."
- ETB trigger: sacrifice two lands (MANDATORY)
- Can sacrifice any lands including itself? NO — it's already on BF when
  the trigger resolves. But the trigger says "sacrifice two lands" not
  "sacrifice two OTHER lands" — can it sac itself? Actually YES.
  But you'd lose the Lotus, which defeats the purpose.
- Typical play: sac two cheap lands, keep Lotus for the 3 mana
- With Amulet: enters tapped → Amulet untaps → tap for 3 mana →
  THEN sac trigger resolves → sac tapped/empty lands
  (Player orders: Amulet untap on top of stack, sac on bottom)

## SHIFTING WOODLAND — DELIRIUM ACTIVATION (CR 604.2)

Oracle: "{2}{G}{G}, {T}: If there are four or more card types among cards
in your graveyard, this land becomes a copy of target permanent card in
your graveyard until end of turn."
- Activated ability (not triggered)
- Requires delirium (4+ card types in GY)
- Becomes a COPY — gains all characteristics of the target
- Still a LAND in addition to whatever it copies
- When it becomes Analyst: can be sacrificed via Analyst's ability
- When it goes to GY: returns as a land via Analyst sac (it IS a land)

## VESUVA vs ECHOING DEEPS — COPY TIMING (CR 614.12, 706.10)

### Vesuva: "As this land enters, you may choose a land in play"
- Replacement effect — choice made AS it enters (CR 614.1c)
- Can only copy lands ALREADY on the battlefield
- Titan ETB: Vesuva + X simultaneously — Vesuva CANNOT copy X
  (neither is on BF when the choice is made)
- Bible confirms: "Vesuva can only copy a land already in play"

### Echoing Deeps: "As this land enters, you may have it become a copy
of a land card in a graveyard"
- Also replacement effect
- Copies from GRAVEYARD, not battlefield
- Analyst sac: Deeps + Lotus returning simultaneously —
  Deeps CAN copy Lotus because "the game looks ahead to check what a
  card with these effects will enter as while it's still in its current
  zone" (Bible) — both are still in GY when the choice is made
- This is the OPPOSITE of Vesuva because the copy source (GY) is the
  zone the card is currently IN, not the zone it's going TO

## SCAPESHIFT — SIMULTANEOUS ENTRY (CR 614.12b)

Oracle: "Sacrifice any number of lands. Search your library for up to
that many land cards, put them onto the battlefield tapped, then shuffle."
- ALL sacrificed lands go to GY simultaneously
- ALL fetched lands enter BF simultaneously
- ALL triggers from entry go on stack in player-chosen order
- Correct stack order (for Amulet Titan):
  TOP (resolves first): All Amulet untap triggers
  MIDDLE: Bounce return triggers  
  BOTTOM (resolves last): Lotus sac triggers
- After all Amulet triggers resolve: tap all lands for massive mana
- After bounce resolves: TWest goes to hand for transmute
- After Lotus sacs resolve: sacrifice tapped/empty lands (mana already extracted)

## SUMMARY: What the APL Currently Models vs What It Should

### ✅ CORRECTLY MODELED:
1. Amulet as triggered ability (N triggers = N taps)
2. Spelunking as replacement effect (blocks Amulet trigger)
3. Bounce mandatory return trigger
4. Lotus Field sacrifice trigger (with _skip_lotus_sac for Scapeshift/Analyst)
5. Vesuva can't copy simultaneous entry (checks BF only)
6. Echoing Deeps CAN copy GY lands during simultaneous return (checks _lands_in_gy)
7. Vestige ETB is independent of Amulet (always adds 1 any color)
8. Tolaria West enters tapped, produces {U}
9. Shifting Woodland delirium activation
10. Sequential processing gives correct TOTAL mana (same as simultaneous)

### ⚠️ APPROXIMATED (correct enough for goldfish):
1. Trigger ordering is sequential not simultaneous — net mana is the same
   but the CHOICE of which land to bounce differs. Fixed via priority system:
   - Never bounce Woodland when loop is close (priority 9)
   - Never bounce Lotus (priority 9)
   - Prefer bouncing Forest/TWest (priority 0/-1)
2. Lotus sac is skipped during Scapeshift/Analyst returns — in real MTG,
   the player orders sac triggers LAST so all mana is extracted first.
   Skip achieves the same result (all lands stay on BF and produce mana).
3. Self-return chain: modeled via _land_drops_used counter.
   In real MTG, each bounce self-return is a trigger (not a land play).
   But the REPLAY of the bounce from hand IS a land play.

### ❌ NOT YET MODELED (potential improvements):
1. Optimal bounce return when multiple bounces enter simultaneously
   (Analyst sac with 3+ bounces — currently each bounces independently
   in order; should choose ALL returns optimally as a group)
2. Priority windows between Amulet triggers (tap-between-resolves)
   Currently modeled as one bulk untap+tap per land. With 2+ Amulets,
   the correct model is: enter tapped → Amulet #1 resolves → untap →
   tap for mana → Amulet #2 resolves → untap → tap again.
   The APL already does this (N taps per N Amulets) so it's correct.
3. Responding to triggers with instants (Pact in response to Saga Ch III,
   Pact in response to bounce trigger, etc.)
   In goldfish, this rarely matters — no opponent to surprise.
