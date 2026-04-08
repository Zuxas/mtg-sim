"""
ml/run_pipeline.py — Full ML pipeline runner
1. Collect richer v3 training data (milestone features)
2. Train GBM model
3. Run RL exploration iteration
4. Train Modern format model for Boros Energy
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mtg-meta-analyzer'))

STEP = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# ── Step 1: Collect v3 data ────────────────────────────────────────────────
if STEP in (0, 1):
    print("\n" + "="*60)
    print("STEP 1: Collecting v3 training data (richer features)")
    print("="*60)
    from ml.win_prob_model import collect_training_data, train_model, save_model
    X, y = collect_training_data(n_games=20000,
                                  save_path='data/win_prob_training_v3.json')
    print(f"\nTraining on {len(X):,} samples...")
    m = train_model(X, y, model_type='gbm')
    if m:
        save_model(m, 'data/win_prob_model_v3.pkl')
        # Also update the live model
        save_model(m, 'data/win_prob_model_v2.pkl')
    print("Step 1 complete.")

# ── Step 2: RL iteration ───────────────────────────────────────────────────
if STEP in (0, 2):
    print("\n" + "="*60)
    print("STEP 2: RL exploration (epsilon=0.20, 3 iterations x 3k games)")
    print("="*60)
    from ml.rl_trainer import rl_training_loop
    rl_training_loop(
        n_iterations=3,
        games_per_iter=3000,
        epsilon_start=0.25,
        epsilon_end=0.10,
        model_path='data/win_prob_model_v2.pkl',
        data_path='data/win_prob_training_v3.json',
        seed=99,
    )
    print("Step 2 complete.")

# ── Step 3: Modern format model ────────────────────────────────────────────
if STEP in (0, 3):
    print("\n" + "="*60)
    print("STEP 3: Modern model for Boros Energy")
    print("="*60)
    from ml.format_transfer import train_and_save_format_model
    train_and_save_format_model('BorosEnergy', 'modern', n_games=10000)
    print("Step 3 complete.")

print("\nAll steps complete.")
