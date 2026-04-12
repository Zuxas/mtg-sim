# CRITICAL SESSION STATE — April 11 2026
# The git checkout WIPED all 14 bug fixes from this session.
# The APL is back to 976 lines (original pre-session version).
# 
# ALL of the following need to be re-applied from scratch:
# 
# 1. gs.tap_lands() bypass — custom run_game() with _tap_all_lands_for_mana()
# 2. Missing card names (Selesnya Sanctuary, Snow-Covered Forest, Ghost Quarter)
# 3. Main phase → greedy loop (while-loop instead of linear priority)
# 4. Land play value (Hanweir priority 150 for haste, bounce 200 for chain)
# 5. _titan_has_haste never reset — added to reset_turn()
# 6. Double-counting damage — removed from _titan_attack, use KWTag.HASTE
# 7. Haste from pre-existing Hanweir on BF (not just fetched)
# 8. Hanweir protection (never tapped, never bounced, priority 9)
# 9. Mulligan fix (keep 5-land hands with action, patterns F/G/H)
# 10. Missing keep patterns (Rumble+bounce+threat, multiple bounce+threat)
# 11. Saga Ch II Constructs (free damage from artifact creature tokens)
# 12. Icetill Explorer (extra land drop + play from GY)
# 13. Saga Ch III fix (upkeep() never called → added self.upkeep(gs) to run_game)
# 14. Bounce self-return (core mechanic, was explicitly blocked)
#
# PLUS these NEW features from the Titan Bible audit (never implemented):
# 15. Mycosynth Gardens (add to deck + copy Amulet for {1})
# 16. Scapeshift deterministic kill (1 Amulet + 4 lands → Shift→Lotus→TWest→Pact→Analyst→loop)
# 17. Analyst infinite loop as WIN CONDITION (not just ramp)
# 18. Titan 20+ branch decision tree for fetches
# 19. Mirrorpool Titan copy chains (2-4 ETBs per turn)
# 20. Shifting Woodland delirium activation as attack threat
# 21. Multiple bounce replays per turn (chain 3-4 self-returns)
# 22. Pact safety checks (only cast if can win or pay upkeep)
#
# RECOMMENDATION FOR NEXT SESSION:
# Do NOT try to patch the 976-line file. Instead:
# 1. Read docs/amulet_titan_bible_audit.md (full rewrite spec)
# 2. Write a completely new amulet_titan.py from scratch using the Bible knowledge
# 3. Use Sonnet Extended for the bulk code writing
# 4. Target: 4000+ lines with all 22 items above
# 5. Test with 5000 games, target avg T5-6 kill
