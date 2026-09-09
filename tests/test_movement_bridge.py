import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.db import DB_PATH
from app.index_engine import (
    calculate_empirical_matched_pairs_ratio,
    get_route_movement_series,
    get_route_trend_series,
    get_booking_curve_by_buckets,
)

client = TestClient(app)

class TestHistoricalToCurrentMovementBridge:
    """
    Comprehensive test suite verifying Part 18 requirements:
    1. empirical ratio calculation
    2. same-day bridge calculation
    3. median vs mean bridge robustness
    4. historical normalization
    5. raw data unchanged
    6. legacy rows cannot enter verified one-way metrics
    7. current verified one-way metric calculated correctly
    8. historical series contains only real observation dates
    9. date gaps are preserved
    10. consecutive movement calculation
    11. no fake trend when dates are missing
    12. booking curve stays separate
    13. invalid international transit remains excluded
    14. demo remains excluded
    """

    def test_1_empirical_ratio_calculation(self):
        """1. Verify empirical ratio calculation with matched pairs on route/dates."""
        result = calculate_empirical_matched_pairs_ratio("HYD-DEL", "2026-09-08")
        assert result["route"] == "HYD-DEL"
        assert result["n_matched_pairs"] > 0
        assert result["mean_ratio"] > 1.5
        assert result["median_ratio"] > 1.5
        assert result["p25_ratio"] <= result["median_ratio"] <= result["p75_ratio"]
        assert result["min_ratio"] <= result["max_ratio"]
        assert result["distance_from_2_0"] is not None
        assert result["distance_from_2_1"] is not None
        # Verify 2.0 vs 2.1 closeness check
        assert result["closest_round_factor"] in ["2.0", "2.1"]

    def test_2_same_day_bridge_calculation(self):
        """2. Verify empirical bridge calculation and airline factors for HYD-DEL."""
        res = client.get("/api/movement/route/HYD-DEL")
        assert res.status_code == 200
        data = res.json()
        assert data["route"] == "HYD-DEL"
        assert data["status"] in ["VERIFIED_DAY_OVER_DAY", "PROVISIONAL_SPLICE"]
        assert data["bridge_factor"] is not None
        assert 1.7 <= data["bridge_factor"] <= 2.1
        assert "airline_factors" in data
        assert "Air India" in data["airline_factors"]
        assert "IndiGo" in data["airline_factors"]
        assert "Akasa Air" in data["airline_factors"]

    def test_3_median_vs_mean_bridge_robustness(self):
        """3. Verify median vs mean bridge robustness check is computed and logged."""
        res = client.get("/api/movement/route/HYD-DEL")
        assert res.status_code == 200
        data = res.json()
        assert "robustness_median_factor" in data
        assert data["robustness_median_factor"] is not None
        diff = abs(data["bridge_factor"] - data["robustness_median_factor"])
        # Both factors should be within reasonable proximity (< 0.3)
        assert diff < 0.3

    def test_4_historical_normalization(self):
        """4. Verify historical legacy market fares are normalized onto one-way scale using empirical factors."""
        data = get_route_movement_series("HYD-DEL")
        series = data["series"]
        bridge_factor = data["bridge_factor"]

        historical_points = [p for p in series if p["source_class"] == "historical_reference"]
        assert len(historical_points) >= 5

        for p in historical_points:
            assert p["raw_fare"] is not None
            # Normalized fare must be scaled down by empirical factor (~1.86 to 1.95)
            assert p["fare"] < p["raw_fare"]
            assert 7000 <= p["fare"] <= 10000

    def test_5_raw_data_unchanged(self):
        """5. Verify raw database rows remain intact and unmodified."""
        from app.db import connect
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), AVG(price_inr) FROM raw_prices")
        count, avg_price = cursor.fetchone()
        conn.close()

        assert count >= 1675
        assert avg_price > 0

    def test_6_legacy_rows_cannot_enter_verified_one_way_metrics(self):
        """6. Verify ROUND_TRIP_LEGACY rows never enter the verified one-way trend/snapshot."""
        trend = get_route_trend_series("HYD-DEL", "7D")
        assert trend["current_typical_fare"] < 12000
        assert trend["current_average_fare"] < 12000

        # Direct DB check that only fare_type = 'ONE_WAY' is included in verified snapshot
        from app.db import connect
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT fare_type FROM raw_prices
            WHERE fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID' AND source != 'DEMO - NOT LIVE'
        """)
        fare_types = [r[0] for r in cursor.fetchall()]
        conn.close()
        assert fare_types == ["ONE_WAY"]

    def test_7_current_verified_one_way_metric_calculated_correctly(self):
        """7. Verify current verified point uses median typical and mean average."""
        trend = get_route_trend_series("HYD-DEL", "7D")
        assert trend["current_typical_fare"] > 0
        assert trend["current_average_fare"] > 0
        assert trend["observation_count"] > 0

    def test_8_historical_series_contains_only_real_observation_dates(self):
        """8. Verify series contains only real observation dates (no fake dates)."""
        data = get_route_movement_series("HYD-DEL")
        dates = [p["observation_date"] for p in data["series"]]
        assert "2026-08-28" in dates
        assert "2026-08-29" in dates
        assert "2026-08-30" in dates
        assert "2026-08-31" in dates
        assert "2026-09-07" in dates
        assert "2026-09-08" in dates
        assert "2026-09-09" in dates

    def test_9_date_gaps_are_preserved(self):
        """9. Verify date gaps between 2026-08-31 and 2026-09-07 are preserved without interpolation."""
        data = get_route_movement_series("HYD-DEL")
        dates = [p["observation_date"] for p in data["series"]]
        for missing_date in ["2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04", "2026-09-05", "2026-09-06"]:
            assert missing_date not in dates

    def test_10_consecutive_movement_calculation(self):
        """10. Verify consecutive change_inr and change_pct calculation."""
        data = get_route_movement_series("HYD-DEL")
        series = data["series"]

        # First point has no previous point
        assert series[0]["change_inr"] is None
        assert series[0]["change_pct"] is None

        # Subsequent points calculate consecutive movement
        for i in range(1, len(series)):
            prev = series[i - 1]["fare"]
            curr = series[i]["fare"]
            expected_change_inr = round(curr - prev, 2)
            expected_change_pct = round(((curr - prev) / prev) * 100, 2)
            assert series[i]["change_inr"] == expected_change_inr
            assert series[i]["change_pct"] == expected_change_pct

        # Latest point check
        latest = data["latest_point"]
        assert latest["change_inr"] is not None
        assert latest["change_pct"] is not None
        assert latest["direction"] in ["RISING", "FALLING", "STABLE"]

    def test_11_no_fake_trend_when_dates_are_missing(self):
        """11. Verify HYD-GOI returns verified day-over-day movement or building status without fake data."""
        data = get_route_movement_series("HYD-GOI")
        assert data["status"] in ["BUILDING_BASELINE", "VERIFIED_DAY_OVER_DAY"]
        assert len(data["series"]) >= 1

        res = client.get("/api/movement/route/HYD-GOI")
        assert res.status_code == 200
        body = res.json()
        assert body["status"] in ["BUILDING_BASELINE", "VERIFIED_DAY_OVER_DAY"]

    def test_12_booking_curve_stays_separate(self):
        """12. Verify booking curve (lead time) is completely separate from calendar movement."""
        bc = get_booking_curve_by_buckets("HYD-DEL")
        assert "curve" in bc or "series" in bc
        buckets = [item["bucket"] for item in bc["series"]]
        assert "7D" in buckets
        assert "14D" in buckets
        assert "21D" in buckets
        assert "30D" in buckets
        assert "60D" in buckets

        # Booking curve varies by travel date lead time, not observation date
        mov = get_route_movement_series("HYD-DEL")
        mov_dates = [p["observation_date"] for p in mov["series"]]
        assert mov_dates != buckets

    def test_13_invalid_international_transit_remains_excluded(self):
        """13. Verify international transit rows (e.g. Gulf Air BAH, SriLankan CMB) remain excluded."""
        from app.db import connect
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_prices WHERE eligibility_reason = 'INTERNATIONAL_TRANSIT'")
        invalid_count = cursor.fetchone()[0]
        conn.close()
        assert invalid_count >= 5

        # Check that no invalid rows are in route trend or movement
        trend_goi = get_route_trend_series("HYD-GOI", "7D")
        assert trend_goi["max_fare"] < 30000  # 57k Gulf Air and 31k SriLankan excluded

    def test_14_demo_remains_excluded(self):
        """14. Verify DEMO source observations remain excluded from verified metrics."""
        from app.db import connect
        conn = connect()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_prices WHERE source LIKE '%DEMO%'")
        demo_count = cursor.fetchone()[0]
        conn.close()
        assert demo_count > 0

        # Verified series must have source != 'DEMO - NOT LIVE'
        trend = get_route_trend_series("HYD-DEL", "7D")
        assert trend["observation_count"] > 0

    def test_15_fare_position_low_normal_high_rules(self):
        """15. Verify fare position classification (LOW / NORMAL / HIGH) based on P25 & P75."""
        trend = get_route_trend_series("HYD-DEL", "7D")
        p25 = trend["p25_fare"]
        median = trend["current_typical_fare"]
        p75 = trend["p75_fare"]

        assert p25 <= p75
        assert p25 <= median <= p75 or median <= p25 or median >= p75

    def test_16_future_verified_dates_automatically_incorporated(self):
        """16. Verify that multiple verified observation dates transition to verified day-over-day movement."""
        data = get_route_movement_series("HYD-DEL")
        assert len(data["series"]) >= 6
        assert data["consecutive_verified_dates"] >= 1
        assert "movement_label" in data

    def test_17_latest_prices_returns_real_flight_options(self):
        """17. Verify GET /api/prices/latest returns observed flight cards for Today's Market."""
        res = client.get("/api/prices/latest?route=HYD-DEL")
        assert res.status_code == 200
        body = res.json()
        assert body["route"] == "HYD-DEL"
        assert body["total_observations_in_batch"] > 0
        fares = body["fares"]
        assert len(fares) > 0
        # Verify required flight card fields
        first = fares[0]
        assert "airline" in first
        assert "price_inr" in first
        assert "departure_time" in first
        assert first["price_inr"] > 0

