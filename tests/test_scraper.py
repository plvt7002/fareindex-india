import unittest
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.providers import _parse_route, parse_inr_price, get_provider, PlaywrightProvider, DemoProvider, AmadeusProvider
from app.scrape_service import scrape_all_routes, scrape_status
from app.db import init_db

class TestScraperIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = Path(self.temp_db.name)

        self.db_patcher = patch("app.db.DB_PATH", self.db_path)
        self.db_patcher.start()

        init_db()

    def tearDown(self):
        self.db_patcher.stop()
        try:
            self.temp_db.close()
            self.db_path.unlink(missing_ok=True)
        except Exception:
            pass

    def test_parse_route(self):
        self.assertEqual(_parse_route("HYD-DEL"), ("HYD", "DEL"))
        self.assertEqual(_parse_route("hyd-del"), ("HYD", "DEL"))
        self.assertEqual(_parse_route("DEL-BOM"), ("DEL", "BOM"))
        self.assertEqual(_parse_route("HYDGOI"), ("HYD", "GOI"))

    def test_parse_inr_price(self):
        self.assertEqual(parse_inr_price("₹13,266"), 13266.0)
        self.assertEqual(parse_inr_price("₹ 15,125.50"), 15125.50)
        self.assertEqual(parse_inr_price("18,000 INR"), 18000.0)
        self.assertEqual(parse_inr_price("INR 14,500"), 14500.0)
        self.assertEqual(parse_inr_price(14500), 14500.0)
        self.assertEqual(parse_inr_price(14500.75), 14500.75)
        self.assertEqual(parse_inr_price("7:15 AM - 12:00 PM ₹7,242"), 7242.0)
        self.assertEqual(parse_inr_price("₹7,242 round trip"), 7242.0)

        # Invalid or non-price strings rejected
        self.assertIsNone(parse_inr_price("N/A"))
        self.assertIsNone(parse_inr_price(""))
        self.assertIsNone(parse_inr_price(None))
        self.assertIsNone(parse_inr_price("₹ 0"))
        self.assertIsNone(parse_inr_price("7:15 AM - 12:00 PM"))
        self.assertIsNone(parse_inr_price("4 hr 45 min"))
        self.assertIsNone(parse_inr_price("132 kg CO2e"))
        self.assertIsNone(parse_inr_price("Nonstop"))
        self.assertIsNone(parse_inr_price("1 stop flight with IndiGo"))

    def test_get_provider_factory(self):
        self.assertIsInstance(get_provider("demo"), DemoProvider)
        self.assertIsInstance(get_provider("playwright"), PlaywrightProvider)
        with patch("app.providers.AMADEUS_CLIENT_ID", "test_id"), patch("app.providers.AMADEUS_CLIENT_SECRET", "test_sec"):
            self.assertIsInstance(get_provider("amadeus"), AmadeusProvider)

    def test_playwright_provider_normalized_output_mocked(self):
        provider = PlaywrightProvider()

        mock_flight_cards = [
            {
                "departure_time": "06:00 AM",
                "arrival_time": "08:15 AM",
                "airline": "IndiGo",
                "duration": "2 hr 15 min",
                "stops": "Non-stop",
                "price_inr": 6500.0,
                "seats_left": "3 seats left",
            },
            {
                "departure_time": "09:30 AM",
                "arrival_time": "11:45 AM",
                "airline": "Air India",
                "duration": "2 hr 15 min",
                "stops": "Non-stop",
                "price_inr": 7800.0,
                "seats_left": "Available",
            }
        ]

        with patch.object(provider, "_scrape_window_async", return_value=mock_flight_cards), patch("app.providers.BOOKING_WINDOWS_DAYS", [7]):
            rows = list(provider.fetch("HYD-DEL"))
            self.assertEqual(len(rows), 2)
            first = rows[0]
            self.assertEqual(first["route"], "HYD-DEL")
            self.assertEqual(first["origin"], "HYD")
            self.assertEqual(first["destination"], "DEL")
            self.assertEqual(first["airline"], "IndiGo")
            self.assertEqual(first["source"], "Playwright Scraper")
            self.assertEqual(first["price_inr"], 6500.0)
            self.assertEqual(first["class"], "Economy")
            self.assertEqual(first["stops"], "Non-stop")
            self.assertEqual(first["seats_left"], "3 seats left")
            self.assertIsNotNone(first["travel_date"])
            self.assertIsNotNone(first["search_timestamp"])

    def test_scrape_all_routes_with_mocked_provider(self):
        mock_provider = MagicMock()
        mock_provider.name = "Playwright Scraper"
        mock_provider.fetch.return_value = [
            {
                "route": "HYD-DEL",
                "origin": "HYD",
                "destination": "DEL",
                "airline": "IndiGo",
                "source": "Playwright Scraper",
                "price_inr": 8200.0,
                "travel_date": "2026-09-20",
                "search_timestamp": "2026-09-01T12:00:00+00:00",
                "class": "Economy",
                "stops": "Nonstop",
                "departure_time": "06:00",
                "arrival_time": "08:15",
                "seats_left": "5",
                "fare_type": "ONE_WAY",
                "domestic_eligibility": "VALID",
                "eligibility_reason": "DOMESTIC_ITINERARY",
            },
            {
                "route": "HYD-DEL",
                "origin": "HYD",
                "destination": "DEL",
                "airline": "Air India",
                "source": "Playwright Scraper",
                "price_inr": 9100.0,
                "travel_date": "2026-09-20",
                "search_timestamp": "2026-09-07T12:00:00+00:00",
                "class": "Economy",
                "stops": "Nonstop",
                "departure_time": "09:00",
                "arrival_time": "11:15",
                "seats_left": "2",
                "fare_type": "ONE_WAY",
                "domestic_eligibility": "VALID",
                "eligibility_reason": "DOMESTIC_ITINERARY",
            }
        ]

        with patch("app.scrape_service.get_provider", return_value=mock_provider), patch("app.scrape_service.TRACKED_ROUTES", ["HYD-DEL"]):
            res = scrape_all_routes()
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["inserted"], 2)
            self.assertEqual(res["provider"], "Playwright Scraper")
            self.assertIsNotNone(res["index_result"])

            # Verify rows in SQLite raw_prices
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM raw_prices").fetchall()
            indices = conn.execute("SELECT * FROM index_values").fetchall()
            conn.close()

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["source"], "Playwright Scraper")
            # Multi-day baseline established across the 2 observation dates
            self.assertEqual(len(indices), 2)
            self.assertEqual(indices[0]["route"], "HYD-DEL")
            self.assertEqual(indices[0]["avg_fare"], 8200.0)
            self.assertEqual(indices[1]["avg_fare"], 9100.0)

    def test_duplicate_prevention_within_batch(self):
        mock_provider = MagicMock()
        mock_provider.name = "Playwright Scraper"
        # Return duplicate identical rows
        duplicate_row = {
            "route": "HYD-DEL",
            "origin": "HYD",
            "destination": "DEL",
            "airline": "IndiGo",
            "source": "Playwright Scraper",
            "price_inr": 8200.0,
            "travel_date": "2026-09-20",
            "search_timestamp": "2026-09-07T12:00:00+00:00",
            "class": "Economy",
            "stops": "Nonstop",
            "departure_time": "06:00",
            "arrival_time": "08:15",
            "seats_left": "5",
            "fare_type": "ONE_WAY",
            "domestic_eligibility": "VALID",
            "eligibility_reason": "DOMESTIC_ITINERARY",
        }
        mock_provider.fetch.return_value = [duplicate_row, duplicate_row]

        with patch("app.scrape_service.get_provider", return_value=mock_provider), patch("app.scrape_service.TRACKED_ROUTES", ["HYD-DEL"]):
            res = scrape_all_routes()
            self.assertEqual(res["status"], "ok")
            self.assertEqual(res["inserted"], 1)  # Duplicate skipped

    def test_provider_failure_reporting(self):
        mock_provider = MagicMock()
        mock_provider.fetch.side_effect = RuntimeError("Google Flights connection timeout")

        with patch("app.scrape_service.get_provider", return_value=mock_provider):
            res = scrape_all_routes()
            self.assertEqual(res["status"], "error")
            self.assertIn("Google Flights connection timeout", res["error"])
            status = scrape_status()
            self.assertEqual(status["status"], "error")

if __name__ == "__main__":
    unittest.main()
