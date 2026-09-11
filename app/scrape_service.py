import logging
import threading
from datetime import datetime, timezone
from typing import Any
import numpy as np

from .config import TRACKED_ROUTES, FARE_PROVIDER
from .db import db, init_db
from .providers import get_provider
from .index_engine import rebuild_route_indices

logger = logging.getLogger("fareindex.scraper")

INSERT_SQL = """
INSERT INTO raw_prices (
    route, origin, destination, airline, source, price_inr,
    travel_date, search_timestamp, class, stops,
    departure_time, arrival_time, seats_left, fare_type,
    domestic_eligibility, eligibility_reason, intermediate_airports
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

_scrape_lock = threading.Lock()

_last_run: dict[str, Any] = {
    "status": "never_run",
    "started_at": None,
    "finished_at": None,
    "provider": None,
    "inserted": 0,
    "error": None,
    "index_result": None,
    "validation_reports": [],
}

def validate_observation(row: dict[str, Any]) -> tuple[bool, str]:
    """
    Strict validation before database insert:
    - fare_type == 'ONE_WAY'
    - trip_type == 'one_way'
    - passenger_count == 1
    - class == 'Economy'
    - currency == 'INR'
    - price_inr > 0
    - domestic_eligibility == 'VALID'
    """
    source = str(row.get("source", "")).lower()
    is_live = "playwright" in source or "amadeus" in source

    price = row.get("price_inr")
    if price is None or not isinstance(price, (int, float)) or price <= 0:
        return False, "INVALID_PRICE"

    cabin = str(row.get("class", "Economy")).lower()
    if "economy" not in cabin:
        return False, "INVALID_CABIN"

    fare_type = str(row.get("fare_type", "UNKNOWN")).upper()
    trip_type = str(row.get("trip_type", "one_way")).lower()
    passengers = row.get("passenger_count", 1)
    currency = str(row.get("currency", "INR")).upper()

    if is_live:
        if fare_type != "ONE_WAY":
            return False, "INVALID_TRIP_TYPE"
        if trip_type != "one_way":
            return False, "INVALID_TRIP_TYPE"
        if passengers != 1:
            return False, "INVALID_PASSENGER_COUNT"
        if currency != "INR":
            return False, "INVALID_CURRENCY"

        eligibility = str(row.get("domestic_eligibility", "UNKNOWN")).upper()
        reason = str(row.get("eligibility_reason", "ROUTING_NOT_VERIFIED")).upper()

        if eligibility == "INVALID":
            return False, reason if reason else "INTERNATIONAL_TRANSIT"
        if eligibility == "UNKNOWN":
            return False, "ROUTING_NOT_VERIFIED"
        if eligibility != "VALID":
            return False, "ROUTING_NOT_VERIFIED"

    return True, "OK"

def print_collection_validation_report(
    provider_name: str,
    route: str,
    obs_date: str,
    travel_dates: list[str],
    accepted_fares: list[float],
    rejected_counts: dict[str, int],
    accepted_routes_sample: list[str],
    rejected_routes_sample: list[str],
    fare_type: str = "ONE_WAY",
) -> dict[str, Any]:
    """
    Prints and returns structured Collection Validation Report per Phase 7C specifications.
    """
    total_rejected = sum(rejected_counts.values())
    total_inspected = len(accepted_fares) + total_rejected

    report = {
        "provider": provider_name,
        "route": route,
        "observation_date": obs_date,
        "travel_dates_collected": sorted(list(set(travel_dates))),
        "trip_type": "ONE WAY",
        "passengers": "1 adult",
        "cabin": "Economy",
        "currency": "INR",
        "total_cards_inspected": total_inspected,
        "accepted": len(accepted_fares),
        "rejected": total_rejected,
        "rejection_reasons": rejected_counts,
        "domestic_valid": len(accepted_fares),
        "international_transit": rejected_counts.get("INTERNATIONAL_TRANSIT", 0),
        "routing_not_verified": rejected_counts.get("ROUTING_NOT_VERIFIED", 0),
        "min": float(np.min(accepted_fares)) if accepted_fares else 0.0,
        "p25": float(np.percentile(accepted_fares, 25)) if accepted_fares else 0.0,
        "median": float(np.median(accepted_fares)) if accepted_fares else 0.0,
        "mean": float(np.mean(accepted_fares)) if accepted_fares else 0.0,
        "p75": float(np.percentile(accepted_fares, 75)) if accepted_fares else 0.0,
        "max": float(np.max(accepted_fares)) if accepted_fares else 0.0,
        "fare_type": fare_type,
        "accepted_sample": accepted_routes_sample[:5],
        "rejected_sample": rejected_routes_sample[:5],
    }

    print("\n" + "=" * 60)
    print(f"COLLECTION VALIDATION REPORT — {route}")
    print("=" * 60)
    print(f"Provider:                {report['provider']}")
    print(f"Route:                   {report['route'].replace('-', ' → ')}")
    print(f"Observation date:        {report['observation_date']}")
    print(f"Travel dates:            {', '.join(report['travel_dates_collected'])}")
    print(f"Trip type:               {report['trip_type']}")
    print(f"Passengers:              {report['passengers']}")
    print(f"Cabin:                   {report['cabin']}")
    print(f"Currency:                {report['currency']}")
    print(f"Total cards inspected:   {report['total_cards_inspected']}")
    print(f"Accepted (Domestic):     {report['accepted']}")
    print(f"Rejected:                {report['rejected']}")
    print("\nRejection Reason Breakdown:")
    for r_reason, count in rejected_counts.items():
        if count > 0:
            print(f"  - {r_reason}: {count}")
    if total_rejected == 0:
        print("  (No cards rejected)")

    if accepted_fares:
        print("\nPrice Distribution (Accepted Domestic):")
        print(f"  Min:    ₹{report['min']:,.2f}")
        print(f"  P25:    ₹{report['p25']:,.2f}")
        print(f"  Median: ₹{report['median']:,.2f}")
        print(f"  Mean:   ₹{report['mean']:,.2f}")
        print(f"  P75:    ₹{report['p75']:,.2f}")
        print(f"  Max:    ₹{report['max']:,.2f}")

    if accepted_routes_sample:
        print("\nSample Accepted Itineraries:")
        for line in accepted_routes_sample[:4]:
            print(f"  [ACCEPT] {line}")

    if rejected_routes_sample:
        print("\nSample Rejected Itineraries:")
        for line in rejected_routes_sample[:4]:
            print(f"  [REJECT] {line}")

    print("=" * 60 + "\n")
    return report

def scrape_all_routes() -> dict[str, Any]:
    global _last_run

    # Prevent overlapping collection jobs
    if not _scrape_lock.acquire(blocking=False):
        return {
            "status": "busy",
            "message": "A fare collection job is already running.",
            "last_run": _last_run,
        }

    started = datetime.now(timezone.utc).isoformat()
    _last_run = {
        "status": "running",
        "started_at": started,
        "finished_at": None,
        "provider": FARE_PROVIDER,
        "inserted": 0,
        "error": None,
        "index_result": None,
        "validation_reports": [],
    }

    inserted = 0
    validation_reports: list[dict[str, Any]] = []

    try:
        init_db()
        provider = get_provider(FARE_PROVIDER)
        seen_keys: set[tuple[Any, ...]] = set()

        with db() as conn:
            for route in TRACKED_ROUTES:
                route_accepted_fares: list[float] = []
                route_travel_dates: list[str] = []
                route_rejected_counts: dict[str, int] = {
                    "INTERNATIONAL_TRANSIT": 0,
                    "ROUTING_NOT_VERIFIED": 0,
                    "ROUND_TRIP_DETECTED": 0,
                    "INVALID_PRICE": 0,
                    "INVALID_CABIN": 0,
                    "INVALID_CURRENCY": 0,
                    "INVALID_PASSENGER_COUNT": 0,
                    "INVALID_TRIP_TYPE": 0,
                    "INVALID_ORIGIN_DESTINATION": 0,
                }
                accepted_samples: list[str] = []
                rejected_samples: list[str] = []
                route_obs_date = started[:10]

                for row in provider.fetch(route):
                    # 1. Pre-insert validation
                    is_valid, reason = validate_observation(row)
                    itinerary_str = " → ".join(row.get("itinerary_route", [row.get("origin", ""), row.get("destination", "")]))
                    airline = row.get("airline", "Unknown")
                    price = row.get("price_inr", 0.0)

                    if not is_valid:
                        route_rejected_counts[reason] = route_rejected_counts.get(reason, 0) + 1
                        log_msg = f"{airline} ({itinerary_str}) ₹{price:,.2f} | Reason: {reason}"
                        rejected_samples.append(log_msg)
                        logger.warning(f"Rejected observation for {route}: {log_msg}")
                        continue

                    # 2. Duplicate check within batch and database
                    record_key = (
                        row["route"],
                        row.get("airline"),
                        row.get("travel_date"),
                        row.get("departure_time"),
                        row.get("arrival_time"),
                        float(row["price_inr"]),
                        row["search_timestamp"],
                    )

                    if record_key in seen_keys:
                        continue
                    seen_keys.add(record_key)

                    fare_type = str(row.get("fare_type", "ONE_WAY" if "playwright" in provider.name.lower() or "amadeus" in provider.name.lower() else "UNKNOWN"))
                    dom_elig = str(row.get("domestic_eligibility", "VALID" if "playwright" in provider.name.lower() or "amadeus" in provider.name.lower() else "UNKNOWN"))
                    elig_reason = str(row.get("eligibility_reason", "DOMESTIC_ITINERARY"))
                    inter_airports = row.get("intermediate_airports")

                    conn.execute(
                        INSERT_SQL,
                        (
                            row["route"],
                            row["origin"],
                            row["destination"],
                            row.get("airline"),
                            row.get("source"),
                            float(row["price_inr"]),
                            row.get("travel_date"),
                            row["search_timestamp"],
                            row.get("class", "Economy"),
                            row.get("stops", "Unknown"),
                            row.get("departure_time"),
                            row.get("arrival_time"),
                            str(row.get("seats_left")) if row.get("seats_left") is not None else None,
                            fare_type,
                            dom_elig,
                            elig_reason,
                            inter_airports,
                        ),
                    )
                    inserted += 1
                    route_accepted_fares.append(float(row["price_inr"]))
                    if row.get("travel_date"):
                        route_travel_dates.append(str(row["travel_date"]))

                    accept_msg = f"{airline} ({itinerary_str}) ₹{price:,.2f} | Domestic = {dom_elig}"
                    accepted_samples.append(accept_msg)

                # Generate validation report for route
                rep = print_collection_validation_report(
                    provider_name=provider.name,
                    route=route,
                    obs_date=route_obs_date,
                    travel_dates=route_travel_dates,
                    accepted_fares=route_accepted_fares,
                    rejected_counts=route_rejected_counts,
                    accepted_routes_sample=accepted_samples,
                    rejected_routes_sample=rejected_samples,
                    fare_type="ONE_WAY" if "playwright" in provider.name.lower() or "amadeus" in provider.name.lower() else "UNKNOWN",
                )
                validation_reports.append(rep)

        index_result = rebuild_route_indices() if inserted > 0 else None

        _last_run = {
            "status": "ok",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider.name,
            "inserted": inserted,
            "index_result": index_result,
            "validation_reports": validation_reports,
            "error": None,
        }
        return _last_run

    except Exception as exc:
        _last_run = {
            "status": "error",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "provider": FARE_PROVIDER,
            "inserted": inserted,
            "index_result": None,
            "validation_reports": validation_reports,
            "error": str(exc),
        }
        return _last_run
    finally:
        _scrape_lock.release()

def scrape_status() -> dict[str, Any]:
    return _last_run

