"""Research-only matched forecasts: rolling windows, regularization and features.

Existing return columns and target labels are kept unchanged; all variants
share test dates and the original H+1 purged walk-forward splits.
"""
import re
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from backtesting import generate_walk_forward_predictions
from ml_final_validation import build_final_validation_report
from walk_forward import describe_fold, generate_walk_forward_splits

BASELINES = ("zero_return", "historical_mean", "momentum")
RETURN_FEATURE = re.compile(r"^(?:return_\d+d|relative_return_\d+d|benchmark_return_\d+d|roc_12)$")


def add_volatility_normalized_features(X, *, floor=0.005):
    """Add trailing-vol-normalized features only; preserve raw returns."""
    if "volatility_20d" not in X:
        raise ValueError("Missing volatility_20d.")
    volatility = pd.to_numeric(X["volatility_20d"], errors="coerce")
    if not np.isfinite(volatility.to_numpy(dtype=float)).all() or (volatility < 0).any():
        raise ValueError("Invalid historical trailing volatility.")
    result = X.copy()
    denominator = volatility.clip(lower=floor)
    columns = [name for name in X if RETURN_FEATURE.fullmatch(name)]
    if not columns:
        raise ValueError("No return columns to normalize.")
    for name in columns:
        values = pd.to_numeric(X[name], errors="coerce")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"Invalid return column: {name}")
        result[f"{name}_by_vol20"] = values / denominator
    return result


def rolling_training_folds(base_folds, window):
    if window is not None and (
        isinstance(window, bool) or not isinstance(window, int) or window <= 0
    ):
        raise ValueError("Training window must be a positive integer or None.")
    folds = []
    for original in base_folds:
        fold = dict(original)
        if window is not None:
            fold["train_start"] = max(fold["train_start"], fold["train_end"] - window)
            fold["train_size"] = fold["train_end"] - fold["train_start"]
        if fold["train_end"] > fold["test_start"] - fold["gap"]:
            raise ValueError("Training-label purge was violated.")
        folds.append(fold)
    return folds


def ridge_factory(alpha):
    if alpha not in (100, 300, 1000):
        raise ValueError("Use only predeclared regularization parameters.")
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=float(alpha), fit_intercept=False)),
    ])


def evaluate_pipeline_grid(feature_sets, y, *, horizon, min_train=500,
                           test_size=100, windows=(None, 500, 750),
                           alphas=(100, 300, 1000)):
    """Development diagnostics only; NEVER an independent final holdout."""
    if "price_volume" not in feature_sets:
        raise ValueError("A price_volume reference feature set is required.")
    X_ref = feature_sets["price_volume"]
    if not X_ref.index.is_unique or not X_ref.index.is_monotonic_increasing:
        raise ValueError("Feature dates must be unique and chronological.")
    if not X_ref.index.equals(y.index):
        raise ValueError("Target dates are misaligned.")
    for name, X in feature_sets.items():
        if not X.index.equals(X_ref.index):
            raise ValueError(f"Unmatched dates in {name}.")
    if not alphas or any(a not in (100, 300, 1000) for a in alphas):
        raise ValueError("Invalid predeclared candidate grid.")
    if any(w is not None and w < min_train for w in windows):
        raise ValueError("Rolling windows must be at least min_train.")
    folds = generate_walk_forward_splits(
        X_ref, y, minimum_train_size=min_train, test_size=test_size,
        horizon=horizon, step_size=test_size,
    )
    if len(folds) < 2:
        raise ValueError("At least two valid matched folds are required.")
    reference_baseline = None
    candidates = []
    for feature_name, X in feature_sets.items():
        for window in windows:
            matched_folds = rolling_training_folds(folds, window)
            described = [describe_fold(X, fold) for fold in matched_folds]
            for alpha in alphas:
                predictions = generate_walk_forward_predictions(
                    X, y, matched_folds, lambda a=alpha: ridge_factory(a),
                )
                report = build_final_validation_report(
                    X, y, described, predictions, "zero_anchor_ridge", horizon,
                )
                metrics = report["metrics"]
                baseline = {key: metrics[key] for key in BASELINES}
                if reference_baseline is None:
                    reference_baseline = baseline
                else:
                    # Historical mean is correctly re-estimated for each
                    # rolling training window; zero and momentum must match.
                    for key in ("zero_return", "momentum"):
                        for field in ("mae", "rmse", "observations"):
                            if not np.isclose(
                                baseline[key][field], reference_baseline[key][field],
                                atol=1e-12, rtol=0,
                            ):
                                raise ValueError(f"Baseline mismatch: {key} {field}.")
                best_mae, best_name = min(
                    (baseline[key]["mae"], key) for key in BASELINES
                )
                model = metrics["selected_model"]
                candidates.append({
                    "feature_set": feature_name,
                    "training_window": "expanding" if window is None else window,
                    "ridge_alpha": alpha,
                    "folds": len(folds),
                    "out_of_sample_observations": model["observations"],
                    "oos_start": described[0]["test_start_date"],
                    "oos_end": described[-1]["test_end_date"],
                    "mae_percent": round(model["mae"] * 100, 5),
                    "rmse_percent": round(model["rmse"] * 100, 5),
                    "balanced_directional_accuracy_percent": (
                        round(model["balanced_directional_accuracy"] * 100, 3)
                        if model["balanced_directional_accuracy"] is not None else None
                    ),
                    "negative_specificity_percent": (
                        round(model["negative_specificity"] * 100, 3)
                        if model["negative_specificity"] is not None else None
                    ),
                    "best_baseline": best_name,
                    "best_baseline_mae_percent": round(best_mae * 100, 5),
                    "improvement_over_best_baseline_pp":
                        round((best_mae - model["mae"]) * 100, 5),
                    "beats_all_baselines": all(
                        model["mae"] < baseline[key]["mae"] for key in BASELINES
                    ),
                    "research_only": True,
                })
    return {
        "folds": len(folds), "candidates": candidates,
        "same_test_dates_and_targets": True,
        "historical_window_role": "development_diagnostic_not_final_holdout",
        "note": "Inspecting these folds does not establish independent predictive skill.",
    }
