import numpy as np


def chronological_three_way_split(
    X,
    y,
    train_size=0.70,
    calibration_size=0.15,
    horizon=0,
):
    """
    Chronologically split data into training, calibration and test sets.

    A gap equal to the forecast horizon is omitted at each boundary
    so future-return targets do not overlap between adjacent sets.
    """
    if len(X) != len(y):
        raise ValueError(
            "X and y must contain the same number "
            "of observations."
        )

    if len(X) < 20:
        raise ValueError(
            "At least 20 observations are required."
        )

    if not (0 < train_size < 1):
        raise ValueError(
            "train_size must be between 0 and 1."
        )

    if not (0 < calibration_size < 1):
        raise ValueError(
            "calibration_size must be between 0 and 1."
        )

    if train_size + calibration_size >= 1:
        raise ValueError(
            "train_size + calibration_size "
            "must be less than 1."
        )

    if (
        isinstance(horizon, bool)
        or not isinstance(horizon, (int, np.integer))
        or horizon < 0
    ):
        raise ValueError(
            "horizon must be a non-negative integer."
        )

    n = len(X)
    available_observations = n - (2 * horizon)

    if available_observations < 100:
        raise ValueError(
            "Not enough observations remain after applying "
            "horizon gaps; at least 100 are required."
        )

    train_end = int(available_observations * train_size)
    calibration_count = int(
        available_observations * calibration_size
    )

    calibration_start = train_end + horizon
    calibration_end = calibration_start + calibration_count
    test_start = calibration_end + horizon

    if train_end <= 0:
        raise ValueError("Training set is empty.")

    if calibration_count <= 0:
        raise ValueError("Calibration set is empty.")

    if test_start >= n:
        raise ValueError(
            "Not enough observations remain for the test set "
            "after applying horizon gaps."
        )

    X_train = X.iloc[:train_end].copy()
    X_calibration = X.iloc[
        calibration_start:calibration_end
    ].copy()
    X_test = X.iloc[test_start:].copy()

    y_train = y.iloc[:train_end].copy()
    y_calibration = y.iloc[
        calibration_start:calibration_end
    ].copy()
    y_test = y.iloc[test_start:].copy()

    if X_train.empty or X_calibration.empty or X_test.empty:
        raise ValueError(
            "Training, calibration and test sets must all be non-empty."
        )

    return (
        X_train,
        X_calibration,
        X_test,
        y_train,
        y_calibration,
        y_test,
    )

def calculate_absolute_errors(
    y_true,
    y_pred,
):
    """
    Absolute prediction errors on unseen data.
    """
    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    y_pred = np.asarray(
        y_pred,
        dtype=float,
    )

    if len(y_true) != len(y_pred):
        raise ValueError(
            "y_true and y_pred must have "
            "the same length."
        )

    return np.abs(
        y_true - y_pred
    )


def calculate_calibration_error_quantile(
    y_true,
    y_pred,
    confidence=0.90,
):
    """
    Calculate an empirical error quantile from
    an unseen calibration dataset.

    For confidence=0.90, approximately the 90th
    percentile of absolute prediction errors is used.
    """
    if not (
        0 < confidence < 1
    ):
        raise ValueError(
            "confidence must be between 0 and 1."
        )

    absolute_errors = (
        calculate_absolute_errors(
            y_true,
            y_pred,
        )
    )

    if len(absolute_errors) == 0:
        return None

    # Finite-sample split-conformal order statistic. The required rank is
    # ceil((n + 1) * confidence), using one-based indexing. If that rank
    # exceeds the calibration sample, no finite interval is supported.
    sample_size = len(absolute_errors)
    rank = int(np.ceil((sample_size + 1) * confidence))
    if rank > sample_size:
        return None

    ordered_errors = np.sort(absolute_errors)
    return float(ordered_errors[rank - 1])


def build_prediction_interval(
    prediction,
    error_margin,
):
    """
    Build a symmetric empirical prediction interval.
    """
    if prediction is None:
        return {
            "prediction": None,
            "lower": None,
            "upper": None,
        }

    if error_margin is None:
        return {
            "prediction": float(
                prediction
            ),
            "lower": None,
            "upper": None,
        }

    prediction = float(
        prediction
    )

    error_margin = float(
        max(
            error_margin,
            0,
        )
    )

    return {
        "prediction": prediction,
        "lower": prediction - error_margin,
        "upper": prediction + error_margin,
    }


def calculate_interval_coverage(
    y_true,
    lower,
    upper,
):
    """
    Measure how many observations actually fall
    inside the prediction interval.
    """
    y_true = np.asarray(
        y_true,
        dtype=float,
    )

    lower = np.asarray(
        lower,
        dtype=float,
    )

    upper = np.asarray(
        upper,
        dtype=float,
    )

    if not (
        len(y_true)
        == len(lower)
        == len(upper)
    ):
        raise ValueError(
            "All interval arrays must have "
            "the same length."
        )

    if len(y_true) == 0:
        return None

    covered = (
        (y_true >= lower)
        & (y_true <= upper)
    )

    return float(
        np.mean(covered)
    )


def calculate_prediction_interval(
    model,
    X_calibration,
    y_calibration,
    prediction,
    confidence=0.90,
):
    """
    Generate a prediction interval using empirical
    calibration residuals.

    The model must already be fitted using training
    data only.
    """

    calibration_predictions = (
        model.predict(
            X_calibration
        )
    )

    error_margin = (
        calculate_calibration_error_quantile(
            y_calibration,
            calibration_predictions,
            confidence=confidence,
        )
    )

    return build_prediction_interval(
        prediction,
        error_margin,
    )


def evaluate_prediction_intervals(
    model,
    X_calibration,
    y_calibration,
    X_test,
    y_test,
    confidence=0.90,
):
    """
    Evaluate empirical prediction intervals on an
    unseen test dataset.

    The calibration error is calculated only from
    the calibration dataset.
    """

    calibration_predictions = (
        model.predict(
            X_calibration
        )
    )

    test_predictions = (
        model.predict(
            X_test
        )
    )

    error_margin = (
        calculate_calibration_error_quantile(
            y_calibration,
            calibration_predictions,
            confidence=confidence,
        )
    )

    if error_margin is None:
        return {
            "confidence": confidence,
            "error_margin": None,
            "coverage": None,
            "test_predictions": [],
            "lower_bounds": [],
            "upper_bounds": [],
        }

    lower_bounds = (
        test_predictions
        - error_margin
    )

    upper_bounds = (
        test_predictions
        + error_margin
    )

    coverage = calculate_interval_coverage(
        y_test,
        lower_bounds,
        upper_bounds,
    )

    return {
        "confidence": confidence,
        "error_margin": float(
            error_margin
        ),
        "coverage": coverage,
        "test_predictions": (
            test_predictions
            .astype(float)
            .tolist()
        ),
        "lower_bounds": (
            lower_bounds
            .astype(float)
            .tolist()
        ),
        "upper_bounds": (
            upper_bounds
            .astype(float)
            .tolist()
        ),
    }