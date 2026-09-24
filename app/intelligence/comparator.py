"""
FareIndex India — Deterministic Signal Comparator
Compares Google Flights SerpApi signals against calibrated FareIndex empirical domestic baselines.
"""
from __future__ import annotations

from typing import Any, Optional


TIER_ORDER = {"LOW": 1, "TYPICAL": 2, "HIGH": 3}


def determine_fareindex_tier(live_price: Optional[float], p25: Optional[float], p75: Optional[float]) -> str:
    """Classifies live price against FareIndex empirical P25/P75 percentiles."""
    if live_price is None or p25 is None or p75 is None:
        return "UNKNOWN"
    try:
        lp = float(live_price)
        p25_val = float(p25)
        p75_val = float(p75)
    except (ValueError, TypeError):
        return "UNKNOWN"

    if lp < p25_val:
        return "LOW"
    elif lp <= p75_val:
        return "TYPICAL"
    else:
        return "HIGH"


def determine_google_range_tier(live_price: Optional[float], range_low: Optional[float], range_high: Optional[float]) -> str:
    """Classifies live price against Google Flights typical price range."""
    if live_price is None or range_low is None or range_high is None:
        return "UNKNOWN"
    try:
        lp = float(live_price)
        r_low = float(range_low)
        r_high = float(range_high)
    except (ValueError, TypeError):
        return "UNKNOWN"

    if lp < r_low:
        return "LOW"
    elif lp <= r_high:
        return "TYPICAL"
    else:
        return "HIGH"


def compare_signals(
    live_price: Optional[float],
    fareindex_baseline: Optional[dict[str, Any]],
    serpapi_price_insights: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """
    Deterministically compares live fare against FareIndex distribution and Google Flights range.
    
    Inputs:
    - live_price: primary live comparable domestic fare
    - fareindex_baseline: dict with 'p25', 'median', 'p75'
    - serpapi_price_insights: dict with 'lowest_price', 'price_level', 'typical_price_range'
    
    Returns structured comparison results including tiers, percentage deviations, signal gap,
    and divergence classification.
    """
    # 1. Parse live price
    parsed_live_price: Optional[float] = None
    if live_price is not None:
        try:
            parsed_live_price = float(live_price)
        except (ValueError, TypeError):
            parsed_live_price = None

    # Fallback to serpapi lowest_price if live_price not passed
    if parsed_live_price is None and serpapi_price_insights:
        raw_lowest = serpapi_price_insights.get("lowest_price")
        if raw_lowest is not None:
            try:
                parsed_live_price = float(raw_lowest)
            except (ValueError, TypeError):
                parsed_live_price = None

    # 2. Extract FareIndex baseline
    fi_p25: Optional[float] = None
    fi_median: Optional[float] = None
    fi_p75: Optional[float] = None
    if isinstance(fareindex_baseline, dict):
        for k, v in [("p25", "p25"), ("median", "median"), ("p75", "p75")]:
            val = fareindex_baseline.get(k)
            if val is not None:
                try:
                    if k == "p25":
                        fi_p25 = float(val)
                    elif k == "median":
                        fi_median = float(val)
                    elif k == "p75":
                        fi_p75 = float(val)
                except (ValueError, TypeError):
                    pass

    # 3. Extract SerpApi Google insights
    google_raw_level: Optional[str] = None
    typical_low: Optional[float] = None
    typical_high: Optional[float] = None
    if isinstance(serpapi_price_insights, dict):
        raw_pl = serpapi_price_insights.get("price_level")
        if raw_pl is not None:
            google_raw_level = str(raw_pl).strip()

        tr = serpapi_price_insights.get("typical_price_range")
        if isinstance(tr, dict):
            if tr.get("low") is not None and tr.get("high") is not None:
                try:
                    typical_low = float(tr["low"])
                    typical_high = float(tr["high"])
                except (ValueError, TypeError):
                    pass
        elif isinstance(tr, (list, tuple)) and len(tr) == 2:
            try:
                typical_low = float(tr[0])
                typical_high = float(tr[1])
            except (ValueError, TypeError):
                pass

    # 4. Determine Tiers
    fareindex_tier = determine_fareindex_tier(parsed_live_price, fi_p25, fi_p75)
    google_range_tier = determine_google_range_tier(parsed_live_price, typical_low, typical_high)

    # 5. Raw Level Disagreement
    raw_level_disagreement: Optional[bool] = None
    if google_raw_level is not None and fareindex_tier != "UNKNOWN":
        raw_level_disagreement = (fareindex_tier != google_raw_level.strip().upper())

    # 6. Percentage Deviations & Signal Gap
    fareindex_pct: Optional[float] = None
    if parsed_live_price is not None and fi_median is not None and fi_median > 0:
        fareindex_pct = round(((parsed_live_price - fi_median) / fi_median) * 100.0, 2)

    serpapi_mid: Optional[float] = None
    serpapi_pct: Optional[float] = None
    if typical_low is not None and typical_high is not None:
        serpapi_mid = round((typical_low + typical_high) / 2.0, 2)
        if parsed_live_price is not None and serpapi_mid > 0:
            serpapi_pct = round(((parsed_live_price - serpapi_mid) / serpapi_mid) * 100.0, 2)

    signal_gap: Optional[float] = None
    if fareindex_pct is not None and serpapi_pct is not None:
        signal_gap = round(fareindex_pct - serpapi_pct, 2)

    # 7. Classification
    status = "INSUFFICIENT_DATA"
    if fareindex_tier != "UNKNOWN" and google_range_tier != "UNKNOWN" and signal_gap is not None:
        tier_diff = abs(TIER_ORDER[fareindex_tier] - TIER_ORDER[google_range_tier])
        abs_gap = abs(signal_gap)

        if tier_diff == 0 and abs_gap < 10.0:
            status = "AGREEMENT"
        elif tier_diff == 2 or abs_gap >= 25.0:
            status = "FULL_DIVERGENCE"
        else:
            status = "PARTIAL_DIVERGENCE"

    return {
        "live_price": parsed_live_price,
        "fareindex": {
            "p25": fi_p25,
            "median": fi_median,
            "p75": fi_p75,
            "tier": fareindex_tier,
            "pct_deviation": fareindex_pct,
        },
        "google": {
            "price_level": google_raw_level,
            "typical_price_range": {
                "low": typical_low,
                "high": typical_high,
            } if (typical_low is not None and typical_high is not None) else None,
            "range_midpoint": serpapi_mid,
            "range_tier": google_range_tier,
            "pct_deviation": serpapi_pct,
        },
        "comparison": {
            "status": status,
            "signal_gap": signal_gap,
            "raw_level_disagreement": raw_level_disagreement,
        },
    }
