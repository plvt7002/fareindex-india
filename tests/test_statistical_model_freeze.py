import pytest
import sqlite3
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

from app.main import app
from app.db import connect, init_db
from app.index_engine import (
    rebuild_route_indices,
    get_public_snapshot_dataframe,
    get_route_movement_series,
    get_route_trend_series,
    get_routes_summary,
    get_national_composite_index,
    calculate_empirical_matched_pairs_ratio,
    compute_fare_distribution,
    BUCKET_LABELS,
)

client = TestClient(app)

class TestStatisticalModelFreeze:
    @classmethod
    def setup_class(cls):
        init_db()
        rebuild_route_indices()

    def test_1_daily_median_is_primary_market_metric(self):
        """Rule 1: Primary daily market metric is MEDIAN across canonical market snapshot."""
        mov = get_route_movement_series("HYD-DEL")
        assert mov["primary_market_metric"] == "median"
        assert mov["latest_point"]["fare"] == 8731.50
        assert mov["daily_median_fare"] == 8731.50

    def test_2_daily_mean_remains_secondary(self):
        """Rule 2: Daily mean is preserved as secondary descriptive metric."""
        mov = get_route_movement_series("HYD-DEL")
        assert mov["daily_mean_fare"] == 9323.64
        assert mov["latest_point"]["daily_mean_fare"] == 9323.64

    def test_3_index_uses_daily_median(self):
        """Rule 3: Route index is computed as (daily_median / baseline) * 100."""
        conn = connect()
        try:
            row = conn.execute("""
                SELECT observation_date, avg_fare, median_fare, baseline_fare, index_value
                FROM index_values
                WHERE route = 'HYD-DEL' AND observation_date = '2026-09-09'
            """).fetchone()
            assert row is not None
            assert row["median_fare"] == 8731.50
            assert row["baseline_fare"] == 7959.18
            expected_idx = round((8731.50 / 7959.18) * 100, 2)
            assert row["index_value"] == expected_idx  # 109.70
        finally:
            conn.close()

    def test_4_baseline_uses_historical_daily_market_medians(self):
        """Rule 4: Baseline is the median of usable historical daily market medians (unweighted)."""
        mov = get_route_movement_series("HYD-DEL")
        assert mov["baseline_market_fare"] == 7959.18

    def test_5_each_date_contributes_once_to_baseline(self):
        """Rule 5: Each historical observation date contributes exactly one unweighted median."""
        conn = connect()
        try:
            matched_stats = calculate_empirical_matched_pairs_ratio(route="HYD-DEL", observation_date="2026-09-08", conn=conn)
            global_fallback = matched_stats.get("global_fallback_factor") or 1.8960
            airline_factors_map = {}
            for air_k, air_v in (matched_stats.get("airline_factors") or {}).items():
                if air_v.get("is_eligible"):
                    airline_factors_map[air_k] = air_v.get("effective_factor", global_fallback)

            df_hist = pd.read_sql_query("""
                SELECT id, route, airline, price_inr, travel_date, SUBSTR(search_timestamp, 1, 10) as observation_date
                FROM raw_prices
                WHERE route = 'HYD-DEL'
                  AND source != 'DEMO - NOT LIVE'
                  AND (fare_type = 'ROUND_TRIP_LEGACY' OR fare_type = 'UNKNOWN')
                  AND SUBSTR(search_timestamp, 1, 10) < '2026-09-08'
                ORDER BY observation_date
            """, conn)

            df_hist["norm_fare"] = df_hist.apply(lambda r: r["price_inr"] / airline_factors_map.get(r["airline"], global_fallback), axis=1)
            daily_medians = [round(float(g["norm_fare"].median()), 2) for _, g in df_hist.groupby("observation_date")]
            assert len(daily_medians) == 5  # 5 distinct historical dates
            assert daily_medians == [7917.09, 7917.09, 7959.18, 7959.18, 8701.44]
            computed_baseline = round(float(np.median(daily_medians)), 2)
            assert computed_baseline == 7959.18
        finally:
            conn.close()

    def test_6_same_day_duplicate_runs_are_deduplicated(self):
        """Rule 6: Multi-run same-day observations select only the latest run per bucket."""
        conn = connect()
        try:
            df_snap = get_public_snapshot_dataframe(conn, target_route="HYD-DEL")
            sep8_rows = df_snap[df_snap["observation_date"] == "2026-09-08"]
            assert len(sep8_rows) == 180  # Canonical snapshot deduplicated from raw 538 rows
        finally:
            conn.close()

    def test_7_travel_horizons_do_not_change_calendar_movement_population(self):
        """Rule 7: Calendar movement uses full canonical daily population."""
        mov = get_route_movement_series("HYD-DEL")
        latest = mov["latest_point"]
        assert latest["observation_count"] == 154  # Full Sep 9 canonical snapshot count

    def test_8_1_to_10d_label_is_used_for_7d(self):
        """Rule 8: 7D bucket label is 'Near-term · 1–10 days'."""
        assert BUCKET_LABELS["7D"] == "Near-term · 1–10 days"

    def test_9_current_near_term_median_is_correct(self):
        """Rule 9: Near-term 1-10D median is computed dynamically (Sep 9: 9268.0)."""
        trend = get_route_trend_series("HYD-DEL", lead_time_bucket="7D")
        assert trend["current_typical_fare"] == 9268.0
        assert trend["observation_count"] == 57

    def test_10_current_near_term_mean_is_correct(self):
        """Rule 10: Near-term 1-10D mean is computed dynamically (Sep 9: 9671.81)."""
        trend = get_route_trend_series("HYD-DEL", lead_time_bucket="7D")
        assert trend["current_average_fare"] == 9671.81

    def test_11_movement_uses_median(self):
        """Rule 11: Day-over-day movement is current median vs previous median."""
        mov = get_route_movement_series("HYD-DEL")
        # Sep 9 median (8731.50) - Sep 8 median (8503.50) = +228.00 (+2.68%)
        assert mov["latest_change_inr"] == 228.00
        assert mov["latest_change_pct"] == 2.68
        assert mov["trend_direction"] == "RISING"

    def test_12_sep8_to_sep9_uses_verified_to_verified_median(self):
        """Rule 12: Sep 8 -> Sep 9 is verified-to-verified without historical bridge."""
        mov = get_route_movement_series("HYD-DEL")
        assert mov["status"] == "VERIFIED_DAY_OVER_DAY"
        assert mov["latest_point"]["movement_type"] == "VERIFIED_DAY_OVER_DAY"

    def test_13_legacy_round_trip_cannot_enter_one_way_analytics(self):
        """Rule 13: ROUND_TRIP_LEGACY is strictly excluded from public snapshot."""
        conn = connect()
        try:
            df = get_public_snapshot_dataframe(conn)
            assert (df["fare_type"] != "ONE_WAY").sum() == 0
        finally:
            conn.close()

    def test_14_legitimate_high_fares_remain_in_analytics(self):
        """Rule 14: ₹22,702 remains in max, mean, and distribution analytics."""
        conn = connect()
        try:
            df = get_public_snapshot_dataframe(conn, target_route="HYD-DEL")
            sep9 = df[df["observation_date"] == "2026-09-09"]
            assert float(sep9["price_inr"].max()) == 22702.0
            dist = compute_fare_distribution(sep9["price_inr"])
            assert dist["max_fare"] == 22702.0
        finally:
            conn.close()

    def test_15_representative_filtering_does_not_alter_analytics(self):
        """Rule 15: Route analytics and statistics reflect full 154 rows."""
        summary = get_routes_summary("HYD-DEL")
        assert len(summary) == 1
        assert summary[0]["all_time_max_fare"] >= 22702.0

    def test_16_individual_observed_rows_use_price_inr(self):
        """Rule 16: Individual flights return actual raw price_inr."""
        res = client.get("/api/prices/latest?route=HYD-DEL")
        assert res.status_code == 200
        data = res.json()
        fares = data["fares"]
        prices = [f["price_inr"] for f in fares]
        assert len(set(prices)) > 5  # Distinct individual prices
        assert min(prices) == 7373.0
        assert max(prices) == 22702.0

    def test_17_missing_prices_are_never_replaced_by_median(self):
        """Rule 17: Row price is never overwritten by median/typical aggregate."""
        res = client.get("/api/prices/latest?route=HYD-DEL")
        data = res.json()
        for f in data["fares"]:
            assert f["price_inr"] == f["observed_fare"]

    def test_18_national_composite_is_labelled_provisional(self):
        """Rule 18: National index endpoint returns Tracked-Route Composite (Provisional)."""
        res = client.get("/api/index/national")
        assert res.status_code == 200
        data = res.json()
        assert "Provisional" in data["index_name"]

    def test_19_historical_bridge_does_not_mix_old_means_with_new_medians(self):
        """Rule 19: Historical reference series uses normalized daily medians."""
        mov = get_route_movement_series("HYD-DEL")
        hist_points = [s for s in mov["series"] if s["source_class"] == "historical_reference"]
        for p in hist_points:
            assert p["fare"] == p["daily_median_fare"]
            assert p["fare"] != p["daily_mean_fare"] or p["observation_count"] < 5

    def test_20_old_15268_baseline_cannot_enter_current_index(self):
        """Rule 20: Old ₹15,268.36 baseline is nowhere in active index values."""
        conn = connect()
        try:
            rows = conn.execute("SELECT baseline_fare FROM index_values WHERE route = 'HYD-DEL'").fetchall()
            for r in rows:
                assert r["baseline_fare"] == 7959.18
                assert r["baseline_fare"] != 15268.36
        finally:
            conn.close()
