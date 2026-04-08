"""Step 3: Train Modern Boros Energy model (format transfer demo)."""
import sys
sys.path.insert(0, r'E:\vscode ai project\mtg-sim')
from ml.format_transfer import train_and_save_format_model

model, path = train_and_save_format_model(
    deck_name='BorosEnergy',
    format_name='modern',
    n_games=10000,
    model_type='gbm',
)
print(f'Modern model saved: {path}')
