import pandas as pd


# =========================================================
# SELECTION RULES
# =========================================================

PRIMARY_METRIC = "mae"
SECONDARY_METRIC = "rmse"
TERTIARY_METRIC = "directional_accuracy"


def _valid_results(results):
    """
    Keep only results containing valid evaluation metrics.
    """
    return [
        result
        for result in results
        if result.get("mae") is not None
        and result.get("rmse") is not None
        and result.get(
            "directional_accuracy"
        ) is not None
    ]


def rank_model_results(results):
    """
    Rank models using transparent deterministic criteria:

        1. Lower MAE
        2. Lower RMSE
        3. Higher directional accuracy

    No arbitrary weighted score is used.
    """
    valid = _valid_results(
        results
    )

    ranked = sorted(
        valid,
        key=lambda result: (
            result["mae"],
            result["rmse"],
            -result[
                "directional_accuracy"
            ],
        ),
    )

    ranked_results = []

    for rank, result in enumerate(
        ranked,
        start=1,
    ):
        item = result.copy()
        item["rank"] = rank
        ranked_results.append(
            item
        )

    return ranked_results


def get_model_by_name(
    results,
    model_name,
):
    """
    Find a specific model result.
    """
    for result in results:
        if (
            result.get("model")
            == model_name
        ):
            return result

    return None


def get_best_model(
    results,
):
    """
    Select the best model using the transparent
    ranking rules.
    """
    ranked = rank_model_results(
        results
    )

    if not ranked:
        return None

    return ranked[0]


def compare_against_baseline(
    results,
    baseline_name="Historical Mean",
):
    """
    Compare the selected ML model against
    the Historical Mean baseline.

    Returns explicit metric differences.
    """
    best_model = get_best_model(
        results
    )

    baseline = get_model_by_name(
        results,
        baseline_name,
    )

    if best_model is None:
        return {
            "available": False,
            "reason": (
                "No valid model results."
            ),
        }

    if baseline is None:
        return {
            "available": False,
            "reason": (
                f"Baseline '{baseline_name}' "
                "was not found."
            ),
            "selected_model": (
                best_model["model"]
            ),
        }

    mae_improvement = (
        baseline["mae"]
        - best_model["mae"]
    )

    rmse_improvement = (
        baseline["rmse"]
        - best_model["rmse"]
    )

    directional_difference = (
        best_model[
            "directional_accuracy"
        ]
        - baseline[
            "directional_accuracy"
        ]
    )

    return {
        "available": True,

        "selected_model": (
            best_model["model"]
        ),

        "baseline_model": (
            baseline["model"]
        ),

        "mae": {
            "selected_model": (
                best_model["mae"]
            ),
            "baseline": (
                baseline["mae"]
            ),
            "absolute_improvement": (
                mae_improvement
            ),
            "percentage_improvement": (
                (
                    mae_improvement
                    / baseline["mae"]
                )
                if baseline["mae"] != 0
                else None
            ),
            "better": (
                best_model["mae"]
                < baseline["mae"]
            ),
        },

        "rmse": {
            "selected_model": (
                best_model["rmse"]
            ),
            "baseline": (
                baseline["rmse"]
            ),
            "absolute_improvement": (
                rmse_improvement
            ),
            "percentage_improvement": (
                (
                    rmse_improvement
                    / baseline["rmse"]
                )
                if baseline["rmse"] != 0
                else None
            ),
            "better": (
                best_model["rmse"]
                < baseline["rmse"]
            ),
        },

        "directional_accuracy": {
            "selected_model": (
                best_model[
                    "directional_accuracy"
                ]
            ),
            "baseline": (
                baseline[
                    "directional_accuracy"
                ]
            ),
            "difference": (
                directional_difference
            ),
            "better": (
                best_model[
                    "directional_accuracy"
                ]
                > baseline[
                    "directional_accuracy"
                ]
            ),
        },
    }


def build_horizon_selection(
    horizon_result,
):
    """
    Build a transparent model-selection summary
    for one prediction horizon.
    """
    horizon = horizon_result[
        "horizon"
    ]

    results = horizon_result[
        "results"
    ]

    ranked = rank_model_results(
        results
    )

    best = (
        ranked[0]
        if ranked
        else None
    )

    comparison = (
        compare_against_baseline(
            results,
            baseline_name="Historical Mean",
        )
    )

    return {
        "horizon": horizon,

        "total_observations": (
            horizon_result.get(
                "total_observations"
            )
        ),

        "training_observations": (
            horizon_result.get(
                "training_observations"
            )
        ),

        "testing_observations": (
            horizon_result.get(
                "testing_observations"
            )
        ),

        "best_model": (
            best["model"]
            if best
            else None
        ),

        "best_metrics": (
            {
                "mae": best["mae"],
                "rmse": best["rmse"],
                "directional_accuracy": (
                    best[
                        "directional_accuracy"
                    ]
                ),
            }
            if best
            else None
        ),

        "baseline_comparison": (
            comparison
        ),

        "ranked_models": ranked,
    }


def build_selection_report(
    experiment_results,
):
    """
    Build the complete model-selection report
    across all tested horizons.
    """
    selections = []

    for horizon_result in (
        experiment_results
    ):
        selections.append(
            build_horizon_selection(
                horizon_result
            )
        )

    return {
        "selection_method": {
            "primary_metric": (
                PRIMARY_METRIC
            ),
            "secondary_metric": (
                SECONDARY_METRIC
            ),
            "tertiary_metric": (
                TERTIARY_METRIC
            ),
            "description": (
                "Models are ranked by lower MAE, "
                "then lower RMSE, then higher "
                "directional accuracy."
            ),
        },
        "horizons": selections,
    }


def flatten_selection_report(
    report,
):
    """
    Convert the selection report into a pandas
    DataFrame for inspection or later storage.
    """
    rows = []

    for horizon in report[
        "horizons"
    ]:
        best_metrics = (
            horizon["best_metrics"]
        )

        baseline_comparison = (
            horizon[
                "baseline_comparison"
            ]
        )

        mae_comparison = (
            baseline_comparison.get(
                "mae",
                {}
            )
            if baseline_comparison.get(
                "available",
                False
            )
            else {}
        )

        rmse_comparison = (
            baseline_comparison.get(
                "rmse",
                {}
            )
            if baseline_comparison.get(
                "available",
                False
            )
            else {}
        )

        directional_comparison = (
            baseline_comparison.get(
                "directional_accuracy",
                {}
            )
            if baseline_comparison.get(
                "available",
                False
            )
            else {}
        )

        rows.append(
            {
                "horizon": (
                    horizon["horizon"]
                ),

                "best_model": (
                    horizon["best_model"]
                ),

                "mae": (
                    best_metrics["mae"]
                    if best_metrics
                    else None
                ),

                "rmse": (
                    best_metrics["rmse"]
                    if best_metrics
                    else None
                ),

                "directional_accuracy": (
                    best_metrics[
                        "directional_accuracy"
                    ]
                    if best_metrics
                    else None
                ),

                "beats_mean_mae": (
                    mae_comparison.get(
                        "better"
                    )
                    if mae_comparison
                    else None
                ),

                "mae_improvement": (
                    mae_comparison.get(
                        "percentage_improvement"
                    )
                    if mae_comparison
                    else None
                ),

                "beats_mean_rmse": (
                    rmse_comparison.get(
                        "better"
                    )
                    if rmse_comparison
                    else None
                ),

                "rmse_improvement": (
                    rmse_comparison.get(
                        "percentage_improvement"
                    )
                    if rmse_comparison
                    else None
                ),

                "beats_mean_direction": (
                    directional_comparison.get(
                        "better"
                    )
                    if directional_comparison
                    else None
                ),

                "directional_difference": (
                    directional_comparison.get(
                        "difference"
                    )
                    if directional_comparison
                    else None
                ),

                "training_observations": (
                    horizon[
                        "training_observations"
                    ]
                ),

                "testing_observations": (
                    horizon[
                        "testing_observations"
                    ]
                ),
            }
        )

    return pd.DataFrame(
        rows
    )


def explain_selection(
    selection,
):
    """
    Produce a human-readable explanation of
    the current experimental model selection.
    """
    if not selection:
        return (
            "No valid model was available."
        )

    model = selection[
        "best_model"
    ]

    horizon = selection[
        "horizon"
    ]

    comparison = selection[
        "baseline_comparison"
    ]

    if not comparison.get(
        "available",
        False,
    ):
        return (
            f"{model} is currently ranked "
            f"first for the {horizon}-day horizon "
            "based on MAE, RMSE and directional "
            "accuracy. Baseline comparison is "
            "unavailable."
        )

    mae_better = comparison[
        "mae"
    ]["better"]

    rmse_better = comparison[
        "rmse"
    ]["better"]

    direction_better = comparison[
        "directional_accuracy"
    ]["better"]

    if (
        mae_better
        and rmse_better
        and direction_better
    ):
        return (
            f"{model} currently outperforms "
            "the Historical Mean baseline on "
            "MAE, RMSE and directional accuracy "
            f"for the {horizon}-day horizon."
        )

    if (
        mae_better
        and rmse_better
    ):
        return (
            f"{model} currently has lower MAE "
            "and RMSE than the Historical Mean "
            f"baseline for the {horizon}-day "
            "horizon, but does not have higher "
            "directional accuracy."
        )

    if mae_better:
        return (
            f"{model} currently has lower MAE "
            f"than the Historical Mean baseline "
            f"for the {horizon}-day horizon, "
            "although other metrics are not "
            "uniformly better."
        )

    return (
        f"{model} is ranked first among the "
        "tested models by the current selection "
        f"rule for the {horizon}-day horizon, "
        "but it does not beat the Historical "
        "Mean baseline on MAE."
    )