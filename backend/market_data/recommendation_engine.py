"""Stocks-only recommendation ranking using stored market data."""

from datetime import date, timedelta

from django.db.models import OuterRef, Subquery

from stocks.models import Stock
from .models import HistoricalPrice
from .recommendation_features import extract_candidate_features
from .recommendation_scoring import percentile_ranks


MIN_COMPONENTS = 3
MIN_SENTIMENT_ARTICLES = 3

# Provisional weights: these are not empirically validated.
RISK_TOLERANCE_WEIGHTS = {
    "low": {
        "momentum": 0.15,
        "fundamentals": 0.25,
        "risk_adjusted": 0.40,
        "sentiment": 0.05,
        "data_quality": 0.15,
    },
    "moderate": {
        "momentum": 0.25,
        "fundamentals": 0.25,
        "risk_adjusted": 0.25,
        "sentiment": 0.10,
        "data_quality": 0.15,
    },
    "high": {
        "momentum": 0.35,
        "fundamentals": 0.20,
        "risk_adjusted": 0.15,
        "sentiment": 0.15,
        "data_quality": 0.15,
    },
}


def horizon_adjusted_weights(risk_tolerance, horizon_months=12):
    """Transparent, provisional preference weighting; NOT a return forecast.

    Short horizons place more weight on recent momentum and less on
    fundamentals. Longer horizons reverse this preference. All shifts
    preserve the total weight and the selected risk-tolerance baseline.
    A dedicated walk-forward study must validate these heuristic choices.
    """
    if risk_tolerance not in RISK_TOLERANCE_WEIGHTS:
        raise ValueError("Unsupported risk tolerance.")
    if isinstance(horizon_months, bool) or not isinstance(horizon_months, int):
        raise ValueError("horizon_months must be an integer.")
    if not 1 <= horizon_months <= 600:
        raise ValueError("horizon_months must be between 1 and 600.")

    weights = dict(RISK_TOLERANCE_WEIGHTS[risk_tolerance])
    if horizon_months <= 6:
        shift = 0.08
    elif horizon_months >= 24:
        shift = -0.08
    else:
        shift = 0.0

    weights["momentum"] = round(weights["momentum"] + shift, 4)
    weights["fundamentals"] = round(weights["fundamentals"] - shift, 4)
    return weights


def _average_available(values, minimum=1):
    available = [
        float(value)
        for value in values
        if value is not None
    ]
    if len(available) < minimum:
        return None
    return round(sum(available) / len(available), 2)


def _metric_ranks(records, getter, *, higher_is_better=True):
    return percentile_ranks(
        [getter(record) for record in records],
        higher_is_better=higher_is_better,
    )


def _component_ranks(records):
    """Build component percentiles using only eligible candidates."""

    technical = lambda r: r["technical"]
    fundamentals = lambda r: r["fundamentals"]
    risk = lambda r: r["risk"]
    sentiment = lambda r: r["sentiment"]

    momentum_metrics = [
        _metric_ranks(
            records,
            lambda r: technical(r).get("return_20d"),
        ),
        _metric_ranks(
            records,
            lambda r: technical(r).get("sma20_ratio"),
        ),
        _metric_ranks(
            records,
            lambda r: technical(r).get("sma50_ratio"),
        ),
    ]

    fundamental_metrics = [
        _metric_ranks(
            records,
            lambda r: fundamentals(r).get("roe"),
        ),
        _metric_ranks(
            records,
            lambda r: fundamentals(r).get("profit_margin"),
        ),
        _metric_ranks(
            records,
            lambda r: fundamentals(r).get("operating_margin"),
        ),
        _metric_ranks(
            records,
            lambda r: fundamentals(r).get("current_ratio"),
        ),
        _metric_ranks(
            records,
            lambda r: (
                fundamentals(r).get("debt_to_equity")
                if fundamentals(r).get("debt_to_equity") is None
                or fundamentals(r).get("debt_to_equity") >= 0
                else None
            ),
            higher_is_better=False,
        ),
        _metric_ranks(
            records,
            lambda r: (
                fundamentals(r).get("pe_ratio")
                if fundamentals(r).get("pe_ratio") is not None
                and fundamentals(r).get("pe_ratio") > 0
                else None
            ),
            higher_is_better=False,
        ),
    ]

    risk_metrics = [
        _metric_ranks(
            records,
            lambda r: risk(r).get("annualised_volatility"),
            higher_is_better=False,
        ),
        # The risk engine reports drawdown as a negative return.
        # Rank its absolute magnitude in the lower-is-better direction.
        _metric_ranks(
            records,
            lambda r: (
                abs(risk(r)["maximum_drawdown"])
                if risk(r).get("maximum_drawdown") is not None
                else None
            ),
            higher_is_better=False,
        ),
        _metric_ranks(
            records,
            lambda r: risk(r).get("sharpe_ratio"),
        ),
        _metric_ranks(
            records,
            lambda r: risk(r).get("sortino_ratio"),
        ),
    ]

    sentiment_metrics = [
        _metric_ranks(
            records,
            lambda r: (
                sentiment(r).get("sentiment_score")
                if sentiment(r).get("sentiment_articles", 0)
                >= MIN_SENTIMENT_ARTICLES
                else None
            ),
        ),
    ]

    quality_metrics = [
        _metric_ranks(
            records,
            lambda r: r["risk"].get("risk_observations"),
        ),
        _metric_ranks(
            records,
            lambda r: r.get("price_age_days"),
            higher_is_better=False,
        ),
    ]

    components = []

    for index, record in enumerate(records):
        momentum = _average_available(
            [metric[index] for metric in momentum_metrics],
            minimum=1,
        )
        fundamental = _average_available(
            [metric[index] for metric in fundamental_metrics],
            minimum=2,
        )
        risk_score = _average_available(
            [metric[index] for metric in risk_metrics],
            minimum=2,
        )
        sentiment_score = _average_available(
            [metric[index] for metric in sentiment_metrics],
            minimum=1,
        )
        data_quality = _average_available(
            [metric[index] for metric in quality_metrics],
            minimum=1,
        )

        components.append({
            "momentum": momentum,
            "fundamentals": fundamental,
            "risk_adjusted": risk_score,
            "sentiment": sentiment_score,
            "data_quality": data_quality,
            # Forecast intentionally remains unavailable until
            # the existing ML pipeline is safely integrated.
            "forecast": None,
        })

    return components


def _weighted_score(components, weights):
    available = {
        name: value
        for name, value in components.items()
        if name in weights
        and value is not None
        and 0 <= value <= 100
    }

    if len(available) < MIN_COMPONENTS:
        return None

    total_weight = sum(weights[name] for name in available)
    if total_weight <= 0:
        return None

    return round(
        sum(weights[name] * value for name, value in available.items())
        / total_weight,
        2,
    )


def _explanations(components):
    explanations = []

    labels = {
        "momentum": "historical momentum",
        "fundamentals": "available fundamental metrics",
        "risk_adjusted": "historical risk metrics",
        "sentiment": "analysed news sentiment",
        "data_quality": "data coverage and freshness",
    }

    for name, label in labels.items():
        value = components.get(name)
        if value is None:
            explanations.append(f"No score available for {label}.")
        elif value >= 70:
            explanations.append(
                f"Relatively strong {label} versus this candidate universe."
            )
        elif value <= 30:
            explanations.append(
                f"Relatively weak {label} versus this candidate universe."
            )

    if components.get("forecast") is None:
        explanations.append(
            "No forecast component is included in this score."
        )

    return explanations


def rank_feature_records(feature_records, *, risk_tolerance="moderate",
                         max_candidates=20, horizon_months=12):
    """
    Rank already-extracted feature records.

    Useful for deterministic tests and for keeping data retrieval
    separate from the ranking logic.
    """
    weights = horizon_adjusted_weights(risk_tolerance, horizon_months)

    if not 1 <= max_candidates <= 100:
        raise ValueError("max_candidates must be between 1 and 100.")

    eligible = [
        record for record in feature_records
        if record.get("data_quality", {}).get("eligible_for_scoring")
    ]

    components_by_record = _component_ranks(eligible)

    ranked = []

    for record, components in zip(eligible, components_by_record):
        score = _weighted_score(components, weights)

        if score is None:
            continue

        coverage = record.get("data_quality", {})
        evidence_count = sum(
            components.get(name) is not None
            for name in ("momentum", "fundamentals", "risk_adjusted",
                         "sentiment", "data_quality")
        )
        # "Evidence coverage" reports missing inputs, not a probabilistic
        # confidence that an investment will be profitable.
        evidence = {
            "available_components": evidence_count,
            "total_components": 5,
            "percentage": int(evidence_count / 5 * 100),
            "price_age_days": record.get("price_age_days"),
            "risk_observations": record.get("risk", {}).get("risk_observations"),
            "has_fundamentals": coverage.get(
                "fundamental_data_available",
                any(
                    value is not None
                    for value in record.get("fundamentals", {}).values()
                ),
            ),
            "sentiment_articles": coverage.get(
                "sentiment_articles",
                record.get("sentiment", {}).get("sentiment_articles", 0),
            ),
            "note": "Source coverage, not predicted-return confidence or accuracy.",
        }
        warnings = []
        if evidence_count <= 3:
            warnings.append("Limited independent research evidence is available.")
        if not evidence["has_fundamentals"]:
            warnings.append("No stored fundamentals were available for this stock.")
        if evidence["sentiment_articles"] < MIN_SENTIMENT_ARTICLES:
            warnings.append("News sentiment has insufficient analyzed articles.")
        if evidence["price_age_days"] is not None and evidence["price_age_days"] > 3:
            warnings.append("Stored closing price is several calendar days old.")
        ranked.append({
            "evidence": evidence,
            "research_warnings": warnings,
            "symbol": record["symbol"],
            "company_name": record["company_name"],
            "exchange": record["exchange"],
            "currency": record.get("currency"),
            "sector": record.get("sector"),
            "industry": record.get("industry"),
            "latest_price": record.get("latest_price"),
            "latest_price_date": record.get("latest_price_date"),
            "score": score,
            "risk_tolerance": risk_tolerance,
            "components": components,
            "explanations": _explanations(components),
            "data_quality": record["data_quality"],
        })

    ranked.sort(key=lambda item: (-item["score"], item["symbol"]))

    for rank, item in enumerate(ranked, start=1):
        item["rank"] = rank

    excluded = [
        {
            "symbol": record.get("symbol"),
            "reasons": record.get("data_quality", {}).get("exclusion_reasons", []) or
                ["Insufficient independent evidence to calculate a valid score."],
        }
        for record in feature_records
        if record not in eligible or record.get("symbol") not in {
            item["symbol"] for item in ranked
        }
    ]

    return {
        "ranking_method": "research_percentile_heuristics_not_predictive_probabilities",
        "data_as_of": None,
        "excluded_candidates": excluded[:50],
        "risk_tolerance": risk_tolerance,
        "horizon_months": horizon_months,
        "weighting_method": "provisional_horizon_adjusted_research_heuristic",
        "candidate_universe_size": len(feature_records),
        "eligible_candidate_count": len(eligible),
        "scored_candidate_count": len(ranked),
        "scoring_weights": weights,
        "forecast_included": False,
        "results": ranked[:max_candidates],
        "disclaimer": (
            "Research ranking based on historical stored data. "
            "Scores are relative percentiles, not probabilities of profit "
            "or guarantees of future performance."
        ),
    }


def recommend_stocks(*, risk_tolerance="moderate", market=None,
                     max_candidates=20, horizon_months=12, as_of=None,
                     symbols=None):
    """
    Extract features for all active stocks with recent stored prices,
    then rank the eligible universe. max_candidates limits the response,
    not the input universe.
    """
    as_of = as_of or date.today()
    latest_price_date = (
        HistoricalPrice.objects
        .filter(
            stock_id=OuterRef("pk"),
            date__lte=as_of,
            close_price__gt=0,
        )
        .order_by("-date", "-id")
        .values("date")[:1]
    )

    queryset = (
        Stock.objects
        .filter(is_active=True)
        .annotate(latest_stored_price_date=Subquery(latest_price_date))
        .filter(
            latest_stored_price_date__gte=as_of - timedelta(days=7),
            latest_stored_price_date__lte=as_of,
        )
        .order_by("symbol")
    )

    if market:
        queryset = queryset.filter(exchange__iexact=market.strip())
    if symbols is not None:
        # Research-only explicit cohort filter. No limit or future-data
        # filtering is performed using information after as_of.
        if not isinstance(symbols, (list, tuple)) or not symbols:
            raise ValueError("Explicit research cohort must be a nonempty list.")
        if any(not isinstance(v, str) or not v.strip() for v in symbols):
            raise ValueError("Invalid research cohort symbol.")
        queryset = queryset.filter(symbol__in=symbols)

    features = []

    for stock in queryset.iterator():
        try:
            features.append(
                extract_candidate_features(stock, as_of=as_of)
            )
        except Exception:
            # A single malformed stock should not crash the whole request.
            # It is omitted rather than assigned invented feature values.
            import logging
            logging.getLogger(__name__).exception(
                "Recommendation feature extraction failed for %s",
                stock.symbol,
            )

    result = rank_feature_records(
        features,
        risk_tolerance=risk_tolerance,
        max_candidates=max_candidates,
        horizon_months=horizon_months,
    )
    result["data_as_of"] = as_of.isoformat()
    result["freshness_max_age_days"] = 7
    result["fresh_candidate_universe"] = len(features)
    return result
