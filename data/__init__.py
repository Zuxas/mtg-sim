# Phase 1 — Data layer
# Scryfall fetching is handled by the existing scraper in mtg-meta-analyzer.
# This module provides the Card object and the deck loader.

from data.card import Card, Tag
from data.deck import load_deck_from_text, load_deck_from_file
