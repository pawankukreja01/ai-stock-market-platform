import logging
from datetime import timedelta

import pandas as pd
import yfinance as yf

from ml_explainability import explain_prediction

from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from stocks.models import Stock
from .models import HistoricalPrice
from .benchmark_data import fetch_benchmark_prices
from .prediction_quality import assess_prediction_evidence

from ml_engine import (
    prepare_latest_feature_row,
    prepare_training_dataset,
)

from ml_models import (
    chronological_train_test_split,
    create_linear_regression_model,
    create_random_forest_model,
    create_xgboost_model,
    calculate_mae,
    calculate_rmse,
    calculate_directional_accuracy,
)

from ml_uncertainty import (
    chronological_three_way_split,
    calculate_calibration_error_quantile,
    calculate_interval_coverage,
)

logger = logging.getLogger(__name__)

SUPPORTED_HORIZONS = {
    1: "1D",
    5: "5D",
    20: "1M",
    60: "3M",
    126: "6M",
    252: "1Y",
}


MODEL_FACTORIES = {
    "linear_regression": (
        create_linear_regression_model
    ),
    "random_forest": (
        create_random_forest_model
    ),
    "xgboost": (
        create_xgboost_model
    ),
}


MODEL_LABELS = {
    "linear_regression": "Linear Regression",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}


class MLReturnPredictionView(APIView):
    """
    Generate a return prediction using one of the
    supported machine-learning models.

    IMPORTANT:
    This API predicts future returns, not guaranteed
    future prices.
    """

    DEFAULT_MODEL = "random_forest"
    DEFAULT_CONFIDENCE = 0.90

    def get(self, request):
        symbol = (
            request.query_params
            .get("symbol", "")
            .strip()
            .upper()
        )

        horizon_raw = (
            request.query_params
            .get("horizon", "5")
        )

        model_key = (
            request.query_params
            .get(
                "model",
                self.DEFAULT_MODEL,
            )
            .strip()
            .lower()
        )

        confidence_raw = (
            request.query_params
            .get(
                "confidence",
                str(
                    self.DEFAULT_CONFIDENCE
                ),
            )
        )

        # -------------------------------------------------
        # Validate symbol
        # -------------------------------------------------

        if not symbol:
            return Response(
                {
                    "error": (
                        "symbol is required."
                    )
                },
                status=400,
            )

        try:
            stock = Stock.objects.get(
                symbol=symbol
            )
        except Stock.DoesNotExist:
            return Response(
                {
                    "error": (
                        f"Stock '{symbol}' "
                        "was not found."
                    )
                },
                status=404,
            )

        # -------------------------------------------------
        # Validate horizon
        # -------------------------------------------------

        try:
            horizon = int(
                horizon_raw
            )
        except (
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "error": (
                        "horizon must be one of: "
                        "1, 5, 20, 60, 126, 252."
                    )
                },
                status=400,
            )

        if horizon not in SUPPORTED_HORIZONS:
            return Response(
                {
                    "error": (
                        "Unsupported horizon. "
                        "Use 1, 5, 20, 60, 126, "
                        "or 252 trading days."
                    )
                },
                status=400,
            )

        # -------------------------------------------------
        # Validate model
        # -------------------------------------------------

        if model_key not in MODEL_FACTORIES:
            return Response(
                {
                    "error": (
                        "Unsupported model. "
                        "Use linear_regression, "
                        "random_forest, or xgboost."
                    )
                },
                status=400,
            )

        # -------------------------------------------------
        # Validate confidence
        # -------------------------------------------------

        try:
            confidence = float(
                confidence_raw
            )
        except (
            TypeError,
            ValueError,
        ):
            return Response(
                {
                    "error": (
                        "confidence must be a "
                        "number between 0 and 1."
                    )
                },
                status=400,
            )

        if not (
            0 < confidence < 1
        ):
            return Response(
                {
                    "error": (
                        "confidence must be "
                        "between 0 and 1."
                    )
                },
                status=400,
            )

        # -------------------------------------------------
        # Load historical prices
        # -------------------------------------------------

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

        if len(prices) < 300:
            return Response(
                {
                    "error": (
                        "At least 300 historical "
                        "observations are recommended "
                        "for ML prediction."
                    ),
                    "observations": len(
                        prices
                    ),
                },
                status=400,
            )

        price_df = pd.DataFrame(
            prices
        )

        # -------------------------------------------------
        # Benchmark data
        # -------------------------------------------------

        benchmark_series = self._fetch_benchmark_prices(
            price_df,
            stock.exchange,
        )

        # -------------------------------------------------
        # Build feature dataset
        # -------------------------------------------------

        try:
            X, y = (
                prepare_training_dataset(
                    price_df,
                    benchmark_prices=(
                        benchmark_series
                    ),
                    horizon=horizon,
                )
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to build ML "
                        "training dataset."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        if len(X) < 100:
            return Response(
                {
                    "error": (
                        "Not enough usable observations "
                        "remain after feature engineering."
                    ),
                    "observations": len(X),
                },
                status=400,
            )

        try:
            latest_features = prepare_latest_feature_row(
                price_df,
                benchmark_prices=benchmark_series,
            )
        except Exception as exc:
            return Response(
                {
                    "error": "Unable to build latest forecast features.",
                    "details": str(exc),
                },
                status=400,
            )

        # -------------------------------------------------
        # Three-way chronological split
        # -------------------------------------------------

        try:
            (
                X_train,
                X_calibration,
                X_test,
                y_train,
                y_calibration,
                y_test,
            ) = chronological_three_way_split(
                X,
                y,
                train_size=0.70,
                calibration_size=0.15,
                horizon=horizon,
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to split ML dataset."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        # -------------------------------------------------
        # Train selected model
        # -------------------------------------------------

        model_factory = (
            MODEL_FACTORIES[
                model_key
            ]
        )

        model = model_factory()

        try:
            model.fit(
                X_train,
                y_train,
            )

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

        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to train ML model."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        # -------------------------------------------------
        # Validation metrics
        # -------------------------------------------------

        test_mae = calculate_mae(
            y_test,
            test_predictions,
        )

        test_rmse = calculate_rmse(
            y_test,
            test_predictions,
        )

        directional_accuracy = (
            calculate_directional_accuracy(
                y_test,
                test_predictions,
            )
        )

        # -------------------------------------------------
        # Prediction interval
        #
        # IMPORTANT:
        # Margin comes from calibration data only.
        # -------------------------------------------------

        error_margin = (
            calculate_calibration_error_quantile(
                y_calibration,
                calibration_predictions,
                confidence=confidence,
            )
        )
        if error_margin is None:
            empirical_test_coverage = None
        else:
            empirical_test_coverage = calculate_interval_coverage(
                y_test,
                test_predictions - error_margin,
                test_predictions + error_margin,
            )

        # Use the same fitted model for calibration, held-out evaluation and
        # the current forecast. Refitting on calibration/test labels would
        # change the model and make the existing calibration margin inapplicable.
        try:
            latest_prediction = float(
                model.predict(
                    latest_features
                )[0]
            )

        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to generate "
                        "latest prediction."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        # -------------------------------------------------
        # Explain the latest prediction with SHAP
        # -------------------------------------------------
        # Explanation failure must not invalidate a forecast.
        # X_test was held out when the reported metrics were calculated.
        # After evaluation, the final forecasting model is refitted on all
        # eligible labelled observations; X_test is reused here only for
        # the global explanation summary.
        try:
            explainability = explain_prediction(
                model=model,
                background_features=X_train,
                instance_features=latest_features,
                evaluation_features=X_test,
            )
        except Exception as exc:
            logger.exception(
                "SHAP explanation failed for %s (%s, horizon=%s)",
                symbol,
                model_key,
                horizon,
            )
            explainability = {
                "available": False,
                "method": "SHAP",
                "message": (
                    "The forecast was generated, but its SHAP "
                    "explanation could not be calculated."
                ),
                "details": str(exc),
            }

        # -------------------------------------------------
        # Build prediction interval
        # -------------------------------------------------

        if error_margin is None:
            lower_return = None
            upper_return = None
        else:
            lower_return = (
                latest_prediction
                - error_margin
            )

            upper_return = (
                latest_prediction
                + error_margin
            )

        # -------------------------------------------------
        # Current price
        # -------------------------------------------------

        latest_close = (
            price_df["close_price"]
            .dropna()
            .iloc[-1]
        )

        latest_close = float(
            latest_close
        )

        # The target is anchored to the next session close, which is not yet
        # known when this forecast is issued. A future target price therefore
        # cannot be derived from today's last close without inventing an entry
        # price. Keep the legacy response fields but return null values.
        estimated_price = None
        lower_price = None
        upper_price = None

        # -------------------------------------------------
        # Historical dates
        # -------------------------------------------------

        first_date = (
            price_df["date"]
            .iloc[0]
        )

        last_date = (
            price_df["date"]
            .iloc[-1]
        )

        # Model skill must be compared to simple baselines on the *same*
        # chronologically held-out observations. The diagnostics never
        # retrain on calibration or test outcomes.
        evidence = assess_prediction_evidence(
            y_train=y_train,
            y_test=y_test,
            predictions=test_predictions,
            horizon=horizon,
            last_price_date=last_date,
            as_of=timezone.localdate(),
            confidence=confidence,
            interval_coverage=empirical_test_coverage,
        )

        # -------------------------------------------------
        # Response
        # -------------------------------------------------

        return Response(
            {
                "symbol": symbol,
                "company_name": (
                    stock.company_name
                ),
                "model": model_key,
                "model_name": (
                    MODEL_LABELS[
                        model_key
                    ]
                ),
                "horizon": horizon,
                "horizon_label": (
                    SUPPORTED_HORIZONS[
                        horizon
                    ]
                ),
                "confidence": confidence,
                "target_definition": {
                    "formula": "close_price[t+horizon+1] / close_price[t+1] - 1",
                    "signal_observation": "close at t",
                    "entry": "next trading session close at t+1",
                    "exit": "close at t+horizon+1",
                    "holding_period_trading_days": int(horizon),
                    "price_basis": "unadjusted close_price; dividends are excluded",
                },

                "historical_period": {
                    "start_date": str(
                        first_date
                    ),
                    "end_date": str(
                        last_date
                    ),
                    "observations": int(
                        len(price_df)
                    ),
                },

                "dataset": {
                    "usable_observations": int(
                        len(X)
                    ),
                    "training_observations": int(
                        len(X_train)
                    ),
                    "calibration_observations": int(
                        len(X_calibration)
                    ),
                    "testing_observations": int(
                        len(X_test)
                    ),
                    "gap_observations": int(
                        len(X)
                        - len(X_train)
                        - len(X_calibration)
                        - len(X_test)
                    ),
                },

                "prediction": {
                    "return": (
                        latest_prediction
                    ),
                    "lower_return": (
                        lower_return
                    ),
                    "upper_return": (
                        upper_return
                    ),
                    "current_price": (
                        latest_close
                    ),
                    "estimated_price": (
                        estimated_price
                    ),
                    "lower_price": (
                        lower_price
                    ),
                    "upper_price": (
                        upper_price
                    ),
                },

                "explainability": explainability,
                "evidence": evidence,

                "validation": {
                    "mae": test_mae,
                    "rmse": test_rmse,
                    "directional_accuracy": (
                        directional_accuracy
                    ),
                    "calibration_error_margin": (
                        error_margin
                    ),
                    "nominal_interval_confidence": confidence,
                    "empirical_test_interval_coverage": empirical_test_coverage,
                },

                "benchmark": "^GSPC",

                "notes": [
                    (
                        "The forecast is the H-session return after next-session-close execution: close_price[t+H+1] / close_price[t+1] - 1."
                    ),
                    (
                        "A future target price is not estimated from today's close because the next-session entry price is not yet known. Legacy estimated_price and interval price fields are therefore null."
                    ),
                    (
                        "The model predicts future returns rather than guaranteed future prices."
                    ),
                    (
                        "The prediction interval uses a finite-sample "
                        "calibration-error quantile from a separate chronological "
                        "calibration block. Empirical coverage is reported on "
                        "the held-out test block and is not guaranteed."
                    ),
                    (
                        "Validation metrics are based on "
                        "a chronological holdout period."
                    ),
                    (
                        "Final model selection will be "
                        "validated further using "
                        "walk-forward testing."
                    ),
                ],
            }
        )

    @staticmethod
    def _fetch_benchmark_prices(price_df, exchange=""):
        """Fetch a market-appropriate benchmark with a safe empty fallback."""
        return fetch_benchmark_prices(price_df, exchange=exchange)
