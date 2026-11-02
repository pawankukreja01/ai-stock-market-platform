import pandas as pd
from django.utils import timezone

from ml_engine import prepare_training_dataset
from ml_models import run_all_models


SUPPORTED_HORIZONS = [
    1,
    5,
    20,
    60,
    126,
    252,
]


def load_stock_dataframe(
    HistoricalPrice,
    stock,
):
    """
    Load historical stock prices from Django
    into a pandas DataFrame.
    """
    prices = list(
        HistoricalPrice.objects
        .filter(stock=stock, date__lte=timezone.localdate())
        .order_by("date")
        .values(
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "is_ohlc_valid",
            "is_volume_valid",
        )
    )

    if not prices:
        raise ValueError(
            f"No historical price data found for "
            f"{stock.symbol}."
        )

    return pd.DataFrame(
        prices
    )


def chronological_purged_train_test_split(X, y, test_size=0.2, gap=0):
    """Chronological train/test split with a purged gap before the test block."""
    if len(X) != len(y):
        raise ValueError("X and y must have the same length.")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")
    if isinstance(gap, bool) or not isinstance(gap, int) or gap < 0:
        raise ValueError("gap must be a non-negative integer.")
    if len(X) < 2:
        raise ValueError("At least two observations are required.")

    test_start = int(len(X) * (1 - test_size))
    train_end = test_start - gap
    if train_end <= 0 or test_start >= len(X):
        raise ValueError("Not enough observations remain after applying the gap.")

    return (
        X.iloc[:train_end].copy(),
        X.iloc[test_start:].copy(),
        y.iloc[:train_end].copy(),
        y.iloc[test_start:].copy(),
    )


def run_horizon_experiment(
    price_dataframe,
    horizon,
    test_size=0.2,
):
    """
    Train and evaluate all baseline and ML models
    for one prediction horizon.
    """
    X, y = prepare_training_dataset(
        price_dataframe,
        horizon=horizon,
    )

    if len(X) < 10:
        raise ValueError(
            f"Not enough usable observations for "
            f"{horizon}-day prediction."
        )

    (
        X_train,
        X_test,
        y_train,
        y_test,
    ) = chronological_purged_train_test_split(
        X,
        y,
        test_size=test_size,
        gap=horizon,
    )

    output = run_all_models(
        X_train,
        X_test,
        y_train,
        y_test,
        horizon=horizon,
    )

    return {
        "horizon": horizon,
        "total_observations": int(
            len(X)
        ),
        "training_observations": int(
            len(X_train)
        ),
        "testing_observations": int(
            len(X_test)
        ),
        "results": output["results"],
    }


def run_multi_horizon_experiment(
    price_dataframe,
    horizons=None,
    test_size=0.2,
):
    """
    Run the complete ML experiment across
    multiple prediction horizons.

    Returns a dictionary containing the results
    for every horizon.
    """
    if horizons is None:
        horizons = SUPPORTED_HORIZONS

    experiment_results = []

    for horizon in horizons:
        result = run_horizon_experiment(
            price_dataframe,
            horizon=horizon,
            test_size=test_size,
        )

        experiment_results.append(
            result
        )

    return experiment_results


def get_best_models_by_horizon(
    experiment_results,
):
    """
    Determine the lowest-MAE model for each
    prediction horizon.

    This is an experimental comparison only.
    Final production selection should happen
    after walk-forward validation.
    """
    best_models = {}

    for experiment in experiment_results:
        horizon = experiment[
            "horizon"
        ]

        valid_results = [
            result
            for result in experiment[
                "results"
            ]
            if result["mae"] is not None
        ]

        if not valid_results:
            best_models[horizon] = None
            continue

        best_models[horizon] = min(
            valid_results,
            key=lambda result:
                result["mae"],
        )

    return best_models


def flatten_experiment_results(
    experiment_results,
):
    """
    Convert nested experiment results into a
    flat pandas DataFrame for analysis.
    """
    rows = []

    for experiment in experiment_results:
        horizon = experiment[
            "horizon"
        ]

        for result in experiment[
            "results"
        ]:
            rows.append(
                {
                    "horizon": horizon,
                    "model": result[
                        "model"
                    ],
                    "mae": result[
                        "mae"
                    ],
                    "rmse": result[
                        "rmse"
                    ],
                    "directional_accuracy": (
                        result[
                            "directional_accuracy"
                        ]
                    ),
                    "observations": result[
                        "observations"
                    ],
                }
            )

    return pd.DataFrame(
        rows
    )