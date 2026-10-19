"""Final walk-forward validation summary for financial return models.

This module evaluates already-generated out-of-sample predictions and compares
those predictions with simple baselines evaluated on the same dates. It does
not train models or make investment recommendations.
"""

import math

import numpy as np
import pandas as pd


MODEL_LABELS = {
    "linear_regression": "Linear Regression",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

BASELINE_LABELS = {
    "zero_return": "Zero Return",
    "historical_mean": "Historical Mean",
    "momentum": "Momentum",
}


def _safe_float(value):
    """Convert finite numeric values to JSON-safe floats."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _ratio(numerator, denominator):
    if denominator is None or denominator == 0:
        return None
    if numerator is None:
        return None
    return _safe_float(numerator / denominator)


def calculate_forecast_metrics(y_true, y_pred):
    """Regression and direction metrics over out-of-sample forecast dates.

    Return values such as MAE/RMSE are expressed as decimal returns; 0.02
    means two percentage points of return error.
    """
    true_values = np.asarray(y_true, dtype=float).reshape(-1)
    predicted_values = np.asarray(y_pred, dtype=float).reshape(-1)

    if len(true_values) != len(predicted_values):
        raise ValueError("Actual and predicted values must have equal length.")

    valid = np.isfinite(true_values) & np.isfinite(predicted_values)
    true_values = true_values[valid]
    predicted_values = predicted_values[valid]

    if not len(true_values):
        return {
            "observations": 0,
            "mae": None,
            "rmse": None,
            "directional_accuracy": None,
            "balanced_directional_accuracy": None,
            "positive_precision": None,
            "positive_recall": None,
            "positive_f1": None,
            "negative_specificity": None,
            "actual_positive_rate": None,
            "predicted_positive_rate": None,
            "confusion": {"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0},
        }

    actual_positive = true_values > 0
    predicted_positive = predicted_values > 0

    tp = int(np.sum(actual_positive & predicted_positive))
    tn = int(np.sum(~actual_positive & ~predicted_positive))
    fp = int(np.sum(~actual_positive & predicted_positive))
    fn = int(np.sum(actual_positive & ~predicted_positive))

    precision = _ratio(tp, tp + fp)
    recall = _ratio(tp, tp + fn)
    specificity = _ratio(tn, tn + fp)

    if precision is not None and recall is not None and precision + recall > 0:
        f1 = _safe_float(2 * precision * recall / (precision + recall))
    else:
        f1 = None

    balanced_values = [value for value in (recall, specificity) if value is not None]
    balanced_accuracy = _safe_float(np.mean(balanced_values)) if balanced_values else None

    return {
        "observations": int(len(true_values)),
        "mae": _safe_float(np.mean(np.abs(true_values - predicted_values))),
        "rmse": _safe_float(np.sqrt(np.mean((true_values - predicted_values) ** 2))),
        "directional_accuracy": _safe_float(np.mean(actual_positive == predicted_positive)),
        "balanced_directional_accuracy": balanced_accuracy,
        "positive_precision": precision,
        "positive_recall": recall,
        "positive_f1": f1,
        "negative_specificity": specificity,
        "actual_positive_rate": _safe_float(np.mean(actual_positive)),
        "predicted_positive_rate": _safe_float(np.mean(predicted_positive)),
        "confusion": {
            "true_positive": tp,
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
        },
    }


def generate_walk_forward_baseline_predictions(X, y, folds, horizon):
    """Create baseline predictions for the exact walk-forward test dates.

    Historical mean is refitted from each fold's training labels only.
    Momentum uses only the currently observed horizon return feature.
    """
    momentum_column = f"return_{horizon}d"
    if momentum_column not in X.columns:
        raise ValueError(
            f"Required momentum feature '{momentum_column}' is not available."
        )

    baseline_parts = {
        "zero_return": [],
        "historical_mean": [],
        "momentum": [],
    }

    for fold in folds:
        train_start = fold["train_start"]
        train_end = fold["train_end"]
        test_start = fold["test_start"]
        test_end = fold["test_end"]

        train_target = y.iloc[train_start:train_end]
        X_test = X.iloc[test_start:test_end]
        test_index = X_test.index

        if train_target.empty or X_test.empty:
            continue

        baseline_parts["zero_return"].append(
            pd.Series(0.0, index=test_index, dtype=float)
        )
        baseline_parts["historical_mean"].append(
            pd.Series(float(train_target.mean()), index=test_index, dtype=float)
        )
        baseline_parts["momentum"].append(
            pd.to_numeric(X_test[momentum_column], errors="coerce").astype(float)
        )

    predictions = {}
    for key, parts in baseline_parts.items():
        if parts:
            series = pd.concat(parts).sort_index()
            series = series[~series.index.duplicated(keep="last")]
            predictions[key] = series.rename(key)
        else:
            predictions[key] = pd.Series(dtype=float, name=key)

    return predictions


def _compare_metrics(model_metrics, baseline_metrics, baseline_key):
    model_mae = model_metrics.get("mae")
    baseline_mae = baseline_metrics.get("mae")
    model_rmse = model_metrics.get("rmse")
    baseline_rmse = baseline_metrics.get("rmse")
    model_direction = model_metrics.get("directional_accuracy")
    baseline_direction = baseline_metrics.get("directional_accuracy")

    mae_improvement = (
        _safe_float(baseline_mae - model_mae)
        if model_mae is not None and baseline_mae is not None
        else None
    )
    rmse_improvement = (
        _safe_float(baseline_rmse - model_rmse)
        if model_rmse is not None and baseline_rmse is not None
        else None
    )
    direction_difference = (
        _safe_float(model_direction - baseline_direction)
        if model_direction is not None and baseline_direction is not None
        else None
    )

    return {
        "baseline": baseline_key,
        "mae_improvement": mae_improvement,
        "mae_improvement_percent": _ratio(mae_improvement, baseline_mae),
        "beats_baseline_on_mae": (
            bool(model_mae < baseline_mae)
            if model_mae is not None and baseline_mae is not None
            else None
        ),
        "rmse_improvement": rmse_improvement,
        "beats_baseline_on_rmse": (
            bool(model_rmse < baseline_rmse)
            if model_rmse is not None and baseline_rmse is not None
            else None
        ),
        "directional_accuracy_difference": direction_difference,
        "beats_baseline_on_directional_accuracy": (
            bool(model_direction > baseline_direction)
            if model_direction is not None and baseline_direction is not None
            else None
        ),
    }


def build_final_validation_report(X, y, folds, model_predictions, model_key, horizon):
    """Build a transparent validation report from walk-forward predictions.

    The model prediction series must contain out-of-sample predictions only,
    such as the output from backtesting.generate_walk_forward_predictions.
    """
    if not isinstance(model_predictions, pd.Series):
        model_predictions = pd.Series(model_predictions, index=X.index[-len(model_predictions):])

    model_predictions = pd.to_numeric(model_predictions, errors="coerce")
    model_predictions = model_predictions[~model_predictions.index.duplicated(keep="last")]

    baseline_predictions = generate_walk_forward_baseline_predictions(
        X=X,
        y=y,
        folds=folds,
        horizon=horizon,
    )

    aligned = pd.DataFrame({
        "actual": y,
        "selected_model": model_predictions,
        "zero_return": baseline_predictions["zero_return"],
        "historical_mean": baseline_predictions["historical_mean"],
        "momentum": baseline_predictions["momentum"],
    })
    aligned = aligned.replace([np.inf, -np.inf], np.nan).dropna()

    if aligned.empty:
        raise ValueError(
            "No aligned out-of-sample forecast values are available for validation."
        )

    metrics = {
        "selected_model": calculate_forecast_metrics(
            aligned["actual"], aligned["selected_model"]
        ),
        "zero_return": calculate_forecast_metrics(
            aligned["actual"], aligned["zero_return"]
        ),
        "historical_mean": calculate_forecast_metrics(
            aligned["actual"], aligned["historical_mean"]
        ),
        "momentum": calculate_forecast_metrics(
            aligned["actual"], aligned["momentum"]
        ),
    }

    comparisons = []
    for baseline_key in ("zero_return", "historical_mean", "momentum"):
        comparisons.append({
            "baseline_name": BASELINE_LABELS[baseline_key],
            **_compare_metrics(
                metrics["selected_model"],
                metrics[baseline_key],
                BASELINE_LABELS[baseline_key],
            ),
        })

    fold_metrics = []
    for fold in folds:
        test_index = X.index[fold["test_start"]:fold["test_end"]]
        shared_index = aligned.index.intersection(test_index)
        if shared_index.empty:
            continue

        fold_model_metrics = calculate_forecast_metrics(
            aligned.loc[shared_index, "actual"],
            aligned.loc[shared_index, "selected_model"],
        )
        fold_baseline_metrics = calculate_forecast_metrics(
            aligned.loc[shared_index, "actual"],
            aligned.loc[shared_index, "historical_mean"],
        )

        fold_item = {
            "fold": int(fold["fold"]),
            "observations": int(len(shared_index)),
            "model_metrics": fold_model_metrics,
            "historical_mean_metrics": fold_baseline_metrics,
            "beats_historical_mean_on_mae": (
                fold_model_metrics["mae"] < fold_baseline_metrics["mae"]
                if fold_model_metrics["mae"] is not None and fold_baseline_metrics["mae"] is not None
                else None
            ),
        }
        for date_key in (
            "train_start_date", "train_end_date", "test_start_date", "test_end_date"
        ):
            if date_key in fold:
                fold_item[date_key] = fold[date_key]
        fold_metrics.append(fold_item)

    valid_fold_maes = [
        item["model_metrics"]["mae"]
        for item in fold_metrics
        if item["model_metrics"]["mae"] is not None
    ]
    valid_historical_mean_maes = [
        item["historical_mean_metrics"]["mae"]
        for item in fold_metrics
        if item["historical_mean_metrics"]["mae"] is not None
    ]
    folds_beating_baseline = sum(
        item["beats_historical_mean_on_mae"] is True
        for item in fold_metrics
    )

    selected_label = MODEL_LABELS.get(model_key, model_key)
    selected_metrics = metrics["selected_model"]
    historical_metrics = metrics["historical_mean"]
    comparison_to_mean = _compare_metrics(
        selected_metrics,
        historical_metrics,
        BASELINE_LABELS["historical_mean"],
    )

    if comparison_to_mean["beats_baseline_on_mae"] is True:
        interpretation = (
            f"{selected_label} achieved lower out-of-sample MAE than the Historical Mean "
            f"baseline for the {horizon}-trading-day target on the evaluated walk-forward dates. "
            "This is evidence for this tested period, not proof of future predictive skill."
        )
    else:
        interpretation = (
            f"{selected_label} did not achieve lower out-of-sample MAE than the Historical Mean "
            f"baseline for the {horizon}-trading-day target on the evaluated walk-forward dates. "
            "Do not treat model complexity as evidence of predictive advantage."
        )

    return {
        "protocol": {
            "method": "Expanding-window walk-forward evaluation",
            "target_horizon_trading_days": int(horizon),
            "gap_trading_days": int(horizon),
            "folds_evaluated": int(len(fold_metrics)),
            "out_of_sample_observations": int(len(aligned)),
            "shuffling": False,
            "selected_model": model_key,
            "selected_model_label": selected_label,
        },
        "metrics": metrics,
        "baseline_comparisons": comparisons,
        "fold_stability": {
            "folds_with_valid_mae": len(valid_fold_maes),
            "mean_fold_mae": _safe_float(np.mean(valid_fold_maes)) if valid_fold_maes else None,
            "std_fold_mae": _safe_float(np.std(valid_fold_maes, ddof=1)) if len(valid_fold_maes) > 1 else None,
            "min_fold_mae": _safe_float(np.min(valid_fold_maes)) if valid_fold_maes else None,
            "max_fold_mae": _safe_float(np.max(valid_fold_maes)) if valid_fold_maes else None,
            "folds_beating_historical_mean_on_mae": int(folds_beating_baseline),
            "folds_with_historical_mean_comparison": len(valid_historical_mean_maes),
            "fraction_folds_beating_historical_mean_on_mae": (
                _safe_float(folds_beating_baseline / len(valid_historical_mean_maes))
                if valid_historical_mean_maes else None
            ),
        },
        "fold_metrics": fold_metrics,
        "interpretation": interpretation,
        "limitations": [
            "This report measures historical out-of-sample performance and does not guarantee future results.",
            "Directional accuracy can be misleading when positive and negative target classes are imbalanced; review positive rate, specificity and balanced directional accuracy too.",
            "Multi-day forward-return targets can overlap across adjacent forecast dates, so the forecast observations are not independent.",
            "This report validates the selected model on the supplied walk-forward folds; final investment decisions require additional testing, cost assumptions and risk controls.",
        ],
    }
