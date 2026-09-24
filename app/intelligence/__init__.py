"""
FareIndex India — Second Opinion Intelligence Package
Deterministic signal comparison and transparent, factual insights.
"""
from .comparator import (
    compare_signals,
    determine_fareindex_tier,
    determine_google_range_tier,
)
from .explanations import generate_explanation
from .insights import build_second_opinion, get_route_baseline

__all__ = [
    "compare_signals",
    "determine_fareindex_tier",
    "determine_google_range_tier",
    "generate_explanation",
    "build_second_opinion",
    "get_route_baseline",
]
