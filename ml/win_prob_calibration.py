"""
ml/win_prob_calibration.py -- Probability calibration + reliability check for the
win-probability GBM (Object A: per-game reliability).

ADDITIVE, non-breaking. This module does NOT modify win_prob_model.py, its
train_model() output, the live win_prob_model_v2.pkl, or predict_win_prob().
It sits alongside the raw model:

  * the raw fitted classifier is kept untouched;
  * a CALIBRATED copy is produced and saved to a NEW file
    (data/win_prob_model_v2_calibrated.pkl) -- the live model is left alone;
  * Brier + ECE + a reliability curve are computed BEFORE vs AFTER calibration;
  * a reliability-diagram PNG is written to data/win_prob_calibration.png.

Reliability technique: scikit-learn calibration_curve / CalibratedClassifierCV
(BSD-3, already a project dependency -- see requirements.txt). The IDEA of
validating predicted probabilities against an external ground truth is credited
to ratloop/MatchOutcomeAI (MIT); none of ratloop's code is used here (it has no
calibration code -- verified 2026-06-26). ECE is hand-rolled (sklearn has no
scalar ECE).

Usage:
    python -m ml.win_prob_calibration --selftest      # synthetic math proof
    python -m ml.win_prob_calibration --real          # run on real training data
    python -m ml.win_prob_calibration --real --data data/win_prob_training_v2.json

As a library:
    from ml.win_prob_calibration import (
        expected_calibration_error, calibration_report,
        calibrate_classifier, plot_reliability, run_on_real_data,
    )

ASCII-only terminal output per repo CONVENTIONS.
"""

import os
import pickle

import numpy as np

# Headless plotting: select Agg BEFORE importing pyplot. No GUI / no display.
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from sklearn.calibration import calibration_curve, CalibratedClassifierCV
from sklearn.metrics import brier_score_loss


# --------------------------------------------------------------------------- #
# Core metrics
# --------------------------------------------------------------------------- #
def expected_calibration_error(y_true, y_prob, n_bins=10):
    """
    Hand-rolled Expected Calibration Error using EQUAL-COUNT (quantile) bins,
    matching strategy="quantile" in sklearn's calibration_curve.

    ECE = sum_b (n_b / N) * | mean(y_true in b) - mean(y_prob in b) |

    Returns a float in [0, 1]; 0.0 == perfectly calibrated.
    """
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if y_true.size == 0:
        return 0.0

    # Quantile bin edges; clamp ends to [0,1] and de-duplicate (ties collapse bins).
    edges = np.quantile(y_prob, np.linspace(0.0, 1.0, n_bins + 1))
    edges[0], edges[-1] = 0.0, 1.0
    edges = np.unique(edges)
    n_eff = len(edges) - 1
    if n_eff < 1:
        return 0.0

    # digitize on interior edges -> bin index in [0, n_eff-1]
    idx = np.clip(np.digitize(y_prob, edges[1:-1]), 0, n_eff - 1)

    ece = 0.0
    n = y_true.size
    for b in range(n_eff):
        m = idx == b
        cnt = int(m.sum())
        if cnt:
            ece += (cnt / n) * abs(y_true[m].mean() - y_prob[m].mean())
    return float(ece)


def calibration_report(y_true, y_prob, n_bins=10):
    """
    Compute the Object-A reliability triple for one set of predictions:
      - calibration_curve (strategy="quantile" => equal-count bins)
      - hand-rolled ECE (quantile bins)
      - Brier score (sklearn brier_score_loss)

    Returns a dict: {frac_pos, mean_pred, ece, brier}.
    frac_pos/mean_pred are arrays suitable for a reliability diagram.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    frac_pos, mean_pred = calibration_curve(
        y_true, y_prob, n_bins=n_bins, strategy="quantile"
    )
    return {
        "frac_pos": frac_pos,
        "mean_pred": mean_pred,
        "ece": expected_calibration_error(y_true, y_prob, n_bins=n_bins),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }


# --------------------------------------------------------------------------- #
# Calibration wrapper (keeps the raw model intact)
# --------------------------------------------------------------------------- #
def calibrate_classifier(raw_model, X_cal, y_cal, method=None):
    """
    Wrap an ALREADY-FITTED classifier in CalibratedClassifierCV WITHOUT
    refitting or mutating it. Returns a NEW calibrated estimator; the raw model
    is returned to the caller unchanged.

    method: "isotonic" (default for >~1000 calibration samples; flexible,
            needs data) or "sigmoid" (Platt; safer on tiny data). If None,
            auto-pick: isotonic when len(X_cal) >= 1000 else sigmoid.

    Version-robust: sklearn >= 1.6 deprecated/removed cv="prefit" in favour of
    sklearn.frozen.FrozenEstimator. We try FrozenEstimator first, then fall
    back to cv="prefit" for older sklearn.
    """
    X_cal = np.asarray(X_cal, dtype=float)
    y_cal = np.asarray(y_cal, dtype=int)
    if method is None:
        method = "isotonic" if len(X_cal) >= 1000 else "sigmoid"

    try:
        from sklearn.frozen import FrozenEstimator
        calib = CalibratedClassifierCV(FrozenEstimator(raw_model), method=method)
    except Exception:
        # Older sklearn: prefit path (no FrozenEstimator available).
        calib = CalibratedClassifierCV(raw_model, method=method, cv="prefit")

    calib.fit(X_cal, y_cal)
    return calib


# --------------------------------------------------------------------------- #
# Reliability diagram
# --------------------------------------------------------------------------- #
def plot_reliability(reports, out_path, title="Win-prob reliability"):
    """
    Save a reliability-diagram PNG (Agg backend, no GUI).

    reports: list of (label, report_dict) tuples, where report_dict comes from
    calibration_report(). Each is drawn as observed-WR vs mean-predicted, with
    a y=x perfect-calibration reference.
    """
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="perfect")
    markers = ["o-", "s-", "^-", "d-"]
    for i, (label, rep) in enumerate(reports):
        ax.plot(
            rep["mean_pred"], rep["frac_pos"], markers[i % len(markers)],
            label=f"{label} (Brier={rep['brier']:.4f}, ECE={rep['ece']:.4f})",
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Mean predicted win prob")
    ax.set_ylabel("Observed win rate")
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8)
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path


# --------------------------------------------------------------------------- #
# Real-data driver
# --------------------------------------------------------------------------- #
def run_on_real_data(
    data_path="data/win_prob_training_v2.json",
    model_type="gbm",
    n_bins=10,
    seed=42,
    png_path="data/win_prob_calibration.png",
    save_calibrated_path="data/win_prob_model_v2_calibrated.pkl",
    n_estimators=300,
):
    """
    Honest before/after calibration on real training snapshots.

    A FRESH same-config classifier is trained on a clean 60/20/20
    train/calibrate/test split so the reliability diagram is measured on data
    the calibrator never saw, and so it does not overlap the live pkl's own
    training rows (the live win_prob_model_v2.pkl was trained on 80% of this
    exact file with random_state=42, so reusing it would give an optimistic,
    contaminated Brier). The live pkl and predict_win_prob() are NOT touched.

    Returns a dict of before/after metrics + artifact paths.
    """
    import json
    from sklearn.model_selection import train_test_split

    with open(data_path) as f:
        d = json.load(f)
    X = np.asarray(d["X"], dtype=float)
    y = np.asarray(d["y"], dtype=int)

    # 60 / 20 / 20  train / calibrate / test
    X_tmp, X_te, y_tmp, y_te = train_test_split(
        X, y, test_size=0.20, random_state=seed, stratify=y
    )
    X_tr, X_cal, y_tr, y_cal = train_test_split(
        X_tmp, y_tmp, test_size=0.25, random_state=seed, stratify=y_tmp
    )  # 0.25 * 0.80 = 0.20 overall

    if model_type == "gbm":
        from sklearn.ensemble import GradientBoostingClassifier
        raw = GradientBoostingClassifier(
            n_estimators=n_estimators, max_depth=5, learning_rate=0.05,
            subsample=0.8, min_samples_leaf=20, random_state=seed,
        )
    elif model_type == "rf":
        from sklearn.ensemble import RandomForestClassifier
        raw = RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=10,
            n_jobs=-1, random_state=seed,
        )
    else:
        raise ValueError("model_type must be gbm or rf")

    print(f"[real] training {model_type} raw model on {len(X_tr):,} samples "
          f"(calib={len(X_cal):,}, test={len(X_te):,})...")
    raw.fit(X_tr, y_tr)

    # BEFORE
    p_raw = raw.predict_proba(X_te)[:, 1]
    rep_before = calibration_report(y_te, p_raw, n_bins=n_bins)

    # CALIBRATE (raw model left intact) + AFTER
    method = "isotonic" if len(X_cal) >= 1000 else "sigmoid"
    calib = calibrate_classifier(raw, X_cal, y_cal, method=method)
    p_cal = calib.predict_proba(X_te)[:, 1]
    rep_after = calibration_report(y_te, p_cal, n_bins=n_bins)

    print(f"[real] calibration method: {method}")
    print(f"[real] Brier BEFORE: {rep_before['brier']:.5f}   "
          f"ECE BEFORE: {rep_before['ece']:.5f}")
    print(f"[real] Brier AFTER : {rep_after['brier']:.5f}   "
          f"ECE AFTER : {rep_after['ece']:.5f}")
    d_brier = rep_after["brier"] - rep_before["brier"]
    d_ece = rep_after["ece"] - rep_before["ece"]
    print(f"[real] delta Brier : {d_brier:+.5f}   delta ECE : {d_ece:+.5f}  "
          f"(negative = improvement)")

    png = plot_reliability(
        [("GBM raw", rep_before), ("GBM calibrated", rep_after)],
        png_path, title=f"Win-prob reliability ({model_type}, real data)",
    )
    print(f"[real] wrote reliability PNG -> {png}")

    # Persist the calibrated model ALONGSIDE the raw model (new file only).
    save_calibrated_path = os.path.abspath(save_calibrated_path)
    os.makedirs(os.path.dirname(save_calibrated_path), exist_ok=True)
    with open(save_calibrated_path, "wb") as f:
        pickle.dump(calib, f)
    print(f"[real] wrote calibrated model (alongside raw) -> "
          f"{save_calibrated_path}")
    print("[real] NOTE: live win_prob_model_v2.pkl and predict_win_prob() "
          "were NOT modified.")

    return {
        "method": method,
        "brier_before": rep_before["brier"],
        "brier_after": rep_after["brier"],
        "ece_before": rep_before["ece"],
        "ece_after": rep_after["ece"],
        "png": png,
        "calibrated_model": save_calibrated_path,
    }


# --------------------------------------------------------------------------- #
# Synthetic self-test (proves the math without needing the real model)
# --------------------------------------------------------------------------- #
def _synthetic_self_test(png_path="data/win_prob_calibration_selftest.png",
                         seed=0, n=20000):
    """
    Proof of the calibration math on SYNTHETIC data with a KNOWN ground truth.

    Construction:
      * draw true probabilities p ~ Uniform(0,1);
      * draw outcomes y ~ Bernoulli(p)            (so p is perfectly calibrated);
      * build a DELIBERATELY MISCALIBRATED "model" by distorting p through a
        monotone squashing transform q = p**3 / (p**3 + (1-p)**3)  (overconfident
        S-curve). q ranks identically to p (AUC preserved) but its probabilities
        are wrong -> high ECE / high Brier.
      * fit isotonic calibration (monotone) on a calibration split and evaluate
        on a held-out test split.

    Asserts: calibration strictly reduces BOTH ECE and Brier on the distorted
    predictor, and the perfectly-calibrated p has near-zero ECE. This validates
    expected_calibration_error(), calibration_report(), calibrate_classifier(),
    and plot_reliability() end-to-end -- independent of the real GBM.
    """
    from sklearn.isotonic import IsotonicRegression

    rng = np.random.RandomState(seed)
    p = rng.uniform(0.0, 1.0, size=n)
    y = (rng.uniform(size=n) < p).astype(int)

    # Deliberately miscalibrated predictor (monotone distortion of true p).
    q = p ** 3 / (p ** 3 + (1.0 - p) ** 3)

    # Split into calibration / test.
    half = n // 2
    q_cal, y_cal = q[:half], y[:half]
    q_te, y_te = q[half:], y[half:]
    p_te = p[half:]

    # Sanity: the TRUE probabilities are well-calibrated (near-zero ECE).
    ece_truth = expected_calibration_error(y_te, p_te, n_bins=10)

    # BEFORE: the distorted predictor.
    rep_before = calibration_report(y_te, q_te, n_bins=10)

    # Calibrate the distorted predictor with isotonic regression (1-D analogue
    # of CalibratedClassifierCV(method="isotonic")), fit on calib split only.
    iso = IsotonicRegression(out_of_bounds="clip").fit(q_cal, y_cal)
    q_te_cal = iso.predict(q_te)
    rep_after = calibration_report(y_te, q_te_cal, n_bins=10)

    print("[selftest] ECE of TRUE probabilities (should be ~0):"
          f" {ece_truth:.5f}")
    print(f"[selftest] Brier BEFORE: {rep_before['brier']:.5f}   "
          f"ECE BEFORE: {rep_before['ece']:.5f}")
    print(f"[selftest] Brier AFTER : {rep_after['brier']:.5f}   "
          f"ECE AFTER : {rep_after['ece']:.5f}")

    # Also exercise the full estimator wrapper path on a tiny sklearn model so
    # calibrate_classifier() itself is covered (not just raw isotonic).
    from sklearn.linear_model import LogisticRegression
    Xc = q_cal.reshape(-1, 1)
    Xt = q_te.reshape(-1, 1)
    lr = LogisticRegression().fit(Xc, y_cal)
    wrapped = calibrate_classifier(lr, Xc, y_cal, method="isotonic")
    _ = wrapped.predict_proba(Xt)[:, 1]  # must not raise

    png = plot_reliability(
        [("distorted", rep_before), ("isotonic-calibrated", rep_after)],
        png_path, title="Synthetic self-test reliability",
    )
    print(f"[selftest] wrote PNG -> {png}")

    # Assertions (the actual proof).
    assert ece_truth < 0.02, f"true probs should be calibrated, ECE={ece_truth}"
    assert rep_after["ece"] < rep_before["ece"], (
        f"calibration must reduce ECE: {rep_after['ece']} !< {rep_before['ece']}")
    assert rep_after["brier"] < rep_before["brier"], (
        f"calibration must reduce Brier: "
        f"{rep_after['brier']} !< {rep_before['brier']}")
    assert os.path.getsize(png) > 0, "PNG must be non-empty"
    print("[selftest] PASS: calibration reduced ECE and Brier; math verified.")
    return {
        "ece_truth": ece_truth,
        "brier_before": rep_before["brier"],
        "brier_after": rep_after["brier"],
        "ece_before": rep_before["ece"],
        "ece_after": rep_after["ece"],
        "png": png,
    }


if __name__ == "__main__":
    import argparse
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    ap = argparse.ArgumentParser(description="Win-prob calibration + reliability")
    ap.add_argument("--selftest", action="store_true",
                    help="run synthetic-data math proof (no real model needed)")
    ap.add_argument("--real", action="store_true",
                    help="train + calibrate on real training data")
    ap.add_argument("--data", default="data/win_prob_training_v2.json")
    ap.add_argument("--model", default="gbm", choices=["gbm", "rf"])
    ap.add_argument("--estimators", type=int, default=300)
    args = ap.parse_args()

    if args.selftest:
        _synthetic_self_test()
    elif args.real:
        run_on_real_data(data_path=args.data, model_type=args.model,
                         n_estimators=args.estimators)
    else:
        ap.print_help()
