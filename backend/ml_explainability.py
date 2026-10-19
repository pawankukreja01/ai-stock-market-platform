
import numpy as np
import shap


def _transform_features(pipeline, frame, feature_names):
    """Apply the same preprocessing used by the fitted pipeline."""
    values = frame.loc[:, feature_names]

    imputer = pipeline.named_steps.get("imputer")
    if imputer is not None:
        values = imputer.transform(values)
    else:
        values = values.to_numpy(dtype=float)

    scaler = pipeline.named_steps.get("scaler")
    if scaler is not None:
        values = scaler.transform(values)

    return np.asarray(values, dtype=float)


def _as_2d_array(values):
    """Normalize SHAP output to (samples, features)."""
    if isinstance(values, list):
        values = values[0]

    array = np.asarray(values, dtype=float)

    # Handle single-output models that return an extra axis.
    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[:, :, 0]

    if array.ndim == 1:
        array = array.reshape(1, -1)

    if array.ndim != 2:
        raise ValueError(
            f"Unexpected SHAP output shape: {array.shape}"
        )

    return array


def explain_prediction(
    model,
    background_features,
    instance_features,
    evaluation_features,
    max_global_features=10,
):
    """
    Explain one predicted return and rank global feature importance.

    The fitted sklearn Pipeline is explained without changing
    its trained estimator or prediction values.

    SHAP contributions are in the model's output units:
    decimal future returns.
    """
    if instance_features.empty:
        raise ValueError("No feature row was provided to explain.")

    feature_names = list(instance_features.columns)

    if not feature_names:
        raise ValueError("The feature matrix has no columns.")

    if background_features.empty:
        raise ValueError("The SHAP background dataset is empty.")

    background = background_features.loc[:, feature_names]

    # A reproducible background sample keeps explanations practical.
    background = background.sample(
        n=min(40, len(background)),
        random_state=42,
    )

    background_transformed = _transform_features(
        model, background, feature_names
    )
    instance_transformed = _transform_features(
        model, instance_features, feature_names
    )

    estimator = model.named_steps.get("model")
    if estimator is None:
        raise ValueError(
            "The fitted pipeline has no 'model' step."
        )

    if hasattr(estimator, "feature_importances_"):
        explainer = shap.TreeExplainer(
            estimator,
            data=background_transformed,
            feature_perturbation="interventional",
        )
        model_type = "tree"
    elif hasattr(estimator, "coef_"):
        explainer = shap.LinearExplainer(
            estimator,
            background_transformed,
        )
        model_type = "linear"
    else:
        raise ValueError(
            f"Unsupported estimator: {type(estimator).__name__}"
        )

    # Local explanation for the latest observation.
    local_explanation = explainer(instance_transformed)
    local_values = _as_2d_array(local_explanation.values)[0]

    base_value = float(
        np.asarray(local_explanation.base_values)
        .reshape(-1)[0]
    )

    prediction = float(
        np.asarray(model.predict(instance_features))
        .reshape(-1)[0]
    )

    local_row = instance_features.iloc[0]
    local_contributions = []

    for name, shap_value in zip(feature_names, local_values):
        raw_value = local_row[name]

        if raw_value is None or not np.isfinite(float(raw_value)):
            feature_value = None
        else:
            feature_value = float(raw_value)

        shap_value = float(shap_value)

        local_contributions.append({
            "feature": str(name),
            "feature_value": feature_value,
            "shap_value": round(shap_value, 10),
            "contribution_percentage_points": round(
                shap_value * 100, 6
            ),
            "effect_relative_to_baseline": (
                "increases_prediction"
                if shap_value > 0
                else "decreases_prediction"
                if shap_value < 0
                else "no_change"
            ),
        })

    local_contributions.sort(
        key=lambda item: abs(item["shap_value"]),
        reverse=True,
    )

    # Global importance is measured on held-out evaluation rows.
    # Fall back to background rows if there are no evaluation rows.
    if evaluation_features.empty:
        global_frame = background
    else:
        global_frame = evaluation_features.loc[:, feature_names]

    global_frame = global_frame.sample(
        n=min(50, len(global_frame)),
        random_state=42,
    )

    global_transformed = _transform_features(
        model, global_frame, feature_names
    )

    global_explanation = explainer(global_transformed)
    global_values = _as_2d_array(global_explanation.values)

    mean_abs_values = np.mean(
        np.abs(global_values),
        axis=0,
    )

    global_importance = [
        {
            "feature": str(name),
            "mean_absolute_shap": round(float(value), 10),
            "mean_absolute_contribution_percentage_points": round(
                float(value) * 100, 6
            ),
        }
        for name, value in zip(feature_names, mean_abs_values)
    ]

    global_importance.sort(
        key=lambda item: item["mean_absolute_shap"],
        reverse=True,
    )

    reconstructed_prediction = (
        base_value + float(np.sum(local_values))
    )

    return {
        "available": True,
        "method": "SHAP",
        "model_type": model_type,
        "target": "predicted_future_return",
        "baseline_return": round(base_value, 10),
        "predicted_return": round(prediction, 10),
        "reconstructed_return": round(
            reconstructed_prediction, 10
        ),
        "additivity_difference": round(
            prediction - reconstructed_prediction, 10
        ),
        "local_feature_contributions": local_contributions,
        "global_feature_importance": global_importance[
            :max_global_features
        ],
        "global_evaluation_rows": len(global_frame),
        "notes": [
            (
                "A positive SHAP value pushes the model prediction "
                "above its baseline; a negative value pushes it below."
            ),
            (
                "Global importance is the mean absolute SHAP value "
                "on the sampled evaluation rows."
            ),
            (
                "Feature contributions describe model attribution, "
                "not causal effects or guaranteed market outcomes."
            ),
        ],
    }
