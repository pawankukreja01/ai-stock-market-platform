from datetime import date

import pandas as pd

from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone

from stocks.models import Stock
from .models import HistoricalPrice
from .benchmark_data import BenchmarkDataUnavailable, fetch_benchmark_prices

from ml_engine import prepare_training_dataset
from ml_models import (
    create_linear_regression_model,
    create_random_forest_model,
    create_xgboost_model,
)
from walk_forward import generate_walk_forward_splits
from backtesting import (
    generate_walk_forward_predictions,
    compare_strategies,
    prepare_horizon_backtest_window,
)
from backtest_analysis import build_backtest_analysis
from backtest_sensitivity import run_cost_slippage_sensitivity
from ml_final_validation import build_final_validation_report


MODEL_FACTORIES = {
    "linear_regression": create_linear_regression_model,
    "random_forest": create_random_forest_model,
    "xgboost": create_xgboost_model,
}

MODEL_LABELS = {
    "linear_regression": "Linear Regression",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}

SUPPORTED_HORIZONS = {
    1: "1D",
    5: "5D",
    20: "1M",
    60: "3M",
    126: "6M",
    252: "1Y",
}


class BacktestView(APIView):
    """
    Run a walk-forward strategy backtest for a selected
    stock, prediction horizon and ML model.

    The endpoint returns strategy metrics plus normalized
    equity curves for:
        - ML strategy
        - Buy & Hold
        - SMA 200

    Transaction costs and slippage are explicit assumptions.
    """

    DEFAULT_TRANSACTION_COST_BPS = 5.0
    DEFAULT_SLIPPAGE_BPS = 5.0
    DEFAULT_THRESHOLD = 0.0
    DEFAULT_MINIMUM_TRAIN_SIZE = 1000
    DEFAULT_TEST_SIZE = 200
    DEFAULT_STEP_SIZE = 200

    def get(self, request):
        symbol = (
            request.query_params
            .get("symbol", "")
            .strip()
            .upper()
        )

        model_key = (
            request.query_params
            .get("model", "random_forest")
            .strip()
            .lower()
        )

        horizon_raw = request.query_params.get(
            "horizon", "5"
        )

        transaction_cost_raw = request.query_params.get(
            "transaction_cost_bps",
            str(self.DEFAULT_TRANSACTION_COST_BPS),
        )

        slippage_raw = request.query_params.get(
            "slippage_bps",
            str(self.DEFAULT_SLIPPAGE_BPS),
        )

        threshold_raw = request.query_params.get(
            "threshold",
            str(self.DEFAULT_THRESHOLD),
        )

        if not symbol:
            return Response(
                {"error": "symbol is required."},
                status=400,
            )

        if model_key not in MODEL_FACTORIES:
            return Response(
                {
                    "error": (
                        "Unsupported model. Use "
                        "linear_regression, random_forest, "
                        "or xgboost."
                    )
                },
                status=400,
            )

        try:
            horizon = int(horizon_raw)
        except (TypeError, ValueError):
            return Response(
                {
                    "error": (
                        "horizon must be one of "
                        "1, 5, 20, 60, 126, 252."
                    )
                },
                status=400,
            )

        if horizon not in SUPPORTED_HORIZONS:
            return Response(
                {
                    "error": (
                        "Unsupported horizon. Use 1, 5, 20, "
                        "60, 126, or 252 trading days."
                    )
                },
                status=400,
            )

        try:
            transaction_cost_bps = float(
                transaction_cost_raw
            )
            slippage_bps = float(slippage_raw)
            threshold = float(threshold_raw)
        except (TypeError, ValueError):
            return Response(
                {
                    "error": (
                        "transaction_cost_bps, slippage_bps, "
                        "and threshold must be numeric."
                    )
                },
                status=400,
            )

        if transaction_cost_bps < 0 or slippage_bps < 0:
            return Response(
                {
                    "error": (
                        "transaction_cost_bps and slippage_bps "
                        "cannot be negative."
                    )
                },
                status=400,
            )

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            return Response(
                {
                    "error": (
                        f"Stock '{symbol}' was not found."
                    )
                },
                status=404,
            )

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

        if len(prices) < 1200:
            return Response(
                {
                    "error": (
                        "At least 1200 historical observations "
                        "are recommended for walk-forward "
                        "backtesting."
                    ),
                    "observations": len(prices),
                },
                status=400,
            )

        df = pd.DataFrame(prices)

        try:
            benchmark_series = fetch_benchmark_prices(
                df, stock.exchange, strict=True
            )
        except BenchmarkDataUnavailable as exc:
            return Response(
                {
                    "error": "Benchmark data is unavailable for a reproducible backtest.",
                    "details": str(exc),
                },
                status=503,
            )

        try:
            X, y = prepare_training_dataset(
                df,
                benchmark_prices=benchmark_series,
                horizon=horizon,
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to build the ML dataset."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        minimum_train_size = min(
            self.DEFAULT_MINIMUM_TRAIN_SIZE,
            max(300, len(X) // 2),
        )

        remaining = len(X) - minimum_train_size - horizon

        if remaining < 100:
            return Response(
                {
                    "error": (
                        "Not enough usable observations for "
                        "walk-forward backtesting."
                    ),
                    "usable_observations": len(X),
                },
                status=400,
            )

        test_size = min(
            self.DEFAULT_TEST_SIZE,
            max(50, remaining // 2),
        )

        if minimum_train_size + horizon + test_size > len(X):
            test_size = len(X) - minimum_train_size - horizon

        if test_size <= 0:
            return Response(
                {
                    "error": (
                        "Unable to create a valid test window."
                    )
                },
                status=400,
            )

        step_size = min(
            self.DEFAULT_STEP_SIZE,
            test_size,
        )

        try:
            folds = generate_walk_forward_splits(
                X,
                y,
                minimum_train_size=minimum_train_size,
                test_size=test_size,
                horizon=horizon,
                step_size=step_size,
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to create walk-forward folds."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        try:
            prediction_series = generate_walk_forward_predictions(
                X,
                y,
                folds,
                MODEL_FACTORIES[model_key],
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to generate walk-forward "
                        "predictions."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        try:
            final_validation = build_final_validation_report(
                X=X,
                y=y,
                folds=folds,
                model_predictions=prediction_series,
                model_key=model_key,
                horizon=horizon,
            )
        except Exception as exc:
            return Response(
                {
                    "error": "Unable to calculate final ML validation report.",
                    "details": str(exc),
                },
                status=500,
            )

        # Preserve every stored observation date. The horizon-window helper
        # will reject an invalid execution price instead of bridging the gap.
        close_prices = pd.Series(
            pd.to_numeric(
                df["close_price"],
                errors="coerce",
            ).values,
            index=pd.to_datetime(df["date"]),
            name="close",
        )

        common_index = close_prices.index.intersection(
            prediction_series.index
        )

        if len(common_index) < 20:
            return Response(
                {
                    "error": (
                        "Not enough overlapping prices and "
                        "walk-forward predictions."
                    )
                },
                status=400,
            )

        try:
            aligned_prices, aligned_predictions = prepare_horizon_backtest_window(
                close_prices,
                prediction_series,
                holding_period=horizon,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

        try:
            strategy_results = compare_strategies(
                aligned_prices,
                aligned_predictions,
                transaction_cost_bps=transaction_cost_bps,
                slippage_bps=slippage_bps,
                sma_period=200,
                prediction_threshold=threshold,
                holding_period=horizon,
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Unable to calculate strategy "
                        "backtest results."
                    ),
                    "details": str(exc),
                },
                status=500,
            )

        strategies = {}
        for key in ["ml", "buy_and_hold", "sma"]:
            result = strategy_results[key]
            daily = result["daily"]
            metrics = result["metrics"]

            equity = (
                (1 + daily["net_return"])
                .cumprod()
                .astype(float)
            )

            strategies[key] = {
                "metrics": self._serialize_metrics(
                    metrics
                ),
                "equity_curve": {
                    "dates": [
                        index.strftime("%Y-%m-%d")
                        for index in equity.index
                    ],
                    "values": equity.tolist(),
                },
            }

        first_index = aligned_prices.index[0]
        last_index = aligned_prices.index[-1]

        fold_summary = []
        for fold in folds:
            item = {
                "fold": fold["fold"],
                "train_size": fold["train_size"],
                "test_size": fold["test_size"],
                "gap": fold["gap"],
            }

            if isinstance(X.index, pd.DatetimeIndex):
                item["train_start_date"] = str(
                    X.index[fold["train_start"]].date()
                )
                item["train_end_date"] = str(
                    X.index[fold["train_end"] - 1].date()
                )
                item["test_start_date"] = str(
                    X.index[fold["test_start"]].date()
                )
                item["test_end_date"] = str(
                    X.index[fold["test_end"] - 1].date()
                )

            fold_summary.append(item)

        analysis = build_backtest_analysis(
            strategy_results,
            configuration={
                "transaction_cost_bps": transaction_cost_bps,
                "slippage_bps": slippage_bps,
                "prediction_threshold": threshold,
            },
        )

        try:
            sensitivity = run_cost_slippage_sensitivity(
                aligned_prices,
                aligned_predictions,
                selected_transaction_cost_bps=transaction_cost_bps,
                selected_slippage_bps=slippage_bps,
                prediction_threshold=threshold,
                sma_period=200,
                holding_period=horizon,
            )
        except Exception as exc:
            return Response(
                {
                    "error": "Unable to calculate cost/slippage sensitivity.",
                    "details": str(exc),
                },
                status=500,
            )

        return Response(
            {
                "symbol": symbol,
                "company_name": stock.company_name,
                "model": model_key,
                "model_name": MODEL_LABELS[model_key],
                "horizon": horizon,
                "horizon_label": SUPPORTED_HORIZONS[horizon],
                "backtest_period": {
                    "start_date": first_index.strftime("%Y-%m-%d"),
                    "end_date": last_index.strftime("%Y-%m-%d"),
                    "observations": len(aligned_prices) - 1,
                },
                "configuration": {
                    "transaction_cost_bps": transaction_cost_bps,
                    "slippage_bps": slippage_bps,
                    "prediction_threshold": threshold,
                    "ml_holding_period_trading_days": horizon,
                    "minimum_train_size": minimum_train_size,
                    "test_size": test_size,
                    "step_size": step_size,
                    "gap": horizon,
                    "folds": len(folds),
                },
                "strategies": strategies,
                "analysis": analysis,
                "sensitivity": sensitivity,
                "final_validation": final_validation,
                "folds": fold_summary,
                "notes": [
                    (
                        "ML predictions are generated using expanding-window "
                        "walk-forward training."
                    ),
                    (
                        "A gap equal to the prediction horizon is placed "
                        "between each training window and its test window."
                    ),
                    (
                        "The ML strategy uses non-overlapping blocks: each selected "
                        "forecast determines long/cash exposure for the next horizon "
                        "trading-day returns."
                    ),
                    (
                        "Transaction costs and slippage are explicit backtest "
                        "assumptions and are not guarantees of actual execution costs."
                    ),
                    (
                        "This is a historical simulation, not a prediction "
                        "of future investment performance."
                    ),
                ],
            }
        )

    @staticmethod
    def _serialize_metrics(metrics):
        result = {}
        for key, value in metrics.items():
            if value is None:
                result[key] = None
            elif isinstance(value, (int, float)):
                if value == float("inf"):
                    result[key] = None
                else:
                    result[key] = float(value)
            else:
                result[key] = value
        return result
