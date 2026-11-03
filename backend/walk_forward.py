import numpy as np
import pandas as pd

from ml_models import (
    create_linear_regression_model,
    create_random_forest_model,
    create_xgboost_model,
    calculate_mae,
    calculate_rmse,
    calculate_directional_accuracy,
)


MODEL_FACTORIES = {
    "Linear Regression": create_linear_regression_model,
    "Random Forest": create_random_forest_model,
    "XGBoost": create_xgboost_model,
}


def generate_walk_forward_splits(
    X,
    y,
    minimum_train_size=1000,
    test_size=200,
    horizon=5,
    step_size=None,
):
    """
    Generate expanding-window walk-forward splits.

    Parameters
    ----------
    X, y:
        Time-ordered feature matrix and target.

    minimum_train_size:
        Minimum number of observations used for
        the first training window.

    test_size:
        Number of observations in each forward
        test window.

    horizon:
        Prediction horizon in trading days.

        The target enters at t+1 and exits at t+H+1. A gap of
        horizon + 1 observations ensures the final training label endpoint
        precedes the first test forecast origin.

    step_size:
        Number of observations by which the window
        moves forward after each fold.

        Defaults to test_size.

    Returns
    -------
    list[dict]
        Fold definitions.
    """

    if len(X) != len(y):
        raise ValueError(
            "X and y must have the same length."
        )

    if len(X) < minimum_train_size + test_size:
        raise ValueError(
            "Not enough observations for the requested "
            "walk-forward configuration."
        )

    if minimum_train_size <= 0:
        raise ValueError(
            "minimum_train_size must be greater than zero."
        )

    if test_size <= 0:
        raise ValueError(
            "test_size must be greater than zero."
        )

    if horizon < 0:
        raise ValueError(
            "horizon cannot be negative."
        )

    if step_size is None:
        step_size = test_size

    if step_size <= 0:
        raise ValueError(
            "step_size must be greater than zero."
        )

    purge_gap = int(horizon) + 1
    folds = []

    train_end = minimum_train_size
    fold_number = 1

    while True:
        test_start = train_end + purge_gap
        test_end = test_start + test_size

        if test_end > len(X):
            break

        folds.append(
            {
                "fold": fold_number,
                "train_start": 0,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "train_size": train_end,
                "test_size": test_size,
                "gap": purge_gap,
            }
        )

        train_end += step_size
        fold_number += 1

    if not folds:
        raise ValueError(
            "No valid walk-forward folds could be generated."
        )

    return folds


def describe_fold(
    X,
    fold,
):
    """
    Add human-readable dates to a fold definition
    when X has a DatetimeIndex.
    """
    result = fold.copy()

    try:
        if isinstance(
            X.index,
            pd.DatetimeIndex,
        ):
            train_start_index = fold[
                "train_start"
            ]

            train_end_index = fold[
                "train_end"
            ] - 1

            test_start_index = fold[
                "test_start"
            ]

            test_end_index = fold[
                "test_end"
            ] - 1

            result[
                "train_start_date"
            ] = str(
                X.index[
                    train_start_index
                ].date()
            )

            result[
                "train_end_date"
            ] = str(
                X.index[
                    train_end_index
                ].date()
            )

            result[
                "test_start_date"
            ] = str(
                X.index[
                    test_start_index
                ].date()
            )

            result[
                "test_end_date"
            ] = str(
                X.index[
                    test_end_index
                ].date()
            )

    except Exception:
        pass

    return result


def evaluate_predictions(
    y_true,
    y_pred,
):
    """
    Calculate standard prediction metrics
    for one walk-forward fold.
    """
    return {
        "mae": calculate_mae(
            y_true,
            y_pred,
        ),
        "rmse": calculate_rmse(
            y_true,
            y_pred,
        ),
        "directional_accuracy": (
            calculate_directional_accuracy(
                y_true,
                y_pred,
            )
        ),
        "observations": int(
            len(y_true)
        ),
    }


def run_walk_forward_model(
    model_name,
    model_factory,
    X,
    y,
    folds,
):
    """
    Train and test one model across all
    walk-forward folds.

    A brand-new model is fitted for every fold.
    """

    fold_results = []

    for fold in folds:
        (
            train_start,
            train_end,
            test_start,
            test_end,
        ) = (
            fold["train_start"],
            fold["train_end"],
            fold["test_start"],
            fold["test_end"],
        )

        X_train = X.iloc[
            train_start:train_end
        ]

        y_train = y.iloc[
            train_start:train_end
        ]

        X_test = X.iloc[
            test_start:test_end
        ]

        y_test = y.iloc[
            test_start:test_end
        ]

        if X_train.empty or X_test.empty:
            continue

        model = model_factory()

        model.fit(
            X_train,
            y_train,
        )

        predictions = model.predict(
            X_test
        )

        metrics = evaluate_predictions(
            y_test,
            predictions,
        )

        fold_result = {
            "fold": fold["fold"],
            "model": model_name,
            "train_size": fold[
                "train_size"
            ],
            "test_size": fold[
                "test_size"
            ],
            "gap": fold[
                "gap"
            ],
            **metrics,
        }

        # Add fold dates when possible.
        fold_description = describe_fold(
            X,
            fold,
        )

        for key in [
            "train_start_date",
            "train_end_date",
            "test_start_date",
            "test_end_date",
        ]:
            if key in fold_description:
                fold_result[key] = (
                    fold_description[key]
                )

        fold_results.append(
            fold_result
        )

    return fold_results


def aggregate_model_results(
    fold_results,
):
    """
    Aggregate fold-level metrics into a
    model-level walk-forward result.

    Each fold contributes equally to the
    mean metric.
    """
    if not fold_results:
        return None

    mae_values = [
        result["mae"]
        for result in fold_results
        if result["mae"] is not None
    ]

    rmse_values = [
        result["rmse"]
        for result in fold_results
        if result["rmse"] is not None
    ]

    direction_values = [
        result[
            "directional_accuracy"
        ]
        for result in fold_results
        if result[
            "directional_accuracy"
        ] is not None
    ]

    return {
        "model": fold_results[0][
            "model"
        ],
        "folds": len(
            fold_results
        ),
        "mean_mae": (
            float(
                np.mean(mae_values)
            )
            if mae_values
            else None
        ),
        "mean_rmse": (
            float(
                np.mean(rmse_values)
            )
            if rmse_values
            else None
        ),
        "mean_directional_accuracy": (
            float(
                np.mean(
                    direction_values
                )
            )
            if direction_values
            else None
        ),
        "min_mae": (
            float(
                np.min(mae_values)
            )
            if mae_values
            else None
        ),
        "max_mae": (
            float(
                np.max(mae_values)
            )
            if mae_values
            else None
        ),
    }


def run_walk_forward_experiment(
    X,
    y,
    horizon=5,
    minimum_train_size=1000,
    test_size=200,
    step_size=None,
):
    """
    Run walk-forward validation for all three
    actual ML models.

    Returns:
        {
            "configuration": ...,
            "folds": ...,
            "models": ...,
            "fold_results": ...
        }
    """

    folds = generate_walk_forward_splits(
        X,
        y,
        minimum_train_size=minimum_train_size,
        test_size=test_size,
        horizon=horizon,
        step_size=step_size,
    )

    model_results = {}
    all_fold_results = []

    for (
        model_name,
        model_factory,
    ) in MODEL_FACTORIES.items():

        fold_results = (
            run_walk_forward_model(
                model_name,
                model_factory,
                X,
                y,
                folds,
            )
        )

        model_results[
            model_name
        ] = aggregate_model_results(
            fold_results
        )

        all_fold_results.extend(
            fold_results
        )

    return {
        "configuration": {
            "horizon": horizon,
            "minimum_train_size": (
                minimum_train_size
            ),
            "test_size": test_size,
            "step_size": (
                step_size
                if step_size is not None
                else test_size
            ),
            "gap": int(horizon) + 1,
            "folds": len(folds),
        },
        "folds": [
            describe_fold(
                X,
                fold,
            )
            for fold in folds
        ],
        "models": model_results,
        "fold_results": all_fold_results,
    }


def rank_walk_forward_models(
    experiment,
):
    """
    Rank models using:

        1. Mean MAE ascending
        2. Mean RMSE ascending
        3. Mean directional accuracy descending
    """

    results = [
        result
        for result in experiment[
            "models"
        ].values()
        if result is not None
    ]

    ranked = sorted(
        results,
        key=lambda result: (
            result["mean_mae"],
            result["mean_rmse"],
            -result[
                "mean_directional_accuracy"
            ],
        ),
    )

    ranked_with_positions = []

    for rank, result in enumerate(
        ranked,
        start=1,
    ):
        item = result.copy()
        item["rank"] = rank

        ranked_with_positions.append(
            item
        )

    return ranked_with_positions