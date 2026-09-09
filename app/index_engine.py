from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd

from .config import ROUTE_WEIGHTS, DEFAULT_ROUTE_WEIGHTS, TRACKED_ROUTES
from .db import connect

def assign_lead_time_bucket(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates lead_time_days = (travel_date - observation_date).days
    and assigns standard lead_time_bucket: '7D', '14D', '21D', '30D', '60D'.
    """
    if df.empty:
        df["lead_time_days"] = pd.Series(dtype="float64")
        df["lead_time_bucket"] = pd.Series(dtype="object")
        return df

    obs_dt = pd.to_datetime(df["observation_date"], errors="coerce")
    trv_dt = pd.to_datetime(df["travel_date"], errors="coerce")
    df["lead_time_days"] = (trv_dt - obs_dt).dt.days

    def map_bucket(days: Any) -> str:
        if pd.isna(days) or days is None:
            return "UNKNOWN"
        try:
            d = int(round(float(days)))
        except (ValueError, TypeError):
            return "UNKNOWN"

        if d <= 10:
            return "7D"
        elif 11 <= d <= 17:
            return "14D"
        elif 18 <= d <= 25:
            return "21D"
        elif 26 <= d <= 45:
            return "30D"
        else:
            return "60D"

    df["lead_time_bucket"] = df["lead_time_days"].apply(map_bucket)
    return df

BUCKET_LABELS = {
    "7D": "Near-term · 1–10 days",
    "14D": "14D · 11–17 days",
    "21D": "21D · 18–25 days",
    "30D": "30D · 26–45 days",
    "60D": "60D · 46+ days",
}

BUCKET_NOMINAL_DAYS = {
    "7D": 7,
    "14D": 14,
    "21D": 21,
    "30D": 30,
    "60D": 60,
}

def compute_fare_distribution(prices: pd.Series) -> dict[str, Any]:
    """
    Computes dynamic histogram / frequency distribution bins for a price series.
    Provides counts, percentages, and indicators for where median and mean cluster.
    """
    if prices is None or len(prices) == 0:
        return {
            "bins": [],
            "median_fare": None,
            "average_fare": None,
            "min_fare": None,
            "max_fare": None,
            "p10_fare": None,
            "p25_fare": None,
            "p75_fare": None,
            "p90_fare": None,
            "total_observations": 0,
        }

    total = len(prices)
    median_val = round(float(prices.median()), 2)
    avg_val = round(float(prices.mean()), 2)
    min_val = round(float(prices.min()), 2)
    max_val = round(float(prices.max()), 2)
    p10 = round(float(prices.quantile(0.10)), 2)
    p25 = round(float(prices.quantile(0.25)), 2)
    p75 = round(float(prices.quantile(0.75)), 2)
    p90 = round(float(prices.quantile(0.90)), 2)

    raw_edges = [0, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 12000, 15000, 20000, 25000, 35000, 50000, 100000]
    lower_edges = [e for e in raw_edges if e <= min_val]
    start_edge = lower_edges[-1] if lower_edges else raw_edges[0]
    upper_edges = [e for e in raw_edges if e >= max_val]
    end_edge = upper_edges[0] if upper_edges else raw_edges[-1]

    selected_edges = [e for e in raw_edges if start_edge <= e <= end_edge]
    if len(selected_edges) < 4:
        step = max(500, int((max_val - min_val) / 5)) if max_val > min_val else 1000
        start = int(min_val // step * step)
        selected_edges = [start + i * step for i in range(7)]
        selected_edges = [e for e in selected_edges if e <= max_val + step]

    bins_data = []
    for i in range(len(selected_edges) - 1):
        low = selected_edges[i]
        high = selected_edges[i+1]
        is_last = (i == len(selected_edges) - 2)
        if is_last:
            mask = (prices >= low) & (prices <= high)
        else:
            mask = (prices >= low) & (prices < high)

        count = int(mask.sum())
        pct = round((count / total) * 100, 1) if total > 0 else 0.0

        low_label = f"₹{low//1000}k" if low >= 1000 else f"₹{low}"
        high_label = f"₹{high//1000}k" if high >= 1000 else f"₹{high}"
        label = f"{low_label}–{high_label}"

        has_median = (low <= median_val <= high) if is_last else (low <= median_val < high)
        has_mean = (low <= avg_val <= high) if is_last else (low <= avg_val < high)

        bins_data.append({
            "bin_label": label,
            "min_price": float(low),
            "max_price": float(high),
            "count": count,
            "percentage": pct,
            "has_median": bool(has_median),
            "has_mean": bool(has_mean),
        })

    return {
        "bins": bins_data,
        "median_fare": median_val,
        "average_fare": avg_val,
        "min_fare": min_val,
        "max_fare": max_val,
        "p10_fare": p10,
        "p25_fare": p25,
        "p75_fare": p75,
        "p90_fare": p90,
        "total_observations": total,
    }

def get_public_snapshot_dataframe(
    conn: Any,
    target_route: str | None = None,
    target_bucket: str | None = None,
) -> pd.DataFrame:
    """
    Extracts the clean public observation snapshot DataFrame:
    1) Strictly enforces fare_type = 'ONE_WAY' and domestic_eligibility = 'VALID'.
    2) Excludes synthetic demo rows ('DEMO - NOT LIVE') and invalid prices (<= 0 or NULL).
    3) Standardizes lead-time buckets: '7D', '14D', '21D', '30D', '60D'.
    4) For production live scrapers (e.g. Playwright, Amadeus), when multiple collection runs
       exist on the same (route, observation_date, lead_time_bucket),
       selects ONLY the observations belonging to the LATEST successful collection run
       (max search_timestamp) for that (route, observation_date, lead_time_bucket).
    5) Preserves cross-day longitudinal observations across different observation dates.
    """
    query = """
        SELECT id, route, origin, destination, airline, source, price_inr,
               travel_date, search_timestamp, class, stops, departure_time,
               arrival_time, seats_left, fare_type, domestic_eligibility, eligibility_reason
        FROM raw_prices
        WHERE price_inr IS NOT NULL
          AND price_inr > 0
          AND search_timestamp IS NOT NULL
          AND source NOT LIKE '%DEMO%'
          AND source NOT LIKE '%NOT LIVE%'
          AND UPPER(fare_type) = 'ONE_WAY'
          AND UPPER(domestic_eligibility) = 'VALID'
    """
    params: list[Any] = []
    if target_route:
        query += " AND UPPER(route) = ?"
        params.append(target_route.upper())

    df = pd.read_sql_query(query, conn, params=params)
    if df.empty:
        return df

    df["observation_date"] = df["search_timestamp"].astype(str).str.slice(0, 10)
    df["price_inr"] = pd.to_numeric(df["price_inr"], errors="coerce")
    df = df.dropna(subset=["route", "observation_date", "price_inr"])

    if df.empty:
        return df

    # Assign standardized lead-time buckets
    df = assign_lead_time_bucket(df)

    # For live scrapers on the same (route, observation_date, lead_time_bucket), select latest collection run
    is_live_scraper = df["source"].astype(str).str.contains("Playwright|Amadeus", case=False, regex=True)
    df_live = df[is_live_scraper].copy()
    df_hist = df[~is_live_scraper].copy()

    if not df_live.empty:
        latest_live_ts = df_live.groupby(["route", "observation_date", "lead_time_bucket"])["search_timestamp"].transform("max")
        df_live_latest = df_live[df_live["search_timestamp"] == latest_live_ts].copy()
    else:
        df_live_latest = df_live

    df_snapshot = pd.concat([df_live_latest, df_hist], ignore_index=True)

    if target_bucket:
        df_snapshot = df_snapshot[df_snapshot["lead_time_bucket"].astype(str).str.upper() == target_bucket.upper()].copy()

    return df_snapshot

def rebuild_route_indices() -> dict[str, Any]:
    """
    Production daily observation snapshot methodology:
    1) Extract public snapshot observations (strictly ONE_WAY & domestic VALID, latest Playwright run per day, excluding Demo).
    2) Compute daily median fare and daily mean fare for each route on each observation calendar day.
    3) Baseline for a route:
       - For HYD-DEL: Median of usable historical daily market medians (unweighted by flight count: Aug 28, Aug 29, Aug 30, Aug 31, Sep 7).
       - For other routes: Median of available daily market medians (requires >= 2 distinct observation dates).
    4) Index(t) = daily_median / baseline * 100 (Base = 100).
    """
    conn = connect()
    try:
        # Clear out existing index_values so unindexed / legacy routes are not stale
        conn.execute("DELETE FROM index_values")

        df = get_public_snapshot_dataframe(conn)
        if df.empty:
            conn.commit()
            return {"rows_written": 0, "routes": 0}

        daily = (
            df.groupby(["route", "observation_date"], as_index=False)
              .agg(
                  avg_fare=("price_inr", "mean"),
                  median_fare=("price_inr", "median"),
              )
        )

        all_rows_to_insert = []
        now_iso = datetime.now(timezone.utc).isoformat()
        routes_indexed = set()

        for r_name, group in daily.groupby("route"):
            r_clean = str(r_name).upper()
            if r_clean == "HYD-DEL":
                # Historical empirical baseline
                matched_stats = calculate_empirical_matched_pairs_ratio(route="HYD-DEL", observation_date="2026-09-08", conn=conn)
                global_fallback = matched_stats.get("global_fallback_factor") or 1.8960
                airline_factors_map = {}
                for air_k, air_v in (matched_stats.get("airline_factors") or {}).items():
                    if air_v.get("is_eligible"):
                        airline_factors_map[air_k] = air_v.get("effective_factor", global_fallback)

                df_hist_records = pd.read_sql_query("""
                    SELECT id, route, airline, price_inr, travel_date,
                           SUBSTR(search_timestamp, 1, 10) as observation_date
                    FROM raw_prices
                    WHERE route = 'HYD-DEL'
                      AND source != 'DEMO - NOT LIVE'
                      AND (fare_type = 'ROUND_TRIP_LEGACY' OR fare_type = 'UNKNOWN')
                      AND SUBSTR(search_timestamp, 1, 10) < '2026-09-08'
                    ORDER BY observation_date
                """, conn)

                hist_daily_medians = []
                hist_records_list = []
                if not df_hist_records.empty:
                    df_hist_records["norm_fare"] = df_hist_records.apply(
                        lambda r: r["price_inr"] / airline_factors_map.get(r["airline"], global_fallback),
                        axis=1
                    )
                    hist_grouped = df_hist_records.groupby("observation_date").agg(
                        norm_mean=("norm_fare", "mean"),
                        norm_median=("norm_fare", "median")
                    ).reset_index()

                    for h_row in hist_grouped.itertuples(index=False):
                        h_med = round(float(h_row.norm_median), 2)
                        h_avg = round(float(h_row.norm_mean), 2)
                        hist_daily_medians.append(h_med)
                        hist_records_list.append((str(h_row.observation_date), h_avg, h_med))

                # Baseline is median of historical daily medians (each date contributes 1 value)
                baseline_fare = round(float(np.median(hist_daily_medians)), 2) if hist_daily_medians else round(float(group["median_fare"].median()), 2)

                # Add historical index values
                for h_date, h_avg, h_med in hist_records_list:
                    h_idx = round((h_med / baseline_fare) * 100, 2)
                    all_rows_to_insert.append((r_clean, h_date, h_avg, h_med, baseline_fare, h_idx, now_iso))

                # Add verified current index values
                for v_row in group.itertuples(index=False):
                    v_date = str(v_row.observation_date)
                    v_avg = round(float(v_row.avg_fare), 2)
                    v_med = round(float(v_row.median_fare), 2)
                    v_idx = round((v_med / baseline_fare) * 100, 2)
                    all_rows_to_insert.append((r_clean, v_date, v_avg, v_med, baseline_fare, v_idx, now_iso))

                routes_indexed.add(r_clean)

            else:
                # Other routes require >= 2 distinct observation dates
                unique_dates = group["observation_date"].nunique()
                if unique_dates >= 2:
                    baseline_fare = round(float(group["median_fare"].median()), 2)
                    for row in group.itertuples(index=False):
                        v_date = str(row.observation_date)
                        v_avg = round(float(row.avg_fare), 2)
                        v_med = round(float(row.median_fare), 2)
                        v_idx = round((v_med / baseline_fare) * 100, 2)
                        all_rows_to_insert.append((r_clean, v_date, v_avg, v_med, baseline_fare, v_idx, now_iso))
                    routes_indexed.add(r_clean)

        conn.executemany("""
            INSERT INTO index_values
                (route, observation_date, avg_fare, median_fare, baseline_fare, index_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(route, observation_date) DO UPDATE SET
                avg_fare=excluded.avg_fare,
                median_fare=excluded.median_fare,
                baseline_fare=excluded.baseline_fare,
                index_value=excluded.index_value,
                created_at=excluded.created_at
        """, all_rows_to_insert)
        conn.commit()

        return {
            "rows_written": len(all_rows_to_insert),
            "routes": len(routes_indexed),
        }
    finally:
        conn.close()

def get_provenance_summary() -> dict[str, int]:
    """
    Computes accurate data provenance counts across all records in raw_prices.
    """
    conn = connect()
    try:
        rows = conn.execute("SELECT source, fare_type, domestic_eligibility, COUNT(*) as count FROM raw_prices GROUP BY source, fare_type, domestic_eligibility").fetchall()
        counts = {"live": 0, "recovered": 0, "demo": 0, "total": 0, "one_way": 0, "legacy_round_trip": 0, "unknown": 0, "domestic_valid": 0}
        for r in rows:
            src = str(r["source"] or "").lower()
            ft = str(r["fare_type"] or "").upper()
            elig = str(r["domestic_eligibility"] or "").upper()
            cnt = int(r["count"])
            counts["total"] += cnt
            if "demo" in src or "not live" in src:
                counts["demo"] += cnt
            elif "playwright" in src or "amadeus" in src:
                counts["live"] += cnt
            else:
                counts["recovered"] += cnt

            if ft == "ONE_WAY":
                counts["one_way"] += cnt
            elif ft == "ROUND_TRIP_LEGACY":
                counts["legacy_round_trip"] += cnt
            else:
                counts["unknown"] += cnt

            if elig == "VALID":
                counts["domestic_valid"] += cnt

        return counts
    finally:
        conn.close()

def get_national_composite_index() -> dict[str, Any]:
    """
    Computes Tracked-Route Composite Airfare Index from verified ONE_WAY index points.
    Formula:
        Composite Index(t) = SUM(Route Index(t) * Route Weight) / SUM(Weights of Available Routes)
    """
    conn = connect()
    try:
        df = pd.read_sql_query("""
            SELECT route, observation_date, avg_fare, median_fare, baseline_fare, index_value
            FROM index_values
            ORDER BY observation_date, route
        """, conn)

        if df.empty:
            return {
                "index_name": "FareIndex India Tracked-Route Composite (Provisional)",
                "methodology": "Weighted composite of route-level indices (Base = 100)",
                "baseline_description": "Provisional baseline: Base = 100",
                "weighting_policy": "Route weights are calculated from DGCA-reported annual passenger traffic.",
                "weighting_source": "DGCA Domestic City-Pair Annual Passenger Traffic (Combined bidirectional traffic reference)",
                "configured_weights": ROUTE_WEIGHTS,
                "provenance_breakdown": get_provenance_summary(),
                "values": [],
                "latest_value": None,
                "contributing_routes": list(ROUTE_WEIGHTS.keys()),
            }

        # Apply route weights
        df["weight"] = df["route"].map(lambda r: ROUTE_WEIGHTS.get(r, 1.0))

        national_records: list[dict[str, Any]] = []
        for obs_date, group in df.groupby("observation_date"):
            total_weight = float(group["weight"].sum())
            weighted_index_sum = float((group["index_value"] * group["weight"]).sum())
            weighted_fare_sum = float((group["avg_fare"] * group["weight"]).sum())
            weighted_median_sum = float((group["median_fare"] * group["weight"]).sum())

            national_index = round(weighted_index_sum / total_weight, 2) if total_weight > 0 else 100.0
            national_avg_fare = round(weighted_fare_sum / total_weight, 2) if total_weight > 0 else 0.0
            national_med_fare = round(weighted_median_sum / total_weight, 2) if total_weight > 0 else 0.0

            route_contributions = [
                {
                    "route": row["route"],
                    "route_index": float(row["index_value"]),
                    "median_fare": float(row.get("median_fare", row["avg_fare"])),
                    "avg_fare": float(row["avg_fare"]),
                    "weight": float(row["weight"]),
                    "weight_share_pct": round((float(row["weight"]) / total_weight) * 100, 2) if total_weight > 0 else 0.0,
                }
                for _, row in group.iterrows()
            ]

            national_records.append({
                "observation_date": str(obs_date),
                "national_index": national_index,
                "national_median_fare": national_med_fare,
                "national_avg_fare": national_avg_fare,
                "contributing_routes_count": len(group),
                "total_weight": round(total_weight, 2),
                "route_contributions": route_contributions,
            })

        national_records.sort(key=lambda x: x["observation_date"])

        # Calculate change from previous observation
        for i in range(len(national_records)):
            if i > 0:
                prev_val = national_records[i - 1]["national_index"]
                curr_val = national_records[i]["national_index"]
                change = round(curr_val - prev_val, 2)
                change_pct = round(((curr_val - prev_val) / prev_val) * 100, 2) if prev_val > 0 else 0.0
                national_records[i]["index_change_from_previous"] = change
                national_records[i]["index_change_pct"] = change_pct
            else:
                national_records[i]["index_change_from_previous"] = None
                national_records[i]["index_change_pct"] = None

        latest = national_records[-1] if national_records else None

        return {
            "index_name": "FareIndex India Tracked-Route Composite (Provisional)",
            "methodology": "Weighted composite of route-level indices (Base = 100)",
            "status": "PROVISIONAL",
            "weighting_policy": "Route weights are calculated from DGCA-reported annual passenger traffic.",
            "weighting_source": "DGCA Domestic City-Pair Annual Passenger Traffic (Combined bidirectional traffic reference)",
            "configured_weights": ROUTE_WEIGHTS,
            "provenance_breakdown": get_provenance_summary(),
            "values": national_records,
            "latest_value": latest,
        }
    finally:
        conn.close()

def get_route_trend_series(target_route: str, lead_time_bucket: str = "7D") -> dict[str, Any]:
    """
    Returns time-series daily trend observations for a specific route and lead-time horizon (default '7D').
    Enforces minimum data requirement checks (>= 7 consecutive observation dates for benchmark readiness).
    Provides primary typical fare (median), average observed fare (mean), dynamic distribution, and percentiles.
    """
    route_upper = target_route.upper()
    conn = connect()
    try:
        df_bucket = get_public_snapshot_dataframe(conn, target_route=route_upper, target_bucket=lead_time_bucket)
        lead_label = BUCKET_LABELS.get(lead_time_bucket, lead_time_bucket)
        if df_bucket.empty:
            return {
                "route": route_upper,
                "lead_time_bucket": lead_time_bucket,
                "lead_time_label": lead_label,
                "trend_readiness": "BUILDING",
                "is_provisional": True,
                "observation_dates_count": 0,
                "consecutive_observation_dates_count": 0,
                "status_message": "Building baseline — insufficient historical observations (requires at least 7 consecutive observation dates).",
                "current_typical_fare": None,
                "current_average_fare": None,
                "current_avg_fare": None,
                "previous_typical_fare": None,
                "previous_average_fare": None,
                "previous_avg_fare": None,
                "min_fare": None,
                "max_fare": None,
                "p25_fare": None,
                "p75_fare": None,
                "observation_count": 0,
                "fare_change_inr": None,
                "fare_change_pct": None,
                "trend_direction": "AWAITING_HISTORY",
                "fare_position_bands": None,
                "distribution": compute_fare_distribution(pd.Series(dtype=float)),
                "series": [],
            }

        daily_stats = (
            df_bucket.groupby("observation_date")
            .agg(
                avg_fare=("price_inr", "mean"),
                median_fare=("price_inr", "median"),
                min_fare=("price_inr", "min"),
                max_fare=("price_inr", "max"),
                observation_count=("price_inr", "count"),
            )
            .reset_index()
            .sort_values("observation_date")
        )

        series = [
            {
                "observation_date": str(r.observation_date),
                "typical_fare": round(float(r.median_fare), 2),
                "avg_fare": round(float(r.avg_fare), 2),
                "median_fare": round(float(r.median_fare), 2),
                "min_fare": round(float(r.min_fare), 2),
                "max_fare": round(float(r.max_fare), 2),
                "observation_count": int(r.observation_count),
            }
            for r in daily_stats.itertuples(index=False)
        ]

        obs_dates = [s["observation_date"] for s in series]
        obs_count = len(obs_dates)

        # Calculate consecutive observation days count
        consecutive_count = 1 if obs_count > 0 else 0
        if obs_count >= 2:
            dt_series = pd.to_datetime(obs_dates)
            diffs = (dt_series[1:] - dt_series[:-1]).days
            current_streak = 1
            for d in reversed(diffs.tolist()):
                if d == 1:
                    current_streak += 1
                else:
                    break
            consecutive_count = current_streak

        is_provisional = (obs_count < 7)
        trend_readiness = "READY" if not is_provisional else "BUILDING"
        status_message = (
            "Active trend benchmark"
            if not is_provisional
            else "Building baseline — insufficient historical observations (requires at least 7 consecutive observation dates)."
        )

        # Latest observation metrics
        latest_obs_date = series[-1]["observation_date"] if series else None
        latest_prices = (
            df_bucket[df_bucket["observation_date"] == latest_obs_date]["price_inr"]
            if latest_obs_date is not None
            else pd.Series(dtype=float)
        )
        current_typical = series[-1]["typical_fare"] if series else None
        current_average = series[-1]["avg_fare"] if series else None
        min_f = series[-1]["min_fare"] if series else None
        max_f = series[-1]["max_fare"] if series else None
        p10_f = round(float(latest_prices.quantile(0.10)), 2) if not latest_prices.empty else None
        p25_f = round(float(latest_prices.quantile(0.25)), 2) if not latest_prices.empty else None
        p75_f = round(float(latest_prices.quantile(0.75)), 2) if not latest_prices.empty else None
        p90_f = round(float(latest_prices.quantile(0.90)), 2) if not latest_prices.empty else None
        total_obs_count = int(series[-1]["observation_count"]) if series else 0

        prev_avg = series[-2]["avg_fare"] if len(series) >= 2 else None
        prev_typical = series[-2]["typical_fare"] if len(series) >= 2 else None

        if current_typical is not None and prev_typical is not None:
            fare_change_inr = round(current_typical - prev_typical, 2)
            fare_change_pct = round(((current_typical - prev_typical) / prev_typical) * 100, 2) if prev_typical > 0 else 0.0
            if fare_change_pct > 1.5:
                trend_dir = "RISING"
            elif fare_change_pct < -1.5:
                trend_dir = "FALLING"
            else:
                trend_dir = "STABLE"
        else:
            fare_change_inr = None
            fare_change_pct = None
            trend_dir = "AWAITING_HISTORY"

        dist_data = compute_fare_distribution(latest_prices)

        fare_position_bands = None
        if p25_f is not None and p75_f is not None and total_obs_count >= 5:
            fare_position_bands = {
                "low_max": p25_f,
                "normal_min": p25_f,
                "normal_max": p75_f,
                "high_min": p75_f,
                "median": current_typical,
            }

        return {
            "route": route_upper,
            "lead_time_bucket": lead_time_bucket,
            "lead_time_label": lead_label,
            "trend_readiness": trend_readiness,
            "is_provisional": is_provisional,
            "observation_dates_count": obs_count,
            "consecutive_observation_dates_count": consecutive_count,
            "status_message": status_message,
            "primary_market_metric": "median",
            "current_typical_fare": current_typical,
            "current_average_fare": current_average,
            "current_avg_fare": current_average,  # Backward compatibility
            "daily_median_fare": current_typical,
            "daily_mean_fare": current_average,
            "previous_typical_fare": prev_typical,
            "previous_average_fare": prev_avg,
            "previous_avg_fare": prev_avg,        # Backward compatibility
            "min_fare": min_f,
            "max_fare": max_f,
            "p10_fare": p10_f,
            "p25_fare": p25_f,
            "p75_fare": p75_f,
            "p90_fare": p90_f,
            "observation_count": total_obs_count,
            "fare_change_inr": fare_change_inr,
            "fare_change_pct": fare_change_pct,
            "trend_direction": trend_dir,
            "fare_position_bands": fare_position_bands,
            "distribution": dist_data,
            "series": series,
        }
    finally:
        conn.close()

def get_routes_summary(target_route: str | None = None) -> list[dict[str, Any]]:
    """
    Produces summary analytics for each route (or a specific target route) from ONE_WAY snapshot data:
    - Primary 7D near-term trend & metrics
    - Latest index & baseline
    - Previous available index & DoD change
    - Latest, baseline, minimum & maximum fares
    - Total observation count and date range
    - Tracked airlines & lead-time breakdowns
    """
    conn = connect()
    try:
        if target_route:
            routes_query = "SELECT DISTINCT route FROM raw_prices WHERE UPPER(route) = ? ORDER BY route"
            routes = [r[0] for r in conn.execute(routes_query, (target_route.upper(),)).fetchall()]
        else:
            routes = [r[0] for r in conn.execute("SELECT DISTINCT route FROM raw_prices ORDER BY route").fetchall()]

        summaries: list[dict[str, Any]] = []

        for route in routes:
            # 1. Index history for the route
            idx_rows = conn.execute("""
                SELECT observation_date, avg_fare, median_fare, baseline_fare, index_value
                FROM index_values
                WHERE route = ?
                ORDER BY observation_date ASC
            """, (route,)).fetchall()

            # 2. Public snapshot stats for this route (strictly ONE_WAY & domestic VALID)
            route_snap = get_public_snapshot_dataframe(conn, target_route=route)

            if not route_snap.empty:
                obs_count = len(route_snap)
                min_fare = float(route_snap["price_inr"].min())
                max_fare = float(route_snap["price_inr"].max())
                first_obs_date = str(route_snap["observation_date"].min())
                latest_obs_date = str(route_snap["observation_date"].max())
                latest_search_ts = str(route_snap["search_timestamp"].max())
                airlines = sorted([a for a in route_snap["airline"].dropna().unique() if a])

                latest_rows = route_snap[route_snap["observation_date"] == latest_obs_date]
                latest_min = float(latest_rows["price_inr"].min()) if not latest_rows.empty else None
                latest_max = float(latest_rows["price_inr"].max()) if not latest_rows.empty else None
                latest_snap_avg = float(latest_rows["price_inr"].mean()) if not latest_rows.empty else None
                latest_snap_med = float(latest_rows["price_inr"].median()) if not latest_rows.empty else None

                # Bucket breakdown
                bucket_breakdown: dict[str, Any] = {}
                for b_name, b_group in route_snap.groupby("lead_time_bucket"):
                    bucket_breakdown[str(b_name)] = {
                        "count": len(b_group),
                        "avg_fare": round(float(b_group["price_inr"].mean()), 2),
                        "median_fare": round(float(b_group["price_inr"].median()), 2),
                        "min_fare": round(float(b_group["price_inr"].min()), 2),
                        "max_fare": round(float(b_group["price_inr"].max()), 2),
                    }
            else:
                obs_count = 0
                min_fare = None
                max_fare = None
                first_obs_date = None
                latest_obs_date = None
                latest_search_ts = None
                airlines = []
                latest_min = None
                latest_max = None
                latest_snap_avg = None
                latest_snap_med = None
                bucket_breakdown = {}

            if idx_rows:
                latest_idx_row = idx_rows[-1]
                latest_index = float(latest_idx_row["index_value"])
                latest_avg_fare = float(latest_idx_row["avg_fare"])
                latest_med_fare = float(latest_idx_row["median_fare"]) if "median_fare" in latest_idx_row.keys() and latest_idx_row["median_fare"] else latest_snap_med
                baseline_fare = float(latest_idx_row["baseline_fare"])
                latest_date = latest_idx_row["observation_date"]

                if len(idx_rows) >= 2:
                    prev_idx_row = idx_rows[-2]
                    prev_index = float(prev_idx_row["index_value"])
                    prev_date = prev_idx_row["observation_date"]
                    index_change = round(latest_index - prev_index, 2)
                    index_change_pct = round(((latest_index - prev_index) / prev_index) * 100, 2)
                    change_description = f"Change from previous observation ({prev_date} to {latest_date})"
                else:
                    prev_index = None
                    prev_date = None
                    index_change = None
                    index_change_pct = None
                    change_description = "Single observation date available; baseline established"
            else:
                latest_index = None
                latest_avg_fare = latest_snap_avg
                latest_med_fare = latest_snap_med
                baseline_fare = None
                prev_index = None
                prev_date = None
                index_change = None
                index_change_pct = None
                change_description = "Awaiting baseline establishment (requires >= 2 distinct observation dates)" if obs_count > 0 else "No verified one-way observations yet"

            # Primary 7D trend analysis
            trend_7d = get_route_trend_series(route, lead_time_bucket="7D")

            summaries.append({
                "route": route,
                "latest_index": latest_index,
                "previous_index": prev_index,
                "index_change": index_change,
                "index_change_pct": index_change_pct,
                "change_description": change_description,
                "primary_market_metric": "median",
                "latest_median_fare": latest_med_fare,
                "latest_avg_fare": latest_avg_fare,
                "daily_median_fare": latest_med_fare,
                "daily_mean_fare": latest_avg_fare,
                "near_term_median": trend_7d["current_typical_fare"],
                "near_term_mean": trend_7d["current_average_fare"],
                "current_typical_fare": trend_7d["current_typical_fare"],
                "current_average_fare": trend_7d["current_average_fare"],
                "current_avg_fare": trend_7d["current_average_fare"],
                "baseline_fare": baseline_fare,
                "baseline_market_fare": baseline_fare,
                "all_time_min_fare": min_fare,
                "all_time_max_fare": max_fare,
                "latest_min_fare": latest_min,
                "latest_max_fare": latest_max,
                "observation_count": obs_count,
                "observation_days_count": len(idx_rows) if idx_rows else (1 if obs_count > 0 else 0),
                "first_observation_date": first_obs_date,
                "latest_observation_date": latest_obs_date,
                "latest_search_timestamp": latest_search_ts,
                "airlines": airlines,
                "trend_readiness": trend_7d["trend_readiness"],
                "is_provisional": trend_7d["is_provisional"],
                "status_message": trend_7d["status_message"],
                "primary_lead_time_bucket": "7D",
                "lead_time_7d_typical_fare": trend_7d["current_typical_fare"],
                "lead_time_7d_average_fare": trend_7d["current_average_fare"],
                "lead_time_7d_current_avg": trend_7d["current_avg_fare"],
                "lead_time_7d_previous_avg": trend_7d["previous_avg_fare"],
                "lead_time_7d_change_inr": trend_7d["fare_change_inr"],
                "lead_time_7d_change_pct": trend_7d["fare_change_pct"],
                "lead_time_7d_trend": trend_7d["trend_direction"],
                "bucket_breakdown": bucket_breakdown,
            })

        return summaries
    finally:
        conn.close()

def get_collection_health_summary() -> list[dict[str, Any]]:
    """
    Returns collection health status and data readiness across tracked routes.
    """
    conn = connect()
    try:
        health_reports: list[dict[str, Any]] = []
        for route in TRACKED_ROUTES:
            df_route = get_public_snapshot_dataframe(conn, target_route=route)
            if df_route.empty:
                health_reports.append({
                    "route": route,
                    "latest_observation_date": None,
                    "observation_dates_count": 0,
                    "consecutive_observation_dates_count": 0,
                    "trend_readiness": "BUILDING",
                    "is_provisional": True,
                    "lead_time_counts": {"7D": 0, "14D": 0, "21D": 0, "30D": 0, "60D": 0},
                    "last_successful_collection_timestamp": None,
                })
                continue

            unique_dates = sorted(list(df_route["observation_date"].unique()))
            obs_dates_count = len(unique_dates)

            # Consecutive dates
            consecutive_count = 1 if obs_dates_count > 0 else 0
            if obs_dates_count >= 2:
                dt_series = pd.to_datetime(unique_dates)
                diffs = (dt_series[1:] - dt_series[:-1]).days
                current_streak = 1
                for d in reversed(diffs.tolist()):
                    if d == 1:
                        current_streak += 1
                    else:
                        break
                consecutive_count = current_streak

            bucket_counts = {
                "7D": int((df_route["lead_time_bucket"] == "7D").sum()),
                "14D": int((df_route["lead_time_bucket"] == "14D").sum()),
                "21D": int((df_route["lead_time_bucket"] == "21D").sum()),
                "30D": int((df_route["lead_time_bucket"] == "30D").sum()),
                "60D": int((df_route["lead_time_bucket"] == "60D").sum()),
            }

            health_reports.append({
                "route": route,
                "latest_observation_date": unique_dates[-1] if unique_dates else None,
                "observation_dates_count": obs_dates_count,
                "consecutive_observation_dates_count": consecutive_count,
                "trend_readiness": "READY" if obs_dates_count >= 7 else "BUILDING",
                "is_provisional": obs_dates_count < 7,
                "lead_time_counts": bucket_counts,
                "last_successful_collection_timestamp": str(df_route["search_timestamp"].max()) if not df_route.empty else None,
            })

        return health_reports
    finally:
        conn.close()

def get_booking_curve_by_buckets(target_route: str | None = None) -> dict[str, Any]:
    """
    Computes standardized booking lead-time curve across fixed buckets:
    7D, 14D, 21D, 30D, 60D.
    """
    conn = connect()
    try:
        df = get_public_snapshot_dataframe(conn, target_route=target_route)
        if df.empty:
            return {
                "route": target_route or "ALL",
                "total_observations": 0,
                "series": [],
            }

        buckets = ["7D", "14D", "21D", "30D", "60D"]
        series = []
        for b in buckets:
            df_b = df[df["lead_time_bucket"] == b]
            if not df_b.empty:
                prices = df_b["price_inr"]
                series.append({
                    "bucket": b,
                    "lead_time_label": BUCKET_LABELS.get(b, b),
                    "lead_time_days": BUCKET_NOMINAL_DAYS.get(b, 0),
                    "typical_fare": round(float(prices.median()), 2),
                    "median_fare": round(float(prices.median()), 2),
                    "average_fare": round(float(prices.mean()), 2),
                    "avg_fare": round(float(prices.mean()), 2),
                    "min_fare": round(float(prices.min()), 2),
                    "max_fare": round(float(prices.max()), 2),
                    "p25_fare": round(float(prices.quantile(0.25)), 2),
                    "p75_fare": round(float(prices.quantile(0.75)), 2),
                    "observation_count": len(prices),
                    "airlines": sorted(list(df_b["airline"].dropna().unique())),
                })

        return {
            "route": target_route or "ALL",
            "total_observations": len(df),
            "series": series,
        }
    finally:
        conn.close()

def get_booking_curve_analytics(target_route: str | None = None) -> dict[str, Any]:
    """
    Computes Booking Curve Analytics from verified ONE_WAY public snapshot observations:
    lead_time_days = travel_date - search_timestamp (date)
    Includes both daily curve and bucket summary series.
    """
    conn = connect()
    try:
        df = get_public_snapshot_dataframe(conn, target_route=target_route)
        if df.empty:
            return {
                "route": target_route or "ALL",
                "total_observations": 0,
                "usable_observations": 0,
                "missing_travel_date_count": 0,
                "data_quality_note": "No verified one-way observations found.",
                "curve": [],
                "series": [],
            }

        total_obs = len(df)
        usable_df = df[df["lead_time_days"].notna() & (df["lead_time_days"] >= 0)].copy()
        missing_count = total_obs - len(usable_df)

        if usable_df.empty:
            return {
                "route": target_route or "ALL",
                "total_observations": total_obs,
                "usable_observations": 0,
                "missing_travel_date_count": missing_count,
                "data_quality_note": "Observations lack explicit travel_date stored.",
                "curve": [],
                "series": [],
            }

        curve_rows = (
            usable_df.groupby("lead_time_days")
            .agg(
                avg_fare=("price_inr", "mean"),
                min_fare=("price_inr", "min"),
                max_fare=("price_inr", "max"),
                observation_count=("price_inr", "count"),
                lead_time_bucket=("lead_time_bucket", "first"),
                airlines=("airline", lambda x: list(x.dropna().unique())),
            )
            .reset_index()
            .sort_values("lead_time_days")
        )

        curve_rows["avg_fare"] = curve_rows["avg_fare"].round(2)
        curve_rows["min_fare"] = curve_rows["min_fare"].round(2)
        curve_rows["max_fare"] = curve_rows["max_fare"].round(2)

        curve = [
            {
                "lead_time_days": int(r.lead_time_days),
                "window_label": f"{r.lead_time_days} days out ({r.lead_time_bucket})",
                "lead_time_bucket": str(r.lead_time_bucket),
                "avg_fare": float(r.avg_fare),
                "min_fare": float(r.min_fare),
                "max_fare": float(r.max_fare),
                "observation_count": int(r.observation_count),
                "airlines": list(r.airlines),
            }
            for r in curve_rows.itertuples(index=False)
        ]

        bucket_summary = get_booking_curve_by_buckets(target_route=target_route)

        return {
            "route": target_route or "ALL",
            "total_observations": total_obs,
            "usable_observations": len(usable_df),
            "missing_travel_date_count": missing_count,
            "data_quality_note": (
                f"{len(usable_df)} of {total_obs} one-way observations have valid lead-time data."
                if missing_count > 0
                else "100% of one-way observations have valid lead-time data."
            ),
            "curve": curve,
            "series": bucket_summary.get("series", []),
        }
    finally:
        conn.close()

def get_airline_analytics(target_route: str | None = None) -> dict[str, Any]:
    """
    Computes Airline Price Breakdown and Dispersion Analytics from verified ONE_WAY public snapshot.
    """
    conn = connect()
    try:
        df = get_public_snapshot_dataframe(conn, target_route=target_route)
        if df.empty:
            return {
                "route": target_route or "ALL",
                "total_observations": 0,
                "airlines": [],
            }

        df_valid = df[df["airline"].notna()].copy()
        total_obs = len(df_valid)

        if total_obs == 0:
            return {
                "route": target_route or "ALL",
                "total_observations": 0,
                "airlines": [],
            }

        airline_stats = (
            df_valid.groupby("airline")
            .agg(
                avg_fare=("price_inr", "mean"),
                min_fare=("price_inr", "min"),
                max_fare=("price_inr", "max"),
                observation_count=("price_inr", "count"),
            )
            .reset_index()
        )

        airline_stats["avg_fare"] = airline_stats["avg_fare"].round(2)
        airline_stats["min_fare"] = airline_stats["min_fare"].round(2)
        airline_stats["max_fare"] = airline_stats["max_fare"].round(2)
        airline_stats["spread"] = (airline_stats["max_fare"] - airline_stats["min_fare"]).round(2)
        airline_stats["market_share_pct"] = (
            (airline_stats["observation_count"] / total_obs) * 100
        ).round(2)

        airline_stats = airline_stats.sort_values("avg_fare", ascending=True)

        airlines_list = [
            {
                "airline": str(r.airline),
                "avg_fare": float(r.avg_fare),
                "min_fare": float(r.min_fare),
                "max_fare": float(r.max_fare),
                "spread": float(r.spread),
                "observation_count": int(r.observation_count),
                "market_share_pct": float(r.market_share_pct),
            }
            for r in airline_stats.itertuples(index=False)
        ]

        lowest_carrier = airlines_list[0]["airline"] if airlines_list else None
        highest_carrier = airlines_list[-1]["airline"] if airlines_list else None

        return {
            "route": target_route or "ALL",
            "total_observations": total_obs,
            "lowest_avg_carrier": lowest_carrier,
            "highest_avg_carrier": highest_carrier,
            "airlines": airlines_list,
        }
    finally:
        conn.close()


def calculate_empirical_matched_pairs_ratio(
    route: str = "HYD-DEL",
    observation_date: str = "2026-09-08",
    conn: Any = None
) -> dict[str, Any]:
    """
    Finds matching flight itineraries between legacy round-trip observations and verified one-way observations
    on overlapping observation dates (2026-09-08) for HYD-DEL.
    Returns matched pairs statistics, unique itinerary statistics, airline-specific empirical factors,
    and robustness metrics.
    """
    close_conn = False
    if conn is None:
        conn = connect()
        close_conn = True
    try:
        route_clean = route.upper()
        df_legacy = pd.read_sql_query("""
            SELECT route, airline, price_inr, travel_date, departure_time, arrival_time
            FROM raw_prices
            WHERE route = ? AND fare_type = 'ROUND_TRIP_LEGACY' AND SUBSTR(search_timestamp, 1, 10) = ?
        """, conn, params=(route_clean, observation_date))

        df_oneway = pd.read_sql_query("""
            SELECT route, airline, price_inr, travel_date, departure_time, arrival_time
            FROM raw_prices
            WHERE route = ? AND fare_type = 'ONE_WAY' AND domestic_eligibility = 'VALID' AND SUBSTR(search_timestamp, 1, 10) = ?
        """, conn, params=(route_clean, observation_date))

        def trim_mean(arr: np.ndarray, p: float) -> float:
            a = np.sort(arr)
            n = len(a)
            low = int(n * p)
            high = n - low
            if low >= high or low == 0:
                return float(np.mean(a))
            return float(np.mean(a[low:high]))

        def stats_dict(arr: np.ndarray) -> dict[str, Any]:
            n = len(arr)
            if n == 0:
                return {
                    "N": 0, "mean": None, "median": None, "trim5": None, "trim10": None,
                    "p25": None, "p75": None, "min": None, "max": None, "std": None, "cv_pct": None,
                }
            mean_v = float(np.mean(arr))
            std_v = float(np.std(arr, ddof=1)) if n > 1 else 0.0
            cv_v = (std_v / mean_v) * 100 if mean_v > 0 else 0.0
            return {
                "N": n,
                "mean": round(mean_v, 4),
                "median": round(float(np.median(arr)), 4),
                "trim5": round(trim_mean(arr, 0.05), 4),
                "trim10": round(trim_mean(arr, 0.10), 4),
                "p25": round(float(np.percentile(arr, 25)), 4),
                "p75": round(float(np.percentile(arr, 75)), 4),
                "min": round(float(np.min(arr)), 4),
                "max": round(float(np.max(arr)), 4),
                "std": round(std_v, 4),
                "cv_pct": round(cv_v, 2),
            }

        if df_legacy.empty or df_oneway.empty:
            empty_s = stats_dict(np.array([]))
            return {
                "route": route_clean,
                "observation_date": observation_date,
                "n_matched_pairs": 0,
                "matched_pairs_count": 0,
                "unique_itineraries_count": 0,
                "mean_ratio": None,
                "median_ratio": None,
                "trim5_ratio": None,
                "trim10_ratio": None,
                "std_ratio": None,
                "cv_pct": None,
                "p25_ratio": None,
                "p75_ratio": None,
                "min_ratio": None,
                "max_ratio": None,
                "distance_from_2_0": None,
                "distance_from_2_1": None,
                "closer_hypothesis": None,
                "closest_round_factor": None,
                "airline_factors": {},
                "global_fallback_factor": 1.8960,
            }

        df_matched = pd.merge(
            df_legacy, df_oneway,
            on=["route", "travel_date", "airline", "departure_time"],
            suffixes=("_legacy", "_oneway")
        )

        if df_matched.empty:
            df_matched = pd.merge(
                df_legacy.groupby(["route", "travel_date", "airline"])["price_inr"].mean().reset_index(),
                df_oneway.groupby(["route", "travel_date", "airline"])["price_inr"].mean().reset_index(),
                on=["route", "travel_date", "airline"],
                suffixes=("_legacy", "_oneway")
            )

        if df_matched.empty:
            return {
                "route": route_clean,
                "observation_date": observation_date,
                "n_matched_pairs": 0,
                "matched_pairs_count": 0,
                "unique_itineraries_count": 0,
                "mean_ratio": None,
                "median_ratio": None,
                "trim5_ratio": None,
                "trim10_ratio": None,
                "std_ratio": None,
                "cv_pct": None,
                "p25_ratio": None,
                "p75_ratio": None,
                "min_ratio": None,
                "max_ratio": None,
                "distance_from_2_0": None,
                "distance_from_2_1": None,
                "closer_hypothesis": None,
                "closest_round_factor": None,
                "airline_factors": {},
                "global_fallback_factor": 1.8960,
            }

        df_matched["ratio"] = df_matched["price_inr_legacy"] / df_matched["price_inr_oneway"]
        df_unique = df_matched.groupby(["route", "travel_date", "airline", "departure_time"])["ratio"].mean().reset_index()

        all_pairs_stats = stats_dict(df_matched["ratio"].values)
        unique_stats = stats_dict(df_unique["ratio"].values)

        med = unique_stats["median"]
        dist_20 = round(abs(med - 2.0), 4)
        dist_21 = round(abs(med - 2.1), 4)
        closer = "2.0" if dist_20 < dist_21 else "2.1"

        airline_stats = {}
        for air, group in df_unique.groupby("airline"):
            s = stats_dict(group["ratio"].values)
            pair_count = len(df_matched[df_matched["airline"] == air])
            is_eligible = bool(s["N"] >= 10 and s["cv_pct"] <= 15.0 and (s["p75"] - s["p25"] <= 0.35))
            s["N_pairs"] = pair_count
            s["is_eligible"] = is_eligible
            s["effective_factor"] = s["trim10"] if is_eligible else unique_stats["trim10"]
            airline_stats[air] = s

        return {
            "route": route_clean,
            "observation_date": observation_date,
            "n_matched_pairs": all_pairs_stats["N"],
            "matched_pairs_count": all_pairs_stats["N"],
            "unique_itineraries_count": unique_stats["N"],
            "mean_ratio": unique_stats["mean"],
            "median_ratio": unique_stats["median"],
            "trim5_ratio": unique_stats["trim5"],
            "trim10_ratio": unique_stats["trim10"],
            "std_ratio": unique_stats["std"],
            "cv_pct": unique_stats["cv_pct"],
            "p25_ratio": unique_stats["p25"],
            "p75_ratio": unique_stats["p75"],
            "min_ratio": unique_stats["min"],
            "max_ratio": unique_stats["max"],
            "distance_from_2_0": dist_20,
            "distance_from_2_1": dist_21,
            "closer_hypothesis": closer,
            "closest_round_factor": closer,
            "all_pairs_stats": all_pairs_stats,
            "unique_stats": unique_stats,
            "airline_factors": airline_stats,
            "global_fallback_factor": unique_stats["trim10"],
        }
    finally:
        if close_conn:
            conn.close()


def get_route_movement_series(target_route: str = "HYD-DEL") -> dict[str, Any]:
    """
    Constructs a transparent calendar market movement series bridging genuine historical reference
    observations onto the verified current one-way scale for HYD-DEL using empirical normalization factors.
    Uses daily MEDIAN as the primary market metric.
    For routes with single observation date (HYD-GOI), returns building status.
    Preserves date gaps without synthetic dates or interpolation.
    """
    route_upper = target_route.upper()
    conn = connect()
    try:
        df_snap = get_public_snapshot_dataframe(conn, target_route=route_upper)
        
        if df_snap.empty or route_upper != "HYD-DEL":
            series = []
            if not df_snap.empty:
                dates = sorted(df_snap["observation_date"].unique().tolist())
                for d in dates:
                    sub = df_snap[df_snap["observation_date"] == d]
                    current_med = round(float(sub["price_inr"].median()), 2)
                    current_mean = round(float(sub["price_inr"].mean()), 2)
                    sub_7d = sub[sub["lead_time_bucket"] == "7D"]
                    current_7d_med = round(float(sub_7d["price_inr"].median()), 2) if not sub_7d.empty else current_med
                    current_7d_mean = round(float(sub_7d["price_inr"].mean()), 2) if not sub_7d.empty else current_mean
                    series.append({
                        "observation_date": str(d),
                        "fare": current_med,
                        "typical_fare": current_7d_med,
                        "daily_median_fare": current_med,
                        "daily_mean_fare": current_mean,
                        "near_term_median": current_7d_med,
                        "near_term_mean": current_7d_mean,
                        "raw_fare": current_med,
                        "raw_legacy_fare": None,
                        "source_class": "verified_current",
                        "observation_count": len(sub),
                        "change_inr": None,
                        "change_pct": None,
                        "dod_change": None,
                        "dod_change_pct": None,
                    })

                for i in range(1, len(series)):
                    prev_f = series[i-1]["fare"]
                    curr_f = series[i]["fare"]
                    chg = round(curr_f - prev_f, 2)
                    pct = round(((curr_f - prev_f) / prev_f) * 100, 2) if prev_f > 0 else 0.0
                    series[i]["change_inr"] = chg
                    series[i]["change_pct"] = pct
                    series[i]["dod_change"] = chg
                    series[i]["dod_change_pct"] = pct

            latest_chg = series[-1]["change_inr"] if series else None
            latest_pct = series[-1]["change_pct"] if series else None
            if latest_pct is not None:
                if latest_pct > 1.5:
                    trend_dir = "RISING"
                elif latest_pct < -1.5:
                    trend_dir = "FALLING"
                else:
                    trend_dir = "STABLE"
            else:
                trend_dir = "AWAITING_HISTORY"

            is_verified_to_verified = len(series) >= 2
            movement_label = "Verified day-over-day movement" if is_verified_to_verified else "Calendar movement is building"
            movement_type = "VERIFIED_DAY_OVER_DAY" if is_verified_to_verified else "BUILDING_BASELINE"

            latest_point = {
                "observation_date": series[-1]["observation_date"],
                "fare": series[-1]["fare"],
                "daily_median_fare": series[-1]["daily_median_fare"],
                "daily_mean_fare": series[-1]["daily_mean_fare"],
                "near_term_median": series[-1]["near_term_median"],
                "near_term_mean": series[-1]["near_term_mean"],
                "source_class": series[-1]["source_class"],
                "observation_count": series[-1]["observation_count"],
                "change_inr": latest_chg,
                "change_pct": latest_pct,
                "direction": trend_dir,
                "movement_type": movement_type,
                "movement_label": movement_label,
            } if series else None

            return {
                "route": route_upper,
                "metric": "market_reference_fare",
                "primary_market_metric": "median",
                "primary_market_fare": latest_point["fare"] if latest_point else None,
                "primary_market_population": "all-horizon canonical snapshot",
                "daily_median_fare": latest_point["daily_median_fare"] if latest_point else None,
                "daily_mean_fare": latest_point["daily_mean_fare"] if latest_point else None,
                "near_term_median": series[-1]["near_term_median"] if series else None,
                "near_term_mean": series[-1]["near_term_mean"] if series else None,
                "status": "VERIFIED_DAY_OVER_DAY" if is_verified_to_verified else "BUILDING_BASELINE",
                "display_status": "VERIFIED DAY-OVER-DAY" if is_verified_to_verified else "BUILDING_BASELINE",
                "trend_readiness": "READY" if len(series) >= 7 else ("VERIFIED_DAY_OVER_DAY" if is_verified_to_verified else "BUILDING_BASELINE"),
                "status_label": movement_label,
                "movement_label": movement_label,
                "status_message": "Verified day-over-day market movement." if is_verified_to_verified else "Calendar movement is building — insufficient historical observations.",
                "bridge_factor": None,
                "bridge_factor_median": None,
                "robustness_median_factor": None,
                "bridge_method": None,
                "bridge_methodology": None,
                "empirical_matched_ratio": None,
                "matched_pairs_count": 0,
                "current_typical_fare": series[-1]["typical_fare"] if series else None,
                "current_average_fare": series[-1]["daily_mean_fare"] if series else None,
                "latest_change_inr": latest_chg,
                "latest_change_pct": latest_pct,
                "trend_direction": trend_dir,
                "consecutive_verified_dates": len(series),
                "latest_point": latest_point,
                "series": series,
            }

        # 1. Compute empirical matched pairs & airline-specific factors
        matched_stats = calculate_empirical_matched_pairs_ratio(route="HYD-DEL", observation_date="2026-09-08", conn=conn)
        global_fallback = matched_stats.get("global_fallback_factor") or 1.8960
        airline_factors_map = {}
        for air_k, air_v in (matched_stats.get("airline_factors") or {}).items():
            if air_v.get("is_eligible"):
                airline_factors_map[air_k] = air_v.get("effective_factor", global_fallback)

        # 2. Historical flight records normalization (Aug 28, Aug 29, Aug 30, Aug 31, Sep 7)
        df_hist_records = pd.read_sql_query("""
            SELECT 
                id, route, airline, price_inr, travel_date,
                SUBSTR(search_timestamp, 1, 10) as observation_date
            FROM raw_prices
            WHERE route = 'HYD-DEL'
              AND source != 'DEMO - NOT LIVE'
              AND (fare_type = 'ROUND_TRIP_LEGACY' OR fare_type = 'UNKNOWN')
              AND SUBSTR(search_timestamp, 1, 10) < '2026-09-08'
            ORDER BY observation_date
        """, conn)

        series = []
        hist_daily_medians = []
        if not df_hist_records.empty:
            df_hist_records["norm_fare"] = df_hist_records.apply(
                lambda r: r["price_inr"] / airline_factors_map.get(r["airline"], global_fallback),
                axis=1
            )
            daily_grouped = df_hist_records.groupby("observation_date").agg(
                norm_mean=("norm_fare", "mean"),
                norm_median=("norm_fare", "median"),
                raw_mean=("price_inr", "mean"),
                count=("price_inr", "count")
            ).reset_index()

            for r in daily_grouped.itertuples(index=False):
                normalized_med = round(float(r.norm_median), 2)
                normalized_mean = round(float(r.norm_mean), 2)
                raw_val = round(float(r.raw_mean), 2)
                hist_daily_medians.append(normalized_med)
                series.append({
                    "observation_date": str(r.observation_date),
                    "fare": normalized_med,
                    "typical_fare": normalized_med,
                    "daily_median_fare": normalized_med,
                    "daily_mean_fare": normalized_mean,
                    "near_term_median": normalized_med,
                    "near_term_mean": normalized_mean,
                    "raw_fare": raw_val,
                    "raw_legacy_fare": raw_val,
                    "source_class": "historical_reference",
                    "observation_count": int(r.count),
                })

        baseline_market_fare = round(float(np.median(hist_daily_medians)), 2) if hist_daily_medians else 7959.18

        # 3. Add verified observation dates (dynamically supports 2026-09-08 and future dates from df_snap)
        df_verified = df_snap[df_snap["observation_date"] >= "2026-09-08"]
        verified_dates_list = sorted(df_verified["observation_date"].unique().tolist()) if not df_verified.empty else ["2026-09-08"]
        consecutive_verified_count = len(verified_dates_list)

        for v_date in verified_dates_list:
            df_v = df_verified[df_verified["observation_date"] == v_date] if not df_verified.empty else df_snap
            if df_v.empty:
                continue
            v_mean = float(df_v["price_inr"].mean())
            v_med = float(df_v["price_inr"].median())
            df_v_7d = df_v[df_v["lead_time_bucket"] == "7D"]
            v_7d_typical = round(float(df_v_7d["price_inr"].median()), 2) if not df_v_7d.empty else round(v_med, 2)
            v_7d_average = round(float(df_v_7d["price_inr"].mean()), 2) if not df_v_7d.empty else round(v_mean, 2)

            series.append({
                "observation_date": v_date,
                "fare": round(v_med, 2),
                "typical_fare": v_7d_typical,
                "daily_median_fare": round(v_med, 2),
                "daily_mean_fare": round(v_mean, 2),
                "near_term_median": v_7d_typical,
                "near_term_mean": v_7d_average,
                "raw_fare": round(v_med, 2),
                "raw_legacy_fare": None,
                "source_class": "verified_current",
                "observation_count": len(df_v),
            })

        # Compute period-over-period DoD changes
        for i in range(len(series)):
            if i == 0:
                series[i]["change_inr"] = None
                series[i]["change_pct"] = None
                series[i]["dod_change"] = None
                series[i]["dod_change_pct"] = None
            else:
                prev_fare = series[i-1]["fare"]
                curr_fare = series[i]["fare"]
                chg = round(curr_fare - prev_fare, 2)
                pct = round(((curr_fare - prev_fare) / prev_fare) * 100, 2) if prev_fare > 0 else 0.0
                series[i]["change_inr"] = chg
                series[i]["change_pct"] = pct
                series[i]["dod_change"] = chg
                series[i]["dod_change_pct"] = pct

        latest_change = series[-1]["change_inr"]
        latest_pct = series[-1]["change_pct"]

        if latest_pct is not None:
            if latest_pct > 1.5:
                trend_dir = "RISING"
            elif latest_pct < -1.5:
                trend_dir = "FALLING"
            else:
                trend_dir = "STABLE"
        else:
            trend_dir = "AWAITING_HISTORY"

        # Check if latest movement is verified-to-verified
        is_verified_to_verified = (
            len(series) >= 2
            and series[-1]["source_class"] == "verified_current"
            and series[-2]["source_class"] == "verified_current"
        )
        movement_label = "Verified day-over-day movement" if is_verified_to_verified else "Provisional market movement"
        movement_type = "VERIFIED_DAY_OVER_DAY" if is_verified_to_verified else "PROVISIONAL_SPLICE"

        # Trend readiness
        if consecutive_verified_count >= 7:
            trend_readiness = "READY"
            display_status = "OFFICIAL 7-DAY BENCHMARK"
            status_label = "Official market trend"
        else:
            trend_readiness = "PROVISIONAL_HISTORICAL_REFERENCE"
            display_status = "PROVISIONAL HISTORICAL REFERENCE"
            status_label = movement_label

        latest_point = {
            "observation_date": series[-1]["observation_date"],
            "fare": series[-1]["fare"],
            "daily_median_fare": series[-1]["daily_median_fare"],
            "daily_mean_fare": series[-1]["daily_mean_fare"],
            "near_term_median": series[-1]["near_term_median"],
            "near_term_mean": series[-1]["near_term_mean"],
            "source_class": series[-1]["source_class"],
            "observation_count": series[-1]["observation_count"],
            "change_inr": latest_change,
            "change_pct": latest_pct,
            "direction": trend_dir,
            "movement_type": movement_type,
            "movement_label": movement_label,
        }

        # Latest 7D snapshot metrics for the latest observation date
        latest_obs_d = series[-1]["observation_date"] if series else None
        df_latest_snap = get_public_snapshot_dataframe(conn, target_route=route_upper)
        df_latest_snap_for_d = df_latest_snap[df_latest_snap["observation_date"] == latest_obs_d] if latest_obs_d else df_latest_snap
        df_latest_7d = df_latest_snap_for_d[df_latest_snap_for_d["lead_time_bucket"] == "7D"] if not df_latest_snap_for_d.empty else pd.DataFrame()
        latest_7d_typical = round(float(df_latest_7d["price_inr"].median()), 2) if not df_latest_7d.empty else (series[-1]["near_term_median"] if series else None)
        latest_7d_average = round(float(df_latest_7d["price_inr"].mean()), 2) if not df_latest_7d.empty else (series[-1]["near_term_mean"] if series else None)

        return {
            "route": route_upper,
            "metric": "market_reference_fare",
            "primary_market_metric": "median",
            "primary_market_fare": latest_point["fare"] if latest_point else None,
            "primary_market_population": "all-horizon canonical snapshot",
            "daily_median_fare": latest_point["daily_median_fare"] if latest_point else None,
            "daily_mean_fare": latest_point["daily_mean_fare"] if latest_point else None,
            "near_term_median": latest_7d_typical,
            "near_term_mean": latest_7d_average,
            "baseline_market_fare": baseline_market_fare,
            "status": "PROVISIONAL_SPLICE" if not is_verified_to_verified else "VERIFIED_DAY_OVER_DAY",
            "display_status": display_status,
            "trend_readiness": trend_readiness,
            "status_label": status_label,
            "movement_label": movement_label,
            "status_message": "Bridged historical market reference connected to today's verified domestic one-way observations.",
            "bridge_factor": global_fallback,
            "bridge_factor_median": matched_stats.get("median_ratio"),
            "robustness_median_factor": matched_stats.get("median_ratio"),
            "bridge_method": "airline_specific_empirical_ratio",
            "bridge_methodology": "airline_empirical_matched_pairs",
            "empirical_matched_ratio": matched_stats.get("median_ratio"),
            "matched_pairs_count": matched_stats.get("matched_pairs_count", 0),
            "unique_itineraries_count": matched_stats.get("unique_itineraries_count", 0),
            "airline_factors": airline_factors_map,
            "current_typical_fare": latest_7d_typical,
            "current_average_fare": latest_7d_average,
            "latest_change_inr": latest_change,
            "latest_change_pct": latest_pct,
            "trend_direction": trend_dir,
            "consecutive_verified_dates": consecutive_verified_count,
            "latest_point": latest_point,
            "series": series,
        }
    finally:
        conn.close()
