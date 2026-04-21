"""
ml/format_transfer.py — Train win prob models for any format/deck combination

The same pipeline works for any format — just swap in:
  - A different deck (from playbooks)
  - A different format's archetype list (from MetaBridge)
  - Different opponent clocks (from ARCHETYPE_CLOCKS)

Usage:
    python ml/format_transfer.py --deck "BorosEnergy" --format modern --games 20000
    python ml/format_transfer.py --deck "GolgariYawgmoth" --format modern --games 20000
    python ml/format_transfer.py --list-decks
"""

import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def collect_format_data(
    deck_name:   str,
    format_name: str  = "modern",
    n_games:     int  = 20000,
    seed:        int  = 42,
    top_n:       int  = 12,
) -> tuple[list, list]:
    """Collect training data for any deck vs its format's field."""
    import random
    from apl.playbook_parser import load_all_playbooks, load_all_tac_guides, find_playbook
    from apl.generic_apl import generic_from_playbook
    from sim_any_deck import load_deck_from_playbook
    from engine.runner import run_simulation
    from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn
    from ml.win_prob_model import ARCHETYPE_ENCODING, SNAPSHOT_KEYS, snapshot_to_features

    # Load deck
    pbs = {**load_all_playbooks(), **load_all_tac_guides()}
    pb  = find_playbook(deck_name, pbs)
    if not pb:
        raise ValueError(f"Playbook not found: {deck_name}")

    main_deck, _ = load_deck_from_playbook(pb)
    if not main_deck:
        raise ValueError(f"Could not build deck for: {deck_name}")

    apl = generic_from_playbook(pb)
    print(f"Deck: {deck_name} ({len(main_deck)} cards)  APL: {apl.name}")

    # Get format field
    try:
        from meta_bridge import MetaBridge
        bridge = MetaBridge(format_name=format_name, min_matches=10)
        field  = bridge.field_shares(top_n=top_n)
        print(f"Field: top {top_n} {format_name.upper()} archetypes")
    except Exception as e:
        print(f"MetaBridge unavailable ({e}) — using ARCHETYPE_CLOCKS directly")
        field = {k: 1/10 for k in list(ARCHETYPE_CLOCKS.keys())[:10]}

    rng = random.Random(seed)
    archetypes = list(field.keys())
    games_each = max(1, n_games // len(archetypes))
    X, y = [], []

    print(f"\nCollecting {n_games} games ({games_each}/archetype)...")
    for arch in archetypes:
        opp_key  = _infer_archetype_key(arch)
        opp_dist = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"])
        opp_avg  = avg_kill_turn(opp_dist)
        # Use format-specific arch encoding or hash it
        arch_enc = hash(arch) % 16

        opp_turns   = sorted(opp_dist.keys())
        opp_weights = [opp_dist[t] for t in opp_turns]
        opp_total   = sum(opp_weights)

        sim = run_simulation(apl, main_deck, n=games_each,
                             on_play=True, seed=seed, save_logs=True)

        wins = 0
        for game_log in sim.game_logs:
            r = rng.random() * opp_total
            cumul, opp_kill = 0, opp_turns[-1]
            for t, w in zip(opp_turns, opp_weights):
                cumul += w
                if r <= cumul:
                    opp_kill = t
                    break

            won = 1 if game_log.kill_turn > 0 and game_log.kill_turn <= opp_kill else 0
            wins += won

            for snap in game_log.turn_snapshots:
                feat = snapshot_to_features(snap, arch_enc, opp_avg)
                X.append(feat)
                y.append(won)

        wr = wins / max(1, games_each) * 100
        print(f"  {arch:<35} win%={wr:.1f}%  opp_T={opp_avg:.1f}")

    print(f"\n{deck_name} model: {len(X):,} samples  "
          f"win%={sum(y)/len(y)*100:.1f}%")
    return X, y


def train_and_save_format_model(
    deck_name:   str,
    format_name: str  = "modern",
    n_games:     int  = 20000,
    model_type:  str  = "gbm",
):
    """Full pipeline: collect → train → save for any deck/format."""
    from ml.win_prob_model import train_model

    # Data path per deck
    safe_name  = deck_name.lower().replace(" ", "_").replace("'", "")
    data_path  = f"data/ml_{safe_name}_{format_name}.json"
    model_path = f"data/ml_{safe_name}_{format_name}.pkl"

    X, y = collect_format_data(deck_name, format_name, n_games)

    os.makedirs("data", exist_ok=True)
    with open(data_path, 'w') as f:
        json.dump({"X": X, "y": y, "deck": deck_name, "format": format_name}, f)
    print(f"Data saved: {data_path}")

    model = train_model(X, y, model_type=model_type)
    if model:
        import pickle
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"Model saved: {model_path}")

    return model, model_path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck",       default="BorosEnergy")
    ap.add_argument("--format",     default="modern")
    ap.add_argument("--games",      type=int, default=20000)
    ap.add_argument("--model",      default="gbm")
    ap.add_argument("--list-decks", action="store_true")
    args = ap.parse_args()

    if args.list_decks:
        from apl.playbook_parser import load_all_playbooks
        pbs = load_all_playbooks()
        print("Decks available for ML training:")
        for name, pb in sorted(pbs.items()):
            mb = sum(pb.mainboard.values()) if pb.mainboard else 0
            if mb >= 55:
                print(f"  {name}  ({mb} cards)")
    else:
        train_and_save_format_model(args.deck, args.format, args.games, args.model)
