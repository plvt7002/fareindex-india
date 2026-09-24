"""
FareIndex India — Second Opinion Insights Builder
Assembles deterministic signal comparisons, quantiles, and explanations into an API-ready payload.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from .comparator import compare_signals
from .explanations import generate_explanation

logger = logging.getLogger("fareindex.intelligence.insights")


def get_route_baseline(route: str, conn: Optional[Any] = None) -> dict[str, float]:
    """
    Retrieves empirical verified domestic ONE_WAY quantiles (p25, median, p75)
    for a given route from the existing FareIndex database layer.
    """
    from ..db import connect, db
    from ..index_engine import get_public_snapshot_dataframe

    route_clean = str(route).strip().upper()

    def _compute_from_conn(active_conn: Any) -> dict[str, float]:
        df = get_public_snapshot_dataframe(active_conn, target_route=route_clean)
        if df.empty or "price_inr" not in df:
            return {"p25": None, "median": None, "p75": None, "count": 0}

        prices = df["price_inr"].dropna()
        if prices.empty:
            return {"p25": None, "median": None, "p75": None, "count": 0}

        return {
            "p25": round(float(prices.quantile(0.25)), 2),
            "median": round(float(prices.median()), 2),
            "p75": round(float(prices.quantile(0.75)), 2),
            "min": round(float(prices.min()), 2),
            "max": round(float(prices.max()), 2),
            "count": len(prices),
        }

    if conn is not None:
        return _compute_from_conn(conn)

    with db() as active_conn:
        return _compute_from_conn(active_conn)


def build_second_opinion(
    live_price: Optional[float] = None,
    route: Optional[str] = None,
    fareindex_baseline: Optional[dict[str, Any]] = None,
    serpapi_data: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Builds a full Second Opinion report comparing SerpApi Google Flights data
    with FareIndex domestic observations.
    
    Accepts:
    - live_price: primary live price to evaluate (or extracted from serpapi_data)
    - route: route string (e.g. 'HYD-DEL') to auto-fetch baseline if not passed
    - fareindex_baseline: explicit dict with 'p25', 'median', 'p75'
    - serpapi_data: parsed response dict or raw SerpApi dictionary
    """
    # 1. Resolve baseline if not passed explicitly
    baseline = fareindex_baseline
    if baseline is None and route:
        try:
            baseline = get_route_baseline(route)
        except Exception as exc:
            logger.warning("Failed to auto-fetch FareIndex baseline for route %s: %s", route, exc)
            baseline = None

    # 2. Extract price_insights from parsed or raw serpapi_data
    price_insights = None
    extracted_live_price = live_price

    if isinstance(serpapi_data, dict):
        if "price_insights" in serpapi_data:
            # Raw SerpApi response shape
            price_insights = serpapi_data.get("price_insights")
            # If live_price not passed, check best_flights / other_flights for lowest domestic price
            if extracted_live_price is None:
                from ..serpapi.parser import parse_google_flights_response
                parsed = parse_google_flights_response(serpapi_data)
                domestic_prices = [
                    f["price"] for f in parsed.get("all_flights", [])
                    if f.get("is_domestic") and f.get("price") is not None
                ]
                if domestic_prices:
                    extracted_live_price = min(domestic_prices)
                elif parsed.get("lowest_price") is not None:
                    extracted_live_price = parsed.get("lowest_price")
        else:
            # Already normalized parser shape
            price_insights = {
                "lowest_price": serpapi_data.get("lowest_price"),
                "price_level": serpapi_data.get("price_level"),
                "typical_price_range": serpapi_data.get("typical_price_range"),
                "price_history": serpapi_data.get("price_history"),
            }
            if extracted_live_price is None and serpapi_data.get("lowest_price") is not None:
                extracted_live_price = serpapi_data.get("lowest_price")

    # 3. Compare signals
    comparison_res = compare_signals(
        live_price=extracted_live_price,
        fareindex_baseline=baseline,
        serpapi_price_insights=price_insights,
    )

    # 4. Generate explanation
    explanation = generate_explanation(comparison_res)

    # 5. Assemble final structured payload
    result = dict(comparison_res)
    if route:
        result["route"] = str(route).strip().upper()
    result["explanation"] = explanation
    result["methodology"] = {
        "fareindex_basis": "observed domestic fare distribution",
        "comparison_type": "experimental heuristic",
    }

    return result
