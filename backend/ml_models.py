import math

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor


# =========================================================
# GENERAL HELPERS
# =========================================================


def _to_numpy(values):
    """
    Convert pandas / numpy values to a numeric numpy array.
    """
    return np.asarray(
        values,
        dtype=float,
    )


# =========================================================
# BASELINE PREDICTION FUNCTIONS
# =========================================================


def predict_zero_return(
    y_train,
    y_test,
):
    """
    Baseline 1:
    Predict zero future return for every observation.
    """
    return np.zeros(
        len(y_test),
        dtype=float,
    )


def predict_historical_mean(
    y_train,
    y_test,
):
    """
    Baseline 2:
    Predict the mean return from the training set.
    """
    y_train = _to_numpy(
        y_train
    )

    if len(y_train) == 0:
        return np.zeros(
            len(y_test),
            dtype=float,
        )

    mean_return = np.mean(
        y_train
    )

    return np.full(
        len(y_test),
        mean_return,
        dtype=float,
    )


def predict_momentum(
    X_test,
    horizon,
):
    """
    Baseline 3:
    Use the most recent observed return over
    the same horizon as the predictor.
    """
    column_name = (
        f"return_{horizon}d"
    )

    if column_name not in X_test.columns:
        raise ValueError(
            f"Required feature '{column_name}' "
            "is not available."
        )

    return (
        X_test[column_name]
        .astype(float)
        .to_numpy()
    )


# =========================================================
# EVALUATION METRICS
# =========================================================


def calculate_mae(
    y_true,
    y_pred,
):
    """
    Mean Absolute Error.
    Lower is better.
    """
    y_true = _to_numpy(
        y_true
    )

    y_pred = _to_numpy(
        y_pred
    )

    if len(y_true) == 0:
        return None

    return float(
        np.mean(
            np.abs(
                y_true - y_pred
            )
        )
    )


def calculate_rmse(
    y_true,
    y_pred,
):
    """
    Root Mean Squared Error.
    Lower is better.
    """
    y_true = _to_numpy(
        y_true
    )

    y_pred = _to_numpy(
        y_pred
    )

    if len(y_true) == 0:
        return None

    mse = np.mean(
        (
            y_true - y_pred
        ) ** 2
    )

    return float(
        math.sqrt(mse)
    )


def calculate_directional_accuracy(
    y_true,
    y_pred,
):
    """
    Percentage of observations where the
    predicted return has the correct direction.
    """
    y_true = _to_numpy(
        y_true
    )

    y_pred = _to_numpy(
        y_pred
    )

    if len(y_true) == 0:
        return None

    true_direction = (
        y_true > 0
    )

    predicted_direction = (
        y_pred > 0
    )

    return float(
        np.mean(
            true_direction
            == predicted_direction
        )
    )


def evaluate_model(
    model_name,
    y_true,
    y_pred,
):
    """
    Return standard model evaluation metrics.
    """
    return {
        "model": model_name,
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


# =========================================================
# TIME-SERIES TRAIN / TEST SPLIT
# =========================================================


def chronological_train_test_split(
    X,
    y,
    test_size=0.2,
):
    """
    Split time-series data chronologically.

    No shuffling is performed.

    Earlier observations -> training
    Later observations  -> testing
    """
    if len(X) != len(y):
        raise ValueError(
            "X and y must contain the same number "
            "of observations."
        )

    if not 0 < test_size < 1:
        raise ValueError(
            "test_size must be between 0 and 1."
        )

    if len(X) < 2:
        raise ValueError(
            "At least two observations are required."
        )

    split_index = int(
        len(X) * (1 - test_size)
    )

    if split_index <= 0:
        raise ValueError(
            "Training dataset would be empty."
        )

    if split_index >= len(X):
        raise ValueError(
            "Test dataset would be empty."
        )

    X_train = X.iloc[
        :split_index
    ].copy()

    X_test = X.iloc[
        split_index:
    ].copy()

    y_train = y.iloc[
        :split_index
    ].copy()

    y_test = y.iloc[
        split_index:
    ].copy()

    return (
        X_train,
        X_test,
        y_train,
        y_test,
    )


# =========================================================
# MODEL DEFINITIONS
# =========================================================


def create_linear_regression_model():
    """
    Linear Regression pipeline.

    Imputation and scaling are learned from training
    data only when .fit() is called.
    """
    return Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "model",
                LinearRegression(),
            ),
        ]
    )


def create_random_forest_model():
    """
    Random Forest regression model.
    """
    return Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=300,
                    max_depth=6,
                    min_samples_leaf=5,
                    max_features="sqrt",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )



def create_conservative_random_forest_model():
    """Research-only shallower forest with broader, more stable leaves.

    Not exposed through the live prediction API. Its fixed configuration
    is compared against baselines on time-purged development folds.
    """
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=200,
                    max_depth=3,
                    min_samples_leaf=25,
                    max_features="sqrt",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def create_zero_anchor_ridge_model():
    """Research-only regularized linear forecast with a zero-return anchor.

    The feature scaler is fitted strictly on training data. Disabling
    the intercept shrinks predictions toward zero, not toward the
    historically bullish sample average. Alpha is fixed in advance.
    """
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=100.0, fit_intercept=False)),
        ]
    )


def create_xgboost_model():
    """
    XGBoost regression model.
    """
    return Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "model",
                XGBRegressor(
                    objective="reg:squarederror",
                    n_estimators=300,
                    max_depth=4,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    min_child_weight=5,
                    reg_lambda=1.0,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


# =========================================================
# SINGLE MODEL TRAINING
# =========================================================


def train_and_evaluate_model(
    model_name,
    model,
    X_train,
    X_test,
    y_train,
    y_test,
):
    """
    Fit one ML model using training data and evaluate
    it on the unseen chronological test data.
    """
    model.fit(
        X_train,
        y_train,
    )

    predictions = model.predict(
        X_test
    )

    result = evaluate_model(
        model_name,
        y_test,
        predictions,
    )

    return (
        model,
        predictions,
        result,
    )


# =========================================================
# RUN ACTUAL ML MODELS
# =========================================================


def run_machine_learning_models(
    X_train,
    X_test,
    y_train,
    y_test,
):
    """
    Train and evaluate:

        1. Linear Regression
        2. Random Forest
        3. XGBoost

    Returns
    -------
    dict
        Trained models, predictions and evaluation results.
    """

    model_definitions = [
        (
            "Linear Regression",
            create_linear_regression_model(),
        ),
        (
            "Random Forest",
            create_random_forest_model(),
        ),
        (
            "XGBoost",
            create_xgboost_model(),
        ),
    ]

    models = {}
    predictions = {}
    results = []

    for (
        model_name,
        model,
    ) in model_definitions:

        (
            trained_model,
            model_predictions,
            evaluation,
        ) = train_and_evaluate_model(
            model_name,
            model,
            X_train,
            X_test,
            y_train,
            y_test,
        )

        models[
            model_name
        ] = trained_model

        predictions[
            model_name
        ] = model_predictions

        results.append(
            evaluation
        )

    return {
        "models": models,
        "predictions": predictions,
        "results": results,
    }


# =========================================================
# BASELINES
# =========================================================


def run_baseline_models(
    X_train,
    X_test,
    y_train,
    y_test,
    horizon,
):
    """
    Run the baseline models.
    """

    results = []

    # -----------------------------------------------------
    # Zero Return
    # -----------------------------------------------------

    zero_predictions = (
        predict_zero_return(
            y_train,
            y_test,
        )
    )

    results.append(
        evaluate_model(
            "Zero Return",
            y_test,
            zero_predictions,
        )
    )

    # -----------------------------------------------------
    # Historical Mean
    # -----------------------------------------------------

    mean_predictions = (
        predict_historical_mean(
            y_train,
            y_test,
        )
    )

    results.append(
        evaluate_model(
            "Historical Mean",
            y_test,
            mean_predictions,
        )
    )

    # -----------------------------------------------------
    # Momentum
    # -----------------------------------------------------

    momentum_predictions = (
        predict_momentum(
            X_test,
            horizon,
        )
    )

    results.append(
        evaluate_model(
            "Momentum",
            y_test,
            momentum_predictions,
        )
    )

    return results


# =========================================================
# COMPLETE MODEL COMPARISON
# =========================================================


def run_all_models(
    X_train,
    X_test,
    y_train,
    y_test,
    horizon,
):
    """
    Run all baseline and machine-learning models.

    Returns results sorted by MAE, where lower is better.
    """

    baseline_results = (
        run_baseline_models(
            X_train,
            X_test,
            y_train,
            y_test,
            horizon,
        )
    )

    ml_output = (
        run_machine_learning_models(
            X_train,
            X_test,
            y_train,
            y_test,
        )
    )

    all_results = (
        baseline_results
        + ml_output["results"]
    )

    all_results = sorted(
        all_results,
        key=lambda result: (
            result["mae"]
            if result["mae"] is not None
            else float("inf")
        ),
    )

    return {
        "results": all_results,
        "models": ml_output["models"],
        "predictions": ml_output["predictions"],
    }


# =========================================================
# FEATURE IMPORTANCE
# =========================================================


def get_tree_feature_importance(
    model,
    feature_names,
):
    """
    Extract feature importance from a fitted
    Random Forest or XGBoost pipeline.

    Returns a list sorted from most important
    to least important.
    """
    if (
        not hasattr(model, "named_steps")
        or "model" not in model.named_steps
    ):
        return []

    estimator = (
        model.named_steps["model"]
    )

    if not hasattr(
        estimator,
        "feature_importances_",
    ):
        return []

    importances = (
        estimator.feature_importances_
    )

    if len(importances) != len(
        feature_names
    ):
        return []

    importance_data = [
        {
            "feature": feature,
            "importance": float(
                importance
            ),
        }
        for feature, importance in zip(
            feature_names,
            importances,
        )
    ]

    importance_data.sort(
        key=lambda item: item[
            "importance"
        ],
        reverse=True,
    )

    return importance_data


# =========================================================
# BEST MODEL
# =========================================================


def select_best_model(
    results,
):
    """
    Select the model with the lowest MAE.

    This is only a model-selection helper for the
    current holdout experiment.

    Final model selection will be improved in the
    walk-forward backtesting stage.
    """
    valid_results = [
        result
        for result in results
        if result["mae"] is not None
    ]

    if not valid_results:
        return None

    return min(
        valid_results,
        key=lambda result: result[
            "mae"
        ],
    )