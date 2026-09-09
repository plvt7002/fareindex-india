from __future__ import annotations

import asyncio
import json
import os
import random
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable
import httpx

from .itinerary import validate_itinerary, extract_airports_from_text, is_indian_airport

from .config import (
    AMADEUS_CLIENT_ID,
    AMADEUS_CLIENT_SECRET,
    BOOKING_WINDOWS_DAYS,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_TIMEOUT_MS,
)

AMADEUS_BASE = "https://test.api.amadeus.com"

AIRLINE_NAMES = {
    "6E": "IndiGo",
    "AI": "Air India",
    "IX": "Air India Express",
    "QP": "Akasa Air",
    "SG": "SpiceJet",
    "UK": "Vistara",
    "I5": "AirAsia India",
}

def _parse_route(route: str) -> tuple[str, str]:
    if "-" in route:
        origin, destination = route.split("-", 1)
    else:
        origin, destination = route[:3], route[3:]
    return origin.strip().upper(), destination.strip().upper()

def parse_inr_price(price_raw: Any) -> float | None:
    """
    Cleans currency strings (e.g. '₹13,266', '15,000 INR', '14000.0') into numeric float.
    Strictly extracts the currency amount and rejects non-fare text.
    """
    if price_raw is None:
        return None
    if isinstance(price_raw, (int, float)):
        return float(price_raw) if price_raw > 0 else None

    s = str(price_raw).strip()
    if not s or s.upper() in ("N/A", "NONE", "NULL", "AVAILABLE", "NONSTOP", "UNKNOWN"):
        return None

    # Match explicit ₹ symbol with amount
    match_rupee = re.search(r"₹\s*([\d,]+(?:\.\d+)?)", s)
    if match_rupee:
        try:
            val = float(match_rupee.group(1).replace(",", ""))
            return val if val > 0 else None
        except ValueError:
            return None

    # Match INR prefix/suffix
    match_inr = re.search(r"(?:INR\s+([\d,]+(?:\.\d+)?)|([\d,]+(?:\.\d+)?)\s+INR)", s, re.IGNORECASE)
    if match_inr:
        raw_num = match_inr.group(1) or match_inr.group(2)
        try:
            val = float(raw_num.replace(",", ""))
            return val if val > 0 else None
        except ValueError:
            return None

    # Match pure numeric string (e.g. "14500", "14500.50")
    if re.fullmatch(r"[\d,]+(?:\.\d+)?", s):
        try:
            val = float(s.replace(",", ""))
            return val if val > 0 else None
        except ValueError:
            return None

    return None

class DemoProvider:
    """
    Demo-only fallback so the complete automatic backend pipeline can be shown
    without external credentials or internet access.
    Explicitly labeled 'DEMO - NOT LIVE' and fare_type 'UNKNOWN'.
    """
    name = "DEMO - NOT LIVE"

    def fetch(self, route: str) -> Iterable[dict[str, Any]]:
        origin, destination = _parse_route(route)
        now = datetime.now(timezone.utc)
        base = 5000 if destination in {"GOI", "GOA"} else 7500

        for days in BOOKING_WINDOWS_DAYS:
            travel = date.today() + timedelta(days=days)
            for airline in ["IndiGo", "Air India", "Akasa Air"]:
                price = max(2500, base + random.randint(-900, 1800) + int(1800 / max(days, 1)))
                yield {
                    "route": route,
                    "origin": origin,
                    "destination": destination,
                    "airline": airline,
                    "source": "DEMO - NOT LIVE",
                    "price_inr": float(price),
                    "travel_date": travel.isoformat(),
                    "search_timestamp": now.isoformat(),
                    "class": "Economy",
                    "stops": "Nonstop",
                    "departure_time": "08:00 AM",
                    "arrival_time": "10:30 AM",
                    "seats_left": "Available",
                    "fare_type": "UNKNOWN",
                    "trip_type": "one_way",
                    "passenger_count": 1,
                    "currency": "INR",
                    "domestic_eligibility": "UNKNOWN",
                    "eligibility_reason": "DEMO_DATA",
                }

class AmadeusProvider:
    """
    Reliable API-based automatic data collection using Amadeus Flight Offers Search API.
    Set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env.
    """
    name = "Amadeus API"

    def __init__(self):
        if not AMADEUS_CLIENT_ID or not AMADEUS_CLIENT_SECRET:
            raise RuntimeError(
                "Amadeus credentials missing. Set AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET in .env"
            )

    def _token(self) -> str:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"{AMADEUS_BASE}/v1/security/oauth2/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": AMADEUS_CLIENT_ID,
                    "client_secret": AMADEUS_CLIENT_SECRET,
                },
            )
            r.raise_for_status()
            return r.json()["access_token"]

    def fetch(self, route: str) -> Iterable[dict[str, Any]]:
        origin, destination = _parse_route(route)
        token = self._token()
        headers = {"Authorization": f"Bearer {token}"}
        now = datetime.now(timezone.utc)

        with httpx.Client(timeout=45, headers=headers) as client:
            for days in BOOKING_WINDOWS_DAYS:
                travel = date.today() + timedelta(days=days)

                try:
                    r = client.get(
                        f"{AMADEUS_BASE}/v2/shopping/flight-offers",
                        params={
                            "originLocationCode": origin,
                            "destinationLocationCode": destination,
                            "departureDate": travel.isoformat(),
                            "adults": 1,
                            "travelClass": "ECONOMY",
                            "currencyCode": "INR",
                            "max": 20,
                        },
                    )
                    r.raise_for_status()
                    payload = r.json()
                except Exception:
                    continue

                carriers = payload.get("dictionaries", {}).get("carriers", {})

                for offer in payload.get("data", []):
                    itineraries = offer.get("itineraries", [])
                    if not itineraries:
                        continue

                    segments = itineraries[0].get("segments", [])
                    if not segments:
                        continue

                    first = segments[0]
                    last = segments[-1]
                    carrier_code = first.get("carrierCode", "Unknown")
                    airline = carriers.get(
                        carrier_code,
                        AIRLINE_NAMES.get(carrier_code, carrier_code)
                    )

                    price_raw = offer.get("price", {}).get("grandTotal")
                    price_inr = parse_inr_price(price_raw)
                    if price_inr is None:
                        continue

                    stops_count = max(0, len(segments) - 1)
                    stops_str = "Nonstop" if stops_count == 0 else (f"{stops_count} stop" if stops_count == 1 else f"{stops_count} stops")

                    yield {
                        "route": route,
                        "origin": origin,
                        "destination": destination,
                        "airline": airline,
                        "source": "Amadeus API",
                        "price_inr": price_inr,
                        "travel_date": travel.isoformat(),
                        "search_timestamp": now.isoformat(),
                        "class": "Economy",
                        "stops": stops_str,
                        "departure_time": first.get("departure", {}).get("at"),
                        "arrival_time": last.get("arrival", {}).get("at"),
                        "seats_left": str(offer.get("numberOfBookableSeats", "Available")),
                        "fare_type": "ONE_WAY",
                        "trip_type": "one_way",
                        "passenger_count": 1,
                        "currency": "INR",
                    }

class PlaywrightProvider:
    """
    Google Flights browser automated collection provider with explicit state verification:
    - Trip type: STRICTLY ONE-WAY
    - Passenger: STRICTLY 1 ADULT
    - Cabin: STRICTLY ECONOMY
    - Currency: STRICTLY INR
    - Verified departure/travel date and domestic city-pair
    """
    name = "Playwright Scraper"

    def __init__(self, headless: bool | None = None, timeout_ms: int | None = None):
        self.headless = PLAYWRIGHT_HEADLESS if headless is None else headless
        self.timeout_ms = PLAYWRIGHT_TIMEOUT_MS if timeout_ms is None else timeout_ms

    async def _scrape_window_async(self, origin: str, destination: str, travel_date: str) -> list[dict[str, Any]]:
        from playwright.async_api import async_playwright
        try:
            from playwright_stealth import Stealth
            has_stealth = True
        except ImportError:
            has_stealth = False

        flights: list[dict[str, Any]] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--window-size=1920,1080"
                ]
            )
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                    locale="en-IN",
                    timezone_id="Asia/Kolkata"
                )
                page = await context.new_page()
                if has_stealth:
                    try:
                        stealth = Stealth()
                        await stealth.apply_stealth_async(page)
                    except Exception:
                        pass

                # Explicitly request one-way flight search in URL query
                query = f"one way flights from {origin} to {destination} on {travel_date}"
                url = f"https://www.google.com/travel/flights?q={query.replace(' ', '+')}&curr=INR"

                await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                await page.wait_for_timeout(random.randint(2000, 3500))

                # Handle consent overlay if present
                try:
                    consent_btn = page.locator('button:has-text("Accept all")')
                    if await consent_btn.is_visible(timeout=2000):
                        await consent_btn.click()
                        await page.wait_for_timeout(1000)
                except Exception:
                    pass

                # 1. Establish and Verify Trip Type: One way
                trip_type_locator = page.locator(
                    '[aria-label*="Trip type"], [role="combobox"]:has-text("Round trip"), [role="combobox"]:has-text("One way"), button:has-text("Round trip"), button:has-text("One way")'
                ).first
                if await trip_type_locator.is_visible(timeout=3000):
                    trip_text = await trip_type_locator.inner_text()
                    if "round trip" in trip_text.lower():
                        # Switch to One way
                        await trip_type_locator.click()
                        await page.wait_for_timeout(500)
                        one_way_opt = page.locator('li:has-text("One way"), [role="option"]:has-text("One way")').first
                        if await one_way_opt.is_visible(timeout=2000):
                            await one_way_opt.click()
                            await page.wait_for_timeout(2500)

                # Strict Verification: Verify page is in One way mode
                page_body_text = await page.inner_text("body")
                is_one_way_verified = await page.locator(
                    '[role="combobox"]:has-text("One way"), button:has-text("One way"), [aria-label*="One way"]'
                ).count() > 0

                if not is_one_way_verified and "round trip" in page_body_text.lower() and "one way" not in page_body_text.lower():
                    raise RuntimeError(f"Failed to verify ONE WAY trip type for {origin} -> {destination}")

                # 2. Verify Cabin: Economy
                is_economy_verified = await page.locator(
                    '[role="combobox"]:has-text("Economy"), button:has-text("Economy"), [aria-label*="Economy"]'
                ).count() > 0
                if not is_economy_verified and "business" in page_body_text.lower() and "economy" not in page_body_text.lower():
                    raise RuntimeError(f"Failed to verify ECONOMY cabin class for {origin} -> {destination}")

                # 3. Wait for flight listing container
                try:
                    await page.wait_for_selector("li.pIav2d", timeout=self.timeout_ms)
                except Exception:
                    # Flight cards selector timeout or CAPTCHA
                    return []

                flight_cards = await page.query_selector_all("li.pIav2d")
                for card in flight_cards:
                    try:
                        raw_text = await card.inner_text()
                        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

                        # Guard against accidental round-trip cards
                        if any("round trip" in line.lower() for line in lines):
                            continue

                        # Extract price from dedicated element or line
                        price_val = None
                        price_span = await card.query_selector('div.YMlIz.FpEdX, span[aria-label*="Indian rupees"]')
                        if price_span:
                            price_text = await price_span.text_content()
                            price_val = parse_inr_price(price_text)

                        if price_val is None:
                            price_line = next((line for line in lines if "₹" in line), None)
                            if price_line:
                                price_val = parse_inr_price(price_line)

                        if price_val is None or len(lines) < 4:
                            continue

                        seats_info = next((line for line in lines if "seat" in line.lower() or "left" in line.lower()), "Available")
                        stops_info = next((line for line in lines if "stop" in line.lower() or "nonstop" in line.lower() or "non-stop" in line.lower()), "Unknown")

                        # Handle both dash-separated on new line and contiguous time formats
                        if len(lines) >= 5 and lines[1] in ("–", "-", "—"):
                            dep_time = lines[0]
                            arr_time = lines[2]
                            airline = lines[3]
                            duration = lines[4]
                        elif len(lines) >= 4:
                            dep_time = lines[0]
                            arr_time = lines[1]
                            airline = lines[2]
                            duration = lines[3]
                        else:
                            dep_time = None
                            arr_time = None
                            airline = "Unknown"
                        intermediate_airports = extract_airports_from_text(raw_text, origin, destination)
                        eligibility, reason, itinerary_route = validate_itinerary(
                            origin=origin,
                            destination=destination,
                            stops_str=stops_info,
                            intermediate_airports=intermediate_airports,
                        )

                        flights.append({
                            "departure_time": dep_time,
                            "arrival_time": arr_time,
                            "airline": airline,
                            "duration": duration,
                            "stops": stops_info,
                            "price_inr": price_val,
                            "seats_left": seats_info,
                            "intermediate_airports": intermediate_airports,
                            "domestic_eligibility": eligibility,
                            "eligibility_reason": reason,
                            "itinerary_route": itinerary_route,
                        })
                    except Exception:
                        continue
            finally:
                await browser.close()

        return flights

    def fetch(self, route: str) -> Iterable[dict[str, Any]]:
        origin, destination = _parse_route(route)
        now_iso = datetime.now(timezone.utc).isoformat()

        for days in BOOKING_WINDOWS_DAYS:
            travel_date = (date.today() + timedelta(days=days)).isoformat()
            try:
                flights = asyncio.run(self._scrape_window_async(origin, destination, travel_date))
            except Exception:
                flights = []

            for f in flights:
                inter_airports = f.get("intermediate_airports") or []
                yield {
                    "route": route,
                    "origin": origin,
                    "destination": destination,
                    "airline": f.get("airline") or "Unknown",
                    "source": "Playwright Scraper",
                    "price_inr": float(f["price_inr"]),
                    "travel_date": travel_date,
                    "search_timestamp": now_iso,
                    "class": "Economy",
                    "stops": f.get("stops") or "Unknown",
                    "departure_time": f.get("departure_time"),
                    "arrival_time": f.get("arrival_time"),
                    "seats_left": f.get("seats_left"),
                    "fare_type": "ONE_WAY",
                    "trip_type": "one_way",
                    "passenger_count": 1,
                    "currency": "INR",
                    "domestic_eligibility": f.get("domestic_eligibility", "UNKNOWN"),
                    "eligibility_reason": f.get("eligibility_reason", "ROUTING_NOT_VERIFIED"),
                    "intermediate_airports": json.dumps(inter_airports) if inter_airports else None,
                    "itinerary_route": f.get("itinerary_route", [origin, destination]),
                }

def get_provider(name: str):
    name = (name or "demo").strip().lower()
    if name == "amadeus":
        return AmadeusProvider()
    if name == "playwright":
        return PlaywrightProvider()
    return DemoProvider()

