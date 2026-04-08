"""
ml/win_prob_model.py — Win probability model trained on per-turn board state snapshots

The key insight: ML is only useful if it learns something the heuristic doesn't know.
The heuristic knows: our_kill_turn < opp_kill_turn → win.
ML can learn: "Thalia on T2 vs Dimir Tempo is worth +X% win prob" — context-sensitive
patterns the race model can't capture.

Training data: per-turn snapshots from 20k+ games
Features (per turn):
  - turn_number, damage_dealt, creatures_in_play, total_power
  - lands_in_play, hand_size, energy, mulligans
  - has_thalia, has_champion, has_lieutenant, has_adeline, has_guide_of_souls
  - has_cavern_of_souls, has_esper_sentinel, has_kytheon
  - hand_creatures, hand_lands
  - opponent archetype (one-hot)
  - opp_avg_kill_turn (their speed)

Label: did_win (1/0) — whether this game was eventually won
"""

import json, os, pickle
import numpy as np

ARCHETYPE_ENCODING = {
    "dimir reanimator": 0, "lotus combo": 1, "dimir tempo": 2,
    "cephalid breakfast": 3, "eldrazi stompy": 4, "sneak and show": 5,
    "mono red painter": 6, "doomsday": 7, "izzet delver": 8,
    "death and taxes": 9, "bant nadu": 10, "four-color": 11,
    "jeskai control": 12, "mono red aggro": 13, "mono red prison": 14,
    "unknown": 15,
}
N_ARCHETYPES = len(ARCHETYPE_ENCODING)

SNAPSHOT_KEYS = [
    "turn", "damage_dealt", "creatures_in_play", "total_power",
    "lands_in_play", "hand_size", "life", "energy", "mulligans",
    "has_thalia,_guardian_of_thraben", "has_champion_of_the_parish",
    "has_thalia's_lieutenant", "has_adeline,_resplendent_cathar",
    "has_guide_of_souls", "has_cavern_of_souls",
    "has_esper_sentinel", "has_kytheon,_hero_of_akros",
    "hand_creatures", "hand_lands",
]


def snapshot_to_features(snap: dict, arch_enc: int, opp_avg_kill: float) -> list:
    """Convert a turn snapshot to ML feature vector."""
    base = [snap.get(k, 0) for k in SNAPSHOT_KEYS]
    # Archetype one-hot
    arch_oh = [1 if i == arch_enc else 0 for i in range(N_ARCHETYPES)]
    # Opponent speed
    return base + arch_oh + [opp_avg_kill]


FEATURE_DIM = len(SNAPSHOT_KEYS) + N_ARCHETYPES + 1


def collect_training_data(n_games=20000, seed=42,
                          save_path="data/win_prob_training_v2.json"):
    """
    Collect per-turn snapshot training data.
    Each game produces T snapshots (one per turn), all labeled with the final outcome.
    """
    import random
    from data.deck import load_deck_from_file
    from apl.humans import HumansAPL
    from engine.runner import run_simulation
    from sim_bridge import ARCHETYPE_CLOCKS, _infer_archetype_key, avg_kill_turn

    main_deck, _ = load_deck_from_file("decks/humans_legacy.txt")
    archetypes   = [k for k in ARCHETYPE_ENCODING if k != "unknown"]
    games_each   = max(1, n_games // len(archetypes))
    rng          = random.Random(seed)
    X, y         = [], []

    print(f"Collecting {n_games} games ({games_each}/archetype), "
          f"per-turn snapshots...\n")

    for arch in archetypes:
        apl = HumansAPL()
        try:
            apl.set_opponent(arch, on_play=True)
        except Exception:
            pass

        sim      = run_simulation(apl, main_deck, n=games_each,
                                  on_play=True, seed=seed, save_logs=True)
        arch_enc = ARCHETYPE_ENCODING[arch]

        opp_key     = _infer_archetype_key(arch)
        opp_dist    = ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"])
        opp_avg     = avg_kill_turn(opp_dist)
        opp_turns   = sorted(opp_dist.keys())
        opp_weights = [opp_dist[t] for t in opp_turns]
        opp_total   = sum(opp_weights)

        wins = 0
        for game_log in sim.game_logs:
            # Sample opponent kill turn
            r = rng.random() * opp_total
            cumul, opp_kill = 0, opp_turns[-1]
            for t, w in zip(opp_turns, opp_weights):
                cumul += w
                if r <= cumul:
                    opp_kill = t
                    break

            won = 1 if game_log.kill_turn > 0 and game_log.kill_turn <= opp_kill else 0
            wins += won

            # One training sample per turn snapshot
            for snap in game_log.turn_snapshots:
                feat = snapshot_to_features(snap, arch_enc, opp_avg)
                X.append(feat)
                y.append(won)

        wr = wins / max(1, games_each) * 100
        print(f"  {arch:<30} {games_each}g  win%={wr:.1f}%  "
              f"snapshots={len(X):,}")

    print(f"\nTotal: {len(X):,} samples from {n_games} games")
    print(f"Feature dimension: {FEATURE_DIM}")
    print(f"Win rate: {sum(y)/len(y)*100:.1f}%")

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w') as f:
        json.dump({"X": X, "y": y, "feature_dim": FEATURE_DIM,
                   "feature_keys": SNAPSHOT_KEYS}, f)
    print(f"Saved to {save_path}")
    return X, y


def train_model(X, y, model_type="gbm"):
    """Train win probability model. GBM recommended — handles mixed features well."""
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score, brier_score_loss
        from sklearn.calibration import CalibratedClassifierCV
    except ImportError:
        print("pip install scikit-learn --break-system-packages")
        return None

    Xa = np.array(X, dtype=float)
    ya = np.array(y, dtype=int)
    Xtr, Xte, ytr, yte = train_test_split(Xa, ya, test_size=0.2, random_state=42)

    print(f"\nTraining {model_type} on {len(Xtr):,} samples...")

    if model_type == "gbm":
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=20, random_state=42
        )
    elif model_type == "rf":
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=10,
            n_jobs=-1, random_state=42
        )
    else:
        from sklearn.neural_network import MLPClassifier
        model = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32), activation='relu',
            max_iter=500, random_state=42, early_stopping=True
        )

    model.fit(Xtr, ytr)

    yp    = model.predict(Xte)
    yprob = model.predict_proba(Xte)[:, 1]
    acc   = accuracy_score(yte, yp)
    auc   = roc_auc_score(yte, yprob)
    brier = brier_score_loss(yte, yprob)

    print(f"  Accuracy:  {acc:.4f}")
    print(f"  ROC-AUC:   {auc:.4f}  (1.0 = perfect, 0.5 = random)")
    print(f"  Brier:     {brier:.4f}  (0.0 = perfect calibration)")
    print(f"  Train/Test: {len(Xtr):,} / {len(Xte):,}")

    # Feature importance (if available)
    if hasattr(model, 'feature_importances_'):
        all_names = (SNAPSHOT_KEYS
                     + [f"vs_{a.replace(' ','_')}" for a in ARCHETYPE_ENCODING]
                     + ["opp_avg_kill"])
        top = sorted(zip(all_names, model.feature_importances_),
                     key=lambda x: -x[1])[:15]
        print(f"\n  Top 15 features:")
        for name, imp in top:
            bar = "█" * int(imp * 200)
            print(f"    {name:<45} {imp:.4f}  {bar}")

    return model


def save_model(model, path="data/win_prob_model_v2.pkl"):
    with open(path, 'wb') as f: pickle.dump(model, f)
    print(f"\nSaved to {path}")


def load_model(path="data/win_prob_model_v2.pkl"):
    if not os.path.exists(path): return None
    with open(path, 'rb') as f: return pickle.load(f)


def predict_win_prob(snap: dict, opp_archetype: str, model=None) -> float:
    """
    Predict win probability from a mid-game board state snapshot.
    This is the live inference path called during APL decision-making.
    """
    if model is None:
        model = load_model()
    if model is None:
        return 50.0  # no model — return 50%

    from sim_bridge import avg_kill_turn, ARCHETYPE_CLOCKS, _infer_archetype_key
    arch_enc = ARCHETYPE_ENCODING.get(opp_archetype.lower(), 15)
    opp_key  = _infer_archetype_key(opp_archetype)
    opp_avg  = avg_kill_turn(ARCHETYPE_CLOCKS.get(opp_key, ARCHETYPE_CLOCKS["unknown"]))
    feat     = np.array([snapshot_to_features(snap, arch_enc, opp_avg)])
    prob     = model.predict_proba(feat)[0][1]
    return round(prob * 100, 1)


if __name__ == "__main__":
    import argparse, sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    ap = argparse.ArgumentParser()
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--train",   action="store_true")
    ap.add_argument("--games",   type=int, default=20000)
    ap.add_argument("--model",   default="gbm", choices=["gbm", "rf", "nn"])
    ap.add_argument("--data",    default="data/win_prob_training_v2.json")
    args = ap.parse_args()

    if args.collect:
        collect_training_data(n_games=args.games, save_path=args.data)
    elif args.train:
        if not os.path.exists(args.data):
            print(f"Run --collect first (data not found: {args.data})")
        else:
            with open(args.data) as f:
                d = json.load(f)
            m = train_model(d["X"], d["y"], args.model)
            if m:
                save_model(m)
    else:
        ap.print_help()
