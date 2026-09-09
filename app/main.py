from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .config import SCRAPE_INTERVAL_HOURS, TRACKED_ROUTES, ROUTE_WEIGHTS
from .db import init_db, db
from .index_engine import (
    rebuild_route_indices,
    get_national_composite_index,
    get_routes_summary,
    get_booking_curve_analytics,
    get_booking_curve_by_buckets,
    get_airline_analytics,
    get_collection_health_summary,
    get_route_trend_series,
    get_route_movement_series,
    calculate_empirical_matched_pairs_ratio,
)
from .scrape_service import scrape_all_routes, scrape_status

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Build index immediately from any data already in SQLite.
    rebuild_route_indices()

    # Automatic backend refresh.
    scheduler.add_job(
        scrape_all_routes,
        "interval",
        hours=SCRAPE_INTERVAL_HOURS,
        id="airfare-refresh",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    yield

    scheduler.shutdown(wait=False)

app = FastAPI(
    title="FareIndex India API",
    description="Market Indicator & Airfare Index Engine for Indian Domestic Aviation",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "project": "FareIndex India",
        "description": "Indian Airfare Price Index & Market Indicator",
        "status": "running",
        "docs": "/docs",
        "tracked_routes": TRACKED_ROUTES,
        "index_base": 100.0,
    }

@app.get("/api/health")
def health():
    """Health check endpoint for frontend and monitoring."""
    return {
        "status": "online",
        "service": "FareIndex India Backend",
        "database": "connected",
        "tracked_routes": TRACKED_ROUTES,
    }

@app.get("/api/health/collection")
def collection_health():
    """Returns collection health, consecutive observation counts, and lead-time statistics."""
    return get_collection_health_summary()

@app.get("/api/trend/route/{route}")
def route_trend(route: str, bucket: str = Query("7D", description="Lead-time bucket horizon: 7D, 14D, 21D, 30D, 60D")):
    """Returns standardized daily observation trend time-series for a specific route and lead-time horizon."""
    return get_route_trend_series(target_route=route, lead_time_bucket=bucket)

@app.get("/api/movement/route/{route}")
def route_movement(route: str):
    """
    Returns calendar market movement series bridging historical reference observations
    onto the current verified scale (HYD-DEL), or building status (HYD-GOI).
    """
    return get_route_movement_series(target_route=route)

@app.get("/api/movement/matched-pairs/ratio")
def matched_pairs_ratio():
    """
    Returns empirical matched-pair ratio analysis between legacy round-trip observations
    and verified one-way observations on overlapping dates.
    """
    return calculate_empirical_matched_pairs_ratio()


@app.get("/api/routes")
def routes():
    """Returns list of distinct routes available in the database."""
    with db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT route FROM raw_prices ORDER BY route"
        ).fetchall()
    return [r["route"] for r in rows]

@app.get("/api/routes/summary")
def routes_summary(route: Optional[str] = Query(None, description="Optional target route filter, e.g. HYD-DEL")):
    """
    Returns comprehensive summary metrics for all available routes or a specific route:
    - Latest index & previous observation change
    - Latest, baseline, minimum and maximum fares
    - Total observation count and date range
    - Tracked airlines
    """
    summaries = get_routes_summary(target_route=route)
    if route and not summaries:
        raise HTTPException(status_code=404, detail=f"No route summary data found for {route.upper()}")
    return summaries

@app.get("/api/index/national")
def national_index():
    """
    Returns National Composite Airfare Index:
    - Weighted composite of route-level indices across observation dates
    - Full transparency on route weights and contributing routes per date
    """
    return get_national_composite_index()

@app.get("/api/index/route/{route}")
def route_index(route: str):
    """Returns daily observation index points and provisional baseline for a specific route."""
    route_upper = route.upper()
    with db() as conn:
        rows = conn.execute("""
            SELECT observation_date, avg_fare, median_fare, baseline_fare, index_value
            FROM index_values
            WHERE route = ?
            ORDER BY observation_date
        """, (route_upper,)).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No index data for {route_upper}")

    return {
        "route": route_upper,
        "primary_metric": "median",
        "baseline_method": "median of available historical daily market medians (Base = 100)",
        "values": [dict(r) for r in rows],
    }

@app.get("/api/booking-curve/route/{route}")
def route_booking_curve(route: str):
    """
    Returns standardized booking lead-time curve for a specific route:
    - Segregated into 7D, 14D, 21D, 30D, 60D buckets
    - Provides typical_fare (median), average_fare (mean), min, max, count
    """
    result = get_booking_curve_by_buckets(target_route=route)
    if result["total_observations"] == 0:
        raise HTTPException(status_code=404, detail=f"No flight observations found for route {route.upper()}")
    return result

@app.get("/api/distribution/route/{route}")
def route_distribution(
    route: str,
    bucket: str = Query("7D", description="Lead-time bucket horizon: 7D, 14D, 21D, 30D, 60D"),
):
    """
    Returns dynamic histogram distribution for a specific route and lead-time bucket.
    """
    trend_data = get_route_trend_series(target_route=route, lead_time_bucket=bucket)
    if trend_data["observation_count"] == 0:
        raise HTTPException(status_code=404, detail=f"No flight observations found for route {route.upper()} in bucket {bucket}")
    return {
        "route": route.upper(),
        "lead_time_bucket": bucket,
        "lead_time_label": trend_data["lead_time_label"],
        "distribution": trend_data["distribution"],
        "current_typical_fare": trend_data["current_typical_fare"],
        "current_average_fare": trend_data["current_average_fare"],
        "min_fare": trend_data["min_fare"],
        "max_fare": trend_data["max_fare"],
        "observation_count": trend_data["observation_count"],
    }

@app.get("/api/analytics/booking-curve")
def booking_curve(route: Optional[str] = Query(None, description="Optional target route, e.g. HYD-DEL")):
    """
    Returns booking lead-time curve (average fare by advance booking days):
    - lead_time_days = travel_date - search_date
    - Exposes usable vs missing travel_date count for transparency
    """
    result = get_booking_curve_analytics(target_route=route)
    if route and result["total_observations"] == 0:
        raise HTTPException(status_code=404, detail=f"No flight observations found for route {route.upper()}")
    return result

@app.get("/api/analytics/airlines")
def airline_analytics(route: Optional[str] = Query(None, description="Optional target route, e.g. HYD-DEL")):
    """
    Returns airline price breakdown and price dispersion (min, avg, max, spread, observation count)
    for a given route or across all routes.
    """
    result = get_airline_analytics(target_route=route)
    if route and result["total_observations"] == 0:
        raise HTTPException(status_code=404, detail=f"No airline data found for route {route.upper()}")
    return result

@app.get("/api/prices/latest")
def latest_prices(
    route: str = Query(..., description="Target route code, e.g. HYD-DEL"),
    fare_type: Optional[str] = Query(None, description="Optional filter by fare_type: ONE_WAY, ROUND_TRIP_LEGACY, or ALL"),
):
    """
    Returns the latest batch of raw fare observations for a route, including full data provenance.
    Supports separate queries for ONE_WAY (default) and ROUND_TRIP_LEGACY.
    """
    route_upper = route.upper()
    fare_type_upper = fare_type.upper() if fare_type else None

    with db() as conn:
        if fare_type_upper in ("ROUND_TRIP", "ROUND_TRIP_LEGACY"):
            latest_row = conn.execute("""
                SELECT MAX(search_timestamp) AS ts
                FROM raw_prices
                WHERE route = ? AND fare_type = 'ROUND_TRIP_LEGACY' AND source != 'DEMO' AND price_inr > 0
            """, (route_upper,)).fetchone()
            latest = latest_row["ts"] if latest_row else None
            if latest is None:
                raise HTTPException(status_code=404, detail=f"No round-trip fare data found for route {route_upper}")

            rows = conn.execute("""
                SELECT id, route, origin, destination, airline, source, price_inr,
                       travel_date, class, stops, departure_time, arrival_time,
                       seats_left, search_timestamp, fare_type, domestic_eligibility
                FROM raw_prices
                WHERE route = ? AND search_timestamp = ? AND fare_type = 'ROUND_TRIP_LEGACY' AND source != 'DEMO' AND price_inr > 0
                ORDER BY price_inr ASC
            """, (route_upper, latest)).fetchall()
        elif fare_type_upper == "ONE_WAY":
            latest_row = conn.execute("""
                SELECT MAX(search_timestamp) AS ts
                FROM raw_prices
                WHERE route = ? AND fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID' AND source != 'DEMO' AND price_inr > 0
            """, (route_upper,)).fetchone()
            latest = latest_row["ts"] if latest_row and latest_row["ts"] else None
            if latest is None:
                latest_row = conn.execute("SELECT MAX(search_timestamp) AS ts FROM raw_prices WHERE route = ?", (route_upper,)).fetchone()
                latest = latest_row["ts"] if latest_row else None
            if latest is None:
                raise HTTPException(status_code=404, detail=f"No fare data found for route {route_upper}")

            rows = conn.execute("""
                SELECT id, route, origin, destination, airline, source, price_inr,
                       travel_date, class, stops, departure_time, arrival_time,
                       seats_left, search_timestamp, fare_type, domestic_eligibility
                FROM raw_prices
                WHERE route = ? AND search_timestamp = ? AND fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID' AND source != 'DEMO' AND price_inr > 0
                ORDER BY price_inr ASC
            """, (route_upper, latest)).fetchall()
        else:
            # Default: Latest available batch (prioritizing verified ONE_WAY if present)
            latest_row = conn.execute("""
                SELECT MAX(search_timestamp) AS ts
                FROM raw_prices
                WHERE route = ? AND fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID' AND source != 'DEMO' AND price_inr > 0
            """, (route_upper,)).fetchone()
            latest = latest_row["ts"] if latest_row and latest_row["ts"] else None

            if latest is not None:
                rows = conn.execute("""
                    SELECT id, route, origin, destination, airline, source, price_inr,
                           travel_date, class, stops, departure_time, arrival_time,
                           seats_left, search_timestamp, fare_type, domestic_eligibility
                    FROM raw_prices
                    WHERE route = ? AND search_timestamp = ? AND fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID' AND source != 'DEMO' AND price_inr > 0
                    ORDER BY price_inr ASC
                """, (route_upper, latest)).fetchall()
            else:
                latest_row = conn.execute("SELECT MAX(search_timestamp) AS ts FROM raw_prices WHERE route = ?", (route_upper,)).fetchone()
                latest = latest_row["ts"] if latest_row else None
                if latest is None:
                    raise HTTPException(status_code=404, detail=f"No fare data found for route {route_upper}")
                rows = conn.execute("""
                    SELECT id, route, origin, destination, airline, source, price_inr,
                           travel_date, class, stops, departure_time, arrival_time,
                           seats_left, search_timestamp, fare_type, domestic_eligibility
                    FROM raw_prices
                    WHERE route = ? AND search_timestamp = ?
                    ORDER BY price_inr ASC
                """, (route_upper, latest)).fetchall()

    fares_list = []
    for r in rows:
        row_dict = dict(r)
        price_val = float(row_dict.get("price_inr") or 0.0)
        row_dict["price_inr"] = price_val
        row_dict["observed_fare"] = price_val
        src = row_dict.get("source") or "Recovered Data"
        if src in ("Unknown", "Google Flights"):
            row_dict["provenance"] = f"Recovered Data ({src})"
        else:
            row_dict["provenance"] = src
        fares_list.append(row_dict)

    return {
        "route": route_upper,
        "fare_type": fare_type_upper or "ONE_WAY",
        "latest_search_timestamp": latest,
        "total_observations_in_batch": len(fares_list),
        "fares": fares_list,
    }

@app.post("/api/admin/rebuild-index")
def rebuild_index():
    """Triggers complete index recalculation across all raw price observations."""
    return rebuild_route_indices()

@app.post("/api/admin/scrape-now")
def scrape_now():
    """Manual demo trigger: executes collection across tracked routes and rebuilds indices."""
    result = scrape_all_routes()
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result)
    return result

@app.get("/api/admin/scrape-status")
def get_scrape_status():
    """Returns the status, timing, and outcome of the last fare collection run."""
    return scrape_status()

