"""
FareIndex India — SerpApi Google Flights Response Parser & Itinerary Validator
Normalizes raw Google Flights JSON payloads into stable, well-typed internal structures.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, Union
from ..itinerary import is_indian_airport

logger = logging.getLogger("fareindex.serpapi.parser")

# Known foreign transit airline keywords that indicate non-domestic routing
FOREIGN_TRANSIT_AIRLINES = {
    "GULF AIR", "SRILANKAN", "EMIRATES", "QATAR AIRWAYS",
    "SAUDIA", "KUWAIT AIRWAYS", "OMAN AIR", "ETIHAD",
    "FLYDUBAI", "AIR ARABIA", "SINGAPORE AIRLINES", "MALAYSIA AIRLINES",
    "THAI AIRWAYS", "SCOOT", "BATIK AIR"
}


def is_domestic_itinerary(
    itinerary_or_flight: Union[dict[str, Any], list[dict[str, Any]]]
) -> tuple[bool, str, list[str]]:
    """
    Determines whether a flight itinerary is strictly Indian domestic.
    
    Inspects:
    - Departure airport
    - Arrival airport
    - Intermediate layover airports
    - Operating airline names
    
    Returns:
    (is_domestic: bool, reason: str, airports_visited: list[str])
    """
    if not itinerary_or_flight:
        return False, "EMPTY_ITINERARY", []

    legs: list[dict[str, Any]] = []
    if isinstance(itinerary_or_flight, list):
        legs = itinerary_or_flight
    elif isinstance(itinerary_or_flight, dict):
        legs = itinerary_or_flight.get("flights", [])
        if not legs and "departure_airport" in itinerary_or_flight:
            legs = [itinerary_or_flight]

    if not legs:
        return False, "NO_FLIGHT_LEGS", []

    airports_visited: list[str] = []
    
    # Process the first departure
    first_dep = legs[0].get("departure_airport", {})
    first_dep_code = str(first_dep.get("id") or first_dep.get("name") or "").strip().upper()
    if first_dep_code:
        airports_visited.append(first_dep_code)

    for leg in legs:
        # Check airline
        airline = str(leg.get("airline") or "").strip().upper()
        for foreign_kw in FOREIGN_TRANSIT_AIRLINES:
            if foreign_kw in airline:
                arr = leg.get("arrival_airport", {})
                arr_code = str(arr.get("id") or arr.get("name") or "").strip().upper()
                if arr_code and arr_code not in airports_visited:
                    airports_visited.append(arr_code)
                return False, f"FOREIGN_TRANSIT_AIRLINE_{airline}", airports_visited

        # Check arrival airport
        arr = leg.get("arrival_airport", {})
        arr_code = str(arr.get("id") or arr.get("name") or "").strip().upper()
        if arr_code:
            airports_visited.append(arr_code)

    # Validate that all airports visited are registered Indian domestic airports
    if not airports_visited:
        return False, "AIRPORTS_UNRESOLVED", []

    for apt in airports_visited:
        if not is_indian_airport(apt):
            return False, f"INTERNATIONAL_TRANSIT_AIRPORT_{apt}", airports_visited

    return True, "DOMESTIC_ITINERARY", airports_visited


def parse_flight_item(flight_dict: dict[str, Any]) -> dict[str, Any]:
    """Parses an individual flight option (best_flights or other_flights item)."""
    price_val = flight_dict.get("price")
    price_inr: Optional[float] = None
    if price_val is not None:
        try:
            price_inr = float(price_val)
        except (ValueError, TypeError):
            price_inr = None

    legs_raw = flight_dict.get("flights", [])
    parsed_legs = []
    leg_airlines = []

    for leg in legs_raw:
        dep = leg.get("departure_airport", {})
        arr = leg.get("arrival_airport", {})
        al = leg.get("airline")
        if al:
            leg_airlines.append(str(al).strip())

        parsed_legs.append({
            "departure_airport": {
                "id": str(dep.get("id") or "").strip().upper(),
                "name": dep.get("name"),
                "time": dep.get("time"),
            },
            "arrival_airport": {
                "id": str(arr.get("id") or "").strip().upper(),
                "name": arr.get("name"),
                "time": arr.get("time"),
            },
            "airline": al,
            "flight_number": leg.get("flight_number"),
            "travel_class": leg.get("travel_class"),
            "duration": leg.get("duration"),
            "airplane": leg.get("airplane"),
            "legroom": leg.get("legroom"),
            "extensions": leg.get("extensions", []),
        })

    is_domestic, eligibility_reason, airports = is_domestic_itinerary(legs_raw)

    primary_airline = ", ".join(dict.fromkeys(leg_airlines)) if leg_airlines else None

    return {
        "price": price_inr,
        "primary_airline": primary_airline,
        "airlines": sorted(list(set(leg_airlines))),
        "duration": flight_dict.get("total_duration"),
        "type": flight_dict.get("type"),
        "is_domestic": is_domestic,
        "eligibility_reason": eligibility_reason,
        "airports_visited": airports,
        "layovers": flight_dict.get("layovers", []),
        "flights": parsed_legs,
    }


def parse_google_flights_response(data: Optional[dict[str, Any]]) -> dict[str, Any]:
    """
    Normalizes a SerpApi Google Flights response dictionary into a standardized structure.
    
    Robustly handles nullable/missing fields:
    - price_insights (missing in ~5% of queries)
    - typical_price_range (missing in some seasonal/regional dates)
    - price_history (missing in ~15% of queries)
    - best_flights / other_flights
    """
    if not data or not isinstance(data, dict):
        return {
            "lowest_price": None,
            "price_level": None,
            "typical_price_range": None,
            "price_history": None,
            "best_flights": [],
            "other_flights": [],
            "all_flights": [],
            "total_flight_results": 0,
            "airlines": [],
            "search_parameters": {},
        }

    # Extract and parse price_insights
    pi = data.get("price_insights")
    lowest_price: Optional[float] = None
    price_level: Optional[str] = None
    typical_price_range: Optional[dict[str, float]] = None
    price_history: Optional[list[list[Any]]] = None

    if isinstance(pi, dict):
        raw_lowest = pi.get("lowest_price")
        if raw_lowest is not None:
            try:
                lowest_price = float(raw_lowest)
            except (ValueError, TypeError):
                lowest_price = None

        raw_pl = pi.get("price_level")
        if raw_pl is not None:
            price_level = str(raw_pl).strip().lower()

        raw_tr = pi.get("typical_price_range")
        if isinstance(raw_tr, list) and len(raw_tr) == 2:
            try:
                typical_price_range = {
                    "low": float(raw_tr[0]),
                    "high": float(raw_tr[1])
                }
            except (ValueError, TypeError):
                typical_price_range = None
        elif isinstance(raw_tr, dict) and "low" in raw_tr and "high" in raw_tr:
            try:
                typical_price_range = {
                    "low": float(raw_tr["low"]),
                    "high": float(raw_tr["high"])
                }
            except (ValueError, TypeError):
                typical_price_range = None

        raw_ph = pi.get("price_history")
        if isinstance(raw_ph, list):
            price_history = raw_ph

    # Parse best_flights and other_flights
    best_raw = data.get("best_flights", [])
    other_raw = data.get("other_flights", [])

    best_flights = [parse_flight_item(f) for f in (best_raw if isinstance(best_raw, list) else []) if isinstance(f, dict)]
    other_flights = [parse_flight_item(f) for f in (other_raw if isinstance(other_raw, list) else []) if isinstance(f, dict)]
    all_flights = best_flights + other_flights

    # Unique airlines
    all_airlines_set = set()
    for f in all_flights:
        for al in f.get("airlines", []):
            if al:
                all_airlines_set.add(al)

    # Sanitize search parameters
    search_params = {}
    raw_sp = data.get("search_parameters")
    if isinstance(raw_sp, dict):
        search_params = dict(raw_sp)
        if "api_key" in search_params:
            search_params["api_key"] = "[REDACTED_API_KEY]"

    return {
        "lowest_price": lowest_price,
        "price_level": price_level,
        "typical_price_range": typical_price_range,
        "price_history": price_history,
        "best_flights": best_flights,
        "other_flights": other_flights,
        "all_flights": all_flights,
        "total_flight_results": len(all_flights),
        "airlines": sorted(list(all_airlines_set)),
        "search_parameters": search_params,
    }
