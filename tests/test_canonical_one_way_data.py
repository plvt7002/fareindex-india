"""
Tests for Stage 5 — FareIndex Data Cleanup + Analytics Rebuild + Product Consistency
Validates that:
1. Genuine one-way observation is included.
2. Two-way-derived observation is excluded.
3. Synthetic/demo observation does not enter production analytics.
4. Fare values are not divided by two.
5. FareIndex quantiles use only canonical one-way observations.
6. Second Opinion uses the same canonical population.
7. Existing routes continue working.
8. Existing analytics endpoints still work.
9. Existing Second Opinion API still works.
10. Domestic filtering remains intact.
"""
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
    get_routes_summary,
    get_route_movement_series,
    get_route_trend_series,
    get_national_composite_index,
    get_booking_curve_by_buckets,
    get_airline_analytics,
)
from app.intelligence.insights import get_route_baseline, build_second_opinion

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def ensure_db_clean():
    init_db()
    rebuild_route_indices()


def test_1_genuine_one_way_observation_included():
    """1. Verify genuine verified one-way domestic observations are included in canonical snapshot."""
    conn = connect()
    try:
        df = get_public_snapshot_dataframe(conn)
        assert not df.empty
        assert len(df) == 418  # 334 HYD-DEL + 84 HYD-GOI
        assert (df["fare_type"] == "ONE_WAY").all()
        assert (df["domestic_eligibility"] == "VALID").all()
    finally:
        conn.close()


def test_2_two_way_derived_observation_excluded():
    """2. Verify ROUND_TRIP_LEGACY / two-way derived observations are completely excluded."""
    conn = connect()
    try:
        df = get_public_snapshot_dataframe(conn)
        assert "ROUND_TRIP_LEGACY" not in df["fare_type"].values
        assert (df["fare_type"] != "ONE_WAY").sum() == 0
    finally:
        conn.close()


def test_3_synthetic_demo_does_not_enter_production_analytics():
    """3. Verify DEMO / NOT LIVE data does not enter production analytics or baselines."""
    conn = connect()
    try:
        df = get_public_snapshot_dataframe(conn)
        assert not df["source"].astype(str).str.contains("DEMO", case=False).any()
        assert not df["source"].astype(str).str.contains("NOT LIVE", case=False).any()
    finally:
        conn.close()


def test_4_fare_values_are_not_divided_by_two():
    """4. Verify raw price_inr values are used directly without dividing by 2 or arbitrary factors."""
    conn = connect()
    try:
        df_snap = get_public_snapshot_dataframe(conn, target_route="HYD-DEL")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, price_inr FROM raw_prices
            WHERE route = 'HYD-DEL' AND fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID'
        """)
        raw_prices = dict(cursor.fetchall())
        for _, row in df_snap.iterrows():
            row_id = row["id"]
            if row_id in raw_prices:
                assert float(row["price_inr"]) == float(raw_prices[row_id])
    finally:
        conn.close()


def test_5_fareindex_quantiles_use_only_canonical_one_way():
    """5. Verify FareIndex quantiles (P25, median, P75) compute strictly from canonical one-way snapshot."""
    conn = connect()
    try:
        df_del = get_public_snapshot_dataframe(conn, target_route="HYD-DEL")
        p25 = round(float(df_del["price_inr"].quantile(0.25)), 2)
        median = round(float(df_del["price_inr"].median()), 2)
        p75 = round(float(df_del["price_inr"].quantile(0.75)), 2)

        baseline = get_route_baseline("HYD-DEL", conn=conn)
        assert baseline["p25"] == p25 == 8288.0
        assert baseline["median"] == median == 8643.5
        assert baseline["p75"] == p75 == 9990.5
        assert baseline["count"] == len(df_del) == 334
    finally:
        conn.close()


def test_6_second_opinion_uses_same_canonical_population():
    """6. Verify Second Opinion baseline exactly matches the FareIndex Market Analytics dataset."""
    baseline_del = get_route_baseline("HYD-DEL")
    baseline_goi = get_route_baseline("HYD-GOI")

    assert baseline_del["count"] == 334
    assert baseline_del["p25"] == 8288.0
    assert baseline_del["median"] == 8643.5
    assert baseline_del["p75"] == 9990.5

    assert baseline_goi["count"] == 84
    assert baseline_goi["p25"] == 5149.0
    assert baseline_goi["median"] == 6439.0
    assert baseline_goi["p75"] == 8504.5

    # Check that build_second_opinion utilizes these exact quantiles
    opinion = build_second_opinion(
        live_price=7542.0,
        route="HYD-DEL",
        fareindex_baseline=baseline_del,
        serpapi_data={"lowest_price": 7542, "price_level": "HIGH", "typical_price_range": [6400, 7500]},
    )
    assert opinion["fareindex"]["p25"] == 8288.0
    assert opinion["fareindex"]["median"] == 8643.5
    assert opinion["fareindex"]["p75"] == 9990.5
    assert opinion["fareindex"]["tier"] == "LOW"


def test_7_existing_routes_continue_working():
    """7. Verify existing routes (HYD-DEL, HYD-GOI) are listed and functional."""
    res = client.get("/api/routes")
    assert res.status_code == 200
    routes = res.json()
    assert "HYD-DEL" in routes
    assert "HYD-GOI" in routes


def test_8_existing_analytics_endpoints_still_work():
    """8. Verify all existing analytics endpoints return valid responses."""
    endpoints = [
        "/api/routes/summary",
        "/api/index/national",
        "/api/index/route/HYD-DEL",
        "/api/index/route/HYD-GOI",
        "/api/booking-curve/route/HYD-DEL",
        "/api/distribution/route/HYD-DEL",
        "/api/movement/route/HYD-DEL",
        "/api/movement/route/HYD-GOI",
        "/api/analytics/airlines?route=HYD-DEL",
        "/api/prices/latest?route=HYD-DEL",
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Endpoint {ep} failed with status {res.status_code}"


def test_9_existing_second_opinion_api_still_works():
    """9. Verify GET /api/second-opinion returns the expected structure and calibrated baseline."""
    res = client.get("/api/second-opinion?origin=HYD&destination=DEL&outbound_date=2026-09-29")
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "HYD-DEL"
    assert data["live_price"] == 7542.0
    assert data["fareindex"]["p25"] == 8288.0
    assert data["fareindex"]["median"] == 8643.5
    assert data["fareindex"]["p75"] == 9990.5
    assert data["fareindex"]["tier"] == "LOW"
    assert data["fareindex"]["observation_count"] == 334
    assert data["google"]["range_tier"] == "HIGH"
    assert data["google"]["price_level"].upper() == "HIGH"
    assert data["comparison"]["status"] == "FULL_DIVERGENCE"


def test_10_domestic_filtering_remains_intact():
    """10. Verify international transit itineraries remain excluded from domestic baseline."""
    conn = connect()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_prices WHERE eligibility_reason = 'INTERNATIONAL_TRANSIT'")
        assert cursor.fetchone()[0] == 5

        df_snap = get_public_snapshot_dataframe(conn)
        assert (df_snap["domestic_eligibility"] == "VALID").all()
        assert not df_snap["airline"].astype(str).str.contains("Gulf Air").any()
        assert not df_snap["airline"].astype(str).str.contains("SriLankan").any()
    finally:
        conn.close()
