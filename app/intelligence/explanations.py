"""
FareIndex India — Deterministic Explanation Generator
Generates transparent, factual, template-based explanations for Second Opinion comparisons without LLMs.
"""
from __future__ import annotations

from typing import Any, Optional


def generate_explanation(comparison_result: dict[str, Any]) -> str:
    """
    Generates a deterministic explanation summarizing why the FareIndex empirical signal
    and Google Flights signal agree or diverge.
    
    Adheres to strict transparency guidelines:
    - Never speculates on internal proprietary model details.
    - Presents exact numerical baselines and signal gaps.
    - Explicitly states: 'The two signals use different reference datasets and methodologies.'
    """
    if not isinstance(comparison_result, dict):
        return "Insufficient comparison data available to generate an explanation."

    comparison = comparison_result.get("comparison", {})
    status = comparison.get("status", "INSUFFICIENT_DATA")
    signal_gap = comparison.get("signal_gap")

    fi_data = comparison_result.get("fareindex", {})
    fi_tier = fi_data.get("tier", "UNKNOWN")
    fi_median = fi_data.get("median")
    fi_p25 = fi_data.get("p25")
    fi_p75 = fi_data.get("p75")
    fi_pct = fi_data.get("pct_deviation")

    google_data = comparison_result.get("google", {})
    g_raw_level = google_data.get("price_level")
    g_range_tier = google_data.get("range_tier", "UNKNOWN")
    g_range = google_data.get("typical_price_range")
    g_pct = google_data.get("pct_deviation")

    live_price = comparison_result.get("live_price")

    if status == "INSUFFICIENT_DATA":
        missing_parts = []
        if fi_tier == "UNKNOWN":
            missing_parts.append("FareIndex baseline distribution")
        if g_range_tier == "UNKNOWN" and not g_raw_level:
            missing_parts.append("Google Flights price insights")
        elif g_range_tier == "UNKNOWN":
            missing_parts.append("Google Flights typical price range")
        if live_price is None:
            missing_parts.append("live fare observation")

        detail = f" Missing: {', '.join(missing_parts)}." if missing_parts else ""
        return (
            f"Comparison inconclusive due to insufficient data.{detail} "
            "A second opinion requires both verified domestic distribution baselines and live pricing insights."
        )

    # Contextual strings
    fi_context = ""
    if fi_median is not None and fi_p25 is not None and fi_p75 is not None:
        fi_context = (
            f"FareIndex observed domestic distribution (P25: ₹{fi_p25:,.0f}, Median: ₹{fi_median:,.0f}, P75: ₹{fi_p75:,.0f})"
        )
    else:
        fi_context = "FareIndex observed domestic distribution"

    g_context = ""
    if isinstance(g_range, dict) and g_range.get("low") is not None and g_range.get("high") is not None:
        g_context = f"Google typical range (₹{g_range['low']:,.0f}–₹{g_range['high']:,.0f})"
    else:
        g_context = "Google Flights typical range"

    gap_text = f" (experimental signal gap: {signal_gap:+.1f}%)" if signal_gap is not None else ""

    # 1. Full Divergence
    if status == "FULL_DIVERGENCE":
        g_label = (g_raw_level.upper() if g_raw_level else g_range_tier)
        return (
            f"Google Flights classifies this fare (₹{live_price:,.0f}) as {g_label}, "
            f"while the FareIndex observed domestic distribution places it in the {fi_tier} tier{gap_text}. "
            f"According to {fi_context}, this fare is {fi_pct:+.1f}% relative to our empirical median, "
            f"compared to {g_pct:+.1f}% relative to the {g_context} midpoint. "
            "The two signals use different reference datasets and methodologies."
        )

    # 2. Partial Divergence
    if status == "PARTIAL_DIVERGENCE":
        g_label = (g_raw_level.upper() if g_raw_level else g_range_tier)
        return (
            f"Google Flights indicates a {g_label} price level (range tier: {g_range_tier}), "
            f"whereas FareIndex categorizes this fare (₹{live_price:,.0f}) as {fi_tier}{gap_text}. "
            f"The fare represents a {fi_pct:+.1f}% shift from {fi_context}, "
            f"versus {g_pct:+.1f}% from the {g_context} midpoint. "
            "The two signals use different reference datasets and methodologies."
        )

    # 3. Agreement
    if status == "AGREEMENT":
        return (
            f"Both sources align: Google Flights and FareIndex classify this fare (₹{live_price:,.0f}) as {fi_tier}{gap_text}. "
            f"The live price falls within expected domestic parameters ({fi_context}) "
            f"and matches the {g_context}. "
            "The two signals use different reference datasets and methodologies."
        )

    return "Comparison completed. The two signals use different reference datasets and methodologies."
