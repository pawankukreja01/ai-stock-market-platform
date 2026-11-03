"""Conservative, holdout-only diagnostics for experimental stock forecasts.

A numerical forecast is not evidence of a tradable edge. These diagnostics
compare predictions with forecasts that require no machine learning and
report where historical evidence is too thin. The chronological split and
all forecast features are constructed elsewhere.
"""

from datetime import date, datetime

import numpy as np

from ml_final_validation import calculate_forecast_metrics

from ml_models import (
    calculate_mae,
    calculate_directional_accuracy,
    predict_historical_mean,
    predict_zero_return,
)

# Heuristics for a research warning, not an approval to trade.
MIN_APPROX_NON_OVERLAPPING_WINDOWS = 10
MAX_STORED_PRICE_AGE_DAYS = 7


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise ValueError("A valid latest-price date is required.") from exc


def assess_direction_bias(metrics):
    """Report sign prediction imbalance; never infer profitable directional skill.

    These percentages are descriptive holdout statistics, not probabilities
    of future gains. A large predicted/observed positive-rate difference is
    flagged as a reliability concern, not used to fit or select a model.
    """
    actual = metrics.get("actual_positive_rate")
    predicted = metrics.get("predicted_positive_rate")
    balanced = metrics.get("balanced_directional_accuracy")
    warning = None

    if actual is None or predicted is None:
        warning = "Directional rates are unavailable for this holdout."
    elif actual in (0, 1):
        warning = (
            "The held-out outcomes contain only one return direction; "
            "directional discrimination cannot be established."
        )
    elif abs(predicted - actual) > 0.20:
        bias = "positive" if predicted > actual else "negative"
        warning = (
            f"Directional forecasts are heavily skewed {bias}: "
            f"{predicted:.1%} of predicted returns versus "
            f"{actual:.1%} of observed returns are positive. "
            "Review negative specificity and balanced directional accuracy."
        )

    return {
        "predicted_positive_rate": predicted,
        "actual_positive_rate": actual,
        "balanced_directional_accuracy": balanced,
        "directional_rate_gap_percentage_points": (
            round((predicted - actual) * 100, 2)
            if actual is not None and predicted is not None else None
        ),
        "warning": warning,
    }


def assess_prediction_evidence(
    *,
    y_train,
    y_test,
    predictions,
    horizon,
    last_price_date,
    as_of,
    confidence,
    interval_coverage,
):
    """Describe observed test performance, not the probability of a profit.

    All baselines use the training block only. The held-out test block is
    never used to select or refit a forecasting model.
    """
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")

    train = np.asarray(y_train, dtype=float).reshape(-1)
    actual = np.asarray(y_test, dtype=float).reshape(-1)
    forecast = np.asarray(predictions, dtype=float).reshape(-1)
    if not len(train) or not len(actual) or len(actual) != len(forecast):
        raise ValueError("Nonempty training and aligned test observations are required")
    if not (np.isfinite(train).all() and np.isfinite(actual).all() and np.isfinite(forecast).all()):
        raise ValueError("Holdout values must be finite")

    directional_evidence = assess_direction_bias(
        calculate_forecast_metrics(actual, forecast)
    )

    zero_predictions = predict_zero_return(train, actual)
    mean_predictions = predict_historical_mean(train, actual)

    model_mae = calculate_mae(actual, forecast)
    zero_mae = calculate_mae(actual, zero_predictions)
    mean_mae = calculate_mae(actual, mean_predictions)
    best_baseline_mae = min(zero_mae, mean_mae)
    best_baseline = "zero_return" if zero_mae <= mean_mae else "training_mean_return"

    # This is an arithmetic skill score on the same untouched test set.
    # A negative score means the model has a *larger* error than a baseline.
    skill = (
        (best_baseline_mae - model_mae) / best_baseline_mae
        if best_baseline_mae > 0
        else None
    )
    beats_both = model_mae < zero_mae and model_mae < mean_mae
    last_date = _parse_date(last_price_date)
    reference_date = _parse_date(as_of)
    price_age_days = (reference_date - last_date).days

    # H-session labels overlap heavily for H > 1. This is an approximate
    # count of disjoint label windows, NOT a statistical independence claim.
    approx_windows = len(actual) // horizon
    reasons = []
    if directional_evidence["warning"]:
        reasons.append(directional_evidence["warning"])

    if price_age_days < 0:
        reasons.append("Price history contains a future-dated last observation.")
    elif price_age_days > MAX_STORED_PRICE_AGE_DAYS:
        reasons.append("Latest stored price is more than seven calendar days old.")

    if approx_windows < MIN_APPROX_NON_OVERLAPPING_WINDOWS:
        reasons.append(
            "The held-out period has fewer than 10 approximately non-overlapping "
            "forecast windows for this horizon."
        )

    if not beats_both:
        reasons.append(
            "The model did not beat both the zero-return and training-mean "
            "baselines on held-out mean absolute error."
        )

    if interval_coverage is None:
        reasons.append("Out-of-sample interval coverage is unavailable.")
    elif not np.isfinite(interval_coverage) or not 0 <= interval_coverage <= 1:
        reasons.append("Out-of-sample interval coverage is invalid.")
    elif interval_coverage + 0.15 < confidence:
        reasons.append(
            "Held-out interval coverage is materially below the requested "
            "nominal confidence level."
        )

    return {
        "status": "promising_holdout_only" if not reasons else "limited_evidence",
        "ready_for_live_trading": False,
        "as_of_date": reference_date.isoformat(),
        "latest_price_date": last_date.isoformat(),
        "price_age_days": price_age_days,
        "holdout_observations": int(len(actual)),
        "approx_non_overlapping_holdout_windows": int(approx_windows),
        "directional_evidence": directional_evidence,
        "model_mae": model_mae,
        "baselines": {
            "zero_return": {
                "mae": zero_mae,
                "directional_accuracy": calculate_directional_accuracy(
                    actual, zero_predictions
                ),
            },
            "training_mean_return": {
                "mae": mean_mae,
                "directional_accuracy": calculate_directional_accuracy(
                    actual, mean_predictions
                ),
            },
        },
        "best_baseline": best_baseline,
        "mae_skill_vs_best_baseline": skill,
        "beats_both_baselines_on_mae": beats_both,
        "nominal_interval_confidence": confidence,
        "holdout_interval_coverage": (
            float(interval_coverage) if interval_coverage is not None
            and np.isfinite(interval_coverage) else None
        ),
        "warnings": reasons,
        "interpretation": (
            "Preliminary single-period holdout evidence only. The model must "
            "also pass multi-period, multi-stock walk-forward tests with "
            "transaction costs, data audits, and forward monitoring before "
            "any claim of decision-useful predictive skill. No model "
            "guarantees future returns."
        ),
    }
