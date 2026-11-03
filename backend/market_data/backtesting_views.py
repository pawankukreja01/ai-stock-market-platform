import math

import pandas as pd

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
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
    choose_walk_forward_test_size,
    choose_walk_forward_step_size,
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


def build_backtest_execution_prices(price_frame):
    """Build a close-price series while preserving invalid OHLC rows as gaps.

    Invalid observations remain in the index as NaN so the downstream
    backtest integrity checks reject a window that would otherwise bridge
    across a candle explicitly marked invalid by ingestion.
    """
    if price_frame.empty:
        return pd.Series(dtype=float, name="close")

    required = {"date", "close_price", "is_ohlc_valid"}
    missing = required.difference(price_frame.columns)
    if missing:
        raise ValueError(
            "Missing required execution-price fields: "
            + ", ".join(sorted(missing))
        )

    dates = pd.to_datetime(price_frame["date"])
    close = pd.to_numeric(price_frame["close_price"], errors="coerce")
    valid_ohlc = price_frame["is_ohlc_valid"].fillna(False).astype(bool)
    close = close.where(valid_ohlc)

    return pd.Series(
        close.to_numpy(dtype=float),
        index=dates,
        name="close",
    )


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

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ml_backtest"

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

        if not all(
            math.isfinite(value)
            for value in (transaction_cost_bps, slippage_bps, threshold)
        ):
            return Response(
                {
                    "error": (
                        "transaction_cost_bps, slippage_bps, and threshold "
                        "must be finite numbers."
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

        purge_gap = horizon + 1
        remaining = len(X) - minimum_train_size - purge_gap

        minimum_oos_observations = max(100, horizon + 2)
        if remaining < minimum_oos_observations:
            return Response(
                {
                    "error": (
                        "Not enough usable out-of-sample observations for at least "
                        "two fully realized, non-overlapping strategy holding blocks "
                        f"at the selected {horizon}-day horizon. Try a shorter horizon "
                        "or load more historical data."
                    ),
                    "usable_observations": len(X),
                    "available_out_of_sample_observations": remaining,
                    "minimum_required_out_of_sample_observations": minimum_oos_observations,
                    "purge_gap": purge_gap,
                },
                status=400,
            )

        test_size = choose_walk_forward_test_size(
            available_oos_observations=remaining,
            horizon=horizon,
            default_test_size=self.DEFAULT_TEST_SIZE,
        )

        if test_size <= 0:
            return Response(
                {
                    "error": (
                        "Unable to create a valid test window."
                    )
                },
                status=400,
            )

        # A long-horizon fold may need to be larger than the default
        # 200-row step. Never let fold test windows overlap: duplicate test
        # dates would cause the prediction series to keep only the later fold.
        step_size = choose_walk_forward_step_size(
            test_size=test_size,
            default_step_size=self.DEFAULT_STEP_SIZE,
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
        try:
            close_prices = build_backtest_execution_prices(df)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=400)

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
                close_prices,
                prediction_series,
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

            # Keep the existing API curve contract: the frontend supplies the
            # initial 1.0 point at the beginning of the comparison period.
            strategies[key] = {
                "metrics": self._serialize_metrics(metrics),
                "equity_curve": {
                    "dates": [index.strftime("%Y-%m-%d") for index in equity.index],
                    "values": equity.tolist(),
                },
                # Trade rows are generated by the same execution ledger used
                # for strategy metrics; no second trade-accounting path exists.
                "trades": [self._serialize_trade(trade) for trade in result["trades"]],
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
                close_prices,
                prediction_series,
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
                "price_basis": {
                    "field": "close_price",
                    "description": (
                        "Stored daily closing prices. This is not an adjusted-close "
                        "total-return series; dividend adjustments are not included."
                    ),
                },
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
                    "gap": purge_gap,
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
                        "The target is the H-session close-to-close return after next-session-close execution: C[t+H+1] / C[t+1] - 1."
                    ),
                    (
                        "A purge gap of H+1 observations separates training labels from test forecast origins."
                    ),
                    (
                        "The ML strategy uses non-overlapping forecasts. A signal at close t enters at close t+1, earns H return sessions, and exits at close t+H+1."
                    ),
                    (
                        "Transaction costs and slippage are charged at each execution: entry and exit for a round trip; continuous comparators also liquidate at the final close."
                    ),
                    (
                        "Sharpe and Sortino ratios use a zero risk-free-rate assumption."
                    ),
                    (
                        "The backtest uses the stored close_price field rather than "
                        "adjusted_close; dividend-adjusted total returns are not represented."
                    ),
                    (
                        "Trade win rate and average trade returns use completed, fully closed round trips; an open final position is excluded. Buy & Hold is normally one continuous completed position, not a set of daily trades."
                    ),
                    (
                        "Gross return excludes transaction costs and slippage; net return includes both. The gross-to-net drag is the difference between compounded gross and compounded net returns."
                    ),
                    (
                        "Transaction-cost and slippage totals are return-space deductions summed against the normalised starting capital, not absolute cash fees in USD. Turnover is the sum of absolute position-weight changes."
                    ),
                    (
                        "Transaction costs and slippage are explicit backtest assumptions and are not guarantees of actual execution costs."
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
                result[key] = (
                    float(value) if math.isfinite(float(value)) else None
                )
            else:
                result[key] = value
        return result

    @staticmethod
    def _serialize_trade(trade):
        """Return a JSON-safe completed-trade ledger row."""
        serialized = {}
        for key, value in trade.items():
            if value is None:
                serialized[key] = None
            elif isinstance(value, (int, float)):
                if not math.isfinite(float(value)):
                    serialized[key] = None
                elif isinstance(value, int) and not isinstance(value, bool):
                    serialized[key] = int(value)
                else:
                    serialized[key] = float(value)
            else:
                serialized[key] = str(value)
        return serialized
