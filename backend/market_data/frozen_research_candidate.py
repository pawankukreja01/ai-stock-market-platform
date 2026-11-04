"""Research-only frozen candidate: no production imports or model selection."""
import hashlib
import json
from pathlib import Path

from backtesting import generate_walk_forward_predictions
from ml_final_validation import build_final_validation_report
from market_data.management.commands.validate_stock_forecasts import (
    build_model_scorecard, model_beats_all_baselines,
)
from market_data.research_pipeline_experiments import ridge_factory
from walk_forward import describe_fold, generate_walk_forward_splits

LOCK_FILE = Path(__file__).with_name("frozen_research_candidate.json")
FROZEN_SPEC = {
    "candidate_id": "ridge-zero-anchor-expanding-alpha1000-price-volume-v1",
    "selected_on": "2026-11-04",
    "selection_evidence": "2026-11-02 four-stock 72-configuration development ablation; not independent validation",
    "model": "zero_anchor_ridge",
    "ridge_alpha": 1000,
    "ridge_fit_intercept": False,
    "imputation": "training_fold_median",
    "scaling": "training_fold_standard_scaler",
    "training_window": "expanding",
    "feature_set": "price_volume",
    "price_basis": "unadjusted_close_price",
    "target": "C[t+H+1]/C[t+1]-1",
    "horizons_trading_days": [1, 5, 20, 60],
    "min_train": 500,
    "test_size": 100,
    "step_size": 100,
    "label_purge": "H+1_rows",
    "benchmark_features": "none",
    "validation_status": "frozen_candidate_not_validated",
    "approved_for_live_prediction": False,
    "claims_profitable": False,
}


def load_frozen_spec(path=LOCK_FILE):
    raw = Path(path).read_bytes()
    try:
        spec = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("Invalid frozen candidate JSON.") from exc
    if spec != FROZEN_SPEC:
        raise ValueError("Frozen candidate lock mismatch: rejecting model-parameter drift.")
    return spec, hashlib.sha256(raw).hexdigest()


def evaluate_frozen_candidate(X, y, *, horizon):
    """Existing folds and return target; no adaptive tuning or live model changes."""
    if horizon not in FROZEN_SPEC["horizons_trading_days"]:
        raise ValueError("Horizon is not part of the frozen evaluation plan.")
    if not X.index.is_unique or not X.index.is_monotonic_increasing or not X.index.equals(y.index):
        raise ValueError("Feature and target dates must align and be chronological.")
    if not len(X.columns) or any(
        name.startswith(("target_", "benchmark_", "relative_")) or
        name.endswith("_by_vol20") for name in X.columns
    ):
        raise ValueError("Frozen candidate requires original price/volume-only features.")
    folds = generate_walk_forward_splits(
        X, y, minimum_train_size=FROZEN_SPEC["min_train"],
        test_size=FROZEN_SPEC["test_size"],
        horizon=horizon, step_size=FROZEN_SPEC["step_size"],
    )
    if len(folds) < 3:
        raise ValueError("Fewer than three eligible purged walk-forward folds.")
    if any(f["train_start"] != 0 or f["gap"] != horizon + 1 for f in folds):
        raise ValueError("Frozen expanding-window or purge protocol was altered.")
    pred = generate_walk_forward_predictions(X, y, folds, lambda: ridge_factory(1000))
    described = [describe_fold(X, fold) for fold in folds]
    report = build_final_validation_report(X, y, described, pred, FROZEN_SPEC["model"], horizon)
    return {
        "status": "evaluated",
        "folds": len(folds),
        "out_of_sample_observations": report["protocol"]["out_of_sample_observations"],
        "oos_start": described[0]["test_start_date"],
        "oos_end": described[-1]["test_end_date"],
        "scorecard": build_model_scorecard(report),
        "model_metrics": report["metrics"]["selected_model"],
        "baselines": {key: report["metrics"][key]
                      for key in ("zero_return", "historical_mean", "momentum")},
        "beats_all_baselines_on_mae": model_beats_all_baselines(report),
        "fold_metrics": report["fold_metrics"],
        "historical_window_role": "development_diagnostic_not_independent_holdout",
    }
