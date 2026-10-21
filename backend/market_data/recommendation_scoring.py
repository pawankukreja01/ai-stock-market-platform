
import math


# Initial weights for the available evidence.
# These are design choices, not empirically validated investment weights.
WEIGHTS = {
    "forecast": 0.25,
    "momentum": 0.20,
    "fundamentals": 0.20,
    "risk_adjusted": 0.20,
    "sentiment": 0.10,
    "data_quality": 0.05,
}

MIN_COMPONENTS = 3

# Higher values should be better for every component after normalization.
HIGHER_IS_BETTER = {
    "forecast": True,
    "momentum": True,
    "fundamentals": True,
    "risk_adjusted": True,
    "sentiment": True,
    "data_quality": True,
}


def is_finite_number(value):
    """Return whether value is a finite numeric value."""
    if value is None or isinstance(value, bool):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def percentile_ranks(values, *, higher_is_better=True):
    """
    Map finite values to percentile scores from 0 to 100.

    Missing values remain None. Equal values receive equal scores.
    """
    valid = [
        (index, float(value))
        for index, value in enumerate(values)
        if is_finite_number(value)
    ]

    result = [None] * len(values)

    if not valid:
        return result

    ordered = sorted(valid, key=lambda item: item[1])

    count = len(ordered)
    start = 0

    while start < count:
        end = start + 1

        while (
            end < count
            and ordered[end][1] == ordered[start][1]
        ):
            end += 1

        # Average rank for ties, scaled to 0–100.
        average_rank = ((start + 1) + end) / 2
        percentile = (
            50.0 if count == 1
            else (average_rank - 1) / (count - 1) * 100
        )

        if not higher_is_better:
            percentile = 100.0 - percentile

        for position in range(start, end):
            original_index = ordered[position][0]
            result[original_index] = round(percentile, 2)

        start = end

    return result


def calculate_weighted_score(component_scores):
    """
    Calculate a score from available components.

    Returns None when fewer than MIN_COMPONENTS are available.
    Available weights are rescaled to sum to 1.
    """
    available = {
        name: float(score)
        for name, score in component_scores.items()
        if name in WEIGHTS and is_finite_number(score)
        and 0 <= float(score) <= 100
    }

    if len(available) < MIN_COMPONENTS:
        return None

    total_weight = sum(WEIGHTS[name] for name in available)

    if total_weight <= 0:
        return None

    score = sum(
        WEIGHTS[name] * value
        for name, value in available.items()
    ) / total_weight

    return round(score, 2)


def score_candidate(component_scores, *, eligible=True, reasons=None):
    """
    Return a transparent score result for one candidate.

    Eligibility checks must be performed separately using real
    data-quality and risk rules before a recommendation is returned.
    """
    reasons = list(reasons or [])

    score = calculate_weighted_score(component_scores)

    if not eligible:
        return {
            "score": None,
            "eligible": False,
            "reasons": reasons or ["Candidate failed eligibility checks."],
            "components": component_scores,
        }

    if score is None:
        return {
            "score": None,
            "eligible": False,
            "reasons": reasons + [
                "Insufficient component data to calculate a reliable score."
            ],
            "components": component_scores,
        }

    return {
        "score": score,
        "eligible": True,
        "reasons": reasons,
        "components": component_scores,
    }
