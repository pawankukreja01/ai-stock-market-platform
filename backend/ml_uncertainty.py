import numpy as np


def chronological_three_way_split(
    X,
    y,
    train_size=0.70,
    calibration_size=0.15,
):
    """
    Chronologically split data into:

        Training
        Calibration
        Test

    No shuffling is performed.
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

    if not (
        0 < train_size < 1
    ):
        raise ValueError(
            "train_size must be between 0 and 1."
        )

    if not (
        0 < calibration_size < 1
    ):
        raise ValueError(
            "calibration_size must be between 0 and 1."
        )

    if (
        train_size + calibration_size
        >= 1
    ):
        raise ValueError(
            "train_size + calibration_size "
            "must be less than 1."
        )

    n = len(X)

    train_end = int(
        n * train_size
    )

    calibration_end = int(
        n
        * (
            train_size
            + calibration_size
        )
    )

    if train_end <= 0:
        raise ValueError(
            "Training set is empty."
        )

    if calibration_end <= train_end:
        raise ValueError(
            "Calibration set is empty."
        )

    if calibration_end >= n:
        raise ValueError(
            "Test set is empty."
        )

    X_train = X.iloc[
        :train_end
    ].copy()

    X_calibration = X.iloc[
        train_end:calibration_end
    ].copy()

    X_test = X.iloc[
        calibration_end:
    ].copy()

    y_train = y.iloc[
        :train_end
    ].copy()

    y_calibration = y.iloc[
        train_end:calibration_end
    ].copy()

    y_test = y.iloc[
        calibration_end:
    ].copy()

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

    return float(
        np.quantile(
            absolute_errors,
            confidence,
        )
    )


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